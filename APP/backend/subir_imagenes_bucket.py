"""
PerfumeTrending.cl — Sincronizador de Imágenes a Supabase Storage (Bucket IMG_perfumes)
======================================================================================
Script de nivel de producción para:
1. Cargar las imágenes locales de alta resolución desde APP/assets/perfumes/ al bucket IMG_perfumes.
2. Descargar y alojar en el bucket las imágenes externas descubiertas por los scrapers.
3. Actualizar los campos imagen_url en la tabla public.perfumes en Supabase con sus URLs públicas CDN.
"""

# Importación de componentes (datetime) desde el módulo 'datetime'
from datetime import datetime
# Importación de librería estándar o dependencia externa (mimetypes)
import mimetypes
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de componentes (Any, Dict, List, Optional) desde el módulo 'typing'
from typing import Any, Dict, List, Optional
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse

# Importación de librería estándar o dependencia externa (requests)
import requests

# Ajuste de codificación en Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # Ejecutamos instrucción: pass
        pass

# Asignamos 'BASE_DIR' con os.path.dirname(os.path.dirname(os.path.ab...
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)

# Importación de componentes (_fetch_all_rows, get_supabase, get_supabase_credentials, is_supabase_disponible) desde el módulo 'backend.database'
from backend.database import (
    _fetch_all_rows,
    get_supabase,
    get_supabase_credentials,
    is_supabase_disponible,
)

# Asignamos 'BUCKET_NAME' con 'IMG_perfumes'
BUCKET_NAME = "IMG_perfumes"
# Asignamos 'ASSETS_DIR' con os.path.join(BASE_DIR, 'assets', 'perfumes')
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "perfumes")


# Definición de función 'subir_imagenes' sin parámetros externos
def subir_imagenes():
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("❌ Error: No se pudo inicializar el cliente Supabase con service_role. Revisa tus credenciales.")
        # Finalizamos la ejecución de la función retornando None
        return

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    url_base, _ = get_supabase_credentials(prefer_service_role=True)
    # Asignamos 'storage_public_base' con f'{url_base}/storage/v1/object/public/{BUC...
    storage_public_base = f"{url_base}/storage/v1/object/public/{BUCKET_NAME}"

    # Ejecutamos instrucción: print('=' * 65)
    print("=" * 65)
    # Ejecutamos instrucción: print(f'PerfumeTrending — Sincronizador de Imágenes ...
    print(f"PerfumeTrending — Sincronizador de Imágenes a Bucket: {BUCKET_NAME}")
    # Ejecutamos instrucción: print('=' * 65)
    print("=" * 65)

    # Evaluamos la condición lógica (not os.path.exists(ASSETS_DIR)) para controlar el flujo
    if not os.path.exists(ASSETS_DIR):
        # Ejecutamos instrucción: print(f'❌ Directorio de assets no encontrado en: {AS...
        print(f"❌ Directorio de assets no encontrado en: {ASSETS_DIR}")
        # Finalizamos la ejecución de la función retornando None
        return

    # Asignamos 'archivos_locales' con [f for f in os.listdir(ASSETS_DIR) if f.lo...
    archivos_locales = [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    # Ejecutamos instrucción: print(f'📁 Encontradas {len(archivos_locales)} imágen...
    print(f"📁 Encontradas {len(archivos_locales)} imágenes locales en APP/assets/perfumes/")

    # 1. Subir imágenes locales
    mapa_urls_publicas: Dict[str, str] = {}
    # Asignamos 'exitos' con 0
    exitos = 0
    # Asignamos 'errores' con 0
    errores = 0

    # Recorremos iterativamente cada 'archivo' en archivos_locales
    for archivo in archivos_locales:
        # Asignamos 'ruta_completa' con os.path.join(ASSETS_DIR, archivo)
        ruta_completa = os.path.join(ASSETS_DIR, archivo)
        # Asignamos '(mime_type, _)' con mimetypes.guess_type(ruta_completa)
        mime_type, _ = mimetypes.guess_type(ruta_completa)
        # Asignamos 'mime_type' con mime_type or 'image/jpeg'
        mime_type = mime_type or "image/jpeg"

        # Gestión automática de contexto y recursos para: open(ruta_completa, 'rb')
        with open(ruta_completa, "rb") as f:
            # Asignamos 'contenido' con f.read()
            contenido = f.read()

        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Subir con upsert=True para sobrescribir si ya existe
            sb.storage.from_(BUCKET_NAME).upload(
                path=archivo,
                file=contenido,
                file_options={"content-type": mime_type, "upsert": "true"}
            )
            # Asignamos 'url_publica' con f'{storage_public_base}/{archivo}'
            url_publica = f"{storage_public_base}/{archivo}"
            # Asignamos 'mapa_urls_publicas[archivo]' con url_publica
            mapa_urls_publicas[archivo] = url_publica
            # Actualizamos acumulativamente el valor de 'exitos'
            exitos += 1
            # Ejecutamos instrucción: print(f' ✅ Subida exitosa: {archivo} -> {url_publica}')
            print(f"  ✅ Subida exitosa: {archivo} -> {url_publica}")
        except Exception as e:
            # Si da error 403, probablemente falten las políticas RLS en storage.objects
            errores += 1
            # Ejecutamos instrucción: print(f' ⚠️ Error al subir {archivo}: {e}')
            print(f"  ⚠️ Error al subir {archivo}: {e}")

    # Evaluamos la condición lógica (errores > 0 and exitos == 0) para controlar el flujo
    if errores > 0 and exitos == 0:
        # Ejecutamos instrucción: print('\n' + '!' * 65)
        print("\n" + "!" * 65)
        # Ejecutamos instrucción: print('⚠️ AVISO DE POLÍTICA RLS EN STORAGE:')
        print("⚠️ AVISO DE POLÍTICA RLS EN STORAGE:")
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("Supabase Storage requiere una política para permitir la subida de archivos.")
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("Por favor, ejecuta el archivo SQL en el editor de Supabase:")
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("  -> supabase/migrations/20261014000001_storage_policies.sql")
        # Ejecutamos instrucción: print('!' * 65)
        print("!" * 65)
        # Finalizamos la ejecución de la función retornando None
        return

    # 2. Actualizar las URLs en la tabla perfumes para los que usan assets locales (paginado >1.000 filas)
    print("\n🔄 Sincronizando URLs en la tabla 'perfumes' de Supabase...")
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        perfumes = _fetch_all_rows(
            lambda off, lim: (
                sb.table("perfumes")
                .select("id, nombre, imagen_url")
                .order("id", desc=False)
                .range(off, off + lim - 1)
            ),
            page_size=1000,
        )
        # Asignamos 'actualizados' con 0
        actualizados = 0

        # Recorremos iterativamente cada 'p' en perfumes
        for p in perfumes:
            # Asignamos 'p_id' con p['id']
            p_id = p["id"]
            # Asignamos 'img_actual' con p.get('imagen_url', '')
            img_actual = p.get("imagen_url", "")

            # Si la imagen actual apunta a un archivo local
            for nombre_archivo, url_cdn in mapa_urls_publicas.items():
                # Asignamos 'clave_sin_ext' con os.path.splitext(nombre_archivo)[0]
                clave_sin_ext = os.path.splitext(nombre_archivo)[0]
                # Evaluamos la condición lógica (nombre_archivo in img_actual or clave_sin_ext in img...) para controlar el flujo
                if nombre_archivo in img_actual or clave_sin_ext in img_actual:
                    # Evaluamos la condición lógica (img_actual != url_cdn) para controlar el flujo
                    if img_actual != url_cdn:
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        sb.table("perfumes").update({"imagen_url": url_cdn}).eq("id", p_id).execute()
                        # Actualizamos acumulativamente el valor de 'actualizados'
                        actualizados += 1
                        # Ejecutamos instrucción: print(f" ✨ Perfume #{p_id} ({p['nombre']}) actualiza...
                        print(f"  ✨ Perfume #{p_id} ({p['nombre']}) actualizado con CDN: {url_cdn}")
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break

        # Ejecutamos instrucción: print(f'\n📊 Resumen: {exitos} imágenes subidas al bu...
        print(f"\n📊 Resumen: {exitos} imágenes subidas al bucket | {actualizados} perfumes actualizados en Supabase.")

    except Exception as e:
        # Ejecutamos instrucción: print(f'❌ Error actualizando tabla perfumes: {e}')
        print(f"❌ Error actualizando tabla perfumes: {e}")

    # Ejecutamos instrucción: print('=' * 65)
    print("=" * 65)


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: subir_imagenes()
    subir_imagenes()
