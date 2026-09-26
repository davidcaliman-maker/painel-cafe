"""Gera historico.json com os fechamentos diários de Londres, Nova York e do dólar.

Roda no GitHub Actions antes de publicar o site (o celular não consegue buscar
esse histórico direto). Os contratos seguem a mesma regra de troca automática
do app (index.html): um vencimento fica ativo até o dia 15 do mês anterior.

Uso: python scripts/historico.py <config.json> <saida.json>
"""
import asyncio
import datetime as dt
import json
import random
import re
import string
import sys

import websockets

DIAS = 10  # pregões guardados (o app mostra os últimos 7)

MERCADOS = {
    "londres": {"bolsa": "ICEEUR", "raiz": "RC", "meses": [1, 3, 5, 7, 9, 11]},
    "novaYork": {"bolsa": "ICEUS", "raiz": "KC", "meses": [3, 5, 7, 9, 12]},
}
CODIGOS = {1: "F", 3: "H", 5: "K", 7: "N", 9: "U", 11: "X", 12: "Z"}
BRT = dt.timezone(dt.timedelta(hours=-3))


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

    saida = {
        "geradoEm": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "contratos": contratos,
        "dias": dias[-DIAS:],
    }
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print(f'{len(saida["dias"])} dias, contratos {contratos}')


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
