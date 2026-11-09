"""Gera noticias.json com notícias de café que podem mexer no preço.

Busca no Google Notícias (RSS, sem chave) por temas de mercado (clima, safra, consumo, dólar, Vietnã)
e dá destaque ao Sul da Bahia e ao Espírito Santo. Logística, geopolítica e concorrentes foram
retirados a pedido do usuário (05/10/2026), menos o Vietnã.
Guarda só título, fonte, data e link (o app abre a matéria no site original).

Regras pedidas em 09/11/2026:
- Vietnã (maior produtor de robusta, mexe com o Conilon): buscas e categoria próprias, 30 dias.
- Dólar: só notícias do DIA (data de Brasília) — o dólar muda durante o dia.
- Sul da BA e ES: ficam 30 dias na lista.
- "impacto" virou "muito importante": só o que mexe de verdade no preço (ver `importante()`),
  no lugar das palavras soltas de antes (que marcavam "tombo do petróleo", "da geada ao topo do mundo"…).

Uso: python scripts/noticias.py <saida.json>
"""
import datetime as dt
import email.utils
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SITE = "https://davidcaliman-maker.github.io/painel-cafe/"
DIAS = 7            # mercado, clima, safra, consumo
DIAS_REGIONAL = 30  # Sul da BA e ES podem ficar bastante tempo
DIAS_VIETNA = 30    # sai pouca notícia em português: janela maior
MAX_REGIONAL = 20
MAX_MERCADO = 30
MAX_DOLAR = 8  # notícias de câmbio são muitas: só as mais recentes (e só as de hoje)
MAX_VIETNA = 8
BRT = dt.timezone(dt.timedelta(hours=-3))

BUSCAS_REGIONAL = [  # Sul da Bahia e Espírito Santo
    'conilon "Espírito Santo"',
    'café "Espírito Santo" safra OR colheita OR clima OR preço',
    "café capixaba",
    "Incaper café",
    'café "sul da Bahia" OR "extremo sul da Bahia"',
    "conilon Bahia",
    'café Itamaraju OR Eunápolis OR "Teixeira de Freitas" OR "Porto Seguro"',
]
BUSCAS = [  # Mercado, clima e safra
    "café geada",
    'café "El Niño" OR "La Niña"',
    "café chuva seca estiagem lavouras",
    "café safra estimativa Conab",
    "café produção Brasil safra recorde",
    "café consumo mundial demanda",
    "café estoques certificados ICE",
    "café exportação Cecafé",
    "café preço dispara OR despenca OR recorde",
    "café robusta Londres",
]
# Vietnã: maior produtor de robusta, a colheita de lá mexe com Londres e com o Conilon.
BUSCAS_VIETNA = [
    "café Vietnã colheita",
    "café Vietnã safra",
    "robusta Vietnã",
    "Vietnã café exportações OR estoques OR preços",
    "Vietnã café chuvas OR tufão OR seca",
    "café vietnamita",
    "Vietnam café",
    "Vietnã colheita robusta oferta",
]
# Portal com títulos traduzidos por máquina e muita matéria institucional: fora.
FONTES_FORA = {"Vietnam.vn"}
# Dólar: entram mesmo sem "café" no título (o dólar mexe direto no preço do Conilon).
BUSCAS_DOLAR = [
    "dólar fecha real câmbio",
    "dólar hoje Copom OR Fed OR juros",
    '"Banco Central" câmbio dólar',
]

# Categoria pelo título (a primeira que casar).
CATEGORIAS = [
    ("Vietnã", r"vietn"),
    ("Dólar", r"d[oó]lar|c[aâ]mbio|copom|\bfed\b|selic"),
    ("Clima", r"gead|el ni[nñ]o|la ni[nñ]a|chuv|seca|estiagem|clima|calor|frio|temperatura|florada"),
    ("Safra", r"safra|colheita|conab|produ[cç][aã]o|estimativa|lavoura|produtividade"),
    ("Consumo", r"consumo|demanda|estoque|consumidor"),
]
DOLAR = re.compile(r"\bd[oó]lar", re.I)
VIETNA = re.compile(r"vietn", re.I)

# ---- "Muito importante": só o que mexe de verdade no preço do café ----
# Movimento forte tem de estar LOGO DEPOIS do assunto ("café despenca", "dólar dispara"), para não
# marcar "dólar estável com tombo do petróleo" nem "da geada ao topo do mundo".
_FORTE = (r"(?:dispar|despenc|desab|tomb|salt|afund|derret|explod)\w*|"
          r"(?:maior|forte) (?:alta|queda|baixa)|m[ií]nimas?|m[aá]ximas?")
_MOVE = re.compile(r"\b(?:sobe|subi\w*|cai|ca[ií]\w*|recu\w+|avan[cç]\w+|perde\w*|ganh\w+|alta|queda|baixa|"
                   r"valoriz\w+|desvaloriz\w+|" + _FORTE + r")", re.I)
_PCT = re.compile(r"(\d{1,2}(?:[.,]\d+)?)\s*%")
_SUJ_CAFE = r"(?:caf[eé]|ar[aá]bica|robusta|conilon)"
PRECO_CAFE = re.compile(_SUJ_CAFE + r"\b(?![^;|]*(?:export|embarq|produ[cç]|[aá]rea|venda))", re.I)
CAFE_FORTE = re.compile(_SUJ_CAFE + r"\b[^.;|:]{0,40}?\b(?:" + _FORTE + r")", re.I)
DOLAR_FORTE = re.compile(r"d[oó]lar\b(?:\s+[\w,]+){0,3}?\s+(?:" + _FORTE + r")", re.I)
DOLAR_BC = re.compile(r"(?:interv\w+|leil[aã]o)[^.;|]*(?:c[aâ]mbio|d[oó]lar)|"
                      r"(?:c[aâ]mbio|d[oó]lar)[^.;|]*(?:interv\w+|leil[aã]o)", re.I)
CLIMA_RUIM = re.compile(r"gead\w*|granizo|estiagem|\bseca\b|tuf[aã]o|enchente|inunda\w*|onda de calor|"
                        r"chuvas? (?:fortes?|intensas?|excessivas?|em excesso)|falta de chuva", re.I)
DANO = re.compile(r"amea[cç]|ating|prejudic|perdas?\b|quebra|risco|alert|castig|afet|dano|atras|compromet|"
                  r"preocup|destr[uó]|reduz", re.I)
LAVOURA = re.compile(_SUJ_CAFE + r"|cafe(?:ic|z)|lavoura|vietn", re.I)
QUEBRA = re.compile(r"quebra (?:de|da|na) safra", re.I)
ORGAO = re.compile(r"conab|usda|ibge|\boic\b|rabobank|estimativa|previs[aã]o|proje[cç]", re.I)
SAFRA = re.compile(r"safra|produ[cç][aã]o|colheita", re.I)
MUDA = re.compile(r"reduz|cort[ae]|rev[eêi]|elev|aument|recorde|menor|maior|queda|\bcai\b|sobe|quebra", re.I)
VIETNA_TEMA = re.compile(r"colheita|safra|export|estoque|chuv|tuf|seca|oferta|pre[cç]o", re.I)
VIETNA_MUDA = re.compile(r"atras|avan[cç]|inici|come[cç]|queda|\bca(?:i|em)\b|recu|sobe|aument|recorde|"
                         r"menor (?:pre[cç]o|n[ií]vel)|reduz|pression|escass|apert|quebra|preju|amea|acelera|lent", re.I)
ESTOQUE = re.compile(r"estoques?[^.;|]*(?:certificad|\bice\b|mundia|globa)|"
                     r"(?:certificad|\bice\b)[^.;|]*estoques?", re.I)
ESTOQUE_MUDA = re.compile(r"menor|m[ií]nim|queda|\bcai|recu|sobe|aument|maior|baix", re.I)
TARIFA = re.compile(r"tarif\w*|taxa[cç][aã]o|sobretaxa|embargo", re.I)


def _pct(titulo, assunto):
    """Maior percentual (até 15%, variação de preço num dia) dito na MESMA frase do assunto e com verbo
    de movimento (sobe, cai, alta, queda…): "Dólar cai a R$ 5,50; Ibovespa sobe 2,22%" não vale para o dólar."""
    maior = 0.0
    for frase in re.split(r"[;|]", titulo):
        if assunto.search(frase) and _MOVE.search(frase):
            maior = max([maior] + [v for v in (float(x.replace(",", ".")) for x in _PCT.findall(frase)) if v <= 15])
    return maior


def importante(titulo, so_dolar):
    """True só para o que costuma mexer no preço: movimento forte do café ou do dólar, clima
    ameaçando lavoura, mudança de estimativa de safra, colheita/oferta do Vietnã, estoques
    certificados e tarifas sobre o café."""
    t = titulo
    if so_dolar:  # dólar: movimento forte, 1,5% ou mais no dia, ou intervenção do Banco Central
        return bool(DOLAR_FORTE.search(t) or DOLAR_BC.search(t) or _pct(t, DOLAR) >= 1.5)
    if CAFE_FORTE.search(t) or _pct(t, PRECO_CAFE) >= 3:
        return True
    if CLIMA_RUIM.search(t) and DANO.search(t) and LAVOURA.search(t):
        return True
    if QUEBRA.search(t) or (ORGAO.search(t) and SAFRA.search(t) and MUDA.search(t)):
        return True
    if VIETNA.search(t) and VIETNA_TEMA.search(t) and VIETNA_MUDA.search(t):
        return True
    if ESTOQUE.search(t) and ESTOQUE_MUDA.search(t):
        return True
    return bool(TARIFA.search(t) and CAFE.search(t))


CAFE = re.compile(r"caf[eé]|conilon|robusta|ar[aá]bica|cafeic|coffee", re.I)
# Assuntos sem efeito no preço (lazer, gastronomia, concursos) ou "café" em outro sentido.
FORA = re.compile(r"cafeteria|brunch|barista|receita|restaurante|cafezinho|caf[eé] da manh[aã]|carro|"
                  r"concurso|premia|campeonato|copa do caf|partida|torneio|achadinho|melhores da|"
                  r"lingui[cç]a|licor|queijo|frozen|conquista ouro|dia internacional do caf|\| caf[eé] com|"
                  r"x[ií]caras", re.I)
# Fora da lista de MERCADO (no Sul da BA/ES ficam): eventos, prêmios e curiosidades não mexem no preço.
FORA_MERCADO = re.compile(r"pr[eê]mio|finalist|oscar do caf|semana internacional|festival|h[aá]bitos|"
                          r"bebidas com cafe[ií]na|futebol|[ií]dolos|caf[eé] hall|cultivar|inaugura|"
                          r"caf[eé]s especiais|conquista o mundo|timor", re.I)
REGIAO = re.compile(r"\b(?:esp[ií]rito santo|capixabas?|es|bahia|baian[oa]s?|itamaraju|eun[aá]polis|"
                    r"teixeira de freitas|porto seguro|itabela|prado|alcoba[cç]a|mucuri|linhares|colatina|"
                    r"s[aã]o mateus|nova ven[eé]cia|jaguar[eé]|aracruz|sooretama|rio bananal|pinheiros|"
                    r"vila val[eé]rio|s[aã]o gabriel da palha|maril[aâ]ndia|incaper)\b", re.I)


def buscar(consulta, dias):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{consulta} when:{dias}d", "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raiz = ET.fromstring(r.read())
    for it in raiz.findall("./channel/item"):
        fonte = (it.findtext("source") or "").strip()
        titulo = (it.findtext("title") or "").strip()
        if fonte and titulo.endswith(" - " + fonte):
            titulo = titulo[: -len(" - " + fonte)].strip()
        quando = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        yield {"titulo": titulo, "fonte": fonte, "link": it.findtext("link"), "data": quando}


def palavras(titulo):
    """Palavras significativas do título (sem acento), para achar notícias repetidas."""
    t = unicodedata.normalize("NFKD", titulo.lower())
    t = "".join(c for c in t if c.isalnum() or c == " ")
    return {w for w in t.split() if len(w) >= 4 or any(ch.isdigit() for ch in w)}


def repetida(p, anteriores):
    """Mesma notícia com outro título: muitas palavras em comum, ou mesmo número + 3 palavras."""
    for q in anteriores:
        comum = p & q
        if len(comum) / max(1, len(p | q)) >= 0.45:
            return True
        if any(any(ch.isdigit() for ch in w) for w in comum) and len(comum) >= 4:
            return True
    return False


def categoria(titulo, regional):
    for nome, padrao in CATEGORIAS:
        if re.search(padrao, titulo, re.I):
            return nome
    return "Regional" if regional else "Mercado"


def publicado_anterior():
    try:
        with urllib.request.urlopen(SITE + "noticias.json", timeout=30) as r:
            return json.load(r)
    except Exception:
        return {}


def main(caminho):
    agora = dt.datetime.now(dt.timezone.utc)
    hoje = agora.astimezone(BRT).date()
    grupos = [(BUSCAS_REGIONAL, DIAS_REGIONAL, ""), (BUSCAS, DIAS, ""),
              (BUSCAS_VIETNA, DIAS_VIETNA, ""), (BUSCAS_DOLAR, 1, "dolar")]
    todas, falhas, total = [], 0, 0
    for consultas, dias, tipo in grupos:
        for consulta in consultas:
            total += 1
            try:
                todas.extend(dict(n, dolar=tipo == "dolar") for n in buscar(consulta, dias))
            except Exception as e:
                print(f"aviso: busca falhou ({consulta}): {e}")
                falhas += 1
    if falhas == total:
        raise SystemExit("todas as buscas falharam")

    # Mais recentes primeiro, para a deduplicação manter a versão mais nova de cada notícia.
    todas.sort(key=lambda x: x["data"], reverse=True)
    vistos, regional, mercado, n_dolar, n_vietna = [], [], [], 0, 0
    for n in todas:
        t = n["titulo"]
        so_dolar = bool(n["dolar"] and DOLAR.search(t) and not CAFE.search(t))
        if not (CAFE.search(t) or so_dolar) or FORA.search(t) or n["fonte"] in FONTES_FORA:
            continue
        eh_regional = not so_dolar and bool(REGIAO.search(t))
        eh_vietna = not so_dolar and bool(VIETNA.search(t))
        # Validade de cada tipo: dólar só no dia; Vietnã 30 dias; Sul da BA/ES 30 dias; o resto 7 dias.
        if so_dolar:
            if n["data"].astimezone(BRT).date() != hoje or n_dolar >= MAX_DOLAR:
                continue
        else:
            dias = DIAS_VIETNA if eh_vietna else DIAS_REGIONAL if eh_regional else DIAS
            if n["data"] < agora - dt.timedelta(days=dias):
                continue
            if eh_vietna and n_vietna >= MAX_VIETNA:
                continue
            if not eh_regional and FORA_MERCADO.search(t):
                continue
            # Qualquer notícia de dólar (mesmo falando de café) só vale no dia em que saiu.
            if categoria(t, eh_regional) == "Dólar" and n["data"].astimezone(BRT).date() != hoje:
                continue
        p = palavras(t)
        if repetida(p, vistos):
            continue
        vistos.append(p)
        n_dolar += so_dolar
        n_vietna += eh_vietna
        item = {"titulo": t, "fonte": n["fonte"], "link": n["link"],
                "data": n["data"].astimezone(dt.timezone.utc).isoformat(timespec="minutes"),
                "categoria": "Dólar" if so_dolar else categoria(t, eh_regional)}
        # O selo vale 7 dias (depois a notícia continua na lista, sem ir para o topo).
        if importante(t, so_dolar) and n["data"] >= agora - dt.timedelta(days=DIAS):
            item["impacto"] = True  # nome antigo do campo, mantido para o app que já está instalado
        (regional if eh_regional else mercado).append(item)
    # Muito importantes primeiro; depois dólar de hoje e Vietnã (para o corte não tirar nenhum deles).
    regional.sort(key=lambda x: not x.get("impacto"))
    mercado.sort(key=lambda x: (not x.get("impacto"), x["categoria"] not in ("Dólar", "Vietnã")))

    saida = {"geradoEm": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "regional": regional[:MAX_REGIONAL], "mercado": mercado[:MAX_MERCADO]}
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)

    sem_hora = lambda h: {k: v for k, v in h.items() if k != "geradoEm"}
    mudou = sem_hora(saida) != sem_hora(publicado_anterior())
    print(f'{len(saida["regional"])} regionais, {len(saida["mercado"])} de mercado; '
          + ("mudou" if mudou else "sem mudança"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("mudou=" + ("true" if mudou else "false") + "\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
