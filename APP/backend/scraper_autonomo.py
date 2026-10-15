"""
PerfumeTrending.cl — Motor de Descubrimiento Autónomo de Catálogo (Crawler ETL Cloud)
====================================================================================
Servicio autónomo para el descubrimiento continuo y masivo de fragancias en
comercios auditados de Chile (Silk Perfumes, Elite Perfumes, etc.) sincronizado
directamente con Supabase (PostgreSQL en la nube) y SQLite local.

Capacidades de Ingeniería:
- Rastreo multi-página con límite configurable de productos.
- Extracción de variantes nativas: capacidades (30ml, 50ml, 100ml, 200ml) y precios individuales.
- Deduplicación y normalización inteligente de marcas, nombres y concentraciones.
- Creación automática de nuevos perfumes en el catálogo maestro de Supabase y SQLite.
- Registro de snapshots con cálculo de Precio por Mililitro ($/ml).
- Registro de logs de ejecución en public.scraping_logs en Supabase.
- Generación de informe de auditoría en data/reportes/ultimo_descubrimiento.json.
"""

import argparse
from datetime import datetime
import json
import logging
import os
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Ajuste de codificación en Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CrawlerAutonomo")

# Rutas del sistema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
REPORTES_DIR = os.path.join(BASE_DIR, "data", "reportes")
REPORTE_DESCUBRIMIENTO_PATH = os.path.join(REPORTES_DIR, "ultimo_descubrimiento.json")

# Importación de persistencia y normalización
try:
    from backend.database import (
        get_db_cursor,
        init_db,
        get_supabase,
        is_supabase_disponible,
        registrar_precio
    )
    from backend.normalizador import (
        extraer_volumen_ml,
        extraer_concentracion,
        extraer_genero,
        es_arabe,
        es_producto_perfume_valido,
        limpiar_nombre_perfume
    )
except ImportError:
    from database import (
        get_db_cursor,
        init_db,
        get_supabase,
        is_supabase_disponible,
        registrar_precio
    )
    from normalizador import (
        extraer_volumen_ml,
        extraer_concentracion,
        extraer_genero,
        es_arabe,
        es_producto_perfume_valido,
        limpiar_nombre_perfume
    )

TIENDAS_CRAWLER_CONFIG = [
    {
        "nombre": "Silk Perfumes",
        "url_base": "https://www.silkperfumes.cl",
        "endpoint": "https://www.silkperfumes.cl/products.json",
        "trust_score": 92
    },
    {
        "nombre": "Elite Perfumes",
        "url_base": "https://www.eliteperfumes.cl",
        "endpoint": "https://www.eliteperfumes.cl/products.json",
        "trust_score": 89
    },
    {
        "nombre": "Alisha Perfumes",
        "url_base": "https://alishaperfumes.cl",
        "endpoint": "https://alishaperfumes.cl/products.json",
        "trust_score": 91
    },
    {
        "nombre": "Yauras Perfumes",
        "url_base": "https://yauras.cl",
        "endpoint": "https://yauras.cl/products.json",
        "trust_score": 88
    }
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]


def crear_sesion_robusta() -> requests.Session:
    """Crea una sesión HTTP con reintentos exponenciales y timeouts defensivos."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def obtener_ultimo_reporte_descubrimiento() -> Optional[Dict[str, Any]]:
    """Carga el último informe de descubrimiento autónomo generado."""
    if os.path.exists(REPORTE_DESCUBRIMIENTO_PATH):
        try:
            with open(REPORTE_DESCUBRIMIENTO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def subir_imagen_a_bucket_supabase(
    session: requests.Session,
    img_url: str,
    nombre_perfume: str,
    sb_client: Any
) -> str:
    """
    Descarga la imagen del producto desde la tienda y la sube al bucket IMG_perfumes en Supabase.
    Retorna la URL pública CDN en Supabase Storage.
    Si falla o no hay conexión, retorna la URL original de respaldo sin romper el flujo.
    """
    if not sb_client or not img_url or img_url.startswith("https://miqscdupnknhjemvcjil.supabase.co"):
        return img_url

    try:
        # Generar nombre limpio para el archivo
        slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', nombre_perfume.lower().strip())
        slug = re.sub(r'_+', '_', slug)[:60].strip('_')
        filename = f"{slug}.jpg"

        # Descargar los bytes de la imagen
        resp = session.get(img_url, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 1000:
            content = resp.content
            content_type = resp.headers.get("Content-Type", "image/jpeg")

            # Subir directamente al bucket de Supabase
            sb_client.storage.from_("IMG_perfumes").upload(
                path=filename,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            url_publica = sb_client.storage.from_("IMG_perfumes").get_public_url(filename)
            logger.info(f"📸 Imagen subida y vinculada al bucket IMG_perfumes: {filename}")
            return url_publica
    except Exception as e:
        logger.debug(f"Aviso subiendo imagen a Supabase Storage: {e}")

    return img_url


def guardar_reporte_descubrimiento(reporte: Dict[str, Any]) -> str:
    """Persiste el informe en JSON para auditoría y observabilidad."""
    os.makedirs(REPORTES_DIR, exist_ok=True)
    with open(REPORTE_DESCUBRIMIENTO_PATH, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    return REPORTE_DESCUBRIMIENTO_PATH


def ejecutar_descubrimiento_autonomo(
    limite_por_tienda: int = 20,
    paginas: int = 1
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de rastreo masivo autónomo:
    1. Descarga colecciones públicas JSON de tiendas de perfumería auditadas.
    2. Descarta productos que no sean fragancias (cremas, desodorantes).
    3. Normaliza atributos (marcas, nombres, concentración, género, perfumes árabes).
    4. Deduplica o inserta perfumes nuevos en Supabase (Cloud) y SQLite (Local).
    5. Ingesta snapshots con variantes de tamaño (ml) y precios.
    6. Registra métricas y logs en Supabase y reporte local JSON.
    """
    init_db()
    inicio = time.time()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sb = get_supabase(use_service_role=True)
    supabase_activo = is_supabase_disponible()

    logger.info(f"Iniciando descubrimiento autónomo (límite: {limite_por_tienda} items/tienda, {paginas} páginas)")
    logger.info(f"Destino de persistencia: {'SUPABASE CLOUD + SQLITE' if supabase_activo else 'SQLITE LOCAL'}")

    session = crear_sesion_robusta()
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json"
    }

    total_procesados = 0
    nuevos_perfumes = 0
    precios_registrados = 0
    descartados_no_perfume = 0
    errores: List[str] = []
    muestras_descubiertas: List[Dict[str, Any]] = []

    # Mapas de tiendas y perfumes en Supabase
    sb_tiendas_map: Dict[str, int] = {}
    sb_perfumes_conocidos: Dict[str, int] = {}

    if supabase_activo and sb:
        try:
            res_t = sb.table("tiendas").select("id, nombre").execute()
            for r in res_t.data or []:
                sb_tiendas_map[r["nombre"].lower()] = r["id"]

            res_p = sb.table("perfumes").select("id, nombre").execute()
            for r in res_p.data or []:
                sb_perfumes_conocidos[r["nombre"].strip().lower()] = r["id"]
        except Exception as e:
            logger.warning(f"Error cargando caché inicial desde Supabase: {e}")

    with get_db_cursor(commit=True) as cursor:
        # Obtener mapeo de tiendas en SQLite
        cursor.execute("SELECT id, nombre FROM tiendas;")
        sqlite_tiendas_map = {r["nombre"].lower(): r["id"] for r in cursor.fetchall()}

        for tienda_cfg in TIENDAS_CRAWLER_CONFIG:
            t_nombre = tienda_cfg["nombre"]
            t_url_base = tienda_cfg["url_base"]
            t_endpoint = tienda_cfg["endpoint"]
            t_key = t_nombre.lower()

            # Asegurar tienda en Supabase
            t_id_supabase = sb_tiendas_map.get(t_key)
            if not t_id_supabase and supabase_activo and sb:
                try:
                    ins_t = sb.table("tiendas").upsert({
                        "nombre": t_nombre,
                        "url_base": t_url_base,
                        "trust_score": tienda_cfg["trust_score"],
                        "badge": "Tienda Verificada",
                        "logo_emoji": ""
                    }, on_conflict="nombre").execute()
                    if ins_t.data:
                        t_id_supabase = ins_t.data[0]["id"]
                        sb_tiendas_map[t_key] = t_id_supabase
                except Exception as e:
                    logger.warning(f"Error asegurando tienda {t_nombre} en Supabase: {e}")

            # Asegurar tienda en SQLite
            t_id_sqlite = sqlite_tiendas_map.get(t_key)
            if not t_id_sqlite:
                cursor.execute("""
                INSERT OR IGNORE INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
                VALUES (?, ?, ?, 'Tienda Verificada', '');
                """, (t_nombre, t_url_base, tienda_cfg["trust_score"]))
                cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = ?;", (t_key,))
                row_t = cursor.fetchone()
                t_id_sqlite = row_t["id"] if row_t else 1
                sqlite_tiendas_map[t_key] = t_id_sqlite

            logger.info(f"Rastreando catálogo de: {t_nombre}...")

            for pag in range(1, paginas + 1):
                params = {"limit": limite_por_tienda, "page": pag}
                try:
                    res = session.get(t_endpoint, params=params, headers=headers, timeout=12)
                    if res.status_code != 200:
                        logger.warning(f"Respuesta HTTP {res.status_code} en {t_nombre} (pág {pag})")
                        continue

                    data = res.json()
                    productos = data.get("products", [])
                    if not productos:
                        break

                    for prod in productos:
                        total_procesados += 1
                        raw_title = prod.get("title", "")
                        raw_vendor = (prod.get("vendor", "") or "").strip()
                        tags = prod.get("tags", [])

                        # 1. Filtro estricto de productos que no son fragancias
                        if not es_producto_perfume_valido(raw_title, tags):
                            descartados_no_perfume += 1
                            continue

                        # 2. Normalización de atributos
                        marca = raw_vendor if len(raw_vendor) > 1 else "Diseñador"
                        nombre_limpio = limpiar_nombre_perfume(raw_title, marca)
                        concentracion = extraer_concentracion(raw_title)
                        genero = extraer_genero(raw_title)
                        arabe_flag = 1 if es_arabe(marca, nombre_limpio) else 0

                        # Imagen
                        images = prod.get("images", [])
                        img_url = images[0].get("src", "") if images else "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
                        url_producto = f"{t_url_base}/products/{prod.get('handle', '')}"

                        variants = prod.get("variants", [])
                        if not variants:
                            continue

                        primer_precio = int(float(variants[0].get("price", 0)))
                        if primer_precio <= 0:
                            continue

                        nombre_key = nombre_limpio.strip().lower()
                        es_nuevo = False

                        # -----------------------------------------------------
                        # 3. GESTIÓN DEL PERFUME EN SUPABASE
                        # -----------------------------------------------------
                        perfume_id_sb = sb_perfumes_conocidos.get(nombre_key)
                        if not perfume_id_sb and supabase_activo and sb:
                            try:
                                # Verificar existencia en Supabase
                                chk_p = sb.table("perfumes").select("id").ilike("nombre", nombre_limpio).execute()
                                if chk_p.data:
                                    perfume_id_sb = chk_p.data[0]["id"]
                                else:
                                    # Subir la foto del perfume al bucket IMG_perfumes en Supabase
                                    img_url_cdn = subir_imagen_a_bucket_supabase(
                                        session=session,
                                        img_url=img_url,
                                        nombre_perfume=nombre_limpio,
                                        sb_client=sb if supabase_activo else None
                                    )

                                    # Insertar nuevo perfume en Supabase con su URL CDN
                                    nuevo_p = sb.table("perfumes").insert({
                                        "nombre": nombre_limpio,
                                        "marca": marca,
                                        "genero": genero,
                                        "tipo": concentracion,
                                        "notas": "Notas aromáticas exclusivas",
                                        "imagen_url": img_url_cdn,
                                        "es_arabe": bool(arabe_flag),
                                        "en_tendencia": True,
                                        "en_remate": False,
                                        "precio_referencia": primer_precio
                                    }).execute()
                                    if nuevo_p.data:
                                        perfume_id_sb = nuevo_p.data[0]["id"]
                                        es_nuevo = True

                                if perfume_id_sb:
                                    sb_perfumes_conocidos[nombre_key] = perfume_id_sb
                            except Exception as e:
                                logger.warning(f"Error guardando perfume {nombre_limpio} en Supabase: {e}")

                        # -----------------------------------------------------
                        # 4. GESTIÓN DEL PERFUME EN SQLITE
                        # -----------------------------------------------------
                        cursor.execute("""
                        SELECT id, precio_referencia FROM perfumes 
                        WHERE LOWER(nombre) = ? OR LOWER(nombre) LIKE ?;
                        """, (nombre_key, f"%{nombre_key}%"))
                        row_sqlite = cursor.fetchone()

                        if row_sqlite:
                            perfume_id_sqlite = row_sqlite["id"]
                        else:
                            cursor.execute("""
                            INSERT INTO perfumes (
                                nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia
                            )
                            VALUES (?, ?, ?, ?, 'Notas aromáticas exclusivas', ?, ?, 1, 0, ?);
                            """, (nombre_limpio, marca, genero, concentracion, img_url, arabe_flag, primer_precio))
                            perfume_id_sqlite = cursor.lastrowid
                            es_nuevo = True

                        if es_nuevo:
                            nuevos_perfumes += 1
                            muestras_descubiertas.append({
                                "nombre": nombre_limpio,
                                "marca": marca,
                                "tipo": concentracion,
                                "es_arabe": bool(arabe_flag),
                                "tienda": t_nombre,
                                "precio": primer_precio
                            })
                            logger.info(f"✨ ¡NUEVO PERFUME DESCUBIERTO!: {nombre_limpio} ({marca}) - ${primer_precio:,}")

                        # -----------------------------------------------------
                        # 5. INGESTA DE VARIANTES Y PRECIOS POR VOLUMEN ML
                        # -----------------------------------------------------
                        for v in variants:
                            v_price = int(float(v.get("price", 0)))
                            if v_price <= 0:
                                continue

                            v_compare = int(float(v.get("compare_at_price") or v_price))
                            v_stock = 1 if v.get("available", True) else 0
                            v_title = v.get("title", "")
                            volumen_ml = extraer_volumen_ml(f"{raw_title} {v_title}")

                            # Registrar en Supabase
                            if supabase_activo and sb and perfume_id_sb and t_id_supabase:
                                try:
                                    sb.table("precios_registro").insert({
                                        "perfume_id": perfume_id_sb,
                                        "tienda_id": t_id_supabase,
                                        "precio_actual": v_price,
                                        "precio_normal": v_compare,
                                        "en_stock": bool(v_stock),
                                        "volumen_ml": volumen_ml,
                                        "url_producto": url_producto,
                                        "fecha_registro": ahora
                                    }).execute()
                                except Exception as e:
                                    logger.debug(f"Aviso guardando variante en Supabase: {e}")

                            # Registrar en SQLite
                            cursor.execute("""
                            INSERT INTO precios_registro (
                                perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                            """, (perfume_id_sqlite, t_id_sqlite, v_price, v_compare, v_stock, volumen_ml, url_producto, ahora))

                            precios_registrados += 1

                except Exception as e:
                    err_msg = f"Fallo procesando {t_nombre} página {pag}: {e}"
                    logger.error(err_msg)
                    errores.append(err_msg)

                time.sleep(0.5)

    duracion = round(time.time() - inicio, 2)
    estado = "EXITOSO" if not errores else ("DEGRADADO" if precios_registrados > 0 else "FALLIDO")

    # Registrar log de auditoría en Supabase
    if supabase_activo and sb:
        try:
            sb.table("scraping_logs").insert({
                "tipo_scraper": "Descubrimiento Autónomo",
                "tienda_nombre": "Silk Perfumes & Elite Perfumes",
                "productos_procesados": total_procesados,
                "productos_nuevos": nuevos_perfumes,
                "precios_actualizados": precios_registrados,
                "estado": estado,
                "mensaje_detalle": f"Rastreo autónomo: {nuevos_perfumes} nuevos perfumes, {precios_registrados} variantes en {duracion}s",
                "fecha_ejecucion": ahora
            }).execute()
        except Exception as e:
            logger.debug(f"No se pudo guardar scraping_log en Supabase: {e}")

    reporte = {
        "metadata": {
            "version": "2.0.0 (Cloud Supabase)",
            "sistema": "PerfumeTrending Autonomous Discovery Crawler",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado,
            "destino": "Supabase PostgreSQL + SQLite"
        },
        "metricas": {
            "total_productos_analizados": total_procesados,
            "descartados_no_perfume": descartados_no_perfume,
            "nuevos_perfumes_descubiertos": nuevos_perfumes,
            "precios_variantes_registrados": precios_registrados,
            "errores_totales": len(errores)
        },
        "muestras_nuevas": muestras_descubiertas[:15],
        "errores": errores
    }

    guardar_reporte_descubrimiento(reporte)
    logger.info(f"Ciclo completado en {duracion}s | {nuevos_perfumes} perfumes nuevos descubiertos | {precios_registrados} precios registrados.")
    return reporte


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Autónomo de Perfumes (PerfumeTrending.cl)")
    parser.add_argument("--limit", type=int, default=25, help="Límite de productos por tienda (default: 25)")
    parser.add_argument("--pages", type=int, default=1, help="Páginas a rastrear por tienda (default: 1)")
    args = parser.parse_args()

    resultado = ejecutar_descubrimiento_autonomo(limite_por_tienda=args.limit, paginas=args.pages)
    print("\n" + "=" * 60)
    print("RESUMEN DE DESCUBRIMIENTO AUTÓNOMO EN SUPABASE & SQLITE:")
    print(f"Estado: {resultado['metadata']['estado']}")
    print(f"Productos analizados: {resultado['metricas']['total_productos_analizados']}")
    print(f"Nuevos perfumes descubiertos: {resultado['metricas']['nuevos_perfumes_descubiertos']}")
    print(f"Precios/Variantes registradas: {resultado['metricas']['precios_variantes_registrados']}")
    print(f"Duración: {resultado['metadata']['duracion_segundos']}s")
    print("=" * 60)
