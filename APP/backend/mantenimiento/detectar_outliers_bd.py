# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Detector y Auditor de Precios Atípicos en BD (Fase 5 / Post-Fusión Fase 4)
===============================================================================================
Escanea todas las ofertas activas en stock en Supabase agrupadas por `(perfume_id, volumen_ml)`,
aplica `detectar_precios_atipicos` (< 0.5x mediana, > 2.2x mediana con >= 4 ofertas, y
`tester` > precio regular), respalda las detecciones en `scratch/backups/outliers_precios_<ts>.csv`
y, con `--apply`, marca dichas ofertas con `estado = 'requiere_revision'` (sin borrarlas).

Uso:
  python APP/backend/mantenimiento/detectar_outliers_bd.py --dry-run
  python APP/backend/mantenimiento/detectar_outliers_bd.py --apply
"""

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (defaultdict) desde el módulo 'collections'
from collections import defaultdict
# Importación de librería estándar o dependencia externa (csv)
import csv
# Importación de componentes (datetime, timezone) desde el módulo 'datetime'
from datetime import datetime, timezone
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de componentes (Any, Dict, List, Tuple) desde el módulo 'typing'
from typing import Any, Dict, List, Tuple

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

# Importación de componentes (get_supabase, limpiar_cache_catalogo) desde el módulo 'backend.database'
from backend.database import get_supabase, limpiar_cache_catalogo
# Importación de componentes (detectar_precios_atipicos) desde el módulo 'backend.normalizador'
from backend.normalizador import detectar_precios_atipicos

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Asignamos 'logger' con logging.getLogger('OutliersBD')
logger = logging.getLogger("OutliersBD")


# - ¿Qué hace esta función?:
#   Descarga todas las filas de una tabla de Supabase paginando de 1.000 en 1.000.
def _fetch_all(sb: Any, table: str, select: str) -> List[Dict[str, Any]]:
    # Asignamos 'out' con []
    out: List[Dict[str, Any]] = []
    # Asignamos 'offset' con 0
    offset = 0
    # Ejecutamos el ciclo mientras se mantenga la condición: True
    while True:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        r = sb.table(table).select(select).order("id", desc=False).range(offset, offset + 999).execute()
        # Asignamos 'batch' con r.data or []
        batch = r.data or []
        # Evaluamos la condición lógica (not batch) para controlar el flujo
        if not batch:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Ejecutamos instrucción: out.extend(batch)
        out.extend(batch)
        # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
        if len(batch) < 1000:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Actualizamos acumulativamente el valor de 'offset'
        offset += 1000
    # Retornamos el resultado procesado (out)
    return out


# - ¿Qué hace esta función principal?:
#   Evalúa precios atípicos en todo el catálogo activo, guarda respaldo CSV/JSON y,
#   en modo `--apply`, actualiza `estado='requiere_revision'` sobre las ofertas marcadas.
def ejecutar_deteccion_outliers_bd(apply_changes: bool = False) -> Dict[str, Any]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("No se pudo conectar a Supabase con service_role.")

    # Asignamos 'perfumes' con {int(p['id']): p for p in _fetch_all(sb, '...
    perfumes = {int(p["id"]): p for p in _fetch_all(sb, "perfumes", "id, marca, nombre, tipo")}
    # Asignamos 'variantes' con {int(v['id']): v for v in _fetch_all(sb, '...
    variantes = {int(v["id"]): v for v in _fetch_all(sb, "variantes_perfume", "id, perfume_id, volumen_ml, formato")}
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    tiendas = {int(t["id"]): t["nombre"] for t in (sb.table("tiendas").select("id, nombre").execute().data or [])}

    # Asignamos 'ofertas_activas' con []
    ofertas_activas: List[Dict[str, Any]] = []
    # Asignamos 'offset' con 0
    offset = 0
    # Ejecutamos el ciclo mientras se mantenga la condición: True
    while True:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        r = (
            sb.table("ofertas_actuales")
            .select("id, variante_id, tienda_id, precio_actual, precio_normal, en_stock, estado, url_producto, ultimo_error")
            .eq("estado", "activa")
            .eq("en_stock", True)
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
        # Ejecutamos instrucción: ofertas_activas.extend(batch)
        ofertas_activas.extend(batch)
        # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
        if len(batch) < 1000:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Actualizamos acumulativamente el valor de 'offset'
        offset += 1000

    # Asignamos 'por_perfume_vol' con defaultdict(list)
    por_perfume_vol: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    # Recorremos iterativamente cada 'o' en ofertas_activas
    for o in ofertas_activas:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        v = variantes.get(int(o["variante_id"]))
        # Evaluamos la condición lógica (not v) para controlar el flujo
        if not v:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'pid' con int(v['perfume_id'])
        pid = int(v["perfume_id"])
        # Asignamos 'vol' con int(round(float(v.get('volumen_ml') or 100)))
        vol = int(round(float(v.get("volumen_ml") or 100)))
        # Asignamos 'fmt' con str(v.get('formato') or 'regular').lower()
        fmt = str(v.get("formato") or "regular").lower()
        # Asignamos 'enriq' con dict(o)
        enriq = dict(o)
        # Asignamos 'enriq['perfume_id']' con pid
        enriq["perfume_id"] = pid
        # Asignamos 'enriq['volumen_ml']' con vol
        enriq["volumen_ml"] = vol
        # Asignamos 'enriq['formato']' con fmt
        enriq["formato"] = fmt
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        enriq["tienda_nombre"] = tiendas.get(int(o["tienda_id"]), str(o["tienda_id"]))
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        p_info = perfumes.get(pid, {})
        # Asignamos 'enriq['perfume_label']' con f"{p_info.get('marca', '')} - {p_info.get(...
        enriq["perfume_label"] = f"{p_info.get('marca', '')} - {p_info.get('nombre', '')} ({vol}ml)"
        # Ejecutamos instrucción: por_perfume_vol[pid, vol].append(enriq)
        por_perfume_vol[(pid, vol)].append(enriq)

    # Asignamos 'outliers_totales' con []
    outliers_totales: List[Dict[str, Any]] = []
    # Recorremos iterativamente cada '((_pid, _vol), grupo)' en sorted(por_perfume_vol.items())
    for (_pid, _vol), grupo in sorted(por_perfume_vol.items()):
        # Asignamos 'detectados' con detectar_precios_atipicos(grupo)
        detectados = detectar_precios_atipicos(grupo)
        # Ejecutamos instrucción: outliers_totales.extend(detectados)
        outliers_totales.extend(detectados)

    # Asignamos 'ts' con datetime.now().strftime('%Y%m%d_%H%M%S')
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Asignamos 'modo_str' con 'apply' if apply_changes else 'dry_run'
    modo_str = "apply" if apply_changes else "dry_run"
    # Asignamos 'csv_path' con REPO_ROOT / 'scratch' / 'backups' / f'outl...
    csv_path = REPO_ROOT / "scratch" / "backups" / f"outliers_precios_{modo_str}_{ts}.csv"
    # Ejecutamos instrucción: csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    # Asignamos 'campos' con ['id', 'perfume_id', 'perfume_label', 'vol...
    campos = [
        "id", "perfume_id", "perfume_label", "volumen_ml", "formato",
        "tienda_nombre", "precio_actual", "mediana_referencia", "regla_outlier",
        "motivo_outlier", "url_producto",
    ]
    # Gestión automática de contexto y recursos para: csv_path.open('w', encoding='utf-8', newline='')
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        # Asignamos 'w' con csv.DictWriter(f, fieldnames=campos, extra...
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        # Ejecutamos instrucción: w.writeheader()
        w.writeheader()
        # Ejecutamos instrucción: w.writerows(outliers_totales)
        w.writerows(outliers_totales)

    # Asignamos 'now_iso' con datetime.now(timezone.utc).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    # Asignamos 'aplicados' con 0
    aplicados = 0
    # Evaluamos la condición lógica (apply_changes and outliers_totales) para controlar el flujo
    if apply_changes and outliers_totales:
        # Recorremos iterativamente cada 'out_item' en outliers_totales
        for out_item in outliers_totales:
            # Asignamos 'oid' con int(out_item['id'])
            oid = int(out_item["id"])
            # Asignamos 'motivo_txt' con f"[OUTLIER_PRECIO] {out_item['motivo_outli...
            motivo_txt = f"[OUTLIER_PRECIO] {out_item['motivo_outlier']}"[:240]
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("ofertas_actuales").update({
                "estado": "requiere_revision",
                "ultimo_error": motivo_txt,
                "updated_at": now_iso,
            }).eq("id", oid).execute()
            # Actualizamos acumulativamente el valor de 'aplicados'
            aplicados += 1
        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()

    # Asignamos 'rep_json' con APP_DIR / 'data' / 'reportes' / 'ultimos_o...
    rep_json = APP_DIR / "data" / "reportes" / "ultimos_outliers_precios.json"
    # Ejecutamos instrucción: rep_json.parent.mkdir(parents=True, exist_ok=True)
    rep_json.parent.mkdir(parents=True, exist_ok=True)
    # Procesamiento de serialización o deserialización de estructura JSON
    rep_json.write_text(
        json.dumps(
            {
                "timestamp_utc": now_iso,
                "modo": modo_str,
                "ofertas_evaluadas": len(ofertas_activas),
                "outliers_detectados": len(outliers_totales),
                "outliers_marcados_revision": aplicados,
                "csv_backup": str(csv_path),
                "muestra": outliers_totales[:50],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Ejecutamos instrucción: print('\n' + '=' * 74)
    print("\n" + "=" * 74)
    # Ejecutamos instrucción: print(f'AUDITORÍA DE PRECIOS ATÍPICOS ({modo_str.upp...
    print(f"AUDITORÍA DE PRECIOS ATÍPICOS ({modo_str.upper()})")
    # Ejecutamos instrucción: print('=' * 74)
    print("=" * 74)
    # Ejecutamos instrucción: print(f'Ofertas activas en stock evaluadas : {len(of...
    print(f"Ofertas activas en stock evaluadas : {len(ofertas_activas)}")
    # Ejecutamos instrucción: print(f'Outliers detectados : {len(outliers_totales)}')
    print(f"Outliers detectados                : {len(outliers_totales)}")
    # Ejecutamos instrucción: print(f'CSV respaldo : {csv_path}')
    print(f"CSV respaldo                       : {csv_path}")
    # Recorremos iterativamente cada 'ej' en outliers_totales[:12]
    for ej in outliers_totales[:12]:
        # Ejecutamos instrucción: print(f" - #{ej['id']} | {ej['perfume_label']} [{ej[...
        print(
            f"  - #{ej['id']} | {ej['perfume_label']} [{ej['formato']}] | {ej['tienda_nombre']} | "
            f"${ej['precio_actual']:,} (mediana ${ej.get('mediana_referencia', 0):,}) -> {ej['regla_outlier']}"
        )
    # Ejecutamos instrucción: print('=' * 74)
    print("=" * 74)
    # Retornamos el resultado procesado ({'evaluadas': len(ofertas_activas), 'outliers':...)
    return {
        "evaluadas": len(ofertas_activas),
        "outliers": len(outliers_totales),
        "aplicados": aplicados,
        "csv_path": str(csv_path),
    }


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Detección de precios atípicos en ofertas activas.")
    # Asignamos 'grp' con parser.add_mutually_exclusive_group()
    grp = parser.add_mutually_exclusive_group()
    # Ejecutamos instrucción: grp.add_argument('--dry-run', action='store_true', d...
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo detecta y respalda en CSV (por defecto).")
    # Ejecutamos instrucción: grp.add_argument('--apply', action='store_true', hel...
    grp.add_argument("--apply", action="store_true", help="Marca outliers como estado='requiere_revision' en Supabase.")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()
    # Ejecutamos instrucción: ejecutar_deteccion_outliers_bd(apply_changes=bool(ar...
    ejecutar_deteccion_outliers_bd(apply_changes=bool(args.apply))


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()

