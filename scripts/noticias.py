"""Gera noticias.json com notícias de café que podem mexer no preço.

Busca no Google Notícias (RSS, sem chave) por temas de mercado (clima, safra, consumo,
logística, geopolítica, concorrentes) e dá destaque ao Sul da Bahia e ao Espírito Santo.
Guarda só título, fonte, data e link (o app abre a matéria no site original).

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
DIAS = 7
MAX_REGIONAL = 12
MAX_MERCADO = 30

BUSCAS = [
    # Sul da Bahia e Espírito Santo
    'conilon "Espírito Santo"',
    'café "Espírito Santo" safra OR colheita OR clima OR preço',
    "café capixaba",
    "Incaper café",
    'café "sul da Bahia" OR "extremo sul da Bahia"',
    "conilon Bahia",
    'café Itamaraju OR Eunápolis OR "Teixeira de Freitas" OR "Porto Seguro"',
    # Mercado, clima e safra
    "café geada",
    'café "El Niño" OR "La Niña"',
    "café chuva seca estiagem lavouras",
    "café safra estimativa Conab",
    "café produção Brasil safra recorde",
    "café consumo mundial demanda",
    "café estoques certificados ICE",
    "café exportação Cecafé",
    "café frete navios contêiner porto",
    "café guerra OR tarifa OR sanções",
    "café Vietnã robusta safra",
    "café Colômbia OR Indonésia OR Uganda OR Honduras safra",
]

# Categoria pelo título (a primeira que casar).
CATEGORIAS = [
    ("Clima", r"gead|el ni[nñ]o|la ni[nñ]a|chuv|seca|estiagem|clima|calor|frio|temperatura|florada"),
    ("Safra", r"safra|colheita|conab|produ[cç][aã]o|estimativa|lavoura|produtividade"),
    ("Logística", r"frete|navio|porto|cont[eê]iner|embarque|log[ií]stica|exporta"),
    ("Geopolítica", r"guerra|tarifa|san[cç]|trump|eua|estados unidos|china|europ|eudr"),
    ("Concorrentes", r"vietn|col[oô]mbia|indon[eé]sia|uganda|eti[oó]pia|honduras|peru|[ií]ndia"),
    ("Consumo", r"consumo|demanda|estoque|consumidor"),
]
CAFE = re.compile(r"caf[eé]|conilon|robusta|ar[aá]bica|cafeic|coffee", re.I)
# Assuntos sem efeito no preço (lazer, gastronomia, concursos) ou "café" em outro sentido.
FORA = re.compile(r"cafeteria|brunch|barista|receita|restaurante|cafezinho|caf[eé] da manh[aã]|carro|"
                  r"concurso|premia|campeonato|copa do caf|partida|torneio|achadinho|melhores da|"
                  r"lingui[cç]a|licor|queijo|frozen|conquista ouro", re.I)
REGIAO = re.compile(r"esp[ií]rito santo|capixaba|\bes\b|bahia|baian|itamaraju|eun[aá]polis|"
                    r"teixeira de freitas|porto seguro|itabela|prado|alcoba[cç]a|mucuri|linhares|colatina|"
                    r"s[aã]o mateus|nova ven[eé]cia|jaguar[eé]|aracruz|sooretama|rio bananal|pinheiros|"
                    r"vila val[eé]rio|s[aã]o gabriel da palha|maril[aâ]ndia|incaper", re.I)


def buscar(consulta):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{consulta} when:{DIAS}d", "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"})
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
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DIAS)
    todas, falhas = [], 0
    for consulta in BUSCAS:
        try:
            todas.extend(buscar(consulta))
        except Exception as e:
            print(f"aviso: busca falhou ({consulta}): {e}")
            falhas += 1
    if falhas == len(BUSCAS):
        raise SystemExit("todas as buscas falharam")

    # Mais recentes primeiro, para a deduplicação manter a versão mais nova de cada notícia.
    todas.sort(key=lambda x: x["data"], reverse=True)
    vistos, regional, mercado = [], [], []
    for n in todas:
        if n["data"] < limite or not CAFE.search(n["titulo"]) or FORA.search(n["titulo"]):
            continue
        p = palavras(n["titulo"])
        if repetida(p, vistos):
            continue
        vistos.append(p)
        eh_regional = bool(REGIAO.search(n["titulo"]))
        item = {"titulo": n["titulo"], "fonte": n["fonte"], "link": n["link"],
                "data": n["data"].astimezone(dt.timezone.utc).isoformat(timespec="minutes"),
                "categoria": categoria(n["titulo"], eh_regional)}
        (regional if eh_regional else mercado).append(item)

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
