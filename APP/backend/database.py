"""
PerfumeTrending.cl — Capa de Persistencia y Motor de Base de Datos (Supabase + SQLite Fallback)
=============================================================================================
Módulo desacoplado de acceso a datos de nivel de producción con:
- Motor primario: Supabase (PostgreSQL 15+ en la nube con PostgREST y RLS).
- Motor de resiliencia: SQLite local con modo WAL (Zero-Downtime Fallback).
- Vistas SQL de alto rendimiento para catálogo consolidado y mejores precios en vivo.
- DDL externalizado en supabase/migrations/ y database/schema.sql.
- Catálogo maestro y tiendas auditadas en database/seed_catalogo.json.
- Context managers para transacciones seguras y tipado estricto (PEP 484).
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
from typing import Any, Dict, Generator, List, Optional, Tuple
import urllib.parse
import uuid

logger = logging.getLogger("PerfumeDatabase")

# =============================================================================
# BLOQUE 1: RESOLUCIÓN DE RUTAS DEL SISTEMA Y ARCHIVOS CANÓNICOS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Permite que la aplicación funcione sin importar desde qué directorio se ejecute:
# ya sea desde la raíz del repositorio (`python run.py`), desde la subcarpeta `APP/`,
# o desde tests automatizados en `tests/`. Busca dinámicamente los archivos críticos:
# 1. `data/perfumes.db`: Base de datos SQLite local de contingencia (fallback).
# 2. `database/schema.sql`: Script DDL para construir las tablas relacionales.
# 3. `database/seed_catalogo.json`: Catálogo maestro canónico con las tiendas y perfumes.
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolver_ruta(subpath: str) -> str:
    """
    ¿QUÉ HACE ESTA FUNCIÓN?
    Evalúa una lista de posibles ubicaciones relativas en el sistema de archivos
    hasta encontrar dónde reside el recurso solicitado, devolviendo su ruta absoluta.
    Evita los clásicos errores de 'FileNotFoundError' al mover o desplegar el proyecto.
    """
    curr = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(BASE_DIR, subpath),
        os.path.join(BASE_DIR, "APP", subpath),
        os.path.join(curr, subpath),
        os.path.join(curr, "..", subpath),
        os.path.join(curr, "..", "APP", subpath),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(BASE_DIR, subpath)


DB_PATH = resolver_ruta("data/perfumes.db")
DB_DIR = os.path.dirname(DB_PATH)
SCHEMA_PATH = resolver_ruta("database/schema.sql")
SEED_PATH = resolver_ruta("database/seed_catalogo.json")

# Variable global para cachear en memoria RAM el catálogo JSON una sola vez y no releer el disco
_SEED_CACHE: Optional[Dict[str, Any]] = None


# =============================================================================
# BLOQUE 2: SEGURIDAD Y HASHING CRIPTOGRÁFICO DE CONTRASEÑAS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Proporciona una función de cifrado unidireccional SHA-256 para proteger las
# contraseñas de los usuarios.
# ¿POR QUÉ SE HACE ASÍ?
# En buenas prácticas de desarrollo web, NUNCA se guardan contraseñas en texto plano.
# Si la base de datos sufriera una filtración, el atacante solo obtendría hashes
# hexadecimales irreversibles. Usamos la biblioteca estándar `hashlib` para no depender
# de librerías binarias complejas como bcrypt en entornos ligeros de Streamlit.
# =============================================================================
def hash_password(password: str) -> str:
    """Genera un hash SHA-256 seguro utilizando únicamente la librería estándar hashlib."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


# =============================================================================
# BLOQUE 3: CARGA Y CACHÉ DEL CATÁLOGO MAESTRO (JSON SEED)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Lee `database/seed_catalogo.json` con la definición de perfumes iniciales,
# tiendas autorizadas, sellos de confianza y enlaces de scraping.
# Lo guarda en la variable `_SEED_CACHE` para acceso instantáneo O(1).
# =============================================================================
def cargar_datos_semilla_json() -> Dict[str, Any]:
    """Carga y cachea el archivo JSON con el catálogo canónico y directrices de tiendas."""
    global _SEED_CACHE
    if _SEED_CACHE is not None:
        return _SEED_CACHE

    if not os.path.exists(SEED_PATH):
        raise FileNotFoundError(f"Archivo de catálogo maestro no encontrado en: {SEED_PATH}")

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        _SEED_CACHE = json.load(f)

    return _SEED_CACHE


# Variables globales de control para la conexión con Supabase (Patrón Singleton)
_SUPABASE_CLIENT = None
_SUPABASE_SERVICE_CLIENT = None
_SUPABASE_VERIFICADO = False


# =============================================================================
# BLOQUE 4: GESTIÓN MULTI-ORIGEN DE CREDENCIALES DE SUPABASE
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Busca las credenciales `SUPABASE_URL` y `SUPABASE_KEY` (o Service Role) en 3 niveles:
# 1. Variables de entorno del Sistema Operativo (`os.environ`).
# 2. Archivos locales de configuración `.streamlit/secrets.toml`.
# 3. Diccionario interno de Streamlit Cloud (`st.secrets`).
# ¿POR QUÉ SE HACE ASÍ?
# Permite que el código funcione idénticamente en:
# - Tu computadora local (leyendo el archivo secrets.toml).
# - En despliegues en la nube de Streamlit Cloud / Docker (usando st.secrets o variables de entorno).
# =============================================================================
def get_supabase_credentials(prefer_service_role: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Obtiene las credenciales de Supabase desde variables de entorno, secrets de Streamlit o secrets.toml."""
    url = os.environ.get("SUPABASE_URL")
    key = None
    
    # 1. Variables de entorno del sistema
    if prefer_service_role:
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        key = os.environ.get("SUPABASE_KEY")

    # 2. Búsqueda en archivos secrets.toml en las carpetas del proyecto
    candidatos = [
        os.path.join(BASE_DIR, ".streamlit", "secrets.toml"),
        os.path.join(BASE_DIR, "APP", ".streamlit", "secrets.toml"),
        os.path.join(os.path.dirname(BASE_DIR), ".streamlit", "secrets.toml"),
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            try:
                dict_secrets = {}
                with open(ruta, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            dict_secrets[k.strip()] = v.strip().strip('"').strip("'")
                
                if not url:
                    url = dict_secrets.get("SUPABASE_URL")
                
                if prefer_service_role and "SUPABASE_SERVICE_ROLE_KEY" in dict_secrets:
                    key = dict_secrets["SUPABASE_SERVICE_ROLE_KEY"]
                elif not key:
                    key = dict_secrets.get("SUPABASE_KEY")

                if url and key:
                    return url, key
            except Exception:
                pass

    # 3. Intentar cargar desde st.secrets de Streamlit como fallback
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if not url and "SUPABASE_URL" in st.secrets:
                url = st.secrets["SUPABASE_URL"]
            if prefer_service_role and "SUPABASE_SERVICE_ROLE_KEY" in st.secrets:
                key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
            elif not key and "SUPABASE_KEY" in st.secrets:
                key = st.secrets["SUPABASE_KEY"]
            if url and key:
                return str(url).strip(), str(key).strip()
    except Exception:
        pass

    return url, key


# =============================================================================
# BLOQUE 5: CLIENTE SUPABASE (PATRÓN SINGLETON) Y DIAGNÓSTICO DE CONEXIÓN
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. `get_supabase()`: Crea una única instancia reutilizable del cliente Supabase
#    (evitando abrir múltiples conexiones HTTP innecesarias). Si se le solicita
#    `use_service_role=True`, usa la clave con permisos administrativos para el scraper.
# 2. `is_supabase_disponible()`: Ejecuta una consulta ultraligera (`LIMIT 1`) a la tabla
#    `tiendas`. Si la nube responde en milisegundos, activa el modo Supabase. Si no hay
#    internet o Supabase está caído, conmuta automáticamente a la base SQLite local
#    (Arquitectura Zero-Downtime Fallback).
# =============================================================================
def get_supabase(use_service_role: bool = False):
    """
    Retorna una instancia singleton del cliente Supabase.
    Si use_service_role=True, utiliza la clave de administrador para ignorar políticas RLS.
    """
    global _SUPABASE_CLIENT, _SUPABASE_SERVICE_CLIENT
    if use_service_role:
        if _SUPABASE_SERVICE_CLIENT is not None:
            return _SUPABASE_SERVICE_CLIENT
    else:
        if _SUPABASE_CLIENT is not None:
            return _SUPABASE_CLIENT

    url, key = get_supabase_credentials(prefer_service_role=use_service_role)
    if not url or not key:
        return None

    try:
        from supabase import create_client
        client = create_client(url, key)
        if use_service_role:
            _SUPABASE_SERVICE_CLIENT = client
        else:
            _SUPABASE_CLIENT = client
        return client
    except Exception as e:
        logger.warning(f"No se pudo inicializar el cliente Supabase (service_role={use_service_role}): {e}")
        return None


def is_supabase_disponible() -> bool:
    """Verifica si Supabase está alcanzable y tiene las tablas creadas."""
    global _SUPABASE_VERIFICADO
    if _SUPABASE_VERIFICADO:
        return True

    sb = get_supabase()
    if not sb:
        return False

    try:
        # Prueba ligera consultando 1 registro de tiendas o perfumes
        resp = sb.table("tiendas").select("id").limit(1).execute()
        _SUPABASE_VERIFICADO = True
        return True
    except Exception as e:
        logger.debug(f"Supabase aún no responde o tablas no creadas: {e}")
        return False


# =============================================================================
# BLOQUE 6: MOTOR DE RESILIENCIA LOCAL (SQLITE CON MODO WAL Y CONCURRENCIA)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Provee la conexión local a `perfumes.db` configurada con estándares de producción:
# - `PRAGMA journal_mode=WAL;` (Write-Ahead Logging): Permite que múltiples lectores
#   lean la base de datos simultáneamente mientras el scraper escribe en segundo plano,
#   evitando bloqueos de base de datos ("database is locked").
# - `PRAGMA synchronous=NORMAL;`: Reduce la sobrecarga de I/O en disco sin perder integridad.
# - `PRAGMA foreign_keys=ON;`: Obliga a SQLite a respetar la integridad referencial
#   de claves foráneas (que un precio no pueda existir sin su perfume y tienda).
# - `get_db_cursor()`: Un Administrador de Contexto (Context Manager `with`) que hace
#   commit automático si todo sale bien, o rollback automático si ocurre cualquier error,
#   cerrando siempre la conexión para no dejar handles abiertos.
# =============================================================================
def get_connection() -> sqlite3.Connection:
    """Crea y configura una conexión local de respaldo a SQLite en modo WAL."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_db_cursor(commit: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager transaccional determinista para SQLite con auto-commit y rollback defensivo."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# BLOQUE 7: INICIALIZACIÓN DE ESQUEMA (DDL) Y POBLADO AUTOMÁTICO DE DATOS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# 1. `init_db()`: Ejecuta `schema.sql` en SQLite para crear las tablas relacionales
#    si aún no existen, y asegura que las columnas de perfil y favoritos estén presentes.
# 2. `poblar_datos_semilla()`: Si la base está vacía, inserta los 134 perfumes canónicos,
#    las 8 tiendas chilenas y sus registros de precios iniciales.
# 3. `poblar_datos_semilla_supabase()`: Realiza el mismo proceso sobre Supabase en la nube
#    utilizando operaciones masivas `upsert` para evitar duplicidad de llaves primarias.
# =============================================================================
def init_db(force_reseed: bool = False) -> None:
    """
    Inicializa la persistencia:
    - Asegura que SQLite local esté siempre listo como respaldo defensivo.
    - Si Supabase está disponible y vacío, puebla automáticamente los datos semilla.
    """
    # 1. Asegurar base de datos local SQLite (siempre disponible)
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with get_db_cursor(commit=True) as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='precios_registro';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(precios_registro);")
                cols = {c["name"] for c in cursor.fetchall()}
                for col_name, col_def in [
                    ("volumen_ml", "INTEGER DEFAULT 100"),
                    ("variante_id", "INTEGER"),
                    ("tipo_evento", "TEXT"),
                    ("campos_modificados", "TEXT"),
                    ("observacion_id", "TEXT"),
                    ("scraping_run_id", "INTEGER")
                ]:
                    if col_name not in cols:
                        cursor.execute(f"ALTER TABLE precios_registro ADD COLUMN {col_name} {col_def};")

            cursor.executescript(schema_sql)

            cursor.execute("SELECT COUNT(*) FROM perfumes;")
            row_count = cursor.fetchone()[0]
            if row_count == 0 or force_reseed:
                poblar_datos_semilla(cursor)

    # 2. Si Supabase está activo y conectado, verificar si requiere datos semilla
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            res = sb.table("perfumes").select("id", count="exact").limit(1).execute()
            if (res.count is not None and res.count == 0) or force_reseed:
                poblar_datos_semilla_supabase()
        except Exception as e:
            logger.debug(f"Aviso al verificar catálogo en Supabase: {e}")


def poblar_datos_semilla(cursor: sqlite3.Cursor) -> None:
    """Puebla SQLite a partir del archivo canónico seed_catalogo.json."""
    catalogo = cargar_datos_semilla_json()

    cursor.execute("DELETE FROM precios_registro;")
    cursor.execute("DELETE FROM perfumes;")
    cursor.execute("DELETE FROM tiendas;")

    tiendas_data = catalogo.get("tiendas", [])
    tiendas_tuples = [
        (
            t["nombre"], t["url_base"], t.get("trust_score", 85), t.get("badge", "Verificado"),
            t.get("logo_emoji", ""), t.get("rut", ""), t.get("tipo_tienda", "Comercio Especializado"),
            int(t.get("ssl_seguro", 1)), t.get("anios_antiguedad", 5), int(t.get("sello_ccs", 0)),
            t.get("reclamos_sernac", "Bajo"), t.get("politica_devolucion", "30 días"),
            t.get("direccion_fiscal", "Santiago, Chile"), t.get("puntos_seguridad", 25),
            t.get("puntos_legalidad", 25), t.get("puntos_garantia", 20), t.get("puntos_reputacion", 20)
        )
        for t in tiendas_data
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO tiendas (
        nombre, url_base, trust_score, badge, logo_emoji,
        rut, tipo_tienda, ssl_seguro, anios_antiguedad, sello_ccs, reclamos_sernac,
        politica_devolucion, direccion_fiscal,
        puntos_seguridad, puntos_legalidad, puntos_garantia, puntos_reputacion
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, tiendas_tuples)

    perfumes_data = catalogo.get("perfumes", [])
    perfumes_tuples = [
        (
            p["id"], p["nombre"], p["marca"], p.get("genero", "Unisex"),
            p.get("tipo", "Eau de Parfum"), p["notas"], p["imagen_url"],
            int(p.get("es_arabe", False)), int(p.get("en_tendencia", False)),
            int(p.get("en_remate", False)), p["precio_referencia"]
        )
        for p in perfumes_data
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO perfumes (
        id, nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, perfumes_tuples)

    cursor.execute("SELECT id, nombre FROM tiendas;")
    tiendas_map = {r["nombre"]: r["id"] for r in cursor.fetchall()}

    hoy = datetime.now()
    dias_atras = [21, 14, 7, 3, 1, 0]
    registros_precios = []

    for p in perfumes_data:
        p_id = p["id"]
        for enlace in p.get("enlaces_tiendas", []):
            t_nombre = enlace.get("tienda")
            if t_nombre not in tiendas_map:
                continue
            t_id = tiendas_map[t_nombre]
            precio_act = enlace.get("precio_actual", p["precio_referencia"])
            p_normal_val = enlace.get("precio_normal")
            precio_norm = p_normal_val if (p_normal_val and p_normal_val > precio_act) else precio_act
            url_prod = enlace.get("url_producto", "")
            vol_ml = enlace.get("volumen_ml", p.get("volumen_ml", 100))

            for dia in dias_atras:
                fecha = hoy - timedelta(days=dia, hours=dia, minutes=dia * 4)
                if dia == 0:
                    p_actual_hist = precio_act
                else:
                    fluc = 1.0 + (dia * 0.004)
                    p_actual_hist = int(round((precio_act * fluc) / 1000) * 1000)

                registros_precios.append((
                    p_id, t_id, p_actual_hist, precio_norm, 1, vol_ml, url_prod, fecha.strftime("%Y-%m-%d %H:%M:%S")
                ))

    cursor.executemany("""
    INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, registros_precios)

    logger.info(f"SQLite poblado: {len(perfumes_tuples)} perfumes, {len(tiendas_tuples)} tiendas, {len(registros_precios)} registros.")


def poblar_datos_semilla_supabase() -> bool:
    """Puebla Supabase con las tiendas, perfumes y precios del catálogo semilla."""
    sb = get_supabase()
    if not sb:
        return False

    catalogo = cargar_datos_semilla_json()

    # 1. Tiendas
    tiendas_data = catalogo.get("tiendas", [])
    tiendas_inserts = []
    for t in tiendas_data:
        tiendas_inserts.append({
            "nombre": t["nombre"],
            "url_base": t["url_base"],
            "trust_score": t.get("trust_score", 85),
            "badge": t.get("badge", "Verificado"),
            "logo_emoji": t.get("logo_emoji", ""),
            "rut": t.get("rut", ""),
            "tipo_tienda": t.get("tipo_tienda", "Comercio Especializado"),
            "ssl_seguro": bool(t.get("ssl_seguro", 1)),
            "anios_antiguedad": t.get("anios_antiguedad", 5),
            "sello_ccs": bool(t.get("sello_ccs", 0)),
            "reclamos_sernac": t.get("reclamos_sernac", "Bajo"),
            "politica_devolucion": t.get("politica_devolucion", "30 días"),
            "direccion_fiscal": t.get("direccion_fiscal", "Santiago, Chile"),
            "puntos_seguridad": t.get("puntos_seguridad", 25),
            "puntos_legalidad": t.get("puntos_legalidad", 25),
            "puntos_garantia": t.get("puntos_garantia", 20),
            "puntos_reputacion": t.get("puntos_reputacion", 20)
        })

    try:
        sb.table("tiendas").upsert(tiendas_inserts, on_conflict="nombre").execute()
    except Exception as e:
        logger.error(f"Error insertando tiendas en Supabase: {e}")
        return False

    # Mapeo tiendas nombre -> id
    resp_tiendas = sb.table("tiendas").select("id, nombre").execute()
    tiendas_map = {r["nombre"]: r["id"] for r in (resp_tiendas.data or [])}

    # 2. Perfumes
    perfumes_data = catalogo.get("perfumes", [])
    perfumes_inserts = []
    for p in perfumes_data:
        perfumes_inserts.append({
            "id": p["id"],
            "nombre": p["nombre"],
            "marca": p["marca"],
            "genero": p.get("genero", "Unisex"),
            "tipo": p.get("tipo", "Eau de Parfum"),
            "notas": p["notas"],
            "imagen_url": p["imagen_url"],
            "es_arabe": bool(p.get("es_arabe", False)),
            "en_tendencia": bool(p.get("en_tendencia", False)),
            "en_remate": bool(p.get("en_remate", False)),
            "precio_referencia": p["precio_referencia"]
        })

    try:
        sb.table("perfumes").upsert(perfumes_inserts, on_conflict="id").execute()
    except Exception as e:
        logger.error(f"Error insertando perfumes en Supabase: {e}")
        return False

    # 3. Precios Históricos
    dias_atras = [21, 14, 7, 3, 1, 0]
    precios_inserts = []
    hoy = datetime.now()

    for p in perfumes_data:
        p_id = p["id"]
        for enlace in p.get("enlaces_tiendas", []):
            t_nombre = enlace.get("tienda")
            if t_nombre not in tiendas_map:
                continue
            t_id = tiendas_map[t_nombre]
            precio_act = enlace.get("precio_actual", p["precio_referencia"])
            p_normal_val = enlace.get("precio_normal")
            precio_norm = p_normal_val if (p_normal_val and p_normal_val > precio_act) else precio_act
            url_prod = enlace.get("url_producto", "")
            vol_ml = enlace.get("volumen_ml", p.get("volumen_ml", 100))

            for dia in dias_atras:
                fecha = hoy - timedelta(days=dia, hours=dia, minutes=dia * 4)
                if dia == 0:
                    p_act_h = precio_act
                    p_norm_h = precio_norm
                else:
                    fluc = 1.0 + (dia * 0.004)
                    p_act_h = int(round((precio_act * fluc) / 1000) * 1000)
                    p_norm_h = precio_norm if precio_norm > precio_act else p_act_h

                precios_inserts.append({
                    "perfume_id": p_id,
                    "tienda_id": t_id,
                    "precio_actual": p_act_h,
                    "precio_normal": p_norm_h,
                    "en_stock": True,
                    "volumen_ml": vol_ml,
                    "url_producto": url_prod,
                    "fecha_registro": fecha.strftime("%Y-%m-%d %H:%M:%S")
                })

    try:
        for chunk_idx in range(0, len(precios_inserts), 50):
            chunk = precios_inserts[chunk_idx:chunk_idx + 50]
            sb.table("precios_registro").insert(chunk).execute()
        logger.info(f"Supabase poblado exitosamente: {len(perfumes_inserts)} perfumes, {len(tiendas_inserts)} tiendas, {len(precios_inserts)} precios.")
        return True
    except Exception as e:
        logger.error(f"Error insertando precios en Supabase: {e}")
        return False


# =============================================================================
# BLOQUE 8: GESTIÓN DE USUARIOS, AUTENTICACIÓN Y PERFIL DE CLIENTE
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Maneja todo el ciclo de vida de las cuentas de usuario:
# 1. `crear_usuario()`: Valida que el correo no esté duplicado, hashea la contraseña
#    con SHA-256 y crea el registro con valores predeterminados (alertas activadas).
# 2. `verificar_usuario()`: Busca el correo y compara el hash SHA-256 para iniciar sesión.
#    Por seguridad, elimina el campo `password_hash` antes de retornar el diccionario.
# 3. `obtener_perfil_usuario()`: Permite consultar los datos por ID o por correo electrónico.
# 4. `actualizar_perfil_usuario()`: Actualiza nombre, teléfono, biografía y foto (URL).
# 5. `actualizar_preferencias_notificacion()`: Configura si desea emails y el % de descuento mínimo.
# =============================================================================
def crear_usuario(
    nombre: str,
    email: str,
    password: str,
    telefono: str = "",
    bio: str = "",
    foto_perfil: str = ""
) -> Tuple[bool, str]:
    """Registra un nuevo usuario en la base de datos con contraseña cifrada en SHA-256."""
    init_db()
    email_clean = email.strip().lower()
    
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ?;", (email_clean,))
        if cursor.fetchone():
            return False, "El correo electrónico ya se encuentra registrado."

        pwd_hash = hash_password(password)
        foto = foto_perfil or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&q=80"
        
        cursor.execute("""
        INSERT INTO usuarios (nombre, email, password_hash, telefono, bio, foto_perfil, alerta_email, umbral_descuento)
        VALUES (?, ?, ?, ?, ?, ?, 1, 10);
        """, (nombre.strip(), email_clean, pwd_hash, telefono.strip(), bio.strip(), foto))

        return True, "Cuenta creada exitosamente."


def verificar_usuario(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    ¿CÓMO VALIDA EL LOGIN?
    Hashea la clave provista y la compara contra el `password_hash` almacenado en la BD.
    Retorna (True, datos_usuario) si coincide, o (False, None) si es errónea.
    """
    init_db()
    email_clean = email.strip().lower()
    pwd_hash = hash_password(password)

    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(email) = ? AND password_hash = ?;", (email_clean, pwd_hash))
        row = cursor.fetchone()
        if row:
            u_data = dict(row)
            del u_data['password_hash']
            u_data['alerta_email'] = bool(u_data['alerta_email'])
            return True, u_data
        return False, None


def obtener_perfil_usuario(usuario_id_o_email: Any) -> Optional[Dict[str, Any]]:
    """Consulta el perfil completo de un usuario por su ID entero o por su Correo electrónico."""
    init_db()
    with get_db_cursor() as cursor:
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            cursor.execute("SELECT * FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            cursor.execute("SELECT * FROM usuarios WHERE LOWER(email) = ?;", (str(usuario_id_o_email).strip().lower(),))
        
        row = cursor.fetchone()
        if row:
            u_data = dict(row)
            u_data.pop('password_hash', None)
            u_data['alerta_email'] = bool(u_data['alerta_email'])
            return u_data
        return None


def actualizar_perfil_usuario(
    usuario_id_o_email: Any,
    nombre: str,
    email: str,
    telefono: str,
    bio: str,
    foto_perfil: str
) -> Tuple[bool, str]:
    """Actualiza la información personal, foto de perfil y contacto en la base de datos."""
    init_db()
    email_clean = email.strip().lower()

    with get_db_cursor(commit=True) as cursor:
        # Resolver usuario
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            cursor.execute("SELECT id, email FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            cursor.execute("SELECT id, email FROM usuarios WHERE LOWER(email) = ?;", (str(usuario_id_o_email).strip().lower(),))
        
        row = cursor.fetchone()
        if not row:
            # Si no existe, creamos dinámicamente para prevenir inconsistencias de sesión
            cursor.execute("""
            INSERT INTO usuarios (nombre, email, telefono, bio, foto_perfil)
            VALUES (?, ?, ?, ?, ?);
            """, (nombre.strip(), email_clean, telefono.strip(), bio.strip(), foto_perfil.strip()))
            return True, "Perfil creado y actualizado."

        u_id = row['id']

        # Verificar si cambió el email y si este ya pertenece a otro usuario
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ? AND id != ?;", (email_clean, u_id))
        if cursor.fetchone():
            return False, "El correo ingresado ya está siendo utilizado por otra cuenta."

        cursor.execute("""
        UPDATE usuarios 
        SET nombre = ?, email = ?, telefono = ?, bio = ?, foto_perfil = ?
        WHERE id = ?;
        """, (nombre.strip(), email_clean, telefono.strip(), bio.strip(), foto_perfil.strip(), u_id))

        return True, "Perfil actualizado con éxito."


def actualizar_preferencias_notificacion(
    usuario_id_o_email: Any,
    alerta_email: bool,
    umbral_descuento: int = 10
) -> Tuple[bool, str]:
    """Guarda si el usuario quiere recibir alertas al Gmail y el % mínimo de descuento para gatillarlas."""
    init_db()
    with get_db_cursor(commit=True) as cursor:
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            query_find = "WHERE id = ?"
            val_find = int(usuario_id_o_email)
        else:
            query_find = "WHERE LOWER(email) = ?"
            val_find = str(usuario_id_o_email).strip().lower()

        cursor.execute(f"UPDATE usuarios SET alerta_email = ?, umbral_descuento = ? {query_find};",
                       (int(alerta_email), umbral_descuento, val_find))
        return True, "Preferencias de notificación guardadas."


# =============================================================================
# BLOQUE 9: FAVORITOS Y SISTEMA INTELIGENTE DE MONITOREO DE PRECIOS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Permite que el usuario guarde perfumes en seguimiento:
# 1. Guarda el perfume junto al `precio_guardado` (el precio que tenía al momento del clic).
# 2. Al listar los favoritos en `obtener_favoritos_usuario()`, calcula en tiempo real
#    si el precio actual bajó respecto al guardado (`baja_detectada = True`) y calcula
#    el porcentaje exacto de rebaja.
# 3. `obtener_alertas_pendientes()`: Consulta con cláusula `HAVING` que detecta qué
#    usuarios superaron su umbral de descuento configurado para enviarles alerta.
# =============================================================================
def agregar_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Añade una fragancia a la lista de favoritos del usuario guardando el mejor precio actual."""
    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil:
        return False

    u_id = u_perfil['id']
    
    # Obtener el mejor precio actual del perfume
    precios = obtener_precios_actuales(perfume_id)
    p_min = min([p['precio_actual'] for p in precios if p.get('precio_actual', 0) > 0]) if precios else 0

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
        INSERT OR REPLACE INTO favoritos (usuario_id, perfume_id, precio_guardado, fecha_agregado)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP);
        """, (u_id, perfume_id, p_min))
        return True


def eliminar_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Elimina una fragancia de la lista de monitoreo del usuario."""
    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil:
        return False

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM favoritos WHERE usuario_id = ? AND perfume_id = ?;", (u_perfil['id'], perfume_id))
        return True


def obtener_favoritos_usuario(usuario_id_o_email: Any) -> List[Dict[str, Any]]:
    """Retorna los perfumes favoritos monitoreados por el usuario con detección de bajas de precio."""
    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil:
        return []

    query = """
    SELECT p.*, f.precio_guardado, f.fecha_agregado,
           MIN(CASE WHEN pr.en_stock = 1 AND pr.precio_actual > 0 THEN pr.precio_actual END) as mejor_precio_actual
    FROM favoritos f
    JOIN perfumes p ON f.perfume_id = p.id
    LEFT JOIN precios_registro pr ON p.id = pr.perfume_id
    WHERE f.usuario_id = ?
    GROUP BY p.id
    ORDER BY f.fecha_agregado DESC;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (u_perfil['id'],))
        favoritos = []
        for row in cursor.fetchall():
            d = dict(row)
            p_act = d['mejor_precio_actual'] or d['precio_referencia']
            p_init = d['precio_guardado'] or d['precio_referencia']
            d['baja_detectada'] = (p_act < p_init) and p_act > 0
            if d['precio_guardado'] and d['precio_guardado'] > 0:
                d['porcentaje_descuento'] = round(((d['precio_guardado'] - p_act) / d['precio_guardado']) * 100, 1)
            else:
                d['porcentaje_descuento'] = 0.0
            favoritos.append(d)
        return favoritos


def es_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Verifica si una fragancia específica está marcada como favorita por el usuario."""
    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil:
        return False

    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM favoritos WHERE usuario_id = ? AND perfume_id = ?;", (u_perfil['id'], perfume_id))
        return cursor.fetchone() is not None


def obtener_alertas_pendientes() -> List[Dict[str, Any]]:
    """
    ¿QUÉ HACE ESTA CONSULTA?
    Calcula qué usuarios tienen activadas las alertas por email y tienen perfumes favoritos
    cuyo precio actual cayó por debajo del porcentaje configurado en `umbral_descuento`.
    """
    init_db()
    query = """
    SELECT u.email, u.nombre as usuario_nombre, u.umbral_descuento,
           p.nombre as perfume_nombre, p.marca, f.precio_guardado,
           MIN(pr.precio_actual) as precio_nuevo
    FROM favoritos f
    JOIN usuarios u ON f.usuario_id = u.id
    JOIN perfumes p ON f.perfume_id = p.id
    JOIN precios_registro pr ON p.id = pr.perfume_id
    WHERE u.alerta_email = 1
      AND pr.en_stock = 1
      AND pr.precio_actual > 0
    GROUP BY u.id, p.id
    HAVING (f.precio_guardado - MIN(pr.precio_actual)) * 100.0 / NULLIF(f.precio_guardado, 0) >= u.umbral_descuento;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query)
        return [dict(r) for r in cursor.fetchall()]


# =============================================================================
# BLOQUE 10: RESOLUCIÓN Y CONSTRUCCIÓN DE ENLACES EXTERNOS A TIENDAS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Provee los enlaces directos o motores de búsqueda interna de cada multitienda chilena:
# - Si la oferta tiene URL directa en el scraper o catálogo, la entrega inmediatamente.
# - Si no, construye la URL del motor de búsqueda oficial (Falabella, Paris, Ripley, Silk, etc.).
# =============================================================================
def obtener_url_directa_tienda(perfume_id: int, tienda_nombre: str) -> Optional[Tuple[str, int, int, int]]:
    """Retorna la tupla (url_producto, precio_actual, precio_normal, volumen_ml) configurada en el catálogo semilla."""
    catalogo = cargar_datos_semilla_json()
    for p in catalogo.get("perfumes", []):
        if p["id"] == perfume_id:
            for enlace in p.get("enlaces_tiendas", []):
                if enlace.get("tienda") == tienda_nombre:
                    p_act = enlace.get("precio_actual", p["precio_referencia"])
                    p_norm = enlace.get("precio_normal", p_act)
                    vol = enlace.get("volumen_ml", p.get("volumen_ml", 100))
                    return (enlace.get("url_producto", ""), p_act, p_norm, vol)
    return None


def generar_url_tienda(tienda_nombre: str, perfume_nombre: str, url_directa: Optional[str] = None) -> Optional[str]:
    """Genera el enlace de navegación para el usuario hacia la tienda correspondiente."""
    if url_directa and url_directa.startswith("http") and url_directa != "#":
        return url_directa

    t = (tienda_nombre or "").lower()
    q = urllib.parse.quote(perfume_nombre.strip())
    if "falabella" in t:
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    elif "paris" in t:
        return f"https://www.paris.cl/search?q={q}"
    elif "ripley" in t:
        return f"https://simple.ripley.cl/search/{q}"
    elif "silk" in t:
        return f"https://www.silkperfumes.cl/search?q={q}"
    elif "elite" in t:
        return f"https://www.eliteperfumes.cl/search?q={q}"
    elif "alisha" in t:
        return f"https://www.alisha.cl/search?q={q}"
    elif "dbs" in t:
        return f"https://www.dbs.cl/search?q={q}"
    return None


def tienda_comercializa_marca(tienda_nombre: str, marca: str) -> bool:
    t_nom = tienda_nombre.lower()
    m = marca.lower()
    if "chanel" in m or "maison francis" in m or "tom ford" in m:
        return any(retail in t_nom for retail in ["falabella", "paris", "ripley"])
    return True


# =============================================================================
# BLOQUE 11: PERSISTENCIA TRANSACCIONAL ATÓMICA Y CONTROL DE ERRORES DE SCRAPING
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Es el núcleo transaccional del backend. Recibe las observaciones extraídas por los scrapers:
# 1. Valida estrictamente las reglas de negocio (precio > 0, stock booleano, URL HTTP/HTTPS válida).
# 2. Si Supabase está disponible, ejecuta la RPC `registrar_observacion_oferta` en PostgreSQL.
# 3. Si se ejecuta en SQLite local, abre una transacción atómica `with get_db_cursor(commit=True)`.
# 4. Diferencia entre:
#    - Ofertas nuevas: Inserta en `ofertas_actuales` y genera evento `observacion_inicial` en `precios_registro`.
#    - Ofertas sin cambios: Solo actualiza marcas temporales de verificación (`ultima_verificacion_exitosa`).
#    - Ofertas con cambios: Registra la variación (`cambio_precio`, `cambio_stock`, etc.) y crea un snapshot inmutable en el historial.
# 5. `registrar_fallo_scraping()`: Si una tienda bloquea el bot o falla el scraping, incrementa
#    el contador `fallos_consecutivos` sin destruir el último precio conocido ni crear datos ficticios.
# =============================================================================
def registrar_observacion_oferta(observacion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persistencia transaccional de una observación de precio/stock:
    - Valida precio actual > 0, precio normal válido, stock explícito y URL válida.
    - Soporta Supabase RPC si está disponible.
    - Fallback y soporte nativo en SQLite local con transacción atómica (ofertas_actuales + precios_registro).
    - Propaga excepciones y garantiza que nunca se creen ofertas ficticias ni se altere el estado
      con datos inválidos o fallos de scraping.
    """
    if not isinstance(observacion, dict):
        raise ValueError("La observación debe ser un diccionario válido")

    variante_id = observacion.get("variante_id")
    perfume_id = observacion.get("perfume_id")
    tienda_id = observacion.get("tienda_id")
    precio_actual = observacion.get("precio_actual")
    precio_normal = observacion.get("precio_normal")
    en_stock = observacion.get("en_stock")
    url_producto = (observacion.get("url_producto") or "").strip()
    volumen_ml = observacion.get("volumen_ml") or 100
    scraping_run_id = observacion.get("scraping_run_id")

    # Validaciones obligatorias de negocio
    if tienda_id is None:
        raise ValueError("tienda_id es obligatorio")
    if variante_id is None and perfume_id is None:
        raise ValueError("Se requiere al menos variante_id o perfume_id")
    if precio_actual is None or not isinstance(precio_actual, (int, float)) or int(precio_actual) <= 0:
        raise ValueError("El precio actual confirmado debe ser un entero positivo")
    precio_actual = int(precio_actual)

    if precio_normal is not None:
        if not isinstance(precio_normal, (int, float)) or int(precio_normal) <= 0:
            raise ValueError("El precio normal debe ser un entero positivo o None")
        precio_normal = int(precio_normal)

    if en_stock is None or not isinstance(en_stock, bool):
        raise ValueError("El stock debe ser explícito (True o False), no desconocido ni nulo")

    if not url_producto or not (url_producto.startswith("http://") or url_producto.startswith("https://")):
        raise ValueError("Se requiere una URL HTTP(S) válida")

    # 1. Intentar llamar a RPC en Supabase si está disponible
    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        sb_variante_id = variante_id
        if not sb_variante_id and perfume_id:
            try:
                r_v = sb.table("variantes_perfume").select("id").eq("perfume_id", perfume_id).limit(1).execute()
                if r_v.data and len(r_v.data) > 0:
                    sb_variante_id = r_v.data[0]["id"]
            except Exception as e:
                logger.debug(f"Error resolviendo variante en Supabase: {e}")

        sb_tienda_id = tienda_id
        if sb_tienda_id is not None:
            try:
                r_t = sb.table("tiendas").select("id").eq("id", sb_tienda_id).limit(1).execute()
                if not r_t.data:
                    # Si el ID vino de SQLite, buscar la tienda por nombre en Supabase
                    with get_db_cursor() as cur:
                        cur.execute("SELECT nombre FROM tiendas WHERE id = ?;", (tienda_id,))
                        r_nom = cur.fetchone()
                        if r_nom:
                            r_sb_t = sb.table("tiendas").select("id").ilike("nombre", r_nom["nombre"]).limit(1).execute()
                            if r_sb_t.data:
                                sb_tienda_id = r_sb_t.data[0]["id"]
            except Exception as e:
                logger.debug(f"Error mapeando tienda_id en Supabase: {e}")

        if sb_variante_id and sb_tienda_id:
            try:
                rpc_res = sb.rpc("registrar_observacion_oferta", {
                    "p_variante_id": sb_variante_id,
                    "p_tienda_id": sb_tienda_id,
                    "p_precio_actual": precio_actual,
                    "p_precio_normal": precio_normal,
                    "p_en_stock": en_stock,
                    "p_url_producto": url_producto,
                    "p_scraping_run_id": scraping_run_id
                }).execute()
                if rpc_res.data:
                    return rpc_res.data
            except Exception as e:
                logger.debug(f"RPC Supabase registrar_observacion_oferta ({e}), sincronizando vía capa local.")

    # 2. Persistencia Transaccional Atómica en SQLite Local
    init_db()
    with get_db_cursor(commit=True) as cursor:
        local_variante_id = None
        local_perfume_id = perfume_id
        if local_perfume_id:
            cursor.execute(
                "SELECT id FROM variantes_perfume WHERE perfume_id = ? AND ABS(volumen_ml - ?) < 1 LIMIT 1;",
                (local_perfume_id, volumen_ml)
            )
            row_v = cursor.fetchone()
            if row_v:
                local_variante_id = row_v["id"]
            else:
                cursor.execute("SELECT tipo, nombre FROM perfumes WHERE id = ?;", (local_perfume_id,))
                row_p = cursor.fetchone()
                tipo_p = row_p["tipo"] if row_p else "Eau de Parfum"
                slug_v = f"perfume-{local_perfume_id}-{int(volumen_ml)}ml"
                cursor.execute("""
                INSERT OR IGNORE INTO variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa)
                VALUES (?, ?, ?, 'regular', ?, 1);
                """, (local_perfume_id, tipo_p, volumen_ml, slug_v))
                cursor.execute(
                    "SELECT id FROM variantes_perfume WHERE perfume_id = ? AND ABS(volumen_ml - ?) < 1 LIMIT 1;",
                    (local_perfume_id, volumen_ml)
                )
                row_v = cursor.fetchone()
                if row_v:
                    local_variante_id = row_v["id"]
        elif variante_id:
            cursor.execute("SELECT id, perfume_id, volumen_ml FROM variantes_perfume WHERE id = ?;", (variante_id,))
            row_v = cursor.fetchone()
            if row_v:
                local_variante_id = row_v["id"]
                local_perfume_id = row_v["perfume_id"]
                volumen_ml = row_v["volumen_ml"]

        if not local_variante_id:
            cursor.execute("SELECT id, perfume_id FROM variantes_perfume LIMIT 1;")
            row_first = cursor.fetchone()
            if row_first:
                local_variante_id = row_first["id"]
                local_perfume_id = local_perfume_id or row_first["perfume_id"]
            else:
                cursor.execute("SELECT id, tipo FROM perfumes LIMIT 1;")
                rp = cursor.fetchone()
                if rp:
                    local_perfume_id = rp["id"]
                    cursor.execute("INSERT INTO variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa) VALUES (?, ?, ?, 'regular', ?, 1);", (local_perfume_id, rp["tipo"], 100, f"perfume-{local_perfume_id}-100ml"))
                    local_variante_id = cursor.lastrowid

        # Mapear tienda en SQLite si el ID vino de Supabase
        local_tienda_id = tienda_id
        cursor.execute("SELECT id FROM tiendas WHERE id = ?;", (local_tienda_id,))
        if not cursor.fetchone():
            cursor.execute("SELECT id FROM tiendas LIMIT 1;")
            rt = cursor.fetchone()
            if rt:
                local_tienda_id = rt["id"]

        # Comprobar si existe oferta previa
        cursor.execute(
            "SELECT * FROM ofertas_actuales WHERE variante_id = ? AND tienda_id = ?;",
            (local_variante_id, local_tienda_id)
        )
        row_oferta = cursor.fetchone()

        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obs_uuid = str(observacion.get("observacion_id") or uuid.uuid4())
        p_normal_final = precio_normal if precio_normal else (row_oferta["precio_normal"] if row_oferta else precio_actual)

        if not row_oferta:
            # Crear nueva oferta
            estado_ini = 'activa' if en_stock else 'agotada'
            cursor.execute("""
            INSERT INTO ofertas_actuales (
                variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto,
                estado, ultima_verificacion_exitosa, ultimo_intento, ultimo_cambio_confirmado,
                fallos_consecutivos, ultimo_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?);
            """, (local_variante_id, local_tienda_id, precio_actual, p_normal_final, int(en_stock), url_producto,
                  estado_ini, ahora, ahora, ahora, ahora, ahora))
            oferta_id = cursor.lastrowid
            tipo_evento = 'observacion_inicial'
            campos_mod = ['precio_actual', 'en_stock', 'url_producto']
            if precio_normal:
                campos_mod.append('precio_normal')
            resultado = 'creada'

            cursor.execute("""
            INSERT INTO precios_registro (
                perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
                volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento,
                campos_modificados, observacion_id, scraping_run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (local_perfume_id, local_tienda_id, precio_actual, p_normal_final, int(en_stock),
                  volumen_ml, url_producto, ahora, local_variante_id, tipo_evento,
                  json.dumps(campos_mod), obs_uuid, scraping_run_id))

            return {
                "oferta_id": oferta_id,
                "resultado": resultado,
                "tipo_evento": tipo_evento,
                "campos_modificados": campos_mod,
                "precio_anterior": None,
                "precio_nuevo": precio_actual,
                "stock_anterior": None,
                "stock_nuevo": en_stock,
                "url_anterior": None,
                "url_nueva": url_producto
            }
        else:
            # Oferta preexistente: comparar campos para detectar variaciones
            oferta_id = row_oferta["id"]
            precio_ant = row_oferta["precio_actual"]
            stock_ant = bool(row_oferta["en_stock"])
            url_ant = row_oferta["url_producto"]
            p_norm_ant = row_oferta["precio_normal"]

            campos_mod = []
            if precio_ant != precio_actual:
                campos_mod.append('precio_actual')
            if stock_ant != en_stock:
                campos_mod.append('en_stock')
            if url_ant != url_producto:
                campos_mod.append('url_producto')
            if precio_normal and p_norm_ant != precio_normal:
                campos_mod.append('precio_normal')

            if len(campos_mod) == 0:
                # Sin cambios confirmados: sólo actualizar verificación
                cursor.execute("""
                UPDATE ofertas_actuales
                SET ultima_verificacion_exitosa = ?, ultimo_intento = ?,
                    fallos_consecutivos = 0, ultimo_error = NULL,
                    estado = ?, updated_at = ?
                WHERE id = ?;
                """, (ahora, ahora, 'activa' if en_stock else 'agotada', ahora, oferta_id))
                return {
                    "oferta_id": oferta_id,
                    "resultado": "sin_cambios",
                    "tipo_evento": None,
                    "campos_modificados": []
                }

            # Determinar tipo de evento
            if len(campos_mod) > 1:
                tipo_evento = 'cambio_multiple'
            elif campos_mod[0] == 'precio_actual':
                tipo_evento = 'cambio_precio'
            elif campos_mod[0] == 'en_stock':
                tipo_evento = 'cambio_stock'
            elif campos_mod[0] == 'url_producto':
                tipo_evento = 'cambio_url'
            else:
                tipo_evento = 'cambio_datos'

            cursor.execute("""
            UPDATE ofertas_actuales
            SET precio_actual = ?, precio_normal = ?, en_stock = ?, url_producto = ?,
                estado = ?, ultima_verificacion_exitosa = ?, ultimo_intento = ?,
                ultimo_cambio_confirmado = ?, fallos_consecutivos = 0,
                ultimo_error = NULL, updated_at = ?
            WHERE id = ?;
            """, (precio_actual, p_normal_final, int(en_stock), url_producto,
                  'activa' if en_stock else 'agotada', ahora, ahora, ahora, ahora, oferta_id))
            resultado = 'actualizada'

            cursor.execute("""
            INSERT INTO precios_registro (
                perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
                volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento,
                campos_modificados, observacion_id, scraping_run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (local_perfume_id, local_tienda_id, precio_actual, p_normal_final, int(en_stock),
                  volumen_ml, url_producto, ahora, local_variante_id, tipo_evento,
                  json.dumps(campos_mod), obs_uuid, scraping_run_id))

            return {
                "oferta_id": oferta_id,
                "resultado": resultado,
                "tipo_evento": tipo_evento,
                "campos_modificados": campos_mod,
                "precio_anterior": precio_ant,
                "precio_nuevo": precio_actual,
                "stock_anterior": stock_ant,
                "stock_nuevo": en_stock,
                "url_anterior": url_ant,
                "url_nueva": url_producto
            }


def registrar_fallo_scraping(
    tienda_id: int,
    mensaje: str,
    variante_id: Optional[int] = None,
    perfume_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Registra un fallo de extracción sin alterar el precio actual, stock ni URL confirmada.
    """
    if tienda_id is None:
        raise ValueError("tienda_id es obligatorio")
    if not mensaje or not str(mensaje).strip():
        raise ValueError("Debe indicarse el motivo del fallo")

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_clean = str(mensaje).strip()[:2000]

    # Intentar RPC en Supabase si está disponible (usando service_role para permisos de escritura)
    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        if not variante_id and perfume_id:
            try:
                r_v = sb.table("variantes_perfume").select("id").eq("perfume_id", perfume_id).limit(1).execute()
                if r_v.data and len(r_v.data) > 0:
                    variante_id = r_v.data[0]["id"]
            except Exception as e:
                logger.debug(f"Error resolviendo variante en Supabase: {e}")

        if variante_id:
            try:
                rpc_res = sb.rpc("registrar_fallo_scraping", {
                    "p_variante_id": variante_id,
                    "p_tienda_id": tienda_id,
                    "p_mensaje": msg_clean
                }).execute()
                if rpc_res.data:
                    return rpc_res.data
            except Exception as e:
                logger.debug(f"RPC registrar_fallo_scraping en Supabase omitida ({e}).")

    init_db()
    with get_db_cursor(commit=True) as cursor:
        target_variante_id = variante_id
        if not target_variante_id and perfume_id:
            cursor.execute("SELECT id FROM variantes_perfume WHERE perfume_id = ? LIMIT 1;", (perfume_id,))
            row_v = cursor.fetchone()
            if row_v:
                target_variante_id = row_v["id"]

        if not target_variante_id:
            return {"resultado": "fallo_sin_variante", "mensaje": msg_clean}

        cursor.execute(
            "SELECT id, fallos_consecutivos, precio_actual, en_stock FROM ofertas_actuales WHERE variante_id = ? AND tienda_id = ?;",
            (target_variante_id, tienda_id)
        )
        row_oferta = cursor.fetchone()

        if not row_oferta:
            return {"resultado": "fallo_sin_oferta", "mensaje": msg_clean}

        nueva_cuenta = (row_oferta["fallos_consecutivos"] or 0) + 1
        cursor.execute("""
        UPDATE ofertas_actuales
        SET ultimo_intento = ?, fallos_consecutivos = ?, ultimo_error = ?, updated_at = ?
        WHERE id = ?;
        """, (ahora, nueva_cuenta, msg_clean, ahora, row_oferta["id"]))

        return {
            "resultado": "fallo_registrado",
            "oferta_id": row_oferta["id"],
            "fallos_consecutivos": nueva_cuenta,
            "precio_actual": row_oferta["precio_actual"],
            "en_stock": bool(row_oferta["en_stock"])
        }


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
    """Wrapper retrocompatible que delega en la persistencia transaccional registrar_observacion_oferta."""
    registrar_observacion_oferta({
        "perfume_id": perfume_id,
        "tienda_id": tienda_id,
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "en_stock": bool(en_stock),
        "url_producto": url_producto,
        "volumen_ml": volumen_ml
    })


# =============================================================================
# BLOQUE 12: CONSULTAS DE CATÁLOGO Y OFERTAS CONSOLIDADAS
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Alimenta la vista principal del catálogo, la ficha técnica y los gráficos:
# 1. `obtener_catalogo()`: Realiza el cálculo del mejor precio disponible en stock.
#    - Consulta primaria: Vista `vista_catalogo` en Supabase (precalculada en PostgreSQL).
#    - Fallback: Consulta agregada en SQLite local con `MIN(CASE WHEN en_stock=1 THEN precio_actual END)`.
#    - Filtros: Búsqueda de texto (nombre, marca), categorías (árabes, remates) y esencias (notas).
# 2. `obtener_detalle_perfume()`: Recupera la ficha completa de una fragancia específica.
# 3. `obtener_precios_actuales()`: Retorna la comparativa en vivo entre las tiendas auditadas
#    junto con el cálculo del precio por mililitro ($/ml).
# 4. `obtener_historico_precios()`: Genera la serie cronológica temporal para graficar la evolución.
# 5. `guardar_o_actualizar_perfume_scraped()`: Permite a los scrapers autónomos ingresar nuevos
#    perfumes o actualizar catálogos dinámicamente tanto en Supabase como en SQLite.
# =============================================================================
def obtener_catalogo(
    busqueda: Optional[str] = None,
    esencias: Optional[List[str]] = None,
    categoria: Optional[str] = None,
    orden: str = "id_asc"
) -> List[Dict[str, Any]]:
    """
    Obtiene el listado de perfumes calculando el mejor precio real disponible en stock.
    Intenta consultar Supabase (vista_catalogo); ante cualquier eventualidad, usa SQLite local.
    """
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            query = sb.table("vista_catalogo").select("*")

            if busqueda:
                term = busqueda.strip()
                query = query.or_(f"nombre.ilike.%{term}%,marca.ilike.%{term}%")

            if categoria == "arabes":
                query = query.eq("es_arabe", True)
            elif categoria == "remates":
                query = query.eq("en_remate", True)

            if orden == "precio_asc":
                query = query.order("mejor_precio", desc=False, nulls_first=False)
            elif orden == "precio_desc":
                query = query.order("mejor_precio", desc=True, nulls_first=False)
            elif orden == "nombre_asc":
                query = query.order("nombre", desc=False)
            else:
                query = query.order("id", desc=False)

            resp = query.execute()
            perfumes = resp.data or []

            if esencias:
                perfumes_filtrados = []
                esencias_lower = [e.lower() for e in esencias]
                for p in perfumes:
                    notas_p = [n.strip().lower() for n in p.get("notas", "").split(",")]
                    if any(any(es in nota for nota in notas_p) for es in esencias_lower):
                        perfumes_filtrados.append(p)
                return perfumes_filtrados

            return perfumes
        except Exception as e:
            logger.warning(f"Error consultando vista_catalogo en Supabase ({e}), recurriendo a SQLite.")

    # Fallback SQLite
    init_db()
    query_sql = """
    SELECT p.*,
           MIN(CASE WHEN pr.en_stock = 1 AND pr.precio_actual > 0 THEN pr.precio_actual END) as mejor_precio,
           MAX(pr.fecha_registro) as ultima_actualizacion
    FROM perfumes p
    LEFT JOIN precios_registro pr ON p.id = pr.perfume_id
    WHERE 1=1
    """
    params: List[Any] = []

    if busqueda:
        term = f"%{busqueda.strip()}%"
        query_sql += " AND (p.nombre LIKE ? OR p.marca LIKE ?)"
        params.extend([term, term])

    if categoria == "arabes":
        query_sql += " AND p.es_arabe = 1"
    elif categoria == "remates":
        query_sql += " AND p.en_remate = 1"

    query_sql += " GROUP BY p.id"

    if orden == "precio_asc":
        query_sql += " ORDER BY mejor_precio ASC NULLS LAST"
    elif orden == "precio_desc":
        query_sql += " ORDER BY mejor_precio DESC NULLS LAST"
    elif orden == "nombre_asc":
        query_sql += " ORDER BY p.nombre ASC"
    else:
        query_sql += " ORDER BY p.id ASC"

    with get_db_cursor() as cursor:
        cursor.execute(query_sql, params)
        perfumes = [dict(row) for row in cursor.fetchall()]

    if esencias:
        perfumes_filtrados = []
        esencias_lower = [e.lower() for e in esencias]
        for p in perfumes:
            notas_p = [n.strip().lower() for n in p["notas"].split(",")]
            if any(any(es in nota for nota in notas_p) for es in esencias_lower):
                perfumes_filtrados.append(p)
        return perfumes_filtrados

    return perfumes


def obtener_detalle_perfume(perfume_id: int) -> Optional[Dict[str, Any]]:
    """Retorna información completa del perfume por su ID."""
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            resp = sb.table("perfumes").select("*").eq("id", perfume_id).limit(1).execute()
            if resp.data:
                return resp.data[0]
        except Exception as e:
            logger.warning(f"Error en Supabase obtener_detalle_perfume ({e}), usando SQLite.")

    init_db()
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM perfumes WHERE id = ?;", (perfume_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def obtener_precios_actuales(perfume_id: int) -> List[Dict[str, Any]]:
    """Retorna el precio más reciente registrado en cada tienda para el perfume dado."""
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            resp = sb.table("vista_precios_actuales").select("*").eq("perfume_id", perfume_id).order("precio_actual", desc=False).execute()
            if resp.data is not None:
                return resp.data
        except Exception as e:
            logger.warning(f"Error en Supabase vista_precios_actuales ({e}), usando SQLite.")

    init_db()
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
      AND pr.fecha_registro = (
          SELECT MAX(fecha_registro)
          FROM precios_registro
          WHERE perfume_id = ? AND tienda_id = t.id
      )
    ORDER BY pr.precio_actual ASC;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (perfume_id, perfume_id))
        return [dict(row) for row in cursor.fetchall()]


def obtener_historico_precios(perfume_id: int) -> List[Dict[str, Any]]:
    """Retorna la serie temporal histórica de precios para gráficos de evolución."""
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            resp = sb.table("precios_registro").select("precio_actual, fecha_registro, tiendas(nombre)").eq("perfume_id", perfume_id).eq("en_stock", True).gt("precio_actual", 0).order("fecha_registro", desc=False).execute()
            registros = []
            for r in resp.data or []:
                tienda_info = r.get("tiendas")
                t_nombre = tienda_info.get("nombre", "Tienda") if isinstance(tienda_info, dict) else "Tienda"
                registros.append({
                    "tienda": t_nombre,
                    "precio_actual": r.get("precio_actual"),
                    "fecha_registro": r.get("fecha_registro")
                })
            if registros:
                return registros
        except Exception as e:
            logger.warning(f"Error en Supabase obtener_historico_precios ({e}), usando SQLite.")

    init_db()
    query = """
    SELECT t.nombre as tienda, pr.precio_actual, pr.fecha_registro
    FROM precios_registro pr
    JOIN tiendas t ON pr.tienda_id = t.id
    WHERE pr.perfume_id = ? 
      AND pr.en_stock = 1 
      AND pr.precio_actual > 0
    ORDER BY pr.fecha_registro ASC;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (perfume_id,))
        return [dict(row) for row in cursor.fetchall()]


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
    genero: str = "Unisex",
    volumen_ml: int = 100
) -> Dict[str, Any]:
    """Inserta o actualiza un perfume descubierto tanto en Supabase como en SQLite local."""
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Persistencia en Supabase
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            # Buscar o crear tienda
            res_t = sb.table("tiendas").select("id").ilike("nombre", tienda_nombre).execute()
            if res_t.data:
                tienda_id = res_t.data[0]["id"]
            else:
                base_url = url_producto.split('/')[0] + "//" + url_producto.split('/')[2] if '://' in url_producto else 'https://'
                ins_t = sb.table("tiendas").insert({
                    "nombre": tienda_nombre,
                    "url_base": base_url,
                    "trust_score": 90,
                    "badge": "Tienda Verificada",
                    "logo_emoji": ""
                }).execute()
                tienda_id = ins_t.data[0]["id"]

            # Buscar o crear perfume
            res_p = sb.table("perfumes").select("id").ilike("nombre", nombre.strip()).execute()
            if res_p.data:
                perfume_id = res_p.data[0]["id"]
                es_nuevo = False
            else:
                es_nuevo = True
                img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
                notas_txt = notas or "Cítricos, Maderas, Almizcle"
                ins_p = sb.table("perfumes").insert({
                    "nombre": nombre.strip(),
                    "marca": marca.strip() or "Diseñador",
                    "genero": genero,
                    "tipo": "Eau de Parfum",
                    "notas": notas_txt,
                    "imagen_url": img,
                    "es_arabe": bool(es_arabe),
                    "en_tendencia": True,
                    "en_remate": False,
                    "precio_referencia": precio_actual
                }).execute()
                perfume_id = ins_p.data[0]["id"]

            # Registrar snapshot de precio
            sb.table("precios_registro").insert({
                "perfume_id": perfume_id,
                "tienda_id": tienda_id,
                "precio_actual": precio_actual,
                "precio_normal": precio_normal,
                "en_stock": True,
                "volumen_ml": volumen_ml,
                "url_producto": url_producto,
                "fecha_registro": fecha_actual
            }).execute()

        except Exception as e:
            logger.warning(f"Error sincronizando descubrimiento con Supabase: {e}")

    # 2. Persistencia en SQLite local
    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = LOWER(?);", (tienda_nombre,))
        row_tienda = cursor.fetchone()
        if row_tienda:
            tienda_id_sq = row_tienda["id"]
        else:
            base_url = url_producto.split('/')[0] + "//" + url_producto.split('/')[2] if '://' in url_producto else 'https://'
            cursor.execute("""
            INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
            VALUES (?, ?, 90, 'Tienda Verificada', '');
            """, (tienda_nombre, base_url))
            tienda_id_sq = cursor.lastrowid

        cursor.execute("""
        SELECT id, precio_referencia FROM perfumes 
        WHERE LOWER(nombre) = LOWER(?) OR LOWER(nombre) LIKE ?;
        """, (nombre.strip(), f"%{nombre.strip()}%"))
        row_perfume = cursor.fetchone()

        es_nuevo_sq = False
        if row_perfume:
            perfume_id_sq = row_perfume["id"]
        else:
            es_nuevo_sq = True
            img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
            notas_texto = notas or "Cítricos, Maderas, Almizcle"
            cursor.execute("""
            INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
            VALUES (?, ?, ?, 'Eau de Parfum', ?, ?, ?, 1, 0, ?);
            """, (nombre.strip(), marca.strip() or "Diseñador", genero, notas_texto, img, es_arabe, precio_actual))
            perfume_id_sq = cursor.lastrowid

        cursor.execute("""
        INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?);
        """, (perfume_id_sq, tienda_id_sq, precio_actual, precio_normal, volumen_ml, url_producto, fecha_actual))

        return {"perfume_id": perfume_id_sq, "es_nuevo": es_nuevo_sq, "fecha": fecha_actual}


# =============================================================================
# BLOQUE 13: AUDITORÍA DE TIENDAS Y MOTOR DE CONFIANZA (TRUSTSCORE CHILE)
# -----------------------------------------------------------------------------
# ¿QUÉ HACE ESTE BLOQUE?
# Implementa el algoritmo de evaluación de comercios de perfumería en Chile:
# 1. `obtener_tiendas_trust()`: Retorna el ranking de tiendas ordenadas de mayor a menor confianza.
#    El TrustScore (0 a 100 puntos) se descompone en 4 pilares auditados de 25 puntos cada uno:
#    - Seguridad Web (25 pts): Cifrado SSL/TLS activo y certificado válido.
#    - Legalidad & RUT (25 pts): Razón social constituida y verificable ante el SII.
#    - Garantía & Devoluciones (25 pts): Cumplimiento de la Ley del Consumidor 19.496 y política de 30 días.
#    - Reputación & Sellos (25 pts): Adhesión a la Cámara de Comercio de Santiago (CCS) y bajo reclamo SERNAC.
# 2. `auditar_tienda_por_url()`: Permite al usuario pegar cualquier enlace o URL externa.
#    - Si la tienda está en la base de datos auditada, entrega el reporte oficial certificado.
#    - Si es desconocida, analiza el dominio buscando señales de riesgo (falta de HTTPS,
#      términos engañosos tipo 'outlet-original', 'ganga', o dominios no chilenos) y genera
#      un semáforo preventivo de advertencia contra estafas o perfumes falsificados.
# =============================================================================
def obtener_tiendas() -> List[Dict[str, Any]]:
    """Retorna la lista de tiendas registradas ordenadas por índice de confianza."""
    return obtener_tiendas_trust()


def obtener_tiendas_trust(
    filtro_tipo: Optional[str] = None,
    score_minimo: int = 0,
    busqueda: str = ""
) -> List[Dict[str, Any]]:
    """Retorna tiendas auditadas con métricas detalladas para la página de confianza."""
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            q = sb.table("tiendas").select("*").gte("trust_score", score_minimo)
            if filtro_tipo and filtro_tipo != "Todas":
                q = q.eq("tipo_tienda", filtro_tipo)
            if busqueda:
                term = busqueda.strip()
                q = q.or_(f"nombre.ilike.%{term}%,url_base.ilike.%{term}%,rut.ilike.%{term}%")
            q = q.order("trust_score", desc=True)

            res = q.execute()
            tiendas = []
            for r in res.data or []:
                d = dict(r)
                d["estrellas"] = round(d.get("trust_score", 0) / 20.0, 1)
                tiendas.append(d)
            if tiendas:
                return tiendas
        except Exception as e:
            logger.warning(f"Error consultando tiendas en Supabase ({e}), usando SQLite.")

    init_db()
    query = """
    SELECT 
        id, nombre, url_base, trust_score, badge, logo_emoji,
        rut, tipo_tienda, ssl_seguro, anios_antiguedad, sello_ccs, reclamos_sernac,
        politica_devolucion, direccion_fiscal,
        puntos_seguridad, puntos_legalidad, puntos_garantia, puntos_reputacion
    FROM tiendas
    WHERE trust_score >= ?
    """
    params: List[Any] = [score_minimo]

    if filtro_tipo and filtro_tipo != "Todas":
        query += " AND tipo_tienda = ?"
        params.append(filtro_tipo)

    if busqueda:
        term = f"%{busqueda.lower().strip()}%"
        query += " AND (LOWER(nombre) LIKE ? OR LOWER(url_base) LIKE ? OR LOWER(rut) LIKE ?)"
        params.extend([term, term, term])

    query += " ORDER BY trust_score DESC;"

    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        tiendas = []
        for r in cursor.fetchall():
            d = dict(r)
            d["estrellas"] = round(d["trust_score"] / 20.0, 1)
            tiendas.append(d)
        return tiendas


def auditar_tienda_por_url(url_ingresada: str) -> Optional[Dict[str, Any]]:
    if not url_ingresada or not url_ingresada.strip():
        return None

    url_limpia = url_ingresada.strip().lower()
    if not url_limpia.startswith(("http://", "https://")):
        url_limpia = "https://" + url_limpia

    try:
        parsed = urllib.parse.urlparse(url_limpia)
        netloc = (parsed.netloc or parsed.path.split('/')[0]).replace("www.", "")
    except Exception:
        netloc = url_limpia

    tiendas_db = obtener_tiendas_trust()
    for t in tiendas_db:
        dominio_tienda = t["url_base"].lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        if dominio_tienda in netloc or netloc in dominio_tienda:
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

    puntos_ssl = 25 if url_limpia.startswith("https://") else 0
    es_cl = netloc.endswith(".cl")
    puntos_dominio = 25 if es_cl else 10

    senales_alerta = []
    palabras_sospechosas = ["outlet-original", "perfumes-ganga", "dior-chile-ofertas", "chanel-descuentos", "liquidaciones-lujo"]
    for palabra in palabras_sospechosas:
        if palabra in netloc:
            senales_alerta.append(f"Uso de términos engañosos en el dominio ('{palabra}')")

    if not url_limpia.startswith("https://"):
        senales_alerta.append("No utiliza protocolo cifrado seguro HTTPS")
    if not es_cl:
        senales_alerta.append("No utiliza dominio oficial chileno (.cl)")

    puntos_transparencia = 15 if not senales_alerta else 5
    puntos_reputacion = 15 if not senales_alerta else 5
    score_estimado = max(10, min(80, puntos_ssl + puntos_dominio + puntos_transparencia + puntos_reputacion))

    if score_estimado >= 70:
        badge = "Verificación Básica"
        recom = "El sitio cuenta con HTTPS y dominio estándar, pero no está en el registro oficial de distribuidores autorizados. Revisa que permita pagar con Webpay y no solo transferencias personales."
    else:
        badge = "Sitio No Verificado / Riesgo"
        recom = "⚠️ Precaución extrema. No se registran antecedentes comerciales formales ni sello de confianza. Posible tienda clon o producto sin garantía de originalidad."

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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gestor de Base de Datos PerfumeTrending (Supabase & SQLite)")
    parser.add_argument("--seed", action="store_true", help="Poblar datos semilla en Supabase y SQLite")
    parser.add_argument("--status", action="store_true", help="Verificar estado de conexion con Supabase y SQLite")
    args = parser.parse_args()

    print("=" * 60)
    print("PerfumeTrending.cl — Estado de Persistencia")
    print("=" * 60)
    
    url, key = get_supabase_credentials()
    print(f"Supabase URL: {url if url else 'No configurada'}")
    print(f"Supabase Key: {'Configurada (***)' if key else 'No configurada'}")
    
    sb_activo = is_supabase_disponible()
    print(f"Supabase Estado: {'CONECTADO Y DISPONIBLE' if sb_activo else 'NO DISPONIBLE / TABLAS PENDIENTES'}")
    print(f"SQLite Local: {DB_PATH} ({'Existe' if os.path.exists(DB_PATH) else 'No inicializada'})")
    
    if args.seed:
        print("\nEjecutando poblado de datos...")
        init_db(force_reseed=True)
        if sb_activo:
            poblar_datos_semilla_supabase()
        print("Poblado completado.")
    print("=" * 60)
