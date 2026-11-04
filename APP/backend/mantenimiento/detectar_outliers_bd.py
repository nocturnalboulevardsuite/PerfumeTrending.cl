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

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import get_supabase, limpiar_cache_catalogo
from backend.normalizador import detectar_precios_atipicos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("OutliersBD")


# - ¿Qué hace esta función?:
#   Descarga todas las filas de una tabla de Supabase paginando de 1.000 en 1.000.
def _fetch_all(sb: Any, table: str, select: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        r = sb.table(table).select(select).order("id", desc=False).range(offset, offset + 999).execute()
        batch = r.data or []
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return out


# - ¿Qué hace esta función principal?:
#   Evalúa precios atípicos en todo el catálogo activo, guarda respaldo CSV/JSON y,
#   en modo `--apply`, actualiza `estado='requiere_revision'` sobre las ofertas marcadas.
def ejecutar_deteccion_outliers_bd(apply_changes: bool = False) -> Dict[str, Any]:
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("No se pudo conectar a Supabase con service_role.")

    perfumes = {int(p["id"]): p for p in _fetch_all(sb, "perfumes", "id, marca, nombre, tipo")}
    variantes = {int(v["id"]): v for v in _fetch_all(sb, "variantes_perfume", "id, perfume_id, volumen_ml, formato")}
    tiendas = {int(t["id"]): t["nombre"] for t in (sb.table("tiendas").select("id, nombre").execute().data or [])}

    ofertas_activas: List[Dict[str, Any]] = []
    offset = 0
    while True:
        r = (
            sb.table("ofertas_actuales")
            .select("id, variante_id, tienda_id, precio_actual, precio_normal, en_stock, estado, url_producto, ultimo_error")
            .eq("estado", "activa")
            .eq("en_stock", True)
            .order("id", desc=False)
            .range(offset, offset + 999)
            .execute()
        )
        batch = r.data or []
        if not batch:
            break
        ofertas_activas.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    por_perfume_vol: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for o in ofertas_activas:
        v = variantes.get(int(o["variante_id"]))
        if not v:
            continue
        pid = int(v["perfume_id"])
        vol = int(round(float(v.get("volumen_ml") or 100)))
        fmt = str(v.get("formato") or "regular").lower()
        enriq = dict(o)
        enriq["perfume_id"] = pid
        enriq["volumen_ml"] = vol
        enriq["formato"] = fmt
        enriq["tienda_nombre"] = tiendas.get(int(o["tienda_id"]), str(o["tienda_id"]))
        p_info = perfumes.get(pid, {})
        enriq["perfume_label"] = f"{p_info.get('marca', '')} - {p_info.get('nombre', '')} ({vol}ml)"
        por_perfume_vol[(pid, vol)].append(enriq)

    outliers_totales: List[Dict[str, Any]] = []
    for (_pid, _vol), grupo in sorted(por_perfume_vol.items()):
        detectados = detectar_precios_atipicos(grupo)
        outliers_totales.extend(detectados)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    modo_str = "apply" if apply_changes else "dry_run"
    csv_path = REPO_ROOT / "scratch" / "backups" / f"outliers_precios_{modo_str}_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "id", "perfume_id", "perfume_label", "volumen_ml", "formato",
        "tienda_nombre", "precio_actual", "mediana_referencia", "regla_outlier",
        "motivo_outlier", "url_producto",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(outliers_totales)

    now_iso = datetime.now(timezone.utc).isoformat()
    aplicados = 0
    if apply_changes and outliers_totales:
        for out_item in outliers_totales:
            oid = int(out_item["id"])
            motivo_txt = f"[OUTLIER_PRECIO] {out_item['motivo_outlier']}"[:240]
            sb.table("ofertas_actuales").update({
                "estado": "requiere_revision",
                "ultimo_error": motivo_txt,
                "updated_at": now_iso,
            }).eq("id", oid).execute()
            aplicados += 1
        limpiar_cache_catalogo()

    rep_json = APP_DIR / "data" / "reportes" / "ultimos_outliers_precios.json"
    rep_json.parent.mkdir(parents=True, exist_ok=True)
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

    print("\n" + "=" * 74)
    print(f"AUDITORÍA DE PRECIOS ATÍPICOS ({modo_str.upper()})")
    print("=" * 74)
    print(f"Ofertas activas en stock evaluadas : {len(ofertas_activas)}")
    print(f"Outliers detectados                : {len(outliers_totales)}")
    print(f"CSV respaldo                       : {csv_path}")
    for ej in outliers_totales[:12]:
        print(
            f"  - #{ej['id']} | {ej['perfume_label']} [{ej['formato']}] | {ej['tienda_nombre']} | "
            f"${ej['precio_actual']:,} (mediana ${ej.get('mediana_referencia', 0):,}) -> {ej['regla_outlier']}"
        )
    print("=" * 74)
    return {
        "evaluadas": len(ofertas_activas),
        "outliers": len(outliers_totales),
        "aplicados": aplicados,
        "csv_path": str(csv_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detección de precios atípicos en ofertas activas.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo detecta y respalda en CSV (por defecto).")
    grp.add_argument("--apply", action="store_true", help="Marca outliers como estado='requiere_revision' en Supabase.")
    args = parser.parse_args()
    ejecutar_deteccion_outliers_bd(apply_changes=bool(args.apply))


if __name__ == "__main__":
    main()

