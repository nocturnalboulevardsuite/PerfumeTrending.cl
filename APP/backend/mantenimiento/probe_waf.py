# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Experimento Diagnóstico de WAF Retail (Fase 2)
===================================================================
Prueba 30 URLs reales por tienda Retail (`Paris`, `Ripley`, `Falabella`) desde
el entorno de ejecución (ej. GitHub Actions `ubuntu-latest`) comparando:
  - `requests` estándar con headers de navegador `es-CL`
  - `curl_cffi(impersonate="chrome120")` (TLS/JA3 + HTTP/2 fingerprint real)

Mide distribución de códigos HTTP (200, 403, 429, 404, errores), extracción real
de ficha de producto (`__NEXT_DATA__` / JSON-LD `Product`) y latencia promedio,
escribiendo tabla Markdown en `$GITHUB_STEP_SUMMARY` y JSON en
`APP/data/reportes/probe_waf.json`.
"""

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (Counter) desde el módulo 'collections'
from collections import Counter
# Importación de componentes (ThreadPoolExecutor, as_completed) desde el módulo 'concurrent.futures'
from concurrent.futures import ThreadPoolExecutor, as_completed
# Importación de componentes (datetime, timezone) desde el módulo 'datetime'
from datetime import datetime, timezone
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de librería estándar o dependencia externa (random)
import random
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de componentes (Any, Dict, List) desde el módulo 'typing'
from typing import Any, Dict, List

# Importación de componentes (BeautifulSoup) desde el módulo 'bs4'
from bs4 import BeautifulSoup
# Importación de librería estándar o dependencia externa (requests)
import requests

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (requests) desde el módulo 'curl_cffi'
    from curl_cffi import requests as curl_requests
except ImportError:
    # Asignamos 'curl_requests' con None
    curl_requests = None

# Asignamos 'REPO_ROOT' con Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
# Asignamos 'APP_DIR' con REPO_ROOT / 'APP'
APP_DIR = REPO_ROOT / "APP"
# Recorremos iterativamente cada '_p' en (str(APP_DIR), str(REPO_ROOT))
for _p in (str(APP_DIR), str(REPO_ROOT)):
    # Evaluamos la condición lógica (_p not in sys.path) para controlar el flujo
    if _p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)

# Importación de componentes (get_supabase) desde el módulo 'backend.database'
from backend.database import get_supabase
# Importación de componentes (clean_digits, crear_sesion_robusta, obtener_headers_navegador) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import clean_digits, crear_sesion_robusta, obtener_headers_navegador

# Asignamos 'TIENDAS_OBJETIVO' con ('Paris', 'Ripley', 'Falabella')
TIENDAS_OBJETIVO = ("Paris", "Ripley", "Falabella")


# - ¿Qué hace esta función?:
#   Verifica si un HTML HTTP 200 contiene realmente metadatos estructurados de producto
#   (`__NEXT_DATA__` o Schema.org `Product` con precio > 0) y no una página challenge o vacía.
def tiene_payload_producto_valido(tienda: str, html_text: str) -> bool:
    # Evaluamos la condición lógica (not html_text or len(html_text) < 500) para controlar el flujo
    if not html_text or len(html_text) < 500:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'low' con html_text.lower()
    low = html_text.lower()
    # Evaluamos la condición lógica ('just a moment...' in low or 'cf-chl-bypass' in low ...) para controlar el flujo
    if "just a moment..." in low or "cf-chl-bypass" in low or "attention required! | cloudflare" in low:
        # Retornamos el resultado procesado (False)
        return False

    # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
    tag_next = soup.find("script", id="__NEXT_DATA__")
    # Evaluamos la condición lógica (tag_next and (tag_next.string or tag_next.text)) para controlar el flujo
    if tag_next and (tag_next.string or tag_next.text):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Procesamiento de serialización o deserialización de estructura JSON
            data = json.loads(tag_next.string or tag_next.text)
            # Procesamiento de serialización o deserialización de estructura JSON
            txt = json.dumps(data)
            # Evaluamos la condición lógica ('price' in txt.lower() and ('product' in txt.lower()...) para controlar el flujo
            if "price" in txt.lower() and ("product" in txt.lower() or "variants" in txt.lower()):
                # Retornamos el resultado procesado (True)
                return True
        except Exception:
            # Ejecutamos instrucción: pass
            pass

    # Recorremos iterativamente cada 's_tag' en soup.find_all('script', type='application/...
    for s_tag in soup.find_all("script", type="application/ld+json"):
        # Asignamos 'raw' con s_tag.string or s_tag.get_text() or ''
        raw = s_tag.string or s_tag.get_text() or ""
        # Evaluamos la condición lógica ('Product' in raw and 'price' in raw) para controlar el flujo
        if "Product" in raw and "price" in raw:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Procesamiento de serialización o deserialización de estructura JSON
                d = json.loads(raw)
                # Procesamiento de serialización o deserialización de estructura JSON
                txt = json.dumps(d)
                # Evaluamos la condición lógica (clean_digits(txt) > 0) para controlar el flujo
                if clean_digits(txt) > 0:
                    # Retornamos el resultado procesado (True)
                    return True
            except Exception:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
    # Retornamos el resultado procesado (False)
    return False


# - ¿Qué hace esta función?:
#   Obtiene hasta `sample_size` URLs distintas reales por tienda retail desde `ofertas_actuales`.
def obtener_urls_muestra(sample_size: int = 30) -> Dict[str, List[str]]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("Supabase no disponible para obtener muestra de URLs retail.")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    tiendas = sb.table("tiendas").select("id, nombre").execute().data or []
    # Asignamos 'mapa_tiendas' con {t['nombre']: int(t['id']) for t in tienda...
    mapa_tiendas = {t["nombre"]: int(t["id"]) for t in tiendas if t["nombre"] in TIENDAS_OBJETIVO}

    # Asignamos 'resultado' con {}
    resultado: Dict[str, List[str]] = {}
    # Recorremos iterativamente cada 't_nom' en TIENDAS_OBJETIVO
    for t_nom in TIENDAS_OBJETIVO:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        tid = mapa_tiendas.get(t_nom)
        # Evaluamos la condición lógica (not tid) para controlar el flujo
        if not tid:
            # Asignamos 'resultado[t_nom]' con []
            resultado[t_nom] = []
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        rows = (
            sb.table("ofertas_actuales")
            .select("url_producto, estado, en_stock")
            .eq("tienda_id", tid)
            .eq("estado", "activa")
            .limit(250)
            .execute()
            .data
            or []
        )
        # Asignamos 'urls_unicas' con []
        urls_unicas: List[str] = []
        # Asignamos 'vistas' con set()
        vistas = set()
        # Recorremos iterativamente cada 'r' en rows
        for r in rows:
            # Asignamos 'u' con str(r.get('url_producto') or '').strip()
            u = str(r.get("url_producto") or "").strip()
            # Evaluamos la condición lógica (u.startswith('http') and u not in vistas) para controlar el flujo
            if u.startswith("http") and u not in vistas:
                # Ejecutamos instrucción: vistas.add(u)
                vistas.add(u)
                # Ejecutamos instrucción: urls_unicas.append(u)
                urls_unicas.append(u)
        # Ejecutamos instrucción: random.Random(42).shuffle(urls_unicas)
        random.Random(42).shuffle(urls_unicas)
        # Asignamos 'resultado[t_nom]' con urls_unicas[:sample_size]
        resultado[t_nom] = urls_unicas[:sample_size]
    # Retornamos el resultado procesado (resultado)
    return resultado


# - ¿Qué hace esta función?:
#   Ejecuta la batería secuencial con jitter para una tienda dada bajo ambos clientes HTTP
#   (`requests` y `curl_cffi(chrome120)`), evitando ráfagas artificiales contra un mismo dominio.
def evaluar_tienda(tienda: str, urls: List[str]) -> List[Dict[str, Any]]:
    # Asignamos 'referer_map' con {'Paris': 'https://www.paris.cl/', 'Ripley...
    referer_map = {
        "Paris": "https://www.paris.cl/",
        "Ripley": "https://simple.ripley.cl/",
        "Falabella": "https://www.falabella.com/falabella-cl",
    }
    # Asignamos 'referer' con referer_map.get(tienda, 'https://www.googl...
    referer = referer_map.get(tienda, "https://www.google.cl/")
    # Asignamos 'resultados_tienda' con []
    resultados_tienda: List[Dict[str, Any]] = []

    # Asignamos 'clientes' con ['requests', 'curl_cffi_chrome120']
    clientes = ["requests", "curl_cffi_chrome120"]
    # Recorremos iterativamente cada 'cliente' en clientes
    for cliente in clientes:
        # Evaluamos la condición lógica (cliente == 'requests') para controlar el flujo
        if cliente == "requests":
            # Asignamos 'sess' con crear_sesion_robusta()
            sess = crear_sesion_robusta()
        else:
            # Evaluamos la condición lógica (curl_requests is None) para controlar el flujo
            if curl_requests is None:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'sess' con curl_requests.Session(impersonate='chrome1...
            sess = curl_requests.Session(impersonate="chrome120")

        # Asignamos 'codigos' con Counter()
        codigos = Counter()
        # Asignamos 'con_precio_valido' con 0
        con_precio_valido = 0
        # Asignamos 'latencias_ms' con []
        latencias_ms: List[float] = []

        # Recorremos iterativamente cada 'u' en urls
        for u in urls:
            # Asignamos 'headers' con obtener_headers_navegador(referer=referer)
            headers = obtener_headers_navegador(referer=referer)
            # Asignamos 't0' con time.perf_counter()
            t0 = time.perf_counter()
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                resp = sess.get(u, headers=headers, timeout=14, allow_redirects=True)
                # Asignamos 'dt_ms' con (time.perf_counter() - t0) * 1000.0
                dt_ms = (time.perf_counter() - t0) * 1000.0
                # Ejecutamos instrucción: latencias_ms.append(dt_ms)
                latencias_ms.append(dt_ms)
                # Asignamos 'code' con int(resp.status_code)
                code = int(resp.status_code)
                # Actualizamos acumulativamente el valor de 'codigos[str(code)]'
                codigos[str(code)] += 1
                # Evaluamos la condición lógica (code == 200 and tiene_payload_producto_valido(tienda...) para controlar el flujo
                if code == 200 and tiene_payload_producto_valido(tienda, resp.text or ""):
                    # Actualizamos acumulativamente el valor de 'con_precio_valido'
                    con_precio_valido += 1
            except Exception as exc:
                # Asignamos 'dt_ms' con (time.perf_counter() - t0) * 1000.0
                dt_ms = (time.perf_counter() - t0) * 1000.0
                # Ejecutamos instrucción: latencias_ms.append(dt_ms)
                latencias_ms.append(dt_ms)
                # Actualizamos acumulativamente el valor de 'codigos[f'ERR:{type(exc).__name_...'
                codigos[f"ERR:{type(exc).__name__}"] += 1

            # Ejecutamos instrucción: time.sleep(random.uniform(0.45, 1.05))
            time.sleep(random.uniform(0.45, 1.05))

        # Asignamos 'n_total' con max(1, len(urls))
        n_total = max(1, len(urls))
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        http_200 = codigos.get("200", 0)
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        waf_blocks = codigos.get("403", 0) + codigos.get("429", 0)
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        http_404 = codigos.get("404", 0)
        # Asignamos 'otros' con sum((v for k, v in codigos.items() if k no...
        otros = sum(v for k, v in codigos.items() if k not in ("200", "403", "429", "404"))
        # Asignamos 'lat_prom' con round(sum(latencias_ms) / max(1, len(laten...
        lat_prom = round(sum(latencias_ms) / max(1, len(latencias_ms)), 1)

        # Ejecutamos instrucción: resultados_tienda.append({'tienda': tienda, 'cliente...
        resultados_tienda.append({
            "tienda": tienda,
            "cliente": cliente,
            "urls_probadas": len(urls),
            "http_200": http_200,
            "pct_200": round(http_200 * 100.0 / n_total, 1),
            "payload_valido": con_precio_valido,
            "pct_payload_valido": round(con_precio_valido * 100.0 / n_total, 1),
            "waf_403_429": waf_blocks,
            "pct_waf": round(waf_blocks * 100.0 / n_total, 1),
            "http_404": http_404,
            "otros_errores": otros,
            "latencia_media_ms": lat_prom,
            "codigos_detalle": dict(codigos),
        })

    # Retornamos el resultado procesado (resultados_tienda)
    return resultados_tienda


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Sonda diagnóstica WAF para Paris, Ripley y Falabella.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--sample", type=int, default=30, help="Cantidad de URLs por tienda (default: 30).")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Asignamos 'muestra' con obtener_urls_muestra(sample_size=args.sample)
    muestra = obtener_urls_muestra(sample_size=args.sample)
    # Asignamos 'filas_resumen' con []
    filas_resumen: List[Dict[str, Any]] = []

    # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=3)
    with ThreadPoolExecutor(max_workers=3) as pool:
        # Asignamos 'futs' con {pool.submit(evaluar_tienda, t_nom, urls):...
        futs = {pool.submit(evaluar_tienda, t_nom, urls): t_nom for t_nom, urls in muestra.items() if urls}
        # Recorremos iterativamente cada 'fut' en as_completed(futs)
        for fut in as_completed(futs):
            # Ejecutamos instrucción: filas_resumen.extend(fut.result())
            filas_resumen.extend(fut.result())

    # Asignamos 'orden_tiendas' con {t: i for i, t in enumerate(TIENDAS_OBJETI...
    orden_tiendas = {t: i for i, t in enumerate(TIENDAS_OBJETIVO)}
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    filas_resumen.sort(key=lambda r: (orden_tiendas.get(r["tienda"], 99), r["cliente"]))

    # Asignamos 'md_lines' con ['## Experimento Diagnóstico WAF Retail (`...
    md_lines = [
        "## Experimento Diagnóstico WAF Retail (`requests` vs `curl_cffi chrome120`)",
        "",
        f"- **Fecha UTC:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"- **Muestra por tienda:** `{args.sample}` URLs activas reales",
        "",
        "| Tienda | Cliente HTTP | URLs | HTTP 200 | Payload Producto Válido | WAF (403/429) | HTTP 404 | Otros/Timeout | Latencia Media |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    # Recorremos iterativamente cada 'r' en filas_resumen
    for r in filas_resumen:
        # Ejecutamos instrucción: md_lines.append(f"| {r['tienda']} | `{r['cliente']}`...
        md_lines.append(
            f"| {r['tienda']} | `{r['cliente']}` | {r['urls_probadas']} | "
            f"{r['http_200']} ({r['pct_200']}%) | **{r['payload_valido']} ({r['pct_payload_valido']}%)** | "
            f"{r['waf_403_429']} ({r['pct_waf']}%) | {r['http_404']} | {r['otros_errores']} | {r['latencia_media_ms']} ms |"
        )
    # Asignamos 'md_text' con '\n'.join(md_lines) + '\n'
    md_text = "\n".join(md_lines) + "\n"
    # Ejecutamos instrucción: print('\n' + md_text)
    print("\n" + md_text)

    # Asignamos 'summary_env' con os.environ.get('GITHUB_STEP_SUMMARY')
    summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
    # Evaluamos la condición lógica (summary_env) para controlar el flujo
    if summary_env:
        # Gestión automática de contexto y recursos para: open(summary_env, 'a', encoding='utf-8')
        with open(summary_env, "a", encoding="utf-8") as sf:
            # Ejecutamos instrucción: sf.write(md_text)
            sf.write(md_text)

    # Asignamos 'reportes_dir' con APP_DIR / 'data' / 'reportes'
    reportes_dir = APP_DIR / "data" / "reportes"
    # Ejecutamos instrucción: reportes_dir.mkdir(parents=True, exist_ok=True)
    reportes_dir.mkdir(parents=True, exist_ok=True)
    # Asignamos 'out_json' con reportes_dir / 'probe_waf.json'
    out_json = reportes_dir / "probe_waf.json"
    # Procesamiento de serialización o deserialización de estructura JSON
    out_json.write_text(
        json.dumps(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "sample_per_store": args.sample,
                "resultados": filas_resumen,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    # Ejecutamos instrucción: print(f'Reporte JSON guardado en: {out_json}')
    print(f"Reporte JSON guardado en: {out_json}")


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()
