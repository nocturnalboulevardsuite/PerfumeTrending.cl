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

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

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
    from backend.normalizador import es_producto_perfume_valido, extraer_volumen_ml, coincide_con_perfume, es_precio_valido
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
    from normalizador import es_producto_perfume_valido, extraer_volumen_ml, coincide_con_perfume, es_precio_valido

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

# =============================================================================
# EXTRACTORES NATIVOS POR TIENDA (Puro Python, Anti-bloqueo y Alta Precisión)
# =============================================================================

TIENDAS_SHOPIFY = {
    "Silk Perfumes": "silkperfumes.cl",
    "Elite Perfumes": "eliteperfumes.cl",
    "Alisha Perfumes": "alishaperfumes.cl",
    "Yauras Perfumes": "yauras.cl",
}


def extraer_variedades_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = ""
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples variedades de tamaño (ml) y stock real en tiendas Shopify
    (Silk Perfumes, Elite Perfumes, Alisha Perfumes, Yauras Perfumes).
    Retorna una lista de diccionarios, uno por cada tamaño/presentación detectada.
    """
    query_str = f"{marca} {perfume_nombre}".strip() if (marca and marca.lower() not in perfume_nombre.lower()) else perfume_nombre.strip()
    q = urllib.parse.quote(query_str)
    url_api = f"https://www.{dominio}/search/suggest.json?q={q}&resources[type]=product"
    headers = obtener_headers_json(referer=f"https://www.{dominio}/")

    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    try:
        res = session.get(url_api, headers=headers, timeout=9)
        if res.status_code == 200:
            productos = res.json().get("resources", {}).get("results", {}).get("products", [])
            tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", perfume_nombre).split() if len(t) >= 2]
            if not tokens:
                tokens = [perfume_nombre.lower().strip()]
            for p in productos:
                raw_title = p.get("title", "")
                
                # Descartar si es accesorio o producto derivado
                if not es_producto_perfume_valido(raw_title):
                    continue

                # Validar correspondencia exacta con la fragancia y concentración
                if not coincide_con_perfume(raw_title, perfume_nombre, marca, concentracion):
                    continue

                # Regla de seguridad especial: evitar cruces con fragancias de Chanel
                if "chanel" in perfume_nombre.lower() and "chanel" not in raw_title.lower():
                    continue

                vol_encontrado = extraer_volumen_ml(raw_title) or volumen_ml_defecto or 100
                if vol_encontrado in vols_vistos:
                    continue

                precio_act = int(float(p.get("price", 0)))
                p_comp_raw = p.get("compare_at_price_max") or p.get("compare_at_price_min")
                precio_norm = int(float(p_comp_raw)) if p_comp_raw else precio_act

                if es_precio_valido(precio_act):
                    vols_vistos.add(vol_encontrado)
                    clean_url = f"https://www.{dominio}" + p.get("url", "").split("?")[0]
                    norm_valido = precio_norm if (es_precio_valido(precio_norm) and precio_norm > precio_act) else precio_act
                    variedades.append({
                        "exito": True,
                        "precio_actual": precio_act,
                        "precio_normal": norm_valido,
                        "url": clean_url,
                        "en_stock": bool(p.get("available", True)),
                        "volumen_ml": vol_encontrado,
                        "metodo": "Shopify Multi-Suggest"
                    })
    except Exception as e:
        logger.warning(f"Error consultando Shopify {dominio} para '{perfume_nombre}': {e}")

    return variedades


def extraer_precio_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias: retorna la primera variedad o {exito: False}."""
    vars_found = extraer_variedades_shopify(session, dominio, perfume_nombre, marca, volumen_ml)
    if vars_found:
        return vars_found[0]
    return {"exito": False}


def extraer_variedades_falabella(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = ""
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples presentaciones de Falabella Chile (30ml, 50ml, 60ml, 100ml, 200ml, etc.):
    1. Si se provee una URL directa funcional, lee '__NEXT_DATA__' y extrae todos los SKUs/variantes.
    2. Si no hay URL directa o responde 404, realiza búsqueda viva en Falabella (/search?Ntt=...)
       y extrae las presentaciones de los productos concordantes.
    """
    headers = obtener_headers_navegador(referer="https://www.falabella.com/falabella-cl")
    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    # Intento 1: URL directa
    if url_directa and url_directa.startswith("http"):
        try:
            res = session.get(url_directa, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tag = soup.find("script", id="__NEXT_DATA__")
                if tag and tag.string:
                    data = json.loads(tag.string)
                    pdata = data.get("props", {}).get("pageProps", {}).get("productData", {})
                    is_prod_out = bool(pdata.get("isOutOfStock", False))
                    skus = pdata.get("variants", []) or pdata.get("skus", [])
                    prod_name = pdata.get("name", perfume_nombre)
                    # Validación de integridad: asegurar que la URL directa corresponde al perfume auditado
                    if not coincide_con_perfume(prod_name, perfume_nombre, marca, concentracion):
                        logger.warning(f"⚠️ URL directa Falabella descartada por inconsistencia ({prod_name} != {perfume_nombre})")
                    else:
                        for v in skus:
                            v_name = v.get("name") or prod_name
                            size_attr = v.get("attributes", {}).get("size")
                            vol = clean_digits(size_attr) if size_attr else extraer_volumen_ml(v_name)
                            if not vol or vol < 10 or vol > 1000:
                                vol = extraer_volumen_ml(v_name) or volumen_ml_defecto or 100
                            if vol in vols_vistos:
                                continue
                            prices = v.get("prices", [])
                            p_act, p_norm = 0, 0
                            for p_item in prices:
                                t = p_item.get("type", "")
                                val = clean_digits(p_item.get("price", ["0"])[0])
                                if t in ("internetPrice", "eventPrice") and val > 0:
                                    p_act = val
                                elif t == "normalPrice" and val > 0:
                                    p_norm = val
                            if p_act == 0 and prices:
                                p_act = clean_digits(prices[0].get("price", ["0"])[0])
                            if es_precio_valido(p_act):
                                is_out = bool(v.get("isOutOfStock", False)) or is_prod_out or (v.get("isPurchaseable") is False)
                                vols_vistos.add(vol)
                                norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                variedades.append({
                                    "exito": True,
                                    "precio_actual": p_act,
                                    "precio_normal": norm_valido,
                                    "url": url_directa,
                                    "en_stock": not is_out,
                                    "volumen_ml": vol,
                                    "metodo": "Falabella Direct Variants"
                                })
        except Exception as e:
            logger.debug(f"Aviso leyendo URL directa Falabella: {e}")

    if variedades and any(v.get("en_stock") for v in variedades):
        return variedades

    # Intento 2: Búsqueda dinámica en vivo en Falabella
    query_str = f"{marca} {perfume_nombre}".strip() if (marca and marca.lower() not in perfume_nombre.lower()) else perfume_nombre.strip()
    q = urllib.parse.quote(query_str)
    search_url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    try:
        res_s = session.get(search_url, headers=headers, timeout=11)
        if res_s.status_code == 200:
            soup_s = BeautifulSoup(res_s.text, "html.parser")
            tag_s = soup_s.find("script", id="__NEXT_DATA__")
            if tag_s and tag_s.string:
                data_s = json.loads(tag_s.string)
                results = data_s.get("props", {}).get("pageProps", {}).get("results", [])
                tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", perfume_nombre).split() if len(t) >= 2]
                if not tokens:
                    tokens = [perfume_nombre.lower().strip()]
                for r in results:
                    d_name = r.get("displayName", "")
                    if not es_producto_perfume_valido(d_name):
                        continue
                    if not coincide_con_perfume(d_name, perfume_nombre, marca, concentracion):
                        continue
                    prod_url = r.get("url", "")
                    if prod_url and len(variedades) < 4:
                        try:
                            res_p = session.get(prod_url, headers=headers, timeout=9)
                            if res_p.status_code == 200:
                                soup_p = BeautifulSoup(res_p.text, "html.parser")
                                tag_p = soup_p.find("script", id="__NEXT_DATA__")
                                if tag_p and tag_p.string:
                                    data_p = json.loads(tag_p.string)
                                    pdata = data_p.get("props", {}).get("pageProps", {}).get("productData", {})
                                    is_prod_out = bool(pdata.get("isOutOfStock", False))
                                    skus = pdata.get("variants", []) or pdata.get("skus", [])
                                    for v in skus:
                                        v_name = v.get("name") or d_name
                                        size_attr = v.get("attributes", {}).get("size")
                                        vol = clean_digits(size_attr) if size_attr else extraer_volumen_ml(v_name)
                                        if not vol or vol < 10 or vol > 1000:
                                            vol = extraer_volumen_ml(v_name) or volumen_ml_defecto or 100
                                        if vol in vols_vistos:
                                            continue
                                        prices = v.get("prices", [])
                                        p_act, p_norm = 0, 0
                                        for p_item in prices:
                                            t = p_item.get("type", "")
                                            val = clean_digits(p_item.get("price", ["0"])[0])
                                            if t in ("internetPrice", "eventPrice") and val > 0:
                                                p_act = val
                                            elif t == "normalPrice" and val > 0:
                                                p_norm = val
                                        if p_act == 0 and prices:
                                            p_act = clean_digits(prices[0].get("price", ["0"])[0])
                                        if es_precio_valido(p_act):
                                            is_out = bool(v.get("isOutOfStock", False)) or is_prod_out or (v.get("isPurchaseable") is False)
                                            vols_vistos.add(vol)
                                            norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                            variedades.append({
                                                "exito": True,
                                                "precio_actual": p_act,
                                                "precio_normal": norm_valido,
                                                "url": prod_url,
                                                "en_stock": not is_out,
                                                "volumen_ml": vol,
                                                "metodo": "Falabella Live Variants"
                                            })
                        except Exception:
                            pass
                    # Si no pudimos traer variantes detalladas, registrar precio del resultado de búsqueda
                    if not variedades:
                        prices = r.get("prices", [])
                        if prices:
                            p_act = clean_digits(prices[0].get("price", ["0"])[0])
                            vol = extraer_volumen_ml(d_name) or volumen_ml_defecto or 100
                            if es_precio_valido(p_act) and vol not in vols_vistos:
                                vols_vistos.add(vol)
                                variedades.append({
                                    "exito": True,
                                    "precio_actual": p_act,
                                    "precio_normal": p_act,
                                    "url": prod_url or search_url,
                                    "en_stock": not bool(r.get("isOutOfStock", False)),
                                    "volumen_ml": vol,
                                    "metodo": "Falabella Search Card"
                                })
                    if len(variedades) >= 3:
                        break
    except Exception as e:
        logger.warning(f"Error en búsqueda viva Falabella para '{perfume_nombre}': {e}")

    return variedades


def extraer_precio_falabella(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias y selección de volumen específico."""
    vars_found = extraer_variedades_falabella(session, url_directa, perfume_nombre, "", volumen_ml)
    if vars_found:
        if volumen_ml:
            exacto = [v for v in vars_found if v.get("volumen_ml") == volumen_ml]
            if exacto:
                return exacto[0]
        return vars_found[0]
    return {"exito": False}


def extraer_variedades_paris(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = ""
) -> List[Dict[str, Any]]:
    """
    Extrae presentaciones y precios reales en Paris.cl:
    1. Si hay URL directa, parsea Schema.org JSON-LD.
    2. Si no hay URL directa o es 404, busca en Paris (/search?q=...) e inspecciona las fichas encontradas.
    """
    headers = obtener_headers_navegador(referer="https://www.paris.cl/")
    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    # Intento 1: URL directa
    if url_directa and url_directa.startswith("http"):
        try:
            res = session.get(url_directa, headers=headers, timeout=10)
            if res.status_code == 200:
                is_dead_paris = any(w in res.text.lower() for w in [
                    'página en construcción', 'pagina en construccion',
                    'mejorando tu experiencia', 'página no encontrada', 'no encontramos productos'
                ])
                if not is_dead_paris:
                    soup = BeautifulSoup(res.text, "html.parser")
                    for s_tag in soup.find_all("script", type="application/ld+json"):
                        if "Product" in s_tag.text:
                            d = json.loads(s_tag.text)
                            p_name = d.get("name", perfume_nombre)
                            offers = d.get("offers", [])
                            off = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                            p_raw = off.get("price")
                            if p_raw:
                                p_act = clean_digits(p_raw)
                                vol = extraer_volumen_ml(p_name) or volumen_ml_defecto or 100
                                if es_precio_valido(p_act) and vol not in vols_vistos:
                                    vols_vistos.add(vol)
                                    avail = str(off.get("availability", "")).lower()
                                    en_stock = False if ("outofstock" in avail or "agotado" in avail) else True
                                    variedades.append({
                                        "exito": True,
                                        "precio_actual": p_act,
                                        "precio_normal": p_act,
                                        "url": url_directa,
                                        "en_stock": en_stock,
                                        "volumen_ml": vol,
                                        "metodo": "Paris Schema.org Direct"
                                    })
        except Exception as e:
            logger.debug(f"Aviso leyendo URL directa Paris: {e}")

    if variedades:
        return variedades

    # Intento 2: Búsqueda dinámica en vivo en Paris
    query_str = f"{marca} {perfume_nombre}".strip() if (marca and marca.lower() not in perfume_nombre.lower()) else perfume_nombre.strip()
    q = urllib.parse.quote(query_str)
    url_search = f"https://www.paris.cl/search?q={q}"
    try:
        res_s = session.get(url_search, headers=headers, timeout=10)
        if res_s.status_code == 200:
            soup_s = BeautifulSoup(res_s.text, "html.parser")
            tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", perfume_nombre).split() if len(t) >= 2]
            if not tokens:
                tokens = [perfume_nombre.lower().strip()]
            links = []
            for a in soup_s.find_all("a", href=True):
                h = a.get("href", "")
                if ".html" in h and any(tok in h.lower() for tok in tokens):
                    clean_h = "https://www.paris.cl" + h.split("?")[0] if h.startswith("/") else h.split("?")[0]
                    if clean_h not in links:
                        links.append(clean_h)
            for lk in links[:3]:
                try:
                    res_p = session.get(lk, headers=headers, timeout=8)
                    if res_p.status_code == 200:
                        soup_p = BeautifulSoup(res_p.text, "html.parser")
                        for s_tag in soup_p.find_all("script", type="application/ld+json"):
                            if "Product" in s_tag.text:
                                d = json.loads(s_tag.text)
                                p_name = d.get("name", perfume_nombre)
                                if not es_producto_perfume_valido(p_name):
                                    continue
                                if not coincide_con_perfume(p_name, perfume_nombre, marca, concentracion):
                                    continue
                                offers = d.get("offers", [])
                                off = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                                p_raw = off.get("price")
                                if p_raw:
                                    p_act = clean_digits(p_raw)
                                    vol = extraer_volumen_ml(p_name) or volumen_ml_defecto or 100
                                    if es_precio_valido(p_act) and vol not in vols_vistos:
                                        vols_vistos.add(vol)
                                        avail = str(off.get("availability", "")).lower()
                                        en_stock = False if ("outofstock" in avail or "agotado" in avail) else True
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": p_act,
                                            "url": lk,
                                            "en_stock": en_stock,
                                            "volumen_ml": vol,
                                            "metodo": "Paris Live Schema.org"
                                        })
                except Exception:
                    pass
                if len(variedades) >= 2:
                    break
    except Exception as e:
        logger.warning(f"Error en búsqueda viva Paris para '{perfume_nombre}': {e}")

    return variedades


def extraer_precio_paris(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias y selección de volumen específico."""
    vars_found = extraer_variedades_paris(session, url_directa, perfume_nombre, "", volumen_ml)
    if vars_found:
        if volumen_ml:
            exacto = [v for v in vars_found if v.get("volumen_ml") == volumen_ml]
            if exacto:
                return exacto[0]
        return vars_found[0]
    return {"exito": False}


def extraer_variedades_ripley(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = ""
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples presentaciones de Ripley Chile (30ml, 50ml, 60ml, 100ml, 200ml, etc.):
    Utiliza curl_cffi para emulación nativa de TLS Chrome (evasión transparente de Cloudflare 403),
    inspecciona las fichas técnicas (PDP) encontradas y extrae cada variante con su volumen, precio y stock real.
    """
    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()
    query_str = f"{marca} {perfume_nombre}".strip() if (marca and marca.lower() not in perfume_nombre.lower()) else perfume_nombre.strip()
    q = urllib.parse.quote(query_str)
    url_search = f"https://simple.ripley.cl/search/{q}"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": "https://simple.ripley.cl/"
    }

    try:
        c_session = None
        if curl_requests is not None:
            c_session = curl_requests.Session(impersonate="chrome124")
            res = c_session.get(url_search, headers=headers, timeout=14)
        else:
            res = session.get(url_search, headers=obtener_headers_navegador(), timeout=10)

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            tag = soup.find("script", id="__NEXT_DATA__")
            if tag and tag.text:
                data = json.loads(tag.text)
                prods = data.get("props", {}).get("pageProps", {}).get("findabilityProps", {}).get("data", {}).get("products", [])

                candidatos = []
                for p in prods:
                    d_name = p.get("name", "")
                    if not es_producto_perfume_valido(d_name):
                        continue
                    if not coincide_con_perfume(d_name, perfume_nombre, marca, concentracion):
                        continue
                    candidatos.append(p)

                # Inspeccionar fichas PDP de los productos coincidentes
                for p in candidatos[:2]:
                    p_id = p.get("parentProductID") or p.get("sku")
                    slug = p.get("url") or p_id
                    pdp_url = f"https://simple.ripley.cl/{slug.lstrip('/')}" if slug and not slug.startswith("http") else (slug or f"https://simple.ripley.cl/{p_id}")

                    if pdp_url and c_session is not None:
                        try:
                            headers_pdp = {
                                "User-Agent": headers["User-Agent"],
                                "Referer": url_search,
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
                            }
                            res_p = c_session.get(pdp_url, headers=headers_pdp, timeout=20)
                            if res_p.status_code == 200:
                                soup_p = BeautifulSoup(res_p.text, "html.parser")
                                tag_p = soup_p.find("script", id="__NEXT_DATA__")
                                if tag_p and tag_p.text:
                                    d_pdp = json.loads(tag_p.text)
                                    prod_info = d_pdp.get("props", {}).get("pageProps", {}).get("detailProps", {}).get("data", {}).get("product", {})
                                    variants = prod_info.get("variants", [])

                                    for v in variants:
                                        price_obj = v.get("price", {})
                                        sale_p = price_obj.get("sale", {}).get("valueNumber") or price_obj.get("master", {}).get("valueNumber")
                                        norm_p = price_obj.get("master", {}).get("valueNumber") or sale_p
                                        if not sale_p or not es_precio_valido(sale_p):
                                            continue

                                        # Identificar volumen específico desde definingAttribute o attributes
                                        vol = None
                                        for def_attr in v.get("definingAttribute", []):
                                            val_str = def_attr.get("value", "")
                                            vol = extraer_volumen_ml(val_str)
                                            if vol:
                                                break

                                        if not vol:
                                            for attr in v.get("attributes", []):
                                                if attr.get("usage") == "Defining" or "contenido_perfume" in (attr.get("identifier") or "").lower():
                                                    vals = attr.get("Values", [{}])
                                                    v_str = vals[0].get("values", "") if vals else ""
                                                    vol = extraer_volumen_ml(v_str)
                                                    if vol:
                                                        break

                                        if not vol:
                                            vol = extraer_volumen_ml(prod_info.get("name", "")) or volumen_ml_defecto or 100

                                        if vol in vols_vistos:
                                            continue
                                        vols_vistos.add(vol)

                                        # Determinar stock real con precisión milimétrica
                                        in_stock = (
                                            bool(v.get("stock", False))
                                            and not bool(v.get("notBuyable", False))
                                            and not bool(v.get("notSelectable", False))
                                            and "sin stock" not in str(v.get("statusUI", "")).lower()
                                            and "agotado" not in str(v.get("statusUI", "")).lower()
                                        )

                                        norm_valido = norm_p if (es_precio_valido(norm_p) and norm_p > sale_p) else sale_p
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": sale_p,
                                            "precio_normal": norm_valido,
                                            "url": pdp_url,
                                            "en_stock": in_stock,
                                            "volumen_ml": vol,
                                            "metodo": "Ripley Live PDP Variants"
                                        })
                        except Exception as e_pdp:
                            logger.debug(f"Aviso leyendo PDP Ripley {pdp_url}: {e_pdp}")

                    if not variedades:
                        p_act = p.get("priceNumber", 0)
                        p_norm = p.get("masterPriceNumber", p_act) or p_act
                        if p_act and es_precio_valido(p_act):
                            vol = extraer_volumen_ml(p.get("name", "")) or volumen_ml_defecto or 100
                            if vol not in vols_vistos:
                                vols_vistos.add(vol)
                                norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                variedades.append({
                                    "exito": True,
                                    "precio_actual": p_act,
                                    "precio_normal": norm_valido,
                                    "url": pdp_url or url_search,
                                    "en_stock": bool(p.get("inStock", True)),
                                    "volumen_ml": vol,
                                    "metodo": "Ripley Chrome Search Card"
                                })
    except Exception as e:
        logger.warning(f"Error consultando Ripley para '{perfume_nombre}': {e}")

    # Fallback a URL directa si no hubo resultados en búsqueda viva
    if not variedades and url_directa:
        res_old = extraer_precio_ripley(session, url_directa, perfume_nombre, volumen_ml_defecto)
        if res_old.get("exito"):
            variedades.append(res_old)

    return variedades


def extraer_precio_ripley(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None
) -> Dict[str, Any]:
    """
    Extrae precio y stock de Ripley Chile combinando Schema.org y selectores DOM.
    Maneja con elegancia protecciones anti-bot de Cloudflare (HTTP 403).
    """
    headers = obtener_headers_navegador(referer="https://simple.ripley.cl/")
    url_a_probar = url_directa

    # Intento 1: Ficha directa
    try:
        res = session.get(url_a_probar, headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"Fallo conexión Ripley direct: {e}")
        res = None

    if res and res.status_code == 403:
        return {"exito": False, "motivo": "Ripley protegido por Cloudflare WAF (HTTP 403)"}

    # Intento 2: Si dio 404, auto-sanar buscando la ficha viva en Ripley
    if not res or res.status_code != 200:
        q = urllib.parse.quote(perfume_nombre)
        try:
            res_s = session.get(f"https://simple.ripley.cl/search/{q}", headers=headers, timeout=10)
            if res_s.status_code == 403:
                return {"exito": False, "motivo": "Ripley protegido por Cloudflare WAF (HTTP 403)"}
            if res_s.status_code == 200:
                soup_s = BeautifulSoup(res_s.text, "html.parser")
                tokens = [t.lower() for t in perfume_nombre.split() if len(t) > 3]
                for a in soup_s.find_all("a", href=True):
                    h = a.get("href", "")
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
                            if es_precio_valido(p_act):
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

            p_val = soup.find(class_=lambda c: c and "price-value" in c)
            if p_val:
                p_act = clean_digits(p_val.get_text())
                agotado_dom = bool(soup.find(string=re.compile(r"agotado|sin stock", re.I)))
                if es_precio_valido(p_act):
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

    actualizaciones = 0
    omitidos = 0
    errores: List[str] = []
    detalle_precios: List[Dict[str, Any]] = []
    tiendas_stats: Dict[str, Dict[str, Any]] = {
        t["nombre"]: {"consultas": 0, "exitos_en_vivo": 0, "fallbacks_seguridad": 0, "trust_score": t["trust_score"]}
        for t in tiendas_db
    }

    # Posibilidad de configurar límite para pruebas de humo o auditar el catálogo completo
    limit_env = os.environ.get("SCRAPER_LIMIT_PERFUMES")
    if limit_env and limit_env.isdigit():
        max_p = int(limit_env)
        perfumes_a_auditar = perfumes_db[:max_p]
        logger.info(f"Modo de prueba activo: auditando los primeros {len(perfumes_a_auditar)} perfumes.")
    else:
        perfumes_a_auditar = perfumes_db
        logger.info(f"Modo completo activo: auditando catálogo entero ({len(perfumes_a_auditar)} perfumes).")

    # 3. Bucle Principal: recorremos cada perfume del catálogo
    for p in perfumes_a_auditar:
        p_id = p["id"]
        p_nom = p["nombre"]
        p_marca = p["marca"]
        p_tipo = p.get("tipo", "")

        logger.info(f"Auditando fragancia: {p_nom} ({p_marca})")

        # 4. Bucle Secundario: consultamos cada tienda auditada
        for tienda in tiendas_db:
            t_id = tienda["id"]
            t_nom = tienda["nombre"]

            # Regla de negocio: verificar si la tienda comercializa esa marca
            if not tienda_comercializa_marca(t_nom, p_marca):
                omitidos += 1
                continue

            url_directa_info = obtener_url_directa_tienda(p_id, t_nom)
            url_directa_guardada = url_directa_info[0] if url_directa_info else None
            vol_ml_base = url_directa_info[3] if url_directa_info else 100

            tiendas_stats[t_nom]["consultas"] += 1

            # Pausa breve humana aleatoria
            time.sleep(random.uniform(0.2, 0.5))

            try:
                lista_variedades: List[Dict[str, Any]] = []

                # Rama A: Tiendas Shopify (Silk, Elite, Alisha, Yauras, DBS)
                if t_nom in TIENDAS_SHOPIFY:
                    dominio = TIENDAS_SHOPIFY[t_nom]
                    lista_variedades = extraer_variedades_shopify(
                        session=session,
                        dominio=dominio,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo
                    )

                # Rama B: Falabella (Búsqueda viva Next.js + múltiples variantes de volumen)
                elif "falabella" in t_nom.lower():
                    lista_variedades = extraer_variedades_falabella(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo
                    )

                # Rama C: Paris (Schema.org JSON-LD de Google + búsqueda viva)
                elif "paris" in t_nom.lower():
                    lista_variedades = extraer_variedades_paris(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo
                    )

                # Rama D: Ripley (Búsqueda viva Next.js + curl_cffi Chrome TLS)
                elif "ripley" in t_nom.lower():
                    lista_variedades = extraer_variedades_ripley(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo
                    )

                # 5. Procesamiento y persistencia de cada variedad extraída
                if lista_variedades:
                    for var_data in lista_variedades:
                        if not var_data.get("exito"):
                            continue
                        precio_actual_final = var_data["precio_actual"]
                        if not es_precio_valido(precio_actual_final):
                            continue
                        precio_normal_final = var_data["precio_normal"]
                        url_final = var_data["url"]
                        vol_final = var_data.get("volumen_ml", vol_ml_base)
                        stock_final = bool(var_data.get("en_stock", True))

                        # Persistencia Transaccional Atómica (ACID en Supabase y SQLite)
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
                            "origen": var_data.get("metodo", "Extracción en Vivo"),
                            "volumen_ml": vol_final,
                            "en_stock": stock_final
                        })
                        logger.info(f"  -> [{t_nom}] EN VIVO: ${precio_actual_final:,} (Normal: ${precio_normal_final:,}) | {vol_final}ml | stock: {stock_final}")
                else:
                    motivo_fallo = f"Sin disponibilidad confirmada en {t_nom}"
                    registrar_fallo_scraping(
                        tienda_id=t_id,
                        perfume_id=p_id,
                        mensaje=motivo_fallo
                    )
                    tiendas_stats[t_nom]["fallbacks_seguridad"] += 1
                    logger.debug(f"  -> [{t_nom}] FALLO SCRAPING: {motivo_fallo}. No se altera precio ni stock.")

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
