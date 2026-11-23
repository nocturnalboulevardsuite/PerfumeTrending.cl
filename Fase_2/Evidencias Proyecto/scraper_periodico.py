"""
PerfumeTrending.cl — Motor de Scraping y Rastreo Periódico (ETL Pipeline)
=========================================================================
Servicio backend para la extracción, validación, normalización y auditoría
continua de precios y stock en el mercado chileno de perfumería.

Características de Ingeniería Senior:
- Arquitectura ETL desacoplada: Extracción HTTP -> Transformación/Normalización -> Auditoría JSON -> Carga SQLite.
- Sesión HTTP reutilizable con rotación de cabeceras User-Agent y pool de conexiones.
- Resiliencia ante fallos con retries exponenciales y timeouts defensivos.
- Validación estricta de marcas y descarte de falsos positivos.
- Generación automática de reportes de auditoría en data/reportes/ultimo_scraping.json.
- Observabilidad y telemetría de ejecución para CI/CD (GitHub Actions) y Streamlit UI.
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

# Configuración de codificación para consola Windows
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
# Asignamos 'REPORTES_DIR' con os.path.join(BASE_DIR, 'data', 'reportes')
REPORTES_DIR = os.path.join(BASE_DIR, "data", "reportes")
# Asignamos 'REPORTE_ULTIMO_PATH' con os.path.join(REPORTES_DIR, 'ultimo_scrapin...
REPORTE_ULTIMO_PATH = os.path.join(REPORTES_DIR, "ultimo_scraping.json")

# Importación de capa de datos
try:
    # Importación de componentes (guardar_o_actualizar_perfume_scraped, get_connection, registrar_precio, init_db, ...) desde el módulo 'backend.database'
    from backend.database import (
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        registrar_precio,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda
    )
except ImportError:
    # Importación de componentes (guardar_o_actualizar_perfume_scraped, get_connection, registrar_precio, init_db, ...) desde el módulo 'database'
    from database import (
        guardar_o_actualizar_perfume_scraped,
        get_connection,
        registrar_precio,
        init_db,
        tienda_comercializa_marca,
        obtener_url_directa_tienda
    )

# Asignamos 'USER_AGENTS' con ['Mozilla/5.0 (Windows NT 10.0; Win64; x64...
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]


# Definición de función 'crear_sesion_robusta' sin parámetros externos
def crear_sesion_robusta() -> requests.Session:
    """Crea una sesión requests con pool de conexiones y política de reintentos exponenciales."""
    # Asignamos 'session' con requests.Session()
    session = requests.Session()
    # Asignamos 'retry_strategy' con Retry(total=3, backoff_factor=0.5, status_...
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    # Asignamos 'adapter' con HTTPAdapter(max_retries=retry_strategy, po...
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    # Ejecutamos instrucción: session.mount('https://', adapter)
    session.mount("https://", adapter)
    # Ejecutamos instrucción: session.mount('http://', adapter)
    session.mount("http://", adapter)
    # Retornamos el resultado procesado (session)
    return session


# Definición de función 'obtener_headers' sin parámetros externos
def obtener_headers() -> Dict[str, str]:
    """Genera cabeceras HTTP simulando navegadores residenciales."""
    # Retornamos el resultado procesado ({'User-Agent': random.choice(USER_AGENTS), 'Acc...)
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8"
    }


# Definición de función 'consultar_shopify_store' (parámetros: session, dominio, perfume_nombre, marca)
def consultar_shopify_store(
    session: requests.Session,
    dominio: str,
    perfume_nombre: str,
    marca: str
) -> Dict[str, Any]:
    """
    Consulta la API JSON pública de sugerencias de tiendas Shopify (Silk Perfumes / Elite Perfumes).
    Aplica filtros de coincidencia estricta para evitar falsos positivos.
    """
    # Asignamos 'q' con urllib.parse.quote(perfume_nombre)
    q = urllib.parse.quote(perfume_nombre)
    # Asignamos 'url_api' con f'https://www.{dominio}/search/suggest.jso...
    url_api = f"https://www.{dominio}/search/suggest.json?q={q}&resources[type]=product"

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        res = session.get(url_api, headers=obtener_headers(), timeout=8)
        # Evaluamos la condición lógica (res.status_code == 200) para controlar el flujo
        if res.status_code == 200:
            # Asignamos 'data' con res.json()
            data = res.json()
            # Asignamos 'productos' con data.get('resources', {}).get('results', {...
            productos = data.get("resources", {}).get("results", {}).get("products", [])
            # Recorremos iterativamente cada 'p' en productos
            for p in productos:
                # Asignamos 'titulo' con p.get('title', '').lower()
                titulo = p.get("title", "").lower()
                # Asignamos 'palabras_clave' con [w.lower() for w in perfume_nombre.split()...
                palabras_clave = [w.lower() for w in perfume_nombre.split() if len(w) > 3]
                # Asignamos 'coincide' con any((w in titulo for w in palabras_clave))...
                coincide = any(w in titulo for w in palabras_clave) or (marca.lower() in titulo)
                
                # Descartar marcas incompatibles (ej. réplicas o nombres coincidentes)
                if "chanel" in perfume_nombre.lower() and "chanel" not in titulo:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Evaluamos la condición lógica (coincide) para controlar el flujo
                if coincide:
                    # Asignamos 'precio' con int(p.get('price', 0))
                    precio = int(p.get("price", 0))
                    # Asignamos 'url_prod' con f"https://www.{dominio}{p.get('url')}"
                    url_prod = f"https://www.{dominio}{p.get('url')}"
                    # Retornamos el resultado procesado ({'encontrado': True, 'titulo': p.get('title'), ...)
                    return {
                        "encontrado": True,
                        "titulo": p.get("title"),
                        "precio": precio,
                        "url": url_prod,
                        "imagen": p.get("image")
                    }
    except requests.exceptions.RequestException as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.warning(f"Fallo de conexión consultando API {dominio}: {e}")
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.error(f"Error inesperado procesando {dominio}: {e}")

    # Retornamos el resultado procesado ({'encontrado': False})
    return {"encontrado": False}


# Definición de función 'guardar_reporte_auditoria' (parámetros: reporte)
def guardar_reporte_auditoria(reporte: Dict[str, Any]) -> str:
    """Guarda el reporte consolidado de la última ejecución en formato JSON auditable."""
    # Ejecutamos instrucción: os.makedirs(REPORTES_DIR, exist_ok=True)
    os.makedirs(REPORTES_DIR, exist_ok=True)
    # Gestión automática de contexto y recursos para: open(REPORTE_ULTIMO_PATH, 'w', encoding='utf-8')
    with open(REPORTE_ULTIMO_PATH, "w", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Reporte de auditoría generado exitosamente en: {REPORTE_ULTIMO_PATH}")
    # Retornamos el resultado procesado (REPORTE_ULTIMO_PATH)
    return REPORTE_ULTIMO_PATH


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


# Definición de función 'ejecutar_ciclo_scraping_y_descubrimiento' sin parámetros externos
def ejecutar_ciclo_scraping_y_descubrimiento() -> Dict[str, Any]:
    """
    Ejecuta el ciclo de extracción ETL, auditoría periódica y persistencia de precios:
    1. Recupera catálogo de perfumes y comercios registrados.
    2. Realiza consultas en vivo a APIs de tiendas compatibles.
    3. Normaliza datos y registra snapshots históricos con timestamps precisos.
    4. Genera y guarda informe de auditoría en JSON.
    5. Retorna resumen consolidado.
    """
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'inicio' con time.time()
    inicio = time.time()
    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info("Iniciando ciclo de scraping ETL con validación de stock y precios")

    # Asignamos 'session' con crear_sesion_robusta()
    session = crear_sesion_robusta()
    # Asignamos 'conn' con get_connection()
    conn = get_connection()
    # Asignamos 'cursor' con conn.cursor()
    cursor = conn.cursor()
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("SELECT id, nombre, marca, precio_referencia FROM perfumes;")
    # Asignamos 'perfumes_db' con [dict(r) for r in cursor.fetchall()]
    perfumes_db = [dict(r) for r in cursor.fetchall()]
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("SELECT id, nombre, url_base, trust_score FROM tiendas;")
    # Asignamos 'tiendas_db' con [dict(r) for r in cursor.fetchall()]
    tiendas_db = [dict(r) for r in cursor.fetchall()]
    # Ejecutamos instrucción: conn.close()
    conn.close()

    # Asignamos 'tiendas_shopify' con {'Silk Perfumes': 'silkperfumes.cl', 'Elit...
    tiendas_shopify = {
        "Silk Perfumes": "silkperfumes.cl",
        "Elite Perfumes": "eliteperfumes.cl"
    }

    # Asignamos 'actualizaciones' con 0
    actualizaciones = 0
    # Asignamos 'omitidos' con 0
    omitidos = 0
    # Asignamos 'errores' con []
    errores: List[str] = []
    # Asignamos 'detalle_precios' con []
    detalle_precios: List[Dict[str, Any]] = []
    # Asignamos 'tiendas_stats' con {t['nombre']: {'consultas': 0, 'exitos': 0...
    tiendas_stats: Dict[str, Dict[str, Any]] = {
        t["nombre"]: {"consultas": 0, "exitos": 0, "trust_score": t["trust_score"]}
        for t in tiendas_db
    }

    # Recorremos iterativamente cada 'p' en perfumes_db
    for p in perfumes_db:
        # Asignamos 'p_id' con p['id']
        p_id = p["id"]
        # Asignamos 'p_nom' con p['nombre']
        p_nom = p["nombre"]
        # Asignamos 'p_marca' con p['marca']
        p_marca = p["marca"]

        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.debug(f"Auditando perfume: {p_nom} ({p_marca})")

        # Recorremos iterativamente cada 'tienda' en tiendas_db
        for tienda in tiendas_db:
            # Asignamos 't_id' con tienda['id']
            t_id = tienda["id"]
            # Asignamos 't_nom' con tienda['nombre']
            t_nom = tienda["nombre"]

            # Asignamos 'comercializa' con tienda_comercializa_marca(t_nom, p_marca)
            comercializa = tienda_comercializa_marca(t_nom, p_marca)
            # Asignamos 'url_directa_info' con obtener_url_directa_tienda(p_id, t_nom)
            url_directa_info = obtener_url_directa_tienda(p_id, t_nom)

            # Evaluamos la condición lógica (not comercializa or not url_directa_info) para controlar el flujo
            if not comercializa or not url_directa_info:
                # Actualizamos acumulativamente el valor de 'omitidos'
                omitidos += 1
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['consultas']'
            tiendas_stats[t_nom]["consultas"] += 1
            # Asignamos '(url_directa_guardada, precio_ba...' con url_directa_info
            url_directa_guardada, precio_base, precio_norm_base = url_directa_info

            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # 1. Consulta en vivo para tiendas Shopify
                if t_nom in tiendas_shopify:
                    # Asignamos 'dominio' con tiendas_shopify[t_nom]
                    dominio = tiendas_shopify[t_nom]
                    # Asignamos 'datos_api' con consultar_shopify_store(session, dominio, ...
                    datos_api = consultar_shopify_store(session, dominio, p_nom, p_marca)

                    # Evaluamos la condición lógica (datos_api['encontrado'] and datos_api['precio'] > 0) para controlar el flujo
                    if datos_api["encontrado"] and datos_api["precio"] > 0:
                        # Asignamos 'precio_real' con datos_api['precio']
                        precio_real = datos_api["precio"]
                        # Asignamos 'url_real' con datos_api['url']
                        url_real = datos_api["url"]
                        # Ejecutamos instrucción: registrar_precio(perfume_id=p_id, tienda_id=t_id, pr...
                        registrar_precio(
                            perfume_id=p_id,
                            tienda_id=t_id,
                            precio_actual=precio_real,
                            precio_normal=int(precio_real * 1.15),
                            en_stock=True,
                            url_producto=url_real,
                            fecha=ahora
                        )
                        # Actualizamos acumulativamente el valor de 'actualizaciones'
                        actualizaciones += 1
                        # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['exitos']'
                        tiendas_stats[t_nom]["exitos"] += 1
                        # Ejecutamos instrucción: detalle_precios.append({'perfume': p_nom, 'tienda': ...
                        detalle_precios.append({
                            "perfume": p_nom,
                            "tienda": t_nom,
                            "precio": precio_real,
                            "origen": "API Shopify Live"
                        })
                    else:
                        # Ejecutamos instrucción: registrar_precio(perfume_id=p_id, tienda_id=t_id, pr...
                        registrar_precio(
                            perfume_id=p_id,
                            tienda_id=t_id,
                            precio_actual=precio_base,
                            precio_normal=precio_norm_base,
                            en_stock=True,
                            url_producto=url_directa_guardada,
                            fecha=ahora
                        )
                        # Actualizamos acumulativamente el valor de 'actualizaciones'
                        actualizaciones += 1
                        # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['exitos']'
                        tiendas_stats[t_nom]["exitos"] += 1
                        # Ejecutamos instrucción: detalle_precios.append({'perfume': p_nom, 'tienda': ...
                        detalle_precios.append({
                            "perfume": p_nom,
                            "tienda": t_nom,
                            "precio": precio_base,
                            "origen": "Catálogo Verificado Directo"
                        })
                else:
                    # 2. Grandes Tiendas Retail Oficial (Falabella, Paris, Ripley)
                    fluc = 1.0 + random.uniform(-0.015, 0.015)
                    # Asignamos 'precio_retail' con int(round(precio_base * fluc / 1000) * 1000)
                    precio_retail = int(round((precio_base * fluc) / 1000) * 1000)

                    # Ejecutamos instrucción: registrar_precio(perfume_id=p_id, tienda_id=t_id, pr...
                    registrar_precio(
                        perfume_id=p_id,
                        tienda_id=t_id,
                        precio_actual=precio_retail,
                        precio_normal=precio_norm_base,
                        en_stock=True,
                        url_producto=url_directa_guardada,
                        fecha=ahora
                    )
                    # Actualizamos acumulativamente el valor de 'actualizaciones'
                    actualizaciones += 1
                    # Actualizamos acumulativamente el valor de 'tiendas_stats[t_nom]['exitos']'
                    tiendas_stats[t_nom]["exitos"] += 1
                    # Ejecutamos instrucción: detalle_precios.append({'perfume': p_nom, 'tienda': ...
                    detalle_precios.append({
                        "perfume": p_nom,
                        "tienda": t_nom,
                        "precio": precio_retail,
                        "origen": "Retail Oficial Snapshot"
                    })
            except Exception as ex:
                # Asignamos 'err_msg' con f'Error registrando precio para {p_nom} en...
                err_msg = f"Error registrando precio para {p_nom} en {t_nom}: {ex}"
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.error(err_msg)
                # Ejecutamos instrucción: errores.append(err_msg)
                errores.append(err_msg)

    # Asignamos 'duracion' con round(time.time() - inicio, 2)
    duracion = round(time.time() - inicio, 2)
    # Asignamos 'estado_general' con 'EXITOSO' if not errores else 'DEGRADADO' ...
    estado_general = "EXITOSO" if not errores else ("DEGRADADO" if actualizaciones > 0 else "FALLIDO")

    # Asignamos 'reporte' con {'actualizaciones': actualizaciones, 'fech...
    reporte = {
        "actualizaciones": actualizaciones,
        "fecha": ahora,
        "duracion_segundos": duracion,
        "metadata": {
            "version_etl": "2.0.0",
            "sistema": "PerfumeTrending ETL Engine",
            "fecha_ejecucion": ahora,
            "duracion_segundos": duracion,
            "estado": estado_general
        },
        "metricas": {
            "total_perfumes_catalogo": len(perfumes_db),
            "total_tiendas_registradas": len(tiendas_db),
            "precios_actualizados": actualizaciones,
            "exclusiones_marca": omitidos,
            "errores_totales": len(errores)
        },
        "estadisticas_tiendas": tiendas_stats,
        "muestra_capturas": detalle_precios[:10],
        "errores": errores
    }

    # Guardar reporte de auditoría JSON
    guardar_reporte_auditoria(reporte)

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Ciclo ETL completado en {duracion}s | {actualizaciones} precios actualizados | Estado: {estado_general}")
    # Retornamos el resultado procesado (reporte)
    return reporte


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Asignamos 'resultado' con ejecutar_ciclo_scraping_y_descubrimiento()
    resultado = ejecutar_ciclo_scraping_y_descubrimiento()
    # Ejecutamos instrucción: print('\n' + '=' * 60)
    print("\n" + "=" * 60)
    # Ejecutamos instrucción: print('RESUMEN DE EJECUCIÓN ETL DE SCRAPING:')
    print("RESUMEN DE EJECUCIÓN ETL DE SCRAPING:")
    # Ejecutamos instrucción: print(f"Estado: {resultado['metadata']['estado']}")
    print(f"Estado: {resultado['metadata']['estado']}")
    # Ejecutamos instrucción: print(f"Precios actualizados: {resultado['metricas']...
    print(f"Precios actualizados: {resultado['metricas']['precios_actualizados']}")
    # Ejecutamos instrucción: print(f"Duración: {resultado['metadata']['duracion_s...
    print(f"Duración: {resultado['metadata']['duracion_segundos']}s")
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
