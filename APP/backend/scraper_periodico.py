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

import argparse
from datetime import datetime
import json
import logging
import math
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
        _fetch_all_rows,
        finalizar_scraping_run,
        precargar_cache_variantes_supabase,
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        iniciar_scraping_run,
        registrar_precio,
        registrar_observacion_oferta,
        registrar_fallo_scraping,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda,
        get_supabase,
        is_supabase_disponible,
    )
    from backend.normalizador import (
        _GENERO_ESPERADO_CTX,
        coincide_con_perfume,
        coincide_entidad_detallada,
        contexto_genero_esperado,
        detectar_formato_oferta,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_volumen_ml,
    )
except ImportError:
    from database import (
        _fetch_all_rows,
        finalizar_scraping_run,
        precargar_cache_variantes_supabase,
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        iniciar_scraping_run,
        registrar_precio,
        registrar_observacion_oferta,
        registrar_fallo_scraping,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda,
        get_supabase,
        is_supabase_disponible,
    )
    from normalizador import (
        _GENERO_ESPERADO_CTX,
        coincide_con_perfume,
        coincide_entidad_detallada,
        contexto_genero_esperado,
        detectar_formato_oferta,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_volumen_ml,
    )

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
    "Oferta Perfumes": "ofertaperfumes.cl",
    "L'Odoro": "lodoro.cl",
    "Mundo Aromas": "mundoaromas.cl",
    "Cosmetic": "cosmetic.cl",
    "Fragante": "fragante.cl",
    "ComprarEnChile": "comprarenchile.cl",
}

TIENDAS_WOOCOMMERCE = {
    "Chile Perfume": "chileperfume.cl",
    "Portal del Perfume": "portaldelperfume.cl",
    "Aromata": "aromata.cl",
}

_DOMINIOS_SIN_WWW = {
    "alishaperfumes.cl",
    "yauras.cl",
    "ofertaperfumes.cl",
    "mundoaromas.cl",
    "cosmetic.cl",
    "fragante.cl",
    "comprarenchile.cl",
    "portaldelperfume.cl",
}

_SELLERS_OFICIALES_MARKETPLACE = (
    "falabella",
    "ripley",
    "paris",
    "cencosud",
    "sodimac",
    "tottus",
    "linio",
    "dbs",
    "preunic",
    "salcobrand",
    "cruz verde",
    "silk perfumes",
    "elite perfumes",
    "alisha perfumes",
    "yauras",
    "oferta perfumes",
    "l'odoro",
    "lodoro",
    "mundo aromas",
    "cosmetic",
    "chile perfume",
    "portal del perfume",
    "fragante",
    "aromata",
    "comprarenchile",
)

_SELLERS_SOSPECHOSOS = (
    "alternativ",
    "imitacion",
    "imitación",
    "inspiracion",
    "inspiración",
    "decant",
    "outlet",
    "generico",
    "genérico",
)


def _resolver_base_shopify(dominio: str) -> str:
    dom = (dominio or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
    if dom.startswith("www."):
        dom_bare = dom[4:]
    else:
        dom_bare = dom
    if dom_bare in _DOMINIOS_SIN_WWW:
        return f"https://{dom_bare}"
    return f"https://www.{dom_bare}"


def _es_vendedor_marketplace_no_verificado(seller_raw: Any, marca: str, perfume_nombre: str) -> bool:
    """
    Detecta vendedores terceros no auditados en Marketplaces (Falabella / Ripley)
    para evitar infiltración de clones o imitaciones sobre fichas de diseñador/nicho.
    """
    if not seller_raw:
        return False
    s_norm = str(seller_raw).strip().lower()
    if not s_norm:
        return False
    if any(oficial in s_norm for oficial in _SELLERS_OFICIALES_MARKETPLACE):
        return False
    if marca and len(marca.strip()) >= 3 and marca.strip().lower() in s_norm:
        return False
    if any(sosp in s_norm for sosp in _SELLERS_SOSPECHOSOS):
        return True
    if marca and not es_arabe(marca, perfume_nombre):
        return True
    return False


def extraer_variedades_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples variedades de tamaño (ml), formato ('regular' vs 'tester') y stock real
    en tiendas Shopify auditadas (Silk, Elite, Alisha, Yauras, Oferta Perfumes).
    """
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    q = urllib.parse.quote(query_str)
    base_host = _resolver_base_shopify(dominio)
    url_api = f"{base_host}/search/suggest.json?q={q}&resources[type]=product"
    headers = obtener_headers_json(referer=f"{base_host}/")

    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    try:
        res = session.get(url_api, headers=headers, timeout=9)
        if res.status_code in (403, 429) and curl_requests is not None:
            try:
                s_cffi = curl_requests.Session(impersonate="chrome124")
                res_cffi = s_cffi.get(url_api, headers=headers, timeout=9)
                if res_cffi.status_code == 200:
                    res = res_cffi
            except Exception:
                pass

        if res.status_code in (403, 429):
            if diagnostico is not None:
                diagnostico["waf_bloqueado"] = True
                diagnostico["http_status"] = res.status_code
            return variedades
        if res.status_code == 200:
            productos = res.json().get("resources", {}).get("results", {}).get("products", [])
            for p in productos:
                raw_title = p.get("title", "")
                if not es_producto_perfume_valido(raw_title, marca=marca or None, volumen_min_ml=25):
                    continue

                raw_path = p.get("url", "").split("?")[0]
                clean_url = raw_path if raw_path.startswith("http") else f"{base_host}{raw_path}"

                precio_act = int(float(p.get("price", 0)))
                if not es_precio_valido(precio_act):
                    continue

                vol_encontrado = extraer_volumen_ml(raw_title) or extraer_volumen_ml(clean_url) or volumen_ml_defecto or 100
                if vol_encontrado < 25:
                    continue

                res_match = coincide_entidad_detallada(
                    titulo=raw_title,
                    perfume_nombre=perfume_nombre,
                    marca=marca,
                    concentracion=concentracion,
                    url=clean_url,
                    precio_candidato=precio_act,
                    precio_referencia=precio_referencia,
                )
                if not res_match.coincide:
                    continue

                if "chanel" in perfume_nombre.lower() and "chanel" not in raw_title.lower():
                    continue

                formato_det = res_match.formato_detectado or detectar_formato_oferta(raw_title, clean_url)
                clave_var = (vol_encontrado, formato_det)
                if clave_var in vols_vistos:
                    continue

                p_comp_raw = p.get("compare_at_price_max") or p.get("compare_at_price_min")
                precio_norm = int(float(p_comp_raw)) if p_comp_raw else precio_act

                vols_vistos.add(clave_var)
                norm_valido = precio_norm if (es_precio_valido(precio_norm) and precio_norm > precio_act) else precio_act
                variedades.append({
                    "exito": True,
                    "precio_actual": precio_act,
                    "precio_normal": norm_valido,
                    "url": clean_url,
                    "en_stock": bool(p.get("available", True)),
                    "volumen_ml": vol_encontrado,
                    "formato": formato_det,
                    "metodo": "Shopify Multi-Suggest",
                })
    except Exception as e:
        logger.warning(f"Error consultando Shopify {dominio} para '{perfume_nombre}': {e}")

    return variedades


def extraer_precio_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias: retorna la primera variedad o {exito: False}."""
    vars_found = extraer_variedades_shopify(session, dominio, perfume_nombre, marca, volumen_ml)
    if vars_found:
        return vars_found[0]
    return {"exito": False}


def extraer_variedades_woocommerce(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae presentaciones y precios reales en tiendas WooCommerce auditadas
    (Chile Perfume, Portal del Perfume, Aromata) mediante la WooCommerce Store API pública.
    """
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    q = urllib.parse.quote(query_str)
    base_host = f"https://{dominio.strip().rstrip('/')}"
    url_api = f"{base_host}/wp-json/wc/store/v1/products?search={q}&per_page=10"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": f"{base_host}/",
    }

    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    try:
        res = session.get(url_api, headers=headers, timeout=10)
        if res.status_code in (403, 429) and curl_requests is not None:
            try:
                s_cffi = curl_requests.Session(impersonate="chrome124")
                res_cffi = s_cffi.get(url_api, headers=headers, timeout=10)
                if res_cffi.status_code == 200:
                    res = res_cffi
            except Exception:
                pass

        if res.status_code in (403, 429):
            if diagnostico is not None:
                diagnostico["waf_bloqueado"] = True
                diagnostico["http_status"] = res.status_code
            return variedades

        if res.status_code == 200:
            productos = res.json()
            if isinstance(productos, list):
                for p in productos:
                    raw_title = p.get("name", "")
                    if not es_producto_perfume_valido(raw_title, marca=marca or None, volumen_min_ml=25):
                        continue

                    clean_url = p.get("permalink", "")
                    prices = p.get("prices", {})
                    p_act = clean_digits(prices.get("price"))
                    p_norm = clean_digits(prices.get("regular_price")) or p_act
                    if not es_precio_valido(p_act):
                        continue

                    vol_encontrado = extraer_volumen_ml(raw_title) or extraer_volumen_ml(clean_url) or volumen_ml_defecto or 100
                    if vol_encontrado < 25:
                        continue

                    res_match = coincide_entidad_detallada(
                        titulo=raw_title,
                        perfume_nombre=perfume_nombre,
                        marca=marca,
                        concentracion=concentracion,
                        url=clean_url,
                        precio_candidato=p_act,
                        precio_referencia=precio_referencia,
                    )
                    if not res_match.coincide:
                        continue

                    formato_det = res_match.formato_detectado or detectar_formato_oferta(raw_title, clean_url)
                    clave_var = (vol_encontrado, formato_det)
                    if clave_var in vols_vistos:
                        continue

                    vols_vistos.add(clave_var)
                    en_stock = bool(p.get("is_in_stock", True))
                    norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act

                    variedades.append({
                        "exito": True,
                        "precio_actual": p_act,
                        "precio_normal": norm_valido,
                        "url": clean_url,
                        "en_stock": en_stock,
                        "volumen_ml": vol_encontrado,
                        "formato": formato_det,
                        "metodo": "WooCommerce Store API",
                    })
    except Exception as e:
        logger.debug(f"Aviso consultando WooCommerce {dominio} para '{perfume_nombre}': {e}")

    return variedades


def extraer_precio_woocommerce(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias: retorna la primera variedad o {exito: False}."""
    vars_found = extraer_variedades_woocommerce(session, dominio, perfume_nombre, marca, volumen_ml)
    if vars_found:
        return vars_found[0]
    return {"exito": False}


def extraer_variedades_falabella(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples presentaciones de Falabella Chile validando entidad en 12 capas
    y descartando vendedores Marketplace terceros no auditados.
    """
    headers = obtener_headers_navegador(referer="https://www.falabella.com/falabella-cl")
    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    # Intento 1: URL directa
    if url_directa and url_directa.startswith("http"):
        try:
            res = session.get(url_directa, headers=headers, timeout=10)
            if res.status_code in (403, 429) and diagnostico is not None:
                diagnostico["waf_bloqueado"] = True
                diagnostico["http_status"] = res.status_code
            elif res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tag = soup.find("script", id="__NEXT_DATA__")
                if tag and tag.string:
                    data = json.loads(tag.string)
                    pdata = data.get("props", {}).get("pageProps", {}).get("productData", {})
                    seller_direct = pdata.get("sellerName") or pdata.get("offeredBy")
                    is_prod_out = bool(pdata.get("isOutOfStock", False))
                    skus = pdata.get("variants", []) or pdata.get("skus", [])
                    prod_name = pdata.get("name", perfume_nombre)

                    if _es_vendedor_marketplace_no_verificado(seller_direct, marca, perfume_nombre):
                        logger.info(f"Omitiendo vendedor Marketplace Falabella no auditado: {seller_direct} ({prod_name})")
                    else:
                        res_head = coincide_entidad_detallada(
                            titulo=prod_name,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=url_directa,
                        )
                        if not res_head.coincide:
                            logger.warning(f"URL directa Falabella descartada ({res_head.motivo}): {prod_name} != {perfume_nombre}")
                        else:
                            for v in skus:
                                v_seller = v.get("sellerName") or seller_direct
                                if _es_vendedor_marketplace_no_verificado(v_seller, marca, perfume_nombre):
                                    continue
                                v_name = v.get("name") or prod_name
                                size_attr = v.get("attributes", {}).get("size")
                                vol = clean_digits(size_attr) if size_attr else extraer_volumen_ml(v_name)
                                if not vol or vol < 10 or vol > 1000:
                                    vol = extraer_volumen_ml(v_name) or volumen_ml_defecto or 100
                                if vol < 25:
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
                                if not es_precio_valido(p_act):
                                    continue
                                res_v = coincide_entidad_detallada(
                                    titulo=v_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=url_directa,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                if not res_v.coincide:
                                    continue
                                formato_det = res_v.formato_detectado or detectar_formato_oferta(v_name, url_directa)
                                clave_var = (vol, formato_det)
                                if clave_var in vols_vistos:
                                    continue
                                is_out = bool(v.get("isOutOfStock", False)) or is_prod_out or (v.get("isPurchaseable") is False)
                                vols_vistos.add(clave_var)
                                norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                variedades.append({
                                    "exito": True,
                                    "precio_actual": p_act,
                                    "precio_normal": norm_valido,
                                    "url": url_directa,
                                    "en_stock": not is_out,
                                    "volumen_ml": vol,
                                    "formato": formato_det,
                                    "metodo": "Falabella Direct Variants",
                                })
        except Exception as e:
            logger.debug(f"Aviso leyendo URL directa Falabella: {e}")

    if variedades and any(v.get("en_stock") for v in variedades):
        return variedades

    # Intento 2: Búsqueda dinámica en vivo en Falabella
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    q = urllib.parse.quote(query_str)
    search_url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    try:
        res_s = session.get(search_url, headers=headers, timeout=11)
        if res_s.status_code in (403, 429) and diagnostico is not None:
            diagnostico["waf_bloqueado"] = True
            diagnostico["http_status"] = res_s.status_code
        elif res_s.status_code == 200:
            soup_s = BeautifulSoup(res_s.text, "html.parser")
            tag_s = soup_s.find("script", id="__NEXT_DATA__")
            if tag_s and tag_s.string:
                data_s = json.loads(tag_s.string)
                results = data_s.get("props", {}).get("pageProps", {}).get("results", [])
                for r in results:
                    d_name = r.get("displayName", "")
                    prod_url = r.get("url", "")
                    r_seller = r.get("sellerName") or r.get("sellerId")
                    if _es_vendedor_marketplace_no_verificado(r_seller, marca, perfume_nombre):
                        continue
                    if not es_producto_perfume_valido(d_name, marca=marca or None, volumen_min_ml=25):
                        continue
                    res_card = coincide_entidad_detallada(
                        titulo=d_name,
                        perfume_nombre=perfume_nombre,
                        marca=marca,
                        concentracion=concentracion,
                        url=prod_url,
                    )
                    if not res_card.coincide:
                        continue
                    if prod_url and len(variedades) < 4:
                        try:
                            res_p = session.get(prod_url, headers=headers, timeout=9)
                            if res_p.status_code == 200:
                                soup_p = BeautifulSoup(res_p.text, "html.parser")
                                tag_p = soup_p.find("script", id="__NEXT_DATA__")
                                if tag_p and tag_p.string:
                                    data_p = json.loads(tag_p.string)
                                    pdata = data_p.get("props", {}).get("pageProps", {}).get("productData", {})
                                    p_seller = pdata.get("sellerName") or pdata.get("offeredBy") or r_seller
                                    if _es_vendedor_marketplace_no_verificado(p_seller, marca, perfume_nombre):
                                        continue
                                    is_prod_out = bool(pdata.get("isOutOfStock", False))
                                    skus = pdata.get("variants", []) or pdata.get("skus", [])
                                    for v in skus:
                                        v_name = v.get("name") or d_name
                                        size_attr = v.get("attributes", {}).get("size")
                                        vol = clean_digits(size_attr) if size_attr else extraer_volumen_ml(v_name)
                                        if not vol or vol < 10 or vol > 1000:
                                            vol = extraer_volumen_ml(v_name) or volumen_ml_defecto or 100
                                        if vol < 25:
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
                                        if not es_precio_valido(p_act):
                                            continue
                                        res_v = coincide_entidad_detallada(
                                            titulo=v_name,
                                            perfume_nombre=perfume_nombre,
                                            marca=marca,
                                            concentracion=concentracion,
                                            url=prod_url,
                                            precio_candidato=p_act,
                                            precio_referencia=precio_referencia,
                                        )
                                        if not res_v.coincide:
                                            continue
                                        formato_det = res_v.formato_detectado or detectar_formato_oferta(v_name, prod_url)
                                        clave_var = (vol, formato_det)
                                        if clave_var in vols_vistos:
                                            continue
                                        is_out = bool(v.get("isOutOfStock", False)) or is_prod_out or (v.get("isPurchaseable") is False)
                                        vols_vistos.add(clave_var)
                                        norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": norm_valido,
                                            "url": prod_url,
                                            "en_stock": not is_out,
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Falabella Live Variants",
                                        })
                        except Exception:
                            pass
                    if not variedades:
                        prices = r.get("prices", [])
                        if prices:
                            p_act = clean_digits(prices[0].get("price", ["0"])[0])
                            vol = extraer_volumen_ml(d_name) or volumen_ml_defecto or 100
                            if vol >= 25 and es_precio_valido(p_act):
                                res_sc = coincide_entidad_detallada(
                                    titulo=d_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=prod_url or search_url,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                if res_sc.coincide:
                                    formato_det = res_sc.formato_detectado or detectar_formato_oferta(d_name, prod_url or "")
                                    clave_var = (vol, formato_det)
                                    if clave_var not in vols_vistos:
                                        vols_vistos.add(clave_var)
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": p_act,
                                            "url": prod_url or search_url,
                                            "en_stock": not bool(r.get("isOutOfStock", False)),
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Falabella Search Card",
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
    volumen_ml: Optional[int] = None,
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
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae presentaciones y precios reales en Paris.cl validando entidad tanto en URLs
    directas como en búsqueda viva para impedir SKUs reciclados o cruzados.
    """
    headers = obtener_headers_navegador(referer="https://www.paris.cl/")
    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()

    # Intento 1: URL directa con validación estricta de entidad
    if url_directa and url_directa.startswith("http"):
        try:
            res = session.get(url_directa, headers=headers, timeout=10)
            if res.status_code in (403, 429) and diagnostico is not None:
                diagnostico["waf_bloqueado"] = True
                diagnostico["http_status"] = res.status_code
            elif res.status_code == 200:
                is_dead_paris = any(w in res.text.lower() for w in [
                    'página en construcción', 'pagina en construccion',
                    'mejorando tu experiencia', 'página no encontrada', 'no encontramos productos',
                ])
                if not is_dead_paris:
                    soup = BeautifulSoup(res.text, "html.parser")
                    for s_tag in soup.find_all("script", type="application/ld+json"):
                        if "Product" in s_tag.text:
                            d = json.loads(s_tag.text)
                            p_name = d.get("name", perfume_nombre)
                            if not es_producto_perfume_valido(p_name, marca=marca or None, volumen_min_ml=25):
                                continue
                            offers = d.get("offers", [])
                            off = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                            p_raw = off.get("price")
                            if p_raw:
                                p_act = clean_digits(p_raw)
                                vol = extraer_volumen_ml(p_name) or volumen_ml_defecto or 100
                                if vol < 25 or not es_precio_valido(p_act):
                                    continue
                                res_match = coincide_entidad_detallada(
                                    titulo=p_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=url_directa,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                if not res_match.coincide:
                                    logger.warning(f"URL directa Paris descartada ({res_match.motivo}): {p_name} != {perfume_nombre}")
                                    continue
                                formato_det = res_match.formato_detectado or detectar_formato_oferta(p_name, url_directa)
                                clave_var = (vol, formato_det)
                                if clave_var not in vols_vistos:
                                    vols_vistos.add(clave_var)
                                    avail = str(off.get("availability", "")).lower()
                                    en_stock = False if ("outofstock" in avail or "agotado" in avail) else True
                                    variedades.append({
                                        "exito": True,
                                        "precio_actual": p_act,
                                        "precio_normal": p_act,
                                        "url": url_directa,
                                        "en_stock": en_stock,
                                        "volumen_ml": vol,
                                        "formato": formato_det,
                                        "metodo": "Paris Schema.org Direct",
                                    })
        except Exception as e:
            logger.debug(f"Aviso leyendo URL directa Paris: {e}")

    if variedades:
        return variedades

    # Intento 2: Búsqueda dinámica en vivo en Paris
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    q = urllib.parse.quote(query_str)
    url_search = f"https://www.paris.cl/search?q={q}"
    try:
        res_s = session.get(url_search, headers=headers, timeout=10)
        if res_s.status_code in (403, 429) and diagnostico is not None:
            diagnostico["waf_bloqueado"] = True
            diagnostico["http_status"] = res_s.status_code
        elif res_s.status_code == 200:
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
                                if not es_producto_perfume_valido(p_name, marca=marca or None, volumen_min_ml=25):
                                    continue
                                offers = d.get("offers", [])
                                off = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                                p_raw = off.get("price")
                                if p_raw:
                                    p_act = clean_digits(p_raw)
                                    vol = extraer_volumen_ml(p_name) or volumen_ml_defecto or 100
                                    if vol < 25 or not es_precio_valido(p_act):
                                        continue
                                    res_match = coincide_entidad_detallada(
                                        titulo=p_name,
                                        perfume_nombre=perfume_nombre,
                                        marca=marca,
                                        concentracion=concentracion,
                                        url=lk,
                                        precio_candidato=p_act,
                                        precio_referencia=precio_referencia,
                                    )
                                    if not res_match.coincide:
                                        continue
                                    formato_det = res_match.formato_detectado or detectar_formato_oferta(p_name, lk)
                                    clave_var = (vol, formato_det)
                                    if clave_var not in vols_vistos:
                                        vols_vistos.add(clave_var)
                                        avail = str(off.get("availability", "")).lower()
                                        en_stock = False if ("outofstock" in avail or "agotado" in avail) else True
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": p_act,
                                            "url": lk,
                                            "en_stock": en_stock,
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Paris Live Schema.org",
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
    volumen_ml: Optional[int] = None,
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
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples presentaciones de Ripley Chile validando entidad, vendedores Marketplace
    y distinguiendo bloqueos HTTP 403 WAF de falta real de stock.
    """
    variedades: List[Dict[str, Any]] = []
    vols_vistos = set()
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    q = urllib.parse.quote(query_str)
    url_search = f"https://simple.ripley.cl/search/{q}"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": "https://simple.ripley.cl/",
    }

    try:
        c_session = None
        if curl_requests is not None:
            c_session = curl_requests.Session(impersonate="chrome124")
            res = c_session.get(url_search, headers=headers, timeout=14)
        else:
            res = session.get(url_search, headers=obtener_headers_navegador(), timeout=10)

        if res.status_code in (403, 429):
            if diagnostico is not None:
                diagnostico["waf_bloqueado"] = True
                diagnostico["http_status"] = res.status_code
        elif res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            tag = soup.find("script", id="__NEXT_DATA__")
            if tag and tag.text:
                data = json.loads(tag.text)
                prods = data.get("props", {}).get("pageProps", {}).get("findabilityProps", {}).get("data", {}).get("products", [])

                candidatos = []
                for p in prods:
                    d_name = p.get("name", "")
                    r_seller = p.get("marketplaceSeller") or p.get("sellerName") or p.get("seller")
                    if _es_vendedor_marketplace_no_verificado(r_seller, marca, perfume_nombre):
                        continue
                    p_id = p.get("parentProductID") or p.get("sku")
                    slug = p.get("url") or p_id
                    pdp_url = (
                        f"https://simple.ripley.cl/{slug.lstrip('/')}"
                        if slug and not slug.startswith("http")
                        else (slug or f"https://simple.ripley.cl/{p_id}")
                    )
                    if not es_producto_perfume_valido(d_name, marca=marca or None, volumen_min_ml=25):
                        continue
                    res_cand = coincide_entidad_detallada(
                        titulo=d_name,
                        perfume_nombre=perfume_nombre,
                        marca=marca,
                        concentracion=concentracion,
                        url=pdp_url,
                    )
                    if not res_cand.coincide:
                        continue
                    candidatos.append((p, pdp_url))

                for p, pdp_url in candidatos[:2]:
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
                                    p_seller = prod_info.get("sellerName") or prod_info.get("marketplaceSeller")
                                    if _es_vendedor_marketplace_no_verificado(p_seller, marca, perfume_nombre):
                                        continue
                                    variants = prod_info.get("variants", [])
                                    pdp_title = prod_info.get("name", p.get("name", ""))

                                    for v in variants:
                                        price_obj = v.get("price", {})
                                        sale_p = price_obj.get("sale", {}).get("valueNumber") or price_obj.get("master", {}).get("valueNumber")
                                        norm_p = price_obj.get("master", {}).get("valueNumber") or sale_p
                                        if not sale_p or not es_precio_valido(sale_p):
                                            continue

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
                                            vol = extraer_volumen_ml(pdp_title) or volumen_ml_defecto or 100
                                        if vol < 25:
                                            continue

                                        res_v = coincide_entidad_detallada(
                                            titulo=pdp_title,
                                            perfume_nombre=perfume_nombre,
                                            marca=marca,
                                            concentracion=concentracion,
                                            url=pdp_url,
                                            precio_candidato=int(sale_p),
                                            precio_referencia=precio_referencia,
                                        )
                                        if not res_v.coincide:
                                            continue

                                        formato_det = res_v.formato_detectado or detectar_formato_oferta(pdp_title, pdp_url)
                                        clave_var = (vol, formato_det)
                                        if clave_var in vols_vistos:
                                            continue
                                        vols_vistos.add(clave_var)

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
                                            "formato": formato_det,
                                            "metodo": "Ripley Live PDP Variants",
                                        })
                        except Exception as e_pdp:
                            logger.debug(f"Aviso leyendo PDP Ripley {pdp_url}: {e_pdp}")

                    if not variedades:
                        p_act = p.get("priceNumber", 0)
                        p_norm = p.get("masterPriceNumber", p_act) or p_act
                        if p_act and es_precio_valido(p_act):
                            p_title = p.get("name", "")
                            vol = extraer_volumen_ml(p_title) or volumen_ml_defecto or 100
                            if vol >= 25:
                                res_sc = coincide_entidad_detallada(
                                    titulo=p_title,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=pdp_url or url_search,
                                    precio_candidato=int(p_act),
                                    precio_referencia=precio_referencia,
                                )
                                if res_sc.coincide:
                                    formato_det = res_sc.formato_detectado or detectar_formato_oferta(p_title, pdp_url or "")
                                    clave_var = (vol, formato_det)
                                    if clave_var not in vols_vistos:
                                        vols_vistos.add(clave_var)
                                        norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": norm_valido,
                                            "url": pdp_url or url_search,
                                            "en_stock": bool(p.get("inStock", True)),
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Ripley Chrome Search Card",
                                        })
    except Exception as e:
        logger.warning(f"Error consultando Ripley para '{perfume_nombre}': {e}")

    if not variedades and url_directa:
        res_old = extraer_precio_ripley(
            session,
            url_directa,
            perfume_nombre,
            volumen_ml_defecto,
            marca=marca,
            concentracion=concentracion,
            precio_referencia=precio_referencia,
        )
        if res_old.get("waf_bloqueado") and diagnostico is not None:
            diagnostico["waf_bloqueado"] = True
        if res_old.get("exito"):
            variedades.append(res_old)

    return variedades


def extraer_precio_ripley(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None,
    marca: str = "",
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Extrae precio y stock de Ripley Chile combinando Schema.org y selectores DOM,
    validando entidad en auto-sanación 404 y manejando protecciones WAF (HTTP 403).
    """
    headers = obtener_headers_navegador(referer="https://simple.ripley.cl/")
    url_a_probar = url_directa

    # Intento 1: Ficha directa
    try:
        res = session.get(url_a_probar, headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"Fallo conexión Ripley direct: {e}")
        res = None

    if res and res.status_code in (403, 429):
        return {
            "exito": False,
            "waf_bloqueado": True,
            "motivo": f"Ripley protegido por Cloudflare WAF (HTTP {res.status_code})",
        }

    # Intento 2: Si dio 404, auto-sanar validando entidad antes de adoptar el enlace nuevo
    if not res or res.status_code != 200:
        query_str = (
            f"{marca} {perfume_nombre}".strip()
            if (marca and marca.lower() not in perfume_nombre.lower())
            else perfume_nombre.strip()
        )
        q = urllib.parse.quote(query_str)
        try:
            res_s = session.get(f"https://simple.ripley.cl/search/{q}", headers=headers, timeout=10)
            if res_s.status_code in (403, 429):
                return {
                    "exito": False,
                    "waf_bloqueado": True,
                    "motivo": f"Ripley protegido por Cloudflare WAF (HTTP {res_s.status_code})",
                }
            if res_s.status_code == 200:
                soup_s = BeautifulSoup(res_s.text, "html.parser")
                tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", perfume_nombre).split() if len(t) >= 3]
                for a in soup_s.find_all("a", href=True):
                    h = a.get("href", "")
                    if not h.endswith("p"):
                        continue
                    cand_url = h.split("?")[0] if h.startswith("http") else "https://simple.ripley.cl" + h.split("?")[0]
                    anchor_txt = a.get_text(" ", strip=True)
                    if anchor_txt and len(anchor_txt) >= 4:
                        res_a = coincide_entidad_detallada(
                            titulo=anchor_txt,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=cand_url,
                        )
                        if not res_a.coincide:
                            continue
                    elif tokens and not all(tok in h.lower() for tok in tokens[:2]):
                        continue
                    url_a_probar = cand_url
                    res = session.get(url_a_probar, headers=headers, timeout=9)
                    break
        except Exception as e:
            logger.warning(f"Fallo auto-sanación Ripley: {e}")

    # Paso 3: Parsear ficha del producto con validación de entidad
    if res and res.status_code == 200:
        try:
            soup = BeautifulSoup(res.text, "html.parser")
            blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', res.text, re.DOTALL)
            for b in blocks:
                if '"@type":"Product"' in b or '"@type": "Product"' in b:
                    try:
                        d = json.loads(b)
                        p_name = d.get("name", "")
                        offers = d.get("offers", {})
                        if isinstance(offers, dict) and "price" in offers:
                            p_act = clean_digits(offers["price"])
                            if not es_precio_valido(p_act):
                                continue
                            if p_name:
                                res_ld = coincide_entidad_detallada(
                                    titulo=p_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=url_a_probar,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                if not res_ld.coincide:
                                    continue
                                vol_det = extraer_volumen_ml(p_name) or volumen_ml or 100
                                fmt_det = res_ld.formato_detectado or detectar_formato_oferta(p_name, url_a_probar)
                            else:
                                vol_det = volumen_ml or 100
                                fmt_det = detectar_formato_oferta(perfume_nombre, url_a_probar)
                            if vol_det < 25:
                                continue
                            avail_r = str(offers.get("availability", "")).lower()
                            en_stock_r = False if ("outofstock" in avail_r or "agotado" in avail_r) else True
                            return {
                                "exito": True,
                                "precio_actual": p_act,
                                "precio_normal": p_act,
                                "url": url_a_probar,
                                "en_stock": en_stock_r,
                                "volumen_ml": vol_det,
                                "formato": fmt_det,
                                "metodo": "Ripley Schema.org",
                            }
                    except Exception:
                        pass

            p_val = soup.find(class_=lambda c: c and "price-value" in c)
            if p_val:
                p_act = clean_digits(p_val.get_text())
                agotado_dom = bool(soup.find(string=re.compile(r"agotado|sin stock", re.I)))
                if es_precio_valido(p_act):
                    dom_title_el = soup.find("h1") or soup.find("title")
                    dom_title = dom_title_el.get_text(" ", strip=True) if dom_title_el else ""
                    if dom_title:
                        res_dom = coincide_entidad_detallada(
                            titulo=dom_title,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=url_a_probar,
                            precio_candidato=p_act,
                            precio_referencia=precio_referencia,
                        )
                        if not res_dom.coincide:
                            return {"exito": False, "motivo": res_dom.motivo}
                        vol_dom = extraer_volumen_ml(dom_title) or volumen_ml or 100
                        fmt_dom = res_dom.formato_detectado or detectar_formato_oferta(dom_title, url_a_probar)
                    else:
                        vol_dom = volumen_ml or 100
                        fmt_dom = detectar_formato_oferta(perfume_nombre, url_a_probar)
                    if vol_dom >= 25:
                        return {
                            "exito": True,
                            "precio_actual": p_act,
                            "precio_normal": p_act,
                            "url": url_a_probar,
                            "en_stock": not agotado_dom,
                            "volumen_ml": vol_dom,
                            "formato": fmt_dom,
                            "metodo": "Ripley DOM Price",
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
# MOTOR PRINCIPAL DE EJECUCIÓN ETL (ARQUITECTURA DE ROTACIONES LRU)
# =============================================================================

def _combinar_tiendas_stats(
    stats_list: List[Dict[str, Dict[str, Any]]],
    tiendas_db: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Combina métricas agregadas de comercios auditados a lo largo de múltiples rotaciones."""
    consolidado = {
        t["nombre"]: {
            "consultas": 0,
            "exitos_en_vivo": 0,
            "fallbacks_seguridad": 0,
            "bloqueos_waf": 0,
            "trust_score": t.get("trust_score", 90),
        }
        for t in tiendas_db
    }
    for st in stats_list:
        for t_nom, vals in st.items():
            if t_nom in consolidado:
                consolidado[t_nom]["consultas"] += vals.get("consultas", 0)
                consolidado[t_nom]["exitos_en_vivo"] += vals.get("exitos_en_vivo", 0)
                consolidado[t_nom]["fallbacks_seguridad"] += vals.get("fallbacks_seguridad", 0)
                consolidado[t_nom]["bloqueos_waf"] += vals.get("bloqueos_waf", 0)
    return consolidado


def auditar_lote_perfumes(
    perfumes_lote: List[Dict[str, Any]],
    tiendas_db: List[Dict[str, Any]],
    urls_conocidas_map: Dict[Tuple[int, int], Tuple[str, int]],
    session: requests.Session,
    rotacion_idx: int = 1,
    total_rotaciones: int = 1,
    total_catalogo: int = 0,
) -> Dict[str, Any]:
    """
    Ejecuta la auditoría en vivo para un subconjunto (lote/rotación) específico de perfumes.
    Cada lote crea y cierra su propio `scraping_run_id` para trazabilidad atómica y persistencia
    resiliente ante desconexiones, cancelaciones o timeouts en runners de CI/CD.
    """
    inicio = time.time()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    msg_inicio = (
        f"Rotación {rotacion_idx}/{total_rotaciones}: auditando lote de {len(perfumes_lote)} perfumes "
        f"(catálogo total: {total_catalogo})"
    )
    logger.info(f"Iniciando {msg_inicio}")
    run_id = iniciar_scraping_run(
        tipo_scraper="Scraper Periódico Precios y Stock",
        mensaje_detalle=msg_inicio,
    )

    actualizaciones = 0
    ofertas_nuevas = 0
    cambios_precio = 0
    cambios_stock = 0
    cambios_url = 0
    omitidos = 0
    bloqueos_waf = 0
    errores: List[str] = []
    detalle_precios: List[Dict[str, Any]] = []
    tiendas_stats: Dict[str, Dict[str, Any]] = {
        t["nombre"]: {
            "consultas": 0,
            "exitos_en_vivo": 0,
            "fallbacks_seguridad": 0,
            "bloqueos_waf": 0,
            "trust_score": t.get("trust_score", 90),
        }
        for t in tiendas_db
    }

    for p in perfumes_lote:
        p_id = p["id"]
        p_nom = p["nombre"]
        p_marca = p["marca"]
        p_genero = p.get("genero") or "Unisex"
        p_tipo = p.get("tipo") or ""
        p_ref = p.get("precio_referencia")

        logger.info(f"[Rotación {rotacion_idx}/{total_rotaciones}] Auditando: {p_nom} ({p_marca}) [{p_tipo or 'N/A'} · {p_genero}]")
        _GENERO_ESPERADO_CTX.set(p_genero)

        for tienda in tiendas_db:
            t_id = tienda["id"]
            t_nom = tienda["nombre"]

            if not tienda_comercializa_marca(t_nom, p_marca):
                omitidos += 1
                continue

            url_directa_info = obtener_url_directa_tienda(p_id, t_nom)
            if url_directa_info:
                url_directa_guardada = url_directa_info[0]
                vol_ml_base = url_directa_info[3] or 100
            elif (int(p_id), int(t_id)) in urls_conocidas_map:
                url_directa_guardada, vol_ml_base = urls_conocidas_map[(int(p_id), int(t_id))]
            else:
                url_directa_guardada = None
                vol_ml_base = 100

            tiendas_stats[t_nom]["consultas"] += 1
            time.sleep(random.uniform(0.18, 0.45))

            diag: Dict[str, Any] = {}
            try:
                lista_variedades: List[Dict[str, Any]] = []

                if t_nom in TIENDAS_SHOPIFY:
                    dominio = TIENDAS_SHOPIFY[t_nom]
                    lista_variedades = extraer_variedades_shopify(
                        session=session,
                        dominio=dominio,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo,
                        precio_referencia=p_ref,
                        diagnostico=diag,
                    )
                elif t_nom in TIENDAS_WOOCOMMERCE:
                    dominio = TIENDAS_WOOCOMMERCE[t_nom]
                    lista_variedades = extraer_variedades_woocommerce(
                        session=session,
                        dominio=dominio,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo,
                        precio_referencia=p_ref,
                        diagnostico=diag,
                    )
                elif "falabella" in t_nom.lower():
                    lista_variedades = extraer_variedades_falabella(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo,
                        precio_referencia=p_ref,
                        diagnostico=diag,
                    )
                elif "paris" in t_nom.lower():
                    lista_variedades = extraer_variedades_paris(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo,
                        precio_referencia=p_ref,
                        diagnostico=diag,
                    )
                elif "ripley" in t_nom.lower():
                    lista_variedades = extraer_variedades_ripley(
                        session=session,
                        url_directa=url_directa_guardada,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=vol_ml_base,
                        concentracion=p_tipo,
                        precio_referencia=p_ref,
                        diagnostico=diag,
                    )
                else:
                    omitidos += 1
                    continue

                if lista_variedades:
                    for var_data in lista_variedades:
                        if not var_data.get("exito"):
                            continue
                        precio_actual_final = int(var_data["precio_actual"])
                        if not es_precio_valido(precio_actual_final):
                            continue
                        precio_normal_final = int(var_data.get("precio_normal") or precio_actual_final)
                        url_final = var_data["url"]
                        vol_final = int(var_data.get("volumen_ml") or vol_ml_base or 100)
                        if vol_final < 25:
                            continue
                        stock_final = bool(var_data.get("en_stock", True))
                        formato_final = str(var_data.get("formato") or detectar_formato_oferta(p_nom, url_final))

                        res_obs = registrar_observacion_oferta({
                            "perfume_id": p_id,
                            "tienda_id": t_id,
                            "precio_actual": precio_actual_final,
                            "precio_normal": precio_normal_final,
                            "en_stock": stock_final,
                            "url_producto": url_final,
                            "volumen_ml": vol_final,
                            "formato": formato_final,
                            "scraping_run_id": run_id,
                        })
                        res_tipo = res_obs.get("resultado")
                        if res_tipo in ("creada", "actualizada"):
                            actualizaciones += 1
                            if res_tipo == "creada":
                                ofertas_nuevas += 1
                            c_mods = res_obs.get("campos_modificados") or []
                            if "precio_actual" in c_mods:
                                cambios_precio += 1
                            if "en_stock" in c_mods:
                                cambios_stock += 1
                            if "url_producto" in c_mods:
                                cambios_url += 1

                        tiendas_stats[t_nom]["exitos_en_vivo"] += 1
                        detalle_precios.append({
                            "perfume": p_nom,
                            "tienda": t_nom,
                            "precio_actual": precio_actual_final,
                            "precio_normal": precio_normal_final,
                            "tiene_descuento": bool(precio_normal_final > precio_actual_final),
                            "origen": var_data.get("metodo", "Extracción en Vivo"),
                            "volumen_ml": vol_final,
                            "formato": formato_final,
                            "en_stock": stock_final,
                        })
                        logger.info(
                            f"  -> [{t_nom}] EN VIVO: ${precio_actual_final:,} "
                            f"(Normal: ${precio_normal_final:,}) | {vol_final}ml ({formato_final}) | stock: {stock_final}"
                        )
                elif diag.get("waf_bloqueado"):
                    bloqueos_waf += 1
                    tiendas_stats[t_nom]["bloqueos_waf"] += 1
                    logger.info(
                        f"  -> [{t_nom}] Bloqueo temporal WAF (HTTP {diag.get('http_status', 403)}). "
                        "Se preserva última oferta sin penalizar fallos consecutivos."
                    )
                else:
                    motivo_fallo = f"Sin disponibilidad confirmada en {t_nom}"
                    registrar_fallo_scraping(
                        tienda_id=t_id,
                        perfume_id=p_id,
                        mensaje=motivo_fallo,
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
                        mensaje=str(ex),
                    )
                except Exception:
                    pass

    duracion = round(time.time() - inicio, 2)
    estado_general = "EXITOSO" if not errores else ("DEGRADADO" if actualizaciones > 0 else "FALLIDO")

    finalizar_scraping_run(
        run_id=run_id,
        estado="completado" if estado_general == "EXITOSO" else estado_general.lower(),
        productos_procesados=len(perfumes_lote),
        ofertas_nuevas=ofertas_nuevas,
        cambios_precio=cambios_precio,
        cambios_stock=cambios_stock,
        cambios_url=cambios_url,
        errores=len(errores),
        mensaje_detalle=(
            f"Rotación {rotacion_idx}/{total_rotaciones}: auditados {len(perfumes_lote)} perfumes en {duracion}s: "
            f"{actualizaciones} actualizaciones, {bloqueos_waf} bloqueos WAF."
        ),
    )

    return {
        "actualizaciones": actualizaciones,
        "fecha": ahora,
        "duracion_segundos": duracion,
        "metadata": {
            "version_etl": "3.3.0",
            "sistema": "PerfumeTrending Professional Anti-Bot ETL (Batch)",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado_general,
            "scraping_run_id": run_id,
            "rotacion_idx": rotacion_idx,
            "total_rotaciones": total_rotaciones,
        },
        "metricas": {
            "total_perfumes_catalogo": total_catalogo,
            "perfumes_auditados": len(perfumes_lote),
            "total_tiendas_registradas": len(tiendas_db),
            "precios_actualizados": actualizaciones,
            "ofertas_nuevas": ofertas_nuevas,
            "cambios_precio": cambios_precio,
            "cambios_stock": cambios_stock,
            "cambios_url": cambios_url,
            "bloqueos_waf": bloqueos_waf,
            "exclusiones_marca": omitidos,
            "errores_totales": len(errores),
        },
        "estadisticas_tiendas": tiendas_stats,
        "muestra_capturas": detalle_precios[:15],
        "errores": errores,
    }


def ejecutar_ciclo_scraping_y_descubrimiento(
    batch_size: Optional[int] = None,
    rotations: Optional[int] = None,
    delay_between_rotations: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Orquesta el ciclo de extracción ETL en rotaciones sucesivas priorizadas mediante cola LRU:
    1. Recupera catálogo completo y el mapa de última verificación exitosa (`ultima_verificacion_exitosa`).
    2. Ordena los perfumes con política LRU (los nunca auditados o con auditoría más antigua primero).
    3. Segmenta el catálogo en lotes de tamaño `batch_size` (por defecto 500 o variable de entorno `SCRAPER_BATCH_SIZE`).
    4. Ejecuta consecutivamente las rotaciones solicitadas (o todas las necesarias si `rotations` es 0 o None).
       Entre cada rotación, realiza una pausa configurable de cooldown (`delay_between_rotations` segundos).
    5. Cada lote registra su propia transacción en `scraping_runs` y actualiza inmediatamente la BD,
       asegurando tolerancia absoluta a timeouts y cero pérdida de trabajo.
    """
    init_db()
    inicio_global = time.time()
    ahora_global = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Resolución de parámetros (CLI / argumento / entorno / defecto)
    try:
        bs_cfg = batch_size if batch_size is not None else int(os.environ.get("SCRAPER_BATCH_SIZE", 500))
    except (ValueError, TypeError):
        bs_cfg = 500
    effective_batch_size = max(1, bs_cfg)

    try:
        rot_cfg = rotations if rotations is not None else int(os.environ.get("SCRAPER_ROTATIONS", 0))
    except (ValueError, TypeError):
        rot_cfg = 0

    try:
        delay_cfg = delay_between_rotations if delay_between_rotations is not None else int(os.environ.get("SCRAPER_DELAY_ROTATIONS", 10))
    except (ValueError, TypeError):
        delay_cfg = 10

    session = crear_sesion_robusta()

    perfumes_db: List[Dict[str, Any]] = []
    tiendas_db: List[Dict[str, Any]] = []
    urls_conocidas_map: Dict[Tuple[int, int], Tuple[str, int]] = {}
    perfume_last_verified: Dict[int, str] = {}

    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        try:
            perfumes_db = _fetch_all_rows(
                lambda off, lim: (
                    sb.table("perfumes")
                    .select("id, nombre, marca, genero, tipo, precio_referencia, es_arabe")
                    .order("id", desc=False)
                    .range(off, off + lim - 1)
                ),
                page_size=1000,
            )
            resp_t = sb.table("tiendas").select("id, nombre, url_base, trust_score").order("id").execute()
            tiendas_db = resp_t.data or []

            variantes_rows = _fetch_all_rows(
                lambda off, lim: (
                    sb.table("variantes_perfume")
                    .select("id, perfume_id, volumen_ml, formato")
                    .order("id", desc=False)
                    .range(off, off + lim - 1)
                ),
                page_size=1000,
            )
            precargar_cache_variantes_supabase(variantes_rows)
            var_to_perf: Dict[int, Tuple[int, int, str]] = {}
            for vr in variantes_rows:
                try:
                    var_to_perf[int(vr["id"])] = (
                        int(vr["perfume_id"]),
                        int(round(float(vr.get("volumen_ml") or 100))),
                        str(vr.get("formato") or "regular").lower(),
                    )
                except Exception:
                    pass

            ofertas_rows = _fetch_all_rows(
                lambda off, lim: (
                    sb.table("ofertas_actuales")
                    .select("variante_id, tienda_id, url_producto, estado, ultima_verificacion_exitosa")
                    .neq("estado", "requiere_revision")
                    .order("id", desc=False)
                    .range(off, off + lim - 1)
                ),
                page_size=1000,
            )
            for oa in ofertas_rows:
                v_info = var_to_perf.get(int(oa.get("variante_id") or 0))
                if v_info:
                    pid = v_info[0]
                    ts = oa.get("ultima_verificacion_exitosa")
                    if ts:
                        if pid not in perfume_last_verified or ts > perfume_last_verified[pid]:
                            perfume_last_verified[pid] = ts
                    u_prod = str(oa.get("url_producto") or "").strip()
                    if u_prod.startswith("http") and v_info[2] != "tester":
                        k_pt = (pid, int(oa["tienda_id"]))
                        if k_pt not in urls_conocidas_map:
                            urls_conocidas_map[k_pt] = (u_prod, v_info[1])

            logger.info(
                f"Catálogo cargado desde Supabase Cloud: {len(perfumes_db)} perfumes, "
                f"{len(tiendas_db)} tiendas, {len(urls_conocidas_map)} enlaces directos en caché."
            )
        except Exception as e:
            logger.warning(f"Aviso consultando catálogo en Supabase ({e}), recurriendo a SQLite local.")

    if not perfumes_db or not tiendas_db:
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, marca, genero, tipo, precio_referencia, es_arabe FROM perfumes ORDER BY id ASC;")
        perfumes_db = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, nombre, url_base, trust_score FROM tiendas ORDER BY id ASC;")
        tiendas_db = [dict(r) for r in cursor.fetchall()]
        cursor.execute(
            """
            SELECT vp.perfume_id, oa.tienda_id, oa.url_producto, 
                   CAST(ROUND(COALESCE(vp.volumen_ml, 100)) AS INTEGER) as vol_ml,
                   oa.ultima_verificacion_exitosa
            FROM ofertas_actuales oa
            JOIN variantes_perfume vp ON vp.id = oa.variante_id
            WHERE oa.url_producto IS NOT NULL AND oa.estado != 'requiere_revision' AND COALESCE(vp.formato, 'regular') != 'tester';
            """
        )
        for r in cursor.fetchall():
            pid = int(r["perfume_id"])
            k_pt = (pid, int(r["tienda_id"]))
            if k_pt not in urls_conocidas_map and str(r["url_producto"]).startswith("http"):
                urls_conocidas_map[k_pt] = (str(r["url_producto"]), int(r["vol_ml"] or 100))
            ts = r["ultima_verificacion_exitosa"] if isinstance(r, dict) else r.get("ultima_verificacion_exitosa")
            if ts:
                if pid not in perfume_last_verified or ts > perfume_last_verified[pid]:
                    perfume_last_verified[pid] = ts
        conn.close()
        logger.info(f"Catálogo cargado desde SQLite local: {len(perfumes_db)} perfumes, {len(tiendas_db)} tiendas.")

    # Priorización inteligente mediante cola LRU:
    # 1. Perfumes sin verificación previa o nuevos (False, "")
    # 2. Perfumes con auditoría más lejana en el tiempo (True, "2026-10-14...")
    # 3. Perfumes auditados recientemente quedan al final de la cola (True, "2026-10-28...")
    perfumes_db.sort(
        key=lambda p: (
            perfume_last_verified.get(p["id"]) is not None,
            perfume_last_verified.get(p["id"]) or "",
        )
    )

    limit_env = os.environ.get("SCRAPER_LIMIT_PERFUMES")
    if limit_env and limit_env.isdigit():
        max_p = int(limit_env)
        perfumes_db = perfumes_db[:max_p]
        logger.info(f"Modo de prueba activo (SCRAPER_LIMIT_PERFUMES={max_p}): auditando {len(perfumes_db)} perfumes.")

    total_perfumes = len(perfumes_db)
    max_posibles_rotaciones = max(1, math.ceil(total_perfumes / effective_batch_size))
    if rot_cfg <= 0:
        num_rotaciones = max_posibles_rotaciones
    else:
        num_rotaciones = min(rot_cfg, max_posibles_rotaciones)

    logger.info(
        f"Planificando ejecución ETL por rotaciones: {total_perfumes} perfumes totales, "
        f"{num_rotaciones} rotación(es) planificada(s) de hasta {effective_batch_size} perfumes c/u "
        f"(cooldown entre rotaciones: {delay_cfg}s)."
    )

    consolidado_reportes: List[Dict[str, Any]] = []
    total_actualizaciones = 0
    total_ofertas_nuevas = 0
    total_cambios_precio = 0
    total_cambios_stock = 0
    total_cambios_url = 0
    total_bloqueos_waf = 0
    total_exclusiones = 0
    total_errores: List[str] = []
    muestras_consolidadas: List[Dict[str, Any]] = []
    reporte_resultado: Dict[str, Any] = {}

    for rot_idx in range(1, num_rotaciones + 1):
        idx_start = (rot_idx - 1) * effective_batch_size
        idx_end = min(idx_start + effective_batch_size, total_perfumes)
        lote = perfumes_db[idx_start:idx_end]

        sep_line = "=" * 70
        logger.info(
            f"\n{sep_line}\n"
            f"INICIANDO ROTACIÓN {rot_idx}/{num_rotaciones} "
            f"({len(lote)} perfumes: rango [{idx_start}:{idx_end}] de {total_perfumes})\n"
            f"{sep_line}"
        )

        rep_lote = auditar_lote_perfumes(
            perfumes_lote=lote,
            tiendas_db=tiendas_db,
            urls_conocidas_map=urls_conocidas_map,
            session=session,
            rotacion_idx=rot_idx,
            total_rotaciones=num_rotaciones,
            total_catalogo=total_perfumes,
        )

        consolidado_reportes.append(rep_lote)
        m_lote = rep_lote["metricas"]
        total_actualizaciones += m_lote["precios_actualizados"]
        total_ofertas_nuevas += m_lote["ofertas_nuevas"]
        total_cambios_precio += m_lote["cambios_precio"]
        total_cambios_stock += m_lote["cambios_stock"]
        total_cambios_url += m_lote["cambios_url"]
        total_bloqueos_waf += m_lote["bloqueos_waf"]
        total_exclusiones += m_lote.get("exclusiones_marca", 0)
        total_errores.extend(rep_lote.get("errores", []))
        muestras_consolidadas.extend(rep_lote.get("muestra_capturas", []))

        duracion_parcial = round(time.time() - inicio_global, 2)
        estado_global = "EXITOSO" if not total_errores else ("DEGRADADO" if total_actualizaciones > 0 else "FALLIDO")

        # Guardar reporte consolidado intermedio de auditoría tras cada rotación
        reporte_resultado = {
            "actualizaciones": total_actualizaciones,
            "fecha": ahora_global,
            "duracion_segundos": duracion_parcial,
            "metadata": {
                "version_etl": "3.3.0",
                "sistema": "PerfumeTrending Professional Anti-Bot ETL (Multi-Rotation LRU)",
                "fecha_ejecucion": ahora_global,
                "duracion_segundos": duracion_parcial,
                "estado": estado_global,
                "rotaciones_completadas": rot_idx,
                "total_rotaciones_planificadas": num_rotaciones,
                "tamano_lote": effective_batch_size,
            },
            "metricas": {
                "total_perfumes_catalogo": total_perfumes,
                "perfumes_auditados": idx_end,
                "total_tiendas_registradas": len(tiendas_db),
                "precios_actualizados": total_actualizaciones,
                "ofertas_nuevas": total_ofertas_nuevas,
                "cambios_precio": total_cambios_precio,
                "cambios_stock": total_cambios_stock,
                "cambios_url": total_cambios_url,
                "bloqueos_waf": total_bloqueos_waf,
                "exclusiones_marca": total_exclusiones,
                "errores_totales": len(total_errores),
            },
            "estadisticas_tiendas": _combinar_tiendas_stats(
                [r["estadisticas_tiendas"] for r in consolidado_reportes], tiendas_db
            ),
            "muestra_capturas": muestras_consolidadas[:25],
            "rotaciones_detalle": [
                {
                    "rotacion": r["metadata"].get("rotacion_idx", i + 1),
                    "scraping_run_id": r["metadata"].get("scraping_run_id"),
                    "perfumes": r["metricas"]["perfumes_auditados"],
                    "actualizaciones": r["metricas"]["precios_actualizados"],
                    "duracion_segundos": r["duracion_segundos"],
                    "estado": r["metadata"]["estado"],
                }
                for i, r in enumerate(consolidado_reportes)
            ],
            "errores": total_errores[:20],
        }
        guardar_reporte_auditoria(reporte_resultado)

        logger.info(
            f"=== ROTACIÓN {rot_idx}/{num_rotaciones} COMPLETADA "
            f"({m_lote['precios_actualizados']} precios actualizados en {rep_lote['duracion_segundos']}s) ==="
        )

        if rot_idx < num_rotaciones:
            logger.info(f"Cooldown de {delay_cfg}s antes de iniciar la rotación {rot_idx + 1}/{num_rotaciones}...")
            time.sleep(delay_cfg)

    duracion_final = round(time.time() - inicio_global, 2)
    sep_line = "=" * 70
    logger.info(
        f"\n{sep_line}\n"
        f"CICLO ETL COMPLETO: {num_rotaciones} rotación(es) en {duracion_final}s | "
        f"{total_actualizaciones} precios sincronizados | Estado: {reporte_resultado.get('metadata', {}).get('estado', 'EXITOSO')}\n"
        f"{sep_line}"
    )
    return reporte_resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PerfumeTrending.cl — Motor de Scraping Periódico por Rotaciones LRU"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("SCRAPER_BATCH_SIZE", 500)),
        help="Cantidad de perfumes por rotación (lote). Por defecto 500.",
    )
    parser.add_argument(
        "--rotations",
        type=int,
        default=int(os.environ.get("SCRAPER_ROTATIONS", 0)),
        help="Número de rotaciones a ejecutar (0 = todas las necesarias para cubrir el catálogo).",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=int(os.environ.get("SCRAPER_DELAY_ROTATIONS", 10)),
        help="Segundos de cooldown entre rotaciones consecutivas. Por defecto 10s.",
    )
    args = parser.parse_args()

    resultado = ejecutar_ciclo_scraping_y_descubrimiento(
        batch_size=args.batch_size,
        rotations=args.rotations,
        delay_between_rotations=args.delay,
    )
    sep_box = "=" * 60
    print("\n" + sep_box)
    print("RESUMEN DE EJECUCIÓN ETL DE SCRAPING (ROTACIONES LRU):")
    print(f"Estado General: {resultado.get('metadata', {}).get('estado', 'EXITOSO')}")
    print(f"Rotaciones ejecutadas: {resultado.get('metadata', {}).get('rotaciones_completadas', 1)} / {resultado.get('metadata', {}).get('total_rotaciones_planificadas', 1)}")
    print(f"Perfumes auditados: {resultado.get('metricas', {}).get('perfumes_auditados', 0)} / {resultado.get('metricas', {}).get('total_perfumes_catalogo', 0)}")
    print(f"Precios actualizados: {resultado.get('metricas', {}).get('precios_actualizados', 0)}")
    print(f"Ofertas nuevas: {resultado.get('metricas', {}).get('ofertas_nuevas', 0)}")
    print(f"Duración total: {resultado.get('metadata', {}).get('duracion_segundos', 0)}s")
    print(sep_box)
