"""
PerfumeTrending.cl — Motor de Normalización y Reconocimiento de Entidades
========================================================================
Módulo de procesamiento de lenguaje natural (NLP) y expresiones regulares
para normalizar títulos, variantes, capacidades (ml) y concentraciones
provenientes de catálogos y APIs de e-commerce (Shopify, retail chileno).
"""

# Importación de librería estándar o dependencia externa (re)
import re
# Importación de componentes (List, Optional, Tuple) desde el módulo 'typing'
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


# Definición de función 'extraer_volumen_ml' (parámetros: texto, default)
def extraer_volumen_ml(texto: str, default: int = 100) -> int:
    """
    Extrae la capacidad en mililitros (ml) a partir de títulos o etiquetas de variantes.
    Soporta conversiones desde onzas fluidas (fl oz).
    
    Ejemplos:
    - 'Sauvage Edp 100 Ml' -> 100
    - '50ml Spray' -> 50
    - '3.4 oz' -> 100
    """
    # Evaluamos la condición lógica (not texto) para controlar el flujo
    if not texto:
        # Retornamos el resultado procesado (default)
        return default

    # 1. Búsqueda explícita de mililitros: 30 ml, 50ml, 100 ml, 200ml
    match_ml = re.search(r'(\d{2,3})\s*(?:ml|m\b)', texto, re.IGNORECASE)
    # Evaluamos la condición lógica (match_ml) para controlar el flujo
    if match_ml:
        # Asignamos 'val' con int(match_ml.group(1))
        val = int(match_ml.group(1))
        # Evaluamos la condición lógica (15 <= val <= 500) para controlar el flujo
        if 15 <= val <= 500:
            # Retornamos el resultado procesado (val)
            return val

    # 2. Búsqueda de onzas fluidas: 3.4 oz (100ml), 1.7 oz (50ml), 6.8 oz (200ml)
    match_oz = re.search(r'(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz|oz)', texto, re.IGNORECASE)
    # Evaluamos la condición lógica (match_oz) para controlar el flujo
    if match_oz:
        # Asignamos 'val_oz' con float(match_oz.group(1))
        val_oz = float(match_oz.group(1))
        # Asignamos 'ml_estimado' con int(round(val_oz * 29.5735))
        ml_estimado = int(round(val_oz * 29.5735))
        # Aproximación a tamaños comerciales estándares
        for estandar in [30, 50, 60, 75, 90, 100, 125, 150, 200]:
            # Evaluamos la condición lógica (abs(ml_estimado - estandar) <= 5) para controlar el flujo
            if abs(ml_estimado - estandar) <= 5:
                # Retornamos el resultado procesado (estandar)
                return estandar
        # Evaluamos la condición lógica (15 <= ml_estimado <= 500) para controlar el flujo
        if 15 <= ml_estimado <= 500:
            # Retornamos el resultado procesado (ml_estimado)
            return ml_estimado

    # Retornamos el resultado procesado (default)
    return default


# Definición de función 'extraer_concentracion' (parámetros: texto)
def extraer_concentracion(texto: str) -> str:
    """
    Extrae y normaliza la concentración olfativa (flanker) del perfume.
    """
    # Asignamos 't' con texto.lower()
    t = texto.lower()
    # Evaluamos la condición lógica ('elixir' in t) para controlar el flujo
    if "elixir" in t:
        # Retornamos el resultado procesado ('Elixir')
        return "Elixir"
    # Evaluamos la condición lógica ('extrait' in t or 'extract' in t) para controlar el flujo
    if "extrait" in t or "extract" in t:
        # Retornamos el resultado procesado ('Extrait de Parfum')
        return "Extrait de Parfum"
    # Evaluamos la condición lógica ('eau de parfum intense' in t or 'edp intense' in t) para controlar el flujo
    if "eau de parfum intense" in t or "edp intense" in t:
        # Retornamos el resultado procesado ('Eau de Parfum Intense')
        return "Eau de Parfum Intense"
    # Evaluamos la condición lógica ('eau de parfum' in t or ' edp' in t or '(edp)' in t) para controlar el flujo
    if "eau de parfum" in t or " edp" in t or "(edp)" in t:
        # Retornamos el resultado procesado ('Eau de Parfum')
        return "Eau de Parfum"
    # Evaluamos la condición lógica ('eau de toilette intense' in t or 'edt intense' in t) para controlar el flujo
    if "eau de toilette intense" in t or "edt intense" in t:
        # Retornamos el resultado procesado ('Eau de Toilette Intense')
        return "Eau de Toilette Intense"
    # Evaluamos la condición lógica ('eau de toilette' in t or ' edt' in t or '(edt)' in t) para controlar el flujo
    if "eau de toilette" in t or " edt" in t or "(edt)" in t:
        # Retornamos el resultado procesado ('Eau de Toilette')
        return "Eau de Toilette"
    # Evaluamos la condición lógica ('eau de cologne' in t or ' edc' in t or 'colonia' in t) para controlar el flujo
    if "eau de cologne" in t or " edc" in t or "colonia" in t:
        # Retornamos el resultado procesado ('Eau de Cologne')
        return "Eau de Cologne"
    # Evaluamos la condición lógica ('parfum' in t) para controlar el flujo
    if "parfum" in t:
        # Retornamos el resultado procesado ('Parfum')
        return "Parfum"
    # Retornamos el resultado procesado ('Eau de Parfum')
    return "Eau de Parfum"


# Definición de función 'extraer_genero' (parámetros: texto)
def extraer_genero(texto: str) -> str:
    """
    Determina el género sugerido del perfume a partir del texto del producto.
    """
    # Asignamos 't' con texto.lower()
    t = texto.lower()
    # Evaluamos la condición lógica (any((k in t for k in ['pour femme', 'mujer', 'women'...) para controlar el flujo
    if any(k in t for k in ["pour femme", "mujer", "women", "woman", "dama", "femenino"]):
        # Retornamos el resultado procesado ('Mujer')
        return "Mujer"
    # Evaluamos la condición lógica (any((k in t for k in ['pour homme', 'hombre', 'men',...) para controlar el flujo
    if any(k in t for k in ["pour homme", "hombre", "men", "man", "caballero", "masculino"]):
        # Retornamos el resultado procesado ('Hombre')
        return "Hombre"
    # Retornamos el resultado procesado ('Unisex')
    return "Unisex"


# Definición de función 'es_arabe' (parámetros: marca, nombre)
def es_arabe(marca: str, nombre: str = "") -> bool:
    """
    Indica si el perfume o la marca pertenece a la perfumería árabe/oriental.
    """
    # Asignamos 'texto' con f'{marca} {nombre}'.lower()
    texto = f"{marca} {nombre}".lower()
    # Retornamos el resultado procesado (any((m in texto for m in MARCAS_ARABES_CONOCIDA...)
    return any(m in texto for m in MARCAS_ARABES_CONOCIDAS) or any(
        k in texto for k in ["khamrah", "asad", "club de nuit", "hawas", "fakhar", "yara", "bade'e al oud"]
    )


# Definición de función 'es_producto_perfume_valido' (parámetros: titulo, tags)
def es_producto_perfume_valido(titulo: str, tags: Optional[List[str]] = None) -> bool:
    """
    Filtra y descarta productos no relacionados (accesorios, cremas, desodorantes).
    """
    # Asignamos 't' con titulo.lower()
    t = titulo.lower()
    # Recorremos iterativamente cada 'palabra' en PALABRAS_EXCLUSION
    for palabra in PALABRAS_EXCLUSION:
        # Evaluamos la condición lógica (palabra in t) para controlar el flujo
        if palabra in t:
            # Retornamos el resultado procesado (False)
            return False

    # Evaluamos la condición lógica (tags) para controlar el flujo
    if tags:
        # Asignamos 'tags_str' con ' '.join(tags).lower()
        tags_str = " ".join(tags).lower()
        # Recorremos iterativamente cada 'palabra' en PALABRAS_EXCLUSION
        for palabra in PALABRAS_EXCLUSION:
            # Evaluamos la condición lógica (palabra in tags_str) para controlar el flujo
            if palabra in tags_str:
                # Retornamos el resultado procesado (False)
                return False

    # Retornamos el resultado procesado (True)
    return True


# Definición de función 'limpiar_nombre_perfume' (parámetros: titulo, marca)
def limpiar_nombre_perfume(titulo: str, marca: str = "") -> str:
    """
    Remueve el ruido comercial habitual de títulos de e-commerce:
    'Perfume Lattafa Khamrah Unisex Edp 100 Ml Oferta' -> 'Khamrah'
    """
    # Asignamos 'limpio' con titulo
    limpio = titulo

    # 1. Remover prefijos genéricos
    limpio = re.sub(r'^(?:perfume|fragancia|colonia)\s+', '', limpio, flags=re.IGNORECASE)

    # 2. Remover marca si aparece al inicio
    if marca:
        # Asignamos 'pattern_marca' con f'^{re.escape(marca)}\\s+'
        pattern_marca = rf'^{re.escape(marca)}\s+'
        # Asignamos 'limpio' con re.sub(pattern_marca, '', limpio, flags=re...
        limpio = re.sub(pattern_marca, '', limpio, flags=re.IGNORECASE)

    # 3. Remover mililitros: 100ml, 50 ml, 3.4 oz
    limpio = re.sub(r'\b\d{2,3}\s*(?:ml|m)\b', '', limpio, flags=re.IGNORECASE)
    # Asignamos 'limpio' con re.sub('\\b\\d+(?:\\.\\d+)?\\s*(?:fl\\.?\\...
    limpio = re.sub(r'\b\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|oz)\b', '', limpio, flags=re.IGNORECASE)

    # 4. Remover concentraciones comunes del nombre principal (se guardan en campo 'tipo')
    limpio = re.sub(r'\b(?:eau de parfum|eau de toilette|edp|edt|edc|elixir|parfum)\b', '', limpio, flags=re.IGNORECASE)

    # 5. Remover ruido de e-commerce
    ruidos = [
        "tester", "vaporizador", "spray", "nuevo", "original", "oferta", "despacho", "sellado",
        "hombre", "mujer", "unisex", "pour homme", "pour femme", "set", "estuche", "lujo",
        "intense", "extreme"
    ]
    # Recorremos iterativamente cada 'r' en ruidos
    for r in ruidos:
        # Asignamos 'limpio' con re.sub(f'\\b{r}\\b', '', limpio, flags=re....
        limpio = re.sub(rf'\b{r}\b', '', limpio, flags=re.IGNORECASE)

    # 6. Limpieza de caracteres residuales, puntuaciones y espacios dobles
    limpio = re.sub(r'[-–—/|()\[\]:]', ' ', limpio)
    # Asignamos 'limpio' con re.sub('\\s+', ' ', limpio).strip()
    limpio = re.sub(r'\s+', ' ', limpio).strip()

    # Si quedó vacío o muy corto, retornar el título limpio básico
    if len(limpio) < 2:
        # Asignamos 'limpio' con titulo.split('-')[0].strip()
        limpio = titulo.split("-")[0].strip()

    # Formatear a Title Case
    return limpio.title()
