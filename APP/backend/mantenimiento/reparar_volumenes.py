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

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import sys
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

import requests

# Configuración de rutas
REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import _obtener_mapa_credenciales, get_supabase, limpiar_cache_catalogo
from backend.normalizador import (
    detectar_formato_oferta,
    es_precio_valido,
    extraer_volumen_ml,
    extraer_volumen_ml_opcional,
    resolver_volumen_oferta,
)
from backend.scraper_periodico import (
    TIENDAS_CRAWLER_CONFIG,
    clean_digits,
    crear_sesion_robusta,
    precargar_catalogos_bulk_tiendas,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("RepararVolumenes")


# - ¿Qué hace esta función?:
#   Descarga todas las filas de una tabla de Supabase paginando de a 1.000 registros
#   para no truncar resultados con el límite por defecto de PostgREST.
def fetch_all_supabase(sb: Any, table: str, select: str = "*") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        res = sb.table(table).select(select).order("id", desc=False).range(offset, offset + 999).execute()
        batch = res.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


# - ¿Qué hace esta función?:
#   Normaliza una URL comercial quitando parámetros de consulta, fragmentos, barra final
#   y prefijo `www.` para cruzar de forma exacta `ofertas_actuales.url_producto` con feeds vivos.
def normalizar_url_clave(url: str) -> str:
    if not url:
        return ""
    limpia = url.strip().split("?")[0].split("#")[0].rstrip("/").lower()
    limpia = re.sub(r"^https?://(www\.)?", "https://", limpia)
    return limpia


# - ¿Qué hace esta función?:
#   Extrae el último segmento útil (`handle` o `slug`) de una URL comercial.
def extraer_handle_url(url: str) -> str:
    limpia = normalizar_url_clave(url)
    if not limpia:
        return ""
    return limpia.split("/")[-1]


# - ¿Qué hace esta función?:
#   Consulta directamente una URL individual que no apareció en el catálogo masivo en RAM
#   (ej. productos antiguos de Shopify vía `.json`, fichas de Falabella vía `__NEXT_DATA__`,
#   o páginas WooCommerce), devolviendo estado HTTP y lista estandarizada de variantes vivas.
def consultar_producto_vivo_individual(
    url: str,
    tipo_tienda: str,
) -> Dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9",
    }
    sess = curl_requests.Session(impersonate="chrome120") if curl_requests is not None else requests.Session()
    clean_u = url.split("?")[0].rstrip("/")

    # 1. Shopify: endpoint directo `<url>.json`
    if tipo_tienda == "shopify" and "/products/" in clean_u:
        try:
            r = sess.get(f"{clean_u}.json", headers=headers, timeout=12)
            if r.status_code == 404:
                return {"status": 404, "variants": [], "title": ""}
            if r.status_code in (403, 429):
                return {"status": r.status_code, "variants": [], "title": ""}
            if r.status_code == 200:
                prod = (r.json() or {}).get("product") or {}
                title = str(prod.get("title") or "").strip()
                v_list = []
                for v in prod.get("variants") or []:
                    p_act = clean_digits(str(v.get("price", "0")).split(".")[0])
                    p_cmp_raw = v.get("compare_at_price")
                    p_cmp = clean_digits(str(p_cmp_raw).split(".")[0]) if p_cmp_raw else p_act
                    in_st = bool(v.get("available", True)) if "available" in v else (int(v.get("inventory_quantity") or 0) > 0)
                    v_list.append({
                        "title": str(v.get("title") or ""),
                        "price": p_act,
                        "compare_at_price": max(p_cmp, p_act),
                        "available": in_st,
                    })
                return {"status": 200, "title": title, "variants": v_list}
        except Exception as exc:
            return {"status": 0, "error": str(exc), "variants": [], "title": ""}

    # 2. Falabella o WooCommerce / HTML PDP
    try:
        r = sess.get(url, headers=headers, timeout=14, allow_redirects=True)
        status = r.status_code
        final_u = str(getattr(r, "url", url) or url)
        # Detección de redirección al home o catálogo genérico (soft-404)
        final_path = re.sub(r"^https?://[^/]+", "", final_u.split("?")[0]).strip("/")
        if status == 404 or final_path in ("", "falabella-cl"):
            return {"status": 404, "variants": [], "title": ""}
        if status in (403, 429):
            return {"status": status, "variants": [], "title": ""}
        if status != 200:
            return {"status": status, "variants": [], "title": ""}

        html_txt = r.text or ""
        soup = BeautifulSoup(html_txt, "html.parser")

        # Falabella `__NEXT_DATA__`
        if "falabella" in clean_u.lower():
            tag = soup.find("script", id="__NEXT_DATA__")
            if tag and tag.string:
                data = json.loads(tag.string)
                pdata = data.get("props", {}).get("pageProps", {}).get("productData", {})
                if not pdata:
                    return {"status": 404, "variants": [], "title": ""}
                p_title = str(pdata.get("name") or "").strip()
                is_prod_out = bool(pdata.get("isOutOfStock", False))
                skus = pdata.get("variants") or pdata.get("skus") or []
                v_list = []
                for v in skus:
                    v_name = str(v.get("name") or p_title)
                    size_attr = (v.get("attributes") or {}).get("size")
                    size_num = clean_digits(size_attr) if size_attr else 0
                    v_label = f"{size_num}ml" if (10 <= size_num <= 1000) else v_name
                    prices = v.get("prices") or []
                    p_act, p_norm = 0, 0
                    for pi in prices:
                        pt = pi.get("type", "")
                        pv = clean_digits((pi.get("price") or ["0"])[0])
                        if pt in ("internetPrice", "eventPrice") and pv > 0:
                            p_act = pv
                        elif pt == "normalPrice" and pv > 0:
                            p_norm = pv
                    if p_act == 0 and prices:
                        p_act = clean_digits((prices[0].get("price") or ["0"])[0])
                    avail_v = not is_prod_out and not bool(v.get("isOutOfStock", False))
                    if p_act > 0:
                        v_list.append({
                            "title": v_label,
                            "price": p_act,
                            "compare_at_price": max(p_norm, p_act),
                            "available": avail_v,
                        })
                return {"status": 200, "title": p_title, "variants": v_list}

        # WooCommerce / HTML genérico con JSON-LD o `<h1 class="product_title">`
        low_html = html_txt.lower()
        if "página no encontrada" in low_html or "page not found" in low_html or "error 404" in low_html:
            return {"status": 404, "variants": [], "title": ""}

        h1 = soup.find("h1")
        p_title = h1.get_text(" ", strip=True) if h1 else ""
        v_list = []
        for s_tag in soup.find_all("script", type="application/ld+json"):
            try:
                raw_ld = json.loads(s_tag.string or s_tag.get_text() or "{}")
                nodes = raw_ld if isinstance(raw_ld, list) else (raw_ld.get("@graph") or [raw_ld])
                for nd in nodes:
                    if isinstance(nd, dict) and "Product" in str(nd.get("@type", "")):
                        p_title = p_title or str(nd.get("name") or "").strip()
                        offs = nd.get("offers") or []
                        if isinstance(offs, dict):
                            offs = [offs]
                        for off in offs:
                            if not isinstance(off, dict):
                                continue
                            pr = clean_digits(str(off.get("price") or "0").split(".")[0])
                            av = "outofstock" not in str(off.get("availability") or "").lower()
                            if pr > 0:
                                v_list.append({
                                    "title": str(off.get("name") or ""),
                                    "price": pr,
                                    "compare_at_price": pr,
                                    "available": av,
                                })
            except Exception:
                continue
        return {"status": 200, "title": p_title, "variants": v_list}
    except Exception as exc:
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
    url = str(oferta.get("url_producto") or "")
    db_vol = float(variante_db.get("volumen_ml") or 100.0)
    db_price = int(oferta.get("precio_actual") or 0)
    db_formato = str(variante_db.get("formato") or "regular").lower()
    es_tester = db_formato == "tester" or (detectar_formato_oferta("", url) == "tester")

    status = int(info_viva.get("status") or 0)
    if status == 404:
        return {
            "clasificacion": "no_verificable",
            "submotivo": "http_404_o_eliminado",
            "es_404": True,
            "vol_nuevo": None,
        }
    if status in (403, 429) or status != 200:
        return {
            "clasificacion": "no_verificable",
            "submotivo": f"http_{status or 'timeout'}",
            "es_404": False,
            "vol_nuevo": None,
        }

    live_title = str(info_viva.get("title") or "").strip()
    raw_vars = info_viva.get("variants") or []
    if not raw_vars:
        return {
            "clasificacion": "no_verificable",
            "submotivo": "sin_variantes_en_pdp",
            "es_404": False,
            "vol_nuevo": None,
        }

    n_vars = len(raw_vars)
    parsed_vars: List[Dict[str, Any]] = []
    for rv in raw_vars:
        vt = str(rv.get("title") or "")
        try:
            pr = int(float(rv.get("price") or 0))
        except (ValueError, TypeError):
            pr = 0
        try:
            pc = int(float(rv.get("compare_at_price") or pr)) if rv.get("compare_at_price") else pr
        except (ValueError, TypeError):
            pc = pr
        avail = bool(rv.get("available", True))

        # Chequear si es miniatura explícita (< 25 ml) antes de resolver_volumen_oferta
        vol_raw_v = extraer_volumen_ml_opcional(vt)
        vol_raw_t = extraer_volumen_ml_opcional(live_title)
        vol_raw_u = extraer_volumen_ml_opcional(url.rstrip("/").split("/")[-1])

        vol_res = resolver_volumen_oferta(
            titulo_variante=vt,
            titulo_producto=live_title,
            url_slug=url,
            volumen_ml_defecto=None,
            n_variantes_producto=n_vars,
            es_tester=es_tester,
        )
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
        return {
            "clasificacion": "miniatura_retirada",
            "submotivo": f"miniatura_{parsed_vars[0]['vol_miniatura']}ml",
            "es_404": False,
            "vol_nuevo": parsed_vars[0]["vol_miniatura"],
        }

    # Caso 1: Producto multivariante donde existe una variante con db_vol y precio compatible
    if n_vars > 1:
        vars_mismo_vol = [pv for pv in parsed_vars if pv["vol"] and abs(pv["vol"] - db_vol) <= 1 and pv["price"] > 0]
        vars_otro_vol = [pv for pv in parsed_vars if pv["vol"] and abs(pv["vol"] - db_vol) > 1 and pv["vol"] >= 25 and pv["price"] > 0]

        if vars_mismo_vol:
            mv = min(vars_mismo_vol, key=lambda x: abs(x["price"] - db_price))
            diff_mismo = abs(mv["price"] - db_price) / max(db_price, 1)
            mejor_otro = min(vars_otro_vol, key=lambda x: abs(x["price"] - db_price)) if vars_otro_vol else None
            diff_otro = (abs(mejor_otro["price"] - db_price) / max(db_price, 1)) if mejor_otro else 999.0

            if diff_mismo <= 0.08 or (diff_mismo <= 0.18 and diff_mismo < diff_otro):
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
            mejor_otro = min(vars_otro_vol, key=lambda x: abs(x["price"] - db_price))
            diff_otro = abs(mejor_otro["price"] - db_price) / max(db_price, 1)
            if diff_otro <= 0.05 and es_precio_valido(mejor_otro["price"]):
                return {
                    "clasificacion": "corregible_verificado",
                    "submotivo": f"multivariante_precio_calza_{mejor_otro['vol']}ml",
                    "es_404": False,
                    "vol_nuevo": int(mejor_otro["vol"]),
                    "precio_vivo": mejor_otro["price"],
                    "precio_normal_vivo": mejor_otro["compare_at_price"],
                    "en_stock_vivo": mejor_otro["available"],
                }

        return {
            "clasificacion": "no_verificable",
            "submotivo": "multivariante_precio_no_concluyente",
            "es_404": False,
            "vol_nuevo": None,
        }

    # Caso 2: Producto de 1 sola variante en la tienda
    pv0 = parsed_vars[0]
    vol_real = pv0["vol"]
    if vol_real and vol_real >= 25 and abs(vol_real - db_vol) > 1 and es_precio_valido(pv0["price"]):
        diff_pct = abs(pv0["price"] - db_price) / max(db_price, 1)
        return {
            "clasificacion": "corregible_verificado",
            "submotivo": f"univariante_confirmado_{vol_real}ml_diff_{diff_pct:.2f}",
            "es_404": False,
            "vol_nuevo": int(vol_real),
            "precio_vivo": pv0["price"],
            "precio_normal_vivo": pv0["compare_at_price"],
            "en_stock_vivo": pv0["available"],
        }

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
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("No se pudo inicializar cliente Supabase con service_role.")

    logger.info("Cargando catálogo maestro desde Supabase (tiendas, perfumes, variantes, ofertas)...")
    tiendas_rows = sb.table("tiendas").select("id, nombre, url_base").execute().data or []
    tiendas_by_id = {int(t["id"]): t for t in tiendas_rows}
    perfumes_by_id = {int(p["id"]): p for p in fetch_all_supabase(sb, "perfumes", "id, nombre, marca, tipo")}
    variantes_rows = fetch_all_supabase(sb, "variantes_perfume", "id, perfume_id, concentracion, volumen_ml, formato, slug")
    variantes_by_id = {int(v["id"]): v for v in variantes_rows}
    ofertas_rows = fetch_all_supabase(
        sb,
        "ofertas_actuales",
        "id, variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, estado, ultima_verificacion_exitosa",
    )

    # Índice de variantes por (perfume_id, vol_redondeado, formato) y de ofertas por (variante_id, tienda_id)
    variante_lookup: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for v in variantes_rows:
        key = (int(v["perfume_id"]), int(round(float(v["volumen_ml"]))), str(v.get("formato") or "regular").lower())
        if key not in variante_lookup:
            variante_lookup[key] = v

    oferta_por_var_tienda: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for o in ofertas_rows:
        oferta_por_var_tienda[(int(o["variante_id"]), int(o["tienda_id"]))] = o

    # 1. Seleccionar candidatos incoherentes (ofertas activas con slug explícito NN ml != variante.volumen_ml)
    candidatos: List[Tuple[Dict[str, Any], Dict[str, Any], str, int]] = []
    for o in ofertas_rows:
        if o.get("estado") != "activa":
            continue
        t_info = tiendas_by_id.get(int(o["tienda_id"]))
        t_nombre = t_info["nombre"] if t_info else str(o["tienda_id"])
        if store_filter and store_filter.lower() not in t_nombre.lower():
            continue
        url = str(o.get("url_producto") or "")
        slug = url.rstrip("/").split("/")[-1]
        if not re.search(r"\d\s*[-_]?\s*ml", slug, re.I):
            continue
        v = variantes_by_id.get(int(o["variante_id"]))
        if not v or str(v.get("formato") or "regular").lower() == "tester":
            continue
        vol_slug = extraer_volumen_ml_opcional(slug) or extraer_volumen_ml(slug, default=0)
        if vol_slug and abs(vol_slug - float(v["volumen_ml"])) > 1:
            candidatos.append((o, v, t_nombre, int(vol_slug)))

    logger.info(
        f"Candidatos incoherentes detectados: {len(candidatos)} "
        f"(en_stock=True: {sum(1 for o, _, _, _ in candidatos if o.get('en_stock'))})"
    )
    if not candidatos:
        return {"total_candidatos": 0}

    # 2. Precargar catálogos masivos de las tiendas involucradas
    tiendas_involucradas = sorted({t_nom for _, _, t_nom, _ in candidatos})
    session = crear_sesion_robusta()
    bulk_map = precargar_catalogos_bulk_tiendas(
        session=session,
        tiendas_db=tiendas_rows,
        filtro_tiendas=tiendas_involucradas,
        max_workers=6,
    )

    cfg_tipo_por_tienda = {c["nombre"].lower(): c.get("tipo", "shopify") for c in TIENDAS_CRAWLER_CONFIG}
    bulk_por_url: Dict[Tuple[str, str], Dict[str, Any]] = {}
    bulk_por_handle: Dict[Tuple[str, str], Dict[str, Any]] = {}
    tiendas_con_feed_completo: Set[str] = set()

    for t_nom, cat in bulk_map.items():
        t_low = t_nom.lower()
        # Si cargó < 3400 items (límite 14*250=3500), el feed en RAM está completo
        if 0 < cat.total_productos < 3400:
            tiendas_con_feed_completo.add(t_low)
        for it in cat.todos_items:
            u_norm = normalizar_url_clave(it.get("url", ""))
            h_norm = extraer_handle_url(it.get("url", ""))
            if u_norm:
                bulk_por_url[(t_low, u_norm)] = it
            if h_norm:
                bulk_por_handle[(t_low, h_norm)] = it

    # 3. Resolver info viva (primero RAM O(1), luego fetch individual concurrente para faltantes)
    info_viva_por_oferta: Dict[int, Dict[str, Any]] = {}
    faltantes_red: List[Tuple[int, str, str]] = []

    for o, _, t_nom, _ in candidatos:
        oid = int(o["id"])
        t_low = t_nom.lower()
        url = str(o.get("url_producto") or "")
        item_ram = bulk_por_url.get((t_low, normalizar_url_clave(url))) or bulk_por_handle.get((t_low, extraer_handle_url(url)))
        if item_ram is not None:
            info_viva_por_oferta[oid] = {
                "status": 200,
                "title": item_ram.get("title", ""),
                "variants": item_ram.get("variants", []),
                "fuente": "bulk_ram",
            }
        else:
            t_tipo = cfg_tipo_por_tienda.get(t_low, "retail")
            faltantes_red.append((oid, url, t_tipo))

    if faltantes_red:
        # Deduplicar URLs idénticas para no consultar 2 veces la misma ficha
        urls_unicas: Dict[str, str] = {}
        for _, u, t_tipo in faltantes_red:
            urls_unicas[u] = t_tipo
        logger.info(f"Consultando directamente {len(urls_unicas)} URLs no presentes en el índice RAM...")
        cache_red: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(consultar_producto_vivo_individual, u, tt): u for u, tt in urls_unicas.items()}
            for fut in as_completed(futs):
                u = futs[fut]
                cache_red[u] = fut.result()
        for oid, u, _ in faltantes_red:
            res_u = dict(cache_red[u])
            res_u["fuente"] = "http_directo"
            info_viva_por_oferta[oid] = res_u

    # 4. Clasificar todos los candidatos y escribir CSV auditable
    resumen_counts = Counter()
    por_tienda_counts: Dict[str, Counter] = defaultdict(Counter)
    plan_acciones: List[Dict[str, Any]] = []

    for o, v, t_nom, vol_slug in candidatos:
        oid = int(o["id"])
        info_viva = info_viva_por_oferta[oid]
        decision = clasificar_candidato_volumen(o, v, info_viva)
        clasif = decision["clasificacion"]
        resumen_counts[clasif] += 1
        por_tienda_counts[t_nom][clasif] += 1

        perf = perfumes_by_id.get(int(v["perfume_id"]), {})
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

    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = REPO_ROOT / "scratch" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    csv_path = backup_dir / f"reparacion_volumenes_{ts_tag}.csv"

    # 5. Aplicar cambios en BD si `--apply` está activo
    errores_aplicacion = 0
    variantes_origen_tocadas: Set[int] = set()
    variantes_huerfanas_eliminadas = 0

    if apply_changes:
        now_iso = datetime.now(timezone.utc).isoformat()
        logger.info("Aplicando reparaciones verificadas en Supabase...")

        # Paso 5.1: Pre-crear en lote cualquier `variantes_perfume` destino faltante
        pendientes_var: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
        for item in plan_acciones:
            if item["clasificacion"] != "corregible_verificado":
                continue
            pid = item["perfume_id"]
            vol_n = int(item["vol_nuevo"])
            fmt = item["formato"]
            v_key = (pid, vol_n, fmt)
            if v_key not in variante_lookup and v_key not in pendientes_var:
                perf = perfumes_by_id.get(pid, {})
                conc = perf.get("tipo") or "Eau de Parfum"
                slug_base = f"p-{pid}-{vol_n}ml" if fmt == "regular" else f"p-{pid}-{vol_n}ml-{fmt}"
                pendientes_var[v_key] = {
                    "perfume_id": pid,
                    "concentracion": conc,
                    "volumen_ml": vol_n,
                    "formato": fmt,
                    "slug": slug_base,
                    "activa": True,
                }

        if pendientes_var:
            lista_nuevas = list(pendientes_var.values())
            logger.info(f"Creando {len(lista_nuevas)} variantes destino nuevas en `variantes_perfume`...")
            for i in range(0, len(lista_nuevas), 200):
                lote_v = lista_nuevas[i : i + 200]
                try:
                    ins_b = sb.table("variantes_perfume").insert(lote_v).execute()
                    for vr in ins_b.data or []:
                        vk = (int(vr["perfume_id"]), int(round(float(vr["volumen_ml"]))), str(vr.get("formato") or "regular").lower())
                        variante_lookup[vk] = vr
                except Exception:
                    for row_v in lote_v:
                        vk = (int(row_v["perfume_id"]), int(row_v["volumen_ml"]), str(row_v["formato"]).lower())
                        try:
                            ins_1 = sb.table("variantes_perfume").insert(row_v).execute()
                            if ins_1.data:
                                variante_lookup[vk] = ins_1.data[0]
                        except Exception:
                            q_ex = (
                                sb.table("variantes_perfume")
                                .select("id, perfume_id, concentracion, volumen_ml, formato, slug")
                                .eq("perfume_id", row_v["perfume_id"])
                                .eq("volumen_ml", row_v["volumen_ml"])
                                .eq("formato", row_v["formato"])
                                .limit(1)
                                .execute()
                            )
                            if q_ex.data:
                                variante_lookup[vk] = q_ex.data[0]
                            else:
                                row_v2 = dict(row_v, slug=f"{row_v['slug']}-u{int(datetime.now().timestamp())}")
                                ins_2 = sb.table("variantes_perfume").insert(row_v2).execute()
                                variante_lookup[vk] = ins_2.data[0]

        # Paso 5.2: Ejecutar mutaciones agrupadas por (perfume_id, tienda_id) con clientes thread-local
        from supabase import create_client

        creds = _obtener_mapa_credenciales()
        sb_url = creds["SUPABASE_URL"]
        sb_key = creds.get("SUPABASE_SERVICE_ROLE_KEY") or creds["SUPABASE_KEY"]
        tls = threading.local()

        def _get_thread_sb():
            cli = getattr(tls, "sb", None)
            if cli is None:
                cli = create_client(sb_url, sb_key)
                tls.sb = cli
            return cli

        grupos_pt: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
        for item in plan_acciones:
            grupos_pt[(item["perfume_id"], item["tienda_id"])].append(item)

        lock_meta = threading.Lock()

        def _procesar_grupo_pt(items_grupo: List[Dict[str, Any]]) -> int:
            cli = _get_thread_sb()
            err_local = 0
            for item in items_grupo:
                oid = item["oferta_id"]
                clasif = item["clasificacion"]
                old_vid = item["variante_id_anterior"]
                tid = item["tienda_id"]
                url_p = item["url_producto"]

                try:
                    if clasif == "coherente_multivariante":
                        item["accion_aplicada"] = "mantenida_multivariante"
                        continue

                    if clasif == "corregible_verificado":
                        v_dest = variante_lookup[(item["perfume_id"], int(item["vol_nuevo"]), item["formato"])]
                        dest_vid = int(v_dest["id"])
                        if dest_vid == old_vid:
                            item["accion_aplicada"] = "ya_en_variante_destino"
                            continue

                        with lock_meta:
                            variantes_origen_tocadas.add(old_vid)
                            existente_dest = oferta_por_var_tienda.get((dest_vid, tid))

                        p_vivo = int(item["precio_vivo"])
                        p_norm_vivo = int(item["precio_normal_vivo"] or p_vivo)
                        st_vivo = bool(item["en_stock_vivo"])

                        cli.table("precios_registro").update({"variante_id": dest_vid}).eq(
                            "variante_id", old_vid
                        ).eq("tienda_id", tid).eq("url_producto", url_p).execute()

                        if existente_dest and int(existente_dest["id"]) != oid:
                            if st_vivo or not existente_dest.get("en_stock"):
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
                            cli.table("ofertas_actuales").delete().eq("id", oid).execute()
                            with lock_meta:
                                oferta_por_var_tienda.pop((old_vid, tid), None)
                            item["accion_aplicada"] = f"fusionada_en_oferta_{existente_dest['id']}_var_{dest_vid}"
                        else:
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
                            with lock_meta:
                                oferta_por_var_tienda.pop((old_vid, tid), None)
                                oferta_por_var_tienda[(dest_vid, tid)] = {"id": oid, "en_stock": st_vivo}
                            item["accion_aplicada"] = f"movida_a_variante_{dest_vid}"

                    elif clasif == "miniatura_retirada":
                        with lock_meta:
                            variantes_origen_tocadas.add(old_vid)
                        cli.table("ofertas_actuales").update({
                            "en_stock": False,
                            "estado": "retirada",
                            "ultimo_error": f"reparar_volumenes: {item['submotivo']}",
                            "updated_at": now_iso,
                        }).eq("id", oid).execute()
                        item["accion_aplicada"] = "retirada_miniatura"

                    elif clasif == "no_verificable":
                        payload_nv: Dict[str, Any] = {
                            "estado": "requiere_revision",
                            "ultimo_error": f"reparar_volumenes: {item['submotivo']}",
                            "updated_at": now_iso,
                        }
                        if item["es_404"]:
                            payload_nv["en_stock"] = False
                        cli.table("ofertas_actuales").update(payload_nv).eq("id", oid).execute()
                        item["accion_aplicada"] = "marcada_requiere_revision_404" if item["es_404"] else "marcada_requiere_revision"

                except Exception as exc:
                    err_local += 1
                    item["accion_aplicada"] = f"ERROR: {exc}"
                    logger.error(f"Error aplicando acción sobre oferta #{oid}: {exc}")
            return err_local

        with ThreadPoolExecutor(max_workers=6) as pool:
            for e_cnt in pool.map(_procesar_grupo_pt, grupos_pt.values()):
                errores_aplicacion += e_cnt

        # Paso 5.3: Eliminar en lotes variantes antiguas que quedaron 100% huérfanas (0 ofertas y 0 precios_registro)
        cand_vids = sorted(variantes_origen_tocadas)
        vids_con_uso: Set[int] = set()
        for i in range(0, len(cand_vids), 150):
            chunk_v = cand_vids[i : i + 150]
            r_of = sb.table("ofertas_actuales").select("variante_id").in_("variante_id", chunk_v).execute().data or []
            for r in r_of:
                vids_con_uso.add(int(r["variante_id"]))
            rem_check = [vid for vid in chunk_v if vid not in vids_con_uso]
            if rem_check:
                r_pr = sb.table("precios_registro").select("variante_id").in_("variante_id", rem_check).limit(1000).execute().data or []
                for r in r_pr:
                    vids_con_uso.add(int(r["variante_id"]))

        vids_huerfanas = [vid for vid in cand_vids if vid not in vids_con_uso]
        for wid in vids_huerfanas:
            try:
                # Doble verificación individual exacta antes del DELETE (0 filas en ambas tablas)
                c1 = sb.table("ofertas_actuales").select("id", count="exact").eq("variante_id", wid).limit(1).execute()
                if (c1.count or 0) > 0 or c1.data:
                    continue
                c2 = sb.table("precios_registro").select("id", count="exact").eq("variante_id", wid).limit(1).execute()
                if (c2.count or 0) > 0 or c2.data:
                    continue
                sb.table("variantes_perfume").delete().eq("id", wid).execute()
                variantes_huerfanas_eliminadas += 1
            except Exception as exc:
                logger.warning(f"No se eliminó variante #{wid} por restricción activa: {exc}")

        limpiar_cache_catalogo()

    # 6. Guardar registro CSV completo de auditoría
    fieldnames = list(plan_acciones[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(plan_acciones)

    print("\n" + "=" * 78)
    print(f"REPORTE REPARACIÓN DE VOLÚMENES ({'APPLY' if apply_changes else 'DRY-RUN'})")
    print("=" * 78)
    print(f"Candidatos evaluados            : {len(plan_acciones)}")
    for k in ("corregible_verificado", "coherente_multivariante", "miniatura_retirada", "no_verificable"):
        print(f"  - {k:28s}: {resumen_counts[k]}")
    if apply_changes:
        print(f"Variantes huérfanas eliminadas  : {variantes_huerfanas_eliminadas}")
        print(f"Errores de escritura            : {errores_aplicacion}")
    print("\nDesglose por tienda:")
    for t_nom in sorted(por_tienda_counts.keys()):
        c = por_tienda_counts[t_nom]
        print(
            f"  {t_nom:20s} | corregibles={c['corregible_verificado']:4d} | "
            f"multivar_ok={c['coherente_multivariante']:4d} | "
            f"mini={c['miniatura_retirada']:3d} | no_verif={c['no_verificable']:4d}"
        )
    print(f"\nCSV de auditoría guardado en: {csv_path}")
    print("=" * 78)

    return {
        "total_candidatos": len(plan_acciones),
        "resumen": dict(resumen_counts),
        "errores_aplicacion": errores_aplicacion,
        "variantes_huerfanas_eliminadas": variantes_huerfanas_eliminadas,
        "csv_path": str(csv_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reparación verificada de incoherencias URL <-> volumen_ml.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo simula y genera CSV sin escribir en BD (por defecto).")
    grp.add_argument("--apply", action="store_true", help="Aplica en Supabase las correcciones verificadas.")
    parser.add_argument("--store", type=str, default=None, help="Filtrar por nombre de tienda (ej. 'Mundo Aromas').")
    args = parser.parse_args()

    ejecutar_reparacion_volumenes(apply_changes=bool(args.apply), store_filter=args.store)


if __name__ == "__main__":
    main()
