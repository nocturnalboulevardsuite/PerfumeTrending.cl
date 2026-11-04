# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Auditoría y Re-hospedaje de Imágenes de Catálogo (Fase 6.4)
================================================================================
Verifica mediante `HEAD`/`GET` concurrente todas las `perfumes.imagen_url` de Supabase:
  1. Detecta URLs rotas (`404`, `410`, timeout, no-imagen) o placeholders genéricos de Unsplash.
  2. Para cada perfume con imagen rota/vacía, busca en los feeds vivos de las 13 tiendas
     auditadas (`precargar_catalogos_bulk_tiendas`) una fotografía real verificada con
     `coincide_entidad_detallada` que responda `HTTP 200`.
  3. En modo `--apply`, descarga la imagen válida y la re-hospeda de forma permanente en el
     bucket público de Supabase Storage `IMG_perfumes` (`catalog/perfume_<id>.<ext>`),
     actualizando `perfumes.imagen_url`. Si no existe imagen válida en ninguna tienda, limpia
     la URL rota a `""` para que la UI renderice el SVG embebido limpio (0 enlaces rotos).
  4. Respalda siempre el antes/después en `scratch/backups/auditoria_imagenes_<modo>_<ts>.csv`.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import get_supabase, limpiar_cache_catalogo
from backend.normalizador import coincide_entidad_detallada, normalizar_marca_canonica
from backend.scraper_periodico import crear_sesion_robusta, precargar_catalogos_bulk_tiendas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AuditarImagenes")

BUCKET_IMAGENES = "IMG_perfumes"
UNSPLASH_PLACEHOLDER_SUBSTR = "images.unsplash.com/"


# - ¿Qué hace esta función?:
#   Verifica si una URL de imagen existe y responde HTTP 200 real (descartando placeholders Unsplash).
def verificar_salud_imagen(url: Optional[str]) -> Tuple[bool, str]:
    u = str(url or "").strip()
    if not u:
        return True, "vacia_usa_svg_local"
    if not u.startswith("http"):
        return False, "protocolo_invalido"
    if UNSPLASH_PLACEHOLDER_SUBSTR in u:
        return False, "placeholder_unsplash_generico"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        r = requests.head(u, headers=headers, timeout=7, allow_redirects=True)
        if r.status_code == 200:
            return True, "ok_200"
        if r.status_code in (403, 405, 400):
            rg = requests.get(u, headers=headers, timeout=8, stream=True, allow_redirects=True)
            code = rg.status_code
            rg.close()
            if code == 200:
                return True, "ok_200_get"
            if code in (403, 429) and curl_requests is not None:
                with curl_requests.Session(impersonate="chrome120") as cs:
                    rc = cs.get(u, headers=headers, timeout=8, allow_redirects=True)
                    if rc.status_code == 200:
                        return True, "ok_200_cffi"
                    return False, f"http_{rc.status_code}"
            return False, f"http_{code}"
        return False, f"http_{r.status_code}"
    except Exception as exc:
        return False, f"err_{type(exc).__name__}"


# - ¿Qué hace esta función?:
#   Busca en los catálogos precargados de las tiendas una imagen válida HTTP 200 que corresponda
#   exactamente a la fragancia auditada.
def buscar_packshot_alternativo(perfume: Dict[str, Any], bulk_catalogs: Dict[str, Any]) -> Optional[str]:
    marca = perfume.get("marca") or ""
    nombre = perfume.get("nombre") or ""
    tipo = perfume.get("tipo") or ""
    m_can = (normalizar_marca_canonica(marca) or marca).strip().lower()

    for _t_nom, cat in bulk_catalogs.items():
        candidatos = cat.por_marca.get(m_can, [])
        for it in candidatos:
            img_cand = str(it.get("imagen_url") or "").strip()
            if not img_cand.startswith("http") or UNSPLASH_PLACEHOLDER_SUBSTR in img_cand:
                continue
            res_m = coincide_entidad_detallada(
                titulo=it.get("title") or "",
                perfume_nombre=nombre,
                marca=marca,
                concentracion=tipo,
                url=it.get("url") or "",
            )
            if not res_m.coincide:
                continue
            ok, _mot = verificar_salud_imagen(img_cand)
            if ok and img_cand:
                return img_cand
    return None


# - ¿Qué hace esta función?:
#   Descarga los bytes de `source_url` y los sube al bucket `IMG_perfumes` de Supabase Storage,
#   retornando la URL pública permanente.
def rehospedar_en_bucket_supabase(sb: Any, perfume_id: int, source_url: str) -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    raw_bytes = None
    ctype = "image/jpeg"
    try:
        resp = requests.get(source_url, headers=headers, timeout=12)
        if resp.status_code != 200 and curl_requests is not None:
            with curl_requests.Session(impersonate="chrome120") as cs:
                resp = cs.get(source_url, headers=headers, timeout=12)
        if resp.status_code == 200 and resp.content and len(resp.content) > 800:
            raw_bytes = resp.content
            ctype = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip().lower()
    except Exception as exc:
        logger.warning(f"No se pudo descargar packshot alternativo {source_url}: {exc}")
        return None

    if not raw_bytes:
        return None

    ext = "jpg"
    if "png" in ctype:
        ext = "png"
    elif "webp" in ctype:
        ext = "webp"
    storage_path = f"catalog/perfume_{perfume_id}.{ext}"

    try:
        sb.storage.from_(BUCKET_IMAGENES).upload(
            path=storage_path,
            file=raw_bytes,
            file_options={"content-type": ctype, "upsert": "true"},
        )
        pub_url = sb.storage.from_(BUCKET_IMAGENES).get_public_url(storage_path)
        return pub_url
    except Exception as exc:
        logger.warning(f"Fallo subiendo {storage_path} a {BUCKET_IMAGENES}: {exc}")
        return None


# - ¿Qué hace esta función principal?:
#   Audita las `imagen_url` de todo el catálogo, respalda resultados en CSV y re-hospeda
#   o sanea todas las rotas cuando se invoca con `--apply`.
def ejecutar_auditoria_imagenes(apply_changes: bool = False, workers: int = 24) -> Dict[str, Any]:
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("No se pudo conectar a Supabase con service_role.")

    perfumes: List[Dict[str, Any]] = []
    offset = 0
    while True:
        r = sb.table("perfumes").select("id, marca, nombre, tipo, imagen_url").order("id", desc=False).range(offset, offset + 999).execute()
        batch = r.data or []
        if not batch:
            break
        perfumes.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    logger.info(f"Auditando salud HTTP de imágenes en {len(perfumes)} perfumes (workers={workers})...")
    rotas: List[Tuple[Dict[str, Any], str]] = []
    ok_count = 0

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        fut_map = {pool.submit(verificar_salud_imagen, p.get("imagen_url")): p for p in perfumes}
        for fut in as_completed(fut_map):
            p = fut_map[fut]
            es_ok, motivo = fut.result()
            if es_ok:
                ok_count += 1
            else:
                rotas.append((p, motivo))

    logger.info(f"Resultado chequeo inicial: sanas={ok_count} | rotas/placeholder={len(rotas)}")

    bulk_cats: Dict[str, Any] = {}
    if rotas:
        tiendas_db = sb.table("tiendas").select("id, nombre, url_base, trust_score").execute().data or []
        bulk_cats = precargar_catalogos_bulk_tiendas(crear_sesion_robusta(), tiendas_db)

    registros_csv: List[Dict[str, Any]] = []
    rehospedadas = 0
    limpiadas_svg = 0

    for p, motivo in sorted(rotas, key=lambda x: int(x[0]["id"])):
        pid = int(p["id"])
        img_antes = str(p.get("imagen_url") or "")
        alt_packshot = buscar_packshot_alternativo(p, bulk_cats) if bulk_cats else None
        img_despues = ""
        accion = "limpiar_a_svg_local"

        if alt_packshot:
            if apply_changes:
                hosted = rehospedar_en_bucket_supabase(sb, pid, alt_packshot)
                img_despues = hosted or alt_packshot
            else:
                img_despues = alt_packshot
            accion = "rehospedar_bucket_img_perfumes"

        if apply_changes:
            sb.table("perfumes").update({"imagen_url": img_despues}).eq("id", pid).execute()
            if img_despues:
                rehospedadas += 1
            else:
                limpiadas_svg += 1

        registros_csv.append({
            "perfume_id": pid,
            "marca": p.get("marca", ""),
            "nombre": p.get("nombre", ""),
            "motivo_fallo": motivo,
            "accion": accion,
            "imagen_antes": img_antes,
            "imagen_despues": img_despues,
        })

    if apply_changes and rotas:
        limpiar_cache_catalogo()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    modo_str = "apply" if apply_changes else "dry_run"
    csv_path = REPO_ROOT / "scratch" / "backups" / f"auditoria_imagenes_{modo_str}_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        campos = ["perfume_id", "marca", "nombre", "motivo_fallo", "accion", "imagen_antes", "imagen_despues"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(registros_csv)

    print("\n" + "=" * 74)
    print(f"AUDITORÍA DE IMÁGENES DE CATÁLOGO ({modo_str.upper()})")
    print("=" * 74)
    print(f"Perfumes totales evaluados : {len(perfumes)}")
    print(f"Imágenes sanas (200 / SVG) : {ok_count}")
    print(f"Imágenes rotas/placeholder : {len(rotas)}")
    if apply_changes:
        print(f"Re-hospedadas IMG_perfumes : {rehospedadas}")
        print(f"Saneadas a SVG embebido    : {limpiadas_svg}")
    print(f"CSV respaldo               : {csv_path}")
    print("=" * 74)
    return {
        "total": len(perfumes),
        "sanas": ok_count,
        "rotas": len(rotas),
        "rehospedadas": rehospedadas,
        "limpiadas_svg": limpiadas_svg,
        "csv_path": str(csv_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita y re-hospeda imágenes rotas en IMG_perfumes.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo audita y genera CSV (por defecto).")
    grp.add_argument("--apply", action="store_true", help="Re-hospeda en IMG_perfumes y limpia URLs rotas en Supabase.")
    parser.add_argument("--workers", type=int, default=24, help="Hilos HTTP concurrentes.")
    args = parser.parse_args()
    ejecutar_auditoria_imagenes(apply_changes=bool(args.apply), workers=args.workers)


if __name__ == "__main__":
    main()

