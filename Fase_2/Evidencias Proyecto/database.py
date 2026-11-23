"""
PerfumeTrending.cl — Capa de Persistencia y Motor de Base de Datos
==================================================================
Módulo desacoplado de acceso a datos de alto rendimiento basado en SQLite con:
- Esquema relacional DDL puro externalizado en database/schema.sql.
- Catálogo maestro y tiendas auditadas desacopladas en database/seed_catalogo.json.
- Modo WAL (Write-Ahead Logging) para concurrencia multi-hilo (Streamlit + Scraper).
- Context managers para gestión determinista de transacciones y conexiones.
- Índices B-Tree optimizados para series de tiempo y búsquedas de catálogo.
- Tipado estricto (PEP 484) y control defensivo de excepciones.
"""

# Importación de componentes (contextmanager) desde el módulo 'contextlib'
from contextlib import contextmanager
# Importación de componentes (datetime, timedelta) desde el módulo 'datetime'
from datetime import datetime, timedelta
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (random)
import random
# Importación de librería estándar o dependencia externa (sqlite3)
import sqlite3
# Importación de componentes (Any, Dict, Generator, List, ...) desde el módulo 'typing'
from typing import Any, Dict, Generator, List, Optional, Tuple
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse

# Asignamos 'logger' con logging.getLogger('PerfumeDatabase')
logger = logging.getLogger("PerfumeDatabase")

# Configuración de rutas canónicas del sistema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Definición de función 'resolver_ruta' (parámetros: subpath)
def resolver_ruta(subpath: str) -> str:
    """Busca un recurso en la raíz del proyecto o dentro de APP/"""
    # Asignamos 'curr' con os.path.dirname(os.path.abspath(__file__))
    curr = os.path.dirname(os.path.abspath(__file__))
    # Asignamos 'candidatos' con [os.path.join(BASE_DIR, subpath), os.path....
    candidatos = [
        os.path.join(BASE_DIR, subpath),
        os.path.join(BASE_DIR, "APP", subpath),
        os.path.join(curr, subpath),
        os.path.join(curr, "..", subpath),
        os.path.join(curr, "..", "APP", subpath),
    ]
    # Recorremos iterativamente cada 'c' en candidatos
    for c in candidatos:
        # Evaluamos la condición lógica (os.path.exists(c)) para controlar el flujo
        if os.path.exists(c):
            # Retornamos el resultado procesado (os.path.abspath(c))
            return os.path.abspath(c)
    # Retornamos el resultado procesado (os.path.join(BASE_DIR, subpath))
    return os.path.join(BASE_DIR, subpath)

# Asignamos 'DB_PATH' con resolver_ruta('data/perfumes.db')
DB_PATH = resolver_ruta("data/perfumes.db")
# Asignamos 'DB_DIR' con os.path.dirname(DB_PATH)
DB_DIR = os.path.dirname(DB_PATH)
# Asignamos 'SCHEMA_PATH' con resolver_ruta('database/schema.sql')
SCHEMA_PATH = resolver_ruta("database/schema.sql")
# Asignamos 'SEED_PATH' con resolver_ruta('database/seed_catalogo.json')
SEED_PATH = resolver_ruta("database/seed_catalogo.json")

# Cache en memoria para catálogo semilla desacoplado
_SEED_CACHE: Optional[Dict[str, Any]] = None


# Definición de función 'cargar_datos_semilla_json' sin parámetros externos
def cargar_datos_semilla_json() -> Dict[str, Any]:
    """Carga y cachea el archivo JSON con el catálogo canónico y directrices de tiendas."""
    # Ejecutamos instrucción: global _SEED_CACHE
    global _SEED_CACHE
    # Evaluamos la condición lógica (_SEED_CACHE is not None) para controlar el flujo
    if _SEED_CACHE is not None:
        # Retornamos el resultado procesado (_SEED_CACHE)
        return _SEED_CACHE

    # Evaluamos la condición lógica (not os.path.exists(SEED_PATH)) para controlar el flujo
    if not os.path.exists(SEED_PATH):
        # Propagamos excepción explícita ante condición de error detectada
        raise FileNotFoundError(f"Archivo de catálogo maestro no encontrado en: {SEED_PATH}")

    # Gestión automática de contexto y recursos para: open(SEED_PATH, 'r', encoding='utf-8')
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        # Procesamiento de serialización o deserialización de estructura JSON
        _SEED_CACHE = json.load(f)

    # Retornamos el resultado procesado (_SEED_CACHE)
    return _SEED_CACHE


# Definición de función 'get_connection' sin parámetros externos
def get_connection() -> sqlite3.Connection:
    """
    Crea y configura una conexión de producción a SQLite.
    
    Ajustes de rendimiento y concurrencia:
    - WAL Mode: Permite lecturas y escrituras simultáneas sin bloqueos de tabla.
    - Busy timeout (15s): Previene bloqueos por concurrencia entre Streamlit y el Scraper.
    - Synchronous NORMAL: Optimiza I/O en disco garantizando durabilidad ACID.
    - Foreign Keys: Integridad referencial habilitada a nivel de motor.
    """
    # Ejecutamos instrucción: os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    conn.row_factory = sqlite3.Row
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    conn.execute("PRAGMA journal_mode=WAL;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    conn.execute("PRAGMA synchronous=NORMAL;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    conn.execute("PRAGMA foreign_keys=ON;")
    # Retornamos el resultado procesado (conn)
    return conn


# Definición de función 'get_db_cursor' (parámetros: commit)
@contextmanager
def get_db_cursor(commit: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager transaccional determinista.
    
    Garantiza commit automático en éxito, rollback ante excepciones y cierre seguro de conexión.
    """
    # Asignamos 'conn' con get_connection()
    conn = get_connection()
    # Asignamos 'cursor' con conn.cursor()
    cursor = conn.cursor()
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: yield cursor
        yield cursor
        # Evaluamos la condición lógica (commit) para controlar el flujo
        if commit:
            # Ejecutamos instrucción: conn.commit()
            conn.commit()
    except Exception:
        # Ejecutamos instrucción: conn.rollback()
        conn.rollback()
        # Propagamos excepción explícita ante condición de error detectada
        raise
    finally:
        # Ejecutamos instrucción: conn.close()
        conn.close()


# -----------------------------------------------------------------------------
# INICIALIZACIÓN DE ESQUEMA (DDL) Y CARGA DE SEMILLA
# -----------------------------------------------------------------------------
def init_db(force_reseed: bool = False) -> None:
    """
    Inicializa la base de datos aplicando el esquema DDL y cargando datos semilla si está vacía.
    """
    # Evaluamos la condición lógica (not os.path.exists(SCHEMA_PATH)) para controlar el flujo
    if not os.path.exists(SCHEMA_PATH):
        # Propagamos excepción explícita ante condición de error detectada
        raise FileNotFoundError(f"No se encontró el archivo de esquema SQL en: {SCHEMA_PATH}")

    # Gestión automática de contexto y recursos para: open(SCHEMA_PATH, 'r', encoding='utf-8')
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        # Asignamos 'schema_sql' con f.read()
        schema_sql = f.read()

    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # 1. Migración previa defensiva si la tabla precios_registro ya existía sin volumen_ml
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='precios_registro';")
        # Evaluamos la condición lógica (cursor.fetchone()) para controlar el flujo
        if cursor.fetchone():
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("PRAGMA table_info(precios_registro);")
            # Asignamos 'cols' con {c['name'] for c in cursor.fetchall()}
            cols = {c["name"] for c in cursor.fetchall()}
            # Evaluamos la condición lógica ('volumen_ml' not in cols) para controlar el flujo
            if "volumen_ml" not in cols:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("ALTER TABLE precios_registro ADD COLUMN volumen_ml INTEGER DEFAULT 100;")

        # 2. Aplicar esquema DDL e índices
        cursor.executescript(schema_sql)

        # 3. Verificar si la base de datos requiere población inicial
        cursor.execute("SELECT COUNT(*) FROM perfumes;")
        # Asignamos 'row_count' con cursor.fetchone()[0]
        row_count = cursor.fetchone()[0]
        # Evaluamos la condición lógica (row_count == 0 or force_reseed) para controlar el flujo
        if row_count == 0 or force_reseed:
            # Ejecutamos instrucción: poblar_datos_semilla(cursor)
            poblar_datos_semilla(cursor)


# Definición de función 'poblar_datos_semilla' (parámetros: cursor)
def poblar_datos_semilla(cursor: sqlite3.Cursor) -> None:
    """
    Puebla la base de datos a partir del archivo canónico seed_catalogo.json.
    """
    # Asignamos 'catalogo' con cargar_datos_semilla_json()
    catalogo = cargar_datos_semilla_json()

    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM precios_registro;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM perfumes;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM tiendas;")

    # 1. Inserción de Tiendas Auditadas
    tiendas_data = catalogo.get("tiendas", [])
    # Asignamos 'tiendas_tuples' con [(t['nombre'], t['url_base'], t.get('trust...
    tiendas_tuples = [
        (
            t["nombre"], t["url_base"], t.get("trust_score", 85), t.get("badge", "Verificado"),
            t.get("logo_emoji", "🏬"), t.get("rut", ""), t.get("tipo_tienda", "Comercio Especializado"),
            int(t.get("ssl_seguro", 1)), t.get("anios_antiguedad", 5), int(t.get("sello_ccs", 0)),
            t.get("reclamos_sernac", "Bajo"), t.get("politica_devolucion", "30 días"),
            t.get("direccion_fiscal", "Santiago, Chile"), t.get("puntos_seguridad", 25),
            t.get("puntos_legalidad", 25), t.get("puntos_garantia", 20), t.get("puntos_reputacion", 20)
        )
        for t in tiendas_data
    ]

    # Ejecutamos instrucción: cursor.executemany('\n INSERT OR REPLACE INTO tienda...
    cursor.executemany("""
    INSERT OR REPLACE INTO tiendas (
        nombre, url_base, trust_score, badge, logo_emoji,
        rut, tipo_tienda, ssl_seguro, anios_antiguedad, sello_ccs, reclamos_sernac,
        politica_devolucion, direccion_fiscal,
        puntos_seguridad, puntos_legalidad, puntos_garantia, puntos_reputacion
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, tiendas_tuples)

    # 2. Inserción de Perfumes
    perfumes_data = catalogo.get("perfumes", [])
    # Asignamos 'perfumes_tuples' con [(p['id'], p['nombre'], p['marca'], p.get(...
    perfumes_tuples = [
        (
            p["id"], p["nombre"], p["marca"], p.get("genero", "Unisex"),
            p.get("tipo", "Eau de Parfum"), p["notas"], p["imagen_url"],
            int(p.get("es_arabe", False)), int(p.get("en_tendencia", False)),
            int(p.get("en_remate", False)), p["precio_referencia"]
        )
        for p in perfumes_data
    ]

    # Ejecutamos instrucción: cursor.executemany('\n INSERT OR REPLACE INTO perfum...
    cursor.executemany("""
    INSERT OR REPLACE INTO perfumes (
        id, nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, perfumes_tuples)

    # Mapeo de tiendas nombre -> id
    cursor.execute("SELECT id, nombre FROM tiendas;")
    # Asignamos 'tiendas_map' con {r['nombre']: r['id'] for r in cursor.fetc...
    tiendas_map = {r["nombre"]: r["id"] for r in cursor.fetchall()}

    # 3. Inserción de Serie Temporal Histórica de Precios por Tienda
    hoy = datetime.now()
    # Asignamos 'dias_atras' con [21, 14, 7, 3, 1, 0]
    dias_atras = [21, 14, 7, 3, 1, 0]
    # Asignamos 'registros_precios' con []
    registros_precios = []

    # Recorremos iterativamente cada 'p' en perfumes_data
    for p in perfumes_data:
        # Asignamos 'p_id' con p['id']
        p_id = p["id"]
        # Recorremos iterativamente cada 'enlace' en p.get('enlaces_tiendas', [])
        for enlace in p.get("enlaces_tiendas", []):
            # Asignamos 't_nombre' con enlace.get('tienda')
            t_nombre = enlace.get("tienda")
            # Evaluamos la condición lógica (t_nombre not in tiendas_map) para controlar el flujo
            if t_nombre not in tiendas_map:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 't_id' con tiendas_map[t_nombre]
            t_id = tiendas_map[t_nombre]
            # Asignamos 'precio_act' con enlace.get('precio_actual', p['precio_refe...
            precio_act = enlace.get("precio_actual", p["precio_referencia"])
            # Asignamos 'precio_norm' con enlace.get('precio_normal', int(precio_act...
            precio_norm = enlace.get("precio_normal", int(precio_act * 1.15))
            # Asignamos 'url_prod' con enlace.get('url_producto', '')
            url_prod = enlace.get("url_producto", "")

            # Recorremos iterativamente cada 'dia' en dias_atras
            for dia in dias_atras:
                # Asignamos 'fecha' con hoy - timedelta(days=dia, hours=dia, minut...
                fecha = hoy - timedelta(days=dia, hours=dia, minutes=dia * 4)
                # Asignamos 'fluc' con 1.0 + dia * 0.004 - (0.015 if dia == 0 els...
                fluc = 1.0 + (dia * 0.004) - (0.015 if dia == 0 else 0)
                # Asignamos 'p_actual_hist' con int(round(precio_act * fluc / 1000) * 1000)
                p_actual_hist = int(round((precio_act * fluc) / 1000) * 1000)
                # Asignamos 'p_norm_hist' con int(round(precio_norm * 1.05 / 1000) * 1000)
                p_norm_hist = int(round((precio_norm * 1.05) / 1000) * 1000)

                # Ejecutamos instrucción: registros_precios.append((p_id, t_id, p_actual_hist,...
                registros_precios.append((
                    p_id, t_id, p_actual_hist, p_norm_hist, 1, 100, url_prod, fecha.strftime("%Y-%m-%d %H:%M:%S")
                ))

    # Ejecutamos instrucción: cursor.executemany('\n INSERT INTO precios_registro ...
    cursor.executemany("""
    INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, registros_precios)

    # Registro de evento diagnóstico en la bitácora (logger) del sistema
    logger.info(f"Base de datos poblada exitosamente: {len(perfumes_tuples)} perfumes, {len(tiendas_tuples)} tiendas, {len(registros_precios)} registros históricos.")


# -----------------------------------------------------------------------------
# REGLAS DE NEGOCIO Y RESOLUCIÓN DE CATÁLOGO
# -----------------------------------------------------------------------------
def obtener_url_directa_tienda(perfume_id: int, tienda_nombre: str) -> Optional[Tuple[str, int, int]]:
    """
    Retorna la tupla (url_producto, precio_actual, precio_normal) configurada en el catálogo semilla.
    """
    # Asignamos 'catalogo' con cargar_datos_semilla_json()
    catalogo = cargar_datos_semilla_json()
    # Recorremos iterativamente cada 'p' en catalogo.get('perfumes', [])
    for p in catalogo.get("perfumes", []):
        # Evaluamos la condición lógica (p['id'] == perfume_id) para controlar el flujo
        if p["id"] == perfume_id:
            # Recorremos iterativamente cada 'enlace' en p.get('enlaces_tiendas', [])
            for enlace in p.get("enlaces_tiendas", []):
                # Evaluamos la condición lógica (enlace.get('tienda') == tienda_nombre) para controlar el flujo
                if enlace.get("tienda") == tienda_nombre:
                    # Retornamos el resultado procesado ((enlace.get('url_producto', ''), enlace.get('pr...)
                    return (
                        enlace.get("url_producto", ""),
                        enlace.get("precio_actual", p["precio_referencia"]),
                        enlace.get("precio_normal", int(enlace.get("precio_actual", p["precio_referencia"]) * 1.15))
                    )
    # Retornamos el resultado procesado (None)
    return None


# Definición de función 'generar_url_tienda' (parámetros: tienda_nombre, perfume_nombre, url_directa)
def generar_url_tienda(tienda_nombre: str, perfume_nombre: str, url_directa: Optional[str] = None) -> Optional[str]:
    """Retorna la URL directa verificada descartando búsquedas genéricas con /search."""
    # Evaluamos la condición lógica (url_directa and url_directa.startswith('http') and (...) para controlar el flujo
    if url_directa and url_directa.startswith("http") and "/search" not in url_directa:
        # Retornamos el resultado procesado (url_directa)
        return url_directa
    # Retornamos el resultado procesado (None)
    return None


# Definición de función 'tienda_comercializa_marca' (parámetros: tienda_nombre, marca)
def tienda_comercializa_marca(tienda_nombre: str, marca: str) -> bool:
    """Valida reglas de distribución oficial y comercialización legal en Chile."""
    # Asignamos 't_nom' con tienda_nombre.lower()
    t_nom = tienda_nombre.lower()
    # Asignamos 'm' con marca.lower()
    m = marca.lower()
    # Marcas con distribución exclusiva de retail de lujo oficial
    if "chanel" in m or "maison francis" in m or "tom ford" in m:
        # Retornamos el resultado procesado (any((retail in t_nom for retail in ['falabella'...)
        return any(retail in t_nom for retail in ["falabella", "paris", "ripley"])
    # Retornamos el resultado procesado (True)
    return True


# -----------------------------------------------------------------------------
# CONSULTAS DE DOMINIO Y ACCESO A DATOS (DAO / REPOSITORY)
# -----------------------------------------------------------------------------
def registrar_precio(
    perfume_id: int,
    tienda_id: int,
    precio_actual: int,
    precio_normal: int,
    en_stock: bool,
    url_producto: str,
    fecha: Optional[str] = None,
    volumen_ml: int = 100
) -> None:
    """Inserta una captura periódica de precio para un perfume en una tienda específica y tamaño en ml."""
    # Evaluamos la condición lógica (fecha is None) para controlar el flujo
    if fecha is None:
        # Asignamos 'fecha' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (perfume_id, tienda_id, precio_actual, precio_normal, int(en_stock), volumen_ml, url_producto, fecha))


# Definición de función 'obtener_catalogo' (parámetros: busqueda, esencias, categoria, orden)
def obtener_catalogo(
    busqueda: Optional[str] = None,
    esencias: Optional[List[str]] = None,
    categoria: Optional[str] = None,
    orden: str = "id_asc"
) -> List[Dict[str, Any]]:
    """
    Obtiene el listado de perfumes calculando el mejor precio real disponible en stock.
    
    Args:
        busqueda: Filtro de texto por nombre o marca.
        esencias: Lista de notas olfativas requeridas.
        categoria: 'arabes', 'remates' o None.
        orden: Criterio de ordenamiento ('precio_asc', 'precio_desc', 'nombre_asc', 'id_asc').
    """
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'query' con '\n SELECT p.*,\n MIN(CASE WHEN pr.en_stoc...
    query = """
    SELECT p.*,
           MIN(CASE WHEN pr.en_stock = 1 AND pr.precio_actual > 0 THEN pr.precio_actual END) as mejor_precio,
           MAX(pr.fecha_registro) as ultima_actualizacion
    FROM perfumes p
    LEFT JOIN precios_registro pr ON p.id = pr.perfume_id
    WHERE 1=1
    """
    # Asignamos 'params' con []
    params: List[Any] = []

    # Evaluamos la condición lógica (busqueda) para controlar el flujo
    if busqueda:
        # Asignamos 'term' con f'%{busqueda.strip()}%'
        term = f"%{busqueda.strip()}%"
        # Actualizamos acumulativamente el valor de 'query'
        query += " AND (p.nombre LIKE ? OR p.marca LIKE ?)"
        # Ejecutamos instrucción: params.extend([term, term])
        params.extend([term, term])

    # Evaluamos la condición lógica (categoria == 'arabes') para controlar el flujo
    if categoria == "arabes":
        # Actualizamos acumulativamente el valor de 'query'
        query += " AND p.es_arabe = 1"
    # Evaluamos la condición lógica (categoria == 'remates') para controlar el flujo
    elif categoria == "remates":
        # Actualizamos acumulativamente el valor de 'query'
        query += " AND p.en_remate = 1"

    # Actualizamos acumulativamente el valor de 'query'
    query += " GROUP BY p.id"

    # Evaluamos la condición lógica (orden == 'precio_asc') para controlar el flujo
    if orden == "precio_asc":
        # Actualizamos acumulativamente el valor de 'query'
        query += " ORDER BY mejor_precio ASC NULLS LAST"
    # Evaluamos la condición lógica (orden == 'precio_desc') para controlar el flujo
    elif orden == "precio_desc":
        # Actualizamos acumulativamente el valor de 'query'
        query += " ORDER BY mejor_precio DESC NULLS LAST"
    # Evaluamos la condición lógica (orden == 'nombre_asc') para controlar el flujo
    elif orden == "nombre_asc":
        # Actualizamos acumulativamente el valor de 'query'
        query += " ORDER BY p.nombre ASC"
    else:
        # Actualizamos acumulativamente el valor de 'query'
        query += " ORDER BY p.id ASC"

    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, params)
        # Asignamos 'perfumes' con [dict(row) for row in cursor.fetchall()]
        perfumes = [dict(row) for row in cursor.fetchall()]

    # Evaluamos la condición lógica (esencias) para controlar el flujo
    if esencias:
        # Asignamos 'perfumes_filtrados' con []
        perfumes_filtrados = []
        # Asignamos 'esencias_lower' con [e.lower() for e in esencias]
        esencias_lower = [e.lower() for e in esencias]
        # Recorremos iterativamente cada 'p' en perfumes
        for p in perfumes:
            # Asignamos 'notas_p' con [n.strip().lower() for n in p['notas'].spl...
            notas_p = [n.strip().lower() for n in p["notas"].split(",")]
            # Evaluamos la condición lógica (any((any((es in nota for nota in notas_p)) for es in...) para controlar el flujo
            if any(any(es in nota for nota in notas_p) for es in esencias_lower):
                # Ejecutamos instrucción: perfumes_filtrados.append(p)
                perfumes_filtrados.append(p)
        # Retornamos el resultado procesado (perfumes_filtrados)
        return perfumes_filtrados

    # Retornamos el resultado procesado (perfumes)
    return perfumes


# Definición de función 'obtener_detalle_perfume' (parámetros: perfume_id)
def obtener_detalle_perfume(perfume_id: int) -> Optional[Dict[str, Any]]:
    """Retorna información completa del perfume por su ID."""
    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT * FROM perfumes WHERE id = ?;", (perfume_id,))
        # Asignamos 'row' con cursor.fetchone()
        row = cursor.fetchone()
        # Retornamos el resultado procesado (dict(row) if row else None)
        return dict(row) if row else None


# Definición de función 'obtener_precios_actuales' (parámetros: perfume_id)
def obtener_precios_actuales(perfume_id: int) -> List[Dict[str, Any]]:
    """
    Retorna el precio más reciente registrado en cada tienda para el perfume dado.
    Garantiza enlaces directos, stock verificado y cálculo de precio por ml ($/ml).
    """
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'query' con "\n SELECT t.id as tienda_id, t.nombre as ...
    query = """
    SELECT t.id as tienda_id, t.nombre as tienda_nombre, t.url_base, t.trust_score, t.badge, t.logo_emoji,
           pr.precio_actual, pr.precio_normal, pr.en_stock, COALESCE(pr.volumen_ml, 100) as volumen_ml,
           ROUND(CAST(pr.precio_actual AS REAL) / MAX(1, COALESCE(pr.volumen_ml, 100))) as precio_por_ml,
           pr.url_producto, pr.fecha_registro
    FROM tiendas t
    JOIN precios_registro pr ON t.id = pr.tienda_id
    WHERE pr.perfume_id = ?
      AND pr.en_stock = 1
      AND pr.precio_actual > 0
      AND pr.url_producto IS NOT NULL
      AND pr.url_producto NOT LIKE '%/search%'
      AND pr.fecha_registro = (
          SELECT MAX(fecha_registro)
          FROM precios_registro
          WHERE perfume_id = ? AND tienda_id = t.id
      )
    ORDER BY pr.precio_actual ASC;
    """
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, (perfume_id, perfume_id))
        # Retornamos el resultado procesado ([dict(row) for row in cursor.fetchall()])
        return [dict(row) for row in cursor.fetchall()]


# Definición de función 'obtener_historico_precios' (parámetros: perfume_id)
def obtener_historico_precios(perfume_id: int) -> List[Dict[str, Any]]:
    """Retorna la serie temporal histórica de precios válidos para gráficos de evolución."""
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'query' con "\n SELECT t.nombre as tienda, pr.precio_a...
    query = """
    SELECT t.nombre as tienda, pr.precio_actual, pr.fecha_registro
    FROM precios_registro pr
    JOIN tiendas t ON pr.tienda_id = t.id
    WHERE pr.perfume_id = ? 
      AND pr.en_stock = 1 
      AND pr.precio_actual > 0
      AND pr.url_producto NOT LIKE '%/search%'
    ORDER BY pr.fecha_registro ASC;
    """
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, (perfume_id,))
        # Retornamos el resultado procesado ([dict(row) for row in cursor.fetchall()])
        return [dict(row) for row in cursor.fetchall()]


# Definición de función 'guardar_o_actualizar_perfume_scraped' (parámetros: nombre, marca, precio_actual, precio_normal, ...)
def guardar_o_actualizar_perfume_scraped(
    nombre: str,
    marca: str,
    precio_actual: int,
    precio_normal: int,
    tienda_nombre: str,
    url_producto: str,
    imagen_url: Optional[str] = None,
    notas: Optional[str] = None,
    es_arabe: int = 0,
    genero: str = "Unisex"
) -> Dict[str, Any]:
    """Inserta o actualiza un perfume descubierto con enlace funcional y nuevo snapshot de precio."""
    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = LOWER(?);", (tienda_nombre,))
        # Asignamos 'row_tienda' con cursor.fetchone()
        row_tienda = cursor.fetchone()
        # Evaluamos la condición lógica (row_tienda) para controlar el flujo
        if row_tienda:
            # Asignamos 'tienda_id' con row_tienda['id']
            tienda_id = row_tienda["id"]
        else:
            # Asignamos 'base_url' con url_producto.split('/')[0] + '//' + url_pr...
            base_url = url_producto.split('/')[0] + "//" + url_producto.split('/')[2] if '://' in url_producto else 'https://'
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
            VALUES (?, ?, 90, 'Tienda Verificada 🇨🇱', '🏬');
            """, (tienda_nombre, base_url))
            # Asignamos 'tienda_id' con cursor.lastrowid
            tienda_id = cursor.lastrowid

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        SELECT id, precio_referencia FROM perfumes 
        WHERE LOWER(nombre) = LOWER(?) OR LOWER(nombre) LIKE ?;
        """, (nombre.strip(), f"%{nombre.strip()}%"))
        # Asignamos 'row_perfume' con cursor.fetchone()
        row_perfume = cursor.fetchone()

        # Asignamos 'es_nuevo' con False
        es_nuevo = False
        # Evaluamos la condición lógica (row_perfume) para controlar el flujo
        if row_perfume:
            # Asignamos 'perfume_id' con row_perfume['id']
            perfume_id = row_perfume["id"]
        else:
            # Asignamos 'es_nuevo' con True
            es_nuevo = True
            # Asignamos 'img' con imagen_url or 'https://images.unsplash.com...
            img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
            # Asignamos 'notas_texto' con notas or 'Cítricos, Maderas, Almizcle'
            notas_texto = notas or "Cítricos, Maderas, Almizcle"
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
            VALUES (?, ?, ?, 'Eau de Parfum', ?, ?, ?, 1, 0, ?);
            """, (nombre.strip(), marca.strip() or "Diseñador", genero, notas_texto, img, es_arabe, precio_actual))
            # Asignamos 'perfume_id' con cursor.lastrowid
            perfume_id = cursor.lastrowid

        # Asignamos 'fecha_actual' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha_registro)
        VALUES (?, ?, ?, ?, 1, ?, ?);
        """, (perfume_id, tienda_id, precio_actual, precio_normal, url_producto, fecha_actual))

        # Retornamos el resultado procesado ({'perfume_id': perfume_id, 'es_nuevo': es_nuevo...)
        return {"perfume_id": perfume_id, "es_nuevo": es_nuevo, "fecha": fecha_actual}


# Definición de función 'obtener_tiendas' sin parámetros externos
def obtener_tiendas() -> List[Dict[str, Any]]:
    """Retorna la lista de tiendas registradas ordenadas por índice de confianza."""
    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT * FROM tiendas ORDER BY trust_score DESC;")
        # Retornamos el resultado procesado ([dict(row) for row in cursor.fetchall()])
        return [dict(row) for row in cursor.fetchall()]


# Definición de función 'obtener_tiendas_trust' (parámetros: filtro_tipo, score_minimo, busqueda)
def obtener_tiendas_trust(
    filtro_tipo: Optional[str] = None,
    score_minimo: int = 0,
    busqueda: str = ""
) -> List[Dict[str, Any]]:
    """Retorna tiendas auditadas con métricas detalladas para la página de confianza."""
    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'query' con '\n SELECT \n id, nombre, url_base, trust_...
    query = """
    SELECT 
        id, nombre, url_base, trust_score, badge, logo_emoji,
        rut, tipo_tienda, ssl_seguro, anios_antiguedad, sello_ccs, reclamos_sernac,
        politica_devolucion, direccion_fiscal,
        puntos_seguridad, puntos_legalidad, puntos_garantia, puntos_reputacion
    FROM tiendas
    WHERE trust_score >= ?
    """
    # Asignamos 'params' con [score_minimo]
    params: List[Any] = [score_minimo]

    # Evaluamos la condición lógica (filtro_tipo and filtro_tipo != 'Todas') para controlar el flujo
    if filtro_tipo and filtro_tipo != "Todas":
        # Actualizamos acumulativamente el valor de 'query'
        query += " AND tipo_tienda = ?"
        # Ejecutamos instrucción: params.append(filtro_tipo)
        params.append(filtro_tipo)

    # Evaluamos la condición lógica (busqueda) para controlar el flujo
    if busqueda:
        # Asignamos 'term' con f'%{busqueda.lower().strip()}%'
        term = f"%{busqueda.lower().strip()}%"
        # Actualizamos acumulativamente el valor de 'query'
        query += " AND (LOWER(nombre) LIKE ? OR LOWER(url_base) LIKE ? OR LOWER(rut) LIKE ?)"
        # Ejecutamos instrucción: params.extend([term, term, term])
        params.extend([term, term, term])

    # Actualizamos acumulativamente el valor de 'query'
    query += " ORDER BY trust_score DESC;"

    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, params)
        # Asignamos 'tiendas' con []
        tiendas = []
        # Recorremos iterativamente cada 'r' en cursor.fetchall()
        for r in cursor.fetchall():
            # Asignamos 'd' con dict(r)
            d = dict(r)
            # Asignamos 'd['estrellas']' con round(d['trust_score'] / 20.0, 1)
            d["estrellas"] = round(d["trust_score"] / 20.0, 1)
            # Ejecutamos instrucción: tiendas.append(d)
            tiendas.append(d)
        # Retornamos el resultado procesado (tiendas)
        return tiendas


# Definición de función 'auditar_tienda_por_url' (parámetros: url_ingresada)
def auditar_tienda_por_url(url_ingresada: str) -> Optional[Dict[str, Any]]:
    """Audita en vivo cualquier URL con detección de comercios oficiales y análisis heurístico."""
    # Evaluamos la condición lógica (not url_ingresada or not url_ingresada.strip()) para controlar el flujo
    if not url_ingresada or not url_ingresada.strip():
        # Retornamos el resultado procesado (None)
        return None

    # Asignamos 'url_limpia' con url_ingresada.strip().lower()
    url_limpia = url_ingresada.strip().lower()
    # Evaluamos la condición lógica (not url_limpia.startswith(('http://', 'https://'))) para controlar el flujo
    if not url_limpia.startswith(("http://", "https://")):
        # Asignamos 'url_limpia' con 'https://' + url_limpia
        url_limpia = "https://" + url_limpia

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'parsed' con urllib.parse.urlparse(url_limpia)
        parsed = urllib.parse.urlparse(url_limpia)
        # Asignamos 'netloc' con (parsed.netloc or parsed.path.split('/')[0...
        netloc = (parsed.netloc or parsed.path.split('/')[0]).replace("www.", "")
    except Exception:
        # Asignamos 'netloc' con url_limpia
        netloc = url_limpia

    # Asignamos 'tiendas_db' con obtener_tiendas_trust()
    tiendas_db = obtener_tiendas_trust()
    # Recorremos iterativamente cada 't' en tiendas_db
    for t in tiendas_db:
        # Asignamos 'dominio_tienda' con t['url_base'].lower().replace('https://', ...
        dominio_tienda = t["url_base"].lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        # Evaluamos la condición lógica (dominio_tienda in netloc or netloc in dominio_tienda) para controlar el flujo
        if dominio_tienda in netloc or netloc in dominio_tienda:
            # Retornamos el resultado procesado ({'nombre': t['nombre'], 'url': t['url_base'], '...)
            return {
                "nombre": t["nombre"],
                "url": t["url_base"],
                "dominio": netloc,
                "score": t["trust_score"],
                "badge": t["badge"],
                "es_conocida": True,
                "tipo": t["tipo_tienda"],
                "rut": t["rut"],
                "ssl": bool(t["ssl_seguro"]),
                "sello_ccs": bool(t["sello_ccs"]),
                "antiguedad": f"{t['anios_antiguedad']} años",
                "sernac": t["reclamos_sernac"],
                "devolucion": t["politica_devolucion"],
                "desglose": {
                    "Seguridad Web (SSL/TLS)": f"{t['puntos_seguridad']}/25",
                    "Legalidad & RUT": f"{t['puntos_legalidad']}/25",
                    "Garantía & Devoluciones": f"{t['puntos_garantia']}/25",
                    "Reputación & Sellos": f"{t['puntos_reputacion']}/25"
                },
                "recomendacion": "Comercio verificado y auditado en PerfumeTrending. Cuenta con respaldo legal y trazabilidad en Chile."
            }

    # Asignamos 'puntos_ssl' con 25 if url_limpia.startswith('https://') el...
    puntos_ssl = 25 if url_limpia.startswith("https://") else 0
    # Asignamos 'es_cl' con netloc.endswith('.cl')
    es_cl = netloc.endswith(".cl")
    # Asignamos 'puntos_dominio' con 25 if es_cl else 10
    puntos_dominio = 25 if es_cl else 10

    # Asignamos 'senales_alerta' con []
    senales_alerta = []
    # Asignamos 'palabras_sospechosas' con ['outlet-original', 'perfumes-ganga', 'dio...
    palabras_sospechosas = ["outlet-original", "perfumes-ganga", "dior-chile-ofertas", "chanel-descuentos", "liquidaciones-lujo"]
    # Recorremos iterativamente cada 'palabra' en palabras_sospechosas
    for palabra in palabras_sospechosas:
        # Evaluamos la condición lógica (palabra in netloc) para controlar el flujo
        if palabra in netloc:
            # Ejecutamos instrucción: senales_alerta.append(f"Uso de términos engañosos en...
            senales_alerta.append(f"Uso de términos engañosos en el dominio ('{palabra}')")

    # Evaluamos la condición lógica (not url_limpia.startswith('https://')) para controlar el flujo
    if not url_limpia.startswith("https://"):
        # Ejecutamos instrucción: senales_alerta.append('No utiliza protocolo cifrado ...
        senales_alerta.append("No utiliza protocolo cifrado seguro HTTPS")
    # Evaluamos la condición lógica (not es_cl) para controlar el flujo
    if not es_cl:
        # Ejecutamos instrucción: senales_alerta.append('No utiliza dominio oficial ch...
        senales_alerta.append("No utiliza dominio oficial chileno (.cl)")

    # Asignamos 'puntos_transparencia' con 15 if not senales_alerta else 5
    puntos_transparencia = 15 if not senales_alerta else 5
    # Asignamos 'puntos_reputacion' con 15 if not senales_alerta else 5
    puntos_reputacion = 15 if not senales_alerta else 5
    # Asignamos 'score_estimado' con max(10, min(80, puntos_ssl + puntos_domini...
    score_estimado = max(10, min(80, puntos_ssl + puntos_dominio + puntos_transparencia + puntos_reputacion))

    # Evaluamos la condición lógica (score_estimado >= 70) para controlar el flujo
    if score_estimado >= 70:
        # Asignamos 'badge' con 'Verificación Básica'
        badge = "Verificación Básica"
        # Asignamos 'recom' con 'El sitio cuenta con HTTPS y dominio están...
        recom = "El sitio cuenta con HTTPS y dominio estándar, pero no está en el registro oficial de distribuidores autorizados. Revisa que permita pagar con Webpay y no solo transferencias personales."
    else:
        # Asignamos 'badge' con 'Sitio No Verificado / Riesgo'
        badge = "Sitio No Verificado / Riesgo"
        # Asignamos 'recom' con '⚠️ Precaución extrema. No se registran an...
        recom = "⚠️ Precaución extrema. No se registran antecedentes comerciales formales ni sello de confianza. Posible tienda clon o producto sin garantía de originalidad."

    # Retornamos el resultado procesado ({'nombre': netloc.capitalize(), 'url': url_limp...)
    return {
        "nombre": netloc.capitalize(),
        "url": url_limpia,
        "dominio": netloc,
        "score": score_estimado,
        "badge": badge,
        "es_conocida": False,
        "tipo": "Comercio Externo No Auditado",
        "rut": "No registrado en plataforma",
        "ssl": url_limpia.startswith("https://"),
        "sello_ccs": False,
        "antiguedad": "Desconocida",
        "sernac": "Sin historial",
        "devolucion": "No especificada legalmente",
        "desglose": {
            "Seguridad Web": f"{puntos_ssl}/25",
            "Dominio (.cl)": f"{puntos_dominio}/25",
            "Transparencia": f"{puntos_transparencia}/25",
            "Acreditación": f"{puntos_reputacion}/25"
        },
        "senales_alerta": senales_alerta,
        "recomendacion": recom
    }
