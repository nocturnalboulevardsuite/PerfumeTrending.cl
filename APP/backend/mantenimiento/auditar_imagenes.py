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

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (ThreadPoolExecutor, as_completed) desde el módulo 'concurrent.futures'
from concurrent.futures import ThreadPoolExecutor, as_completed
# Importación de librería estándar o dependencia externa (csv)
import csv
# Importación de componentes (datetime) desde el módulo 'datetime'
from datetime import datetime
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de componentes (Any, Dict, List, Optional, ...) desde el módulo 'typing'
from typing import Any, Dict, List, Optional, Tuple

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (requests) desde el módulo 'curl_cffi'
    from curl_cffi import requests as curl_requests
except ImportError:
    # Asignamos 'curl_requests' con None
    curl_requests = None

# Importación de librería estándar o dependencia externa (requests)
import requests

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
# Importación de componentes (coincide_entidad_detallada, normalizar_marca_canonica) desde el módulo 'backend.normalizador'
from backend.normalizador import coincide_entidad_detallada, normalizar_marca_canonica
# Importación de componentes (crear_sesion_robusta, precargar_catalogos_bulk_tiendas) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import crear_sesion_robusta, precargar_catalogos_bulk_tiendas

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Asignamos 'logger' con logging.getLogger('AuditarImagenes')
logger = logging.getLogger("AuditarImagenes")

# Asignamos 'BUCKET_IMAGENES' con 'IMG_perfumes'
BUCKET_IMAGENES = "IMG_perfumes"
# Asignamos 'UNSPLASH_PLACEHOLDER_SUBSTR' con 'images.unsplash.com/'
UNSPLASH_PLACEHOLDER_SUBSTR = "images.unsplash.com/"


# - ¿Qué hace esta función?:
#   Verifica si una URL de imagen existe y responde HTTP 200 real (descartando placeholders Unsplash).
def verificar_salud_imagen(url: Optional[str]) -> Tuple[bool, str]:
    # Asignamos 'u' con str(url or '').strip()
    u = str(url or "").strip()
    # Evaluamos la condición lógica (not u) para controlar el flujo
    if not u:
        # Retornamos el resultado procesado ((True, 'vacia_usa_svg_local'))
        return True, "vacia_usa_svg_local"
    # Evaluamos la condición lógica (not u.startswith('http')) para controlar el flujo
    if not u.startswith("http"):
        # Retornamos el resultado procesado ((False, 'protocolo_invalido'))
        return False, "protocolo_invalido"
    # Evaluamos la condición lógica (UNSPLASH_PLACEHOLDER_SUBSTR in u) para controlar el flujo
    if UNSPLASH_PLACEHOLDER_SUBSTR in u:
        # Retornamos el resultado procesado ((False, 'placeholder_unsplash_generico'))
        return False, "placeholder_unsplash_generico"

    # Asignamos 'headers' con {'User-Agent': 'Mozilla/5.0 (Windows NT 10...
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'r' con requests.head(u, headers=headers, timeout=...
        r = requests.head(u, headers=headers, timeout=7, allow_redirects=True)
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Retornamos el resultado procesado ((True, 'ok_200'))
            return True, "ok_200"
        # Evaluamos la condición lógica (r.status_code in (403, 405, 400)) para controlar el flujo
        if r.status_code in (403, 405, 400):
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            rg = requests.get(u, headers=headers, timeout=8, stream=True, allow_redirects=True)
            # Asignamos 'code' con rg.status_code
            code = rg.status_code
            # Ejecutamos instrucción: rg.close()
            rg.close()
            # Evaluamos la condición lógica (code == 200) para controlar el flujo
            if code == 200:
                # Retornamos el resultado procesado ((True, 'ok_200_get'))
                return True, "ok_200_get"
            # Evaluamos la condición lógica (code in (403, 429) and curl_requests is not None) para controlar el flujo
            if code in (403, 429) and curl_requests is not None:
                # Gestión automática de contexto y recursos para: curl_requests.Session(impersonate='chrome120')
                with curl_requests.Session(impersonate="chrome120") as cs:
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    rc = cs.get(u, headers=headers, timeout=8, allow_redirects=True)
                    # Evaluamos la condición lógica (rc.status_code == 200) para controlar el flujo
                    if rc.status_code == 200:
                        # Retornamos el resultado procesado ((True, 'ok_200_cffi'))
                        return True, "ok_200_cffi"
                    # Retornamos el resultado procesado ((False, f'http_{rc.status_code}'))
                    return False, f"http_{rc.status_code}"
            # Retornamos el resultado procesado ((False, f'http_{code}'))
            return False, f"http_{code}"
        # Retornamos el resultado procesado ((False, f'http_{r.status_code}'))
        return False, f"http_{r.status_code}"
    except Exception as exc:
        # Retornamos el resultado procesado ((False, f'err_{type(exc).__name__}'))
        return False, f"err_{type(exc).__name__}"


# - ¿Qué hace esta función?:
#   Busca en los catálogos precargados de las tiendas una imagen válida HTTP 200 que corresponda
#   exactamente a la fragancia auditada.
def buscar_packshot_alternativo(perfume: Dict[str, Any], bulk_catalogs: Dict[str, Any]) -> Optional[str]:
    # Asignamos 'marca' con perfume.get('marca') or ''
    marca = perfume.get("marca") or ""
    # Asignamos 'nombre' con perfume.get('nombre') or ''
    nombre = perfume.get("nombre") or ""
    # Asignamos 'tipo' con perfume.get('tipo') or ''
    tipo = perfume.get("tipo") or ""
    # Asignamos 'm_can' con (normalizar_marca_canonica(marca) or marca...
    m_can = (normalizar_marca_canonica(marca) or marca).strip().lower()

    # Recorremos iterativamente cada '(_t_nom, cat)' en bulk_catalogs.items()
    for _t_nom, cat in bulk_catalogs.items():
        # Asignamos 'candidatos' con cat.por_marca.get(m_can, [])
        candidatos = cat.por_marca.get(m_can, [])
        # Recorremos iterativamente cada 'it' en candidatos
        for it in candidatos:
            # Asignamos 'img_cand' con str(it.get('imagen_url') or '').strip()
            img_cand = str(it.get("imagen_url") or "").strip()
            # Evaluamos la condición lógica (not img_cand.startswith('http') or UNSPLASH_PLACEHOL...) para controlar el flujo
            if not img_cand.startswith("http") or UNSPLASH_PLACEHOLDER_SUBSTR in img_cand:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'res_m' con coincide_entidad_detallada(titulo=it.get('...
            res_m = coincide_entidad_detallada(
                titulo=it.get("title") or "",
                perfume_nombre=nombre,
                marca=marca,
                concentracion=tipo,
                url=it.get("url") or "",
            )
            # Evaluamos la condición lógica (not res_m.coincide) para controlar el flujo
            if not res_m.coincide:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos '(ok, _mot)' con verificar_salud_imagen(img_cand)
            ok, _mot = verificar_salud_imagen(img_cand)
            # Evaluamos la condición lógica (ok and img_cand) para controlar el flujo
            if ok and img_cand:
                # Retornamos el resultado procesado (img_cand)
                return img_cand
    # Retornamos el resultado procesado (None)
    return None


# - ¿Qué hace esta función?:
#   Descarga los bytes de `source_url` y los sube al bucket `IMG_perfumes` de Supabase Storage,
#   retornando la URL pública permanente.
def rehospedar_en_bucket_supabase(sb: Any, perfume_id: int, source_url: str) -> Optional[str]:
    # Asignamos 'headers' con {'User-Agent': 'Mozilla/5.0 (Windows NT 10...
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    # Asignamos 'raw_bytes' con None
    raw_bytes = None
    # Asignamos 'ctype' con 'image/jpeg'
    ctype = "image/jpeg"
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        resp = requests.get(source_url, headers=headers, timeout=12)
        # Evaluamos la condición lógica (resp.status_code != 200 and curl_requests is not None) para controlar el flujo
        if resp.status_code != 200 and curl_requests is not None:
            # Gestión automática de contexto y recursos para: curl_requests.Session(impersonate='chrome120')
            with curl_requests.Session(impersonate="chrome120") as cs:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                resp = cs.get(source_url, headers=headers, timeout=12)
        # Evaluamos la condición lógica (resp.status_code == 200 and resp.content and (len(re...) para controlar el flujo
        if resp.status_code == 200 and resp.content and len(resp.content) > 800:
            # Asignamos 'raw_bytes' con resp.content
            raw_bytes = resp.content
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            ctype = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip().lower()
    except Exception as exc:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"No se pudo descargar packshot alternativo {source_url}: {exc}")
        # Retornamos el resultado procesado (None)
        return None

    # Evaluamos la condición lógica (not raw_bytes) para controlar el flujo
    if not raw_bytes:
        # Retornamos el resultado procesado (None)
        return None

    # Asignamos 'ext' con 'jpg'
    ext = "jpg"
    # Evaluamos la condición lógica ('png' in ctype) para controlar el flujo
    if "png" in ctype:
        # Asignamos 'ext' con 'png'
        ext = "png"
    # Evaluamos la condición lógica ('webp' in ctype) para controlar el flujo
    elif "webp" in ctype:
        # Asignamos 'ext' con 'webp'
        ext = "webp"
    # Asignamos 'storage_path' con f'catalog/perfume_{perfume_id}.{ext}'
    storage_path = f"catalog/perfume_{perfume_id}.{ext}"

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: sb.storage.from_(BUCKET_IMAGENES).upload(path=storag...
        sb.storage.from_(BUCKET_IMAGENES).upload(
            path=storage_path,
            file=raw_bytes,
            file_options={"content-type": ctype, "upsert": "true"},
        )
        # Asignamos 'pub_url' con sb.storage.from_(BUCKET_IMAGENES).get_publ...
        pub_url = sb.storage.from_(BUCKET_IMAGENES).get_public_url(storage_path)
        # Retornamos el resultado procesado (pub_url)
        return pub_url
    except Exception as exc:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Fallo subiendo {storage_path} a {BUCKET_IMAGENES}: {exc}")
        # Retornamos el resultado procesado (None)
        return None


# - ¿Qué hace esta función principal?:
#   Audita las `imagen_url` de todo el catálogo, respalda resultados en CSV y re-hospeda
#   o sanea todas las rotas cuando se invoca con `--apply`.
def ejecutar_auditoria_imagenes(apply_changes: bool = False, workers: int = 24) -> Dict[str, Any]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("No se pudo conectar a Supabase con service_role.")

    # Asignamos 'perfumes' con []
    perfumes: List[Dict[str, Any]] = []
    # Asignamos 'offset' con 0
    offset = 0
    # Ejecutamos el ciclo mientras se mantenga la condición: True
    while True:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        r = sb.table("perfumes").select("id, marca, nombre, tipo, imagen_url").order("id", desc=False).range(offset, offset + 999).execute()
        # Asignamos 'batch' con r.data or []
        batch = r.data or []
        # Evaluamos la condición lógica (not batch) para controlar el flujo
        if not batch:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Ejecutamos instrucción: perfumes.extend(batch)
        perfumes.extend(batch)
        # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
        if len(batch) < 1000:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Actualizamos acumulativamente el valor de 'offset'
        offset += 1000

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Auditando salud HTTP de imágenes en {len(perfumes)} perfumes (workers={workers})...")
    # Asignamos 'rotas' con []
    rotas: List[Tuple[Dict[str, Any], str]] = []
    # Asignamos 'ok_count' con 0
    ok_count = 0

    # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=max(1, workers))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        # Asignamos 'fut_map' con {pool.submit(verificar_salud_imagen, p.get...
        fut_map = {pool.submit(verificar_salud_imagen, p.get("imagen_url")): p for p in perfumes}
        # Recorremos iterativamente cada 'fut' en as_completed(fut_map)
        for fut in as_completed(fut_map):
            # Asignamos 'p' con fut_map[fut]
            p = fut_map[fut]
            # Asignamos '(es_ok, motivo)' con fut.result()
            es_ok, motivo = fut.result()
            # Evaluamos la condición lógica (es_ok) para controlar el flujo
            if es_ok:
                # Actualizamos acumulativamente el valor de 'ok_count'
                ok_count += 1
            else:
                # Ejecutamos instrucción: rotas.append((p, motivo))
                rotas.append((p, motivo))

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Resultado chequeo inicial: sanas={ok_count} | rotas/placeholder={len(rotas)}")

    # Asignamos 'bulk_cats' con {}
    bulk_cats: Dict[str, Any] = {}
    # Evaluamos la condición lógica (rotas) para controlar el flujo
    if rotas:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        tiendas_db = sb.table("tiendas").select("id, nombre, url_base, trust_score").execute().data or []
        # Asignamos 'bulk_cats' con precargar_catalogos_bulk_tiendas(crear_ses...
        bulk_cats = precargar_catalogos_bulk_tiendas(crear_sesion_robusta(), tiendas_db)

    # Asignamos 'registros_csv' con []
    registros_csv: List[Dict[str, Any]] = []
    # Asignamos 'rehospedadas' con 0
    rehospedadas = 0
    # Asignamos 'limpiadas_svg' con 0
    limpiadas_svg = 0

    # Recorremos iterativamente cada '(p, motivo)' en sorted(rotas, key=lambda x: int(x[0]['id']))
    for p, motivo in sorted(rotas, key=lambda x: int(x[0]["id"])):
        # Asignamos 'pid' con int(p['id'])
        pid = int(p["id"])
        # Asignamos 'img_antes' con str(p.get('imagen_url') or '')
        img_antes = str(p.get("imagen_url") or "")
        # Asignamos 'alt_packshot' con buscar_packshot_alternativo(p, bulk_cats) ...
        alt_packshot = buscar_packshot_alternativo(p, bulk_cats) if bulk_cats else None
        # Asignamos 'img_despues' con ''
        img_despues = ""
        # Asignamos 'accion' con 'limpiar_a_svg_local'
        accion = "limpiar_a_svg_local"

        # Evaluamos la condición lógica (alt_packshot) para controlar el flujo
        if alt_packshot:
            # Evaluamos la condición lógica (apply_changes) para controlar el flujo
            if apply_changes:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                hosted = rehospedar_en_bucket_supabase(sb, pid, alt_packshot)
                # Asignamos 'img_despues' con hosted or alt_packshot
                img_despues = hosted or alt_packshot
            else:
                # Asignamos 'img_despues' con alt_packshot
                img_despues = alt_packshot
            # Asignamos 'accion' con 'rehospedar_bucket_img_perfumes'
            accion = "rehospedar_bucket_img_perfumes"

        # Evaluamos la condición lógica (apply_changes) para controlar el flujo
        if apply_changes:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("perfumes").update({"imagen_url": img_despues}).eq("id", pid).execute()
            # Evaluamos la condición lógica (img_despues) para controlar el flujo
            if img_despues:
                # Actualizamos acumulativamente el valor de 'rehospedadas'
                rehospedadas += 1
            else:
                # Actualizamos acumulativamente el valor de 'limpiadas_svg'
                limpiadas_svg += 1

        # Ejecutamos instrucción: registros_csv.append({'perfume_id': pid, 'marca': p....
        registros_csv.append({
            "perfume_id": pid,
            "marca": p.get("marca", ""),
            "nombre": p.get("nombre", ""),
            "motivo_fallo": motivo,
            "accion": accion,
            "imagen_antes": img_antes,
            "imagen_despues": img_despues,
        })

    # Evaluamos la condición lógica (apply_changes and rotas) para controlar el flujo
    if apply_changes and rotas:
        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()

    # Asignamos 'ts' con datetime.now().strftime('%Y%m%d_%H%M%S')
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Asignamos 'modo_str' con 'apply' if apply_changes else 'dry_run'
    modo_str = "apply" if apply_changes else "dry_run"
    # Asignamos 'csv_path' con REPO_ROOT / 'scratch' / 'backups' / f'audi...
    csv_path = REPO_ROOT / "scratch" / "backups" / f"auditoria_imagenes_{modo_str}_{ts}.csv"
    # Ejecutamos instrucción: csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    # Gestión automática de contexto y recursos para: csv_path.open('w', encoding='utf-8', newline='')
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        # Asignamos 'campos' con ['perfume_id', 'marca', 'nombre', 'motivo_...
        campos = ["perfume_id", "marca", "nombre", "motivo_fallo", "accion", "imagen_antes", "imagen_despues"]
        # Asignamos 'w' con csv.DictWriter(f, fieldnames=campos)
        w = csv.DictWriter(f, fieldnames=campos)
        # Ejecutamos instrucción: w.writeheader()
        w.writeheader()
        # Ejecutamos instrucción: w.writerows(registros_csv)
        w.writerows(registros_csv)

    # Ejecutamos instrucción: print('\n' + '=' * 74)
    print("\n" + "=" * 74)
    # Ejecutamos instrucción: print(f'AUDITORÍA DE IMÁGENES DE CATÁLOGO ({modo_str...
    print(f"AUDITORÍA DE IMÁGENES DE CATÁLOGO ({modo_str.upper()})")
    # Ejecutamos instrucción: print('=' * 74)
    print("=" * 74)
    # Ejecutamos instrucción: print(f'Perfumes totales evaluados : {len(perfumes)}')
    print(f"Perfumes totales evaluados : {len(perfumes)}")
    # Ejecutamos instrucción: print(f'Imágenes sanas (200 / SVG) : {ok_count}')
    print(f"Imágenes sanas (200 / SVG) : {ok_count}")
    # Ejecutamos instrucción: print(f'Imágenes rotas/placeholder : {len(rotas)}')
    print(f"Imágenes rotas/placeholder : {len(rotas)}")
    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Ejecutamos instrucción: print(f'Re-hospedadas IMG_perfumes : {rehospedadas}')
        print(f"Re-hospedadas IMG_perfumes : {rehospedadas}")
        # Ejecutamos instrucción: print(f'Saneadas a SVG embebido : {limpiadas_svg}')
        print(f"Saneadas a SVG embebido    : {limpiadas_svg}")
    # Ejecutamos instrucción: print(f'CSV respaldo : {csv_path}')
    print(f"CSV respaldo               : {csv_path}")
    # Ejecutamos instrucción: print('=' * 74)
    print("=" * 74)
    # Retornamos el resultado procesado ({'total': len(perfumes), 'sanas': ok_count, 'ro...)
    return {
        "total": len(perfumes),
        "sanas": ok_count,
        "rotas": len(rotas),
        "rehospedadas": rehospedadas,
        "limpiadas_svg": limpiadas_svg,
        "csv_path": str(csv_path),
    }


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Audita y re-hospeda imágenes rotas en IMG_perfumes.")
    # Asignamos 'grp' con parser.add_mutually_exclusive_group()
    grp = parser.add_mutually_exclusive_group()
    # Ejecutamos instrucción: grp.add_argument('--dry-run', action='store_true', d...
    grp.add_argument("--dry-run", action="store_true", default=True, help="Solo audita y genera CSV (por defecto).")
    # Ejecutamos instrucción: grp.add_argument('--apply', action='store_true', hel...
    grp.add_argument("--apply", action="store_true", help="Re-hospeda en IMG_perfumes y limpia URLs rotas en Supabase.")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--workers", type=int, default=24, help="Hilos HTTP concurrentes.")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()
    # Ejecutamos instrucción: ejecutar_auditoria_imagenes(apply_changes=bool(args....
    ejecutar_auditoria_imagenes(apply_changes=bool(args.apply), workers=args.workers)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()

