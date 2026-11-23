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

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de librería estándar o dependencia externa (html)
import html
# Importación de componentes (datetime) desde el módulo 'datetime'
from datetime import datetime
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (random)
import random
# Importación de librería estándar o dependencia externa (re)
import re
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de componentes (Any, Dict, List, Optional, ...) desde el módulo 'typing'
from typing import Any, Dict, List, Optional, Set, Tuple
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse

# Importación de librería estándar o dependencia externa (requests)
import requests
# Importación de componentes (HTTPAdapter) desde el módulo 'requests.adapters'
from requests.adapters import HTTPAdapter
# Importación de componentes (Retry) desde el módulo 'urllib3.util'
from urllib3.util import Retry

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (requests) desde el módulo 'curl_cffi'
    from curl_cffi import requests as curl_requests
except ImportError:
    # Asignamos 'curl_requests' con None
    curl_requests = None

# - ¿Qué hace esta función?:
#   1. Extrae dígitos puros de un valor textual o numérico sucio (e.g. \'$59.990 CLP\' -> 59990).
#   2. Devuelve 0 entero seguro ante valores None o textos sin caracteres numéricos.

def clean_digits(val: Any) -> int:
    # Evaluamos la condición lógica (val is None) para controlar el flujo
    if val is None:
        # Retornamos el resultado procesado (0)
        return 0
    # Asignamos 's' con re.sub('[^\\d]', '', str(val))
    s = re.sub(r'[^\d]', '', str(val))
    # Retornamos el resultado procesado (int(s) if s else 0)
    return int(s) if s else 0

# Ajuste de codificación en Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # Ejecutamos instrucción: pass
        pass

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# Asignamos 'logger' con logging.getLogger('CrawlerAutonomo')
logger = logging.getLogger("CrawlerAutonomo")

# Rutas del sistema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)
# Asignamos 'REPORTES_DIR' con os.path.join(BASE_DIR, 'data', 'reportes')
REPORTES_DIR = os.path.join(BASE_DIR, "data", "reportes")
# Asignamos 'REPORTE_DESCUBRIMIENTO_PATH' con os.path.join(REPORTES_DIR, 'ultimo_descubr...
REPORTE_DESCUBRIMIENTO_PATH = os.path.join(REPORTES_DIR, "ultimo_descubrimiento.json")

# Importación de persistencia y normalización
try:
    # Importación de componentes (finalizar_scraping_run, get_db_cursor, init_db, iniciar_scraping_run, ...) desde el módulo 'backend.database'
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
    # Importación de componentes (generos_compatibles, normalizar_genero, CANONICAL_BRAND_MAP, MARCAS_INVALIDAS_CATALOGO, ...) desde el módulo 'backend.normalizador'
    from backend.normalizador import (
        generos_compatibles,
        normalizar_genero,
        CANONICAL_BRAND_MAP,
        MARCAS_INVALIDAS_CATALOGO,
        detectar_formato_oferta,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_concentracion,
        extraer_genero,
        extraer_volumen_ml,
        extraer_volumen_ml_opcional,
        limpiar_nombre_perfume,
        normalizar_marca_canonica,
        resolver_volumen_oferta,
    )
except ImportError:
    # Importación de componentes (finalizar_scraping_run, get_db_cursor, init_db, iniciar_scraping_run, ...) desde el módulo 'database'
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
    # Importación de componentes (generos_compatibles, normalizar_genero, CANONICAL_BRAND_MAP, MARCAS_INVALIDAS_CATALOGO, ...) desde el módulo 'normalizador'
    from normalizador import (
        generos_compatibles,
        normalizar_genero,
        CANONICAL_BRAND_MAP,
        MARCAS_INVALIDAS_CATALOGO,
        detectar_formato_oferta,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_concentracion,
        extraer_genero,
        extraer_volumen_ml,
        extraer_volumen_ml_opcional,
        limpiar_nombre_perfume,
        normalizar_marca_canonica,
        resolver_volumen_oferta,
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
    # Configuración de elemento #1 (nombre='Silk Perfumes')
    {
        "nombre": "Silk Perfumes",
        "url_base": "https://www.silkperfumes.cl",
        "endpoint": "https://www.silkperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 92
    },
    # Configuración de elemento #2 (nombre='Elite Perfumes')
    {
        "nombre": "Elite Perfumes",
        "url_base": "https://www.eliteperfumes.cl",
        "endpoint": "https://www.eliteperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 89
    },
    # Configuración de elemento #3 (nombre='Alisha Perfumes')
    {
        "nombre": "Alisha Perfumes",
        "url_base": "https://alishaperfumes.cl",
        "endpoint": "https://alishaperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 91
    },
    # Configuración de elemento #4 (nombre='Yauras Perfumes')
    {
        "nombre": "Yauras Perfumes",
        "url_base": "https://yauras.cl",
        "endpoint": "https://yauras.cl/products.json",
        "tipo": "shopify",
        "trust_score": 88
    },
    # Configuración de elemento #5 (nombre='Oferta Perfumes')
    {
        "nombre": "Oferta Perfumes",
        "url_base": "https://ofertaperfumes.cl",
        "endpoint": "https://ofertaperfumes.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    # Configuración de elemento #6 (nombre='L'Odoro')
    {
        "nombre": "L'Odoro",
        "url_base": "https://www.lodoro.cl",
        "endpoint": "https://www.lodoro.cl/products.json",
        "tipo": "shopify",
        "trust_score": 92
    },
    # Configuración de elemento #7 (nombre='Chile Perfume')
    {
        "nombre": "Chile Perfume",
        "url_base": "https://www.chileperfume.cl",
        "endpoint": "https://www.chileperfume.cl/wp-json/wc/store/v1/products",
        "tipo": "woocommerce",
        "trust_score": 91
    },
    # Configuración de elemento #8 (nombre='Mundo Aromas')
    {
        "nombre": "Mundo Aromas",
        "url_base": "https://mundoaromas.cl",
        "endpoint": "https://mundoaromas.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    # Configuración de elemento #9 (nombre='Cosmetic')
    {
        "nombre": "Cosmetic",
        "url_base": "https://cosmetic.cl",
        "endpoint": "https://cosmetic.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    # Configuración de elemento #10 (nombre='Fragante')
    {
        "nombre": "Fragante",
        "url_base": "https://fragante.cl",
        "endpoint": "https://fragante.cl/products.json",
        "tipo": "shopify",
        "trust_score": 90
    },
    # Configuración de elemento #11 (nombre='ComprarEnChile')
    {
        "nombre": "ComprarEnChile",
        "url_base": "https://comprarenchile.cl",
        "endpoint": "https://comprarenchile.cl/products.json",
        "tipo": "shopify",
        "trust_score": 88
    },
    # Configuración de elemento #12 (nombre='Portal del Perfume')
    {
        "nombre": "Portal del Perfume",
        "url_base": "https://portaldelperfume.cl",
        "endpoint": "https://portaldelperfume.cl/wp-json/wc/store/v1/products",
        "tipo": "woocommerce",
        "trust_score": 89
    },
    # Configuración de elemento #13 (nombre='Aromata')
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
    # Asignamos 'session' con requests.Session()
    session = requests.Session()
    # Asignamos 'retry_strategy' con Retry(total=3, backoff_factor=0.5, status_...
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"]
    )
    # Asignamos 'adapter' con HTTPAdapter(max_retries=retry_strategy, po...
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    # Ejecutamos instrucción: session.mount('https://', adapter)
    session.mount("https://", adapter)
    # Ejecutamos instrucción: session.mount('http://', adapter)
    session.mount("http://", adapter)
    # Retornamos el resultado procesado (session)
    return session


# - ¿Qué hace esta función?:
#   1. Carga desde disco el archivo JSON 'data/reportes/ultimo_descubrimiento.json' (o ruta personalizada).
#   2. Retorna un diccionario con las métricas del último ciclo de auto-descubrimiento o None si no existe.
def obtener_ultimo_reporte_descubrimiento(ruta_destino: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Carga el último informe de descubrimiento autónomo generado en disco."""
    # Asignamos 'target' con ruta_destino or REPORTE_DESCUBRIMIENTO_PATH
    target = ruta_destino or REPORTE_DESCUBRIMIENTO_PATH
    # Evaluamos la condición lógica (os.path.exists(target)) para controlar el flujo
    if os.path.exists(target):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Gestión automática de contexto y recursos para: open(target, 'r', encoding='utf-8')
            with open(target, "r", encoding="utf-8") as f:
                # Retornamos el resultado procesado (json.load(f))
                return json.load(f)
        except Exception:
            # Ejecutamos instrucción: pass
            pass
    # Retornamos el resultado procesado (None)
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
    # Evaluamos la condición lógica (not sb_client or not img_url or img_url.startswith('...) para controlar el flujo
    if not sb_client or not img_url or img_url.startswith("https://miqscdupnknhjemvcjil.supabase.co"):
        # Retornamos el resultado procesado (img_url)
        return img_url

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Generar nombre limpio (slug) para el archivo en el bucket
        slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', nombre_perfume.lower().strip())
        # Asignamos 'slug' con re.sub('_+', '_', slug)[:60].strip('_')
        slug = re.sub(r'_+', '_', slug)[:60].strip('_')
        # Asignamos 'filename' con f'{slug}.jpg'
        filename = f"{slug}.jpg"

        # Descargar los bytes de la imagen
        resp = session.get(img_url, timeout=10)
        # Evaluamos la condición lógica (resp.status_code == 200 and len(resp.content) > 1000) para controlar el flujo
        if resp.status_code == 200 and len(resp.content) > 1000:
            # Asignamos 'content' con resp.content
            content = resp.content
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            content_type = resp.headers.get("Content-Type", "image/jpeg")

            # Subir directamente al bucket de Supabase con sobrescritura permitida
            sb_client.storage.from_("IMG_perfumes").upload(
                path=filename,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"}
            )

            # Asignamos 'url_publica' con sb_client.storage.from_('IMG_perfumes').ge...
            url_publica = sb_client.storage.from_("IMG_perfumes").get_public_url(filename)
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info(f"📸 Imagen subida y vinculada al bucket IMG_perfumes: {filename}")
            # Retornamos el resultado procesado (url_publica)
            return url_publica
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.debug(f"Aviso subiendo imagen a Supabase Storage: {e}")

    # Retornamos el resultado procesado (img_url)
    return img_url


# - ¿Qué hace esta función?:
#   1. Asegura que el directorio 'data/reportes' exista en el entorno de ejecución.
#   2. Serializa el diccionario del informe en JSON con codificación UTF-8 e indentación legible.
#   3. Permite especificar una ruta de destino alternativa para auditoría y pruebas unitarias.
def guardar_reporte_descubrimiento(reporte: Dict[str, Any], ruta_destino: Optional[str] = None) -> str:
    """Persiste el informe en JSON para auditoría y observabilidad del sistema."""
    # Asignamos 'destino' con ruta_destino or REPORTE_DESCUBRIMIENTO_PATH
    destino = ruta_destino or REPORTE_DESCUBRIMIENTO_PATH
    # Ejecutamos instrucción: os.makedirs(os.path.dirname(os.path.abspath(destino)...
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    # Gestión automática de contexto y recursos para: open(destino, 'w', encoding='utf-8')
    with open(destino, "w", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    # Retornamos el resultado procesado (destino)
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
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'inicio' con time.time()
    inicio = time.time()
    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    supabase_activo = is_supabase_disponible()

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Iniciando descubrimiento autónomo masivo (límite: {limite_por_tienda} items/página, {paginas} páginas)")
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    logger.info(f"Destino de persistencia: {'SUPABASE CLOUD + SQLITE' if supabase_activo else 'SQLITE LOCAL'}")

    # Asignamos 'session' con crear_sesion_robusta()
    session = crear_sesion_robusta()
    # Asignamos 'headers' con {'User-Agent': random.choice(USER_AGENTS),...
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json"
    }

    # Asignamos 'total_procesados' con 0
    total_procesados = 0
    # Asignamos 'nuevos_perfumes' con 0
    nuevos_perfumes = 0
    # Asignamos 'precios_registrados' con 0
    precios_registrados = 0
    # Asignamos 'descartados_no_perfume' con 0
    descartados_no_perfume = 0
    # Asignamos 'errores' con []
    errores: List[str] = []
    # Asignamos 'muestras_descubiertas' con []
    muestras_descubiertas: List[Dict[str, Any]] = []

    # Asignamos 'run_id' con iniciar_scraping_run(tipo_scraper='Descubr...
    run_id = iniciar_scraping_run(
        tipo_scraper="Descubrimiento Autónomo Multitienda",
        mensaje_detalle=f"Rastreo masivo ({paginas} páginas/tienda, límite {limite_por_tienda})",
    )

    # - ¿Qué hace esta función?:
    #   Construye la clave canónica de entidad `(marca, nombre_limpio, concentracion)` SIN género
    #   para evitar fragmentar el mismo perfume cuando distintas tiendas lo etiquetan Hombre vs Unisex.
    def _perfume_canon_key(m_raw: str, n_raw: str, c_raw: str) -> Tuple[str, str, str]:
        # Asignamos 'm_c' con (normalizar_marca_canonica(m_raw) or 'Dise...
        m_c = (normalizar_marca_canonica(m_raw) or "Diseñador").strip().lower()
        # Asignamos 'n_c' con (limpiar_nombre_perfume(n_raw, m_raw) or n...
        n_c = (limpiar_nombre_perfume(n_raw, m_raw) or n_raw or "").strip().lower()
        # Asignamos 'c_c' con (c_raw or 'Eau de Parfum').strip().lower()
        c_c = (c_raw or "Eau de Parfum").strip().lower()
        # Retornamos el resultado procesado ((m_c, n_c, c_c))
        return (m_c, n_c, c_c)

    # Definición de función '_resolver_id_en_mapa' (parámetros: mapa, ck, genero_obs)
    def _resolver_id_en_mapa(
        mapa: Dict[Tuple[str, str, str], List[Tuple[int, str]]],
        ck: Tuple[str, str, str],
        genero_obs: str,
    ) -> Tuple[Optional[int], Optional[str], bool]:
        # Asignamos 'g_norm' con normalizar_genero(genero_obs) or 'Unisex'
        g_norm = normalizar_genero(genero_obs) or "Unisex"
        # Asignamos 'entradas' con mapa.get(ck) or []
        entradas = mapa.get(ck) or []
        # Evaluamos la condición lógica (not entradas) para controlar el flujo
        if not entradas:
            # Retornamos el resultado procesado ((None, None, False))
            return None, None, False
        # Recorremos iterativamente cada '(pid_e, g_e)' en entradas
        for pid_e, g_e in entradas:
            # Evaluamos la condición lógica ((normalizar_genero(g_e) or 'Unisex') == g_norm) para controlar el flujo
            if (normalizar_genero(g_e) or "Unisex") == g_norm:
                # Retornamos el resultado procesado ((pid_e, g_norm, False))
                return pid_e, g_norm, False
        # Recorremos iterativamente cada '(pid_e, g_e)' en entradas
        for pid_e, g_e in entradas:
            # Asignamos '(es_comp, g_res)' con generos_compatibles(g_e, g_norm)
            es_comp, g_res = generos_compatibles(g_e, g_norm)
            # Evaluamos la condición lógica (es_comp) para controlar el flujo
            if es_comp:
                # Retornamos el resultado procesado ((pid_e, g_res, False))
                return pid_e, g_res, False
        # Existe la misma clave (marca, nombre, tipo) pero con género opuesto explícito (Hombre vs Mujer)
        return None, None, True

    # Asignamos 'sb_tiendas_map' con {}
    sb_tiendas_map: Dict[str, int] = {}
    # Asignamos 'sb_perfumes_conocidos' con {}
    sb_perfumes_conocidos: Dict[Tuple[str, str, str], List[Tuple[int, str]]] = {}
    # Asignamos 'sb_variantes_conocidas' con {}
    sb_variantes_conocidas: Dict[Tuple[int, int, str], int] = {}

    # Evaluamos la condición lógica (supabase_activo and sb) para controlar el flujo
    if supabase_activo and sb:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res_t = sb.table("tiendas").select("id, nombre").execute()
            # Recorremos iterativamente cada 'r' en res_t.data or []
            for r in res_t.data or []:
                # Asignamos 'sb_tiendas_map[r['nombre'].lower()]' con r['id']
                sb_tiendas_map[r["nombre"].lower()] = r["id"]

            # Asignamos 'offset' con 0
            offset = 0
            # Ejecutamos el ciclo mientras se mantenga la condición: True
            while True:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                res_p = sb.table("perfumes").select("id, marca, nombre, tipo, genero").range(offset, offset + 999).execute()
                # Evaluamos la condición lógica (not res_p.data) para controlar el flujo
                if not res_p.data:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Recorremos iterativamente cada 'r' en res_p.data
                for r in res_p.data:
                    # Asignamos 'ck' con _perfume_canon_key(r.get('marca') or '', r...
                    ck = _perfume_canon_key(r.get("marca") or "", r.get("nombre") or "", r.get("tipo") or "")
                    # Ejecutamos instrucción: sb_perfumes_conocidos.setdefault(ck, []).append((r['...
                    sb_perfumes_conocidos.setdefault(ck, []).append((r["id"], normalizar_genero(r.get("genero")) or "Unisex"))
                # Evaluamos la condición lógica (len(res_p.data) < 1000) para controlar el flujo
                if len(res_p.data) < 1000:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Actualizamos acumulativamente el valor de 'offset'
                offset += 1000

            # Asignamos 'offset_v' con 0
            offset_v = 0
            # Ejecutamos el ciclo mientras se mantenga la condición: True
            while True:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                res_v = sb.table("variantes_perfume").select("id, perfume_id, volumen_ml, formato").range(offset_v, offset_v + 999).execute()
                # Evaluamos la condición lógica (not res_v.data) para controlar el flujo
                if not res_v.data:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Recorremos iterativamente cada 'r' en res_v.data
                for r in res_v.data:
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Asignamos 'v_ml' con int(round(float(r['volumen_ml'])))
                        v_ml = int(round(float(r["volumen_ml"])))
                        # Asignamos 'v_fmt' con str(r.get('formato') or 'regular').lower()
                        v_fmt = str(r.get("formato") or "regular").lower()
                        # Asignamos 'sb_variantes_conocidas[r['perfum...' con r['id']
                        sb_variantes_conocidas[(r["perfume_id"], v_ml, v_fmt)] = r["id"]
                    except Exception:
                        # Ejecutamos instrucción: pass
                        pass
                # Evaluamos la condición lógica (len(res_v.data) < 1000) para controlar el flujo
                if len(res_v.data) < 1000:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Actualizamos acumulativamente el valor de 'offset_v'
                offset_v += 1000

            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.info(f"Caché Supabase inicializada: {len(sb_perfumes_conocidos)} perfumes, {len(sb_variantes_conocidas)} variantes.")
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error cargando caché inicial desde Supabase: {e}")

    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id, nombre FROM tiendas;")
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        sqlite_tiendas_map = {r["nombre"].lower(): r["id"] for r in cursor.fetchall()}

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id, marca, nombre, tipo, genero FROM perfumes;")
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        sqlite_perfumes_map: Dict[Tuple[str, str, str], List[Tuple[int, str]]] = {}
        # Recorremos iterativamente cada 'r' en cursor.fetchall()
        for r in cursor.fetchall():
            # Asignamos 'ck' con _perfume_canon_key(r['marca'] or '', r['no...
            ck = _perfume_canon_key(r["marca"] or "", r["nombre"] or "", r["tipo"] or "")
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            sqlite_perfumes_map.setdefault(ck, []).append((r["id"], normalizar_genero(r["genero"]) or "Unisex"))

        # Recorremos iterativamente cada 'tienda_cfg' en TIENDAS_CRAWLER_CONFIG
        for tienda_cfg in TIENDAS_CRAWLER_CONFIG:
            # Asignamos 't_nombre' con tienda_cfg['nombre']
            t_nombre = tienda_cfg["nombre"]
            # Asignamos 't_url_base' con tienda_cfg['url_base']
            t_url_base = tienda_cfg["url_base"]
            # Asignamos 't_endpoint' con tienda_cfg['endpoint']
            t_endpoint = tienda_cfg["endpoint"]
            # Asignamos 't_key' con t_nombre.lower()
            t_key = t_nombre.lower()

            # Evaluamos la condición lógica (filtro_tiendas and (not any((f.lower() in t_key for ...) para controlar el flujo
            if filtro_tiendas and not any(f.lower() in t_key for f in filtro_tiendas):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            t_id_supabase = sb_tiendas_map.get(t_key)
            # Evaluamos la condición lógica (not t_id_supabase and supabase_activo and sb) para controlar el flujo
            if not t_id_supabase and supabase_activo and sb:
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    ins_t = sb.table("tiendas").upsert({
                        "nombre": t_nombre,
                        "url_base": t_url_base,
                        "trust_score": tienda_cfg["trust_score"],
                        "badge": "Tienda Verificada",
                        "logo_emoji": "",
                    }, on_conflict="nombre").execute()
                    # Evaluamos la condición lógica (ins_t.data) para controlar el flujo
                    if ins_t.data:
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        t_id_supabase = ins_t.data[0]["id"]
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        sb_tiendas_map[t_key] = t_id_supabase
                except Exception as e:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    logger.warning(f"Error asegurando tienda {t_nombre} en Supabase: {e}")

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            t_id_sqlite = sqlite_tiendas_map.get(t_key)
            # Evaluamos la condición lógica (not t_id_sqlite) para controlar el flujo
            if not t_id_sqlite:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("""
                INSERT OR IGNORE INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
                VALUES (?, ?, ?, 'Tienda Verificada', '');
                """, (t_nombre, t_url_base, tienda_cfg["trust_score"]))
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = ?;", (t_key,))
                # Asignamos 'row_t' con cursor.fetchone()
                row_t = cursor.fetchone()
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                t_id_sqlite = row_t["id"] if row_t else 1
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                sqlite_tiendas_map[t_key] = t_id_sqlite

            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info(f"Rastreando catálogo masivo de: {t_nombre}...")

            # Asignamos 't_tipo' con tienda_cfg.get('tipo', 'shopify')
            t_tipo = tienda_cfg.get("tipo", "shopify")
            # Recorremos iterativamente cada 'pag' en range(1, paginas + 1)
            for pag in range(1, paginas + 1):
                # Evaluamos la condición lógica (t_tipo == 'woocommerce') para controlar el flujo
                if t_tipo == "woocommerce":
                    # Asignamos 'params' con {'per_page': min(limite_por_tienda, 100), ...
                    params = {"per_page": min(limite_por_tienda, 100), "page": pag}
                else:
                    # Asignamos 'params' con {'limit': min(limite_por_tienda, 250), 'pa...
                    params = {"limit": min(limite_por_tienda, 250), "page": pag}

                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Asignamos 'res' con None
                    res = None
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                        res = session.get(t_endpoint, params=params, headers=headers, timeout=10)
                    except Exception as ex_req:
                        # Registro de evento diagnóstico en la bitácora (logger) del sistema
                        logger.debug(f"Petición inicial con requests falló ({ex_req}), probando con curl_cffi...")

                    # Evaluamos la condición lógica ((res is None or res.status_code in (403, 429)) and c...) para controlar el flujo
                    if (res is None or res.status_code in (403, 429)) and curl_requests is not None:
                        # Bloque try/except para manejo seguro de errores y resiliencia operativa
                        try:
                            # Asignamos 's_cffi' con curl_requests.Session(impersonate='chrome1...
                            s_cffi = curl_requests.Session(impersonate="chrome124")
                            # Asignamos 'res_cffi' con s_cffi.get(t_endpoint, params=params, head...
                            res_cffi = s_cffi.get(t_endpoint, params=params, headers=headers, timeout=15)
                            # Evaluamos la condición lógica (res_cffi.status_code == 200) para controlar el flujo
                            if res_cffi.status_code == 200:
                                # Asignamos 'res' con res_cffi
                                res = res_cffi
                        except Exception as ex_cffi:
                            # Registro de evento diagnóstico en la bitácora (logger) del sistema
                            logger.debug(f"curl_cffi falló: {ex_cffi}")

                    # Evaluamos la condición lógica (res is None or res.status_code != 200) para controlar el flujo
                    if res is None or res.status_code != 200:
                        # Asignamos 'code_show' con res.status_code if res is not None else 'E...
                        code_show = res.status_code if res is not None else "Error de Conexión"
                        # Registro de evento diagnóstico en la bitácora (logger) del sistema
                        logger.warning(f"Respuesta HTTP {code_show} en {t_nombre} (pág {pag})")
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break

                    # Asignamos 'data' con res.json()
                    data = res.json()
                    # Evaluamos la condición lógica (t_tipo == 'woocommerce') para controlar el flujo
                    if t_tipo == "woocommerce":
                        # Asignamos 'productos' con data if isinstance(data, list) else []
                        productos = data if isinstance(data, list) else []
                    else:
                        # Asignamos 'productos' con data.get('products', []) if isinstance(dat...
                        productos = data.get("products", []) if isinstance(data, dict) else []

                    # Evaluamos la condición lógica (not productos) para controlar el flujo
                    if not productos:
                        # Registro de evento diagnóstico en la bitácora (logger) del sistema
                        logger.info(f"Fin del catálogo en {t_nombre} en página {pag}.")
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break

                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.info(f"Procesando lote de {len(productos)} productos en {t_nombre} (pág {pag})...")

                    # Recorremos iterativamente cada 'prod' en productos
                    for prod in productos:
                        # Actualizamos acumulativamente el valor de 'total_procesados'
                        total_procesados += 1
                        # Evaluamos la condición lógica (t_tipo == 'woocommerce') para controlar el flujo
                        if t_tipo == "woocommerce":
                            # Asignamos 'raw_title' con html.unescape(prod.get('name', '')).strip()
                            raw_title = html.unescape(prod.get("name", "")).strip()
                            # Asignamos 'wc_brands' con [html.unescape(b.get('name', '')).strip() ...
                            wc_brands = [html.unescape(b.get("name", "")).strip() for b in prod.get("brands", []) if b.get("name")]
                            # Asignamos 'raw_vendor' con wc_brands[0] if wc_brands else ''
                            raw_vendor = wc_brands[0] if wc_brands else ""
                            # Evaluamos la condición lógica (not raw_vendor) para controlar el flujo
                            if not raw_vendor:
                                # Recorremos iterativamente cada 'c' en prod.get('categories', [])
                                for c in prod.get("categories", []):
                                    # Asignamos 'c_name' con html.unescape(c.get('name', '')).strip()
                                    c_name = html.unescape(c.get("name", "")).strip()
                                    # Evaluamos la condición lógica (c_name.lower() not in ('perfumes', 'perfume', 'hombr...) para controlar el flujo
                                    if c_name.lower() not in ("perfumes", "perfume", "hombre", "hombres", "mujer", "mujeres", "unisex", "nicho", "diseñador", "ofertas", "destacados", "inicio"):
                                        # Asignamos 'm_can' con normalizar_marca_canonica(c_name)
                                        m_can = normalizar_marca_canonica(c_name)
                                        # Evaluamos la condición lógica (m_can and m_can not in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
                                        if m_can and m_can not in MARCAS_INVALIDAS_CATALOGO:
                                            # Asignamos 'raw_vendor' con m_can
                                            raw_vendor = m_can
                                            # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                            break
                            # Asignamos 'tags' con []
                            tags = []
                            # Asignamos 'url_producto' con prod.get('permalink', '')
                            url_producto = prod.get("permalink", "")
                            # Asignamos 'images' con prod.get('images', [])
                            images = prod.get("images", [])
                            # Asignamos 'img_url' con images[0].get('src', '') if images else ''
                            img_url = images[0].get("src", "") if images else ""
                            # Asignamos 'prices_wc' con prod.get('prices', {})
                            prices_wc = prod.get("prices", {})
                            # Asignamos 'wc_price' con clean_digits(prices_wc.get('price'))
                            wc_price = clean_digits(prices_wc.get("price"))
                            # Asignamos 'wc_reg' con clean_digits(prices_wc.get('regular_price'))
                            wc_reg = clean_digits(prices_wc.get("regular_price"))
                            # Asignamos 'wc_stock' con bool(prod.get('is_in_stock', True))
                            wc_stock = bool(prod.get("is_in_stock", True))
                            # Asignamos 'formato_prod' con detectar_formato_oferta(raw_title, url_pro...
                            formato_prod = detectar_formato_oferta(raw_title, url_producto)
                            # Asignamos 'vol_ml_wc' con extraer_volumen_ml_opcional(raw_title) or ...
                            vol_ml_wc = extraer_volumen_ml_opcional(raw_title) or extraer_volumen_ml_opcional(url_producto)
                            # Asignamos 'variants' con [{'price': wc_price, 'compare_at_price': w...
                            variants = [{"price": wc_price, "compare_at_price": wc_reg if wc_reg > wc_price else None, "available": wc_stock, "title": f"{vol_ml_wc}ml" if vol_ml_wc else ""}]
                        else:
                            # Asignamos 'raw_title' con html.unescape(prod.get('title', '')).strip()
                            raw_title = html.unescape(prod.get("title", "")).strip()
                            # Asignamos 'raw_vendor' con html.unescape((prod.get('vendor', '') or '...
                            raw_vendor = html.unescape((prod.get("vendor", "") or "").strip())
                            # Asignamos 'tags' con prod.get('tags', [])
                            tags = prod.get("tags", [])
                            # Asignamos 'url_producto' con f"{t_url_base}/products/{prod.get('handle'...
                            url_producto = f"{t_url_base}/products/{prod.get('handle', '')}"
                            # Asignamos 'images' con prod.get('images', [])
                            images = prod.get("images", [])
                            # Asignamos 'img_url' con images[0].get('src', '') if images else ''
                            img_url = images[0].get("src", "") if images else ""
                            # Asignamos 'formato_prod' con detectar_formato_oferta(raw_title, url_pro...
                            formato_prod = detectar_formato_oferta(raw_title, url_producto)
                            # Asignamos 'variants' con prod.get('variants', [])
                            variants = prod.get("variants", [])

                        # Descartar clones/inspiraciones notorios
                        if any(c in (raw_vendor or "").lower() for c in ("loris", "martin lion", "aroma d'or", "volare")):
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Evaluamos la condición lógica (any((w in raw_title.lower() for w in ('inspiracion',...) para controlar el flujo
                        if any(w in raw_title.lower() for w in ("inspiracion", "inspiración", "inspirado en", "tipo sauvage", "tipo invictus")):
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Asignamos 'marca' con normalizar_marca_canonica(raw_vendor) if l...
                        marca = normalizar_marca_canonica(raw_vendor) if len(raw_vendor) > 1 else ""
                        # Evaluamos la condición lógica (not marca or marca in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
                        if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                            # Recorremos iterativamente cada 'b_cand' en sorted(CANONICAL_BRAND_MAP.keys(), key=len...
                            for b_cand in sorted(CANONICAL_BRAND_MAP.keys(), key=len, reverse=True):
                                # Evaluamos la condición lógica (re.search('\\b' + re.escape(b_cand) + '\\b', raw_tit...) para controlar el flujo
                                if re.search(r'\b' + re.escape(b_cand) + r'\b', raw_title.lower()):
                                    # Asignamos 'marca' con CANONICAL_BRAND_MAP[b_cand]
                                    marca = CANONICAL_BRAND_MAP[b_cand]
                                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                    break

                        # Si no hay marca canónica verificada, descartar producto (sin evidencia de identidad)
                        if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # 1. Filtro estricto de productos que no son fragancias embotelladas (>= 25 ml)
                        if not es_producto_perfume_valido(raw_title, tags, marca=marca, volumen_min_ml=25):
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Asignamos 'nombre_limpio' con limpiar_nombre_perfume(raw_title, marca)
                        nombre_limpio = limpiar_nombre_perfume(raw_title, marca)
                        # Evaluamos la condición lógica (not nombre_limpio or len(nombre_limpio.strip()) < 2) para controlar el flujo
                        if not nombre_limpio or len(nombre_limpio.strip()) < 2:
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Asignamos 'concentracion' con extraer_concentracion(raw_title)
                        concentracion = extraer_concentracion(raw_title)
                        # Asignamos 'genero' con extraer_genero(raw_title)
                        genero = extraer_genero(raw_title)
                        # Asignamos 'arabe_flag' con 1 if es_arabe(marca, nombre_limpio) else 0
                        arabe_flag = 1 if es_arabe(marca, nombre_limpio) else 0

                        # Evaluamos la condición lógica (not variants) para controlar el flujo
                        if not variants:
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Pre-filtrar solo variantes válidas (>= 25 ml y precio comercial sano)
                        variantes_validas: List[Dict[str, Any]] = []
                        # Recorremos iterativamente cada 'v' en variants
                        for v in variants:
                            # Asignamos 'v_price' con int(float(v.get('price', 0)))
                            v_price = int(float(v.get("price", 0)))
                            # Evaluamos la condición lógica (not es_precio_valido(v_price)) para controlar el flujo
                            if not es_precio_valido(v_price):
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue
                            # Asignamos 'v_title' con v.get('title', '')
                            v_title = v.get("title", "")
                            # Asignamos 'es_tst_disc' con formato_prod == 'tester' or detectar_forma...
                            es_tst_disc = (formato_prod == "tester" or detectar_formato_oferta(f"{raw_title} {v_title}", url_producto) == "tester")
                            # Asignamos 'vol_ml' con resolver_volumen_oferta(titulo_variante=v_...
                            vol_ml = resolver_volumen_oferta(
                                titulo_variante=v_title,
                                titulo_producto=raw_title,
                                url_slug=url_producto,
                                n_variantes_producto=len(variants),
                                es_tester=es_tst_disc,
                            )
                            # Evaluamos la condición lógica (not vol_ml or vol_ml < 25) para controlar el flujo
                            if not vol_ml or vol_ml < 25:
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue
                            # Asignamos 'v_compare_raw' con v.get('compare_at_price')
                            v_compare_raw = v.get("compare_at_price")
                            # Asignamos 'v_compare' con int(float(v_compare_raw)) if v_compare_raw...
                            v_compare = int(float(v_compare_raw)) if (v_compare_raw and float(v_compare_raw) > v_price) else None
                            # Asignamos 'v_avail' con v.get('available')
                            v_avail = v.get("available")
                            # Asignamos 'v_stock' con bool(v_avail) if v_avail is not None else ...
                            v_stock = bool(v_avail) if v_avail is not None else True
                            # Asignamos 'v_fmt' con detectar_formato_oferta(f'{raw_title} {v_t...
                            v_fmt = detectar_formato_oferta(f"{raw_title} {v_title}", url_producto) if formato_prod == "regular" else formato_prod
                            # Ejecutamos instrucción: variantes_validas.append({'price': v_price, 'compare...
                            variantes_validas.append({
                                "price": v_price,
                                "compare": v_compare,
                                "stock": v_stock,
                                "vol": vol_ml,
                                "formato": v_fmt,
                            })

                        # Evaluamos la condición lógica (not variantes_validas) para controlar el flujo
                        if not variantes_validas:
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Asignamos 'primer_precio' con variantes_validas[0]['price']
                        primer_precio = variantes_validas[0]["price"]
                        # Asignamos 'canon_key' con _perfume_canon_key(marca, nombre_limpio, c...
                        canon_key = _perfume_canon_key(marca, nombre_limpio, concentracion)
                        # Asignamos 'es_nuevo' con False
                        es_nuevo = False

                        # -----------------------------------------------------
                        # 3. GESTIÓN CANÓNICA DEL PERFUME EN SUPABASE (SIN GÉNERO EN CLAVE)
                        # -----------------------------------------------------
                        perfume_id_sb, genero_res_sb, conflicto_sb = _resolver_id_en_mapa(sb_perfumes_conocidos, canon_key, genero)
                        # Evaluamos la condición lógica (not perfume_id_sb and supabase_activo and sb) para controlar el flujo
                        if not perfume_id_sb and supabase_activo and sb:
                            # Bloque try/except para manejo seguro de errores y resiliencia operativa
                            try:
                                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                                chk_p = (
                                    sb.table("perfumes")
                                    .select("id, genero")
                                    .ilike("marca", marca)
                                    .ilike("nombre", nombre_limpio)
                                    .ilike("tipo", concentracion)
                                    .execute()
                                )
                                # Recorremos iterativamente cada 'row_c' en chk_p.data or []
                                for row_c in (chk_p.data or []):
                                    # Asignamos '(es_c, g_res)' con generos_compatibles(row_c.get('genero'), g...
                                    es_c, g_res = generos_compatibles(row_c.get("genero"), genero)
                                    # Evaluamos la condición lógica (es_c) para controlar el flujo
                                    if es_c:
                                        # Asignamos 'perfume_id_sb' con row_c['id']
                                        perfume_id_sb = row_c["id"]
                                        # Asignamos 'genero_res_sb' con g_res
                                        genero_res_sb = g_res
                                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                        break
                                # Evaluamos la condición lógica (not perfume_id_sb) para controlar el flujo
                                if not perfume_id_sb:
                                    # Asignamos 'img_url_final' con img_url
                                    img_url_final = img_url
                                    # Evaluamos la condición lógica (subir_imagenes) para controlar el flujo
                                    if subir_imagenes:
                                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                                        img_url_final = subir_imagen_a_bucket_supabase(
                                            session=session,
                                            img_url=img_url,
                                            nombre_perfume=nombre_limpio,
                                            sb_client=sb if supabase_activo else None,
                                        )

                                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                                    nuevo_p = sb.table("perfumes").insert({
                                        "nombre": nombre_limpio,
                                        "marca": marca,
                                        "genero": normalizar_genero(genero) or "Unisex",
                                        "tipo": concentracion,
                                        "notas": "Notas aromáticas exclusivas",
                                        "imagen_url": img_url_final,
                                        "es_arabe": bool(arabe_flag),
                                        "en_tendencia": True,
                                        "en_remate": False,
                                        "precio_referencia": primer_precio,
                                    }).execute()
                                    # Evaluamos la condición lógica (nuevo_p.data) para controlar el flujo
                                    if nuevo_p.data:
                                        # Asignamos 'perfume_id_sb' con nuevo_p.data[0]['id']
                                        perfume_id_sb = nuevo_p.data[0]["id"]
                                        # Asignamos 'es_nuevo' con True
                                        es_nuevo = True

                                # Evaluamos la condición lógica (perfume_id_sb) para controlar el flujo
                                if perfume_id_sb:
                                    # Ejecutamos instrucción: sb_perfumes_conocidos.setdefault(canon_key, []).appe...
                                    sb_perfumes_conocidos.setdefault(canon_key, []).append(
                                        (perfume_id_sb, genero_res_sb or normalizar_genero(genero) or "Unisex")
                                    )
                            except Exception as e:
                                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                                logger.warning(f"Error guardando perfume {nombre_limpio} en Supabase: {e}")

                        # -----------------------------------------------------
                        # 4. GESTIÓN CANÓNICA DEL PERFUME EN SQLITE (COMPATIBILIDAD DE GÉNERO)
                        # -----------------------------------------------------
                        perfume_id_sqlite, genero_res_sq, _ = _resolver_id_en_mapa(sqlite_perfumes_map, canon_key, genero)
                        # Evaluamos la condición lógica (not perfume_id_sqlite) para controlar el flujo
                        if not perfume_id_sqlite:
                            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                            cursor.execute(
                                """
                                SELECT id, genero FROM perfumes
                                WHERE LOWER(TRIM(marca)) = LOWER(?)
                                  AND LOWER(TRIM(nombre)) = LOWER(?)
                                  AND LOWER(COALESCE(TRIM(tipo), '')) = LOWER(?);
                                """,
                                (marca, nombre_limpio, concentracion),
                            )
                            # Asignamos 'rows_sq' con cursor.fetchall()
                            rows_sq = cursor.fetchall()
                            # Recorremos iterativamente cada 'r_sq' en rows_sq
                            for r_sq in rows_sq:
                                # Asignamos '(es_c, g_res)' con generos_compatibles(r_sq['genero'], genero)
                                es_c, g_res = generos_compatibles(r_sq["genero"], genero)
                                # Evaluamos la condición lógica (es_c) para controlar el flujo
                                if es_c:
                                    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                                    perfume_id_sqlite = r_sq["id"]
                                    # Asignamos 'genero_res_sq' con g_res
                                    genero_res_sq = g_res
                                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                    break

                            # Evaluamos la condición lógica (not perfume_id_sqlite) para controlar el flujo
                            if not perfume_id_sqlite:
                                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                                cursor.execute("""
                                INSERT INTO perfumes (
                                    nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia
                                )
                                VALUES (?, ?, ?, ?, 'Notas aromáticas exclusivas', ?, ?, 1, 0, ?);
                                """, (nombre_limpio, marca, normalizar_genero(genero) or "Unisex", concentracion, img_url, arabe_flag, primer_precio))
                                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                                perfume_id_sqlite = cursor.lastrowid
                                # Asignamos 'es_nuevo' con True
                                es_nuevo = True

                            # Evaluamos la condición lógica (perfume_id_sqlite) para controlar el flujo
                            if perfume_id_sqlite:
                                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                                sqlite_perfumes_map.setdefault(canon_key, []).append(
                                    (perfume_id_sqlite, genero_res_sq or normalizar_genero(genero) or "Unisex")
                                )

                        # Evaluamos la condición lógica (es_nuevo) para controlar el flujo
                        if es_nuevo:
                            # Actualizamos acumulativamente el valor de 'nuevos_perfumes'
                            nuevos_perfumes += 1
                            # Ejecutamos instrucción: muestras_descubiertas.append({'nombre': nombre_limpi...
                            muestras_descubiertas.append({
                                "nombre": nombre_limpio,
                                "marca": marca,
                                "tipo": concentracion,
                                "es_arabe": bool(arabe_flag),
                                "tienda": t_nombre,
                                "precio": primer_precio,
                            })
                            # Registro de evento diagnóstico en la bitácora (logger) del sistema
                            logger.info(f"NUEVO PERFUME DESCUBIERTO: {nombre_limpio} ({marca}) - ${primer_precio:,}")

                        # -----------------------------------------------------
                        # 5. INGESTA DE VARIANTES Y PRECIOS POR VOLUMEN Y FORMATO
                        # -----------------------------------------------------
                        for v_item in variantes_validas:
                            # Asignamos 'v_price' con v_item['price']
                            v_price = v_item["price"]
                            # Asignamos 'v_compare' con v_item['compare']
                            v_compare = v_item["compare"]
                            # Asignamos 'v_stock' con v_item['stock']
                            v_stock = v_item["stock"]
                            # Asignamos 'volumen_ml' con v_item['vol']
                            volumen_ml = v_item["vol"]
                            # Asignamos 'v_fmt' con v_item['formato']
                            v_fmt = v_item["formato"]

                            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                            var_id_sb = sb_variantes_conocidas.get((perfume_id_sb, volumen_ml, v_fmt)) if perfume_id_sb else None

                            # Bloque try/except para manejo seguro de errores y resiliencia operativa
                            try:
                                # Asignamos 'res_obs' con registrar_observacion_oferta({'perfume_id'...
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
                                # Actualizamos acumulativamente el valor de 'precios_registrados'
                                precios_registrados += 1
                                # Evaluamos la condición lógica (perfume_id_sb and (not var_id_sb) and res_obs and is...) para controlar el flujo
                                if perfume_id_sb and not var_id_sb and res_obs and isinstance(res_obs, dict) and res_obs.get("variante_id"):
                                    # Asignamos 'sb_variantes_conocidas[perfume_i...' con res_obs['variante_id']
                                    sb_variantes_conocidas[(perfume_id_sb, volumen_ml, v_fmt)] = res_obs["variante_id"]
                            except Exception as ex_obs:
                                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                                logger.debug(f"Aviso registrando oferta de {nombre_limpio} ({volumen_ml}ml): {ex_obs}")

                except Exception as e:
                    # Asignamos 'err_msg' con f'Fallo procesando {t_nombre} página {pag}...
                    err_msg = f"Fallo procesando {t_nombre} página {pag}: {e}"
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.error(err_msg)
                    # Ejecutamos instrucción: errores.append(err_msg)
                    errores.append(err_msg)

                # Ejecutamos instrucción: time.sleep(0.3)
                time.sleep(0.3)

    # Asignamos 'duracion' con round(time.time() - inicio, 2)
    duracion = round(time.time() - inicio, 2)
    # Asignamos 'estado' con 'EXITOSO' if not errores else 'DEGRADADO' ...
    estado = "EXITOSO" if not errores else ("DEGRADADO" if precios_registrados > 0 else "FALLIDO")

    # Ejecutamos instrucción: finalizar_scraping_run(run_id=run_id, estado='comple...
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
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
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
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.debug(f"No se pudo guardar scraping_log en Supabase: {e}")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
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

    # Ejecutamos instrucción: guardar_reporte_descubrimiento(reporte)
    guardar_reporte_descubrimiento(reporte)
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Ciclo completado en {duracion}s | {nuevos_perfumes} perfumes nuevos descubiertos | {precios_registrados} precios registrados.")
    # Retornamos el resultado procesado (reporte)
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
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'inicio' con time.time()
    inicio = time.time()
    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Asignamos 'perfumes_conocidos' con {}
    perfumes_conocidos: Dict[Tuple[str, str, str], Set[str]] = {}
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    supabase_activo = is_supabase_disponible()

    # Evaluamos la condición lógica (supabase_activo and sb) para controlar el flujo
    if supabase_activo and sb:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'offset' con 0
            offset = 0
            # Ejecutamos el ciclo mientras se mantenga la condición: True
            while True:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                res = sb.table("perfumes").select("marca, nombre, tipo, genero").range(offset, offset + 999).execute()
                # Evaluamos la condición lógica (not res.data) para controlar el flujo
                if not res.data:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Recorremos iterativamente cada 'r' en res.data
                for r in res.data:
                    # Asignamos 'm' con (normalizar_marca_canonica(r.get('marca') ...
                    m = (normalizar_marca_canonica(r.get("marca") or "") or "").strip().lower()
                    # Asignamos 'n' con (limpiar_nombre_perfume(r.get('nombre') or...
                    n = (limpiar_nombre_perfume(r.get("nombre") or "", r.get("marca") or "") or "").strip().lower()
                    # Asignamos 't_c' con (r.get('tipo') or 'Eau de Parfum').strip()...
                    t_c = (r.get("tipo") or "Eau de Parfum").strip().lower()
                    # Asignamos 'g_c' con normalizar_genero(r.get('genero')) or 'Uni...
                    g_c = normalizar_genero(r.get("genero")) or "Unisex"
                    # Evaluamos la condición lógica (m and n) para controlar el flujo
                    if m and n:
                        # Ejecutamos instrucción: perfumes_conocidos.setdefault((m, n, t_c), set()).ad...
                        perfumes_conocidos.setdefault((m, n, t_c), set()).add(g_c)
                # Evaluamos la condición lógica (len(res.data) < 1000) para controlar el flujo
                if len(res.data) < 1000:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Actualizamos acumulativamente el valor de 'offset'
                offset += 1000
        except Exception as e_sb:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Aviso consultando perfumes conocidos en Supabase: {e_sb}")

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Gestión automática de contexto y recursos para: get_db_cursor()
        with get_db_cursor() as cur:
            # Ejecutamos instrucción: cur.execute('SELECT marca, nombre, tipo, genero FROM...
            cur.execute("SELECT marca, nombre, tipo, genero FROM perfumes;")
            # Recorremos iterativamente cada 'r' en cur.fetchall()
            for r in cur.fetchall():
                # Asignamos 'm' con (normalizar_marca_canonica(r['marca'] or '...
                m = (normalizar_marca_canonica(r["marca"] or "") or "").strip().lower()
                # Asignamos 'n' con (limpiar_nombre_perfume(r['nombre'] or '',...
                n = (limpiar_nombre_perfume(r["nombre"] or "", r["marca"] or "") or "").strip().lower()
                # Asignamos 't_c' con (r['tipo'] or 'Eau de Parfum').strip().low...
                t_c = (r["tipo"] or "Eau de Parfum").strip().lower()
                # Asignamos 'g_c' con normalizar_genero(r['genero']) or 'Unisex'
                g_c = normalizar_genero(r["genero"]) or "Unisex"
                # Evaluamos la condición lógica (m and n) para controlar el flujo
                if m and n:
                    # Ejecutamos instrucción: perfumes_conocidos.setdefault((m, n, t_c), set()).ad...
                    perfumes_conocidos.setdefault((m, n, t_c), set()).add(g_c)
    except Exception as e_sq:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        logger.warning(f"Aviso consultando perfumes conocidos en SQLite: {e_sq}")

    # Asignamos 'total_analizados' con 0
    total_analizados = 0
    # Asignamos 'descartados_no_perfume' con 0
    descartados_no_perfume = 0
    # Asignamos 'nuevos_descubiertos' con 0
    nuevos_descubiertos = 0
    # Asignamos 'precios_variantes_registrados' con 0
    precios_variantes_registrados = 0
    # Asignamos 'muestras' con []
    muestras: List[Dict[str, Any]] = []
    # Asignamos 'errores' con []
    errores: List[str] = []

    # Recorremos iterativamente cada '(tienda_slug, cat)' en cache_tiendas_bulk.items()
    for tienda_slug, cat in cache_tiendas_bulk.items():
        # Asignamos 'tienda_nombre' con getattr(cat, 'nombre_tienda', tienda_slug)
        tienda_nombre = getattr(cat, "nombre_tienda", tienda_slug)
        # Asignamos 'nuevos_en_tienda' con 0
        nuevos_en_tienda = 0
        # Asignamos 'items' con getattr(cat, 'todos_items', [])
        items = getattr(cat, "todos_items", [])

        # Recorremos iterativamente cada 'item' en items
        for item in items:
            # Actualizamos acumulativamente el valor de 'total_analizados'
            total_analizados += 1
            # Asignamos 'raw_title' con item.get('title', '')
            raw_title = item.get("title", "")
            # Asignamos 'raw_vendor' con item.get('vendor', '')
            raw_vendor = item.get("vendor", "")
            # Asignamos 'item_url' con item.get('url', '')
            item_url = item.get("url", "")
            # Asignamos 'img_url' con item.get('imagen_url', '')
            img_url = item.get("imagen_url", "")
            # Asignamos 'formato' con item.get('formato', 'regular')
            formato = item.get("formato", "regular")

            # Filtro 1: Clones e imitaciones
            if any(c in (raw_vendor or "").lower() for c in ("loris", "martin lion", "aroma d'or", "volare")):
                # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                descartados_no_perfume += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Evaluamos la condición lógica (any((w in raw_title.lower() for w in ('inspiracion',...) para controlar el flujo
            if any(w in raw_title.lower() for w in ("inspiracion", "inspiración", "inspirado en", "tipo sauvage", "tipo invictus")):
                # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                descartados_no_perfume += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Filtro 2: Marca canónica verificada
            marca = item.get("marca") or normalizar_marca_canonica(raw_vendor)
            # Evaluamos la condición lógica (not marca or marca in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
            if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                # Recorremos iterativamente cada '(b_cand, b_canon)' en sorted(CANONICAL_BRAND_MAP.items(), key=la...
                for b_cand, b_canon in sorted(CANONICAL_BRAND_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                    # Evaluamos la condición lógica (re.search('\\b' + re.escape(b_cand) + '\\b', raw_tit...) para controlar el flujo
                    if re.search(r'\b' + re.escape(b_cand) + r'\b', raw_title.lower()):
                        # Asignamos 'marca' con b_canon
                        marca = b_canon
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break

            # Evaluamos la condición lógica (not marca or marca in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
            if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
                # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                descartados_no_perfume += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Filtro 3: Validación estricta de perfume (>=25ml, sin cosméticos ni desodorantes)
            if not es_producto_perfume_valido(raw_title, marca=marca, volumen_min_ml=25):
                # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                descartados_no_perfume += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Filtro 4: Nombre canónico limpio
            nombre_limpio = limpiar_nombre_perfume(raw_title, marca)
            # Evaluamos la condición lógica (not nombre_limpio or len(nombre_limpio.strip()) < 2) para controlar el flujo
            if not nombre_limpio or len(nombre_limpio.strip()) < 2:
                # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                descartados_no_perfume += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Asignamos 'conc_item' con (extraer_concentracion(raw_title) or 'Eau ...
            conc_item = (extraer_concentracion(raw_title) or "Eau de Parfum").strip()
            # Asignamos 'gen_item' con normalizar_genero(extraer_genero(raw_title...
            gen_item = normalizar_genero(extraer_genero(raw_title)) or "Unisex"
            # Asignamos 'clave_canon' con (marca.strip().lower(), nombre_limpio.stri...
            clave_canon = (marca.strip().lower(), nombre_limpio.strip().lower(), conc_item.lower())
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            generos_existentes = perfumes_conocidos.get(clave_canon, set())
            # Evaluamos la condición lógica (any((generos_compatibles(g_ex, gen_item)[0] for g_ex...) para controlar el flujo
            if any(generos_compatibles(g_ex, gen_item)[0] for g_ex in generos_existentes):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Evaluamos la condición lógica (nuevos_en_tienda >= limite_nuevos_por_tienda) para controlar el flujo
            if nuevos_en_tienda >= limite_nuevos_por_tienda:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break

            # Filtro 5: Variantes válidas con precio comercial
            variants = item.get("variants", [])
            # Asignamos 'var_valida' con None
            var_valida = None
            # Recorremos iterativamente cada 'v' en variants
            for v in variants:
                # Asignamos 'p_val' con clean_digits(v.get('price'))
                p_val = clean_digits(v.get("price"))
                # Evaluamos la condición lógica (es_precio_valido(p_val) and p_val >= 4000) para controlar el flujo
                if es_precio_valido(p_val) and p_val >= 4000:
                    # Asignamos 'v_title' con v.get('title', '')
                    v_title = v.get("title", "")
                    # Asignamos 'es_tst_b' con formato == 'tester' or detectar_formato_of...
                    es_tst_b = (formato == "tester" or detectar_formato_oferta(f"{raw_title} {v_title}", item_url) == "tester")
                    # Asignamos 'vol_cand' con resolver_volumen_oferta(titulo_variante=v_...
                    vol_cand = resolver_volumen_oferta(
                        titulo_variante=v_title,
                        titulo_producto=raw_title,
                        url_slug=item_url,
                        n_variantes_producto=len(variants),
                        es_tester=es_tst_b,
                    )
                    # Evaluamos la condición lógica (vol_cand and vol_cand >= 25) para controlar el flujo
                    if vol_cand and vol_cand >= 25:
                        # Asignamos 'var_valida' con (v, p_val, vol_cand)
                        var_valida = (v, p_val, vol_cand)
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break

            # Evaluamos la condición lógica (not var_valida) para controlar el flujo
            if not var_valida:
                # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                descartados_no_perfume += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Asignamos '(v_dict, p_act, vol_ml)' con var_valida
            v_dict, p_act, vol_ml = var_valida
            # Asignamos 'p_norm_raw' con clean_digits(v_dict.get('compare_at_price'))
            p_norm_raw = clean_digits(v_dict.get("compare_at_price"))
            # Asignamos 'p_norm' con p_norm_raw if p_norm_raw and p_norm_raw > ...
            p_norm = p_norm_raw if (p_norm_raw and p_norm_raw > p_act) else p_act
            # Asignamos 'in_stock' con bool(v_dict.get('available', True))
            in_stock = bool(v_dict.get("available", True))
            # Asignamos 'concentracion' con extraer_concentracion(raw_title) or 'Eau d...
            concentracion = extraer_concentracion(raw_title) or "Eau de Parfum"
            # Asignamos 'genero' con extraer_genero(raw_title) or 'Unisex'
            genero = extraer_genero(raw_title) or "Unisex"
            # Asignamos 'arabe_flag' con 1 if es_arabe(marca, nombre_limpio) else 0
            arabe_flag = 1 if es_arabe(marca, nombre_limpio) else 0

            # Ingesta en base de datos
            try:
                # Asignamos 'res_ing' con guardar_o_actualizar_perfume_scraped(nombr...
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
                # Evaluamos la condición lógica (res_ing.get('exito')) para controlar el flujo
                if res_ing.get("exito"):
                    # Actualizamos acumulativamente el valor de 'nuevos_descubiertos'
                    nuevos_descubiertos += 1
                    # Actualizamos acumulativamente el valor de 'nuevos_en_tienda'
                    nuevos_en_tienda += 1
                    # Actualizamos acumulativamente el valor de 'precios_variantes_registrados'
                    precios_variantes_registrados += 1
                    # Ejecutamos instrucción: perfumes_conocidos.setdefault(clave_canon, set()).ad...
                    perfumes_conocidos.setdefault(clave_canon, set()).add(gen_item)
                    # Ejecutamos instrucción: muestras.append({'nombre': nombre_limpio, 'marca': m...
                    muestras.append({
                        "nombre": nombre_limpio,
                        "marca": marca,
                        "tipo": concentracion,
                        "es_arabe": bool(arabe_flag),
                        "tienda": tienda_nombre,
                        "precio": p_act,
                        "volumen_ml": vol_ml,
                    })
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.info(f"✨ [DESCUBRIMIENTO BULK] Nuevo perfume: {nombre_limpio} ({marca}) en {tienda_nombre} - ${p_act:,}")
            except Exception as ex_ing:
                # Asignamos 'err_msg' con f'Error ingesta descubrimiento para {nombr...
                err_msg = f"Error ingesta descubrimiento para {nombre_limpio} ({marca}): {ex_ing}"
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.warning(err_msg)
                # Ejecutamos instrucción: errores.append(err_msg)
                errores.append(err_msg)

    # Asignamos 'duracion' con round(time.time() - inicio, 2)
    duracion = round(time.time() - inicio, 2)
    # Asignamos 'estado' con 'EXITOSO' if not errores else 'DEGRADADO' ...
    estado = "EXITOSO" if not errores else ("DEGRADADO" if nuevos_descubiertos > 0 else "FALLIDO")

    # Asignamos 'reporte' con {'metadata': {'version': '3.3.0 (In-Memory...
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

    # Ejecutamos instrucción: guardar_reporte_descubrimiento(reporte, ruta_destino...
    guardar_reporte_descubrimiento(reporte, ruta_destino=reporte_path)
    # Retornamos el resultado procesado (reporte)
    return reporte


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Scraper Autónomo de Perfumes (PerfumeTrending.cl)")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--limit", type=int, default=250, help="Límite de productos por página (default: 250)")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--pages", type=int, default=2, help="Páginas a rastrear por tienda (default: 2)")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--upload-images", action="store_true", help="Subir imágenes a Supabase Storage (más lento)")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--stores", type=str, default="all", help="Tiendas separadas por coma (ej: silk,elite,oferta)")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Asignamos 'filtro' con None if args.stores.lower() == 'all' else ...
    filtro = None if args.stores.lower() == "all" else [s.strip() for s in args.stores.split(",") if s.strip()]

    # Asignamos 'resultado' con ejecutar_descubrimiento_autonomo(limite_po...
    resultado = ejecutar_descubrimiento_autonomo(
        limite_por_tienda=args.limit,
        paginas=args.pages,
        subir_imagenes=args.upload_images,
        filtro_tiendas=filtro
    )
    # Ejecutamos instrucción: print('\n' + '=' * 60)
    print("\n" + "=" * 60)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    print("RESUMEN DE DESCUBRIMIENTO AUTÓNOMO EN SUPABASE & SQLITE:")
    # Ejecutamos instrucción: print(f"Estado: {resultado['metadata']['estado']}")
    print(f"Estado: {resultado['metadata']['estado']}")
    # Ejecutamos instrucción: print(f"Productos analizados: {resultado['metricas']...
    print(f"Productos analizados: {resultado['metricas']['total_productos_analizados']}")
    # Ejecutamos instrucción: print(f"Nuevos perfumes descubiertos: {resultado['me...
    print(f"Nuevos perfumes descubiertos: {resultado['metricas']['nuevos_perfumes_descubiertos']}")
    # Ejecutamos instrucción: print(f"Precios/Variantes registradas: {resultado['m...
    print(f"Precios/Variantes registradas: {resultado['metricas']['precios_variantes_registrados']}")
    # Ejecutamos instrucción: print(f"Duración: {resultado['metadata']['duracion_s...
    print(f"Duración: {resultado['metadata']['duracion_segundos']}s")
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)

