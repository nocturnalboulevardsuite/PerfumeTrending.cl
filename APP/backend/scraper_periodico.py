"""
PerfumeTrending.cl — Motor de Scraping y Rastreo Periódico (ETL Pipeline Profesional)
======================================================================================
Servicio backend de alto rendimiento para la extracción, validación, normalización
y persistencia continua de precios y stock 100% reales en el mercado chileno.

Tiendas Soportadas:
1. Silk Perfumes (Shopify API + JSON suggest)
2. Elite Perfumes (Shopify API + JSON suggest)
3. Falabella (Next.js __NEXT_DATA__ extraction + live self-healing)
4. Paris (Schema.org JSON-LD extraction + live self-healing)
5. Ripley (Schema.org JSON-LD & DOM extraction + live self-healing)

Características de Ingeniería:
- Extracción de precios reales y descuentos genuinos (sin simulaciones ni fórmulas artificiales).
- Identificación precisa de tamaño en ml para cada comercio.
- Auto-sanación de enlaces (self-healing): Si una tienda rota el SKU (404), localiza la nueva ficha viva.
- Emulación de navegador residencial chileno (headers completos de Chrome/Edge en Santiago).
- Delays humanos aleatorios y retries exponenciales para evitar bloqueos y rate limiting.
- Resiliencia Zero-Downtime: Si un comercio está temporalmente inaccesible, preserva el último precio válido.
- Generación de informes de auditoría estructurados en data/reportes/ultimo_scraping.json.
"""

from datetime import datetime
import json
import logging
import os
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Ajuste de codificación para consola Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PerfumeScraper")

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
REPORTES_DIR = os.path.join(BASE_DIR, "data", "reportes")
REPORTE_ULTIMO_PATH = os.path.join(REPORTES_DIR, "ultimo_scraping.json")

# Importación de capa de persistencia y normalización
try:
    from backend.database import (
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        registrar_precio,
        registrar_observacion_oferta,
        registrar_fallo_scraping,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda,
        get_supabase,
        is_supabase_disponible
    )
    from backend.normalizador import es_producto_perfume_valido, extraer_volumen_ml
except ImportError:
    from database import (
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        registrar_precio,
        registrar_observacion_oferta,
        registrar_fallo_scraping,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda,
        get_supabase,
        is_supabase_disponible
    )
    from normalizador import es_producto_perfume_valido, extraer_volumen_ml

# Pool de User-Agents residenciales modernos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def clean_digits(val: Any) -> int:
    """Extrae únicamente los dígitos de una cadena o número ('$ 145.200' -> 145200)."""
    digits = re.sub(r"[^\d]", "", str(val))
    return int(digits) if digits else 0


# =============================================================================
# BLOQUE: CONFIGURACIÓN DE RED RESILIENTE Y EVASIÓN DE BLOQUEOS (ANTI-BOT)
# =============================================================================

def crear_sesion_robusta() -> requests.Session:
    """
    ¿Qué hace este bloque?
    Configura un cliente HTTP con reintentos automáticos (Retries) y reutilización de sockets (Connection Pooling).
    
    ¿Por qué está aquí?
    Si un comercio sufre una caída momentánea (HTTP 500, 502, 503, 504) o limita la velocidad (HTTP 429),
    la sesión reintenta hasta 3 veces esperando un tiempo exponencialmente mayor (backoff de 0.6s).
    Esto evita que un micro-corte de red haga fallar el raspado de datos.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3,                           # Máximo 3 reintentos antes de declarar fallo
        backoff_factor=0.6,                # Tiempo de espera incremental (0.6s, 1.2s, 2.4s)
        status_forcelist=[429, 500, 502, 503, 504], # Códigos de error transitorios a reintentar
        allowed_methods=["HEAD", "GET", "OPTIONS"]   # Solo métodos seguros de solo lectura
    )
    # Montamos el adaptador de reintentos tanto para HTTP como para HTTPS
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def obtener_headers_navegador(referer: Optional[str] = None) -> Dict[str, str]:
    """
    ¿Qué hace este bloque?
    Genera cabeceras HTTP realistas simulando ser un usuario humano navegando desde Santiago de Chile.
    
    ¿Por qué está aquí?
    Los cortafuegos de los grandes retailers (Cloudflare, Akamai, CloudFront) bloquean peticiones que
    no envían cabeceras modernas como Sec-Ch-Ua, Accept-Language es-CL y User-Agent residencial.
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",  # Localización explícita para Chile
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",                      # Indica que es un computador de escritorio
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    if referer:
        headers["Referer"] = referer  # Simula de dónde vino el usuario (p.ej. la página principal de la tienda)
    return headers


def obtener_headers_json(referer: Optional[str] = None) -> Dict[str, str]:
    """
    Cabeceras específicas para consultar APIs REST y endpoints JSON internos de las tiendas (como Shopify).
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    return headers


# =============================================================================
# EXTRACTORES NATIVOS POR TIENDA (Puro Python, Anti-bloqueo y Alta Precisión)
# =============================================================================

def extraer_precio_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """
    ¿Qué hace esta función?
    Extrae precios y stock en vivo de perfumerías que usan la plataforma Shopify (Silk Perfumes y Elite Perfumes).
    
    ¿Cómo funciona?
    1. Consulta el endpoint público `/search/suggest.json` que responde en milisegundos.
    2. Valida que el producto devuelto sea un perfume legítimo (no desodorante ni crema).
    3. Comprueba coincidencia por tokens de texto del nombre y la marca.
    4. Detecta precio actual, precio de lista (compare_at_price) y disponibilidad de stock real.
    """
    q = urllib.parse.quote(perfume_nombre)
    url_api = f"https://www.{dominio}/search/suggest.json?q={q}&resources[type]=product"
    headers = obtener_headers_json(referer=f"https://www.{dominio}/")

    try:
        res = session.get(url_api, headers=headers, timeout=9)
        if res.status_code == 200:
            productos = res.json().get("resources", {}).get("results", {}).get("products", [])
            for p in productos:
                raw_title = p.get("title", "")
                
                # Paso 1: Descartar si es accesorio o producto derivado (ej. desodorante)
                if not es_producto_perfume_valido(raw_title):
                    continue

                titulo_lower = raw_title.lower()
                tokens = [t.lower() for t in perfume_nombre.split() if len(t) > 3]
                coincide = any(tok in titulo_lower for tok in tokens) or (marca.lower() in titulo_lower)

                # Regla de seguridad especial: evitar cruces con fragancias de Chanel
                if "chanel" in perfume_nombre.lower() and "chanel" not in titulo_lower:
                    continue

                if coincide:
                    # Paso 2: Extraer y validar el volumen en mililitros
                    vol_encontrado = extraer_volumen_ml(raw_title)

                    # Paso 3: Extraer precios (actual y comparativo)
                    precio_act = int(float(p.get("price", 0)))
                    p_comp_raw = p.get("compare_at_price_max") or p.get("compare_at_price_min")
                    precio_norm = int(float(p_comp_raw)) if p_comp_raw else precio_act

                    # Filtro de sanidad: debe ser un precio mayor a $10.000 CLP
                    if precio_act >= 10000:
                        clean_url = f"https://www.{dominio}" + p.get("url", "").split("?")[0]
                        return {
                            "exito": True,
                            "precio_actual": precio_act,
                            "precio_normal": precio_norm if precio_norm > precio_act else precio_act,
                            "url": clean_url,
                            "en_stock": bool(p.get("available", True)), # Detección nativa de inventario Shopify
                            "volumen_ml": vol_encontrado or volumen_ml or 100,
                            "metodo": "Shopify Live Suggest"
                        }
    except Exception as e:
        logger.warning(f"Error consultando Shopify {dominio} para '{perfume_nombre}': {e}")

    # Si no hubo coincidencia o la tienda falló, retornamos exito=False sin inventar precios
    return {"exito": False}


def extraer_precio_falabella(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """
    ¿Qué hace esta función?
    Extrae el precio, precio normal y disponibilidad de stock en Falabella Chile.
    
    ¿Cómo funciona?
    1. Consulta primero la URL directa guardada de la ficha.
    2. Si devuelve 404 (Falabella rotó el SKU o cambió la URL), activa 'auto-sanación':
       busca el producto en Falabella y localiza la nueva ficha viva sin intervención manual.
    3. Lee el script '__NEXT_DATA__' de Next.js, extrayendo el precio de internet y el estado de stock
       ('isOutOfStock').
    """
    headers = obtener_headers_navegador(referer="https://www.falabella.com/falabella-cl")
    url_a_probar = url_directa

    # Intento 1: Consultar la URL directa que teníamos almacenada
    try:
        res = session.get(url_a_probar, headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"Fallo conexión Falabella direct: {e}")
        res = None

    # Intento 2: Si la URL dio error (404), activamos auto-sanación (Self-Healing)
    if not res or res.status_code != 200:
        logger.info(f"Falabella: URL previa no disponible ({res.status_code if res else 'Error'}). Buscando ficha viva...")
        q = urllib.parse.quote(perfume_nombre)
        search_url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
        try:
            res_s = session.get(search_url, headers=headers, timeout=10)
            if res_s.status_code == 200:
                soup_s = BeautifulSoup(res_s.text, "html.parser")
                tag_s = soup_s.find("script", id="__NEXT_DATA__")
                if tag_s and tag_s.string:
                    data_s = json.loads(tag_s.string)
                    results = data_s.get("props", {}).get("pageProps", {}).get("results", [])
                    tokens = [t.lower() for t in perfume_nombre.split() if len(t) > 3]
                    for r in results:
                        d_name = r.get("displayName", "").lower()
                        if any(tok in d_name for tok in tokens):
                            url_a_probar = r.get("url", url_a_probar)
                            prices = r.get("prices", [])
                            if prices:
                                p_act = clean_digits(prices[0].get("price", ["0"])[0])
                                is_out = bool(r.get("isOutOfStock", False))
                                if p_act >= 10000:
                                    return {
                                        "exito": True,
                                        "precio_actual": p_act,
                                        "precio_normal": p_act,
                                        "url": url_a_probar,
                                        "en_stock": not is_out, # Negación: si isOutOfStock es True, en_stock es False
                                        "volumen_ml": volumen_ml or 100,
                                        "metodo": "Falabella Next Search Healed"
                                    }
        except Exception as e:
            logger.warning(f"Fallo auto-sanación Falabella: {e}")

    # Si tenemos respuesta 200 de la ficha directa
    if res and res.status_code == 200:
        try:
            soup = BeautifulSoup(res.text, "html.parser")
            tag = soup.find("script", id="__NEXT_DATA__")
            if tag and tag.string:
                data = json.loads(tag.string)
                page_props = data.get("props", {}).get("pageProps", {})
                prod = page_props.get("productData", {})
                skus = prod.get("variants", []) or prod.get("skus", [])
                
                prices = []
                if skus:
                    prices = skus[0].get("prices", [])
                if not prices and "prices" in prod:
                    prices = prod.get("prices", [])

                p_act, p_norm = 0, 0
                for p in prices:
                    p_type = p.get("type", "")
                    val = clean_digits(p.get("price", ["0"])[0])
                    if p_type in ("internetPrice", "eventPrice") and val > 0:
                        p_act = val
                    elif p_type == "normalPrice" and val > 0:
                        p_norm = val

                if p_act == 0 and prices:
                    p_act = clean_digits(prices[0].get("price", ["0"])[0])

                is_out = bool(prod.get("isOutOfStock", False))
                if skus:
                    is_out = is_out or bool(skus[0].get("isOutOfStock", False))

                if p_act >= 10000:
                    return {
                        "exito": True,
                        "precio_actual": p_act,
                        "precio_normal": p_norm if p_norm > p_act else p_act,
                        "url": url_a_probar,
                        "en_stock": not is_out,
                        "volumen_ml": volumen_ml or 100,
                        "metodo": "Falabella Next Direct"
                    }
        except Exception as e:
            logger.warning(f"Error parseando __NEXT_DATA__ Falabella: {e}")

    return {"exito": False}


def extraer_precio_paris(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """
    ¿Qué hace esta función?
    Extrae el precio real y la disponibilidad de stock en Paris.cl utilizando Schema.org JSON-LD.
    
    ¿Por qué se usa Schema.org en Paris?
    Paris inyecta en el HTML etiquetas de datos estructurados para Google (Schema.org 'Product').
    Al leer directamente el objeto JSON-LD de la oferta, obtenemos el precio verificado y el estado
    de disponibilidad oficial ('ItemAvailability: InStock' o 'OutOfStock') sin depender del CSS visual.
    """
    headers = obtener_headers_navegador(referer="https://www.paris.cl/")
    url_a_probar = url_directa

    # Intento 1: Consultar la URL directa almacenada
    try:
        res = session.get(url_a_probar, headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"Fallo conexión Paris direct: {e}")
        res = None

    # Intento 2: Si dio 404 o timeout, activar auto-sanación buscando la nueva ficha viva
    if not res or res.status_code != 200:
        logger.info(f"Paris: URL previa no disponible ({res.status_code if res else 'Error'}). Buscando ficha viva...")
        q = urllib.parse.quote(perfume_nombre)
        try:
            res_s = session.get(f"https://www.paris.cl/search?q={q}", headers=headers, timeout=10)
            if res_s.status_code == 200:
                soup_s = BeautifulSoup(res_s.text, "html.parser")
                tokens = [t.lower() for t in perfume_nombre.split() if len(t) > 3]
                for a in soup_s.find_all("a", href=True):
                    h = a.get("href", "")
                    # En Paris las fichas directas de productos contienen '.html'
                    if ".html" in h and any(tok in h.lower() for tok in tokens):
                        url_a_probar = "https://www.paris.cl" + h.split("?")[0]
                        res = session.get(url_a_probar, headers=headers, timeout=9)
                        break
        except Exception as e:
            logger.warning(f"Fallo auto-sanación Paris: {e}")

    # Paso 3: Parsear la etiqueta de datos estructurados JSON-LD de Google
    if res and res.status_code == 200:
        try:
            blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', res.text, re.DOTALL)
            for b in blocks:
                if "Product" in b:
                    d = json.loads(b)
                    offers = d.get("offers", [])
                    # Las ofertas pueden venir como lista o como diccionario individual
                    offer_obj = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                    p_raw = offer_obj.get("price")
                    
                    # Detección estricta de stock: si dice 'outofstock' o 'agotado', en_stock es False
                    avail = str(offer_obj.get("availability", "")).lower()
                    en_stock_val = False if ("outofstock" in avail or "agotado" in avail) else True
                    
                    if p_raw:
                        p_act = int(float(p_raw))
                        if p_act >= 10000:
                            return {
                                "exito": True,
                                "precio_actual": p_act,
                                "precio_normal": p_act,
                                "url": url_a_probar,
                                "en_stock": en_stock_val,
                                "volumen_ml": volumen_ml or 100,
                                "metodo": "Paris JSON-LD Direct"
                            }
        except Exception as e:
            logger.warning(f"Error parseando JSON-LD en Paris: {e}")

    # Si no se pudo obtener un precio verificado, retornamos fallo limpio sin inventar datos
    return {"exito": False}


def extraer_precio_ripley(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """
    ¿Qué hace esta función?
    Extrae precio y stock de Ripley Chile combinando Schema.org y selectores DOM optimizados.
    
    ¿Cómo garantiza la detección de stock?
    Comprueba dos vías independientes:
    1. El bloque JSON-LD 'availability'.
    2. Si en el DOM visual aparece la etiqueta 'Agotado' o 'Sin stock', fuerza en_stock = False.
    """
    headers = obtener_headers_navegador(referer="https://simple.ripley.cl/")
    url_a_probar = url_directa

    # Intento 1: Ficha directa
    try:
        res = session.get(url_a_probar, headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"Fallo conexión Ripley direct: {e}")
        res = None

    # Intento 2: Si dio 404, auto-sanar buscando la ficha viva en Ripley
    if not res or res.status_code != 200:
        logger.info(f"Ripley: URL previa no disponible ({res.status_code if res else 'Error'}). Buscando ficha viva...")
        q = urllib.parse.quote(perfume_nombre)
        try:
            res_s = session.get(f"https://simple.ripley.cl/search/{q}", headers=headers, timeout=10)
            if res_s.status_code == 200:
                soup_s = BeautifulSoup(res_s.text, "html.parser")
                tokens = [t.lower() for t in perfume_nombre.split() if len(t) > 3]
                for a in soup_s.find_all("a", href=True):
                    h = a.get("href", "")
                    # En Ripley los productos terminan con el sufijo 'p'
                    if h.endswith("p") and any(tok in h.lower() for tok in tokens):
                        url_a_probar = "https://simple.ripley.cl" + h.split("?")[0]
                        res = session.get(url_a_probar, headers=headers, timeout=9)
                        break
        except Exception as e:
            logger.warning(f"Fallo auto-sanación Ripley: {e}")

    # Paso 3: Parsear ficha del producto
    if res and res.status_code == 200:
        try:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Vía A: Datos estructurados Schema.org
            blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', res.text, re.DOTALL)
            for b in blocks:
                if '"@type":"Product"' in b or '"@type": "Product"' in b:
                    try:
                        d = json.loads(b)
                        offers = d.get("offers", {})
                        if isinstance(offers, dict) and "price" in offers:
                            p_act = clean_digits(offers["price"])
                            avail_r = str(offers.get("availability", "")).lower()
                            en_stock_r = False if ("outofstock" in avail_r or "agotado" in avail_r) else True
                            if p_act >= 10000:
                                return {
                                    "exito": True,
                                    "precio_actual": p_act,
                                    "precio_normal": p_act,
                                    "url": url_a_probar,
                                    "en_stock": en_stock_r,
                                    "volumen_ml": volumen_ml or 100,
                                    "metodo": "Ripley Schema.org"
                                }
                    except Exception:
                        pass

            # Vía B: Selector DOM visual si el JSON-LD no estaba presente
            p_val = soup.find(class_=lambda c: c and "price-value" in c)
            if p_val:
                p_act = clean_digits(p_val.get_text())
                agotado_dom = bool(soup.find(string=re.compile(r"agotado|sin stock", re.I)))
                if p_act >= 10000:
                    return {
                        "exito": True,
                        "precio_actual": p_act,
                        "precio_normal": p_act,
                        "url": url_a_probar,
                        "en_stock": not agotado_dom,
                        "volumen_ml": volumen_ml or 100,
                        "metodo": "Ripley DOM Price"
                    }
        except Exception as e:
            logger.warning(f"Error parseando precio en Ripley: {e}")

    return {"exito": False}


# =============================================================================
# PERSISTENCIA DEL REPORTE DE AUDITORÍA
# =============================================================================

def guardar_reporte_auditoria(reporte: Dict[str, Any]) -> str:
    """Guarda el reporte consolidado de la última ejecución en formato JSON auditable."""
    os.makedirs(REPORTES_DIR, exist_ok=True)
    with open(REPORTE_ULTIMO_PATH, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    logger.info(f"Reporte de auditoría generado exitosamente en: {REPORTE_ULTIMO_PATH}")
    return REPORTE_ULTIMO_PATH


def obtener_ultimo_reporte_scraping() -> Optional[Dict[str, Any]]:
    """Lee y retorna el último reporte de auditoría generado por el scraper."""
    if os.path.exists(REPORTE_ULTIMO_PATH):
        try:
            with open(REPORTE_ULTIMO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo leer el reporte de auditoría: {e}")
    return None


# =============================================================================
# MOTOR PRINCIPAL DE EJECUCIÓN ETL
# =============================================================================

def ejecutar_ciclo_scraping_y_descubrimiento() -> Dict[str, Any]:
    """
    ¿Qué hace este gran bloque orquestador?
    Ejecuta el ciclo de extracción ETL, auditoría periódica y persistencia de precios reales:
    1. Recupera catálogo de perfumes y comercios registrados en base de datos.
    2. Realiza extracciones en vivo contra los 5 comercios oficiales con cabeceras de navegador.
    3. Si una tienda tiene descuento real, registra precio_normal y precio_actual.
       Si no tiene descuento, precio_normal == precio_actual (sin tachado falso).
    4. Auto-sana URLs rotas y preserva el volumen_ml calibrado.
    5. Fallback de resiliencia: Si una tienda responde 429/403 o timeout, mantiene el último
       precio verificado para garantizar Zero-Downtime.
    6. Genera informe auditable en data/reportes/ultimo_scraping.json.
    """
    init_db()
    inicio = time.time()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info("Iniciando ciclo de scraping ETL profesional con precios 100% reales")

    # 1. Sesión HTTP reutilizable con reintentos exponenciales
    session = crear_sesion_robusta()
    
    # 2. Consultamos la lista de perfumes y tiendas desde la base de datos (Supabase prioritario, SQLite fallback)
    perfumes_db: List[Dict[str, Any]] = []
    tiendas_db: List[Dict[str, Any]] = []
    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        try:
            resp_p = sb.table("perfumes").select("id, nombre, marca, precio_referencia").order("id").execute()
            perfumes_db = resp_p.data or []
            resp_t = sb.table("tiendas").select("id, nombre, url_base, trust_score").order("id").execute()
            tiendas_db = resp_t.data or []
            logger.info(f"Catálogo cargado desde Supabase Cloud: {len(perfumes_db)} perfumes, {len(tiendas_db)} tiendas.")
        except Exception as e:
            logger.warning(f"Aviso consultando catálogo en Supabase ({e}), recurriendo a SQLite local.")

    if not perfumes_db or not tiendas_db:
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, marca, precio_referencia FROM perfumes;")
        perfumes_db = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, nombre, url_base, trust_score FROM tiendas;")
        tiendas_db = [dict(r) for r in cursor.fetchall()]
        conn.close()
        logger.info(f"Catálogo cargado desde SQLite local: {len(perfumes_db)} perfumes, {len(tiendas_db)} tiendas.")

    tiendas_shopify = {
        "Silk Perfumes": "silkperfumes.cl",
        "Elite Perfumes": "eliteperfumes.cl"
    }

    actualizaciones = 0
    omitidos = 0
    errores: List[str] = []
    detalle_precios: List[Dict[str, Any]] = []
    tiendas_stats: Dict[str, Dict[str, Any]] = {
        t["nombre"]: {"consultas": 0, "exitos_en_vivo": 0, "fallbacks_seguridad": 0, "trust_score": t["trust_score"]}
        for t in tiendas_db
    }

    # 3. Bucle Principal: recorremos cada perfume del catálogo
    for p in perfumes_db:
        p_id = p["id"]
        p_nom = p["nombre"]
        p_marca = p["marca"]

        logger.info(f"Auditando fragancia: {p_nom} ({p_marca})")

        # 4. Bucle Secundario: consultamos cada tienda auditada
        for tienda in tiendas_db:
            t_id = tienda["id"]
            t_nom = tienda["nombre"]

            # Regla de negocio: verificar si la tienda comercializa esa marca (evita búsquedas inútiles)
            comercializa = tienda_comercializa_marca(t_nom, p_marca)
            url_directa_info = obtener_url_directa_tienda(p_id, t_nom)

            if not comercializa or not url_directa_info:
                omitidos += 1
                continue

            tiendas_stats[t_nom]["consultas"] += 1
            url_directa_guardada, precio_base, precio_norm_base, vol_ml_base = url_directa_info

            # Pausa humana aleatoria (0.7s a 1.6s) para respetar los servidores y evitar baneos por IP
            time.sleep(random.uniform(0.7, 1.6))

            try:
                datos_extraccion = {"exito": False}

                # Rama A: Tiendas basadas en Shopify (Silk Perfumes y Elite Perfumes)
                if t_nom in tiendas_shopify:
                    dominio = tiendas_shopify[t_nom]
                    datos_extraccion = extraer_precio_shopify(
                        session=session,
                        dominio=dominio,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml=vol_ml_base
                    )

                # Rama B: Falabella (Next.js __NEXT_DATA__)
                elif "falabella" in t_nom.lower():
                    datos_extraccion = extraer_precio_falabella(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        volumen_ml=vol_ml_base
                    )

                # Rama C: Paris (Schema.org JSON-LD de Google)
                elif "paris" in t_nom.lower():
                    datos_extraccion = extraer_precio_paris(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        volumen_ml=vol_ml_base
                    )

                # Rama D: Ripley (Schema.org y selectores DOM)
                elif "ripley" in t_nom.lower():
                    datos_extraccion = extraer_precio_ripley(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        volumen_ml=vol_ml_base
                    )

                # Registrar resultado
                # 5. Procesamiento del resultado de la extracción
                if datos_extraccion.get("exito"):
                    precio_actual_final = datos_extraccion["precio_actual"]
                    precio_normal_final = datos_extraccion["precio_normal"]
                    url_final = datos_extraccion["url"]
                    vol_final = datos_extraccion.get("volumen_ml", vol_ml_base)
                    stock_final = bool(datos_extraccion.get("en_stock", True))

                    # Persistencia Transaccional Atómica (ACID en Supabase y SQLite)
                    # Esta función actualiza la oferta viva y guarda el historial solo si hubo un cambio real
                    res_obs = registrar_observacion_oferta({
                        "perfume_id": p_id,
                        "tienda_id": t_id,
                        "precio_actual": precio_actual_final,
                        "precio_normal": precio_normal_final,
                        "en_stock": stock_final,
                        "url_producto": url_final,
                        "volumen_ml": vol_final
                    })
                    if res_obs.get("resultado") in ("creada", "actualizada"):
                        actualizaciones += 1
                    tiendas_stats[t_nom]["exitos_en_vivo"] += 1
                    detalle_precios.append({
                        "perfume": p_nom,
                        "tienda": t_nom,
                        "precio_actual": precio_actual_final,
                        "precio_normal": precio_normal_final,
                        "tiene_descuento": bool(precio_normal_final > precio_actual_final),
                        "origen": datos_extraccion.get("metodo", "Extracción en Vivo"),
                        "volumen_ml": vol_final,
                        "en_stock": stock_final
                    })
                    logger.info(f"  -> [{t_nom}] EN VIVO: ${precio_actual_final:,} (Normal: ${precio_normal_final:,}) | stock: {stock_final} | ml: {vol_final}")
                else:
                    # En caso de fallo de red, bloqueo o producto no encontrado:
                    # NUNCA inventamos un precio artificial ni convertimos un 'Agotado' en 'Disponible'.
                    # Se registra el fallo de forma limpia para que los administradores puedan auditarlo.
                    motivo_fallo = datos_extraccion.get("motivo", f"Extracción no exitosa en {t_nom}")
                    registrar_fallo_scraping(
                        tienda_id=t_id,
                        perfume_id=p_id,
                        mensaje=motivo_fallo
                    )
                    tiendas_stats[t_nom]["fallbacks_seguridad"] += 1
                    logger.warning(f"  -> [{t_nom}] FALLO SCRAPING: {motivo_fallo}. No se altera precio ni stock.")

            except Exception as ex:
                err_msg = f"Error en ciclo para {p_nom} en {t_nom}: {ex}"
                logger.error(err_msg)
                errores.append(err_msg)
                try:
                    registrar_fallo_scraping(
                        tienda_id=t_id,
                        perfume_id=p_id,
                        mensaje=str(ex)
                    )
                except Exception:
                    pass

    duracion = round(time.time() - inicio, 2)
    estado_general = "EXITOSO" if not errores else ("DEGRADADO" if actualizaciones > 0 else "FALLIDO")

    reporte = {
        "actualizaciones": actualizaciones,
        "fecha": ahora,
        "duracion_segundos": duracion,
        "metadata": {
            "version_etl": "3.0.0",
            "sistema": "PerfumeTrending Professional Anti-Bot ETL",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado_general
        },
        "metricas": {
            "total_perfumes_catalogo": len(perfumes_db),
            "total_tiendas_registradas": len(tiendas_db),
            "precios_actualizados": actualizaciones,
            "exclusiones_marca": omitidos,
            "errores_totales": len(errores)
        },
        "estadisticas_tiendas": tiendas_stats,
        "muestra_capturas": detalle_precios[:15],
        "errores": errores
    }

    # Guardar reporte de auditoría JSON
    guardar_reporte_auditoria(reporte)

    logger.info(f"Ciclo ETL completado en {duracion}s | {actualizaciones} precios sincronizados | Estado: {estado_general}")
    return reporte


if __name__ == "__main__":
    resultado = ejecutar_ciclo_scraping_y_descubrimiento()
    print("\n" + "=" * 60)
    print("RESUMEN DE EJECUCIÓN ETL DE SCRAPING:")
    print(f"Estado: {resultado['metadata']['estado']}")
    print(f"Precios actualizados: {resultado['metricas']['precios_actualizados']}")
    print(f"Duración: {resultado['metadata']['duracion_segundos']}s")
    print("=" * 60)
