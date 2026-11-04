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

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.parse

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import (
    finalizar_scraping_run,
    get_supabase,
    iniciar_scraping_run,
    limpiar_cache_catalogo,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AuditoriaEnlaces")

STRIKE_1_TAG = "[AUDIT_STRIKE_1]"
STRIKE_2_TAG = "[AUDIT_STRIKE_2]"


# - ¿Qué hace esta función?:
#   Evalúa si la URL final tras redirecciones cayó en la portada o catálogo raíz
#   de la tienda en vez de una ficha de producto (soft-404 por redirección al home).
def es_redireccion_al_home(url_original: str, url_final: str) -> bool:
    try:
        orig_p = urllib.parse.urlparse(url_original).path.strip("/").lower()
        fin_p = urllib.parse.urlparse(url_final).path.strip("/").lower()
    except Exception:
        return False
    if len(orig_p) <= 4:
        return False
    rutas_home = {"", "falabella-cl", "collections", "collections/all", "tienda", "shop"}
    return fin_p in rutas_home


# - ¿Qué hace esta función?:
#   Clasifica la respuesta HTTP de un enlace de oferta en `OK_200`, `DEAD_404`,
#   `SOFT_404`, `REDIRECT_HOME`, `WAF_403`, `RATE_LIMIT_429`, `TIMEOUT` o `SERVER_ERR_*`.
def clasificar_respuesta_http(url_original: str, status_code: int, url_final: str, body_text: str) -> tuple[str, str]:
    if status_code == 200:
        low_u = (url_final or "").lower()
        low_t = (body_text or "")[:40000].lower()
        if "/404" in low_u or low_u.endswith("404"):
            return "SOFT_404", "Redirigió a ruta /404"
        if es_redireccion_al_home(url_original, url_final):
            return "REDIRECT_HOME", "Redirigió al home de la tienda (producto dado de baja)"
        patrones_404 = (
            "página no encontrada",
            "pagina no encontrada",
            "lo sentimos, no pudimos encontrar",
            "esta página no existe",
            "page not found",
        )
        if any(p in low_t for p in patrones_404) and '"@type":"product"' not in low_t.replace(" ", ""):
            return "SOFT_404", "Página muestra mensaje de no encontrada sin schema Product"
        return "OK_200", "Navegación exitosa 200 OK"
    if status_code == 404 or status_code == 410:
        return "DEAD_404", f"HTTP {status_code}"
    if status_code == 403:
        return "WAF_403", "Cloudflare/WAF anti-bot 403"
    if status_code == 429:
        return "RATE_LIMIT_429", "Rate limit HTTP 429"
    if status_code in (500, 502, 503, 504):
        return f"SERVER_ERR_{status_code}", f"Error servidor tienda {status_code}"
    return f"HTTP_{status_code}", f"Código HTTP {status_code}"


# - ¿Qué hace esta función?:
#   Aplica la máquina de estados de histéresis de 2 strikes a partir del `status_type`
#   observado y el valor previo de `ultimo_error` en la oferta.
def decidir_accion_histeresis(status_type: str, motivo: str, ultimo_error_previo: Optional[str]) -> Dict[str, Any]:
    prev = str(ultimo_error_previo or "")
    tenia_strike_1 = STRIKE_1_TAG in prev

    if status_type == "OK_200":
        if tenia_strike_1:
            return {"accion": "limpiar_strike", "payload": {"ultimo_error": None}}
        return {"accion": "ninguna", "payload": {}}

    if status_type in ("DEAD_404", "SOFT_404", "REDIRECT_HOME", "INVALID_URL"):
        if tenia_strike_1:
            return {
                "accion": "desactivar_strike_2",
                "payload": {
                    "en_stock": False,
                    "estado": "requiere_revision",
                    "ultimo_error": f"{STRIKE_2_TAG} {status_type}: {motivo}"[:240],
                },
            }
        return {
            "accion": "marcar_strike_1",
            "payload": {
                "ultimo_error": f"{STRIKE_1_TAG} {status_type}: {motivo}"[:240],
            },
        }

    # WAF 403, 429, 5xx o timeout: inmunidad total
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
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("Supabase no disponible para ejecutar auditoría de enlaces.")

    run_id = None if dry_run else iniciar_scraping_run(
        tipo_scraper="Auditoría Continua de Enlaces (Histéresis 2-Strike)",
        mensaje_detalle=f"Muestra objetivo: {sample_size} enlaces activos",
    )

    tiendas_raw = sb.table("tiendas").select("id, nombre").execute().data or []
    tiendas_map = {int(t["id"]): t["nombre"] for t in tiendas_raw}

    pool_ofertas: List[Dict[str, Any]] = []
    offset = 0
    while True:
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
        batch = r.data or []
        if not batch:
            break
        pool_ofertas.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    # Priorizar re-verificación de ofertas que ya tengan [AUDIT_STRIKE_1] + muestra aleatoria del resto
    con_strike_prev = [o for o in pool_ofertas if STRIKE_1_TAG in str(o.get("ultimo_error") or "")]
    sin_strike_prev = [o for o in pool_ofertas if STRIKE_1_TAG not in str(o.get("ultimo_error") or "")]
    random.shuffle(sin_strike_prev)
    cupo_restante = max(0, sample_size - len(con_strike_prev))
    sample = (con_strike_prev[:sample_size] + sin_strike_prev[:cupo_restante])[:sample_size]

    logger.info(
        f"Pool activo total: {len(pool_ofertas)} | Muestra seleccionada: {len(sample)} "
        f"(con Strike 1 previo: {min(len(con_strike_prev), sample_size)})"
    )

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    def _check_one(item: Dict[str, Any]) -> Dict[str, Any]:
        oid = int(item["id"])
        url = str(item.get("url_producto") or "").strip()
        tid = int(item.get("tienda_id") or 0)
        tname = tiendas_map.get(tid, f"Tienda {tid}")
        var_d = item.get("variantes_perfume") or {}
        perf_d = var_d.get("perfumes") or {}
        label = f"{perf_d.get('marca', '')} - {perf_d.get('nombre', '')} ({var_d.get('volumen_ml', 0)}ml)"

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
        if not url.startswith("http"):
            out["status_type"] = "INVALID_URL"
            out["motivo"] = "URL vacía o sin protocolo"
            return out

        try:
            if curl_requests is not None:
                with curl_requests.Session(impersonate="chrome120") as s:
                    resp = s.get(url, headers=headers, timeout=10, allow_redirects=True)
                    code = int(resp.status_code)
                    fin_u = str(resp.url)
                    txt = resp.text or ""
            else:
                resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                code = int(resp.status_code)
                fin_u = str(resp.url)
                txt = resp.text or ""

            out["status_code"] = code
            out["final_url"] = fin_u
            stype, mot = clasificar_respuesta_http(url, code, fin_u, txt)
            out["status_type"] = stype
            out["motivo"] = mot
        except Exception as exc:
            ename = type(exc).__name__.lower()
            if "timeout" in ename or "timed out" in str(exc).lower():
                out["status_type"] = "TIMEOUT"
                out["motivo"] = "Timeout > 10s"
            else:
                out["status_type"] = "CONN_ERR"
                out["motivo"] = str(exc)[:120]
        return out

    t0 = time.time()
    stats = defaultdict(int)
    tiendas_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    acciones_count = defaultdict(int)
    desactivados_strike2: List[Dict[str, Any]] = []
    marcados_strike1: List[Dict[str, Any]] = []
    resultados: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = [pool.submit(_check_one, it) for it in sample]
        for fut in as_completed(futs):
            r = fut.result()
            resultados.append(r)
            st = r["status_type"]
            stats[st] += 1
            tiendas_stats[r["tienda"]][st] += 1

    now_iso = datetime.now(timezone.utc).isoformat()
    for r in resultados:
        dec = decidir_accion_histeresis(r["status_type"], r["motivo"], r["ultimo_error_previo"])
        acc = dec["accion"]
        acciones_count[acc] += 1
        r["accion_histeresis"] = acc
        if acc == "desactivar_strike_2":
            desactivados_strike2.append(r)
        elif acc == "marcar_strike_1":
            marcados_strike1.append(r)

        if not dry_run and dec["payload"]:
            payload = dict(dec["payload"], updated_at=now_iso)
            try:
                sb.table("ofertas_actuales").update(payload).eq("id", r["id"]).execute()
            except Exception as exc:
                logger.warning(f"Error actualizando histéresis en oferta #{r['id']}: {exc}")

    if not dry_run and desactivados_strike2:
        limpiar_cache_catalogo()

    duracion = round(time.time() - t0, 1)
    n_eval = max(1, len(resultados))
    n_no_waf = max(
        1,
        sum(
            v for k, v in stats.items()
            if k not in ("WAF_403", "RATE_LIMIT_429", "TIMEOUT", "CONN_ERR") and not k.startswith("SERVER_ERR_")
        ),
    )
    tasa_validos_efectiva = round(stats["OK_200"] * 100.0 / n_no_waf, 2)

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

    target_json = Path(output_path) if output_path else (APP_DIR / "data" / "reportes" / "ultima_auditoria_enlaces.json")
    target_json.parent.mkdir(parents=True, exist_ok=True)
    target_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    # Persistir en `scraping_runs` y opcionalmente en `scraping_logs`
    detalle_run = (
        f"Evaluados={len(resultados)} | OK_200={stats['OK_200']} ({tasa_validos_efectiva}% s/WAF) | "
        f"Strike1={acciones_count['marcar_strike_1']} | Strike2_Off={acciones_count['desactivar_strike_2']} | "
        f"WAF_403={stats['WAF_403']}"
    )
    if run_id:
        finalizar_scraping_run(
            run_id=run_id,
            estado="exitoso",
            productos_procesados=len(resultados),
            cambios_stock=acciones_count["desactivar_strike_2"],
            errores=stats["DEAD_404"] + stats["SOFT_404"] + stats["REDIRECT_HOME"],
            mensaje_detalle=detalle_run,
        )
    if not dry_run:
        try:
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
    for t_nom, st_d in sorted(tiendas_stats.items()):
        rotos_t = st_d.get("DEAD_404", 0) + st_d.get("SOFT_404", 0) + st_d.get("REDIRECT_HOME", 0)
        waf_t = st_d.get("WAF_403", 0) + st_d.get("RATE_LIMIT_429", 0)
        red_t = st_d.get("TIMEOUT", 0) + st_d.get("CONN_ERR", 0)
        md.append(f"| {t_nom} | {st_d.get('OK_200', 0)} | {rotos_t} | {waf_t} | {red_t} |")

    md_txt = "\n".join(md) + "\n"
    print("\n" + md_txt)
    summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_env:
        with open(summary_env, "a", encoding="utf-8") as sf:
            sf.write(md_txt)

    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoría continua de enlaces con histéresis de 2 strikes.")
    parser.add_argument("--sample", type=int, default=1000, help="Tamaño de muestra (default: 1000).")
    parser.add_argument("--workers", type=int, default=20, help="Hilos concurrentes (default: 20).")
    parser.add_argument("--dry-run", action="store_true", help="Solo evalúa sin modificar Supabase.")
    parser.add_argument("--output", type=str, default=None, help="Ruta opcional del reporte JSON.")
    args = parser.parse_args()

    ejecutar_auditoria_enlaces(
        sample_size=args.sample,
        workers=args.workers,
        dry_run=bool(args.dry_run),
        output_path=args.output,
    )


if __name__ == "__main__":
    main()

