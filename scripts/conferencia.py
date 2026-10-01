"""Confere se o fechamento do Conilon publicado no app bate com o preço principal do
cotacaodocafe.com (indicador Cepea/Esalq). Roda no GitHub Actions todo dia útil à noite.

Sai com erro (e o GitHub avisa por e-mail) se:
  - o app e o site estiverem em datas de fechamento diferentes (o app não pegou o Cepea do dia), ou
  - na mesma data, o valor do Cepea usado pelo app diferir do site em mais de R$ 0,50.

Uso: python scripts/conferencia.py
"""
import json
import sys
import time

from monitor import SITE_APP, get, preco_site

TOLERANCIA = 0.50


def main():
    h = json.loads(get(SITE_APP + "historico.json?t=" + str(int(time.time()))))
    cal = h["calibracao"]
    site = preco_site()
    dia_app = cal["data"][8:10] + "/" + cal["data"][5:7]
    print(f"App: Cepea {dia_app} = R$ {cal['cepeaConilon']:.2f} (preço mostrado R$ {cal['precoConilon']:.2f})")
    print(f"Site cotacaodocafe.com: fechamento {site['data']} = R$ {site['preco']:.2f}")

    problemas = []
    if not site["data"]:
        # O site mudou o jeito de mostrar a data: compara só o valor (não é motivo de alarme).
        print("aviso: data do fechamento não encontrada no site; comparando só o valor")
    elif site["data"] != dia_app:
        problemas.append(f"datas diferentes: app usa o Cepea de {dia_app}, site mostra {site['data']}")
    if not problemas and abs(cal["cepeaConilon"] - site["preco"]) > TOLERANCIA:
        problemas.append(f"valores diferentes: app R$ {cal['cepeaConilon']:.2f} × site R$ {site['preco']:.2f}")

    if problemas:
        print("PROBLEMA: " + "; ".join(problemas))
        sys.exit(1)
    print("OK: app e site iguais.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
