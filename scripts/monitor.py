"""Compara o Conilon do nosso app com o preço principal do Conilon no cotacaodocafe.com
(indicador nacional Cepea/Esalq exibido no topo do site).

Calcula o preço do app com a mesma regra do index.html (calibração do historico.json
publicado + Londres e dólar ao vivo) e grava uma linha em monitoramento/conilon.csv.

Uso: python scripts/monitor.py
"""
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

SITE_APP = "https://davidcaliman-maker.github.io/painel-cafe/"
SITE_REF = "https://cotacaodocafe.com/"
BRT = dt.timezone(dt.timedelta(hours=-3))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
CSV = os.path.join(os.path.dirname(__file__), "..", "monitoramento", "conilon.csv")


def get(url, corpo=None):
    req = urllib.request.Request(url, data=corpo, headers={"User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def scan(mercado, tickers):
    corpo = json.dumps({"symbols": {"tickers": tickers}, "columns": ["close", "time", "close[1]"]}).encode()
    dados = json.loads(get(f"https://scanner.tradingview.com/{mercado}/scan", corpo))
    return {x["s"]: {"close": x["d"][0], "time": x["d"][1], "prev": x["d"][2]} for x in dados.get("data", [])}


def preco_app():
    """Preço do Conilon como o app mostra agora, e o estado (AO VIVO / FECHAMENTO)."""
    h = json.loads(get(SITE_APP + "historico.json?t=" + str(dt.datetime.now().timestamp())))
    c = h["calibracao"]
    ctr = h["contratos"]["londres"]
    f = scan("futures", [f"ICEEUR:{ctr}", f"ICEEUR:{c['contrato']}"])
    usd = round(scan("forex", ["FX_IDC:USDBRL"])["FX_IDC:USDBRL"]["close"], 2)
    q = f[f"ICEEUR:{ctr}"]
    sessao = dt.datetime.fromtimestamp(q["time"], dt.timezone.utc).date().isoformat()
    ajuste_troca = 0.0
    if c["contrato"] != ctr and f.get(f"ICEEUR:{c['contrato']}"):
        r = f[f"ICEEUR:{c['contrato']}"]
        ajuste_troca = (r["prev"] or r["close"]) - (q["prev"] or q["close"])
    if sessao > c["data"] or ajuste_troca:
        estado, preco = "AO VIVO", (q["close"] + c["diferencialConilon"] + ajuste_troca) * 0.06 * usd
    else:
        estado, preco = "FECHAMENTO", c["precoConilon"]
    return {"preco": round(preco, 2), "estado": estado, "cepea": c["cepeaConilon"], "cepea_data": c["data"],
            "ajuste": c["ajusteConilonCepea"], "londres": q["close"], "usd": usd}


def preco_site():
    """Preço principal do Conilon no cotacaodocafe.com e a data do fechamento a que se refere."""
    t = get(SITE_REF)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    preco = re.search(r"Indicador nacional conilon R\$ ([\d.]+,\d{2})", t)
    data = re.search(r"Fechamento de [^,]+, (\d{2}/\d{2})", t)
    if not preco:
        raise RuntimeError("preço principal do Conilon não encontrado no site")
    return {"preco": float(preco.group(1).replace(".", "").replace(",", ".")), "data": data.group(1) if data else ""}


def main():
    agora = dt.datetime.now(BRT)
    app, site = preco_app(), preco_site()
    dif = round(app["preco"] - site["preco"], 2)
    linha = {
        "quando": agora.strftime("%Y-%m-%d %H:%M"),
        "app": app["preco"], "estado_app": app["estado"],
        "site_principal": site["preco"], "data_site": site["data"],
        "diferenca": dif, "diferenca_pct": round(dif / site["preco"] * 100, 2),
        "cepea": app["cepea"], "cepea_data": app["cepea_data"], "ajuste_atual": app["ajuste"],
        "ajuste_que_zeraria": round(app["ajuste"] - dif, 2),
        "londres": app["londres"], "dolar": app["usd"],
    }
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    novo = not os.path.exists(CSV)
    with open(CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linha), delimiter=";")
        if novo:
            w.writeheader()
        w.writerow(linha)
    print(json.dumps(linha, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
