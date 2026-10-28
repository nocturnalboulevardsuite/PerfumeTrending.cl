"""
PerfumeTrending.cl — Capa de Seguridad de Interfaz (UI Security & URL Sanitizers)
=================================================================================
Centraliza las defensas contra vulnerabilidades web en el portal Streamlit:
- Prevención estricta de Local File Inclusion / Path Traversal (LFI) en imágenes.
- Sanitización HTML contra Cross-Site Scripting (XSS) almacenado y reflejado.
- Validación de esquemas URL (`http://` / `https://`) en enlaces de salida a tiendas.
- Resolución canónica de enlaces de oferta para las 9 tiendas monitoreadas.
"""

import base64
import functools
import html
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

APP_DIR = Path(__file__).resolve().parent.parent
ALLOWED_ASSETS_DIR = (APP_DIR / "assets").resolve()
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

DEFAULT_PERFUME_IMAGE = "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
DEFAULT_AVATAR_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 80' fill='none'>"
    "<rect width='80' height='80' rx='40' fill='%23232834'/>"
    "<circle cx='40' cy='31' r='13' stroke='%23d4c2a5' stroke-width='3'/>"
    "<path d='M18 67c3.5-11.5 12.5-18 22-18s18.5 6.5 22 18' stroke='%23d4c2a5' stroke-width='3' stroke-linecap='round'/>"
    "</svg>"
)

SAFE_DATA_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
    "data:image/svg+xml;utf8,",
)


@functools.lru_cache(maxsize=512)
def _read_local_asset_data_uri(resolved_str: str) -> Optional[str]:
    """Codifica y cachea en RAM imágenes locales dentro de APP/assets/ para evitar lecturas de disco repetidas."""
    try:
        resolved = Path(resolved_str)
        ext = resolved.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        mime = mime_map.get(ext, "image/jpeg")
        b64 = base64.b64encode(resolved.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def formatear_nombre_especifico(perfume: Optional[Dict[str, Any]]) -> str:
    """
    Construye un título comercial específico e inequívoco para cada fragancia
    (ej. 'Romance Mujer EDP', 'Eros Pour Femme EDP', 'Eros Hombre EDT') para que
    ninguna ficha se muestre como una palabra suelta ambigua.
    """
    if not perfume or not isinstance(perfume, dict):
        return ""
    raw_name = str(perfume.get("nombre") or "").strip()
    if not raw_name:
        return ""

    # Eliminar palabras consecutivas repetidas (ej. 'Absolute Absolute')
    words = raw_name.split()
    dedup_words = []
    for w in words:
        if dedup_words and dedup_words[-1].lower() == w.lower():
            continue
        dedup_words.append(w)
    nombre = " ".join(dedup_words)
    nom_low = nombre.lower()

    genero = str(perfume.get("genero") or "").strip()
    tipo = str(perfume.get("tipo") or "").strip()
    tipo_low = tipo.lower()

    # Verificar si el nombre ya declara explícitamente género
    tiene_genero_en_nombre = bool(
        re.search(
            r"\b(?:pour femme|pour homme|l'homme|la femme|femme|homme|for her|for him|for women|for men|"
            r"woman|women|man|men|mujer|hombre|uomo|donna|girl|boy|lady|mademoiselle|her|elle)\b",
            nom_low,
        )
    )

    sufijos = []
    if not tiene_genero_en_nombre and genero in ("Mujer", "Hombre"):
        # Agregar género explícito en nombres cortos/ambiguos (<= 2 palabras) o líneas compartidas Hom/Muj
        lineas_compartidas = {
            "eros", "romance", "light blue", "the one", "one", "obsession", "eternity",
            "euphoria", "acqua di gio", "acqua di giò", "code", "scandal", "guilty",
            "le male", "classique", "9 pm", "9pm", "fakhar", "qimmah", "the kingdom",
            "yara", "asad", "cool water", "boss orange", "212", "212 vip", "ch",
            "individuel", "presence", "legend", "emblem", "starwalker",
        }
        if len(dedup_words) <= 2 or nom_low in lineas_compartidas:
            sufijos.append(genero)

    # Abreviatura de concentración si no está ya en el nombre
    abrev_conc = ""
    if "elixir" in tipo_low and "elixir" not in nom_low:
        abrev_conc = "Elixir"
    elif "extrait" in tipo_low and "extrait" not in nom_low:
        abrev_conc = "Extrait"
    elif "eau de parfum intense" in tipo_low:
        abrev_conc = "EDP Intense" if "intense" not in nom_low else "EDP"
    elif "eau de toilette intense" in tipo_low:
        abrev_conc = "EDT Intense" if "intense" not in nom_low else "EDT"
    elif "eau de parfum" in tipo_low or tipo_low == "edp":
        if not re.search(r"\b(?:edp|eau de parfum)\b", nom_low):
            abrev_conc = "EDP"
    elif "eau de toilette" in tipo_low or tipo_low == "edt":
        if not re.search(r"\b(?:edt|eau de toilette)\b", nom_low):
            abrev_conc = "EDT"
    elif "eau de cologne" in tipo_low or tipo_low == "edc":
        if not re.search(r"\b(?:edc|cologne|colonia)\b", nom_low):
            abrev_conc = "EDC"
    elif tipo_low == "parfum" and "parfum" not in nom_low:
        abrev_conc = "Parfum"

    if abrev_conc:
        sufijos.append(abrev_conc)

    if sufijos:
        return f"{nombre} {' '.join(sufijos)}"
    return nombre


def escape_html(value: Any) -> str:
    """Escapa caracteres especiales HTML (`<`, `>`, `&`, `\"`, `'`) para prevenir XSS."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def clean_html(html_str: str, join_char: str = "\n") -> str:
    """Elimina indentación inicial por línea para evitar bloques de código accidentales en Markdown."""
    if not html_str:
        return ""
    if join_char == " ":
        return " ".join(line.strip() for line in html_str.splitlines() if line.strip())
    return join_char.join(line.strip() for line in html_str.splitlines())


def sanitize_external_url(url: Optional[str], fallback: str = "#") -> str:
    """
    Valida que un enlace externo utilice exclusivamente `https://` o `http://`
    y escapa comillas/caracteres peligrosos para inserción segura en atributos `href`.
    """
    if not url or not isinstance(url, str):
        return fallback
    cleaned = url.strip()
    if not cleaned or cleaned == "#":
        return fallback
    try:
        parsed = urllib.parse.urlsplit(cleaned)
    except Exception:
        return fallback

    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return fallback

    # Bloquear saltos de línea o inyecciones de atributos
    safe_url = cleaned.replace('"', "%22").replace("'", "%27").replace("<", "%3C").replace(">", "%3E")
    return safe_url


def is_valid_https_image_url(url: Optional[str]) -> bool:
    """Verifica que una URL de avatar ingresada por usuario sea estrictamente HTTPS válida."""
    if not url or not isinstance(url, str):
        return False
    cleaned = url.strip()
    try:
        parsed = urllib.parse.urlsplit(cleaned)
    except Exception:
        return False
    return parsed.scheme.lower() == "https" and bool(parsed.netloc) and len(cleaned) <= 1024


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
    if not img_path_or_url or not isinstance(img_path_or_url, str):
        return default_src

    raw = img_path_or_url.strip()
    if not raw:
        return default_src

    # 1. URLs remotas HTTP/HTTPS
    if raw.lower().startswith(("https://", "http://")):
        if not allow_local and not raw.lower().startswith("https://"):
            return default_src
        safe_remote = sanitize_external_url(raw, fallback="")
        return safe_remote if safe_remote else default_src

    # 2. Data URIs de imagen controlados (validación estricta de alfabeto base64 contra ruptura de atributos)
    if raw == DEFAULT_AVATAR_SVG:
        return raw
    for prefix in (
        "data:image/png;base64,",
        "data:image/jpeg;base64,",
        "data:image/webp;base64,",
        "data:image/gif;base64,",
    ):
        if raw.startswith(prefix):
            b64_payload = raw[len(prefix):].strip()
            if b64_payload and len(b64_payload) <= 600_000 and all(
                c.isalnum() or c in "+/=" for c in b64_payload
            ):
                return prefix + b64_payload
            return default_src
    if allow_local and raw.startswith("data:image/svg+xml;utf8,"):
        if any(bad in raw.lower() for bad in ("<script", "onload", "onerror", "javascript:")):
            return default_src
        return raw.replace('"', "%22")

    # 3. Bloquear acceso local cuando no está explícitamente habilitado (ej. perfil de usuario)
    if not allow_local:
        return default_src

    # 4. Resolución confinada exclusivamente a APP/assets/
    candidates = []
    rel_clean = raw.lstrip("/\\")
    if rel_clean.lower().startswith("app/"):
        rel_clean = rel_clean[4:].lstrip("/\\")
    elif rel_clean.lower().startswith("app\\"):
        rel_clean = rel_clean[4:].lstrip("/\\")

    candidates.append(APP_DIR / rel_clean)
    candidates.append(ALLOWED_ASSETS_DIR / rel_clean)

    for cand in candidates:
        try:
            resolved = cand.resolve(strict=False)
            if not resolved.is_relative_to(ALLOWED_ASSETS_DIR):
                continue
            if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                continue
            if resolved.is_file():
                uri = _read_local_asset_data_uri(str(resolved))
                if uri:
                    return uri
        except Exception:
            continue

    return default_src


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
    t = (tienda_nombre or "").lower().strip()
    marca_clean = (marca or "").strip()
    nom_clean = (perfume_nombre or "").strip()
    if marca_clean and marca_clean.lower() not in nom_clean.lower():
        termino_busqueda = f"{marca_clean} {nom_clean}".strip()
    else:
        termino_busqueda = nom_clean
    q = urllib.parse.quote(termino_busqueda)

    safe_prod = sanitize_external_url(url_prod, fallback="")
    dead_markers = ("916524999", "construccion", "experiencia", "/test")

    if safe_prod and not any(dead in safe_prod.lower() for dead in dead_markers):
        return safe_prod

    if "falabella" in t:
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    if "paris" in t:
        return f"https://www.paris.cl/search?q={q}"
    if "ripley" in t:
        return f"https://simple.ripley.cl/search/{q}"
    if "silk" in t:
        return f"https://www.silkperfumes.cl/search?q={q}"
    if "elite" in t:
        return f"https://www.eliteperfumes.cl/search?q={q}"
    if "alisha" in t:
        return f"https://alishaperfumes.cl/search?q={q}"
    if "yauras" in t:
        return f"https://yauras.cl/search?q={q}"
    if "oferta" in t:
        return f"https://ofertaperfumes.cl/search?q={q}"
    if "dbs" in t:
        return f"https://www.dbs.cl/catalogsearch/result/?q={q}"

    return sanitize_external_url(url_base, fallback="#")
