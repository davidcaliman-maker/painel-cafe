"""Produtos registrados para CAFÉ no Agrofit (Ministério da Agricultura, dados abertos, licença CC-BY) →
app/src/main/assets/agrofit-cafe.json, usado pela consulta da aba CÁLCULO (pedido do usuário em 29/10/2026).

O CSV oficial (~400 MB, uma linha por produto × cultura × praga) é lido em fluxo, sem salvar no disco; ficam só
as linhas da cultura "Café" com registro ativo. O arquivo NÃO traz dose nem volume de calda (só na bula).
Uso: python scripts/agrofit_cafe.py app/src/main/assets/agrofit-cafe.json
"""
import csv
import datetime as dt
import io
import json
import sys
import urllib.request

URL = ("https://dados.agricultura.gov.br/dataset/6c913699-e82e-4da3-a0a1-fb6c431e367f/resource/"
       "d30b30d7-e256-484e-9ab8-cd40974e1238/download/agrofitprodutosformulados.csv")


def limpar(t):
    return " ".join(str(t or "").replace("\xa0", " ").split()).strip(" ;")


def main(destino):
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (Pregao do Cafe)"})
    produtos, pragas, idx_praga = {}, [], {}
    with urllib.request.urlopen(req, timeout=600) as resp:
        linhas = csv.DictReader(io.TextIOWrapper(resp, encoding="utf-8-sig", errors="replace", newline=""), delimiter=";")
        for l in linhas:
            if limpar(l.get("CULTURA")) != "Café" or limpar(l.get("SITUACAO")).upper() != "TRUE":
                continue
            reg = limpar(l.get("NR_REGISTRO"))
            p = produtos.setdefault(reg, {
                "r": reg,
                "m": limpar(l.get("MARCA_COMERCIAL")).strip('"'),
                "i": limpar(l.get("INGREDIENTE_ATIVO")),
                "c": limpar(l.get("CLASSE")),
                "f": limpar(l.get("FORMULACAO")),
                "x": limpar(l.get("CLASSE_TOXICOLOGICA")).split(" - ")[0].replace("Categoria ", "Cat. "),
                "p": [],
            })
            chave = (limpar(l.get("PRAGA_NOME_CIENTIFICO")), limpar(l.get("PRAGA_NOME_COMUM")))
            if chave not in idx_praga:
                idx_praga[chave] = len(pragas)
                pragas.append({"s": chave[0], "n": chave[1]})
            if idx_praga[chave] not in p["p"]:
                p["p"].append(idx_praga[chave])
    if len(produtos) < 100:  # arquivo cortado ou formato mudou: mantém o publicado
        raise RuntimeError(f"só {len(produtos)} produtos para café; algo deu errado")
    try:  # nada mudou: mantém o arquivo (e a data) de antes, para o robô não gravar à toa
        with open(destino, encoding="utf-8") as f:
            antes = json.load(f)
        if antes.get("pragas") == pragas and antes.get("produtos") == sorted(produtos.values(), key=lambda p: p["m"].lower()):
            print(f"agrofit: sem mudança ({len(produtos)} produtos)")
            return
    except (OSError, ValueError):
        pass
    saida = {
        "geradoEm": dt.date.today().isoformat(),
        "fonte": "Agrofit/MAPA (dados abertos, CC-BY)",
        "pragas": pragas,
        "produtos": sorted(produtos.values(), key=lambda p: p["m"].lower()),
    }
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, separators=(",", ":"))
    print(f"agrofit: {len(produtos)} produtos, {len(pragas)} pragas/doenças/plantas daninhas para café")


if __name__ == "__main__":
    main(sys.argv[1])
