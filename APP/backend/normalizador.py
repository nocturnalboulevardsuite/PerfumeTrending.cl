"""
PerfumeTrending.cl — Motor de Normalización y Reconocimiento Determinista de Entidades
=====================================================================================
Módulo especializado en procesamiento de texto, heurísticas comerciales y expresiones regulares
para la estandarización y validación estricta de perfumes y ofertas en e-commerce chileno:
- Normalización canónica de marcas (unificando más de 110 variantes ortográficas y de casing).
- Extracción precisa de volumen (ml / fl oz), concentración, género y formato ('regular' vs 'tester').
- Filtrado riguroso de accesorios, cosméticos en gramos, brumas, lociones, recargas, sets/combos y decants.
- Motor determinista de resolución de entidades en 12 capas contra clones, keyword stuffing y cruces de flankers.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

# Género esperado del perfume que se está auditando en el hilo/tarea actual.
# Permite que los scrapers propaguen el género a TODAS las validaciones internas
# (15+ llamadas a `coincide_entidad_detallada`) sin modificar cada firma intermedia.
_GENERO_ESPERADO_CTX: ContextVar[Optional[str]] = ContextVar("genero_esperado_perfume", default=None)


@contextmanager
def contexto_genero_esperado(genero: Optional[str]) -> Iterator[None]:
    """Establece temporalmente el género esperado para las validaciones de entidad del bloque."""
    token = _GENERO_ESPERADO_CTX.set(genero)
    try:
        yield
    finally:
        _GENERO_ESPERADO_CTX.reset(token)

# =============================================================================
# 1. CONSTANTES DE DOMINIO Y NORMALIZACIÓN CANÓNICA DE MARCAS
# =============================================================================

MARCAS_ARABES_CONOCIDAS: Set[str] = {
    "lattafa", "armaf", "afnan", "rasasi", "al haramain", "orientica",
    "swiss arabian", "maison alhambra", "alhambra", "fragrance world",
    "paris corner", "french avenue", "zimaya", "ard al zaafaran", "al wataniah",
    "khadlaj", "emper", "pendora scents", "riiffs", "anfar", "grandeur",
    "gulf orchid", "rayhaan", "dumont", "flavia", "oriental",
}

# Mapa de normalización canónica de marcas para evitar fragmentación de catálogo
CANONICAL_BRAND_MAP: Dict[str, str] = {
    "lattafa": "Lattafa",
    "lataffa": "Lattafa",
    "lattafa perfumes": "Lattafa",
    "maison alhambra": "Maison Alhambra",
    "maison al hambra": "Maison Alhambra",
    "alhambra": "Maison Alhambra",
    "fragrance world": "Fragrance World",
    "fragance world": "Fragrance World",
    "french avenue": "French Avenue",
    "paris corner": "Paris Corner",
    "armaf": "Armaf",
    "afnan": "Afnan",
    "rasasi": "Rasasi",
    "al haramain": "Al Haramain",
    "haramain": "Al Haramain",
    "ard al zaafaran": "Ard Al Zaafaran",
    "al zaafaran": "Ard Al Zaafaran",
    "al wataniah": "Al Wataniah",
    "swiss arabian": "Swiss Arabian",
    "zimaya": "Zimaya",
    "orientica": "Orientica",
    "emper": "Emper",
    "riiffs": "Riiffs",
    "anfar": "Anfar",
    "oudh al anfar": "Anfar",
    "grandeur": "Grandeur",
    "jo milano": "Jo Milano",
    "risala": "Risala",
    "flavia": "Flavia",
    "tubbees": "Tubbees",
    "pendora": "Pendora Scents",
    "pendora scents": "Pendora Scents",
    "khadlaj": "Khadlaj",
    "gulf orchid": "Gulf Orchid",
    "rayhaan": "Rayhaan",
    "dumont": "Dumont",
    # Casas de diseñador y nicho occidental
    "dior": "Dior",
    "christian dior": "Dior",
    "chanel": "Chanel",
    "versace": "Versace",
    "jean paul gaultier": "Jean Paul Gaultier",
    "jpg": "Jean Paul Gaultier",
    "giorgio armani": "Giorgio Armani",
    "armani": "Giorgio Armani",
    "emporio armani": "Giorgio Armani",
    "carolina herrera": "Carolina Herrera",
    "paco rabanne": "Paco Rabanne",
    "rabanne": "Paco Rabanne",
    "tom ford": "Tom Ford",
    "yves saint laurent": "Yves Saint Laurent",
    "saint laurent": "Yves Saint Laurent",
    "ysl": "Yves Saint Laurent",
    "creed": "Creed",
    "parfums de marly": "Parfums de Marly",
    "xerjoff": "Xerjoff",
    "maison francis kurkdjian": "Maison Francis Kurkdjian",
    "mfk": "Maison Francis Kurkdjian",
    "azzaro": "Azzaro",
    "dolce gabbana": "Dolce & Gabbana",
    "dolce and gabbana": "Dolce & Gabbana",
    "d g": "Dolce & Gabbana",
    "calvin klein": "Calvin Klein",
    "hugo boss": "Hugo Boss",
    "boss": "Hugo Boss",
    "moschino": "Moschino",
    "valentino": "Valentino",
    "prada": "Prada",
    "montblanc": "Montblanc",
    "mont blanc": "Montblanc",
    "burberry": "Burberry",
    "gucci": "Gucci",
    "bvlgari": "Bvlgari",
    "bulgari": "Bvlgari",
    "narciso rodriguez": "Narciso Rodriguez",
    "hermes": "Hermès",
    "mugler": "Mugler",
    "thierry mugler": "Mugler",
    "loewe": "Loewe",
    "kenzo": "Kenzo",
    "issey miyake": "Issey Miyake",
    "lancome": "Lancôme",
    "guerlain": "Guerlain",
    "ralph lauren": "Ralph Lauren",
    "polo ralph lauren": "Ralph Lauren",
    "antonio banderas": "Antonio Banderas",
    "benetton": "Benetton",
    "guess": "Guess",
    "ariana grande": "Ariana Grande",
    "rihanna": "Rihanna",
    "billie eilish": "Billie Eilish",
    "sabrina carpenter": "Sabrina Carpenter",
    "tous": "Tous",
    "sospiro": "Sospiro",
    "initio": "Initio Parfums Privés",
    "initio parfums": "Initio Parfums Privés",
    "roja": "Roja Parfums",
    "roja dove": "Roja Parfums",
    "roja parfums": "Roja Parfums",
    "kilian": "By Kilian",
    "by kilian": "By Kilian",
    "mancera": "Mancera",
    "montale": "Montale",
    "givenchy": "Givenchy",
    "viktor rolf": "Viktor & Rolf",
    "viktor and rolf": "Viktor & Rolf",
    "lacoste": "Lacoste",
    "victoria secret": "Victoria's Secret",
    "victorias secret": "Victoria's Secret",
    "salvatore ferragamo": "Salvatore Ferragamo",
    "ferragamo": "Salvatore Ferragamo",
    "mercedes benz": "Mercedes-Benz",
    "police": "Police",
    "nikos": "Nikos",
    "jesus del pozo": "Jesús del Pozo",
    "halloween": "Halloween",
    "adolfo dominguez": "Adolfo Domínguez",
    "agatha ruiz de la prada": "Agatha Ruiz de la Prada",
    "oscar de la renta": "Oscar de la Renta",
    "paloma picasso": "Paloma Picasso",
    "michael kors": "Michael Kors",
    "jimmy choo": "Jimmy Choo",
    "coach": "Coach",
    "boucheron": "Boucheron",
    "clinique": "Clinique",
    "estee lauder": "Estée Lauder",
    "elizabeth arden": "Elizabeth Arden",
    "davidoff": "Davidoff",
    "nautica": "Nautica",
    "tommy hilfiger": "Tommy Hilfiger",
    "dkny": "DKNY",
    "donna karan": "Donna Karan",
    "cacharel": "Cacharel",
    "chloe": "Chloé",
    "marc jacobs": "Marc Jacobs",
    "issey": "Issey Miyake",
    "argos": "Argos",
    "bon parfumeur": "Bon Parfumeur",
    "eight & bob": "Eight & Bob",
    "eight and bob": "Eight & Bob",
    "eight bob": "Eight & Bob",
    "andy tauer": "Tauer Perfumes",
    "tauer": "Tauer Perfumes",
    "tauer perfumes": "Tauer Perfumes",
    "stephane humbert lucas": "Stéphane Humbert Lucas",
    "stephane humbert lucas 777": "Stéphane Humbert Lucas",
    "stephane humbert": "Stéphane Humbert Lucas",
    "ramon monegal": "Ramón Monegal",
    "jovoy": "Jovoy Paris",
    "jovoy paris": "Jovoy Paris",
    "lorenzo pazzaglia": "Lorenzo Pazzaglia",
    "pastor prive": "Pastor Privé",
    "pastor fragrances": "Pastor Privé",
    "m micallef": "M. Micallef",
    "m. micallef": "M. Micallef",
    "micallef": "M. Micallef",
    "thameen": "Thameen",
    "thameen london": "Thameen",
    "shakira": "Shakira",
    "bharara": "Bharara",
    "rave": "Rave",
    "rayhaan": "Rayhaan",
    "just lychee": "Fragrance World",
}

MARCAS_INVALIDAS_CATALOGO: Set[str] = {
    "", "varios", "perfumero", "generico", "sin marca", "otros",
    "accesorios", "pack", "set", "muestra", "decant", "test", "s/m",
    "garnier", "vogue", "maybelline", "loreal paris", "l'oreal paris", "l'oréal paris",
    "nivea", "dove", "pantene", "head & shoulders", "sedal", "etienne", "petrizzio",
    "disenador", "diseñador", "nicho", "perfume", "perfumes",
}

# Palabras clave de productos derivados, cosméticos o formatos que NO son frascos individuales de perfume
PALABRAS_EXCLUSION: List[str] = [
    "desodorante", "deodorant", "body mist", "bodymist", "body spray", "bodyspray",
    "body splash", "bodysplash", "splash", "hair mist", "hairmist", "bruma", "leau brume", "l'eau brume",
    "body lotion", "crema", "locion corporal", "loción corporal", "locion ", "loción ",
    "locion para despues", "loción para después", "después del afeitado", "despues del afeitado",
    "shampoo", "champu", "acondicionador", "gel de ducha", "shower gel", "jabon", "jabón", "vela", "candle",
    "after shave", "after-shave", "aftershave", "balsamo", "bálsamo", "neceser", "estuche vacio",
    "estuche vacío", "perfumero", "de vidrio", "atomizador recargable", "recargable", "recarga",
    "refill", "refillable", "recargrefill",
    "labial", "mascara pestañas", "mascara", "sachet", "achet", "with box",
    "roll on", "roll-on", "cuidado del cabello", "tratamiento hidratante",
    "twist and spray", "twist & spray", "travel purse",
    # Muestras, decants, discovery sets y sets multipieza
    "atomizador", "atomizer", "travel spray", "pocket spray", "miniatura", "decant", "sample",
    "muestra", "vial", "discovery", "estuche", "cofre", "coffret", "gift set",
    # Imitaciones, clones explícitos y equivalencias
    "inspirado en", "inspirada en", "inspiracion", "inspiración", "tipo ", "dupe",
    "equivalencia", "imitacion", "imitación", "clon", "alternativo",
    # Artículos ajenos a perfumería (cosméticos, cabello, hogar, puericultura)
    "repelente", "roedores", "extractor", "extractor de leche", "brillo labial", "voluminizador",
    "lip gloss", "suero", "serum", "difusor", "ambientador", "home spray",
    "tinte", "nutrisse", "maquillaje", "aclarante", "facial", "capilar", "mascarilla",
    "pestañina", "rubor", "polvo", "iluminador", "base liquida", "base líquida", "esmalte", "uñas",
]

RE_PRODUCTO_INVALIDO = re.compile(
    r"(?:"
    r"\b\d+(?:[.,]\d+)?\s*(?:g|gr|grs|gramos)\b|"  # Cosméticos/desodorantes en gramos (ej. 1,5G, 75G)
    r"\b\d+\s*x\s*\d+(?:[.,]\d+)?\s*ml\b|"         # Multipacks/viales (ej. 4 x 2 ml)
    r"\b\d+\s*(?:pzas|pcs|piezas|pc)\b|"           # Sets multipieza (ej. 3 pzas, 4pc)
    r"\b(?:set|pack|kit|duo|trio)\b|"              # Kits y packs
    r"(?:\s*\+\s*)"                                # Combos con '+' (ej. Polo Red + Polo 67, +Sg, +Deo)
    r")",
    re.IGNORECASE,
)


def _norm_ascii(texto: str) -> str:
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("utf-8")
    t = re.sub(r"[^a-z0-9\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def normalizar_marca_canonica(marca: str) -> str:
    """
    Convierte cualquier variante de casing u ortografía de marca en su nombre canónico oficial.
    Ejemplo: 'MAISON AL HAMBRA' -> 'Maison Alhambra', 'CHRISTIAN DIOR' -> 'Dior'.
    """
    if not marca or not isinstance(marca, str):
        return ""
    raw = marca.strip()
    clave = _norm_ascii(raw)
    if clave in CANONICAL_BRAND_MAP:
        return CANONICAL_BRAND_MAP[clave]

    # Comprobar sin espacios para variantes como 'maisonalhambra' o 'montblanc'
    compacta = clave.replace(" ", "")
    for k, canon in CANONICAL_BRAND_MAP.items():
        if k.replace(" ", "") == compacta:
            return canon

    # Si está completamente en mayúsculas o minúsculas, aplicar Title Case limpio
    if raw.isupper() or raw.islower():
        return " ".join(w.capitalize() if len(w) > 2 else w.upper() if w.lower() in {"ck", "dkny", "ysl"} else w.capitalize() for w in raw.split())
    return re.sub(r"\s+", " ", raw)


def detectar_formato_oferta(titulo: str, url: str = "") -> str:
    """Clasifica si una oferta corresponde a frasco comercial sellado ('regular') o 'tester'."""
    combo = f"{titulo or ''} {url or ''}".lower()
    if re.search(r"\btester\b", combo):
        return "tester"
    return "regular"


# =============================================================================
# 2. EXTRACCIÓN DE METADATOS (VOLUMEN, CONCENTRACIÓN, GÉNERO, SANIDAD)
# =============================================================================

def extraer_volumen_ml(texto: str, default: int = 100) -> int:
    """
    Extrae la capacidad en mililitros (ml) desde el título, URL o etiqueta de variante.
    Soporta mililitros directos (2 a 1000 ml) y conversión desde fl oz.
    """
    if not texto:
        return default

    # Si hay decimales tipo '1,5 ml' o '7.5ml', redondear para detectar decants/viales pequeños
    match_dec_ml = re.search(r"(\d{1,3}[.,]\d+)\s*ml\b", texto, re.IGNORECASE)
    if match_dec_ml:
        val_f = float(match_dec_ml.group(1).replace(",", "."))
        val_i = max(1, int(round(val_f)))
        if 1 <= val_i <= 1000:
            return val_i

    match_ml = re.search(r"(\d{1,4})\s*(?:ml|m\b)", texto, re.IGNORECASE)
    if match_ml:
        val = int(match_ml.group(1))
        if 2 <= val <= 1000:
            return val

    match_oz = re.search(r"(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz|oz)\b", texto, re.IGNORECASE)
    if match_oz:
        val_oz = float(match_oz.group(1))
        ml_estimado = int(round(val_oz * 29.5735))
        for estandar in [30, 50, 60, 75, 80, 90, 100, 105, 125, 150, 200]:
            if abs(ml_estimado - estandar) <= 4:
                return estandar
        if 2 <= ml_estimado <= 1000:
            return ml_estimado

    return default


def extraer_concentracion(texto: str) -> str:
    """Identifica y normaliza la concentración olfativa del perfume."""
    t = (texto or "").lower()
    if "elixir" in t:
        return "Elixir"
    if "extrait" in t or "extract" in t or "exdp" in t:
        return "Extrait de Parfum"
    if "eau de parfum intense" in t or "edp intense" in t:
        return "Eau de Parfum Intense"
    if "eau de parfum" in t or re.search(r"\bedp\b", t):
        return "Eau de Parfum"
    if "eau de toilette intense" in t or "edt intense" in t:
        return "Eau de Toilette Intense"
    if "eau de toilette" in t or re.search(r"\bedt\b", t):
        return "Eau de Toilette"
    if "eau de cologne" in t or re.search(r"\bedc\b", t) or "colonia" in t:
        return "Eau de Cologne"
    if "parfum" in t:
        return "Parfum"
    return "Eau de Parfum"


# Marcadores de género evaluados SIEMPRE por palabra completa (\b...\b).
# Antes se buscaban como subcadena, lo que clasificaba 'Romance', 'Armani' o 'Mancera'
# como masculinos por contener 'man', y 'Hermès' como femenino por contener 'her'.
MARCADORES_GENERO_FEMENINO: Tuple[str, ...] = (
    "pour femme", "femme", "mujer", "mujeres", "women", "woman", "for her", "donna",
    "dama", "damas", "femenino", "femenina", "lady", "girl",
)
MARCADORES_GENERO_MASCULINO: Tuple[str, ...] = (
    "pour homme", "homme", "hombre", "hombres", "men", "man", "for him", "uomo",
    "caballero", "caballeros", "masculino", "varon", "male", "boy",
)
_RE_FEMENINO = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in MARCADORES_GENERO_FEMENINO) + r")\b")
_RE_MASCULINO = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in MARCADORES_GENERO_MASCULINO) + r")\b")


def detectar_marcadores_genero(texto: str) -> Tuple[bool, bool]:
    """Retorna `(tiene_marcador_femenino, tiene_marcador_masculino)` evaluando palabras completas."""
    t = _norm_ascii(texto)
    if not t:
        return False, False
    return bool(_RE_FEMENINO.search(t)), bool(_RE_MASCULINO.search(t))


def detectar_genero_explicito(texto: str) -> Optional[str]:
    """
    Retorna 'Mujer' u 'Hombre' solo cuando el texto declara un único género de forma inequívoca.
    Retorna None si no hay marcadores o si aparecen marcadores de ambos géneros.
    """
    fem, masc = detectar_marcadores_genero(texto)
    if fem and not masc:
        return "Mujer"
    if masc and not fem:
        return "Hombre"
    return None


def normalizar_genero(genero: Optional[str]) -> Optional[str]:
    """Normaliza etiquetas de género heterogéneas a 'Mujer', 'Hombre', 'Unisex' o None."""
    g = _norm_ascii(genero or "")
    if not g:
        return None
    if g in ("mujer", "femenino", "female", "women", "woman", "dama", "f"):
        return "Mujer"
    if g in ("hombre", "masculino", "male", "men", "man", "caballero", "h"):
        return "Hombre"
    if g in ("unisex", "u", "ambos"):
        return "Unisex"
    return None


def extraer_genero(texto: str) -> str:
    """Determina el género objetivo del perfume ('Mujer', 'Hombre' o 'Unisex')."""
    t_raw = (texto or "").lower()
    fem, masc = detectar_marcadores_genero(t_raw)
    if re.search(r"\(\s*m\s*\)", t_raw):
        fem = True
    if re.search(r"\(\s*h\s*\)", t_raw):
        masc = True
    if fem and not masc:
        return "Mujer"
    if masc and not fem:
        return "Hombre"
    if fem and masc:
        # Ambos marcadores: priorizar el identificador más específico del nombre comercial
        t = _norm_ascii(t_raw)
        if re.search(r"\b(?:pour femme|femme|woman|for her)\b", t):
            return "Mujer"
        if re.search(r"\b(?:pour homme|homme|for him|uomo)\b", t):
            return "Hombre"
        return "Unisex"
    if re.search(r"\s+m\s*$", t_raw):
        return "Mujer"
    if re.search(r"\s+h\s*$", t_raw):
        return "Hombre"
    return "Unisex"


def es_arabe(marca: str, nombre: str = "") -> bool:
    """Indica si una fragancia pertenece a perfumería oriental / árabe."""
    m_canon = normalizar_marca_canonica(marca).lower()
    texto = f"{m_canon} {(marca or '').lower()} {(nombre or '').lower()}"
    if any(m in texto for m in MARCAS_ARABES_CONOCIDAS):
        return True
    lineas_iconicas = ["khamrah", "asad", "club de nuit", "hawas", "fakhar", "yara", "bade'e al oud", "badee al oud"]
    return any(k in texto for k in lineas_iconicas)


def es_precio_valido(precio: Optional[Any], min_clp: int = 5000) -> bool:
    """
    Validador de sanidad comercial para precios de perfumes de frasco completo en CLP.
    Descarta nulos, valores menores al umbral comercial ($5.000 CLP por defecto),
    valores >= $1.000.000 CLP y placeholders de sin stock ($9.999.999 / $999.999).
    """
    if precio is None:
        return False
    try:
        p = int(round(float(precio)))
    except (ValueError, TypeError):
        return False

    if p < min_clp or p >= 1000000:
        return False
    if p in (9999999, 9999990, 999999):
        return False
    return True


def es_producto_perfume_valido(
    titulo: str,
    tags: Optional[List[str]] = None,
    marca: Optional[str] = None,
    volumen_min_ml: int = 25,
) -> bool:
    """
    Valida que un producto sea un frasco individual de perfume genuino y NO un accesorio,
    cosmético en gramos, bruma, crema, desodorante, set/combo multipieza ni decant (<25 ml).
    """
    if not titulo or not isinstance(titulo, str) or len(titulo.strip()) < 3:
        return False

    if marca and marca.strip():
        m_clean = _norm_ascii(marca)
        if m_clean in MARCAS_INVALIDAS_CATALOGO:
            return False

    t = titulo.lower()
    for palabra in PALABRAS_EXCLUSION:
        if palabra in t:
            return False

    if RE_PRODUCTO_INVALIDO.search(t):
        return False

    # Si el título declara un volumen explícito inferior al mínimo de frasco comercial (ej. 5ml, 10ml, 15ml), descartar
    vol_explicito = extraer_volumen_ml(t, default=0)
    if 0 < vol_explicito < volumen_min_ml:
        return False

    if tags:
        tags_str = " ".join(str(x) for x in tags).lower()
        for palabra in PALABRAS_EXCLUSION:
            if palabra in tags_str:
                return False

    return True


PALABRAS_REPETIDAS_LEGITIMAS = {
    "anais", "amor", "can", "plus", "ricci", "love", "yum", "pyar", "ella"
}


def eliminar_palabras_duplicadas(texto: str) -> str:
    """
    Elimina palabras repetidas de forma consecutiva sin distinguir mayúsculas ni acentos.
    Ej: 'Good Girl Jasmine Absolute Absolute' -> 'Good Girl Jasmine Absolute'.
    Preserva nombres legítimos repetidos como 'Anais Anais', 'Amor Amor', 'Can Can', 'Plus Plus'.
    """
    if not texto:
        return ""
    palabras = str(texto).split()
    resultado: List[str] = []
    for w in palabras:
        norm_w = _norm_ascii(w)
        if resultado and _norm_ascii(resultado[-1]) == norm_w and norm_w:
            if norm_w not in PALABRAS_REPETIDAS_LEGITIMAS:
                continue
        resultado.append(w)
    return " ".join(resultado)


def limpiar_nombre_perfume(titulo: str, marca: str = "") -> str:
    """
    Limpia el título comercial de e-commerce para obtener el nombre canónico del perfume
    PRESERVANDO flankers esenciales ('Intense', 'Elixir', 'Extreme', 'Absolu', 'Le Parfum',
    'Royal', 'Lucky', 'Profondo', 'Flame', 'Energy', 'Pour Homme', 'Pour Femme').
    """
    if not titulo:
        return ""

    limpio = str(titulo).strip()

    # 1. Remover prefijos genéricos de categoría o etiqueta 'Tester' inicial antes de extraer marca
    limpio = re.sub(
        r"^(?:(?:tester|perfume|fragancia|agua de perfume|agua de tocador|colonia)\s*[-|:/]?\s*)+(?:(?:hombre|mujer|unisex|dama|varon|varón|arabe|árabe)\s+)?",
        "",
        limpio,
        flags=re.IGNORECASE,
    )

    # 2. Remover marca (tanto cruda como canónica y variantes conocidas) si aparece como prefijo
    marcas_a_quitar = set()
    if marca:
        marcas_a_quitar.add(marca.strip())
        m_canon = normalizar_marca_canonica(marca)
        if m_canon:
            marcas_a_quitar.add(m_canon)
            if m_canon == "Maison Alhambra":
                marcas_a_quitar.update(["Maison Al Hambra", "Alhambra"])
            elif m_canon == "Dior":
                marcas_a_quitar.add("Christian Dior")
            elif m_canon == "Yves Saint Laurent":
                marcas_a_quitar.update(["Saint Laurent"])
            elif m_canon == "Dolce & Gabbana":
                marcas_a_quitar.update(["Dolce Gabbana", "Dolce-Gabbana", "Dolce and Gabbana"])
            elif m_canon == "Ard Al Zaafaran":
                marcas_a_quitar.add("Al Zaafaran")

    # Ordenar de más larga a más corta para remover prefijos compuestos completos
    for m_var in sorted(marcas_a_quitar, key=len, reverse=True):
        if m_var:
            limpio = re.sub(rf"^(?:{re.escape(m_var)}\s*[-|:/]?\s*)+", "", limpio, flags=re.IGNORECASE)

    # 3. Remover especificaciones de mililitros (1 a 4 dígitos + decimales) y onzas
    limpio = re.sub(r"\b\d{1,4}(?:[.,]\d+)?\s*(?:ml|m)\b", "", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:fl\.?\s*oz|oz)\b", "", limpio, flags=re.IGNORECASE)

    # 4. Remover concentraciones puras (pero conservar 'Elixir', 'Le Parfum', 'Intense', 'Extreme', 'Absolu'!)
    limpio = re.sub(
        r"\b(?:eau\s+de\s+parfum|eau\s+de\s+toilette|eau\s+de\s+cologne|extrait\s+de\s+parfum|edp|edt|edc|exdp)\b",
        "",
        limpio,
        flags=re.IGNORECASE,
    )

    # 5. Remover ruido comercial y etiquetas de género genéricas que NO son parte del nombre oficial
    limpio = re.sub(r"\((?:h|m|u|hombre|mujer|unisex|men|women|tester)\)", "", limpio, flags=re.IGNORECASE)
    # Remover conectores 'de {marca}' o 'para {genero}' antes de ruidos
    if marca:
        for m_var in sorted(marcas_a_quitar, key=len, reverse=True):
            if m_var:
                limpio = re.sub(rf"\bde\s+{re.escape(m_var)}\b", "", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\bpara\s+(?:hombre|mujer|unisex|caballero|dama|varon|varón)\b", "", limpio, flags=re.IGNORECASE)

    ruidos = [
        "tester", "vaporizador", "natural spray", "spray", "nuevo", "nueva coleccion",
        "nueva colección", "original", "oferta", "envio gratis", "despacho", "sellado",
        "hombre", "mujer", "unisex", "dama", "varon", "varón", "caballero",
    ]
    for r in ruidos:
        limpio = re.sub(rf"\b{re.escape(r)}\b", "", limpio, flags=re.IGNORECASE)

    # Remover preposiciones sueltas al final (ej. '... De', '... Para')
    limpio = re.sub(r"\s+\b(?:de|para)\b\s*$", "", limpio, flags=re.IGNORECASE)

    # Remover 'men' o 'woman'/'women' sueltos al final salvo cuando forman parte del nombre (ej. '212 Men', '212 VIP Men', 'CH Men')
    if not re.search(r"\b(?:212|ch|solo|boss)\s+(?:vip\s+)?men\b", limpio, flags=re.IGNORECASE):
        limpio = re.sub(r"\s+\b(?:men|man|women|woman)\b\s*$", "", limpio, flags=re.IGNORECASE)

    # 6. Remover códigos finales de catálogo (' H', ' M', ' U')
    limpio = re.sub(r"\s+[hmuHMU]\s*$", "", limpio)

    # 7. Limpiar signos residuales respetando apóstrofes y '&' dentro de nombres (ej. J'adore, D&G, Bade'e)
    limpio = re.sub(r"[-–—/|()\[\]:+]+", " ", limpio)
    limpio = re.sub(r"\s+", " ", limpio).strip()

    # 8. Eliminar palabras consecutivas repetidas (ej. 'Good Girl Jasmine Absolute Absolute')
    limpio = eliminar_palabras_duplicadas(limpio)

    if len(limpio) < 2:
        limpio = titulo.split("-")[0].strip()

    # Capitalización inteligente preservando números romanos o siglas cortas
    palabras = []
    for w in limpio.split():
        if w.upper() in {"II", "III", "IV", "VI", "VIP", "NYC", "YSL", "CH", "CK", "XS"}:
            palabras.append(w.upper())
        elif "'" in w or "’" in w:
            partes = re.split(r"(['’])", w)
            palabras.append("".join(p.capitalize() if p not in ("'", "’") else p for p in partes))
        else:
            palabras.append(w.capitalize())
    return " ".join(palabras)


# =============================================================================
# 3. MOTOR DE RESOLUCIÓN DETERMINISTA DE ENTIDADES (ENTITY RESOLUTION)
# =============================================================================

@dataclass
class ResultadoCoincidencia:
    """Estructura de trazabilidad para validación y auditoría de ofertas."""
    coincide: bool
    confianza: float
    motivo: str
    marca_detectada: Optional[str] = None
    flanker_detectado: Optional[str] = None
    concentracion_detectada: Optional[str] = None
    volumen_detectado: Optional[int] = None
    formato_invalido: Optional[str] = None
    formato_detectado: str = "regular"


CASAS_CLON_DEDICADAS: Set[str] = {
    "fragrance world", "fragance world", "maison alhambra", "maison al hambra", "alhambra",
    "paris corner", "la french", "french avenue", "barakkat", "orientica", "zimaya",
    "emper", "milestone", "camara", "dumont", "flavia", "sterling", "pendora",
    "pendora scents", "khalis", "ard al zaafaran", "al zaafaran", "my perfumes",
    "paris riviera", "georges mezotti", "creation lamis", "dorall collection", "shirley may",
    "velinne", "nazire", "nayel", "layna", "avinari", "inzpira", "inzpira fragrances",
    "asten", "risala", "gulf orchid", "fumeri", "maison azhar", "le chameau",
    "hamidi", "rayhaan", "anfar", "oudh al anfar", "beas", "al wataniah", "khadlaj",
    "grandeur", "jo milano", "riiffs", "zakat",
}

MARCAS_DISENADOR_PRESTIGIO: Dict[str, List[str]] = {
    "dior": ["dior", "christian dior"],
    "christian dior": ["dior", "christian dior"],
    "chanel": ["chanel"],
    "versace": ["versace"],
    "jean paul gaultier": ["jean paul gaultier", "gaultier", "jpg"],
    "giorgio armani": ["giorgio armani", "armani", "emporio armani"],
    "carolina herrera": ["carolina herrera", "ch"],
    "paco rabanne": ["paco rabanne", "rabanne"],
    "tom ford": ["tom ford"],
    "yves saint laurent": ["yves saint laurent", "saint laurent", "ysl"],
    "creed": ["creed"],
    "parfums de marly": ["parfums de marly", "de marly", "pdm"],
    "xerjoff": ["xerjoff"],
    "maison francis kurkdjian": ["maison francis kurkdjian", "francis kurkdjian", "mfk"],
    "azzaro": ["azzaro"],
    "dolce & gabbana": ["dolce & gabbana", "dolce gabbana", "dolce and gabbana", "d&g"],
    "calvin klein": ["calvin klein", "ck"],
    "hugo boss": ["hugo boss", "boss"],
    "moschino": ["moschino"],
    "valentino": ["valentino"],
    "prada": ["prada"],
    "montblanc": ["montblanc", "mont blanc"],
    "burberry": ["burberry"],
    "gucci": ["gucci"],
    "bvlgari": ["bvlgari", "bulgari"],
    "narciso rodriguez": ["narciso rodriguez"],
    "hermes": ["hermes", "hermès"],
    "mugler": ["mugler", "thierry mugler"],
    "loewe": ["loewe"],
    "kenzo": ["kenzo"],
    "issey miyake": ["issey miyake"],
    "lancome": ["lancome", "lancôme"],
    "guerlain": ["guerlain"],
    "ralph lauren": ["ralph lauren", "polo ralph lauren"],
    "antonio banderas": ["antonio banderas", "banderas"],
    "benetton": ["benetton"],
    "guess": ["guess"],
    "ariana grande": ["ariana grande"],
    "rihanna": ["rihanna"],
    "billie eilish": ["billie eilish", "eilish"],
    "sabrina carpenter": ["sabrina carpenter"],
    "tous": ["tous"],
    "sospiro": ["sospiro"],
    "initio": ["initio", "initio parfums"],
    "roja": ["roja", "roja dove", "roja parfums"],
    "kilian": ["kilian", "by kilian"],
    "mancera": ["mancera"],
    "montale": ["montale"],
    "givenchy": ["givenchy"],
    "viktor & rolf": ["viktor & rolf", "viktor rolf", "viktor and rolf"],
    "lacoste": ["lacoste"],
}

MARCAS_ORIENTALES_RECONOCIDAS: Dict[str, List[str]] = {
    "lattafa": ["lattafa"],
    "armaf": ["armaf"],
    "afnan": ["afnan"],
    "rasasi": ["rasasi"],
    "al haramain": ["al haramain", "al-haramain", "haramain"],
    "swiss arabian": ["swiss arabian"],
}

FORMATOS_EXCLUIDOS: List[Tuple[str, str]] = [
    (r"\brecarga\b", "recarga"),
    (r"\brecargable\b", "recargable"),
    (r"\brefill\b", "refill"),
    (r"\brefillable\b", "refillable"),
    (r"recargrefill", "refill"),
    (r"\bestuche\b", "estuche"),
    (r"\bcofre\b", "cofre"),
    (r"\bcoffret\b", "cofre"),
    (r"\bgift\s*set\b", "gift set"),
    (r"\bset\b", "set"),
    (r"\bkit\b", "kit"),
    (r"\bdiscovery\b", "discovery set"),
    (r"\b\d+\s*(?:pzas|pcs|piezas|pc)\b", "multipack"),
    (r"\b\d+\s*x\s*\d+\s*ml\b", "multipack viales"),
    (r"\bdesodorante\b", "desodorante"),
    (r"\bdeodorant\b", "desodorante"),
    (r"\bafter\s*shave\b", "after shave"),
    (r"\baftershave\b", "after shave"),
    (r"\bbody\s*mist\b", "body mist"),
    (r"\bhair\s*mist\b", "hair mist"),
    (r"\bleau[\s\-]*brume\b", "bruma capilar/corporal"),
    (r"\bbrume\b", "bruma"),
    (r"\bbruma\b", "bruma"),
    (r"\bsplash\b", "body splash"),
    (r"\bbody\s*spray\b", "body spray"),
    (r"\bbody\s*lotion\b", "body lotion"),
    (r"\blocion\b", "loción"),
    (r"\bloci[oó]n\b", "loción"),
    (r"\bcrema\b", "crema"),
    (r"\bshower\s*gel\b", "shower gel"),
    (r"\bgel\s+de\s+ducha\b", "shower gel"),
    (r"\bshampoo\b", "shampoo"),
    (r"\bvela\b", "vela"),
    (r"\bcandle\b", "vela"),
    (r"\broll[\s\-]*on\b", "roll-on"),
    (r"\bdecant\b", "decant"),
    (r"\bvial\b", "vial"),
    (r"\bmuestra\b", "muestra"),
    (r"\bsample\b", "sample"),
    (r"\bminiatura\b", "miniatura"),
    (r"\btravel\s*spray\b", "travel spray"),
    (r"\bpocket\s*spray\b", "pocket spray"),
    (r"\btravel\s*purse\b", "travel purse"),
    (r"\batomizador\b", "atomizador"),
    (r"\bperfumero\b", "perfumero"),
    (r"\bsachet\b", "sachet"),
    (r"\bachet\b", "sachet"),
    (r"\b\d+(?:[.,]\d+)?\s*(?:g|gr|grs|gramos)\b", "cosmético en gramos"),
    (r"\b\d{2,3}\s*ml\s*\+\s*\d{1,3}\s*ml\b", "set/pack combinado"),
    (r"\+\s*(?:sg|bl|deo|mini|travel|crema|locion|loci[oó]n|shower)\b", "set con regalo"),
]

FLANKERS_EXCLUSIVOS: Set[str] = {
    "elixir", "intense", "intenso", "extreme", "absolu", "absolute", "absolue",
    "profondo", "profumo", "flame", "energy", "lucky", "royal", "prive", "privé",
    "sport", "cologne", "fraiche", "fraîche", "noir", "rouge", "bleu", "blue",
    "gold", "platinum", "platine", "cobalt", "paradox", "floral", "nectar",
    "lumiere", "lumière", "ultime", "essentiel", "leau", "l'eau", "reserve",
    "parfum", "le parfum", "extrait", "legend", "victory", "hero", "black",
    "white", "silver", "coral", "valentina", "intensement", "intensément",
    "flowers", "libre intense", "born in roma intense", "coral fantasy",
    "yellow dream", "green stravaganza", "udo", "oud", "amber", "velvet",
    "cherry", "peach", "vanilla", "vanille", "rose", "musk", "leather",
    "urban", "untold", "sillage", "milestone", "iconic", "precieux", "précieux",
    "ice", "fire", "tropical", "malibu", "glacial", "komodo",
    "nuit", "night", "beyond", "sheer", "summer",
}

PALABRAS_GENERICAS_NOMBRE: Set[str] = {
    "eau", "de", "parfum", "toilette", "cologne", "edp", "edt", "edc",
    "perfume", "fragancia", "spray", "vaporizador", "hombre", "mujer",
    "unisex", "men", "man", "women", "woman", "for", "pour", "him", "her",
    "the", "and", "by", "ml", "oz",
}


def _normalizar_texto_match(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("utf-8").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s\+]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _aliases_marca(marca_norm: str) -> List[str]:
    if not marca_norm:
        return []
    for k, aliases in MARCAS_DISENADOR_PRESTIGIO.items():
        if k in marca_norm or any(a == marca_norm for a in aliases):
            return aliases
    for k, aliases in MARCAS_ORIENTALES_RECONOCIDAS.items():
        if k in marca_norm or any(a == marca_norm for a in aliases):
            return aliases
    return [marca_norm]


def coincide_entidad_detallada(
    titulo: str,
    perfume_nombre: str,
    marca: str = "",
    concentracion: str = "",
    volumen_esperado: Optional[int] = None,
    url: str = "",
    precio_candidato: Optional[int] = None,
    precio_referencia: Optional[int] = None,
    formato_esperado: Optional[str] = None,
    vendedor: str = "",
    genero_esperado: Optional[str] = None,
) -> ResultadoCoincidencia:
    """
    Evalúa determinísticamente en 12 capas si una oferta candidata corresponde exactamente
    al perfume buscado, bloqueando clones, keyword stuffing, formatos inválidos, decants,
    vendedores terceros sospechosos, cruces de género/flankers y anomalías de precio.

    `genero_esperado` ('Mujer' | 'Hombre' | 'Unisex'): si no se entrega explícitamente,
    se toma del contexto activo (`contexto_genero_esperado`) establecido por el scraper.
    """
    if not titulo or not perfume_nombre:
        return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Título o nombre vacío")

    if genero_esperado is None:
        genero_esperado = _GENERO_ESPERADO_CTX.get()

    tit_raw = str(titulo)
    url_raw = str(url or "")
    tit = _normalizar_texto_match(tit_raw)
    url_norm = _normalizar_texto_match(url_raw.replace("-", " ").replace("/", " ").replace("_", " "))
    combo_text = f"{tit} {url_norm}".strip()

    p_norm = _normalizar_texto_match(perfume_nombre)
    m_canon = normalizar_marca_canonica(marca)
    m_norm = _normalizar_texto_match(m_canon or marca)
    c_norm = _normalizar_texto_match(concentracion)
    formato_det = detectar_formato_oferta(tit_raw, url_raw)

    # 0. Guardia de formato esperado ('regular' vs 'tester') si el llamador lo restringe explícitamente
    if formato_esperado and formato_esperado in ("regular", "tester") and formato_det != formato_esperado:
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo=f"Formato discrepante: esperado '{formato_esperado}', candidato es '{formato_det}'",
            formato_detectado=formato_det,
        )

    # 1. Exclusión inmediata de vocabulario de clones explícitos, accesorios y no-perfumes
    frases_clon_no_perfume = [
        "inspirado en", "inspirada en", "inspiracion", "tipo ", "dupe", "equivalencia",
        "imitacion", "clon", "alternativo", "similar a", "version de",
        "repelente", "roedores", "extractor de leche", "brillo labial", "lip gloss",
        "voluminizador", "suero", "serum", "mascara pestanas",
    ]
    for f_bad in frases_clon_no_perfume:
        if f_bad in combo_text:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Artículo excluido o clon explícito detectado ('{f_bad.strip()}')",
                formato_invalido=f_bad.strip(),
                formato_detectado=formato_det,
            )

    for regex_fmt, label_fmt in FORMATOS_EXCLUIDOS:
        if re.search(regex_fmt, combo_text, re.IGNORECASE):
            # Permitir solo si el propio perfume canónico lo lleva explícitamente en su nombre
            if label_fmt not in p_norm:
                return ResultadoCoincidencia(
                    coincide=False,
                    confianza=0.0,
                    motivo=f"Formato excluido detectado: {label_fmt}",
                    formato_invalido=label_fmt,
                    formato_detectado=formato_det,
                )

    # Bloquear combos '+' en el título cuando el perfume buscado no es un combo
    if "+" in tit_raw and "+" not in perfume_nombre:
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo="Formato excluido detectado: pack/combo '+'",
            formato_invalido="combo +",
            formato_detectado=formato_det,
        )

    # 2. Guardia contra Keyword Stuffing de Marketplaces (separadores -, –, —, |, /)
    es_busqueda_disenador = any(
        k in m_norm or any(a == m_norm for a in als)
        for k, als in MARCAS_DISENADOR_PRESTIGIO.items()
    )
    if es_busqueda_disenador and re.search(r"[\-–—|/]", tit_raw):
        partes_sep = [p.strip() for p in re.split(r"[\-–—|/]", tit_raw) if len(p.strip()) >= 3]
        if len(partes_sep) >= 2:
            aliases_propios = _aliases_marca(m_norm)
            p_tokens_check = [w for w in p_norm.split() if len(w) >= 3 and w not in PALABRAS_GENERICAS_NOMBRE]
            primera_norm = _normalizar_texto_match(partes_sep[0])
            ultima_norm = _normalizar_texto_match(partes_sep[-1])

            # Si el perfume/marca buscada solo aparece en el último segmento tras un separador
            # y el primer segmento tiene otra marca/nombre extraño (ej. "VELINNE NAZIRE - TOM FORD TOBACCO VANILLE")
            marca_en_primera = any(re.search(rf"\b{re.escape(a)}\b", primera_norm) for a in aliases_propios)
            nombre_en_primera = any(re.search(rf"\b{re.escape(t)}\b", primera_norm) for t in p_tokens_check)
            marca_o_nombre_en_ultima = (
                any(re.search(rf"\b{re.escape(a)}\b", ultima_norm) for a in aliases_propios)
                or any(re.search(rf"\b{re.escape(t)}\b", ultima_norm) for t in p_tokens_check)
            )
            # Excepción legítima de Falabella/Paris: "VERSACE | Perfume Hombre Eros..." (donde primera_norm ES la marca buscada)
            if not marca_en_primera and not nombre_en_primera and marca_o_nombre_en_ultima:
                # Verificar que primera_norm no sea solo prefijo genérico ("Perfume Hombre", "Eau de Parfum")
                primera_sin_gen = re.sub(
                    r"\b(?:perfume|fragancia|hombre|mujer|unisex|edp|edt|parfum|eau|de|toilette|oferta|tester)\b",
                    "",
                    primera_norm,
                ).strip()
                if len(primera_sin_gen) >= 3:
                    return ResultadoCoincidencia(
                        coincide=False,
                        confianza=0.0,
                        motivo=f"Estructura de clon/keyword stuffing en marketplace ('{partes_sep[0]}' -> '{partes_sep[-1]}')",
                        formato_detectado=formato_det,
                    )

    # 3. Guardia de Casas Clon Dedicadas y Casas Orientales Ajenas sobre Marcas de Prestigio
    if es_busqueda_disenador:
        for casa_clon in CASAS_CLON_DEDICADAS:
            if re.search(rf"\b{re.escape(casa_clon)}\b", combo_text):
                return ResultadoCoincidencia(
                    coincide=False,
                    confianza=0.0,
                    motivo=f"Casa clon detectada ('{casa_clon}') al buscar marca original '{marca}'",
                    marca_detectada=casa_clon,
                    formato_detectado=formato_det,
                )
        for casa_or, als_or in MARCAS_ORIENTALES_RECONOCIDAS.items():
            for al in als_or:
                if re.search(rf"\b{re.escape(al)}\b", combo_text):
                    return ResultadoCoincidencia(
                        coincide=False,
                        confianza=0.0,
                        motivo=f"Casa oriental ajena ('{al}') detectada al buscar '{marca}'",
                        marca_detectada=al,
                        formato_detectado=formato_det,
                    )

        # Si proviene de un vendedor externo de Marketplace que es una casa de equivalencias
        if vendedor:
            vend_norm = _normalizar_texto_match(vendedor)
            for casa_clon in CASAS_CLON_DEDICADAS:
                if casa_clon in vend_norm:
                    return ResultadoCoincidencia(
                        coincide=False,
                        confianza=0.0,
                        motivo=f"Vendedor externo de clones detectado ('{vendedor}')",
                        marca_detectada=vendedor,
                        formato_detectado=formato_det,
                    )

    # 4. Guardia de Conflicto Directo entre Marcas Reconocidas
    if m_norm:
        aliases_esperados = _aliases_marca(m_norm)
        todas_marcas_conocidas: Dict[str, List[str]] = {}
        todas_marcas_conocidas.update(MARCAS_DISENADOR_PRESTIGIO)
        todas_marcas_conocidas.update(MARCAS_ORIENTALES_RECONOCIDAS)

        for otra_key, otros_aliases in todas_marcas_conocidas.items():
            if any(a in aliases_esperados for a in otros_aliases) or otra_key == m_norm:
                continue
            for alias_ajeno in otros_aliases:
                if len(alias_ajeno) <= 3:
                    continue  # Evitar falsos positivos con siglas cortas como 'ch' o 'ck' dentro de palabras
                if re.search(rf"\b{re.escape(alias_ajeno)}\b", combo_text):
                    return ResultadoCoincidencia(
                        coincide=False,
                        confianza=0.0,
                        motivo=f"Conflicto de marca: detectada '{alias_ajeno}', esperada '{marca}'",
                        marca_detectada=alias_ajeno,
                        formato_detectado=formato_det,
                    )

        # Si el nombre del perfume es ultra corto o palabra común ambigua (<= 3 letras como 'Y', 'Si', 'Ch', 'Xs',
        # o adjetivos genéricos como 'Libre', 'Solo', 'Fame', 'Noir', 'Gold'), exigir presencia explícita de la marca.
        tokens_significativos = [
            w for w in p_norm.split()
            if w not in PALABRAS_GENERICAS_NOMBRE and w not in aliases_esperados
        ]
        palabras_ambiguas_sin_marca = {"libre", "solo", "fame", "luna", "halo", "pure", "noir", "gold", "code"}
        nombre_corto = (
            bool(tokens_significativos)
            and (
                len("".join(tokens_significativos)) <= 3
                or (len(tokens_significativos) == 1 and tokens_significativos[0] in palabras_ambiguas_sin_marca)
            )
        )
        if nombre_corto and aliases_esperados:
            if not any(re.search(rf"\b{re.escape(a)}\b", combo_text) for a in aliases_esperados):
                return ResultadoCoincidencia(
                    coincide=False,
                    confianza=0.0,
                    motivo=f"Nombre corto/ambiguo ('{perfume_nombre}') requiere presencia explícita de marca '{marca}'",
                    formato_detectado=formato_det,
                )

    # 5. Extracción de Tokens Nucleares del Nombre del Perfume
    aliases_m = _aliases_marca(m_norm) if m_norm else []
    tokens = []
    for w in p_norm.split():
        if w in PALABRAS_GENERICAS_NOMBRE:
            continue
        if len(w) >= 3 and w in aliases_m and len(p_norm.split()) > 1:
            continue
        tokens.append(w)

    if not tokens:
        tokens = [w for w in p_norm.split() if len(w) >= 1 and w not in PALABRAS_GENERICAS_NOMBRE]

    # 6. Guardia de Flankers No Solicitados (ej. buscar 'Sauvage' y recibir 'Sauvage Elixir' o 'Eros Flame')
    for flanker in FLANKERS_EXCLUSIVOS:
        # 'parfum' suelto no se trata como flanker prohibido cuando solo expresa concentración 'Eau de Parfum'
        if flanker == "parfum":
            continue
        if re.search(rf"\b{re.escape(flanker)}\b", tit):
            en_buscado = re.search(rf"\b{re.escape(flanker)}\b", p_norm) or (
                c_norm and re.search(rf"\b{re.escape(flanker)}\b", c_norm)
            )
            if not en_buscado:
                # Permitir 'oud' o 'rose' o 'vanilla' solo si es parte de la marca buscada
                if flanker in m_norm:
                    continue
                return ResultadoCoincidencia(
                    coincide=False,
                    confianza=0.0,
                    motivo=f"Flanker no solicitado detectado: '{flanker}' ausente en '{perfume_nombre}'",
                    flanker_detectado=flanker,
                    formato_detectado=formato_det,
                )

    # 7. Guardia de Cruce de Género y Líneas Homónimas (ej. Eros vs Eros Pour Femme; Scandal Pour Homme vs Scandal Woman; YSL Libre vs MYSLF/Y)
    #    Todas las comparaciones usan palabra completa para no confundir 'Romance'/'Armani' con 'man'
    #    ni 'Hermès' con 'her'.
    es_femenino_cand, es_masculino_cand = detectar_marcadores_genero(combo_text)
    p_pide_mujer, p_pide_hombre = detectar_marcadores_genero(p_norm)
    if not p_pide_mujer and re.search(r"\b(?:her|elle|mademoiselle)\b", p_norm):
        p_pide_mujer = True

    if p_pide_hombre and es_femenino_cand and not es_masculino_cand:
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo=f"Conflicto de género: '{perfume_nombre}' es masculino pero candidato es femenino",
            formato_detectado=formato_det,
        )
    if p_pide_mujer and es_masculino_cand and not es_femenino_cand:
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo=f"Conflicto de género: '{perfume_nombre}' es femenino pero candidato es masculino",
            formato_detectado=formato_det,
        )
    if "eros" in p_norm.split() and not p_pide_mujer and re.search(r"\b(?:pour femme|femme|woman|mujer)\b", combo_text):
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo="Eros Woman/Pour Femme no coincide con Eros masculino",
            formato_detectado=formato_det,
        )

    # 7b. Guardia de género esperado de la ficha (columna `perfumes.genero`).
    #     El nombre comercial tiene prioridad (ej. 'Light Blue Pour Homme' siempre es masculino);
    #     si el nombre no declara género, se usa el género almacenado de la ficha.
    genero_ficha = None
    if p_pide_mujer and not p_pide_hombre:
        genero_ficha = "Mujer"
    elif p_pide_hombre and not p_pide_mujer:
        genero_ficha = "Hombre"
    else:
        genero_ficha = normalizar_genero(genero_esperado)

    if genero_ficha == "Mujer" and es_masculino_cand and not es_femenino_cand:
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo=f"Conflicto de género: ficha '{perfume_nombre}' es de Mujer pero candidato declara Hombre",
            formato_detectado=formato_det,
        )
    if genero_ficha == "Hombre" and es_femenino_cand and not es_masculino_cand:
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo=f"Conflicto de género: ficha '{perfume_nombre}' es de Hombre pero candidato declara Mujer",
            formato_detectado=formato_det,
        )

    # 8. Presencia Obligatoria de Todos los Tokens Nucleares de la Fragancia
    for tok in tokens:
        if tok == "ysl" and ("yves saint laurent" in combo_text or "saint laurent" in combo_text):
            continue
        if tok in ("sweet", "tooth") and re.search(r"\bsweettooth\b", combo_text):
            continue
        if tok == "dior" and "dior" in m_norm and ("dior" in combo_text):
            continue
        if not re.search(rf"\b{re.escape(tok)}\b", combo_text):
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Token nuclear obligatorio '{tok}' ausente en candidato",
                formato_detectado=formato_det,
            )

    # 9. Guardia de Concentración (EDT vs EDP vs EDC vs Elixir)
    if c_norm:
        es_elixir_p = "elixir" in c_norm or "elixir" in p_norm
        es_edt_p = ("toilette" in c_norm or "edt" in c_norm) and not es_elixir_p
        es_edc_p = ("cologne" in c_norm or "edc" in c_norm or "colonia" in c_norm)
        es_edp_p = ("eau de parfum" in c_norm or "edp" in c_norm) and not es_edt_p and not es_elixir_p

        es_edt_t = bool(re.search(r"\b(?:eau de toilette|toilette|edt)\b", combo_text)) and not bool(
            re.search(r"\b(?:eau de parfum|edp)\b", combo_text)
        )
        es_edp_t = bool(re.search(r"\b(?:eau de parfum|edp)\b", combo_text)) and not bool(
            re.search(r"\b(?:eau de toilette|toilette|edt)\b", combo_text)
        )
        es_edc_t = bool(re.search(r"\b(?:eau de cologne|edc)\b", combo_text))

        if es_edt_p and es_edp_t:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: esperado EDT, candidato es EDP",
                formato_detectado=formato_det,
            )
        if es_edp_p and es_edt_t:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: esperado EDP, candidato es EDT",
                formato_detectado=formato_det,
            )
        if (es_edp_p or es_edt_p) and es_edc_t and not es_edc_p:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: candidato es Eau de Cologne (EDC)",
                formato_detectado=formato_det,
            )

        # Parfum puro / Extrait vs EDP-EDT (ej. 'Sauvage Parfum' nunca es 'Sauvage Eau de Parfum')
        texto_sin_compuestos = re.sub(
            r"\b(?:eau de parfum|extrait de parfum|le parfum|parfums?\s+de\s+\w+)\b", " ", combo_text
        )
        es_parfum_puro_t = bool(re.search(r"\bparfum\b", texto_sin_compuestos)) and not bool(
            re.search(r"\b(?:eau de parfum|edp|eau de toilette|edt)\b", combo_text)
        )
        es_parfum_puro_p = (
            bool(re.search(r"\b(?:parfum|extrait)\b", c_norm))
            and "eau de" not in c_norm
            and not es_elixir_p
        )
        if es_parfum_puro_p and (es_edp_t or es_edt_t):
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: esperado Parfum/Extrait, candidato es EDP/EDT",
                formato_detectado=formato_det,
            )
        if (es_edp_p or es_edt_p) and es_parfum_puro_t and "parfum" not in p_norm:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: candidato es Parfum puro, esperado EDP/EDT",
                formato_detectado=formato_det,
            )

        # Elixir / Intense exigidos por la concentración de la ficha deben estar en el candidato
        if es_elixir_p and not re.search(r"\belixir\b", combo_text):
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: esperado Elixir, candidato no lo declara",
                formato_detectado=formato_det,
            )
        if "intense" in c_norm and not re.search(r"\b(?:intense|intenso)\b", combo_text):
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo="Incompatibilidad de concentración: esperado versión Intense, candidato no lo declara",
                formato_detectado=formato_det,
            )

    # 10. Guardia Universal contra Decants/Viales (<25ml) y Discrepancia de Volumen
    vol_candidato = extraer_volumen_ml(combo_text, default=0)
    # Incluso cuando volumen_esperado es None (búsqueda multi-variante), prohibir decants/viales < 25ml
    if 0 < vol_candidato < 25 and (volumen_esperado is None or volumen_esperado >= 25):
        return ResultadoCoincidencia(
            coincide=False,
            confianza=0.0,
            motivo=f"Candidato es decant/muestra/vial ({vol_candidato}ml < 25ml), incompatible con frasco comercial",
            volumen_detectado=vol_candidato,
            formato_invalido="decant_menor_25ml",
            formato_detectado=formato_det,
        )

    if volumen_esperado:
        if vol_candidato > 0 and abs(vol_candidato - volumen_esperado) > 5:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Discrepancia de volumen: esperado {volumen_esperado}ml, recibido {vol_candidato}ml",
                volumen_detectado=vol_candidato,
                formato_detectado=formato_det,
            )

    # 11. Guardia de Sanidad Comercial de Precio vs Referencia de Mercado (Ajustada por Volumen y Tester)
    if precio_candidato and precio_referencia and precio_referencia >= 65000:
        vol_base = volumen_esperado or (vol_candidato if vol_candidato >= 25 else 100)
        vol_ratio = max(0.42, min(1.5, vol_base / 100.0))
        ref_ajustada = precio_referencia * vol_ratio
        # Los testers legítimos pueden costar algo menos que el retail sellado, pero nunca < 28% del valor oficial
        umbral_min = 0.28 if formato_det == "tester" else 0.35
        if precio_candidato < (umbral_min * ref_ajustada):
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=(
                    f"Precio sospechosamente bajo ({precio_candidato} CLP vs ref {int(ref_ajustada)} CLP): "
                    f"probable clon, decant o accesorio mal etiquetado"
                ),
                volumen_detectado=vol_candidato or volumen_esperado,
                formato_detectado=formato_det,
            )

    return ResultadoCoincidencia(
        coincide=True,
        confianza=0.98,
        motivo="Entidad validada con alta fidelidad",
        marca_detectada=m_canon or marca,
        concentracion_detectada=extraer_concentracion(combo_text),
        volumen_detectado=vol_candidato if vol_candidato > 0 else volumen_esperado,
        formato_detectado=formato_det,
    )


def coincide_con_perfume(
    titulo: str,
    perfume_nombre: str,
    marca: str = "",
    concentracion: str = "",
    volumen_esperado: Optional[int] = None,
    url: str = "",
    precio_candidato: Optional[int] = None,
    precio_referencia: Optional[int] = None,
    formato_esperado: Optional[str] = None,
    vendedor: str = "",
    genero_esperado: Optional[str] = None,
) -> bool:
    """Wrapper retrocompatible que devuelve un booleano para los scrapers y vistas."""
    return coincide_entidad_detallada(
        titulo=titulo,
        perfume_nombre=perfume_nombre,
        marca=marca,
        concentracion=concentracion,
        volumen_esperado=volumen_esperado,
        url=url,
        precio_candidato=precio_candidato,
        precio_referencia=precio_referencia,
        formato_esperado=formato_esperado,
        vendedor=vendedor,
        genero_esperado=genero_esperado,
    ).coincide
