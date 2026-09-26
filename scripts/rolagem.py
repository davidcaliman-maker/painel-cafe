"""Ajusta os diferenciais quando o app troca de vencimento, sem mudar o preço físico.

O diferencial do config.json vale para o contrato indicado em "referenciaLondres" /
"referenciaNovaYork". Quando a regra automática passa para outro vencimento:

    diferencial novo = diferencial atual + (fechamento anterior do contrato de referência
                                            - fechamento anterior do contrato novo)

e a referência passa a ser o contrato novo. O app (index.html) aplica a mesma conta
enquanto este script ainda não rodou, então o preço não salta em nenhum momento.

Uso: python scripts/rolagem.py <config.json>
Imprime "alterado" se o arquivo foi regravado.
"""
import datetime as dt
import json
import sys
import urllib.request

from historico import BRT, MERCADOS, escolher_contrato

CAMPOS = {
    "londres": ("referenciaLondres", "diferencialConilon"),
    "novaYork": ("referenciaNovaYork", "diferencialArabica"),
}


def fechamento_anterior(tickers):
    """Fechamento do pregão anterior (close[1]); se faltar, o último preço."""
    corpo = json.dumps({"symbols": {"tickers": tickers}, "columns": ["close[1]", "close"]}).encode()
    req = urllib.request.Request("https://scanner.tradingview.com/futures/scan", data=corpo,
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = json.load(r)
    return {x["s"]: (x["d"][0] if x["d"][0] is not None else x["d"][1]) for x in dados.get("data", [])}


def main(caminho):
    with open(caminho, encoding="utf-8") as f:
        cfg = json.load(f)
    hoje = dt.datetime.now(BRT).date()
    alterado = False

    for nome, (campo_ref, campo_dif) in CAMPOS.items():
        atual = escolher_contrato(cfg, nome, hoje)
        ref = str(cfg.get(campo_ref) or atual).upper()
        if ref == atual:
            continue
        bolsa = MERCADOS[nome]["bolsa"]
        precos = fechamento_anterior([f"{bolsa}:{ref}", f"{bolsa}:{atual}"])
        p_ref, p_atual = precos.get(f"{bolsa}:{ref}"), precos.get(f"{bolsa}:{atual}")
        if p_ref is None or p_atual is None:
            raise SystemExit(f"{nome}: sem cotação para {ref} ou {atual}; diferencial não ajustado")
        antigo = float(cfg[campo_dif])
        novo = round(antigo + (p_ref - p_atual), 2)
        print(f"{nome}: {ref} -> {atual} | {ref}={p_ref} {atual}={p_atual} | "
              f"{campo_dif}: {antigo} -> {novo}")
        cfg[campo_dif] = novo
        cfg[campo_ref] = atual
        alterado = True

    if alterado:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("alterado")


if __name__ == "__main__":
    main(sys.argv[1])
