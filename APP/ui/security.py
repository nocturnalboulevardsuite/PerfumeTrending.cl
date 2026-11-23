"""
PerfumeTrending.cl — Capa de Seguridad de Interfaz (UI Security & URL Sanitizers)
=================================================================================
Centraliza las defensas contra vulnerabilidades web en el portal Streamlit:
- Prevención estricta de Local File Inclusion / Path Traversal (LFI) en imágenes.
- Sanitización HTML contra Cross-Site Scripting (XSS) almacenado y reflejado.
- Validación de esquemas URL (`http://` / `https://`) en enlaces de salida a tiendas.
- Resolución canónica de enlaces de oferta para las 9 tiendas monitoreadas.
"""

# Importación de librería estándar o dependencia externa (base64)
import base64
# Importación de librería estándar o dependencia externa (functools)
import functools
# Importación de librería estándar o dependencia externa (html)
import html
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de componentes (Any, Dict, Optional) desde el módulo 'typing'
from typing import Any, Dict, Optional

# Asignamos 'APP_DIR' con Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent.parent
# Asignamos 'ALLOWED_ASSETS_DIR' con (APP_DIR / 'assets').resolve()
ALLOWED_ASSETS_DIR = (APP_DIR / "assets").resolve()
# Asignamos 'ALLOWED_IMAGE_EXTENSIONS' con {'.jpg', '.jpeg', '.png', '.webp', '.gif',...
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

# Asignamos 'DEFAULT_PERFUME_IMAGE' con "data:image/svg+xml;utf8,<svg xmlns='http:...
DEFAULT_PERFUME_IMAGE = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200' fill='none'>"
    "<rect width='200' height='200' rx='16' fill='%2314171f'/>"
    "<rect x='80' y='28' width='40' height='24' rx='4' fill='%232a303f' stroke='%23d4af37' stroke-width='2'/>"
    "<rect x='88' y='20' width='24' height='10' rx='2' fill='%23d4af37'/>"
    "<rect x='48' y='52' width='104' height='120' rx='12' fill='%231c212d' stroke='%23d4af37' stroke-width='2'/>"
    "<rect x='64' y='82' width='72' height='60' rx='6' fill='%23232938' stroke='rgba(212,175,55,0.4)' stroke-width='1'/>"
    "<line x1='76' y1='102' x2='124' y2='102' stroke='%23d4af37' stroke-width='1.5' stroke-linecap='round'/>"
    "<line x1='86' y1='114' x2='114' y2='114' stroke='rgba(255,255,255,0.3)' stroke-width='1' stroke-linecap='round'/>"
    "<circle cx='100' cy='130' r='3' fill='%23d4af37'/>"
    "</svg>"
)
# Asignamos 'DEFAULT_AVATAR_SVG' con "data:image/svg+xml;utf8,<svg xmlns='http:...
DEFAULT_AVATAR_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 80' fill='none'>"
    "<rect width='80' height='80' rx='40' fill='%23232834'/>"
    "<circle cx='40' cy='31' r='13' stroke='%23d4c2a5' stroke-width='3'/>"
    "<path d='M18 67c3.5-11.5 12.5-18 22-18s18.5 6.5 22 18' stroke='%23d4c2a5' stroke-width='3' stroke-linecap='round'/>"
    "</svg>"
)

# Asignamos 'SAFE_DATA_IMAGE_PREFIXES' con ('data:image/png;base64,', 'data:image/jpe...
SAFE_DATA_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
    "data:image/svg+xml;utf8,",
)


# Definición de función '_read_local_asset_data_uri' (parámetros: resolved_str)
@functools.lru_cache(maxsize=512)
def _read_local_asset_data_uri(resolved_str: str) -> Optional[str]:
    """Codifica y cachea en RAM imágenes locales dentro de APP/assets/ para evitar lecturas de disco repetidas."""
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'resolved' con Path(resolved_str)
        resolved = Path(resolved_str)
        # Asignamos 'ext' con resolved.suffix.lower()
        ext = resolved.suffix.lower()
        # Asignamos 'mime_map' con {'.png': 'image/png', '.webp': 'image/webp...
        mime_map = {
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        # Asignamos 'mime' con mime_map.get(ext, 'image/jpeg')
        mime = mime_map.get(ext, "image/jpeg")
        # Asignamos 'b64' con base64.b64encode(resolved.read_bytes()).de...
        b64 = base64.b64encode(resolved.read_bytes()).decode("ascii")
        # Retornamos el resultado procesado (f'data:{mime};base64,{b64}')
        return f"data:{mime};base64,{b64}"
    except Exception:
        # Retornamos el resultado procesado (None)
        return None


# Definición de función 'formatear_nombre_especifico' (parámetros: perfume)
def formatear_nombre_especifico(perfume: Optional[Dict[str, Any]]) -> str:
    """
    Construye un título comercial específico e inequívoco para cada fragancia
    (ej. 'Romance Mujer EDP', 'Eros Pour Femme EDP', 'Eros Hombre EDT') para que
    ninguna ficha se muestre como una palabra suelta ambigua.
    """
    # Evaluamos la condición lógica (not perfume or not isinstance(perfume, dict)) para controlar el flujo
    if not perfume or not isinstance(perfume, dict):
        # Retornamos el resultado procesado ('')
        return ""
    # Asignamos 'raw_name' con str(perfume.get('nombre') or '').strip()
    raw_name = str(perfume.get("nombre") or "").strip()
    # Evaluamos la condición lógica (not raw_name) para controlar el flujo
    if not raw_name:
        # Retornamos el resultado procesado ('')
        return ""

    # Eliminar palabras consecutivas repetidas (ej. 'Absolute Absolute')
    words = raw_name.split()
    # Asignamos 'dedup_words' con []
    dedup_words = []
    # Recorremos iterativamente cada 'w' en words
    for w in words:
        # Evaluamos la condición lógica (dedup_words and dedup_words[-1].lower() == w.lower()) para controlar el flujo
        if dedup_words and dedup_words[-1].lower() == w.lower():
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Ejecutamos instrucción: dedup_words.append(w)
        dedup_words.append(w)
    # Asignamos 'nombre' con ' '.join(dedup_words)
    nombre = " ".join(dedup_words)
    # Asignamos 'nom_low' con nombre.lower()
    nom_low = nombre.lower()

    # Asignamos 'genero' con str(perfume.get('genero') or '').strip()
    genero = str(perfume.get("genero") or "").strip()
    # Asignamos 'tipo' con str(perfume.get('tipo') or '').strip()
    tipo = str(perfume.get("tipo") or "").strip()
    # Asignamos 'tipo_low' con tipo.lower()
    tipo_low = tipo.lower()

    # Verificar si el nombre ya declara explícitamente género
    tiene_genero_en_nombre = bool(
        re.search(
            r"\b(?:pour femme|pour homme|l'homme|la femme|femme|homme|for her|for him|for women|for men|"
            r"woman|women|man|men|mujer|hombre|uomo|donna|girl|boy|lady|mademoiselle|her|elle)\b",
            nom_low,
        )
    )

    # Asignamos 'sufijos' con []
    sufijos = []
    # Evaluamos la condición lógica (not tiene_genero_en_nombre and genero in ('Mujer', '...) para controlar el flujo
    if not tiene_genero_en_nombre and genero in ("Mujer", "Hombre"):
        # Agregar género explícito en nombres cortos/ambiguos (<= 2 palabras) o líneas compartidas Hom/Muj
        lineas_compartidas = {
            "eros", "romance", "light blue", "the one", "one", "obsession", "eternity",
            "euphoria", "acqua di gio", "acqua di giò", "code", "scandal", "guilty",
            "le male", "classique", "9 pm", "9pm", "fakhar", "qimmah", "the kingdom",
            "yara", "asad", "cool water", "boss orange", "212", "212 vip", "ch",
            "individuel", "presence", "legend", "emblem", "starwalker",
        }
        # Evaluamos la condición lógica (len(dedup_words) <= 2 or nom_low in lineas_compartidas) para controlar el flujo
        if len(dedup_words) <= 2 or nom_low in lineas_compartidas:
            # Ejecutamos instrucción: sufijos.append(genero)
            sufijos.append(genero)

    # Abreviatura de concentración si no está ya en el nombre
    abrev_conc = ""
    # Evaluamos la condición lógica ('elixir' in tipo_low and 'elixir' not in nom_low) para controlar el flujo
    if "elixir" in tipo_low and "elixir" not in nom_low:
        # Asignamos 'abrev_conc' con 'Elixir'
        abrev_conc = "Elixir"
    # Evaluamos la condición lógica ('extrait' in tipo_low and 'extrait' not in nom_low) para controlar el flujo
    elif "extrait" in tipo_low and "extrait" not in nom_low:
        # Asignamos 'abrev_conc' con 'Extrait'
        abrev_conc = "Extrait"
    # Evaluamos la condición lógica ('eau de parfum intense' in tipo_low) para controlar el flujo
    elif "eau de parfum intense" in tipo_low:
        # Asignamos 'abrev_conc' con 'EDP Intense' if 'intense' not in nom_low ...
        abrev_conc = "EDP Intense" if "intense" not in nom_low else "EDP"
    # Evaluamos la condición lógica ('eau de toilette intense' in tipo_low) para controlar el flujo
    elif "eau de toilette intense" in tipo_low:
        # Asignamos 'abrev_conc' con 'EDT Intense' if 'intense' not in nom_low ...
        abrev_conc = "EDT Intense" if "intense" not in nom_low else "EDT"
    # Evaluamos la condición lógica ('eau de parfum' in tipo_low or tipo_low == 'edp') para controlar el flujo
    elif "eau de parfum" in tipo_low or tipo_low == "edp":
        # Evaluamos la condición lógica (not re.search('\\b(?:edp|eau de parfum)\\b', nom_low)) para controlar el flujo
        if not re.search(r"\b(?:edp|eau de parfum)\b", nom_low):
            # Asignamos 'abrev_conc' con 'EDP'
            abrev_conc = "EDP"
    # Evaluamos la condición lógica ('eau de toilette' in tipo_low or tipo_low == 'edt') para controlar el flujo
    elif "eau de toilette" in tipo_low or tipo_low == "edt":
        # Evaluamos la condición lógica (not re.search('\\b(?:edt|eau de toilette)\\b', nom_low)) para controlar el flujo
        if not re.search(r"\b(?:edt|eau de toilette)\b", nom_low):
            # Asignamos 'abrev_conc' con 'EDT'
            abrev_conc = "EDT"
    # Evaluamos la condición lógica ('eau de cologne' in tipo_low or tipo_low == 'edc') para controlar el flujo
    elif "eau de cologne" in tipo_low or tipo_low == "edc":
        # Evaluamos la condición lógica (not re.search('\\b(?:edc|cologne|colonia)\\b', nom_low)) para controlar el flujo
        if not re.search(r"\b(?:edc|cologne|colonia)\b", nom_low):
            # Asignamos 'abrev_conc' con 'EDC'
            abrev_conc = "EDC"
    # Evaluamos la condición lógica (tipo_low == 'parfum' and 'parfum' not in nom_low) para controlar el flujo
    elif tipo_low == "parfum" and "parfum" not in nom_low:
        # Asignamos 'abrev_conc' con 'Parfum'
        abrev_conc = "Parfum"

    # Evaluamos la condición lógica (abrev_conc) para controlar el flujo
    if abrev_conc:
        # Ejecutamos instrucción: sufijos.append(abrev_conc)
        sufijos.append(abrev_conc)

    # Evaluamos la condición lógica (sufijos) para controlar el flujo
    if sufijos:
        # Retornamos el resultado procesado (f"{nombre} {' '.join(sufijos)}")
        return f"{nombre} {' '.join(sufijos)}"
    # Retornamos el resultado procesado (nombre)
    return nombre


# Definición de función 'escape_html' (parámetros: value)
def escape_html(value: Any) -> str:
    """Escapa caracteres especiales HTML (`<`, `>`, `&`, `\"`, `'`) para prevenir XSS."""
    # Evaluamos la condición lógica (value is None) para controlar el flujo
    if value is None:
        # Retornamos el resultado procesado ('')
        return ""
    # Retornamos el resultado procesado (html.escape(str(value), quote=True))
    return html.escape(str(value), quote=True)


# Definición de función 'clean_html' (parámetros: html_str, join_char)
def clean_html(html_str: str, join_char: str = "\n") -> str:
    """Elimina indentación inicial por línea para evitar bloques de código accidentales en Markdown."""
    # Evaluamos la condición lógica (not html_str) para controlar el flujo
    if not html_str:
        # Retornamos el resultado procesado ('')
        return ""
    # Evaluamos la condición lógica (join_char == ' ') para controlar el flujo
    if join_char == " ":
        # Retornamos el resultado procesado (' '.join((line.strip() for line in html_str.spl...)
        return " ".join(line.strip() for line in html_str.splitlines() if line.strip())
    # Retornamos el resultado procesado (join_char.join((line.strip() for line in html_s...)
    return join_char.join(line.strip() for line in html_str.splitlines())


# Definición de función 'sanitize_external_url' (parámetros: url, fallback)
def sanitize_external_url(url: Optional[str], fallback: str = "#") -> str:
    """
    Valida que un enlace externo utilice exclusivamente `https://` o `http://`
    y escapa comillas/caracteres peligrosos para inserción segura en atributos `href`.
    """
    # Evaluamos la condición lógica (not url or not isinstance(url, str)) para controlar el flujo
    if not url or not isinstance(url, str):
        # Retornamos el resultado procesado (fallback)
        return fallback
    # Asignamos 'cleaned' con url.strip()
    cleaned = url.strip()
    # Evaluamos la condición lógica (not cleaned or cleaned == '#') para controlar el flujo
    if not cleaned or cleaned == "#":
        # Retornamos el resultado procesado (fallback)
        return fallback
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'parsed' con urllib.parse.urlsplit(cleaned)
        parsed = urllib.parse.urlsplit(cleaned)
    except Exception:
        # Retornamos el resultado procesado (fallback)
        return fallback

    # Evaluamos la condición lógica (parsed.scheme.lower() not in ('http', 'https') or no...) para controlar el flujo
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        # Retornamos el resultado procesado (fallback)
        return fallback

    # Bloquear saltos de línea o inyecciones de atributos
    safe_url = cleaned.replace('"', "%22").replace("'", "%27").replace("<", "%3C").replace(">", "%3E")
    # Retornamos el resultado procesado (safe_url)
    return safe_url


# Definición de función 'is_valid_https_image_url' (parámetros: url)
def is_valid_https_image_url(url: Optional[str]) -> bool:
    """Verifica que una URL de avatar ingresada por usuario sea estrictamente HTTPS válida."""
    # Evaluamos la condición lógica (not url or not isinstance(url, str)) para controlar el flujo
    if not url or not isinstance(url, str):
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'cleaned' con url.strip()
    cleaned = url.strip()
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'parsed' con urllib.parse.urlsplit(cleaned)
        parsed = urllib.parse.urlsplit(cleaned)
    except Exception:
        # Retornamos el resultado procesado (False)
        return False
    # Retornamos el resultado procesado (parsed.scheme.lower() == 'https' and bool(parse...)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc) and len(cleaned) <= 1024


# Definición de función 'get_image_src' (parámetros: img_path_or_url)
def get_image_src(
    img_path_or_url: Optional[str],
    *,
    allow_local: bool = True,
    default_src: str = DEFAULT_PERFUME_IMAGE,
) -> str:
    """
    Resuelve de forma segura una imagen remota o un packshot estático local.

    Mitigación de seguridad (Cierre total de LFI / Path Traversal):
    - Si `allow_local=False` (ej. avatares de usuario), rechaza cualquier ruta local y exige HTTPS.
    - Si `allow_local=True`, cualquier ruta en disco debe resolverse canónicamente DENTRO de
      `APP/assets/` y tener extensión de imagen permitida. Jamás puede leer `secrets.toml`,
      bases `.db`, código `.py` ni rutas fuera de `APP/assets/`.
    """
    # Evaluamos la condición lógica (not img_path_or_url or not isinstance(img_path_or_ur...) para controlar el flujo
    if not img_path_or_url or not isinstance(img_path_or_url, str):
        # Retornamos el resultado procesado (default_src)
        return default_src

    # Asignamos 'raw' con img_path_or_url.strip()
    raw = img_path_or_url.strip()
    # Evaluamos la condición lógica (not raw) para controlar el flujo
    if not raw:
        # Retornamos el resultado procesado (default_src)
        return default_src

    # 1. URLs remotas HTTP/HTTPS
    if raw.lower().startswith(("https://", "http://")):
        # Evaluamos la condición lógica (not allow_local and (not raw.lower().startswith('htt...) para controlar el flujo
        if not allow_local and not raw.lower().startswith("https://"):
            # Retornamos el resultado procesado (default_src)
            return default_src
        # Asignamos 'safe_remote' con sanitize_external_url(raw, fallback='')
        safe_remote = sanitize_external_url(raw, fallback="")
        # Retornamos el resultado procesado (safe_remote if safe_remote else default_src)
        return safe_remote if safe_remote else default_src

    # 2. Data URIs de imagen controlados (validación estricta de alfabeto base64 contra ruptura de atributos)
    if raw == DEFAULT_AVATAR_SVG:
        # Retornamos el resultado procesado (raw)
        return raw
    # Recorremos iterativamente cada 'prefix' en ('data:image/png;base64,', 'data:image/jpe...
    for prefix in (
        "data:image/png;base64,",
        "data:image/jpeg;base64,",
        "data:image/webp;base64,",
        "data:image/gif;base64,",
    ):
        # Evaluamos la condición lógica (raw.startswith(prefix)) para controlar el flujo
        if raw.startswith(prefix):
            # Asignamos 'b64_payload' con raw[len(prefix):].strip()
            b64_payload = raw[len(prefix):].strip()
            # Evaluamos la condición lógica (b64_payload and len(b64_payload) <= 600000 and all((...) para controlar el flujo
            if b64_payload and len(b64_payload) <= 600_000 and all(
                c.isalnum() or c in "+/=" for c in b64_payload
            ):
                # Retornamos el resultado procesado (prefix + b64_payload)
                return prefix + b64_payload
            # Retornamos el resultado procesado (default_src)
            return default_src
    # Evaluamos la condición lógica (allow_local and raw.startswith('data:image/svg+xml;u...) para controlar el flujo
    if allow_local and raw.startswith("data:image/svg+xml;utf8,"):
        # Evaluamos la condición lógica (any((bad in raw.lower() for bad in ('<script', 'onlo...) para controlar el flujo
        if any(bad in raw.lower() for bad in ("<script", "onload", "onerror", "javascript:")):
            # Retornamos el resultado procesado (default_src)
            return default_src
        # Retornamos el resultado procesado (raw.replace('"', '%22'))
        return raw.replace('"', "%22")

    # 3. Bloquear acceso local cuando no está explícitamente habilitado (ej. perfil de usuario)
    if not allow_local:
        # Retornamos el resultado procesado (default_src)
        return default_src

    # 4. Resolución confinada exclusivamente a APP/assets/
    candidates = []
    # Asignamos 'rel_clean' con raw.lstrip('/\\')
    rel_clean = raw.lstrip("/\\")
    # Evaluamos la condición lógica (rel_clean.lower().startswith('app/')) para controlar el flujo
    if rel_clean.lower().startswith("app/"):
        # Asignamos 'rel_clean' con rel_clean[4:].lstrip('/\\')
        rel_clean = rel_clean[4:].lstrip("/\\")
    # Evaluamos la condición lógica (rel_clean.lower().startswith('app\\')) para controlar el flujo
    elif rel_clean.lower().startswith("app\\"):
        # Asignamos 'rel_clean' con rel_clean[4:].lstrip('/\\')
        rel_clean = rel_clean[4:].lstrip("/\\")

    # Ejecutamos instrucción: candidates.append(APP_DIR / rel_clean)
    candidates.append(APP_DIR / rel_clean)
    # Ejecutamos instrucción: candidates.append(ALLOWED_ASSETS_DIR / rel_clean)
    candidates.append(ALLOWED_ASSETS_DIR / rel_clean)

    # Recorremos iterativamente cada 'cand' en candidates
    for cand in candidates:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'resolved' con cand.resolve(strict=False)
            resolved = cand.resolve(strict=False)
            # Evaluamos la condición lógica (not resolved.is_relative_to(ALLOWED_ASSETS_DIR)) para controlar el flujo
            if not resolved.is_relative_to(ALLOWED_ASSETS_DIR):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Evaluamos la condición lógica (resolved.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS) para controlar el flujo
            if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Evaluamos la condición lógica (resolved.is_file()) para controlar el flujo
            if resolved.is_file():
                # Asignamos 'uri' con _read_local_asset_data_uri(str(resolved))
                uri = _read_local_asset_data_uri(str(resolved))
                # Evaluamos la condición lógica (uri) para controlar el flujo
                if uri:
                    # Retornamos el resultado procesado (uri)
                    return uri
        except Exception:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

    # Retornamos el resultado procesado (default_src)
    return default_src


# Definición de función 'resolver_url_oferta' (parámetros: tienda_nombre, perfume_nombre, url_prod, url_base, ...)
def resolver_url_oferta(
    tienda_nombre: str,
    perfume_nombre: str,
    url_prod: str = "",
    url_base: str = "",
    marca: str = "",
) -> str:
    """
    Retorna la URL directa sanitizada hacia la ficha del producto en la tienda,
    o construye el enlace de búsqueda oficial de respaldo si la URL no es válida.
    """
    # Asignamos 't' con (tienda_nombre or '').lower().strip()
    t = (tienda_nombre or "").lower().strip()
    # Asignamos 'marca_clean' con (marca or '').strip()
    marca_clean = (marca or "").strip()
    # Asignamos 'nom_clean' con (perfume_nombre or '').strip()
    nom_clean = (perfume_nombre or "").strip()
    # Evaluamos la condición lógica (marca_clean and marca_clean.lower() not in nom_clean...) para controlar el flujo
    if marca_clean and marca_clean.lower() not in nom_clean.lower():
        # Asignamos 'termino_busqueda' con f'{marca_clean} {nom_clean}'.strip()
        termino_busqueda = f"{marca_clean} {nom_clean}".strip()
    else:
        # Asignamos 'termino_busqueda' con nom_clean
        termino_busqueda = nom_clean
    # Asignamos 'q' con urllib.parse.quote(termino_busqueda)
    q = urllib.parse.quote(termino_busqueda)

    # Asignamos 'safe_prod' con sanitize_external_url(url_prod, fallback='')
    safe_prod = sanitize_external_url(url_prod, fallback="")
    # Asignamos 'dead_markers' con ('916524999', 'construccion', 'experiencia...
    dead_markers = ("916524999", "construccion", "experiencia", "/test")

    # Evaluamos la condición lógica (safe_prod and (not any((dead in safe_prod.lower() fo...) para controlar el flujo
    if safe_prod and not any(dead in safe_prod.lower() for dead in dead_markers):
        # Retornamos el resultado procesado (safe_prod)
        return safe_prod

    # Evaluamos la condición lógica ('falabella' in t) para controlar el flujo
    if "falabella" in t:
        # Retornamos el resultado procesado (f'https://www.falabella.com/falabella-cl/search...)
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    # Evaluamos la condición lógica ('paris' in t) para controlar el flujo
    if "paris" in t:
        # Retornamos el resultado procesado (f'https://www.paris.cl/search?q={q}')
        return f"https://www.paris.cl/search?q={q}"
    # Evaluamos la condición lógica ('ripley' in t) para controlar el flujo
    if "ripley" in t:
        # Retornamos el resultado procesado (f'https://simple.ripley.cl/search/{q}')
        return f"https://simple.ripley.cl/search/{q}"
    # Evaluamos la condición lógica ('silk' in t) para controlar el flujo
    if "silk" in t:
        # Retornamos el resultado procesado (f'https://www.silkperfumes.cl/search?q={q}')
        return f"https://www.silkperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('elite' in t) para controlar el flujo
    if "elite" in t:
        # Retornamos el resultado procesado (f'https://www.eliteperfumes.cl/search?q={q}')
        return f"https://www.eliteperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('alisha' in t) para controlar el flujo
    if "alisha" in t:
        # Retornamos el resultado procesado (f'https://alishaperfumes.cl/search?q={q}')
        return f"https://alishaperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('yauras' in t) para controlar el flujo
    if "yauras" in t:
        # Retornamos el resultado procesado (f'https://yauras.cl/search?q={q}')
        return f"https://yauras.cl/search?q={q}"
    # Evaluamos la condición lógica ('oferta' in t) para controlar el flujo
    if "oferta" in t:
        # Retornamos el resultado procesado (f'https://ofertaperfumes.cl/search?q={q}')
        return f"https://ofertaperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('dbs' in t) para controlar el flujo
    if "dbs" in t:
        # Retornamos el resultado procesado (f'https://www.dbs.cl/catalogsearch/result/?q={q}')
        return f"https://www.dbs.cl/catalogsearch/result/?q={q}"

    # Retornamos el resultado procesado (sanitize_external_url(url_base, fallback='#'))
    return sanitize_external_url(url_base, fallback="#")
