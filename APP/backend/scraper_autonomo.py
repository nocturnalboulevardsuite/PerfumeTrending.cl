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
import html
from datetime import datetime
import json
import logging
import os
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

# - ¿Qué hace esta función?:
#   1. Extrae dígitos puros de un valor textual o numérico sucio (e.g. \'$59.990 CLP\' -> 59990).
#   2. Devuelve 0 entero seguro ante valores None o textos sin caracteres numéricos.

def clean_digits(val: Any) -> int:
    if val is None:
        return 0
    s = re.sub(r'[^\d]', '', str(val))
    return int(s) if s else 0

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
        finalizar_scraping_run,
        get_db_cursor,
        init_db,
        iniciar_scraping_run,
        get_supabase,
        is_supabase_disponible,
        registrar_precio,
        registrar_observacion_oferta,
    guardar_o_actualizar_perfume_scraped,
    )
    from backend.normalizador import (
        CANONICAL_BRAND_MAP,
        MARCAS_INVALIDAS_CATALOGO,
        detectar_formato_oferta,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_concentracion,
        extraer_genero,
        extraer_volumen_ml,
        limpiar_nombre_perfume,
        normalizar_marca_canonica,
    )
except ImportError:
    from database import (
        finalizar_scraping_run,
        get_db_cursor,
        init_db,
        iniciar_scraping_run,
        get_supabase,
        is_supabase_disponible,
        registrar_precio,
        registrar_observacion_oferta,
    guardar_o_actualizar_perfume_scraped,
    )
    from normalizador import (
        CANONICAL_BRAND_MAP,
        MARCAS_INVALIDAS_CATALOGO,
        detectar_formato_oferta,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_concentracion,
        extraer_genero,
        extraer_volumen_ml,
        limpiar_nombre_perfume,
        normalizar_marca_canonica,
    )

# =============================================================================
# BLOQUE 1: CONFIGURACIÓN DE TIENDAS AUDITADAS Y ENDPOINTS SHOPIFY
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Define las tiendas especializadas chilenas que utilizan el motor Shopify y exponen
# legalmente su catálogo público mediante el endpoint `/products.json`.
# Permite descubrir perfumes masivamente con sus variantes de volumen (ml) y precios.
# =============================================================================
TIENDAS_CRAWLER_CONFIG = [
    {
        "nombre": "Silk Perfumes",
        "url_base": "https://www.silkperfumes.cl",
        "endpoint": "https://www.silkperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 92
    },
    {
        "nombre": "Elite Perfumes",
        "url_base": "https://www.eliteperfumes.cl",
        "endpoint": "https://www.eliteperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 89
    },
    {
        "nombre": "Alisha Perfumes",
        "url_base": "https://alishaperfumes.cl",
        "endpoint": "https://alishaperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 91
    },
    {
        "nombre": "Yauras Perfumes",
        "url_base": "https://yauras.cl",
        "endpoint": "https://yauras.cl/products.json",
        "tipo": "shopify",
        "trust_score": 88
    },
    {
        "nombre": "Oferta Perfumes",
        "url_base": "https://ofertaperfumes.cl",
        "endpoint": "https://ofertaperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    {
        "nombre": "L'Odoro",
        "url_base": "https://www.lodoro.cl",
        "endpoint": "https://www.lodoro.cl/products.json",
        "tipo": "shopify",
        "trust_score": 92
    },
    {
        "nombre": "Chile Perfume",
        "url_base": "https://www.chileperfume.cl",
        "endpoint": "https://www.chileperfume.cl/wp-json/wc/store/v1/products",
        "tipo": "woocommerce",
        "trust_score": 91
    },
    {
        "nombre": "Mundo Aromas",
        "url_base": "https://mundoaromas.cl",
        "endpoint": "https://mundoaromas.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    {
        "nombre": "Cosmetic",
        "url_base": "https://cosmetic.cl",
        "endpoint": "https://cosmetic.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    {
        "nombre": "Fragante",
        "url_base": "https://fragante.cl",
        "endpoint": "https://fragante.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    {
        "nombre": "ComprarEnChile",
        "url_base": "https://comprarenchile.cl",
        "endpoint": "https://comprarenchile.cl/products.json",
        "tipo": "shopify",
        "trust_score": 88
    },
    {
        "nombre": "Portal del Perfume",
        "url_base": "https://portaldelperfume.cl",
        "endpoint": "https://portaldelperfume.cl/wp-json/wc/store/v1/products",
        "tipo": "woocommerce",
        "trust_score": 89
    },
    {
        "nombre": "Aromata",
        "url_base": "https://www.aromata.cl",
        "endpoint": "https://www.aromata.cl/wp-json/wc/store/v1/products",
        "tipo": "woocommerce",
        "trust_score": 89
    }
]

# Lista rotativa de User-Agents estándar para no ser bloqueados por firewalls perimetrales
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]


# =============================================================================
# BLOQUE 2: CONEXIÓN HTTP RESILIENTE CON REINTENTOS EXPONENCIALES
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Configura un cliente HTTP con connection pooling (10 conexiones activas, max 20)
# y reintentos automáticos con retroceso exponencial (Backoff) ante errores 429
# (Too Many Requests) o 5xx (Server Error), previniendo caídas del crawler.
# =============================================================================
# - ¿Qué hace esta función?:
#   1. Instancia una sesión requests con Connection Pooling (10 conexiones reutilizables, hasta 20 concurrentes).
#   2. Configura reintentos exponenciales con \'urllib3.util.Retry\' ante errores 5xx o 429 (Too Many Requests).
#   3. Evita que caídas momentáneas o congestión de internet detengan el rastreo autónomo.

def crear_sesion_robusta() -> requests.Session:
    """Crea una sesión HTTP con reintentos exponenciales y timeouts defensivos."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# - ¿Qué hace esta función?:
#   1. Carga desde disco el archivo JSON 'data/reportes/ultimo_descubrimiento.json' (o ruta personalizada).
#   2. Retorna un diccionario con las métricas del último ciclo de auto-descubrimiento o None si no existe.
def obtener_ultimo_reporte_descubrimiento(ruta_destino: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Carga el último informe de descubrimiento autónomo generado en disco."""
    target = ruta_destino or REPORTE_DESCUBRIMIENTO_PATH
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# =============================================================================
# BLOQUE 3: ALMACENAMIENTO DE ASSETS EN LA NUBE (SUPABASE STORAGE CDN)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Descarga los bytes de la fotografía del perfume desde la tienda de origen y la
# sube directamente al bucket `IMG_perfumes` en Supabase Storage, devolviendo una URL
# pública permanente servida por CDN.
# ¿POR QUÉ SE HACE ASÍ?
# Evita que las imágenes se rompan si la tienda externa cambia su URL o la borra.
# Si la subida falla, mantiene la URL original como respaldo sin interrumpir el proceso.
# =============================================================================
# - ¿Qué hace esta función?:
#   1. Descarga la imagen del producto desde la tienda de origen mediante HTTP GET.
#   2. Genera un slug limpio y seguro para el nombre de archivo dentro del bucket.
#   3. Sube los bytes binarios al bucket \'IMG_perfumes\' en Supabase Storage con flag upsert=True.
#   4. Retorna la URL pública CDN permanente de Supabase para evitar enlaces rotos si la tienda externa cambia su web.

def subir_imagen_a_bucket_supabase(
    session: requests.Session,
    img_url: str,
    nombre_perfume: str,
    sb_client: Any
) -> str:
    """
    Descarga la imagen del producto desde la tienda y la sube al bucket IMG_perfumes en Supabase.
    Retorna la URL pública CDN en Supabase Storage.
    """
    if not sb_client or not img_url or img_url.startswith("https://miqscdupnknhjemvcjil.supabase.co"):
        return img_url

    try:
        # Generar nombre limpio (slug) para el archivo en el bucket
        slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', nombre_perfume.lower().strip())
        slug = re.sub(r'_+', '_', slug)[:60].strip('_')
        filename = f"{slug}.jpg"

        # Descargar los bytes de la imagen
        resp = session.get(img_url, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 1000:
            content = resp.content
            content_type = resp.headers.get("Content-Type", "image/jpeg")

            # Subir directamente al bucket de Supabase con sobrescritura permitida
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


# - ¿Qué hace esta función?:
#   1. Asegura que el directorio 'data/reportes' exista en el entorno de ejecución.
#   2. Serializa el diccionario del informe en JSON con codificación UTF-8 e indentación legible.
#   3. Permite especificar una ruta de destino alternativa para auditoría y pruebas unitarias.
def guardar_reporte_descubrimiento(reporte: Dict[str, Any], ruta_destino: Optional[str] = None) -> str:
    """Persiste el informe en JSON para auditoría y observabilidad del sistema."""
    destino = ruta_destino or REPORTE_DESCUBRIMIENTO_PATH
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    return destino


# =============================================================================
# BLOQUE 4: MOTOR PRINCIPAL DE CRAWLING Y PIPELINE ETL AUTÓNOMO
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Orquesta el proceso completo de extracción, transformación y carga (ETL):
# 1. Extracción (E): Itera por las tiendas consultando su API JSON de productos paginada.
# 2. Filtrado: Utiliza `es_producto_perfume_valido()` para descartar cremas, shampoos y testers.
# 3. Transformación (T): Limpia el nombre, normaliza marca, concentración (EDP/EDT),
#    género (Hombre/Mujer/Unisex) y detecta si es tendencia árabe.
# 4. Deduplicación: Compara contra los perfumes ya conocidos en Supabase y SQLite.
#    Si es un perfume nuevo, lo crea e inserta automáticamente.
# 5. Carga (L): Para cada variante encontrada (ej. 50ml, 100ml, 200ml), invoca la función
#    transaccional `registrar_observacion_oferta()` para registrar la oferta viva y el historial.
# =============================================================================
# - ¿Qué hace esta función?:
#   1. Orquesta el ciclo de crawling masivo multi-tienda y multi-página (Shopify / WooCommerce).
#   2. Aplica el escudo estricto de control de calidad: descarta clones, cosméticos, cremas y frascos < 25ml.
#   3. Normaliza marca canónica, limpia el nombre y deduce concentración, género y tendencia árabe.
#   4. Comprueba en Supabase y SQLite si la fragancia ya existe antes de registrar un nuevo perfume.
#   5. Ingiere variantes de volumen y precios con \'registrar_observacion_oferta\'.
#   6. Guarda el informe de auditoría en \'ultimo_descubrimiento.json\' y registra logs en \'scraping_logs\'.

def ejecutar_descubrimiento_autonomo(
    limite_por_tienda: int = 250,
    paginas: int = 2,
    subir_imagenes: bool = False,
    filtro_tiendas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de rastreo masivo autónomo en comercios especializados.
    Optimizado para alta concurrencia y volumen masivo (cientos/miles de productos).
    """
    init_db()
    inicio = time.time()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sb = get_supabase(use_service_role=True)
    supabase_activo = is_supabase_disponible()

    logger.info(f"Iniciando descubrimiento autónomo masivo (límite: {limite_por_tienda} items/página, {paginas} páginas)")
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

    run_id = iniciar_scraping_run(
        tipo_scraper="Descubrimiento Autónomo Multitienda",
        mensaje_detalle=f"Rastreo masivo ({paginas} páginas/tienda, límite {limite_por_tienda})",
    )

    def _perfume_canon_key(m_raw: str, n_raw: str, c_raw: str, g_raw: str = "") -> Tuple[str, str, str, str]:
        m_c = (normalizar_marca_canonica(m_raw) or "Diseñador").strip().lower()
        n_c = (limpiar_nombre_perfume(n_raw, m_raw) or n_raw or "").strip().lower()
        c_c = (c_raw or "Eau de Parfum").strip().lower()
        g_c = (g_raw or extraer_genero(n_raw) or "Unisex").strip().lower()
        return (m_c, n_c, c_c, g_c)

    sb_tiendas_map: Dict[str, int] = {}
    sb_perfumes_conocidos: Dict[Tuple[str, str, str, str], int] = {}
    sb_variantes_conocidas: Dict[Tuple[int, int, str], int] = {}

    if supabase_activo and sb:
        try:
            res_t = sb.table("tiendas").select("id, nombre").execute()
            for r in res_t.data or []:
                sb_tiendas_map[r["nombre"].lower()] = r["id"]

            offset = 0
            while True:
                res_p = sb.table("perfumes").select("id, marca, nombre, tipo, genero").range(offset, offset + 999).execute()
                if not res_p.data:
                    break
                for r in res_p.data:
                    ck = _perfume_canon_key(r.get("marca") or "", r.get("nombre") or "", r.get("tipo") or "", r.get("genero") or "")
                    sb_perfumes_conocidos[ck] = r["id"]
                if len(res_p.data) < 1000:
                    break
                offset += 1000

            offset_v = 0
            while True:
                res_v = sb.table("variantes_perfume").select("id, perfume_id, volumen_ml, formato").range(offset_v, offset_v + 999).execute()
                if not res_v.data:
                    break
                for r in res_v.data:
                    try:
                        v_ml = int(round(float(r["volumen_ml"])))
                        v_fmt = str(r.get("formato") or "regular").lower()
                        sb_variantes_conocidas[(r["perfume_id"], v_ml, v_fmt)] = r["id"]
                    except Exception:
                        pass
                if len(res_v.data) < 1000:
                    break
                offset_v += 1000

            logger.info(f"Caché Supabase inicializada: {len(sb_perfumes_conocidos)} perfumes, {len(sb_variantes_conocidas)} variantes.")
        except Exception as e:
            logger.warning(f"Error cargando caché inicial desde Supabase: {e}")

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id, nombre FROM tiendas;")
        sqlite_tiendas_map = {r["nombre"].lower(): r["id"] for r in cursor.fetchall()}

        cursor.execute("SELECT id, marca, nombre, tipo, genero FROM perfumes;")
        sqlite_perfumes_map: Dict[Tuple[str, str, str, str], int] = {}
        for r in cursor.fetchall():
            ck = _perfume_canon_key(r["marca"] or "", r["nombre"] or "", r["tipo"] or "", r["genero"] or "")
            sqlite_perfumes_map[ck] = r["id"]

        for tienda_cfg in TIENDAS_CRAWLER_CONFIG:
            t_nombre = tienda_cfg["nombre"]
            t_url_base = tienda_cfg["url_base"]
            t_endpoint = tienda_cfg["endpoint"]
            t_key = t_nombre.lower()

            if filtro_tiendas and not any(f.lower() in t_key for f in filtro_tiendas):
                continue

            t_id_supabase = sb_tiendas_map.get(t_key)
            if not t_id_supabase and supabase_activo and sb:
                try:
                    ins_t = sb.table("tiendas").upsert({
                        "nombre": t_nombre,
                        "url_base": t_url_base,
                        "trust_score": tienda_cfg["trust_score"],
                        "badge": "Tienda Verificada",
                        "logo_emoji": "",
                    }, on_conflict="nombre").execute()
                    if ins_t.data:
                        t_id_supabase = ins_t.data[0]["id"]
                        sb_tiendas_map[t_key] = t_id_supabase
                except Exception as e:
                    logger.warning(f"Error asegurando tienda {t_nombre} en Supabase: {e}")

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

            logger.info(f"Rastreando catálogo masivo de: {t_nombre}...")

            t_tipo = tienda_cfg.get("tipo", "shopify")
            for pag in range(1, paginas + 1):
                if t_tipo == "woocommerce":
                    params = {"per_page": min(limite_por_tienda, 100), "page": pag}
                else:
                    params = {"limit": min(limite_por_tienda, 250), "page": pag}

                try:
                    res = None
                    try:
                        res = session.get(t_endpoint, params=params, headers=headers, timeout=10)
                    except Exception as ex_req:
                        logger.debug(f"Petición inicial con requests falló ({ex_req}), probando con curl_cffi...")

                    if (res is None or res.status_code in (403, 429)) and curl_requests is not None:
                        try:
                            s_cffi = curl_requests.Session(impersonate="chrome124")
                            res_cffi = s_cffi.get(t_endpoint, params=params, headers=headers, timeout=15)
                            if res_cffi.status_code == 200:
                                res = res_cffi
                        except Exception as ex_cffi:
                            logger.debug(f"curl_cffi falló: {ex_cffi}")

                    if res is None or res.status_code != 200:
                        code_show = res.status_code if res is not None else "Error de Conexión"
                        logger.warning(f"Respuesta HTTP {code_show} en {t_nombre} (pág {pag})")
                        break

                    data = res.json()
                    if t_tipo == "woocommerce":
                        productos = data if isinstance(data, list) else []
                    else:
                        productos = data.get("products", []) if isinstance(data, dict) else []

                    if not productos:
                        logger.info(f"Fin del catálogo en {t_nombre} en página {pag}.")
                        break

                    logger.info(f"Procesando lote de {len(productos)} productos en {t_nombre} (pág {pag})...")

                    for prod in productos:
                        total_procesados += 1
                        if t_tipo == "woocommerce":
                            raw_title = html.unescape(prod.get("name", "")).strip()
                            wc_brands = [html.unescape(b.get("name", "")).strip() for b in prod.get("brands", []) if b.get("name")]
                            raw_vendor = wc_brands[0] if wc_brands else ""
                            if not raw_vendor:
                                for c in prod.get("categories", []):
                                    c_name = html.unescape(c.get("name", "")).strip()
                                    if c_name.lower() not in ("perfumes", "perfume", "hombre", "hombres", "mujer", "mujeres", "unisex", "nicho", "diseñador", "ofertas", "destacados", "inicio"):
                                        m_can = normalizar_marca_canonica(c_name)
                                        if m_can and m_can not in MARCAS_INVALIDAS_CATALOGO:
                                            raw_vendor = m_can
                                            break
                            tags = []
                            url_producto = prod.get("permalink", "")
                            images = prod.get("images", [])
                            img_url = images[0].get("src", "") if images else "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
                            prices_wc = prod.get("prices", {})
                            wc_price = clean_digits(prices_wc.get("price"))
                            wc_reg = clean_digits(prices_wc.get("regular_price"))
                            wc_stock = bool(prod.get("is_in_stock", True))
                            formato_prod = detectar_formato_oferta(raw_title, url_producto)
                            vol_ml = extraer_volumen_ml(raw_title) or extraer_volumen_ml(url_producto) or 100
                            variants = [{"price": wc_price, "compare_at_price": wc_reg if wc_reg > wc_price else None, "available": wc_stock, "title": f"{vol_ml}ml"}]
                        else:
                            raw_title = html.unescape(prod.get("title", "")).strip()
                            raw_vendor = html.unescape((prod.get("vendor", "") or "").strip())
                            tags = prod.get("tags", [])
                            url_producto = f"{t_url_base}/products/{prod.get('handle', '')}"
                            images = prod.get("images", [])
                            img_url = images[0].get("src", "") if images else "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
                            formato_prod = detectar_formato_oferta(raw_title, url_producto)
                            variants = prod.get("variants", [])

                        # Descartar clones/inspiraciones notorios
                        if any(c in (raw_vendor or "").lower() for c in ("loris", "martin lion", "aroma d'or", "volare")):
                            descartados_no_perfume += 1
                            continue
                        if any(w in raw_title.lower() for w in ("inspiracion", "inspiración", "inspirado en", "tipo sauvage", "tipo invictus")):
                            descartados_no_perfume += 1
                            continue

                        marca = normalizar_marca_canonica(raw_vendor) if len(raw_vendor) > 1 else ""
                        if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                            for b_cand in sorted(CANONICAL_BRAND_MAP.keys(), key=len, reverse=True):
                                if re.search(r'\b' + re.escape(b_cand) + r'\b', raw_title.lower()):
                                    marca = CANONICAL_BRAND_MAP[b_cand]
                                    break

                        # Si no hay marca canónica verificada, descartar producto (sin evidencia de identidad)
                        if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                            descartados_no_perfume += 1
                            continue

                        # 1. Filtro estricto de productos que no son fragancias embotelladas (>= 25 ml)
                        if not es_producto_perfume_valido(raw_title, tags, marca=marca, volumen_min_ml=25):
                            descartados_no_perfume += 1
                            continue

                        nombre_limpio = limpiar_nombre_perfume(raw_title, marca)
                        if not nombre_limpio or len(nombre_limpio.strip()) < 2:
                            descartados_no_perfume += 1
                            continue

                        concentracion = extraer_concentracion(raw_title)
                        genero = extraer_genero(raw_title)
                        arabe_flag = 1 if es_arabe(marca, nombre_limpio) else 0

                        if not variants:
                            continue

                        # Pre-filtrar solo variantes válidas (>= 25 ml y precio comercial sano)
                        variantes_validas: List[Dict[str, Any]] = []
                        for v in variants:
                            v_price = int(float(v.get("price", 0)))
                            if not es_precio_valido(v_price):
                                continue
                            v_title = v.get("title", "")
                            vol_ml = extraer_volumen_ml(f"{raw_title} {v_title}") or 100
                            if vol_ml < 25:
                                continue
                            v_compare_raw = v.get("compare_at_price")
                            v_compare = int(float(v_compare_raw)) if (v_compare_raw and float(v_compare_raw) > v_price) else None
                            v_avail = v.get("available")
                            v_stock = bool(v_avail) if v_avail is not None else True
                            v_fmt = detectar_formato_oferta(f"{raw_title} {v_title}", url_producto) if formato_prod == "regular" else formato_prod
                            variantes_validas.append({
                                "price": v_price,
                                "compare": v_compare,
                                "stock": v_stock,
                                "vol": vol_ml,
                                "formato": v_fmt,
                            })

                        if not variantes_validas:
                            descartados_no_perfume += 1
                            continue

                        primer_precio = variantes_validas[0]["price"]
                        canon_key = _perfume_canon_key(marca, nombre_limpio, concentracion, genero)
                        es_nuevo = False

                        # -----------------------------------------------------
                        # 3. GESTIÓN CANÓNICA DEL PERFUME EN SUPABASE
                        # -----------------------------------------------------
                        perfume_id_sb = sb_perfumes_conocidos.get(canon_key)
                        if not perfume_id_sb and supabase_activo and sb:
                            try:
                                chk_p = (
                                    sb.table("perfumes")
                                    .select("id")
                                    .ilike("marca", marca)
                                    .ilike("nombre", nombre_limpio)
                                    .ilike("tipo", concentracion)
                                    .ilike("genero", genero)
                                    .limit(1)
                                    .execute()
                                )
                                if chk_p.data:
                                    perfume_id_sb = chk_p.data[0]["id"]
                                else:
                                    img_url_final = img_url
                                    if subir_imagenes:
                                        img_url_final = subir_imagen_a_bucket_supabase(
                                            session=session,
                                            img_url=img_url,
                                            nombre_perfume=nombre_limpio,
                                            sb_client=sb if supabase_activo else None,
                                        )

                                    nuevo_p = sb.table("perfumes").insert({
                                        "nombre": nombre_limpio,
                                        "marca": marca,
                                        "genero": genero,
                                        "tipo": concentracion,
                                        "notas": "Notas aromáticas exclusivas",
                                        "imagen_url": img_url_final,
                                        "es_arabe": bool(arabe_flag),
                                        "en_tendencia": True,
                                        "en_remate": False,
                                        "precio_referencia": primer_precio,
                                    }).execute()
                                    if nuevo_p.data:
                                        perfume_id_sb = nuevo_p.data[0]["id"]
                                        es_nuevo = True

                                if perfume_id_sb:
                                    sb_perfumes_conocidos[canon_key] = perfume_id_sb
                            except Exception as e:
                                logger.warning(f"Error guardando perfume {nombre_limpio} en Supabase: {e}")

                        # -----------------------------------------------------
                        # 4. GESTIÓN CANÓNICA DEL PERFUME EN SQLITE (SIN LIKE AMBIGUO)
                        # -----------------------------------------------------
                        perfume_id_sqlite = sqlite_perfumes_map.get(canon_key)
                        if not perfume_id_sqlite:
                            cursor.execute(
                                """
                                SELECT id FROM perfumes
                                WHERE LOWER(TRIM(marca)) = LOWER(?)
                                  AND LOWER(TRIM(nombre)) = LOWER(?)
                                  AND LOWER(COALESCE(TRIM(tipo), '')) = LOWER(?)
                                  AND LOWER(COALESCE(TRIM(genero), '')) = LOWER(?);
                                """,
                                (marca, nombre_limpio, concentracion, genero),
                            )
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

                            if perfume_id_sqlite:
                                sqlite_perfumes_map[canon_key] = perfume_id_sqlite

                        if es_nuevo:
                            nuevos_perfumes += 1
                            muestras_descubiertas.append({
                                "nombre": nombre_limpio,
                                "marca": marca,
                                "tipo": concentracion,
                                "es_arabe": bool(arabe_flag),
                                "tienda": t_nombre,
                                "precio": primer_precio,
                            })
                            logger.info(f"NUEVO PERFUME DESCUBIERTO: {nombre_limpio} ({marca}) - ${primer_precio:,}")

                        # -----------------------------------------------------
                        # 5. INGESTA DE VARIANTES Y PRECIOS POR VOLUMEN Y FORMATO
                        # -----------------------------------------------------
                        for v_item in variantes_validas:
                            v_price = v_item["price"]
                            v_compare = v_item["compare"]
                            v_stock = v_item["stock"]
                            volumen_ml = v_item["vol"]
                            v_fmt = v_item["formato"]

                            var_id_sb = sb_variantes_conocidas.get((perfume_id_sb, volumen_ml, v_fmt)) if perfume_id_sb else None

                            try:
                                res_obs = registrar_observacion_oferta({
                                    "perfume_id": perfume_id_sb,
                                    "perfume_id_sb": perfume_id_sb,
                                    "perfume_id_sqlite": perfume_id_sqlite,
                                    "tienda_id": t_id_supabase or t_id_sqlite,
                                    "tienda_id_sb": t_id_supabase,
                                    "tienda_id_sqlite": t_id_sqlite,
                                    "variante_id_sb": var_id_sb,
                                    "precio_actual": v_price,
                                    "precio_normal": v_compare,
                                    "en_stock": v_stock,
                                    "volumen_ml": volumen_ml,
                                    "formato": v_fmt,
                                    "url_producto": url_producto,
                                    "scraping_run_id": run_id,
                                })
                                precios_registrados += 1
                                if perfume_id_sb and not var_id_sb and res_obs and isinstance(res_obs, dict) and res_obs.get("variante_id"):
                                    sb_variantes_conocidas[(perfume_id_sb, volumen_ml, v_fmt)] = res_obs["variante_id"]
                            except Exception as ex_obs:
                                logger.debug(f"Aviso registrando oferta de {nombre_limpio} ({volumen_ml}ml): {ex_obs}")

                except Exception as e:
                    err_msg = f"Fallo procesando {t_nombre} página {pag}: {e}"
                    logger.error(err_msg)
                    errores.append(err_msg)

                time.sleep(0.3)

    duracion = round(time.time() - inicio, 2)
    estado = "EXITOSO" if not errores else ("DEGRADADO" if precios_registrados > 0 else "FALLIDO")

    finalizar_scraping_run(
        run_id=run_id,
        estado="completado" if estado == "EXITOSO" else estado.lower(),
        productos_procesados=total_procesados,
        ofertas_nuevas=nuevos_perfumes,
        cambios_precio=precios_registrados,
        errores=len(errores),
        mensaje_detalle=f"Rastreo masivo: {nuevos_perfumes} nuevos perfumes, {precios_registrados} variantes en {duracion}s",
    )

    # Registrar log de auditoría en Supabase
    if supabase_activo and sb:
        try:
            sb.table("scraping_logs").insert({
                "tipo_scraper": "Descubrimiento Autónomo",
                "tienda_nombre": "Crawler Multitienda (Silk, Elite, Alisha, Yauras, Oferta)",
                "productos_procesados": total_procesados,
                "productos_nuevos": nuevos_perfumes,
                "precios_actualizados": precios_registrados,
                "estado": estado,
                "mensaje_detalle": f"Rastreo masivo: {nuevos_perfumes} nuevos perfumes, {precios_registrados} variantes en {duracion}s",
                "fecha_ejecucion": ahora
            }).execute()
        except Exception as e:
            logger.debug(f"No se pudo guardar scraping_log en Supabase: {e}")

    reporte = {
        "metadata": {
            "version": "2.1.0 (Cloud Supabase Multi-Tienda Masivo)",
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
        "muestras_nuevas": muestras_descubiertas[:25],
        "errores": errores
    }

    guardar_reporte_descubrimiento(reporte)
    logger.info(f"Ciclo completado en {duracion}s | {nuevos_perfumes} perfumes nuevos descubiertos | {precios_registrados} precios registrados.")
    return reporte




# - ¿Qué hace esta función?:
#   1. Opera en memoria RAM de ultra-alta velocidad (< 2 segundos) sobre los catálogos masivos precargados (cache_tiendas_bulk).
#   2. Carga en un conjunto hash O(1) todos los perfumes ya conocidos en Supabase y SQLite para deduplicar al instante.
#   3. Itera sobre los productos no catalogados presentes en los feeds de las tiendas especializadas.
#   4. Aplica el escudo de control de calidad: descarta clones ('tipo Sauvage'), marcas apócrifas, cosméticos y frascos < 25ml.
#   5. Ingiere las nuevas fragancias legítimas en Supabase Cloud y SQLite delegando en 'guardar_o_actualizar_perfume_scraped'.
#   6. Genera y guarda el informe de auditoría en 'data/reportes/ultimo_descubrimiento.json'.
def descubrir_nuevos_perfumes_desde_bulk(
    cache_tiendas_bulk: Dict[str, Any],
    limite_nuevos_por_tienda: int = 50,
    reporte_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Descubre de manera instantánea en memoria nuevas fragancias no presentes en el catálogo
    aprovechando los feeds descargados por el scraper periódico.
    """
    init_db()
    inicio = time.time()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    perfumes_conocidos: Set[Tuple[str, str]] = set()
    sb = get_supabase(use_service_role=True)
    supabase_activo = is_supabase_disponible()

    if supabase_activo and sb:
        try:
            offset = 0
            while True:
                res = sb.table("perfumes").select("marca, nombre").range(offset, offset + 999).execute()
                if not res.data:
                    break
                for r in res.data:
                    m = (normalizar_marca_canonica(r.get("marca") or "") or "").strip().lower()
                    n = (limpiar_nombre_perfume(r.get("nombre") or "", r.get("marca") or "") or "").strip().lower()
                    if m and n:
                        perfumes_conocidos.add((m, n))
                if len(res.data) < 1000:
                    break
                offset += 1000
        except Exception as e_sb:
            logger.warning(f"Aviso consultando perfumes conocidos en Supabase: {e_sb}")

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT marca, nombre FROM perfumes;")
            for r in cur.fetchall():
                m = (normalizar_marca_canonica(r["marca"] or "") or "").strip().lower()
                n = (limpiar_nombre_perfume(r["nombre"] or "", r["marca"] or "") or "").strip().lower()
                if m and n:
                    perfumes_conocidos.add((m, n))
    except Exception as e_sq:
        logger.warning(f"Aviso consultando perfumes conocidos en SQLite: {e_sq}")

    total_analizados = 0
    descartados_no_perfume = 0
    nuevos_descubiertos = 0
    precios_variantes_registrados = 0
    muestras: List[Dict[str, Any]] = []
    errores: List[str] = []

    for tienda_slug, cat in cache_tiendas_bulk.items():
        tienda_nombre = getattr(cat, "nombre_tienda", tienda_slug)
        nuevos_en_tienda = 0
        items = getattr(cat, "todos_items", [])

        for item in items:
            total_analizados += 1
            raw_title = item.get("title", "")
            raw_vendor = item.get("vendor", "")
            item_url = item.get("url", "")
            img_url = item.get("imagen_url", "")
            formato = item.get("formato", "regular")

            # Filtro 1: Clones e imitaciones
            if any(c in (raw_vendor or "").lower() for c in ("loris", "martin lion", "aroma d'or", "volare")):
                descartados_no_perfume += 1
                continue
            if any(w in raw_title.lower() for w in ("inspiracion", "inspiración", "inspirado en", "tipo sauvage", "tipo invictus")):
                descartados_no_perfume += 1
                continue

            # Filtro 2: Marca canónica verificada
            marca = item.get("marca") or normalizar_marca_canonica(raw_vendor)
            if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                for b_cand, b_canon in sorted(CANONICAL_BRAND_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                    if re.search(r'\b' + re.escape(b_cand) + r'\b', raw_title.lower()):
                        marca = b_canon
                        break

            if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                descartados_no_perfume += 1
                continue

            # Filtro 3: Validación estricta de perfume (>=25ml, sin cosméticos ni desodorantes)
            if not es_producto_perfume_valido(raw_title, marca=marca, volumen_min_ml=25):
                descartados_no_perfume += 1
                continue

            # Filtro 4: Nombre canónico limpio
            nombre_limpio = limpiar_nombre_perfume(raw_title, marca)
            if not nombre_limpio or len(nombre_limpio.strip()) < 2:
                descartados_no_perfume += 1
                continue

            clave_canon = (marca.strip().lower(), nombre_limpio.strip().lower())
            if clave_canon in perfumes_conocidos:
                continue

            if nuevos_en_tienda >= limite_nuevos_por_tienda:
                break

            # Filtro 5: Variantes válidas con precio comercial
            variants = item.get("variants", [])
            var_valida = None
            for v in variants:
                p_val = clean_digits(v.get("price"))
                if es_precio_valido(p_val) and p_val >= 4000:
                    v_title = v.get("title", "")
                    vol_cand = extraer_volumen_ml(f"{raw_title} {v_title}") or extraer_volumen_ml(item_url) or 100
                    if vol_cand >= 25:
                        var_valida = (v, p_val, vol_cand)
                        break

            if not var_valida:
                descartados_no_perfume += 1
                continue

            v_dict, p_act, vol_ml = var_valida
            p_norm_raw = clean_digits(v_dict.get("compare_at_price"))
            p_norm = p_norm_raw if (p_norm_raw and p_norm_raw > p_act) else p_act
            in_stock = bool(v_dict.get("available", True))
            concentracion = extraer_concentracion(raw_title) or "Eau de Parfum"
            genero = extraer_genero(raw_title) or "Unisex"
            arabe_flag = 1 if es_arabe(marca, nombre_limpio) else 0

            # Ingesta en base de datos
            try:
                res_ing = guardar_o_actualizar_perfume_scraped(
                    nombre=nombre_limpio,
                    marca=marca,
                    precio_actual=p_act,
                    precio_normal=p_norm,
                    tienda_nombre=tienda_nombre,
                    url_producto=item_url,
                    imagen_url=img_url or None,
                    es_arabe=arabe_flag,
                    genero=genero,
                    volumen_ml=vol_ml,
                    tipo=concentracion,
                    formato=formato,
                    en_stock=in_stock,
                )
                if res_ing.get("exito"):
                    nuevos_descubiertos += 1
                    nuevos_en_tienda += 1
                    precios_variantes_registrados += 1
                    perfumes_conocidos.add(clave_canon)
                    muestras.append({
                        "nombre": nombre_limpio,
                        "marca": marca,
                        "tipo": concentracion,
                        "es_arabe": bool(arabe_flag),
                        "tienda": tienda_nombre,
                        "precio": p_act,
                        "volumen_ml": vol_ml,
                    })
                    logger.info(f"✨ [DESCUBRIMIENTO BULK] Nuevo perfume: {nombre_limpio} ({marca}) en {tienda_nombre} - ${p_act:,}")
            except Exception as ex_ing:
                err_msg = f"Error ingesta descubrimiento para {nombre_limpio} ({marca}): {ex_ing}"
                logger.warning(err_msg)
                errores.append(err_msg)

    duracion = round(time.time() - inicio, 2)
    estado = "EXITOSO" if not errores else ("DEGRADADO" if nuevos_descubiertos > 0 else "FALLIDO")

    reporte = {
        "metadata": {
            "version": "3.3.0 (In-Memory Bulk Stream Discovery)",
            "sistema": "PerfumeTrending Autonomous Discovery Engine",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado,
            "destino": "Supabase Cloud + SQLite Local",
        },
        "metricas": {
            "total_productos_analizados": total_analizados,
            "descartados_no_perfume": descartados_no_perfume,
            "nuevos_perfumes_descubiertos": nuevos_descubiertos,
            "precios_variantes_registrados": precios_variantes_registrados,
            "errores_totales": len(errores),
        },
        "muestras_nuevas": muestras[:25],
        "errores": errores,
    }

    guardar_reporte_descubrimiento(reporte, ruta_destino=reporte_path)
    return reporte


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Autónomo de Perfumes (PerfumeTrending.cl)")
    parser.add_argument("--limit", type=int, default=250, help="Límite de productos por página (default: 250)")
    parser.add_argument("--pages", type=int, default=2, help="Páginas a rastrear por tienda (default: 2)")
    parser.add_argument("--upload-images", action="store_true", help="Subir imágenes a Supabase Storage (más lento)")
    parser.add_argument("--stores", type=str, default="all", help="Tiendas separadas por coma (ej: silk,elite,oferta)")
    args = parser.parse_args()

    filtro = None if args.stores.lower() == "all" else [s.strip() for s in args.stores.split(",") if s.strip()]

    resultado = ejecutar_descubrimiento_autonomo(
        limite_por_tienda=args.limit,
        paginas=args.pages,
        subir_imagenes=args.upload_images,
        filtro_tiendas=filtro
    )
    print("\n" + "=" * 60)
    print("RESUMEN DE DESCUBRIMIENTO AUTÓNOMO EN SUPABASE & SQLITE:")
    print(f"Estado: {resultado['metadata']['estado']}")
    print(f"Productos analizados: {resultado['metricas']['total_productos_analizados']}")
    print(f"Nuevos perfumes descubiertos: {resultado['metricas']['nuevos_perfumes_descubiertos']}")
    print(f"Precios/Variantes registradas: {resultado['metricas']['precios_variantes_registrados']}")
    print(f"Duración: {resultado['metadata']['duracion_segundos']}s")
    print("=" * 60)

