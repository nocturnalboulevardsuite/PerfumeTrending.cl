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

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (datetime, timezone) desde el módulo 'datetime'
from datetime import datetime, timezone
# Importación de librería estándar o dependencia externa (logging)
import logging
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

# Importación de componentes (finalizar_scraping_run, get_supabase, iniciar_scraping_run, limpiar_cache_catalogo, ...) desde el módulo 'backend.database'
from backend.database import (
    finalizar_scraping_run,
    get_supabase,
    iniciar_scraping_run,
    limpiar_cache_catalogo,
    registrar_fallo_scraping,
    registrar_observacion_oferta,
)
# Importación de componentes (contexto_genero_esperado) desde el módulo 'backend.normalizador'
from backend.normalizador import contexto_genero_esperado
# Importación de componentes (crear_sesion_robusta, extraer_variedades_paris, extraer_variedades_ripley) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import (
    crear_sesion_robusta,
    extraer_variedades_paris,
    extraer_variedades_ripley,
)

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Asignamos 'logger' con logging.getLogger('SyncRetailLocal')
logger = logging.getLogger("SyncRetailLocal")


# - ¿Qué hace esta función?:
#   Descarga paginadamente las ofertas de Paris y Ripley ordenadas por mayor antigüedad
#   (`ultima_verificacion_exitosa` ASC) para refrescar primero las más obsoletas desde IP residencial.
def obtener_cola_lru_retail(sb: Any, nombres_tiendas: List[str], limit: int) -> List[Dict[str, Any]]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    tiendas = sb.table("tiendas").select("id, nombre").execute().data or []
    # Asignamos 'mapa_tiendas' con {int(t['id']): t['nombre'] for t in tienda...
    mapa_tiendas = {int(t["id"]): t["nombre"] for t in tiendas if t["nombre"].lower() in {n.lower() for n in nombres_tiendas}}
    # Evaluamos la condición lógica (not mapa_tiendas) para controlar el flujo
    if not mapa_tiendas:
        # Retornamos el resultado procesado ([])
        return []

    # Asignamos 'filas' con []
    filas: List[Dict[str, Any]] = []
    # Recorremos iterativamente cada '(tid, tnom)' en mapa_tiendas.items()
    for tid, tnom in mapa_tiendas.items():
        # Asignamos 'offset' con 0
        offset = 0
        # Ejecutamos el ciclo mientras se mantenga la condición: True
        while True:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
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
            # Asignamos 'batch' con r.data or []
            batch = r.data or []
            # Evaluamos la condición lógica (not batch) para controlar el flujo
            if not batch:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # Recorremos iterativamente cada 'row' en batch
            for row in batch:
                # Asignamos 'row['_tienda_nombre']' con tnom
                row["_tienda_nombre"] = tnom
                # Ejecutamos instrucción: filas.append(row)
                filas.append(row)
            # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
            if len(batch) < 1000:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # Actualizamos acumulativamente el valor de 'offset'
            offset += 1000

    # Deduplicar por (perfume_id, tienda_id) priorizando la oferta más antigua
    filas.sort(key=lambda x: str(x.get("ultima_verificacion_exitosa") or ""))
    # Asignamos 'vistos' con set()
    vistos = set()
    # Asignamos 'cola' con []
    cola = []
    # Recorremos iterativamente cada 'f' en filas
    for f in filas:
        # Asignamos 'perf' con f['variantes_perfume']['perfumes']
        perf = f["variantes_perfume"]["perfumes"]
        # Asignamos 'key' con (int(perf['id']), int(f['tienda_id']))
        key = (int(perf["id"]), int(f["tienda_id"]))
        # Evaluamos la condición lógica (key in vistos) para controlar el flujo
        if key in vistos:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Ejecutamos instrucción: vistos.add(key)
        vistos.add(key)
        # Ejecutamos instrucción: cola.append(f)
        cola.append(f)
        # Evaluamos la condición lógica (len(cola) >= limit) para controlar el flujo
        if len(cola) >= limit:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
    # Retornamos el resultado procesado (cola)
    return cola


# - ¿Qué hace esta función principal?:
#   Audita en vivo la cola LRU de Paris/Ripley usando `curl_cffi` desde IP local y,
#   si `apply_changes=True`, actualiza `ofertas_actuales` y `scraping_runs`.
def ejecutar_sincronizacion_retail_local(
    stores: List[str],
    limit: int = 200,
    apply_changes: bool = False,
) -> Dict[str, Any]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("No se pudo conectar a Supabase con service_role.")

    # Asignamos 'cola' con obtener_cola_lru_retail(sb, stores, limit=...
    cola = obtener_cola_lru_retail(sb, stores, limit=limit)
    # Asignamos 'session' con crear_sesion_robusta()
    session = crear_sesion_robusta()
    # Asignamos 'run_id' con iniciar_scraping_run(tipo_scraper='Sincron...
    run_id = iniciar_scraping_run(
        tipo_scraper="Sincronización Retail Local (IP Residencial)",
        mensaje_detalle=f"Tiendas={','.join(stores)} | Lote={len(cola)}",
    ) if apply_changes else None

    # Asignamos 'stats' con {s: {'consultas': 0, 'exitos': 0, 'waf': 0...
    stats = {s: {"consultas": 0, "exitos": 0, "waf": 0, "sin_match": 0} for s in stores}
    # Asignamos 'actualizadas' con 0
    actualizadas = 0

    # Recorremos iterativamente cada 'item' en cola
    for item in cola:
        # Asignamos 'tnom' con item['_tienda_nombre']
        tnom = item["_tienda_nombre"]
        # Asignamos 'tid' con int(item['tienda_id'])
        tid = int(item["tienda_id"])
        # Asignamos 'var_d' con item['variantes_perfume']
        var_d = item["variantes_perfume"]
        # Asignamos 'perf' con var_d['perfumes']
        perf = var_d["perfumes"]
        # Asignamos 'pid' con int(perf['id'])
        pid = int(perf["id"])
        # Asignamos 'vol_base' con int(round(float(var_d.get('volumen_ml') or...
        vol_base = int(round(float(var_d.get("volumen_ml") or 100)))
        # Asignamos 'url_dir' con item.get('url_producto')
        url_dir = item.get("url_producto")
        # Asignamos 'diag' con {}
        diag: Dict[str, Any] = {}

        # Ejecutamos instrucción: stats.setdefault(tnom, {'consultas': 0, 'exitos': 0,...
        stats.setdefault(tnom, {"consultas": 0, "exitos": 0, "waf": 0, "sin_match": 0})
        # Actualizamos acumulativamente el valor de 'stats[tnom]['consultas']'
        stats[tnom]["consultas"] += 1

        # Gestión automática de contexto y recursos para: contexto_genero_esperado(perf.get('genero'))
        with contexto_genero_esperado(perf.get("genero")):
            # Evaluamos la condición lógica ('paris' in tnom.lower()) para controlar el flujo
            if "paris" in tnom.lower():
                # Asignamos 'vars_res' con extraer_variedades_paris(session=session, ...
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
                # Asignamos 'vars_res' con extraer_variedades_ripley(session=session,...
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

        # Evaluamos la condición lógica (vars_res) para controlar el flujo
        if vars_res:
            # Actualizamos acumulativamente el valor de 'stats[tnom]['exitos']'
            stats[tnom]["exitos"] += 1
            # Evaluamos la condición lógica (apply_changes) para controlar el flujo
            if apply_changes:
                # Recorremos iterativamente cada 'vd' en vars_res
                for vd in vars_res:
                    # Evaluamos la condición lógica (not vd.get('exito') or not vd.get('volumen_ml')) para controlar el flujo
                    if not vd.get("exito") or not vd.get("volumen_ml"):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Ejecutamos instrucción: registrar_observacion_oferta({'perfume_id': pid, 'ti...
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
                    # Actualizamos acumulativamente el valor de 'actualizadas'
                    actualizadas += 1
        # Evaluamos la condición lógica (diag.get('waf_bloqueado')) para controlar el flujo
        elif diag.get("waf_bloqueado"):
            # Actualizamos acumulativamente el valor de 'stats[tnom]['waf']'
            stats[tnom]["waf"] += 1
        else:
            # Actualizamos acumulativamente el valor de 'stats[tnom]['sin_match']'
            stats[tnom]["sin_match"] += 1
            # Evaluamos la condición lógica (apply_changes) para controlar el flujo
            if apply_changes:
                # Ejecutamos instrucción: registrar_fallo_scraping(tienda_id=tid, perfume_id=p...
                registrar_fallo_scraping(
                    tienda_id=tid,
                    perfume_id=pid,
                    mensaje=f"No encontrado en {tnom} (sync local)",
                    motivo_codigo="no_encontrado_en_feed",
                )

        # Ejecutamos instrucción: time.sleep(random.uniform(0.35, 0.75))
        time.sleep(random.uniform(0.35, 0.75))

    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Evaluamos la condición lógica (run_id) para controlar el flujo
        if run_id:
            # Ejecutamos instrucción: finalizar_scraping_run(run_id=run_id, estado='comple...
            finalizar_scraping_run(
                run_id=run_id,
                estado="completado",
                productos_procesados=len(cola),
                cambios_precio=actualizadas,
                mensaje_detalle=f"Sync retail local completado: {actualizadas} ofertas actualizadas.",
            )
        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()

    # Ejecutamos instrucción: print('\n' + '=' * 72)
    print("\n" + "=" * 72)
    # Ejecutamos instrucción: print(f"RESUMEN SINCRONIZACIÓN RETAIL LOCAL ({('APPL...
    print(f"RESUMEN SINCRONIZACIÓN RETAIL LOCAL ({'APPLY' if apply_changes else 'DRY-RUN'})")
    # Ejecutamos instrucción: print('=' * 72)
    print("=" * 72)
    # Recorremos iterativamente cada '(st_name, vals)' en stats.items()
    for st_name, vals in stats.items():
        # Asignamos 'c' con max(1, vals['consultas'])
        c = max(1, vals["consultas"])
        # Ejecutamos instrucción: print(f" {st_name:12s} | consultas={vals['consultas'...
        print(
            f"  {st_name:12s} | consultas={vals['consultas']:4d} | exitos={vals['exitos']:4d} "
            f"({vals['exitos']*100.0/c:5.1f}%) | waf={vals['waf']:3d} | sin_match={vals['sin_match']:3d}"
        )
    # Ejecutamos instrucción: print('=' * 72)
    print("=" * 72)
    # Retornamos el resultado procesado ({'stats': stats, 'actualizadas': actualizadas, ...)
    return {"stats": stats, "actualizadas": actualizadas, "modo": "apply" if apply_changes else "dry_run"}


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Sincronización de Paris y Ripley desde IP residencial.")
    # Asignamos 'grp' con parser.add_mutually_exclusive_group()
    grp = parser.add_mutually_exclusive_group()
    # Ejecutamos instrucción: grp.add_argument('--dry-run', action='store_true', d...
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo diagnóstico en vivo sin escribir en BD.")
    # Ejecutamos instrucción: grp.add_argument('--apply', action='store_true', hel...
    grp.add_argument("--apply", action="store_true", help="Persiste las actualizaciones en Supabase.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--stores", type=str, default="Paris,Ripley", help="Tiendas separadas por coma.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--limit", type=int, default=50, help="Máximo de perfumes por corrida.")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Asignamos 'tiendas' con [s.strip() for s in args.stores.split(',')...
    tiendas = [s.strip() for s in args.stores.split(",") if s.strip()]
    # Ejecutamos instrucción: ejecutar_sincronizacion_retail_local(stores=tiendas,...
    ejecutar_sincronizacion_retail_local(stores=tiendas, limit=max(1, args.limit), apply_changes=bool(args.apply))


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()

