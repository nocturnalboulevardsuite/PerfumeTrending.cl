"""
PerfumeTrending.cl — Motor de Normalización y Reconocimiento de Entidades
========================================================================
Módulo especializado en procesamiento de texto, heurísticas y expresiones regulares
para la estandarización de metadatos de perfumes provenientes de catálogos y tiendas online:
- Extracción de volumen en mililitros (ml) y conversión desde onzas fluidas (fl oz).
- Detección y clasificación de concentración olfativa (EDP, EDT, Parfum, Elixir, etc.).
- Clasificación de género objetivo (Hombre, Mujer, Unisex).
- Identificación de perfumería oriental/árabe.
- Filtrado y descarte de productos no relacionados (desodorantes, cremas, estuches vacíos).
- Limpieza de títulos de e-commerce para obtener nombres canónicos y limpios.
"""

import re
from typing import Any, List, Optional, Tuple, Union

# =============================================================================
# CONSTANTES Y LISTAS DE CONTROL
# =============================================================================

# Casas de perfumería oriental / árabe populares en el mercado chileno
# Utilizadas para clasificar automáticamente perfumes árabes de alta demanda (tendencia Hype)
MARCAS_ARABES_CONOCIDAS = {
    "lattafa", "armaf", "afnan", "rasasi", "al haramain", "orientica",
    "swiss arabian", "maison alhambra", "alhambra", "fragrance world", "paris corner"
}

# Palabras clave de productos derivados o accesorios que deben excluirse
# Evita que el comparador mezcle perfumes reales con desodorantes, cremas o estuches
PALABRAS_EXCLUSION = [
    "desodorante", "deodorant", "body mist", "bodymist", "body spray", "bodyspray",
    "body splash", "bodysplash", "body lotion", "crema corporal", "locion corporal",
    "locion para despues", "loción para después", "después del afeitado", "despues del afeitado",
    "shampoo", "champu", "gel de ducha", "shower gel", "jabon", "vela", "after shave",
    "after-shave", "aftershave", "balsamo", "neceser", "estuche vacio", "atomizador recargable",
    "labial", "mascara pestañas", "roll on", "roll-on", "cuidado del cabello", "tratamiento hidratante",
    "twist and spray", "twist & spray",
    # Imitaciones, clones y equivalencias de baja fidelidad
    "inspirado en", "inspirada en", "inspiracion", "inspiración", "tipo ", "dupe",
    "equivalencia", "imitacion", "imitación", "clon"
]


# =============================================================================
# FUNCIONES DE EXTRACCIÓN Y NORMALIZACIÓN
# =============================================================================

def extraer_volumen_ml(texto: str, default: int = 100) -> int:
    """
    Extrae la capacidad en mililitros (ml) a partir del título o la etiqueta de la variante.
    Soporta conversiones automáticas desde onzas fluidas (fl oz) a presentaciones estándar.
    
    Args:
        texto (str): Cadena de texto donde se buscará la medida (ej: 'Sauvage Edp 100 Ml').
        default (int, opcional): Valor de fallback si no se detecta volumen. Por defecto 100.
        
    Returns:
        int: Capacidad estimada en mililitros dentro del rango comercial (15 a 500 ml).
        
    Ejemplos:
        >>> extraer_volumen_ml("Dior Sauvage EDP 100 ml")
        100
        >>> extraer_volumen_ml("Bleu de Chanel 3.4 oz")
        100
        >>> extraer_volumen_ml("Eros Flame 50ml Spray")
        50
    """
    if not texto:
        return default

    # 1. Búsqueda explícita de mililitros con regex: '100 ml', '50ml', '200ml'
    match_ml = re.search(r'(\d{2,3})\s*(?:ml|m\b)', texto, re.IGNORECASE)
    if match_ml:
        val = int(match_ml.group(1))
        # Validar que el volumen esté dentro del rango comercial realista de perfumes
        if 15 <= val <= 500:
            return val

    # 2. Búsqueda de onzas fluidas: '3.4 oz' (100ml), '1.7 oz' (50ml), '6.8 oz' (200ml)
    match_oz = re.search(r'(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz|oz)', texto, re.IGNORECASE)
    if match_oz:
        val_oz = float(match_oz.group(1))
        # Factor de conversión estándar internacional: 1 fl oz ≈ 29.5735 ml
        ml_estimado = int(round(val_oz * 29.5735))
        
        # Ajuste por aproximación a tamaños comerciales universales
        for estandar in [30, 50, 60, 75, 90, 100, 125, 150, 200]:
            if abs(ml_estimado - estandar) <= 5:
                return estandar
                
        if 15 <= ml_estimado <= 500:
            return ml_estimado

    # Si no se detectó ningún patrón numérico reconocible, retorna el valor por defecto
    return default


def extraer_concentracion(texto: str) -> str:
    """
    Identifica y normaliza la concentración olfativa (flanker / formulación) del perfume.
    
    Args:
        texto (str): Título, subtítulo o descripción del perfume.
        
    Returns:
        str: Nombre canónico de la concentración (ej: 'Eau de Parfum', 'Eau de Toilette', 'Elixir').
    """
    t = texto.lower()
    
    # Evaluación en orden de especificidad (los más específicos primero)
    if "elixir" in t:
        return "Elixir"
    if "extrait" in t or "extract" in t:
        return "Extrait de Parfum"
    if "eau de parfum intense" in t or "edp intense" in t:
        return "Eau de Parfum Intense"
    if "eau de parfum" in t or " edp" in t or "(edp)" in t:
        return "Eau de Parfum"
    if "eau de toilette intense" in t or "edt intense" in t:
        return "Eau de Toilette Intense"
    if "eau de toilette" in t or " edt" in t or "(edt)" in t:
        return "Eau de Toilette"
    if "eau de cologne" in t or " edc" in t or "colonia" in t:
        return "Eau de Cologne"
    if "parfum" in t:
        return "Parfum"
        
    # Concentración estándar por defecto si no se especifica explícitamente
    return "Eau de Parfum"


def extraer_genero(texto: str) -> str:
    """
    Determina el género o público objetivo del perfume a partir del texto del producto.
    
    Args:
        texto (str): Texto donde buscar marcadores de género en español, inglés o francés.
        
    Returns:
        str: Género canónico: 'Mujer', 'Hombre' o 'Unisex'.
    """
    t = texto.lower()
    if any(k in t for k in ["pour femme", "mujer", "women", "woman", "dama", "femenino"]):
        return "Mujer"
    if any(k in t for k in ["pour homme", "hombre", "men", "man", "caballero", "masculino"]):
        return "Hombre"
    return "Unisex"


def es_arabe(marca: str, nombre: str = "") -> bool:
    """
    Indica si una fragancia pertenece a la categoría de perfumería oriental / árabe,
    analizando tanto la marca como líneas de fragancias populares de Medio Oriente.
    
    Args:
        marca (str): Marca del perfume (ej: 'Lattafa', 'Armaf').
        nombre (str, opcional): Nombre del producto (ej: 'Khamrah', 'Club de Nuit').
        
    Returns:
        bool: True si coincide con marcas o líneas árabes populares, False de lo contrario.
    """
    texto = f"{marca} {nombre}".lower()
    # Coincidencia con marcas árabes conocidas
    if any(m in texto for m in MARCAS_ARABES_CONOCIDAS):
        return True
        
    # Coincidencia con líneas icónicas reconocidas internacionalmente
    lineas_iconicas = ["khamrah", "asad", "club de nuit", "hawas", "fakhar", "yara", "bade'e al oud"]
    return any(k in texto for k in lineas_iconicas)


def es_precio_valido(precio: Optional[Any]) -> bool:
    """
    Validador de sanidad comercial para precios de perfumes en CLP (pesos chilenos).
    
    Descarta:
    - Precios nulos, vacíos o no numéricos.
    - Precios menores a $8.000 CLP (generalmente muestras de 1ml, decants no oficiales o errores).
    - Precios iguales o mayores a $1.000.000 CLP (valores atípicos fuera de escala comercial retail).
    - Placeholders de comercio electrónico como $9.999.999 o $9.999.990 (utilizados por tiendas
      como Yauras Perfumes para productos agotados o preventas cerradas).
    """
    if precio is None:
        return False
    try:
        p = int(round(float(precio)))
    except (ValueError, TypeError):
        return False

    if p < 4000:
        return False
    if p >= 1000000:
        return False
    if p in (9999999, 9999990, 999999):
        return False
    return True


def es_producto_perfume_valido(titulo: str, tags: Optional[List[str]] = None) -> bool:
    """
    Validador de integridad: filtra y descarta productos no relacionados (accesorios,
    cosmética, cremas, desodorantes corporales) que a veces devuelven las APIs de tiendas.
    
    Args:
        titulo (str): Título del producto en la tienda.
        tags (List[str], opcional): Lista de etiquetas del producto (común en Shopify).
        
    Returns:
        bool: True si el producto es un perfume legítimo; False si contiene palabras excluidas.
    """
    t = titulo.lower()
    # 1. Validar contra el título principal
    for palabra in PALABRAS_EXCLUSION:
        if palabra in t:
            return False

    # 2. Validar contra etiquetas / tags si están presentes
    if tags:
        tags_str = " ".join(tags).lower()
        for palabra in PALABRAS_EXCLUSION:
            if palabra in tags_str:
                return False

    return True


def limpiar_nombre_perfume(titulo: str, marca: str = "") -> str:
    """
    Limpia y estandariza el título comercial de un e-commerce para obtener el nombre canónico:
    Transforma cadenas sobrecargadas de marketing como:
    'Perfume Lattafa Khamrah Unisex Edp 100 Ml Oferta Envio Gratis' -> 'Khamrah'
    
    Args:
        titulo (str): Título en bruto extraído del HTML o JSON del comercio.
        marca (str, opcional): Nombre de la marca para su remoción si aparece como prefijo redundante.
        
    Returns:
        str: Nombre limpio formateado en Title Case.
    """
    limpio = titulo

    # 1. Remover prefijos genéricos de comercio
    limpio = re.sub(r'^(?:perfume|fragancia|colonia)\s+', '', limpio, flags=re.IGNORECASE)

    # 2. Remover marca si aparece al inicio para no duplicarla
    if marca:
        pattern_marca = rf'^{re.escape(marca)}\s+'
        limpio = re.sub(pattern_marca, '', limpio, flags=re.IGNORECASE)

    # 3. Remover especificaciones de mililitros y onzas
    limpio = re.sub(r'\b\d{2,3}\s*(?:ml|m)\b', '', limpio, flags=re.IGNORECASE)
    limpio = re.sub(r'\b\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|oz)\b', '', limpio, flags=re.IGNORECASE)

    # 4. Remover concentraciones comunes (estas se almacenan en su propio campo 'tipo' o 'concentracion')
    limpio = re.sub(r'\b(?:eau de parfum|eau de toilette|edp|edt|edc|elixir|parfum)\b', '', limpio, flags=re.IGNORECASE)

    # 5. Remover ruido publicitario típico de e-commerce
    ruidos = [
        "tester", "vaporizador", "spray", "nuevo", "original", "oferta", "despacho", "sellado",
        "hombre", "mujer", "unisex", "pour homme", "pour femme", "set", "estuche", "lujo",
        "intense", "extreme"
    ]
    for r in ruidos:
        limpio = re.sub(rf'\b{r}\b', '', limpio, flags=re.IGNORECASE)

    # 6. Remover sufijos de género aislados de catálogos e-commerce (ej: ' H', ' M', ' U')
    limpio = re.sub(r'\s+[hmuHMU]\b', '', limpio)

    # 7. Limpieza de caracteres residuales, puntuaciones y espacios múltiples
    limpio = re.sub(r'[-–—/|()\[\]:]', ' ', limpio)
    limpio = re.sub(r'\s+', ' ', limpio).strip()

    # Si la limpieza dejó el texto vacío o demasiado corto (< 2 caracteres), fallback al nombre base
    if len(limpio) < 2:
        limpio = titulo.split("-")[0].strip()

    # Formatear el resultado final a formato Capitalizado (Title Case)
    return limpio.title()


MARCAS_CONOCIDAS_INTEGRIDAD = {
    "chanel", "dior", "versace", "givenchy", "gaultier", "jean paul gaultier",
    "armani", "giorgio armani", "carolina herrera", "paco rabanne", "rabanne",
    "tom ford", "yves saint laurent", "saint laurent", "ysl", "creed",
    "parfums de marly", "xerjoff", "maison francis kurkdjian", "kurkdjian", "mfk",
    "azzaro", "dolce & gabbana", "dolce gabbana", "d&g", "calvin klein", "ck",
    "hugo boss", "boss", "moschino", "valentino", "prada", "montblanc", "mont blanc",
    "burberry", "gucci", "bvlgari", "bulgari", "narciso rodriguez", "hermes", "hermès",
    "mugler", "thierry mugler", "loewe", "kenzo", "issey miyake", "lancome", "lancôme",
    "guerlain", "ralph lauren", "antonio banderas", "benetton", "guess", "nike",
    "rihanna", "ariana grande", "sabrina carpenter", "tous", "lattafa", "armaf",
    "afnan", "rasasi", "al haramain", "orientica", "swiss arabian"
}

MARCAS_CLONES_DUPE = {
    "fragrance world", "maison alhambra", "alhambra", "paris corner", "la french",
    "french avenue", "barakkat", "orientica", "zimaya"
}

KNOWN_FLANKERS = [
    # Cítricos / Frescos / Deportes
    "energy", "sport", "cologne", "fraiche", "fresh", "freeze", "ice",
    # Intensos / Fuego / Noche / Oscuros
    "flame", "intense", "intensely", "absolutely", "extreme", "noir", "black", "night", "nuit", "dark",
    # Maderas / Oud / Ámbar
    "oud", "amber", "leather", "tobacco",
    # Acuáticos / Profundos
    "profondo", "profumo", "absolu", "ocean", "deep",
    # Metales / Joyas / Colores
    "rouge", "white", "blanche", "gold", "silver", "cobalt", "coral", "crystal", "bright", "pink",
    # Ediciones de concentración superior o flankers icónicos
    "elixir", "ultra", "lucky", "prive", "privé", "royal", "victory", "legend",
    "platinum", "forever", "summer", "lover", "hero", "blush", "sparkling",
    "dazzling", "najim", "gioia", "barakkat"
]


def coincide_con_perfume(titulo: str, perfume_nombre: str, marca: str = "", concentracion: str = "") -> bool:
    """
    Verifica con alta fidelidad e integridad si el título de un producto de e-commerce corresponde a la fragancia.
    
    Capacidades de Integridad:
    1. Descarte inmediato de imitaciones, dupes y equivalencias ('inspirado en', 'tipo', etc.).
    2. Integridad de Marca:
       - Si el perfume buscado es de una casa original, descarta productos de casas clon (Fragrance World, Barakkat, etc.).
       - En títulos estructurados ('MARCA | Producto' o 'MARCA - Producto'), exige que el prefijo sea compatible con la marca buscada.
       - Si el título menciona explícitamente otra marca mayor conocida (ej: Givenchy buscando Maison Francis Kurkdjian), descarta.
    3. Guardia de Flankers: si el título contiene un flanker conocido (ej: 'energy', 'flame', 'profondo', 'rouge') que no pertenece al perfume canónico, descarta.
    4. Guardia de Género / Variantes: descarta 'Eros Woman' o 'Eros Pour Femme' si se busca el 'Eros' clásico masculino.
    5. Coherencia de Concentración: evita cruces incompatibles (EDP vs EDT) cuando está especificado.
    6. Verificación de Tokens: exige que todos los tokens significativos del nombre del perfume estén presentes.
    """
    tit = titulo.lower()
    p_lower = perfume_nombre.lower()
    m_lower = marca.lower().strip() if marca else ""
    c_lower = concentracion.lower().strip() if concentracion else ""

    # 0. Descarte inmediato de imitaciones, dupes o equivalencias
    if re.search(r"\b(inspirad[oa]\s+en|imitaci[oó]n|equivalencia|tipo\s+|dupe)\b", tit):
        return False

    # 1. Validación estricta de Marca (Brand Integrity)
    if m_lower:
        # A. Si la marca buscada NO es una casa de clones, pero el título contiene una marca clon -> descartar
        es_marca_clon = any(clon in m_lower for clon in MARCAS_CLONES_DUPE)
        if not es_marca_clon:
            if any(re.search(rf"\b{re.escape(clon)}\b", tit) for clon in MARCAS_CLONES_DUPE):
                return False

        # B. Títulos estructurados con delimitador (ej: 'GIVENCHY | Perfume Mujer L'Interdit...')
        if "|" in titulo:
            prefix_marca = titulo.split("|")[0].strip().lower()
            for k_brand in MARCAS_CONOCIDAS_INTEGRIDAD:
                if re.search(rf"\b{re.escape(k_brand)}\b", prefix_marca):
                    if not (k_brand in m_lower or m_lower in k_brand or k_brand in p_lower):
                        return False

        # C. Conflicto con marcas reconocidas incompatibles en el título
        for k_brand in MARCAS_CONOCIDAS_INTEGRIDAD:
            if len(k_brand) >= 4 and re.search(rf"\b{re.escape(k_brand)}\b", tit):
                if not (k_brand in m_lower or m_lower in k_brand or k_brand in p_lower):
                    return False

    # 2. Guardia de concentración (evitar emparejar EDT si buscamos EDP, o viceversa)
    if c_lower:
        if ("parfum" in c_lower or "edp" in c_lower) and not ("toilette" in c_lower or "edt" in c_lower):
            if ("toilette" in tit or "edt" in tit) and not ("eau de parfum" in tit or "edp" in tit):
                return False
        elif ("toilette" in c_lower or "edt" in c_lower) and not ("parfum" in c_lower or "edp" in c_lower):
            if ("eau de parfum" in tit or "edp" in tit) and not ("toilette" in tit or "edt" in tit):
                return False

    # 3. Guardia de Flankers: si el título contiene un flanker que NO está en el nombre del perfume, descartar
    for fl in KNOWN_FLANKERS:
        if fl == "parfum" and "eau de parfum" in tit:
            continue
        if re.search(rf"\b{re.escape(fl)}\b", tit) and fl not in p_lower:
            return False

    # 4. Guardia de Género / Variantes ('Woman', 'Pour Femme')
    if re.search(rf"\b{re.escape(p_lower)}\s+(?:woman|femme|pour femme)\b", tit):
        if not re.search(r"\b(woman|women|femme|mujer|dama|donna)\b", p_lower):
            return False

    # 5. Tokens significativos del perfume
    t_clean = re.sub(r"[^\w\s]", " ", perfume_nombre).lower()
    stop_words = {
        "de", "la", "el", "los", "las", "en", "pour", "for", "men", "women",
        "homme", "femme", "eau", "parfum", "toilette", "edp", "edt", "unisex"
    }
    tokens = [t for t in t_clean.split() if t not in stop_words]
    if not tokens:
        tokens = [t for t in t_clean.split()]

    for tok in tokens:
        if tok.isdigit() or len(tok) <= 2:
            if tok not in tit:
                return False
        else:
            if not re.search(rf"\b{re.escape(tok)}\b", tit):
                return False

    return True
