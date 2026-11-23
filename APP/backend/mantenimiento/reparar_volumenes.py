# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Reparación Verificada de Volúmenes Incoherentes (Fase 3)
=============================================================================
Detecta ofertas activas cuyo slug de URL contiene un volumen explícito (`NN ml`)
que contradice el `volumen_ml` de su `variantes_perfume` actual, verifica CADA
oferta contra la fuente viva de la tienda (catálogo masivo en memoria + consulta
directa `.json` / PDP `curl_cffi`), y clasifica estrictamente en:
  1. `coherente_multivariante`: el producto vivo tiene múltiples variantes y una
     coincide en volumen Y precio (<= 8 %) con la fila de BD -> se mantiene intacta.
  2. `corregible_verificado`: la fuente viva confirma otro volumen real (>= 25 ml) ->
     reasigna `ofertas_actuales` y `precios_registro` a la variante correcta,
     resolviendo colisiones `UNIQUE(variante_id, tienda_id)` y limpiando variantes
     huérfanas sin referencias residuales.
  3. `miniatura_retirada`: la fuente viva confirma que el producto es < 25 ml
     (decant / vial / miniatura) -> marca `en_stock=False, estado='retirada'`.
  4. `no_verificable`: URL muerta (404), WAF (403/429) o título/slug contradictorio ->
     marca `estado='requiere_revision'` (y `en_stock=False` si es 404 confirmado),
     sin adivinar jamás el volumen solo por el slug.

Uso:
  python APP/backend/mantenimiento/reparar_volumenes.py --dry-run
  python APP/backend/mantenimiento/reparar_volumenes.py --apply --store "Mundo Aromas"
  python APP/backend/mantenimiento/reparar_volumenes.py --apply
"""

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (Counter, defaultdict) desde el módulo 'collections'
from collections import Counter, defaultdict
# Importación de componentes (ThreadPoolExecutor, as_completed) desde el módulo 'concurrent.futures'
from concurrent.futures import ThreadPoolExecutor, as_completed
# Importación de librería estándar o dependencia externa (csv)
import csv
# Importación de componentes (datetime, timezone) desde el módulo 'datetime'
from datetime import datetime, timezone
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (threading)
import threading
# Importación de componentes (Any, Dict, List, Optional, ...) desde el módulo 'typing'
from typing import Any, Dict, List, Optional, Set, Tuple

# Importación de componentes (BeautifulSoup) desde el módulo 'bs4'
from bs4 import BeautifulSoup

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (requests) desde el módulo 'curl_cffi'
    from curl_cffi import requests as curl_requests
except ImportError:
    # Asignamos 'curl_requests' con None
    curl_requests = None

# Importación de librería estándar o dependencia externa (requests)
import requests

# Configuración de rutas
REPO_ROOT = Path(__file__).resolve().parents[3]
# Asignamos 'APP_DIR' con REPO_ROOT / 'APP'
APP_DIR = REPO_ROOT / "APP"
# Recorremos iterativamente cada '_p' en (str(APP_DIR), str(REPO_ROOT))
for _p in (str(APP_DIR), str(REPO_ROOT)):
    # Evaluamos la condición lógica (_p not in sys.path) para controlar el flujo
    if _p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)

# Importación de componentes (_obtener_mapa_credenciales, get_supabase, limpiar_cache_catalogo) desde el módulo 'backend.database'
from backend.database import _obtener_mapa_credenciales, get_supabase, limpiar_cache_catalogo
# Importación de componentes (detectar_formato_oferta, es_precio_valido, extraer_volumen_ml, extraer_volumen_ml_opcional, ...) desde el módulo 'backend.normalizador'
from backend.normalizador import (
    detectar_formato_oferta,
    es_precio_valido,
    extraer_volumen_ml,
    extraer_volumen_ml_opcional,
    resolver_volumen_oferta,
)
# Importación de componentes (TIENDAS_CRAWLER_CONFIG, clean_digits, crear_sesion_robusta, precargar_catalogos_bulk_tiendas) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import (
    TIENDAS_CRAWLER_CONFIG,
    clean_digits,
    crear_sesion_robusta,
    precargar_catalogos_bulk_tiendas,
)

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Asignamos 'logger' con logging.getLogger('RepararVolumenes')
logger = logging.getLogger("RepararVolumenes")


# - ¿Qué hace esta función?:
#   Descarga todas las filas de una tabla de Supabase paginando de a 1.000 registros
#   para no truncar resultados con el límite por defecto de PostgREST.
def fetch_all_supabase(sb: Any, table: str, select: str = "*") -> List[Dict[str, Any]]:
    # Asignamos 'rows' con []
    rows: List[Dict[str, Any]] = []
    # Asignamos 'offset' con 0
    offset = 0
    # Ejecutamos el ciclo mientras se mantenga la condición: True
    while True:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        res = sb.table(table).select(select).order("id", desc=False).range(offset, offset + 999).execute()
        # Asignamos 'batch' con res.data or []
        batch = res.data or []
        # Evaluamos la condición lógica (not batch) para controlar el flujo
        if not batch:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Ejecutamos instrucción: rows.extend(batch)
        rows.extend(batch)
        # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
        if len(batch) < 1000:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Actualizamos acumulativamente el valor de 'offset'
        offset += 1000
    # Retornamos el resultado procesado (rows)
    return rows


# - ¿Qué hace esta función?:
#   Normaliza una URL comercial quitando parámetros de consulta, fragmentos, barra final
#   y prefijo `www.` para cruzar de forma exacta `ofertas_actuales.url_producto` con feeds vivos.
def normalizar_url_clave(url: str) -> str:
    # Evaluamos la condición lógica (not url) para controlar el flujo
    if not url:
        # Retornamos el resultado procesado ('')
        return ""
    # Asignamos 'limpia' con url.strip().split('?')[0].split('#')[0].rs...
    limpia = url.strip().split("?")[0].split("#")[0].rstrip("/").lower()
    # Asignamos 'limpia' con re.sub('^https?://(www\\.)?', 'https://', ...
    limpia = re.sub(r"^https?://(www\.)?", "https://", limpia)
    # Retornamos el resultado procesado (limpia)
    return limpia


# - ¿Qué hace esta función?:
#   Extrae el último segmento útil (`handle` o `slug`) de una URL comercial.
def extraer_handle_url(url: str) -> str:
    # Asignamos 'limpia' con normalizar_url_clave(url)
    limpia = normalizar_url_clave(url)
    # Evaluamos la condición lógica (not limpia) para controlar el flujo
    if not limpia:
        # Retornamos el resultado procesado ('')
        return ""
    # Retornamos el resultado procesado (limpia.split('/')[-1])
    return limpia.split("/")[-1]


# - ¿Qué hace esta función?:
#   Consulta directamente una URL individual que no apareció en el catálogo masivo en RAM
#   (ej. productos antiguos de Shopify vía `.json`, fichas de Falabella vía `__NEXT_DATA__`,
#   o páginas WooCommerce), devolviendo estado HTTP y lista estandarizada de variantes vivas.
def consultar_producto_vivo_individual(
    url: str,
    tipo_tienda: str,
) -> Dict[str, Any]:
    # Asignamos 'headers' con {'User-Agent': 'Mozilla/5.0 (Windows NT 10...
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9",
    }
    # Asignamos 'sess' con curl_requests.Session(impersonate='chrome1...
    sess = curl_requests.Session(impersonate="chrome120") if curl_requests is not None else requests.Session()
    # Asignamos 'clean_u' con url.split('?')[0].rstrip('/')
    clean_u = url.split("?")[0].rstrip("/")

    # 1. Shopify: endpoint directo `<url>.json`
    if tipo_tienda == "shopify" and "/products/" in clean_u:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            r = sess.get(f"{clean_u}.json", headers=headers, timeout=12)
            # Evaluamos la condición lógica (r.status_code == 404) para controlar el flujo
            if r.status_code == 404:
                # Retornamos el resultado procesado ({'status': 404, 'variants': [], 'title': ''})
                return {"status": 404, "variants": [], "title": ""}
            # Evaluamos la condición lógica (r.status_code in (403, 429)) para controlar el flujo
            if r.status_code in (403, 429):
                # Retornamos el resultado procesado ({'status': r.status_code, 'variants': [], 'titl...)
                return {"status": r.status_code, "variants": [], "title": ""}
            # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
            if r.status_code == 200:
                # Asignamos 'prod' con (r.json() or {}).get('product') or {}
                prod = (r.json() or {}).get("product") or {}
                # Asignamos 'title' con str(prod.get('title') or '').strip()
                title = str(prod.get("title") or "").strip()
                # Asignamos 'v_list' con []
                v_list = []
                # Recorremos iterativamente cada 'v' en prod.get('variants') or []
                for v in prod.get("variants") or []:
                    # Asignamos 'p_act' con clean_digits(str(v.get('price', '0')).spli...
                    p_act = clean_digits(str(v.get("price", "0")).split(".")[0])
                    # Asignamos 'p_cmp_raw' con v.get('compare_at_price')
                    p_cmp_raw = v.get("compare_at_price")
                    # Asignamos 'p_cmp' con clean_digits(str(p_cmp_raw).split('.')[0])...
                    p_cmp = clean_digits(str(p_cmp_raw).split(".")[0]) if p_cmp_raw else p_act
                    # Asignamos 'in_st' con bool(v.get('available', True)) if 'availab...
                    in_st = bool(v.get("available", True)) if "available" in v else (int(v.get("inventory_quantity") or 0) > 0)
                    # Ejecutamos instrucción: v_list.append({'title': str(v.get('title') or ''), '...
                    v_list.append({
                        "title": str(v.get("title") or ""),
                        "price": p_act,
                        "compare_at_price": max(p_cmp, p_act),
                        "available": in_st,
                    })
                # Retornamos el resultado procesado ({'status': 200, 'title': title, 'variants': v_l...)
                return {"status": 200, "title": title, "variants": v_list}
        except Exception as exc:
            # Retornamos el resultado procesado ({'status': 0, 'error': str(exc), 'variants': []...)
            return {"status": 0, "error": str(exc), "variants": [], "title": ""}

    # 2. Falabella o WooCommerce / HTML PDP
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = sess.get(url, headers=headers, timeout=14, allow_redirects=True)
        # Asignamos 'status' con r.status_code
        status = r.status_code
        # Asignamos 'final_u' con str(getattr(r, 'url', url) or url)
        final_u = str(getattr(r, "url", url) or url)
        # Detección de redirección al home o catálogo genérico (soft-404)
        final_path = re.sub(r"^https?://[^/]+", "", final_u.split("?")[0]).strip("/")
        # Evaluamos la condición lógica (status == 404 or final_path in ('', 'falabella-cl')) para controlar el flujo
        if status == 404 or final_path in ("", "falabella-cl"):
            # Retornamos el resultado procesado ({'status': 404, 'variants': [], 'title': ''})
            return {"status": 404, "variants": [], "title": ""}
        # Evaluamos la condición lógica (status in (403, 429)) para controlar el flujo
        if status in (403, 429):
            # Retornamos el resultado procesado ({'status': status, 'variants': [], 'title': ''})
            return {"status": status, "variants": [], "title": ""}
        # Evaluamos la condición lógica (status != 200) para controlar el flujo
        if status != 200:
            # Retornamos el resultado procesado ({'status': status, 'variants': [], 'title': ''})
            return {"status": status, "variants": [], "title": ""}

        # Asignamos 'html_txt' con r.text or ''
        html_txt = r.text or ""
        # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
        soup = BeautifulSoup(html_txt, "html.parser")

        # Falabella `__NEXT_DATA__`
        if "falabella" in clean_u.lower():
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            tag = soup.find("script", id="__NEXT_DATA__")
            # Evaluamos la condición lógica (tag and tag.string) para controlar el flujo
            if tag and tag.string:
                # Procesamiento de serialización o deserialización de estructura JSON
                data = json.loads(tag.string)
                # Asignamos 'pdata' con data.get('props', {}).get('pageProps', {})...
                pdata = data.get("props", {}).get("pageProps", {}).get("productData", {})
                # Evaluamos la condición lógica (not pdata) para controlar el flujo
                if not pdata:
                    # Retornamos el resultado procesado ({'status': 404, 'variants': [], 'title': ''})
                    return {"status": 404, "variants": [], "title": ""}
                # Asignamos 'p_title' con str(pdata.get('name') or '').strip()
                p_title = str(pdata.get("name") or "").strip()
                # Asignamos 'is_prod_out' con bool(pdata.get('isOutOfStock', False))
                is_prod_out = bool(pdata.get("isOutOfStock", False))
                # Asignamos 'skus' con pdata.get('variants') or pdata.get('skus')...
                skus = pdata.get("variants") or pdata.get("skus") or []
                # Asignamos 'v_list' con []
                v_list = []
                # Recorremos iterativamente cada 'v' en skus
                for v in skus:
                    # Asignamos 'v_name' con str(v.get('name') or p_title)
                    v_name = str(v.get("name") or p_title)
                    # Asignamos 'size_attr' con (v.get('attributes') or {}).get('size')
                    size_attr = (v.get("attributes") or {}).get("size")
                    # Asignamos 'size_num' con clean_digits(size_attr) if size_attr else 0
                    size_num = clean_digits(size_attr) if size_attr else 0
                    # Asignamos 'v_label' con f'{size_num}ml' if 10 <= size_num <= 1000 ...
                    v_label = f"{size_num}ml" if (10 <= size_num <= 1000) else v_name
                    # Asignamos 'prices' con v.get('prices') or []
                    prices = v.get("prices") or []
                    # Asignamos '(p_act, p_norm)' con (0, 0)
                    p_act, p_norm = 0, 0
                    # Recorremos iterativamente cada 'pi' en prices
                    for pi in prices:
                        # Asignamos 'pt' con pi.get('type', '')
                        pt = pi.get("type", "")
                        # Asignamos 'pv' con clean_digits((pi.get('price') or ['0'])[0])
                        pv = clean_digits((pi.get("price") or ["0"])[0])
                        # Evaluamos la condición lógica (pt in ('internetPrice', 'eventPrice') and pv > 0) para controlar el flujo
                        if pt in ("internetPrice", "eventPrice") and pv > 0:
                            # Asignamos 'p_act' con pv
                            p_act = pv
                        # Evaluamos la condición lógica (pt == 'normalPrice' and pv > 0) para controlar el flujo
                        elif pt == "normalPrice" and pv > 0:
                            # Asignamos 'p_norm' con pv
                            p_norm = pv
                    # Evaluamos la condición lógica (p_act == 0 and prices) para controlar el flujo
                    if p_act == 0 and prices:
                        # Asignamos 'p_act' con clean_digits((prices[0].get('price') or ['...
                        p_act = clean_digits((prices[0].get("price") or ["0"])[0])
                    # Asignamos 'avail_v' con not is_prod_out and (not bool(v.get('isOut...
                    avail_v = not is_prod_out and not bool(v.get("isOutOfStock", False))
                    # Evaluamos la condición lógica (p_act > 0) para controlar el flujo
                    if p_act > 0:
                        # Ejecutamos instrucción: v_list.append({'title': v_label, 'price': p_act, 'co...
                        v_list.append({
                            "title": v_label,
                            "price": p_act,
                            "compare_at_price": max(p_norm, p_act),
                            "available": avail_v,
                        })
                # Retornamos el resultado procesado ({'status': 200, 'title': p_title, 'variants': v...)
                return {"status": 200, "title": p_title, "variants": v_list}

        # WooCommerce / HTML genérico con JSON-LD o `<h1 class="product_title">`
        low_html = html_txt.lower()
        # Evaluamos la condición lógica ('página no encontrada' in low_html or 'page not foun...) para controlar el flujo
        if "página no encontrada" in low_html or "page not found" in low_html or "error 404" in low_html:
            # Retornamos el resultado procesado ({'status': 404, 'variants': [], 'title': ''})
            return {"status": 404, "variants": [], "title": ""}

        # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
        h1 = soup.find("h1")
        # Asignamos 'p_title' con h1.get_text(' ', strip=True) if h1 else ''
        p_title = h1.get_text(" ", strip=True) if h1 else ""
        # Asignamos 'v_list' con []
        v_list = []
        # Recorremos iterativamente cada 's_tag' en soup.find_all('script', type='application/...
        for s_tag in soup.find_all("script", type="application/ld+json"):
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Procesamiento de serialización o deserialización de estructura JSON
                raw_ld = json.loads(s_tag.string or s_tag.get_text() or "{}")
                # Asignamos 'nodes' con raw_ld if isinstance(raw_ld, list) else ra...
                nodes = raw_ld if isinstance(raw_ld, list) else (raw_ld.get("@graph") or [raw_ld])
                # Recorremos iterativamente cada 'nd' en nodes
                for nd in nodes:
                    # Evaluamos la condición lógica (isinstance(nd, dict) and 'Product' in str(nd.get('@t...) para controlar el flujo
                    if isinstance(nd, dict) and "Product" in str(nd.get("@type", "")):
                        # Asignamos 'p_title' con p_title or str(nd.get('name') or '').strip()
                        p_title = p_title or str(nd.get("name") or "").strip()
                        # Asignamos 'offs' con nd.get('offers') or []
                        offs = nd.get("offers") or []
                        # Evaluamos la condición lógica (isinstance(offs, dict)) para controlar el flujo
                        if isinstance(offs, dict):
                            # Asignamos 'offs' con [offs]
                            offs = [offs]
                        # Recorremos iterativamente cada 'off' en offs
                        for off in offs:
                            # Evaluamos la condición lógica (not isinstance(off, dict)) para controlar el flujo
                            if not isinstance(off, dict):
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue
                            # Asignamos 'pr' con clean_digits(str(off.get('price') or '0')....
                            pr = clean_digits(str(off.get("price") or "0").split(".")[0])
                            # Asignamos 'av' con 'outofstock' not in str(off.get('availabil...
                            av = "outofstock" not in str(off.get("availability") or "").lower()
                            # Evaluamos la condición lógica (pr > 0) para controlar el flujo
                            if pr > 0:
                                # Ejecutamos instrucción: v_list.append({'title': str(off.get('name') or ''), ...
                                v_list.append({
                                    "title": str(off.get("name") or ""),
                                    "price": pr,
                                    "compare_at_price": pr,
                                    "available": av,
                                })
            except Exception:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
        # Retornamos el resultado procesado ({'status': 200, 'title': p_title, 'variants': v...)
        return {"status": 200, "title": p_title, "variants": v_list}
    except Exception as exc:
        # Retornamos el resultado procesado ({'status': 0, 'error': str(exc), 'variants': []...)
        return {"status": 0, "error": str(exc), "variants": [], "title": ""}


# - ¿Qué hace esta función?:
#   Evalúa una oferta candidata frente a la respuesta viva de la tienda y determina
#   su clasificación (`coherente_multivariante`, `corregible_verificado`,
#   `miniatura_retirada` o `no_verificable`) junto con el volumen y precio verificados.
def clasificar_candidato_volumen(
    oferta: Dict[str, Any],
    variante_db: Dict[str, Any],
    info_viva: Dict[str, Any],
) -> Dict[str, Any]:
    # Asignamos 'url' con str(oferta.get('url_producto') or '')
    url = str(oferta.get("url_producto") or "")
    # Asignamos 'db_vol' con float(variante_db.get('volumen_ml') or 100.0)
    db_vol = float(variante_db.get("volumen_ml") or 100.0)
    # Asignamos 'db_price' con int(oferta.get('precio_actual') or 0)
    db_price = int(oferta.get("precio_actual") or 0)
    # Asignamos 'db_formato' con str(variante_db.get('formato') or 'regular...
    db_formato = str(variante_db.get("formato") or "regular").lower()
    # Asignamos 'es_tester' con db_formato == 'tester' or detectar_formato...
    es_tester = db_formato == "tester" or (detectar_formato_oferta("", url) == "tester")

    # Asignamos 'status' con int(info_viva.get('status') or 0)
    status = int(info_viva.get("status") or 0)
    # Evaluamos la condición lógica (status == 404) para controlar el flujo
    if status == 404:
        # Retornamos el resultado procesado ({'clasificacion': 'no_verificable', 'submotivo'...)
        return {
            "clasificacion": "no_verificable",
            "submotivo": "http_404_o_eliminado",
            "es_404": True,
            "vol_nuevo": None,
        }
    # Evaluamos la condición lógica (status in (403, 429) or status != 200) para controlar el flujo
    if status in (403, 429) or status != 200:
        # Retornamos el resultado procesado ({'clasificacion': 'no_verificable', 'submotivo'...)
        return {
            "clasificacion": "no_verificable",
            "submotivo": f"http_{status or 'timeout'}",
            "es_404": False,
            "vol_nuevo": None,
        }

    # Asignamos 'live_title' con str(info_viva.get('title') or '').strip()
    live_title = str(info_viva.get("title") or "").strip()
    # Asignamos 'raw_vars' con info_viva.get('variants') or []
    raw_vars = info_viva.get("variants") or []
    # Evaluamos la condición lógica (not raw_vars) para controlar el flujo
    if not raw_vars:
        # Retornamos el resultado procesado ({'clasificacion': 'no_verificable', 'submotivo'...)
        return {
            "clasificacion": "no_verificable",
            "submotivo": "sin_variantes_en_pdp",
            "es_404": False,
            "vol_nuevo": None,
        }

    # Asignamos 'n_vars' con len(raw_vars)
    n_vars = len(raw_vars)
    # Asignamos 'parsed_vars' con []
    parsed_vars: List[Dict[str, Any]] = []
    # Recorremos iterativamente cada 'rv' en raw_vars
    for rv in raw_vars:
        # Asignamos 'vt' con str(rv.get('title') or '')
        vt = str(rv.get("title") or "")
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'pr' con int(float(rv.get('price') or 0))
            pr = int(float(rv.get("price") or 0))
        except (ValueError, TypeError):
            # Asignamos 'pr' con 0
            pr = 0
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'pc' con int(float(rv.get('compare_at_price') or pr...
            pc = int(float(rv.get("compare_at_price") or pr)) if rv.get("compare_at_price") else pr
        except (ValueError, TypeError):
            # Asignamos 'pc' con pr
            pc = pr
        # Asignamos 'avail' con bool(rv.get('available', True))
        avail = bool(rv.get("available", True))

        # Chequear si es miniatura explícita (< 25 ml) antes de resolver_volumen_oferta
        vol_raw_v = extraer_volumen_ml_opcional(vt)
        # Asignamos 'vol_raw_t' con extraer_volumen_ml_opcional(live_title)
        vol_raw_t = extraer_volumen_ml_opcional(live_title)
        # Asignamos 'vol_raw_u' con extraer_volumen_ml_opcional(url.rstrip('/'...
        vol_raw_u = extraer_volumen_ml_opcional(url.rstrip("/").split("/")[-1])

        # Asignamos 'vol_res' con resolver_volumen_oferta(titulo_variante=vt...
        vol_res = resolver_volumen_oferta(
            titulo_variante=vt,
            titulo_producto=live_title,
            url_slug=url,
            volumen_ml_defecto=None,
            n_variantes_producto=n_vars,
            es_tester=es_tester,
        )
        # Ejecutamos instrucción: parsed_vars.append({'title': vt, 'price': pr, 'compa...
        parsed_vars.append({
            "title": vt,
            "price": pr,
            "compare_at_price": max(pc, pr),
            "available": avail,
            "vol": vol_res,
            "vol_miniatura": next((x for x in (vol_raw_v, vol_raw_t, vol_raw_u) if x is not None and x < 25), None),
        })

    # Caso miniatura / decant confirmado en producto univariante (< 25 ml)
    if n_vars == 1 and parsed_vars[0]["vol"] is None and parsed_vars[0]["vol_miniatura"] is not None:
        # Retornamos el resultado procesado ({'clasificacion': 'miniatura_retirada', 'submot...)
        return {
            "clasificacion": "miniatura_retirada",
            "submotivo": f"miniatura_{parsed_vars[0]['vol_miniatura']}ml",
            "es_404": False,
            "vol_nuevo": parsed_vars[0]["vol_miniatura"],
        }

    # Caso 1: Producto multivariante donde existe una variante con db_vol y precio compatible
    if n_vars > 1:
        # Asignamos 'vars_mismo_vol' con [pv for pv in parsed_vars if pv['vol'] and...
        vars_mismo_vol = [pv for pv in parsed_vars if pv["vol"] and abs(pv["vol"] - db_vol) <= 1 and pv["price"] > 0]
        # Asignamos 'vars_otro_vol' con [pv for pv in parsed_vars if pv['vol'] and...
        vars_otro_vol = [pv for pv in parsed_vars if pv["vol"] and abs(pv["vol"] - db_vol) > 1 and pv["vol"] >= 25 and pv["price"] > 0]

        # Evaluamos la condición lógica (vars_mismo_vol) para controlar el flujo
        if vars_mismo_vol:
            # Asignamos 'mv' con min(vars_mismo_vol, key=lambda x: abs(x['p...
            mv = min(vars_mismo_vol, key=lambda x: abs(x["price"] - db_price))
            # Asignamos 'diff_mismo' con abs(mv['price'] - db_price) / max(db_price...
            diff_mismo = abs(mv["price"] - db_price) / max(db_price, 1)
            # Asignamos 'mejor_otro' con min(vars_otro_vol, key=lambda x: abs(x['pr...
            mejor_otro = min(vars_otro_vol, key=lambda x: abs(x["price"] - db_price)) if vars_otro_vol else None
            # Asignamos 'diff_otro' con abs(mejor_otro['price'] - db_price) / max(...
            diff_otro = (abs(mejor_otro["price"] - db_price) / max(db_price, 1)) if mejor_otro else 999.0

            # Evaluamos la condición lógica (diff_mismo <= 0.08 or (diff_mismo <= 0.18 and diff_m...) para controlar el flujo
            if diff_mismo <= 0.08 or (diff_mismo <= 0.18 and diff_mismo < diff_otro):
                # Retornamos el resultado procesado ({'clasificacion': 'coherente_multivariante', 's...)
                return {
                    "clasificacion": "coherente_multivariante",
                    "submotivo": f"multivariante_{int(round(db_vol))}ml_confirmado",
                    "es_404": False,
                    "vol_nuevo": int(round(db_vol)),
                    "precio_vivo": mv["price"],
                    "precio_normal_vivo": mv["compare_at_price"],
                    "en_stock_vivo": mv["available"],
                }

        # Si en multivariante el precio guardado calza exactamente (<= 5 %) con otra variante real:
        if vars_otro_vol:
            # Asignamos 'mejor_otro' con min(vars_otro_vol, key=lambda x: abs(x['pr...
            mejor_otro = min(vars_otro_vol, key=lambda x: abs(x["price"] - db_price))
            # Asignamos 'diff_otro' con abs(mejor_otro['price'] - db_price) / max(...
            diff_otro = abs(mejor_otro["price"] - db_price) / max(db_price, 1)
            # Evaluamos la condición lógica (diff_otro <= 0.05 and es_precio_valido(mejor_otro['p...) para controlar el flujo
            if diff_otro <= 0.05 and es_precio_valido(mejor_otro["price"]):
                # Retornamos el resultado procesado ({'clasificacion': 'corregible_verificado', 'sub...)
                return {
                    "clasificacion": "corregible_verificado",
                    "submotivo": f"multivariante_precio_calza_{mejor_otro['vol']}ml",
                    "es_404": False,
                    "vol_nuevo": int(mejor_otro["vol"]),
                    "precio_vivo": mejor_otro["price"],
                    "precio_normal_vivo": mejor_otro["compare_at_price"],
                    "en_stock_vivo": mejor_otro["available"],
                }

        # Retornamos el resultado procesado ({'clasificacion': 'no_verificable', 'submotivo'...)
        return {
            "clasificacion": "no_verificable",
            "submotivo": "multivariante_precio_no_concluyente",
            "es_404": False,
            "vol_nuevo": None,
        }

    # Caso 2: Producto de 1 sola variante en la tienda
    pv0 = parsed_vars[0]
    # Asignamos 'vol_real' con pv0['vol']
    vol_real = pv0["vol"]
    # Evaluamos la condición lógica (vol_real and vol_real >= 25 and (abs(vol_real - db_v...) para controlar el flujo
    if vol_real and vol_real >= 25 and abs(vol_real - db_vol) > 1 and es_precio_valido(pv0["price"]):
        # Asignamos 'diff_pct' con abs(pv0['price'] - db_price) / max(db_pric...
        diff_pct = abs(pv0["price"] - db_price) / max(db_price, 1)
        # Retornamos el resultado procesado ({'clasificacion': 'corregible_verificado', 'sub...)
        return {
            "clasificacion": "corregible_verificado",
            "submotivo": f"univariante_confirmado_{vol_real}ml_diff_{diff_pct:.2f}",
            "es_404": False,
            "vol_nuevo": int(vol_real),
            "precio_vivo": pv0["price"],
            "precio_normal_vivo": pv0["compare_at_price"],
            "en_stock_vivo": pv0["available"],
        }

    # Retornamos el resultado procesado ({'clasificacion': 'no_verificable', 'submotivo'...)
    return {
        "clasificacion": "no_verificable",
        "submotivo": "volumen_ambiguo_o_contradictorio",
        "es_404": False,
        "vol_nuevo": None,
    }


# - ¿Qué hace esta función principal?:
#   Orquesta la auditoría completa de incoherencias URL<->volumen, genera el CSV de
#   respaldo/auditoría en `scratch/backups/` y, cuando se pasa `--apply`, aplica las
#   correcciones verificadas respetando llaves foráneas e índices únicos de PostgreSQL.
def ejecutar_reparacion_volumenes(
    apply_changes: bool = False,
    store_filter: Optional[str] = None,
) -> Dict[str, Any]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("No se pudo inicializar cliente Supabase con service_role.")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    logger.info("Cargando catálogo maestro desde Supabase (tiendas, perfumes, variantes, ofertas)...")
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    tiendas_rows = sb.table("tiendas").select("id, nombre, url_base").execute().data or []
    # Asignamos 'tiendas_by_id' con {int(t['id']): t for t in tiendas_rows}
    tiendas_by_id = {int(t["id"]): t for t in tiendas_rows}
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    perfumes_by_id = {int(p["id"]): p for p in fetch_all_supabase(sb, "perfumes", "id, nombre, marca, tipo")}
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    variantes_rows = fetch_all_supabase(sb, "variantes_perfume", "id, perfume_id, concentracion, volumen_ml, formato, slug")
    # Asignamos 'variantes_by_id' con {int(v['id']): v for v in variantes_rows}
    variantes_by_id = {int(v["id"]): v for v in variantes_rows}
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    ofertas_rows = fetch_all_supabase(
        sb,
        "ofertas_actuales",
        "id, variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, estado, ultima_verificacion_exitosa",
    )

    # Índice de variantes por (perfume_id, vol_redondeado, formato) y de ofertas por (variante_id, tienda_id)
    variante_lookup: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    # Recorremos iterativamente cada 'v' en variantes_rows
    for v in variantes_rows:
        # Asignamos 'key' con (int(v['perfume_id']), int(round(float(v['...
        key = (int(v["perfume_id"]), int(round(float(v["volumen_ml"]))), str(v.get("formato") or "regular").lower())
        # Evaluamos la condición lógica (key not in variante_lookup) para controlar el flujo
        if key not in variante_lookup:
            # Asignamos 'variante_lookup[key]' con v
            variante_lookup[key] = v

    # Asignamos 'oferta_por_var_tienda' con {}
    oferta_por_var_tienda: Dict[Tuple[int, int], Dict[str, Any]] = {}
    # Recorremos iterativamente cada 'o' en ofertas_rows
    for o in ofertas_rows:
        # Asignamos 'oferta_por_var_tienda[int(o['var...' con o
        oferta_por_var_tienda[(int(o["variante_id"]), int(o["tienda_id"]))] = o

    # 1. Seleccionar candidatos incoherentes (ofertas activas con slug explícito NN ml != variante.volumen_ml)
    candidatos: List[Tuple[Dict[str, Any], Dict[str, Any], str, int]] = []
    # Recorremos iterativamente cada 'o' en ofertas_rows
    for o in ofertas_rows:
        # Evaluamos la condición lógica (o.get('estado') != 'activa') para controlar el flujo
        if o.get("estado") != "activa":
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 't_info' con tiendas_by_id.get(int(o['tienda_id']))
        t_info = tiendas_by_id.get(int(o["tienda_id"]))
        # Asignamos 't_nombre' con t_info['nombre'] if t_info else str(o['tie...
        t_nombre = t_info["nombre"] if t_info else str(o["tienda_id"])
        # Evaluamos la condición lógica (store_filter and store_filter.lower() not in t_nombr...) para controlar el flujo
        if store_filter and store_filter.lower() not in t_nombre.lower():
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'url' con str(o.get('url_producto') or '')
        url = str(o.get("url_producto") or "")
        # Asignamos 'slug' con url.rstrip('/').split('/')[-1]
        slug = url.rstrip("/").split("/")[-1]
        # Evaluamos la condición lógica (not re.search('\\d\\s*[-_]?\\s*ml', slug, re.I)) para controlar el flujo
        if not re.search(r"\d\s*[-_]?\s*ml", slug, re.I):
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'v' con variantes_by_id.get(int(o['variante_id']))
        v = variantes_by_id.get(int(o["variante_id"]))
        # Evaluamos la condición lógica (not v or str(v.get('formato') or 'regular').lower() ...) para controlar el flujo
        if not v or str(v.get("formato") or "regular").lower() == "tester":
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'vol_slug' con extraer_volumen_ml_opcional(slug) or extra...
        vol_slug = extraer_volumen_ml_opcional(slug) or extraer_volumen_ml(slug, default=0)
        # Evaluamos la condición lógica (vol_slug and abs(vol_slug - float(v['volumen_ml'])) > 1) para controlar el flujo
        if vol_slug and abs(vol_slug - float(v["volumen_ml"])) > 1:
            # Ejecutamos instrucción: candidatos.append((o, v, t_nombre, int(vol_slug)))
            candidatos.append((o, v, t_nombre, int(vol_slug)))

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(
        f"Candidatos incoherentes detectados: {len(candidatos)} "
        f"(en_stock=True: {sum(1 for o, _, _, _ in candidatos if o.get('en_stock'))})"
    )
    # Evaluamos la condición lógica (not candidatos) para controlar el flujo
    if not candidatos:
        # Retornamos el resultado procesado ({'total_candidatos': 0})
        return {"total_candidatos": 0}

    # 2. Precargar catálogos masivos de las tiendas involucradas
    tiendas_involucradas = sorted({t_nom for _, _, t_nom, _ in candidatos})
    # Asignamos 'session' con crear_sesion_robusta()
    session = crear_sesion_robusta()
    # Asignamos 'bulk_map' con precargar_catalogos_bulk_tiendas(session=s...
    bulk_map = precargar_catalogos_bulk_tiendas(
        session=session,
        tiendas_db=tiendas_rows,
        filtro_tiendas=tiendas_involucradas,
        max_workers=6,
    )

    # Asignamos 'cfg_tipo_por_tienda' con {c['nombre'].lower(): c.get('tipo', 'shopi...
    cfg_tipo_por_tienda = {c["nombre"].lower(): c.get("tipo", "shopify") for c in TIENDAS_CRAWLER_CONFIG}
    # Asignamos 'bulk_por_url' con {}
    bulk_por_url: Dict[Tuple[str, str], Dict[str, Any]] = {}
    # Asignamos 'bulk_por_handle' con {}
    bulk_por_handle: Dict[Tuple[str, str], Dict[str, Any]] = {}
    # Asignamos 'tiendas_con_feed_completo' con set()
    tiendas_con_feed_completo: Set[str] = set()

    # Recorremos iterativamente cada '(t_nom, cat)' en bulk_map.items()
    for t_nom, cat in bulk_map.items():
        # Asignamos 't_low' con t_nom.lower()
        t_low = t_nom.lower()
        # Si cargó < 3400 items (límite 14*250=3500), el feed en RAM está completo
        if 0 < cat.total_productos < 3400:
            # Ejecutamos instrucción: tiendas_con_feed_completo.add(t_low)
            tiendas_con_feed_completo.add(t_low)
        # Recorremos iterativamente cada 'it' en cat.todos_items
        for it in cat.todos_items:
            # Asignamos 'u_norm' con normalizar_url_clave(it.get('url', ''))
            u_norm = normalizar_url_clave(it.get("url", ""))
            # Asignamos 'h_norm' con extraer_handle_url(it.get('url', ''))
            h_norm = extraer_handle_url(it.get("url", ""))
            # Evaluamos la condición lógica (u_norm) para controlar el flujo
            if u_norm:
                # Asignamos 'bulk_por_url[t_low, u_norm]' con it
                bulk_por_url[(t_low, u_norm)] = it
            # Evaluamos la condición lógica (h_norm) para controlar el flujo
            if h_norm:
                # Asignamos 'bulk_por_handle[t_low, h_norm]' con it
                bulk_por_handle[(t_low, h_norm)] = it

    # 3. Resolver info viva (primero RAM O(1), luego fetch individual concurrente para faltantes)
    info_viva_por_oferta: Dict[int, Dict[str, Any]] = {}
    # Asignamos 'faltantes_red' con []
    faltantes_red: List[Tuple[int, str, str]] = []

    # Recorremos iterativamente cada '(o, _, t_nom, _)' en candidatos
    for o, _, t_nom, _ in candidatos:
        # Asignamos 'oid' con int(o['id'])
        oid = int(o["id"])
        # Asignamos 't_low' con t_nom.lower()
        t_low = t_nom.lower()
        # Asignamos 'url' con str(o.get('url_producto') or '')
        url = str(o.get("url_producto") or "")
        # Asignamos 'item_ram' con bulk_por_url.get((t_low, normalizar_url_cl...
        item_ram = bulk_por_url.get((t_low, normalizar_url_clave(url))) or bulk_por_handle.get((t_low, extraer_handle_url(url)))
        # Evaluamos la condición lógica (item_ram is not None) para controlar el flujo
        if item_ram is not None:
            # Asignamos 'info_viva_por_oferta[oid]' con {'status': 200, 'title': item_ram.get('tit...
            info_viva_por_oferta[oid] = {
                "status": 200,
                "title": item_ram.get("title", ""),
                "variants": item_ram.get("variants", []),
                "fuente": "bulk_ram",
            }
        else:
            # Asignamos 't_tipo' con cfg_tipo_por_tienda.get(t_low, 'retail')
            t_tipo = cfg_tipo_por_tienda.get(t_low, "retail")
            # Ejecutamos instrucción: faltantes_red.append((oid, url, t_tipo))
            faltantes_red.append((oid, url, t_tipo))

    # Evaluamos la condición lógica (faltantes_red) para controlar el flujo
    if faltantes_red:
        # Deduplicar URLs idénticas para no consultar 2 veces la misma ficha
        urls_unicas: Dict[str, str] = {}
        # Recorremos iterativamente cada '(_, u, t_tipo)' en faltantes_red
        for _, u, t_tipo in faltantes_red:
            # Asignamos 'urls_unicas[u]' con t_tipo
            urls_unicas[u] = t_tipo
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(f"Consultando directamente {len(urls_unicas)} URLs no presentes en el índice RAM...")
        # Asignamos 'cache_red' con {}
        cache_red: Dict[str, Dict[str, Any]] = {}
        # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=8)
        with ThreadPoolExecutor(max_workers=8) as pool:
            # Asignamos 'futs' con {pool.submit(consultar_producto_vivo_indiv...
            futs = {pool.submit(consultar_producto_vivo_individual, u, tt): u for u, tt in urls_unicas.items()}
            # Recorremos iterativamente cada 'fut' en as_completed(futs)
            for fut in as_completed(futs):
                # Asignamos 'u' con futs[fut]
                u = futs[fut]
                # Asignamos 'cache_red[u]' con fut.result()
                cache_red[u] = fut.result()
        # Recorremos iterativamente cada '(oid, u, _)' en faltantes_red
        for oid, u, _ in faltantes_red:
            # Asignamos 'res_u' con dict(cache_red[u])
            res_u = dict(cache_red[u])
            # Asignamos 'res_u['fuente']' con 'http_directo'
            res_u["fuente"] = "http_directo"
            # Asignamos 'info_viva_por_oferta[oid]' con res_u
            info_viva_por_oferta[oid] = res_u

    # 4. Clasificar todos los candidatos y escribir CSV auditable
    resumen_counts = Counter()
    # Asignamos 'por_tienda_counts' con defaultdict(Counter)
    por_tienda_counts: Dict[str, Counter] = defaultdict(Counter)
    # Asignamos 'plan_acciones' con []
    plan_acciones: List[Dict[str, Any]] = []

    # Recorremos iterativamente cada '(o, v, t_nom, vol_slug)' en candidatos
    for o, v, t_nom, vol_slug in candidatos:
        # Asignamos 'oid' con int(o['id'])
        oid = int(o["id"])
        # Asignamos 'info_viva' con info_viva_por_oferta[oid]
        info_viva = info_viva_por_oferta[oid]
        # Asignamos 'decision' con clasificar_candidato_volumen(o, v, info_viva)
        decision = clasificar_candidato_volumen(o, v, info_viva)
        # Asignamos 'clasif' con decision['clasificacion']
        clasif = decision["clasificacion"]
        # Actualizamos acumulativamente el valor de 'resumen_counts[clasif]'
        resumen_counts[clasif] += 1
        # Actualizamos acumulativamente el valor de 'por_tienda_counts[t_nom][clasif]'
        por_tienda_counts[t_nom][clasif] += 1

        # Asignamos 'perf' con perfumes_by_id.get(int(v['perfume_id']), {})
        perf = perfumes_by_id.get(int(v["perfume_id"]), {})
        # Ejecutamos instrucción: plan_acciones.append({'oferta_id': oid, 'tienda_id':...
        plan_acciones.append({
            "oferta_id": oid,
            "tienda_id": int(o["tienda_id"]),
            "tienda": t_nom,
            "perfume_id": int(v["perfume_id"]),
            "perfume": f"{perf.get('marca', '')} - {perf.get('nombre', '')}".strip(" -"),
            "variante_id_anterior": int(v["id"]),
            "vol_anterior": float(v["volumen_ml"]),
            "formato": str(v.get("formato") or "regular").lower(),
            "vol_slug": vol_slug,
            "vol_nuevo": decision.get("vol_nuevo"),
            "precio_bd": int(o.get("precio_actual") or 0),
            "precio_vivo": decision.get("precio_vivo"),
            "precio_normal_vivo": decision.get("precio_normal_vivo"),
            "en_stock_bd": bool(o.get("en_stock")),
            "en_stock_vivo": decision.get("en_stock_vivo"),
            "clasificacion": clasif,
            "submotivo": decision.get("submotivo", ""),
            "es_404": bool(decision.get("es_404", False)),
            "fuente": info_viva.get("fuente", ""),
            "url_producto": o.get("url_producto", ""),
            "accion_aplicada": "dry_run" if not apply_changes else "pendiente",
        })

    # Asignamos 'ts_tag' con datetime.now().strftime('%Y%m%d_%H%M%S')
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Asignamos 'backup_dir' con REPO_ROOT / 'scratch' / 'backups'
    backup_dir = REPO_ROOT / "scratch" / "backups"
    # Ejecutamos instrucción: backup_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Asignamos 'csv_path' con backup_dir / f'reparacion_volumenes_{ts_ta...
    csv_path = backup_dir / f"reparacion_volumenes_{ts_tag}.csv"

    # 5. Aplicar cambios en BD si `--apply` está activo
    errores_aplicacion = 0
    # Asignamos 'variantes_origen_tocadas' con set()
    variantes_origen_tocadas: Set[int] = set()
    # Asignamos 'variantes_huerfanas_eliminadas' con 0
    variantes_huerfanas_eliminadas = 0

    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Asignamos 'now_iso' con datetime.now(timezone.utc).isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.info("Aplicando reparaciones verificadas en Supabase...")

        # Paso 5.1: Pre-crear en lote cualquier `variantes_perfume` destino faltante
        pendientes_var: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
        # Recorremos iterativamente cada 'item' en plan_acciones
        for item in plan_acciones:
            # Evaluamos la condición lógica (item['clasificacion'] != 'corregible_verificado') para controlar el flujo
            if item["clasificacion"] != "corregible_verificado":
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'pid' con item['perfume_id']
            pid = item["perfume_id"]
            # Asignamos 'vol_n' con int(item['vol_nuevo'])
            vol_n = int(item["vol_nuevo"])
            # Asignamos 'fmt' con item['formato']
            fmt = item["formato"]
            # Asignamos 'v_key' con (pid, vol_n, fmt)
            v_key = (pid, vol_n, fmt)
            # Evaluamos la condición lógica (v_key not in variante_lookup and v_key not in pendie...) para controlar el flujo
            if v_key not in variante_lookup and v_key not in pendientes_var:
                # Asignamos 'perf' con perfumes_by_id.get(pid, {})
                perf = perfumes_by_id.get(pid, {})
                # Asignamos 'conc' con perf.get('tipo') or 'Eau de Parfum'
                conc = perf.get("tipo") or "Eau de Parfum"
                # Asignamos 'slug_base' con f'p-{pid}-{vol_n}ml' if fmt == 'regular' e...
                slug_base = f"p-{pid}-{vol_n}ml" if fmt == "regular" else f"p-{pid}-{vol_n}ml-{fmt}"
                # Asignamos 'pendientes_var[v_key]' con {'perfume_id': pid, 'concentracion': conc,...
                pendientes_var[v_key] = {
                    "perfume_id": pid,
                    "concentracion": conc,
                    "volumen_ml": vol_n,
                    "formato": fmt,
                    "slug": slug_base,
                    "activa": True,
                }

        # Evaluamos la condición lógica (pendientes_var) para controlar el flujo
        if pendientes_var:
            # Asignamos 'lista_nuevas' con list(pendientes_var.values())
            lista_nuevas = list(pendientes_var.values())
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info(f"Creando {len(lista_nuevas)} variantes destino nuevas en `variantes_perfume`...")
            # Recorremos iterativamente cada 'i' en range(0, len(lista_nuevas), 200)
            for i in range(0, len(lista_nuevas), 200):
                # Asignamos 'lote_v' con lista_nuevas[i:i + 200]
                lote_v = lista_nuevas[i : i + 200]
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    ins_b = sb.table("variantes_perfume").insert(lote_v).execute()
                    # Recorremos iterativamente cada 'vr' en ins_b.data or []
                    for vr in ins_b.data or []:
                        # Asignamos 'vk' con (int(vr['perfume_id']), int(round(float(vr...
                        vk = (int(vr["perfume_id"]), int(round(float(vr["volumen_ml"]))), str(vr.get("formato") or "regular").lower())
                        # Asignamos 'variante_lookup[vk]' con vr
                        variante_lookup[vk] = vr
                except Exception:
                    # Recorremos iterativamente cada 'row_v' en lote_v
                    for row_v in lote_v:
                        # Asignamos 'vk' con (int(row_v['perfume_id']), int(row_v['volu...
                        vk = (int(row_v["perfume_id"]), int(row_v["volumen_ml"]), str(row_v["formato"]).lower())
                        # Bloque try/except para manejo seguro de errores y resiliencia operativa
                        try:
                            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                            ins_1 = sb.table("variantes_perfume").insert(row_v).execute()
                            # Evaluamos la condición lógica (ins_1.data) para controlar el flujo
                            if ins_1.data:
                                # Asignamos 'variante_lookup[vk]' con ins_1.data[0]
                                variante_lookup[vk] = ins_1.data[0]
                        except Exception:
                            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                            q_ex = (
                                sb.table("variantes_perfume")
                                .select("id, perfume_id, concentracion, volumen_ml, formato, slug")
                                .eq("perfume_id", row_v["perfume_id"])
                                .eq("volumen_ml", row_v["volumen_ml"])
                                .eq("formato", row_v["formato"])
                                .limit(1)
                                .execute()
                            )
                            # Evaluamos la condición lógica (q_ex.data) para controlar el flujo
                            if q_ex.data:
                                # Asignamos 'variante_lookup[vk]' con q_ex.data[0]
                                variante_lookup[vk] = q_ex.data[0]
                            else:
                                # Asignamos 'row_v2' con dict(row_v, slug=f"{row_v['slug']}-u{int(d...
                                row_v2 = dict(row_v, slug=f"{row_v['slug']}-u{int(datetime.now().timestamp())}")
                                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                                ins_2 = sb.table("variantes_perfume").insert(row_v2).execute()
                                # Asignamos 'variante_lookup[vk]' con ins_2.data[0]
                                variante_lookup[vk] = ins_2.data[0]

        # Paso 5.2: Ejecutar mutaciones agrupadas por (perfume_id, tienda_id) con clientes thread-local
        from supabase import create_client

        # Asignamos 'creds' con _obtener_mapa_credenciales()
        creds = _obtener_mapa_credenciales()
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb_url = creds["SUPABASE_URL"]
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb_key = creds.get("SUPABASE_SERVICE_ROLE_KEY") or creds["SUPABASE_KEY"]
        # Asignamos 'tls' con threading.local()
        tls = threading.local()

        # Definición de función '_get_thread_sb' sin parámetros externos
        def _get_thread_sb():
            # Asignamos 'cli' con getattr(tls, 'sb', None)
            cli = getattr(tls, "sb", None)
            # Evaluamos la condición lógica (cli is None) para controlar el flujo
            if cli is None:
                # Asignamos 'cli' con create_client(sb_url, sb_key)
                cli = create_client(sb_url, sb_key)
                # Asignamos 'tls.sb' con cli
                tls.sb = cli
            # Retornamos el resultado procesado (cli)
            return cli

        # Asignamos 'grupos_pt' con defaultdict(list)
        grupos_pt: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
        # Recorremos iterativamente cada 'item' en plan_acciones
        for item in plan_acciones:
            # Ejecutamos instrucción: grupos_pt[item['perfume_id'], item['tienda_id']].app...
            grupos_pt[(item["perfume_id"], item["tienda_id"])].append(item)

        # Asignamos 'lock_meta' con threading.Lock()
        lock_meta = threading.Lock()

        # Definición de función '_procesar_grupo_pt' (parámetros: items_grupo)
        def _procesar_grupo_pt(items_grupo: List[Dict[str, Any]]) -> int:
            # Asignamos 'cli' con _get_thread_sb()
            cli = _get_thread_sb()
            # Asignamos 'err_local' con 0
            err_local = 0
            # Recorremos iterativamente cada 'item' en items_grupo
            for item in items_grupo:
                # Asignamos 'oid' con item['oferta_id']
                oid = item["oferta_id"]
                # Asignamos 'clasif' con item['clasificacion']
                clasif = item["clasificacion"]
                # Asignamos 'old_vid' con item['variante_id_anterior']
                old_vid = item["variante_id_anterior"]
                # Asignamos 'tid' con item['tienda_id']
                tid = item["tienda_id"]
                # Asignamos 'url_p' con item['url_producto']
                url_p = item["url_producto"]

                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Evaluamos la condición lógica (clasif == 'coherente_multivariante') para controlar el flujo
                    if clasif == "coherente_multivariante":
                        # Asignamos 'item['accion_aplicada']' con 'mantenida_multivariante'
                        item["accion_aplicada"] = "mantenida_multivariante"
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Evaluamos la condición lógica (clasif == 'corregible_verificado') para controlar el flujo
                    if clasif == "corregible_verificado":
                        # Asignamos 'v_dest' con variante_lookup[item['perfume_id'], int(it...
                        v_dest = variante_lookup[(item["perfume_id"], int(item["vol_nuevo"]), item["formato"])]
                        # Asignamos 'dest_vid' con int(v_dest['id'])
                        dest_vid = int(v_dest["id"])
                        # Evaluamos la condición lógica (dest_vid == old_vid) para controlar el flujo
                        if dest_vid == old_vid:
                            # Asignamos 'item['accion_aplicada']' con 'ya_en_variante_destino'
                            item["accion_aplicada"] = "ya_en_variante_destino"
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Gestión automática de contexto y recursos para: lock_meta
                        with lock_meta:
                            # Ejecutamos instrucción: variantes_origen_tocadas.add(old_vid)
                            variantes_origen_tocadas.add(old_vid)
                            # Asignamos 'existente_dest' con oferta_por_var_tienda.get((dest_vid, tid))
                            existente_dest = oferta_por_var_tienda.get((dest_vid, tid))

                        # Asignamos 'p_vivo' con int(item['precio_vivo'])
                        p_vivo = int(item["precio_vivo"])
                        # Asignamos 'p_norm_vivo' con int(item['precio_normal_vivo'] or p_vivo)
                        p_norm_vivo = int(item["precio_normal_vivo"] or p_vivo)
                        # Asignamos 'st_vivo' con bool(item['en_stock_vivo'])
                        st_vivo = bool(item["en_stock_vivo"])

                        # Ejecutamos instrucción: cli.table('precios_registro').update({'variante_id':...
                        cli.table("precios_registro").update({"variante_id": dest_vid}).eq(
                            "variante_id", old_vid
                        ).eq("tienda_id", tid).eq("url_producto", url_p).execute()

                        # Evaluamos la condición lógica (existente_dest and int(existente_dest['id']) != oid) para controlar el flujo
                        if existente_dest and int(existente_dest["id"]) != oid:
                            # Evaluamos la condición lógica (st_vivo or not existente_dest.get('en_stock')) para controlar el flujo
                            if st_vivo or not existente_dest.get("en_stock"):
                                # Ejecutamos instrucción: cli.table('ofertas_actuales').update({'precio_actual...
                                cli.table("ofertas_actuales").update({
                                    "precio_actual": p_vivo,
                                    "precio_normal": max(p_norm_vivo, p_vivo),
                                    "en_stock": st_vivo,
                                    "url_producto": url_p,
                                    "estado": "activa" if st_vivo else "agotada",
                                    "ultima_verificacion_exitosa": now_iso,
                                    "ultimo_intento": now_iso,
                                    "fallos_consecutivos": 0,
                                    "ultimo_error": None,
                                    "updated_at": now_iso,
                                }).eq("id", int(existente_dest["id"])).execute()
                            # Ejecutamos instrucción: cli.table('ofertas_actuales').delete().eq('id', oid)...
                            cli.table("ofertas_actuales").delete().eq("id", oid).execute()
                            # Gestión automática de contexto y recursos para: lock_meta
                            with lock_meta:
                                # Ejecutamos instrucción: oferta_por_var_tienda.pop((old_vid, tid), None)
                                oferta_por_var_tienda.pop((old_vid, tid), None)
                            # Asignamos 'item['accion_aplicada']' con f"fusionada_en_oferta_{existente_dest['id'...
                            item["accion_aplicada"] = f"fusionada_en_oferta_{existente_dest['id']}_var_{dest_vid}"
                        else:
                            # Ejecutamos instrucción: cli.table('ofertas_actuales').update({'variante_id':...
                            cli.table("ofertas_actuales").update({
                                "variante_id": dest_vid,
                                "precio_actual": p_vivo,
                                "precio_normal": max(p_norm_vivo, p_vivo),
                                "en_stock": st_vivo,
                                "estado": "activa" if st_vivo else "agotada",
                                "ultima_verificacion_exitosa": now_iso,
                                "ultimo_intento": now_iso,
                                "fallos_consecutivos": 0,
                                "ultimo_error": None,
                                "updated_at": now_iso,
                            }).eq("id", oid).execute()
                            # Gestión automática de contexto y recursos para: lock_meta
                            with lock_meta:
                                # Ejecutamos instrucción: oferta_por_var_tienda.pop((old_vid, tid), None)
                                oferta_por_var_tienda.pop((old_vid, tid), None)
                                # Asignamos 'oferta_por_var_tienda[dest_vid, ...' con {'id': oid, 'en_stock': st_vivo}
                                oferta_por_var_tienda[(dest_vid, tid)] = {"id": oid, "en_stock": st_vivo}
                            # Asignamos 'item['accion_aplicada']' con f'movida_a_variante_{dest_vid}'
                            item["accion_aplicada"] = f"movida_a_variante_{dest_vid}"

                    # Evaluamos la condición lógica (clasif == 'miniatura_retirada') para controlar el flujo
                    elif clasif == "miniatura_retirada":
                        # Gestión automática de contexto y recursos para: lock_meta
                        with lock_meta:
                            # Ejecutamos instrucción: variantes_origen_tocadas.add(old_vid)
                            variantes_origen_tocadas.add(old_vid)
                        # Ejecutamos instrucción: cli.table('ofertas_actuales').update({'en_stock': Fa...
                        cli.table("ofertas_actuales").update({
                            "en_stock": False,
                            "estado": "retirada",
                            "ultimo_error": f"reparar_volumenes: {item['submotivo']}",
                            "updated_at": now_iso,
                        }).eq("id", oid).execute()
                        # Asignamos 'item['accion_aplicada']' con 'retirada_miniatura'
                        item["accion_aplicada"] = "retirada_miniatura"

                    # Evaluamos la condición lógica (clasif == 'no_verificable') para controlar el flujo
                    elif clasif == "no_verificable":
                        # Asignamos 'payload_nv' con {'estado': 'requiere_revision', 'ultimo_er...
                        payload_nv: Dict[str, Any] = {
                            "estado": "requiere_revision",
                            "ultimo_error": f"reparar_volumenes: {item['submotivo']}",
                            "updated_at": now_iso,
                        }
                        # Evaluamos la condición lógica (item['es_404']) para controlar el flujo
                        if item["es_404"]:
                            # Asignamos 'payload_nv['en_stock']' con False
                            payload_nv["en_stock"] = False
                        # Ejecutamos instrucción: cli.table('ofertas_actuales').update(payload_nv).eq(...
                        cli.table("ofertas_actuales").update(payload_nv).eq("id", oid).execute()
                        # Asignamos 'item['accion_aplicada']' con 'marcada_requiere_revision_404' if item['e...
                        item["accion_aplicada"] = "marcada_requiere_revision_404" if item["es_404"] else "marcada_requiere_revision"

                except Exception as exc:
                    # Actualizamos acumulativamente el valor de 'err_local'
                    err_local += 1
                    # Asignamos 'item['accion_aplicada']' con f'ERROR: {exc}'
                    item["accion_aplicada"] = f"ERROR: {exc}"
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.error(f"Error aplicando acción sobre oferta #{oid}: {exc}")
            # Retornamos el resultado procesado (err_local)
            return err_local

        # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=6)
        with ThreadPoolExecutor(max_workers=6) as pool:
            # Recorremos iterativamente cada 'e_cnt' en pool.map(_procesar_grupo_pt, grupos_pt.val...
            for e_cnt in pool.map(_procesar_grupo_pt, grupos_pt.values()):
                # Actualizamos acumulativamente el valor de 'errores_aplicacion'
                errores_aplicacion += e_cnt

        # Paso 5.3: Eliminar en lotes variantes antiguas que quedaron 100% huérfanas (0 ofertas y 0 precios_registro)
        cand_vids = sorted(variantes_origen_tocadas)
        # Asignamos 'vids_con_uso' con set()
        vids_con_uso: Set[int] = set()
        # Recorremos iterativamente cada 'i' en range(0, len(cand_vids), 150)
        for i in range(0, len(cand_vids), 150):
            # Asignamos 'chunk_v' con cand_vids[i:i + 150]
            chunk_v = cand_vids[i : i + 150]
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            r_of = sb.table("ofertas_actuales").select("variante_id").in_("variante_id", chunk_v).execute().data or []
            # Recorremos iterativamente cada 'r' en r_of
            for r in r_of:
                # Ejecutamos instrucción: vids_con_uso.add(int(r['variante_id']))
                vids_con_uso.add(int(r["variante_id"]))
            # Asignamos 'rem_check' con [vid for vid in chunk_v if vid not in vids...
            rem_check = [vid for vid in chunk_v if vid not in vids_con_uso]
            # Evaluamos la condición lógica (rem_check) para controlar el flujo
            if rem_check:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                r_pr = sb.table("precios_registro").select("variante_id").in_("variante_id", rem_check).limit(1000).execute().data or []
                # Recorremos iterativamente cada 'r' en r_pr
                for r in r_pr:
                    # Ejecutamos instrucción: vids_con_uso.add(int(r['variante_id']))
                    vids_con_uso.add(int(r["variante_id"]))

        # Asignamos 'vids_huerfanas' con [vid for vid in cand_vids if vid not in vi...
        vids_huerfanas = [vid for vid in cand_vids if vid not in vids_con_uso]
        # Recorremos iterativamente cada 'wid' en vids_huerfanas
        for wid in vids_huerfanas:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Doble verificación individual exacta antes del DELETE (0 filas en ambas tablas)
                c1 = sb.table("ofertas_actuales").select("id", count="exact").eq("variante_id", wid).limit(1).execute()
                # Evaluamos la condición lógica ((c1.count or 0) > 0 or c1.data) para controlar el flujo
                if (c1.count or 0) > 0 or c1.data:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                c2 = sb.table("precios_registro").select("id", count="exact").eq("variante_id", wid).limit(1).execute()
                # Evaluamos la condición lógica ((c2.count or 0) > 0 or c2.data) para controlar el flujo
                if (c2.count or 0) > 0 or c2.data:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("variantes_perfume").delete().eq("id", wid).execute()
                # Actualizamos acumulativamente el valor de 'variantes_huerfanas_eliminadas'
                variantes_huerfanas_eliminadas += 1
            except Exception as exc:
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.warning(f"No se eliminó variante #{wid} por restricción activa: {exc}")

        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()

    # 6. Guardar registro CSV completo de auditoría
    fieldnames = list(plan_acciones[0].keys())
    # Gestión automática de contexto y recursos para: csv_path.open('w', encoding='utf-8', newline='')
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        # Asignamos 'writer' con csv.DictWriter(fh, fieldnames=fieldnames)
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        # Ejecutamos instrucción: writer.writeheader()
        writer.writeheader()
        # Ejecutamos instrucción: writer.writerows(plan_acciones)
        writer.writerows(plan_acciones)

    # Ejecutamos instrucción: print('\n' + '=' * 78)
    print("\n" + "=" * 78)
    # Ejecutamos instrucción: print(f"REPORTE REPARACIÓN DE VOLÚMENES ({('APPLY' i...
    print(f"REPORTE REPARACIÓN DE VOLÚMENES ({'APPLY' if apply_changes else 'DRY-RUN'})")
    # Ejecutamos instrucción: print('=' * 78)
    print("=" * 78)
    # Ejecutamos instrucción: print(f'Candidatos evaluados : {len(plan_acciones)}')
    print(f"Candidatos evaluados            : {len(plan_acciones)}")
    # Recorremos iterativamente cada 'k' en ('corregible_verificado', 'coherente_multi...
    for k in ("corregible_verificado", "coherente_multivariante", "miniatura_retirada", "no_verificable"):
        # Ejecutamos instrucción: print(f' - {k:28s}: {resumen_counts[k]}')
        print(f"  - {k:28s}: {resumen_counts[k]}")
    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Ejecutamos instrucción: print(f'Variantes huérfanas eliminadas : {variantes_...
        print(f"Variantes huérfanas eliminadas  : {variantes_huerfanas_eliminadas}")
        # Ejecutamos instrucción: print(f'Errores de escritura : {errores_aplicacion}')
        print(f"Errores de escritura            : {errores_aplicacion}")
    # Ejecutamos instrucción: print('\nDesglose por tienda:')
    print("\nDesglose por tienda:")
    # Recorremos iterativamente cada 't_nom' en sorted(por_tienda_counts.keys())
    for t_nom in sorted(por_tienda_counts.keys()):
        # Asignamos 'c' con por_tienda_counts[t_nom]
        c = por_tienda_counts[t_nom]
        # Ejecutamos instrucción: print(f" {t_nom:20s} | corregibles={c['corregible_ve...
        print(
            f"  {t_nom:20s} | corregibles={c['corregible_verificado']:4d} | "
            f"multivar_ok={c['coherente_multivariante']:4d} | "
            f"mini={c['miniatura_retirada']:3d} | no_verif={c['no_verificable']:4d}"
        )
    # Ejecutamos instrucción: print(f'\nCSV de auditoría guardado en: {csv_path}')
    print(f"\nCSV de auditoría guardado en: {csv_path}")
    # Ejecutamos instrucción: print('=' * 78)
    print("=" * 78)

    # Retornamos el resultado procesado ({'total_candidatos': len(plan_acciones), 'resum...)
    return {
        "total_candidatos": len(plan_acciones),
        "resumen": dict(resumen_counts),
        "errores_aplicacion": errores_aplicacion,
        "variantes_huerfanas_eliminadas": variantes_huerfanas_eliminadas,
        "csv_path": str(csv_path),
    }


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Reparación verificada de incoherencias URL <-> volumen_ml.")
    # Asignamos 'grp' con parser.add_mutually_exclusive_group()
    grp = parser.add_mutually_exclusive_group()
    # Ejecutamos instrucción: grp.add_argument('--dry-run', action='store_true', d...
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo simula y genera CSV sin escribir en BD (por defecto).")
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    grp.add_argument("--apply", action="store_true", help="Aplica en Supabase las correcciones verificadas.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--store", type=str, default=None, help="Filtrar por nombre de tienda (ej. 'Mundo Aromas').")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Ejecutamos instrucción: ejecutar_reparacion_volumenes(apply_changes=bool(arg...
    ejecutar_reparacion_volumenes(apply_changes=bool(args.apply), store_filter=args.store)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()
