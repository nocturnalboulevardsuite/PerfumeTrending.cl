"""
PerfumeTrending.cl — Motor de Descubrimiento Autónomo de Catálogo (Crawler ETL)
==============================================================================
Servicio autónomo para el descubrimiento continuo y masivo de fragancias en
comercios auditados de Chile a través de endpoints JSON estandarizados (Shopify).

Capacidades de Ingeniería:
- Rastreo multi-página con límite configurable de productos.
- Extracción de variantes nativas: capacidades (30ml, 50ml, 100ml, 200ml) y precios individuales.
- Deduplicación y normalización inteligente de marcas, nombres y concentraciones.
- Creación automática de nuevos perfumes en el catálogo maestro.
- Registro de snapshots con cálculo de Precio por Mililitro ($/ml).
- Generación de informe de auditoría en data/reportes/ultimo_descubrimiento.json.
"""

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
# Importación de componentes (Any, Dict, List, Optional) desde el módulo 'typing'
from typing import Any, Dict, List, Optional
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse

# Importación de librería estándar o dependencia externa (requests)
import requests
# Importación de componentes (HTTPAdapter) desde el módulo 'requests.adapters'
from requests.adapters import HTTPAdapter
# Importación de componentes (Retry) desde el módulo 'urllib3.util'
from urllib3.util import Retry

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
# Asignamos 'REPORTES_DIR' con os.path.join(BASE_DIR, 'data', 'reportes')
REPORTES_DIR = os.path.join(BASE_DIR, "data", "reportes")
# Asignamos 'REPORTE_DESCUBRIMIENTO_PATH' con os.path.join(REPORTES_DIR, 'ultimo_descubr...
REPORTE_DESCUBRIMIENTO_PATH = os.path.join(REPORTES_DIR, "ultimo_descubrimiento.json")

# Importación de persistencia y normalización
try:
    # Importación de componentes (get_db_cursor, init_db) desde el módulo 'backend.database'
    from backend.database import get_db_cursor, init_db
    # Importación de componentes (extraer_volumen_ml, extraer_concentracion, extraer_genero, es_arabe, ...) desde el módulo 'backend.normalizador'
    from backend.normalizador import (
        extraer_volumen_ml,
        extraer_concentracion,
        extraer_genero,
        es_arabe,
        es_producto_perfume_valido,
        limpiar_nombre_perfume
    )
except ImportError:
    # Importación de componentes (get_db_cursor, init_db) desde el módulo 'database'
    from database import get_db_cursor, init_db
    # Importación de componentes (extraer_volumen_ml, extraer_concentracion, extraer_genero, es_arabe, ...) desde el módulo 'normalizador'
    from normalizador import (
        extraer_volumen_ml,
        extraer_concentracion,
        extraer_genero,
        es_arabe,
        es_producto_perfume_valido,
        limpiar_nombre_perfume
    )

# Asignamos 'TIENDAS_CRAWLER_CONFIG' con [{'nombre': 'Silk Perfumes', 'url_base': '...
TIENDAS_CRAWLER_CONFIG = [
    # Configuración de elemento #1 (nombre='Silk Perfumes')
    {
        "nombre": "Silk Perfumes",
        "url_base": "https://www.silkperfumes.cl",
        "endpoint": "https://www.silkperfumes.cl/products.json",
        "trust_score": 92
    },
    # Configuración de elemento #2 (nombre='Elite Perfumes')
    {
        "nombre": "Elite Perfumes",
        "url_base": "https://www.eliteperfumes.cl",
        "endpoint": "https://www.eliteperfumes.cl/products.json",
        "trust_score": 89
    }
]

# Asignamos 'USER_AGENTS' con ['Mozilla/5.0 (Windows NT 10.0; Win64; x64...
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
]


# Definición de función 'crear_sesion_robusta' sin parámetros externos
def crear_sesion_robusta() -> requests.Session:
    """Crea una sesión HTTP con reintentos exponenciales y timeouts defensivos."""
    # Asignamos 'session' con requests.Session()
    session = requests.Session()
    # Asignamos 'retry_strategy' con Retry(total=3, backoff_factor=0.5, status_...
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
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


# Definición de función 'obtener_ultimo_reporte_descubrimiento' sin parámetros externos
def obtener_ultimo_reporte_descubrimiento() -> Optional[Dict[str, Any]]:
    """Carga el último informe de descubrimiento autónomo generado."""
    # Evaluamos la condición lógica (os.path.exists(REPORTE_DESCUBRIMIENTO_PATH)) para controlar el flujo
    if os.path.exists(REPORTE_DESCUBRIMIENTO_PATH):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Gestión automática de contexto y recursos para: open(REPORTE_DESCUBRIMIENTO_PATH, 'r', encoding...
            with open(REPORTE_DESCUBRIMIENTO_PATH, "r", encoding="utf-8") as f:
                # Retornamos el resultado procesado (json.load(f))
                return json.load(f)
        except Exception:
            # Ejecutamos instrucción: pass
            pass
    # Retornamos el resultado procesado (None)
    return None


# Definición de función 'guardar_reporte_descubrimiento' (parámetros: reporte)
def guardar_reporte_descubrimiento(reporte: Dict[str, Any]) -> str:
    """Persiste el informe en JSON para auditoría y observabilidad."""
    # Ejecutamos instrucción: os.makedirs(REPORTES_DIR, exist_ok=True)
    os.makedirs(REPORTES_DIR, exist_ok=True)
    # Gestión automática de contexto y recursos para: open(REPORTE_DESCUBRIMIENTO_PATH, 'w', encoding...
    with open(REPORTE_DESCUBRIMIENTO_PATH, "w", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    # Retornamos el resultado procesado (REPORTE_DESCUBRIMIENTO_PATH)
    return REPORTE_DESCUBRIMIENTO_PATH


# Definición de función 'ejecutar_descubrimiento_autonomo' (parámetros: limite_por_tienda, paginas)
def ejecutar_descubrimiento_autonomo(
    limite_por_tienda: int = 30,
    paginas: int = 1
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de rastreo masivo autónomo:
    1. Descarga colecciones públicas JSON de tiendas de perfumería.
    2. Descarta productos que no sean fragancias (cremas, desodorantes).
    3. Extrae variantes (volumen en ml y precios de cada tamaño).
    4. Deduplica o inserta perfumes nuevos con sus packshots en alta resolución.
    5. Ingesta snapshots con cálculo de Precio por Mililitro ($/ml).
    6. Genera reporte auditable de ejecución.
    """
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'inicio' con time.time()
    inicio = time.time()
    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Iniciando descubrimiento autónomo (límite: {limite_por_tienda} items/tienda, {paginas} páginas)")

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

    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Obtener mapeo de tiendas existentes
        cursor.execute("SELECT id, nombre FROM tiendas;")
        # Asignamos 'tiendas_map' con {r['nombre']: r['id'] for r in cursor.fetc...
        tiendas_map = {r["nombre"]: r["id"] for r in cursor.fetchall()}

        # Recorremos iterativamente cada 'tienda_cfg' en TIENDAS_CRAWLER_CONFIG
        for tienda_cfg in TIENDAS_CRAWLER_CONFIG:
            # Asignamos 't_nombre' con tienda_cfg['nombre']
            t_nombre = tienda_cfg["nombre"]
            # Asignamos 't_url_base' con tienda_cfg['url_base']
            t_url_base = tienda_cfg["url_base"]
            # Asignamos 't_endpoint' con tienda_cfg['endpoint']
            t_endpoint = tienda_cfg["endpoint"]

            # Asegurar que la tienda exista en BD
            if t_nombre not in tiendas_map:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("""
                INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
                VALUES (?, ?, ?, 'Comercio Auditado 🇨🇱', '🏬');
                """, (t_nombre, t_url_base, tienda_cfg["trust_score"]))
                # Asignamos 't_id' con cursor.lastrowid
                t_id = cursor.lastrowid
                # Asignamos 'tiendas_map[t_nombre]' con t_id
                tiendas_map[t_nombre] = t_id
            else:
                # Asignamos 't_id' con tiendas_map[t_nombre]
                t_id = tiendas_map[t_nombre]

            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.info(f"Rastreando catálogo de: {t_nombre}...")

            # Recorremos iterativamente cada 'pag' en range(1, paginas + 1)
            for pag in range(1, paginas + 1):
                # Asignamos 'params' con {'limit': limite_por_tienda, 'page': pag}
                params = {"limit": limite_por_tienda, "page": pag}
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
                    res = session.get(t_endpoint, params=params, headers=headers, timeout=12)
                    # Evaluamos la condición lógica (res.status_code != 200) para controlar el flujo
                    if res.status_code != 200:
                        # Registro de evento diagnóstico en la bitácora (logger) del sistema
                        logger.warning(f"Respuesta HTTP {res.status_code} en {t_nombre} (pág {pag})")
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Asignamos 'data' con res.json()
                    data = res.json()
                    # Asignamos 'productos' con data.get('products', [])
                    productos = data.get("products", [])
                    # Evaluamos la condición lógica (not productos) para controlar el flujo
                    if not productos:
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break

                    # Recorremos iterativamente cada 'prod' en productos
                    for prod in productos:
                        # Actualizamos acumulativamente el valor de 'total_procesados'
                        total_procesados += 1
                        # Asignamos 'raw_title' con prod.get('title', '')
                        raw_title = prod.get("title", "")
                        # Asignamos 'raw_vendor' con (prod.get('vendor', '') or '').strip()
                        raw_vendor = (prod.get("vendor", "") or "").strip()
                        # Asignamos 'tags' con prod.get('tags', [])
                        tags = prod.get("tags", [])

                        # 1. Filtro estricto de productos que no son fragancias
                        if not es_producto_perfume_valido(raw_title, tags):
                            # Actualizamos acumulativamente el valor de 'descartados_no_perfume'
                            descartados_no_perfume += 1
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # 2. Normalización de atributos
                        marca = raw_vendor if len(raw_vendor) > 1 else "Diseñador"
                        # Asignamos 'nombre_limpio' con limpiar_nombre_perfume(raw_title, marca)
                        nombre_limpio = limpiar_nombre_perfume(raw_title, marca)
                        # Asignamos 'concentracion' con extraer_concentracion(raw_title)
                        concentracion = extraer_concentracion(raw_title)
                        # Asignamos 'genero' con extraer_genero(raw_title)
                        genero = extraer_genero(raw_title)
                        # Asignamos 'arabe_flag' con 1 if es_arabe(marca, nombre_limpio) else 0
                        arabe_flag = 1 if es_arabe(marca, nombre_limpio) else 0

                        # Imagen
                        images = prod.get("images", [])
                        # Asignamos 'img_url' con images[0].get('src', '') if images else 'h...
                        img_url = images[0].get("src", "") if images else "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
                        # Asignamos 'url_producto' con f"{t_url_base}/products/{prod.get('handle'...
                        url_producto = f"{t_url_base}/products/{prod.get('handle', '')}"

                        # 3. Buscar si el perfume ya existe en catálogo
                        cursor.execute("""
                        SELECT id, precio_referencia FROM perfumes 
                        WHERE LOWER(nombre) = LOWER(?) AND (LOWER(marca) = LOWER(?) OR ? = 'Diseñador');
                        """, (nombre_limpio, marca, marca))
                        # Asignamos 'row_perfume' con cursor.fetchone()
                        row_perfume = cursor.fetchone()

                        # Asignamos 'variants' con prod.get('variants', [])
                        variants = prod.get("variants", [])
                        # Evaluamos la condición lógica (not variants) para controlar el flujo
                        if not variants:
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Precio base para referencia
                        primer_precio = int(float(variants[0].get("price", 0)))
                        # Evaluamos la condición lógica (primer_precio <= 0) para controlar el flujo
                        if primer_precio <= 0:
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue

                        # Evaluamos la condición lógica (row_perfume) para controlar el flujo
                        if row_perfume:
                            # Asignamos 'perfume_id' con row_perfume['id']
                            perfume_id = row_perfume["id"]
                        else:
                            # Insertar nuevo perfume descubierto
                            cursor.execute("""
                            INSERT INTO perfumes (
                                nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia
                            )
                            VALUES (?, ?, ?, ?, 'Notas aromáticas exclusivas', ?, ?, 0, 0, ?);
                            """, (nombre_limpio, marca, genero, concentracion, img_url, arabe_flag, primer_precio))
                            # Asignamos 'perfume_id' con cursor.lastrowid
                            perfume_id = cursor.lastrowid
                            # Actualizamos acumulativamente el valor de 'nuevos_perfumes'
                            nuevos_perfumes += 1

                            # Ejecutamos instrucción: muestras_descubiertas.append({'id': perfume_id, 'nom...
                            muestras_descubiertas.append({
                                "id": perfume_id,
                                "nombre": nombre_limpio,
                                "marca": marca,
                                "tipo": concentracion,
                                "es_arabe": bool(arabe_flag),
                                "tienda": t_nombre,
                                "precio": primer_precio
                            })

                        # 4. Ingesta de cada variante por volumen en ML
                        for v in variants:
                            # Asignamos 'v_price' con int(float(v.get('price', 0)))
                            v_price = int(float(v.get("price", 0)))
                            # Evaluamos la condición lógica (v_price <= 0) para controlar el flujo
                            if v_price <= 0:
                                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                                continue

                            # Asignamos 'v_compare' con int(float(v.get('compare_at_price') or v_p...
                            v_compare = int(float(v.get("compare_at_price") or (v_price * 1.15)))
                            # Asignamos 'v_stock' con 1 if v.get('available', True) else 0
                            v_stock = 1 if v.get("available", True) else 0
                            # Asignamos 'v_title' con v.get('title', '')
                            v_title = v.get("title", "")
                            # Asignamos 'volumen_ml' con extraer_volumen_ml(f'{raw_title} {v_title}')
                            volumen_ml = extraer_volumen_ml(f"{raw_title} {v_title}")

                            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                            cursor.execute("""
                            INSERT INTO precios_registro (
                                perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                            """, (perfume_id, t_id, v_price, v_compare, v_stock, volumen_ml, url_producto, ahora))
                            # Actualizamos acumulativamente el valor de 'precios_registrados'
                            precios_registrados += 1

                except Exception as e:
                    # Asignamos 'err_msg' con f'Fallo procesando {t_nombre} página {pag}...
                    err_msg = f"Fallo procesando {t_nombre} página {pag}: {e}"
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.error(err_msg)
                    # Ejecutamos instrucción: errores.append(err_msg)
                    errores.append(err_msg)

                # Pausa cortés entre páginas
                time.sleep(0.6)

    # Asignamos 'duracion' con round(time.time() - inicio, 2)
    duracion = round(time.time() - inicio, 2)
    # Asignamos 'estado' con 'EXITOSO' if not errores else 'DEGRADADO' ...
    estado = "EXITOSO" if not errores else ("DEGRADADO" if precios_registrados > 0 else "FALLIDO")

    # Asignamos 'reporte' con {'metadata': {'version': '1.0.0', 'sistema...
    reporte = {
        "metadata": {
            "version": "1.0.0",
            "sistema": "PerfumeTrending Autonomous Discovery Crawler",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado
        },
        "metricas": {
            "total_productos_analizados": total_procesados,
            "descartados_no_perfume": descartados_no_perfume,
            "nuevos_perfumes_descubiertos": nuevos_perfumes,
            "precios_variantes_registrados": precios_registrados,
            "errores_totales": len(errores)
        },
        "muestras_nuevas": muestras_descubiertas[:10],
        "errores": errores
    }

    # Ejecutamos instrucción: guardar_reporte_descubrimiento(reporte)
    guardar_reporte_descubrimiento(reporte)
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Ciclo completado en {duracion}s | {nuevos_perfumes} perfumes nuevos descubiertos | {precios_registrados} precios registrados.")
    # Retornamos el resultado procesado (reporte)
    return reporte


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Asignamos 'resultado' con ejecutar_descubrimiento_autonomo(limite_po...
    resultado = ejecutar_descubrimiento_autonomo(limite_por_tienda=15, paginas=1)
    # Ejecutamos instrucción: print('\n' + '=' * 60)
    print("\n" + "=" * 60)
    # Ejecutamos instrucción: print('RESUMEN DE DESCUBRIMIENTO AUTÓNOMO:')
    print("RESUMEN DE DESCUBRIMIENTO AUTÓNOMO:")
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
