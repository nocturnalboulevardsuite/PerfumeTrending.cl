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

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List

from bs4 import BeautifulSoup
import requests

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import get_supabase
from backend.scraper_periodico import clean_digits, crear_sesion_robusta, obtener_headers_navegador

TIENDAS_OBJETIVO = ("Paris", "Ripley", "Falabella")


# - ¿Qué hace esta función?:
#   Verifica si un HTML HTTP 200 contiene realmente metadatos estructurados de producto
#   (`__NEXT_DATA__` o Schema.org `Product` con precio > 0) y no una página challenge o vacía.
def tiene_payload_producto_valido(tienda: str, html_text: str) -> bool:
    if not html_text or len(html_text) < 500:
        return False
    low = html_text.lower()
    if "just a moment..." in low or "cf-chl-bypass" in low or "attention required! | cloudflare" in low:
        return False

    soup = BeautifulSoup(html_text, "html.parser")
    tag_next = soup.find("script", id="__NEXT_DATA__")
    if tag_next and (tag_next.string or tag_next.text):
        try:
            data = json.loads(tag_next.string or tag_next.text)
            txt = json.dumps(data)
            if "price" in txt.lower() and ("product" in txt.lower() or "variants" in txt.lower()):
                return True
        except Exception:
            pass

    for s_tag in soup.find_all("script", type="application/ld+json"):
        raw = s_tag.string or s_tag.get_text() or ""
        if "Product" in raw and "price" in raw:
            try:
                d = json.loads(raw)
                txt = json.dumps(d)
                if clean_digits(txt) > 0:
                    return True
            except Exception:
                continue
    return False


# - ¿Qué hace esta función?:
#   Obtiene hasta `sample_size` URLs distintas reales por tienda retail desde `ofertas_actuales`.
def obtener_urls_muestra(sample_size: int = 30) -> Dict[str, List[str]]:
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("Supabase no disponible para obtener muestra de URLs retail.")

    tiendas = sb.table("tiendas").select("id, nombre").execute().data or []
    mapa_tiendas = {t["nombre"]: int(t["id"]) for t in tiendas if t["nombre"] in TIENDAS_OBJETIVO}

    resultado: Dict[str, List[str]] = {}
    for t_nom in TIENDAS_OBJETIVO:
        tid = mapa_tiendas.get(t_nom)
        if not tid:
            resultado[t_nom] = []
            continue
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
        urls_unicas: List[str] = []
        vistas = set()
        for r in rows:
            u = str(r.get("url_producto") or "").strip()
            if u.startswith("http") and u not in vistas:
                vistas.add(u)
                urls_unicas.append(u)
        random.Random(42).shuffle(urls_unicas)
        resultado[t_nom] = urls_unicas[:sample_size]
    return resultado


# - ¿Qué hace esta función?:
#   Ejecuta la batería secuencial con jitter para una tienda dada bajo ambos clientes HTTP
#   (`requests` y `curl_cffi(chrome120)`), evitando ráfagas artificiales contra un mismo dominio.
def evaluar_tienda(tienda: str, urls: List[str]) -> List[Dict[str, Any]]:
    referer_map = {
        "Paris": "https://www.paris.cl/",
        "Ripley": "https://simple.ripley.cl/",
        "Falabella": "https://www.falabella.com/falabella-cl",
    }
    referer = referer_map.get(tienda, "https://www.google.cl/")
    resultados_tienda: List[Dict[str, Any]] = []

    clientes = ["requests", "curl_cffi_chrome120"]
    for cliente in clientes:
        if cliente == "requests":
            sess = crear_sesion_robusta(total_retries=1, backoff_factor=0.3)
        else:
            if curl_requests is None:
                continue
            sess = curl_requests.Session(impersonate="chrome120")

        codigos = Counter()
        con_precio_valido = 0
        latencias_ms: List[float] = []

        for u in urls:
            headers = obtener_headers_navegador(referer=referer)
            t0 = time.perf_counter()
            try:
                resp = sess.get(u, headers=headers, timeout=14, allow_redirects=True)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                latencias_ms.append(dt_ms)
                code = int(resp.status_code)
                codigos[str(code)] += 1
                if code == 200 and tiene_payload_producto_valido(tienda, resp.text or ""):
                    con_precio_valido += 1
            except Exception as exc:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                latencias_ms.append(dt_ms)
                codigos[f"ERR:{type(exc).__name__}"] += 1

            time.sleep(random.uniform(0.45, 1.05))

        n_total = max(1, len(urls))
        http_200 = codigos.get("200", 0)
        waf_blocks = codigos.get("403", 0) + codigos.get("429", 0)
        http_404 = codigos.get("404", 0)
        otros = sum(v for k, v in codigos.items() if k not in ("200", "403", "429", "404"))
        lat_prom = round(sum(latencias_ms) / max(1, len(latencias_ms)), 1)

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

    return resultados_tienda


def main() -> None:
    parser = argparse.ArgumentParser(description="Sonda diagnóstica WAF para Paris, Ripley y Falabella.")
    parser.add_argument("--sample", type=int, default=30, help="Cantidad de URLs por tienda (default: 30).")
    args = parser.parse_args()

    muestra = obtener_urls_muestra(sample_size=args.sample)
    filas_resumen: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(evaluar_tienda, t_nom, urls): t_nom for t_nom, urls in muestra.items() if urls}
        for fut in as_completed(futs):
            filas_resumen.extend(fut.result())

    orden_tiendas = {t: i for i, t in enumerate(TIENDAS_OBJETIVO)}
    filas_resumen.sort(key=lambda r: (orden_tiendas.get(r["tienda"], 99), r["cliente"]))

    md_lines = [
        "## Experimento Diagnóstico WAF Retail (`requests` vs `curl_cffi chrome120`)",
        "",
        f"- **Fecha UTC:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"- **Muestra por tienda:** `{args.sample}` URLs activas reales",
        "",
        "| Tienda | Cliente HTTP | URLs | HTTP 200 | Payload Producto Válido | WAF (403/429) | HTTP 404 | Otros/Timeout | Latencia Media |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in filas_resumen:
        md_lines.append(
            f"| {r['tienda']} | `{r['cliente']}` | {r['urls_probadas']} | "
            f"{r['http_200']} ({r['pct_200']}%) | **{r['payload_valido']} ({r['pct_payload_valido']}%)** | "
            f"{r['waf_403_429']} ({r['pct_waf']}%) | {r['http_404']} | {r['otros_errores']} | {r['latencia_media_ms']} ms |"
        )
    md_text = "\n".join(md_lines) + "\n"
    print("\n" + md_text)

    summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_env:
        with open(summary_env, "a", encoding="utf-8") as sf:
            sf.write(md_text)

    reportes_dir = APP_DIR / "data" / "reportes"
    reportes_dir.mkdir(parents=True, exist_ok=True)
    out_json = reportes_dir / "probe_waf.json"
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
    print(f"Reporte JSON guardado en: {out_json}")


if __name__ == "__main__":
    main()
