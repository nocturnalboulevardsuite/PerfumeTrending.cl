"""
PerfumeTrending.cl — Motor de Normalización y Reconocimiento de Entidades
========================================================================
Módulo de procesamiento de lenguaje natural (NLP) y expresiones regulares
para normalizar títulos, variantes, capacidades (ml) y concentraciones
provenientes de catálogos y APIs de e-commerce (Shopify, retail chileno).
"""

import re
from typing import List, Optional, Tuple

# Casas de perfumería oriental / árabe populares en Chile
MARCAS_ARABES_CONOCIDAS = {
    "lattafa", "armaf", "afnan", "rasasi", "al haramain", "orientica",
    "swiss arabian", "maison alhambra", "alhambra", "fragrance world", "paris corner"
}

# Palabras clave de productos no deseados (desodorantes, cremas, etc.)
PALABRAS_EXCLUSION = [
    "desodorante", "deodorant", "body mist", "body spray", "body lotion",
    "crema corporal", "locion corporal", "shampoo", "champu", "gel de ducha",
    "shower gel", "jabon", "vela", "after shave", "after-shave", "balsamo",
    "neceser", "estuche vacio", "atomizador recargable", "labial", "mascara pestañas"
]


def extraer_volumen_ml(texto: str, default: int = 100) -> int:
    """
    Extrae la capacidad en mililitros (ml) a partir de títulos o etiquetas de variantes.
    Soporta conversiones desde onzas fluidas (fl oz).
    
    Ejemplos:
    - 'Sauvage Edp 100 Ml' -> 100
    - '50ml Spray' -> 50
    - '3.4 oz' -> 100
    """
    if not texto:
        return default

    # 1. Búsqueda explícita de mililitros: 30 ml, 50ml, 100 ml, 200ml
    match_ml = re.search(r'(\d{2,3})\s*(?:ml|m\b)', texto, re.IGNORECASE)
    if match_ml:
        val = int(match_ml.group(1))
        if 15 <= val <= 500:
            return val

    # 2. Búsqueda de onzas fluidas: 3.4 oz (100ml), 1.7 oz (50ml), 6.8 oz (200ml)
    match_oz = re.search(r'(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz|oz)', texto, re.IGNORECASE)
    if match_oz:
        val_oz = float(match_oz.group(1))
        ml_estimado = int(round(val_oz * 29.5735))
        # Aproximación a tamaños comerciales estándares
        for estandar in [30, 50, 60, 75, 90, 100, 125, 150, 200]:
            if abs(ml_estimado - estandar) <= 5:
                return estandar
        if 15 <= ml_estimado <= 500:
            return ml_estimado

    return default


def extraer_concentracion(texto: str) -> str:
    """
    Extrae y normaliza la concentración olfativa (flanker) del perfume.
    """
    t = texto.lower()
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
    return "Eau de Parfum"


def extraer_genero(texto: str) -> str:
    """
    Determina el género sugerido del perfume a partir del texto del producto.
    """
    t = texto.lower()
    if any(k in t for k in ["pour femme", "mujer", "women", "woman", "dama", "femenino"]):
        return "Mujer"
    if any(k in t for k in ["pour homme", "hombre", "men", "man", "caballero", "masculino"]):
        return "Hombre"
    return "Unisex"


def es_arabe(marca: str, nombre: str = "") -> bool:
    """
    Indica si el perfume o la marca pertenece a la perfumería árabe/oriental.
    """
    texto = f"{marca} {nombre}".lower()
    return any(m in texto for m in MARCAS_ARABES_CONOCIDAS) or any(
        k in texto for k in ["khamrah", "asad", "club de nuit", "hawas", "fakhar", "yara", "bade'e al oud"]
    )


def es_producto_perfume_valido(titulo: str, tags: Optional[List[str]] = None) -> bool:
    """
    Filtra y descarta productos no relacionados (accesorios, cremas, desodorantes).
    """
    t = titulo.lower()
    for palabra in PALABRAS_EXCLUSION:
        if palabra in t:
            return False

    if tags:
        tags_str = " ".join(tags).lower()
        for palabra in PALABRAS_EXCLUSION:
            if palabra in tags_str:
                return False

    return True


def limpiar_nombre_perfume(titulo: str, marca: str = "") -> str:
    """
    Remueve el ruido comercial habitual de títulos de e-commerce:
    'Perfume Lattafa Khamrah Unisex Edp 100 Ml Oferta' -> 'Khamrah'
    """
    limpio = titulo

    # 1. Remover prefijos genéricos
    limpio = re.sub(r'^(?:perfume|fragancia|colonia)\s+', '', limpio, flags=re.IGNORECASE)

    # 2. Remover marca si aparece al inicio
    if marca:
        pattern_marca = rf'^{re.escape(marca)}\s+'
        limpio = re.sub(pattern_marca, '', limpio, flags=re.IGNORECASE)

    # 3. Remover mililitros: 100ml, 50 ml, 3.4 oz
    limpio = re.sub(r'\b\d{2,3}\s*(?:ml|m)\b', '', limpio, flags=re.IGNORECASE)
    limpio = re.sub(r'\b\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|oz)\b', '', limpio, flags=re.IGNORECASE)

    # 4. Remover concentraciones comunes del nombre principal (se guardan en campo 'tipo')
    limpio = re.sub(r'\b(?:eau de parfum|eau de toilette|edp|edt|edc|elixir|parfum)\b', '', limpio, flags=re.IGNORECASE)

    # 5. Remover ruido de e-commerce
    ruidos = [
        "tester", "vaporizador", "spray", "nuevo", "original", "oferta", "despacho", "sellado",
        "hombre", "mujer", "unisex", "pour homme", "pour femme", "set", "estuche", "lujo",
        "intense", "extreme"
    ]
    for r in ruidos:
        limpio = re.sub(rf'\b{r}\b', '', limpio, flags=re.IGNORECASE)

    # 6. Limpieza de caracteres residuales, puntuaciones y espacios dobles
    limpio = re.sub(r'[-–—/|()\[\]:]', ' ', limpio)
    limpio = re.sub(r'\s+', ' ', limpio).strip()

    # Si quedó vacío o muy corto, retornar el título limpio básico
    if len(limpio) < 2:
        limpio = titulo.split("-")[0].strip()

    # Formatear a Title Case
    return limpio.title()
