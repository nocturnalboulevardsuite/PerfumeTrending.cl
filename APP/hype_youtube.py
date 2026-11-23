"""
PerfumeTrending.cl — Radar del Hype con datos reales de YouTube
================================================================
Detecta qué perfumes se están volviendo virales en Latinoamérica (videos en español)
según el período elegido: hoy, esta semana, este mes, este año o el año pasado.

Cómo funciona
-------------
1. Busca en YouTube (YouTube Data API v3) los videos de perfumes en español más vistos
   publicados dentro del período, con varias búsquedas (virales, árabes, diseñador, nicho,
   reseñas, lanzamientos) y priorizando países de Latinoamérica.
2. Pide las estadísticas reales de cada video (visitas, likes, comentarios).
3. Reconoce qué perfume aparece en cada título:
   - primero contra tu catálogo (así se enlaza al comparador y a favoritos),
   - luego con una lista de casas perfumistas (Lattafa, Armaf, Afnan, Riiffs, Xerjoff, Dior...)
     para descubrir perfumes NUEVOS que aún no están en tu catálogo,
   - y, si configuras una clave de Anthropic (opcional), una IA revisa los títulos difíciles.
4. Calcula el Hype Score: visitas, cantidad de videos nuevos, canales distintos y la
   velocidad (visitas por día desde que se publicó cada video). Así sube un perfume que se
   "dispara" aunque sea nuevo, y también uno antiguo que vuelve a tener muchos videos.

Configuración (Streamlit Cloud > Settings > Secrets):

    [youtube]
    api_key = "AIza..."

    [anthropic]          # opcional, mejora el reconocimiento de nombres y los textos
    api_key = "sk-ant-..."

La cuota gratuita de YouTube es de 10.000 unidades diarias. Cada actualización de un
período usa unas 600, y los resultados se guardan en caché (compartida por todos los
visitantes) para no gastar la cuota: Hoy se renueva cada 3 h, la semana cada 6 h,
el mes cada 12 h, el año cada 24 h y el año pasado cada 7 días.
"""

# Importación de componentes (annotations) desde el módulo '__future__'
from __future__ import annotations

# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (math)
import math
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (threading)
import threading
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de librería estándar o dependencia externa (unicodedata)
import unicodedata
# Importación de librería estándar o dependencia externa (urllib.error)
import urllib.error
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de librería estándar o dependencia externa (urllib.request)
import urllib.request
# Importación de componentes (defaultdict) desde el módulo 'collections'
from collections import defaultdict
# Importación de componentes (datetime, timedelta, timezone) desde el módulo 'datetime'
from datetime import datetime, timedelta, timezone

# Importación de librería estándar o dependencia externa (streamlit)
import streamlit as st

# Asignamos 'YT_SEARCH' con 'https://www.googleapis.com/youtube/v3/sea...
YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
# Asignamos 'YT_VIDEOS' con 'https://www.googleapis.com/youtube/v3/vid...
YT_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"
# Asignamos 'ANTHROPIC_URL' con 'https://api.anthropic.com/v1/messages'
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
# Asignamos 'ANTHROPIC_MODEL' con 'claude-haiku-5-5'
ANTHROPIC_MODEL = "claude-haiku-5-5"

# Búsquedas en español; cada una se asocia a un país de Latinoamérica para priorizar esa región.
BUSQUEDAS = [
    ("perfume viral", "MX"),
    ("perfume árabe reseña", "CL"),
    ("nuevo perfume reseña", "AR"),
    ("perfumes de nicho", "CO"),
    ("mejores perfumes hombre", "MX"),
    ("mejores perfumes mujer", "CL"),
]

# Asignamos 'PERIODOS' con {'Hoy / Día': {'ttl': 3 * 3600, 'texto': '...
PERIODOS = {
    "Hoy / Día": {"ttl": 3 * 3600, "texto": "hoy"},
    "Esta Semana": {"ttl": 6 * 3600, "texto": "esta semana"},
    "Este Mes": {"ttl": 12 * 3600, "texto": "este mes"},
    "Este Año": {"ttl": 24 * 3600, "texto": "este año"},
    "Año Pasado": {"ttl": 7 * 24 * 3600, "texto": "el año pasado"},
}

# Casas perfumistas para descubrir perfumes nuevos en los títulos (nombre normalizado -> nombre visible)
MARCAS = {
    "lattafa": "Lattafa", "armaf": "Armaf", "afnan": "Afnan", "rasasi": "Rasasi",
    "al haramain": "Al Haramain", "maison alhambra": "Maison Alhambra", "alhambra": "Maison Alhambra",
    "rayhaan": "Rayhaan", "fragrance world": "Fragrance World", "french avenue": "French Avenue",
    "paris corner": "Paris Corner", "zimaya": "Zimaya", "ard al zaafaran": "Ard Al Zaafaran",
    "emper": "Emper", "riiffs": "Riiffs", "riffs": "Riiffs", "al wataniah": "Al Wataniah",
    "swiss arabian": "Swiss Arabian", "ajmal": "Ajmal", "nabeel": "Nabeel", "khadlaj": "Khadlaj",
    "dior": "Dior", "chanel": "Chanel", "ysl": "YSL", "yves saint laurent": "YSL",
    "versace": "Versace", "giorgio armani": "Armani", "armani": "Armani", "prada": "Prada",
    "paco rabanne": "Rabanne", "rabanne": "Rabanne", "carolina herrera": "Carolina Herrera",
    "jean paul gaultier": "Jean Paul Gaultier", "jpg": "Jean Paul Gaultier", "valentino": "Valentino",
    "dolce gabbana": "Dolce & Gabbana", "dolce & gabbana": "Dolce & Gabbana", "gucci": "Gucci",
    "tom ford": "Tom Ford", "creed": "Creed", "xerjoff": "Xerjoff", "parfums de marly": "Parfums de Marly",
    "maison francis kurkdjian": "Maison Francis Kurkdjian", "mfk": "Maison Francis Kurkdjian",
    "initio": "Initio", "mancera": "Mancera", "montale": "Montale", "kilian": "Kilian",
    "nishane": "Nishane", "azzaro": "Azzaro", "burberry": "Burberry", "hugo boss": "Hugo Boss",
    "boss": "Hugo Boss", "montblanc": "Montblanc", "givenchy": "Givenchy", "lancome": "Lancôme",
    "mugler": "Mugler", "bvlgari": "Bvlgari", "hermes": "Hermès", "guerlain": "Guerlain",
    "viktor rolf": "Viktor&Rolf", "viktor&rolf": "Viktor&Rolf", "jo malone": "Jo Malone",
    "le labo": "Le Labo", "byredo": "Byredo", "amouage": "Amouage", "natura": "Natura",
    "esika": "Ésika", "lbel": "L'Bel", "l bel": "L'Bel", "cyzone": "Cyzone", "zara": "Zara",
    "ariana grande": "Ariana Grande", "sol de janeiro": "Sol de Janeiro", "victoria secret": "Victoria's Secret",
    "victorias secret": "Victoria's Secret", "louis vuitton": "Louis Vuitton", "maison margiela": "Maison Margiela",
    "replica": "Maison Margiela", "diptyque": "Diptyque", "frederic malle": "Frederic Malle",
}

# Perfumes muy conocidos que suelen nombrarse sin la marca en los títulos
ALIAS_SIN_MARCA = {
    "erba pura": ("Xerjoff", "Erba Pura"),
    "khamrah": ("Lattafa", "Khamrah"),
    "asad": ("Lattafa", "Asad"),
    "yara": ("Lattafa", "Yara"),
    "badee al oud": ("Lattafa", "Bade'e Al Oud"),
    "baccarat rouge": ("Maison Francis Kurkdjian", "Baccarat Rouge 540"),
    "club de nuit": ("Armaf", "Club de Nuit"),
    "9pm": ("Afnan", "9pm"),
    "hawas": ("Rasasi", "Hawas"),
    "sauvage": ("Dior", "Sauvage"),
    "bleu de chanel": ("Chanel", "Bleu de Chanel"),
    "le male elixir": ("Jean Paul Gaultier", "Le Male Elixir"),
    "le beau": ("Jean Paul Gaultier", "Le Beau"),
    "aventus": ("Creed", "Aventus"),
    "layton": ("Parfums de Marly", "Layton"),
    "stronger with you": ("Armani", "Stronger With You"),
    "acqua di gio": ("Armani", "Acqua di Giò"),
    "eros": ("Versace", "Eros"),
    "one million": ("Rabanne", "1 Million"),
    "1 million": ("Rabanne", "1 Million"),
    "invictus": ("Rabanne", "Invictus"),
    "good girl": ("Carolina Herrera", "Good Girl"),
    "212 vip": ("Carolina Herrera", "212 VIP"),
    "libre": ("YSL", "Libre"),
    "y edp": ("YSL", "Y EDP"),
    "myslf": ("YSL", "MYSLF"),
    "his confession": ("Lattafa", "His Confession"),
    "freeze in flames": ("Riiffs", "Freeze in Flames"),
    "cloud": ("Ariana Grande", "Cloud"),
    "delina": ("Parfums de Marly", "Delina"),
    "angels share": ("Kilian", "Angels' Share"),
}

# Palabras que cortan el nombre del perfume al leer un título
PALABRAS_CORTE = {
    "review", "reseña", "resena", "opinion", "opinión", "vs", "versus", "perfume", "perfumes",
    "fragancia", "fragancias", "colonia", "el", "la", "los", "las", "que", "es", "mejor", "mejores",
    "nuevo", "nueva", "nuevos", "hombre", "hombres", "mujer", "mujeres", "para", "por", "con", "en",
    "y", "o", "top", "unboxing", "primeras", "impresiones", "clon", "clones", "dupe", "dupes", "del",
    "un", "una", "mi", "mis", "tu", "este", "esta", "lo", "se", "me", "te", "si", "no", "muy",
    "barato", "baratos", "original", "originales", "parte", "ep", "short", "shorts", "tiktok",
    "2023", "2024", "2025", "2026", "2027", "edp", "edt", "parfum", "eau", "toilette",
}
# Asignamos 'CONECTORES_INTERNOS' con {'de', 'du', 'di', 'la', 'le', 'in', 'of',...
CONECTORES_INTERNOS = {"de", "du", "di", "la", "le", "in", "of", "the", "al", "el"}
# Asignamos 'SEPARADORES' con re.compile('[|\\-–—:()\\[\\]!¡¿?,.#\\"“”/•...
SEPARADORES = re.compile(r"[|\-–—:()\[\]!¡¿?,.#\"“”/•*]+")


# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
def _secret(seccion: str, clave: str, env: str) -> str:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Evaluamos la condición lógica (seccion in st.secrets and st.secrets[seccion].get(cl...) para controlar el flujo
        if seccion in st.secrets and st.secrets[seccion].get(clave):
            # Retornamos el resultado procesado (str(st.secrets[seccion][clave]))
            return str(st.secrets[seccion][clave])
    except Exception:
        # Ejecutamos instrucción: pass
        pass
    # Retornamos el resultado procesado (os.environ.get(env, ''))
    return os.environ.get(env, "")


# Definición de función 'youtube_configurado' sin parámetros externos
def youtube_configurado() -> bool:
    # Retornamos el resultado procesado (bool(_secret('youtube', 'api_key', 'YOUTUBE_API...)
    return bool(_secret("youtube", "api_key", "YOUTUBE_API_KEY"))


# Definición de función '_norm' (parámetros: texto)
def _norm(texto: str) -> str:
    # Asignamos 'texto' con unicodedata.normalize('NFKD', str(texto or...
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    # Asignamos 'texto' con texto.lower().replace('&', ' & ')
    texto = texto.lower().replace("&", " & ")
    # Asignamos 'texto' con re.sub('[^a-z0-9& ]+', ' ', texto)
    texto = re.sub(r"[^a-z0-9& ]+", " ", texto)
    # Retornamos el resultado procesado (re.sub('\\s+', ' ', texto).strip())
    return re.sub(r"\s+", " ", texto).strip()


# Definición de función '_get_json' (parámetros: url, params, timeout)
def _get_json(url: str, params: dict, timeout: int = 20) -> dict:
    # Asignamos 'full' con f'{url}?{urllib.parse.urlencode(params)}'
    full = f"{url}?{urllib.parse.urlencode(params)}"
    # Asignamos 'req' con urllib.request.Request(full, headers={'Acc...
    req = urllib.request.Request(full, headers={"Accept": "application/json"})
    # Gestión automática de contexto y recursos para: urllib.request.urlopen(req, timeout=timeout)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        # Retornamos el resultado procesado (json.loads(resp.read().decode('utf-8')))
        return json.loads(resp.read().decode("utf-8"))


# Definición de función '_rango_periodo' (parámetros: periodo)
def _rango_periodo(periodo: str) -> tuple[datetime, datetime]:
    # Asignamos 'ahora' con datetime.now(timezone.utc)
    ahora = datetime.now(timezone.utc)
    # Evaluamos la condición lógica (periodo == 'Hoy / Día') para controlar el flujo
    if periodo == "Hoy / Día":
        # Retornamos el resultado procesado ((ahora - timedelta(days=1), ahora))
        return ahora - timedelta(days=1), ahora
    # Evaluamos la condición lógica (periodo == 'Esta Semana') para controlar el flujo
    if periodo == "Esta Semana":
        # Retornamos el resultado procesado ((ahora - timedelta(days=7), ahora))
        return ahora - timedelta(days=7), ahora
    # Evaluamos la condición lógica (periodo == 'Este Mes') para controlar el flujo
    if periodo == "Este Mes":
        # Retornamos el resultado procesado ((ahora - timedelta(days=30), ahora))
        return ahora - timedelta(days=30), ahora
    # Evaluamos la condición lógica (periodo == 'Este Año') para controlar el flujo
    if periodo == "Este Año":
        # Retornamos el resultado procesado ((datetime(ahora.year, 1, 1, tzinfo=timezone.utc...)
        return datetime(ahora.year, 1, 1, tzinfo=timezone.utc), ahora
    # Evaluamos la condición lógica (periodo == 'Año Pasado') para controlar el flujo
    if periodo == "Año Pasado":
        # Retornamos el resultado procesado ((datetime(ahora.year - 1, 1, 1, tzinfo=timezone...)
        return (datetime(ahora.year - 1, 1, 1, tzinfo=timezone.utc),
                datetime(ahora.year, 1, 1, tzinfo=timezone.utc))
    # Retornamos el resultado procesado ((ahora - timedelta(days=30), ahora))
    return ahora - timedelta(days=30), ahora


# Definición de función '_iso' (parámetros: dt)
def _iso(dt: datetime) -> str:
    # Retornamos el resultado procesado (dt.strftime('%Y-%m-%dT%H:%M:%SZ'))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# Definición de función 'formatear_numero' (parámetros: n)
def formatear_numero(n: float) -> str:
    # Asignamos 'n' con float(n or 0)
    n = float(n or 0)
    # Evaluamos la condición lógica (n >= 1000000) para controlar el flujo
    if n >= 1_000_000:
        # Retornamos el resultado procesado (f'{n / 1000000:.1f}M'.replace('.0M', 'M'))
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    # Evaluamos la condición lógica (n >= 1000) para controlar el flujo
    if n >= 1_000:
        # Retornamos el resultado procesado (f'{n / 1000:.0f}k')
        return f"{n / 1_000:.0f}k"
    # Retornamos el resultado procesado (f'{int(n)}')
    return f"{int(n)}"


# -----------------------------------------------------------------------------
# 1) Descarga de videos y estadísticas desde YouTube
# -----------------------------------------------------------------------------
def _buscar_videos(api_key: str, desde: datetime, hasta: datetime) -> dict:
    # Asignamos 'videos' con {}
    videos = {}
    # Asignamos 'errores' con []
    errores = []
    # Recorremos iterativamente cada '(consulta, region)' en BUSQUEDAS
    for consulta, region in BUSQUEDAS:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'data' con _get_json(YT_SEARCH, {'part': 'snippet', '...
            data = _get_json(YT_SEARCH, {
                "part": "snippet",
                "type": "video",
                "q": consulta,
                "order": "viewCount",
                "maxResults": 50,
                "publishedAfter": _iso(desde),
                "publishedBefore": _iso(hasta),
                "relevanceLanguage": "es",
                "regionCode": region,
                "safeSearch": "none",
                "key": api_key,
            })
        except urllib.error.HTTPError as exc:
            # Asignamos 'cuerpo' con ''
            cuerpo = ""
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 'cuerpo' con exc.read().decode('utf-8')
                cuerpo = exc.read().decode("utf-8")
            except Exception:
                # Ejecutamos instrucción: pass
                pass
            # Evaluamos la condición lógica (exc.code == 403 and 'quota' in cuerpo.lower()) para controlar el flujo
            if exc.code == 403 and "quota" in cuerpo.lower():
                # Propagamos excepción explícita ante condición de error detectada
                raise RuntimeError("Se agotó la cuota diaria de YouTube. Se renueva cada día.") from exc
            # Evaluamos la condición lógica (exc.code in (400, 403)) para controlar el flujo
            if exc.code in (400, 403):
                # Propagamos excepción explícita ante condición de error detectada
                raise RuntimeError("YouTube rechazó la clave de API. Revisa [youtube] api_key en Secrets.") from exc
            # Ejecutamos instrucción: errores.append(str(exc))
            errores.append(str(exc))
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        except Exception as exc:
            # Ejecutamos instrucción: errores.append(str(exc))
            errores.append(str(exc))
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Recorremos iterativamente cada 'item' en data.get('items', [])
        for item in data.get("items", []):
            # Asignamos 'vid' con (item.get('id') or {}).get('videoId')
            vid = (item.get("id") or {}).get("videoId")
            # Asignamos 'sn' con item.get('snippet') or {}
            sn = item.get("snippet") or {}
            # Evaluamos la condición lógica (not vid or vid in videos) para controlar el flujo
            if not vid or vid in videos:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'thumbs' con sn.get('thumbnails') or {}
            thumbs = sn.get("thumbnails") or {}
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
            # Asignamos 'videos[vid]' con {'id': vid, 'titulo': sn.get('title', ''),...
            videos[vid] = {
                "id": vid,
                "titulo": sn.get("title", ""),
                "descripcion": sn.get("description", ""),
                "canal": sn.get("channelTitle", ""),
                "canal_id": sn.get("channelId", ""),
                "publicado": sn.get("publishedAt", ""),
                "miniatura": thumb,
                "visitas": 0,
                "likes": 0,
                "comentarios": 0,
            }
    # Evaluamos la condición lógica (not videos and errores) para controlar el flujo
    if not videos and errores:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("No se pudo conectar con YouTube en este momento.")

    # Estadísticas reales (1 unidad de cuota por cada 50 videos)
    ids = list(videos.keys())
    # Recorremos iterativamente cada 'i' en range(0, len(ids), 50)
    for i in range(0, len(ids), 50):
        # Asignamos 'lote' con ids[i:i + 50]
        lote = ids[i:i + 50]
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'data' con _get_json(YT_VIDEOS, {'part': 'statistics'...
            data = _get_json(YT_VIDEOS, {"part": "statistics", "id": ",".join(lote), "key": api_key})
        except Exception:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Recorremos iterativamente cada 'item' en data.get('items', [])
        for item in data.get("items", []):
            # Asignamos 'stats' con item.get('statistics') or {}
            stats = item.get("statistics") or {}
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            v = videos.get(item.get("id"))
            # Evaluamos la condición lógica (v) para controlar el flujo
            if v:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                v["visitas"] = int(stats.get("viewCount", 0) or 0)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                v["likes"] = int(stats.get("likeCount", 0) or 0)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                v["comentarios"] = int(stats.get("commentCount", 0) or 0)
    # Retornamos el resultado procesado (videos)
    return videos


# -----------------------------------------------------------------------------
# 2) Reconocimiento del perfume en cada video
# -----------------------------------------------------------------------------
def _indice_catalogo(catalogo: list[dict]) -> list[tuple[str, str, dict]]:
    """Lista de (nombre_normalizado, marca_normalizada, perfume) ordenada de más a menos específica."""
    # Asignamos 'indice' con []
    indice = []
    # Recorremos iterativamente cada 'p' en catalogo or []
    for p in catalogo or []:
        # Asignamos 'nombre' con _norm(p.get('nombre', ''))
        nombre = _norm(p.get("nombre", ""))
        # Asignamos 'marca' con _norm(p.get('marca', ''))
        marca = _norm(p.get("marca", ""))
        # Evaluamos la condición lógica (not nombre) para controlar el flujo
        if not nombre:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Quita concentraciones del final para reconocer "Sauvage" en "Dior Sauvage EDT"
        nucleo = re.sub(r"\b(eau de parfum|eau de toilette|edp|edt|parfum|extrait|cologne)\b", " ", nombre)
        # Asignamos 'nucleo' con re.sub('\\s+', ' ', nucleo).strip() or nombre
        nucleo = re.sub(r"\s+", " ", nucleo).strip() or nombre
        # Evaluamos la condición lógica (marca and nucleo.startswith(marca + ' ')) para controlar el flujo
        if marca and nucleo.startswith(marca + " "):
            # Asignamos 'nucleo' con nucleo[len(marca) + 1:]
            nucleo = nucleo[len(marca) + 1:]
        # Evaluamos la condición lógica (len(nucleo) < 3) para controlar el flujo
        if len(nucleo) < 3:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Ejecutamos instrucción: indice.append((nucleo, marca, p))
        indice.append((nucleo, marca, p))
    # Ejecutamos instrucción: indice.sort(key=lambda t: len(t[0]), reverse=True)
    indice.sort(key=lambda t: len(t[0]), reverse=True)
    # Retornamos el resultado procesado (indice)
    return indice


# Definición de función '_palabras_con_mayuscula' (parámetros: original)
def _palabras_con_mayuscula(original: str) -> set[str] | None:
    """Palabras escritas con mayúscula inicial en el título. None si el título está todo en MAYÚSCULAS."""
    # Asignamos 'letras' con [c for c in original if c.isalpha()]
    letras = [c for c in original if c.isalpha()]
    # Evaluamos la condición lógica (not letras or sum((c.isupper() for c in letras)) / l...) para controlar el flujo
    if not letras or sum(c.isupper() for c in letras) / len(letras) > 0.6:
        # Retornamos el resultado procesado (None)
        return None
    # Retornamos el resultado procesado ({_norm(w) for w in re.findall("[\\w']+", origin...)
    return {_norm(w) for w in re.findall(r"[\w']+", original) if w[:1].isupper() or w[:1].isdigit()}


# Definición de función '_tokens_siguientes' (parámetros: texto_norm, frase, maximo, original)
def _tokens_siguientes(texto_norm: str, frase: str, maximo: int = 2, original: str = "") -> list[str]:
    """Palabras que siguen a `frase` y forman parte del nombre (p. ej. 'Khamrah Qahwa', 'Sauvage Elixir').

    Solo cuentan las que vienen escritas con mayúscula en el título original, para no confundir
    "Erba Pura vuelve a estar de moda" con un perfume llamado "Erba Pura Vuelve".
    """
    # Asignamos 'mayus' con _palabras_con_mayuscula(original) if origi...
    mayus = _palabras_con_mayuscula(original) if original else None
    # Evaluamos la condición lógica (not mayus) para controlar el flujo
    if not mayus:
        # Retornamos el resultado procesado ([])
        return []
    # Asignamos 't' con f' {texto_norm} '
    t = f" {texto_norm} "
    # Asignamos 'pos' con t.find(f' {frase} ')
    pos = t.find(f" {frase} ")
    # Evaluamos la condición lógica (pos < 0) para controlar el flujo
    if pos < 0:
        # Retornamos el resultado procesado ([])
        return []
    # Asignamos 'siguientes' con []
    siguientes = []
    # Recorremos iterativamente cada 'tok' en t[pos + len(frase) + 2:].split()
    for tok in t[pos + len(frase) + 2:].split():
        # Evaluamos la condición lógica (tok in PALABRAS_CORTE or tok in MARCAS or tok in CON...) para controlar el flujo
        if tok in PALABRAS_CORTE or tok in MARCAS or tok in CONECTORES_INTERNOS or tok not in mayus:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Ejecutamos instrucción: siguientes.append(tok)
        siguientes.append(tok)
        # Evaluamos la condición lógica (len(siguientes) >= maximo) para controlar el flujo
        if len(siguientes) >= maximo:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
    # Retornamos el resultado procesado (siguientes)
    return siguientes


# Definición de función '_formatear_nombre' (parámetros: tokens)
def _formatear_nombre(tokens: list[str]) -> str:
    # Asignamos 'nombre' con ' '.join((t.upper() if len(t) <= 3 and any...
    nombre = " ".join(t.upper() if len(t) <= 3 and any(c.isdigit() for c in t) else t.capitalize() for t in tokens)
    # Asignamos 'nombre' con re.sub('\\b(De|Du|Di|La|Le|In|Of|The|Al|El...
    nombre = re.sub(r"\b(De|Du|Di|La|Le|In|Of|The|Al|El)\b", lambda m: m.group(0).lower(), nombre)
    # Retornamos el resultado procesado (nombre[:1].upper() + nombre[1:])
    return nombre[:1].upper() + nombre[1:]


# Definición de función '_buscar_en_catalogo' (parámetros: texto_norm, indice, original)
def _buscar_en_catalogo(texto_norm: str, indice, original: str = "") -> dict | None:
    # Recorremos iterativamente cada '(nucleo, marca, p)' en indice
    for nucleo, marca, p in indice:
        # Evaluamos la condición lógica (f' {nucleo} ' in f' {texto_norm} ') para controlar el flujo
        if f" {nucleo} " in f" {texto_norm} ":
            # Si al nombre le sigue otra palabra del nombre (p. ej. "Khamrah Qahwa", "Sauvage Elixir"),
            # es una versión distinta del perfume del catálogo: no se mezcla.
            if original and _tokens_siguientes(texto_norm, nucleo, 1, original):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Nombres cortos o genéricos exigen que también aparezca la marca
            if len(nucleo) < 6 or len(nucleo.split()) == 1 and len(nucleo) < 8:
                # Evaluamos la condición lógica (marca and f' {marca} ' not in f' {texto_norm} ') para controlar el flujo
                if marca and f" {marca} " not in f" {texto_norm} ":
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
            # Retornamos el resultado procesado (p)
            return p
    # Retornamos el resultado procesado (None)
    return None


# Definición de función '_extraer_por_marca' (parámetros: titulo)
def _extraer_por_marca(titulo: str) -> tuple[str, str] | None:
    """Encuentra el perfume de un título y devuelve (marca, nombre)."""
    # Asignamos 'tn' con _norm(titulo)
    tn = _norm(titulo)

    # 1) "<Marca> <Nombre>": Lattafa Khamrah Qahwa, Afnan 9pm Rebel, Riiffs Freeze in Flames...
    #    Se lee cada tramo del título por separado (los signos | - : ¿ ? cortan el nombre).
    mayus = _palabras_con_mayuscula(titulo)
    # Asignamos 'tramos' con [_norm(t) for t in SEPARADORES.split(titul...
    tramos = [_norm(t) for t in SEPARADORES.split(titulo) if _norm(t)]
    # Recorremos iterativamente cada 'marca_norm' en sorted(MARCAS, key=len, reverse=True)
    for marca_norm in sorted(MARCAS, key=len, reverse=True):
        # Asignamos 'tramo' con next((tr for tr in tramos if f' {marca_nor...
        tramo = next((tr for tr in tramos if f" {marca_norm} " in f" {tr} "), None)
        # Evaluamos la condición lógica (tramo is None) para controlar el flujo
        if tramo is None:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'pos' con f' {tramo} '.find(f' {marca_norm} ')
        pos = f" {tramo} ".find(f" {marca_norm} ")
        # Asignamos 'resto_norm' con tramo[pos + len(marca_norm):].strip()
        resto_norm = tramo[pos + len(marca_norm):].strip()
        # Asignamos 'tokens' con []
        tokens = []
        # Recorremos iterativamente cada 'tok' en resto_norm.split()
        for tok in resto_norm.split():
            # Evaluamos la condición lógica (tok in PALABRAS_CORTE or tok in MARCAS) para controlar el flujo
            if tok in PALABRAS_CORTE or tok in MARCAS:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # En títulos normales el nombre va con mayúscula ("Khamrah de Lattafa sigue siendo...")
            if mayus is not None and tok not in mayus and tok not in CONECTORES_INTERNOS:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # Ejecutamos instrucción: tokens.append(tok)
            tokens.append(tok)
            # Evaluamos la condición lógica (len(tokens) >= 4) para controlar el flujo
            if len(tokens) >= 4:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
        # Ejecutamos el ciclo mientras se mantenga la condición: tokens and tokens[-1] in CONECTORES_INTERNOS
        while tokens and tokens[-1] in CONECTORES_INTERNOS:
            # Ejecutamos instrucción: tokens.pop()
            tokens.pop()
        # Evaluamos la condición lógica (not tokens or (len(tokens) == 1 and len(tokens[0]) <...) para controlar el flujo
        if not tokens or (len(tokens) == 1 and len(tokens[0]) < 3 and not tokens[0].isdigit()):
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Retornamos el resultado procesado ((MARCAS[marca_norm], _formatear_nombre(tokens)))
        return MARCAS[marca_norm], _formatear_nombre(tokens)

    # 2) Perfumes famosos nombrados sin la marca ("Erba Pura", "Khamrah Qahwa de Lattafa"...)
    for alias in sorted(ALIAS_SIN_MARCA, key=len, reverse=True):
        # Evaluamos la condición lógica (f' {alias} ' in f' {tn} ') para controlar el flujo
        if f" {alias} " in f" {tn} ":
            # Asignamos '(marca, nombre)' con ALIAS_SIN_MARCA[alias]
            marca, nombre = ALIAS_SIN_MARCA[alias]
            # Asignamos 'extra' con _tokens_siguientes(tn, alias, 2, titulo)
            extra = _tokens_siguientes(tn, alias, 2, titulo)
            # Evaluamos la condición lógica (extra) para controlar el flujo
            if extra:
                # Asignamos 'nombre' con f'{nombre} {_formatear_nombre(extra)}'
                nombre = f"{nombre} {_formatear_nombre(extra)}"
            # Retornamos el resultado procesado ((marca, nombre))
            return marca, nombre
    # Retornamos el resultado procesado (None)
    return None


# Definición de función '_extraer_con_ia' (parámetros: titulos)
def _extraer_con_ia(titulos: list[str]) -> dict[int, tuple[str, str]]:
    """Opcional: una IA identifica el perfume principal de cada título difícil."""
    # Asignamos 'api_key' con _secret('anthropic', 'api_key', 'ANTHROPIC...
    api_key = _secret("anthropic", "api_key", "ANTHROPIC_API_KEY")
    # Evaluamos la condición lógica (not api_key or not titulos) para controlar el flujo
    if not api_key or not titulos:
        # Retornamos el resultado procesado ({})
        return {}
    # Asignamos 'lista' con '\n'.join((f'{i}. {t}' for i, t in enumera...
    lista = "\n".join(f"{i}. {t}" for i, t in enumerate(titulos))
    # Asignamos 'prompt' con f"""Eres experto en perfumería. Para cada ...
    prompt = (
        "Eres experto en perfumería. Para cada título de video de YouTube, identifica el perfume "
        "principal del que habla (marca y nombre comercial exacto). Si el título no trata de un perfume "
        "específico (por ejemplo, 'top 10 perfumes'), responde null.\n"
        "Responde SOLO con JSON, sin texto adicional, con este formato: "
        '{"0": {"marca": "Lattafa", "perfume": "Khamrah"}, "1": null}\n\n'
        f"Títulos:\n{lista}"
    )
    # Procesamiento de serialización o deserialización de estructura JSON
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    # Asignamos 'req' con urllib.request.Request(ANTHROPIC_URL, data...
    req = urllib.request.Request(ANTHROPIC_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Gestión automática de contexto y recursos para: urllib.request.urlopen(req, timeout=60)
        with urllib.request.urlopen(req, timeout=60) as resp:
            # Procesamiento de serialización o deserialización de estructura JSON
            data = json.loads(resp.read().decode("utf-8"))
        # Asignamos 'texto' con ''.join((b.get('text', '') for b in data.g...
        texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        # Asignamos 'texto' con texto.strip().removeprefix('```json').remo...
        texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        # Procesamiento de serialización o deserialización de estructura JSON
        crudo = json.loads(texto)
    except Exception:
        # Retornamos el resultado procesado ({})
        return {}
    # Asignamos 'salida' con {}
    salida = {}
    # Recorremos iterativamente cada '(k, v)' en (crudo or {}).items()
    for k, v in (crudo or {}).items():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Evaluamos la condición lógica (v and v.get('marca') and v.get('perfume')) para controlar el flujo
            if v and v.get("marca") and v.get("perfume"):
                # Asignamos 'salida[int(k)]' con (str(v['marca']).strip()[:40], str(v['perf...
                salida[int(k)] = (str(v["marca"]).strip()[:40], str(v["perfume"]).strip()[:60])
        except Exception:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
    # Retornamos el resultado procesado (salida)
    return salida


# -----------------------------------------------------------------------------
# 3) Hype Score y ranking
# -----------------------------------------------------------------------------
def _calcular_ranking(videos: dict, catalogo: list[dict], periodo: str, limite: int) -> list[dict]:
    # Asignamos 'indice' con _indice_catalogo(catalogo)
    indice = _indice_catalogo(catalogo)
    # Asignamos 'ahora' con datetime.now(timezone.utc)
    ahora = datetime.now(timezone.utc)
    # Asignamos 'grupos' con {}
    grupos: dict[str, dict] = {}
    # Asignamos 'sin_identificar' con []
    sin_identificar = []

    # Definición de función 'agregar' (parámetros: clave, video, perfume_cat, marca, ...)
    def agregar(clave, video, perfume_cat=None, marca="", nombre=""):
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        g = grupos.get(clave)
        # Evaluamos la condición lógica (g is None) para controlar el flujo
        if g is None:
            # Asignamos 'g' con {'perfume': perfume_cat, 'marca': marca, '...
            g = grupos[clave] = {
                "perfume": perfume_cat, "marca": marca, "nombre": nombre,
                "videos": [], "canales": set(),
            }
        # Ejecutamos instrucción: g['videos'].append(video)
        g["videos"].append(video)
        # Ejecutamos instrucción: g['canales'].add(video['canal_id'] or video['canal'])
        g["canales"].add(video["canal_id"] or video["canal"])

    # Recorremos iterativamente cada 'v' en videos.values()
    for v in videos.values():
        # Asignamos 'texto' con _norm(f"{v['titulo']} {v['descripcion'][:1...
        texto = _norm(f"{v['titulo']} {v['descripcion'][:160]}")
        # Asignamos 'p' con _buscar_en_catalogo(texto, indice, v['titu...
        p = _buscar_en_catalogo(texto, indice, v["titulo"])
        # Evaluamos la condición lógica (p) para controlar el flujo
        if p:
            # Ejecutamos instrucción: agregar(f"cat:{p['id']}", v, perfume_cat=p)
            agregar(f"cat:{p['id']}", v, perfume_cat=p)
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'hallado' con _extraer_por_marca(v['titulo'])
        hallado = _extraer_por_marca(v["titulo"])
        # Evaluamos la condición lógica (hallado) para controlar el flujo
        if hallado:
            # Asignamos '(marca, nombre)' con hallado
            marca, nombre = hallado
            # ¿El perfume descubierto en realidad está en el catálogo?
            p2 = _buscar_en_catalogo(_norm(f"{marca} {nombre}"), indice, f"{marca} {nombre}")
            # Evaluamos la condición lógica (p2) para controlar el flujo
            if p2:
                # Ejecutamos instrucción: agregar(f"cat:{p2['id']}", v, perfume_cat=p2)
                agregar(f"cat:{p2['id']}", v, perfume_cat=p2)
            else:
                # Ejecutamos instrucción: agregar(f"new:{_norm(marca + ' ' + nombre)}", v, mar...
                agregar(f"new:{_norm(marca + ' ' + nombre)}", v, marca=marca, nombre=nombre)
        else:
            # Ejecutamos instrucción: sin_identificar.append(v)
            sin_identificar.append(v)

    # IA opcional para los títulos que no se reconocieron (los más vistos primero)
    if sin_identificar:
        # Ejecutamos instrucción: sin_identificar.sort(key=lambda x: x['visitas'], rev...
        sin_identificar.sort(key=lambda x: x["visitas"], reverse=True)
        # Asignamos 'candidatos' con sin_identificar[:120]
        candidatos = sin_identificar[:120]
        # Asignamos 'respuesta' con _extraer_con_ia([c['titulo'] for c in cand...
        respuesta = _extraer_con_ia([c["titulo"] for c in candidatos])
        # Recorremos iterativamente cada '(i, (marca, nombre))' en respuesta.items()
        for i, (marca, nombre) in respuesta.items():
            # Evaluamos la condición lógica (0 <= i < len(candidatos)) para controlar el flujo
            if 0 <= i < len(candidatos):
                # Asignamos 'v' con candidatos[i]
                v = candidatos[i]
                # Asignamos 'p3' con _buscar_en_catalogo(_norm(f'{marca} {nombr...
                p3 = _buscar_en_catalogo(_norm(f"{marca} {nombre}"), indice, f"{marca} {nombre}")
                # Evaluamos la condición lógica (p3) para controlar el flujo
                if p3:
                    # Ejecutamos instrucción: agregar(f"cat:{p3['id']}", v, perfume_cat=p3)
                    agregar(f"cat:{p3['id']}", v, perfume_cat=p3)
                else:
                    # Ejecutamos instrucción: agregar(f"new:{_norm(marca + ' ' + nombre)}", v, mar...
                    agregar(f"new:{_norm(marca + ' ' + nombre)}", v, marca=marca, nombre=nombre)

    # Asignamos 'minimo_videos' con 1 if periodo == 'Hoy / Día' else 2
    minimo_videos = 1 if periodo == "Hoy / Día" else 2
    # Asignamos 'filas' con []
    filas = []
    # Recorremos iterativamente cada '(clave, g)' en grupos.items()
    for clave, g in grupos.items():
        # Asignamos 'vids' con g['videos']
        vids = g["videos"]
        # Evaluamos la condición lógica (len(vids) < minimo_videos) para controlar el flujo
        if len(vids) < minimo_videos:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'visitas' con sum((v['visitas'] for v in vids))
        visitas = sum(v["visitas"] for v in vids)
        # Asignamos 'likes' con sum((v['likes'] for v in vids))
        likes = sum(v["likes"] for v in vids)
        # Asignamos 'comentarios' con sum((v['comentarios'] for v in vids))
        comentarios = sum(v["comentarios"] for v in vids)
        # Asignamos 'velocidad' con 0.0
        velocidad = 0.0
        # Recorremos iterativamente cada 'v' en vids
        for v in vids:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 'pub' con datetime.strptime(v['publicado'], '%Y-%m-%...
                pub = datetime.strptime(v["publicado"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                # Asignamos 'dias' con max((ahora - pub).total_seconds() / 86400,...
                dias = max((ahora - pub).total_seconds() / 86400, 0.5)
            except Exception:
                # Asignamos 'dias' con 7
                dias = 7
            # Actualizamos acumulativamente el valor de 'velocidad'
            velocidad += v["visitas"] / dias
        # Asignamos 'top' con max(vids, key=lambda x: x['visitas'])
        top = max(vids, key=lambda x: x["visitas"])
        # Puntaje bruto: alcance + cantidad de videos + canales distintos + velocidad + interacción
        bruto = (
            0.40 * math.log10(visitas + 1)
            + 0.20 * math.log2(len(vids) + 1)
            + 0.15 * math.log2(len(g["canales"]) + 1)
            + 0.20 * math.log10(velocidad + 1)
            + 0.05 * math.log10(likes + comentarios + 1)
        )
        # Evaluamos la condición lógica (g['perfume']) para controlar el flujo
        if g["perfume"]:
            # Asignamos 'p' con g['perfume']
            p = g["perfume"]
            # Asignamos 'nombre_vis' con f"{p.get('marca', '')} {p.get('nombre', ''...
            nombre_vis = f"{p.get('marca', '')} {p.get('nombre', '')}".strip()
        else:
            # Asignamos 'nombre_vis' con f"{g['marca']} {g['nombre']}".strip()
            nombre_vis = f"{g['marca']} {g['nombre']}".strip()
        # Ejecutamos instrucción: filas.append({'clave': clave, 'perfume_id': g['perfu...
        filas.append({
            "clave": clave,
            "perfume_id": g["perfume"]["id"] if g["perfume"] else None,
            "en_catalogo": bool(g["perfume"]),
            "nombre": nombre_vis,
            "videos": len(vids),
            "canales": len(g["canales"]),
            "visitas": visitas,
            "likes": likes,
            "velocidad": velocidad,
            "top_titulo": top["titulo"],
            "top_canal": top["canal"],
            "top_url": f"https://www.youtube.com/watch?v={top['id']}",
            "miniatura": top["miniatura"],
            "bruto": bruto,
        })

    # Ejecutamos instrucción: filas.sort(key=lambda f: f['bruto'], reverse=True)
    filas.sort(key=lambda f: f["bruto"], reverse=True)
    # Asignamos 'filas' con filas[:limite]
    filas = filas[:limite]
    # Evaluamos la condición lógica (filas) para controlar el flujo
    if filas:
        # Asignamos '(mx, mn)' con (filas[0]['bruto'], filas[-1]['bruto'])
        mx, mn = filas[0]["bruto"], filas[-1]["bruto"]
        # Asignamos 'rango' con mx - mn or 1
        rango = (mx - mn) or 1
        # Recorremos iterativamente cada 'f' en filas
        for f in filas:
            # Asignamos 'f['score']' con int(round(60 + 39 * (f['bruto'] - mn) / ra...
            f["score"] = int(round(60 + 39 * (f["bruto"] - mn) / rango))
    # Retornamos el resultado procesado (filas)
    return filas


# Definición de función '_texto_insight' (parámetros: f, periodo_txt)
def _texto_insight(f: dict, periodo_txt: str) -> str:
    # Asignamos 'ritmo' con formatear_numero(f['velocidad'])
    ritmo = formatear_numero(f["velocidad"])
    # Asignamos 'canales' con f['canales']
    canales = f["canales"]
    # Asignamos 'texto' con f"{f['videos']} videos de {canales} canal{...
    texto = (
        f"{f['videos']} videos de {canales} canal{'es' if canales != 1 else ''} distinto{'s' if canales != 1 else ''} "
        f"{periodo_txt}, con un ritmo de {ritmo} visitas por día. "
        f"El más visto es de {f['top_canal']}."
    )
    # Retornamos el resultado procesado (texto)
    return texto


# Definición de función '_insights_con_ia' (parámetros: filas, periodo_txt)
def _insights_con_ia(filas: list[dict], periodo_txt: str) -> dict[str, str]:
    """Opcional: frases cortas de la IA explicando por qué cada perfume está en tendencia."""
    # Asignamos 'api_key' con _secret('anthropic', 'api_key', 'ANTHROPIC...
    api_key = _secret("anthropic", "api_key", "ANTHROPIC_API_KEY")
    # Evaluamos la condición lógica (not api_key or not filas) para controlar el flujo
    if not api_key or not filas:
        # Retornamos el resultado procesado ({})
        return {}
    # Asignamos 'datos' con [{'id': f['clave'], 'perfume': f['nombre']...
    datos = [
        {"id": f["clave"], "perfume": f["nombre"], "videos": f["videos"], "visitas": f["visitas"],
         "titulo_mas_visto": f["top_titulo"]}
        for f in filas
    ]
    # Asignamos 'prompt' con f'Eres analista de tendencias de perfumerí...
    prompt = (
        "Eres analista de tendencias de perfumería en Latinoamérica. Para cada perfume, escribe UNA frase "
        f"breve en español (máximo 18 palabras) que explique por qué está en tendencia en YouTube {periodo_txt}, "
        "usando solo los datos entregados (sin inventar cifras). Responde SOLO con JSON: "
        '{"<id>": "frase", ...}\n\n' + json.dumps(datos, ensure_ascii=False)
    )
    # Procesamiento de serialización o deserialización de estructura JSON
    body = json.dumps({"model": ANTHROPIC_MODEL, "max_tokens": 1500,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    # Asignamos 'req' con urllib.request.Request(ANTHROPIC_URL, data...
    req = urllib.request.Request(ANTHROPIC_URL, data=body, method="POST", headers={
        "content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01",
    })
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Gestión automática de contexto y recursos para: urllib.request.urlopen(req, timeout=45)
        with urllib.request.urlopen(req, timeout=45) as resp:
            # Procesamiento de serialización o deserialización de estructura JSON
            data = json.loads(resp.read().decode("utf-8"))
        # Asignamos 'texto' con ''.join((b.get('text', '') for b in data.g...
        texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        # Asignamos 'texto' con texto.strip().removeprefix('```json').remo...
        texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        # Retornamos el resultado procesado ({str(k): str(v)[:220] for k, v in json.loads(te...)
        return {str(k): str(v)[:220] for k, v in json.loads(texto).items() if v}
    except Exception:
        # Retornamos el resultado procesado ({})
        return {}


# -----------------------------------------------------------------------------
# 4) Caché compartida por período (ahorra cuota de YouTube)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _almacen_cache():
    # Retornamos el resultado procesado ({'datos': {}, 'lock': threading.Lock()})
    return {"datos": {}, "lock": threading.Lock()}


# Definición de función 'obtener_ranking_hype' (parámetros: periodo, catalogo, limite)
def obtener_ranking_hype(periodo: str, catalogo: list[dict], limite: int = 12) -> dict:
    """
    Devuelve {"ok": bool, "items": [...], "mensaje": str, "actualizado": datetime|None, "videos_analizados": int}.
    Si YouTube no está configurado o falla, ok=False y la página muestra los datos de ejemplo.
    """
    # Asignamos 'api_key' con _secret('youtube', 'api_key', 'YOUTUBE_API...
    api_key = _secret("youtube", "api_key", "YOUTUBE_API_KEY")
    # Evaluamos la condición lógica (not api_key) para controlar el flujo
    if not api_key:
        # Retornamos el resultado procesado ({'ok': False, 'items': [], 'actualizado': None,...)
        return {"ok": False, "items": [], "actualizado": None, "videos_analizados": 0,
                "mensaje": "Modo demostración: agrega tu clave de YouTube en Secrets ([youtube] api_key) para ver tendencias reales."}

    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    cfg = PERIODOS.get(periodo, PERIODOS["Este Mes"])
    # Asignamos 'almacen' con _almacen_cache()
    almacen = _almacen_cache()
    # Asignamos 'guardado' con almacen['datos'].get(periodo)
    guardado = almacen["datos"].get(periodo)
    # Evaluamos la condición lógica (guardado and time.time() - guardado['ts'] < cfg['ttl']) para controlar el flujo
    if guardado and time.time() - guardado["ts"] < cfg["ttl"]:
        # Retornamos el resultado procesado (guardado['resultado'])
        return guardado["resultado"]

    # Gestión automática de contexto y recursos para: almacen['lock']
    with almacen["lock"]:
        # Asignamos 'guardado' con almacen['datos'].get(periodo)
        guardado = almacen["datos"].get(periodo)
        # Evaluamos la condición lógica (guardado and time.time() - guardado['ts'] < cfg['ttl']) para controlar el flujo
        if guardado and time.time() - guardado["ts"] < cfg["ttl"]:
            # Retornamos el resultado procesado (guardado['resultado'])
            return guardado["resultado"]
        # Asignamos '(desde, hasta)' con _rango_periodo(periodo)
        desde, hasta = _rango_periodo(periodo)
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'videos' con _buscar_videos(api_key, desde, hasta)
            videos = _buscar_videos(api_key, desde, hasta)
            # Asignamos 'filas' con _calcular_ranking(videos, catalogo, period...
            filas = _calcular_ranking(videos, catalogo, periodo, limite)
            # Asignamos 'frases' con _insights_con_ia(filas, cfg['texto'])
            frases = _insights_con_ia(filas, cfg["texto"])
            # Recorremos iterativamente cada 'f' en filas
            for f in filas:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                f["insight"] = frases.get(f["clave"]) or _texto_insight(f, cfg["texto"])
            # Asignamos 'resultado' con {'ok': bool(filas), 'items': filas, 'actua...
            resultado = {
                "ok": bool(filas),
                "items": filas,
                "actualizado": datetime.now(timezone.utc),
                "videos_analizados": len(videos),
                "mensaje": "" if filas else "YouTube no tiene suficientes videos de perfumes en este período todavía.",
            }
            # Asignamos 'almacen['datos'][periodo]' con {'ts': time.time(), 'resultado': resultado}
            almacen["datos"][periodo] = {"ts": time.time(), "resultado": resultado}
            # Retornamos el resultado procesado (resultado)
            return resultado
        except RuntimeError as exc:
            # Evaluamos la condición lógica (guardado) para controlar el flujo
            if guardado:  # se muestra lo último que funcionó
                # Asignamos 'viejo' con dict(guardado['resultado'])
                viejo = dict(guardado["resultado"])
                # Asignamos 'viejo['mensaje']' con f'{exc} Mostrando la última actualización ...
                viejo["mensaje"] = f"{exc} Mostrando la última actualización disponible."
                # Retornamos el resultado procesado (viejo)
                return viejo
            # Retornamos el resultado procesado ({'ok': False, 'items': [], 'actualizado': None,...)
            return {"ok": False, "items": [], "actualizado": None, "videos_analizados": 0, "mensaje": str(exc)}
