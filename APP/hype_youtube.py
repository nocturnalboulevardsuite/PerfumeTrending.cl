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

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import streamlit as st

YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
YT_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
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
CONECTORES_INTERNOS = {"de", "du", "di", "la", "le", "in", "of", "the", "al", "el"}
SEPARADORES = re.compile(r"[|\-–—:()\[\]!¡¿?,.#\"“”/•*]+")


# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
def _secret(seccion: str, clave: str, env: str) -> str:
    try:
        if seccion in st.secrets and st.secrets[seccion].get(clave):
            return str(st.secrets[seccion][clave])
    except Exception:
        pass
    return os.environ.get(env, "")


def youtube_configurado() -> bool:
    return bool(_secret("youtube", "api_key", "YOUTUBE_API_KEY"))


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().replace("&", " & ")
    texto = re.sub(r"[^a-z0-9& ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _get_json(url: str, params: dict, timeout: int = 20) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _rango_periodo(periodo: str) -> tuple[datetime, datetime]:
    ahora = datetime.now(timezone.utc)
    if periodo == "Hoy / Día":
        return ahora - timedelta(days=1), ahora
    if periodo == "Esta Semana":
        return ahora - timedelta(days=7), ahora
    if periodo == "Este Mes":
        return ahora - timedelta(days=30), ahora
    if periodo == "Este Año":
        return datetime(ahora.year, 1, 1, tzinfo=timezone.utc), ahora
    if periodo == "Año Pasado":
        return (datetime(ahora.year - 1, 1, 1, tzinfo=timezone.utc),
                datetime(ahora.year, 1, 1, tzinfo=timezone.utc))
    return ahora - timedelta(days=30), ahora


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def formatear_numero(n: float) -> str:
    n = float(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return f"{int(n)}"


# -----------------------------------------------------------------------------
# 1) Descarga de videos y estadísticas desde YouTube
# -----------------------------------------------------------------------------
def _buscar_videos(api_key: str, desde: datetime, hasta: datetime) -> dict:
    videos = {}
    errores = []
    for consulta, region in BUSQUEDAS:
        try:
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
            cuerpo = ""
            try:
                cuerpo = exc.read().decode("utf-8")
            except Exception:
                pass
            if exc.code == 403 and "quota" in cuerpo.lower():
                raise RuntimeError("Se agotó la cuota diaria de YouTube. Se renueva cada día.") from exc
            if exc.code in (400, 403):
                raise RuntimeError("YouTube rechazó la clave de API. Revisa [youtube] api_key en Secrets.") from exc
            errores.append(str(exc))
            continue
        except Exception as exc:
            errores.append(str(exc))
            continue

        for item in data.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            sn = item.get("snippet") or {}
            if not vid or vid in videos:
                continue
            thumbs = sn.get("thumbnails") or {}
            thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
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
    if not videos and errores:
        raise RuntimeError("No se pudo conectar con YouTube en este momento.")

    # Estadísticas reales (1 unidad de cuota por cada 50 videos)
    ids = list(videos.keys())
    for i in range(0, len(ids), 50):
        lote = ids[i:i + 50]
        try:
            data = _get_json(YT_VIDEOS, {"part": "statistics", "id": ",".join(lote), "key": api_key})
        except Exception:
            continue
        for item in data.get("items", []):
            stats = item.get("statistics") or {}
            v = videos.get(item.get("id"))
            if v:
                v["visitas"] = int(stats.get("viewCount", 0) or 0)
                v["likes"] = int(stats.get("likeCount", 0) or 0)
                v["comentarios"] = int(stats.get("commentCount", 0) or 0)
    return videos


# -----------------------------------------------------------------------------
# 2) Reconocimiento del perfume en cada video
# -----------------------------------------------------------------------------
def _indice_catalogo(catalogo: list[dict]) -> list[tuple[str, str, dict]]:
    """Lista de (nombre_normalizado, marca_normalizada, perfume) ordenada de más a menos específica."""
    indice = []
    for p in catalogo or []:
        nombre = _norm(p.get("nombre", ""))
        marca = _norm(p.get("marca", ""))
        if not nombre:
            continue
        # Quita concentraciones del final para reconocer "Sauvage" en "Dior Sauvage EDT"
        nucleo = re.sub(r"\b(eau de parfum|eau de toilette|edp|edt|parfum|extrait|cologne)\b", " ", nombre)
        nucleo = re.sub(r"\s+", " ", nucleo).strip() or nombre
        if marca and nucleo.startswith(marca + " "):
            nucleo = nucleo[len(marca) + 1:]
        if len(nucleo) < 3:
            continue
        indice.append((nucleo, marca, p))
    indice.sort(key=lambda t: len(t[0]), reverse=True)
    return indice


def _palabras_con_mayuscula(original: str) -> set[str] | None:
    """Palabras escritas con mayúscula inicial en el título. None si el título está todo en MAYÚSCULAS."""
    letras = [c for c in original if c.isalpha()]
    if not letras or sum(c.isupper() for c in letras) / len(letras) > 0.6:
        return None
    return {_norm(w) for w in re.findall(r"[\w']+", original) if w[:1].isupper() or w[:1].isdigit()}


def _tokens_siguientes(texto_norm: str, frase: str, maximo: int = 2, original: str = "") -> list[str]:
    """Palabras que siguen a `frase` y forman parte del nombre (p. ej. 'Khamrah Qahwa', 'Sauvage Elixir').

    Solo cuentan las que vienen escritas con mayúscula en el título original, para no confundir
    "Erba Pura vuelve a estar de moda" con un perfume llamado "Erba Pura Vuelve".
    """
    mayus = _palabras_con_mayuscula(original) if original else None
    if not mayus:
        return []
    t = f" {texto_norm} "
    pos = t.find(f" {frase} ")
    if pos < 0:
        return []
    siguientes = []
    for tok in t[pos + len(frase) + 2:].split():
        if tok in PALABRAS_CORTE or tok in MARCAS or tok in CONECTORES_INTERNOS or tok not in mayus:
            break
        siguientes.append(tok)
        if len(siguientes) >= maximo:
            break
    return siguientes


def _formatear_nombre(tokens: list[str]) -> str:
    nombre = " ".join(t.upper() if len(t) <= 3 and any(c.isdigit() for c in t) else t.capitalize() for t in tokens)
    nombre = re.sub(r"\b(De|Du|Di|La|Le|In|Of|The|Al|El)\b", lambda m: m.group(0).lower(), nombre)
    return nombre[:1].upper() + nombre[1:]


def _buscar_en_catalogo(texto_norm: str, indice, original: str = "") -> dict | None:
    for nucleo, marca, p in indice:
        if f" {nucleo} " in f" {texto_norm} ":
            # Si al nombre le sigue otra palabra del nombre (p. ej. "Khamrah Qahwa", "Sauvage Elixir"),
            # es una versión distinta del perfume del catálogo: no se mezcla.
            if original and _tokens_siguientes(texto_norm, nucleo, 1, original):
                continue
            # Nombres cortos o genéricos exigen que también aparezca la marca
            if len(nucleo) < 6 or len(nucleo.split()) == 1 and len(nucleo) < 8:
                if marca and f" {marca} " not in f" {texto_norm} ":
                    continue
            return p
    return None


def _extraer_por_marca(titulo: str) -> tuple[str, str] | None:
    """Encuentra el perfume de un título y devuelve (marca, nombre)."""
    tn = _norm(titulo)

    # 1) "<Marca> <Nombre>": Lattafa Khamrah Qahwa, Afnan 9pm Rebel, Riiffs Freeze in Flames...
    #    Se lee cada tramo del título por separado (los signos | - : ¿ ? cortan el nombre).
    mayus = _palabras_con_mayuscula(titulo)
    tramos = [_norm(t) for t in SEPARADORES.split(titulo) if _norm(t)]
    for marca_norm in sorted(MARCAS, key=len, reverse=True):
        tramo = next((tr for tr in tramos if f" {marca_norm} " in f" {tr} "), None)
        if tramo is None:
            continue
        pos = f" {tramo} ".find(f" {marca_norm} ")
        resto_norm = tramo[pos + len(marca_norm):].strip()
        tokens = []
        for tok in resto_norm.split():
            if tok in PALABRAS_CORTE or tok in MARCAS:
                break
            # En títulos normales el nombre va con mayúscula ("Khamrah de Lattafa sigue siendo...")
            if mayus is not None and tok not in mayus and tok not in CONECTORES_INTERNOS:
                break
            tokens.append(tok)
            if len(tokens) >= 4:
                break
        while tokens and tokens[-1] in CONECTORES_INTERNOS:
            tokens.pop()
        if not tokens or (len(tokens) == 1 and len(tokens[0]) < 3 and not tokens[0].isdigit()):
            continue
        return MARCAS[marca_norm], _formatear_nombre(tokens)

    # 2) Perfumes famosos nombrados sin la marca ("Erba Pura", "Khamrah Qahwa de Lattafa"...)
    for alias in sorted(ALIAS_SIN_MARCA, key=len, reverse=True):
        if f" {alias} " in f" {tn} ":
            marca, nombre = ALIAS_SIN_MARCA[alias]
            extra = _tokens_siguientes(tn, alias, 2, titulo)
            if extra:
                nombre = f"{nombre} {_formatear_nombre(extra)}"
            return marca, nombre
    return None


def _extraer_con_ia(titulos: list[str]) -> dict[int, tuple[str, str]]:
    """Opcional: una IA identifica el perfume principal de cada título difícil."""
    api_key = _secret("anthropic", "api_key", "ANTHROPIC_API_KEY")
    if not api_key or not titulos:
        return {}
    lista = "\n".join(f"{i}. {t}" for i, t in enumerate(titulos))
    prompt = (
        "Eres experto en perfumería. Para cada título de video de YouTube, identifica el perfume "
        "principal del que habla (marca y nombre comercial exacto). Si el título no trata de un perfume "
        "específico (por ejemplo, 'top 10 perfumes'), responde null.\n"
        "Responde SOLO con JSON, sin texto adicional, con este formato: "
        '{"0": {"marca": "Lattafa", "perfume": "Khamrah"}, "1": null}\n\n'
        f"Títulos:\n{lista}"
    )
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        crudo = json.loads(texto)
    except Exception:
        return {}
    salida = {}
    for k, v in (crudo or {}).items():
        try:
            if v and v.get("marca") and v.get("perfume"):
                salida[int(k)] = (str(v["marca"]).strip()[:40], str(v["perfume"]).strip()[:60])
        except Exception:
            continue
    return salida


# -----------------------------------------------------------------------------
# 3) Hype Score y ranking
# -----------------------------------------------------------------------------
def _calcular_ranking(videos: dict, catalogo: list[dict], periodo: str, limite: int) -> list[dict]:
    indice = _indice_catalogo(catalogo)
    ahora = datetime.now(timezone.utc)
    grupos: dict[str, dict] = {}
    sin_identificar = []

    def agregar(clave, video, perfume_cat=None, marca="", nombre=""):
        g = grupos.get(clave)
        if g is None:
            g = grupos[clave] = {
                "perfume": perfume_cat, "marca": marca, "nombre": nombre,
                "videos": [], "canales": set(),
            }
        g["videos"].append(video)
        g["canales"].add(video["canal_id"] or video["canal"])

    for v in videos.values():
        texto = _norm(f"{v['titulo']} {v['descripcion'][:160]}")
        p = _buscar_en_catalogo(texto, indice, v["titulo"])
        if p:
            agregar(f"cat:{p['id']}", v, perfume_cat=p)
            continue
        hallado = _extraer_por_marca(v["titulo"])
        if hallado:
            marca, nombre = hallado
            # ¿El perfume descubierto en realidad está en el catálogo?
            p2 = _buscar_en_catalogo(_norm(f"{marca} {nombre}"), indice, f"{marca} {nombre}")
            if p2:
                agregar(f"cat:{p2['id']}", v, perfume_cat=p2)
            else:
                agregar(f"new:{_norm(marca + ' ' + nombre)}", v, marca=marca, nombre=nombre)
        else:
            sin_identificar.append(v)

    # IA opcional para los títulos que no se reconocieron (los más vistos primero)
    if sin_identificar:
        sin_identificar.sort(key=lambda x: x["visitas"], reverse=True)
        candidatos = sin_identificar[:120]
        respuesta = _extraer_con_ia([c["titulo"] for c in candidatos])
        for i, (marca, nombre) in respuesta.items():
            if 0 <= i < len(candidatos):
                v = candidatos[i]
                p3 = _buscar_en_catalogo(_norm(f"{marca} {nombre}"), indice, f"{marca} {nombre}")
                if p3:
                    agregar(f"cat:{p3['id']}", v, perfume_cat=p3)
                else:
                    agregar(f"new:{_norm(marca + ' ' + nombre)}", v, marca=marca, nombre=nombre)

    minimo_videos = 1 if periodo == "Hoy / Día" else 2
    filas = []
    for clave, g in grupos.items():
        vids = g["videos"]
        if len(vids) < minimo_videos:
            continue
        visitas = sum(v["visitas"] for v in vids)
        likes = sum(v["likes"] for v in vids)
        comentarios = sum(v["comentarios"] for v in vids)
        velocidad = 0.0
        for v in vids:
            try:
                pub = datetime.strptime(v["publicado"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                dias = max((ahora - pub).total_seconds() / 86400, 0.5)
            except Exception:
                dias = 7
            velocidad += v["visitas"] / dias
        top = max(vids, key=lambda x: x["visitas"])
        # Puntaje bruto: alcance + cantidad de videos + canales distintos + velocidad + interacción
        bruto = (
            0.40 * math.log10(visitas + 1)
            + 0.20 * math.log2(len(vids) + 1)
            + 0.15 * math.log2(len(g["canales"]) + 1)
            + 0.20 * math.log10(velocidad + 1)
            + 0.05 * math.log10(likes + comentarios + 1)
        )
        if g["perfume"]:
            p = g["perfume"]
            nombre_vis = f"{p.get('marca', '')} {p.get('nombre', '')}".strip()
        else:
            nombre_vis = f"{g['marca']} {g['nombre']}".strip()
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

    filas.sort(key=lambda f: f["bruto"], reverse=True)
    filas = filas[:limite]
    if filas:
        mx, mn = filas[0]["bruto"], filas[-1]["bruto"]
        rango = (mx - mn) or 1
        for f in filas:
            f["score"] = int(round(60 + 39 * (f["bruto"] - mn) / rango))
    return filas


def _texto_insight(f: dict, periodo_txt: str) -> str:
    ritmo = formatear_numero(f["velocidad"])
    canales = f["canales"]
    texto = (
        f"{f['videos']} videos de {canales} canal{'es' if canales != 1 else ''} distinto{'s' if canales != 1 else ''} "
        f"{periodo_txt}, con un ritmo de {ritmo} visitas por día. "
        f"El más visto es de {f['top_canal']}."
    )
    return texto


def _insights_con_ia(filas: list[dict], periodo_txt: str) -> dict[str, str]:
    """Opcional: frases cortas de la IA explicando por qué cada perfume está en tendencia."""
    api_key = _secret("anthropic", "api_key", "ANTHROPIC_API_KEY")
    if not api_key or not filas:
        return {}
    datos = [
        {"id": f["clave"], "perfume": f["nombre"], "videos": f["videos"], "visitas": f["visitas"],
         "titulo_mas_visto": f["top_titulo"]}
        for f in filas
    ]
    prompt = (
        "Eres analista de tendencias de perfumería en Latinoamérica. Para cada perfume, escribe UNA frase "
        f"breve en español (máximo 18 palabras) que explique por qué está en tendencia en YouTube {periodo_txt}, "
        "usando solo los datos entregados (sin inventar cifras). Responde SOLO con JSON: "
        '{"<id>": "frase", ...}\n\n' + json.dumps(datos, ensure_ascii=False)
    )
    body = json.dumps({"model": ANTHROPIC_MODEL, "max_tokens": 1500,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_URL, data=body, method="POST", headers={
        "content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return {str(k): str(v)[:220] for k, v in json.loads(texto).items() if v}
    except Exception:
        return {}


# -----------------------------------------------------------------------------
# 4) Caché compartida por período (ahorra cuota de YouTube)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _almacen_cache():
    return {"datos": {}, "lock": threading.Lock()}


def obtener_ranking_hype(periodo: str, catalogo: list[dict], limite: int = 12) -> dict:
    """
    Devuelve {"ok": bool, "items": [...], "mensaje": str, "actualizado": datetime|None, "videos_analizados": int}.
    Si YouTube no está configurado o falla, ok=False y la página muestra los datos de ejemplo.
    """
    api_key = _secret("youtube", "api_key", "YOUTUBE_API_KEY")
    if not api_key:
        return {"ok": False, "items": [], "actualizado": None, "videos_analizados": 0,
                "mensaje": "Modo demostración: agrega tu clave de YouTube en Secrets ([youtube] api_key) para ver tendencias reales."}

    cfg = PERIODOS.get(periodo, PERIODOS["Este Mes"])
    almacen = _almacen_cache()
    guardado = almacen["datos"].get(periodo)
    if guardado and time.time() - guardado["ts"] < cfg["ttl"]:
        return guardado["resultado"]

    with almacen["lock"]:
        guardado = almacen["datos"].get(periodo)
        if guardado and time.time() - guardado["ts"] < cfg["ttl"]:
            return guardado["resultado"]
        desde, hasta = _rango_periodo(periodo)
        try:
            videos = _buscar_videos(api_key, desde, hasta)
            filas = _calcular_ranking(videos, catalogo, periodo, limite)
            frases = _insights_con_ia(filas, cfg["texto"])
            for f in filas:
                f["insight"] = frases.get(f["clave"]) or _texto_insight(f, cfg["texto"])
            resultado = {
                "ok": bool(filas),
                "items": filas,
                "actualizado": datetime.now(timezone.utc),
                "videos_analizados": len(videos),
                "mensaje": "" if filas else "YouTube no tiene suficientes videos de perfumes en este período todavía.",
            }
            almacen["datos"][periodo] = {"ts": time.time(), "resultado": resultado}
            return resultado
        except RuntimeError as exc:
            if guardado:  # se muestra lo último que funcionó
                viejo = dict(guardado["resultado"])
                viejo["mensaje"] = f"{exc} Mostrando la última actualización disponible."
                return viejo
            return {"ok": False, "items": [], "actualizado": None, "videos_analizados": 0, "mensaje": str(exc)}
