# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Sincronizador Local de Retailers (Paris / Ripley) — Fase 2 (§5-B Opción 1)
===============================================================================================
Como los runners en la nube de GitHub Actions (`ubuntu-latest`, IPs datacenter de EE.UU.) reciben
bloqueo WAF 403 por reputación de IP/ASN en Paris y Ripley (incluso con `curl_cffi`), este CLI
permite actualizar únicamente las ofertas de Paris y Ripley desde una IP residencial chilena
(por ejemplo, tarea programada en el PC del usuario o runner auto-hospedado).

Por defecto se ejecuta en `--dry-run` (solo verifica en vivo e imprime métricas sin tocar Supabase).
Para persistir las actualizaciones en Supabase, pasar `--apply`.

Uso:
  python APP/backend/mantenimiento/sincronizar_retail_local.py --dry-run --limit 20
  python APP/backend/mantenimiento/sincronizar_retail_local.py --apply --stores Paris,Ripley --limit 300
"""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import (
    finalizar_scraping_run,
    get_supabase,
    iniciar_scraping_run,
    limpiar_cache_catalogo,
    registrar_fallo_scraping,
    registrar_observacion_oferta,
)
from backend.normalizador import contexto_genero_esperado
from backend.scraper_periodico import (
    crear_sesion_robusta,
    extraer_variedades_paris,
    extraer_variedades_ripley,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SyncRetailLocal")


# - ¿Qué hace esta función?:
#   Descarga paginadamente las ofertas de Paris y Ripley ordenadas por mayor antigüedad
#   (`ultima_verificacion_exitosa` ASC) para refrescar primero las más obsoletas desde IP residencial.
def obtener_cola_lru_retail(sb: Any, nombres_tiendas: List[str], limit: int) -> List[Dict[str, Any]]:
    tiendas = sb.table("tiendas").select("id, nombre").execute().data or []
    mapa_tiendas = {int(t["id"]): t["nombre"] for t in tiendas if t["nombre"].lower() in {n.lower() for n in nombres_tiendas}}
    if not mapa_tiendas:
        return []

    filas: List[Dict[str, Any]] = []
    for tid, tnom in mapa_tiendas.items():
        offset = 0
        while True:
            r = (
                sb.table("ofertas_actuales")
                .select(
                    "id, tienda_id, url_producto, precio_actual, en_stock, estado, ultima_verificacion_exitosa, "
                    "variantes_perfume!inner(id, volumen_ml, formato, perfumes!inner(id, nombre, marca, tipo, genero, precio_referencia))"
                )
                .eq("tienda_id", tid)
                .neq("estado", "requiere_revision")
                .order("ultima_verificacion_exitosa", desc=False)
                .range(offset, offset + 999)
                .execute()
            )
            batch = r.data or []
            if not batch:
                break
            for row in batch:
                row["_tienda_nombre"] = tnom
                filas.append(row)
            if len(batch) < 1000:
                break
            offset += 1000

    # Deduplicar por (perfume_id, tienda_id) priorizando la oferta más antigua
    filas.sort(key=lambda x: str(x.get("ultima_verificacion_exitosa") or ""))
    vistos = set()
    cola = []
    for f in filas:
        perf = f["variantes_perfume"]["perfumes"]
        key = (int(perf["id"]), int(f["tienda_id"]))
        if key in vistos:
            continue
        vistos.add(key)
        cola.append(f)
        if len(cola) >= limit:
            break
    return cola


# - ¿Qué hace esta función principal?:
#   Audita en vivo la cola LRU de Paris/Ripley usando `curl_cffi` desde IP local y,
#   si `apply_changes=True`, actualiza `ofertas_actuales` y `scraping_runs`.
def ejecutar_sincronizacion_retail_local(
    stores: List[str],
    limit: int = 200,
    apply_changes: bool = False,
) -> Dict[str, Any]:
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("No se pudo conectar a Supabase con service_role.")

    cola = obtener_cola_lru_retail(sb, stores, limit=limit)
    session = crear_sesion_robusta()
    run_id = iniciar_scraping_run(
        tipo_scraper="Sincronización Retail Local (IP Residencial)",
        mensaje_detalle=f"Tiendas={','.join(stores)} | Lote={len(cola)}",
    ) if apply_changes else None

    stats = {s: {"consultas": 0, "exitos": 0, "waf": 0, "sin_match": 0} for s in stores}
    actualizadas = 0

    for item in cola:
        tnom = item["_tienda_nombre"]
        tid = int(item["tienda_id"])
        var_d = item["variantes_perfume"]
        perf = var_d["perfumes"]
        pid = int(perf["id"])
        vol_base = int(round(float(var_d.get("volumen_ml") or 100)))
        url_dir = item.get("url_producto")
        diag: Dict[str, Any] = {}

        stats.setdefault(tnom, {"consultas": 0, "exitos": 0, "waf": 0, "sin_match": 0})
        stats[tnom]["consultas"] += 1

        with contexto_genero_esperado(perf.get("genero")):
            if "paris" in tnom.lower():
                vars_res = extraer_variedades_paris(
                    session=session,
                    url_directa=url_dir,
                    perfume_nombre=perf["nombre"],
                    marca=perf.get("marca") or "",
                    volumen_ml_defecto=vol_base,
                    concentracion=perf.get("tipo") or "",
                    precio_referencia=perf.get("precio_referencia"),
                    diagnostico=diag,
                )
            else:
                vars_res = extraer_variedades_ripley(
                    session=session,
                    url_directa=url_dir,
                    perfume_nombre=perf["nombre"],
                    marca=perf.get("marca") or "",
                    volumen_ml_defecto=vol_base,
                    concentracion=perf.get("tipo") or "",
                    precio_referencia=perf.get("precio_referencia"),
                    diagnostico=diag,
                )

        if vars_res:
            stats[tnom]["exitos"] += 1
            if apply_changes:
                for vd in vars_res:
                    if not vd.get("exito") or not vd.get("volumen_ml"):
                        continue
                    registrar_observacion_oferta({
                        "perfume_id": pid,
                        "tienda_id": tid,
                        "precio_actual": int(vd["precio_actual"]),
                        "precio_normal": int(vd.get("precio_normal") or vd["precio_actual"]),
                        "en_stock": bool(vd.get("en_stock", True)),
                        "url_producto": vd["url"],
                        "volumen_ml": int(vd["volumen_ml"]),
                        "formato": str(vd.get("formato") or "regular"),
                        "scraping_run_id": run_id,
                    })
                    actualizadas += 1
        elif diag.get("waf_bloqueado"):
            stats[tnom]["waf"] += 1
        else:
            stats[tnom]["sin_match"] += 1
            if apply_changes:
                registrar_fallo_scraping(
                    tienda_id=tid,
                    perfume_id=pid,
                    mensaje=f"No encontrado en {tnom} (sync local)",
                    motivo_codigo="no_encontrado_en_feed",
                )

        time.sleep(random.uniform(0.35, 0.75))

    if apply_changes:
        if run_id:
            finalizar_scraping_run(
                run_id=run_id,
                estado="completado",
                productos_procesados=len(cola),
                cambios_precio=actualizadas,
                mensaje_detalle=f"Sync retail local completado: {actualizadas} ofertas actualizadas.",
            )
        limpiar_cache_catalogo()

    print("\n" + "=" * 72)
    print(f"RESUMEN SINCRONIZACIÓN RETAIL LOCAL ({'APPLY' if apply_changes else 'DRY-RUN'})")
    print("=" * 72)
    for st_name, vals in stats.items():
        c = max(1, vals["consultas"])
        print(
            f"  {st_name:12s} | consultas={vals['consultas']:4d} | exitos={vals['exitos']:4d} "
            f"({vals['exitos']*100.0/c:5.1f}%) | waf={vals['waf']:3d} | sin_match={vals['sin_match']:3d}"
        )
    print("=" * 72)
    return {"stats": stats, "actualizadas": actualizadas, "modo": "apply" if apply_changes else "dry_run"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincronización de Paris y Ripley desde IP residencial.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo diagnóstico en vivo sin escribir en BD.")
    grp.add_argument("--apply", action="store_true", help="Persiste las actualizaciones en Supabase.")
    parser.add_argument("--stores", type=str, default="Paris,Ripley", help="Tiendas separadas por coma.")
    parser.add_argument("--limit", type=int, default=50, help="Máximo de perfumes por corrida.")
    args = parser.parse_args()

    tiendas = [s.strip() for s in args.stores.split(",") if s.strip()]
    ejecutar_sincronizacion_retail_local(stores=tiendas, limit=max(1, args.limit), apply_changes=bool(args.apply))


if __name__ == "__main__":
    main()
