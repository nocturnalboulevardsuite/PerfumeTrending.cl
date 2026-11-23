"""
PerfumeTrending.cl — Motor de Scraping y Rastreo Periódico (ETL Pipeline Profesional)
======================================================================================
Servicio backend de alto rendimiento para la extracción, validación, normalización
y persistencia continua de precios y stock 100% reales en el mercado chileno.

Tiendas Soportadas:
1. Silk Perfumes (Shopify API + JSON suggest)
2. Elite Perfumes (Shopify API + JSON suggest)
3. Falabella (Next.js __NEXT_DATA__ extraction + live self-healing)
4. Paris (Schema.org JSON-LD extraction + live self-healing)
5. Ripley (Schema.org JSON-LD & DOM extraction + live self-healing)

Características de Ingeniería:
- Extracción de precios reales y descuentos genuinos (sin simulaciones ni fórmulas artificiales).
- Identificación precisa de tamaño en ml para cada comercio.
- Auto-sanación de enlaces (self-healing): Si una tienda rota el SKU (404), localiza la nueva ficha viva.
- Emulación de navegador residencial chileno (headers completos de Chrome/Edge en Santiago).
- Delays humanos aleatorios y retries exponenciales para evitar bloqueos y rate limiting.
- Resiliencia Zero-Downtime: Si un comercio está temporalmente inaccesible, preserva el último precio válido.
- Generación de informes de auditoría estructurados en data/reportes/ultimo_scraping.json.
"""

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (defaultdict) desde el módulo 'collections'
from collections import defaultdict
# Importación de componentes (ThreadPoolExecutor) desde el módulo 'concurrent.futures'
from concurrent.futures import ThreadPoolExecutor
# Importación de componentes (datetime) desde el módulo 'datetime'
from datetime import datetime
# Importación de librería estándar o dependencia externa (html)
import html
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de librería estándar o dependencia externa (math)
import math
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

# Importación de componentes (BeautifulSoup) desde el módulo 'bs4'
from bs4 import BeautifulSoup
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

# Ajuste de codificación para consola Windows
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
# Asignamos 'logger' con logging.getLogger('PerfumeScraper')
logger = logging.getLogger("PerfumeScraper")

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Evaluamos la condición lógica (BASE_DIR not in sys.path) para controlar el flujo
if BASE_DIR not in sys.path:
    # Ejecutamos instrucción: sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, BASE_DIR)
# Asignamos 'REPORTES_DIR' con os.path.join(BASE_DIR, 'data', 'reportes')
REPORTES_DIR = os.path.join(BASE_DIR, "data", "reportes")
# Asignamos 'REPORTE_ULTIMO_PATH' con os.path.join(REPORTES_DIR, 'ultimo_scrapin...
REPORTE_ULTIMO_PATH = os.path.join(REPORTES_DIR, "ultimo_scraping.json")
# Asignamos 'CACHE_DIR' con os.path.join(BASE_DIR, 'data', 'cache')
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
# Asignamos 'CIRCUIT_BREAKER_PATH' con os.path.join(CACHE_DIR, 'circuit_breaker_r...
CIRCUIT_BREAKER_PATH = os.path.join(CACHE_DIR, "circuit_breaker_retail.json")


# Definición de función 'cargar_circuit_breaker' sin parámetros externos
def cargar_circuit_breaker() -> Dict[str, Dict[str, Any]]:
    """Carga el estado persistido de backoff/circuit breaker para búsquedas dinámicas sin URL directa."""
    # Evaluamos la condición lógica (os.path.exists(CIRCUIT_BREAKER_PATH)) para controlar el flujo
    if os.path.exists(CIRCUIT_BREAKER_PATH):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Gestión automática de contexto y recursos para: open(CIRCUIT_BREAKER_PATH, 'r', encoding='utf-8')
            with open(CIRCUIT_BREAKER_PATH, "r", encoding="utf-8") as f:
                # Retornamos el resultado procesado (json.load(f))
                return json.load(f)
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.debug(f"Aviso leyendo circuit breaker: {e}")
    # Retornamos el resultado procesado ({})
    return {}


# Definición de función 'guardar_circuit_breaker' (parámetros: cb_data)
def guardar_circuit_breaker(cb_data: Dict[str, Dict[str, Any]]) -> None:
    """Persiste el estado de enfriamiento/circuit breaker en disco."""
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        # Gestión automática de contexto y recursos para: open(CIRCUIT_BREAKER_PATH, 'w', encoding='utf-8')
        with open(CIRCUIT_BREAKER_PATH, "w", encoding="utf-8") as f:
            # Procesamiento de serialización o deserialización de estructura JSON
            json.dump(cb_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.debug(f"Aviso guardando circuit breaker: {e}")


# - ¿Qué hace esta función (Circuit Breaker)?:
#   Comprueba si un perfume sin enlace directo ha fallado repetidamente (>=3 veces) en tiendas departamentales (Falabella, Paris, Ripley).
#   Si está activo, entra en período de enfriamiento (cooldown de 7 días) para omitir la búsqueda y no saturar el servidor ni gastar tiempo.
#   Implementa el estado 'Half-Open': pasados los 7 días, permite 1 reintento para comprobar si el producto ya fue incorporado al stock.
def es_circuit_breaker_activo(
    perfume_id: int,
    tienda_id: int,
    cb_data: Optional[Dict[str, Dict[str, Any]]],
    umbral_fallos: int = 3,
    dias_enfriamiento: int = 7,
) -> bool:
    """
    Retorna True si un perfume sin URL directa en esta tienda ha fallado repetidamente (>= umbral)
    y se encuentra en período de enfriamiento (cooldown de 7 días).
    Permite reintentos periódicos (half-open) una vez cumplido el plazo de enfriamiento.
    """
    # Evaluamos la condición lógica (not cb_data) para controlar el flujo
    if not cb_data:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'clave' con f'{int(perfume_id)}:{int(tienda_id)}'
    clave = f"{int(perfume_id)}:{int(tienda_id)}"
    # Asignamos 'info' con cb_data.get(clave)
    info = cb_data.get(clave)
    # Evaluamos la condición lógica (not info) para controlar el flujo
    if not info:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'fallos' con int(info.get('fallos_consecutivos', 0))
    fallos = int(info.get("fallos_consecutivos", 0))
    # Evaluamos la condición lógica (fallos < umbral_fallos) para controlar el flujo
    if fallos < umbral_fallos:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'ultimo_intento_str' con info.get('ultimo_intento')
    ultimo_intento_str = info.get("ultimo_intento")
    # Evaluamos la condición lógica (not ultimo_intento_str) para controlar el flujo
    if not ultimo_intento_str:
        # Retornamos el resultado procesado (False)
        return False
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'ultimo_dt' con datetime.fromisoformat(ultimo_intento_str)
        ultimo_dt = datetime.fromisoformat(ultimo_intento_str)
        # Evaluamos la condición lógica ((datetime.now() - ultimo_dt).total_seconds() < dias_...) para controlar el flujo
        if (datetime.now() - ultimo_dt).total_seconds() < dias_enfriamiento * 86400:
            # Retornamos el resultado procesado (True)
            return True
    except Exception:
        # Ejecutamos instrucción: pass
        pass
    # Retornamos el resultado procesado (False)
    return False


# Definición de función 'registrar_resultado_circuit_breaker' (parámetros: perfume_id, tienda_id, exito, cb_data)
def registrar_resultado_circuit_breaker(
    perfume_id: int,
    tienda_id: int,
    exito: bool,
    cb_data: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    """Actualiza el contador de fallos consecutivos o lo remueve de cooldown si se encontró oferta."""
    # Evaluamos la condición lógica (cb_data is None) para controlar el flujo
    if cb_data is None:
        # Finalizamos la ejecución de la función retornando None
        return
    # Asignamos 'clave' con f'{int(perfume_id)}:{int(tienda_id)}'
    clave = f"{int(perfume_id)}:{int(tienda_id)}"
    # Asignamos 'ahora_iso' con datetime.now().isoformat()
    ahora_iso = datetime.now().isoformat()
    # Evaluamos la condición lógica (exito) para controlar el flujo
    if exito:
        # Evaluamos la condición lógica (clave in cb_data) para controlar el flujo
        if clave in cb_data:
            # Ejecutamos instrucción: del cb_data[clave]
            del cb_data[clave]
    else:
        # Asignamos 'info' con cb_data.get(clave, {'fallos_consecutivos':...
        info = cb_data.get(clave, {"fallos_consecutivos": 0})
        # Asignamos 'info['fallos_consecutivos']' con int(info.get('fallos_consecutivos', 0)) + 1
        info["fallos_consecutivos"] = int(info.get("fallos_consecutivos", 0)) + 1
        # Asignamos 'info['ultimo_intento']' con ahora_iso
        info["ultimo_intento"] = ahora_iso
        # Asignamos 'cb_data[clave]' con info
        cb_data[clave] = info



# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (descubrir_nuevos_perfumes_desde_bulk, obtener_ultimo_reporte_descubrimiento) desde el módulo 'backend.scraper_autonomo'
    from backend.scraper_autonomo import (
        descubrir_nuevos_perfumes_desde_bulk,
        obtener_ultimo_reporte_descubrimiento,
    )
except ImportError:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (descubrir_nuevos_perfumes_desde_bulk, obtener_ultimo_reporte_descubrimiento) desde el módulo 'scraper_autonomo'
        from scraper_autonomo import (
            descubrir_nuevos_perfumes_desde_bulk,
            obtener_ultimo_reporte_descubrimiento,
        )
    except ImportError:
        # Asignamos 'descubrir_nuevos_perfumes_desde_...' con None
        descubrir_nuevos_perfumes_desde_bulk = None
        # Asignamos 'obtener_ultimo_reporte_descubrim...' con None
        obtener_ultimo_reporte_descubrimiento = None

# Importación de capa de persistencia y normalización
try:
    # Importación de componentes (_fetch_all_rows, finalizar_scraping_run, precargar_cache_variantes_supabase, guardar_o_actualizar_perfume_scraped, ...) desde el módulo 'backend.database'
    from backend.database import (
        _fetch_all_rows,
        finalizar_scraping_run,
        precargar_cache_variantes_supabase,
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        iniciar_scraping_run,
        registrar_precio,
        registrar_observacion_oferta,
        registrar_fallo_scraping,
        marcar_oferta_requiere_revision,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda,
        get_supabase,
        is_supabase_disponible,
    )
    # Importación de componentes (_GENERO_ESPERADO_CTX, CANONICAL_BRAND_MAP, MARCAS_INVALIDAS_CATALOGO, coincide_con_perfume, ...) desde el módulo 'backend.normalizador'
    from backend.normalizador import (
        _GENERO_ESPERADO_CTX,
        CANONICAL_BRAND_MAP,
        MARCAS_INVALIDAS_CATALOGO,
        coincide_con_perfume,
        coincide_entidad_detallada,
        contexto_genero_esperado,
        detectar_formato_oferta,
        detectar_precios_atipicos,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_volumen_ml,
        extraer_volumen_ml_opcional,
        normalizar_marca_canonica,
        resolver_volumen_oferta,
    )
    # Importación de componentes (TIENDAS_CRAWLER_CONFIG) desde el módulo 'backend.scraper_autonomo'
    from backend.scraper_autonomo import (
        TIENDAS_CRAWLER_CONFIG,
    )
except ImportError:
    # Importación de componentes (_fetch_all_rows, finalizar_scraping_run, precargar_cache_variantes_supabase, guardar_o_actualizar_perfume_scraped, ...) desde el módulo 'database'
    from database import (
        _fetch_all_rows,
        finalizar_scraping_run,
        precargar_cache_variantes_supabase,
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        iniciar_scraping_run,
        registrar_precio,
        registrar_observacion_oferta,
        registrar_fallo_scraping,
        marcar_oferta_requiere_revision,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda,
        get_supabase,
        is_supabase_disponible,
    )
    # Importación de componentes (_GENERO_ESPERADO_CTX, CANONICAL_BRAND_MAP, MARCAS_INVALIDAS_CATALOGO, coincide_con_perfume, ...) desde el módulo 'normalizador'
    from normalizador import (
        _GENERO_ESPERADO_CTX,
        CANONICAL_BRAND_MAP,
        MARCAS_INVALIDAS_CATALOGO,
        coincide_con_perfume,
        coincide_entidad_detallada,
        contexto_genero_esperado,
        detectar_formato_oferta,
        detectar_precios_atipicos,
        es_arabe,
        es_precio_valido,
        es_producto_perfume_valido,
        extraer_volumen_ml,
        extraer_volumen_ml_opcional,
        normalizar_marca_canonica,
        resolver_volumen_oferta,
    )
    # Importación de componentes (TIENDAS_CRAWLER_CONFIG) desde el módulo 'scraper_autonomo'
    from scraper_autonomo import (
        TIENDAS_CRAWLER_CONFIG,
    )

# Pool de User-Agents residenciales modernos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


# Definición de función 'clean_digits' (parámetros: val)
def clean_digits(val: Any) -> int:
    """Extrae únicamente los dígitos de una cadena o número ('$ 145.200' -> 145200)."""
    # Asignamos 'digits' con re.sub('[^\\d]', '', str(val))
    digits = re.sub(r"[^\d]", "", str(val))
    # Retornamos el resultado procesado (int(digits) if digits else 0)
    return int(digits) if digits else 0


# =============================================================================
# BLOQUE: CONFIGURACIÓN DE RED RESILIENTE Y EVASIÓN DE BLOQUEOS (ANTI-BOT)
# =============================================================================

def crear_sesion_robusta() -> requests.Session:
    """
    ¿Qué hace este bloque?
    Configura un cliente HTTP con reintentos automáticos (Retries) y reutilización de sockets (Connection Pooling).
    
    ¿Por qué está aquí?
    Si un comercio sufre una caída momentánea (HTTP 500, 502, 503, 504) o limita la velocidad (HTTP 429),
    la sesión reintenta hasta 3 veces esperando un tiempo exponencialmente mayor (backoff de 0.6s).
    Esto evita que un micro-corte de red haga fallar el raspado de datos.
    """
    # Asignamos 'session' con requests.Session()
    session = requests.Session()
    # Asignamos 'retry_strategy' con Retry(total=3, backoff_factor=0.6, status_...
    retry_strategy = Retry(
        total=3,                           # Máximo 3 reintentos antes de declarar fallo
        backoff_factor=0.6,                # Tiempo de espera incremental (0.6s, 1.2s, 2.4s)
        status_forcelist=[429, 500, 502, 503, 504], # Códigos de error transitorios a reintentar
        allowed_methods=["HEAD", "GET", "OPTIONS"]   # Solo métodos seguros de solo lectura
    )
    # Montamos el adaptador de reintentos tanto para HTTP como para HTTPS
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    # Ejecutamos instrucción: session.mount('https://', adapter)
    session.mount("https://", adapter)
    # Ejecutamos instrucción: session.mount('http://', adapter)
    session.mount("http://", adapter)
    # Asignamos 'proxy_url' con os.environ.get('RETAIL_PROXY_URL', '').str...
    proxy_url = os.environ.get("RETAIL_PROXY_URL", "").strip()
    # Evaluamos la condición lógica (proxy_url) para controlar el flujo
    if proxy_url:
        # Ejecutamos instrucción: session.proxies.update({'http': proxy_url, 'https': ...
        session.proxies.update({"http": proxy_url, "https": proxy_url})
    # Retornamos el resultado procesado (session)
    return session


# Umbral de cortocircuito por lote cuando un retailer bloquea por IP/ASN de datacenter
WAF_FAST_FAIL_THRESHOLD = 15

# Taxonomía controlada de motivos de fallo para observabilidad 100 % clasificada (Fase 5)
CODIGOS_FALLO_CONTROLADOS: Tuple[str, ...] = (
    "no_encontrado_en_feed",
    "waf",
    "timeout",
    "parse_error",
    "marca_excluida",
    "volumen_ambiguo",
    "entidad_no_coincide",
)


# - ¿Qué hace esta función?:
#   Ejecuta peticiones HTTP hacia tiendas departamentales (Falabella, Paris, Ripley)
#   combinando `requests.Session` y `curl_cffi` con reintentos exponenciales, jitter
#   y soporte opcional de `RETAIL_PROXY_URL`, preservando compatibilidad total con
#   sesiones simuladas (`MagicMock`) en pruebas unitarias.
def _peticion_retail_resiliente(
    session: Any,
    url: str,
    headers: Dict[str, str],
    timeout: int = 12,
    prefer_curl_cffi: bool = False,
) -> Any:
    """
    Realiza una petición GET resiliente para retailers:
    - Si `session` es un mock de prueba unitaria (`type(session) is not requests.Session`),
      delega directamente a `session.get(...)` sin tocar la red real.
    - Para Falabella (`prefer_curl_cffi=False`): usa `requests.Session` primero (100 % éxito
      verificado en GitHub Actions `probe_waf`) y recurre a `curl_cffi(chrome120)` solo ante 403/429
      fuera de Actions o con `RETAIL_PROXY_URL`.
    - Para Ripley (`prefer_curl_cffi=True`): prioriza `curl_cffi(chrome120)` con huella TLS Chrome
      y cabeceras alineadas, reintentando con backoff + jitter ante 429/5xx.
    """
    # Evaluamos la condición lógica (type(session) is not requests.Session) para controlar el flujo
    if type(session) is not requests.Session:
        # Retornamos el resultado procesado (session.get(url, headers=headers, timeout=timeout))
        return session.get(url, headers=headers, timeout=timeout)

    # Asignamos 'proxy_url' con os.environ.get('RETAIL_PROXY_URL', '').str...
    proxy_url = os.environ.get("RETAIL_PROXY_URL", "").strip()
    # Asignamos 'proxies' con {'http': proxy_url, 'https': proxy_url} if...
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    # Asignamos 'en_actions_sin_proxy' con bool(os.environ.get('GITHUB_ACTIONS')) and...
    en_actions_sin_proxy = bool(os.environ.get("GITHUB_ACTIONS")) and not proxy_url

    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    headers_cffi = {
        "Accept": headers.get("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        "Accept-Language": headers.get("Accept-Language", "es-CL,es;q=0.9,en;q=0.8"),
    }
    # Evaluamos la condición lógica (headers.get('Referer')) para controlar el flujo
    if headers.get("Referer"):
        # Asignamos 'headers_cffi['Referer']' con headers['Referer']
        headers_cffi["Referer"] = headers["Referer"]

    # Definición de función '_get_con_cffi' sin parámetros externos
    def _get_con_cffi() -> Any:
        # Asignamos 'ultimo' con None
        ultimo = None
        # Recorremos iterativamente cada 'intento' en range(2)
        for intento in range(2):
            # Gestión automática de contexto y recursos para: curl_requests.Session(impersonate='chrome120', ...
            with curl_requests.Session(impersonate="chrome120", proxies=proxies) as cs:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                ultimo = cs.get(url, headers=headers_cffi, timeout=timeout, allow_redirects=True)
            # Evaluamos la condición lógica (ultimo.status_code not in (429, 500, 502, 503, 504)) para controlar el flujo
            if ultimo.status_code not in (429, 500, 502, 503, 504):
                # Retornamos el resultado procesado (ultimo)
                return ultimo
            # Evaluamos la condición lógica (intento == 0) para controlar el flujo
            if intento == 0:
                # Ejecutamos instrucción: time.sleep(0.5 + random.uniform(0.15, 0.45))
                time.sleep(0.5 + random.uniform(0.15, 0.45))
        # Retornamos el resultado procesado (ultimo)
        return ultimo

    # Evaluamos la condición lógica (prefer_curl_cffi and curl_requests is not None) para controlar el flujo
    if prefer_curl_cffi and curl_requests is not None:
        # Retornamos el resultado procesado (_get_con_cffi())
        return _get_con_cffi()

    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
    res = session.get(url, headers=headers, timeout=timeout)
    # Evaluamos la condición lógica (res.status_code in (403, 429) and curl_requests is n...) para controlar el flujo
    if res.status_code in (403, 429) and curl_requests is not None:
        # Asignamos 'es_falabella' con 'falabella.com' in (url or '').lower()
        es_falabella = "falabella.com" in (url or "").lower()
        # Evaluamos la condición lógica (not (en_actions_sin_proxy and es_falabella)) para controlar el flujo
        if not (en_actions_sin_proxy and es_falabella):
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: time.sleep(random.uniform(0.12, 0.35))
                time.sleep(random.uniform(0.12, 0.35))
                # Asignamos 'res_cffi' con _get_con_cffi()
                res_cffi = _get_con_cffi()
                # Evaluamos la condición lógica (res_cffi is not None and res_cffi.status_code == 200) para controlar el flujo
                if res_cffi is not None and res_cffi.status_code == 200:
                    # Retornamos el resultado procesado (res_cffi)
                    return res_cffi
            except Exception as exc_cffi:
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.debug(f"Fallback curl_cffi no disponible para {url}: {exc_cffi}")
    # Retornamos el resultado procesado (res)
    return res


# Definición de función 'obtener_headers_navegador' (parámetros: referer)
def obtener_headers_navegador(referer: Optional[str] = None) -> Dict[str, str]:
    """
    ¿Qué hace este bloque?
    Genera cabeceras HTTP realistas simulando ser un usuario humano navegando desde Santiago de Chile.
    
    ¿Por qué está aquí?
    Los cortafuegos de los grandes retailers (Cloudflare, Akamai, CloudFront) bloquean peticiones que
    no envían cabeceras modernas como Sec-Ch-Ua, Accept-Language es-CL y User-Agent residencial.
    """
    # Asignamos 'headers' con {'User-Agent': random.choice(USER_AGENTS),...
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",  # Localización explícita para Chile
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",                      # Indica que es un computador de escritorio
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    # Evaluamos la condición lógica (referer) para controlar el flujo
    if referer:
        # Asignamos 'headers['Referer']' con referer
        headers["Referer"] = referer  # Simula de dónde vino el usuario (p.ej. la página principal de la tienda)
    # Retornamos el resultado procesado (headers)
    return headers


# Definición de función 'obtener_headers_json' (parámetros: referer)
def obtener_headers_json(referer: Optional[str] = None) -> Dict[str, str]:
    """
    Cabeceras específicas para consultar APIs REST y endpoints JSON internos de las tiendas (como Shopify).
    """
    # Asignamos 'headers' con {'User-Agent': random.choice(USER_AGENTS),...
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    # Evaluamos la condición lógica (referer) para controlar el flujo
    if referer:
        # Asignamos 'headers['Referer']' con referer
        headers["Referer"] = referer
    # Retornamos el resultado procesado (headers)
    return headers


# =============================================================================
# EXTRACTORES NATIVOS POR TIENDA (Puro Python, Anti-bloqueo y Alta Precisión)
# =============================================================================

# =============================================================================
# EXTRACTORES NATIVOS POR TIENDA (Puro Python, Anti-bloqueo y Alta Precisión)
# =============================================================================

TIENDAS_SHOPIFY = {
    "Silk Perfumes": "silkperfumes.cl",
    "Elite Perfumes": "eliteperfumes.cl",
    "Alisha Perfumes": "alishaperfumes.cl",
    "Yauras Perfumes": "yauras.cl",
    "Oferta Perfumes": "ofertaperfumes.cl",
    "L'Odoro": "lodoro.cl",
    "Mundo Aromas": "mundoaromas.cl",
    "Cosmetic": "cosmetic.cl",
    "Fragante": "fragante.cl",
    "ComprarEnChile": "comprarenchile.cl",
}

# Asignamos 'TIENDAS_WOOCOMMERCE' con {'Chile Perfume': 'chileperfume.cl', 'Port...
TIENDAS_WOOCOMMERCE = {
    "Chile Perfume": "chileperfume.cl",
    "Portal del Perfume": "portaldelperfume.cl",
    "Aromata": "aromata.cl",
}

# Asignamos '_DOMINIOS_SIN_WWW' con {'alishaperfumes.cl', 'yauras.cl', 'oferta...
_DOMINIOS_SIN_WWW = {
    "alishaperfumes.cl",
    "yauras.cl",
    "ofertaperfumes.cl",
    "mundoaromas.cl",
    "cosmetic.cl",
    "fragante.cl",
    "comprarenchile.cl",
    "portaldelperfume.cl",
}

# Asignamos '_SELLERS_OFICIALES_MARKETPLACE' con ('falabella', 'ripley', 'paris', 'cencosud...
_SELLERS_OFICIALES_MARKETPLACE = (
    "falabella",
    "ripley",
    "paris",
    "cencosud",
    "sodimac",
    "tottus",
    "linio",
    "dbs",
    "preunic",
    "salcobrand",
    "cruz verde",
    "silk perfumes",
    "elite perfumes",
    "alisha perfumes",
    "yauras",
    "oferta perfumes",
    "l'odoro",
    "lodoro",
    "mundo aromas",
    "cosmetic",
    "chile perfume",
    "portal del perfume",
    "fragante",
    "aromata",
    "comprarenchile",
)

# Asignamos '_SELLERS_SOSPECHOSOS' con ('alternativ', 'imitacion', 'imitación', '...
_SELLERS_SOSPECHOSOS = (
    "alternativ",
    "imitacion",
    "imitación",
    "inspiracion",
    "inspiración",
    "decant",
    "outlet",
    "generico",
    "genérico",
)


# Definición de función '_resolver_base_shopify' (parámetros: dominio)
def _resolver_base_shopify(dominio: str) -> str:
    # Asignamos 'dom' con (dominio or '').strip().lower().replace('h...
    dom = (dominio or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
    # Evaluamos la condición lógica (dom.startswith('www.')) para controlar el flujo
    if dom.startswith("www."):
        # Asignamos 'dom_bare' con dom[4:]
        dom_bare = dom[4:]
    else:
        # Asignamos 'dom_bare' con dom
        dom_bare = dom
    # Evaluamos la condición lógica (dom_bare in _DOMINIOS_SIN_WWW) para controlar el flujo
    if dom_bare in _DOMINIOS_SIN_WWW:
        # Retornamos el resultado procesado (f'https://{dom_bare}')
        return f"https://{dom_bare}"
    # Retornamos el resultado procesado (f'https://www.{dom_bare}')
    return f"https://www.{dom_bare}"


# Definición de función '_es_vendedor_marketplace_no_verificado' (parámetros: seller_raw, marca, perfume_nombre)
def _es_vendedor_marketplace_no_verificado(seller_raw: Any, marca: str, perfume_nombre: str) -> bool:
    """
    Detecta vendedores terceros no auditados en Marketplaces (Falabella / Ripley)
    para evitar infiltración de clones o imitaciones sobre fichas de diseñador/nicho.
    """
    # Evaluamos la condición lógica (not seller_raw) para controlar el flujo
    if not seller_raw:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 's_norm' con str(seller_raw).strip().lower()
    s_norm = str(seller_raw).strip().lower()
    # Evaluamos la condición lógica (not s_norm) para controlar el flujo
    if not s_norm:
        # Retornamos el resultado procesado (False)
        return False
    # Evaluamos la condición lógica (any((oficial in s_norm for oficial in _SELLERS_OFICI...) para controlar el flujo
    if any(oficial in s_norm for oficial in _SELLERS_OFICIALES_MARKETPLACE):
        # Retornamos el resultado procesado (False)
        return False
    # Evaluamos la condición lógica (marca and len(marca.strip()) >= 3 and (marca.strip()...) para controlar el flujo
    if marca and len(marca.strip()) >= 3 and marca.strip().lower() in s_norm:
        # Retornamos el resultado procesado (False)
        return False
    # Evaluamos la condición lógica (any((sosp in s_norm for sosp in _SELLERS_SOSPECHOSOS))) para controlar el flujo
    if any(sosp in s_norm for sosp in _SELLERS_SOSPECHOSOS):
        # Retornamos el resultado procesado (True)
        return True
    # Evaluamos la condición lógica (marca and (not es_arabe(marca, perfume_nombre))) para controlar el flujo
    if marca and not es_arabe(marca, perfume_nombre):
        # Retornamos el resultado procesado (True)
        return True
    # Retornamos el resultado procesado (False)
    return False


# Definición de función 'extraer_variedades_shopify' (parámetros: session, dominio, perfume_nombre, marca, ...)
def extraer_variedades_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples variedades de tamaño (ml), formato ('regular' vs 'tester') y stock real
    en tiendas Shopify auditadas (Silk, Elite, Alisha, Yauras, Oferta Perfumes).
    """
    # Asignamos 'query_str' con f'{marca} {perfume_nombre}'.strip() if mar...
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    # Asignamos 'q' con urllib.parse.quote(query_str)
    q = urllib.parse.quote(query_str)
    # Asignamos 'base_host' con _resolver_base_shopify(dominio)
    base_host = _resolver_base_shopify(dominio)
    # Asignamos 'url_api' con f'{base_host}/search/suggest.json?q={q}&re...
    url_api = f"{base_host}/search/suggest.json?q={q}&resources[type]=product"
    # Asignamos 'headers' con obtener_headers_json(referer=f'{base_host}/')
    headers = obtener_headers_json(referer=f"{base_host}/")

    # Asignamos 'variedades' con []
    variedades: List[Dict[str, Any]] = []
    # Asignamos 'vols_vistos' con set()
    vols_vistos = set()

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        res = session.get(url_api, headers=headers, timeout=9)
        # Evaluamos la condición lógica (res.status_code in (403, 429) and curl_requests is n...) para controlar el flujo
        if res.status_code in (403, 429) and curl_requests is not None:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 's_cffi' con curl_requests.Session(impersonate='chrome1...
                s_cffi = curl_requests.Session(impersonate="chrome124")
                # Asignamos 'res_cffi' con s_cffi.get(url_api, headers=headers, timeo...
                res_cffi = s_cffi.get(url_api, headers=headers, timeout=9)
                # Evaluamos la condición lógica (res_cffi.status_code == 200) para controlar el flujo
                if res_cffi.status_code == 200:
                    # Asignamos 'res' con res_cffi
                    res = res_cffi
            except Exception:
                # Ejecutamos instrucción: pass
                pass

        # Evaluamos la condición lógica (res.status_code in (403, 429)) para controlar el flujo
        if res.status_code in (403, 429):
            # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
            if diagnostico is not None:
                # Asignamos 'diagnostico['waf_bloqueado']' con True
                diagnostico["waf_bloqueado"] = True
                # Asignamos 'diagnostico['http_status']' con res.status_code
                diagnostico["http_status"] = res.status_code
            # Retornamos el resultado procesado (variedades)
            return variedades
        # Evaluamos la condición lógica (res.status_code == 200) para controlar el flujo
        if res.status_code == 200:
            # Asignamos 'productos' con res.json().get('resources', {}).get('resul...
            productos = res.json().get("resources", {}).get("results", {}).get("products", [])
            # Recorremos iterativamente cada 'p' en productos
            for p in productos:
                # Asignamos 'raw_title' con p.get('title', '')
                raw_title = p.get("title", "")
                # Evaluamos la condición lógica (not es_producto_perfume_valido(raw_title, marca=marc...) para controlar el flujo
                if not es_producto_perfume_valido(raw_title, marca=marca or None, volumen_min_ml=25):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'raw_path' con p.get('url', '').split('?')[0]
                raw_path = p.get("url", "").split("?")[0]
                # Asignamos 'clean_url' con raw_path if raw_path.startswith('http') el...
                clean_url = raw_path if raw_path.startswith("http") else f"{base_host}{raw_path}"

                # Asignamos 'precio_act' con int(float(p.get('price', 0)))
                precio_act = int(float(p.get("price", 0)))
                # Evaluamos la condición lógica (not es_precio_valido(precio_act)) para controlar el flujo
                if not es_precio_valido(precio_act):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'es_tst_cand' con detectar_formato_oferta(raw_title, clean_u...
                es_tst_cand = detectar_formato_oferta(raw_title, clean_url) == "tester"
                # Asignamos 'vol_encontrado' con resolver_volumen_oferta(titulo_producto=ra...
                vol_encontrado = resolver_volumen_oferta(
                    titulo_producto=raw_title,
                    url_slug=clean_url,
                    volumen_ml_defecto=volumen_ml_defecto,
                    n_variantes_producto=1,
                    es_tester=es_tst_cand,
                )
                # Evaluamos la condición lógica (not vol_encontrado or vol_encontrado < 25) para controlar el flujo
                if not vol_encontrado or vol_encontrado < 25:
                    # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
                    if diagnostico is not None:
                        # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                        diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'res_match' con coincide_entidad_detallada(titulo=raw_titl...
                res_match = coincide_entidad_detallada(
                    titulo=raw_title,
                    perfume_nombre=perfume_nombre,
                    marca=marca,
                    concentracion=concentracion,
                    url=clean_url,
                    precio_candidato=precio_act,
                    precio_referencia=precio_referencia,
                )
                # Evaluamos la condición lógica (not res_match.coincide) para controlar el flujo
                if not res_match.coincide:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Evaluamos la condición lógica ('chanel' in perfume_nombre.lower() and 'chanel' not ...) para controlar el flujo
                if "chanel" in perfume_nombre.lower() and "chanel" not in raw_title.lower():
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'formato_det' con res_match.formato_detectado or detectar_fo...
                formato_det = res_match.formato_detectado or detectar_formato_oferta(raw_title, clean_url)
                # Asignamos 'clave_var' con (vol_encontrado, formato_det)
                clave_var = (vol_encontrado, formato_det)
                # Evaluamos la condición lógica (clave_var in vols_vistos) para controlar el flujo
                if clave_var in vols_vistos:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'p_comp_raw' con p.get('compare_at_price_max') or p.get('co...
                p_comp_raw = p.get("compare_at_price_max") or p.get("compare_at_price_min")
                # Asignamos 'precio_norm' con int(float(p_comp_raw)) if p_comp_raw else ...
                precio_norm = int(float(p_comp_raw)) if p_comp_raw else precio_act

                # Ejecutamos instrucción: vols_vistos.add(clave_var)
                vols_vistos.add(clave_var)
                # Asignamos 'norm_valido' con precio_norm if es_precio_valido(precio_nor...
                norm_valido = precio_norm if (es_precio_valido(precio_norm) and precio_norm > precio_act) else precio_act
                # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                variedades.append({
                    "exito": True,
                    "precio_actual": precio_act,
                    "precio_normal": norm_valido,
                    "url": clean_url,
                    "en_stock": bool(p.get("available", True)),
                    "volumen_ml": vol_encontrado,
                    "formato": formato_det,
                    "metodo": "Shopify Multi-Suggest",
                })
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error consultando Shopify {dominio} para '{perfume_nombre}': {e}")

    # Retornamos el resultado procesado (variedades)
    return variedades


# Definición de función 'extraer_precio_shopify' (parámetros: session, dominio, perfume_nombre, marca, ...)
def extraer_precio_shopify(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias: retorna la primera variedad o {exito: False}."""
    # Asignamos 'vars_found' con extraer_variedades_shopify(session, domini...
    vars_found = extraer_variedades_shopify(session, dominio, perfume_nombre, marca, volumen_ml)
    # Evaluamos la condición lógica (vars_found) para controlar el flujo
    if vars_found:
        # Retornamos el resultado procesado (vars_found[0])
        return vars_found[0]
    # Retornamos el resultado procesado ({'exito': False})
    return {"exito": False}


# Definición de función 'extraer_variedades_woocommerce' (parámetros: session, dominio, perfume_nombre, marca, ...)
def extraer_variedades_woocommerce(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae presentaciones y precios reales en tiendas WooCommerce auditadas
    (Chile Perfume, Portal del Perfume, Aromata) mediante la WooCommerce Store API pública.
    """
    # Asignamos 'query_str' con f'{marca} {perfume_nombre}'.strip() if mar...
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    # Asignamos 'q' con urllib.parse.quote(query_str)
    q = urllib.parse.quote(query_str)
    # Asignamos 'base_host' con f"https://{dominio.strip().rstrip('/')}"
    base_host = f"https://{dominio.strip().rstrip('/')}"
    # Asignamos 'url_api' con f'{base_host}/wp-json/wc/store/v1/products...
    url_api = f"{base_host}/wp-json/wc/store/v1/products?search={q}&per_page=10"
    # Asignamos 'headers' con {'User-Agent': random.choice(USER_AGENTS),...
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": f"{base_host}/",
    }

    # Asignamos 'variedades' con []
    variedades: List[Dict[str, Any]] = []
    # Asignamos 'vols_vistos' con set()
    vols_vistos = set()

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        res = session.get(url_api, headers=headers, timeout=10)
        # Evaluamos la condición lógica (res.status_code in (403, 429) and curl_requests is n...) para controlar el flujo
        if res.status_code in (403, 429) and curl_requests is not None:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 's_cffi' con curl_requests.Session(impersonate='chrome1...
                s_cffi = curl_requests.Session(impersonate="chrome124")
                # Asignamos 'res_cffi' con s_cffi.get(url_api, headers=headers, timeo...
                res_cffi = s_cffi.get(url_api, headers=headers, timeout=10)
                # Evaluamos la condición lógica (res_cffi.status_code == 200) para controlar el flujo
                if res_cffi.status_code == 200:
                    # Asignamos 'res' con res_cffi
                    res = res_cffi
            except Exception:
                # Ejecutamos instrucción: pass
                pass

        # Evaluamos la condición lógica (res.status_code in (403, 429)) para controlar el flujo
        if res.status_code in (403, 429):
            # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
            if diagnostico is not None:
                # Asignamos 'diagnostico['waf_bloqueado']' con True
                diagnostico["waf_bloqueado"] = True
                # Asignamos 'diagnostico['http_status']' con res.status_code
                diagnostico["http_status"] = res.status_code
            # Retornamos el resultado procesado (variedades)
            return variedades

        # Evaluamos la condición lógica (res.status_code == 200) para controlar el flujo
        if res.status_code == 200:
            # Asignamos 'productos' con res.json()
            productos = res.json()
            # Evaluamos la condición lógica (isinstance(productos, list)) para controlar el flujo
            if isinstance(productos, list):
                # Recorremos iterativamente cada 'p' en productos
                for p in productos:
                    # Asignamos 'raw_title' con p.get('name', '')
                    raw_title = p.get("name", "")
                    # Evaluamos la condición lógica (not es_producto_perfume_valido(raw_title, marca=marc...) para controlar el flujo
                    if not es_producto_perfume_valido(raw_title, marca=marca or None, volumen_min_ml=25):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Asignamos 'clean_url' con p.get('permalink', '')
                    clean_url = p.get("permalink", "")
                    # Asignamos 'prices' con p.get('prices', {})
                    prices = p.get("prices", {})
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    p_act = clean_digits(prices.get("price"))
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    p_norm = clean_digits(prices.get("regular_price")) or p_act
                    # Evaluamos la condición lógica (not es_precio_valido(p_act)) para controlar el flujo
                    if not es_precio_valido(p_act):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Asignamos 'es_tst_wc' con detectar_formato_oferta(raw_title, clean_u...
                    es_tst_wc = detectar_formato_oferta(raw_title, clean_url) == "tester"
                    # Asignamos 'vol_encontrado' con resolver_volumen_oferta(titulo_producto=ra...
                    vol_encontrado = resolver_volumen_oferta(
                        titulo_producto=raw_title,
                        url_slug=clean_url,
                        volumen_ml_defecto=volumen_ml_defecto,
                        n_variantes_producto=1,
                        es_tester=es_tst_wc,
                    )
                    # Evaluamos la condición lógica (not vol_encontrado or vol_encontrado < 25) para controlar el flujo
                    if not vol_encontrado or vol_encontrado < 25:
                        # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
                        if diagnostico is not None:
                            # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                            diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Asignamos 'res_match' con coincide_entidad_detallada(titulo=raw_titl...
                    res_match = coincide_entidad_detallada(
                        titulo=raw_title,
                        perfume_nombre=perfume_nombre,
                        marca=marca,
                        concentracion=concentracion,
                        url=clean_url,
                        precio_candidato=p_act,
                        precio_referencia=precio_referencia,
                    )
                    # Evaluamos la condición lógica (not res_match.coincide) para controlar el flujo
                    if not res_match.coincide:
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Asignamos 'formato_det' con res_match.formato_detectado or detectar_fo...
                    formato_det = res_match.formato_detectado or detectar_formato_oferta(raw_title, clean_url)
                    # Asignamos 'clave_var' con (vol_encontrado, formato_det)
                    clave_var = (vol_encontrado, formato_det)
                    # Evaluamos la condición lógica (clave_var in vols_vistos) para controlar el flujo
                    if clave_var in vols_vistos:
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Ejecutamos instrucción: vols_vistos.add(clave_var)
                    vols_vistos.add(clave_var)
                    # Asignamos 'en_stock' con bool(p.get('is_in_stock', True))
                    en_stock = bool(p.get("is_in_stock", True))
                    # Asignamos 'norm_valido' con p_norm if es_precio_valido(p_norm) and p_n...
                    norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act

                    # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                    variedades.append({
                        "exito": True,
                        "precio_actual": p_act,
                        "precio_normal": norm_valido,
                        "url": clean_url,
                        "en_stock": en_stock,
                        "volumen_ml": vol_encontrado,
                        "formato": formato_det,
                        "metodo": "WooCommerce Store API",
                    })
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.debug(f"Aviso consultando WooCommerce {dominio} para '{perfume_nombre}': {e}")

    # Retornamos el resultado procesado (variedades)
    return variedades


# Definición de función 'extraer_precio_woocommerce' (parámetros: session, dominio, perfume_nombre, marca, ...)
def extraer_precio_woocommerce(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str,
    volumen_ml: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias: retorna la primera variedad o {exito: False}."""
    # Asignamos 'vars_found' con extraer_variedades_woocommerce(session, do...
    vars_found = extraer_variedades_woocommerce(session, dominio, perfume_nombre, marca, volumen_ml)
    # Evaluamos la condición lógica (vars_found) para controlar el flujo
    if vars_found:
        # Retornamos el resultado procesado (vars_found[0])
        return vars_found[0]
    # Retornamos el resultado procesado ({'exito': False})
    return {"exito": False}


# - ¿Qué hace esta función (Extractor Falabella)?:
#   Descarga el HTML de Falabella y parsea la etiqueta incrustada <script id="__NEXT_DATA__"> de Next.js.
#   Extrae precios, tallas/volúmenes y stock directamente del JSON de hidratación de React sin usar un navegador pesado.
def _es_variante_falabella_agotada(v: Dict[str, Any], is_prod_out: bool) -> bool:
    """
    Determina si una variante de Falabella carece de disponibilidad real de compra.
    En el JSON __NEXT_DATA__ de Falabella:
    - Las tallas agotadas no siempre traen 'isOutOfStock: True'; en su lugar, omiten
      'isPurchaseable' (None) y 'isOnlineSellable' (None), y sus 'availabilityLabels'
      quedan con strings vacíos ("").
    - Las variantes con stock activo siempre tienen al menos uno de los flags de compra
      ('isPurchaseable', 'isOnlineSellable', 'isHDAvailable', 'isCCAvailable') en True,
      o textos descriptivos de despacho válidos en 'availabilityLabels'.
    """
    # Evaluamos la condición lógica (is_prod_out or bool(v.get('isOutOfStock', False))) para controlar el flujo
    if is_prod_out or bool(v.get("isOutOfStock", False)):
        # Retornamos el resultado procesado (True)
        return True
    # Evaluamos la condición lógica (v.get('isPurchaseable') is False or v.get('isOnlineS...) para controlar el flujo
    if v.get("isPurchaseable") is False or v.get("isOnlineSellable") is False:
        # Retornamos el resultado procesado (True)
        return True

    # Indicadores positivos de stock
    indicadores_positivos = (
        bool(v.get("isPurchaseable"))
        or bool(v.get("isOnlineSellable"))
        or bool(v.get("isHDAvailable"))
        or bool(v.get("isCCAvailable"))
    )
    # Evaluamos la condición lógica (indicadores_positivos) para controlar el flujo
    if indicadores_positivos:
        # Retornamos el resultado procesado (False)
        return False

    # Asignamos 'labels' con v.get('availabilityLabels')
    labels = v.get("availabilityLabels")
    # Evaluamos la condición lógica (isinstance(labels, dict) and labels) para controlar el flujo
    if isinstance(labels, dict) and labels:
        # Evaluamos la condición lógica (any((bool(txt and str(txt).strip()) for txt in label...) para controlar el flujo
        if any(bool(txt and str(txt).strip()) for txt in labels.values()):
            # Retornamos el resultado procesado (False)
            return False
        # Retornamos el resultado procesado (True)
        return True

    # Si contiene claves de stock del payload Next.js pero ninguna fue positiva
    claves_stock = {"isPurchaseable", "isOnlineSellable", "isHDAvailable", "isCCAvailable", "availabilityLabels"}
    # Evaluamos la condición lógica (any((k in v for k in claves_stock))) para controlar el flujo
    if any(k in v for k in claves_stock):
        # Retornamos el resultado procesado (True)
        return True

    # En caso de mocks o payloads sintéticos que no incluyan la estructura completa de Next.js
    return False


# Definición de función '_extraer_volumen_atributo_falabella' (parámetros: size_attr)
def _extraer_volumen_atributo_falabella(size_attr: Any) -> Optional[int]:
    """
    Extrae el volumen en ml desde `attributes.size` de Falabella sin confundir tallas de calzado/ropa
    (ej. '36', '38', '37.5' -> nunca deben convertirse en 36ml, 38ml ni 375ml).
    """
    # Evaluamos la condición lógica (not size_attr) para controlar el flujo
    if not size_attr:
        # Retornamos el resultado procesado (None)
        return None
    # Asignamos 's' con str(size_attr).strip()
    s = str(size_attr).strip()
    # Asignamos 'vol_exp' con extraer_volumen_ml_opcional(s)
    vol_exp = extraer_volumen_ml_opcional(s)
    # Evaluamos la condición lógica (vol_exp is not None and 25 <= vol_exp <= 1000) para controlar el flujo
    if vol_exp is not None and 25 <= vol_exp <= 1000:
        # Retornamos el resultado procesado (vol_exp)
        return vol_exp
    # Evaluamos la condición lógica (re.fullmatch('\\d{2,3}', s)) para controlar el flujo
    if re.fullmatch(r"\d{2,3}", s):
        # Asignamos 'val' con int(s)
        val = int(s)
        # Evaluamos la condición lógica (val in {30, 50, 60, 75, 80, 90, 100, 105, 120, 125, ...) para controlar el flujo
        if val in {30, 50, 60, 75, 80, 90, 100, 105, 120, 125, 150, 175, 200, 250}:
            # Retornamos el resultado procesado (val)
            return val
    # Retornamos el resultado procesado (None)
    return None


# Definición de función 'extraer_variedades_falabella' (parámetros: session, url_directa, perfume_nombre, marca, ...)
def extraer_variedades_falabella(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples presentaciones de Falabella Chile validando entidad en 12 capas
    y descartando vendedores Marketplace terceros no auditados.
    """
    # Asignamos 'headers' con obtener_headers_navegador(referer='https:/...
    headers = obtener_headers_navegador(referer="https://www.falabella.com/falabella-cl")
    # Asignamos 'variedades' con []
    variedades: List[Dict[str, Any]] = []
    # Asignamos 'vols_vistos' con set()
    vols_vistos = set()

    # Intento 1: URL directa
    if url_directa and url_directa.startswith("http"):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = _peticion_retail_resiliente(session, url_directa, headers=headers, timeout=10, prefer_curl_cffi=False)
            # Evaluamos la condición lógica (res.status_code in (403, 429) and diagnostico is not...) para controlar el flujo
            if res.status_code in (403, 429) and diagnostico is not None:
                # Asignamos 'diagnostico['waf_bloqueado']' con True
                diagnostico["waf_bloqueado"] = True
                # Asignamos 'diagnostico['http_status']' con res.status_code
                diagnostico["http_status"] = res.status_code
            # Evaluamos la condición lógica (res.status_code == 200) para controlar el flujo
            elif res.status_code == 200:
                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                soup = BeautifulSoup(res.text, "html.parser")
                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                tag = soup.find("script", id="__NEXT_DATA__")
                # Evaluamos la condición lógica (tag and tag.string) para controlar el flujo
                if tag and tag.string:
                    # Procesamiento de serialización o deserialización de estructura JSON
                    data = json.loads(tag.string)
                    # Asignamos 'pdata' con data.get('props', {}).get('pageProps', {})...
                    pdata = data.get("props", {}).get("pageProps", {}).get("productData", {})
                    # Asignamos 'seller_direct' con pdata.get('sellerName') or pdata.get('offe...
                    seller_direct = pdata.get("sellerName") or pdata.get("offeredBy")
                    # Asignamos 'is_prod_out' con bool(pdata.get('isOutOfStock', False))
                    is_prod_out = bool(pdata.get("isOutOfStock", False))
                    # Asignamos 'skus' con pdata.get('variants', []) or pdata.get('sk...
                    skus = pdata.get("variants", []) or pdata.get("skus", [])
                    # Asignamos 'prod_name' con pdata.get('name', perfume_nombre)
                    prod_name = pdata.get("name", perfume_nombre)

                    # Evaluamos la condición lógica (_es_vendedor_marketplace_no_verificado(seller_direct...) para controlar el flujo
                    if _es_vendedor_marketplace_no_verificado(seller_direct, marca, perfume_nombre):
                        # Registro de evento diagnóstico en la bitácora (logger) del sistema
                        logger.info(f"Omitiendo vendedor Marketplace Falabella no auditado: {seller_direct} ({prod_name})")
                    else:
                        # Asignamos 'res_head' con coincide_entidad_detallada(titulo=prod_nam...
                        res_head = coincide_entidad_detallada(
                            titulo=prod_name,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=url_directa,
                        )
                        # Evaluamos la condición lógica (not res_head.coincide) para controlar el flujo
                        if not res_head.coincide:
                            # Registro de evento diagnóstico en la bitácora (logger) del sistema
                            logger.warning(f"URL directa Falabella descartada ({res_head.motivo}): {prod_name} != {perfume_nombre}")
                        else:
                            # Recorremos iterativamente cada 'v' en skus
                            for v in skus:
                                # Asignamos 'v_seller' con v.get('sellerName') or seller_direct
                                v_seller = v.get("sellerName") or seller_direct
                                # Evaluamos la condición lógica (_es_vendedor_marketplace_no_verificado(v_seller, mar...) para controlar el flujo
                                if _es_vendedor_marketplace_no_verificado(v_seller, marca, perfume_nombre):
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'v_name' con v.get('name') or prod_name
                                v_name = v.get("name") or prod_name
                                # Asignamos 'size_attr' con v.get('attributes', {}).get('size')
                                size_attr = v.get("attributes", {}).get("size")
                                # Asignamos 'vol_attr' con _extraer_volumen_atributo_falabella(size_a...
                                vol_attr = _extraer_volumen_atributo_falabella(size_attr)
                                # Asignamos 'vol' con vol_attr if vol_attr else resolver_volumen...
                                vol = vol_attr if vol_attr else resolver_volumen_oferta(
                                    titulo_variante=v_name,
                                    titulo_producto=prod_name,
                                    url_slug=url_directa or "",
                                    volumen_ml_defecto=volumen_ml_defecto,
                                    n_variantes_producto=len(skus),
                                    es_tester=(detectar_formato_oferta(v_name, url_directa or "") == "tester"),
                                )
                                # Evaluamos la condición lógica (not vol or vol < 25) para controlar el flujo
                                if not vol or vol < 25:
                                    # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
                                    if diagnostico is not None:
                                        # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                                        diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'prices' con v.get('prices', [])
                                prices = v.get("prices", [])
                                # Asignamos '(p_act, p_norm)' con (0, 0)
                                p_act, p_norm = 0, 0
                                # Recorremos iterativamente cada 'p_item' en prices
                                for p_item in prices:
                                    # Asignamos 't' con p_item.get('type', '')
                                    t = p_item.get("type", "")
                                    # Asignamos 'val' con clean_digits(p_item.get('price', ['0'])[0])
                                    val = clean_digits(p_item.get("price", ["0"])[0])
                                    # Evaluamos la condición lógica (t in ('internetPrice', 'eventPrice') and val > 0) para controlar el flujo
                                    if t in ("internetPrice", "eventPrice") and val > 0:
                                        # Asignamos 'p_act' con val
                                        p_act = val
                                    # Evaluamos la condición lógica (t == 'normalPrice' and val > 0) para controlar el flujo
                                    elif t == "normalPrice" and val > 0:
                                        # Asignamos 'p_norm' con val
                                        p_norm = val
                                # Evaluamos la condición lógica (p_act == 0 and prices) para controlar el flujo
                                if p_act == 0 and prices:
                                    # Asignamos 'p_act' con clean_digits(prices[0].get('price', ['0'])...
                                    p_act = clean_digits(prices[0].get("price", ["0"])[0])
                                # Evaluamos la condición lógica (not es_precio_valido(p_act)) para controlar el flujo
                                if not es_precio_valido(p_act):
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'res_v' con coincide_entidad_detallada(titulo=v_name, ...
                                res_v = coincide_entidad_detallada(
                                    titulo=v_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=url_directa,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                # Evaluamos la condición lógica (not res_v.coincide) para controlar el flujo
                                if not res_v.coincide:
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'formato_det' con res_v.formato_detectado or detectar_format...
                                formato_det = res_v.formato_detectado or detectar_formato_oferta(v_name, url_directa)
                                # Asignamos 'clave_var' con (vol, formato_det)
                                clave_var = (vol, formato_det)
                                # Evaluamos la condición lógica (clave_var in vols_vistos) para controlar el flujo
                                if clave_var in vols_vistos:
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'is_out' con _es_variante_falabella_agotada(v, is_prod_...
                                is_out = _es_variante_falabella_agotada(v, is_prod_out)
                                # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                vols_vistos.add(clave_var)
                                # Asignamos 'norm_valido' con p_norm if es_precio_valido(p_norm) and p_n...
                                norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                                variedades.append({
                                    "exito": True,
                                    "precio_actual": p_act,
                                    "precio_normal": norm_valido,
                                    "url": url_directa,
                                    "en_stock": not is_out,
                                    "volumen_ml": vol,
                                    "formato": formato_det,
                                    "metodo": "Falabella Direct Variants",
                                })
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.debug(f"Aviso leyendo URL directa Falabella: {e}")

    # Evaluamos la condición lógica (variedades and any((v.get('en_stock') for v in varie...) para controlar el flujo
    if variedades and any(v.get("en_stock") for v in variedades):
        # Retornamos el resultado procesado (variedades)
        return variedades

    # Intento 2: Búsqueda dinámica en vivo en Falabella
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    # Asignamos 'q' con urllib.parse.quote(query_str)
    q = urllib.parse.quote(query_str)
    # Asignamos 'search_url' con f'https://www.falabella.com/falabella-cl/s...
    search_url = f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        res_s = session.get(search_url, headers=headers, timeout=11)
        # Evaluamos la condición lógica (res_s.status_code in (403, 429) and diagnostico is n...) para controlar el flujo
        if res_s.status_code in (403, 429) and diagnostico is not None:
            # Asignamos 'diagnostico['waf_bloqueado']' con True
            diagnostico["waf_bloqueado"] = True
            # Asignamos 'diagnostico['http_status']' con res_s.status_code
            diagnostico["http_status"] = res_s.status_code
        # Evaluamos la condición lógica (res_s.status_code == 200) para controlar el flujo
        elif res_s.status_code == 200:
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            soup_s = BeautifulSoup(res_s.text, "html.parser")
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            tag_s = soup_s.find("script", id="__NEXT_DATA__")
            # Evaluamos la condición lógica (tag_s and tag_s.string) para controlar el flujo
            if tag_s and tag_s.string:
                # Procesamiento de serialización o deserialización de estructura JSON
                data_s = json.loads(tag_s.string)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                results = data_s.get("props", {}).get("pageProps", {}).get("results", [])
                # Recorremos iterativamente cada 'r' en results
                for r in results:
                    # Asignamos 'd_name' con r.get('displayName', '')
                    d_name = r.get("displayName", "")
                    # Asignamos 'prod_url' con r.get('url', '')
                    prod_url = r.get("url", "")
                    # Asignamos 'r_seller' con r.get('sellerName') or r.get('sellerId')
                    r_seller = r.get("sellerName") or r.get("sellerId")
                    # Evaluamos la condición lógica (_es_vendedor_marketplace_no_verificado(r_seller, mar...) para controlar el flujo
                    if _es_vendedor_marketplace_no_verificado(r_seller, marca, perfume_nombre):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Evaluamos la condición lógica (not es_producto_perfume_valido(d_name, marca=marca o...) para controlar el flujo
                    if not es_producto_perfume_valido(d_name, marca=marca or None, volumen_min_ml=25):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'res_card' con coincide_entidad_detallada(titulo=d_name, ...
                    res_card = coincide_entidad_detallada(
                        titulo=d_name,
                        perfume_nombre=perfume_nombre,
                        marca=marca,
                        concentracion=concentracion,
                        url=prod_url,
                    )
                    # Evaluamos la condición lógica (not res_card.coincide) para controlar el flujo
                    if not res_card.coincide:
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Evaluamos la condición lógica (prod_url and len(variedades) < 4) para controlar el flujo
                    if prod_url and len(variedades) < 4:
                        # Bloque try/except para manejo seguro de errores y resiliencia operativa
                        try:
                            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                            res_p = session.get(prod_url, headers=headers, timeout=9)
                            # Evaluamos la condición lógica (res_p.status_code == 200) para controlar el flujo
                            if res_p.status_code == 200:
                                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                                soup_p = BeautifulSoup(res_p.text, "html.parser")
                                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                                tag_p = soup_p.find("script", id="__NEXT_DATA__")
                                # Evaluamos la condición lógica (tag_p and tag_p.string) para controlar el flujo
                                if tag_p and tag_p.string:
                                    # Procesamiento de serialización o deserialización de estructura JSON
                                    data_p = json.loads(tag_p.string)
                                    # Asignamos 'pdata' con data_p.get('props', {}).get('pageProps', {...
                                    pdata = data_p.get("props", {}).get("pageProps", {}).get("productData", {})
                                    # Asignamos 'p_seller' con pdata.get('sellerName') or pdata.get('offe...
                                    p_seller = pdata.get("sellerName") or pdata.get("offeredBy") or r_seller
                                    # Evaluamos la condición lógica (_es_vendedor_marketplace_no_verificado(p_seller, mar...) para controlar el flujo
                                    if _es_vendedor_marketplace_no_verificado(p_seller, marca, perfume_nombre):
                                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                        continue
                                    # Asignamos 'is_prod_out' con bool(pdata.get('isOutOfStock', False))
                                    is_prod_out = bool(pdata.get("isOutOfStock", False))
                                    # Asignamos 'skus' con pdata.get('variants', []) or pdata.get('sk...
                                    skus = pdata.get("variants", []) or pdata.get("skus", [])
                                    # Recorremos iterativamente cada 'v' en skus
                                    for v in skus:
                                        # Asignamos 'v_name' con v.get('name') or d_name
                                        v_name = v.get("name") or d_name
                                        # Asignamos 'size_attr' con v.get('attributes', {}).get('size')
                                        size_attr = v.get("attributes", {}).get("size")
                                        # Asignamos 'vol_attr' con _extraer_volumen_atributo_falabella(size_a...
                                        vol_attr = _extraer_volumen_atributo_falabella(size_attr)
                                        # Asignamos 'vol' con vol_attr if vol_attr else resolver_volumen...
                                        vol = vol_attr if vol_attr else resolver_volumen_oferta(
                                            titulo_variante=v_name,
                                            titulo_producto=d_name,
                                            url_slug=prod_url or "",
                                            volumen_ml_defecto=volumen_ml_defecto,
                                            n_variantes_producto=len(skus),
                                            es_tester=(detectar_formato_oferta(v_name, prod_url or "") == "tester"),
                                        )
                                        # Evaluamos la condición lógica (not vol or vol < 25) para controlar el flujo
                                        if not vol or vol < 25:
                                            # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
                                            if diagnostico is not None:
                                                # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                                                diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue
                                        # Asignamos 'prices' con v.get('prices', [])
                                        prices = v.get("prices", [])
                                        # Asignamos '(p_act, p_norm)' con (0, 0)
                                        p_act, p_norm = 0, 0
                                        # Recorremos iterativamente cada 'p_item' en prices
                                        for p_item in prices:
                                            # Asignamos 't' con p_item.get('type', '')
                                            t = p_item.get("type", "")
                                            # Asignamos 'val' con clean_digits(p_item.get('price', ['0'])[0])
                                            val = clean_digits(p_item.get("price", ["0"])[0])
                                            # Evaluamos la condición lógica (t in ('internetPrice', 'eventPrice') and val > 0) para controlar el flujo
                                            if t in ("internetPrice", "eventPrice") and val > 0:
                                                # Asignamos 'p_act' con val
                                                p_act = val
                                            # Evaluamos la condición lógica (t == 'normalPrice' and val > 0) para controlar el flujo
                                            elif t == "normalPrice" and val > 0:
                                                # Asignamos 'p_norm' con val
                                                p_norm = val
                                        # Evaluamos la condición lógica (p_act == 0 and prices) para controlar el flujo
                                        if p_act == 0 and prices:
                                            # Asignamos 'p_act' con clean_digits(prices[0].get('price', ['0'])...
                                            p_act = clean_digits(prices[0].get("price", ["0"])[0])
                                        # Evaluamos la condición lógica (not es_precio_valido(p_act)) para controlar el flujo
                                        if not es_precio_valido(p_act):
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue
                                        # Asignamos 'res_v' con coincide_entidad_detallada(titulo=v_name, ...
                                        res_v = coincide_entidad_detallada(
                                            titulo=v_name,
                                            perfume_nombre=perfume_nombre,
                                            marca=marca,
                                            concentracion=concentracion,
                                            url=prod_url,
                                            precio_candidato=p_act,
                                            precio_referencia=precio_referencia,
                                        )
                                        # Evaluamos la condición lógica (not res_v.coincide) para controlar el flujo
                                        if not res_v.coincide:
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue
                                        # Asignamos 'formato_det' con res_v.formato_detectado or detectar_format...
                                        formato_det = res_v.formato_detectado or detectar_formato_oferta(v_name, prod_url)
                                        # Asignamos 'clave_var' con (vol, formato_det)
                                        clave_var = (vol, formato_det)
                                        # Asignamos 'is_out' con _es_variante_falabella_agotada(v, is_prod_...
                                        is_out = _es_variante_falabella_agotada(v, is_prod_out)
                                        # Asignamos 'norm_valido' con p_norm if es_precio_valido(p_norm) and p_n...
                                        norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                        # Asignamos 'nueva_var_f' con {'exito': True, 'precio_actual': p_act, 'p...
                                        nueva_var_f = {
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": norm_valido,
                                            "url": prod_url,
                                            "en_stock": not is_out,
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Falabella Live Variants",
                                        }
                                        # Evaluamos la condición lógica (clave_var not in vols_vistos) para controlar el flujo
                                        if clave_var not in vols_vistos:
                                            # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                            vols_vistos.add(clave_var)
                                            # Ejecutamos instrucción: variedades.append(nueva_var_f)
                                            variedades.append(nueva_var_f)
                                        else:
                                            # Si la URL directa previa estaba agotada o era más cara, reemplazar por la oferta en stock más económica
                                            for idx_vf, vf_prev in enumerate(variedades):
                                                # Evaluamos la condición lógica ((vf_prev.get('volumen_ml'), vf_prev.get('formato')) ...) para controlar el flujo
                                                if (vf_prev.get("volumen_ml"), vf_prev.get("formato")) == clave_var:
                                                    # Evaluamos la condición lógica (not is_out and (not vf_prev.get('en_stock') or p_act...) para controlar el flujo
                                                    if (not is_out) and (not vf_prev.get("en_stock") or p_act < vf_prev.get("precio_actual", p_act)):
                                                        # Asignamos 'variedades[idx_vf]' con nueva_var_f
                                                        variedades[idx_vf] = nueva_var_f
                                                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                                    break
                        except Exception:
                            # Ejecutamos instrucción: pass
                            pass
                    # Evaluamos la condición lógica (not variedades) para controlar el flujo
                    if not variedades:
                        # Asignamos 'prices' con r.get('prices', [])
                        prices = r.get("prices", [])
                        # Evaluamos la condición lógica (prices) para controlar el flujo
                        if prices:
                            # Asignamos 'p_act' con clean_digits(prices[0].get('price', ['0'])...
                            p_act = clean_digits(prices[0].get("price", ["0"])[0])
                            # Asignamos 'vol' con resolver_volumen_oferta(titulo_producto=d_...
                            vol = resolver_volumen_oferta(
                                titulo_producto=d_name,
                                url_slug=prod_url or "",
                                volumen_ml_defecto=volumen_ml_defecto,
                                n_variantes_producto=1,
                                es_tester=(detectar_formato_oferta(d_name, prod_url or "") == "tester"),
                            )
                            # Evaluamos la condición lógica (vol and vol >= 25 and es_precio_valido(p_act)) para controlar el flujo
                            if vol and vol >= 25 and es_precio_valido(p_act):
                                # Asignamos 'res_sc' con coincide_entidad_detallada(titulo=d_name, ...
                                res_sc = coincide_entidad_detallada(
                                    titulo=d_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=prod_url or search_url,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                # Evaluamos la condición lógica (res_sc.coincide) para controlar el flujo
                                if res_sc.coincide:
                                    # Asignamos 'formato_det' con res_sc.formato_detectado or detectar_forma...
                                    formato_det = res_sc.formato_detectado or detectar_formato_oferta(d_name, prod_url or "")
                                    # Asignamos 'clave_var' con (vol, formato_det)
                                    clave_var = (vol, formato_det)
                                    # Evaluamos la condición lógica (clave_var not in vols_vistos) para controlar el flujo
                                    if clave_var not in vols_vistos:
                                        # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                        vols_vistos.add(clave_var)
                                        # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": p_act,
                                            "url": prod_url or search_url,
                                            "en_stock": not bool(r.get("isOutOfStock", False)),
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Falabella Search Card",
                                        })
                    # Evaluamos la condición lógica (len(variedades) >= 3) para controlar el flujo
                    if len(variedades) >= 3:
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error en búsqueda viva Falabella para '{perfume_nombre}': {e}")

    # Retornamos el resultado procesado (variedades)
    return variedades


# Definición de función 'extraer_precio_falabella' (parámetros: session, url_directa, perfume_nombre, volumen_ml)
def extraer_precio_falabella(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias y selección de volumen específico."""
    # Asignamos 'vars_found' con extraer_variedades_falabella(session, url_...
    vars_found = extraer_variedades_falabella(session, url_directa, perfume_nombre, "", volumen_ml)
    # Evaluamos la condición lógica (vars_found) para controlar el flujo
    if vars_found:
        # Evaluamos la condición lógica (volumen_ml) para controlar el flujo
        if volumen_ml:
            # Asignamos 'exacto' con [v for v in vars_found if v.get('volumen_m...
            exacto = [v for v in vars_found if v.get("volumen_ml") == volumen_ml]
            # Evaluamos la condición lógica (exacto) para controlar el flujo
            if exacto:
                # Retornamos el resultado procesado (exacto[0])
                return exacto[0]
        # Retornamos el resultado procesado (vars_found[0])
        return vars_found[0]
    # Retornamos el resultado procesado ({'exito': False})
    return {"exito": False}


# - ¿Qué hace esta función (Extractor Paris)?:
#   Consulta los endpoints de búsqueda de Paris (VTEX) o parsea los metadatos Schema.org (JSON-LD)
#   para obtener el precio vigente, descuento y disponibilidad en stock.
def extraer_variedades_paris(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae presentaciones y precios reales en Paris.cl validando entidad tanto en URLs
    directas como en búsqueda viva para impedir SKUs reciclados o cruzados.
    """
    # Asignamos 'headers' con obtener_headers_navegador(referer='https:/...
    headers = obtener_headers_navegador(referer="https://www.paris.cl/")
    # Asignamos 'variedades' con []
    variedades: List[Dict[str, Any]] = []
    # Asignamos 'vols_vistos' con set()
    vols_vistos = set()

    # Intento 1: URL directa con validación estricta de entidad
    if url_directa and url_directa.startswith("http"):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = _peticion_retail_resiliente(session, url_directa, headers=headers, timeout=10, prefer_curl_cffi=False)
            # Evaluamos la condición lógica (res.status_code in (403, 429) and diagnostico is not...) para controlar el flujo
            if res.status_code in (403, 429) and diagnostico is not None:
                # Asignamos 'diagnostico['waf_bloqueado']' con True
                diagnostico["waf_bloqueado"] = True
                # Asignamos 'diagnostico['http_status']' con res.status_code
                diagnostico["http_status"] = res.status_code
            # Evaluamos la condición lógica (res.status_code == 200) para controlar el flujo
            elif res.status_code == 200:
                # Asignamos 'is_dead_paris' con any((w in res.text.lower() for w in ['pági...
                is_dead_paris = any(w in res.text.lower() for w in [
                    'página en construcción', 'pagina en construccion',
                    'mejorando tu experiencia', 'página no encontrada', 'no encontramos productos',
                ])
                # Evaluamos la condición lógica (not is_dead_paris) para controlar el flujo
                if not is_dead_paris:
                    # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                    soup = BeautifulSoup(res.text, "html.parser")
                    # Recorremos iterativamente cada 's_tag' en soup.find_all('script', type='application/...
                    for s_tag in soup.find_all("script", type="application/ld+json"):
                        # Evaluamos la condición lógica ('Product' in s_tag.text) para controlar el flujo
                        if "Product" in s_tag.text:
                            # Procesamiento de serialización o deserialización de estructura JSON
                            d = json.loads(s_tag.text)
                            # Asignamos 'p_name' con d.get('name', perfume_nombre)
                            p_name = d.get("name", perfume_nombre)
                            # Evaluamos la condición lógica (not es_producto_perfume_valido(p_name, marca=marca o...) para controlar el flujo
                            if not es_producto_perfume_valido(p_name, marca=marca or None, volumen_min_ml=25):
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue
                            # Asignamos 'offers' con d.get('offers', [])
                            offers = d.get("offers", [])
                            # Asignamos 'lista_offs' con offers if isinstance(offers, list) else [o...
                            lista_offs = offers if isinstance(offers, list) else ([offers] if isinstance(offers, dict) else [])
                            # Asignamos 'precios_validos' con []
                            precios_validos = []
                            # Recorremos iterativamente cada 'o_item' en lista_offs
                            for o_item in lista_offs:
                                # Evaluamos la condición lógica (isinstance(o_item, dict) and o_item.get('price') is ...) para controlar el flujo
                                if isinstance(o_item, dict) and o_item.get("price") is not None:
                                    # Asignamos 'p_cand' con clean_digits(o_item.get('price'))
                                    p_cand = clean_digits(o_item.get("price"))
                                    # Evaluamos la condición lógica (es_precio_valido(p_cand)) para controlar el flujo
                                    if es_precio_valido(p_cand):
                                        # Ejecutamos instrucción: precios_validos.append(p_cand)
                                        precios_validos.append(p_cand)
                            # Asignamos 'off' con lista_offs[0] if lista_offs and isinstance...
                            off = lista_offs[0] if lista_offs and isinstance(lista_offs[0], dict) else {}
                            # Evaluamos la condición lógica (precios_validos) para controlar el flujo
                            if precios_validos:
                                # Asignamos 'p_act' con min(precios_validos)
                                p_act = min(precios_validos)
                                # Asignamos 'p_norm' con max(precios_validos)
                                p_norm = max(precios_validos)
                                # Asignamos 'vol' con resolver_volumen_oferta(titulo_producto=p_...
                                vol = resolver_volumen_oferta(
                                    titulo_producto=p_name,
                                    url_slug=url_directa or "",
                                    volumen_ml_defecto=volumen_ml_defecto,
                                    n_variantes_producto=1,
                                    es_tester=(detectar_formato_oferta(p_name, url_directa or "") == "tester"),
                                )
                                # Evaluamos la condición lógica (not vol or vol < 25 or (not es_precio_valido(p_act))) para controlar el flujo
                                if not vol or vol < 25 or not es_precio_valido(p_act):
                                    # Evaluamos la condición lógica (not vol and diagnostico is not None) para controlar el flujo
                                    if not vol and diagnostico is not None:
                                        # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                                        diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'res_match' con coincide_entidad_detallada(titulo=p_name, ...
                                res_match = coincide_entidad_detallada(
                                    titulo=p_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=url_directa,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                # Evaluamos la condición lógica (not res_match.coincide) para controlar el flujo
                                if not res_match.coincide:
                                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                                    logger.warning(f"URL directa Paris descartada ({res_match.motivo}): {p_name} != {perfume_nombre}")
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'formato_det' con res_match.formato_detectado or detectar_fo...
                                formato_det = res_match.formato_detectado or detectar_formato_oferta(p_name, url_directa)
                                # Asignamos 'clave_var' con (vol, formato_det)
                                clave_var = (vol, formato_det)
                                # Evaluamos la condición lógica (clave_var not in vols_vistos) para controlar el flujo
                                if clave_var not in vols_vistos:
                                    # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                    vols_vistos.add(clave_var)
                                    # Asignamos 'avail' con str(off.get('availability', '')).lower()
                                    avail = str(off.get("availability", "")).lower()
                                    # Asignamos 'en_stock' con False if 'outofstock' in avail or 'agotado...
                                    en_stock = False if ("outofstock" in avail or "agotado" in avail) else True
                                    # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                                    variedades.append({
                                        "exito": True,
                                        "precio_actual": p_act,
                                        "precio_normal": p_norm,
                                        "url": url_directa,
                                        "en_stock": en_stock,
                                        "volumen_ml": vol,
                                        "formato": formato_det,
                                        "metodo": "Paris Schema.org Direct",
                                    })
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.debug(f"Aviso leyendo URL directa Paris: {e}")

    # Evaluamos la condición lógica (variedades and any((v.get('en_stock') for v in varie...) para controlar el flujo
    if variedades and any(v.get("en_stock") for v in variedades):
        # Retornamos el resultado procesado (variedades)
        return variedades

    # Intento 2: Búsqueda dinámica en vivo en Paris
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    # Asignamos 'q' con urllib.parse.quote(query_str)
    q = urllib.parse.quote(query_str)
    # Asignamos 'url_search' con f'https://www.paris.cl/search?q={q}'
    url_search = f"https://www.paris.cl/search?q={q}"
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        res_s = _peticion_retail_resiliente(session, url_search, headers=headers, timeout=10, prefer_curl_cffi=False)
        # Evaluamos la condición lógica (res_s.status_code in (403, 429) and diagnostico is n...) para controlar el flujo
        if res_s.status_code in (403, 429) and diagnostico is not None:
            # Asignamos 'diagnostico['waf_bloqueado']' con True
            diagnostico["waf_bloqueado"] = True
            # Asignamos 'diagnostico['http_status']' con res_s.status_code
            diagnostico["http_status"] = res_s.status_code
        # Evaluamos la condición lógica (res_s.status_code == 200) para controlar el flujo
        elif res_s.status_code == 200:
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            soup_s = BeautifulSoup(res_s.text, "html.parser")
            # Asignamos 'tokens' con [t.lower() for t in re.sub('[^\\w\\s]', ' ...
            tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", perfume_nombre).split() if len(t) >= 2]
            # Evaluamos la condición lógica (not tokens) para controlar el flujo
            if not tokens:
                # Asignamos 'tokens' con [perfume_nombre.lower().strip()]
                tokens = [perfume_nombre.lower().strip()]
            # Asignamos 'links' con []
            links = []
            # Recorremos iterativamente cada 'a' en soup_s.find_all('a', href=True)
            for a in soup_s.find_all("a", href=True):
                # Asignamos 'h' con a.get('href', '')
                h = a.get("href", "")
                # Evaluamos la condición lógica ('.html' in h and any((tok in h.lower() for tok in to...) para controlar el flujo
                if ".html" in h and any(tok in h.lower() for tok in tokens):
                    # Asignamos 'clean_h' con 'https://www.paris.cl' + h.split('?')[0] i...
                    clean_h = "https://www.paris.cl" + h.split("?")[0] if h.startswith("/") else h.split("?")[0]
                    # Evaluamos la condición lógica (clean_h not in links) para controlar el flujo
                    if clean_h not in links:
                        # Ejecutamos instrucción: links.append(clean_h)
                        links.append(clean_h)
            # Recorremos iterativamente cada 'lk' en links[:5]
            for lk in links[:5]:
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    res_p = _peticion_retail_resiliente(session, lk, headers=headers, timeout=8, prefer_curl_cffi=False)
                    # Evaluamos la condición lógica (res_p.status_code == 200) para controlar el flujo
                    if res_p.status_code == 200:
                        # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                        soup_p = BeautifulSoup(res_p.text, "html.parser")
                        # Recorremos iterativamente cada 's_tag' en soup_p.find_all('script', type='applicatio...
                        for s_tag in soup_p.find_all("script", type="application/ld+json"):
                            # Evaluamos la condición lógica ('Product' in s_tag.text) para controlar el flujo
                            if "Product" in s_tag.text:
                                # Procesamiento de serialización o deserialización de estructura JSON
                                d = json.loads(s_tag.text)
                                # Asignamos 'p_name' con d.get('name', perfume_nombre)
                                p_name = d.get("name", perfume_nombre)
                                # Evaluamos la condición lógica (not es_producto_perfume_valido(p_name, marca=marca o...) para controlar el flujo
                                if not es_producto_perfume_valido(p_name, marca=marca or None, volumen_min_ml=25):
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'offers' con d.get('offers', [])
                                offers = d.get("offers", [])
                                # Asignamos 'lista_offs' con offers if isinstance(offers, list) else [o...
                                lista_offs = offers if isinstance(offers, list) else ([offers] if isinstance(offers, dict) else [])
                                # Asignamos 'precios_validos' con []
                                precios_validos = []
                                # Recorremos iterativamente cada 'o_item' en lista_offs
                                for o_item in lista_offs:
                                    # Evaluamos la condición lógica (isinstance(o_item, dict) and o_item.get('price') is ...) para controlar el flujo
                                    if isinstance(o_item, dict) and o_item.get("price") is not None:
                                        # Asignamos 'p_cand' con clean_digits(o_item.get('price'))
                                        p_cand = clean_digits(o_item.get("price"))
                                        # Evaluamos la condición lógica (es_precio_valido(p_cand)) para controlar el flujo
                                        if es_precio_valido(p_cand):
                                            # Ejecutamos instrucción: precios_validos.append(p_cand)
                                            precios_validos.append(p_cand)
                                # Asignamos 'off' con lista_offs[0] if lista_offs and isinstance...
                                off = lista_offs[0] if lista_offs and isinstance(lista_offs[0], dict) else {}
                                # Evaluamos la condición lógica (precios_validos) para controlar el flujo
                                if precios_validos:
                                    # Asignamos 'p_act' con min(precios_validos)
                                    p_act = min(precios_validos)
                                    # Asignamos 'p_norm' con max(precios_validos)
                                    p_norm = max(precios_validos)
                                    # Asignamos 'vol' con resolver_volumen_oferta(titulo_producto=p_...
                                    vol = resolver_volumen_oferta(
                                        titulo_producto=p_name,
                                        url_slug=lk,
                                        volumen_ml_defecto=volumen_ml_defecto,
                                        n_variantes_producto=1,
                                        es_tester=(detectar_formato_oferta(p_name, lk) == "tester"),
                                    )
                                    # Evaluamos la condición lógica (not vol or vol < 25 or (not es_precio_valido(p_act))) para controlar el flujo
                                    if not vol or vol < 25 or not es_precio_valido(p_act):
                                        # Evaluamos la condición lógica (not vol and diagnostico is not None) para controlar el flujo
                                        if not vol and diagnostico is not None:
                                            # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                                            diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                        continue
                                    # Asignamos 'res_match' con coincide_entidad_detallada(titulo=p_name, ...
                                    res_match = coincide_entidad_detallada(
                                        titulo=p_name,
                                        perfume_nombre=perfume_nombre,
                                        marca=marca,
                                        concentracion=concentracion,
                                        url=lk,
                                        precio_candidato=p_act,
                                        precio_referencia=precio_referencia,
                                    )
                                    # Evaluamos la condición lógica (not res_match.coincide) para controlar el flujo
                                    if not res_match.coincide:
                                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                        continue
                                    # Asignamos 'formato_det' con res_match.formato_detectado or detectar_fo...
                                    formato_det = res_match.formato_detectado or detectar_formato_oferta(p_name, lk)
                                    # Asignamos 'clave_var' con (vol, formato_det)
                                    clave_var = (vol, formato_det)
                                    # Asignamos 'avail' con str(off.get('availability', '')).lower()
                                    avail = str(off.get("availability", "")).lower()
                                    # Asignamos 'en_stock' con False if 'outofstock' in avail or 'agotado...
                                    en_stock = False if ("outofstock" in avail or "agotado" in avail) else True
                                    # Asignamos 'nueva_var' con {'exito': True, 'precio_actual': p_act, 'p...
                                    nueva_var = {
                                        "exito": True,
                                        "precio_actual": p_act,
                                        "precio_normal": p_norm,
                                        "url": lk,
                                        "en_stock": en_stock,
                                        "volumen_ml": vol,
                                        "formato": formato_det,
                                        "metodo": "Paris Live Schema.org",
                                    }
                                    # Evaluamos la condición lógica (clave_var not in vols_vistos) para controlar el flujo
                                    if clave_var not in vols_vistos:
                                        # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                        vols_vistos.add(clave_var)
                                        # Ejecutamos instrucción: variedades.append(nueva_var)
                                        variedades.append(nueva_var)
                                    else:
                                        # Si ya vimos este (volumen, formato) en otro vendedor de Paris Marketplace, conservar el de menor precio con stock
                                        for idx_v, v_prev in enumerate(variedades):
                                            # Evaluamos la condición lógica ((v_prev.get('volumen_ml'), v_prev.get('formato')) ==...) para controlar el flujo
                                            if (v_prev.get("volumen_ml"), v_prev.get("formato")) == clave_var:
                                                # Evaluamos la condición lógica (en_stock and (not v_prev.get('en_stock') or p_act < ...) para controlar el flujo
                                                if en_stock and (not v_prev.get("en_stock") or p_act < v_prev.get("precio_actual", p_act)):
                                                    # Asignamos 'variedades[idx_v]' con nueva_var
                                                    variedades[idx_v] = nueva_var
                                                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                                break
                except Exception:
                    # Ejecutamos instrucción: pass
                    pass
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error en búsqueda viva Paris para '{perfume_nombre}': {e}")

    # Retornamos el resultado procesado (variedades)
    return variedades


# Definición de función 'extraer_precio_paris' (parámetros: session, url_directa, perfume_nombre, volumen_ml)
def extraer_precio_paris(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrocompatibilidad con pruebas unitarias y selección de volumen específico."""
    # Asignamos 'vars_found' con extraer_variedades_paris(session, url_dire...
    vars_found = extraer_variedades_paris(session, url_directa, perfume_nombre, "", volumen_ml)
    # Evaluamos la condición lógica (vars_found) para controlar el flujo
    if vars_found:
        # Evaluamos la condición lógica (volumen_ml) para controlar el flujo
        if volumen_ml:
            # Asignamos 'exacto' con [v for v in vars_found if v.get('volumen_m...
            exacto = [v for v in vars_found if v.get("volumen_ml") == volumen_ml]
            # Evaluamos la condición lógica (exacto) para controlar el flujo
            if exacto:
                # Retornamos el resultado procesado (exacto[0])
                return exacto[0]
        # Retornamos el resultado procesado (vars_found[0])
        return vars_found[0]
    # Retornamos el resultado procesado ({'exito': False})
    return {"exito": False}


# - ¿Qué hace esta función (Extractor Ripley)?:
#   Consume la API interna de catálogo de Ripley en formato JSON estructurado,
#   extrayendo SKU, variantes de tamaño y precios oficiales de la tienda.
def extraer_variedades_ripley(
    session: requests.Session,
    url_directa: Optional[str],
    perfume_nombre: str,
    marca: str = "",
    volumen_ml_defecto: Optional[int] = None,
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
    diagnostico: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples presentaciones de Ripley Chile validando entidad, vendedores Marketplace
    y distinguiendo bloqueos HTTP 403 WAF de falta real de stock.
    """
    # Asignamos 'variedades' con []
    variedades: List[Dict[str, Any]] = []
    # Asignamos 'vols_vistos' con set()
    vols_vistos = set()
    # Asignamos 'query_str' con f'{marca} {perfume_nombre}'.strip() if mar...
    query_str = (
        f"{marca} {perfume_nombre}".strip()
        if (marca and marca.lower() not in perfume_nombre.lower())
        else perfume_nombre.strip()
    )
    # Asignamos 'q' con urllib.parse.quote(query_str)
    q = urllib.parse.quote(query_str)
    # Asignamos 'url_search' con f'https://simple.ripley.cl/search/{q}'
    url_search = f"https://simple.ripley.cl/search/{q}"

    # Asignamos 'headers' con {'User-Agent': random.choice(USER_AGENTS),...
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Referer": "https://simple.ripley.cl/",
    }

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'c_session' con None
        c_session = None
        # Evaluamos la condición lógica (curl_requests is not None) para controlar el flujo
        if curl_requests is not None:
            # Asignamos 'c_session' con curl_requests.Session(impersonate='chrome1...
            c_session = curl_requests.Session(impersonate="chrome124")
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = c_session.get(url_search, headers=headers, timeout=14)
        else:
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res = session.get(url_search, headers=obtener_headers_navegador(), timeout=10)

        # Evaluamos la condición lógica (res.status_code in (403, 429)) para controlar el flujo
        if res.status_code in (403, 429):
            # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
            if diagnostico is not None:
                # Asignamos 'diagnostico['waf_bloqueado']' con True
                diagnostico["waf_bloqueado"] = True
                # Asignamos 'diagnostico['http_status']' con res.status_code
                diagnostico["http_status"] = res.status_code
        # Evaluamos la condición lógica (res.status_code == 200) para controlar el flujo
        elif res.status_code == 200:
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            tag = soup.find("script", id="__NEXT_DATA__")
            # Evaluamos la condición lógica (tag and tag.text) para controlar el flujo
            if tag and tag.text:
                # Procesamiento de serialización o deserialización de estructura JSON
                data = json.loads(tag.text)
                # Asignamos 'prods' con data.get('props', {}).get('pageProps', {})...
                prods = data.get("props", {}).get("pageProps", {}).get("findabilityProps", {}).get("data", {}).get("products", [])

                # Mapear enlaces SEO reales del DOM (<a href="/slug-mpm123...">) por parentProductID/SKU
                dom_links_map: Dict[str, str] = {}
                # Recorremos iterativamente cada 'a_tag' en soup.find_all('a', href=True)
                for a_tag in soup.find_all("a", href=True):
                    # Asignamos 'href_clean' con a_tag['href'].split('?')[0].strip()
                    href_clean = a_tag["href"].split("?")[0].strip()
                    # Evaluamos la condición lógica (href_clean.startswith('/') and len(href_clean) > 4) para controlar el flujo
                    if href_clean.startswith("/") and len(href_clean) > 4:
                        # Asignamos 'dom_links_map[href_clean.lower()]' con f'https://simple.ripley.cl{href_clean}'
                        dom_links_map[href_clean.lower()] = f"https://simple.ripley.cl{href_clean}"

                # Definición de función '_filtrar_candidatos_ripley' (parámetros: lista_prods, mapa_links)
                def _filtrar_candidatos_ripley(lista_prods: List[Dict[str, Any]], mapa_links: Dict[str, str]) -> List[Tuple[Dict[str, Any], str]]:
                    # Asignamos 'cands' con []
                    cands: List[Tuple[Dict[str, Any], str]] = []
                    # Recorremos iterativamente cada 'p_item' en lista_prods
                    for p_item in lista_prods:
                        # Asignamos 'd_name' con p_item.get('name', '')
                        d_name = p_item.get("name", "")
                        # Asignamos 'shop_obj' con p_item.get('shop')
                        shop_obj = p_item.get("shop")
                        # Asignamos 'shop_name' con shop_obj.get('shopName') if isinstance(sho...
                        shop_name = shop_obj.get("shopName") if isinstance(shop_obj, dict) else None
                        # Asignamos 'r_seller' con p_item.get('marketplaceSeller') or p_item....
                        r_seller = p_item.get("marketplaceSeller") or p_item.get("sellerName") or shop_name or p_item.get("seller")
                        # Evaluamos la condición lógica (_es_vendedor_marketplace_no_verificado(r_seller, mar...) para controlar el flujo
                        if _es_vendedor_marketplace_no_verificado(r_seller, marca, perfume_nombre):
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Asignamos 'p_id' con p_item.get('parentProductID') or p_item.ge...
                        p_id = p_item.get("parentProductID") or p_item.get("sku")
                        # Asignamos 'slug' con p_item.get('url')
                        slug = p_item.get("url")
                        # Asignamos 'pdp_url' con ''
                        pdp_url = ""
                        # Evaluamos la condición lógica (slug) para controlar el flujo
                        if slug:
                            # Asignamos 'pdp_url' con f"https://simple.ripley.cl/{slug.lstrip('/...
                            pdp_url = f"https://simple.ripley.cl/{slug.lstrip('/')}" if not str(slug).startswith("http") else str(slug)
                        # Evaluamos la condición lógica (p_id) para controlar el flujo
                        elif p_id:
                            # Asignamos 'pid_low' con str(p_id).lower()
                            pid_low = str(p_id).lower()
                            # Recorremos iterativamente cada '(k_href, full_u)' en mapa_links.items()
                            for k_href, full_u in mapa_links.items():
                                # Evaluamos la condición lógica (k_href.endswith(f'-{pid_low}') or k_href.endswith(f'...) para controlar el flujo
                                if k_href.endswith(f"-{pid_low}") or k_href.endswith(f"/{pid_low}"):
                                    # Asignamos 'pdp_url' con full_u
                                    pdp_url = full_u
                                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                    break
                            # Evaluamos la condición lógica (not pdp_url) para controlar el flujo
                            if not pdp_url:
                                # Asignamos 'pdp_url' con f'https://simple.ripley.cl/{p_id}'
                                pdp_url = f"https://simple.ripley.cl/{p_id}"
                        # Evaluamos la condición lógica (not es_producto_perfume_valido(d_name, marca=marca o...) para controlar el flujo
                        if not es_producto_perfume_valido(d_name, marca=marca or None, volumen_min_ml=25):
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Asignamos 'res_cand' con coincide_entidad_detallada(titulo=d_name, ...
                        res_cand = coincide_entidad_detallada(
                            titulo=d_name,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=pdp_url,
                        )
                        # Evaluamos la condición lógica (not res_cand.coincide) para controlar el flujo
                        if not res_cand.coincide:
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Ejecutamos instrucción: cands.append((p_item, pdp_url))
                        cands.append((p_item, pdp_url))
                    # Retornamos el resultado procesado (cands)
                    return cands

                # Asignamos 'candidatos' con _filtrar_candidatos_ripley(prods, dom_link...
                candidatos = _filtrar_candidatos_ripley(prods, dom_links_map)

                # Si la consulta con sufijo de concentración (ej. 'EDP', 'EDT') diluyó el motor de búsqueda de Ripley,
                # reintentar limpiando el sufijo de concentración para obtener coincidencias exactas del perfume.
                if not candidatos:
                    # Asignamos 'nombre_sin_conc' con re.sub('\\b(?:edp|edt|edc|eau\\s+de\\s+par...
                    nombre_sin_conc = re.sub(
                        r"\b(?:edp|edt|edc|eau\s+de\s+parfum|eau\s+de\s+toilette|parfum|extrait)\b",
                        "",
                        perfume_nombre,
                        flags=re.IGNORECASE,
                    ).strip()
                    # Evaluamos la condición lógica (nombre_sin_conc and nombre_sin_conc.lower() != perfu...) para controlar el flujo
                    if nombre_sin_conc and nombre_sin_conc.lower() != perfume_nombre.lower():
                        # Asignamos 'q_alt_str' con f'{marca} {nombre_sin_conc}'.strip() if ma...
                        q_alt_str = (
                            f"{marca} {nombre_sin_conc}".strip()
                            if (marca and marca.lower() not in nombre_sin_conc.lower())
                            else nombre_sin_conc
                        )
                        # Asignamos 'url_search_alt' con f'https://simple.ripley.cl/search/{urllib....
                        url_search_alt = f"https://simple.ripley.cl/search/{urllib.parse.quote(q_alt_str)}"
                        # Bloque try/except para manejo seguro de errores y resiliencia operativa
                        try:
                            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                            res_alt = (
                                c_session.get(url_search_alt, headers=headers, timeout=14)
                                if c_session is not None
                                else session.get(url_search_alt, headers=obtener_headers_navegador(), timeout=10)
                            )
                            # Evaluamos la condición lógica (res_alt.status_code == 200) para controlar el flujo
                            if res_alt.status_code == 200:
                                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                                soup_alt = BeautifulSoup(res_alt.text, "html.parser")
                                # Asignamos 'tag_alt' con soup_alt.find('script', id='__NEXT_DATA__')
                                tag_alt = soup_alt.find("script", id="__NEXT_DATA__")
                                # Evaluamos la condición lógica (tag_alt and tag_alt.text) para controlar el flujo
                                if tag_alt and tag_alt.text:
                                    # Procesamiento de serialización o deserialización de estructura JSON
                                    data_alt = json.loads(tag_alt.text)
                                    # Asignamos 'prods_alt' con data_alt.get('props', {}).get('pageProps',...
                                    prods_alt = data_alt.get("props", {}).get("pageProps", {}).get("findabilityProps", {}).get("data", {}).get("products", [])
                                    # Asignamos 'dom_links_alt' con {}
                                    dom_links_alt: Dict[str, str] = {}
                                    # Recorremos iterativamente cada 'a_tag' en soup_alt.find_all('a', href=True)
                                    for a_tag in soup_alt.find_all("a", href=True):
                                        # Asignamos 'href_clean' con a_tag['href'].split('?')[0].strip()
                                        href_clean = a_tag["href"].split("?")[0].strip()
                                        # Evaluamos la condición lógica (href_clean.startswith('/') and len(href_clean) > 4) para controlar el flujo
                                        if href_clean.startswith("/") and len(href_clean) > 4:
                                            # Asignamos 'dom_links_alt[href_clean.lower()]' con f'https://simple.ripley.cl{href_clean}'
                                            dom_links_alt[href_clean.lower()] = f"https://simple.ripley.cl{href_clean}"
                                    # Asignamos 'candidatos' con _filtrar_candidatos_ripley(prods_alt, dom_...
                                    candidatos = _filtrar_candidatos_ripley(prods_alt, dom_links_alt)
                        except Exception:
                            # Ejecutamos instrucción: pass
                            pass

                # Recorremos iterativamente cada '(p, pdp_url)' en candidatos[:3]
                for p, pdp_url in candidatos[:3]:
                    # Asignamos 'added_from_pdp' con False
                    added_from_pdp = False
                    # Evaluamos la condición lógica (pdp_url and c_session is not None) para controlar el flujo
                    if pdp_url and c_session is not None:
                        # Bloque try/except para manejo seguro de errores y resiliencia operativa
                        try:
                            # Asignamos 'headers_pdp' con {'User-Agent': headers['User-Agent'], 'Ref...
                            headers_pdp = {
                                "User-Agent": headers["User-Agent"],
                                "Referer": url_search,
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
                            }
                            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                            res_p = c_session.get(pdp_url, headers=headers_pdp, timeout=20)
                            # Evaluamos la condición lógica (res_p.status_code == 200) para controlar el flujo
                            if res_p.status_code == 200:
                                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                                soup_p = BeautifulSoup(res_p.text, "html.parser")
                                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                                tag_p = soup_p.find("script", id="__NEXT_DATA__")
                                # Evaluamos la condición lógica (tag_p and tag_p.text) para controlar el flujo
                                if tag_p and tag_p.text:
                                    # Procesamiento de serialización o deserialización de estructura JSON
                                    d_pdp = json.loads(tag_p.text)
                                    # Asignamos 'prod_info' con d_pdp.get('props', {}).get('pageProps', {}...
                                    prod_info = d_pdp.get("props", {}).get("pageProps", {}).get("detailProps", {}).get("data", {}).get("product", {})
                                    # Asignamos 'p_seller' con prod_info.get('sellerName') or prod_info.g...
                                    p_seller = prod_info.get("sellerName") or prod_info.get("marketplaceSeller")
                                    # Evaluamos la condición lógica (_es_vendedor_marketplace_no_verificado(p_seller, mar...) para controlar el flujo
                                    if _es_vendedor_marketplace_no_verificado(p_seller, marca, perfume_nombre):
                                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                        continue
                                    # Asignamos 'variants' con prod_info.get('variants', [])
                                    variants = prod_info.get("variants", [])
                                    # Asignamos 'pdp_title' con prod_info.get('name', p.get('name', ''))
                                    pdp_title = prod_info.get("name", p.get("name", ""))

                                    # Recorremos iterativamente cada 'v' en variants
                                    for v in variants:
                                        # Asignamos 'price_obj' con v.get('price', {})
                                        price_obj = v.get("price", {})
                                        # Asignamos 'sale_p' con price_obj.get('sale', {}).get('valueNumber...
                                        sale_p = price_obj.get("sale", {}).get("valueNumber") or price_obj.get("master", {}).get("valueNumber")
                                        # Asignamos 'norm_p' con price_obj.get('master', {}).get('valueNumb...
                                        norm_p = price_obj.get("master", {}).get("valueNumber") or sale_p
                                        # Evaluamos la condición lógica (not sale_p or not es_precio_valido(sale_p)) para controlar el flujo
                                        if not sale_p or not es_precio_valido(sale_p):
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue

                                        # Asignamos 'vol' con None
                                        vol = None
                                        # Recorremos iterativamente cada 'def_attr' en v.get('definingAttribute', [])
                                        for def_attr in v.get("definingAttribute", []):
                                            # Asignamos 'val_str' con def_attr.get('value', '')
                                            val_str = def_attr.get("value", "")
                                            # Asignamos 'vol' con extraer_volumen_ml_opcional(val_str)
                                            vol = extraer_volumen_ml_opcional(val_str)
                                            # Evaluamos la condición lógica (vol) para controlar el flujo
                                            if vol:
                                                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                                break

                                        # Evaluamos la condición lógica (not vol) para controlar el flujo
                                        if not vol:
                                            # Recorremos iterativamente cada 'attr' en v.get('attributes', [])
                                            for attr in v.get("attributes", []):
                                                # Evaluamos la condición lógica (attr.get('usage') == 'Defining' or 'contenido_perfum...) para controlar el flujo
                                                if attr.get("usage") == "Defining" or "contenido_perfume" in (attr.get("identifier") or "").lower():
                                                    # Asignamos 'vals' con attr.get('Values', [{}])
                                                    vals = attr.get("Values", [{}])
                                                    # Asignamos 'v_str' con vals[0].get('values', '') if vals else ''
                                                    v_str = vals[0].get("values", "") if vals else ""
                                                    # Asignamos 'vol' con extraer_volumen_ml_opcional(v_str)
                                                    vol = extraer_volumen_ml_opcional(v_str)
                                                    # Evaluamos la condición lógica (vol) para controlar el flujo
                                                    if vol:
                                                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                                                        break

                                        # Evaluamos la condición lógica (not vol) para controlar el flujo
                                        if not vol:
                                            # Asignamos 'vol' con resolver_volumen_oferta(titulo_producto=pd...
                                            vol = resolver_volumen_oferta(
                                                titulo_producto=pdp_title,
                                                url_slug=pdp_url or "",
                                                volumen_ml_defecto=volumen_ml_defecto,
                                                n_variantes_producto=max(1, len(variants)),
                                                es_tester=(detectar_formato_oferta(pdp_title, pdp_url or "") == "tester"),
                                            )
                                        # Evaluamos la condición lógica (not vol or vol < 25) para controlar el flujo
                                        if not vol or vol < 25:
                                            # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
                                            if diagnostico is not None:
                                                # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                                                diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue

                                        # Asignamos 'res_v' con coincide_entidad_detallada(titulo=pdp_titl...
                                        res_v = coincide_entidad_detallada(
                                            titulo=pdp_title,
                                            perfume_nombre=perfume_nombre,
                                            marca=marca,
                                            concentracion=concentracion,
                                            url=pdp_url,
                                            precio_candidato=int(sale_p),
                                            precio_referencia=precio_referencia,
                                        )
                                        # Evaluamos la condición lógica (not res_v.coincide) para controlar el flujo
                                        if not res_v.coincide:
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue

                                        # Asignamos 'formato_det' con res_v.formato_detectado or detectar_format...
                                        formato_det = res_v.formato_detectado or detectar_formato_oferta(pdp_title, pdp_url)
                                        # Asignamos 'clave_var' con (vol, formato_det)
                                        clave_var = (vol, formato_det)
                                        # Evaluamos la condición lógica (clave_var in vols_vistos) para controlar el flujo
                                        if clave_var in vols_vistos:
                                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                            continue
                                        # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                        vols_vistos.add(clave_var)

                                        # Asignamos 'in_stock' con bool(v.get('stock', False)) and (not bool(...
                                        in_stock = (
                                            bool(v.get("stock", False))
                                            and not bool(v.get("notBuyable", False))
                                            and not bool(v.get("notSelectable", False))
                                            and "sin stock" not in str(v.get("statusUI", "")).lower()
                                            and "agotado" not in str(v.get("statusUI", "")).lower()
                                        )

                                        # Asignamos 'norm_valido' con norm_p if es_precio_valido(norm_p) and nor...
                                        norm_valido = norm_p if (es_precio_valido(norm_p) and norm_p > sale_p) else sale_p
                                        # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': s...
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": sale_p,
                                            "precio_normal": norm_valido,
                                            "url": pdp_url,
                                            "en_stock": in_stock,
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Ripley Live PDP Variants",
                                        })
                                        # Asignamos 'added_from_pdp' con True
                                        added_from_pdp = True
                        except Exception as e_pdp:
                            # Registro de evento diagnóstico en la bitácora (logger) del sistema
                            logger.debug(f"Aviso leyendo PDP Ripley {pdp_url}: {e_pdp}")

                    # Evaluamos la condición lógica (not added_from_pdp) para controlar el flujo
                    if not added_from_pdp:
                        # Asignamos 'p_act' con p.get('priceNumber', 0)
                        p_act = p.get("priceNumber", 0)
                        # Asignamos 'p_norm' con p.get('masterPriceNumber', p_act) or p_act
                        p_norm = p.get("masterPriceNumber", p_act) or p_act
                        # Evaluamos la condición lógica (p_act and es_precio_valido(p_act)) para controlar el flujo
                        if p_act and es_precio_valido(p_act):
                            # Asignamos 'p_title' con p.get('name', '')
                            p_title = p.get("name", "")
                            # Asignamos 'vol' con resolver_volumen_oferta(titulo_producto=p_...
                            vol = resolver_volumen_oferta(
                                titulo_producto=p_title,
                                url_slug=pdp_url or "",
                                volumen_ml_defecto=volumen_ml_defecto,
                                n_variantes_producto=1,
                                es_tester=(detectar_formato_oferta(p_title, pdp_url or "") == "tester"),
                            )
                            # Evaluamos la condición lógica (vol and vol >= 25) para controlar el flujo
                            if vol and vol >= 25:
                                # Asignamos 'res_sc' con coincide_entidad_detallada(titulo=p_title,...
                                res_sc = coincide_entidad_detallada(
                                    titulo=p_title,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=pdp_url or url_search,
                                    precio_candidato=int(p_act),
                                    precio_referencia=precio_referencia,
                                )
                                # Evaluamos la condición lógica (res_sc.coincide) para controlar el flujo
                                if res_sc.coincide:
                                    # Asignamos 'formato_det' con res_sc.formato_detectado or detectar_forma...
                                    formato_det = res_sc.formato_detectado or detectar_formato_oferta(p_title, pdp_url or "")
                                    # Asignamos 'clave_var' con (vol, formato_det)
                                    clave_var = (vol, formato_det)
                                    # Evaluamos la condición lógica (clave_var not in vols_vistos) para controlar el flujo
                                    if clave_var not in vols_vistos:
                                        # Ejecutamos instrucción: vols_vistos.add(clave_var)
                                        vols_vistos.add(clave_var)
                                        # Asignamos 'norm_valido' con p_norm if es_precio_valido(p_norm) and p_n...
                                        norm_valido = p_norm if (es_precio_valido(p_norm) and p_norm > p_act) else p_act
                                        # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                                        variedades.append({
                                            "exito": True,
                                            "precio_actual": p_act,
                                            "precio_normal": norm_valido,
                                            "url": pdp_url or url_search,
                                            "en_stock": bool(p.get("inStock", True)),
                                            "volumen_ml": vol,
                                            "formato": formato_det,
                                            "metodo": "Ripley Chrome Search Card",
                                        })
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Error consultando Ripley para '{perfume_nombre}': {e}")

    # Evaluamos la condición lógica (not variedades and url_directa) para controlar el flujo
    if not variedades and url_directa:
        # Asignamos 'res_old' con extraer_precio_ripley(session, url_directa...
        res_old = extraer_precio_ripley(
            session,
            url_directa,
            perfume_nombre,
            volumen_ml_defecto,
            marca=marca,
            concentracion=concentracion,
            precio_referencia=precio_referencia,
        )
        # Evaluamos la condición lógica (res_old.get('waf_bloqueado') and diagnostico is not ...) para controlar el flujo
        if res_old.get("waf_bloqueado") and diagnostico is not None:
            # Asignamos 'diagnostico['waf_bloqueado']' con True
            diagnostico["waf_bloqueado"] = True
        # Evaluamos la condición lógica (res_old.get('exito')) para controlar el flujo
        if res_old.get("exito"):
            # Ejecutamos instrucción: variedades.append(res_old)
            variedades.append(res_old)

    # Retornamos el resultado procesado (variedades)
    return variedades


# Definición de función 'extraer_precio_ripley' (parámetros: session, url_directa, perfume_nombre, volumen_ml, ...)
def extraer_precio_ripley(
    session: requests.Session,
    url_directa: str,
    perfume_nombre: str,
    volumen_ml: Optional[int] = None,
    marca: str = "",
    concentracion: str = "",
    precio_referencia: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Extrae precio y stock de Ripley Chile combinando Schema.org y selectores DOM,
    validando entidad en auto-sanación 404 y manejando protecciones WAF (HTTP 403).
    """
    # Asignamos 'headers' con obtener_headers_navegador(referer='https:/...
    headers = obtener_headers_navegador(referer="https://simple.ripley.cl/")
    # Asignamos 'url_a_probar' con url_directa
    url_a_probar = url_directa

    # Intento 1: Ficha directa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        res = _peticion_retail_resiliente(session, url_a_probar, headers=headers, timeout=12, prefer_curl_cffi=True)
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Fallo conexión Ripley direct: {e}")
        # Asignamos 'res' con None
        res = None

    # Evaluamos la condición lógica (res and res.status_code in (403, 429)) para controlar el flujo
    if res and res.status_code in (403, 429):
        # Retornamos el resultado procesado ({'exito': False, 'waf_bloqueado': True, 'motivo...)
        return {
            "exito": False,
            "waf_bloqueado": True,
            "motivo": f"Ripley protegido por Cloudflare WAF (HTTP {res.status_code})",
        }

    # Intento 2: Si dio 404, auto-sanar validando entidad antes de adoptar el enlace nuevo
    if not res or res.status_code != 200:
        # Asignamos 'query_str' con f'{marca} {perfume_nombre}'.strip() if mar...
        query_str = (
            f"{marca} {perfume_nombre}".strip()
            if (marca and marca.lower() not in perfume_nombre.lower())
            else perfume_nombre.strip()
        )
        # Asignamos 'q' con urllib.parse.quote(query_str)
        q = urllib.parse.quote(query_str)
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            res_s = _peticion_retail_resiliente(session, f"https://simple.ripley.cl/search/{q}", headers=headers, timeout=12, prefer_curl_cffi=True)
            # Evaluamos la condición lógica (res_s.status_code in (403, 429)) para controlar el flujo
            if res_s.status_code in (403, 429):
                # Retornamos el resultado procesado ({'exito': False, 'waf_bloqueado': True, 'motivo...)
                return {
                    "exito": False,
                    "waf_bloqueado": True,
                    "motivo": f"Ripley protegido por Cloudflare WAF (HTTP {res_s.status_code})",
                }
            # Evaluamos la condición lógica (res_s.status_code == 200) para controlar el flujo
            if res_s.status_code == 200:
                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                soup_s = BeautifulSoup(res_s.text, "html.parser")
                # Asignamos 'tokens' con [t.lower() for t in re.sub('[^\\w\\s]', ' ...
                tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", perfume_nombre).split() if len(t) >= 3]
                # Recorremos iterativamente cada 'a' en soup_s.find_all('a', href=True)
                for a in soup_s.find_all("a", href=True):
                    # Asignamos 'h' con a.get('href', '')
                    h = a.get("href", "")
                    # Evaluamos la condición lógica (not h.endswith('p')) para controlar el flujo
                    if not h.endswith("p"):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'cand_url' con h.split('?')[0] if h.startswith('http') el...
                    cand_url = h.split("?")[0] if h.startswith("http") else "https://simple.ripley.cl" + h.split("?")[0]
                    # Asignamos 'anchor_txt' con a.get_text(' ', strip=True)
                    anchor_txt = a.get_text(" ", strip=True)
                    # Evaluamos la condición lógica (anchor_txt and len(anchor_txt) >= 4) para controlar el flujo
                    if anchor_txt and len(anchor_txt) >= 4:
                        # Asignamos 'res_a' con coincide_entidad_detallada(titulo=anchor_t...
                        res_a = coincide_entidad_detallada(
                            titulo=anchor_txt,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=cand_url,
                        )
                        # Evaluamos la condición lógica (not res_a.coincide) para controlar el flujo
                        if not res_a.coincide:
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                    # Evaluamos la condición lógica (tokens and (not all((tok in h.lower() for tok in tok...) para controlar el flujo
                    elif tokens and not all(tok in h.lower() for tok in tokens[:2]):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'url_a_probar' con cand_url
                    url_a_probar = cand_url
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    res = _peticion_retail_resiliente(session, url_a_probar, headers=headers, timeout=10, prefer_curl_cffi=True)
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"Fallo auto-sanación Ripley: {e}")

    # Paso 3: Parsear ficha del producto con validación de entidad
    if res and res.status_code == 200:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            # Asignamos 'blocks' con re.findall('<script[^>]*type="application/...
            blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', res.text, re.DOTALL)
            # Recorremos iterativamente cada 'b' en blocks
            for b in blocks:
                # Evaluamos la condición lógica ('"@type":"Product"' in b or '"@type": "Product"' in b) para controlar el flujo
                if '"@type":"Product"' in b or '"@type": "Product"' in b:
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Procesamiento de serialización o deserialización de estructura JSON
                        d = json.loads(b)
                        # Asignamos 'p_name' con d.get('name', '')
                        p_name = d.get("name", "")
                        # Asignamos 'offers' con d.get('offers', {})
                        offers = d.get("offers", {})
                        # Evaluamos la condición lógica (isinstance(offers, dict) and 'price' in offers) para controlar el flujo
                        if isinstance(offers, dict) and "price" in offers:
                            # Asignamos 'p_act' con clean_digits(offers['price'])
                            p_act = clean_digits(offers["price"])
                            # Evaluamos la condición lógica (not es_precio_valido(p_act)) para controlar el flujo
                            if not es_precio_valido(p_act):
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue
                            # Evaluamos la condición lógica (p_name) para controlar el flujo
                            if p_name:
                                # Asignamos 'res_ld' con coincide_entidad_detallada(titulo=p_name, ...
                                res_ld = coincide_entidad_detallada(
                                    titulo=p_name,
                                    perfume_nombre=perfume_nombre,
                                    marca=marca,
                                    concentracion=concentracion,
                                    url=url_a_probar,
                                    precio_candidato=p_act,
                                    precio_referencia=precio_referencia,
                                )
                                # Evaluamos la condición lógica (not res_ld.coincide) para controlar el flujo
                                if not res_ld.coincide:
                                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                    continue
                                # Asignamos 'fmt_det' con res_ld.formato_detectado or detectar_forma...
                                fmt_det = res_ld.formato_detectado or detectar_formato_oferta(p_name, url_a_probar)
                                # Asignamos 'vol_det' con resolver_volumen_oferta(titulo_producto=p_...
                                vol_det = resolver_volumen_oferta(
                                    titulo_producto=p_name,
                                    url_slug=url_a_probar,
                                    volumen_ml_defecto=volumen_ml,
                                    n_variantes_producto=1,
                                    es_tester=(fmt_det == "tester"),
                                )
                            else:
                                # Asignamos 'fmt_det' con detectar_formato_oferta(perfume_nombre, ur...
                                fmt_det = detectar_formato_oferta(perfume_nombre, url_a_probar)
                                # Asignamos 'vol_det' con resolver_volumen_oferta(url_slug=url_a_pro...
                                vol_det = resolver_volumen_oferta(
                                    url_slug=url_a_probar,
                                    volumen_ml_defecto=volumen_ml,
                                    n_variantes_producto=1,
                                    es_tester=(fmt_det == "tester"),
                                )
                            # Evaluamos la condición lógica (not vol_det or vol_det < 25) para controlar el flujo
                            if not vol_det or vol_det < 25:
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue
                            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                            avail_r = str(offers.get("availability", "")).lower()
                            # Asignamos 'en_stock_r' con False if 'outofstock' in avail_r or 'agota...
                            en_stock_r = False if ("outofstock" in avail_r or "agotado" in avail_r) else True
                            # Retornamos el resultado procesado ({'exito': True, 'precio_actual': p_act, 'precio...)
                            return {
                                "exito": True,
                                "precio_actual": p_act,
                                "precio_normal": p_act,
                                "url": url_a_probar,
                                "en_stock": en_stock_r,
                                "volumen_ml": vol_det,
                                "formato": fmt_det,
                                "metodo": "Ripley Schema.org",
                            }
                    except Exception:
                        # Ejecutamos instrucción: pass
                        pass

            # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
            p_val = soup.find(class_=lambda c: c and "price-value" in c)
            # Evaluamos la condición lógica (p_val) para controlar el flujo
            if p_val:
                # Asignamos 'p_act' con clean_digits(p_val.get_text())
                p_act = clean_digits(p_val.get_text())
                # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                agotado_dom = bool(soup.find(string=re.compile(r"agotado|sin stock", re.I)))
                # Evaluamos la condición lógica (es_precio_valido(p_act)) para controlar el flujo
                if es_precio_valido(p_act):
                    # Extracción y análisis de nodos del árbol DOM HTML mediante BeautifulSoup
                    dom_title_el = soup.find("h1") or soup.find("title")
                    # Asignamos 'dom_title' con dom_title_el.get_text(' ', strip=True) if ...
                    dom_title = dom_title_el.get_text(" ", strip=True) if dom_title_el else ""
                    # Evaluamos la condición lógica (dom_title) para controlar el flujo
                    if dom_title:
                        # Asignamos 'res_dom' con coincide_entidad_detallada(titulo=dom_titl...
                        res_dom = coincide_entidad_detallada(
                            titulo=dom_title,
                            perfume_nombre=perfume_nombre,
                            marca=marca,
                            concentracion=concentracion,
                            url=url_a_probar,
                            precio_candidato=p_act,
                            precio_referencia=precio_referencia,
                        )
                        # Evaluamos la condición lógica (not res_dom.coincide) para controlar el flujo
                        if not res_dom.coincide:
                            # Retornamos el resultado procesado ({'exito': False, 'motivo': res_dom.motivo})
                            return {"exito": False, "motivo": res_dom.motivo}
                        # Asignamos 'fmt_dom' con res_dom.formato_detectado or detectar_form...
                        fmt_dom = res_dom.formato_detectado or detectar_formato_oferta(dom_title, url_a_probar)
                        # Asignamos 'vol_dom' con resolver_volumen_oferta(titulo_producto=do...
                        vol_dom = resolver_volumen_oferta(
                            titulo_producto=dom_title,
                            url_slug=url_a_probar,
                            volumen_ml_defecto=volumen_ml,
                            n_variantes_producto=1,
                            es_tester=(fmt_dom == "tester"),
                        )
                    else:
                        # Asignamos 'fmt_dom' con detectar_formato_oferta(perfume_nombre, ur...
                        fmt_dom = detectar_formato_oferta(perfume_nombre, url_a_probar)
                        # Asignamos 'vol_dom' con resolver_volumen_oferta(url_slug=url_a_pro...
                        vol_dom = resolver_volumen_oferta(
                            url_slug=url_a_probar,
                            volumen_ml_defecto=volumen_ml,
                            n_variantes_producto=1,
                            es_tester=(fmt_dom == "tester"),
                        )
                    # Evaluamos la condición lógica (vol_dom and vol_dom >= 25) para controlar el flujo
                    if vol_dom and vol_dom >= 25:
                        # Retornamos el resultado procesado ({'exito': True, 'precio_actual': p_act, 'precio...)
                        return {
                            "exito": True,
                            "precio_actual": p_act,
                            "precio_normal": p_act,
                            "url": url_a_probar,
                            "en_stock": not agotado_dom,
                            "volumen_ml": vol_dom,
                            "formato": fmt_dom,
                            "metodo": "Ripley DOM Price",
                        }
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"Error parseando precio en Ripley: {e}")

    # Retornamos el resultado procesado ({'exito': False})
    return {"exito": False}


# =============================================================================
# PERSISTENCIA DEL REPORTE DE AUDITORÍA
# =============================================================================

def guardar_reporte_auditoria(reporte: Dict[str, Any], ruta_destino: Optional[str] = None) -> str:
    """Guarda el reporte consolidado de la última ejecución en formato JSON auditable."""
    # Ejecutamos instrucción: os.makedirs(REPORTES_DIR, exist_ok=True)
    os.makedirs(REPORTES_DIR, exist_ok=True)
    # Asignamos 'target_path' con ruta_destino or REPORTE_ULTIMO_PATH
    target_path = ruta_destino or REPORTE_ULTIMO_PATH
    # Gestión automática de contexto y recursos para: open(target_path, 'w', encoding='utf-8')
    with open(target_path, "w", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Reporte de auditoría generado exitosamente en: {target_path}")
    # Retornamos el resultado procesado (target_path)
    return target_path


# Definición de función 'obtener_ultimo_reporte_scraping' sin parámetros externos
def obtener_ultimo_reporte_scraping() -> Optional[Dict[str, Any]]:
    """Lee y retorna el último reporte de auditoría generado por el scraper."""
    # Evaluamos la condición lógica (os.path.exists(REPORTE_ULTIMO_PATH)) para controlar el flujo
    if os.path.exists(REPORTE_ULTIMO_PATH):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Gestión automática de contexto y recursos para: open(REPORTE_ULTIMO_PATH, 'r', encoding='utf-8')
            with open(REPORTE_ULTIMO_PATH, "r", encoding="utf-8") as f:
                # Retornamos el resultado procesado (json.load(f))
                return json.load(f)
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"No se pudo leer el reporte de auditoría: {e}")
    # Retornamos el resultado procesado (None)
    return None

# =============================================================================
# MOTOR PRINCIPAL DE EJECUCIÓN ETL (ARQUITECTURA DE ROTACIONES LRU)
# =============================================================================

def _combinar_tiendas_stats(
    stats_list: List[Dict[str, Dict[str, Any]]],
    tiendas_db: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Combina métricas agregadas de comercios auditados a lo largo de múltiples rotaciones."""
    # Asignamos 'consolidado' con {t['nombre']: {'consultas': 0, 'exitos_en_...
    consolidado = {
        t["nombre"]: {
            "consultas": 0,
            "exitos_en_vivo": 0,
            "fallbacks_seguridad": 0,
            "bloqueos_waf": 0,
            "omitidos_circuit_breaker": 0,
            "exclusiones_volumen_ambiguo": 0,
            "fallos_por_codigo": {c: 0 for c in CODIGOS_FALLO_CONTROLADOS},
            "trust_score": t.get("trust_score", 90),
        }
        for t in tiendas_db
    }
    # Recorremos iterativamente cada 'st' en stats_list
    for st in stats_list:
        # Recorremos iterativamente cada '(t_nom, vals)' en st.items()
        for t_nom, vals in st.items():
            # Evaluamos la condición lógica (t_nom in consolidado) para controlar el flujo
            if t_nom in consolidado:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                consolidado[t_nom]["consultas"] += vals.get("consultas", 0)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                consolidado[t_nom]["exitos_en_vivo"] += vals.get("exitos_en_vivo", 0)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                consolidado[t_nom]["fallbacks_seguridad"] += vals.get("fallbacks_seguridad", 0)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                consolidado[t_nom]["bloqueos_waf"] += vals.get("bloqueos_waf", 0)
                # Asignamos 'consolidado[t_nom]['omitidos_cir...' con consolidado[t_nom].get('omitidos_circuit_b...
                consolidado[t_nom]["omitidos_circuit_breaker"] = consolidado[t_nom].get("omitidos_circuit_breaker", 0) + vals.get("omitidos_circuit_breaker", 0)
                # Asignamos 'consolidado[t_nom]['exclusiones_...' con consolidado[t_nom].get('exclusiones_volume...
                consolidado[t_nom]["exclusiones_volumen_ambiguo"] = consolidado[t_nom].get("exclusiones_volumen_ambiguo", 0) + vals.get("exclusiones_volumen_ambiguo", 0)
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                fpc = vals.get("fallos_por_codigo") or {}
                # Recorremos iterativamente cada 'c_key' en CODIGOS_FALLO_CONTROLADOS
                for c_key in CODIGOS_FALLO_CONTROLADOS:
                    # Actualizamos acumulativamente el valor de 'consolidado[t_nom]['fallos_por_c...'
                    consolidado[t_nom]["fallos_por_codigo"][c_key] += int(fpc.get(c_key, 0) or 0)
    # Retornamos el resultado procesado (consolidado)
    return consolidado


# =============================================================================
# INGESTA MASIVA EN MEMORIA (SHOPFIY & WOOCOMMERCE)
# =============================================================================
# - ¿Qué hace esta clase (Ingesta Masiva en Memoria RAM)?:
#   En lugar de hacer 3,224 peticiones HTTP individuales a Silk Perfumes, Elite Perfumes, etc.,
#   descarga el catálogo completo paginado (/products.json) en 1 sola ráfaga al iniciar (15-20s) y lo indexa en memoria RAM.
#   Permite resolver precios, variantes y stock en menos de 0.5 milisegundos por fragancia, ahorrando 95% de tráfico de red.
class CatalogoTiendaBulk:
    """
    Catálogo indexado en memoria para tiendas especializadas (Shopify / WooCommerce).
    Descarga todo el catálogo en ráfagas paginadas (1-5s por tienda) y resuelve variantes
    en <0.5ms sin peticiones de red adicionales por cada perfume.
    """
    # Definición de función '__init__' (parámetros: nombre_tienda, tipo, url_base)
    def __init__(self, nombre_tienda: str, tipo: str, url_base: str):
        # Asignamos 'self.nombre_tienda' con nombre_tienda
        self.nombre_tienda = nombre_tienda
        # Asignamos 'self.tipo' con tipo
        self.tipo = tipo
        # Asignamos 'self.url_base' con url_base.rstrip('/')
        self.url_base = url_base.rstrip("/")
        # Asignamos 'self.por_marca' con defaultdict(list)
        self.por_marca: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Asignamos 'self.todos_items' con []
        self.todos_items: List[Dict[str, Any]] = []
        # Asignamos 'self.total_productos' con 0
        self.total_productos: int = 0

    # Definición de función 'agregar_producto_shopify' (parámetros: prod)
    def agregar_producto_shopify(self, prod: Dict[str, Any]):
        # Asignamos 'raw_title' con html.unescape(prod.get('title', '') or '')...
        raw_title = html.unescape(prod.get("title", "") or "").strip()
        # Asignamos 'raw_vendor' con html.unescape(prod.get('vendor', '') or ''...
        raw_vendor = html.unescape(prod.get("vendor", "") or "").strip()
        # Asignamos 'handle' con prod.get('handle', '')
        handle = prod.get("handle", "")
        # Asignamos 'clean_url' con f'{self.url_base}/products/{handle}' if ha...
        clean_url = f"{self.url_base}/products/{handle}" if handle else ""
        # Asignamos 'formato_prod' con detectar_formato_oferta(raw_title, clean_url)
        formato_prod = detectar_formato_oferta(raw_title, clean_url)
        # Asignamos 'images_raw' con prod.get('images', [])
        images_raw = prod.get("images", [])
        # Asignamos 'img_url' con images_raw[0].get('src', '') if images_raw...
        img_url = images_raw[0].get("src", "") if (images_raw and isinstance(images_raw, list) and isinstance(images_raw[0], dict)) else ""

        # Asignamos 'marca' con normalizar_marca_canonica(raw_vendor) if l...
        marca = normalizar_marca_canonica(raw_vendor) if len(raw_vendor) > 1 else ""
        # Evaluamos la condición lógica (not marca or marca in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
        if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
            # Asignamos 'raw_title_lower' con raw_title.lower()
            raw_title_lower = raw_title.lower()
            # Recorremos iterativamente cada '(b_cand, b_canon)' en sorted(CANONICAL_BRAND_MAP.items(), key=la...
            for b_cand, b_canon in sorted(CANONICAL_BRAND_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                # Evaluamos la condición lógica (re.search('\\b' + re.escape(b_cand) + '\\b', raw_tit...) para controlar el flujo
                if re.search(r'\b' + re.escape(b_cand) + r'\b', raw_title_lower):
                    # Asignamos 'marca' con b_canon
                    marca = b_canon
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break

        # Asignamos 'item' con {'title': raw_title, 'vendor': raw_vendor,...
        item = {
            "title": raw_title,
            "vendor": raw_vendor,
            "marca": marca,
            "url": clean_url,
            "formato": formato_prod,
            "imagen_url": img_url,
            "variants": prod.get("variants", []),
            "tipo": "shopify",
        }
        # Ejecutamos instrucción: self.todos_items.append(item)
        self.todos_items.append(item)
        # Evaluamos la condición lógica (marca) para controlar el flujo
        if marca:
            # Ejecutamos instrucción: self.por_marca[marca.lower()].append(item)
            self.por_marca[marca.lower()].append(item)
        # Actualizamos acumulativamente el valor de 'self.total_productos'
        self.total_productos += 1

    # Definición de función 'ingestar_productos' (parámetros: prods)
    def ingestar_productos(self, prods: List[Dict[str, Any]]):
        # Recorremos iterativamente cada 'p' en prods
        for p in prods:
            # Evaluamos la condición lógica (self.tipo == 'shopify') para controlar el flujo
            if self.tipo == "shopify":
                # Ejecutamos instrucción: self.agregar_producto_shopify(p)
                self.agregar_producto_shopify(p)
            else:
                # Ejecutamos instrucción: self.agregar_producto_woocommerce(p)
                self.agregar_producto_woocommerce(p)

    # Definición de función 'agregar_producto_woocommerce' (parámetros: prod)
    def agregar_producto_woocommerce(self, prod: Dict[str, Any]):
        # Asignamos 'raw_title' con html.unescape(prod.get('name', '') or '')....
        raw_title = html.unescape(prod.get("name", "") or "").strip()
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
                # Asignamos 'm_can' con normalizar_marca_canonica(c_name)
                m_can = normalizar_marca_canonica(c_name)
                # Evaluamos la condición lógica (m_can and m_can not in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
                if m_can and m_can not in MARCAS_INVALIDAS_CATALOGO:
                    # Asignamos 'raw_vendor' con m_can
                    raw_vendor = m_can
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break

        # Asignamos 'marca' con normalizar_marca_canonica(raw_vendor) if l...
        marca = normalizar_marca_canonica(raw_vendor) if len(raw_vendor) > 1 else ""
        # Evaluamos la condición lógica (not marca or marca in MARCAS_INVALIDAS_CATALOGO) para controlar el flujo
        if not marca or marca in MARCAS_INVALIDAS_CATALOGO:
            # Asignamos 'raw_title_lower' con raw_title.lower()
            raw_title_lower = raw_title.lower()
            # Recorremos iterativamente cada '(b_cand, b_canon)' en sorted(CANONICAL_BRAND_MAP.items(), key=la...
            for b_cand, b_canon in sorted(CANONICAL_BRAND_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                # Evaluamos la condición lógica (re.search('\\b' + re.escape(b_cand) + '\\b', raw_tit...) para controlar el flujo
                if re.search(r'\b' + re.escape(b_cand) + r'\b', raw_title_lower):
                    # Asignamos 'marca' con b_canon
                    marca = b_canon
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break

        # Asignamos 'clean_url' con prod.get('permalink', '')
        clean_url = prod.get("permalink", "")
        # Asignamos 'formato_prod' con detectar_formato_oferta(raw_title, clean_url)
        formato_prod = detectar_formato_oferta(raw_title, clean_url)
        # Asignamos 'images_raw' con prod.get('images', [])
        images_raw = prod.get("images", [])
        # Asignamos 'img_url' con images_raw[0].get('src', '') if images_raw...
        img_url = images_raw[0].get("src", "") if (images_raw and isinstance(images_raw, list) and isinstance(images_raw[0], dict)) else ""
        # Asignamos 'prices' con prod.get('prices', {})
        prices = prod.get("prices", {})
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        p_act = clean_digits(prices.get("price")) or clean_digits(prod.get("price"))
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        p_norm = clean_digits(prices.get("regular_price")) or clean_digits(prod.get("regular_price")) or p_act
        # Asignamos 'in_stock' con bool(prod.get('is_in_stock', True)) if 'is...
        in_stock = bool(prod.get("is_in_stock", True)) if "is_in_stock" in prod else (prod.get("stock_status") != "outofstock")
        # Asignamos 'vol_ml_opt' con extraer_volumen_ml_opcional(raw_title) or ...
        vol_ml_opt = extraer_volumen_ml_opcional(raw_title) or extraer_volumen_ml_opcional(clean_url)

        # Asignamos 'item' con {'title': raw_title, 'vendor': raw_vendor,...
        item = {
            "title": raw_title,
            "vendor": raw_vendor,
            "marca": marca,
            "url": clean_url,
            "formato": formato_prod,
            "imagen_url": img_url,
            "variants": [{
                "title": f"{vol_ml_opt}ml" if vol_ml_opt else "",
                "price": p_act,
                "compare_at_price": p_norm if p_norm > p_act else None,
                "available": in_stock,
            }],
            "tipo": "woocommerce",
        }
        # Ejecutamos instrucción: self.todos_items.append(item)
        self.todos_items.append(item)
        # Evaluamos la condición lógica (marca) para controlar el flujo
        if marca:
            # Ejecutamos instrucción: self.por_marca[marca.lower()].append(item)
            self.por_marca[marca.lower()].append(item)
        # Actualizamos acumulativamente el valor de 'self.total_productos'
        self.total_productos += 1

    # Definición de función 'extraer_variedades' (parámetros: perfume_nombre, marca, volumen_ml_defecto, concentracion, ...)
    def extraer_variedades(
        self,
        perfume_nombre: str,
        marca: str,
        volumen_ml_defecto: Optional[int] = None,
        concentracion: str = "",
        precio_referencia: Optional[int] = None,
        diagnostico: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        # Asignamos 'marca_canon' con (normalizar_marca_canonica(marca) or marca...
        marca_canon = (normalizar_marca_canonica(marca) or marca or "").strip().lower()
        # Asignamos 'candidatos' con self.por_marca.get(marca_canon, [])
        candidatos = self.por_marca.get(marca_canon, [])
        # Evaluamos la condición lógica (not candidatos and marca) para controlar el flujo
        if not candidatos and marca:
            # Asignamos 'm_low' con marca.lower()
            m_low = marca.lower()
            # Asignamos 'candidatos' con [it for it in self.todos_items if m_low in...
            candidatos = [it for it in self.todos_items if m_low in it["title"].lower()]

        # Evaluamos la condición lógica (not candidatos) para controlar el flujo
        if not candidatos:
            # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
            if diagnostico is not None:
                # Asignamos 'diagnostico['motivo_codigo']' con 'no_encontrado_en_feed'
                diagnostico["motivo_codigo"] = "no_encontrado_en_feed"
                # Asignamos 'diagnostico['detalle']' con f"Sin productos de marca '{marca}' en feed...
                diagnostico["detalle"] = f"Sin productos de marca '{marca}' en feed de {self.nombre_tienda}"
            # Retornamos el resultado procesado ([])
            return []

        # Pre-filtrar por tokens distintivos del nombre del perfume
        p_tokens = [w for w in re.split(r'[\s\-_\.,]+', perfume_nombre.lower()) if len(w) >= 3 and w not in ('perfume', 'eau', 'parfum', 'toilette', 'cologne', 'pour', 'femme', 'homme')]

        # Asignamos 'variedades' con []
        variedades: List[Dict[str, Any]] = []
        # Asignamos 'vols_vistos' con set()
        vols_vistos = set()
        # Asignamos 'vio_candidato_tokens' con False
        vio_candidato_tokens = False
        # Asignamos 'rechazos_entidad' con 0
        rechazos_entidad = 0
        # Asignamos 'rechazos_volumen_entidad_ok' con 0
        rechazos_volumen_entidad_ok = 0

        # Recorremos iterativamente cada 'item' en candidatos
        for item in candidatos:
            # Asignamos 'raw_title' con item['title']
            raw_title = item["title"]
            # Asignamos 'raw_title_lower' con raw_title.lower()
            raw_title_lower = raw_title.lower()
            # Evaluamos la condición lógica (p_tokens and (not any((tok in raw_title_lower for to...) para controlar el flujo
            if p_tokens and not any(tok in raw_title_lower for tok in p_tokens):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Evaluamos la condición lógica (not es_producto_perfume_valido(raw_title, marca=marc...) para controlar el flujo
            if not es_producto_perfume_valido(raw_title, marca=marca or None, volumen_min_ml=25):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Asignamos 'vio_candidato_tokens' con True
            vio_candidato_tokens = True
            # Asignamos 'clean_url' con item['url']
            clean_url = item["url"]
            # Asignamos 'formato_prod' con item['formato']
            formato_prod = item["formato"]

            # Asignamos 'lista_vars_item' con item.get('variants', [])
            lista_vars_item = item.get("variants", [])
            # Asignamos 'n_vars_item' con len(lista_vars_item)
            n_vars_item = len(lista_vars_item)
            # Recorremos iterativamente cada 'v' en lista_vars_item
            for v in lista_vars_item:
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Asignamos 'p_act' con int(float(v.get('price', 0)))
                    p_act = int(float(v.get("price", 0)))
                except (ValueError, TypeError):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Evaluamos la condición lógica (not es_precio_valido(p_act)) para controlar el flujo
                if not es_precio_valido(p_act):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'v_title' con v.get('title', '')
                v_title = v.get("title", "")
                # Asignamos 'es_tst_bulk' con formato_prod == 'tester' or detectar_forma...
                es_tst_bulk = (
                    formato_prod == "tester"
                    or detectar_formato_oferta(f"{raw_title} {v_title}", clean_url) == "tester"
                )
                # Asignamos 'vol_encontrado' con resolver_volumen_oferta(titulo_variante=v_...
                vol_encontrado = resolver_volumen_oferta(
                    titulo_variante=v_title,
                    titulo_producto=raw_title,
                    url_slug=clean_url,
                    volumen_ml_defecto=volumen_ml_defecto,
                    n_variantes_producto=n_vars_item,
                    es_tester=es_tst_bulk,
                )
                # Evaluamos la condición lógica (not vol_encontrado or vol_encontrado < 25) para controlar el flujo
                if not vol_encontrado or vol_encontrado < 25:
                    # Evaluamos la condición lógica (diagnostico is not None) para controlar el flujo
                    if diagnostico is not None:
                        # Asignamos 'diagnostico['exclusiones_volumen...' con diagnostico.get('exclusiones_volumen_ambig...
                        diagnostico["exclusiones_volumen_ambiguo"] = diagnostico.get("exclusiones_volumen_ambiguo", 0) + 1
                    # Asignamos 'res_pre' con coincide_entidad_detallada(titulo=raw_titl...
                    res_pre = coincide_entidad_detallada(
                        titulo=raw_title,
                        perfume_nombre=perfume_nombre,
                        marca=marca,
                        concentracion=concentracion,
                        url=clean_url,
                    )
                    # Evaluamos la condición lógica (res_pre.coincide) para controlar el flujo
                    if res_pre.coincide:
                        # Actualizamos acumulativamente el valor de 'rechazos_volumen_entidad_ok'
                        rechazos_volumen_entidad_ok += 1
                    else:
                        # Actualizamos acumulativamente el valor de 'rechazos_entidad'
                        rechazos_entidad += 1
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'res_match' con coincide_entidad_detallada(titulo=raw_titl...
                res_match = coincide_entidad_detallada(
                    titulo=raw_title,
                    perfume_nombre=perfume_nombre,
                    marca=marca,
                    concentracion=concentracion,
                    url=clean_url,
                    precio_candidato=p_act,
                    precio_referencia=precio_referencia,
                )
                # Evaluamos la condición lógica (not res_match.coincide) para controlar el flujo
                if not res_match.coincide:
                    # Actualizamos acumulativamente el valor de 'rechazos_entidad'
                    rechazos_entidad += 1
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Evaluamos la condición lógica ('chanel' in perfume_nombre.lower() and 'chanel' not ...) para controlar el flujo
                if "chanel" in perfume_nombre.lower() and "chanel" not in raw_title.lower():
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'formato_det' con res_match.formato_detectado or (detectar_f...
                formato_det = res_match.formato_detectado or (detectar_formato_oferta(f"{raw_title} {v_title}", clean_url) if formato_prod == "regular" else formato_prod)
                # Asignamos 'clave_var' con (vol_encontrado, formato_det)
                clave_var = (vol_encontrado, formato_det)
                # Evaluamos la condición lógica (clave_var in vols_vistos) para controlar el flujo
                if clave_var in vols_vistos:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Ejecutamos instrucción: vols_vistos.add(clave_var)
                vols_vistos.add(clave_var)

                # Asignamos 'p_comp_raw' con v.get('compare_at_price')
                p_comp_raw = v.get("compare_at_price")
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Asignamos 'p_comp' con int(float(p_comp_raw)) if p_comp_raw and f...
                    p_comp = int(float(p_comp_raw)) if p_comp_raw and float(p_comp_raw) > p_act else p_act
                except (ValueError, TypeError):
                    # Asignamos 'p_comp' con p_act
                    p_comp = p_act

                # Asignamos 'norm_valido' con p_comp if es_precio_valido(p_comp) and p_c...
                norm_valido = p_comp if (es_precio_valido(p_comp) and p_comp > p_act) else p_act

                # Ejecutamos instrucción: variedades.append({'exito': True, 'precio_actual': p...
                variedades.append({
                    "exito": True,
                    "precio_actual": p_act,
                    "precio_normal": norm_valido,
                    "url": clean_url,
                    "en_stock": bool(v.get("available", True)),
                    "volumen_ml": vol_encontrado,
                    "formato": formato_det,
                    "metodo": f"{self.nombre_tienda} Bulk Cache",
                })

        # Evaluamos la condición lógica (not variedades and diagnostico is not None) para controlar el flujo
        if not variedades and diagnostico is not None:
            # Evaluamos la condición lógica (rechazos_volumen_entidad_ok > 0) para controlar el flujo
            if rechazos_volumen_entidad_ok > 0:
                # Asignamos 'diagnostico['motivo_codigo']' con 'volumen_ambiguo'
                diagnostico["motivo_codigo"] = "volumen_ambiguo"
                # Asignamos 'diagnostico['detalle']' con f'Producto coincide en {self.nombre_tienda...
                diagnostico["detalle"] = f"Producto coincide en {self.nombre_tienda} pero sin volumen inequívoco"
            # Evaluamos la condición lógica (rechazos_entidad > 0) para controlar el flujo
            elif rechazos_entidad > 0:
                # Asignamos 'diagnostico['motivo_codigo']' con 'entidad_no_coincide'
                diagnostico["motivo_codigo"] = "entidad_no_coincide"
                # Asignamos 'diagnostico['detalle']' con f"Candidatos de '{marca}' en {self.nombre_...
                diagnostico["detalle"] = f"Candidatos de '{marca}' en {self.nombre_tienda} descartados por flanker/concentración/género"
            # Evaluamos la condición lógica (not vio_candidato_tokens) para controlar el flujo
            elif not vio_candidato_tokens:
                # Asignamos 'diagnostico['motivo_codigo']' con 'no_encontrado_en_feed'
                diagnostico["motivo_codigo"] = "no_encontrado_en_feed"
                # Asignamos 'diagnostico['detalle']' con f"'{perfume_nombre}' ausente en feed de {s...
                diagnostico["detalle"] = f"'{perfume_nombre}' ausente en feed de {self.nombre_tienda}"
            else:
                # Asignamos 'diagnostico['motivo_codigo']' con 'no_encontrado_en_feed'
                diagnostico["motivo_codigo"] = "no_encontrado_en_feed"
                # Asignamos 'diagnostico['detalle']' con f'Sin variantes válidas en {self.nombre_ti...
                diagnostico["detalle"] = f"Sin variantes válidas en {self.nombre_tienda}"

        # Retornamos el resultado procesado (variedades)
        return variedades


# - ¿Qué hace esta función (Precarga Ráfaga en Memoria)?:
#   Descarga en paralelo los catálogos completos de las 13 tiendas especializadas Shopify/WooCommerce.
#   Puebla las instancias de CatalogoTiendaBulk en RAM en solo 15-20 segundos antes de comenzar a auditar perfumes.
def precargar_catalogos_bulk_tiendas(
    session: requests.Session,
    tiendas_db: List[Dict[str, Any]],
    filtro_tiendas: Optional[List[str]] = None,
    max_workers: int = 4,
) -> Dict[str, CatalogoTiendaBulk]:
    """
    Descarga concurrentemente el catálogo completo de las tiendas especializadas (Shopify y WooCommerce)
    mediante sus endpoints públicos masivos (/products.json y Store API).
    Rendimiento: 13 tiendas (~25.000 productos) precargadas en ~15-20 segundos.
    """
    # Asignamos 't_nombres_db' con {t['nombre'].lower(): t for t in tiendas_db}
    t_nombres_db = {t["nombre"].lower(): t for t in tiendas_db}
    # Asignamos 'tiendas_a_descargar' con []
    tiendas_a_descargar = []
    # Recorremos iterativamente cada 'cfg' en TIENDAS_CRAWLER_CONFIG
    for cfg in TIENDAS_CRAWLER_CONFIG:
        # Asignamos 'nom_cfg' con cfg['nombre']
        nom_cfg = cfg["nombre"]
        # Evaluamos la condición lógica (filtro_tiendas and (not any((f.lower() in nom_cfg.lo...) para controlar el flujo
        if filtro_tiendas and not any(f.lower() in nom_cfg.lower() for f in filtro_tiendas):
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Evaluamos la condición lógica (nom_cfg.lower() in t_nombres_db) para controlar el flujo
        if nom_cfg.lower() in t_nombres_db:
            # Ejecutamos instrucción: tiendas_a_descargar.append(cfg)
            tiendas_a_descargar.append(cfg)

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Iniciando precarga masiva en memoria de {len(tiendas_a_descargar)} tiendas especializadas...")
    # Asignamos 'inicio' con time.time()
    inicio = time.time()
    # Asignamos 'headers_browser' con {'User-Agent': 'Mozilla/5.0 (Windows NT 10...
    headers_browser = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CL,es;q=0.9",
    }

    # Definición de función '_descargar_tienda_individual' (parámetros: cfg)
    def _descargar_tienda_individual(cfg: Dict[str, Any]) -> Tuple[str, CatalogoTiendaBulk]:
        # Asignamos 't_nom' con cfg['nombre']
        t_nom = cfg["nombre"]
        # Asignamos 't_tipo' con cfg.get('tipo', 'shopify')
        t_tipo = cfg.get("tipo", "shopify")
        # Asignamos 'endpoint' con cfg['endpoint']
        endpoint = cfg["endpoint"]
        # Asignamos 'url_base' con cfg['url_base']
        url_base = cfg["url_base"]
        # Asignamos 'cat' con CatalogoTiendaBulk(nombre_tienda=t_nom, ti...
        cat = CatalogoTiendaBulk(nombre_tienda=t_nom, tipo=t_tipo, url_base=url_base)

        # Asignamos 'sess' con curl_requests.Session(impersonate='chrome1...
        sess = curl_requests.Session(impersonate="chrome124") if curl_requests is not None else session
        # Asignamos 'seen_prod_keys' con set()
        seen_prod_keys: Set[Any] = set()

        # Recorremos iterativamente cada 'page' en range(1, 30)
        for page in range(1, 30):
            # Evaluamos la condición lógica (t_tipo == 'woocommerce') para controlar el flujo
            if t_tipo == "woocommerce":
                # Asignamos 'url' con f'{endpoint}?per_page=100&page={page}'
                url = f"{endpoint}?per_page=100&page={page}"
                # Asignamos 'page_size' con 100
                page_size = 100
            else:
                # Asignamos 'url' con f'{endpoint}?limit=250&page={page}'
                url = f"{endpoint}?limit=250&page={page}"
                # Asignamos 'page_size' con 250
                page_size = 250

            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                r = sess.get(url, headers=headers_browser, timeout=12)
                # Evaluamos la condición lógica (r.status_code != 200) para controlar el flujo
                if r.status_code != 200:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Asignamos 'data' con r.json()
                data = r.json()
                # Asignamos 'items' con data if isinstance(data, list) else data.g...
                items = data if isinstance(data, list) else data.get("products", [])
                # Evaluamos la condición lógica (not items) para controlar el flujo
                if not items:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                # Asignamos 'nuevos_en_pagina' con 0
                nuevos_en_pagina = 0
                # Recorremos iterativamente cada 'it' en items
                for it in items:
                    # Asignamos 'pk' con it.get('id') or it.get('handle') or it.get...
                    pk = it.get("id") or it.get("handle") or it.get("permalink")
                    # Evaluamos la condición lógica (pk is not None) para controlar el flujo
                    if pk is not None:
                        # Evaluamos la condición lógica (pk in seen_prod_keys) para controlar el flujo
                        if pk in seen_prod_keys:
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        # Ejecutamos instrucción: seen_prod_keys.add(pk)
                        seen_prod_keys.add(pk)
                    # Actualizamos acumulativamente el valor de 'nuevos_en_pagina'
                    nuevos_en_pagina += 1
                    # Evaluamos la condición lógica (t_tipo == 'woocommerce') para controlar el flujo
                    if t_tipo == "woocommerce":
                        # Ejecutamos instrucción: cat.agregar_producto_woocommerce(it)
                        cat.agregar_producto_woocommerce(it)
                    else:
                        # Ejecutamos instrucción: cat.agregar_producto_shopify(it)
                        cat.agregar_producto_shopify(it)

                # Evaluamos la condición lógica (nuevos_en_pagina == 0 or len(items) < page_size) para controlar el flujo
                if nuevos_en_pagina == 0 or len(items) < page_size:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
            except Exception as ex:
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.debug(f"Aviso descargando página {page} de {t_nom}: {ex}")
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break

        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(f"  ✓ [{t_nom}] {cat.total_productos} productos indexados en memoria.")
        # Retornamos el resultado procesado ((t_nom, cat))
        return (t_nom, cat)

    # Asignamos 'resultados' con {}
    resultados: Dict[str, CatalogoTiendaBulk] = {}
    # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=max_workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Recorremos iterativamente cada '(t_nom, cat)' en executor.map(_descargar_tienda_individual,...
        for t_nom, cat in executor.map(_descargar_tienda_individual, tiendas_a_descargar):
            # Evaluamos la condición lógica (cat.total_productos > 0) para controlar el flujo
            if cat.total_productos > 0:
                # Asignamos 'resultados[t_nom]' con cat
                resultados[t_nom] = cat

    # Asignamos 'duracion' con round(time.time() - inicio, 2)
    duracion = round(time.time() - inicio, 2)
    # Asignamos 'total_prods' con sum((c.total_productos for c in resultados...
    total_prods = sum(c.total_productos for c in resultados.values())
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Precarga masiva completada: {len(resultados)} tiendas y {total_prods:,} productos listos en {duracion}s.")
    # Retornamos el resultado procesado (resultados)
    return resultados


# Definición de función 'auditar_lote_perfumes' (parámetros: perfumes_lote, tiendas_db, urls_conocidas_map, session, ...)
def auditar_lote_perfumes(
    perfumes_lote: List[Dict[str, Any]],
    tiendas_db: List[Dict[str, Any]],
    urls_conocidas_map: Dict[Tuple[int, int], Tuple[str, int]],
    session: requests.Session,
    rotacion_idx: int = 1,
    total_rotaciones: int = 1,
    total_catalogo: int = 0,
    cache_tiendas_bulk: Optional[Dict[str, CatalogoTiendaBulk]] = None,
    ofertas_activas_set: Optional[Set[Tuple[int, int]]] = None,
    cb_cache: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta la auditoría en vivo para un subconjunto (lote/rotación) específico de perfumes.
    Cada lote crea y cierra su propio `scraping_run_id` para trazabilidad atómica y persistencia
    resiliente ante desconexiones, cancelaciones o timeouts en runners de CI/CD.
    """
    # Asignamos 'inicio' con time.time()
    inicio = time.time()
    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Asignamos 'msg_inicio' con f'Rotación {rotacion_idx}/{total_rotacione...
    msg_inicio = (
        f"Rotación {rotacion_idx}/{total_rotaciones}: auditando lote de {len(perfumes_lote)} perfumes "
        f"(catálogo total: {total_catalogo})"
    )
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Iniciando {msg_inicio}")
    # Asignamos 'run_id' con iniciar_scraping_run(tipo_scraper='Scraper...
    run_id = iniciar_scraping_run(
        tipo_scraper="Scraper Periódico Precios y Stock",
        mensaje_detalle=msg_inicio,
    )

    # Asignamos 'actualizaciones' con 0
    actualizaciones = 0
    # Asignamos 'ofertas_nuevas' con 0
    ofertas_nuevas = 0
    # Asignamos 'cambios_precio' con 0
    cambios_precio = 0
    # Asignamos 'cambios_stock' con 0
    cambios_stock = 0
    # Asignamos 'cambios_url' con 0
    cambios_url = 0
    # Asignamos 'omitidos' con 0
    omitidos = 0
    # Asignamos 'omitidos_cb' con 0
    omitidos_cb = 0
    # Asignamos 'bloqueos_waf' con 0
    bloqueos_waf = 0
    # Asignamos 'errores' con []
    errores: List[str] = []
    # Asignamos 'detalle_precios' con []
    detalle_precios: List[Dict[str, Any]] = []
    # Asignamos 'muestra_exclusiones_marca' con []
    muestra_exclusiones_marca: List[Dict[str, Any]] = []
    # Asignamos 'outliers_lote' con []
    outliers_lote: List[Dict[str, Any]] = []
    # Asignamos 'tiendas_stats' con {t['nombre']: {'consultas': 0, 'exitos_en_...
    tiendas_stats: Dict[str, Dict[str, Any]] = {
        t["nombre"]: {
            "consultas": 0,
            "exitos_en_vivo": 0,
            "fallbacks_seguridad": 0,
            "bloqueos_waf": 0,
            "omitidos_circuit_breaker": 0,
            "exclusiones_volumen_ambiguo": 0,
            "fallos_por_codigo": {c: 0 for c in CODIGOS_FALLO_CONTROLADOS},
            "trust_score": t.get("trust_score", 90),
        }
        for t in tiendas_db
    }

    # Recorremos iterativamente cada 'p' en perfumes_lote
    for p in perfumes_lote:
        # Asignamos 'p_id' con p['id']
        p_id = p["id"]
        # Asignamos 'p_nom' con p['nombre']
        p_nom = p["nombre"]
        # Asignamos 'p_marca' con p['marca']
        p_marca = p["marca"]
        # Asignamos 'p_genero' con p.get('genero') or 'Unisex'
        p_genero = p.get("genero") or "Unisex"
        # Asignamos 'p_tipo' con p.get('tipo') or ''
        p_tipo = p.get("tipo") or ""
        # Asignamos 'p_ref' con p.get('precio_referencia')
        p_ref = p.get("precio_referencia")

        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(f"[Rotación {rotacion_idx}/{total_rotaciones}] Auditando: {p_nom} ({p_marca}) [{p_tipo or 'N/A'} • {p_genero}]")
        # Ejecutamos instrucción: _GENERO_ESPERADO_CTX.set(p_genero)
        _GENERO_ESPERADO_CTX.set(p_genero)
        # Asignamos 'capturas_perfume_por_vol' con defaultdict(list)
        capturas_perfume_por_vol: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

        # Definición de función '_procesar_resultado_tienda' (parámetros: tienda_item, u_directa, v_base, lista_vars, ...)
        def _procesar_resultado_tienda(tienda_item, u_directa, v_base, lista_vars, diag_dict, err_item):
            # Ejecutamos instrucción: nonlocal actualizaciones, ofertas_nuevas, cambios_pr...
            nonlocal actualizaciones, ofertas_nuevas, cambios_precio, cambios_stock, cambios_url, bloqueos_waf
            # Asignamos 't_id' con tienda_item['id']
            t_id = tienda_item["id"]
            # Asignamos 't_nom' con tienda_item['nombre']
            t_nom = tienda_item["nombre"]

            # Evaluamos la condición lógica (diag_dict and diag_dict.get('exclusiones_volumen_amb...) para controlar el flujo
            if diag_dict and diag_dict.get("exclusiones_volumen_ambiguo"):
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['exclusione...'
                tiendas_stats[t_nom]["exclusiones_volumen_ambiguo"] += int(diag_dict["exclusiones_volumen_ambiguo"])

            # Evaluamos la condición lógica (err_item is not None) para controlar el flujo
            if err_item is not None:
                # Asignamos 'err_msg' con f'Error en ciclo para {p_nom} en {t_nom}: ...
                err_msg = f"Error en ciclo para {p_nom} en {t_nom}: {err_item}"
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.error(err_msg)
                # Ejecutamos instrucción: errores.append(err_msg)
                errores.append(err_msg)
                # Asignamos 'err_low' con str(err_item).lower()
                err_low = str(err_item).lower()
                # Asignamos 'cod_err' con 'timeout' if isinstance(err_item, TimeoutE...
                cod_err = "timeout" if (isinstance(err_item, TimeoutError) or "timeout" in err_low or "timed out" in err_low) else "parse_error"
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['fallos_por...'
                tiendas_stats[t_nom]["fallos_por_codigo"][cod_err] += 1
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Ejecutamos instrucción: registrar_fallo_scraping(tienda_id=t_id, perfume_id=...
                    registrar_fallo_scraping(
                        tienda_id=t_id,
                        perfume_id=p_id,
                        mensaje=str(err_item),
                        motivo_codigo=cod_err,
                    )
                except Exception:
                    # Ejecutamos instrucción: pass
                    pass
                # Finalizamos la ejecución de la función retornando None
                return

            # Evaluamos la condición lógica (lista_vars) para controlar el flujo
            if lista_vars:
                # Recorremos iterativamente cada 'var_data' en lista_vars
                for var_data in lista_vars:
                    # Evaluamos la condición lógica (not var_data.get('exito')) para controlar el flujo
                    if not var_data.get("exito"):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'precio_actual_final' con int(var_data['precio_actual'])
                    precio_actual_final = int(var_data["precio_actual"])
                    # Evaluamos la condición lógica (not es_precio_valido(precio_actual_final)) para controlar el flujo
                    if not es_precio_valido(precio_actual_final):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'precio_normal_final' con int(var_data.get('precio_normal') or preci...
                    precio_normal_final = int(var_data.get("precio_normal") or precio_actual_final)
                    # Asignamos 'url_final' con var_data['url']
                    url_final = var_data["url"]
                    # Asignamos 'vol_raw_final' con var_data.get('volumen_ml')
                    vol_raw_final = var_data.get("volumen_ml")
                    # Evaluamos la condición lógica (not vol_raw_final) para controlar el flujo
                    if not vol_raw_final:
                        # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['exclusione...'
                        tiendas_stats[t_nom]["exclusiones_volumen_ambiguo"] += 1
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'vol_final' con int(vol_raw_final)
                    vol_final = int(vol_raw_final)
                    # Evaluamos la condición lógica (vol_final < 25) para controlar el flujo
                    if vol_final < 25:
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'stock_final' con bool(var_data.get('en_stock', True))
                    stock_final = bool(var_data.get("en_stock", True))
                    # Asignamos 'formato_final' con str(var_data.get('formato') or detectar_fo...
                    formato_final = str(var_data.get("formato") or detectar_formato_oferta(p_nom, url_final))

                    # Asignamos 'res_obs' con registrar_observacion_oferta({'perfume_id'...
                    res_obs = registrar_observacion_oferta({
                        "perfume_id": p_id,
                        "tienda_id": t_id,
                        "precio_actual": precio_actual_final,
                        "precio_normal": precio_normal_final,
                        "en_stock": stock_final,
                        "url_producto": url_final,
                        "volumen_ml": vol_final,
                        "formato": formato_final,
                        "scraping_run_id": run_id,
                    })
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    res_tipo = res_obs.get("resultado")
                    # Evaluamos la condición lógica (res_tipo in ('creada', 'actualizada')) para controlar el flujo
                    if res_tipo in ("creada", "actualizada"):
                        # Actualizamos acumulativamente el valor de 'actualizaciones'
                        actualizaciones += 1
                        # Evaluamos la condición lógica (res_tipo == 'creada') para controlar el flujo
                        if res_tipo == "creada":
                            # Actualizamos acumulativamente el valor de 'ofertas_nuevas'
                            ofertas_nuevas += 1
                        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                        c_mods = res_obs.get("campos_modificados") or []
                        # Evaluamos la condición lógica ('precio_actual' in c_mods) para controlar el flujo
                        if "precio_actual" in c_mods:
                            # Actualizamos acumulativamente el valor de 'cambios_precio'
                            cambios_precio += 1
                        # Evaluamos la condición lógica ('en_stock' in c_mods) para controlar el flujo
                        if "en_stock" in c_mods:
                            # Actualizamos acumulativamente el valor de 'cambios_stock'
                            cambios_stock += 1
                        # Evaluamos la condición lógica ('url_producto' in c_mods) para controlar el flujo
                        if "url_producto" in c_mods:
                            # Actualizamos acumulativamente el valor de 'cambios_url'
                            cambios_url += 1

                    # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['exitos_en_...'
                    tiendas_stats[t_nom]["exitos_en_vivo"] += 1
                    # Ejecutamos instrucción: registrar_resultado_circuit_breaker(p_id, t_id, exit...
                    registrar_resultado_circuit_breaker(p_id, t_id, exito=True, cb_data=cb_cache)
                    # Evaluamos la condición lógica (stock_final) para controlar el flujo
                    if stock_final:
                        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                        capturas_perfume_por_vol[vol_final].append({
                            "id": res_obs.get("oferta_id") if isinstance(res_obs, dict) else None,
                            "perfume_id": p_id,
                            "perfume": f"{p_marca} - {p_nom} ({vol_final}ml)",
                            "tienda_id": t_id,
                            "tienda": t_nom,
                            "precio_actual": precio_actual_final,
                            "volumen_ml": vol_final,
                            "formato": formato_final,
                            "en_stock": True,
                            "estado": "activa",
                            "url_producto": url_final,
                        })
                    # Ejecutamos instrucción: detalle_precios.append({'perfume': p_nom, 'tienda': ...
                    detalle_precios.append({
                        "perfume": p_nom,
                        "tienda": t_nom,
                        "precio_actual": precio_actual_final,
                        "precio_normal": precio_normal_final,
                        "tiene_descuento": bool(precio_normal_final > precio_actual_final),
                        "origen": var_data.get("metodo", "Extracción en Vivo"),
                        "volumen_ml": vol_final,
                        "formato": formato_final,
                        "en_stock": stock_final,
                    })
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.info(
                        f"  -> [{t_nom}] EN VIVO: ${precio_actual_final:,} "
                        f"(Normal: ${precio_normal_final:,}) | {vol_final}ml ({formato_final}) | stock: {stock_final}"
                    )
            # Evaluamos la condición lógica (diag_dict.get('waf_bloqueado')) para controlar el flujo
            elif diag_dict.get("waf_bloqueado"):
                # Actualizamos acumulativamente el valor de 'bloqueos_waf'
                bloqueos_waf += 1
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['bloqueos_w...'
                tiendas_stats[t_nom]["bloqueos_waf"] += 1
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['fallos_por...'
                tiendas_stats[t_nom]["fallos_por_codigo"]["waf"] += 1
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.info(
                    f"  -> [{t_nom}] Bloqueo temporal WAF (HTTP {diag_dict.get('http_status', 403)}). "
                    "Se preserva última oferta sin penalizar fallos consecutivos."
                )
            else:
                # Asignamos 'codigo_fallo' con str(diag_dict.get('motivo_codigo') or '')....
                codigo_fallo = str(diag_dict.get("motivo_codigo") or "").strip().lower()
                # Evaluamos la condición lógica (not codigo_fallo) para controlar el flujo
                if not codigo_fallo:
                    # Evaluamos la condición lógica (diag_dict.get('exclusiones_volumen_ambiguo', 0) > 0) para controlar el flujo
                    if diag_dict.get("exclusiones_volumen_ambiguo", 0) > 0:
                        # Asignamos 'codigo_fallo' con 'volumen_ambiguo'
                        codigo_fallo = "volumen_ambiguo"
                    else:
                        # Asignamos 'codigo_fallo' con 'no_encontrado_en_feed'
                        codigo_fallo = "no_encontrado_en_feed"
                # Evaluamos la condición lógica (codigo_fallo not in CODIGOS_FALLO_CONTROLADOS) para controlar el flujo
                if codigo_fallo not in CODIGOS_FALLO_CONTROLADOS:
                    # Asignamos 'codigo_fallo' con 'no_encontrado_en_feed'
                    codigo_fallo = "no_encontrado_en_feed"
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['fallos_por...'
                tiendas_stats[t_nom]["fallos_por_codigo"][codigo_fallo] += 1
                # Asignamos 'motivo_fallo' con str(diag_dict.get('detalle') or f'Sin disp...
                motivo_fallo = str(diag_dict.get("detalle") or f"Sin disponibilidad confirmada en {t_nom}")
                # Asignamos 'tiene_oferta_previa' con False
                tiene_oferta_previa = False
                # Evaluamos la condición lógica (ofertas_activas_set is not None) para controlar el flujo
                if ofertas_activas_set is not None:
                    # Asignamos 'tiene_oferta_previa' con (int(p_id), int(t_id)) in ofertas_activas_set
                    tiene_oferta_previa = (int(p_id), int(t_id)) in ofertas_activas_set
                else:
                    # Asignamos 'tiene_oferta_previa' con (int(p_id), int(t_id)) in urls_conocidas_m...
                    tiene_oferta_previa = (
                        (int(p_id), int(t_id)) in urls_conocidas_map
                        or bool(u_directa)
                    )

                # Evaluamos la condición lógica (tiene_oferta_previa and codigo_fallo in ('no_encontr...) para controlar el flujo
                if tiene_oferta_previa and codigo_fallo in (
                    "no_encontrado_en_feed",
                    "entidad_no_coincide",
                    "volumen_ambiguo",
                    "waf",
                    "timeout",
                    "parse_error",
                ):
                    # Asignamos 'codigo_registro' con 'no_encontrado_en_feed' if codigo_fallo in...
                    codigo_registro = (
                        "no_encontrado_en_feed"
                        if codigo_fallo in ("entidad_no_coincide", "volumen_ambiguo")
                        else codigo_fallo
                    )
                    # Ejecutamos instrucción: registrar_fallo_scraping(tienda_id=t_id, perfume_id=...
                    registrar_fallo_scraping(
                        tienda_id=t_id,
                        perfume_id=p_id,
                        mensaje=motivo_fallo,
                        motivo_codigo=codigo_registro,
                    )
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['fallbacks_...'
                tiendas_stats[t_nom]["fallbacks_seguridad"] += 1
                # Evaluamos la condición lógica (not u_directa) para controlar el flujo
                if not u_directa:
                    # Ejecutamos instrucción: registrar_resultado_circuit_breaker(p_id, t_id, exit...
                    registrar_resultado_circuit_breaker(p_id, t_id, exito=False, cb_data=cb_cache)
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.debug(f"  -> [{t_nom}] FALLO SCRAPING: {motivo_fallo}. No se altera precio ni stock.")

        # 1. Separar tiendas bulk (en RAM instantáneo) de tiendas de red (Network)
        tiendas_bulk_items = []
        # Asignamos 'tiendas_network_items' con []
        tiendas_network_items = []

        # Recorremos iterativamente cada 'tienda' en tiendas_db
        for tienda in tiendas_db:
            # Asignamos 't_nom' con tienda['nombre']
            t_nom = tienda["nombre"]

            # Evaluamos la condición lógica (not tienda_comercializa_marca(t_nom, p_marca, es_ara...) para controlar el flujo
            if not tienda_comercializa_marca(t_nom, p_marca, es_arabe_flag=p.get("es_arabe")):
                # Actualizamos acumulativamente el valor de 'omitidos'
                omitidos += 1
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['fallos_por...'
                tiendas_stats[t_nom]["fallos_por_codigo"]["marca_excluida"] += 1
                # Evaluamos la condición lógica (len(muestra_exclusiones_marca) < 50) para controlar el flujo
                if len(muestra_exclusiones_marca) < 50:
                    # Ejecutamos instrucción: muestra_exclusiones_marca.append({'perfume_id': p_id...
                    muestra_exclusiones_marca.append({
                        "perfume_id": p_id,
                        "perfume": p_nom,
                        "marca": p_marca,
                        "es_arabe": bool(p.get("es_arabe")),
                        "tienda": t_nom,
                        "motivo": "marca_excluida_por_perfil_tienda",
                    })
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Asignamos 'tiene_extractor' con cache_tiendas_bulk and t_nom in cache_tien...
            tiene_extractor = (
                (cache_tiendas_bulk and t_nom in cache_tiendas_bulk)
                or (t_nom in TIENDAS_SHOPIFY)
                or (t_nom in TIENDAS_WOOCOMMERCE)
                or any(r in t_nom.lower() for r in ["falabella", "paris", "ripley"])
            )
            # Evaluamos la condición lógica (not tiene_extractor) para controlar el flujo
            if not tiene_extractor:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Asignamos 'url_directa_info' con obtener_url_directa_tienda(p_id, t_nom)
            url_directa_info = obtener_url_directa_tienda(p_id, t_nom)
            # Evaluamos la condición lógica (url_directa_info) para controlar el flujo
            if url_directa_info:
                # Asignamos 'url_directa_guardada' con url_directa_info[0]
                url_directa_guardada = url_directa_info[0]
                # Asignamos 'vol_ml_base' con url_directa_info[3] or 100
                vol_ml_base = url_directa_info[3] or 100
            # Evaluamos la condición lógica ((int(p_id), int(tienda['id'])) in urls_conocidas_map) para controlar el flujo
            elif (int(p_id), int(tienda["id"])) in urls_conocidas_map:
                # Asignamos '(url_directa_guardada, vol_ml_base)' con urls_conocidas_map[int(p_id), int(tienda['...
                url_directa_guardada, vol_ml_base = urls_conocidas_map[(int(p_id), int(tienda["id"]))]
            else:
                # Asignamos 'url_directa_guardada' con None
                url_directa_guardada = None
                # Asignamos 'vol_ml_base' con 100
                vol_ml_base = 100

            # Asignamos 'item' con (tienda, url_directa_guardada, vol_ml_base)
            item = (tienda, url_directa_guardada, vol_ml_base)
            # Evaluamos la condición lógica (cache_tiendas_bulk and t_nom in cache_tiendas_bulk) para controlar el flujo
            if cache_tiendas_bulk and t_nom in cache_tiendas_bulk:
                # Ejecutamos instrucción: tiendas_bulk_items.append(item)
                tiendas_bulk_items.append(item)
            else:
                # Circuito abierto / cooldown para búsquedas dinámicas sin URL que fallaron repetidamente
                if not url_directa_guardada and es_circuit_breaker_activo(p_id, int(tienda["id"]), cb_cache):
                    # Actualizamos acumulativamente el valor de 'omitidos_cb'
                    omitidos_cb += 1
                    # Asignamos 'tiendas_stats[t_nom]['omitidos_c...' con tiendas_stats[t_nom].get('omitidos_circuit...
                    tiendas_stats[t_nom]["omitidos_circuit_breaker"] = (
                        tiendas_stats[t_nom].get("omitidos_circuit_breaker", 0) + 1
                    )
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Cortocircuito WAF por lote: si un retailer bloquea 100% por IP/ASN (>=15 WAF y 0 éxitos),
                # evitamos golpear inútilmente el CDN el resto del lote registrando el bloqueo limpio.
                if (
                    tiendas_stats[t_nom]["exitos_en_vivo"] == 0
                    and tiendas_stats[t_nom]["bloqueos_waf"] >= WAF_FAST_FAIL_THRESHOLD
                ):
                    # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['consultas']'
                    tiendas_stats[t_nom]["consultas"] += 1
                    # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['bloqueos_w...'
                    tiendas_stats[t_nom]["bloqueos_waf"] += 1
                    # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['fallos_por...'
                    tiendas_stats[t_nom]["fallos_por_codigo"]["waf"] += 1
                    # Actualizamos acumulativamente el valor de 'bloqueos_waf'
                    bloqueos_waf += 1
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Ejecutamos instrucción: tiendas_network_items.append(item)
                tiendas_network_items.append(item)

        # 2. Procesamiento instantáneo en memoria para tiendas especializadas (RAM < 0.5ms)
        for tienda, url_directa_guardada, vol_ml_base in tiendas_bulk_items:
            # Asignamos 't_nom' con tienda['nombre']
            t_nom = tienda["nombre"]
            # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['consultas']'
            tiendas_stats[t_nom]["consultas"] += 1
            # Asignamos 'diag' con {}
            diag = {}
            # Asignamos 'lista_variedades' con cache_tiendas_bulk[t_nom].extraer_variedad...
            lista_variedades = cache_tiendas_bulk[t_nom].extraer_variedades(
                perfume_nombre=p_nom,
                marca=p_marca,
                volumen_ml_defecto=vol_ml_base,
                concentracion=p_tipo,
                precio_referencia=p_ref,
                diagnostico=diag,
            )
            # Ejecutamos instrucción: _procesar_resultado_tienda(tienda, url_directa_guard...
            _procesar_resultado_tienda(tienda, url_directa_guardada, vol_ml_base, lista_variedades, diag, None)

        # - ¿Qué hace este bloque de concurrencia (ThreadPoolExecutor)?:
        #   Como las tiendas departamentales (Falabella, Paris, Ripley) tienen tiempos de respuesta de ~1s por red,
        #   las consulta en paralelo mediante hilos asíncronos concurrentes (max_workers=3).
        #   Esto baja el tiempo de procesamiento por perfume de 3.4 segundos a solo 1.1 segundos.
        # 3. Procesamiento concurrente en paralelo para tiendas de red (Falabella, Paris, Ripley)
        if tiendas_network_items:
            # Definición de función '_ejecutar_extraccion_network' (parámetros: net_item)
            def _ejecutar_extraccion_network(net_item):
                # Asignamos '(t_obj, u_directa, v_base)' con net_item
                t_obj, u_directa, v_base = net_item
                # Asignamos 't_name' con t_obj['nombre']
                t_name = t_obj["nombre"]
                # Asignamos 'd_diag' con {}
                d_diag: Dict[str, Any] = {}
                # Asignamos 'err_ex' con None
                err_ex = None
                # Asignamos 'vars_res' con []
                vars_res: List[Dict[str, Any]] = []
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Evaluamos la condición lógica ('falabella' in t_name.lower()) para controlar el flujo
                    if "falabella" in t_name.lower():
                        # Ejecutamos instrucción: time.sleep(random.uniform(0.12, 0.28))
                        time.sleep(random.uniform(0.12, 0.28))
                        # Asignamos 'vars_res' con extraer_variedades_falabella(session=sessi...
                        vars_res = extraer_variedades_falabella(
                            session=session,
                            url_directa=u_directa,
                            perfume_nombre=p_nom,
                            marca=p_marca,
                            volumen_ml_defecto=v_base,
                            concentracion=p_tipo,
                            precio_referencia=p_ref,
                            diagnostico=d_diag,
                        )
                    # Evaluamos la condición lógica ('paris' in t_name.lower()) para controlar el flujo
                    elif "paris" in t_name.lower():
                        # Ejecutamos instrucción: time.sleep(random.uniform(0.12, 0.28))
                        time.sleep(random.uniform(0.12, 0.28))
                        # Asignamos 'vars_res' con extraer_variedades_paris(session=session, ...
                        vars_res = extraer_variedades_paris(
                            session=session,
                            url_directa=u_directa,
                            perfume_nombre=p_nom,
                            marca=p_marca,
                            volumen_ml_defecto=v_base,
                            concentracion=p_tipo,
                            precio_referencia=p_ref,
                            diagnostico=d_diag,
                        )
                    # Evaluamos la condición lógica ('ripley' in t_name.lower()) para controlar el flujo
                    elif "ripley" in t_name.lower():
                        # Ejecutamos instrucción: time.sleep(random.uniform(0.12, 0.28))
                        time.sleep(random.uniform(0.12, 0.28))
                        # Asignamos 'vars_res' con extraer_variedades_ripley(session=session,...
                        vars_res = extraer_variedades_ripley(
                            session=session,
                            url_directa=u_directa,
                            perfume_nombre=p_nom,
                            marca=p_marca,
                            volumen_ml_defecto=v_base,
                            concentracion=p_tipo,
                            precio_referencia=p_ref,
                            diagnostico=d_diag,
                        )
                    # Evaluamos la condición lógica (t_name in TIENDAS_SHOPIFY) para controlar el flujo
                    elif t_name in TIENDAS_SHOPIFY:
                        # Ejecutamos instrucción: time.sleep(random.uniform(0.12, 0.28))
                        time.sleep(random.uniform(0.12, 0.28))
                        # Asignamos 'dom' con TIENDAS_SHOPIFY[t_name]
                        dom = TIENDAS_SHOPIFY[t_name]
                        # Asignamos 'vars_res' con extraer_variedades_shopify(session=session...
                        vars_res = extraer_variedades_shopify(
                            session=session,
                            dominio=dom,
                            perfume_nombre=p_nom,
                            marca=p_marca,
                            volumen_ml_defecto=v_base,
                            concentracion=p_tipo,
                            precio_referencia=p_ref,
                            diagnostico=d_diag,
                        )
                    # Evaluamos la condición lógica (t_name in TIENDAS_WOOCOMMERCE) para controlar el flujo
                    elif t_name in TIENDAS_WOOCOMMERCE:
                        # Ejecutamos instrucción: time.sleep(random.uniform(0.12, 0.28))
                        time.sleep(random.uniform(0.12, 0.28))
                        # Asignamos 'dom' con TIENDAS_WOOCOMMERCE[t_name]
                        dom = TIENDAS_WOOCOMMERCE[t_name]
                        # Asignamos 'vars_res' con extraer_variedades_woocommerce(session=ses...
                        vars_res = extraer_variedades_woocommerce(
                            session=session,
                            dominio=dom,
                            perfume_nombre=p_nom,
                            marca=p_marca,
                            volumen_ml_defecto=v_base,
                            concentracion=p_tipo,
                            precio_referencia=p_ref,
                            diagnostico=d_diag,
                        )
                except Exception as ex:
                    # Asignamos 'err_ex' con ex
                    err_ex = ex
                # Retornamos el resultado procesado ((t_obj, u_directa, v_base, vars_res, d_diag, er...)
                return (t_obj, u_directa, v_base, vars_res, d_diag, err_ex)

            # Asignamos 'max_w' con min(3, len(tiendas_network_items))
            max_w = min(3, len(tiendas_network_items))
            # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=max_w)
            with ThreadPoolExecutor(max_workers=max_w) as executor:
                # Asignamos 'net_results' con list(executor.map(_ejecutar_extraccion_net...
                net_results = list(executor.map(_ejecutar_extraccion_network, tiendas_network_items))

            # Recorremos iterativamente cada '(t_obj, u_directa, v_base, ...' en net_results
            for t_obj, u_directa, v_base, vars_res, d_diag, err_ex in net_results:
                # Asignamos 't_nom' con t_obj['nombre']
                t_nom = t_obj["nombre"]
                # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['consultas']'
                tiendas_stats[t_nom]["consultas"] += 1
                # Ejecutamos instrucción: _procesar_resultado_tienda(t_obj, u_directa, v_base,...
                _procesar_resultado_tienda(t_obj, u_directa, v_base, vars_res, d_diag, err_ex)

        # 4. Control estadístico de precios atípicos sobre las ofertas en stock capturadas de esta fragancia
        for _vol_chk, grupo_vol in capturas_perfume_por_vol.items():
            # Asignamos 'detectados_v' con detectar_precios_atipicos(grupo_vol)
            detectados_v = detectar_precios_atipicos(grupo_vol)
            # Recorremos iterativamente cada 'out_item' en detectados_v
            for out_item in detectados_v:
                # Ejecutamos instrucción: outliers_lote.append(out_item)
                outliers_lote.append(out_item)
                # Asignamos 'oid_rev' con out_item.get('id')
                oid_rev = out_item.get("id")
                # Evaluamos la condición lógica (oid_rev) para controlar el flujo
                if oid_rev:
                    # Ejecutamos instrucción: marcar_oferta_requiere_revision(int(oid_rev), f"[OUT...
                    marcar_oferta_requiere_revision(
                        int(oid_rev),
                        f"[OUTLIER_PRECIO] {out_item.get('motivo_outlier', '')}",
                    )
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.warning(
                    f"  [OUTLIER_PRECIO] {out_item.get('perfume')} en {out_item.get('tienda')}: "
                    f"${out_item.get('precio_actual', 0):,} -> {out_item.get('motivo_outlier')}"
                )

    # Asignamos 'duracion' con round(time.time() - inicio, 2)
    duracion = round(time.time() - inicio, 2)
    # Asignamos 'estado_general' con 'EXITOSO' if not errores else 'DEGRADADO' ...
    estado_general = "EXITOSO" if not errores else ("DEGRADADO" if actualizaciones > 0 else "FALLIDO")

    # Ejecutamos instrucción: finalizar_scraping_run(run_id=run_id, estado='comple...
    finalizar_scraping_run(
        run_id=run_id,
        estado="completado" if estado_general == "EXITOSO" else estado_general.lower(),
        productos_procesados=len(perfumes_lote),
        ofertas_nuevas=ofertas_nuevas,
        cambios_precio=cambios_precio,
        cambios_stock=cambios_stock,
        cambios_url=cambios_url,
        errores=len(errores),
        mensaje_detalle=(
            f"Rotación {rotacion_idx}/{total_rotaciones}: auditados {len(perfumes_lote)} perfumes en {duracion}s: "
            f"{actualizaciones} actualizaciones, {bloqueos_waf} bloqueos WAF."
        ),
    )

    # Retornamos el resultado procesado ({'actualizaciones': actualizaciones, 'fecha': a...)
    return {
        "actualizaciones": actualizaciones,
        "fecha": ahora,
        "duracion_segundos": duracion,
        "metadata": {
            "version_etl": "3.3.0",
            "sistema": "PerfumeTrending Professional Anti-Bot ETL (Batch)",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado_general,
            "scraping_run_id": run_id,
            "rotacion_idx": rotacion_idx,
            "total_rotaciones": total_rotaciones,
        },
        "metricas": {
            "total_perfumes_catalogo": total_catalogo,
            "perfumes_auditados": len(perfumes_lote),
            "total_tiendas_registradas": len(tiendas_db),
            "precios_actualizados": actualizaciones,
            "ofertas_nuevas": ofertas_nuevas,
            "cambios_precio": cambios_precio,
            "cambios_stock": cambios_stock,
            "cambios_url": cambios_url,
            "bloqueos_waf": bloqueos_waf,
            "exclusiones_marca": omitidos,
            "omitidos_circuit_breaker": omitidos_cb,
            "outliers_marcados": len(outliers_lote),
            "errores_totales": len(errores),
        },
        "estadisticas_tiendas": tiendas_stats,
        "muestra_capturas": detalle_precios[:15],
        "muestra_exclusiones_marca": muestra_exclusiones_marca[:50],
        "outliers_detectados": outliers_lote[:50],
        "errores": errores,
    }


# Definición de función 'ejecutar_ciclo_scraping_y_descubrimiento' (parámetros: batch_size, rotations, delay_between_rotations, shard, ...)
def ejecutar_ciclo_scraping_y_descubrimiento(
    batch_size: Optional[int] = None,
    rotations: Optional[int] = None,
    delay_between_rotations: Optional[int] = None,
    shard: Optional[int] = None,
    total_shards: Optional[int] = None,
    descubrir: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Orquesta el ciclo de extracción ETL en rotaciones sucesivas priorizadas mediante cola LRU:
    1. Recupera catálogo completo y el mapa de última verificación exitosa (`ultima_verificacion_exitosa`).
    2. Ordena los perfumes con política LRU (los nunca auditados o con auditoría más antigua primero).
    3. Segmenta el catálogo en lotes de tamaño `batch_size` (por defecto 500 o variable de entorno `SCRAPER_BATCH_SIZE`).
    4. Ejecuta consecutivamente las rotaciones solicitadas (o todas las necesarias si `rotations` es 0 o None).
       Entre cada rotación, realiza una pausa configurable de cooldown (`delay_between_rotations` segundos).
    5. Cada lote registra su propia transacción en `scraping_runs` y actualiza inmediatamente la BD,
       asegurando tolerancia absoluta a timeouts y cero pérdida de trabajo.
    """
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'inicio_global' con time.time()
    inicio_global = time.time()
    # Asignamos 'ahora_global' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora_global = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Resolución de parámetros (CLI / argumento / entorno / defecto)
    try:
        # Asignamos 'bs_cfg' con batch_size if batch_size is not None else ...
        bs_cfg = batch_size if batch_size is not None else int(os.environ.get("SCRAPER_BATCH_SIZE", 500))
    except (ValueError, TypeError):
        # Asignamos 'bs_cfg' con 500
        bs_cfg = 500
    # Asignamos 'effective_batch_size' con max(1, bs_cfg)
    effective_batch_size = max(1, bs_cfg)

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'rot_cfg' con rotations if rotations is not None else in...
        rot_cfg = rotations if rotations is not None else int(os.environ.get("SCRAPER_ROTATIONS", 0))
    except (ValueError, TypeError):
        # Asignamos 'rot_cfg' con 0
        rot_cfg = 0

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'delay_cfg' con delay_between_rotations if delay_between_r...
        delay_cfg = delay_between_rotations if delay_between_rotations is not None else int(os.environ.get("SCRAPER_DELAY_ROTATIONS", 10))
    except (ValueError, TypeError):
        # Asignamos 'delay_cfg' con 10
        delay_cfg = 10

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'sh_cfg' con shard if shard is not None else int(os.env...
        sh_cfg = shard if shard is not None else int(os.environ.get("SCRAPER_SHARD", 0))
    except (ValueError, TypeError):
        # Asignamos 'sh_cfg' con 0
        sh_cfg = 0

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 't_sh_cfg' con total_shards if total_shards is not None e...
        t_sh_cfg = total_shards if total_shards is not None else int(os.environ.get("SCRAPER_TOTAL_SHARDS", 0))
    except (ValueError, TypeError):
        # Asignamos 't_sh_cfg' con 0
        t_sh_cfg = 0

    # Asignamos 'session' con crear_sesion_robusta()
    session = crear_sesion_robusta()
    # Asignamos 'cb_cache' con cargar_circuit_breaker()
    cb_cache = cargar_circuit_breaker()

    # Asignamos 'perfumes_db' con []
    perfumes_db: List[Dict[str, Any]] = []
    # Asignamos 'tiendas_db' con []
    tiendas_db: List[Dict[str, Any]] = []
    # Asignamos 'urls_conocidas_map' con {}
    urls_conocidas_map: Dict[Tuple[int, int], Tuple[str, int]] = {}
    # Asignamos 'ofertas_activas_set' con set()
    ofertas_activas_set: Set[Tuple[int, int]] = set()
    # Asignamos 'perfume_last_verified' con {}
    perfume_last_verified: Dict[int, str] = {}

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            perfumes_db = _fetch_all_rows(
                lambda off, lim: (
                    sb.table("perfumes")
                    .select("id, nombre, marca, genero, tipo, precio_referencia, es_arabe")
                    .order("id", desc=False)
                    .range(off, off + lim - 1)
                ),
                page_size=1000,
            )
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            resp_t = sb.table("tiendas").select("id, nombre, url_base, trust_score").order("id").execute()
            # Asignamos 'tiendas_db' con resp_t.data or []
            tiendas_db = resp_t.data or []

            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            variantes_rows = _fetch_all_rows(
                lambda off, lim: (
                    sb.table("variantes_perfume")
                    .select("id, perfume_id, volumen_ml, formato")
                    .order("id", desc=False)
                    .range(off, off + lim - 1)
                ),
                page_size=1000,
            )
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            precargar_cache_variantes_supabase(variantes_rows)
            # Asignamos 'var_to_perf' con {}
            var_to_perf: Dict[int, Tuple[int, int, str]] = {}
            # Recorremos iterativamente cada 'vr' en variantes_rows
            for vr in variantes_rows:
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Asignamos 'var_to_perf[int(vr['id'])]' con (int(vr['perfume_id']), int(round(float(vr...
                    var_to_perf[int(vr["id"])] = (
                        int(vr["perfume_id"]),
                        int(round(float(vr.get("volumen_ml") or 100))),
                        str(vr.get("formato") or "regular").lower(),
                    )
                except Exception:
                    # Ejecutamos instrucción: pass
                    pass

            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            ofertas_rows = _fetch_all_rows(
                lambda off, lim: (
                    sb.table("ofertas_actuales")
                    .select("variante_id, tienda_id, url_producto, estado, ultima_verificacion_exitosa")
                    .neq("estado", "requiere_revision")
                    .order("id", desc=False)
                    .range(off, off + lim - 1)
                ),
                page_size=1000,
            )
            # Recorremos iterativamente cada 'oa' en ofertas_rows
            for oa in ofertas_rows:
                # Asignamos 'v_info' con var_to_perf.get(int(oa.get('variante_id') ...
                v_info = var_to_perf.get(int(oa.get("variante_id") or 0))
                # Evaluamos la condición lógica (v_info) para controlar el flujo
                if v_info:
                    # Asignamos 'pid' con v_info[0]
                    pid = v_info[0]
                    # Asignamos 't_id_oa' con int(oa['tienda_id'])
                    t_id_oa = int(oa["tienda_id"])
                    # Ejecutamos instrucción: ofertas_activas_set.add((pid, t_id_oa))
                    ofertas_activas_set.add((pid, t_id_oa))
                    # Asignamos 'ts' con oa.get('ultima_verificacion_exitosa')
                    ts = oa.get("ultima_verificacion_exitosa")
                    # Evaluamos la condición lógica (ts) para controlar el flujo
                    if ts:
                        # Evaluamos la condición lógica (pid not in perfume_last_verified or ts > perfume_las...) para controlar el flujo
                        if pid not in perfume_last_verified or ts > perfume_last_verified[pid]:
                            # Asignamos 'perfume_last_verified[pid]' con ts
                            perfume_last_verified[pid] = ts
                    # Asignamos 'u_prod' con str(oa.get('url_producto') or '').strip()
                    u_prod = str(oa.get("url_producto") or "").strip()
                    # Evaluamos la condición lógica (u_prod.startswith('http') and v_info[2] != 'tester') para controlar el flujo
                    if u_prod.startswith("http") and v_info[2] != "tester":
                        # Asignamos 'k_pt' con (pid, t_id_oa)
                        k_pt = (pid, t_id_oa)
                        # Evaluamos la condición lógica (k_pt not in urls_conocidas_map) para controlar el flujo
                        if k_pt not in urls_conocidas_map:
                            # Asignamos 'urls_conocidas_map[k_pt]' con (u_prod, v_info[1])
                            urls_conocidas_map[k_pt] = (u_prod, v_info[1])

            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.info(
                f"Catálogo cargado desde Supabase Cloud: {len(perfumes_db)} perfumes, "
                f"{len(tiendas_db)} tiendas, {len(urls_conocidas_map)} enlaces directos en caché."
            )
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Aviso consultando catálogo en Supabase ({e}), recurriendo a SQLite local.")

    # Evaluamos la condición lógica (not perfumes_db or not tiendas_db) para controlar el flujo
    if not perfumes_db or not tiendas_db:
        # Ejecutamos instrucción: init_db()
        init_db()
        # Asignamos 'conn' con get_connection()
        conn = get_connection()
        # Asignamos 'cursor' con conn.cursor()
        cursor = conn.cursor()
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id, nombre, marca, genero, tipo, precio_referencia, es_arabe FROM perfumes ORDER BY id ASC;")
        # Asignamos 'perfumes_db' con [dict(r) for r in cursor.fetchall()]
        perfumes_db = [dict(r) for r in cursor.fetchall()]
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id, nombre, url_base, trust_score FROM tiendas ORDER BY id ASC;")
        # Asignamos 'tiendas_db' con [dict(r) for r in cursor.fetchall()]
        tiendas_db = [dict(r) for r in cursor.fetchall()]
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            """
            SELECT vp.perfume_id, oa.tienda_id, oa.url_producto, 
                   CAST(ROUND(COALESCE(vp.volumen_ml, 100)) AS INTEGER) as vol_ml,
                   oa.ultima_verificacion_exitosa
            FROM ofertas_actuales oa
            JOIN variantes_perfume vp ON vp.id = oa.variante_id
            WHERE oa.url_producto IS NOT NULL AND oa.estado != 'requiere_revision' AND COALESCE(vp.formato, 'regular') != 'tester';
            """
        )
        # Recorremos iterativamente cada 'r' en cursor.fetchall()
        for r in cursor.fetchall():
            # Asignamos 'pid' con int(r['perfume_id'])
            pid = int(r["perfume_id"])
            # Asignamos 't_id_r' con int(r['tienda_id'])
            t_id_r = int(r["tienda_id"])
            # Ejecutamos instrucción: ofertas_activas_set.add((pid, t_id_r))
            ofertas_activas_set.add((pid, t_id_r))
            # Asignamos 'k_pt' con (pid, t_id_r)
            k_pt = (pid, t_id_r)
            # Evaluamos la condición lógica (k_pt not in urls_conocidas_map and str(r['url_produc...) para controlar el flujo
            if k_pt not in urls_conocidas_map and str(r["url_producto"]).startswith("http"):
                # Asignamos 'urls_conocidas_map[k_pt]' con (str(r['url_producto']), int(r['vol_ml'] o...
                urls_conocidas_map[k_pt] = (str(r["url_producto"]), int(r["vol_ml"] or 100))
            # Asignamos 'ts' con r['ultima_verificacion_exitosa'] if isinst...
            ts = r["ultima_verificacion_exitosa"] if isinstance(r, dict) else r.get("ultima_verificacion_exitosa")
            # Evaluamos la condición lógica (ts) para controlar el flujo
            if ts:
                # Evaluamos la condición lógica (pid not in perfume_last_verified or ts > perfume_las...) para controlar el flujo
                if pid not in perfume_last_verified or ts > perfume_last_verified[pid]:
                    # Asignamos 'perfume_last_verified[pid]' con ts
                    perfume_last_verified[pid] = ts
        # Ejecutamos instrucción: conn.close()
        conn.close()
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        logger.info(f"Catálogo cargado desde SQLite local: {len(perfumes_db)} perfumes, {len(tiendas_db)} tiendas.")

    # Priorización inteligente mediante cola LRU:
    # 1. Perfumes sin verificación previa o nuevos (False, "")
    # 2. Perfumes con auditoría más lejana en el tiempo (True, "2026-10-14...")
    # 3. Perfumes auditados recientemente quedan al final de la cola (True, "2026-10-28...")
    perfumes_db.sort(
        key=lambda p: (
            perfume_last_verified.get(p["id"]) is not None,
            perfume_last_verified.get(p["id"]) or "",
        )
    )

    # - ¿Qué hace esta fórmula matemática de Horizontal Sharding?:
    #   Aplica el operador módulo [idx % total_shards == (shard - 1)] para particionar los 3,224 perfumes en 4 subconjuntos disjuntos.
    #   Cada uno de los 4 runners de GitHub Actions recibe exactamente 806 perfumes, trabajando en paralelo sin colisionar ni duplicar trabajo.
    if sh_cfg > 0 and t_sh_cfg > 1:
        # Evaluamos la condición lógica (sh_cfg > t_sh_cfg) para controlar el flujo
        if sh_cfg > t_sh_cfg:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"Shard {sh_cfg} es mayor que total_shards {t_sh_cfg}. Ajustando a {t_sh_cfg}.")
            # Asignamos 'sh_cfg' con t_sh_cfg
            sh_cfg = t_sh_cfg
        # Asignamos 'perfumes_antes' con len(perfumes_db)
        perfumes_antes = len(perfumes_db)
        # Asignamos 'perfumes_db' con [p for idx, p in enumerate(perfumes_db) if...
        perfumes_db = [p for idx, p in enumerate(perfumes_db) if idx % t_sh_cfg == (sh_cfg - 1)]
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(
            f"Horizontal Sharding activo: Shard {sh_cfg}/{t_sh_cfg} asignado. "
            f"Procesando {len(perfumes_db)} de {perfumes_antes} perfumes del catálogo."
        )

    # Asignamos 'limit_env' con os.environ.get('SCRAPER_LIMIT_PERFUMES')
    limit_env = os.environ.get("SCRAPER_LIMIT_PERFUMES")
    # Evaluamos la condición lógica (limit_env and limit_env.isdigit()) para controlar el flujo
    if limit_env and limit_env.isdigit():
        # Asignamos 'max_p' con int(limit_env)
        max_p = int(limit_env)
        # Asignamos 'perfumes_db' con perfumes_db[:max_p]
        perfumes_db = perfumes_db[:max_p]
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(f"Modo de prueba activo (SCRAPER_LIMIT_PERFUMES={max_p}): auditando {len(perfumes_db)} perfumes.")

    # Asignamos 'total_perfumes' con len(perfumes_db)
    total_perfumes = len(perfumes_db)
    # Asignamos 'max_posibles_rotaciones' con max(1, math.ceil(total_perfumes / effectiv...
    max_posibles_rotaciones = max(1, math.ceil(total_perfumes / effective_batch_size))
    # Evaluamos la condición lógica (rot_cfg <= 0) para controlar el flujo
    if rot_cfg <= 0:
        # Asignamos 'num_rotaciones' con max_posibles_rotaciones
        num_rotaciones = max_posibles_rotaciones
    else:
        # Asignamos 'num_rotaciones' con min(rot_cfg, max_posibles_rotaciones)
        num_rotaciones = min(rot_cfg, max_posibles_rotaciones)

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(
        f"Planificando ejecución ETL por rotaciones: {total_perfumes} perfumes totales, "
        f"{num_rotaciones} rotación(es) planificada(s) de hasta {effective_batch_size} perfumes c/u "
        f"(cooldown entre rotaciones: {delay_cfg}s)."
    )

    # Asignamos 'consolidado_reportes' con []
    consolidado_reportes: List[Dict[str, Any]] = []
    # Asignamos 'total_actualizaciones' con 0
    total_actualizaciones = 0
    # Asignamos 'total_ofertas_nuevas' con 0
    total_ofertas_nuevas = 0
    # Asignamos 'total_cambios_precio' con 0
    total_cambios_precio = 0
    # Asignamos 'total_cambios_stock' con 0
    total_cambios_stock = 0
    # Asignamos 'total_cambios_url' con 0
    total_cambios_url = 0
    # Asignamos 'total_bloqueos_waf' con 0
    total_bloqueos_waf = 0
    # Asignamos 'total_exclusiones' con 0
    total_exclusiones = 0
    # Asignamos 'total_omitidos_cb' con 0
    total_omitidos_cb = 0
    # Asignamos 'total_outliers' con 0
    total_outliers = 0
    # Asignamos 'total_errores' con []
    total_errores: List[str] = []
    # Asignamos 'muestras_consolidadas' con []
    muestras_consolidadas: List[Dict[str, Any]] = []
    # Asignamos 'muestras_exclusiones' con []
    muestras_exclusiones: List[Dict[str, Any]] = []
    # Asignamos 'outliers_consolidados' con []
    outliers_consolidados: List[Dict[str, Any]] = []
    # Asignamos 'reporte_resultado' con {}
    reporte_resultado: Dict[str, Any] = {}

    # Precarga masiva en memoria de tiendas Shopify y WooCommerce (13 tiendas en ~15-20s)
    cache_tiendas_bulk: Optional[Dict[str, CatalogoTiendaBulk]] = None
    # Asignamos 'bulk_habilitado' con os.environ.get('SCRAPER_ENABLE_BULK', 'tru...
    bulk_habilitado = os.environ.get("SCRAPER_ENABLE_BULK", "true").lower() not in ("false", "0", "no")
    # Evaluamos la condición lógica (bulk_habilitado) para controlar el flujo
    if bulk_habilitado:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'cache_tiendas_bulk' con precargar_catalogos_bulk_tiendas(session=s...
            cache_tiendas_bulk = precargar_catalogos_bulk_tiendas(
                session=session,
                tiendas_db=tiendas_db,
            )
        except Exception as e_bulk:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"Aviso en precarga masiva de tiendas ({e_bulk}), continuando con modo estándar individual.")
            # Asignamos 'cache_tiendas_bulk' con None
            cache_tiendas_bulk = None

    # Asignamos 'descubrir_activo' con descubrir if descubrir is not None else os...
    descubrir_activo = (
        descubrir if descubrir is not None
        else os.environ.get("SCRAPER_AUTO_DISCOVER", "false").lower() in ("true", "1", "yes")
    )
    # Asignamos 'reporte_descubrimiento' con None
    reporte_descubrimiento: Optional[Dict[str, Any]] = None
    # Evaluamos la condición lógica (descubrir_activo and cache_tiendas_bulk and descubri...) para controlar el flujo
    if descubrir_activo and cache_tiendas_bulk and descubrir_nuevos_perfumes_desde_bulk:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info("\n" + "=" * 70)
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info("INICIANDO FASE DE AUTO-DESCUBRIMIENTO DE NUEVOS PERFUMES EN MEMORIA")
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info("=" * 70)
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'reporte_descubrimiento' con descubrir_nuevos_perfumes_desde_bulk(cache...
            reporte_descubrimiento = descubrir_nuevos_perfumes_desde_bulk(cache_tiendas_bulk)
            # Asignamos 'nuevos_desc' con reporte_descubrimiento.get('metricas', {})...
            nuevos_desc = (
                reporte_descubrimiento.get("metricas", {}).get("nuevos_perfumes_descubiertos", 0)
                if reporte_descubrimiento else 0
            )
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info(f"Fase de auto-descubrimiento completada: {nuevos_desc} nuevas fragancias incorporadas a la base de datos.")
        except Exception as e_desc:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"Aviso en fase de auto-descubrimiento en bulk: {e_desc}")

    # Recorremos iterativamente cada 'rot_idx' en range(1, num_rotaciones + 1)
    for rot_idx in range(1, num_rotaciones + 1):
        # Asignamos 'idx_start' con (rot_idx - 1) * effective_batch_size
        idx_start = (rot_idx - 1) * effective_batch_size
        # Asignamos 'idx_end' con min(idx_start + effective_batch_size, tota...
        idx_end = min(idx_start + effective_batch_size, total_perfumes)
        # Asignamos 'lote' con perfumes_db[idx_start:idx_end]
        lote = perfumes_db[idx_start:idx_end]

        # Asignamos 'sep_line' con '=' * 70
        sep_line = "=" * 70
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(
            f"\n{sep_line}\n"
            f"INICIANDO ROTACIÓN {rot_idx}/{num_rotaciones} "
            f"({len(lote)} perfumes: rango [{idx_start}:{idx_end}] de {total_perfumes})\n"
            f"{sep_line}"
        )

        # Asignamos 'rep_lote' con auditar_lote_perfumes(perfumes_lote=lote, ...
        rep_lote = auditar_lote_perfumes(
            perfumes_lote=lote,
            tiendas_db=tiendas_db,
            urls_conocidas_map=urls_conocidas_map,
            session=session,
            rotacion_idx=rot_idx,
            total_rotaciones=num_rotaciones,
            total_catalogo=total_perfumes,
            cache_tiendas_bulk=cache_tiendas_bulk,
            ofertas_activas_set=ofertas_activas_set,
            cb_cache=cb_cache,
        )
        # Ejecutamos instrucción: guardar_circuit_breaker(cb_cache)
        guardar_circuit_breaker(cb_cache)

        # Ejecutamos instrucción: consolidado_reportes.append(rep_lote)
        consolidado_reportes.append(rep_lote)
        # Asignamos 'm_lote' con rep_lote['metricas']
        m_lote = rep_lote["metricas"]
        # Actualizamos acumulativamente el valor de 'total_actualizaciones'
        total_actualizaciones += m_lote["precios_actualizados"]
        # Actualizamos acumulativamente el valor de 'total_ofertas_nuevas'
        total_ofertas_nuevas += m_lote["ofertas_nuevas"]
        # Actualizamos acumulativamente el valor de 'total_cambios_precio'
        total_cambios_precio += m_lote["cambios_precio"]
        # Actualizamos acumulativamente el valor de 'total_cambios_stock'
        total_cambios_stock += m_lote["cambios_stock"]
        # Actualizamos acumulativamente el valor de 'total_cambios_url'
        total_cambios_url += m_lote["cambios_url"]
        # Actualizamos acumulativamente el valor de 'total_bloqueos_waf'
        total_bloqueos_waf += m_lote["bloqueos_waf"]
        # Actualizamos acumulativamente el valor de 'total_exclusiones'
        total_exclusiones += m_lote.get("exclusiones_marca", 0)
        # Actualizamos acumulativamente el valor de 'total_omitidos_cb'
        total_omitidos_cb += m_lote.get("omitidos_circuit_breaker", 0)
        # Actualizamos acumulativamente el valor de 'total_outliers'
        total_outliers += m_lote.get("outliers_marcados", 0)
        # Ejecutamos instrucción: total_errores.extend(rep_lote.get('errores', []))
        total_errores.extend(rep_lote.get("errores", []))
        # Ejecutamos instrucción: muestras_consolidadas.extend(rep_lote.get('muestra_c...
        muestras_consolidadas.extend(rep_lote.get("muestra_capturas", []))
        # Evaluamos la condición lógica (len(muestras_exclusiones) < 50) para controlar el flujo
        if len(muestras_exclusiones) < 50:
            # Ejecutamos instrucción: muestras_exclusiones.extend(rep_lote.get('muestra_ex...
            muestras_exclusiones.extend(rep_lote.get("muestra_exclusiones_marca", [])[: max(0, 50 - len(muestras_exclusiones))])
        # Evaluamos la condición lógica (len(outliers_consolidados) < 50) para controlar el flujo
        if len(outliers_consolidados) < 50:
            # Ejecutamos instrucción: outliers_consolidados.extend(rep_lote.get('outliers_...
            outliers_consolidados.extend(rep_lote.get("outliers_detectados", [])[: max(0, 50 - len(outliers_consolidados))])

        # Asignamos 'duracion_parcial' con round(time.time() - inicio_global, 2)
        duracion_parcial = round(time.time() - inicio_global, 2)
        # Asignamos 'estado_global' con 'EXITOSO' if not total_errores else 'DEGRA...
        estado_global = "EXITOSO" if not total_errores else ("DEGRADADO" if total_actualizaciones > 0 else "FALLIDO")

        # Guardar reporte consolidado intermedio de auditoría tras cada rotación
        reporte_resultado = {
            "actualizaciones": total_actualizaciones,
            "fecha": ahora_global,
            "duracion_segundos": duracion_parcial,
            "metadata": {
                "version_etl": "3.3.0",
                "sistema": "PerfumeTrending Professional Anti-Bot ETL (Multi-Rotation LRU)",
                "fecha_ejecucion": ahora_global,
                "duracion_segundos": duracion_parcial,
                "estado": estado_global,
                "rotaciones_completadas": rot_idx,
                "total_rotaciones_planificadas": num_rotaciones,
                "tamano_lote": effective_batch_size,
                "shard": sh_cfg,
                "total_shards": t_sh_cfg,
            },
            "metricas": {
                "total_perfumes_catalogo": total_perfumes,
                "perfumes_auditados": idx_end,
                "total_tiendas_registradas": len(tiendas_db),
                "precios_actualizados": total_actualizaciones,
                "ofertas_nuevas": total_ofertas_nuevas,
                "cambios_precio": total_cambios_precio,
                "cambios_stock": total_cambios_stock,
                "cambios_url": total_cambios_url,
                "bloqueos_waf": total_bloqueos_waf,
                "exclusiones_marca": total_exclusiones,
                "omitidos_circuit_breaker": total_omitidos_cb,
                "outliers_marcados": total_outliers,
                "errores_totales": len(total_errores),
            },
            "estadisticas_tiendas": _combinar_tiendas_stats(
                [r["estadisticas_tiendas"] for r in consolidado_reportes], tiendas_db
            ),
            "muestra_capturas": muestras_consolidadas[:25],
            "muestra_exclusiones_marca": muestras_exclusiones[:50],
            "outliers_detectados": outliers_consolidados[:50],
            "descubrimiento": reporte_descubrimiento,
            "rotaciones_detalle": [
                {
                    "rotacion": r["metadata"].get("rotacion_idx", i + 1),
                    "scraping_run_id": r["metadata"].get("scraping_run_id"),
                    "perfumes": r["metricas"]["perfumes_auditados"],
                    "actualizaciones": r["metricas"]["precios_actualizados"],
                    "duracion_segundos": r["duracion_segundos"],
                    "estado": r["metadata"]["estado"],
                }
                for i, r in enumerate(consolidado_reportes)
            ],
            "errores": total_errores[:20],
        }
        # Evaluamos la condición lógica (sh_cfg > 0 and t_sh_cfg > 1) para controlar el flujo
        if sh_cfg > 0 and t_sh_cfg > 1:
            # Asignamos 'target_reporte' con os.path.join(REPORTES_DIR, f'ultimo_scrapi...
            target_reporte = os.path.join(REPORTES_DIR, f"ultimo_scraping_shard_{sh_cfg}.json")
            # Ejecutamos instrucción: guardar_reporte_auditoria(reporte_resultado, ruta_de...
            guardar_reporte_auditoria(reporte_resultado, ruta_destino=target_reporte)
            # Evaluamos la condición lógica (sh_cfg == 1) para controlar el flujo
            if sh_cfg == 1:
                # Ejecutamos instrucción: guardar_reporte_auditoria(reporte_resultado, ruta_de...
                guardar_reporte_auditoria(reporte_resultado, ruta_destino=REPORTE_ULTIMO_PATH)
        else:
            # Ejecutamos instrucción: guardar_reporte_auditoria(reporte_resultado)
            guardar_reporte_auditoria(reporte_resultado)

        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.info(
            f"=== ROTACIÓN {rot_idx}/{num_rotaciones} COMPLETADA "
            f"({m_lote['precios_actualizados']} precios actualizados en {rep_lote['duracion_segundos']}s) ==="
        )

        # Evaluamos la condición lógica (rot_idx < num_rotaciones) para controlar el flujo
        if rot_idx < num_rotaciones:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info(f"Cooldown de {delay_cfg}s antes de iniciar la rotación {rot_idx + 1}/{num_rotaciones}...")
            # Ejecutamos instrucción: time.sleep(delay_cfg)
            time.sleep(delay_cfg)

    # Asignamos 'duracion_final' con round(time.time() - inicio_global, 2)
    duracion_final = round(time.time() - inicio_global, 2)
    # Asignamos 'sep_line' con '=' * 70
    sep_line = "=" * 70
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(
        f"\n{sep_line}\n"
        f"CICLO ETL COMPLETO: {num_rotaciones} rotación(es) en {duracion_final}s | "
        f"{total_actualizaciones} precios sincronizados | Estado: {reporte_resultado.get('metadata', {}).get('estado', 'EXITOSO')}\n"
        f"{sep_line}"
    )
    # Retornamos el resultado procesado (reporte_resultado)
    return reporte_resultado


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(
        description="PerfumeTrending.cl — Motor de Scraping Periódico por Rotaciones LRU"
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("SCRAPER_BATCH_SIZE", 500)),
        help="Cantidad de perfumes por rotación (lote). Por defecto 500.",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--rotations",
        type=int,
        default=int(os.environ.get("SCRAPER_ROTATIONS", 0)),
        help="Número de rotaciones a ejecutar (0 = todas las necesarias para cubrir el catálogo).",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--delay",
        type=int,
        default=int(os.environ.get("SCRAPER_DELAY_ROTATIONS", 10)),
        help="Segundos de cooldown entre rotaciones consecutivas. Por defecto 10s.",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--no-bulk",
        action="store_true",
        help="Desactivar precarga masiva JSON y forzar modo HTTP individual secuencial.",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--shard",
        type=int,
        default=int(os.environ.get("SCRAPER_SHARD", 0)),
        help="Índice de partición horizontal (1-based, e.g. 1 o 2). Por defecto 0 (sin partición).",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--total-shards",
        type=int,
        default=int(os.environ.get("SCRAPER_TOTAL_SHARDS", 0)),
        help="Total de particiones horizontales en ejecución paralela (e.g. 2). Por defecto 0.",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--reset-circuit-breaker",
        action="store_true",
        help="Reiniciar archivo de cooldown/circuit breaker para tiendas retail.",
    )
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument(
        "--descubrir",
        action="store_true",
        help="Activar auto-descubrimiento en memoria de nuevas fragancias en los feeds de tiendas.",
    )
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Evaluamos la condición lógica (args.no_bulk) para controlar el flujo
    if args.no_bulk:
        # Asignamos 'os.environ['SCRAPER_ENABLE_BULK']' con 'false'
        os.environ["SCRAPER_ENABLE_BULK"] = "false"
    # Evaluamos la condición lógica (args.reset_circuit_breaker and os.path.exists(CIRCUI...) para controlar el flujo
    if args.reset_circuit_breaker and os.path.exists(CIRCUIT_BREAKER_PATH):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Ejecutamos instrucción: os.remove(CIRCUIT_BREAKER_PATH)
            os.remove(CIRCUIT_BREAKER_PATH)
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info("Circuit breaker reiniciado exitosamente.")
        except Exception as e_cb_rm:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"Error reiniciando circuit breaker: {e_cb_rm}")

    # Asignamos 'resultado' con ejecutar_ciclo_scraping_y_descubrimiento(b...
    resultado = ejecutar_ciclo_scraping_y_descubrimiento(
        batch_size=args.batch_size,
        rotations=args.rotations,
        delay_between_rotations=args.delay,
        shard=args.shard,
        total_shards=args.total_shards,
        descubrir=args.descubrir,
    )
    # Asignamos 'sep_box' con '=' * 60
    sep_box = "=" * 60
    # Ejecutamos instrucción: print('\n' + sep_box)
    print("\n" + sep_box)
    # Ejecutamos instrucción: print('RESUMEN DE EJECUCIÓN ETL DE SCRAPING (ROTACIO...
    print("RESUMEN DE EJECUCIÓN ETL DE SCRAPING (ROTACIONES LRU):")
    # Ejecutamos instrucción: print(f"Estado General: {resultado.get('metadata', {...
    print(f"Estado General: {resultado.get('metadata', {}).get('estado', 'EXITOSO')}")
    # Ejecutamos instrucción: print(f"Rotaciones ejecutadas: {resultado.get('metad...
    print(f"Rotaciones ejecutadas: {resultado.get('metadata', {}).get('rotaciones_completadas', 1)} / {resultado.get('metadata', {}).get('total_rotaciones_planificadas', 1)}")
    # Ejecutamos instrucción: print(f"Perfumes auditados: {resultado.get('metricas...
    print(f"Perfumes auditados: {resultado.get('metricas', {}).get('perfumes_auditados', 0)} / {resultado.get('metricas', {}).get('total_perfumes_catalogo', 0)}")
    # Ejecutamos instrucción: print(f"Precios actualizados: {resultado.get('metric...
    print(f"Precios actualizados: {resultado.get('metricas', {}).get('precios_actualizados', 0)}")
    # Ejecutamos instrucción: print(f"Ofertas nuevas: {resultado.get('metricas', {...
    print(f"Ofertas nuevas: {resultado.get('metricas', {}).get('ofertas_nuevas', 0)}")
    # Evaluamos la condición lógica (resultado.get('descubrimiento')) para controlar el flujo
    if resultado.get("descubrimiento"):
        # Asignamos 'd_met' con resultado['descubrimiento'].get('metricas'...
        d_met = resultado["descubrimiento"].get("metricas", {})
        # Ejecutamos instrucción: print(f"Nuevos perfumes descubiertos: {d_met.get('nu...
        print(f"Nuevos perfumes descubiertos: {d_met.get('nuevos_perfumes_descubiertos', 0)}")
    # Ejecutamos instrucción: print(f"Duración total: {resultado.get('metadata', {...
    print(f"Duración total: {resultado.get('metadata', {}).get('duracion_segundos', 0)}s")
    # Ejecutamos instrucción: print(sep_box)
    print(sep_box)
