"""Gera historico.json: fechamentos diários de Londres, Nova York e do dólar, o indicador
CEPEA/Esalq do Conilon e a calibração do preço físico do Conilon.

Calibração: preço-alvo = último CEPEA Conilon + "ajusteConilonCepea" (config.json). O
diferencial sobre Londres sai do fechamento de Londres e do dólar do mesmo dia do CEPEA:
    diferencial = alvo / (0,06 × dólar) − Londres
Durante o dia o app aplica esse diferencial às cotações ao vivo.

Roda no GitHub Actions antes de publicar o site (o celular não consegue buscar esses
dados direto). Os contratos seguem a mesma regra de troca automática do app (index.html):
um vencimento fica ativo até o dia 15 do mês anterior.

Uso: python scripts/historico.py <config.json> <saida.json>
"""
import asyncio
import datetime as dt
import json
import random
import re
import string
import sys
import urllib.request

import websockets

DIAS = 10  # pregões guardados (o app mostra os últimos 7)

MERCADOS = {
    "londres": {"bolsa": "ICEEUR", "raiz": "RC", "meses": [1, 3, 5, 7, 9, 11]},
    "novaYork": {"bolsa": "ICEUS", "raiz": "KC", "meses": [3, 5, 7, 9, 12]},
}
CODIGOS = {1: "F", 3: "H", 5: "K", 7: "N", 9: "U", 11: "X", 12: "Z"}
BRT = dt.timezone(dt.timedelta(hours=-3))
SITE = "https://davidcaliman-maker.github.io/painel-cafe/"
CEPEA_URL = "https://www.cepea.org.br/br/indicador/cafe.aspx"


def contrato_auto(mercado, posicao, hoje):
    """Lista os vencimentos ainda ativos e devolve o da posição pedida (1 = primeiro)."""
    ativos = []
    for ano in range(hoje.year, hoje.year + 3):
        for mes in mercado["meses"]:
            ano_troca, mes_troca = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
            if hoje < dt.date(ano_troca, mes_troca, 15):
                ativos.append(f'{mercado["raiz"]}{CODIGOS[mes]}{ano}')
    return ativos[max(0, posicao - 1)]


def escolher_contrato(cfg, nome, hoje):
    chave = "contratoLondres" if nome == "londres" else "contratoNovaYork"
    pos = "posicaoLondres" if nome == "londres" else "posicaoNovaYork"
    manual = str(cfg.get(chave, "auto")).strip().upper()
    if manual and manual != "AUTO":
        return manual
    return contrato_auto(MERCADOS[nome], int(cfg.get(pos, 1)), hoje)


def _msg(func, params):
    p = json.dumps({"m": func, "p": params}, separators=(",", ":"))
    return f"~m~{len(p)}~m~{p}"


async def historico_diario(simbolo, barras=DIAS + 5):
    """Fechamentos diários via canal de gráficos do TradingView: {data ISO: fechamento}."""
    cs = "cs_" + "".join(random.choices(string.ascii_lowercase, k=12))
    async with websockets.connect(
        "wss://data.tradingview.com/socket.io/websocket",
        origin="https://www.tradingview.com",
        additional_headers={"User-Agent": "Mozilla/5.0"},
    ) as ws:
        await ws.send(_msg("set_auth_token", ["unauthorized_user_token"]))
        await ws.send(_msg("chart_create_session", [cs, ""]))
        await ws.send(_msg("resolve_symbol", [cs, "sym_1", '={"symbol":"%s","adjustment":"splits"}' % simbolo]))
        await ws.send(_msg("create_series", [cs, "s1", "s1", "sym_1", "1D", barras, ""]))
        while True:
            bruto = await asyncio.wait_for(ws.recv(), 30)
            for parte in re.split(r"~m~\d+~m~", bruto):
                if parte.startswith("~h~"):  # heartbeat
                    await ws.send(f"~m~{len(parte)}~m~{parte}")
                    continue
                if not parte.startswith("{"):
                    continue
                d = json.loads(parte)
                if d.get("m") == "timescale_update":
                    saida = {}
                    for barra in d["p"][1]["s1"]["s"]:
                        t, fechamento = barra["v"][0], barra["v"][4]
                        # Barras do câmbio começam na noite anterior (UTC); +12h cai no dia do pregão.
                        dia = dt.datetime.fromtimestamp(t + 12 * 3600, dt.timezone.utc).date()
                        saida[dia.isoformat()] = fechamento
                    return saida
                if d.get("m") in ("symbol_error", "series_error", "critical_error"):
                    raise RuntimeError(f"{simbolo}: {d}")


def cepea_conilon():
    """Indicador CEPEA/Esalq do café Robusta (Conilon), R$/saca: {data ISO: valor}."""
    req = urllib.request.Request(CEPEA_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/128.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    tabela = re.search(r'id="imagenet-indicador2".*?</table>', html, re.S)
    if not tabela:
        raise RuntimeError("tabela do Robusta não encontrada no CEPEA")
    valores = {}
    for d, m, a, v in re.findall(r"<td>(\d{2})/(\d{2})/(\d{4})</td>\s*<td>([\d.]+,\d+)</td>", tabela.group(0)):
        valores[f"{a}-{m}-{d}"] = float(v.replace(".", "").replace(",", "."))
    if not valores:
        raise RuntimeError("CEPEA sem valores")
    return valores


def publicado_anterior():
    """historico.json atualmente no ar (reserva se o CEPEA estiver fora)."""
    try:
        with urllib.request.urlopen(SITE + "historico.json", timeout=30) as r:
            return json.load(r)
    except Exception:
        return {}


async def main(caminho_config, caminho_saida):
    with open(caminho_config, encoding="utf-8") as f:
        cfg = json.load(f)
    hoje = dt.datetime.now(BRT).date()
    contratos = {nome: escolher_contrato(cfg, nome, hoje) for nome in MERCADOS}

    ldn = await historico_diario(f'{MERCADOS["londres"]["bolsa"]}:{contratos["londres"]}')
    ny = await historico_diario(f'{MERCADOS["novaYork"]["bolsa"]}:{contratos["novaYork"]}')
    usd = await historico_diario("FX_IDC:USDBRL")

    # Dias com pregão nas duas bolsas; o dólar usa o último fechamento disponível até o dia.
    dias = []
    for data in sorted(set(ldn) & set(ny)):
        anteriores = [d for d in usd if d <= data]
        if not anteriores:
            continue
        dias.append({"data": data, "usd": usd[max(anteriores)], "londres": ldn[data], "novaYork": ny[data]})

    anterior = publicado_anterior()
    cepea_falhou = False
    try:
        cepea = cepea_conilon()
    except Exception as e:  # CEPEA fora do ar: mantém os valores já publicados
        print(f"aviso: CEPEA indisponível ({e}); usando o último publicado")
        cepea_falhou = True
        cepea = {d["data"]: d["cepeaConilon"] for d in anterior.get("dias", []) if d.get("cepeaConilon")}
    for d in dias:
        if d["data"] in cepea:
            d["cepeaConilon"] = cepea[d["data"]]

    # Calibra pelo dia mais recente que tem CEPEA e fechamento de Londres.
    ajuste = float(cfg.get("ajusteConilonCepea", 0))
    calibracao = anterior.get("calibracao")
    com_cepea = [d for d in dias if "cepeaConilon" in d]
    if com_cepea:
        d = com_cepea[-1]
        usd_dia = round(d["usd"], 2)  # o app também usa o dólar com 2 casas
        alvo = d["cepeaConilon"] + ajuste
        calibracao = {
            "data": d["data"],
            "cepeaConilon": d["cepeaConilon"],
            "ajusteConilonCepea": ajuste,
            "precoConilon": round(alvo, 2),
            "londres": d["londres"],
            "usd": usd_dia,
            "contrato": contratos["londres"],
            "diferencialConilon": round(alvo / (0.06 * usd_dia) - d["londres"], 2),
        }

    saida = {
        "geradoEm": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "contratos": contratos,
        "calibracao": calibracao,
        "dias": dias[-DIAS:],
    }
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print(f'{len(saida["dias"])} dias, contratos {contratos}, calibração {calibracao}')
    if cepea_falhou:
        sys.exit(2)  # arquivo gravado, mas a execução fica marcada como falha (aviso por e-mail)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
