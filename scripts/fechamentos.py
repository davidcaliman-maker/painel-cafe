"""Guarda para sempre os fechamentos do Conilon do app em dados/fechamentos.csv (pedido do usuário em
24/10/2026): o historico.json só tem os últimos pregões. Roda no pages.yml depois do historico.py.

Cada dia com fechamento ("fechamentoApp") no historico.json recém-gerado entra (ou é atualizado) no
CSV; dias que já saíram do historico.json continuam no CSV. Uma linha por pregão.
Uso: python scripts/fechamentos.py <historico.json> <dados/fechamentos.csv>
"""
import csv
import json
import os
import sys

COLUNAS = ["data", "abertura", "fechamento", "variacao", "londres", "dolar", "nova_york", "cccv"]


def main(caminho_hist, caminho_csv):
    with open(caminho_hist, encoding="utf-8") as f:
        dias = json.load(f).get("dias", [])
    linhas = {}
    if os.path.exists(caminho_csv):
        with open(caminho_csv, encoding="utf-8", newline="") as f:
            linhas = {l["data"]: l for l in csv.DictReader(f)}
    antes = dict(linhas)
    for d in dias:
        if d.get("fechamentoApp") is None:
            continue
        base = d.get("baseConilon")
        linhas[d["data"]] = {
            "data": d["data"],
            "abertura": f"{base:.2f}" if base is not None else "",
            "fechamento": f'{d["fechamentoApp"]:.2f}',
            "variacao": f'{d["fechamentoApp"] - base:.2f}' if base is not None else "",
            "londres": f'{d["londres"]:.0f}',
            "dolar": f'{d["usd"]:.4f}',
            "nova_york": f'{d["novaYork"]:.2f}',
            "cccv": f'{d["cccv"]:.2f}' if d.get("cccv") is not None else "",  # CCCV 7/8 do dia
        }
    if linhas == antes:
        print("fechamentos: nada novo")
        return
    os.makedirs(os.path.dirname(caminho_csv) or ".", exist_ok=True)
    with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, restval="")
        w.writeheader()
        for data in sorted(linhas):
            w.writerow(linhas[data])
    novos = sorted(set(linhas) - set(antes))
    print(f"fechamentos: {len(linhas)} dias" + (f" (novos: {', '.join(novos)})" if novos else " (atualizado)"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
