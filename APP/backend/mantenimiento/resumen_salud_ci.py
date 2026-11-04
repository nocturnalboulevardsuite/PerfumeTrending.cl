# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Publicador de Salud CI y Alertas No Bloqueantes (Fase 6)
=============================================================================
Se ejecuta al cierre de cada shard en `.github/workflows/scraper_nocturno.yml` (`if: always()`):
  1. Lee el reporte JSON del shard (`ultimo_scraping_shard_<N>.json` o `ultimo_scraping.json`).
  2. Calcula por tienda: consultas efectivas, éxito en vivo %, WAF %, desglose `fallos_por_codigo`
     y obsolescencia actual (>3d / >7d) desde Supabase (si las credenciales están presentes).
  3. Escribe una tabla Markdown completa en `$GITHUB_STEP_SUMMARY` (o stdout si se corre local).
  4. Si una tienda cae bajo el umbral de 20 % de éxito en vivo sobre consultas efectivas
     (excluyendo `no_encontrado_en_feed` y `marca_excluida`), emite una anotación oficial
     `::warning title=...::` de GitHub Actions SIN fallar el job (`exit 0` garantizado).
"""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

UMBRAL_ALARMA_EXITO_PCT = 20.0


# - ¿Qué hace esta función?:
#   Calcula el porcentaje de éxito en vivo de una tienda excluyendo `no_encontrado_en_feed`
#   y `marca_excluida` del denominador, y determina si debe emitirse alarma `< 20 %`.
def evaluar_salud_tienda(nombre_tienda: str, st: Dict[str, Any]) -> Dict[str, Any]:
    consultas = int(st.get("consultas", 0) or 0)
    exitos = int(st.get("exitos_en_vivo", 0) or 0)
    waf = int(st.get("bloqueos_waf", 0) or 0)
    cods = st.get("fallos_por_codigo") or {}
    no_enc = int(cods.get("no_encontrado_en_feed", 0) or 0)

    # `marca_excluida` no suma a `consultas` (se omite antes de consultar la tienda),
    # mientras que `no_encontrado_en_feed` sí forma parte de `consultas`.
    denominador_efectivo = max(0, consultas - no_enc)
    if denominador_efectivo == 0:
        pct_exito = 100.0 if exitos > 0 else None
    else:
        pct_exito = round(exitos * 100.0 / denominador_efectivo, 1)

    pct_waf = round(waf * 100.0 / max(1, consultas), 1) if consultas > 0 else 0.0
    dispara_alarma = (
        denominador_efectivo >= 5
        and pct_exito is not None
        and pct_exito < UMBRAL_ALARMA_EXITO_PCT
    )

    return {
        "tienda": nombre_tienda,
        "consultas": consultas,
        "denominador_efectivo": denominador_efectivo,
        "exitos_en_vivo": exitos,
        "pct_exito_efectivo": pct_exito,
        "bloqueos_waf": waf,
        "pct_waf": pct_waf,
        "fallos_por_codigo": cods,
        "alarma_baja_salud": dispara_alarma,
    }


# - ¿Qué hace esta función?:
#   Consulta de forma ligera en Supabase cuántas ofertas activas en stock por tienda llevan
#   más de 3 y más de 7 días sin verificación exitosa. Si falla, retorna diccionario vacío.
def consultar_obsolescencia_por_tienda() -> Dict[str, Tuple[int, int, int]]:
    try:
        from backend.database import get_supabase

        sb = get_supabase(use_service_role=True)
        if not sb:
            return {}
        tiendas = {int(t["id"]): t["nombre"] for t in (sb.table("tiendas").select("id, nombre").execute().data or [])}
        now = datetime.now(timezone.utc)
        c3 = (now - timedelta(days=3)).isoformat()
        c7 = (now - timedelta(days=7)).isoformat()

        tot: Dict[str, int] = defaultdict(int)
        gt3: Dict[str, int] = defaultdict(int)
        gt7: Dict[str, int] = defaultdict(int)

        offset = 0
        while True:
            r = (
                sb.table("ofertas_actuales")
                .select("tienda_id, ultima_verificacion_exitosa")
                .eq("en_stock", True)
                .eq("estado", "activa")
                .range(offset, offset + 999)
                .execute()
            )
            batch = r.data or []
            if not batch:
                break
            for row in batch:
                tn = tiendas.get(int(row["tienda_id"]), str(row["tienda_id"]))
                tot[tn] += 1
                ts = str(row.get("ultima_verificacion_exitosa") or "")
                if not ts or ts < c3:
                    gt3[tn] += 1
                if not ts or ts < c7:
                    gt7[tn] += 1
            if len(batch) < 1000:
                break
            offset += 1000

        return {tn: (tot[tn], gt3[tn], gt7[tn]) for tn in tot}
    except Exception:
        return {}


# - ¿Qué hace esta función?:
#   Construye el bloque Markdown de salud y la lista de anotaciones `::warning::` a partir
#   de un diccionario de reporte de scraping.
def generar_markdown_y_alertas(
    reporte: Dict[str, Any],
    obsolescencia: Optional[Dict[str, Tuple[int, int, int]]] = None,
    shard_label: str = "",
) -> Tuple[str, List[str]]:
    obs = obsolescencia or {}
    meta = reporte.get("metadata") or {}
    met = reporte.get("metricas") or {}
    stats_tiendas = reporte.get("estadisticas_tiendas") or {}

    titulo_shard = f" (Shard {shard_label})" if shard_label else ""
    lines = [
        f"## Salud del Scraper Nocturno{titulo_shard}",
        "",
        f"- **Estado ETL:** `{meta.get('estado', 'DESCONOCIDO')}` · **Duración:** `{meta.get('duracion_segundos', 0)}s`",
        f"- **Perfumes auditados:** `{met.get('perfumes_auditados', 0)}` / `{met.get('total_perfumes_catalogo', 0)}`",
        f"- **Precios sincronizados:** `{met.get('precios_actualizados', 0)}` (Nuevas: `{met.get('ofertas_nuevas', 0)}` · Outliers marcados: `{met.get('outliers_marcados', 0)}`)",
        "",
        "| Tienda | Consultas | Éxito en vivo | % Éxito (s/ausentes) | WAF 403/429 (%) | Códigos de fallo principales | Stock >3d / >7d | Estado |",
        "|---|---:|---:|---:|---:|---|---:|:---:|",
    ]

    warnings_gh: List[str] = []
    for t_nom in sorted(stats_tiendas.keys()):
        ev = evaluar_salud_tienda(t_nom, stats_tiendas[t_nom])
        pct_str = f"{ev['pct_exito_efectivo']:.1f}%" if ev["pct_exito_efectivo"] is not None else "N/A"
        waf_str = f"{ev['bloqueos_waf']} ({ev['pct_waf']:.0f}%)"
        cods_no_cero = [f"{k}:{v}" for k, v in sorted((ev["fallos_por_codigo"] or {}).items()) if v]
        cods_str = ", ".join(cods_no_cero[:4]) if cods_no_cero else "—"
        if t_nom in obs:
            t_tot, t_3, t_7 = obs[t_nom]
            obs_str = f"{t_3}/{t_tot} (>7d: {t_7})"
        else:
            obs_str = "—"

        icono = "⚠️ Baja salud" if ev["alarma_baja_salud"] else "✅ OK"
        lines.append(
            f"| {t_nom} | {ev['consultas']} | {ev['exitos_en_vivo']} | {pct_str} | {waf_str} | {cods_str} | {obs_str} | {icono} |"
        )
        if ev["alarma_baja_salud"]:
            warnings_gh.append(
                f"::warning title=Salud baja en {t_nom}{titulo_shard}::"
                f"Éxito en vivo {pct_str} (< {UMBRAL_ALARMA_EXITO_PCT:.0f}%) sobre {ev['denominador_efectivo']} consultas efectivas "
                f"(WAF={ev['bloqueos_waf']}, códigos={cods_str}). El workflow continúa sin bloquear otros comercios."
            )

    outliers_muestra = reporte.get("outliers_detectados") or []
    if outliers_muestra:
        lines.append("")
        lines.append(f"### Muestra de precios atípicos marcados (`requiere_revision`: {len(outliers_muestra)})")
        for o in outliers_muestra[:10]:
            lines.append(
                f"- `{o.get('perfume', '')}` en **{o.get('tienda', '')}**: `${int(o.get('precio_actual', 0)):,}` ({o.get('motivo_outlier', '')})"
            )

    return "\n".join(lines) + "\n", warnings_gh


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera resumen Markdown y warnings CI sin fallar el workflow.")
    parser.add_argument("--shard", type=str, default="", help="Número de shard (ej. 1..4).")
    parser.add_argument("--report-path", type=str, default="", help="Ruta explícita al JSON de reporte.")
    parser.add_argument("--skip-db", action="store_true", help="Omitir consulta de obsolescencia a Supabase.")
    args = parser.parse_args()

    try:
        rep_dir = APP_DIR / "data" / "reportes"
        if args.report_path:
            rpath = Path(args.report_path)
        elif args.shard and str(args.shard).strip() not in ("", "0"):
            rpath = rep_dir / f"ultimo_scraping_shard_{str(args.shard).strip()}.json"
        else:
            rpath = rep_dir / "ultimo_scraping.json"

        if not rpath.exists():
            msg = f"## Salud del Scraper\n\nNo se encontró archivo de reporte en `{rpath}`.\n"
            summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary_env:
                with open(summary_env, "a", encoding="utf-8") as fs:
                    fs.write(msg)
            print(msg)
            sys.exit(0)

        reporte = json.loads(rpath.read_text(encoding="utf-8"))
        obs = {} if args.skip_db else consultar_obsolescencia_por_tienda()
        md, warnings_gh = generar_markdown_y_alertas(reporte, obsolescencia=obs, shard_label=str(args.shard).strip())

        for w in warnings_gh:
            print(w)

        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env:
            with open(summary_env, "a", encoding="utf-8") as fs:
                fs.write(md)
        else:
            print(md)
    except Exception as exc:
        print(f"::warning title=Resumen salud CI::Aviso generando tabla de observabilidad: {exc}")
    sys.exit(0)


if __name__ == "__main__":
    main()

