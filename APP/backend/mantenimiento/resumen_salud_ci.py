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

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (defaultdict) desde el módulo 'collections'
from collections import defaultdict
# Importación de componentes (datetime, timedelta, timezone) desde el módulo 'datetime'
from datetime import datetime, timedelta, timezone
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de componentes (Any, Dict, List, Optional, ...) desde el módulo 'typing'
from typing import Any, Dict, List, Optional, Tuple

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

# Asignamos 'UMBRAL_ALARMA_EXITO_PCT' con 20.0
UMBRAL_ALARMA_EXITO_PCT = 20.0


# - ¿Qué hace esta función?:
#   Calcula el porcentaje de éxito en vivo de una tienda excluyendo `no_encontrado_en_feed`
#   y `marca_excluida` del denominador, y determina si debe emitirse alarma `< 20 %`.
def evaluar_salud_tienda(nombre_tienda: str, st: Dict[str, Any]) -> Dict[str, Any]:
    # Asignamos 'consultas' con int(st.get('consultas', 0) or 0)
    consultas = int(st.get("consultas", 0) or 0)
    # Asignamos 'exitos' con int(st.get('exitos_en_vivo', 0) or 0)
    exitos = int(st.get("exitos_en_vivo", 0) or 0)
    # Asignamos 'waf' con int(st.get('bloqueos_waf', 0) or 0)
    waf = int(st.get("bloqueos_waf", 0) or 0)
    # Asignamos 'cods' con st.get('fallos_por_codigo') or {}
    cods = st.get("fallos_por_codigo") or {}
    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    no_enc = int(cods.get("no_encontrado_en_feed", 0) or 0)

    # `marca_excluida` no suma a `consultas` (se omite antes de consultar la tienda),
    # mientras que `no_encontrado_en_feed` sí forma parte de `consultas`.
    denominador_efectivo = max(0, consultas - no_enc)
    # Evaluamos la condición lógica (denominador_efectivo == 0) para controlar el flujo
    if denominador_efectivo == 0:
        # Asignamos 'pct_exito' con 100.0 if exitos > 0 else None
        pct_exito = 100.0 if exitos > 0 else None
    else:
        # Asignamos 'pct_exito' con round(exitos * 100.0 / denominador_efectiv...
        pct_exito = round(exitos * 100.0 / denominador_efectivo, 1)

    # Asignamos 'pct_waf' con round(waf * 100.0 / max(1, consultas), 1) ...
    pct_waf = round(waf * 100.0 / max(1, consultas), 1) if consultas > 0 else 0.0
    # Asignamos 'dispara_alarma' con denominador_efectivo >= 5 and pct_exito is...
    dispara_alarma = (
        denominador_efectivo >= 5
        and pct_exito is not None
        and pct_exito < UMBRAL_ALARMA_EXITO_PCT
    )

    # Retornamos el resultado procesado ({'tienda': nombre_tienda, 'consultas': consulta...)
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
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (get_supabase) desde el módulo 'backend.database'
        from backend.database import get_supabase

        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb = get_supabase(use_service_role=True)
        # Evaluamos la condición lógica (not sb) para controlar el flujo
        if not sb:
            # Retornamos el resultado procesado ({})
            return {}
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        tiendas = {int(t["id"]): t["nombre"] for t in (sb.table("tiendas").select("id, nombre").execute().data or [])}
        # Asignamos 'now' con datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        # Asignamos 'c3' con (now - timedelta(days=3)).isoformat()
        c3 = (now - timedelta(days=3)).isoformat()
        # Asignamos 'c7' con (now - timedelta(days=7)).isoformat()
        c7 = (now - timedelta(days=7)).isoformat()

        # Asignamos 'tot' con defaultdict(int)
        tot: Dict[str, int] = defaultdict(int)
        # Asignamos 'gt3' con defaultdict(int)
        gt3: Dict[str, int] = defaultdict(int)
        # Asignamos 'gt7' con defaultdict(int)
        gt7: Dict[str, int] = defaultdict(int)

        # Asignamos 'offset' con 0
        offset = 0
        # Ejecutamos el ciclo mientras se mantenga la condición: True
        while True:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            r = (
                sb.table("ofertas_actuales")
                .select("tienda_id, ultima_verificacion_exitosa")
                .eq("en_stock", True)
                .eq("estado", "activa")
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
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                tn = tiendas.get(int(row["tienda_id"]), str(row["tienda_id"]))
                # Actualizamos acumulativamente el valor de 'tot[tn]'
                tot[tn] += 1
                # Asignamos 'ts' con str(row.get('ultima_verificacion_exitosa')...
                ts = str(row.get("ultima_verificacion_exitosa") or "")
                # Evaluamos la condición lógica (not ts or ts < c3) para controlar el flujo
                if not ts or ts < c3:
                    # Actualizamos acumulativamente el valor de 'gt3[tn]'
                    gt3[tn] += 1
                # Evaluamos la condición lógica (not ts or ts < c7) para controlar el flujo
                if not ts or ts < c7:
                    # Actualizamos acumulativamente el valor de 'gt7[tn]'
                    gt7[tn] += 1
            # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
            if len(batch) < 1000:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # Actualizamos acumulativamente el valor de 'offset'
            offset += 1000

        # Retornamos el resultado procesado ({tn: (tot[tn], gt3[tn], gt7[tn]) for tn in tot})
        return {tn: (tot[tn], gt3[tn], gt7[tn]) for tn in tot}
    except Exception:
        # Retornamos el resultado procesado ({})
        return {}


# - ¿Qué hace esta función?:
#   Construye el bloque Markdown de salud y la lista de anotaciones `::warning::` a partir
#   de un diccionario de reporte de scraping.
def generar_markdown_y_alertas(
    reporte: Dict[str, Any],
    obsolescencia: Optional[Dict[str, Tuple[int, int, int]]] = None,
    shard_label: str = "",
) -> Tuple[str, List[str]]:
    # Asignamos 'obs' con obsolescencia or {}
    obs = obsolescencia or {}
    # Asignamos 'meta' con reporte.get('metadata') or {}
    meta = reporte.get("metadata") or {}
    # Asignamos 'met' con reporte.get('metricas') or {}
    met = reporte.get("metricas") or {}
    # Asignamos 'stats_tiendas' con reporte.get('estadisticas_tiendas') or {}
    stats_tiendas = reporte.get("estadisticas_tiendas") or {}

    # Asignamos 'titulo_shard' con f' (Shard {shard_label})' if shard_label e...
    titulo_shard = f" (Shard {shard_label})" if shard_label else ""
    # Asignamos 'lines' con [f'## Salud del Scraper Nocturno{titulo_sh...
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

    # Asignamos 'warnings_gh' con []
    warnings_gh: List[str] = []
    # Recorremos iterativamente cada 't_nom' en sorted(stats_tiendas.keys())
    for t_nom in sorted(stats_tiendas.keys()):
        # Asignamos 'ev' con evaluar_salud_tienda(t_nom, stats_tiendas[...
        ev = evaluar_salud_tienda(t_nom, stats_tiendas[t_nom])
        # Asignamos 'pct_str' con f"{ev['pct_exito_efectivo']:.1f}%" if ev['...
        pct_str = f"{ev['pct_exito_efectivo']:.1f}%" if ev["pct_exito_efectivo"] is not None else "N/A"
        # Asignamos 'waf_str' con f"{ev['bloqueos_waf']} ({ev['pct_waf']:.0f...
        waf_str = f"{ev['bloqueos_waf']} ({ev['pct_waf']:.0f}%)"
        # Asignamos 'cods_no_cero' con [f'{k}:{v}' for k, v in sorted((ev['fallos...
        cods_no_cero = [f"{k}:{v}" for k, v in sorted((ev["fallos_por_codigo"] or {}).items()) if v]
        # Asignamos 'cods_str' con ', '.join(cods_no_cero[:4]) if cods_no_cer...
        cods_str = ", ".join(cods_no_cero[:4]) if cods_no_cero else "—"
        # Evaluamos la condición lógica (t_nom in obs) para controlar el flujo
        if t_nom in obs:
            # Asignamos '(t_tot, t_3, t_7)' con obs[t_nom]
            t_tot, t_3, t_7 = obs[t_nom]
            # Asignamos 'obs_str' con f'{t_3}/{t_tot} (>7d: {t_7})'
            obs_str = f"{t_3}/{t_tot} (>7d: {t_7})"
        else:
            # Asignamos 'obs_str' con '—'
            obs_str = "—"

        # Asignamos 'icono' con '⚠️ Baja salud' if ev['alarma_baja_salud']...
        icono = "⚠️ Baja salud" if ev["alarma_baja_salud"] else "✅ OK"
        # Ejecutamos instrucción: lines.append(f"| {t_nom} | {ev['consultas']} | {ev['...
        lines.append(
            f"| {t_nom} | {ev['consultas']} | {ev['exitos_en_vivo']} | {pct_str} | {waf_str} | {cods_str} | {obs_str} | {icono} |"
        )
        # Evaluamos la condición lógica (ev['alarma_baja_salud']) para controlar el flujo
        if ev["alarma_baja_salud"]:
            # Ejecutamos instrucción: warnings_gh.append(f"::warning title=Salud baja en {...
            warnings_gh.append(
                f"::warning title=Salud baja en {t_nom}{titulo_shard}::"
                f"Éxito en vivo {pct_str} (< {UMBRAL_ALARMA_EXITO_PCT:.0f}%) sobre {ev['denominador_efectivo']} consultas efectivas "
                f"(WAF={ev['bloqueos_waf']}, códigos={cods_str}). El workflow continúa sin bloquear otros comercios."
            )

    # Asignamos 'outliers_muestra' con reporte.get('outliers_detectados') or []
    outliers_muestra = reporte.get("outliers_detectados") or []
    # Evaluamos la condición lógica (outliers_muestra) para controlar el flujo
    if outliers_muestra:
        # Ejecutamos instrucción: lines.append('')
        lines.append("")
        # Ejecutamos instrucción: lines.append(f'### Muestra de precios atípicos marca...
        lines.append(f"### Muestra de precios atípicos marcados (`requiere_revision`: {len(outliers_muestra)})")
        # Recorremos iterativamente cada 'o' en outliers_muestra[:10]
        for o in outliers_muestra[:10]:
            # Ejecutamos instrucción: lines.append(f"- `{o.get('perfume', '')}` en **{o.ge...
            lines.append(
                f"- `{o.get('perfume', '')}` en **{o.get('tienda', '')}**: `${int(o.get('precio_actual', 0)):,}` ({o.get('motivo_outlier', '')})"
            )

    # Retornamos el resultado procesado (('\n'.join(lines) + '\n', warnings_gh))
    return "\n".join(lines) + "\n", warnings_gh


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Genera resumen Markdown y warnings CI sin fallar el workflow.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--shard", type=str, default="", help="Número de shard (ej. 1..4).")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--report-path", type=str, default="", help="Ruta explícita al JSON de reporte.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--skip-db", action="store_true", help="Omitir consulta de obsolescencia a Supabase.")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'rep_dir' con APP_DIR / 'data' / 'reportes'
        rep_dir = APP_DIR / "data" / "reportes"
        # Evaluamos la condición lógica (args.report_path) para controlar el flujo
        if args.report_path:
            # Asignamos 'rpath' con Path(args.report_path)
            rpath = Path(args.report_path)
        # Evaluamos la condición lógica (args.shard and str(args.shard).strip() not in ('', '0')) para controlar el flujo
        elif args.shard and str(args.shard).strip() not in ("", "0"):
            # Asignamos 'rpath' con rep_dir / f'ultimo_scraping_shard_{str(arg...
            rpath = rep_dir / f"ultimo_scraping_shard_{str(args.shard).strip()}.json"
        else:
            # Asignamos 'rpath' con rep_dir / 'ultimo_scraping.json'
            rpath = rep_dir / "ultimo_scraping.json"

        # Evaluamos la condición lógica (not rpath.exists()) para controlar el flujo
        if not rpath.exists():
            # Asignamos 'msg' con f'## Salud del Scraper\n\nNo se encontró a...
            msg = f"## Salud del Scraper\n\nNo se encontró archivo de reporte en `{rpath}`.\n"
            # Asignamos 'summary_env' con os.environ.get('GITHUB_STEP_SUMMARY')
            summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
            # Evaluamos la condición lógica (summary_env) para controlar el flujo
            if summary_env:
                # Gestión automática de contexto y recursos para: open(summary_env, 'a', encoding='utf-8')
                with open(summary_env, "a", encoding="utf-8") as fs:
                    # Ejecutamos instrucción: fs.write(msg)
                    fs.write(msg)
            # Ejecutamos instrucción: print(msg)
            print(msg)
            # Ejecutamos instrucción: sys.exit(0)
            sys.exit(0)

        # Procesamiento de serialización o deserialización de estructura JSON
        reporte = json.loads(rpath.read_text(encoding="utf-8"))
        # Asignamos 'obs' con {} if args.skip_db else consultar_obsolesc...
        obs = {} if args.skip_db else consultar_obsolescencia_por_tienda()
        # Asignamos '(md, warnings_gh)' con generar_markdown_y_alertas(reporte, obsole...
        md, warnings_gh = generar_markdown_y_alertas(reporte, obsolescencia=obs, shard_label=str(args.shard).strip())

        # Recorremos iterativamente cada 'w' en warnings_gh
        for w in warnings_gh:
            # Ejecutamos instrucción: print(w)
            print(w)

        # Asignamos 'summary_env' con os.environ.get('GITHUB_STEP_SUMMARY')
        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        # Evaluamos la condición lógica (summary_env) para controlar el flujo
        if summary_env:
            # Gestión automática de contexto y recursos para: open(summary_env, 'a', encoding='utf-8')
            with open(summary_env, "a", encoding="utf-8") as fs:
                # Ejecutamos instrucción: fs.write(md)
                fs.write(md)
        else:
            # Ejecutamos instrucción: print(md)
            print(md)
    except Exception as exc:
        # Ejecutamos instrucción: print(f'::warning title=Resumen salud CI::Aviso gene...
        print(f"::warning title=Resumen salud CI::Aviso generando tabla de observabilidad: {exc}")
    # Ejecutamos instrucción: sys.exit(0)
    sys.exit(0)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()

