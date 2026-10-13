"""
PerfumeTrending.cl — Capa de Persistencia y Motor de Base de Datos
==================================================================
Módulo desacoplado de acceso a datos de alto rendimiento basado en SQLite con:
- Esquema relacional DDL puro y migraciones automáticas.
- Gestión de usuarios, edición de perfil y preferencias de notificación.
- Sistema de fragancias favoritas (me gusta) y monitoreo de bajas de precio.
- Catálogo maestro y tiendas auditadas desacopladas en database/seed_catalogo.json.
- Modo WAL (Write-Ahead Logging) para concurrencia multi-hilo (Streamlit + Scraper).
- Context managers para gestión determinista de transacciones y conexiones.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
import random
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Tuple
import urllib.parse

logger = logging.getLogger("PerfumeDatabase")

# Configuración de rutas canónicas del sistema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resolver_ruta(subpath: str) -> str:
    """Busca un recurso en la raíz del proyecto o dentro de APP/"""
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

# Cache en memoria para catálogo semilla desacoplado
_SEED_CACHE: Optional[Dict[str, Any]] = None


def hash_password(password: str) -> str:
    """Genera un hash SHA-256 seguro utilizando únicamente la librería estándar."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


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


def get_connection() -> sqlite3.Connection:
    """
    Crea y configura una conexión de producción a SQLite.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_db_cursor(commit: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager transaccional determinista.
    """
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


# -----------------------------------------------------------------------------
# INICIALIZACIÓN DE ESQUEMA (DDL) Y MIGRACIONES DE USUARIOS / FAVORITOS
# -----------------------------------------------------------------------------
def init_db(force_reseed: bool = False) -> None:
    """
    Inicializa la base de datos aplicando el esquema DDL y asegurando las tablas
    de usuarios y favoritos.
    """
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
    else:
        schema_sql = ""

    with get_db_cursor(commit=True) as cursor:
        # 1. Aplicar esquema DDL base si existe
        if schema_sql:
            cursor.executescript(schema_sql)

        # 2. Migraciones defensivas para tabla precios_registro
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='precios_registro';")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(precios_registro);")
            cols = {c["name"] for c in cursor.fetchall()}
            if "volumen_ml" not in cols:
                cursor.execute("ALTER TABLE precios_registro ADD COLUMN volumen_ml INTEGER DEFAULT 100;")

        # 3. Creación de la tabla USUARIOS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            telefono TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            foto_perfil TEXT DEFAULT '',
            alerta_email INTEGER DEFAULT 1,
            umbral_descuento INTEGER DEFAULT 10,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Asegurar columnas nuevas en usuarios si la tabla ya existía
        cursor.execute("PRAGMA table_info(usuarios);")
        u_cols = {c["name"] for c in cursor.fetchall()}
        if "telefono" not in u_cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN telefono TEXT DEFAULT '';")
        if "bio" not in u_cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN bio TEXT DEFAULT '';")
        if "foto_perfil" not in u_cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT DEFAULT '';")
        if "alerta_email" not in u_cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN alerta_email INTEGER DEFAULT 1;")
        if "umbral_descuento" not in u_cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN umbral_descuento INTEGER DEFAULT 10;")

        # 4. Creación de la tabla FAVORITOS (Monitoreo de fragancias por usuario)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            perfume_id INTEGER NOT NULL,
            precio_guardado INTEGER DEFAULT 0,
            fecha_agregado DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
            FOREIGN KEY (perfume_id) REFERENCES perfumes (id) ON DELETE CASCADE,
            UNIQUE(usuario_id, perfume_id)
        );
        """)

        # 5. Población inicial si está vacía
        cursor.execute("SELECT COUNT(*) FROM perfumes;")
        row_count = cursor.fetchone()[0]
        if row_count == 0 or force_reseed:
            poblar_datos_semilla(cursor)


def poblar_datos_semilla(cursor: sqlite3.Cursor) -> None:
    """Puebla la base de datos a partir del archivo canónico seed_catalogo.json."""
    catalogo = cargar_datos_semilla_json()

    cursor.execute("DELETE FROM precios_registro;")
    cursor.execute("DELETE FROM perfumes;")
    cursor.execute("DELETE FROM tiendas;")

    # Inserción de Tiendas Auditadas
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

    # Inserción de Perfumes
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

    # Inserción de Serie Temporal Histórica de Precios por Tienda
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

    # Usuario demo inicial
    cursor.execute("""
    INSERT OR IGNORE INTO usuarios (nombre, email, password_hash, telefono, bio, foto_perfil, alerta_email, umbral_descuento)
    VALUES ('Carlos Mendoza', 'carlos.mendoza@ejemplo.cl', ?, '+56 9 8765 4321', 
            'Coleccionista de perfumes de nicho y de diseñador.', 
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&q=80', 1, 10);
    """, (hash_password("123456"),))


# -----------------------------------------------------------------------------
# AUTENTICACIÓN, USUARIOS Y PERFIL
# -----------------------------------------------------------------------------
def crear_usuario(
    nombre: str,
    email: str,
    password: str,
    telefono: str = "",
    bio: str = "",
    foto_perfil: str = ""
) -> Tuple[bool, str]:
    """Registra un nuevo usuario en la plataforma."""
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
    """Valida credenciales de acceso y retorna la información completa del usuario."""
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
    """Consulta el perfil completo de un usuario por su ID o Correo."""
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
    """Guarda si el usuario quiere recibir alertas al Gmail y el % mínimo de descuento."""
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


# -----------------------------------------------------------------------------
# FRAGANCIAS FAVORITAS Y MONITOREO DE PRECIOS
# -----------------------------------------------------------------------------
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
    Función utilizada por el backend / scraper / cronjob para determinar qué usuarios
    deben recibir un correo electrónico al haberse detectado una baja de precio.
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


# -----------------------------------------------------------------------------
# CONSULTAS DE DOMINIO Y ACCESO A DATOS ORIGINALES (MANTENIDOS)
# -----------------------------------------------------------------------------
def obtener_url_directa_tienda(perfume_id: int, tienda_nombre: str) -> Optional[Tuple[str, int, int, int]]:
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
    if fecha is None:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
        INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (perfume_id, tienda_id, precio_actual, precio_normal, int(en_stock), volumen_ml, url_producto, fecha))


def obtener_catalogo(
    busqueda: Optional[str] = None,
    esencias: Optional[List[str]] = None,
    categoria: Optional[str] = None,
    orden: str = "id_asc"
) -> List[Dict[str, Any]]:
    init_db()
    query = """
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
        query += " AND (p.nombre LIKE ? OR p.marca LIKE ?)"
        params.extend([term, term])

    if categoria == "arabes":
        query += " AND p.es_arabe = 1"
    elif categoria == "remates":
        query += " AND p.en_remate = 1"

    query += " GROUP BY p.id"

    if orden == "precio_asc":
        query += " ORDER BY mejor_precio ASC NULLS LAST"
    elif orden == "precio_desc":
        query += " ORDER BY mejor_precio DESC NULLS LAST"
    elif orden == "nombre_asc":
        query += " ORDER BY p.nombre ASC"
    else:
        query += " ORDER BY p.id ASC"

    with get_db_cursor() as cursor:
        cursor.execute(query, params)
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
    init_db()
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM perfumes WHERE id = ?;", (perfume_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def obtener_precios_actuales(perfume_id: int) -> List[Dict[str, Any]]:
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
    genero: str = "Unisex"
) -> Dict[str, Any]:
    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = LOWER(?);", (tienda_nombre,))
        row_tienda = cursor.fetchone()
        if row_tienda:
            tienda_id = row_tienda["id"]
        else:
            base_url = url_producto.split('/')[0] + "//" + url_producto.split('/')[2] if '://' in url_producto else 'https://'
            cursor.execute("""
            INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
            VALUES (?, ?, 90, 'Tienda Verificada', '');
            """, (tienda_nombre, base_url))
            tienda_id = cursor.lastrowid

        cursor.execute("""
        SELECT id, precio_referencia FROM perfumes 
        WHERE LOWER(nombre) = LOWER(?) OR LOWER(nombre) LIKE ?;
        """, (nombre.strip(), f"%{nombre.strip()}%"))
        row_perfume = cursor.fetchone()

        es_nuevo = False
        if row_perfume:
            perfume_id = row_perfume["id"]
        else:
            es_nuevo = True
            img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
            notas_texto = notas or "Cítricos, Maderas, Almizcle"
            cursor.execute("""
            INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
            VALUES (?, ?, ?, 'Eau de Parfum', ?, ?, ?, 1, 0, ?);
            """, (nombre.strip(), marca.strip() or "Diseñador", genero, notas_texto, img, es_arabe, precio_actual))
            perfume_id = cursor.lastrowid

        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO precios_registro (perfume_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto, fecha_registro)
        VALUES (?, ?, ?, ?, 1, ?, ?);
        """, (perfume_id, tienda_id, precio_actual, precio_normal, url_producto, fecha_actual))

        return {"perfume_id": perfume_id, "es_nuevo": es_nuevo, "fecha": fecha_actual}


def obtener_tiendas() -> List[Dict[str, Any]]:
    init_db()
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM tiendas ORDER BY trust_score DESC;")
        return [dict(row) for row in cursor.fetchall()]


def obtener_tiendas_trust(
    filtro_tipo: Optional[str] = None,
    score_minimo: int = 0,
    busqueda: str = ""
) -> List[Dict[str, Any]]:
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
