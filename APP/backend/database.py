"""
PerfumeTrending.cl — Capa de Persistencia y Motor de Base de Datos (Supabase + SQLite Fallback)
=============================================================================================
Módulo desacoplado de acceso a datos de nivel de producción con:
- Motor primario: Supabase (PostgreSQL 15+ en la nube con PostgREST, RLS y GoTrue Auth).
- Motor de resiliencia: SQLite local con modo WAL y contraseñas con PBKDF2-HMAC-SHA256.
- Paginación automática PostgREST (>1.000 registros) para catálogos completos sin truncamiento.
- Persistencia transaccional atómica sin corrupción de variantes ni split-brain silencioso.
"""

import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple
import urllib.parse
import uuid

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

try:
    from backend.normalizador import (
        detectar_formato_oferta,
        limpiar_nombre_perfume,
        normalizar_marca_canonica,
    )
except ImportError:
    try:
        from APP.backend.normalizador import (
            detectar_formato_oferta,
            limpiar_nombre_perfume,
            normalizar_marca_canonica,
        )
    except ImportError:
        def detectar_formato_oferta(titulo: str, url: str = "") -> str:
            return "tester" if "tester" in f"{titulo} {url}".lower() else "regular"

        def limpiar_nombre_perfume(titulo: str, marca: str = "") -> str:
            return (titulo or "").strip()

        def normalizar_marca_canonica(marca: str) -> str:
            return (marca or "").strip()

logger = logging.getLogger("PerfumeDatabase")

# =============================================================================
# BLOQUE 1: RESOLUCIÓN DE RUTAS DEL SISTEMA Y ARCHIVOS CANÓNICOS
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolver_ruta(subpath: str) -> str:
    """Resuelve la ruta absoluta de un recurso del proyecto independientemente del cwd."""
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

_SEED_CACHE: Optional[Dict[str, Any]] = None
_INITIALIZED_DB_PATHS: Set[str] = set()
_CATALOGO_CACHE: Dict[Tuple[Any, ...], Tuple[float, List[Dict[str, Any]]]] = {}
CATALOGO_CACHE_TTL_SECONDS = 30.0


def limpiar_cache_catalogo() -> None:
    """Invalida la caché en memoria del catálogo tras escrituras o actualizaciones."""
    _CATALOGO_CACHE.clear()


# =============================================================================
# BLOQUE 2: SEGURIDAD Y HASHING CRIPTOGRÁFICO DE CONTRASEÑAS (PBKDF2-HMAC-SHA256)
# =============================================================================
PBKDF2_ITERATIONS = 600_000


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Genera un hash seguro con sal criptográfica mediante PBKDF2-HMAC-SHA256 (OWASP 600k iteraciones).
    Formato: pbkdf2_sha256$<iteraciones>$<salt_hex>$<dk_hex>
    """
    salt_hex = salt if (salt and len(salt) >= 16) else secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_hex}${dk}"


def verify_password_hash(password: str, stored_hash: str) -> Tuple[bool, bool]:
    """
    Verifica una contraseña en tiempo constante (`hmac.compare_digest`).
    Retorna `(es_valida, requiere_rehash)`.
    Soporta hashes modernos `pbkdf2_sha256$...` y migración transparente de SHA-256 legado.
    """
    if not password or not stored_hash:
        return False, False

    if stored_hash.startswith("pbkdf2_sha256$"):
        partes = stored_hash.split("$")
        if len(partes) != 4:
            return False, False
        try:
            iters = int(partes[1])
            salt_hex = partes[2]
            expected_hex = partes[3]
            cand_hex = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                iters,
            ).hex()
            es_valida = hmac.compare_digest(cand_hex, expected_hex)
            return es_valida, (es_valida and iters < PBKDF2_ITERATIONS)
        except (ValueError, TypeError):
            return False, False

    # Compatibilidad con hashes SHA-256 hexadecimales legados (64 caracteres) -> fuerza rehash
    if len(stored_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in stored_hash):
        legacy_cand = hashlib.sha256(password.encode("utf-8")).hexdigest()
        es_valida = hmac.compare_digest(legacy_cand, stored_hash.lower())
        return es_valida, es_valida

    return False, False


# =============================================================================
# BLOQUE 3: CARGA Y CACHÉ DEL CATÁLOGO MAESTRO (JSON SEED)
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


# =============================================================================
# BLOQUE 4: GESTIÓN SEGURA DE CREDENCIALES DE SUPABASE (SIN SECRETOS HARDCODEADOS)
# =============================================================================
_SUPABASE_CLIENT = None
_SUPABASE_SERVICE_CLIENT = None
_SUPABASE_VERIFICADO = False


def _leer_secrets_toml(ruta: str) -> Dict[str, str]:
    """Lee un archivo TOML de secretos de forma segura sin exponer su contenido."""
    if not os.path.exists(ruta):
        return {}
    try:
        if tomllib is not None:
            with open(ruta, "rb") as fb:
                parsed = tomllib.load(fb)
                return {str(k): str(v).strip() for k, v in parsed.items() if isinstance(v, (str, int, float))}
    except Exception:
        pass

    resultado: Dict[str, str] = {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    resultado[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return resultado


def _obtener_mapa_credenciales() -> Dict[str, str]:
    """Consolida variables de entorno, secrets.toml locales y st.secrets."""
    creds: Dict[str, str] = {}

    for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        val = os.environ.get(k)
        if val and val.strip():
            creds[k] = val.strip()

    if len(creds) < 3:
        candidatos = [
            os.path.join(BASE_DIR, ".streamlit", "secrets.toml"),
            os.path.join(BASE_DIR, "APP", ".streamlit", "secrets.toml"),
            os.path.join(os.path.dirname(BASE_DIR), ".streamlit", "secrets.toml"),
        ]
        for ruta in candidatos:
            archivo_creds = _leer_secrets_toml(ruta)
            for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
                if k not in creds and archivo_creds.get(k):
                    creds[k] = archivo_creds[k]

    if len(creds) < 3:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
                    if k not in creds and k in st.secrets and st.secrets[k]:
                        creds[k] = str(st.secrets[k]).strip()
        except Exception:
            pass

    return creds


def has_service_role_key() -> bool:
    """Indica si existe SUPABASE_SERVICE_ROLE_KEY configurada sin exponer su valor."""
    creds = _obtener_mapa_credenciales()
    return bool(creds.get("SUPABASE_URL") and creds.get("SUPABASE_SERVICE_ROLE_KEY"))


def get_supabase_credentials(prefer_service_role: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtiene las credenciales de Supabase estrictamente desde entorno, secrets.toml o st.secrets.
    No contiene ningún JWT ni URL hardcodeada en el código fuente.
    """
    creds = _obtener_mapa_credenciales()
    url = creds.get("SUPABASE_URL")
    if prefer_service_role:
        key = creds.get("SUPABASE_SERVICE_ROLE_KEY") or creds.get("SUPABASE_KEY")
    else:
        key = creds.get("SUPABASE_KEY") or creds.get("SUPABASE_SERVICE_ROLE_KEY")
    return (url or None), (key or None)


# =============================================================================
# BLOQUE 5: CLIENTE SUPABASE (SINGLETON) Y UTILIDAD DE PAGINACIÓN POSTGREST
# =============================================================================
def get_supabase(use_service_role: bool = False):
    """Retorna una instancia singleton del cliente Supabase."""
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
        sb.table("tiendas").select("id").limit(1).execute()
        _SUPABASE_VERIFICADO = True
        return True
    except Exception as e:
        logger.debug(f"Supabase no disponible, activando modo SQLite local: {e}")
        return False


def _fetch_all_rows(query_factory: Callable[[int, int], Any], page_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Itera automáticamente con `.range(offset, offset + page_size - 1)` sobre PostgREST
    para superar el límite por defecto de 1.000 filas sin truncar resultados.
    """
    acumulado: List[Dict[str, Any]] = []
    offset = 0
    while True:
        resp = query_factory(offset, page_size).execute()
        lote = resp.data or []
        acumulado.extend(lote)
        if len(lote) < page_size:
            break
        offset += page_size
    return acumulado


# =============================================================================
# BLOQUE 6: MOTOR DE RESILIENCIA LOCAL (SQLITE CON MODO WAL Y CONCURRENCIA)
# =============================================================================
def get_connection() -> sqlite3.Connection:
    """Crea y configura una conexión local a SQLite en modo WAL."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_db_cursor(commit: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager transaccional determinista para SQLite con auto-commit y rollback."""
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
# BLOQUE 7: INICIALIZACIÓN DE ESQUEMA (IDEMPOTENTE UNA SOLA VEZ POR PROCESO)
# =============================================================================
def init_db(force_reseed: bool = False) -> None:
    """
    Inicializa el esquema SQLite una única vez por ruta `DB_PATH` en el ciclo de vida del proceso,
    eliminando la sobrecarga de re-ejecutar `executescript(schema.sql)` en cada consulta.
    """
    abs_db_path = os.path.abspath(DB_PATH)
    if not force_reseed and abs_db_path in _INITIALIZED_DB_PATHS and os.path.exists(abs_db_path):
        return

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
                    ("scraping_run_id", "INTEGER"),
                ]:
                    if col_name not in cols:
                        cursor.execute(f"ALTER TABLE precios_registro ADD COLUMN {col_name} {col_def};")

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(usuarios);")
                u_cols = {c["name"] for c in cursor.fetchall()}
                for col_name, col_def in [
                    ("ubicacion", "TEXT DEFAULT 'Santiago, Chile'"),
                    ("notif_stock", "BOOLEAN DEFAULT 1"),
                    ("notif_resumen", "BOOLEAN DEFAULT 0"),
                ]:
                    if col_name not in u_cols:
                        cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_def};")

            cursor.executescript(schema_sql)

            cursor.execute("SELECT COUNT(*) FROM perfumes;")
            row_count = cursor.fetchone()[0]
            if row_count == 0 or force_reseed:
                poblar_datos_semilla(cursor)

        _INITIALIZED_DB_PATHS.add(abs_db_path)

    sb = get_supabase(use_service_role=True) or get_supabase()
    if sb and is_supabase_disponible():
        try:
            res = sb.table("perfumes").select("id", count="exact").limit(1).execute()
            if (res.count is not None and res.count == 0) or force_reseed:
                poblar_datos_semilla_supabase()
        except Exception as e:
            logger.debug(f"Aviso al verificar catálogo en Supabase: {e}")


def poblar_datos_semilla(cursor: sqlite3.Cursor) -> None:
    """Puebla SQLite a partir de seed_catalogo.json con snapshots reales (sin fluctuaciones falsas)."""
    catalogo = cargar_datos_semilla_json()

    cursor.execute("DELETE FROM ofertas_actuales;")
    cursor.execute("DELETE FROM precios_registro;")
    cursor.execute("DELETE FROM variantes_perfume;")
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
            t.get("puntos_legalidad", 25), t.get("puntos_garantia", 20), t.get("puntos_reputacion", 20),
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
            int(p.get("en_remate", False)), p["precio_referencia"],
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

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    registros_precios = []

    for p in perfumes_data:
        p_id = p["id"]
        tipo_p = p.get("tipo", "Eau de Parfum")
        for enlace in p.get("enlaces_tiendas", []):
            t_nombre = enlace.get("tienda")
            if t_nombre not in tiendas_map:
                continue
            t_id = tiendas_map[t_nombre]
            precio_act = int(enlace.get("precio_actual", p["precio_referencia"]))
            p_normal_val = enlace.get("precio_normal")
            precio_norm = int(p_normal_val) if (p_normal_val and int(p_normal_val) > precio_act) else precio_act
            url_prod = enlace.get("url_producto", "")
            vol_ml = int(enlace.get("volumen_ml", p.get("volumen_ml", 100)))
            formato = detectar_formato_oferta(p["nombre"], url_prod)
            slug_v = f"perfume-{p_id}-{vol_ml}ml" if formato == "regular" else f"perfume-{p_id}-{vol_ml}ml-{formato}"

            cursor.execute(
                "INSERT OR IGNORE INTO variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa) VALUES (?, ?, ?, ?, ?, 1);",
                (p_id, tipo_p, vol_ml, formato, slug_v),
            )
            cursor.execute("SELECT id FROM variantes_perfume WHERE slug = ?;", (slug_v,))
            rv = cursor.fetchone()
            var_id = rv["id"] if rv else None

            if var_id:
                cursor.execute("""
                INSERT OR REPLACE INTO ofertas_actuales (
                    variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto,
                    estado, ultima_verificacion_exitosa, ultimo_intento, ultimo_cambio_confirmado,
                    fallos_consecutivos, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, 'activa', ?, ?, ?, 0, ?, ?);
                """, (var_id, t_id, precio_act, precio_norm, url_prod, ahora, ahora, ahora, ahora, ahora))

            registros_precios.append((
                p_id, t_id, precio_act, precio_norm, 1, vol_ml, url_prod, ahora, var_id, "observacion_inicial"
            ))

    cursor.executemany("""
    INSERT INTO precios_registro (
        perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
        volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, registros_precios)

    limpiar_cache_catalogo()
    logger.info(
        f"SQLite poblado: {len(perfumes_tuples)} perfumes, {len(tiendas_tuples)} tiendas, {len(registros_precios)} observaciones."
    )


def poblar_datos_semilla_supabase() -> bool:
    """Puebla Supabase con tiendas, perfumes y observaciones reales usando service_role."""
    sb = get_supabase(use_service_role=True)
    if not sb:
        logger.warning("Se requiere SUPABASE_SERVICE_ROLE_KEY para poblar datos semilla en Supabase.")
        return False

    catalogo = cargar_datos_semilla_json()
    tiendas_data = catalogo.get("tiendas", [])
    tiendas_inserts = [
        {
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
            "puntos_reputacion": t.get("puntos_reputacion", 20),
        }
        for t in tiendas_data
    ]

    try:
        sb.table("tiendas").upsert(tiendas_inserts, on_conflict="nombre").execute()
    except Exception as e:
        logger.error(f"Error insertando tiendas en Supabase: {e}")
        return False

    resp_tiendas = sb.table("tiendas").select("id, nombre").execute()
    tiendas_map = {r["nombre"]: r["id"] for r in (resp_tiendas.data or [])}

    perfumes_data = catalogo.get("perfumes", [])
    perfumes_inserts = [
        {
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
            "precio_referencia": p["precio_referencia"],
        }
        for p in perfumes_data
    ]

    try:
        sb.table("perfumes").upsert(perfumes_inserts, on_conflict="id").execute()
    except Exception as e:
        logger.error(f"Error insertando perfumes en Supabase: {e}")
        return False

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    precios_inserts = []
    for p in perfumes_data:
        p_id = p["id"]
        for enlace in p.get("enlaces_tiendas", []):
            t_nombre = enlace.get("tienda")
            if t_nombre not in tiendas_map:
                continue
            t_id = tiendas_map[t_nombre]
            precio_act = int(enlace.get("precio_actual", p["precio_referencia"]))
            p_normal_val = enlace.get("precio_normal")
            precio_norm = int(p_normal_val) if (p_normal_val and int(p_normal_val) > precio_act) else precio_act
            url_prod = enlace.get("url_producto", "")
            vol_ml = int(enlace.get("volumen_ml", p.get("volumen_ml", 100)))
            precios_inserts.append({
                "perfume_id": p_id,
                "tienda_id": t_id,
                "precio_actual": precio_act,
                "precio_normal": precio_norm,
                "en_stock": True,
                "volumen_ml": vol_ml,
                "url_producto": url_prod,
                "fecha_registro": ahora,
            })

    try:
        for chunk_idx in range(0, len(precios_inserts), 100):
            sb.table("precios_registro").insert(precios_inserts[chunk_idx:chunk_idx + 100]).execute()
        limpiar_cache_catalogo()
        return True
    except Exception as e:
        logger.error(f"Error insertando precios semilla en Supabase: {e}")
        return False


# =============================================================================
# BLOQUE 8: AUTENTICACIÓN HÍBRIDA CLOUD (SUPABASE GOTRUE) + SQLITE PBKDF2
# =============================================================================
def _es_uuid(valor: Any) -> bool:
    s = str(valor or "").strip()
    if len(s) != 36 or "-" not in s:
        return False
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False


def _obtener_admin_auth():
    """Retorna el cliente Supabase con privilegios Admin Auth si está disponible."""
    if not is_supabase_disponible() or not has_service_role_key():
        return None
    sb_srv = get_supabase(use_service_role=True)
    if sb_srv and hasattr(sb_srv, "auth") and hasattr(sb_srv.auth, "admin"):
        return sb_srv
    return None


def _buscar_usuario_cloud(sb_srv, usuario_id_o_email: Any, email_fallback: Optional[str] = None):
    """Resuelve un usuario en Supabase Auth (`auth.users`) por UUID o por correo electrónico."""
    if usuario_id_o_email is not None and _es_uuid(usuario_id_o_email):
        try:
            resp = sb_srv.auth.admin.get_user_by_id(str(usuario_id_o_email).strip())
            user_obj = getattr(resp, "user", None)
            if user_obj:
                return user_obj
        except Exception:
            pass

    target_email = (
        str(email_fallback).strip().lower()
        if email_fallback
        else (str(usuario_id_o_email).strip().lower() if "@" in str(usuario_id_o_email or "") else "")
    )
    if not target_email:
        return None

    try:
        page = 1
        while page <= 10:
            users_resp = sb_srv.auth.admin.list_users(page=page, per_page=200)
            users_list = users_resp if isinstance(users_resp, list) else getattr(users_resp, "users", []) or []
            for u in users_list:
                if (getattr(u, "email", "") or "").strip().lower() == target_email:
                    return u
            if len(users_list) < 200:
                break
            page += 1
    except Exception as e:
        logger.debug(f"No se pudo listar usuarios en Supabase Auth: {e}")
    return None


def _normalizar_usuario_cloud(user_obj) -> Dict[str, Any]:
    """Convierte un objeto `User` de Supabase GoTrue al diccionario estándar de la aplicación."""
    meta = dict(getattr(user_obj, "user_metadata", None) or {})
    email_val = (getattr(user_obj, "email", "") or "").strip().lower()
    favs_raw = meta.get("favoritos") or {}
    fav_ids: List[int] = []
    if isinstance(favs_raw, dict):
        for k in favs_raw.keys():
            if str(k).isdigit():
                fav_ids.append(int(k))
    elif isinstance(favs_raw, list):
        fav_ids = [int(x) for x in favs_raw if str(x).isdigit()]

    return {
        "id": str(getattr(user_obj, "id", "")),
        "nombre": str(meta.get("nombre") or (email_val.split("@")[0] if email_val else "Usuario")).strip(),
        "email": email_val,
        "telefono": str(meta.get("telefono") or "").strip(),
        "ubicacion": str(meta.get("ubicacion") or "Santiago, Chile").strip(),
        "bio": str(meta.get("bio") or "").strip(),
        "foto_perfil": str(meta.get("foto_perfil") or "").strip(),
        "alerta_email": bool(meta.get("alerta_email", True)),
        "notif_stock": bool(meta.get("notif_stock", True)),
        "notif_resumen": bool(meta.get("notif_resumen", False)),
        "umbral_descuento": int(meta.get("umbral_descuento", 10)),
        "favoritos": fav_ids,
    }


def crear_usuario(
    nombre: str,
    email: str,
    password: str,
    telefono: str = "",
    bio: str = "",
    foto_perfil: str = "",
    ubicacion: str = "Santiago, Chile",
) -> Tuple[bool, str]:
    """
    Registra un nuevo usuario de forma persistente:
    - En producción (Supabase disponible): crea el usuario en `auth.users` con bcrypt nativo de GoTrue
      y almacena sus atributos de perfil en `user_metadata` (sobreviviendo reinicios de Streamlit Cloud).
    - En respaldo local (SQLite): almacena el hash con `PBKDF2-HMAC-SHA256` (600.000 iteraciones + salt).
    """
    nombre_clean = (nombre or "").strip()
    email_clean = (email or "").strip().lower()
    if not nombre_clean or not email_clean or "@" not in email_clean:
        return False, "Debes ingresar un nombre y correo electrónico válidos."
    if not password or len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."

    foto_limpia = (foto_perfil or "").strip()
    if foto_limpia and not foto_limpia.lower().startswith("https://"):
        foto_limpia = ""

    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        existente = _buscar_usuario_cloud(sb_srv, email_clean)
        if existente is not None:
            return False, "El correo electrónico ya se encuentra registrado."

        metadata = {
            "nombre": nombre_clean,
            "telefono": (telefono or "").strip(),
            "ubicacion": (ubicacion or "Santiago, Chile").strip(),
            "bio": (bio or "").strip(),
            "foto_perfil": foto_limpia,
            "alerta_email": True,
            "notif_stock": True,
            "notif_resumen": False,
            "umbral_descuento": 10,
            "favoritos": {},
        }
        try:
            resp = sb_srv.auth.admin.create_user({
                "email": email_clean,
                "password": password,
                "email_confirm": True,
                "user_metadata": metadata,
            })
            user_obj = getattr(resp, "user", None)
            if user_obj is not None:
                # Si la tabla perfiles_usuario ya existe en PostgreSQL, sincronizarla silenciosamente
                try:
                    sb_srv.table("perfiles_usuario").upsert({
                        "id": str(user_obj.id),
                        "nombre": nombre_clean,
                        "email": email_clean,
                        "telefono": metadata["telefono"],
                        "ubicacion": metadata["ubicacion"],
                        "bio": metadata["bio"],
                        "foto_perfil": foto_limpia,
                        "alerta_email": True,
                        "notif_stock": True,
                        "notif_resumen": False,
                        "umbral_descuento": 10,
                    }, on_conflict="id").execute()
                except Exception:
                    pass
                return True, "Cuenta creada exitosamente."
        except Exception as e:
            err_txt = str(e).lower()
            if "already" in err_txt or "exists" in err_txt or "registered" in err_txt:
                return False, "El correo electrónico ya se encuentra registrado."
            logger.error(f"Error registrando usuario en Supabase Auth: {e}")
            return False, "No fue posible crear la cuenta en este momento. Intenta nuevamente."

    # Si Supabase está disponible pero el entorno solo tiene clave pública anon (sin service_role),
    # registrar igualmente en GoTrue mediante sign_up aislado para no perder cuentas en contenedores efímeros.
    if is_supabase_disponible():
        url_pub, anon_key = get_supabase_credentials(prefer_service_role=False)
        if url_pub and anon_key:
            metadata_pub = {
                "nombre": nombre_clean,
                "telefono": (telefono or "").strip(),
                "ubicacion": (ubicacion or "Santiago, Chile").strip(),
                "bio": (bio or "").strip(),
                "foto_perfil": foto_limpia,
                "alerta_email": True,
                "notif_stock": True,
                "notif_resumen": False,
                "umbral_descuento": 10,
                "favoritos": {},
            }
            try:
                from supabase import create_client
                transient_signup = create_client(url_pub, anon_key)
                resp_su = transient_signup.auth.sign_up({
                    "email": email_clean,
                    "password": password,
                    "options": {"data": metadata_pub},
                })
                if getattr(resp_su, "user", None) is not None:
                    try:
                        transient_signup.auth.sign_out()
                    except Exception:
                        pass
                    return True, "Cuenta creada exitosamente."
            except Exception as e:
                err_su = str(e).lower()
                if "already" in err_su or "exists" in err_su or "registered" in err_su:
                    return False, "El correo electrónico ya se encuentra registrado."
                logger.error(f"Error en sign_up público de Supabase Auth: {e}")
                return False, "No fue posible crear la cuenta en este momento. Intenta nuevamente."

    # Respaldo SQLite local (modo offline / desarrollo sin red)
    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ?;", (email_clean,))
        if cursor.fetchone():
            return False, "El correo electrónico ya se encuentra registrado."

        pwd_hash = hash_password(password)
        cursor.execute("""
        INSERT INTO usuarios (
            nombre, email, password_hash, telefono, ubicacion, bio, foto_perfil,
            alerta_email, notif_stock, notif_resumen, umbral_descuento
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 0, 10);
        """, (
            nombre_clean,
            email_clean,
            pwd_hash,
            (telefono or "").strip(),
            (ubicacion or "Santiago, Chile").strip(),
            (bio or "").strip(),
            foto_limpia,
        ))
        return True, "Cuenta creada exitosamente."


def verificar_usuario(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Autentica al usuario verificando sus credenciales:
    - En modo Supabase: usa un cliente efímero aislado (`sign_in_with_password`) para no contaminar
      las cabeceras JWT del cliente singleton compartido.
    - En modo SQLite: verifica con `verify_password_hash` en tiempo constante y actualiza
      automáticamente hashes SHA-256 antiguos a `PBKDF2-HMAC-SHA256`.
    """
    email_clean = (email or "").strip().lower()
    if not email_clean or not password:
        return False, None

    if is_supabase_disponible():
        url, anon_key = get_supabase_credentials(prefer_service_role=False)
        if url and anon_key:
            try:
                from supabase import create_client
                transient_client = create_client(url, anon_key)
                auth_resp = transient_client.auth.sign_in_with_password({
                    "email": email_clean,
                    "password": password,
                })
                user_obj = getattr(auth_resp, "user", None)
                if user_obj is not None:
                    u_data = _normalizar_usuario_cloud(user_obj)
                    try:
                        transient_client.auth.sign_out()
                    except Exception:
                        pass
                    return True, u_data
            except Exception:
                # Si no autenticó en GoTrue, revisar únicamente si existe cuenta local legado en SQLite
                pass

    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(email) = ?;", (email_clean,))
        row = cursor.fetchone()
        if not row:
            return False, None

        es_valida, requiere_rehash = verify_password_hash(password, row["password_hash"])
        if not es_valida:
            return False, None

        if requiere_rehash:
            nuevo_hash = hash_password(password)
            cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?;", (nuevo_hash, row["id"]))

        u_data = dict(row)
        u_data.pop("password_hash", None)
        u_data["alerta_email"] = bool(u_data.get("alerta_email", True))
        u_data["notif_stock"] = bool(u_data.get("notif_stock", True))
        u_data["notif_resumen"] = bool(u_data.get("notif_resumen", False))
        u_data["ubicacion"] = u_data.get("ubicacion") or "Santiago, Chile"
        cursor.execute("SELECT perfume_id FROM favoritos WHERE usuario_id = ?;", (row["id"],))
        u_data["favoritos"] = [int(r["perfume_id"]) for r in cursor.fetchall()]
        return True, u_data


def obtener_perfil_usuario(usuario_id_o_email: Any) -> Optional[Dict[str, Any]]:
    """Consulta el perfil completo de un usuario por UUID, ID entero o correo electrónico."""
    if usuario_id_o_email is None:
        return None

    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        if user_obj is not None:
            return _normalizar_usuario_cloud(user_obj)

    init_db()
    with get_db_cursor() as cursor:
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            cursor.execute("SELECT * FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            cursor.execute(
                "SELECT * FROM usuarios WHERE LOWER(email) = ?;",
                (str(usuario_id_o_email).strip().lower(),),
            )

        row = cursor.fetchone()
        if row:
            u_data = dict(row)
            u_data.pop("password_hash", None)
            u_data["alerta_email"] = bool(u_data.get("alerta_email", True))
            u_data["notif_stock"] = bool(u_data.get("notif_stock", True))
            u_data["notif_resumen"] = bool(u_data.get("notif_resumen", False))
            u_data["ubicacion"] = u_data.get("ubicacion") or "Santiago, Chile"
            return u_data
        return None


def subir_avatar_usuario(
    usuario_id_o_email: Any,
    file_bytes: bytes,
    mime_type: str = "",
) -> Tuple[bool, str]:
    """
    Valida criptográficamente el formato binario (magic bytes) de una imagen subida por el usuario
    y la publica en Supabase Storage (`IMG_perfumes/avatars/`) mediante `service_role`, retornando
    su URL HTTPS pública limpia (o un Data URI acotado solo en modo offline SQLite).
    """
    if not file_bytes or not isinstance(file_bytes, (bytes, bytearray)):
        return False, "No se recibió un archivo de imagen válido."
    if len(file_bytes) > 2 * 1024 * 1024:
        return False, "El archivo supera el tamaño máximo permitido (2 MB)."

    raw = bytes(file_bytes)
    detected_mime = ""
    ext = ""
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime, ext = "image/png", "png"
    elif raw.startswith(b"\xff\xd8\xff"):
        detected_mime, ext = "image/jpeg", "jpg"
    elif raw.startswith((b"GIF87a", b"GIF89a")):
        detected_mime, ext = "image/gif", "gif"
    elif len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        detected_mime, ext = "image/webp", "webp"
    else:
        return False, "Formato de archivo rechazado. Solo se admiten imágenes PNG, JPG, WEBP o GIF auténticas."

    safe_owner = hashlib.sha256(str(usuario_id_o_email).strip().lower().encode("utf-8")).hexdigest()[:16]
    storage_path = f"avatars/{safe_owner}_{int(time.time())}.{ext}"

    sb_srv = get_supabase(use_service_role=True)
    if sb_srv is not None and is_supabase_disponible():
        try:
            bucket = sb_srv.storage.from_("IMG_perfumes")
            bucket.upload(
                path=storage_path,
                file=raw,
                file_options={"content-type": detected_mime, "upsert": "true"},
            )
            public_url = bucket.get_public_url(storage_path)
            if isinstance(public_url, str) and public_url.startswith("https://"):
                return True, public_url
        except Exception as e:
            logger.error(f"Error subiendo avatar a Supabase Storage: {e}")
            return False, "No fue posible almacenar la fotografía en la nube en este momento."

    if len(raw) > 380 * 1024:
        return False, "En modo local sin conexión, la imagen de avatar no debe superar los 380 KB."
    b64_str = base64.b64encode(raw).decode("ascii")
    return True, f"data:{detected_mime};base64,{b64_str}"


def actualizar_perfil_usuario(
    usuario_id_o_email: Any,
    nombre: str,
    email: str,
    telefono: str,
    bio: str,
    foto_perfil: str,
    ubicacion: Optional[str] = None,
) -> Tuple[bool, str]:
    """Actualiza de forma persistente la información personal del usuario en Supabase Auth o SQLite."""
    nombre_clean = (nombre or "").strip()
    email_clean = (email or "").strip().lower()
    tel_clean = (telefono or "").strip()
    bio_clean = (bio or "").strip()
    foto_clean = (foto_perfil or "").strip()

    if not nombre_clean or not email_clean or "@" not in email_clean:
        return False, "El nombre y un correo electrónico válido son obligatorios."

    sb_srv = _obtener_admin_auth()
    es_data_img_seguro = (
        sb_srv is None
        and foto_clean.startswith((
            "data:image/png;base64,",
            "data:image/jpeg;base64,",
            "data:image/webp;base64,",
            "data:image/gif;base64,",
        ))
        and len(foto_clean) <= 550_000
    )

    if foto_clean and not foto_clean.lower().startswith("https://") and not es_data_img_seguro:
        return False, "Por seguridad, la foto de perfil debe ser una URL pública con HTTPS (https://...)."

    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email, email_fallback=email_clean)
        if user_obj is not None:
            uid = str(user_obj.id)
            curr_email = (getattr(user_obj, "email", "") or "").strip().lower()
            if email_clean != curr_email:
                otro = _buscar_usuario_cloud(sb_srv, email_clean)
                if otro is not None and str(otro.id) != uid:
                    return False, "El correo ingresado ya está siendo utilizado por otra cuenta."

            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            meta["nombre"] = nombre_clean
            meta["telefono"] = tel_clean
            meta["bio"] = bio_clean
            meta["foto_perfil"] = foto_clean
            if ubicacion is not None:
                meta["ubicacion"] = ubicacion.strip() or "Santiago, Chile"

            payload: Dict[str, Any] = {"user_metadata": meta}
            if email_clean != curr_email:
                payload["email"] = email_clean
                payload["email_confirm"] = True

            try:
                sb_srv.auth.admin.update_user_by_id(uid, payload)
                try:
                    sb_srv.table("perfiles_usuario").upsert({
                        "id": uid,
                        "nombre": nombre_clean,
                        "email": email_clean,
                        "telefono": tel_clean,
                        "ubicacion": meta.get("ubicacion", "Santiago, Chile"),
                        "bio": bio_clean,
                        "foto_perfil": foto_clean,
                    }, on_conflict="id").execute()
                except Exception:
                    pass
                return True, "Perfil actualizado con éxito en la nube."
            except Exception as e:
                logger.error(f"Error actualizando perfil en Supabase Auth: {e}")
                return False, "No se pudo actualizar el perfil en la nube."

    init_db()
    ubic_final = (ubicacion or "Santiago, Chile").strip()
    with get_db_cursor(commit=True) as cursor:
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            cursor.execute("SELECT id, email FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            cursor.execute(
                "SELECT id, email FROM usuarios WHERE LOWER(email) = ?;",
                (str(usuario_id_o_email).strip().lower(),),
            )

        row = cursor.fetchone()
        if not row:
            pwd_random = hash_password(secrets.token_urlsafe(24))
            cursor.execute("""
            INSERT INTO usuarios (nombre, email, password_hash, telefono, ubicacion, bio, foto_perfil)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (nombre_clean, email_clean, pwd_random, tel_clean, ubic_final, bio_clean, foto_clean))
            return True, "Perfil creado y actualizado."

        u_id = row["id"]
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ? AND id != ?;", (email_clean, u_id))
        if cursor.fetchone():
            return False, "El correo ingresado ya está siendo utilizado por otra cuenta."

        if ubicacion is not None:
            cursor.execute("""
            UPDATE usuarios
            SET nombre = ?, email = ?, telefono = ?, ubicacion = ?, bio = ?, foto_perfil = ?
            WHERE id = ?;
            """, (nombre_clean, email_clean, tel_clean, ubic_final, bio_clean, foto_clean, u_id))
        else:
            cursor.execute("""
            UPDATE usuarios
            SET nombre = ?, email = ?, telefono = ?, bio = ?, foto_perfil = ?
            WHERE id = ?;
            """, (nombre_clean, email_clean, tel_clean, bio_clean, foto_clean, u_id))

        return True, "Perfil actualizado con éxito."


def actualizar_preferencias_notificacion(
    usuario_id_o_email: Any,
    alerta_email: bool,
    umbral_descuento: int = 10,
    notif_stock: Optional[bool] = None,
    notif_resumen: Optional[bool] = None,
) -> Tuple[bool, str]:
    """Guarda de forma persistente las preferencias de alertas del usuario."""
    umbral_limpio = max(1, min(90, int(umbral_descuento or 10)))

    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        if user_obj is not None:
            uid = str(user_obj.id)
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            meta["alerta_email"] = bool(alerta_email)
            meta["umbral_descuento"] = umbral_limpio
            if notif_stock is not None:
                meta["notif_stock"] = bool(notif_stock)
            if notif_resumen is not None:
                meta["notif_resumen"] = bool(notif_resumen)
            try:
                sb_srv.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
                try:
                    sb_srv.table("perfiles_usuario").update({
                        "alerta_email": bool(alerta_email),
                        "umbral_descuento": umbral_limpio,
                        "notif_stock": bool(meta.get("notif_stock", True)),
                        "notif_resumen": bool(meta.get("notif_resumen", False)),
                    }).eq("id", uid).execute()
                except Exception:
                    pass
                return True, "Preferencias de notificación guardadas."
            except Exception as e:
                logger.error(f"Error guardando preferencias en Supabase Auth: {e}")
                return False, "No se pudieron guardar las preferencias."

    init_db()
    with get_db_cursor(commit=True) as cursor:
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            query_find = "WHERE id = ?"
            val_find: Any = int(usuario_id_o_email)
        else:
            query_find = "WHERE LOWER(email) = ?"
            val_find = str(usuario_id_o_email).strip().lower()

        if notif_stock is not None or notif_resumen is not None:
            cursor.execute(
                f"UPDATE usuarios SET alerta_email = ?, umbral_descuento = ?, "
                f"notif_stock = COALESCE(?, notif_stock), notif_resumen = COALESCE(?, notif_resumen) {query_find};",
                (
                    int(bool(alerta_email)),
                    umbral_limpio,
                    int(bool(notif_stock)) if notif_stock is not None else None,
                    int(bool(notif_resumen)) if notif_resumen is not None else None,
                    val_find,
                ),
            )
        else:
            cursor.execute(
                f"UPDATE usuarios SET alerta_email = ?, umbral_descuento = ? {query_find};",
                (int(bool(alerta_email)), umbral_limpio, val_find),
            )
        return True, "Preferencias de notificación guardadas."


# =============================================================================
# BLOQUE 9: FAVORITOS Y SISTEMA INTELIGENTE DE MONITOREO DE PRECIOS
# =============================================================================
def agregar_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Añade una fragancia a favoritos guardando el mejor precio en stock actual."""
    perfume_id = int(perfume_id)
    precios = obtener_precios_actuales(perfume_id)
    precios_stock = [int(p["precio_actual"]) for p in precios if p.get("en_stock") and (p.get("precio_actual") or 0) > 0]
    p_min = min(precios_stock) if precios_stock else 0
    ahora_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        if user_obj is not None:
            uid = str(user_obj.id)
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            favs = dict(meta.get("favoritos") or {}) if isinstance(meta.get("favoritos"), dict) else {}
            favs[str(perfume_id)] = {
                "precio_guardado": p_min,
                "fecha_agregado": ahora_iso,
            }
            meta["favoritos"] = favs
            try:
                sb_srv.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
                try:
                    sb_srv.table("favoritos_usuario").upsert({
                        "usuario_id": uid,
                        "perfume_id": perfume_id,
                        "precio_guardado": p_min,
                    }, on_conflict="usuario_id,perfume_id").execute()
                except Exception:
                    pass
                return True
            except Exception as e:
                logger.error(f"Error guardando favorito en Supabase Auth: {e}")
                return False

    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        return False

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
        INSERT OR REPLACE INTO favoritos (usuario_id, perfume_id, precio_guardado, fecha_agregado)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP);
        """, (int(u_perfil["id"]), perfume_id, p_min))
        return True


def eliminar_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Elimina una fragancia de la lista de monitoreo del usuario."""
    perfume_id = int(perfume_id)

    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        if user_obj is not None:
            uid = str(user_obj.id)
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            favs = dict(meta.get("favoritos") or {}) if isinstance(meta.get("favoritos"), dict) else {}
            favs.pop(str(perfume_id), None)
            meta["favoritos"] = favs
            try:
                sb_srv.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
                try:
                    sb_srv.table("favoritos_usuario").delete().eq("usuario_id", uid).eq("perfume_id", perfume_id).execute()
                except Exception:
                    pass
                return True
            except Exception as e:
                logger.error(f"Error eliminando favorito en Supabase Auth: {e}")
                return False

    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        return False

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM favoritos WHERE usuario_id = ? AND perfume_id = ?;",
            (int(u_perfil["id"]), perfume_id),
        )
        return True


def obtener_favoritos_Ids_usuario(usuario_id_o_email: Any, email: Optional[str] = None) -> List[int]:
    """Retorna la lista de `perfume_id` favoritos del usuario."""
    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email, email_fallback=email)
        if user_obj is not None:
            u_norm = _normalizar_usuario_cloud(user_obj)
            return u_norm.get("favoritos", [])

    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email or email)
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        return []

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT perfume_id FROM favoritos WHERE usuario_id = ? ORDER BY fecha_agregado DESC;",
            (int(u_perfil["id"]),),
        )
        return [int(r["perfume_id"]) for r in cursor.fetchall()]


def obtener_favoritos_usuario(usuario_id_o_email: Any) -> List[Dict[str, Any]]:
    """Retorna los perfumes favoritos monitoreados por el usuario con detección real de bajas de precio."""
    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        if user_obj is not None:
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            favs_raw = meta.get("favoritos") or {}
            fav_entries: Dict[int, Dict[str, Any]] = {}
            if isinstance(favs_raw, dict):
                for k, v in favs_raw.items():
                    if str(k).isdigit():
                        fav_entries[int(k)] = v if isinstance(v, dict) else {"precio_guardado": 0}
            elif isinstance(favs_raw, list):
                for x in favs_raw:
                    if str(x).isdigit():
                        fav_entries[int(x)] = {"precio_guardado": 0}

            if not fav_entries:
                return []

            catalogo_map = {int(p["id"]): p for p in obtener_catalogo()}
            resultado: List[Dict[str, Any]] = []
            for pid, meta_fav in fav_entries.items():
                perf = catalogo_map.get(pid) or obtener_detalle_perfume(pid)
                if not perf:
                    continue
                d = dict(perf)
                mejor_actual = d.get("mejor_precio")
                p_act = int(mejor_actual) if mejor_actual else int(d.get("precio_referencia") or 0)
                p_guardado = int(meta_fav.get("precio_guardado") or 0) or p_act
                d["precio_guardado"] = p_guardado
                d["fecha_agregado"] = meta_fav.get("fecha_agregado", "")
                d["mejor_precio_actual"] = mejor_actual
                d["baja_detectada"] = bool(mejor_actual and mejor_actual < p_guardado)
                if p_guardado > 0 and mejor_actual and mejor_actual < p_guardado:
                    d["porcentaje_descuento"] = round(((p_guardado - mejor_actual) / p_guardado) * 100, 1)
                else:
                    d["porcentaje_descuento"] = 0.0
                resultado.append(d)
            return resultado

    init_db()
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        return []

    query = """
    SELECT p.*, f.precio_guardado, f.fecha_agregado,
           COALESCE(
               (SELECT MIN(oa.precio_actual)
                FROM ofertas_actuales oa
                JOIN variantes_perfume vp ON vp.id = oa.variante_id
                WHERE vp.perfume_id = p.id AND oa.en_stock = 1 AND oa.estado = 'activa' AND oa.precio_actual > 0),
               (SELECT MIN(pr.precio_actual)
                FROM precios_registro pr
                WHERE pr.perfume_id = p.id AND pr.en_stock = 1 AND pr.precio_actual > 0)
           ) as mejor_precio_actual
    FROM favoritos f
    JOIN perfumes p ON f.perfume_id = p.id
    WHERE f.usuario_id = ?
    ORDER BY f.fecha_agregado DESC;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (int(u_perfil["id"]),))
        favoritos = []
        for row in cursor.fetchall():
            d = dict(row)
            p_act = d["mejor_precio_actual"] or d["precio_referencia"]
            p_init = d["precio_guardado"] or d["precio_referencia"]
            d["mejor_precio"] = d["mejor_precio_actual"]
            d["baja_detectada"] = bool(d["mejor_precio_actual"] and p_act < p_init and p_act > 0)
            if d["precio_guardado"] and d["precio_guardado"] > 0 and p_act < d["precio_guardado"]:
                d["porcentaje_descuento"] = round(((d["precio_guardado"] - p_act) / d["precio_guardado"]) * 100, 1)
            else:
                d["porcentaje_descuento"] = 0.0
            favoritos.append(d)
        return favoritos


def es_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Verifica si una fragancia específica está marcada como favorita por el usuario."""
    ids = obtener_favoritos_Ids_usuario(usuario_id_o_email)
    return int(perfume_id) in ids


def obtener_alertas_pendientes() -> List[Dict[str, Any]]:
    """Calcula qué usuarios superaron su umbral de descuento configurado en sus favoritos."""
    sb_srv = _obtener_admin_auth()
    if sb_srv is not None:
        alertas: List[Dict[str, Any]] = []
        try:
            users_resp = sb_srv.auth.admin.list_users(page=1, per_page=200)
            users_list = users_resp if isinstance(users_resp, list) else getattr(users_resp, "users", []) or []
            catalogo_map = {int(p["id"]): p for p in obtener_catalogo()}
            for u in users_list:
                u_norm = _normalizar_usuario_cloud(u)
                if not u_norm.get("alerta_email"):
                    continue
                umbral = int(u_norm.get("umbral_descuento", 10))
                meta = dict(getattr(u, "user_metadata", None) or {})
                favs = meta.get("favoritos") or {}
                if not isinstance(favs, dict):
                    continue
                for k, v in favs.items():
                    if not str(k).isdigit() or not isinstance(v, dict):
                        continue
                    pid = int(k)
                    p_guardado = int(v.get("precio_guardado") or 0)
                    perf = catalogo_map.get(pid)
                    mejor = perf.get("mejor_precio") if perf else None
                    if perf and p_guardado > 0 and mejor and mejor > 0:
                        rebaja_pct = ((p_guardado - mejor) * 100.0) / p_guardado
                        if rebaja_pct >= umbral:
                            alertas.append({
                                "email": u_norm["email"],
                                "usuario_nombre": u_norm["nombre"],
                                "umbral_descuento": umbral,
                                "perfume_nombre": perf["nombre"],
                                "marca": perf["marca"],
                                "precio_guardado": p_guardado,
                                "precio_nuevo": mejor,
                            })
            return alertas
        except Exception as e:
            logger.debug(f"Aviso evaluando alertas cloud: {e}")

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
# =============================================================================
def obtener_url_directa_tienda(perfume_id: int, tienda_nombre: str) -> Optional[Tuple[str, int, int, int]]:
    """Retorna la tupla (url_producto, precio_actual, precio_normal, volumen_ml) configurada en seed_catalogo.json."""
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
    """Genera el enlace de navegación hacia la tienda correspondiente."""
    if url_directa and url_directa.startswith(("http://", "https://")) and url_directa != "#":
        return url_directa

    t = (tienda_nombre or "").lower()
    q = urllib.parse.quote((perfume_nombre or "").strip())
    if "falabella" in t:
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    if "paris" in t:
        return f"https://www.paris.cl/search?q={q}"
    if "ripley" in t:
        return f"https://simple.ripley.cl/search/{q}"
    if "silk" in t:
        return f"https://www.silkperfumes.cl/search?q={q}"
    if "elite" in t:
        return f"https://www.eliteperfumes.cl/search?q={q}"
    if "alisha" in t:
        return f"https://alishaperfumes.cl/search?q={q}"
    if "yauras" in t:
        return f"https://yauras.cl/search?q={q}"
    if "oferta" in t:
        return f"https://ofertaperfumes.cl/search?q={q}"
    if "dbs" in t:
        return f"https://www.dbs.cl/search?q={q}"
    return None


def tienda_comercializa_marca(tienda_nombre: str, marca: str) -> bool:
    t_nom = (tienda_nombre or "").lower()
    m = (marca or "").lower()
    if "chanel" in m or "maison francis" in m or "tom ford" in m:
        return any(retail in t_nom for retail in ["falabella", "paris", "ripley"])
    return True


# =============================================================================
# BLOQUE 11: PERSISTENCIA TRANSACCIONAL ATÓMICA Y CONTROL DE RUNS / ERRORES
# =============================================================================
def iniciar_scraping_run(
    tipo_scraper: str,
    tienda_id: Optional[int] = None,
    mensaje_detalle: Optional[str] = None,
) -> Optional[int]:
    """Registra el inicio auditable de un ciclo de scraping en `scraping_runs`."""
    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        try:
            payload: Dict[str, Any] = {
                "tipo_scraper": tipo_scraper,
                "estado": "iniciado",
                "mensaje_detalle": mensaje_detalle,
            }
            if tienda_id is not None:
                payload["tienda_id"] = int(tienda_id)
            resp = sb.table("scraping_runs").insert(payload).execute()
            if resp.data:
                return int(resp.data[0]["id"])
        except Exception as e:
            logger.debug(f"No se pudo iniciar scraping_run en Supabase: {e}")
        return None

    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO scraping_runs (tipo_scraper, tienda_id, estado, mensaje_detalle) VALUES (?, ?, 'iniciado', ?);",
            (tipo_scraper, tienda_id, mensaje_detalle),
        )
        return int(cursor.lastrowid) if cursor.lastrowid else None


def finalizar_scraping_run(
    run_id: Optional[int],
    estado: str = "exitoso",
    productos_procesados: int = 0,
    ofertas_nuevas: int = 0,
    cambios_precio: int = 0,
    cambios_stock: int = 0,
    cambios_url: int = 0,
    errores: int = 0,
    mensaje_detalle: Optional[str] = "",
) -> None:
    """Cierra el registro de auditoría en `scraping_runs` con contadores reales."""
    if not run_id:
        return
    estado_norm = "exitoso" if estado in ("completado", "exitoso") else estado
    estado_valido = estado_norm if estado_norm in ("exitoso", "parcial", "fallido", "cancelado") else "exitoso"
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        try:
            sb.table("scraping_runs").update({
                "estado": estado_valido,
                "fecha_fin": datetime.now(timezone.utc).isoformat(),
                "productos_procesados": max(0, int(productos_procesados)),
                "ofertas_nuevas": max(0, int(ofertas_nuevas)),
                "cambios_precio": max(0, int(cambios_precio)),
                "cambios_stock": max(0, int(cambios_stock)),
                "cambios_url": max(0, int(cambios_url)),
                "errores": max(0, int(errores)),
                "mensaje_detalle": (mensaje_detalle or "")[:2000] or None,
            }).eq("id", int(run_id)).execute()
        except Exception as e:
            logger.debug(f"No se pudo finalizar scraping_run {run_id}: {e}")
        return

    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
        UPDATE scraping_runs
        SET estado = ?, fecha_fin = ?, productos_procesados = ?, ofertas_nuevas = ?,
            cambios_precio = ?, cambios_stock = ?, cambios_url = ?, errores = ?, mensaje_detalle = ?
        WHERE id = ?;
        """, (
            estado_valido, ahora, max(0, int(productos_procesados)), max(0, int(ofertas_nuevas)),
            max(0, int(cambios_precio)), max(0, int(cambios_stock)), max(0, int(cambios_url)),
            max(0, int(errores)), (mensaje_detalle or "")[:2000] or None, int(run_id),
        ))


def registrar_observacion_oferta(observacion: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Persistencia transaccional de una observación de precio/stock:
    - Separa explícitamente variantes `'regular'` de `'tester'` para impedir que un Tester pise a un sellado.
    - Garantiza `p_precio_normal` no nulo al invocar la RPC en PostgreSQL, eliminando el rollback en `precios_registro`.
    - Elimina por completo los fallbacks `LIMIT 1` y el split-brain silencioso a SQLite cuando Supabase está activo.
    """
    if observacion is None:
        observacion = kwargs
    elif kwargs:
        observacion = {**observacion, **kwargs}

    if not isinstance(observacion, dict):
        raise ValueError("La observación debe ser un diccionario válido")

    variante_id = observacion.get("variante_id") or observacion.get("variante_id_sb")
    perfume_id = observacion.get("perfume_id") or observacion.get("perfume_id_sb") or observacion.get("perfume_id_sqlite")
    tienda_id = observacion.get("tienda_id") or observacion.get("tienda_id_sb") or observacion.get("tienda_id_sqlite")
    precio_actual = observacion.get("precio_actual")
    precio_normal = observacion.get("precio_normal")
    en_stock = observacion.get("en_stock")
    url_producto = (observacion.get("url_producto") or "").strip()
    volumen_ml = observacion.get("volumen_ml") or 100
    scraping_run_id = observacion.get("scraping_run_id")

    formato_raw = str(observacion.get("formato") or "").strip().lower()
    if formato_raw not in ("regular", "tester"):
        formato_raw = detectar_formato_oferta("", url_producto)

    # Validaciones obligatorias de negocio
    if tienda_id is None:
        raise ValueError("tienda_id es obligatorio")
    if variante_id is None and perfume_id is None:
        raise ValueError("Se requiere al menos variante_id o perfume_id")
    if precio_actual is None or not isinstance(precio_actual, (int, float)) or int(precio_actual) <= 0:
        raise ValueError("El precio actual confirmado debe ser un entero positivo")
    precio_actual = int(precio_actual)
    if precio_actual < 4000 or precio_actual >= 1000000 or precio_actual in (9999999, 9999990, 999999):
        raise ValueError(
            f"Precio fuera de rango comercial ({precio_actual}). Se descartan precios irreales o placeholders."
        )

    if precio_normal is not None:
        if not isinstance(precio_normal, (int, float)) or int(precio_normal) <= 0:
            raise ValueError("El precio normal debe ser un entero positivo o None")
        precio_normal = int(precio_normal)
        if precio_normal >= 1000000 or precio_normal in (9999999, 9999990, 999999):
            precio_normal = None

    if en_stock is None or not isinstance(en_stock, bool):
        raise ValueError("El stock debe ser explícito (True o False), no desconocido ni nulo")

    if not url_producto or not (url_producto.startswith("http://") or url_producto.startswith("https://")):
        raise ValueError("Se requiere una URL HTTP(S) válida")

    limpiar_cache_catalogo()

    # 1. Camino Primario: Supabase Transaccional (sin split-brain silencioso a SQLite)
    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        sb_variante_id = observacion.get("variante_id_sb") or variante_id
        sb_perfume_id = observacion.get("perfume_id_sb") or perfume_id
        vol_int = int(round(float(volumen_ml))) if volumen_ml else 100

        if not sb_variante_id and sb_perfume_id:
            r_v = (
                sb.table("variantes_perfume")
                .select("id")
                .eq("perfume_id", sb_perfume_id)
                .eq("volumen_ml", vol_int)
                .eq("formato", formato_raw)
                .limit(1)
                .execute()
            )
            if r_v.data:
                sb_variante_id = r_v.data[0]["id"]
            else:
                r_p = sb.table("perfumes").select("id, tipo, nombre").eq("id", sb_perfume_id).limit(1).execute()
                if not r_p.data:
                    raise ValueError(f"El perfume_id {sb_perfume_id} no existe en Supabase.")
                tipo_p = r_p.data[0].get("tipo") or "Eau de Parfum"
                slug_v = (
                    f"perfume-{sb_perfume_id}-{vol_int}ml"
                    if formato_raw == "regular"
                    else f"perfume-{sb_perfume_id}-{vol_int}ml-{formato_raw}"
                )
                r_ins = sb.table("variantes_perfume").upsert(
                    {
                        "perfume_id": sb_perfume_id,
                        "concentracion": tipo_p,
                        "volumen_ml": vol_int,
                        "formato": formato_raw,
                        "slug": slug_v,
                        "activa": True,
                    },
                    on_conflict="slug",
                ).execute()
                if r_ins.data:
                    sb_variante_id = r_ins.data[0]["id"]
                else:
                    r_recheck = sb.table("variantes_perfume").select("id").eq("slug", slug_v).limit(1).execute()
                    if r_recheck.data:
                        sb_variante_id = r_recheck.data[0]["id"]

        if not sb_variante_id:
            raise ValueError(f"No fue posible resolver variante_id en Supabase para perfume_id={sb_perfume_id}.")

        sb_tienda_id = observacion.get("tienda_id_sb") or tienda_id
        # Asegurar precio_normal válido para evitar rollback NOT NULL en precios_registro
        p_normal_rpc = precio_normal if (precio_normal and precio_normal >= precio_actual) else precio_actual

        try:
            rpc_res = sb.rpc("registrar_observacion_oferta", {
                "p_variante_id": int(sb_variante_id),
                "p_tienda_id": int(sb_tienda_id),
                "p_precio_actual": precio_actual,
                "p_precio_normal": p_normal_rpc,
                "p_en_stock": en_stock,
                "p_url_producto": url_producto,
                "p_scraping_run_id": scraping_run_id,
            }).execute()
            if rpc_res.data:
                return rpc_res.data
            raise RuntimeError("La RPC registrar_observacion_oferta no retornó datos.")
        except Exception as e:
            logger.error(
                f"Fallo transaccional en Supabase RPC registrar_observacion_oferta "
                f"(variante={sb_variante_id}, tienda={sb_tienda_id}): {e}"
            )
            raise

    # 2. Camino Local: Persistencia Transaccional Atómica en SQLite (sin fallbacks LIMIT 1)
    init_db()
    with get_db_cursor(commit=True) as cursor:
        local_variante_id = None
        local_perfume_id = observacion.get("perfume_id_sqlite") or perfume_id

        if variante_id:
            cursor.execute(
                "SELECT id, perfume_id, volumen_ml, formato FROM variantes_perfume WHERE id = ?;",
                (variante_id,),
            )
            row_v = cursor.fetchone()
            if row_v:
                local_variante_id = row_v["id"]
                local_perfume_id = row_v["perfume_id"]
                volumen_ml = row_v["volumen_ml"]

        if not local_variante_id and local_perfume_id:
            cursor.execute(
                "SELECT id FROM variantes_perfume WHERE perfume_id = ? AND ABS(volumen_ml - ?) < 1 AND LOWER(formato) = ? LIMIT 1;",
                (local_perfume_id, volumen_ml, formato_raw),
            )
            row_v = cursor.fetchone()
            if row_v:
                local_variante_id = row_v["id"]
            else:
                cursor.execute("SELECT id, tipo, nombre FROM perfumes WHERE id = ?;", (local_perfume_id,))
                row_p = cursor.fetchone()
                if not row_p:
                    raise ValueError(f"El perfume_id {local_perfume_id} no existe en SQLite.")
                tipo_p = row_p["tipo"] or "Eau de Parfum"
                vol_int = int(round(float(volumen_ml)))
                slug_v = (
                    f"perfume-{local_perfume_id}-{vol_int}ml"
                    if formato_raw == "regular"
                    else f"perfume-{local_perfume_id}-{vol_int}ml-{formato_raw}"
                )
                cursor.execute("""
                INSERT OR IGNORE INTO variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa)
                VALUES (?, ?, ?, ?, ?, 1);
                """, (local_perfume_id, tipo_p, volumen_ml, formato_raw, slug_v))
                cursor.execute(
                    "SELECT id FROM variantes_perfume WHERE perfume_id = ? AND ABS(volumen_ml - ?) < 1 AND LOWER(formato) = ? LIMIT 1;",
                    (local_perfume_id, volumen_ml, formato_raw),
                )
                row_v = cursor.fetchone()
                if row_v:
                    local_variante_id = row_v["id"]

        if not local_variante_id:
            raise ValueError("La variante especificada no existe y no pudo crearse válidamente.")

        local_tienda_id = observacion.get("tienda_id_sqlite") or tienda_id
        cursor.execute("SELECT id FROM tiendas WHERE id = ?;", (local_tienda_id,))
        if not cursor.fetchone():
            raise ValueError(f"La tienda_id {local_tienda_id} no existe en la base de datos.")

        cursor.execute(
            "SELECT * FROM ofertas_actuales WHERE variante_id = ? AND tienda_id = ?;",
            (local_variante_id, local_tienda_id),
        )
        row_oferta = cursor.fetchone()

        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obs_uuid = str(observacion.get("observacion_id") or uuid.uuid4())
        p_normal_final = (
            precio_normal
            if precio_normal
            else (row_oferta["precio_normal"] if (row_oferta and row_oferta["precio_normal"]) else precio_actual)
        )

        if not row_oferta:
            estado_ini = "activa" if en_stock else "agotada"
            cursor.execute("""
            INSERT INTO ofertas_actuales (
                variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto,
                estado, ultima_verificacion_exitosa, ultimo_intento, ultimo_cambio_confirmado,
                fallos_consecutivos, ultimo_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?);
            """, (
                local_variante_id, local_tienda_id, precio_actual, p_normal_final, int(en_stock), url_producto,
                estado_ini, ahora, ahora, ahora, ahora, ahora,
            ))
            oferta_id = cursor.lastrowid
            tipo_evento = "observacion_inicial"
            campos_mod = ["precio_actual", "en_stock", "url_producto"]
            if precio_normal:
                campos_mod.append("precio_normal")

            cursor.execute("""
            INSERT INTO precios_registro (
                perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
                volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento,
                campos_modificados, observacion_id, scraping_run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                local_perfume_id, local_tienda_id, precio_actual, p_normal_final, int(en_stock),
                volumen_ml, url_producto, ahora, local_variante_id, tipo_evento,
                json.dumps(campos_mod), obs_uuid, scraping_run_id,
            ))

            return {
                "oferta_id": oferta_id,
                "resultado": "creada",
                "tipo_evento": tipo_evento,
                "campos_modificados": campos_mod,
                "precio_anterior": None,
                "precio_nuevo": precio_actual,
                "stock_anterior": None,
                "stock_nuevo": en_stock,
                "url_anterior": None,
                "url_nueva": url_producto,
            }

        oferta_id = row_oferta["id"]
        precio_ant = row_oferta["precio_actual"]
        stock_ant = bool(row_oferta["en_stock"])
        url_ant = row_oferta["url_producto"]
        p_norm_ant = row_oferta["precio_normal"]

        campos_mod = []
        if precio_ant != precio_actual:
            campos_mod.append("precio_actual")
        if stock_ant != en_stock:
            campos_mod.append("en_stock")
        if url_ant != url_producto:
            campos_mod.append("url_producto")
        if precio_normal and p_norm_ant != precio_normal:
            campos_mod.append("precio_normal")

        if not campos_mod:
            cursor.execute("""
            UPDATE ofertas_actuales
            SET ultima_verificacion_exitosa = ?, ultimo_intento = ?,
                fallos_consecutivos = 0, ultimo_error = NULL,
                estado = ?, updated_at = ?
            WHERE id = ?;
            """, (ahora, ahora, "activa" if en_stock else "agotada", ahora, oferta_id))
            return {
                "oferta_id": oferta_id,
                "resultado": "sin_cambios",
                "tipo_evento": None,
                "campos_modificados": [],
            }

        if len(campos_mod) > 1:
            tipo_evento = "cambio_multiple"
        elif campos_mod[0] == "precio_actual":
            tipo_evento = "cambio_precio"
        elif campos_mod[0] == "en_stock":
            tipo_evento = "cambio_stock"
        elif campos_mod[0] == "url_producto":
            tipo_evento = "cambio_url"
        else:
            tipo_evento = "cambio_datos"

        cursor.execute("""
        UPDATE ofertas_actuales
        SET precio_actual = ?, precio_normal = ?, en_stock = ?, url_producto = ?,
            estado = ?, ultima_verificacion_exitosa = ?, ultimo_intento = ?,
            ultimo_cambio_confirmado = ?, fallos_consecutivos = 0,
            ultimo_error = NULL, updated_at = ?
        WHERE id = ?;
        """, (
            precio_actual, p_normal_final, int(en_stock), url_producto,
            "activa" if en_stock else "agotada", ahora, ahora, ahora, ahora, oferta_id,
        ))

        cursor.execute("""
        INSERT INTO precios_registro (
            perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
            volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento,
            campos_modificados, observacion_id, scraping_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            local_perfume_id, local_tienda_id, precio_actual, p_normal_final, int(en_stock),
            volumen_ml, url_producto, ahora, local_variante_id, tipo_evento,
            json.dumps(campos_mod), obs_uuid, scraping_run_id,
        ))

        return {
            "oferta_id": oferta_id,
            "resultado": "actualizada",
            "tipo_evento": tipo_evento,
            "campos_modificados": campos_mod,
            "precio_anterior": precio_ant,
            "precio_nuevo": precio_actual,
            "stock_anterior": stock_ant,
            "stock_nuevo": en_stock,
            "url_anterior": url_ant,
            "url_nueva": url_producto,
        }


def registrar_fallo_scraping(
    tienda_id: int,
    mensaje: str,
    variante_id: Optional[int] = None,
    perfume_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Registra un fallo de extracción sin alterar el precio actual, stock ni URL confirmada.
    Si una oferta acumula 5 o más fallos consecutivos, pasa a `estado='requiere_revision'`.
    """
    if tienda_id is None:
        raise ValueError("tienda_id es obligatorio")
    if not mensaje or not str(mensaje).strip():
        raise ValueError("Debe indicarse el motivo del fallo")

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_clean = str(mensaje).strip()[:2000]

    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        if not variante_id and perfume_id:
            try:
                r_v = sb.table("variantes_perfume").select("id").eq("perfume_id", perfume_id).limit(1).execute()
                if r_v.data:
                    variante_id = r_v.data[0]["id"]
            except Exception as e:
                logger.debug(f"Error resolviendo variante en Supabase: {e}")

        if not variante_id:
            return {"resultado": "fallo_sin_variante", "mensaje": msg_clean}

        try:
            rpc_res = sb.rpc("registrar_fallo_scraping", {
                "p_variante_id": int(variante_id),
                "p_tienda_id": int(tienda_id),
                "p_mensaje": msg_clean,
            }).execute()
            res_data = rpc_res.data or {"resultado": "fallo_registrado"}
            # Si la migración 10 aún no se aplicó en SQL, asegurar retiro tras >= 5 fallos desde Python
            if isinstance(res_data, dict) and int(res_data.get("fallos_consecutivos") or 0) >= 5:
                oferta_id_sb = res_data.get("oferta_id")
                if oferta_id_sb:
                    sb.table("ofertas_actuales").update({"estado": "requiere_revision"}).eq("id", oferta_id_sb).execute()
                    limpiar_cache_catalogo()
            return res_data
        except Exception as e:
            logger.error(f"Error en RPC registrar_fallo_scraping en Supabase: {e}")
            raise

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
            "SELECT id, fallos_consecutivos, precio_actual, en_stock, estado "
            "FROM ofertas_actuales WHERE variante_id = ? AND tienda_id = ?;",
            (target_variante_id, tienda_id),
        )
        row_oferta = cursor.fetchone()

        if not row_oferta:
            return {"resultado": "fallo_sin_oferta", "mensaje": msg_clean}

        nueva_cuenta = (row_oferta["fallos_consecutivos"] or 0) + 1
        nuevo_estado = "requiere_revision" if nueva_cuenta >= 5 else row_oferta["estado"]
        cursor.execute("""
        UPDATE ofertas_actuales
        SET ultimo_intento = ?, fallos_consecutivos = ?, ultimo_error = ?, estado = ?, updated_at = ?
        WHERE id = ?;
        """, (ahora, nueva_cuenta, msg_clean, nuevo_estado, ahora, row_oferta["id"]))

        return {
            "resultado": "fallo_registrado",
            "oferta_id": row_oferta["id"],
            "fallos_consecutivos": nueva_cuenta,
            "estado": nuevo_estado,
            "precio_actual": row_oferta["precio_actual"],
            "en_stock": bool(row_oferta["en_stock"]),
        }


def registrar_precio(
    perfume_id: int,
    tienda_id: int,
    precio_actual: int,
    precio_normal: int,
    en_stock: bool,
    url_producto: str,
    fecha: Optional[str] = None,
    volumen_ml: int = 100,
) -> None:
    """Wrapper retrocompatible que delega en la persistencia transaccional `registrar_observacion_oferta`."""
    registrar_observacion_oferta({
        "perfume_id": perfume_id,
        "tienda_id": tienda_id,
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "en_stock": bool(en_stock),
        "url_producto": url_producto,
        "volumen_ml": volumen_ml,
    })


# =============================================================================
# BLOQUE 12: CONSULTAS DE CATÁLOGO Y OFERTAS CON PAGINACIÓN AUTOMÁTICA (>1.000)
# =============================================================================
def obtener_catalogo(
    busqueda: Optional[str] = None,
    esencias: Optional[List[str]] = None,
    categoria: Optional[str] = None,
    orden: str = "id_asc",
) -> List[Dict[str, Any]]:
    """
    Obtiene el catálogo completo paginando automáticamente sobre PostgREST (>1.000 filas):
    - Prioriza ofertas `'regular'` (>= 25 ml) sobre `'tester'` para calcular `mejor_precio`.
    - Detecta descuentos reales (`precio_normal > precio_actual`) además de `en_remate`.
    """
    sb = get_supabase()
    if sb and is_supabase_disponible():
        cache_key = (
            (busqueda or "").strip().lower(),
            tuple(sorted(e.lower() for e in (esencias or []))),
            categoria or "",
            orden,
        )
        now_ts = time.monotonic()
        cached = _CATALOGO_CACHE.get(cache_key)
        if cached and (now_ts - cached[0]) < CATALOGO_CACHE_TTL_SECONDS:
            return [dict(item) for item in cached[1]]

        try:
            def _perfumes_page(offset: int, limit: int):
                q = sb.table("perfumes").select("*").order("id", desc=False)
                if busqueda:
                    term = busqueda.strip()
                    q = q.or_(f"nombre.ilike.%{term}%,marca.ilike.%{term}%")
                if categoria == "arabes":
                    q = q.eq("es_arabe", True)
                return q.range(offset, offset + limit - 1)

            perfumes = _fetch_all_rows(_perfumes_page, page_size=1000)

            def _ofertas_page(offset: int, limit: int):
                return (
                    sb.table("ofertas_actuales")
                    .select("id, precio_actual, precio_normal, en_stock, url_producto, variantes_perfume!inner(perfume_id, volumen_ml, formato)")
                    .eq("estado", "activa")
                    .eq("en_stock", True)
                    .gt("precio_actual", 0)
                    .order("id", desc=False)
                    .range(offset, offset + limit - 1)
                )

            ofertas_activas = _fetch_all_rows(_ofertas_page, page_size=1000)

            precios_regular: Dict[int, int] = {}
            precios_tester: Dict[int, int] = {}
            remates_reales: Set[int] = set()

            for o in ofertas_activas:
                vp = o.get("variantes_perfume") or {}
                pid = vp.get("perfume_id")
                p_act = int(o.get("precio_actual") or 0)
                p_norm = int(o.get("precio_normal") or 0)
                vol = float(vp.get("volumen_ml") or 100)
                url_p = str(o.get("url_producto") or "")
                fmt = str(vp.get("formato") or "").lower()
                if fmt != "tester" and "tester" in url_p.lower():
                    fmt = "tester"

                if not pid or p_act <= 0 or vol < 25:
                    continue

                pid_int = int(pid)
                if fmt == "tester":
                    if pid_int not in precios_tester or p_act < precios_tester[pid_int]:
                        precios_tester[pid_int] = p_act
                else:
                    if pid_int not in precios_regular or p_act < precios_regular[pid_int]:
                        precios_regular[pid_int] = p_act

                if p_norm > p_act and ((p_norm - p_act) / p_norm) >= 0.08:
                    remates_reales.add(pid_int)

            perfumes_procesados: List[Dict[str, Any]] = []
            for p in perfumes:
                pid_int = int(p.get("id") or 0)
                mejor_reg = precios_regular.get(pid_int)
                mejor_tst = precios_tester.get(pid_int)
                if mejor_reg is not None:
                    p["mejor_precio"] = mejor_reg
                    p["mejor_precio_es_tester"] = False
                elif mejor_tst is not None:
                    p["mejor_precio"] = mejor_tst
                    p["mejor_precio_es_tester"] = True
                else:
                    p["mejor_precio"] = None
                    p["mejor_precio_es_tester"] = False

                es_remate_real = bool(p.get("en_remate")) or (pid_int in remates_reales)
                if categoria == "remates" and not (es_remate_real and p["mejor_precio"] is not None):
                    continue
                perfumes_procesados.append(p)

            perfumes = perfumes_procesados

            if orden == "precio_asc":
                perfumes.sort(key=lambda x: (x.get("mejor_precio") is None, x.get("mejor_precio") or 999999999))
            elif orden == "precio_desc":
                perfumes.sort(key=lambda x: (x.get("mejor_precio") is None, -(x.get("mejor_precio") or 0)))
            elif orden == "nombre_asc":
                perfumes.sort(key=lambda x: (x.get("nombre") or "").lower())
            else:
                perfumes.sort(key=lambda x: x.get("id", 0))

            if esencias:
                esencias_lower = [e.lower() for e in esencias]
                perfumes = [
                    p for p in perfumes
                    if any(
                        any(es in nota for nota in [n.strip().lower() for n in (p.get("notas") or "").split(",")])
                        for es in esencias_lower
                    )
                ]

            _CATALOGO_CACHE[cache_key] = (now_ts, [dict(item) for item in perfumes])
            return perfumes
        except Exception as e:
            logger.warning(f"Error consultando catálogo en Supabase ({e}), recurriendo a SQLite de respaldo.")

    # Respaldo SQLite local (prioriza ofertas_actuales y cae a precios_registro si está vacío)
    init_db()
    query_sql = """
    SELECT p.*,
           COALESCE(
               (SELECT MIN(oa.precio_actual)
                FROM ofertas_actuales oa
                JOIN variantes_perfume vp ON vp.id = oa.variante_id
                WHERE vp.perfume_id = p.id
                  AND oa.estado = 'activa'
                  AND oa.en_stock = 1
                  AND oa.precio_actual > 0
                  AND COALESCE(vp.volumen_ml, 100) >= 25
                  AND LOWER(COALESCE(vp.formato, 'regular')) != 'tester'),
               (SELECT MIN(oa2.precio_actual)
                FROM ofertas_actuales oa2
                JOIN variantes_perfume vp2 ON vp2.id = oa2.variante_id
                WHERE vp2.perfume_id = p.id
                  AND oa2.estado = 'activa'
                  AND oa2.en_stock = 1
                  AND oa2.precio_actual > 0
                  AND COALESCE(vp2.volumen_ml, 100) >= 25),
               (SELECT MIN(pr.precio_actual)
                FROM precios_registro pr
                WHERE pr.perfume_id = p.id
                  AND pr.en_stock = 1
                  AND pr.precio_actual > 0
                  AND pr.id = (
                      SELECT pr2.id
                      FROM precios_registro pr2
                      WHERE pr2.perfume_id = pr.perfume_id
                        AND pr2.tienda_id = pr.tienda_id
                        AND ABS(COALESCE(pr2.volumen_ml, 100) - COALESCE(pr.volumen_ml, 100)) < 1
                      ORDER BY pr2.fecha_registro DESC, pr2.id DESC
                      LIMIT 1
                  ))
           ) as mejor_precio
    FROM perfumes p
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

    with get_db_cursor() as cursor:
        cursor.execute(query_sql, params)
        perfumes = [dict(row) for row in cursor.fetchall()]

    if orden == "precio_asc":
        perfumes.sort(key=lambda x: (x.get("mejor_precio") is None, x.get("mejor_precio") or 999999999))
    elif orden == "precio_desc":
        perfumes.sort(key=lambda x: (x.get("mejor_precio") is None, -(x.get("mejor_precio") or 0)))
    elif orden == "nombre_asc":
        perfumes.sort(key=lambda x: (x.get("nombre") or "").lower())
    else:
        perfumes.sort(key=lambda x: x.get("id", 0))

    if esencias:
        esencias_lower = [e.lower() for e in esencias]
        perfumes = [
            p for p in perfumes
            if any(
                any(es in nota for nota in [n.strip().lower() for n in (p.get("notas") or "").split(",")])
                for es in esencias_lower
            )
        ]

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
    """
    Retorna las ofertas vigentes por tienda y presentación para el perfume dado,
    incluyendo estado de stock, volumen_ml, precio_por_ml y formato ('regular' vs 'tester').
    """
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            resp = (
                sb.table("ofertas_actuales")
                .select(
                    "id, precio_actual, precio_normal, en_stock, url_producto, ultima_verificacion_exitosa, "
                    "tiendas(id, nombre, url_base, trust_score, badge, logo_emoji), "
                    "variantes_perfume!inner(id, perfume_id, volumen_ml, formato)"
                )
                .eq("variantes_perfume.perfume_id", perfume_id)
                .in_("estado", ["activa", "agotada"])
                .order("precio_actual", desc=False)
                .execute()
            )
            if resp.data:
                res_lista = []
                for item in resp.data:
                    t = item.get("tiendas") or {}
                    v = item.get("variantes_perfume") or {}
                    p_act = int(item.get("precio_actual") or 0)
                    vol = int(round(float(v.get("volumen_ml") or 100)))
                    if vol < 25 or p_act <= 0:
                        continue
                    url_prod = str(item.get("url_producto") or "")
                    fmt = str(v.get("formato") or "regular").lower()
                    if fmt != "tester" and "tester" in url_prod.lower():
                        fmt = "tester"
                    p_ml = int(round(p_act / vol)) if (p_act and vol) else 0
                    res_lista.append({
                        "id": item.get("id"),
                        "perfume_id": perfume_id,
                        "tienda_id": t.get("id"),
                        "tienda_nombre": t.get("nombre", "Tienda"),
                        "url_base": t.get("url_base", ""),
                        "trust_score": t.get("trust_score", 90),
                        "badge": t.get("badge", "Retail Oficial"),
                        "logo_emoji": t.get("logo_emoji", ""),
                        "precio_actual": p_act,
                        "precio_normal": item.get("precio_normal") or p_act,
                        "en_stock": bool(item.get("en_stock", True)),
                        "volumen_ml": vol,
                        "formato": fmt,
                        "precio_por_ml": p_ml,
                        "url_producto": url_prod,
                        "fecha_registro": item.get("ultima_verificacion_exitosa"),
                    })
                return res_lista
            return []
        except Exception as e:
            logger.warning(f"Error en Supabase obtener_precios_actuales ({e}), recurriendo a SQLite de respaldo.")

    init_db()
    with get_db_cursor() as cursor:
        cursor.execute("""
        SELECT oa.id, t.id as tienda_id, t.nombre as tienda_nombre, t.url_base, t.trust_score, t.badge, t.logo_emoji,
               oa.precio_actual, COALESCE(oa.precio_normal, oa.precio_actual) as precio_normal, oa.en_stock,
               CAST(ROUND(COALESCE(vp.volumen_ml, 100)) AS INTEGER) as volumen_ml,
               LOWER(COALESCE(vp.formato, 'regular')) as formato,
               CAST(ROUND(CAST(oa.precio_actual AS REAL) / MAX(1, COALESCE(vp.volumen_ml, 100))) AS INTEGER) as precio_por_ml,
               oa.url_producto, oa.ultima_verificacion_exitosa as fecha_registro
        FROM ofertas_actuales oa
        JOIN variantes_perfume vp ON vp.id = oa.variante_id
        JOIN tiendas t ON t.id = oa.tienda_id
        WHERE vp.perfume_id = ?
          AND oa.estado IN ('activa', 'agotada')
          AND oa.precio_actual > 0
          AND COALESCE(vp.volumen_ml, 100) >= 25
        ORDER BY oa.precio_actual ASC;
        """, (perfume_id,))
        rows_oa = [dict(r) for r in cursor.fetchall()]
        if rows_oa:
            for r in rows_oa:
                r["en_stock"] = bool(r["en_stock"])
                if r.get("formato") != "tester" and "tester" in str(r.get("url_producto") or "").lower():
                    r["formato"] = "tester"
            return rows_oa

        query = """
        SELECT t.id as tienda_id, t.nombre as tienda_nombre, t.url_base, t.trust_score, t.badge, t.logo_emoji,
               pr.precio_actual, COALESCE(pr.precio_normal, pr.precio_actual) as precio_normal, pr.en_stock,
               COALESCE(pr.volumen_ml, 100) as volumen_ml,
               'regular' as formato,
               CAST(ROUND(CAST(pr.precio_actual AS REAL) / MAX(1, COALESCE(pr.volumen_ml, 100))) AS INTEGER) as precio_por_ml,
               pr.url_producto, pr.fecha_registro
        FROM tiendas t
        JOIN precios_registro pr ON t.id = pr.tienda_id
        WHERE pr.perfume_id = ?
          AND pr.precio_actual > 0
          AND pr.url_producto IS NOT NULL
          AND pr.fecha_registro = (
              SELECT MAX(fecha_registro)
              FROM precios_registro
              WHERE perfume_id = ? AND tienda_id = t.id AND ABS(COALESCE(volumen_ml, 100) - COALESCE(pr.volumen_ml, 100)) < 1
          )
        ORDER BY pr.precio_actual ASC;
        """
        cursor.execute(query, (perfume_id, perfume_id))
        res_legacy = [dict(row) for row in cursor.fetchall()]
        for r in res_legacy:
            r["en_stock"] = bool(r["en_stock"])
            if "tester" in str(r.get("url_producto") or "").lower():
                r["formato"] = "tester"
        return res_legacy


def obtener_historico_precios(perfume_id: int, volumen_ml: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retorna la serie temporal histórica de precios filtrada opcionalmente por `volumen_ml`
    para no mezclar presentaciones de 50ml, 100ml y 200ml en un mismo gráfico.
    """
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            def _hist_page(offset: int, limit: int):
                q = (
                    sb.table("precios_registro")
                    .select("precio_actual, volumen_ml, fecha_registro, tiendas(nombre)")
                    .eq("perfume_id", perfume_id)
                    .eq("en_stock", True)
                    .gt("precio_actual", 0)
                )
                if volumen_ml is not None:
                    q = q.eq("volumen_ml", int(volumen_ml))
                return q.order("fecha_registro", desc=False).range(offset, offset + limit - 1)

            filas = _fetch_all_rows(_hist_page, page_size=1000)
            registros = []
            for r in filas:
                tienda_info = r.get("tiendas")
                t_nombre = tienda_info.get("nombre", "Tienda") if isinstance(tienda_info, dict) else "Tienda"
                registros.append({
                    "tienda": t_nombre,
                    "precio_actual": r.get("precio_actual"),
                    "volumen_ml": r.get("volumen_ml") or 100,
                    "fecha_registro": r.get("fecha_registro"),
                })
            return registros
        except Exception as e:
            logger.warning(f"Error en Supabase obtener_historico_precios ({e}), usando SQLite.")

    init_db()
    params: List[Any] = [perfume_id]
    filtro_vol = ""
    if volumen_ml is not None:
        filtro_vol = " AND ABS(COALESCE(pr.volumen_ml, 100) - ?) < 2"
        params.append(int(volumen_ml))

    query = f"""
    SELECT t.nombre as tienda, pr.precio_actual, COALESCE(pr.volumen_ml, 100) as volumen_ml, pr.fecha_registro
    FROM precios_registro pr
    JOIN tiendas t ON pr.tienda_id = t.id
    WHERE pr.perfume_id = ?
      AND pr.en_stock = 1
      AND pr.precio_actual > 0
      {filtro_vol}
    ORDER BY pr.fecha_registro ASC;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def obtener_remates_reales(limite: int = 60, descuento_min_pct: int = 12) -> List[Dict[str, Any]]:
    """
    Consulta ofertas activas y verificadas en stock con descuento real comprobable
    (`precio_normal > precio_actual`, formato `'regular'`, volumen >= 25 ml),
    ordenadas de mayor a menor porcentaje de ahorro para la vista `remates.py`.
    """
    sb = get_supabase()
    if sb and is_supabase_disponible():
        try:
            def _remates_page(offset: int, limit: int):
                return (
                    sb.table("ofertas_actuales")
                    .select(
                        "id, precio_actual, precio_normal, en_stock, url_producto, ultima_verificacion_exitosa, "
                        "tiendas(id, nombre, url_base, trust_score, badge), "
                        "variantes_perfume!inner(id, perfume_id, volumen_ml, formato, "
                        "perfumes!inner(id, nombre, marca, tipo, notas, imagen_url, es_arabe))"
                    )
                    .eq("estado", "activa")
                    .eq("en_stock", True)
                    .gt("precio_actual", 0)
                    .order("id", desc=False)
                    .range(offset, offset + limit - 1)
                )

            filas = _fetch_all_rows(_remates_page, page_size=1000)
            candidatos: List[Dict[str, Any]] = []
            vistos_perfume_tienda: Set[Tuple[int, int, int]] = set()

            for item in filas:
                p_act = int(item.get("precio_actual") or 0)
                p_norm = int(item.get("precio_normal") or 0)
                if p_act <= 0 or p_norm <= p_act or p_norm >= 1_000_000:
                    continue

                vp = item.get("variantes_perfume") or {}
                perf = vp.get("perfumes") or {}
                t = item.get("tiendas") or {}
                vol = int(round(float(vp.get("volumen_ml") or 100)))
                url_prod = str(item.get("url_producto") or "")
                fmt = str(vp.get("formato") or "regular").lower()
                if fmt != "tester" and "tester" in url_prod.lower():
                    fmt = "tester"

                if vol < 25 or fmt == "tester" or not perf.get("id"):
                    continue

                ahorro = p_norm - p_act
                pct = int(round((ahorro * 100.0) / p_norm))
                if pct < descuento_min_pct or pct > 80 or ahorro < 3000:
                    continue

                pid = int(perf["id"])
                tid = int(t.get("id") or 0)
                key_dedup = (pid, tid, vol)
                if key_dedup in vistos_perfume_tienda:
                    continue
                vistos_perfume_tienda.add(key_dedup)

                candidatos.append({
                    "id": item.get("id") or pid,
                    "perfume_id": pid,
                    "nombre": perf.get("nombre", ""),
                    "marca": perf.get("marca", ""),
                    "tipo": perf.get("tipo", "Eau de Parfum"),
                    "notas": perf.get("notas", ""),
                    "imagen_url": perf.get("imagen_url", ""),
                    "es_arabe": bool(perf.get("es_arabe", False)),
                    "tienda": t.get("nombre", "Tienda Oficial"),
                    "url_base": t.get("url_base", ""),
                    "trust_score": int(t.get("trust_score") or 90),
                    "badge_tienda": t.get("badge", "Comercio Verificado"),
                    "volumen_ml": vol,
                    "precio_normal": p_norm,
                    "precio_remate": p_act,
                    "ahorro_clp": ahorro,
                    "descuento_pct": pct,
                    "url": url_prod,
                    "ultima_verificacion": item.get("ultima_verificacion_exitosa") or "",
                })

            candidatos.sort(key=lambda x: (-x["descuento_pct"], -x["ahorro_clp"], x["precio_remate"]))
            return candidatos[: max(1, int(limite))]
        except Exception as e:
            logger.warning(f"Error consultando remates reales en Supabase ({e}), usando SQLite.")

    init_db()
    with get_db_cursor() as cursor:
        cursor.execute("""
        SELECT oa.id, p.id as perfume_id, p.nombre, p.marca, p.tipo, p.notas, p.imagen_url, p.es_arabe,
               t.nombre as tienda, t.url_base, t.trust_score, t.badge as badge_tienda,
               CAST(ROUND(COALESCE(vp.volumen_ml, 100)) AS INTEGER) as volumen_ml,
               oa.precio_normal, oa.precio_actual as precio_remate,
               oa.url_producto as url, oa.ultima_verificacion_exitosa as ultima_verificacion
        FROM ofertas_actuales oa
        JOIN variantes_perfume vp ON vp.id = oa.variante_id
        JOIN perfumes p ON p.id = vp.perfume_id
        JOIN tiendas t ON t.id = oa.tienda_id
        WHERE oa.estado = 'activa'
          AND oa.en_stock = 1
          AND oa.precio_actual > 0
          AND oa.precio_normal > oa.precio_actual
          AND COALESCE(vp.volumen_ml, 100) >= 25
          AND LOWER(COALESCE(vp.formato, 'regular')) != 'tester'
        ORDER BY (CAST(oa.precio_normal - oa.precio_actual AS REAL) / oa.precio_normal) DESC
        LIMIT ?;
        """, (max(1, int(limite) * 2),))
        rows = [dict(r) for r in cursor.fetchall()]

        if not rows:
            cursor.execute("""
            SELECT pr.id, p.id as perfume_id, p.nombre, p.marca, p.tipo, p.notas, p.imagen_url, p.es_arabe,
                   t.nombre as tienda, t.url_base, t.trust_score, t.badge as badge_tienda,
                   COALESCE(pr.volumen_ml, 100) as volumen_ml,
                   pr.precio_normal, pr.precio_actual as precio_remate,
                   pr.url_producto as url, pr.fecha_registro as ultima_verificacion
            FROM precios_registro pr
            JOIN perfumes p ON p.id = pr.perfume_id
            JOIN tiendas t ON t.id = pr.tienda_id
            WHERE pr.en_stock = 1
              AND pr.precio_actual > 0
              AND pr.precio_normal > pr.precio_actual
              AND COALESCE(pr.volumen_ml, 100) >= 25
            ORDER BY pr.fecha_registro DESC
            LIMIT ?;
            """, (max(1, int(limite) * 2),))
            rows = [dict(r) for r in cursor.fetchall()]

        res_local: List[Dict[str, Any]] = []
        vistos_sq: Set[Tuple[int, str, int]] = set()
        for r in rows:
            p_act = int(r.get("precio_remate") or 0)
            p_norm = int(r.get("precio_normal") or 0)
            if p_act <= 0 or p_norm <= p_act or p_norm >= 1_000_000:
                continue
            if "tester" in str(r.get("url") or "").lower():
                continue
            ahorro = p_norm - p_act
            pct = int(round((ahorro * 100.0) / p_norm))
            if pct < descuento_min_pct or pct > 80 or ahorro < 3000:
                continue
            k = (int(r["perfume_id"]), str(r["tienda"]), int(r.get("volumen_ml") or 100))
            if k in vistos_sq:
                continue
            vistos_sq.add(k)
            r["ahorro_clp"] = ahorro
            r["descuento_pct"] = pct
            r["es_arabe"] = bool(r.get("es_arabe"))
            res_local.append(r)

        res_local.sort(key=lambda x: (-x["descuento_pct"], -x["ahorro_clp"], x["precio_remate"]))
        return res_local[: max(1, int(limite))]


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
    volumen_ml: int = 100,
    tipo: str = "Eau de Parfum",
    formato: Optional[str] = None,
    en_stock: bool = True,
) -> Dict[str, Any]:
    """
    Inserta o actualiza un perfume descubierto de forma canónica (sin `LIKE` ambiguo)
    y delega la persistencia de su oferta en `registrar_observacion_oferta`.
    """
    try:
        p_act_int = int(round(float(precio_actual)))
    except (ValueError, TypeError):
        return {"exito": False, "motivo": f"Precio inválido: {precio_actual}"}

    if p_act_int < 4000 or p_act_int >= 1000000 or p_act_int in (9999999, 9999990, 999999):
        return {"exito": False, "motivo": f"Precio fuera de rango comercial ({p_act_int})"}

    if int(volumen_ml or 100) < 25:
        return {"exito": False, "motivo": f"Volumen menor a 25 ml descartado ({volumen_ml} ml)"}

    marca_canon = normalizar_marca_canonica(marca) or "Diseñador"
    nombre_canon = limpiar_nombre_perfume(nombre, marca_canon) or (nombre or "").strip()
    if len(nombre_canon) < 2:
        return {"exito": False, "motivo": "Nombre de perfume vacío tras normalización"}

    formato_final = formato or detectar_formato_oferta(nombre, url_producto)
    p_norm_int = int(round(float(precio_normal))) if (precio_normal and precio_normal > p_act_int) else p_act_int
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sb = get_supabase(use_service_role=True)
    if sb and is_supabase_disponible():
        try:
            res_t = sb.table("tiendas").select("id").ilike("nombre", tienda_nombre.strip()).limit(1).execute()
            if res_t.data:
                tienda_id_sb = res_t.data[0]["id"]
            else:
                base_url = (
                    url_producto.split("/")[0] + "//" + url_producto.split("/")[2]
                    if "://" in url_producto
                    else "https://"
                )
                ins_t = sb.table("tiendas").insert({
                    "nombre": tienda_nombre.strip(),
                    "url_base": base_url,
                    "trust_score": 88,
                    "badge": "Tienda Verificada",
                    "logo_emoji": "",
                }).execute()
                tienda_id_sb = ins_t.data[0]["id"]

            genero_norm = (genero or "Unisex").strip() or "Unisex"
            res_p = (
                sb.table("perfumes")
                .select("id, genero")
                .ilike("marca", marca_canon)
                .ilike("nombre", nombre_canon)
                .ilike("tipo", tipo)
                .execute()
            )
            perfume_id_sb = None
            for cand_p in (res_p.data or []):
                g_cand = (cand_p.get("genero") or "Unisex").strip().lower()
                g_req = genero_norm.lower()
                if g_cand == g_req or (g_req == "unisex") or (g_cand == "unisex"):
                    perfume_id_sb = cand_p["id"]
                    break

            if perfume_id_sb is not None:
                es_nuevo = False
            else:
                es_nuevo = True
                img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
                notas_txt = notas or "Cítricos, Maderas, Almizcle"
                ins_p = sb.table("perfumes").insert({
                    "nombre": nombre_canon,
                    "marca": marca_canon,
                    "genero": genero_norm,
                    "tipo": tipo,
                    "notas": notas_txt,
                    "imagen_url": img,
                    "es_arabe": bool(es_arabe),
                    "en_tendencia": False,
                    "en_remate": bool(p_norm_int > p_act_int * 1.08),
                    "precio_referencia": p_norm_int,
                }).execute()
                perfume_id_sb = ins_p.data[0]["id"]

            registrar_observacion_oferta({
                "perfume_id_sb": perfume_id_sb,
                "tienda_id_sb": tienda_id_sb,
                "precio_actual": p_act_int,
                "precio_normal": p_norm_int,
                "en_stock": bool(en_stock),
                "url_producto": url_producto,
                "volumen_ml": int(volumen_ml),
                "formato": formato_final,
            })
            return {"exito": True, "perfume_id": perfume_id_sb, "es_nuevo": es_nuevo, "fecha": fecha_actual}
        except Exception as e:
            logger.error(f"Error persistiendo descubrimiento en Supabase ({marca_canon} - {nombre_canon}): {e}")
            return {"exito": False, "motivo": str(e)}

    # Respaldo SQLite local (coincidencia exacta canónica, sin LIKE ambiguo)
    init_db()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = LOWER(?);", (tienda_nombre.strip(),))
        row_tienda = cursor.fetchone()
        if row_tienda:
            tienda_id_sq = row_tienda["id"]
        else:
            base_url = (
                url_producto.split("/")[0] + "//" + url_producto.split("/")[2]
                if "://" in url_producto
                else "https://"
            )
            cursor.execute("""
            INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
            VALUES (?, ?, 88, 'Tienda Verificada', '');
            """, (tienda_nombre.strip(), base_url))
            tienda_id_sq = cursor.lastrowid

        genero_sq = (genero or "Unisex").strip() or "Unisex"
        cursor.execute("""
        SELECT id, genero FROM perfumes
        WHERE LOWER(TRIM(marca)) = LOWER(?)
          AND LOWER(TRIM(nombre)) = LOWER(?)
          AND LOWER(COALESCE(TRIM(tipo), '')) = LOWER(?);
        """, (marca_canon, nombre_canon, tipo))
        rows_perf = cursor.fetchall()
        row_perfume = None
        for rp in rows_perf:
            g_c = (rp["genero"] or "Unisex").strip().lower()
            if g_c == genero_sq.lower():
                row_perfume = rp
                break
        if row_perfume is None:
            for rp in rows_perf:
                g_c = (rp["genero"] or "Unisex").strip().lower()
                if genero_sq.lower() == "unisex" or g_c == "unisex":
                    row_perfume = rp
                    break

        es_nuevo_sq = False
        if row_perfume:
            perfume_id_sq = row_perfume["id"]
        else:
            es_nuevo_sq = True
            img = imagen_url or "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&q=80"
            notas_texto = notas or "Cítricos, Maderas, Almizcle"
            cursor.execute("""
            INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
            """, (
                nombre_canon, marca_canon, genero_sq, tipo, notas_texto, img,
                int(bool(es_arabe)), int(bool(p_norm_int > p_act_int * 1.08)), p_norm_int,
            ))
            perfume_id_sq = cursor.lastrowid

    registrar_observacion_oferta({
        "perfume_id_sqlite": perfume_id_sq,
        "tienda_id_sqlite": tienda_id_sq,
        "precio_actual": p_act_int,
        "precio_normal": p_norm_int,
        "en_stock": bool(en_stock),
        "url_producto": url_producto,
        "volumen_ml": int(volumen_ml),
        "formato": formato_final,
    })
    return {"exito": True, "perfume_id": perfume_id_sq, "es_nuevo": es_nuevo_sq, "fecha": fecha_actual}


# =============================================================================
# BLOQUE 13: AUDITORÍA DE TIENDAS Y MOTOR DE CONFIANZA (TRUSTSCORE CHILE)
# =============================================================================
def obtener_tiendas() -> List[Dict[str, Any]]:
    """Retorna la lista de tiendas registradas ordenadas por índice de confianza."""
    return obtener_tiendas_trust()


def obtener_tiendas_trust(
    filtro_tipo: Optional[str] = None,
    score_minimo: int = 0,
    busqueda: str = "",
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
        netloc = (parsed.netloc or parsed.path.split("/")[0]).replace("www.", "")
    except Exception:
        netloc = url_limpia

    tiendas_db = obtener_tiendas_trust()
    for t in tiendas_db:
        dominio_tienda = (
            t["url_base"]
            .lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip("/")
        )
        if dominio_tienda and (dominio_tienda in netloc or netloc in dominio_tienda):
            score_val = int(t.get("trust_score") or 90)
            p_base = max(15, min(25, round(score_val / 4)))
            return {
                "nombre": t.get("nombre") or "Tienda Auditada",
                "url": t.get("url_base") or url_limpia,
                "dominio": netloc,
                "score": score_val,
                "badge": t.get("badge") or "Tienda Verificada",
                "es_conocida": True,
                "tipo": t.get("tipo_tienda") or "Comercio Oficial Auditado",
                "rut": t.get("rut") or "Verificado SII",
                "ssl": bool(t.get("ssl_seguro", True)),
                "sello_ccs": bool(t.get("sello_ccs", score_val >= 92)),
                "antiguedad": f"{t.get('anios_antiguedad') or 5}+ años",
                "sernac": t.get("reclamos_sernac") or "Tasa baja / Resolución formal",
                "devolucion": t.get("politica_devolucion") or "Garantía legal SERNAC vigente",
                "desglose": {
                    "Seguridad Web (SSL/TLS)": f"{t.get('puntos_seguridad') or 25}/25",
                    "Legalidad & RUT": f"{t.get('puntos_legalidad') or p_base}/25",
                    "Garantía & Devoluciones": f"{t.get('puntos_garantia') or p_base}/25",
                    "Reputación & Sellos": f"{t.get('puntos_reputacion') or p_base}/25",
                },
                "senales_alerta": [],
                "recomendacion": (
                    "Comercio verificado y auditado en PerfumeTrending. "
                    "Cuenta con respaldo legal y trazabilidad en Chile."
                ),
            }

    puntos_ssl = 25 if url_limpia.startswith("https://") else 0
    es_cl = netloc.endswith(".cl")
    puntos_dominio = 25 if es_cl else 10

    senales_alerta = []
    palabras_sospechosas = [
        "outlet-original",
        "perfumes-ganga",
        "dior-chile-ofertas",
        "chanel-descuentos",
        "liquidaciones-lujo",
    ]
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
        recom = (
            "El sitio cuenta con HTTPS y dominio estándar, pero no está en el registro oficial "
            "de distribuidores autorizados. Revisa que permita pagar con Webpay y no solo transferencias personales."
        )
    else:
        badge = "Sitio No Verificado / Riesgo"
        recom = (
            "Precaución extrema. No se registran antecedentes comerciales formales ni sello de confianza. "
            "Posible tienda clon o producto sin garantía de originalidad."
        )

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
            "Acreditación": f"{puntos_reputacion}/25",
        },
        "senales_alerta": senales_alerta,
        "recomendacion": recom,
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

    url_cfg, key_cfg = get_supabase_credentials()
    print(f"Supabase URL configurada: {'Sí' if url_cfg else 'No'}")
    print(f"Supabase Key configurada: {'Sí' if key_cfg else 'No'}")
    print(f"Service Role configurada: {'Sí' if has_service_role_key() else 'No'}")

    sb_activo = is_supabase_disponible()
    print(f"Supabase Estado: {'CONECTADO Y DISPONIBLE' if sb_activo else 'NO DISPONIBLE / MODO SQLITE'}")
    print(f"SQLite Local: {DB_PATH} ({'Existe' if os.path.exists(DB_PATH) else 'No inicializada'})")

    if args.seed:
        print("\nEjecutando poblado de datos...")
        init_db(force_reseed=True)
        if sb_activo:
            poblar_datos_semilla_supabase()
        print("Poblado completado.")
    print("=" * 60)
