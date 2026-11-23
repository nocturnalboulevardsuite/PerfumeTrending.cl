# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Auditoría Continua de Enlaces con Histéresis de 2 Strikes (Fase 6)
=======================================================================================
Muestrea aleatoriamente hasta `sample_size` enlaces activos (`en_stock=True, estado='activa'`),
los verifica con `curl_cffi(impersonate="chrome120")` y aplica reglas estrictas
anti-falsos positivos:
  1. Histéresis de 2 strikes:
     - 1ª detección de 404 / soft-404 / redirect-home -> anota `[AUDIT_STRIKE_1]` en
       `ultimo_error` SIN desactivar la oferta.
     - 2ª detección consecutiva -> desactiva (`en_stock=False, estado='requiere_revision'`).
     - Si una oferta con `[AUDIT_STRIKE_1]` vuelve a responder `200 OK` -> limpia el strike.
  2. Inmunidad ante bloqueos o fallos transitorios:
     - Jamás desactiva ni penaliza por `403`, `429`, `5xx` ni `timeout`.
  3. Trazabilidad:
     - Registra la corrida en `scraping_runs` / `scraping_logs`, guarda JSON en
       `APP/data/reportes/ultima_auditoria_enlaces.json` y escribe tabla Markdown en
       `$GITHUB_STEP_SUMMARY`.
"""

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (defaultdict) desde el módulo 'collections'
from collections import defaultdict
# Importación de componentes (ThreadPoolExecutor, as_completed) desde el módulo 'concurrent.futures'
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# Importación de librería estándar o dependencia externa (random)
import random
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de componentes (Any, Dict, List, Optional) desde el módulo 'typing'
from typing import Any, Dict, List, Optional
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (requests) desde el módulo 'curl_cffi'
    from curl_cffi import requests as curl_requests
except ImportError:
    # Asignamos 'curl_requests' con None
    curl_requests = None

# Importación de librería estándar o dependencia externa (requests)
import requests

# Asignamos 'REPO_ROOT' con Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
# Asignamos 'APP_DIR' con REPO_ROOT / 'APP'
APP_DIR = REPO_ROOT / "APP"
# Recorremos iterativamente cada '_p' en (str(APP_DIR), str(REPO_ROOT))
for _p in (str(APP_DIR), str(REPO_ROOT)):
    # Evaluamos la condición lógica (_p not in sys.path) para controlar el flujo
    if _p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)

# Importación de componentes (finalizar_scraping_run, get_supabase, iniciar_scraping_run, limpiar_cache_catalogo) desde el módulo 'backend.database'
from backend.database import (
    finalizar_scraping_run,
    get_supabase,
    iniciar_scraping_run,
    limpiar_cache_catalogo,
)

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Asignamos 'logger' con logging.getLogger('AuditoriaEnlaces')
logger = logging.getLogger("AuditoriaEnlaces")

# Asignamos 'STRIKE_1_TAG' con '[AUDIT_STRIKE_1]'
STRIKE_1_TAG = "[AUDIT_STRIKE_1]"
# Asignamos 'STRIKE_2_TAG' con '[AUDIT_STRIKE_2]'
STRIKE_2_TAG = "[AUDIT_STRIKE_2]"


# - ¿Qué hace esta función?:
#   Evalúa si la URL final tras redirecciones cayó en la portada o catálogo raíz
#   de la tienda en vez de una ficha de producto (soft-404 por redirección al home).
def es_redireccion_al_home(url_original: str, url_final: str) -> bool:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Extraemos únicamente el path limpio (sin dominio ni barras laterales) de la URL original y la final
        orig_p = urllib.parse.urlparse(url_original).path.strip("/").lower()
        # Asignamos 'fin_p' con urllib.parse.urlparse(url_final).path.stri...
        fin_p = urllib.parse.urlparse(url_final).path.strip("/").lower()
    except Exception:
        # Si alguna URL tiene formato malformado, no la clasificamos como redirección al home
        return False
    # Si la URL original ya era una ruta muy corta (<= 4 caracteres), no hay redirección anómala
    if len(orig_p) <= 4:
        # Retornamos el resultado procesado (False)
        return False
    # Conjunto de rutas raíz conocidas donde las tiendas redirigen cuando un producto fue eliminado
    rutas_home = {"", "falabella-cl", "collections", "collections/all", "tienda", "shop"}
    # Retornamos el resultado procesado (fin_p in rutas_home)
    return fin_p in rutas_home


# - ¿Qué hace esta función?:
#   Clasifica la respuesta HTTP de un enlace de oferta en `OK_200`, `DEAD_404`,
#   `SOFT_404`, `REDIRECT_HOME`, `WAF_403`, `RATE_LIMIT_429`, `TIMEOUT` o `SERVER_ERR_*`.
def clasificar_respuesta_http(url_original: str, status_code: int, url_final: str, body_text: str) -> tuple[str, str]:
    # Caso 1: El servidor respondió HTTP 200 OK; verificamos que no sea un "Soft-404" disfrazado
    if status_code == 200:
        # Asignamos 'low_u' con (url_final or '').lower()
        low_u = (url_final or "").lower()
        # Analizamos los primeros 40.000 caracteres del HTML en minúsculas para inspección rápida
        low_t = (body_text or "")[:40000].lower()
        # Si la URL final termina o contiene '/404', es una página de no encontrado con código 200
        if "/404" in low_u or low_u.endswith("404"):
            # Retornamos el resultado procesado (('SOFT_404', 'Redirigió a ruta /404'))
            return "SOFT_404", "Redirigió a ruta /404"
        # Si redirigió silenciosamente a la portada general de la tienda
        if es_redireccion_al_home(url_original, url_final):
            # Retornamos el resultado procesado (('REDIRECT_HOME', 'Redirigió al home de la tien...)
            return "REDIRECT_HOME", "Redirigió al home de la tienda (producto dado de baja)"
        # Frases típicas de producto inexistente cuando el e-commerce no devuelve código 404 real
        patrones_404 = (
            "página no encontrada",
            "pagina no encontrada",
            "lo sentimos, no pudimos encontrar",
            "esta página no existe",
            "page not found",
        )
        # Si aparece un mensaje de página no encontrada y no hay metadatos Schema.org de tipo Product
        if any(p in low_t for p in patrones_404) and '"@type":"product"' not in low_t.replace(" ", ""):
            # Retornamos el resultado procesado (('SOFT_404', 'Página muestra mensaje de no enco...)
            return "SOFT_404", "Página muestra mensaje de no encontrada sin schema Product"
        # El enlace está vivo y corresponde a una ficha válida
        return "OK_200", "Navegación exitosa 200 OK"
    # Caso 2: Error HTTP 404 (Not Found) o 410 (Gone) definitivo
    if status_code == 404 or status_code == 410:
        # Retornamos el resultado procesado (('DEAD_404', f'HTTP {status_code}'))
        return "DEAD_404", f"HTTP {status_code}"
    # Caso 3: Bloqueo de firewall perimetral WAF / Cloudflare (no es culpa del enlace)
    if status_code == 403:
        # Retornamos el resultado procesado (('WAF_403', 'Cloudflare/WAF anti-bot 403'))
        return "WAF_403", "Cloudflare/WAF anti-bot 403"
    # Caso 4: Límite de tasa de peticiones alcanzado temporalmente
    if status_code == 429:
        # Retornamos el resultado procesado (('RATE_LIMIT_429', 'Rate limit HTTP 429'))
        return "RATE_LIMIT_429", "Rate limit HTTP 429"
    # Caso 5: Caída o mantenimiento temporal del servidor de la tienda (5xx)
    if status_code in (500, 502, 503, 504):
        # Retornamos el resultado procesado ((f'SERVER_ERR_{status_code}', f'Error servidor ...)
        return f"SERVER_ERR_{status_code}", f"Error servidor tienda {status_code}"
    # Cualquier otro código HTTP no contemplado explícitamente
    return f"HTTP_{status_code}", f"Código HTTP {status_code}"


# - ¿Qué hace esta función?:
#   Aplica la máquina de estados de histéresis de 2 strikes a partir del `status_type`
#   observado y el valor previo de `ultimo_error` en la oferta.
def decidir_accion_histeresis(status_type: str, motivo: str, ultimo_error_previo: Optional[str]) -> Dict[str, Any]:
    # Normalizamos el texto del error previo almacenado en la base de datos
    prev = str(ultimo_error_previo or "")
    # Verificamos si esta oferta ya tenía una primera advertencia ([AUDIT_STRIKE_1]) de la corrida anterior
    tenia_strike_1 = STRIKE_1_TAG in prev

    # Si el enlace respondió 200 OK, se limpia cualquier strike previo o se mantiene intacto
    if status_type == "OK_200":
        # Evaluamos la condición lógica (tenia_strike_1) para controlar el flujo
        if tenia_strike_1:
            # Retornamos el resultado procesado ({'accion': 'limpiar_strike', 'payload': {'ultim...)
            return {"accion": "limpiar_strike", "payload": {"ultimo_error": None}}
        # Retornamos el resultado procesado ({'accion': 'ninguna', 'payload': {}})
        return {"accion": "ninguna", "payload": {}}

    # Si el enlace está caído (404, Soft-404, redirección al home o URL inválida)
    if status_type in ("DEAD_404", "SOFT_404", "REDIRECT_HOME", "INVALID_URL"):
        # Si ya tenía Strike 1 previo -> pasa a Strike 2 y se desactiva la oferta en base de datos
        if tenia_strike_1:
            # Retornamos el resultado procesado ({'accion': 'desactivar_strike_2', 'payload': {'...)
            return {
                "accion": "desactivar_strike_2",
                "payload": {
                    "en_stock": False,
                    "estado": "requiere_revision",
                    "ultimo_error": f"{STRIKE_2_TAG} {status_type}: {motivo}"[:240],
                },
            }
        # Si es su primer fallo detectado -> se anota Strike 1 como advertencia sin apagar la oferta
        return {
            "accion": "marcar_strike_1",
            "payload": {
                "ultimo_error": f"{STRIKE_1_TAG} {status_type}: {motivo}"[:240],
            },
        }

    # WAF 403, 429, 5xx o timeout: inmunidad total (no se altera la oferta ni se suma strike)
    return {"accion": "ignorar_transitorio", "payload": {}}


# - ¿Qué hace esta función principal?:
#   Ejecuta la auditoría completa sobre una muestra estratificada/aleatoria de ofertas
#   activas, aplica la histéresis en Supabase (salvo `--dry-run`) y persiste reportes.
def ejecutar_auditoria_enlaces(
    sample_size: int = 1000,
    workers: int = 20,
    dry_run: bool = False,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    # Obtenemos la instancia singleton del cliente Supabase con privilegios service_role
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("Supabase no disponible para ejecutar auditoría de enlaces.")

    # Registramos el inicio formal de la corrida en scraping_runs (solo si no estamos en modo simulación --dry-run)
    run_id = None if dry_run else iniciar_scraping_run(
        tipo_scraper="Auditoría Continua de Enlaces (Histéresis 2-Strike)",
        mensaje_detalle=f"Muestra objetivo: {sample_size} enlaces activos",
    )

    # Cargamos el diccionario de tiendas {tienda_id: nombre_tienda} para etiquetar los reportes
    tiendas_raw = sb.table("tiendas").select("id, nombre").execute().data or []
    # Asignamos 'tiendas_map' con {int(t['id']): t['nombre'] for t in tienda...
    tiendas_map = {int(t["id"]): t["nombre"] for t in tiendas_raw}

    # Descargamos por bloques paginados de 1.000 filas todas las ofertas activas y con stock
    pool_ofertas: List[Dict[str, Any]] = []
    # Asignamos 'offset' con 0
    offset = 0
    # Ejecutamos el ciclo mientras se mantenga la condición: True
    while True:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        r = (
            sb.table("ofertas_actuales")
            .select(
                "id, variante_id, tienda_id, precio_actual, en_stock, url_producto, ultimo_error, "
                "variantes_perfume!inner(volumen_ml, formato, perfumes!inner(id, nombre, marca))"
            )
            .eq("en_stock", True)
            .eq("estado", "activa")
            .order("id", desc=False)
            .range(offset, offset + 999)
            .execute()
        )
        # Asignamos 'batch' con r.data or []
        batch = r.data or []
        # Evaluamos la condición lógica (not batch) para controlar el flujo
        if not batch:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Ejecutamos instrucción: pool_ofertas.extend(batch)
        pool_ofertas.extend(batch)
        # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
        if len(batch) < 1000:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Actualizamos acumulativamente el valor de 'offset'
        offset += 1000

    # Priorizar re-verificación de ofertas que ya tengan [AUDIT_STRIKE_1] + muestra aleatoria del resto
    con_strike_prev = [o for o in pool_ofertas if STRIKE_1_TAG in str(o.get("ultimo_error") or "")]
    # Asignamos 'sin_strike_prev' con [o for o in pool_ofertas if STRIKE_1_TAG n...
    sin_strike_prev = [o for o in pool_ofertas if STRIKE_1_TAG not in str(o.get("ultimo_error") or "")]
    # Mezclamos aleatoriamente el resto de ofertas sin strike para muestreo uniforme
    random.shuffle(sin_strike_prev)
    # Asignamos 'cupo_restante' con max(0, sample_size - len(con_strike_prev))
    cupo_restante = max(0, sample_size - len(con_strike_prev))
    # Asignamos 'sample' con (con_strike_prev[:sample_size] + sin_strik...
    sample = (con_strike_prev[:sample_size] + sin_strike_prev[:cupo_restante])[:sample_size]

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(
        f"Pool activo total: {len(pool_ofertas)} | Muestra seleccionada: {len(sample)} "
        f"(con Strike 1 previo: {min(len(con_strike_prev), sample_size)})"
    )

    # Cabeceras estándar de navegación web en español de Chile
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    # Función worker interna que verifica un enlace individual en un hilo del ThreadPoolExecutor
    def _check_one(item: Dict[str, Any]) -> Dict[str, Any]:
        # Asignamos 'oid' con int(item['id'])
        oid = int(item["id"])
        # Asignamos 'url' con str(item.get('url_producto') or '').strip()
        url = str(item.get("url_producto") or "").strip()
        # Asignamos 'tid' con int(item.get('tienda_id') or 0)
        tid = int(item.get("tienda_id") or 0)
        # Asignamos 'tname' con tiendas_map.get(tid, f'Tienda {tid}')
        tname = tiendas_map.get(tid, f"Tienda {tid}")
        # Asignamos 'var_d' con item.get('variantes_perfume') or {}
        var_d = item.get("variantes_perfume") or {}
        # Asignamos 'perf_d' con var_d.get('perfumes') or {}
        perf_d = var_d.get("perfumes") or {}
        # Asignamos 'label' con f"{perf_d.get('marca', '')} - {perf_d.get(...
        label = f"{perf_d.get('marca', '')} - {perf_d.get('nombre', '')} ({var_d.get('volumen_ml', 0)}ml)"

        # Estructura base del resultado de diagnóstico para esta oferta
        out = {
            "id": oid,
            "tienda": tname,
            "perfume": label,
            "precio": int(item.get("precio_actual") or 0),
            "url": url,
            "status_code": 0,
            "status_type": "UNKNOWN",
            "motivo": "",
            "final_url": "",
            "ultimo_error_previo": item.get("ultimo_error"),
        }
        # Si la URL no comienza con http/https, se marca inmediatamente como INVALID_URL
        if not url.startswith("http"):
            # Asignamos 'out['status_type']' con 'INVALID_URL'
            out["status_type"] = "INVALID_URL"
            # Asignamos 'out['motivo']' con 'URL vacía o sin protocolo'
            out["motivo"] = "URL vacía o sin protocolo"
            # Retornamos el resultado procesado (out)
            return out

        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Preferimos curl_cffi con impersonación TLS de Chrome 120 para reducir falsos bloqueos WAF
            if curl_requests is not None:
                # Gestión automática de contexto y recursos para: curl_requests.Session(impersonate='chrome120')
                with curl_requests.Session(impersonate="chrome120") as s:
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    resp = s.get(url, headers=headers, timeout=10, allow_redirects=True)
                    # Asignamos 'code' con int(resp.status_code)
                    code = int(resp.status_code)
                    # Asignamos 'fin_u' con str(resp.url)
                    fin_u = str(resp.url)
                    # Asignamos 'txt' con resp.text or ''
                    txt = resp.text or ""
            else:
                # Fallback a requests estándar si curl_cffi no está instalado en el entorno
                resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                # Asignamos 'code' con int(resp.status_code)
                code = int(resp.status_code)
                # Asignamos 'fin_u' con str(resp.url)
                fin_u = str(resp.url)
                # Asignamos 'txt' con resp.text or ''
                txt = resp.text or ""

            # Guardamos código HTTP, URL final tras redirecciones y clasificación semántica
            out["status_code"] = code
            # Asignamos 'out['final_url']' con fin_u
            out["final_url"] = fin_u
            # Asignamos '(stype, mot)' con clasificar_respuesta_http(url, code, fin_u...
            stype, mot = clasificar_respuesta_http(url, code, fin_u, txt)
            # Asignamos 'out['status_type']' con stype
            out["status_type"] = stype
            # Asignamos 'out['motivo']' con mot
            out["motivo"] = mot
        except Exception as exc:
            # Capturamos timeouts o errores de red sin penalizar la oferta (inmunidad transitoria)
            ename = type(exc).__name__.lower()
            # Evaluamos la condición lógica ('timeout' in ename or 'timed out' in str(exc).lower()) para controlar el flujo
            if "timeout" in ename or "timed out" in str(exc).lower():
                # Asignamos 'out['status_type']' con 'TIMEOUT'
                out["status_type"] = "TIMEOUT"
                # Asignamos 'out['motivo']' con 'Timeout > 10s'
                out["motivo"] = "Timeout > 10s"
            else:
                # Asignamos 'out['status_type']' con 'CONN_ERR'
                out["status_type"] = "CONN_ERR"
                # Asignamos 'out['motivo']' con str(exc)[:120]
                out["motivo"] = str(exc)[:120]
        # Retornamos el resultado procesado (out)
        return out

    # Contadores y estructuras de agregación de métricas por tienda y estado
    t0 = time.time()
    # Asignamos 'stats' con defaultdict(int)
    stats = defaultdict(int)
    # Asignamos 'tiendas_stats' con defaultdict(lambda: defaultdict(int))
    tiendas_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # Asignamos 'acciones_count' con defaultdict(int)
    acciones_count = defaultdict(int)
    # Asignamos 'desactivados_strike2' con []
    desactivados_strike2: List[Dict[str, Any]] = []
    # Asignamos 'marcados_strike1' con []
    marcados_strike1: List[Dict[str, Any]] = []
    # Asignamos 'resultados' con []
    resultados: List[Dict[str, Any]] = []

    # Ejecución concurrente multihilo para verificar la muestra completa en pocos segundos
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        # Asignamos 'futs' con [pool.submit(_check_one, it) for it in sam...
        futs = [pool.submit(_check_one, it) for it in sample]
        # Recorremos iterativamente cada 'fut' en as_completed(futs)
        for fut in as_completed(futs):
            # Asignamos 'r' con fut.result()
            r = fut.result()
            # Ejecutamos instrucción: resultados.append(r)
            resultados.append(r)
            # Asignamos 'st' con r['status_type']
            st = r["status_type"]
            # Actualizamos acumulativamente el valor de 'stats[st]'
            stats[st] += 1
            # Actualizamos acumulativamente el valor de 'tiendas_stats[r['tienda']][st]'
            tiendas_stats[r["tienda"]][st] += 1

    # Aplicamos la máquina de estados de histéresis de 2 strikes sobre cada resultado obtenido
    now_iso = datetime.now(timezone.utc).isoformat()
    # Recorremos iterativamente cada 'r' en resultados
    for r in resultados:
        # Asignamos 'dec' con decidir_accion_histeresis(r['status_type']...
        dec = decidir_accion_histeresis(r["status_type"], r["motivo"], r["ultimo_error_previo"])
        # Asignamos 'acc' con dec['accion']
        acc = dec["accion"]
        # Actualizamos acumulativamente el valor de 'acciones_count[acc]'
        acciones_count[acc] += 1
        # Asignamos 'r['accion_histeresis']' con acc
        r["accion_histeresis"] = acc
        # Evaluamos la condición lógica (acc == 'desactivar_strike_2') para controlar el flujo
        if acc == "desactivar_strike_2":
            # Ejecutamos instrucción: desactivados_strike2.append(r)
            desactivados_strike2.append(r)
        # Evaluamos la condición lógica (acc == 'marcar_strike_1') para controlar el flujo
        elif acc == "marcar_strike_1":
            # Ejecutamos instrucción: marcados_strike1.append(r)
            marcados_strike1.append(r)

        # Si no es dry_run y hay cambios que persistir (Strike 1, Strike 2 o limpieza de Strike), actualizamos Supabase
        if not dry_run and dec["payload"]:
            # Asignamos 'payload' con dict(dec['payload'], updated_at=now_iso)
            payload = dict(dec["payload"], updated_at=now_iso)
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("ofertas_actuales").update(payload).eq("id", r["id"]).execute()
            except Exception as exc:
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.warning(f"Error actualizando histéresis en oferta #{r['id']}: {exc}")

    # Si se desactivó alguna oferta por Strike 2, invalidamos la caché del catálogo
    if not dry_run and desactivados_strike2:
        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()

    # Asignamos 'duracion' con round(time.time() - t0, 1)
    duracion = round(time.time() - t0, 1)
    # Asignamos 'n_eval' con max(1, len(resultados))
    n_eval = max(1, len(resultados))
    # Asignamos 'n_no_waf' con max(1, sum((v for k, v in stats.items() if...
    n_no_waf = max(
        1,
        sum(
            v for k, v in stats.items()
            if k not in ("WAF_403", "RATE_LIMIT_429", "TIMEOUT", "CONN_ERR") and not k.startswith("SERVER_ERR_")
        ),
    )
    # Asignamos 'tasa_validos_efectiva' con round(stats['OK_200'] * 100.0 / n_no_waf, 2)
    tasa_validos_efectiva = round(stats["OK_200"] * 100.0 / n_no_waf, 2)

    # Asignamos 'reporte' con {'timestamp_utc': now_iso, 'modo': 'dry_ru...
    reporte = {
        "timestamp_utc": now_iso,
        "modo": "dry_run" if dry_run else "live",
        "total_evaluados": len(resultados),
        "duracion_segundos": duracion,
        "tasa_validos_sin_waf_pct": tasa_validos_efectiva,
        "resumen_estados": dict(stats),
        "acciones_histeresis": dict(acciones_count),
        "tiendas": {k: dict(v) for k, v in sorted(tiendas_stats.items())},
        "strike_1_registrados": marcados_strike1[:50],
        "strike_2_desactivados": desactivados_strike2,
    }

    # Asignamos 'target_json' con Path(output_path) if output_path else APP_...
    target_json = Path(output_path) if output_path else (APP_DIR / "data" / "reportes" / "ultima_auditoria_enlaces.json")
    # Ejecutamos instrucción: target_json.parent.mkdir(parents=True, exist_ok=True)
    target_json.parent.mkdir(parents=True, exist_ok=True)
    # Procesamiento de serialización o deserialización de estructura JSON
    target_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    # Persistir en `scraping_runs` y opcionalmente en `scraping_logs`
    detalle_run = (
        f"Evaluados={len(resultados)} | OK_200={stats['OK_200']} ({tasa_validos_efectiva}% s/WAF) | "
        f"Strike1={acciones_count['marcar_strike_1']} | Strike2_Off={acciones_count['desactivar_strike_2']} | "
        f"WAF_403={stats['WAF_403']}"
    )
    # Evaluamos la condición lógica (run_id) para controlar el flujo
    if run_id:
        # Ejecutamos instrucción: finalizar_scraping_run(run_id=run_id, estado='exitos...
        finalizar_scraping_run(
            run_id=run_id,
            estado="exitoso",
            productos_procesados=len(resultados),
            cambios_stock=acciones_count["desactivar_strike_2"],
            errores=stats["DEAD_404"] + stats["SOFT_404"] + stats["REDIRECT_HOME"],
            mensaje_detalle=detalle_run,
        )
    # Evaluamos la condición lógica (not dry_run) para controlar el flujo
    if not dry_run:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("scraping_logs").insert({
                "tipo_scraper": "auditoria_enlaces",
                "tienda_nombre": "Todas (Muestra Activa)",
                "estado": "EXITOSO",
                "productos_procesados": len(resultados),
                "productos_nuevos": 0,
                "precios_actualizados": acciones_count["limpiar_strike"],
                "mensaje_detalle": detalle_run,
            }).execute()
        except Exception as exc_log:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning("No se pudo insertar resumen en scraping_logs: %s", exc_log)

    # Generar resumen Markdown para consola y `$GITHUB_STEP_SUMMARY`
    md = [
        "## Auditoría Semanal de Enlaces Activos (Histéresis 2 Strikes)",
        "",
        f"- **Enlaces evaluados:** `{len(resultados)}` en `{duracion}s` (`{'DRY-RUN' if dry_run else 'LIVE'}`)",
        f"- **Enlaces válidos (excluyendo WAF/transitorios):** **{tasa_validos_efectiva}%** (`{stats['OK_200']}` HTTP 200 OK)",
        f"- **Strike 1 (advertencia sin desactivar):** `{acciones_count['marcar_strike_1']}`",
        f"- **Strike 2 (desactivados tras 2 fallos consecutivos):** `{acciones_count['desactivar_strike_2']}`",
        f"- **Strikes limpiados por recuperación 200 OK:** `{acciones_count['limpiar_strike']}`",
        f"- **Bloqueos WAF / Rate-limit ignorados (no penalizados):** `{stats['WAF_403'] + stats['RATE_LIMIT_429']}`",
        "",
        "| Tienda | OK 200 | Rotos (404/Soft/Home) | WAF 403/429 | Timeout/Red |",
        "|---|---:|---:|---:|---:|",
    ]
    # Recorremos iterativamente cada '(t_nom, st_d)' en sorted(tiendas_stats.items())
    for t_nom, st_d in sorted(tiendas_stats.items()):
        # Asignamos 'rotos_t' con st_d.get('DEAD_404', 0) + st_d.get('SOFT_4...
        rotos_t = st_d.get("DEAD_404", 0) + st_d.get("SOFT_404", 0) + st_d.get("REDIRECT_HOME", 0)
        # Asignamos 'waf_t' con st_d.get('WAF_403', 0) + st_d.get('RATE_LI...
        waf_t = st_d.get("WAF_403", 0) + st_d.get("RATE_LIMIT_429", 0)
        # Asignamos 'red_t' con st_d.get('TIMEOUT', 0) + st_d.get('CONN_ER...
        red_t = st_d.get("TIMEOUT", 0) + st_d.get("CONN_ERR", 0)
        # Ejecutamos instrucción: md.append(f"| {t_nom} | {st_d.get('OK_200', 0)} | {r...
        md.append(f"| {t_nom} | {st_d.get('OK_200', 0)} | {rotos_t} | {waf_t} | {red_t} |")

    # Asignamos 'md_txt' con '\n'.join(md) + '\n'
    md_txt = "\n".join(md) + "\n"
    # Ejecutamos instrucción: print('\n' + md_txt)
    print("\n" + md_txt)
    # Asignamos 'summary_env' con os.environ.get('GITHUB_STEP_SUMMARY')
    summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
    # Evaluamos la condición lógica (summary_env) para controlar el flujo
    if summary_env:
        # Gestión automática de contexto y recursos para: open(summary_env, 'a', encoding='utf-8')
        with open(summary_env, "a", encoding="utf-8") as sf:
            # Ejecutamos instrucción: sf.write(md_txt)
            sf.write(md_txt)

    # Retornamos el resultado procesado (reporte)
    return reporte


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Auditoría continua de enlaces con histéresis de 2 strikes.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--sample", type=int, default=1000, help="Tamaño de muestra (default: 1000).")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--workers", type=int, default=20, help="Hilos concurrentes (default: 20).")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--dry-run", action="store_true", help="Solo evalúa sin modificar Supabase.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--output", type=str, default=None, help="Ruta opcional del reporte JSON.")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Ejecutamos instrucción: ejecutar_auditoria_enlaces(sample_size=args.sample, ...
    ejecutar_auditoria_enlaces(
        sample_size=args.sample,
        workers=args.workers,
        dry_run=bool(args.dry_run),
        output_path=args.output,
    )


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()

