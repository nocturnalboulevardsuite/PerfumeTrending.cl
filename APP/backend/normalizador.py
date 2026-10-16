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

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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


# =============================================================================
# BLOQUE: MOTOR DE RESOLUCIÓN DETERMINISTA DE ENTIDADES (ENTITY RESOLUTION)
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


# Casas dedicadas de clones, dupes y equivalencias (mercado global y local)
CASAS_CLON_DEDICADAS: Set[str] = {
    "fragrance world", "maison alhambra", "alhambra", "paris corner", "la french",
    "french avenue", "barakkat", "orientica", "zimaya", "emper", "milestone",
    "camara", "dumont", "flavia", "sterling", "pendora", "pendora scents",
    "khalis", "ard al zaafaran", "al zaafaran", "my perfumes", "paris riviera",
    "georges mezotti", "creation lamis", "dorall collection", "shirley may"
}

# Marcas de prestigio / diseñador internacional reconocidas
MARCAS_DISENADOR_PRESTIGIO: Dict[str, List[str]] = {
    "christian dior": ["dior", "christian dior"],
    "chanel": ["chanel"],
    "versace": ["versace"],
    "jean paul gaultier": ["jean paul gaultier", "gaultier", "jpg"],
    "giorgio armani": ["giorgio armani", "armani"],
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
    "tous": ["tous"]
}

# Casas orientales legítimas de alta gama y hype
MARCAS_ORIENTALES_RECONOCIDAS: Dict[str, List[str]] = {
    "lattafa": ["lattafa"],
    "armaf": ["armaf"],
    "afnan": ["afnan"],
    "rasasi": ["rasasi"],
    "al haramain": ["al haramain", "al-haramain", "haramain"],
    "swiss arabian": ["swiss arabian"]
}

# Patrones de formatos y accesorios excluidos (evita asociar recargas o kits)
FORMATOS_EXCLUIDOS: List[Tuple[str, str]] = [
    (r"\b(recarga|recargable|refill|refillable|recharge)\b", "Recarga / Refill"),
    (r"\b(set|estuche|cofre|gift\s*set|travel\s*set|pack\s*\+\s*)\b", "Set / Estuche"),
    (r"\b(desodorante|deodorant|roll\s*on|roll-on)\b", "Desodorante"),
    (r"\b(body\s*spray|bodyspray|body\s*mist|bodymist|body\s*splash|hair\s*mist)\b", "Body / Hair Mist"),
    (r"\b(after\s*shave|after-shave|aftershave|balsamo|balm)\b", "After Shave"),
    (r"\b(shower\s*gel|gel\s*de\s*ducha|shampoo|champu|jabon|jabón|soap|locion\s*corporal|body\s*lotion|crema)\b", "Baño / Cuidado Corporal"),
    (r"\b(decant|muestra|sample|vial)\b", "Muestra / Decant"),
    (r"\b(inspirad[oa]\s+en|imitaci[oó]n|equivalencia|tipo\s+|dupe)\b", "Imitación / Dupe explícito"),
]

# Mapa de flankers conocidos y sus variantes de escritura
FLANKERS_MAP: Dict[str, List[str]] = {
    "elixir": [r"\belixir\b", r"\bl'elixir\b"],
    "flame": [r"\bflame\b"],
    "energy": [r"\benergy\b"],
    "lucky": [r"\blucky\b"],
    "royal": [r"\broyal\b"],
    "prive": [r"\bprive\b", r"\bprivé\b"],
    "profondo": [r"\bprofondo\b"],
    "profumo": [r"\bprofumo\b"],
    "absolu": [r"\babsolu\b", r"\babsolute\b", r"\babsolue\b"],
    "intense": [r"\bintense\b", r"\bintensely\b", r"\bintenso\b"],
    "extreme": [r"\bextreme\b", r"\bextremo\b"],
    "noir": [r"\bnoir\b", r"\bblack\b", r"\bnight\b", r"\bnuit\b", r"\bdark\b"],
    "white": [r"\bwhite\b", r"\bblanche\b"],
    "rouge": [r"\brouge\b", r"\bred\b"],
    "gold": [r"\bgold\b", r"\bdorado\b"],
    "cobalt": [r"\bcobalt\b"],
    "coral": [r"\bcoral\b"],
    "crystal": [r"\bcrystal\b"],
    "bright": [r"\bbright\b"],
    "ultra": [r"\bultra\b"],
    "victory": [r"\bvictory\b"],
    "legend": [r"\blegend\b"],
    "hero": [r"\bhero\b"],
    "lover": [r"\blover\b"],
    "blush": [r"\bblush\b"],
    "sport": [r"\bsport\b"],
    "fraiche": [r"\bfraiche\b", r"\beau\s+fraiche\b", r"\bfresh\b"],
    "ice": [r"\bice\b", r"\bfreeze\b"],
    "le beau": [r"\ble\s+beau\b", r"\bbeau\b"],
    "bad boy": [r"\bbad\s+boy\b"],
    "very good girl": [r"\bvery\s+good\s+girl\b"],
    "good girl": [r"\bgood\s+girl\b"],
    "dylan blue": [r"\bdylan\s*blue\b", r"\bdylan\b"],
    "eros": [r"\beros\b"],
    "the one": [r"\bthe\s*one\b"],
    "light blue": [r"\blight\s*blue\b"],
    "black xs": [r"\bblack\s*xs\b"],
    "pure xs": [r"\bpure\s*xs\b"],
    "le male": [r"\ble\s*male\b"],
    "scandal": [r"\bscandal\b"],
    "invictus": [r"\binvictus\b"],
    "phantom": [r"\bphantom\b"],
    "one million": [r"\b1\s*million\b", r"\bone\s*million\b"],
    "sauvage": [r"\bsauvage\b"],
    "bleu": [r"\bbleu\b"],
    "libre": [r"\blibre\b"],
    "toy boy": [r"\btoy\s*boy\b"],
}


def _normalizar_para_matching(s: str) -> str:
    """Normaliza texto removiendo diacríticos y homogeneizando espacios."""
    if not s:
        return ""
    t = s.lower()
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return t


def coincide_entidad_detallada(
    titulo: str,
    perfume_nombre: str,
    marca: str = "",
    concentracion: str = "",
    volumen_esperado: Optional[int] = None,
    url: str = ""
) -> ResultadoCoincidencia:
    """
    Motor determinista jerárquico de resolución de entidades.
    
    Verifica con alta precisión si una oferta de e-commerce corresponde exactamente
    al perfume canónico, evaluando de forma desacoplada:
    1. Formato de producto (descarte de recargas, sets, cosméticos).
    2. Integridad de marca (bloqueo total de casas clon en fragancias de diseñador).
    3. Conflicto con marcas ajenas en el título o URL.
    4. Guard de Flankers (rechazo si contiene flankers no solicitados o carece de requeridos).
    5. Género y líneas cruzadas (ej: Libre vs Y, Scandal Homme vs Woman, Eros Men vs Woman).
    6. Tokens nucleares obligatorios de la fragancia.
    7. Compatibilidad de formulación / concentración (EDT vs EDP).
    8. Verificación de volumen (ml) frente a la variante esperada.
    """
    tit = _normalizar_para_matching(titulo)
    p_norm = _normalizar_para_matching(perfume_nombre)
    m_norm = _normalizar_para_matching(marca) if marca else ""
    c_norm = _normalizar_para_matching(concentracion) if concentracion else ""
    url_norm = _normalizar_para_matching(url) if url else ""
    combo_text = f"{tit} {url_norm}"

    # 1. Guard de Formato de Producto (Recargas, Sets, Cosméticos, Decants)
    for pattern, desc in FORMATOS_EXCLUIDOS:
        if not re.search(pattern, p_norm):
            if re.search(pattern, combo_text):
                return ResultadoCoincidencia(
                    coincide=False,
                    confianza=0.0,
                    motivo=f"Formato excluido detectado: {desc}",
                    formato_invalido=desc
                )

    # 2. Guard de Integridad de Marca y Clones Árabes
    es_marca_clon_buscada = any(re.search(rf"\b{re.escape(clon)}\b", m_norm) for clon in CASAS_CLON_DEDICADAS)
    es_marca_disenador = False
    if not es_marca_clon_buscada:
        for can_k, aliases in MARCAS_DISENADOR_PRESTIGIO.items():
            if any(re.search(rf"\b{re.escape(a)}\b", m_norm) for a in aliases):
                es_marca_disenador = True
                break
            if any(len(a) >= 4 and re.search(rf"\b{re.escape(a)}\b", p_norm) for a in aliases):
                es_marca_disenador = True
                break

    if es_marca_disenador:
        for clon in CASAS_CLON_DEDICADAS:
            if re.search(rf"\b{re.escape(clon)}\b", combo_text):
                return ResultadoCoincidencia(
                    coincide=False,
                    confianza=0.0,
                    motivo=f"Casa clon detectada '{clon}' en producto de diseñador",
                    marca_detectada=clon
                )
        for ar_k, aliases in MARCAS_ORIENTALES_RECONOCIDAS.items():
            for a in aliases:
                if re.search(rf"\b{re.escape(a)}\b", combo_text):
                    return ResultadoCoincidencia(
                        coincide=False,
                        confianza=0.0,
                        motivo=f"Casa oriental ajena '{a}' detectada en perfume de diseñador",
                        marca_detectada=a
                    )

    # Conflicto con marcas de diseñador incompatibles en título o URL
    for can_k, aliases in MARCAS_DISENADOR_PRESTIGIO.items():
        es_marca_propia = any(re.search(rf"\b{re.escape(a)}\b", m_norm) for a in aliases) or any(re.search(rf"\b{re.escape(a)}\b", p_norm) for a in aliases)
        if not es_marca_propia:
            for a in aliases:
                if len(a) >= 4 and re.search(rf"\b{re.escape(a)}\b", tit):
                    return ResultadoCoincidencia(
                        coincide=False,
                        confianza=0.0,
                        motivo=f"Conflicto de marca: se detectó marca ajena '{a}'",
                        marca_detectada=a
                    )

    # 3. Guard de Flankers (Positivos y Negativos)
    for fl_key, patterns in FLANKERS_MAP.items():
        flanker_en_perfume = any(re.search(p, p_norm) for p in patterns)
        flanker_en_candidato = any(re.search(p, combo_text) for p in patterns)

        if fl_key in ("noir", "white", "gold") and fl_key in p_norm:
            pass

        if not flanker_en_perfume and flanker_en_candidato:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Flanker no solicitado '{fl_key}' detectado en candidato",
                flanker_detectado=fl_key
            )
        elif flanker_en_perfume and not flanker_en_candidato:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Flanker obligatorio '{fl_key}' ausente en candidato",
                flanker_detectado=fl_key
            )

    # 4. Guard de Género y Líneas Cruzadas
    if "libre" in p_norm and not ("libre" in tit or "libre" in url_norm):
        return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Línea 'Libre' ausente")
    if "myslf" in combo_text and "myslf" not in p_norm:
        return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Línea 'MYSLF' no corresponde")
    if re.search(r"\by\b", combo_text) and " y " not in f" {p_norm} " and not p_norm.startswith("y "):
        if "yves saint laurent" in m_norm or "ysl" in m_norm:
            if "libre" in p_norm:
                return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Línea masculina 'Y' no corresponde a 'Libre'")

    if "scandal" in p_norm:
        if "homme" in p_norm and any(re.search(r, tit) for r in [r"\bwoman\b", r"\bfemme\b", r"\bmujer\b", r"\bdama\b"]):
            return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Género femenino incompatible con Scandal Pour Homme")
        if any(re.search(r, p_norm) for r in [r"\bwoman\b", r"\bfemme\b", r"\bmujer\b"]) and any(re.search(r, tit) for r in [r"\bhomme\b", r"\bmen\b", r"\bhombre\b"]):
            return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Género masculino incompatible con Scandal Woman")

    if "eros" in p_norm and not any(w in p_norm for w in ["woman", "femme", "mujer", "dama"]):
        if any(re.search(r, tit) for r in [r"\bwoman\b", r"\bfemme\b", r"\bmujer\b", r"\bdama\b"]):
            return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Eros Woman no coincide con Eros masculino")

    # 5. Tokens nucleares obligatorios de la fragancia
    stop_words = {
        "de", "la", "el", "los", "las", "en", "para", "por", "un", "una",
        "pour", "for", "men", "women", "homme", "femme", "man", "woman",
        "eau", "parfum", "toilette", "cologne", "edp", "edt", "edc",
        "unisex", "perfume", "fragancia", "colonia", "spray", "vaporisateur",
        "vaporizador", "natural", "original", "hombre", "mujer", "dama",
        "nueva", "presentacion", "presentación"
    }

    # Limpiar marca redundante de los tokens del nombre
    p_clean_nom = p_norm
    if m_norm:
        p_clean_nom = re.sub(rf"\b{re.escape(m_norm)}\b", " ", p_clean_nom)
    for acr in ["ysl", "jpg", "d&g", "ch", "ck", "mfk"]:
        p_clean_nom = re.sub(rf"\b{acr}\b", " ", p_clean_nom)

    t_clean = re.sub(r"[^\w\s]", " ", p_clean_nom)
    tokens = [tok for tok in t_clean.split() if tok not in stop_words and len(tok) >= 2]
    if not tokens:
        t_clean_orig = re.sub(r"[^\w\s]", " ", p_norm)
        tokens = [tok for tok in t_clean_orig.split() if tok not in stop_words and len(tok) >= 2]
        if not tokens:
            tokens = [tok for tok in t_clean_orig.split() if len(tok) >= 2]

    for tok in tokens:
        # Equivalencias de marca / nombres
        if tok == "ysl" and ("yves saint laurent" in combo_text or "saint laurent" in combo_text):
            continue
        if tok == "sweet" and re.search(r"\bsweettooth\b", combo_text):
            continue
        if tok == "tooth" and re.search(r"\bsweettooth\b", combo_text):
            continue
        if tok == "dior" and "dior" in m_norm:
            continue

        if not re.search(rf"\b{re.escape(tok)}\b", combo_text):
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Token nuclear obligatorio '{tok}' ausente en candidato"
            )

    # 6. Guard de Concentración (EDT vs EDP)
    if c_norm:
        es_edt_p = "toilette" in c_norm or "edt" in c_norm
        es_edp_p = ("parfum" in c_norm or "edp" in c_norm) and not es_edt_p

        es_edt_t = ("toilette" in tit or "edt" in tit) and not ("eau de parfum" in tit or "edp" in tit)
        es_edp_t = ("eau de parfum" in tit or "edp" in tit) and not ("toilette" in tit or "edt" in tit)

        if es_edt_p and es_edp_t:
            return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Incompatibilidad: esperado EDT, candidato es EDP")
        if es_edp_p and es_edt_t:
            return ResultadoCoincidencia(coincide=False, confianza=0.0, motivo="Incompatibilidad: esperado EDP, candidato es EDT")

    # 7. Guard de Volumen (si se especifica volumen esperado)
    if volumen_esperado:
        vol_candidato = extraer_volumen_ml(combo_text, default=0)
        if vol_candidato > 0 and abs(vol_candidato - volumen_esperado) > 5:
            return ResultadoCoincidencia(
                coincide=False,
                confianza=0.0,
                motivo=f"Discrepancia de volumen: esperado {volumen_esperado}ml, recibido {vol_candidato}ml",
                volumen_detectado=vol_candidato
            )

    return ResultadoCoincidencia(
        coincide=True,
        confianza=0.98,
        motivo="Entidad validada con alta fidelidad"
    )


def coincide_con_perfume(
    titulo: str,
    perfume_nombre: str,
    marca: str = "",
    concentracion: str = "",
    volumen_esperado: Optional[int] = None,
    url: str = ""
) -> bool:
    """Wrapper retrocompatible que devuelve un booleano para los scrapers y vistas."""
    return coincide_entidad_detallada(
        titulo=titulo,
        perfume_nombre=perfume_nombre,
        marca=marca,
        concentracion=concentracion,
        volumen_esperado=volumen_esperado,
        url=url
    ).coincide

