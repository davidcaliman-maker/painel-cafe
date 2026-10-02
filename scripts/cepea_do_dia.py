"""Confere, à noite, se o app já tem o Cepea do dia (é com ele que o preço do dia seguinte começa).

Se não tiver:
  - e o Cepea já publicou → manda o "Publicar no GitHub Pages" rodar de novo e confere outra vez
    (com --corrigir); se resolver, termina sem erro;
  - senão (Cepea não publicou, site do Cepea fora do ar, Londres sem pregão…) → sai com erro e
    escreve o motivo no resumo da execução. O GitHub avisa o usuário por e-mail.

Roda no GitHub Actions (conferencia.yml, 22h30, dias úteis).
Uso: python scripts/cepea_do_dia.py [--corrigir]
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.request

from historico import BRT, SITE, cepea_conilon


# Feriados nacionais em que o Cepea não publica (mesma lista do index.html): fixos + Carnaval (seg e
# ter), Sexta-feira Santa e Corpus Christi, calculados pela Páscoa. Nesses dias não há aviso.
FERIADOS_FIXOS = {"01-01", "04-21", "05-01", "09-07", "10-12", "11-02", "11-15", "11-20", "12-25"}


def pascoa(ano):
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e, f = b // 4, b % 4, (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    n = h + l - 7 * m + 114
    return dt.date(ano, n // 31, n % 31 + 1)


def feriado(iso):
    if iso[5:] in FERIADOS_FIXOS:
        return True
    p = pascoa(int(iso[:4]))
    return any((p + dt.timedelta(days=n)).isoformat() == iso for n in (-48, -47, -2, 60))


def publicado():
    with urllib.request.urlopen(f"{SITE}historico.json?t={int(time.time())}", timeout=30) as r:
        return json.load(r)


def ddmm(iso):
    return f"{iso[8:10]}/{iso[5:7]}"


def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def avisar(msg):
    """Mensagem no log, como anotação de erro e no resumo da execução (aparece no GitHub)."""
    print(f"::error title=Cepea do dia::{msg}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"### ⚠️ Cepea do dia\n\n{msg}\n")
    sys.exit(1)


def main(corrigir):
    hoje = dt.datetime.now(BRT).date().isoformat()
    h = publicado()
    if h["calibracao"]["data"] == hoje:
        print(f'OK: o app já tem o Cepea de {ddmm(hoje)} ({brl(h["calibracao"]["cepeaConilon"])}).')
        return

    if feriado(hoje):
        print(f"Feriado nacional ({ddmm(hoje)}): o Cepea não publica hoje; nada a avisar.")
        return

    cal = h["calibracao"]
    amanha = f'Amanhã o app começa pelo último Cepea que tem: {ddmm(cal["data"])}, {brl(cal["precoConilon"])}.'
    try:
        cepea = cepea_conilon()
    except Exception as e:
        avisar(f"Não consegui abrir o site do Cepea para buscar o indicador de {ddmm(hoje)} ({e}). {amanha}")

    if hoje not in cepea:
        ultimo = max(cepea)
        avisar(f"O Cepea ainda não publicou o indicador do Conilon de {ddmm(hoje)} (pode ser feriado ou "
               f"atraso; o último publicado é {ddmm(ultimo)}, {brl(cepea[ultimo])}). {amanha}")

    if not any(d["data"] == hoje for d in h.get("dias", [])):
        avisar(f"O Cepea publicou {brl(cepea[hoje])} em {ddmm(hoje)}, mas a bolsa de Londres não teve pregão "
               f"hoje, então o app não usa esse dia para calibrar. {amanha}")

    if corrigir:
        print(f"Cepea de {ddmm(hoje)} publicado ({brl(cepea[hoje])}), mas o app ainda não tem: publicando de novo…")
        subprocess.run(["gh", "workflow", "run", "pages.yml"], check=True)
        for _ in range(20):  # até ~10 min
            time.sleep(30)
            try:
                if publicado()["calibracao"]["data"] == hoje:
                    print(f"OK: corrigido, o app agora tem o Cepea de {ddmm(hoje)} ({brl(cepea[hoje])}).")
                    return
            except Exception:
                pass
    avisar(f"O Cepea publicou {brl(cepea[hoje])} em {ddmm(hoje)}, mas o app não conseguiu buscar. {amanha}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main("--corrigir" in sys.argv)
