"""Gera historico.json e intradia.json: fechamentos diários de Londres, Nova York e do dólar e o
preço do Conilon do próprio app. intradia.json tem o gráfico do dia (5 em 5 min).

Preço do Conilon (pedido do usuário em 24/10/2026, valendo a partir de 26/10/2026; o Cepea não é mais
usado): cada dia começa no FECHAMENTO DO APP no dia anterior ("baseConilon"). O diferencial sobre
Londres sai do fechamento de Londres e do dólar do dia anterior:
    diferencial = base / (0,06 × dólar) − Londres
e o preço do dia é (Londres + diferencial) × 0,06 × dólar. De vez em quando o usuário passa um preço
para começar um dia e recalibrar (config.json → "inicios").

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


def dolar_awesome():
    """Segunda fonte do dólar (AwesomeAPI): (cotação, variação no dia, quando em Brasília).

    Em 26/10/2026 o TradingView travou o dólar em 4,97 (fechamento de sexta) enquanto o dólar real
    subia 12%, a R$ 5,60; o app passou a conferir as duas fontes.
    """
    req = urllib.request.Request("https://economia.awesomeapi.com.br/json/last/USD-BRL",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        v = json.load(r)["USDBRL"]
    return float(v["bid"]), float(v["varBid"]), dt.datetime.fromtimestamp(int(v["timestamp"]), BRT)


async def gerar_intradia(dias, usd_diario, simbolos, usd_reserva=None):
    """Gráfico do dia (intradia.json): pontos de 5 em 5 min do último pregão de Londres.

    O Conilon do dia é a mesma estimativa do app (Londres × dólar) sobre a base do dia (fechamento
    do app no dia anterior ou o preço combinado pelo usuário). O dólar só vale
    "ao vivo" a partir das 9h; antes disso vale o fechamento anterior (como no app).
    """
    b_ldn = await barras(simbolos["londres"], "5", 400)
    b_ny = await barras(simbolos["novaYork"], "5", 400)
    b_usd = await barras("FX_IDC:USDBRL", "5", 400)
    dia = dt.datetime.fromtimestamp(b_ldn[-1][0], BRT).date().isoformat()
    ldn, ny, usd = por_minuto(b_ldn, dia), por_minuto(b_ny, dia), por_minuto(b_usd, dia)
    # TradingView com o dólar travado: vale a série da segunda fonte (pontos de cada rodada).
    fonte_usd = None
    if usd_reserva and dia == dt.datetime.now(BRT).date().isoformat():
        usd, fonte_usd = dict(usd_reserva), "awesome"

    anteriores = [d for d in dias if d["data"] < dia]
    hoje = next((d for d in dias if d["data"] == dia), {})
    if not ldn or not anteriores or hoje.get("baseConilon") is None:
        raise RuntimeError(f"intradia sem dados suficientes para {dia}")
    ant, base = anteriores[-1], hoje["baseConilon"]
    dif = diferencial(base, ant)
    usd_ant = usd_diario[max(d for d in usd_diario if d < dia)]

    def usd_vigente(m):
        v = ultimo_ate(usd, m) if m >= 9 * 60 else None
        return usd_ant if v is None else v

    arred = lambda v: round(v * 10) / 10  # de 10 em 10 centavos, como no app
    inicio_ldn = min(ldn)
    minutos = sorted(set(ldn) | {m for m in usd if m >= 9 * 60 and m >= inicio_ldn})
    conilon = [[m, arred((ultimo_ate(ldn, m) + dif) * 0.06 * round(usd_vigente(m), 2))] for m in minutos]

    saida = {
        "data": dia,
        # "conilon" = fechamento do app no dia anterior (linha pontilhada); "base" = preço em que o dia
        # começou, contra o qual a variação do dia é medida (igual ao "conilon", salvo recalibração).
        "anterior": {"data": ant["data"], "base": arred(base),
                     "conilon": ant.get("fechamentoApp", arred(base)),
                     "londres": ant["londres"], "novaYork": ant["novaYork"], "usd": round(usd_ant, 4)},
        "fechamentoApp": hoje.get("fechamentoApp"),
        "series": {
            "conilon": conilon,
            "londres": [[m, v] for m, v in sorted(ldn.items())],
            "novaYork": [[m, v] for m, v in sorted(ny.items())],
            "usd": [[m, round(v, 4)] for m, v in sorted(usd.items()) if m >= 9 * 60],
        },
    }
    if fonte_usd:
        saida["usdFonte"] = fonte_usd
    return saida


def montar_dias(ldn, ny, usd):
    """Um dia para cada data em que Londres ou Nova York negociou.

    Bolsa fechada no dia (feriado no Reino Unido ou nos EUA) repete o último fechamento dela e
    fica listada em "fechadas". O dólar usa o último fechamento até o dia.
    """
    inicio = max(min(ldn), min(ny), min(usd))
    ultimo = lambda serie, data: serie[max(k for k in serie if k <= data)]
    dias = []
    for data in sorted(d for d in set(ldn) | set(ny) if d >= inicio):
        dia = {"data": data, "usd": ultimo(usd, data), "londres": ultimo(ldn, data), "novaYork": ultimo(ny, data)}
        fechadas = [nome for nome, serie in (("londres", ldn), ("novaYork", ny)) if data not in serie]
        if fechadas:
            dia["fechadas"] = fechadas
        dias.append(dia)
    return dias


def minuto_fechado(dia):
    """Minuto do dia (Brasília) em que o app considera o dia fechado: 30 min depois do fechamento do
    câmbio, às 17h de Nova York = 18h de Brasília no horário de verão dos EUA (2º domingo de março ao
    1º domingo de novembro) e 19h fora dele. Mesma regra do index.html (minutoFechado)."""
    def domingo(mes, n):
        d = dt.date(dia.year, mes, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    verao = domingo(3, 2) <= dia < domingo(11, 1)
    return (18 if verao else 19) * 60 + 30


def diferencial(base, ant):
    """Diferencial sobre Londres que faz o preço valer "base" no fechamento do dia anterior "ant"."""
    return base / (0.06 * round(ant["usd"], 2)) - ant["londres"]


def marcar_fechamentos(dias, inicios, publicados, agora):
    """Base ("baseConilon") e fechamento do app ("fechamentoApp") de cada dia desde o 1º início combinado.

    Base do dia = preço combinado para o dia em "inicios" (o usuário recalibra de vez em quando) ou,
    sem ele, o fechamento do app no dia anterior. O fechamento é a bolsa e o dólar de fechamento
    sobre essa base; hoje só tem fechamento depois que o dólar fechou (ver minuto_fechado).
    Dias que já passaram ficam como foram publicados ("publicados"): uma troca de contrato de
    Londres não muda os preços antigos. Dias anteriores ao 1º início (época do Cepea, até 23/10/2026)
    só repetem o que foi publicado.
    """
    hoje = agora.date().isoformat()
    dolar_fechou = agora.hour * 60 + agora.minute >= minuto_fechado(agora.date())
    desde = min(inicios) if inicios else hoje
    ant = None
    for d in dias:
        pub = publicados.get(d["data"], {})
        if d["data"] < desde or (d["data"] < hoje and pub.get("fechamentoApp") is not None):
            for k in ("baseConilon", "fechamentoApp"):
                if pub.get(k) is not None:
                    d[k] = pub[k]
        elif ant is not None:
            base = inicios.get(d["data"], ant.get("fechamentoApp"))
            if base is not None:
                d["baseConilon"] = round(float(base), 2)
                if d["data"] < hoje or dolar_fechou:
                    dif = diferencial(d["baseConilon"], ant)
                    d["fechamentoApp"] = round((d["londres"] + dif) * 0.06 * round(d["usd"], 2) * 10) / 10
        ant = d

def publicado_anterior(nome="historico.json"):
    """Arquivo atualmente no ar (preços dos dias que já passaram; reserva se a bolsa estiver fora)."""
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

    # Segunda fonte do dólar: se a AwesomeAPI (cotação de hoje, depois das 9h) discordar mais de
    # 0,5% do TradingView, vale ela para hoje. O dia fica marcado "usdFonte" e, depois que passa,
    # mantém o dólar publicado (o TradingView pode continuar errado para aquele dia).
    hoje_iso = hoje.isoformat()
    usd_aw = None
    try:
        bid, _var, quando = dolar_awesome()
        minuto = quando.hour * 60 + quando.minute
        tv = usd.get(hoje_iso)
        if quando.date() == hoje and minuto >= 9 * 60 and (tv is None or abs(bid / tv - 1) > 0.005):
            usd_aw = (minuto, bid)
            usd[hoje_iso] = bid
            print(f"aviso: dólar do TradingView ({tv}) diferente da AwesomeAPI ({bid}); usando a AwesomeAPI")
    except Exception as e:
        print(f"aviso: AwesomeAPI indisponível ({e})")

    anterior = publicado_anterior()
    # Preços combinados com o usuário para começar um dia ({data: preço}); o 1º (26/10/2026) é o
    # fechamento do app em 23/10, quando o Cepea deixou de ser usado.
    inicios = {i["data"]: float(i["preco"]) for i in cfg.get("inicios", [])}
    publicados = {d["data"]: d for d in anterior.get("dias", [])}
    dias = montar_dias(ldn, ny, usd)
    for d in dias:
        pub = publicados.get(d["data"], {})
        if d["data"] == hoje_iso and usd_aw:
            d["usdFonte"] = "awesome"
        elif d["data"] < hoje_iso and pub.get("usdFonte") and pub.get("usd") is not None:
            d["usd"], d["usdFonte"] = pub["usd"], pub["usdFonte"]
    marcar_fechamentos(dias, inicios, publicados, dt.datetime.now(BRT))

    # Calibração = fechamento do app no último dia fechado, que é a base do próximo dia (salvo preço
    # combinado em "inicios", que o app também recebe).
    fechados = [d for d in dias if d.get("fechamentoApp") is not None]
    if not fechados:
        raise RuntimeError("nenhum dia com fechamento do app (histórico publicado indisponível?)")
    d = fechados[-1]
    calibracao = {
        "data": d["data"],
        "precoConilon": d["fechamentoApp"],
        "londres": d["londres"],
        "usd": round(d["usd"], 2),  # o app também usa o dólar com 2 casas
        "contrato": contratos["londres"],
        "diferencialConilon": round(diferencial(d["fechamentoApp"], d), 2),
        "inicios": [{"data": k, "preco": v} for k, v in sorted(inicios.items())],
        # Só para o alerta do APK já instalado (AlertaService.java lê estes nomes antigos): base do
        # próximo dia, sem ajuste. O app (index.html) não usa.
        "cepeaConilon": d["fechamentoApp"],
        "ajusteConilonCepea": 0,
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
    usd_reserva = None
    if usd_aw:  # junta os pontos do dólar da segunda fonte das rodadas anteriores de hoje
        usd_reserva = {}
        if intra_anterior and intra_anterior.get("data") == hoje_iso and intra_anterior.get("usdFonte"):
            usd_reserva = {m: v for m, v in intra_anterior["series"]["usd"]}
        usd_reserva[usd_aw[0]] = usd_aw[1]
    try:
        simbolos = {nome: f'{MERCADOS[nome]["bolsa"]}:{contratos[nome]}' for nome in MERCADOS}
        intra = await gerar_intradia(dias, usd, simbolos, usd_reserva)
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


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
