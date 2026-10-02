"""Gera historico.json e intradia.json: fechamentos diários de Londres, Nova York e do dólar, o indicador
CEPEA/Esalq do Conilon e a calibração do preço físico do Conilon. intradia.json tem o gráfico do dia (5 em 5 min).

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
import os
import random
import re
import string
import sys
import urllib.request

import websockets

DIAS = 10  # pregões guardados (o app mostra os últimos 7)
INTRA_INI, INTRA_FIM = 4 * 60, 18 * 60  # gráfico do dia: 04h às 18h (Brasília)

MERCADOS = {
    "londres": {"bolsa": "ICEEUR", "raiz": "RC", "meses": [1, 3, 5, 7, 9, 11]},
    "novaYork": {"bolsa": "ICEUS", "raiz": "KC", "meses": [3, 5, 7, 9, 12]},
}
CODIGOS = {1: "F", 3: "H", 5: "K", 7: "N", 9: "U", 11: "X", 12: "Z"}
BRT = dt.timezone(dt.timedelta(hours=-3))
SITE = "https://davidcaliman-maker.github.io/painel-cafe/"
CEPEA_URL = "https://www.cepea.org.br/br/indicador/cafe.aspx"


def contratos_ativos(mercado, hoje):
    """Vencimentos ainda ativos, do mais próximo ao mais distante."""
    ativos = []
    for ano in range(hoje.year, hoje.year + 3):
        for mes in mercado["meses"]:
            ano_troca, mes_troca = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
            if hoje < dt.date(ano_troca, mes_troca, 15):
                ativos.append(f'{mercado["raiz"]}{CODIGOS[mes]}{ano}')
    return ativos


def contrato_auto(mercado, posicao, hoje):
    """Devolve o vencimento da posição pedida (1 = primeiro)."""
    return contratos_ativos(mercado, hoje)[max(0, posicao - 1)]


def cotacoes_scanner(hoje):
    """Cotações atuais (mesma consulta que o app faz) para a reserva do app: cotacoes.json.

    Se o celular não conseguir buscar direto (ex.: falha de rede no 5G), o app usa este arquivo,
    publicado no próprio site. Inclui os 4 primeiros vencimentos de cada bolsa e o dólar.
    """
    def scan(mercado, tickers):
        corpo = json.dumps({"symbols": {"tickers": tickers},
                            "columns": ["close", "change", "time", "close[1]"]}).encode()
        req = urllib.request.Request(f"https://scanner.tradingview.com/{mercado}/scan", data=corpo,
                                     headers={"User-Agent": "Mozilla/5.0", "Content-Type": "text/plain"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dados = json.load(r)
        return {x["s"]: {"close": x["d"][0], "change": x["d"][1], "time": x["d"][2], "prev": x["d"][3]}
                for x in dados.get("data", [])}

    futuros = [f'{MERCADOS[n]["bolsa"]}:{c}' for n in MERCADOS for c in contratos_ativos(MERCADOS[n], hoje)[:4]]
    cot = scan("futures", futuros)
    cot.update(scan("forex", ["FX_IDC:USDBRL"]))
    if "FX_IDC:USDBRL" not in cot or len(cot) < 3:
        raise RuntimeError(f"scanner incompleto: {sorted(cot)}")
    return cot


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


async def barras(simbolo, resolucao, quantidade):
    """Barras do canal de gráficos do TradingView: lista de [tempo, abertura, máx, mín, fechamento, …]."""
    cs = "cs_" + "".join(random.choices(string.ascii_lowercase, k=12))
    async with websockets.connect(
        "wss://data.tradingview.com/socket.io/websocket",
        origin="https://www.tradingview.com",
        additional_headers={"User-Agent": "Mozilla/5.0"},
    ) as ws:
        await ws.send(_msg("set_auth_token", ["unauthorized_user_token"]))
        await ws.send(_msg("chart_create_session", [cs, ""]))
        await ws.send(_msg("resolve_symbol", [cs, "sym_1", '={"symbol":"%s","adjustment":"splits"}' % simbolo]))
        await ws.send(_msg("create_series", [cs, "s1", "s1", "sym_1", resolucao, quantidade, ""]))
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
                    return [b["v"] for b in d["p"][1]["s1"]["s"]]
                if d.get("m") in ("symbol_error", "series_error", "critical_error"):
                    raise RuntimeError(f"{simbolo}: {d}")


async def historico_diario(simbolo, barras_=DIAS + 5):
    """Fechamentos diários: {data ISO: fechamento}."""
    saida = {}
    for v in await barras(simbolo, "1D", barras_):
        # Barras do câmbio começam na noite anterior (UTC); +12h cai no dia do pregão.
        dia = dt.datetime.fromtimestamp(v[0] + 12 * 3600, dt.timezone.utc).date()
        saida[dia.isoformat()] = v[4]
    return saida


def por_minuto(lista, dia):
    """Barras de 5 min de um dia (horário de Brasília, 04h–18h): {minuto do dia: fechamento}."""
    saida = {}
    for v in lista:
        h = dt.datetime.fromtimestamp(v[0], BRT)
        m = h.hour * 60 + h.minute
        if h.date().isoformat() == dia and INTRA_INI <= m <= INTRA_FIM:
            saida[m] = v[4]
    return saida


def ultimo_ate(pontos, m):
    """Último valor com minuto <= m (ou None)."""
    antes = [k for k in pontos if k <= m]
    return pontos[max(antes)] if antes else None


async def gerar_intradia(dias, usd_diario, simbolos, ajuste):
    """Gráfico do dia (intradia.json): pontos de 5 em 5 min do último pregão de Londres.

    O Conilon do dia é a mesma estimativa do app (Londres × dólar) com a calibração do Cepea
    anterior ao dia; por isso a linha não muda depois que o Cepea do dia sai. O dólar só vale
    "ao vivo" a partir das 9h; antes disso vale o fechamento anterior (como no app).
    """
    b_ldn = await barras(simbolos["londres"], "5", 400)
    b_ny = await barras(simbolos["novaYork"], "5", 400)
    b_usd = await barras("FX_IDC:USDBRL", "5", 400)
    dia = dt.datetime.fromtimestamp(b_ldn[-1][0], BRT).date().isoformat()
    ldn, ny, usd = por_minuto(b_ldn, dia), por_minuto(b_ny, dia), por_minuto(b_usd, dia)

    anteriores = [d for d in dias if d["data"] < dia]
    com_cepea = [d for d in anteriores if "cepeaConilon" in d]
    if not ldn or not anteriores or not com_cepea:
        raise RuntimeError(f"intradia sem dados suficientes para {dia}")
    ant, cal = anteriores[-1], com_cepea[-1]
    preco_cal = cal["cepeaConilon"] + ajuste
    dif = preco_cal / (0.06 * round(cal["usd"], 2)) - cal["londres"]
    usd_ant = usd_diario[max(d for d in usd_diario if d < dia)]

    def usd_vigente(m):
        v = ultimo_ate(usd, m) if m >= 9 * 60 else None
        return usd_ant if v is None else v

    arred = lambda v: round(v * 10) / 10  # de 10 em 10 centavos, como no app
    inicio_ldn = min(ldn)
    minutos = sorted(set(ldn) | {m for m in usd if m >= 9 * 60 and m >= inicio_ldn})
    conilon = [[m, arred((ultimo_ate(ldn, m) + dif) * 0.06 * round(usd_vigente(m), 2))] for m in minutos]

    hoje = next((d for d in dias if d["data"] == dia), {})
    return {
        "data": dia,
        "anterior": {"data": ant["data"], "dataCepea": cal["data"], "conilon": arred(preco_cal),
                     "londres": ant["londres"], "novaYork": ant["novaYork"], "usd": round(usd_ant, 4)},
        "fechamentoCepea": arred(hoje["cepeaConilon"] + ajuste) if "cepeaConilon" in hoje else None,
        "series": {
            "conilon": conilon,
            "londres": [[m, v] for m, v in sorted(ldn.items())],
            "novaYork": [[m, v] for m, v in sorted(ny.items())],
            "usd": [[m, round(v, 4)] for m, v in sorted(usd.items()) if m >= 9 * 60],
        },
    }


def montar_dias(ldn, ny, usd, cepea):
    """Um dia para cada data em que Londres ou Nova York negociou ou o Cepea publicou.

    Bolsa fechada no dia (feriado no Reino Unido ou nos EUA) repete o último fechamento dela e
    fica listada em "fechadas"; assim o Cepea desses dias também é usado (o app mostra o
    FECHAMENTO e o dia seguinte começa por ele). O dólar usa o último fechamento até o dia.
    """
    inicio = max(min(ldn), min(ny), min(usd))
    ultimo = lambda serie, data: serie[max(k for k in serie if k <= data)]
    dias = []
    for data in sorted(d for d in set(ldn) | set(ny) | set(cepea) if d >= inicio):
        dia = {"data": data, "usd": ultimo(usd, data), "londres": ultimo(ldn, data), "novaYork": ultimo(ny, data)}
        fechadas = [nome for nome, serie in (("londres", ldn), ("novaYork", ny)) if data not in serie]
        if fechadas:
            dia["fechadas"] = fechadas
        if data in cepea:
            dia["cepeaConilon"] = cepea[data]
        dias.append(dia)
    return dias


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


def publicado_anterior(nome="historico.json"):
    """Arquivo atualmente no ar (reserva se o CEPEA ou a bolsa estiverem fora)."""
    try:
        with urllib.request.urlopen(SITE + nome, timeout=30) as r:
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

    anterior = publicado_anterior()
    try:
        cepea = cepea_conilon()
    except Exception as e:  # CEPEA fora do ar: mantém os valores já publicados
        print(f"aviso: CEPEA indisponível ({e}); usando o último publicado")
        cepea = {d["data"]: d["cepeaConilon"] for d in anterior.get("dias", []) if d.get("cepeaConilon")}

    dias = montar_dias(ldn, ny, usd, cepea)

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

    # Cotações prontas (reserva do app). Se falhar, o arquivo não é gerado e o workflow mantém
    # o publicado. Não entra no "mudou": republica junto com o histórico/gráfico do dia.
    try:
        cot = {"geradoEm": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "cotacoes": cotacoes_scanner(hoje)}
        with open(os.path.join(os.path.dirname(caminho_saida), "cotacoes.json"), "w", encoding="utf-8") as f:
            json.dump(cot, f, separators=(",", ":"))
        print(f'cotações de reserva: {len(cot["cotacoes"])} símbolos')
    except Exception as e:
        print(f"aviso: cotações de reserva indisponíveis ({e})")

    # Gráfico do dia. Se falhar, mantém o publicado (o app mostra o que tiver).
    caminho_intra = os.path.join(os.path.dirname(caminho_saida), "intradia.json")
    intra_anterior = publicado_anterior("intradia.json")
    try:
        simbolos = {nome: f'{MERCADOS[nome]["bolsa"]}:{contratos[nome]}' for nome in MERCADOS}
        intra = await gerar_intradia(dias, usd, simbolos, ajuste)
        print(f'intradia {intra["data"]}: ' + ", ".join(f"{k} {len(v)}" for k, v in intra["series"].items()))
    except Exception as e:
        print(f"aviso: gráfico do dia indisponível ({e}); mantendo o publicado")
        intra = intra_anterior
    if intra:
        with open(caminho_intra, "w", encoding="utf-8") as f:
            json.dump(intra, f, ensure_ascii=False, separators=(",", ":"))

    # Informa ao GitHub Actions se algo mudou em relação ao que está no ar (sem contar a hora
    # de geração): as execuções agendadas só republicam o site quando há dado novo.
    sem_hora = lambda h: {k: v for k, v in h.items() if k != "geradoEm"}
    mudou = sem_hora(saida) != sem_hora(anterior) or intra != intra_anterior
    print("mudou" if mudou else "sem mudança em relação ao publicado")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("mudou=" + ("true" if mudou else "false") + "\n")
    # Falha do Cepea numa rodada não marca erro (as rodadas são de 15 em 15 min e a próxima costuma
    # conseguir). Quem avisa o usuário é scripts/cepea_do_dia.py, às 22h30, se o dia ficou sem Cepea.


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
