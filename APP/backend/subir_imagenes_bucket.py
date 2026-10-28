"""
PerfumeTrending.cl — Sincronizador de Imágenes a Supabase Storage (Bucket IMG_perfumes)
======================================================================================
Script de nivel de producción para:
1. Cargar las imágenes locales de alta resolución desde APP/assets/perfumes/ al bucket IMG_perfumes.
2. Descargar y alojar en el bucket las imágenes externas descubiertas por los scrapers.
3. Actualizar los campos imagen_url en la tabla public.perfumes en Supabase con sus URLs públicas CDN.
"""

from datetime import datetime
import mimetypes
import os
import sys
from typing import Any, Dict, List, Optional
import urllib.parse

import requests

# Ajuste de codificación en Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import (
    _fetch_all_rows,
    get_supabase,
    get_supabase_credentials,
    is_supabase_disponible,
)

BUCKET_NAME = "IMG_perfumes"
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "perfumes")


def subir_imagenes():
    sb = get_supabase(use_service_role=True)
    if not sb:
        print("❌ Error: No se pudo inicializar el cliente Supabase con service_role. Revisa tus credenciales.")
        return

    url_base, _ = get_supabase_credentials(prefer_service_role=True)
    storage_public_base = f"{url_base}/storage/v1/object/public/{BUCKET_NAME}"

    print("=" * 65)
    print(f"PerfumeTrending — Sincronizador de Imágenes a Bucket: {BUCKET_NAME}")
    print("=" * 65)

    if not os.path.exists(ASSETS_DIR):
        print(f"❌ Directorio de assets no encontrado en: {ASSETS_DIR}")
        return

    archivos_locales = [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    print(f"📁 Encontradas {len(archivos_locales)} imágenes locales en APP/assets/perfumes/")

    # 1. Subir imágenes locales
    mapa_urls_publicas: Dict[str, str] = {}
    exitos = 0
    errores = 0

    for archivo in archivos_locales:
        ruta_completa = os.path.join(ASSETS_DIR, archivo)
        mime_type, _ = mimetypes.guess_type(ruta_completa)
        mime_type = mime_type or "image/jpeg"

        with open(ruta_completa, "rb") as f:
            contenido = f.read()

        try:
            # Subir con upsert=True para sobrescribir si ya existe
            sb.storage.from_(BUCKET_NAME).upload(
                path=archivo,
                file=contenido,
                file_options={"content-type": mime_type, "upsert": "true"}
            )
            url_publica = f"{storage_public_base}/{archivo}"
            mapa_urls_publicas[archivo] = url_publica
            exitos += 1
            print(f"  ✅ Subida exitosa: {archivo} -> {url_publica}")
        except Exception as e:
            # Si da error 403, probablemente falten las políticas RLS en storage.objects
            errores += 1
            print(f"  ⚠️ Error al subir {archivo}: {e}")

    if errores > 0 and exitos == 0:
        print("\n" + "!" * 65)
        print("⚠️ AVISO DE POLÍTICA RLS EN STORAGE:")
        print("Supabase Storage requiere una política para permitir la subida de archivos.")
        print("Por favor, ejecuta el archivo SQL en el editor de Supabase:")
        print("  -> supabase/migrations/20261014000001_storage_policies.sql")
        print("!" * 65)
        return

    # 2. Actualizar las URLs en la tabla perfumes para los que usan assets locales (paginado >1.000 filas)
    print("\n🔄 Sincronizando URLs en la tabla 'perfumes' de Supabase...")
    try:
        perfumes = _fetch_all_rows(
            lambda off, lim: (
                sb.table("perfumes")
                .select("id, nombre, imagen_url")
                .order("id", desc=False)
                .range(off, off + lim - 1)
            ),
            page_size=1000,
        )
        actualizados = 0

        for p in perfumes:
            p_id = p["id"]
            img_actual = p.get("imagen_url", "")

            # Si la imagen actual apunta a un archivo local
            for nombre_archivo, url_cdn in mapa_urls_publicas.items():
                clave_sin_ext = os.path.splitext(nombre_archivo)[0]
                if nombre_archivo in img_actual or clave_sin_ext in img_actual:
                    if img_actual != url_cdn:
                        sb.table("perfumes").update({"imagen_url": url_cdn}).eq("id", p_id).execute()
                        actualizados += 1
                        print(f"  ✨ Perfume #{p_id} ({p['nombre']}) actualizado con CDN: {url_cdn}")
                    break

        print(f"\n📊 Resumen: {exitos} imágenes subidas al bucket | {actualizados} perfumes actualizados en Supabase.")

    except Exception as e:
        print(f"❌ Error actualizando tabla perfumes: {e}")

    print("=" * 65)


if __name__ == "__main__":
    subir_imagenes()
