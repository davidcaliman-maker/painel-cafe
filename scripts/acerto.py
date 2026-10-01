"""Anota todo dia útil o acerto da estimativa AO VIVO do Conilon contra o Cepea do dia.

Pega no site publicado o gráfico do dia (intradia.json) e o histórico (historico.json) e grava em
dados/acerto.csv, para cada pregão, a estimativa do app às 10h, 13h, 16h e no último ponto do dia
("fim"), com Londres e o dólar daquele momento, o Cepea do dia e o erro (estimativa − Cepea).
Também guarda a base da estimativa (Cepea, Londres e dólar do fechamento anterior), para testar
depois outras fórmulas com os mesmos dados.

Roda no GitHub Actions (conferencia.yml, 22h30), depois que o Cepea do dia sai. Se o Cepea do dia
ainda não saiu ou não houve pregão, não grava nada.

Uso: python scripts/acerto.py dados/acerto.csv
"""
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.request

SITE = "https://davidcaliman-maker.github.io/painel-cafe/"
BRT = dt.timezone(dt.timedelta(hours=-3))
MOMENTOS = [("10h", 10 * 60), ("13h", 13 * 60), ("16h", 16 * 60)]
COLUNAS = ["data", "momento", "hora", "londres", "dolar", "estimativa", "cepea", "erro",
           "cepea_ant", "londres_ant", "dolar_ant", "data_ant"]


def baixar(nome):
    with urllib.request.urlopen(f"{SITE}{nome}?t={int(time.time())}", timeout=30) as r:
        return json.load(r)


def ultimo_ate(serie, m):
    """Último ponto [minuto, valor] com minuto <= m (ou None)."""
    antes = [p for p in serie if p[0] <= m]
    return antes[-1] if antes else None


def hhmm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def main(caminho):
    intra, hist = baixar("intradia.json"), baixar("historico.json")
    hoje = dt.datetime.now(BRT).date().isoformat()
    dia = intra["data"]
    if dia != hoje:
        print(f"sem pregão hoje (gráfico do dia é de {dia}); nada a anotar")
        return
    dias = {d["data"]: d for d in hist["dias"]}
    cepea = dias.get(dia, {}).get("cepeaConilon")
    if cepea is None:
        print(f"Cepea de {dia} ainda não saiu; nada a anotar")
        return
    base = dias.get(intra["anterior"]["dataCepea"])
    if not base or "cepeaConilon" not in base:
        print("sem o Cepea anterior no histórico; nada a anotar")
        return

    ser = intra["series"]
    linhas = []
    fim = ser["conilon"][-1][0] if ser["conilon"] else None
    for nome, m in MOMENTOS + ([("fim", fim)] if fim is not None else []):
        est = ultimo_ate(ser["conilon"], m)
        if not est:
            continue
        ldn = ultimo_ate(ser["londres"], m)
        usd = ultimo_ate(ser["usd"], m)
        linhas.append({
            "data": dia, "momento": nome, "hora": hhmm(est[0]),
            "londres": ldn[1] if ldn else "", "dolar": usd[1] if usd else intra["anterior"]["usd"],
            "estimativa": est[1], "cepea": cepea, "erro": round(est[1] - cepea, 2),
            "cepea_ant": base["cepeaConilon"], "londres_ant": base["londres"],
            "dolar_ant": round(base["usd"], 2), "data_ant": base["data"],
        })

    # Junta com o que já foi anotado (substitui o dia se rodar de novo).
    antigas = []
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8", newline="") as f:
            antigas = [r for r in csv.DictReader(f) if r["data"] != dia]
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(sorted(antigas + linhas, key=lambda r: (r["data"], r["momento"])))
    for r in linhas:
        print(f'{r["data"]} {r["momento"]:>3} ({r["hora"]}): estimativa {r["estimativa"]:.2f} x Cepea {cepea:.2f} '
              f'-> erro {r["erro"]:+.2f}')


if __name__ == "__main__":
    main(sys.argv[1])
