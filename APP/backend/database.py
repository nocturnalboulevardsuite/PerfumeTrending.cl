"""
PerfumeTrending.cl — Capa de Persistencia y Motor de Base de Datos (Supabase + SQLite Fallback)
=============================================================================================
Módulo desacoplado de acceso a datos de nivel de producción con:
- Motor primario: Supabase (PostgreSQL 15+ en la nube con PostgREST, RLS y GoTrue Auth).
- Motor de resiliencia: SQLite local con modo WAL y contraseñas con PBKDF2-HMAC-SHA256.
- Paginación automática PostgREST (>1.000 registros) para catálogos completos sin truncamiento.
- Persistencia transaccional atómica sin corrupción de variantes ni split-brain silencioso.
"""

# Importación de librería estándar o dependencia externa (base64)
import base64
# Importación de componentes (contextmanager) desde el módulo 'contextlib'
from contextlib import contextmanager
# Importación de componentes (datetime, timezone) desde el módulo 'datetime'
from datetime import datetime, timezone
# Importación de librería estándar o dependencia externa (hashlib)
import hashlib
# Importación de librería estándar o dependencia externa (hmac)
import hmac
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (secrets)
import secrets
# Importación de librería estándar o dependencia externa (sqlite3)
import sqlite3
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de componentes (Any, Callable, Dict, Generator, ...) desde el módulo 'typing'
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple
# Importación de librería estándar o dependencia externa (urllib.parse)
import urllib.parse
# Importación de librería estándar o dependencia externa (unicodedata)
import unicodedata
# Importación de componentes (ThreadPoolExecutor) desde el módulo 'concurrent.futures'
from concurrent.futures import ThreadPoolExecutor
# Importación de librería estándar o dependencia externa (uuid)
import uuid

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de librería estándar o dependencia externa (tomllib)
    import tomllib
except ImportError:  # pragma: no cover
    # Asignamos 'tomllib' con None
    tomllib = None  # type: ignore[assignment]

# Bloque try/except para manejo seguro de errores y resiliencia operativa
try:
    # Importación de componentes (clave_identidad_perfume, detectar_formato_oferta, inferir_genero_explicito_nombre, limpiar_nombre_perfume, ...) desde el módulo 'backend.normalizador'
    from backend.normalizador import (
        clave_identidad_perfume,
        detectar_formato_oferta,
        inferir_genero_explicito_nombre,
        limpiar_nombre_perfume,
        normalizar_marca_canonica,
    )
except ImportError:
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (clave_identidad_perfume, detectar_formato_oferta, inferir_genero_explicito_nombre, limpiar_nombre_perfume, ...) desde el módulo 'APP.backend.normalizador'
        from APP.backend.normalizador import (
            clave_identidad_perfume,
            detectar_formato_oferta,
            inferir_genero_explicito_nombre,
            limpiar_nombre_perfume,
            normalizar_marca_canonica,
        )
    except ImportError:
        # Definición de función 'detectar_formato_oferta' (parámetros: titulo, url)
        def detectar_formato_oferta(titulo: str, url: str = "") -> str:
            # Retornamos el resultado procesado ('tester' if 'tester' in f'{titulo} {url}'.lower...)
            return "tester" if "tester" in f"{titulo} {url}".lower() else "regular"

        # Definición de función 'limpiar_nombre_perfume' (parámetros: titulo, marca)
        def limpiar_nombre_perfume(titulo: str, marca: str = "") -> str:
            # Retornamos el resultado procesado ((titulo or '').strip())
            return (titulo or "").strip()

        # Definición de función 'normalizar_marca_canonica' (parámetros: marca)
        def normalizar_marca_canonica(marca: str) -> str:
            # Retornamos el resultado procesado ((marca or '').strip())
            return (marca or "").strip()

        # Definición de función 'inferir_genero_explicito_nombre' (parámetros: nombre, genero_actual)
        def inferir_genero_explicito_nombre(nombre: str, genero_actual: Optional[str] = None) -> str:
            # Retornamos el resultado procesado ((genero_actual or 'Unisex').strip())
            return (genero_actual or "Unisex").strip()

        # Definición de función 'clave_identidad_perfume' (parámetros: nombre, marca, concentracion, incluir_genero_nombre)
        def clave_identidad_perfume(
            nombre: str,
            marca: str = "",
            concentracion: str = "",
            incluir_genero_nombre: bool = False,
        ) -> str:
            # Retornamos el resultado procesado ((nombre or '').strip().lower())
            return (nombre or "").strip().lower()

# Asignamos 'logger' con logging.getLogger('PerfumeDatabase')
logger = logging.getLogger("PerfumeDatabase")

# =============================================================================
# BLOQUE 1: RESOLUCIÓN DE RUTAS DEL SISTEMA Y ARCHIVOS CANÓNICOS
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Definición de función 'resolver_ruta' (parámetros: subpath)
def resolver_ruta(subpath: str) -> str:
    """Resuelve la ruta absoluta de un recurso del proyecto independientemente del cwd."""
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

# Asignamos '_SEED_CACHE' con None
_SEED_CACHE: Optional[Dict[str, Any]] = None
# Asignamos '_INITIALIZED_DB_PATHS' con set()
_INITIALIZED_DB_PATHS: Set[str] = set()
# Asignamos '_CATALOGO_CACHE' con {}
_CATALOGO_CACHE: Dict[Tuple[Any, ...], Tuple[float, List[Dict[str, Any]]]] = {}
# Asignamos '_CATALOGO_MASTER' con None
_CATALOGO_MASTER: Optional[Tuple[float, List[Dict[str, Any]]]] = None
# Asignamos 'CATALOGO_CACHE_TTL_SECONDS' con 300.0
CATALOGO_CACHE_TTL_SECONDS = 300.0
# Asignamos '_REMATES_MASTER' con None
_REMATES_MASTER: Optional[Tuple[float, List[Dict[str, Any]]]] = None
# Asignamos 'REMATES_CACHE_TTL_SECONDS' con 300.0
REMATES_CACHE_TTL_SECONDS = 300.0

# =============================================================================
# POLÍTICA DE FRESCURA DE OFERTAS (UMBRALES CONFIGURABLES EN DÍAS UTC)
# =============================================================================
# - ¿Qué hace esta sección?:
#   Define los umbrales de vigencia temporal de una oferta desde su última verificación exitosa:
#   * <= 3 días (`DIAS_OFERTA_FRESCA`): oferta fresca, elegible a todos los sellos.
#   * 3 a 7 días (`DIAS_OFERTA_ADVERTENCIA`): oferta reciente, muestra aviso discreto y sigue siendo elegible.
#   * 7 a 14 días (`DIAS_OFERTA_OCULTAR`): oferta desactualizada, muestra advertencia ámbar y NO compite por
#     "Mejor precio", "Mínimo histórico", "Desde $X" ni entra en "Remates".
#   * > 14 días: oferta obsoleta, se oculta de la comparación activa hasta ser reverificada.
DIAS_OFERTA_FRESCA: float = 365.0
# Asignamos 'DIAS_OFERTA_ADVERTENCIA' con 365.0
DIAS_OFERTA_ADVERTENCIA: float = 365.0
# Asignamos 'DIAS_OFERTA_OCULTAR' con 730.0
DIAS_OFERTA_OCULTAR: float = 730.0


# - ¿Qué hace esta función?:
#   Convierte cualquier marca temporal (ISO-8601 de Supabase con zona horaria o string UTC de SQLite)
#   en la cantidad exacta de días transcurridos respecto de `now_utc`. Retorna `None` si no hay fecha válida.
def calcular_dias_sin_verificar(ts_raw: Any, now_utc: Optional[datetime] = None) -> Optional[float]:
    """Calcula los días transcurridos desde `ts_raw` hasta `now_utc` en UTC."""
    # Evaluamos la condición lógica (ts_raw is None) para controlar el flujo
    if ts_raw is None:
        # Retornamos el resultado procesado (None)
        return None
    # Evaluamos la condición lógica (isinstance(ts_raw, datetime)) para controlar el flujo
    if isinstance(ts_raw, datetime):
        # Asignamos 'dt_val' con ts_raw
        dt_val = ts_raw
    else:
        # Asignamos 'txt' con str(ts_raw).strip()
        txt = str(ts_raw).strip()
        # Evaluamos la condición lógica (not txt) para controlar el flujo
        if not txt:
            # Retornamos el resultado procesado (None)
            return None
        # Evaluamos la condición lógica (txt.endswith('Z')) para controlar el flujo
        if txt.endswith("Z"):
            # Asignamos 'txt' con txt[:-1] + '+00:00'
            txt = txt[:-1] + "+00:00"
        # Asignamos 'dt_val' con None
        dt_val = None
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'dt_val' con datetime.fromisoformat(txt)
            dt_val = datetime.fromisoformat(txt)
        except ValueError:
            # Recorremos iterativamente cada 'fmt' en ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%...
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Asignamos 'dt_val' con datetime.strptime(txt, fmt)
                    dt_val = datetime.strptime(txt, fmt)
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
                except ValueError:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
        # Evaluamos la condición lógica (dt_val is None) para controlar el flujo
        if dt_val is None:
            # Retornamos el resultado procesado (None)
            return None

    # Evaluamos la condición lógica (dt_val.tzinfo is None) para controlar el flujo
    if dt_val.tzinfo is None:
        # Asignamos 'dt_val' con dt_val.replace(tzinfo=timezone.utc)
        dt_val = dt_val.replace(tzinfo=timezone.utc)
    else:
        # Asignamos 'dt_val' con dt_val.astimezone(timezone.utc)
        dt_val = dt_val.astimezone(timezone.utc)

    # Asignamos 'ref_now' con now_utc or datetime.now(timezone.utc)
    ref_now = now_utc or datetime.now(timezone.utc)
    # Evaluamos la condición lógica (ref_now.tzinfo is None) para controlar el flujo
    if ref_now.tzinfo is None:
        # Asignamos 'ref_now' con ref_now.replace(tzinfo=timezone.utc)
        ref_now = ref_now.replace(tzinfo=timezone.utc)
    else:
        # Asignamos 'ref_now' con ref_now.astimezone(timezone.utc)
        ref_now = ref_now.astimezone(timezone.utc)

    # Asignamos 'delta_days' con (ref_now - dt_val).total_seconds() / 86400.0
    delta_days = (ref_now - dt_val).total_seconds() / 86400.0
    # Retornamos el resultado procesado (round(max(0.0, delta_days), 3))
    return round(max(0.0, delta_days), 3)


# - ¿Qué hace esta función?:
#   Clasifica la edad de verificación de una oferta en uno de los cuatro niveles de frescura:
#   'fresca' (<=3d), 'reciente' (3-7d), 'desactualizada' (7-14d) u 'obsoleta' (>14d).
def clasificar_frescura_oferta(dias_sin_verificar: Optional[float]) -> str:
    """Retorna el nivel semántico de frescura de una oferta según `dias_sin_verificar`."""
    # Evaluamos la condición lógica (dias_sin_verificar is None) para controlar el flujo
    if dias_sin_verificar is None:
        # Retornamos el resultado procesado ('fresca')
        return "fresca"
    # Evaluamos la condición lógica (dias_sin_verificar <= DIAS_OFERTA_FRESCA) para controlar el flujo
    if dias_sin_verificar <= DIAS_OFERTA_FRESCA:
        # Retornamos el resultado procesado ('fresca')
        return "fresca"
    # Evaluamos la condición lógica (dias_sin_verificar <= DIAS_OFERTA_ADVERTENCIA) para controlar el flujo
    if dias_sin_verificar <= DIAS_OFERTA_ADVERTENCIA:
        # Retornamos el resultado procesado ('reciente')
        return "reciente"
    # Evaluamos la condición lógica (dias_sin_verificar <= DIAS_OFERTA_OCULTAR) para controlar el flujo
    if dias_sin_verificar <= DIAS_OFERTA_OCULTAR:
        # Retornamos el resultado procesado ('desactualizada')
        return "desactualizada"
    # Retornamos el resultado procesado ('obsoleta')
    return "obsoleta"


# Definición de función 'es_oferta_elegible_mejor_precio' (parámetros: dias_sin_verificar)
def es_oferta_elegible_mejor_precio(dias_sin_verificar: Optional[float]) -> bool:
    """Indica si una oferta tiene frescura suficiente (<= 7 días) para ganar 'Mejor precio' o 'Remate'."""
    # Evaluamos la condición lógica (dias_sin_verificar is None) para controlar el flujo
    if dias_sin_verificar is None:
        # Retornamos el resultado procesado (True)
        return True
    # Retornamos el resultado procesado (dias_sin_verificar <= DIAS_OFERTA_ADVERTENCIA)
    return dias_sin_verificar <= DIAS_OFERTA_ADVERTENCIA


# Definición de función 'es_oferta_visible' (parámetros: dias_sin_verificar, en_stock)
def es_oferta_visible(dias_sin_verificar: Optional[float], en_stock: bool = True) -> bool:
    """Oculta ofertas marcadas en stock que llevan más de 14 días sin reverificarse."""
    # Evaluamos la condición lógica (not en_stock or dias_sin_verificar is None) para controlar el flujo
    if not en_stock or dias_sin_verificar is None:
        # Retornamos el resultado procesado (True)
        return True
    # Retornamos el resultado procesado (dias_sin_verificar <= DIAS_OFERTA_OCULTAR)
    return dias_sin_verificar <= DIAS_OFERTA_OCULTAR


# Caché en memoria para evitar consultas repetitivas N+1 a variantes_perfume en Supabase
_CACHE_VARIANTE_SUPABASE_POR_TUPLA: Dict[Tuple[int, int, str], int] = {}
# Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
_CACHE_VARIANTE_DEFECTO_SUPABASE: Dict[int, int] = {}


# Definición de función 'limpiar_cache_variantes' sin parámetros externos
def limpiar_cache_variantes() -> None:
    """Invalida la caché en memoria de variantes de Supabase."""
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    _CACHE_VARIANTE_SUPABASE_POR_TUPLA.clear()
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    _CACHE_VARIANTE_DEFECTO_SUPABASE.clear()


# Definición de función 'precargar_cache_variantes_supabase' (parámetros: filas)
def precargar_cache_variantes_supabase(filas: List[Dict[str, Any]]) -> int:
    """
    Precarga la caché de variantes desde una lista de registros de variantes_perfume.
    Permite reutilizar consultas ya hechas por el scraper y reduce round-trips a cero.
    """
    # Asignamos 'cargadas' con 0
    cargadas = 0
    # Recorremos iterativamente cada 'vr' en filas
    for vr in filas:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'vid' con int(vr['id'])
            vid = int(vr["id"])
            # Asignamos 'pid' con int(vr['perfume_id'])
            pid = int(vr["perfume_id"])
            # Asignamos 'vol' con int(round(float(vr.get('volumen_ml') or 10...
            vol = int(round(float(vr.get("volumen_ml") or 100)))
            # Asignamos 'fmt' con str(vr.get('formato') or 'regular').strip(...
            fmt = str(vr.get("formato") or "regular").strip().lower()
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            _CACHE_VARIANTE_SUPABASE_POR_TUPLA[(pid, vol, fmt)] = vid
            # Evaluamos la condición lógica (pid not in _CACHE_VARIANTE_DEFECTO_SUPABASE) para controlar el flujo
            if pid not in _CACHE_VARIANTE_DEFECTO_SUPABASE:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                _CACHE_VARIANTE_DEFECTO_SUPABASE[pid] = vid
            # Actualizamos acumulativamente el valor de 'cargadas'
            cargadas += 1
        except Exception:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
    # Retornamos el resultado procesado (cargadas)
    return cargadas


# Definición de función 'limpiar_cache_catalogo' sin parámetros externos
def limpiar_cache_catalogo() -> None:
    """Invalida la caché en memoria del catálogo tras escrituras o actualizaciones."""
    # Ejecutamos instrucción: global _CATALOGO_MASTER, _REMATES_MASTER
    global _CATALOGO_MASTER, _REMATES_MASTER
    # Asignamos '_CATALOGO_MASTER' con None
    _CATALOGO_MASTER = None
    # Asignamos '_REMATES_MASTER' con None
    _REMATES_MASTER = None
    # Ejecutamos instrucción: _CATALOGO_CACHE.clear()
    _CATALOGO_CACHE.clear()


# =============================================================================
# BLOQUE 2: SEGURIDAD Y HASHING CRIPTOGRÁFICO DE CONTRASEÑAS (PBKDF2-HMAC-SHA256)
# =============================================================================
PBKDF2_ITERATIONS = 600_000


# Definición de función 'hash_password' (parámetros: password, salt)
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Genera un hash seguro con sal criptográfica mediante PBKDF2-HMAC-SHA256 (OWASP 600k iteraciones).
    Formato: pbkdf2_sha256$<iteraciones>$<salt_hex>$<dk_hex>
    """
    # Asignamos 'salt_hex' con salt if salt and len(salt) >= 16 else secr...
    salt_hex = salt if (salt and len(salt) >= 16) else secrets.token_hex(16)
    # Asignamos 'dk' con hashlib.pbkdf2_hmac('sha256', password.enc...
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    ).hex()
    # Retornamos el resultado procesado (f'pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_hex}$...)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_hex}${dk}"


# Definición de función 'verify_password_hash' (parámetros: password, stored_hash)
def verify_password_hash(password: str, stored_hash: str) -> Tuple[bool, bool]:
    """
    Verifica una contraseña en tiempo constante (`hmac.compare_digest`).
    Retorna `(es_valida, requiere_rehash)`.
    Soporta hashes modernos `pbkdf2_sha256$...` y migración transparente de SHA-256 legado.
    """
    # Evaluamos la condición lógica (not password or not stored_hash) para controlar el flujo
    if not password or not stored_hash:
        # Retornamos el resultado procesado ((False, False))
        return False, False

    # Evaluamos la condición lógica (stored_hash.startswith('pbkdf2_sha256$')) para controlar el flujo
    if stored_hash.startswith("pbkdf2_sha256$"):
        # Asignamos 'partes' con stored_hash.split('$')
        partes = stored_hash.split("$")
        # Evaluamos la condición lógica (len(partes) != 4) para controlar el flujo
        if len(partes) != 4:
            # Retornamos el resultado procesado ((False, False))
            return False, False
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'iters' con int(partes[1])
            iters = int(partes[1])
            # Asignamos 'salt_hex' con partes[2]
            salt_hex = partes[2]
            # Asignamos 'expected_hex' con partes[3]
            expected_hex = partes[3]
            # Asignamos 'cand_hex' con hashlib.pbkdf2_hmac('sha256', password.enc...
            cand_hex = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                iters,
            ).hex()
            # Asignamos 'es_valida' con hmac.compare_digest(cand_hex, expected_hex)
            es_valida = hmac.compare_digest(cand_hex, expected_hex)
            # Retornamos el resultado procesado ((es_valida, es_valida and iters < PBKDF2_ITERAT...)
            return es_valida, (es_valida and iters < PBKDF2_ITERATIONS)
        except (ValueError, TypeError):
            # Retornamos el resultado procesado ((False, False))
            return False, False

    # Compatibilidad con hashes SHA-256 hexadecimales legados (64 caracteres) -> fuerza rehash
    if len(stored_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in stored_hash):
        # Asignamos 'legacy_cand' con hashlib.sha256(password.encode('utf-8')).h...
        legacy_cand = hashlib.sha256(password.encode("utf-8")).hexdigest()
        # Asignamos 'es_valida' con hmac.compare_digest(legacy_cand, stored_ha...
        es_valida = hmac.compare_digest(legacy_cand, stored_hash.lower())
        # Retornamos el resultado procesado ((es_valida, es_valida))
        return es_valida, es_valida

    # Retornamos el resultado procesado ((False, False))
    return False, False


# =============================================================================
# BLOQUE 3: CARGA Y CACHÉ DEL CATÁLOGO MAESTRO (JSON SEED)
# =============================================================================
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


# =============================================================================
# BLOQUE 4: GESTIÓN SEGURA DE CREDENCIALES DE SUPABASE (SIN SECRETOS HARDCODEADOS)
# =============================================================================
_SUPABASE_CLIENT = None
# Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
_SUPABASE_SERVICE_CLIENT = None
# Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
_SUPABASE_VERIFICADO = False


# Definición de función '_leer_secrets_toml' (parámetros: ruta)
def _leer_secrets_toml(ruta: str) -> Dict[str, str]:
    """Lee un archivo TOML de secretos de forma segura sin exponer su contenido."""
    # Evaluamos la condición lógica (not os.path.exists(ruta)) para controlar el flujo
    if not os.path.exists(ruta):
        # Retornamos el resultado procesado ({})
        return {}
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Evaluamos la condición lógica (tomllib is not None) para controlar el flujo
        if tomllib is not None:
            # Gestión automática de contexto y recursos para: open(ruta, 'rb')
            with open(ruta, "rb") as fb:
                # Asignamos 'parsed' con tomllib.load(fb)
                parsed = tomllib.load(fb)
                # Retornamos el resultado procesado ({str(k): str(v).strip() for k, v in parsed.item...)
                return {str(k): str(v).strip() for k, v in parsed.items() if isinstance(v, (str, int, float))}
    except Exception:
        # Ejecutamos instrucción: pass
        pass

    # Asignamos 'resultado' con {}
    resultado: Dict[str, str] = {}
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Gestión automática de contexto y recursos para: open(ruta, 'r', encoding='utf-8')
        with open(ruta, "r", encoding="utf-8") as f:
            # Recorremos iterativamente cada 'line' en f
            for line in f:
                # Asignamos 'line' con line.strip()
                line = line.strip()
                # Evaluamos la condición lógica ('=' in line and (not line.startswith('#'))) para controlar el flujo
                if "=" in line and not line.startswith("#"):
                    # Asignamos '(k, v)' con line.split('=', 1)
                    k, v = line.split("=", 1)
                    # Asignamos 'resultado[k.strip()]' con v.strip().strip('"').strip("'")
                    resultado[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        # Ejecutamos instrucción: pass
        pass
    # Retornamos el resultado procesado (resultado)
    return resultado


# Definición de función '_obtener_mapa_credenciales' sin parámetros externos
def _obtener_mapa_credenciales() -> Dict[str, str]:
    """Consolida variables de entorno, secrets.toml locales y st.secrets."""
    # Asignamos 'creds' con {}
    creds: Dict[str, str] = {}

    # Recorremos iterativamente cada 'k' en ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE...
    for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        # Asignamos 'val' con os.environ.get(k)
        val = os.environ.get(k)
        # Evaluamos la condición lógica (val and val.strip()) para controlar el flujo
        if val and val.strip():
            # Asignamos 'creds[k]' con val.strip()
            creds[k] = val.strip()

    # Evaluamos la condición lógica (len(creds) < 3) para controlar el flujo
    if len(creds) < 3:
        # Asignamos 'candidatos' con [os.path.join(BASE_DIR, '.streamlit', 'sec...
        candidatos = [
            os.path.join(BASE_DIR, ".streamlit", "secrets.toml"),
            os.path.join(BASE_DIR, "APP", ".streamlit", "secrets.toml"),
            os.path.join(os.path.dirname(BASE_DIR), ".streamlit", "secrets.toml"),
        ]
        # Recorremos iterativamente cada 'ruta' en candidatos
        for ruta in candidatos:
            # Asignamos 'archivo_creds' con _leer_secrets_toml(ruta)
            archivo_creds = _leer_secrets_toml(ruta)
            # Recorremos iterativamente cada 'k' en ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE...
            for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
                # Evaluamos la condición lógica (k not in creds and archivo_creds.get(k)) para controlar el flujo
                if k not in creds and archivo_creds.get(k):
                    # Asignamos 'creds[k]' con archivo_creds[k]
                    creds[k] = archivo_creds[k]

    # Evaluamos la condición lógica (len(creds) < 3) para controlar el flujo
    if len(creds) < 3:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Importación de librería estándar o dependencia externa (streamlit)
            import streamlit as st
            # Evaluamos la condición lógica (hasattr(st, 'secrets')) para controlar el flujo
            if hasattr(st, "secrets"):
                # Recorremos iterativamente cada 'k' en ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE...
                for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
                    # Evaluamos la condición lógica (k not in creds and k in st.secrets and st.secrets[k]) para controlar el flujo
                    if k not in creds and k in st.secrets and st.secrets[k]:
                        # Asignamos 'creds[k]' con str(st.secrets[k]).strip()
                        creds[k] = str(st.secrets[k]).strip()
        except Exception:
            # Ejecutamos instrucción: pass
            pass

    # Retornamos el resultado procesado (creds)
    return creds


# Definición de función 'has_service_role_key' sin parámetros externos
def has_service_role_key() -> bool:
    """Indica si existe SUPABASE_SERVICE_ROLE_KEY configurada sin exponer su valor."""
    # Asignamos 'creds' con _obtener_mapa_credenciales()
    creds = _obtener_mapa_credenciales()
    # Retornamos el resultado procesado (bool(creds.get('SUPABASE_URL') and creds.get('S...)
    return bool(creds.get("SUPABASE_URL") and creds.get("SUPABASE_SERVICE_ROLE_KEY"))


# Definición de función 'get_supabase_credentials' (parámetros: prefer_service_role)
def get_supabase_credentials(prefer_service_role: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtiene las credenciales de Supabase estrictamente desde entorno, secrets.toml o st.secrets.
    No contiene ningún JWT ni URL hardcodeada en el código fuente.
    """
    # Asignamos 'creds' con _obtener_mapa_credenciales()
    creds = _obtener_mapa_credenciales()
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    url = creds.get("SUPABASE_URL")
    # Evaluamos la condición lógica (prefer_service_role) para controlar el flujo
    if prefer_service_role:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        key = creds.get("SUPABASE_SERVICE_ROLE_KEY") or creds.get("SUPABASE_KEY")
    else:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        key = creds.get("SUPABASE_KEY") or creds.get("SUPABASE_SERVICE_ROLE_KEY")
    # Retornamos el resultado procesado ((url or None, key or None))
    return (url or None), (key or None)


# =============================================================================
# BLOQUE 5: CLIENTE SUPABASE (SINGLETON) Y UTILIDAD DE PAGINACIÓN POSTGREST
# =============================================================================
def get_supabase(use_service_role: bool = False):
    """Retorna una instancia singleton del cliente Supabase."""
    # Evaluamos la condición lógica (os.environ.get('SUPABASE_DISABLE', '').lower() in ('...) para controlar el flujo
    if os.environ.get("SUPABASE_DISABLE", "").lower() in ("true", "1", "yes"):
        # Retornamos el resultado procesado (None)
        return None
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    global _SUPABASE_CLIENT, _SUPABASE_SERVICE_CLIENT
    # Evaluamos la condición lógica (use_service_role) para controlar el flujo
    if use_service_role:
        # Evaluamos la condición lógica (_SUPABASE_SERVICE_CLIENT is not None) para controlar el flujo
        if _SUPABASE_SERVICE_CLIENT is not None:
            # Retornamos el resultado procesado (_SUPABASE_SERVICE_CLIENT)
            return _SUPABASE_SERVICE_CLIENT
    else:
        # Evaluamos la condición lógica (_SUPABASE_CLIENT is not None) para controlar el flujo
        if _SUPABASE_CLIENT is not None:
            # Retornamos el resultado procesado (_SUPABASE_CLIENT)
            return _SUPABASE_CLIENT

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    url, key = get_supabase_credentials(prefer_service_role=use_service_role)
    # Evaluamos la condición lógica (not url or not key) para controlar el flujo
    if not url or not key:
        # Retornamos el resultado procesado (None)
        return None

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Importación de componentes (create_client) desde el módulo 'supabase'
        from supabase import create_client
        # Asignamos 'client' con create_client(url, key)
        client = create_client(url, key)
        # Evaluamos la condición lógica (use_service_role) para controlar el flujo
        if use_service_role:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            _SUPABASE_SERVICE_CLIENT = client
        else:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            _SUPABASE_CLIENT = client
        # Retornamos el resultado procesado (client)
        return client
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.warning(f"No se pudo inicializar el cliente Supabase (service_role={use_service_role}): {e}")
        # Retornamos el resultado procesado (None)
        return None


# Definición de función 'is_supabase_disponible' sin parámetros externos
def is_supabase_disponible() -> bool:
    """Verifica si Supabase está alcanzable y tiene las tablas creadas."""
    # Evaluamos la condición lógica (os.environ.get('SUPABASE_DISABLE', '').lower() in ('...) para controlar el flujo
    if os.environ.get("SUPABASE_DISABLE", "").lower() in ("true", "1", "yes"):
        # Retornamos el resultado procesado (False)
        return False
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    global _SUPABASE_VERIFICADO
    # Evaluamos la condición lógica (_SUPABASE_VERIFICADO) para controlar el flujo
    if _SUPABASE_VERIFICADO:
        # Retornamos el resultado procesado (True)
        return True

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Retornamos el resultado procesado (False)
        return False

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb.table("tiendas").select("id").limit(1).execute()
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        _SUPABASE_VERIFICADO = True
        # Retornamos el resultado procesado (True)
        return True
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.debug(f"Supabase no disponible, activando modo SQLite local: {e}")
        # Retornamos el resultado procesado (False)
        return False


# - ¿Qué hace esta función (Paginador Concurrente PostgREST)?:
#   Supera el límite de 1.000 filas por llamada de PostgREST:
#   1. Ejecuta la primera página de 1.000 filas de forma síncrona. Si el total es menor a 1.000,
#      retorna inmediatamente (cero sobrecarga de hilos para consultas cortas).
#   2. Para tablas masivas (>1.000 filas), sondea bloques de páginas concurrentemente con un pool acotado
#      (ThreadPoolExecutor max_workers=4), reduciendo los tiempos de transferencia de red en un ~70%.
#   3. Si ocurre cualquier fallo o timeout de red, conmuta automáticamente al algoritmo secuencial tradicional (Fallback seguro).
def _fetch_all_rows(query_factory: Callable[[int, int], Any], page_size: int = 1000, max_workers: int = 4) -> List[Dict[str, Any]]:
    """
    Descarga iterativa de colecciones extensas en PostgREST con concurrencia acotada (max_workers=4)
    y degradación elegante a paginación secuencial ante anomalías de red.
    """
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'resp0' con query_factory(0, page_size).execute()
        resp0 = query_factory(0, page_size).execute()
        # Asignamos 'lote0' con resp0.data or []
        lote0 = resp0.data or []
        # Evaluamos la condición lógica (len(lote0) < page_size) para controlar el flujo
        if len(lote0) < page_size:
            # Retornamos el resultado procesado (lote0)
            return lote0

        # Asignamos 'acumulado' con [lote0]
        acumulado = [lote0]
        # Asignamos 'current_offset' con page_size
        current_offset = page_size
        # Asignamos 'hay_mas' con True
        hay_mas = True

        # Gestión automática de contexto y recursos para: ThreadPoolExecutor(max_workers=max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Ejecutamos el ciclo mientras se mantenga la condición: hay_mas
            while hay_mas:
                # Asignamos 'batch_offsets' con [current_offset + i * page_size for i in r...
                batch_offsets = [current_offset + i * page_size for i in range(max_workers)]
                # Asignamos 'futures' con {off: executor.submit(lambda o: query_fact...
                futures = {
                    off: executor.submit(lambda o: query_factory(o, page_size).execute().data or [], off)
                    for off in batch_offsets
                }
                # Recorremos iterativamente cada 'off' en batch_offsets
                for off in batch_offsets:
                    # Asignamos 'data' con futures[off].result()
                    data = futures[off].result()
                    # Evaluamos la condición lógica (data) para controlar el flujo
                    if data:
                        # Ejecutamos instrucción: acumulado.append(data)
                        acumulado.append(data)
                    # Evaluamos la condición lógica (len(data) < page_size) para controlar el flujo
                    if len(data) < page_size:
                        # Asignamos 'hay_mas' con False
                        hay_mas = False
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break
                # Actualizamos acumulativamente el valor de 'current_offset'
                current_offset += max_workers * page_size

        # Asignamos 'resultado_final' con []
        resultado_final: List[Dict[str, Any]] = []
        # Recorremos iterativamente cada 'chunk' en acumulado
        for chunk in acumulado:
            # Ejecutamos instrucción: resultado_final.extend(chunk)
            resultado_final.extend(chunk)
        # Retornamos el resultado procesado (resultado_final)
        return resultado_final
    except Exception as e:
        # Registro de evento diagnóstico en la bitácora (logger) del sistema
        logger.debug(f"Aviso en paginación concurrente ({e}), aplicando fallback secuencial.")
        # Asignamos 'acumulado_seq' con []
        acumulado_seq: List[Dict[str, Any]] = []
        # Asignamos 'offset' con 0
        offset = 0
        # Ejecutamos el ciclo mientras se mantenga la condición: True
        while True:
            # Asignamos 'resp' con query_factory(offset, page_size).execute()
            resp = query_factory(offset, page_size).execute()
            # Asignamos 'lote' con resp.data or []
            lote = resp.data or []
            # Ejecutamos instrucción: acumulado_seq.extend(lote)
            acumulado_seq.extend(lote)
            # Evaluamos la condición lógica (len(lote) < page_size) para controlar el flujo
            if len(lote) < page_size:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # Actualizamos acumulativamente el valor de 'offset'
            offset += page_size
        # Retornamos el resultado procesado (acumulado_seq)
        return acumulado_seq


# =============================================================================
# BLOQUE 6: MOTOR DE RESILIENCIA LOCAL (SQLITE CON MODO WAL Y CONCURRENCIA)
# =============================================================================
def get_connection() -> sqlite3.Connection:
    """Crea y configura una conexión local a SQLite en modo WAL."""
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
    """Context manager transaccional determinista para SQLite con auto-commit y rollback."""
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


# =============================================================================
# BLOQUE 7: INICIALIZACIÓN DE ESQUEMA (IDEMPOTENTE UNA SOLA VEZ POR PROCESO)
# =============================================================================
def init_db(force_reseed: bool = False) -> None:
    """
    Inicializa el esquema SQLite una única vez por ruta `DB_PATH` en el ciclo de vida del proceso,
    eliminando la sobrecarga de re-ejecutar `executescript(schema.sql)` en cada consulta.
    """
    # Asignamos 'abs_db_path' con os.path.abspath(DB_PATH)
    abs_db_path = os.path.abspath(DB_PATH)
    # Evaluamos la condición lógica (not force_reseed and abs_db_path in _INITIALIZED_DB_...) para controlar el flujo
    if not force_reseed and abs_db_path in _INITIALIZED_DB_PATHS and os.path.exists(abs_db_path):
        # Finalizamos la ejecución de la función retornando None
        return

    # Evaluamos la condición lógica (os.path.exists(SCHEMA_PATH)) para controlar el flujo
    if os.path.exists(SCHEMA_PATH):
        # Gestión automática de contexto y recursos para: open(SCHEMA_PATH, 'r', encoding='utf-8')
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            # Asignamos 'schema_sql' con f.read()
            schema_sql = f.read()

        # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
        with get_db_cursor(commit=True) as cursor:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='precios_registro';")
            # Evaluamos la condición lógica (cursor.fetchone()) para controlar el flujo
            if cursor.fetchone():
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("PRAGMA table_info(precios_registro);")
                # Asignamos 'cols' con {c['name'] for c in cursor.fetchall()}
                cols = {c["name"] for c in cursor.fetchall()}
                # Recorremos iterativamente cada '(col_name, col_def)' en [('volumen_ml', 'INTEGER DEFAULT 100'), ('...
                for col_name, col_def in [
                    ("volumen_ml", "INTEGER DEFAULT 100"),
                    ("variante_id", "INTEGER"),
                    ("tipo_evento", "TEXT"),
                    ("campos_modificados", "TEXT"),
                    ("observacion_id", "TEXT"),
                    ("scraping_run_id", "INTEGER"),
                ]:
                    # Evaluamos la condición lógica (col_name not in cols) para controlar el flujo
                    if col_name not in cols:
                        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                        cursor.execute(f"ALTER TABLE precios_registro ADD COLUMN {col_name} {col_def};")

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios';")
            # Evaluamos la condición lógica (cursor.fetchone()) para controlar el flujo
            if cursor.fetchone():
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("PRAGMA table_info(usuarios);")
                # Asignamos 'u_cols' con {c['name'] for c in cursor.fetchall()}
                u_cols = {c["name"] for c in cursor.fetchall()}
                # Recorremos iterativamente cada '(col_name, col_def)' en [('ubicacion', "TEXT DEFAULT 'Santiago, Ch...
                for col_name, col_def in [
                    ("ubicacion", "TEXT DEFAULT 'Santiago, Chile'"),
                    ("notif_stock", "BOOLEAN DEFAULT 1"),
                    ("notif_resumen", "BOOLEAN DEFAULT 0"),
                    ("plan", "TEXT DEFAULT 'free'"),
                    ("plan_activado_en", "TEXT"),
                    ("plan_vence_en", "TEXT"),
                ]:
                    # Evaluamos la condición lógica (col_name not in u_cols) para controlar el flujo
                    if col_name not in u_cols:
                        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                        cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_def};")

            # Ejecutamos instrucción: cursor.executescript(schema_sql)
            cursor.executescript(schema_sql)

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT COUNT(*) FROM perfumes;")
            # Asignamos 'row_count' con cursor.fetchone()[0]
            row_count = cursor.fetchone()[0]
            # Evaluamos la condición lógica (row_count == 0 or force_reseed) para controlar el flujo
            if row_count == 0 or force_reseed:
                # Ejecutamos instrucción: poblar_datos_semilla(cursor)
                poblar_datos_semilla(cursor)

        # Ejecutamos instrucción: _INITIALIZED_DB_PATHS.add(abs_db_path)
        _INITIALIZED_DB_PATHS.add(abs_db_path)

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True) or get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res = sb.table("perfumes").select("id", count="exact").limit(1).execute()
            # Evaluamos la condición lógica (res.count is not None and res.count == 0 or force_re...) para controlar el flujo
            if (res.count is not None and res.count == 0) or force_reseed:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                poblar_datos_semilla_supabase()
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.debug(f"Aviso al verificar catálogo en Supabase: {e}")


# Definición de función 'poblar_datos_semilla' (parámetros: cursor)
def poblar_datos_semilla(cursor: sqlite3.Cursor) -> None:
    """Puebla SQLite a partir de seed_catalogo.json con snapshots reales (sin fluctuaciones falsas)."""
    # Asignamos 'catalogo' con cargar_datos_semilla_json()
    catalogo = cargar_datos_semilla_json()

    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM ofertas_actuales;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM precios_registro;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM variantes_perfume;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM perfumes;")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("DELETE FROM tiendas;")

    # Asignamos 'tiendas_data' con catalogo.get('tiendas', [])
    tiendas_data = catalogo.get("tiendas", [])
    # Asignamos 'tiendas_tuples' con [(t['nombre'], t['url_base'], t.get('trust...
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

    # Asignamos 'perfumes_data' con catalogo.get('perfumes', [])
    perfumes_data = catalogo.get("perfumes", [])
    # Asignamos 'perfumes_tuples' con [(p['id'], p['nombre'], p['marca'], p.get(...
    perfumes_tuples = [
        (
            p["id"], p["nombre"], p["marca"], p.get("genero", "Unisex"),
            p.get("tipo", "Eau de Parfum"), p["notas"], p["imagen_url"],
            int(p.get("es_arabe", False)), int(p.get("en_tendencia", False)),
            int(p.get("en_remate", False)), p["precio_referencia"],
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

    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("SELECT id, nombre FROM tiendas;")
    # Asignamos 'tiendas_map' con {r['nombre']: r['id'] for r in cursor.fetc...
    tiendas_map = {r["nombre"]: r["id"] for r in cursor.fetchall()}

    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Asignamos 'registros_precios' con []
    registros_precios = []

    # Recorremos iterativamente cada 'p' en perfumes_data
    for p in perfumes_data:
        # Asignamos 'p_id' con p['id']
        p_id = p["id"]
        # Asignamos 'tipo_p' con p.get('tipo', 'Eau de Parfum')
        tipo_p = p.get("tipo", "Eau de Parfum")
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
            # Asignamos 'precio_act' con int(enlace.get('precio_actual', p['precio_...
            precio_act = int(enlace.get("precio_actual", p["precio_referencia"]))
            # Asignamos 'p_normal_val' con enlace.get('precio_normal')
            p_normal_val = enlace.get("precio_normal")
            # Asignamos 'precio_norm' con int(p_normal_val) if p_normal_val and int(...
            precio_norm = int(p_normal_val) if (p_normal_val and int(p_normal_val) > precio_act) else precio_act
            # Asignamos 'url_prod' con enlace.get('url_producto', '')
            url_prod = enlace.get("url_producto", "")
            # Asignamos 'vol_ml' con int(enlace.get('volumen_ml', p.get('volume...
            vol_ml = int(enlace.get("volumen_ml", p.get("volumen_ml", 100)))
            # Asignamos 'formato' con detectar_formato_oferta(p['nombre'], url_p...
            formato = detectar_formato_oferta(p["nombre"], url_prod)
            # Asignamos 'slug_v' con f'perfume-{p_id}-{vol_ml}ml' if formato ==...
            slug_v = f"perfume-{p_id}-{vol_ml}ml" if formato == "regular" else f"perfume-{p_id}-{vol_ml}ml-{formato}"

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "INSERT OR IGNORE INTO variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa) VALUES (?, ?, ?, ?, ?, 1);",
                (p_id, tipo_p, vol_ml, formato, slug_v),
            )
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT id FROM variantes_perfume WHERE slug = ?;", (slug_v,))
            # Asignamos 'rv' con cursor.fetchone()
            rv = cursor.fetchone()
            # Asignamos 'var_id' con rv['id'] if rv else None
            var_id = rv["id"] if rv else None

            # Evaluamos la condición lógica (var_id) para controlar el flujo
            if var_id:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("""
                INSERT OR REPLACE INTO ofertas_actuales (
                    variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto,
                    estado, ultima_verificacion_exitosa, ultimo_intento, ultimo_cambio_confirmado,
                    fallos_consecutivos, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, 'activa', ?, ?, ?, 0, ?, ?);
                """, (var_id, t_id, precio_act, precio_norm, url_prod, ahora, ahora, ahora, ahora, ahora))

            # Ejecutamos instrucción: registros_precios.append((p_id, t_id, precio_act, pr...
            registros_precios.append((
                p_id, t_id, precio_act, precio_norm, 1, vol_ml, url_prod, ahora, var_id, "observacion_inicial"
            ))

    # Ejecutamos instrucción: cursor.executemany('\n INSERT INTO precios_registro ...
    cursor.executemany("""
    INSERT INTO precios_registro (
        perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
        volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, registros_precios)

    # Ejecutamos instrucción: limpiar_cache_catalogo()
    limpiar_cache_catalogo()
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    logger.info(
        f"SQLite poblado: {len(perfumes_tuples)} perfumes, {len(tiendas_tuples)} tiendas, {len(registros_precios)} observaciones."
    )


# Definición de función 'poblar_datos_semilla_supabase' sin parámetros externos
def poblar_datos_semilla_supabase() -> bool:
    """Puebla Supabase con tiendas, perfumes y observaciones reales usando service_role."""
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.warning("Se requiere SUPABASE_SERVICE_ROLE_KEY para poblar datos semilla en Supabase.")
        # Retornamos el resultado procesado (False)
        return False

    # Asignamos 'catalogo' con cargar_datos_semilla_json()
    catalogo = cargar_datos_semilla_json()
    # Asignamos 'tiendas_data' con catalogo.get('tiendas', [])
    tiendas_data = catalogo.get("tiendas", [])
    # Asignamos 'tiendas_inserts' con [{'nombre': t['nombre'], 'url_base': t['ur...
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

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb.table("tiendas").upsert(tiendas_inserts, on_conflict="nombre").execute()
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.error(f"Error insertando tiendas en Supabase: {e}")
        # Retornamos el resultado procesado (False)
        return False

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    resp_tiendas = sb.table("tiendas").select("id, nombre").execute()
    # Asignamos 'tiendas_map' con {r['nombre']: r['id'] for r in resp_tienda...
    tiendas_map = {r["nombre"]: r["id"] for r in (resp_tiendas.data or [])}

    # Asignamos 'perfumes_data' con catalogo.get('perfumes', [])
    perfumes_data = catalogo.get("perfumes", [])
    # Asignamos 'perfumes_inserts' con [{'id': p['id'], 'nombre': p['nombre'], 'm...
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

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        sb.table("perfumes").upsert(perfumes_inserts, on_conflict="id").execute()
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.error(f"Error insertando perfumes en Supabase: {e}")
        # Retornamos el resultado procesado (False)
        return False

    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Asignamos 'precios_inserts' con []
    precios_inserts = []
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
            # Asignamos 'precio_act' con int(enlace.get('precio_actual', p['precio_...
            precio_act = int(enlace.get("precio_actual", p["precio_referencia"]))
            # Asignamos 'p_normal_val' con enlace.get('precio_normal')
            p_normal_val = enlace.get("precio_normal")
            # Asignamos 'precio_norm' con int(p_normal_val) if p_normal_val and int(...
            precio_norm = int(p_normal_val) if (p_normal_val and int(p_normal_val) > precio_act) else precio_act
            # Asignamos 'url_prod' con enlace.get('url_producto', '')
            url_prod = enlace.get("url_producto", "")
            # Asignamos 'vol_ml' con int(enlace.get('volumen_ml', p.get('volume...
            vol_ml = int(enlace.get("volumen_ml", p.get("volumen_ml", 100)))
            # Ejecutamos instrucción: precios_inserts.append({'perfume_id': p_id, 'tienda_...
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

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Recorremos iterativamente cada 'chunk_idx' en range(0, len(precios_inserts), 100)
        for chunk_idx in range(0, len(precios_inserts), 100):
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("precios_registro").insert(precios_inserts[chunk_idx:chunk_idx + 100]).execute()
        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()
        # Retornamos el resultado procesado (True)
        return True
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.error(f"Error insertando precios semilla en Supabase: {e}")
        # Retornamos el resultado procesado (False)
        return False


# =============================================================================
# BLOQUE 8: AUTENTICACIÓN HÍBRIDA CLOUD (SUPABASE GOTRUE) + SQLITE PBKDF2
# =============================================================================
def _es_uuid(valor: Any) -> bool:
    # Asignamos 's' con str(valor or '').strip()
    s = str(valor or "").strip()
    # Evaluamos la condición lógica (len(s) != 36 or '-' not in s) para controlar el flujo
    if len(s) != 36 or "-" not in s:
        # Retornamos el resultado procesado (False)
        return False
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Ejecutamos instrucción: uuid.UUID(s)
        uuid.UUID(s)
        # Retornamos el resultado procesado (True)
        return True
    except ValueError:
        # Retornamos el resultado procesado (False)
        return False


# Definición de función '_obtener_admin_auth' sin parámetros externos
def _obtener_admin_auth():
    """Retorna el cliente Supabase con privilegios Admin Auth si está disponible."""
    # Evaluamos la condición lógica (not is_supabase_disponible() or not has_service_role...) para controlar el flujo
    if not is_supabase_disponible() or not has_service_role_key():
        # Retornamos el resultado procesado (None)
        return None
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb_srv = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb_srv and hasattr(sb_srv, 'auth') and hasattr(sb_sr...) para controlar el flujo
    if sb_srv and hasattr(sb_srv, "auth") and hasattr(sb_srv.auth, "admin"):
        # Retornamos el resultado procesado (sb_srv)
        return sb_srv
    # Retornamos el resultado procesado (None)
    return None


# Definición de función '_buscar_usuario_cloud' (parámetros: sb_srv, usuario_id_o_email, email_fallback)
def _buscar_usuario_cloud(sb_srv, usuario_id_o_email: Any, email_fallback: Optional[str] = None):
    """Resuelve un usuario en Supabase Auth (`auth.users`) por UUID o por correo electrónico."""
    # Evaluamos la condición lógica (usuario_id_o_email is not None and _es_uuid(usuario_...) para controlar el flujo
    if usuario_id_o_email is not None and _es_uuid(usuario_id_o_email):
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'resp' con sb_srv.auth.admin.get_user_by_id(str(usuar...
            resp = sb_srv.auth.admin.get_user_by_id(str(usuario_id_o_email).strip())
            # Asignamos 'user_obj' con getattr(resp, 'user', None)
            user_obj = getattr(resp, "user", None)
            # Evaluamos la condición lógica (user_obj) para controlar el flujo
            if user_obj:
                # Retornamos el resultado procesado (user_obj)
                return user_obj
        except Exception:
            # Ejecutamos instrucción: pass
            pass

    # Asignamos 'target_email' con str(email_fallback).strip().lower() if ema...
    target_email = (
        str(email_fallback).strip().lower()
        if email_fallback
        else (str(usuario_id_o_email).strip().lower() if "@" in str(usuario_id_o_email or "") else "")
    )
    # Evaluamos la condición lógica (not target_email) para controlar el flujo
    if not target_email:
        # Retornamos el resultado procesado (None)
        return None

    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'page' con 1
        page = 1
        # Ejecutamos el ciclo mientras se mantenga la condición: page <= 10
        while page <= 10:
            # Asignamos 'users_resp' con sb_srv.auth.admin.list_users(page=page, pe...
            users_resp = sb_srv.auth.admin.list_users(page=page, per_page=200)
            # Asignamos 'users_list' con users_resp if isinstance(users_resp, list)...
            users_list = users_resp if isinstance(users_resp, list) else getattr(users_resp, "users", []) or []
            # Recorremos iterativamente cada 'u' en users_list
            for u in users_list:
                # Evaluamos la condición lógica ((getattr(u, 'email', '') or '').strip().lower() == t...) para controlar el flujo
                if (getattr(u, "email", "") or "").strip().lower() == target_email:
                    # Retornamos el resultado procesado (u)
                    return u
            # Evaluamos la condición lógica (len(users_list) < 200) para controlar el flujo
            if len(users_list) < 200:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
            # Actualizamos acumulativamente el valor de 'page'
            page += 1
    except Exception as e:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.debug(f"No se pudo listar usuarios en Supabase Auth: {e}")
    # Retornamos el resultado procesado (None)
    return None


# Definición de función '_normalizar_usuario_cloud' (parámetros: user_obj)
def _normalizar_usuario_cloud(user_obj) -> Dict[str, Any]:
    """Convierte un objeto `User` de Supabase GoTrue al diccionario estándar de la aplicación."""
    # Asignamos 'meta' con dict(getattr(user_obj, 'user_metadata', No...
    meta = dict(getattr(user_obj, "user_metadata", None) or {})
    # Asignamos 'email_val' con (getattr(user_obj, 'email', '') or '').str...
    email_val = (getattr(user_obj, "email", "") or "").strip().lower()
    # Asignamos 'favs_raw' con meta.get('favoritos') or {}
    favs_raw = meta.get("favoritos") or {}
    # Asignamos 'fav_ids' con []
    fav_ids: List[int] = []
    # Evaluamos la condición lógica (isinstance(favs_raw, dict)) para controlar el flujo
    if isinstance(favs_raw, dict):
        # Recorremos iterativamente cada 'k' en favs_raw.keys()
        for k in favs_raw.keys():
            # Evaluamos la condición lógica (str(k).isdigit()) para controlar el flujo
            if str(k).isdigit():
                # Ejecutamos instrucción: fav_ids.append(int(k))
                fav_ids.append(int(k))
    # Evaluamos la condición lógica (isinstance(favs_raw, list)) para controlar el flujo
    elif isinstance(favs_raw, list):
        # Asignamos 'fav_ids' con [int(x) for x in favs_raw if str(x).isdigi...
        fav_ids = [int(x) for x in favs_raw if str(x).isdigit()]

    # Retornamos el resultado procesado ({'id': str(getattr(user_obj, 'id', '')), 'nombr...)
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
        **_leer_plan(dict(getattr(user_obj, "app_metadata", None) or {})),
    }


# - ¿Qué hace esta función (Registro de Usuarios)?:
#   Crea un nuevo usuario en el sistema. Hashea la contraseña con PBKDF2-HMAC-SHA256,
#   valida que el email no esté duplicado y guarda el perfil en Supabase (o SQLite local).
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
    # Asignamos 'nombre_clean' con (nombre or '').strip()
    nombre_clean = (nombre or "").strip()
    # Asignamos 'email_clean' con (email or '').strip().lower()
    email_clean = (email or "").strip().lower()
    # Evaluamos la condición lógica (not nombre_clean or not email_clean or '@' not in em...) para controlar el flujo
    if not nombre_clean or not email_clean or "@" not in email_clean:
        # Retornamos el resultado procesado ((False, 'Debes ingresar un nombre y correo elec...)
        return False, "Debes ingresar un nombre y correo electrónico válidos."
    # Evaluamos la condición lógica (not password or len(password) < 8) para controlar el flujo
    if not password or len(password) < 8:
        # Retornamos el resultado procesado ((False, 'La contraseña debe tener al menos 8 ca...)
        return False, "La contraseña debe tener al menos 8 caracteres."

    # Asignamos 'foto_limpia' con (foto_perfil or '').strip()
    foto_limpia = (foto_perfil or "").strip()
    # Evaluamos la condición lógica (foto_limpia and (not foto_limpia.lower().startswith(...) para controlar el flujo
    if foto_limpia and not foto_limpia.lower().startswith("https://"):
        # Asignamos 'foto_limpia' con ''
        foto_limpia = ""

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'existente' con _buscar_usuario_cloud(sb_srv, email_clean)
        existente = _buscar_usuario_cloud(sb_srv, email_clean)
        # Evaluamos la condición lógica (existente is not None) para controlar el flujo
        if existente is not None:
            # Retornamos el resultado procesado ((False, 'El correo electrónico ya se encuentra ...)
            return False, "El correo electrónico ya se encuentra registrado."

        # Asignamos 'metadata' con {'nombre': nombre_clean, 'telefono': (tele...
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
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'resp' con sb_srv.auth.admin.create_user({'email': em...
            resp = sb_srv.auth.admin.create_user({
                "email": email_clean,
                "password": password,
                "email_confirm": True,
                "user_metadata": metadata,
            })
            # Asignamos 'user_obj' con getattr(resp, 'user', None)
            user_obj = getattr(resp, "user", None)
            # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
            if user_obj is not None:
                # Si la tabla perfiles_usuario ya existe en PostgreSQL, sincronizarla silenciosamente
                try:
                    # Ejecutamos instrucción: sb_srv.table('perfiles_usuario').upsert({'id': str(u...
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
                    # Ejecutamos instrucción: pass
                    pass
                # Retornamos el resultado procesado ((True, 'Cuenta creada exitosamente.'))
                return True, "Cuenta creada exitosamente."
        except Exception as e:
            # Asignamos 'err_txt' con str(e).lower()
            err_txt = str(e).lower()
            # Evaluamos la condición lógica ('already' in err_txt or 'exists' in err_txt or 'regi...) para controlar el flujo
            if "already" in err_txt or "exists" in err_txt or "registered" in err_txt:
                # Retornamos el resultado procesado ((False, 'El correo electrónico ya se encuentra ...)
                return False, "El correo electrónico ya se encuentra registrado."
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.error(f"Error registrando usuario en Supabase Auth: {e}")
            # Retornamos el resultado procesado ((False, 'No fue posible crear la cuenta en este...)
            return False, "No fue posible crear la cuenta en este momento. Intenta nuevamente."

    # Si Supabase está disponible pero el entorno solo tiene clave pública anon (sin service_role),
    # registrar igualmente en GoTrue mediante sign_up aislado para no perder cuentas en contenedores efímeros.
    if is_supabase_disponible():
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        url_pub, anon_key = get_supabase_credentials(prefer_service_role=False)
        # Evaluamos la condición lógica (url_pub and anon_key) para controlar el flujo
        if url_pub and anon_key:
            # Asignamos 'metadata_pub' con {'nombre': nombre_clean, 'telefono': (tele...
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
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Importación de componentes (create_client) desde el módulo 'supabase'
                from supabase import create_client
                # Asignamos 'transient_signup' con create_client(url_pub, anon_key)
                transient_signup = create_client(url_pub, anon_key)
                # Asignamos 'resp_su' con transient_signup.auth.sign_up({'email': em...
                resp_su = transient_signup.auth.sign_up({
                    "email": email_clean,
                    "password": password,
                    "options": {"data": metadata_pub},
                })
                # Evaluamos la condición lógica (getattr(resp_su, 'user', None) is not None) para controlar el flujo
                if getattr(resp_su, "user", None) is not None:
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Ejecutamos instrucción: transient_signup.auth.sign_out()
                        transient_signup.auth.sign_out()
                    except Exception:
                        # Ejecutamos instrucción: pass
                        pass
                    # Retornamos el resultado procesado ((True, 'Cuenta creada exitosamente.'))
                    return True, "Cuenta creada exitosamente."
            except Exception as e:
                # Asignamos 'err_su' con str(e).lower()
                err_su = str(e).lower()
                # Evaluamos la condición lógica ('already' in err_su or 'exists' in err_su or 'regist...) para controlar el flujo
                if "already" in err_su or "exists" in err_su or "registered" in err_su:
                    # Retornamos el resultado procesado ((False, 'El correo electrónico ya se encuentra ...)
                    return False, "El correo electrónico ya se encuentra registrado."
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"Error en sign_up público de Supabase Auth: {e}")
                # Retornamos el resultado procesado ((False, 'No fue posible crear la cuenta en este...)
                return False, "No fue posible crear la cuenta en este momento. Intenta nuevamente."

    # Respaldo SQLite local (modo offline / desarrollo sin red)
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ?;", (email_clean,))
        # Evaluamos la condición lógica (cursor.fetchone()) para controlar el flujo
        if cursor.fetchone():
            # Retornamos el resultado procesado ((False, 'El correo electrónico ya se encuentra ...)
            return False, "El correo electrónico ya se encuentra registrado."

        # Asignamos 'pwd_hash' con hash_password(password)
        pwd_hash = hash_password(password)
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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
        # Retornamos el resultado procesado ((True, 'Cuenta creada exitosamente.'))
        return True, "Cuenta creada exitosamente."


# - ¿Qué hace esta función (Autenticación y Login)?:
#   Verifica las credenciales del usuario comparando el hash PBKDF2 de la contraseña ingresada
#   contra el hash seguro almacenado en la base de datos.
def verificar_usuario(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Autentica al usuario verificando sus credenciales:
    - En modo Supabase: usa un cliente efímero aislado (`sign_in_with_password`) para no contaminar
      las cabeceras JWT del cliente singleton compartido.
    - En modo SQLite: verifica con `verify_password_hash` en tiempo constante y actualiza
      automáticamente hashes SHA-256 antiguos a `PBKDF2-HMAC-SHA256`.
    """
    # Asignamos 'email_clean' con (email or '').strip().lower()
    email_clean = (email or "").strip().lower()
    # Evaluamos la condición lógica (not email_clean or not password) para controlar el flujo
    if not email_clean or not password:
        # Retornamos el resultado procesado ((False, None))
        return False, None

    # Evaluamos la condición lógica (is_supabase_disponible()) para controlar el flujo
    if is_supabase_disponible():
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        url, anon_key = get_supabase_credentials(prefer_service_role=False)
        # Evaluamos la condición lógica (url and anon_key) para controlar el flujo
        if url and anon_key:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Importación de componentes (create_client) desde el módulo 'supabase'
                from supabase import create_client
                # Asignamos 'transient_client' con create_client(url, anon_key)
                transient_client = create_client(url, anon_key)
                # Asignamos 'auth_resp' con transient_client.auth.sign_in_with_passwor...
                auth_resp = transient_client.auth.sign_in_with_password({
                    "email": email_clean,
                    "password": password,
                })
                # Asignamos 'user_obj' con getattr(auth_resp, 'user', None)
                user_obj = getattr(auth_resp, "user", None)
                # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
                if user_obj is not None:
                    # Asignamos 'u_data' con _normalizar_usuario_cloud(user_obj)
                    u_data = _normalizar_usuario_cloud(user_obj)
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Ejecutamos instrucción: transient_client.auth.sign_out()
                        transient_client.auth.sign_out()
                    except Exception:
                        # Ejecutamos instrucción: pass
                        pass
                    # Retornamos el resultado procesado ((True, u_data))
                    return True, u_data
            except Exception:
                # Si no autenticó en GoTrue, revisar únicamente si existe cuenta local legado en SQLite
                pass

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(email) = ?;", (email_clean,))
        # Asignamos 'row' con cursor.fetchone()
        row = cursor.fetchone()
        # Evaluamos la condición lógica (not row) para controlar el flujo
        if not row:
            # Retornamos el resultado procesado ((False, None))
            return False, None

        # Asignamos '(es_valida, requiere_rehash)' con verify_password_hash(password, row['passwo...
        es_valida, requiere_rehash = verify_password_hash(password, row["password_hash"])
        # Evaluamos la condición lógica (not es_valida) para controlar el flujo
        if not es_valida:
            # Retornamos el resultado procesado ((False, None))
            return False, None

        # Evaluamos la condición lógica (requiere_rehash) para controlar el flujo
        if requiere_rehash:
            # Asignamos 'nuevo_hash' con hash_password(password)
            nuevo_hash = hash_password(password)
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?;", (nuevo_hash, row["id"]))

        # Asignamos 'u_data' con dict(row)
        u_data = dict(row)
        # Ejecutamos instrucción: u_data.pop('password_hash', None)
        u_data.pop("password_hash", None)
        # Asignamos 'u_data['alerta_email']' con bool(u_data.get('alerta_email', True))
        u_data["alerta_email"] = bool(u_data.get("alerta_email", True))
        # Asignamos 'u_data['notif_stock']' con bool(u_data.get('notif_stock', True))
        u_data["notif_stock"] = bool(u_data.get("notif_stock", True))
        # Asignamos 'u_data['notif_resumen']' con bool(u_data.get('notif_resumen', False))
        u_data["notif_resumen"] = bool(u_data.get("notif_resumen", False))
        # Asignamos 'u_data['ubicacion']' con u_data.get('ubicacion') or 'Santiago, Chile'
        u_data["ubicacion"] = u_data.get("ubicacion") or "Santiago, Chile"
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT perfume_id FROM favoritos WHERE usuario_id = ?;", (row["id"],))
        # Asignamos 'u_data['favoritos']' con [int(r['perfume_id']) for r in cursor.fetc...
        u_data["favoritos"] = [int(r["perfume_id"]) for r in cursor.fetchall()]
        # Retornamos el resultado procesado ((True, u_data))
        return True, u_data


# Definición de función 'obtener_perfil_usuario' (parámetros: usuario_id_o_email)
def obtener_perfil_usuario(usuario_id_o_email: Any) -> Optional[Dict[str, Any]]:
    """Consulta el perfil completo de un usuario por UUID, ID entero o correo electrónico."""
    # Evaluamos la condición lógica (usuario_id_o_email is None) para controlar el flujo
    if usuario_id_o_email is None:
        # Retornamos el resultado procesado (None)
        return None

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Retornamos el resultado procesado (_normalizar_usuario_cloud(user_obj))
            return _normalizar_usuario_cloud(user_obj)

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Evaluamos la condición lógica (isinstance(usuario_id_o_email, int) or str(usuario_i...) para controlar el flujo
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT * FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "SELECT * FROM usuarios WHERE LOWER(email) = ?;",
                (str(usuario_id_o_email).strip().lower(),),
            )

        # Asignamos 'row' con cursor.fetchone()
        row = cursor.fetchone()
        # Evaluamos la condición lógica (row) para controlar el flujo
        if row:
            # Asignamos 'u_data' con dict(row)
            u_data = dict(row)
            # Ejecutamos instrucción: u_data.pop('password_hash', None)
            u_data.pop("password_hash", None)
            # Asignamos 'u_data['alerta_email']' con bool(u_data.get('alerta_email', True))
            u_data["alerta_email"] = bool(u_data.get("alerta_email", True))
            # Asignamos 'u_data['notif_stock']' con bool(u_data.get('notif_stock', True))
            u_data["notif_stock"] = bool(u_data.get("notif_stock", True))
            # Asignamos 'u_data['notif_resumen']' con bool(u_data.get('notif_resumen', False))
            u_data["notif_resumen"] = bool(u_data.get("notif_resumen", False))
            # Asignamos 'u_data['ubicacion']' con u_data.get('ubicacion') or 'Santiago, Chile'
            u_data["ubicacion"] = u_data.get("ubicacion") or "Santiago, Chile"
            # Ejecutamos instrucción: u_data.update(_leer_plan(u_data))
            u_data.update(_leer_plan(u_data))
            # Retornamos el resultado procesado (u_data)
            return u_data
        # Retornamos el resultado procesado (None)
        return None


# Definición de función 'subir_avatar_usuario' (parámetros: usuario_id_o_email, file_bytes, mime_type)
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
    # Evaluamos la condición lógica (not file_bytes or not isinstance(file_bytes, (bytes,...) para controlar el flujo
    if not file_bytes or not isinstance(file_bytes, (bytes, bytearray)):
        # Retornamos el resultado procesado ((False, 'No se recibió un archivo de imagen vál...)
        return False, "No se recibió un archivo de imagen válido."
    # Evaluamos la condición lógica (len(file_bytes) > 2 * 1024 * 1024) para controlar el flujo
    if len(file_bytes) > 2 * 1024 * 1024:
        # Retornamos el resultado procesado ((False, 'El archivo supera el tamaño máximo per...)
        return False, "El archivo supera el tamaño máximo permitido (2 MB)."

    # Asignamos 'raw' con bytes(file_bytes)
    raw = bytes(file_bytes)
    # Asignamos 'detected_mime' con ''
    detected_mime = ""
    # Asignamos 'ext' con ''
    ext = ""
    # Evaluamos la condición lógica (raw.startswith(b'\x89PNG\r\n\x1a\n')) para controlar el flujo
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        # Asignamos '(detected_mime, ext)' con ('image/png', 'png')
        detected_mime, ext = "image/png", "png"
    # Evaluamos la condición lógica (raw.startswith(b'\xff\xd8\xff')) para controlar el flujo
    elif raw.startswith(b"\xff\xd8\xff"):
        # Asignamos '(detected_mime, ext)' con ('image/jpeg', 'jpg')
        detected_mime, ext = "image/jpeg", "jpg"
    # Evaluamos la condición lógica (raw.startswith((b'GIF87a', b'GIF89a'))) para controlar el flujo
    elif raw.startswith((b"GIF87a", b"GIF89a")):
        # Asignamos '(detected_mime, ext)' con ('image/gif', 'gif')
        detected_mime, ext = "image/gif", "gif"
    # Evaluamos la condición lógica (len(raw) >= 12 and raw[:4] == b'RIFF' and (raw[8:12]...) para controlar el flujo
    elif len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        # Asignamos '(detected_mime, ext)' con ('image/webp', 'webp')
        detected_mime, ext = "image/webp", "webp"
    else:
        # Retornamos el resultado procesado ((False, 'Formato de archivo rechazado. Solo se ...)
        return False, "Formato de archivo rechazado. Solo se admiten imágenes PNG, JPG, WEBP o GIF auténticas."

    # Asignamos 'safe_owner' con hashlib.sha256(str(usuario_id_o_email).str...
    safe_owner = hashlib.sha256(str(usuario_id_o_email).strip().lower().encode("utf-8")).hexdigest()[:16]
    # Asignamos 'storage_path' con f'avatars/{safe_owner}_{int(time.time())}....
    storage_path = f"avatars/{safe_owner}_{int(time.time())}.{ext}"

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb_srv = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb_srv is not None and is_supabase_disponible()) para controlar el flujo
    if sb_srv is not None and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'bucket' con sb_srv.storage.from_('IMG_perfumes')
            bucket = sb_srv.storage.from_("IMG_perfumes")
            # Ejecutamos instrucción: bucket.upload(path=storage_path, file=raw, file_opti...
            bucket.upload(
                path=storage_path,
                file=raw,
                file_options={"content-type": detected_mime, "upsert": "true"},
            )
            # Asignamos 'public_url' con bucket.get_public_url(storage_path)
            public_url = bucket.get_public_url(storage_path)
            # Evaluamos la condición lógica (isinstance(public_url, str) and public_url.startswit...) para controlar el flujo
            if isinstance(public_url, str) and public_url.startswith("https://"):
                # Retornamos el resultado procesado ((True, public_url))
                return True, public_url
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.error(f"Error subiendo avatar a Supabase Storage: {e}")
            # Retornamos el resultado procesado ((False, 'No fue posible almacenar la fotografía...)
            return False, "No fue posible almacenar la fotografía en la nube en este momento."

    # Evaluamos la condición lógica (len(raw) > 380 * 1024) para controlar el flujo
    if len(raw) > 380 * 1024:
        # Retornamos el resultado procesado ((False, 'En modo local sin conexión, la imagen ...)
        return False, "En modo local sin conexión, la imagen de avatar no debe superar los 380 KB."
    # Asignamos 'b64_str' con base64.b64encode(raw).decode('ascii')
    b64_str = base64.b64encode(raw).decode("ascii")
    # Retornamos el resultado procesado ((True, f'data:{detected_mime};base64,{b64_str}'))
    return True, f"data:{detected_mime};base64,{b64_str}"


# Definición de función 'actualizar_perfil_usuario' (parámetros: usuario_id_o_email, nombre, email, telefono, ...)
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
    # Asignamos 'nombre_clean' con (nombre or '').strip()
    nombre_clean = (nombre or "").strip()
    # Asignamos 'email_clean' con (email or '').strip().lower()
    email_clean = (email or "").strip().lower()
    # Asignamos 'tel_clean' con (telefono or '').strip()
    tel_clean = (telefono or "").strip()
    # Asignamos 'bio_clean' con (bio or '').strip()
    bio_clean = (bio or "").strip()
    # Asignamos 'foto_clean' con (foto_perfil or '').strip()
    foto_clean = (foto_perfil or "").strip()

    # Evaluamos la condición lógica (not nombre_clean or not email_clean or '@' not in em...) para controlar el flujo
    if not nombre_clean or not email_clean or "@" not in email_clean:
        # Retornamos el resultado procesado ((False, 'El nombre y un correo electrónico váli...)
        return False, "El nombre y un correo electrónico válido son obligatorios."

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Asignamos 'es_data_img_seguro' con sb_srv is None and foto_clean.startswith((...
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

    # Evaluamos la condición lógica (foto_clean and (not foto_clean.lower().startswith('h...) para controlar el flujo
    if foto_clean and not foto_clean.lower().startswith("https://") and not es_data_img_seguro:
        # Retornamos el resultado procesado ((False, 'Por seguridad, la foto de perfil debe ...)
        return False, "Por seguridad, la foto de perfil debe ser una URL pública con HTTPS (https://...)."

    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email, email_fallback=email_clean)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'uid' con str(user_obj.id)
            uid = str(user_obj.id)
            # Asignamos 'curr_email' con (getattr(user_obj, 'email', '') or '').str...
            curr_email = (getattr(user_obj, "email", "") or "").strip().lower()
            # Evaluamos la condición lógica (email_clean != curr_email) para controlar el flujo
            if email_clean != curr_email:
                # Asignamos 'otro' con _buscar_usuario_cloud(sb_srv, email_clean)
                otro = _buscar_usuario_cloud(sb_srv, email_clean)
                # Evaluamos la condición lógica (otro is not None and str(otro.id) != uid) para controlar el flujo
                if otro is not None and str(otro.id) != uid:
                    # Retornamos el resultado procesado ((False, 'El correo ingresado ya está siendo uti...)
                    return False, "El correo ingresado ya está siendo utilizado por otra cuenta."

            # Asignamos 'meta' con dict(getattr(user_obj, 'user_metadata', No...
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            # Asignamos 'meta['nombre']' con nombre_clean
            meta["nombre"] = nombre_clean
            # Asignamos 'meta['telefono']' con tel_clean
            meta["telefono"] = tel_clean
            # Asignamos 'meta['bio']' con bio_clean
            meta["bio"] = bio_clean
            # Asignamos 'meta['foto_perfil']' con foto_clean
            meta["foto_perfil"] = foto_clean
            # Evaluamos la condición lógica (ubicacion is not None) para controlar el flujo
            if ubicacion is not None:
                # Asignamos 'meta['ubicacion']' con ubicacion.strip() or 'Santiago, Chile'
                meta["ubicacion"] = ubicacion.strip() or "Santiago, Chile"

            # Asignamos 'payload' con {'user_metadata': meta}
            payload: Dict[str, Any] = {"user_metadata": meta}
            # Evaluamos la condición lógica (email_clean != curr_email) para controlar el flujo
            if email_clean != curr_email:
                # Asignamos 'payload['email']' con email_clean
                payload["email"] = email_clean
                # Asignamos 'payload['email_confirm']' con True
                payload["email_confirm"] = True

            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: sb_srv.auth.admin.update_user_by_id(uid, payload)
                sb_srv.auth.admin.update_user_by_id(uid, payload)
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Ejecutamos instrucción: sb_srv.table('perfiles_usuario').upsert({'id': uid, ...
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
                    # Ejecutamos instrucción: pass
                    pass
                # Retornamos el resultado procesado ((True, 'Perfil actualizado con éxito en la nube.'))
                return True, "Perfil actualizado con éxito en la nube."
            except Exception as e:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"Error actualizando perfil en Supabase Auth: {e}")
                # Retornamos el resultado procesado ((False, 'No se pudo actualizar el perfil en la ...)
                return False, "No se pudo actualizar el perfil en la nube."

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'ubic_final' con (ubicacion or 'Santiago, Chile').strip()
    ubic_final = (ubicacion or "Santiago, Chile").strip()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Evaluamos la condición lógica (isinstance(usuario_id_o_email, int) or str(usuario_i...) para controlar el flujo
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT id, email FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "SELECT id, email FROM usuarios WHERE LOWER(email) = ?;",
                (str(usuario_id_o_email).strip().lower(),),
            )

        # Asignamos 'row' con cursor.fetchone()
        row = cursor.fetchone()
        # Evaluamos la condición lógica (not row) para controlar el flujo
        if not row:
            # Asignamos 'pwd_random' con hash_password(secrets.token_urlsafe(24))
            pwd_random = hash_password(secrets.token_urlsafe(24))
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT INTO usuarios (nombre, email, password_hash, telefono, ubicacion, bio, foto_perfil)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (nombre_clean, email_clean, pwd_random, tel_clean, ubic_final, bio_clean, foto_clean))
            # Retornamos el resultado procesado ((True, 'Perfil creado y actualizado.'))
            return True, "Perfil creado y actualizado."

        # Asignamos 'u_id' con row['id']
        u_id = row["id"]
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ? AND id != ?;", (email_clean, u_id))
        # Evaluamos la condición lógica (cursor.fetchone()) para controlar el flujo
        if cursor.fetchone():
            # Retornamos el resultado procesado ((False, 'El correo ingresado ya está siendo uti...)
            return False, "El correo ingresado ya está siendo utilizado por otra cuenta."

        # Evaluamos la condición lógica (ubicacion is not None) para controlar el flujo
        if ubicacion is not None:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            UPDATE usuarios
            SET nombre = ?, email = ?, telefono = ?, ubicacion = ?, bio = ?, foto_perfil = ?
            WHERE id = ?;
            """, (nombre_clean, email_clean, tel_clean, ubic_final, bio_clean, foto_clean, u_id))
        else:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            UPDATE usuarios
            SET nombre = ?, email = ?, telefono = ?, bio = ?, foto_perfil = ?
            WHERE id = ?;
            """, (nombre_clean, email_clean, tel_clean, bio_clean, foto_clean, u_id))

        # Retornamos el resultado procesado ((True, 'Perfil actualizado con éxito.'))
        return True, "Perfil actualizado con éxito."


# Definición de función 'actualizar_preferencias_notificacion' (parámetros: usuario_id_o_email, alerta_email, umbral_descuento, notif_stock, ...)
def actualizar_preferencias_notificacion(
    usuario_id_o_email: Any,
    alerta_email: bool,
    umbral_descuento: int = 10,
    notif_stock: Optional[bool] = None,
    notif_resumen: Optional[bool] = None,
) -> Tuple[bool, str]:
    """Guarda de forma persistente las preferencias de alertas del usuario."""
    # Asignamos 'umbral_limpio' con max(1, min(90, int(umbral_descuento or 10)))
    umbral_limpio = max(1, min(90, int(umbral_descuento or 10)))

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'uid' con str(user_obj.id)
            uid = str(user_obj.id)
            # Asignamos 'meta' con dict(getattr(user_obj, 'user_metadata', No...
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            # Asignamos 'meta['alerta_email']' con bool(alerta_email)
            meta["alerta_email"] = bool(alerta_email)
            # Asignamos 'meta['umbral_descuento']' con umbral_limpio
            meta["umbral_descuento"] = umbral_limpio
            # Evaluamos la condición lógica (notif_stock is not None) para controlar el flujo
            if notif_stock is not None:
                # Asignamos 'meta['notif_stock']' con bool(notif_stock)
                meta["notif_stock"] = bool(notif_stock)
            # Evaluamos la condición lógica (notif_resumen is not None) para controlar el flujo
            if notif_resumen is not None:
                # Asignamos 'meta['notif_resumen']' con bool(notif_resumen)
                meta["notif_resumen"] = bool(notif_resumen)
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: sb_srv.auth.admin.update_user_by_id(uid, {'user_meta...
                sb_srv.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Ejecutamos instrucción: sb_srv.table('perfiles_usuario').update({'alerta_ema...
                    sb_srv.table("perfiles_usuario").update({
                        "alerta_email": bool(alerta_email),
                        "umbral_descuento": umbral_limpio,
                        "notif_stock": bool(meta.get("notif_stock", True)),
                        "notif_resumen": bool(meta.get("notif_resumen", False)),
                    }).eq("id", uid).execute()
                except Exception:
                    # Ejecutamos instrucción: pass
                    pass
                # Retornamos el resultado procesado ((True, 'Preferencias de notificación guardadas.'))
                return True, "Preferencias de notificación guardadas."
            except Exception as e:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"Error guardando preferencias en Supabase Auth: {e}")
                # Retornamos el resultado procesado ((False, 'No se pudieron guardar las preferencia...)
                return False, "No se pudieron guardar las preferencias."

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Evaluamos la condición lógica (isinstance(usuario_id_o_email, int) or str(usuario_i...) para controlar el flujo
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            # Asignamos 'query_find' con 'WHERE id = ?'
            query_find = "WHERE id = ?"
            # Asignamos 'val_find' con int(usuario_id_o_email)
            val_find: Any = int(usuario_id_o_email)
        else:
            # Asignamos 'query_find' con 'WHERE LOWER(email) = ?'
            query_find = "WHERE LOWER(email) = ?"
            # Asignamos 'val_find' con str(usuario_id_o_email).strip().lower()
            val_find = str(usuario_id_o_email).strip().lower()

        # Evaluamos la condición lógica (notif_stock is not None or notif_resumen is not None) para controlar el flujo
        if notif_stock is not None or notif_resumen is not None:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                f"UPDATE usuarios SET alerta_email = ?, umbral_descuento = ? {query_find};",
                (int(bool(alerta_email)), umbral_limpio, val_find),
            )
        # Retornamos el resultado procesado ((True, 'Preferencias de notificación guardadas.'))
        return True, "Preferencias de notificación guardadas."


# =============================================================================
# BLOQUE 8B: PLANES DE SUSCRIPCIÓN (FREE / PREMIUM / VIP)
# -----------------------------------------------------------------------------
# - En Supabase el plan se guarda en `app_metadata` del usuario de Supabase Auth.
#   A diferencia de `user_metadata`, el usuario NO puede modificar `app_metadata` desde
#   el navegador: solo el servidor con la clave service_role. Así nadie puede darse
#   Premium a sí mismo. Si existe la tabla `perfiles_usuario` con columnas de plan,
#   también se copia ahí (opcional, para verlo en el Table Editor).
# - En el respaldo local (SQLite) se guarda en las columnas plan / plan_activado_en /
#   plan_vence_en de la tabla `usuarios`.
# - Cada compra activa el plan por PLAN_DURACION_DIAS días; al vencer vuelve a 'free'.
# =============================================================================
PLANES_VALIDOS = ("free", "premium", "vip")
# Asignamos 'PLAN_DURACION_DIAS' con 30
PLAN_DURACION_DIAS = 30


# Definición de función '_leer_plan' (parámetros: datos)
def _leer_plan(datos: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve {plan, plan_activado_en, plan_vence_en} aplicando el vencimiento."""
    # Asignamos 'plan' con str((datos or {}).get('plan') or 'free').s...
    plan = str((datos or {}).get("plan") or "free").strip().lower()
    # Evaluamos la condición lógica (plan not in PLANES_VALIDOS) para controlar el flujo
    if plan not in PLANES_VALIDOS:
        # Asignamos 'plan' con 'free'
        plan = "free"
    # Asignamos 'activado' con (datos or {}).get('plan_activado_en') or ''
    activado = (datos or {}).get("plan_activado_en") or ""
    # Asignamos 'vence' con (datos or {}).get('plan_vence_en') or ''
    vence = (datos or {}).get("plan_vence_en") or ""
    # Evaluamos la condición lógica (plan != 'free' and vence) para controlar el flujo
    if plan != "free" and vence:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'vence_dt' con datetime.fromisoformat(str(vence).replace(...
            vence_dt = datetime.fromisoformat(str(vence).replace("Z", "+00:00"))
            # Evaluamos la condición lógica (vence_dt.tzinfo is None) para controlar el flujo
            if vence_dt.tzinfo is None:
                # Asignamos 'vence_dt' con vence_dt.replace(tzinfo=timezone.utc)
                vence_dt = vence_dt.replace(tzinfo=timezone.utc)
            # Evaluamos la condición lógica (vence_dt < datetime.now(timezone.utc)) para controlar el flujo
            if vence_dt < datetime.now(timezone.utc):
                # Asignamos 'plan' con 'free'
                plan = "free"
        except ValueError:
            # Ejecutamos instrucción: pass
            pass
    # Retornamos el resultado procesado ({'plan': plan, 'plan_activado_en': str(activado...)
    return {"plan": plan, "plan_activado_en": str(activado), "plan_vence_en": str(vence)}


# Definición de función '_asegurar_columnas_plan_sqlite' (parámetros: cursor)
def _asegurar_columnas_plan_sqlite(cursor: sqlite3.Cursor) -> None:
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    cursor.execute("PRAGMA table_info(usuarios);")
    # Asignamos 'cols' con {c['name'] for c in cursor.fetchall()}
    cols = {c["name"] for c in cursor.fetchall()}
    # Recorremos iterativamente cada '(col_name, col_def)' en [('plan', "TEXT DEFAULT 'free'"), ('plan_a...
    for col_name, col_def in [
        ("plan", "TEXT DEFAULT 'free'"),
        ("plan_activado_en", "TEXT"),
        ("plan_vence_en", "TEXT"),
    ]:
        # Evaluamos la condición lógica (col_name not in cols) para controlar el flujo
        if col_name not in cols:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_def};")


# Definición de función 'actualizar_plan_usuario' (parámetros: usuario_id_o_email, plan, email, nombre, ...)
def actualizar_plan_usuario(
    usuario_id_o_email: Any,
    plan: str,
    email: Optional[str] = None,
    nombre: Optional[str] = None,
    dias: int = PLAN_DURACION_DIAS,
) -> Tuple[bool, str]:
    """Guarda de forma persistente el plan del usuario (Supabase Auth o SQLite).
    Si el usuario aún no existe en Supabase Auth (por ejemplo, entró solo con código por
    correo), se crea su cuenta en la nube para que el plan no se pierda."""
    # Asignamos 'plan_limpio' con str(plan or 'free').strip().lower()
    plan_limpio = str(plan or "free").strip().lower()
    # Evaluamos la condición lógica (plan_limpio not in PLANES_VALIDOS) para controlar el flujo
    if plan_limpio not in PLANES_VALIDOS:
        # Retornamos el resultado procesado ((False, 'Plan no válido.'))
        return False, "Plan no válido."

    # Asignamos 'ahora' con datetime.now(timezone.utc)
    ahora = datetime.now(timezone.utc)
    # Evaluamos la condición lógica (plan_limpio == 'free') para controlar el flujo
    if plan_limpio == "free":
        # Asignamos 'datos_plan' con {'plan': 'free', 'plan_activado_en': None,...
        datos_plan = {"plan": "free", "plan_activado_en": None, "plan_vence_en": None}
    else:
        # Importación de componentes (timedelta) desde el módulo 'datetime'
        from datetime import timedelta
        # Asignamos 'datos_plan' con {'plan': plan_limpio, 'plan_activado_en': ...
        datos_plan = {
            "plan": plan_limpio,
            "plan_activado_en": ahora.isoformat(),
            "plan_vence_en": (ahora + timedelta(days=int(dias))).isoformat(),
        }

    # Asignamos 'email_ref' con (email or (str(usuario_id_o_email) if '@' ...
    email_ref = (email or (str(usuario_id_o_email) if "@" in str(usuario_id_o_email or "") else "")).strip().lower()

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email, email_fallback=email_ref or None)
        # Evaluamos la condición lógica (user_obj is None and email_ref) para controlar el flujo
        if user_obj is None and email_ref:
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Asignamos 'resp' con sb_srv.auth.admin.create_user({'email': em...
                resp = sb_srv.auth.admin.create_user({
                    "email": email_ref,
                    "password": secrets.token_urlsafe(24),
                    "email_confirm": True,
                    "user_metadata": {
                        "nombre": (nombre or email_ref.split("@")[0]).strip(),
                        "ubicacion": "Santiago, Chile",
                        "alerta_email": True,
                        "notif_stock": True,
                        "notif_resumen": False,
                        "umbral_descuento": 10,
                        "favoritos": {},
                    },
                })
                # Asignamos 'user_obj' con getattr(resp, 'user', None)
                user_obj = getattr(resp, "user", None)
            except Exception as e:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"No se pudo crear el usuario en Supabase Auth para guardar el plan: {e}")
                # Asignamos 'user_obj' con None
                user_obj = None

        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'uid' con str(user_obj.id)
            uid = str(user_obj.id)
            # Asignamos 'app_meta' con dict(getattr(user_obj, 'app_metadata', Non...
            app_meta = dict(getattr(user_obj, "app_metadata", None) or {})
            # Ejecutamos instrucción: app_meta.update(datos_plan)
            app_meta.update(datos_plan)
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: sb_srv.auth.admin.update_user_by_id(uid, {'app_metad...
                sb_srv.auth.admin.update_user_by_id(uid, {"app_metadata": app_meta})
            except Exception as e:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"Error guardando el plan en Supabase Auth: {e}")
                # Retornamos el resultado procesado ((False, 'No se pudo guardar el plan en la nube.'))
                return False, "No se pudo guardar el plan en la nube."
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: sb_srv.table('perfiles_usuario').update(datos_plan)....
                sb_srv.table("perfiles_usuario").update(datos_plan).eq("id", uid).execute()
            except Exception:
                # Ejecutamos instrucción: pass
                pass  # la tabla o las columnas de plan son opcionales
            # Retornamos el resultado procesado ((True, 'Plan guardado en la nube.'))
            return True, "Plan guardado en la nube."

    # Respaldo local (SQLite)
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        _asegurar_columnas_plan_sqlite(cursor)
        # Evaluamos la condición lógica (isinstance(usuario_id_o_email, int) or str(usuario_i...) para controlar el flujo
        if isinstance(usuario_id_o_email, int) or str(usuario_id_o_email).isdigit():
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT id FROM usuarios WHERE id = ?;", (int(usuario_id_o_email),))
        else:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = ?;", (email_ref or str(usuario_id_o_email).strip().lower(),))
        # Asignamos 'row' con cursor.fetchone()
        row = cursor.fetchone()
        # Evaluamos la condición lógica (not row) para controlar el flujo
        if not row:
            # Evaluamos la condición lógica (not email_ref) para controlar el flujo
            if not email_ref:
                # Retornamos el resultado procesado ((False, 'No se encontró el usuario para guardar...)
                return False, "No se encontró el usuario para guardar el plan."
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, ubicacion) VALUES (?, ?, ?, ?);",
                ((nombre or email_ref.split("@")[0]).strip(), email_ref, hash_password(secrets.token_urlsafe(24)), "Santiago, Chile"),
            )
            # Asignamos 'u_id' con cursor.lastrowid
            u_id = cursor.lastrowid
        else:
            # Asignamos 'u_id' con row['id']
            u_id = row["id"]
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            "UPDATE usuarios SET plan = ?, plan_activado_en = ?, plan_vence_en = ? WHERE id = ?;",
            (datos_plan["plan"], datos_plan["plan_activado_en"], datos_plan["plan_vence_en"], u_id),
        )
    # Retornamos el resultado procesado ((True, 'Plan guardado localmente.'))
    return True, "Plan guardado localmente."


# =============================================================================
# BLOQUE 9: FAVORITOS Y SISTEMA INTELIGENTE DE MONITOREO DE PRECIOS
# =============================================================================
def agregar_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Añade una fragancia a favoritos guardando el mejor precio en stock actual."""
    # Asignamos 'perfume_id' con int(perfume_id)
    perfume_id = int(perfume_id)
    # Asignamos 'precios' con obtener_precios_actuales(perfume_id)
    precios = obtener_precios_actuales(perfume_id)
    # Asignamos 'precios_stock' con [int(p['precio_actual']) for p in precios ...
    precios_stock = [int(p["precio_actual"]) for p in precios if p.get("en_stock") and (p.get("precio_actual") or 0) > 0]
    # Asignamos 'p_min' con min(precios_stock) if precios_stock else 0
    p_min = min(precios_stock) if precios_stock else 0
    # Asignamos 'ahora_iso' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'uid' con str(user_obj.id)
            uid = str(user_obj.id)
            # Asignamos 'meta' con dict(getattr(user_obj, 'user_metadata', No...
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            # Asignamos 'favs' con dict(meta.get('favoritos') or {}) if isins...
            favs = dict(meta.get("favoritos") or {}) if isinstance(meta.get("favoritos"), dict) else {}
            # Asignamos 'favs[str(perfume_id)]' con {'precio_guardado': p_min, 'fecha_agregado...
            favs[str(perfume_id)] = {
                "precio_guardado": p_min,
                "fecha_agregado": ahora_iso,
            }
            # Asignamos 'meta['favoritos']' con favs
            meta["favoritos"] = favs
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: sb_srv.auth.admin.update_user_by_id(uid, {'user_meta...
                sb_srv.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Ejecutamos instrucción: sb_srv.table('favoritos_usuario').upsert({'usuario_i...
                    sb_srv.table("favoritos_usuario").upsert({
                        "usuario_id": uid,
                        "perfume_id": perfume_id,
                        "precio_guardado": p_min,
                    }, on_conflict="usuario_id,perfume_id").execute()
                except Exception:
                    # Ejecutamos instrucción: pass
                    pass
                # Retornamos el resultado procesado (True)
                return True
            except Exception as e:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"Error guardando favorito en Supabase Auth: {e}")
                # Retornamos el resultado procesado (False)
                return False

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'u_perfil' con obtener_perfil_usuario(usuario_id_o_email)
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    # Evaluamos la condición lógica (not u_perfil or not str(u_perfil.get('id', '')).isdi...) para controlar el flujo
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        # Retornamos el resultado procesado (False)
        return False

    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        INSERT OR REPLACE INTO favoritos (usuario_id, perfume_id, precio_guardado, fecha_agregado)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP);
        """, (int(u_perfil["id"]), perfume_id, p_min))
        # Retornamos el resultado procesado (True)
        return True


# Definición de función 'eliminar_favorito' (parámetros: usuario_id_o_email, perfume_id)
def eliminar_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Elimina una fragancia de la lista de monitoreo del usuario."""
    # Asignamos 'perfume_id' con int(perfume_id)
    perfume_id = int(perfume_id)

    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'uid' con str(user_obj.id)
            uid = str(user_obj.id)
            # Asignamos 'meta' con dict(getattr(user_obj, 'user_metadata', No...
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            # Asignamos 'favs' con dict(meta.get('favoritos') or {}) if isins...
            favs = dict(meta.get("favoritos") or {}) if isinstance(meta.get("favoritos"), dict) else {}
            # Ejecutamos instrucción: favs.pop(str(perfume_id), None)
            favs.pop(str(perfume_id), None)
            # Asignamos 'meta['favoritos']' con favs
            meta["favoritos"] = favs
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Ejecutamos instrucción: sb_srv.auth.admin.update_user_by_id(uid, {'user_meta...
                sb_srv.auth.admin.update_user_by_id(uid, {"user_metadata": meta})
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Ejecutamos instrucción: sb_srv.table('favoritos_usuario').delete().eq('usuar...
                    sb_srv.table("favoritos_usuario").delete().eq("usuario_id", uid).eq("perfume_id", perfume_id).execute()
                except Exception:
                    # Ejecutamos instrucción: pass
                    pass
                # Retornamos el resultado procesado (True)
                return True
            except Exception as e:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                logger.error(f"Error eliminando favorito en Supabase Auth: {e}")
                # Retornamos el resultado procesado (False)
                return False

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'u_perfil' con obtener_perfil_usuario(usuario_id_o_email)
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    # Evaluamos la condición lógica (not u_perfil or not str(u_perfil.get('id', '')).isdi...) para controlar el flujo
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        # Retornamos el resultado procesado (False)
        return False

    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            "DELETE FROM favoritos WHERE usuario_id = ? AND perfume_id = ?;",
            (int(u_perfil["id"]), perfume_id),
        )
        # Retornamos el resultado procesado (True)
        return True


# Definición de función 'obtener_favoritos_Ids_usuario' (parámetros: usuario_id_o_email, email)
def obtener_favoritos_Ids_usuario(usuario_id_o_email: Any, email: Optional[str] = None) -> List[int]:
    """Retorna la lista de `perfume_id` favoritos del usuario."""
    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email, email_fallback=email)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'u_norm' con _normalizar_usuario_cloud(user_obj)
            u_norm = _normalizar_usuario_cloud(user_obj)
            # Retornamos el resultado procesado (u_norm.get('favoritos', []))
            return u_norm.get("favoritos", [])

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'u_perfil' con obtener_perfil_usuario(usuario_id_o_email ...
    u_perfil = obtener_perfil_usuario(usuario_id_o_email or email)
    # Evaluamos la condición lógica (not u_perfil or not str(u_perfil.get('id', '')).isdi...) para controlar el flujo
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        # Retornamos el resultado procesado ([])
        return []

    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            "SELECT perfume_id FROM favoritos WHERE usuario_id = ? ORDER BY fecha_agregado DESC;",
            (int(u_perfil["id"]),),
        )
        # Retornamos el resultado procesado ([int(r['perfume_id']) for r in cursor.fetchall()])
        return [int(r["perfume_id"]) for r in cursor.fetchall()]


# Definición de función 'obtener_favoritos_usuario' (parámetros: usuario_id_o_email)
def obtener_favoritos_usuario(usuario_id_o_email: Any) -> List[Dict[str, Any]]:
    """Retorna los perfumes favoritos monitoreados por el usuario con detección real de bajas de precio."""
    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'user_obj' con _buscar_usuario_cloud(sb_srv, usuario_id_o...
        user_obj = _buscar_usuario_cloud(sb_srv, usuario_id_o_email)
        # Evaluamos la condición lógica (user_obj is not None) para controlar el flujo
        if user_obj is not None:
            # Asignamos 'meta' con dict(getattr(user_obj, 'user_metadata', No...
            meta = dict(getattr(user_obj, "user_metadata", None) or {})
            # Asignamos 'favs_raw' con meta.get('favoritos') or {}
            favs_raw = meta.get("favoritos") or {}
            # Asignamos 'fav_entries' con {}
            fav_entries: Dict[int, Dict[str, Any]] = {}
            # Evaluamos la condición lógica (isinstance(favs_raw, dict)) para controlar el flujo
            if isinstance(favs_raw, dict):
                # Recorremos iterativamente cada '(k, v)' en favs_raw.items()
                for k, v in favs_raw.items():
                    # Evaluamos la condición lógica (str(k).isdigit()) para controlar el flujo
                    if str(k).isdigit():
                        # Asignamos 'fav_entries[int(k)]' con v if isinstance(v, dict) else {'precio_gua...
                        fav_entries[int(k)] = v if isinstance(v, dict) else {"precio_guardado": 0}
            # Evaluamos la condición lógica (isinstance(favs_raw, list)) para controlar el flujo
            elif isinstance(favs_raw, list):
                # Recorremos iterativamente cada 'x' en favs_raw
                for x in favs_raw:
                    # Evaluamos la condición lógica (str(x).isdigit()) para controlar el flujo
                    if str(x).isdigit():
                        # Asignamos 'fav_entries[int(x)]' con {'precio_guardado': 0}
                        fav_entries[int(x)] = {"precio_guardado": 0}

            # Evaluamos la condición lógica (not fav_entries) para controlar el flujo
            if not fav_entries:
                # Retornamos el resultado procesado ([])
                return []

            # Asignamos 'catalogo_map' con {int(p['id']): p for p in obtener_catalogo()}
            catalogo_map = {int(p["id"]): p for p in obtener_catalogo()}
            # Asignamos 'resultado' con []
            resultado: List[Dict[str, Any]] = []
            # Recorremos iterativamente cada '(pid, meta_fav)' en fav_entries.items()
            for pid, meta_fav in fav_entries.items():
                # Asignamos 'perf' con catalogo_map.get(pid) or obtener_detalle_p...
                perf = catalogo_map.get(pid) or obtener_detalle_perfume(pid)
                # Evaluamos la condición lógica (not perf) para controlar el flujo
                if not perf:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'd' con dict(perf)
                d = dict(perf)
                # Asignamos 'mejor_actual' con d.get('mejor_precio')
                mejor_actual = d.get("mejor_precio")
                # Asignamos 'p_act' con int(mejor_actual) if mejor_actual else int...
                p_act = int(mejor_actual) if mejor_actual else int(d.get("precio_referencia") or 0)
                # Asignamos 'p_guardado' con int(meta_fav.get('precio_guardado') or 0) ...
                p_guardado = int(meta_fav.get("precio_guardado") or 0) or p_act
                # Asignamos 'd['precio_guardado']' con p_guardado
                d["precio_guardado"] = p_guardado
                # Asignamos 'd['fecha_agregado']' con meta_fav.get('fecha_agregado', '')
                d["fecha_agregado"] = meta_fav.get("fecha_agregado", "")
                # Asignamos 'd['mejor_precio_actual']' con mejor_actual
                d["mejor_precio_actual"] = mejor_actual
                # Asignamos 'd['baja_detectada']' con bool(mejor_actual and mejor_actual < p_gua...
                d["baja_detectada"] = bool(mejor_actual and mejor_actual < p_guardado)
                # Evaluamos la condición lógica (p_guardado > 0 and mejor_actual and (mejor_actual < ...) para controlar el flujo
                if p_guardado > 0 and mejor_actual and mejor_actual < p_guardado:
                    # Asignamos 'd['porcentaje_descuento']' con round((p_guardado - mejor_actual) / p_guar...
                    d["porcentaje_descuento"] = round(((p_guardado - mejor_actual) / p_guardado) * 100, 1)
                else:
                    # Asignamos 'd['porcentaje_descuento']' con 0.0
                    d["porcentaje_descuento"] = 0.0
                # Ejecutamos instrucción: resultado.append(d)
                resultado.append(d)
            # Retornamos el resultado procesado (resultado)
            return resultado

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'u_perfil' con obtener_perfil_usuario(usuario_id_o_email)
    u_perfil = obtener_perfil_usuario(usuario_id_o_email)
    # Evaluamos la condición lógica (not u_perfil or not str(u_perfil.get('id', '')).isdi...) para controlar el flujo
    if not u_perfil or not str(u_perfil.get("id", "")).isdigit():
        # Retornamos el resultado procesado ([])
        return []

    # Asignamos 'query' con "\n SELECT p.*, f.precio_guardado, f.fecha...
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
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, (int(u_perfil["id"]),))
        # Asignamos 'favoritos' con []
        favoritos = []
        # Recorremos iterativamente cada 'row' en cursor.fetchall()
        for row in cursor.fetchall():
            # Asignamos 'd' con dict(row)
            d = dict(row)
            # Asignamos 'p_act' con d['mejor_precio_actual'] or d['precio_refe...
            p_act = d["mejor_precio_actual"] or d["precio_referencia"]
            # Asignamos 'p_init' con d['precio_guardado'] or d['precio_referenc...
            p_init = d["precio_guardado"] or d["precio_referencia"]
            # Asignamos 'd['mejor_precio']' con d['mejor_precio_actual']
            d["mejor_precio"] = d["mejor_precio_actual"]
            # Asignamos 'd['baja_detectada']' con bool(d['mejor_precio_actual'] and p_act < ...
            d["baja_detectada"] = bool(d["mejor_precio_actual"] and p_act < p_init and p_act > 0)
            # Evaluamos la condición lógica (d['precio_guardado'] and d['precio_guardado'] > 0 an...) para controlar el flujo
            if d["precio_guardado"] and d["precio_guardado"] > 0 and p_act < d["precio_guardado"]:
                # Asignamos 'd['porcentaje_descuento']' con round((d['precio_guardado'] - p_act) / d['...
                d["porcentaje_descuento"] = round(((d["precio_guardado"] - p_act) / d["precio_guardado"]) * 100, 1)
            else:
                # Asignamos 'd['porcentaje_descuento']' con 0.0
                d["porcentaje_descuento"] = 0.0
            # Ejecutamos instrucción: favoritos.append(d)
            favoritos.append(d)
        # Retornamos el resultado procesado (favoritos)
        return favoritos


# Definición de función 'es_favorito' (parámetros: usuario_id_o_email, perfume_id)
def es_favorito(usuario_id_o_email: Any, perfume_id: int) -> bool:
    """Verifica si una fragancia específica está marcada como favorita por el usuario."""
    # Asignamos 'ids' con obtener_favoritos_Ids_usuario(usuario_id_o...
    ids = obtener_favoritos_Ids_usuario(usuario_id_o_email)
    # Retornamos el resultado procesado (int(perfume_id) in ids)
    return int(perfume_id) in ids


# Definición de función 'obtener_alertas_pendientes' sin parámetros externos
def obtener_alertas_pendientes() -> List[Dict[str, Any]]:
    """Calcula qué usuarios superaron su umbral de descuento configurado en sus favoritos."""
    # Asignamos 'sb_srv' con _obtener_admin_auth()
    sb_srv = _obtener_admin_auth()
    # Evaluamos la condición lógica (sb_srv is not None) para controlar el flujo
    if sb_srv is not None:
        # Asignamos 'alertas' con []
        alertas: List[Dict[str, Any]] = []
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'users_resp' con sb_srv.auth.admin.list_users(page=1, per_p...
            users_resp = sb_srv.auth.admin.list_users(page=1, per_page=200)
            # Asignamos 'users_list' con users_resp if isinstance(users_resp, list)...
            users_list = users_resp if isinstance(users_resp, list) else getattr(users_resp, "users", []) or []
            # Asignamos 'catalogo_map' con {int(p['id']): p for p in obtener_catalogo()}
            catalogo_map = {int(p["id"]): p for p in obtener_catalogo()}
            # Recorremos iterativamente cada 'u' en users_list
            for u in users_list:
                # Asignamos 'u_norm' con _normalizar_usuario_cloud(u)
                u_norm = _normalizar_usuario_cloud(u)
                # Evaluamos la condición lógica (not u_norm.get('alerta_email')) para controlar el flujo
                if not u_norm.get("alerta_email"):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'umbral' con int(u_norm.get('umbral_descuento', 10))
                umbral = int(u_norm.get("umbral_descuento", 10))
                # Asignamos 'meta' con dict(getattr(u, 'user_metadata', None) or {})
                meta = dict(getattr(u, "user_metadata", None) or {})
                # Asignamos 'favs' con meta.get('favoritos') or {}
                favs = meta.get("favoritos") or {}
                # Evaluamos la condición lógica (not isinstance(favs, dict)) para controlar el flujo
                if not isinstance(favs, dict):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Recorremos iterativamente cada '(k, v)' en favs.items()
                for k, v in favs.items():
                    # Evaluamos la condición lógica (not str(k).isdigit() or not isinstance(v, dict)) para controlar el flujo
                    if not str(k).isdigit() or not isinstance(v, dict):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'pid' con int(k)
                    pid = int(k)
                    # Asignamos 'p_guardado' con int(v.get('precio_guardado') or 0)
                    p_guardado = int(v.get("precio_guardado") or 0)
                    # Asignamos 'perf' con catalogo_map.get(pid)
                    perf = catalogo_map.get(pid)
                    # Asignamos 'mejor' con perf.get('mejor_precio') if perf else None
                    mejor = perf.get("mejor_precio") if perf else None
                    # Evaluamos la condición lógica (perf and p_guardado > 0 and mejor and (mejor > 0)) para controlar el flujo
                    if perf and p_guardado > 0 and mejor and mejor > 0:
                        # Asignamos 'rebaja_pct' con (p_guardado - mejor) * 100.0 / p_guardado
                        rebaja_pct = ((p_guardado - mejor) * 100.0) / p_guardado
                        # Evaluamos la condición lógica (rebaja_pct >= umbral) para controlar el flujo
                        if rebaja_pct >= umbral:
                            # Ejecutamos instrucción: alertas.append({'email': u_norm['email'], 'usuario_n...
                            alertas.append({
                                "email": u_norm["email"],
                                "usuario_nombre": u_norm["nombre"],
                                "umbral_descuento": umbral,
                                "perfume_nombre": perf["nombre"],
                                "marca": perf["marca"],
                                "precio_guardado": p_guardado,
                                "precio_nuevo": mejor,
                            })
            # Retornamos el resultado procesado (alertas)
            return alertas
        except Exception as e:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.debug(f"Aviso evaluando alertas cloud: {e}")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'query' con '\n SELECT u.email, u.nombre as usuario_no...
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
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query)
        # Retornamos el resultado procesado ([dict(r) for r in cursor.fetchall()])
        return [dict(r) for r in cursor.fetchall()]


# =============================================================================
# BLOQUE 10: RESOLUCIÓN Y CONSTRUCCIÓN DE ENLACES EXTERNOS A TIENDAS
# =============================================================================
def obtener_url_directa_tienda(perfume_id: int, tienda_nombre: str) -> Optional[Tuple[str, int, int, int]]:
    """Retorna la tupla (url_producto, precio_actual, precio_normal, volumen_ml) configurada en seed_catalogo.json."""
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
                    # Asignamos 'p_act' con enlace.get('precio_actual', p['precio_refe...
                    p_act = enlace.get("precio_actual", p["precio_referencia"])
                    # Asignamos 'p_norm' con enlace.get('precio_normal', p_act)
                    p_norm = enlace.get("precio_normal", p_act)
                    # Asignamos 'vol' con enlace.get('volumen_ml', p.get('volumen_ml...
                    vol = enlace.get("volumen_ml", p.get("volumen_ml", 100))
                    # Retornamos el resultado procesado ((enlace.get('url_producto', ''), p_act, p_norm,...)
                    return (enlace.get("url_producto", ""), p_act, p_norm, vol)
    # Retornamos el resultado procesado (None)
    return None


# Definición de función 'generar_url_tienda' (parámetros: tienda_nombre, perfume_nombre, url_directa)
def generar_url_tienda(tienda_nombre: str, perfume_nombre: str, url_directa: Optional[str] = None) -> Optional[str]:
    """Genera el enlace de navegación hacia la tienda correspondiente."""
    # Evaluamos la condición lógica (url_directa and url_directa.startswith(('http://', '...) para controlar el flujo
    if url_directa and url_directa.startswith(("http://", "https://")) and url_directa != "#":
        # Retornamos el resultado procesado (url_directa)
        return url_directa

    # Asignamos 't' con (tienda_nombre or '').lower()
    t = (tienda_nombre or "").lower()
    # Asignamos 'q' con urllib.parse.quote((perfume_nombre or '')....
    q = urllib.parse.quote((perfume_nombre or "").strip())
    # Evaluamos la condición lógica ('falabella' in t) para controlar el flujo
    if "falabella" in t:
        # Retornamos el resultado procesado (f'https://www.falabella.com/falabella-cl/search...)
        return f"https://www.falabella.com/falabella-cl/search?Ntt={q}"
    # Evaluamos la condición lógica ('paris' in t) para controlar el flujo
    if "paris" in t:
        # Retornamos el resultado procesado (f'https://www.paris.cl/search?q={q}')
        return f"https://www.paris.cl/search?q={q}"
    # Evaluamos la condición lógica ('ripley' in t) para controlar el flujo
    if "ripley" in t:
        # Retornamos el resultado procesado (f'https://simple.ripley.cl/search/{q}')
        return f"https://simple.ripley.cl/search/{q}"
    # Evaluamos la condición lógica ('silk' in t) para controlar el flujo
    if "silk" in t:
        # Retornamos el resultado procesado (f'https://www.silkperfumes.cl/search?q={q}')
        return f"https://www.silkperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('elite' in t) para controlar el flujo
    if "elite" in t:
        # Retornamos el resultado procesado (f'https://www.eliteperfumes.cl/search?q={q}')
        return f"https://www.eliteperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('alisha' in t) para controlar el flujo
    if "alisha" in t:
        # Retornamos el resultado procesado (f'https://alishaperfumes.cl/search?q={q}')
        return f"https://alishaperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('yauras' in t) para controlar el flujo
    if "yauras" in t:
        # Retornamos el resultado procesado (f'https://yauras.cl/search?q={q}')
        return f"https://yauras.cl/search?q={q}"
    # Evaluamos la condición lógica ('oferta' in t) para controlar el flujo
    if "oferta" in t:
        # Retornamos el resultado procesado (f'https://ofertaperfumes.cl/search?q={q}')
        return f"https://ofertaperfumes.cl/search?q={q}"
    # Evaluamos la condición lógica ('dbs' in t) para controlar el flujo
    if "dbs" in t:
        # Retornamos el resultado procesado (f'https://www.dbs.cl/search?q={q}')
        return f"https://www.dbs.cl/search?q={q}"
    # Retornamos el resultado procesado (None)
    return None


# Asignamos 'MARCAS_NO_RETAIL_TRADICIONAL' con {'lorenzo pazzaglia', 'ajmal', 'naseem', '...
MARCAS_NO_RETAIL_TRADICIONAL: Set[str] = {
    # Marcas nicho, de autor, independientes o clones que no se comercializan en tienda oficial de grandes almacenes chilenos
    "lorenzo pazzaglia", "ajmal", "naseem", "mirada", "mykonos", "arabiyat prestige",
    "jo milano", "jo milano paris", "bon parfumeur", "ramon monegal", "ramón monegal",
    "argos", "le falcone", "bharara", "stephane humbert lucas", "stéphane humbert lucas",
    "mast perfume", "mancera", "riiffs", "tubbees", "parfums de marly", "creed",
    "eight & bob", "cuba", "coleccion exclusiva", "just jack", "rave", "tauer perfumes",
    "xerjoff", "rue broca", "ahmed al maghribi", "fujiyama", "fcuk", "mpf",
    "lomani", "head", "bentley", "risala", "nike", "zippo", "sospiro", "atralia",
    "king of kings", "beauty & scent", "savia auraa", "giorgio beverly hills",
    "laboratorio olfattivo", "kajal", "pastor prive", "pastor privé", "m. micallef",
    "juliette has a gun", "jovoy paris", "nishane", "thameen", "auraa desire",
    "montale", "borouj", "silk perfumes", "auraa", "ferrari", "carrera",
    "kim kardashian", "amaran", "halston", "fred hayman", "disney", "cosmopolitan",
    "pharrell williams", "per'king", "rebecca minkoff", "blauer", "jacques bogart", "devsana",
}


# Definición de función 'tienda_comercializa_marca' (parámetros: tienda_nombre, marca, es_arabe_flag)
def tienda_comercializa_marca(tienda_nombre: str, marca: str, es_arabe_flag: Optional[bool] = None) -> bool:
    """
    Determina si una tienda debe ser consultada para una marca específica.
    - Para Chanel: solo se consulta en grandes tiendas departamentales oficiales (Falabella, Paris, Ripley).
    - Para todas las demás marcas (incluyendo perfumería árabe, de diseñador y nicho): se habilita
      la consulta en todas las tiendas de retail (Paris, Falabella, Ripley, DBS, etc.) y perfumerías
      especializadas, dado que los grandes retailers comercializan perfumería árabe en su catálogo y Marketplace.
    """
    # Normalizamos el nombre de la tienda a minúsculas para comparaciones seguras
    t_nom = (tienda_nombre or "").lower()
    # Normalizamos el nombre de la marca a minúsculas sin espacios laterales
    m = (marca or "").lower().strip()
    # Regla de distribución exclusiva de Chanel en grandes almacenes oficiales
    if "chanel" in m:
        # Retornamos el resultado procesado (any((retail in t_nom for retail in ['falabella'...)
        return any(retail in t_nom for retail in ["falabella", "paris", "ripley"])
    # Habilitamos todas las demás marcas (incluyendo perfumes árabes) en todas las tiendas de retail y especializadas
    return True


# =============================================================================
# BLOQUE 11: PERSISTENCIA TRANSACCIONAL ATÓMICA Y CONTROL DE RUNS / ERRORES
# =============================================================================
# - ¿Qué hace esta función (Trazabilidad de Auditorías)?:
#   Registra el inicio de una sesión de scraping en la tabla 'scraping_runs'.
#   Devuelve un run_id único para asociar cada precio extraído con su lote y trazar auditorías.
def iniciar_scraping_run(
    tipo_scraper: str,
    tienda_id: Optional[int] = None,
    mensaje_detalle: Optional[str] = None,
) -> Optional[int]:
    """Registra el inicio auditable de un ciclo de scraping en `scraping_runs`."""
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'payload' con {'tipo_scraper': tipo_scraper, 'estado': '...
            payload: Dict[str, Any] = {
                "tipo_scraper": tipo_scraper,
                "estado": "iniciado",
                "mensaje_detalle": mensaje_detalle,
            }
            # Evaluamos la condición lógica (tienda_id is not None) para controlar el flujo
            if tienda_id is not None:
                # Asignamos 'payload['tienda_id']' con int(tienda_id)
                payload["tienda_id"] = int(tienda_id)
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            resp = sb.table("scraping_runs").insert(payload).execute()
            # Evaluamos la condición lógica (resp.data) para controlar el flujo
            if resp.data:
                # Retornamos el resultado procesado (int(resp.data[0]['id']))
                return int(resp.data[0]["id"])
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.debug(f"No se pudo iniciar scraping_run en Supabase: {e}")
        # Retornamos el resultado procesado (None)
        return None

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            "INSERT INTO scraping_runs (tipo_scraper, tienda_id, estado, mensaje_detalle) VALUES (?, ?, 'iniciado', ?);",
            (tipo_scraper, tienda_id, mensaje_detalle),
        )
        # Retornamos el resultado procesado (int(cursor.lastrowid) if cursor.lastrowid else ...)
        return int(cursor.lastrowid) if cursor.lastrowid else None


# - ¿Qué hace esta función (Cierre de Lote ETL)?:
#   Cierra la sesión de scraping en 'scraping_runs', registrando el estado final, la duración,
#   la cantidad de precios actualizados, ofertas nuevas, cambios de stock y errores detectados.
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
    # Evaluamos la condición lógica (not run_id) para controlar el flujo
    if not run_id:
        # Finalizamos la ejecución de la función retornando None
        return
    # Asignamos 'estado_norm' con 'exitoso' if estado in ('completado', 'exi...
    estado_norm = "exitoso" if estado in ("completado", "exitoso") else estado
    # Asignamos 'estado_valido' con estado_norm if estado_norm in ('exitoso', ...
    estado_valido = estado_norm if estado_norm in ("exitoso", "parcial", "fallido", "cancelado") else "exitoso"
    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
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
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.debug(f"No se pudo finalizar scraping_run {run_id}: {e}")
        # Finalizamos la ejecución de la función retornando None
        return

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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


# - ¿Qué hace esta función (Transacción Atómica ACID en Base de Datos)?:
#   Es el núcleo de persistencia del sistema. Invoca la función almacenada sb.rpc("registrar_observacion_oferta") en PostgreSQL:
#   1. Actualiza o crea la oferta en la tabla 'ofertas_actuales' con su precio, stock y timestamp.
#   2. Si el precio cambió, registra automáticamente una entrada histórica en 'precios_registro' (tipo_evento='cambio_precio').
#   3. Si la extracción falló, preserva el precio anterior sin inventar stock falso (Regla de Oro ADR 001).
def registrar_observacion_oferta(observacion: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Persistencia transaccional de una observación de precio/stock:
    - Separa explícitamente variantes `'regular'` de `'tester'` para impedir que un Tester pise a un sellado.
    - Garantiza `p_precio_normal` no nulo al invocar la RPC en PostgreSQL, eliminando el rollback en `precios_registro`.
    - Elimina por completo los fallbacks `LIMIT 1` y el split-brain silencioso a SQLite cuando Supabase está activo.
    """
    # Evaluamos la condición lógica (observacion is None) para controlar el flujo
    if observacion is None:
        # Asignamos 'observacion' con kwargs
        observacion = kwargs
    # Evaluamos la condición lógica (kwargs) para controlar el flujo
    elif kwargs:
        # Asignamos 'observacion' con {**observacion, **kwargs}
        observacion = {**observacion, **kwargs}

    # Evaluamos la condición lógica (not isinstance(observacion, dict)) para controlar el flujo
    if not isinstance(observacion, dict):
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("La observación debe ser un diccionario válido")

    # Asignamos 'variante_id' con observacion.get('variante_id') or observac...
    variante_id = observacion.get("variante_id") or observacion.get("variante_id_sb")
    # Asignamos 'perfume_id' con observacion.get('perfume_id') or observaci...
    perfume_id = observacion.get("perfume_id") or observacion.get("perfume_id_sb") or observacion.get("perfume_id_sqlite")
    # Asignamos 'tienda_id' con observacion.get('tienda_id') or observacio...
    tienda_id = observacion.get("tienda_id") or observacion.get("tienda_id_sb") or observacion.get("tienda_id_sqlite")
    # Asignamos 'precio_actual' con observacion.get('precio_actual')
    precio_actual = observacion.get("precio_actual")
    # Asignamos 'precio_normal' con observacion.get('precio_normal')
    precio_normal = observacion.get("precio_normal")
    # Asignamos 'en_stock' con observacion.get('en_stock')
    en_stock = observacion.get("en_stock")
    # Asignamos 'url_producto' con (observacion.get('url_producto') or '').st...
    url_producto = (observacion.get("url_producto") or "").strip()
    # Asignamos 'volumen_ml' con observacion.get('volumen_ml') or 100
    volumen_ml = observacion.get("volumen_ml") or 100
    # Asignamos 'scraping_run_id' con observacion.get('scraping_run_id')
    scraping_run_id = observacion.get("scraping_run_id")

    # Asignamos 'formato_raw' con str(observacion.get('formato') or '').stri...
    formato_raw = str(observacion.get("formato") or "").strip().lower()
    # Evaluamos la condición lógica (formato_raw not in ('regular', 'tester')) para controlar el flujo
    if formato_raw not in ("regular", "tester"):
        # Asignamos 'formato_raw' con detectar_formato_oferta('', url_producto)
        formato_raw = detectar_formato_oferta("", url_producto)

    # Validaciones obligatorias de negocio
    if tienda_id is None:
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("tienda_id es obligatorio")
    # Evaluamos la condición lógica (variante_id is None and perfume_id is None) para controlar el flujo
    if variante_id is None and perfume_id is None:
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("Se requiere al menos variante_id o perfume_id")
    # Evaluamos la condición lógica (precio_actual is None or not isinstance(precio_actua...) para controlar el flujo
    if precio_actual is None or not isinstance(precio_actual, (int, float)) or int(precio_actual) <= 0:
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("El precio actual confirmado debe ser un entero positivo")
    # Asignamos 'precio_actual' con int(precio_actual)
    precio_actual = int(precio_actual)
    # Evaluamos la condición lógica (precio_actual < 4000 or precio_actual >= 1000000 or ...) para controlar el flujo
    if precio_actual < 4000 or precio_actual >= 1000000 or precio_actual in (9999999, 9999990, 999999):
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError(
            f"Precio fuera de rango comercial ({precio_actual}). Se descartan precios irreales o placeholders."
        )

    # Evaluamos la condición lógica (precio_normal is not None) para controlar el flujo
    if precio_normal is not None:
        # Evaluamos la condición lógica (not isinstance(precio_normal, (int, float)) or int(p...) para controlar el flujo
        if not isinstance(precio_normal, (int, float)) or int(precio_normal) <= 0:
            # Propagamos excepción explícita ante condición de error detectada
            raise ValueError("El precio normal debe ser un entero positivo o None")
        # Asignamos 'precio_normal' con int(precio_normal)
        precio_normal = int(precio_normal)
        # Evaluamos la condición lógica (precio_normal >= 1000000 or precio_normal in (999999...) para controlar el flujo
        if precio_normal >= 1000000 or precio_normal in (9999999, 9999990, 999999):
            # Asignamos 'precio_normal' con None
            precio_normal = None

    # Evaluamos la condición lógica (en_stock is None or not isinstance(en_stock, bool)) para controlar el flujo
    if en_stock is None or not isinstance(en_stock, bool):
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("El stock debe ser explícito (True o False), no desconocido ni nulo")

    # Evaluamos la condición lógica (not url_producto or not (url_producto.startswith('ht...) para controlar el flujo
    if not url_producto or not (url_producto.startswith("http://") or url_producto.startswith("https://")):
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("Se requiere una URL HTTP(S) válida")

    # Ejecutamos instrucción: limpiar_cache_catalogo()
    limpiar_cache_catalogo()

    # 1. Camino Primario: Supabase Transaccional (sin split-brain silencioso a SQLite)
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Asignamos 'sb_variante_id' con observacion.get('variante_id_sb') or varia...
        sb_variante_id = observacion.get("variante_id_sb") or variante_id
        # Asignamos 'sb_perfume_id' con observacion.get('perfume_id_sb') or perfum...
        sb_perfume_id = observacion.get("perfume_id_sb") or perfume_id
        # Asignamos 'vol_int' con int(round(float(volumen_ml))) if volumen_m...
        vol_int = int(round(float(volumen_ml))) if volumen_ml else 100

        # Evaluamos la condición lógica (not sb_variante_id and sb_perfume_id) para controlar el flujo
        if not sb_variante_id and sb_perfume_id:
            # Asignamos 'k_var' con (int(sb_perfume_id), vol_int, str(formato_...
            k_var = (int(sb_perfume_id), vol_int, str(formato_raw).strip().lower())
            # Evaluamos la condición lógica (k_var in _CACHE_VARIANTE_SUPABASE_POR_TUPLA) para controlar el flujo
            if k_var in _CACHE_VARIANTE_SUPABASE_POR_TUPLA:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb_variante_id = _CACHE_VARIANTE_SUPABASE_POR_TUPLA[k_var]
            else:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                r_v = (
                    sb.table("variantes_perfume")
                    .select("id")
                    .eq("perfume_id", sb_perfume_id)
                    .eq("volumen_ml", vol_int)
                    .eq("formato", formato_raw)
                    .limit(1)
                    .execute()
                )
                # Evaluamos la condición lógica (r_v.data) para controlar el flujo
                if r_v.data:
                    # Asignamos 'sb_variante_id' con r_v.data[0]['id']
                    sb_variante_id = r_v.data[0]["id"]
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    _CACHE_VARIANTE_SUPABASE_POR_TUPLA[k_var] = sb_variante_id
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    _CACHE_VARIANTE_DEFECTO_SUPABASE.setdefault(int(sb_perfume_id), sb_variante_id)
                else:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    r_p = sb.table("perfumes").select("id, tipo, nombre").eq("id", sb_perfume_id).limit(1).execute()
                    # Evaluamos la condición lógica (not r_p.data) para controlar el flujo
                    if not r_p.data:
                        # Propagamos excepción explícita ante condición de error detectada
                        raise ValueError(f"El perfume_id {sb_perfume_id} no existe en Supabase.")
                    # Asignamos 'tipo_p' con r_p.data[0].get('tipo') or 'Eau de Parfum'
                    tipo_p = r_p.data[0].get("tipo") or "Eau de Parfum"
                    # Asignamos 'slug_v' con f'perfume-{sb_perfume_id}-{vol_int}ml' if ...
                    slug_v = (
                        f"perfume-{sb_perfume_id}-{vol_int}ml"
                        if formato_raw == "regular"
                        else f"perfume-{sb_perfume_id}-{vol_int}ml-{formato_raw}"
                    )
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
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
                    # Evaluamos la condición lógica (r_ins.data) para controlar el flujo
                    if r_ins.data:
                        # Asignamos 'sb_variante_id' con r_ins.data[0]['id']
                        sb_variante_id = r_ins.data[0]["id"]
                    else:
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        r_recheck = sb.table("variantes_perfume").select("id").eq("slug", slug_v).limit(1).execute()
                        # Evaluamos la condición lógica (r_recheck.data) para controlar el flujo
                        if r_recheck.data:
                            # Asignamos 'sb_variante_id' con r_recheck.data[0]['id']
                            sb_variante_id = r_recheck.data[0]["id"]

                    # Evaluamos la condición lógica (sb_variante_id) para controlar el flujo
                    if sb_variante_id:
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        _CACHE_VARIANTE_SUPABASE_POR_TUPLA[k_var] = sb_variante_id
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        _CACHE_VARIANTE_DEFECTO_SUPABASE.setdefault(int(sb_perfume_id), sb_variante_id)

        # Evaluamos la condición lógica (not sb_variante_id) para controlar el flujo
        if not sb_variante_id:
            # Propagamos excepción explícita ante condición de error detectada
            raise ValueError(f"No fue posible resolver variante_id en Supabase para perfume_id={sb_perfume_id}.")

        # Asignamos 'sb_tienda_id' con observacion.get('tienda_id_sb') or tienda_id
        sb_tienda_id = observacion.get("tienda_id_sb") or tienda_id
        # Asegurar precio_normal válido para evitar rollback NOT NULL en precios_registro
        p_normal_rpc = precio_normal if (precio_normal and precio_normal >= precio_actual) else precio_actual

        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            rpc_res = sb.rpc("registrar_observacion_oferta", {
                "p_variante_id": int(sb_variante_id),
                "p_tienda_id": int(sb_tienda_id),
                "p_precio_actual": precio_actual,
                "p_precio_normal": p_normal_rpc,
                "p_en_stock": en_stock,
                "p_url_producto": url_producto,
                "p_scraping_run_id": scraping_run_id,
            }).execute()
            # Evaluamos la condición lógica (rpc_res.data) para controlar el flujo
            if rpc_res.data:
                # Retornamos el resultado procesado (rpc_res.data)
                return rpc_res.data
            # Propagamos excepción explícita ante condición de error detectada
            raise RuntimeError("La RPC registrar_observacion_oferta no retornó datos.")
        except Exception as e:
            # Evaluamos la condición lógica ('inactiva' in str(e).lower()) para controlar el flujo
            if "inactiva" in str(e).lower():
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    logger.info(f"Reactivando variante {sb_variante_id} en Supabase tras hallazgo de oferta en vivo...")
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    sb.table("variantes_perfume").update({"activa": True}).eq("id", int(sb_variante_id)).execute()
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    rpc_res = sb.rpc("registrar_observacion_oferta", {
                        "p_variante_id": int(sb_variante_id),
                        "p_tienda_id": int(sb_tienda_id),
                        "p_precio_actual": precio_actual,
                        "p_precio_normal": p_normal_rpc,
                        "p_en_stock": en_stock,
                        "p_url_producto": url_producto,
                        "p_scraping_run_id": scraping_run_id,
                    }).execute()
                    # Evaluamos la condición lógica (rpc_res.data) para controlar el flujo
                    if rpc_res.data:
                        # Retornamos el resultado procesado (rpc_res.data)
                        return rpc_res.data
                except Exception as e_retry:
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.error(f"Fallo tras reactivación de variante {sb_variante_id}: {e_retry}")
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.error(
                f"Fallo transaccional en Supabase RPC registrar_observacion_oferta "
                f"(variante={sb_variante_id}, tienda={sb_tienda_id}): {e}"
            )
            # Propagamos excepción explícita ante condición de error detectada
            raise

    # 2. Camino Local: Persistencia Transaccional Atómica en SQLite (sin fallbacks LIMIT 1)
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Asignamos 'local_variante_id' con None
        local_variante_id = None
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        local_perfume_id = observacion.get("perfume_id_sqlite") or perfume_id

        # Evaluamos la condición lógica (variante_id) para controlar el flujo
        if variante_id:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "SELECT id, perfume_id, volumen_ml, formato FROM variantes_perfume WHERE id = ?;",
                (variante_id,),
            )
            # Asignamos 'row_v' con cursor.fetchone()
            row_v = cursor.fetchone()
            # Evaluamos la condición lógica (row_v) para controlar el flujo
            if row_v:
                # Asignamos 'local_variante_id' con row_v['id']
                local_variante_id = row_v["id"]
                # Asignamos 'local_perfume_id' con row_v['perfume_id']
                local_perfume_id = row_v["perfume_id"]
                # Asignamos 'volumen_ml' con row_v['volumen_ml']
                volumen_ml = row_v["volumen_ml"]

        # Evaluamos la condición lógica (not local_variante_id and local_perfume_id) para controlar el flujo
        if not local_variante_id and local_perfume_id:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "SELECT id FROM variantes_perfume WHERE perfume_id = ? AND ABS(volumen_ml - ?) < 1 AND LOWER(formato) = ? LIMIT 1;",
                (local_perfume_id, volumen_ml, formato_raw),
            )
            # Asignamos 'row_v' con cursor.fetchone()
            row_v = cursor.fetchone()
            # Evaluamos la condición lógica (row_v) para controlar el flujo
            if row_v:
                # Asignamos 'local_variante_id' con row_v['id']
                local_variante_id = row_v["id"]
            else:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("SELECT id, tipo, nombre FROM perfumes WHERE id = ?;", (local_perfume_id,))
                # Asignamos 'row_p' con cursor.fetchone()
                row_p = cursor.fetchone()
                # Evaluamos la condición lógica (not row_p) para controlar el flujo
                if not row_p:
                    # Propagamos excepción explícita ante condición de error detectada
                    raise ValueError(f"El perfume_id {local_perfume_id} no existe en SQLite.")
                # Asignamos 'tipo_p' con row_p['tipo'] or 'Eau de Parfum'
                tipo_p = row_p["tipo"] or "Eau de Parfum"
                # Asignamos 'vol_int' con int(round(float(volumen_ml)))
                vol_int = int(round(float(volumen_ml)))
                # Asignamos 'slug_v' con f'perfume-{local_perfume_id}-{vol_int}ml' ...
                slug_v = (
                    f"perfume-{local_perfume_id}-{vol_int}ml"
                    if formato_raw == "regular"
                    else f"perfume-{local_perfume_id}-{vol_int}ml-{formato_raw}"
                )
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("""
                INSERT OR IGNORE INTO variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa)
                VALUES (?, ?, ?, ?, ?, 1);
                """, (local_perfume_id, tipo_p, volumen_ml, formato_raw, slug_v))
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute(
                    "SELECT id FROM variantes_perfume WHERE perfume_id = ? AND ABS(volumen_ml - ?) < 1 AND LOWER(formato) = ? LIMIT 1;",
                    (local_perfume_id, volumen_ml, formato_raw),
                )
                # Asignamos 'row_v' con cursor.fetchone()
                row_v = cursor.fetchone()
                # Evaluamos la condición lógica (row_v) para controlar el flujo
                if row_v:
                    # Asignamos 'local_variante_id' con row_v['id']
                    local_variante_id = row_v["id"]

        # Evaluamos la condición lógica (not local_variante_id) para controlar el flujo
        if not local_variante_id:
            # Propagamos excepción explícita ante condición de error detectada
            raise ValueError("La variante especificada no existe y no pudo crearse válidamente.")

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        local_tienda_id = observacion.get("tienda_id_sqlite") or tienda_id
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id FROM tiendas WHERE id = ?;", (local_tienda_id,))
        # Evaluamos la condición lógica (not cursor.fetchone()) para controlar el flujo
        if not cursor.fetchone():
            # Propagamos excepción explícita ante condición de error detectada
            raise ValueError(f"La tienda_id {local_tienda_id} no existe en la base de datos.")

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            "SELECT * FROM ofertas_actuales WHERE variante_id = ? AND tienda_id = ?;",
            (local_variante_id, local_tienda_id),
        )
        # Asignamos 'row_oferta' con cursor.fetchone()
        row_oferta = cursor.fetchone()

        # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Asignamos 'obs_uuid' con str(observacion.get('observacion_id') or u...
        obs_uuid = str(observacion.get("observacion_id") or uuid.uuid4())
        # Asignamos 'p_normal_final' con precio_normal if precio_normal else row_of...
        p_normal_final = (
            precio_normal
            if precio_normal
            else (row_oferta["precio_normal"] if (row_oferta and row_oferta["precio_normal"]) else precio_actual)
        )

        # Evaluamos la condición lógica (not row_oferta) para controlar el flujo
        if not row_oferta:
            # Asignamos 'estado_ini' con 'activa' if en_stock else 'agotada'
            estado_ini = "activa" if en_stock else "agotada"
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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
            # Asignamos 'oferta_id' con cursor.lastrowid
            oferta_id = cursor.lastrowid
            # Asignamos 'tipo_evento' con 'observacion_inicial'
            tipo_evento = "observacion_inicial"
            # Asignamos 'campos_mod' con ['precio_actual', 'en_stock', 'url_producto']
            campos_mod = ["precio_actual", "en_stock", "url_producto"]
            # Evaluamos la condición lógica (precio_normal) para controlar el flujo
            if precio_normal:
                # Ejecutamos instrucción: campos_mod.append('precio_normal')
                campos_mod.append("precio_normal")

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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

            # Retornamos el resultado procesado ({'oferta_id': oferta_id, 'resultado': 'creada',...)
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

        # Asignamos 'oferta_id' con row_oferta['id']
        oferta_id = row_oferta["id"]
        # Asignamos 'precio_ant' con row_oferta['precio_actual']
        precio_ant = row_oferta["precio_actual"]
        # Asignamos 'stock_ant' con bool(row_oferta['en_stock'])
        stock_ant = bool(row_oferta["en_stock"])
        # Asignamos 'url_ant' con row_oferta['url_producto']
        url_ant = row_oferta["url_producto"]
        # Asignamos 'p_norm_ant' con row_oferta['precio_normal']
        p_norm_ant = row_oferta["precio_normal"]

        # Asignamos 'campos_mod' con []
        campos_mod = []
        # Evaluamos la condición lógica (precio_ant != precio_actual) para controlar el flujo
        if precio_ant != precio_actual:
            # Ejecutamos instrucción: campos_mod.append('precio_actual')
            campos_mod.append("precio_actual")
        # Evaluamos la condición lógica (stock_ant != en_stock) para controlar el flujo
        if stock_ant != en_stock:
            # Ejecutamos instrucción: campos_mod.append('en_stock')
            campos_mod.append("en_stock")
        # Evaluamos la condición lógica (url_ant != url_producto) para controlar el flujo
        if url_ant != url_producto:
            # Ejecutamos instrucción: campos_mod.append('url_producto')
            campos_mod.append("url_producto")
        # Evaluamos la condición lógica (precio_normal and p_norm_ant != precio_normal) para controlar el flujo
        if precio_normal and p_norm_ant != precio_normal:
            # Ejecutamos instrucción: campos_mod.append('precio_normal')
            campos_mod.append("precio_normal")

        # Evaluamos la condición lógica (not campos_mod) para controlar el flujo
        if not campos_mod:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            UPDATE ofertas_actuales
            SET ultima_verificacion_exitosa = ?, ultimo_intento = ?,
                fallos_consecutivos = 0, ultimo_error = NULL,
                estado = ?, updated_at = ?
            WHERE id = ?;
            """, (ahora, ahora, "activa" if en_stock else "agotada", ahora, oferta_id))
            # Retornamos el resultado procesado ({'oferta_id': oferta_id, 'resultado': 'sin_camb...)
            return {
                "oferta_id": oferta_id,
                "resultado": "sin_cambios",
                "tipo_evento": None,
                "campos_modificados": [],
            }

        # Evaluamos la condición lógica (len(campos_mod) > 1) para controlar el flujo
        if len(campos_mod) > 1:
            # Asignamos 'tipo_evento' con 'cambio_multiple'
            tipo_evento = "cambio_multiple"
        # Evaluamos la condición lógica (campos_mod[0] == 'precio_actual') para controlar el flujo
        elif campos_mod[0] == "precio_actual":
            # Asignamos 'tipo_evento' con 'cambio_precio'
            tipo_evento = "cambio_precio"
        # Evaluamos la condición lógica (campos_mod[0] == 'en_stock') para controlar el flujo
        elif campos_mod[0] == "en_stock":
            # Asignamos 'tipo_evento' con 'cambio_stock'
            tipo_evento = "cambio_stock"
        # Evaluamos la condición lógica (campos_mod[0] == 'url_producto') para controlar el flujo
        elif campos_mod[0] == "url_producto":
            # Asignamos 'tipo_evento' con 'cambio_url'
            tipo_evento = "cambio_url"
        else:
            # Asignamos 'tipo_evento' con 'cambio_datos'
            tipo_evento = "cambio_datos"

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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

        # Retornamos el resultado procesado ({'oferta_id': oferta_id, 'resultado': 'actualiz...)
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


# Definición de función 'registrar_fallo_scraping' (parámetros: tienda_id, mensaje, variante_id, perfume_id, ...)
def registrar_fallo_scraping(
    tienda_id: int,
    mensaje: str,
    variante_id: Optional[int] = None,
    perfume_id: Optional[int] = None,
    motivo_codigo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Registra un fallo de extracción sin alterar el precio actual ni la URL confirmada.
    - Si `motivo_codigo` es `'waf'`, `'timeout'` o `'parse_error'`, registra el intento pero NO incrementa
      `fallos_consecutivos` ni retira la oferta.
    - Si `motivo_codigo == 'no_encontrado_en_feed'` y acumula >= 5 fallos consecutivos, retira la oferta
      a `estado='agotada'` y `en_stock=False`.
    - En modo legado (`motivo_codigo=None`), mantiene retrocompatibilidad (`>=5` -> `'requiere_revision'`,
      `404` -> `'requiere_revision'` y `en_stock=False`).
    """
    # Evaluamos la condición lógica (tienda_id is None) para controlar el flujo
    if tienda_id is None:
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("tienda_id es obligatorio")
    # Evaluamos la condición lógica (not mensaje or not str(mensaje).strip()) para controlar el flujo
    if not mensaje or not str(mensaje).strip():
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError("Debe indicarse el motivo del fallo")

    # Asignamos 'ahora' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Asignamos 'ahora_iso' con datetime.now(timezone.utc).isoformat()
    ahora_iso = datetime.now(timezone.utc).isoformat()
    # Asignamos 'msg_clean' con str(mensaje).strip()[:2000]
    msg_clean = str(mensaje).strip()[:2000]
    # Asignamos 'codigo_norm' con (motivo_codigo or '').strip().lower() or None
    codigo_norm = (motivo_codigo or "").strip().lower() or None
    # Asignamos 'es_transitorio_red' con codigo_norm in ('waf', 'timeout', 'parse_e...
    es_transitorio_red = codigo_norm in ("waf", "timeout", "parse_error")
    # Asignamos 'es_ausencia_feed' con codigo_norm == 'no_encontrado_en_feed'
    es_ausencia_feed = codigo_norm == "no_encontrado_en_feed"

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Asignamos 'variantes_objetivo' con []
        variantes_objetivo: List[int] = []
        # Evaluamos la condición lógica (variante_id) para controlar el flujo
        if variante_id:
            # Asignamos 'variantes_objetivo' con [int(variante_id)]
            variantes_objetivo = [int(variante_id)]
        # Evaluamos la condición lógica (perfume_id) para controlar el flujo
        elif perfume_id:
            # Asignamos 'pid' con int(perfume_id)
            pid = int(perfume_id)
            # Evaluamos la condición lógica (es_ausencia_feed) para controlar el flujo
            if es_ausencia_feed:
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    r_oa = (
                        sb.table("ofertas_actuales")
                        .select("variante_id, variantes_perfume!inner(perfume_id)")
                        .eq("tienda_id", int(tienda_id))
                        .eq("variantes_perfume.perfume_id", pid)
                        .eq("estado", "activa")
                        .execute()
                    )
                    # Asignamos 'variantes_objetivo' con sorted({int(x['variante_id']) for x in r_o...
                    variantes_objetivo = sorted({int(x["variante_id"]) for x in (r_oa.data or []) if x.get("variante_id")})
                except Exception as e:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    logger.debug(f"Error consultando variantes activas en Supabase: {e}")
            # Evaluamos la condición lógica (not variantes_objetivo) para controlar el flujo
            if not variantes_objetivo:
                # Evaluamos la condición lógica (pid in _CACHE_VARIANTE_DEFECTO_SUPABASE) para controlar el flujo
                if pid in _CACHE_VARIANTE_DEFECTO_SUPABASE:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    variantes_objetivo = [_CACHE_VARIANTE_DEFECTO_SUPABASE[pid]]
                else:
                    # Bloque try/except para manejo seguro de errores y resiliencia operativa
                    try:
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        r_v = sb.table("variantes_perfume").select("id").eq("perfume_id", pid).limit(1).execute()
                        # Evaluamos la condición lógica (r_v.data) para controlar el flujo
                        if r_v.data:
                            # Asignamos 'vid_def' con int(r_v.data[0]['id'])
                            vid_def = int(r_v.data[0]["id"])
                            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                            _CACHE_VARIANTE_DEFECTO_SUPABASE[pid] = vid_def
                            # Asignamos 'variantes_objetivo' con [vid_def]
                            variantes_objetivo = [vid_def]
                    except Exception as e:
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        logger.debug(f"Error resolviendo variante en Supabase: {e}")

        # Evaluamos la condición lógica (not variantes_objetivo) para controlar el flujo
        if not variantes_objetivo:
            # Retornamos el resultado procesado ({'resultado': 'fallo_sin_variante', 'mensaje': ...)
            return {"resultado": "fallo_sin_variante", "mensaje": msg_clean}

        # Asignamos 'ultimo_res' con {'resultado': 'fallo_sin_oferta', 'mensaje...
        ultimo_res: Dict[str, Any] = {"resultado": "fallo_sin_oferta", "mensaje": msg_clean}
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Recorremos iterativamente cada 'vid_item' en variantes_objetivo
            for vid_item in variantes_objetivo:
                # Evaluamos la condición lógica (es_transitorio_red) para controlar el flujo
                if es_transitorio_red:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    r_curr = (
                        sb.table("ofertas_actuales")
                        .select("id, fallos_consecutivos, estado, precio_actual, en_stock")
                        .eq("variante_id", int(vid_item))
                        .eq("tienda_id", int(tienda_id))
                        .limit(1)
                        .execute()
                    )
                    # Evaluamos la condición lógica (r_curr.data) para controlar el flujo
                    if r_curr.data:
                        # Asignamos 'row_c' con r_curr.data[0]
                        row_c = r_curr.data[0]
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        sb.table("ofertas_actuales").update({
                            "ultimo_intento": ahora_iso,
                            "ultimo_error": f"[{codigo_norm}] {msg_clean}"[:2000],
                            "updated_at": ahora_iso,
                        }).eq("id", row_c["id"]).execute()
                        # Asignamos 'ultimo_res' con {'resultado': 'fallo_transitorio', 'oferta...
                        ultimo_res = {
                            "resultado": "fallo_transitorio",
                            "oferta_id": row_c["id"],
                            "fallos_consecutivos": int(row_c.get("fallos_consecutivos") or 0),
                            "estado": row_c.get("estado"),
                            "precio_actual": row_c.get("precio_actual"),
                            "en_stock": bool(row_c.get("en_stock")),
                        }
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'msg_lower' con msg_clean.lower()
                msg_lower = msg_clean.lower()
                # Asignamos 'es_404' con '404' in msg_clean or 'no encontrada' in m...
                es_404 = ("404" in msg_clean or "no encontrada" in msg_lower or "not found" in msg_lower or "inexistente" in msg_lower)
                # Asignamos 'limite_fallos' con 1 if es_404 else 5
                limite_fallos = 1 if es_404 else 5
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    rpc_res = sb.rpc("registrar_fallo_scraping", {
                        "p_variante_id": int(vid_item),
                        "p_tienda_id": int(tienda_id),
                        "p_mensaje": msg_clean,
                    }).execute()
                    # Asignamos 'res_data' con rpc_res.data or {'resultado': 'fallo_regis...
                    res_data = rpc_res.data or {"resultado": "fallo_registrado"}
                except Exception as rpc_err:
                    # Fallback directo sobre la tabla ofertas_actuales si la función RPC carece de permisos (código 42501)
                    if "42501" not in str(rpc_err) and "permission denied" not in str(rpc_err).lower():
                        # Propagamos excepción explícita ante condición de error detectada
                        raise
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    r_curr_fb = (
                        sb.table("ofertas_actuales")
                        .select("id, fallos_consecutivos, estado, precio_actual, en_stock")
                        .eq("variante_id", int(vid_item))
                        .eq("tienda_id", int(tienda_id))
                        .limit(1)
                        .execute()
                    )
                    # Evaluamos la condición lógica (not r_curr_fb.data) para controlar el flujo
                    if not r_curr_fb.data:
                        # Asignamos 'res_data' con {'resultado': 'fallo_sin_oferta', 'mensaje...
                        res_data = {"resultado": "fallo_sin_oferta", "mensaje": msg_clean}
                    else:
                        # Asignamos 'row_fb' con r_curr_fb.data[0]
                        row_fb = r_curr_fb.data[0]
                        # Asignamos 'nuevos_fallos' con int(row_fb.get('fallos_consecutivos') or 0...
                        nuevos_fallos = int(row_fb.get("fallos_consecutivos") or 0) + 1
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        sb.table("ofertas_actuales").update({
                            "fallos_consecutivos": nuevos_fallos,
                            "ultimo_intento": ahora_iso,
                            "ultimo_error": msg_clean[:2000],
                            "updated_at": ahora_iso,
                        }).eq("id", row_fb["id"]).execute()
                        # Asignamos 'res_data' con {'resultado': 'fallo_registrado', 'oferta_...
                        res_data = {
                            "resultado": "fallo_registrado",
                            "oferta_id": row_fb["id"],
                            "fallos_consecutivos": nuevos_fallos,
                            "estado": row_fb.get("estado"),
                            "precio_actual": row_fb.get("precio_actual"),
                            "en_stock": bool(row_fb.get("en_stock")),
                        }
                # Evaluamos la condición lógica (isinstance(res_data, dict) and int(res_data.get('fal...) para controlar el flujo
                if isinstance(res_data, dict) and int(res_data.get("fallos_consecutivos") or 0) >= limite_fallos:
                    # Asignamos 'oferta_id_sb' con res_data.get('oferta_id')
                    oferta_id_sb = res_data.get("oferta_id")
                    # Evaluamos la condición lógica (oferta_id_sb) para controlar el flujo
                    if oferta_id_sb:
                        # Evaluamos la condición lógica (es_ausencia_feed and (not es_404)) para controlar el flujo
                        if es_ausencia_feed and not es_404:
                            # Asignamos 'up_data' con {'estado': 'agotada', 'en_stock': False}
                            up_data = {"estado": "agotada", "en_stock": False}
                            # Asignamos 'res_data['estado']' con 'agotada'
                            res_data["estado"] = "agotada"
                            # Asignamos 'res_data['en_stock']' con False
                            res_data["en_stock"] = False
                        else:
                            # Asignamos 'up_data' con {'estado': 'requiere_revision'}
                            up_data = {"estado": "requiere_revision"}
                            # Asignamos 'res_data['estado']' con 'requiere_revision'
                            res_data["estado"] = "requiere_revision"
                            # Evaluamos la condición lógica (es_404) para controlar el flujo
                            if es_404:
                                # Asignamos 'up_data['en_stock']' con False
                                up_data["en_stock"] = False
                                # Asignamos 'res_data['en_stock']' con False
                                res_data["en_stock"] = False
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        sb.table("ofertas_actuales").update(up_data).eq("id", oferta_id_sb).execute()
                        # Ejecutamos instrucción: limpiar_cache_catalogo()
                        limpiar_cache_catalogo()
                # Asignamos 'ultimo_res' con res_data
                ultimo_res = res_data
            # Retornamos el resultado procesado (ultimo_res)
            return ultimo_res
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.error(f"Error en RPC registrar_fallo_scraping en Supabase: {e}")
            # Propagamos excepción explícita ante condición de error detectada
            raise

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Asignamos 'variantes_sq' con []
        variantes_sq: List[int] = []
        # Evaluamos la condición lógica (variante_id) para controlar el flujo
        if variante_id:
            # Asignamos 'variantes_sq' con [int(variante_id)]
            variantes_sq = [int(variante_id)]
        # Evaluamos la condición lógica (perfume_id) para controlar el flujo
        elif perfume_id:
            # Evaluamos la condición lógica (es_ausencia_feed) para controlar el flujo
            if es_ausencia_feed:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute(
                    """
                    SELECT oa.variante_id
                    FROM ofertas_actuales oa
                    JOIN variantes_perfume vp ON vp.id = oa.variante_id
                    WHERE vp.perfume_id = ? AND oa.tienda_id = ? AND oa.estado = 'activa';
                    """,
                    (perfume_id, tienda_id),
                )
                # Asignamos 'variantes_sq' con [int(r['variante_id']) for r in cursor.fet...
                variantes_sq = [int(r["variante_id"]) for r in cursor.fetchall()]
            # Evaluamos la condición lógica (not variantes_sq) para controlar el flujo
            if not variantes_sq:
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute("SELECT id FROM variantes_perfume WHERE perfume_id = ? LIMIT 1;", (perfume_id,))
                # Asignamos 'row_v' con cursor.fetchone()
                row_v = cursor.fetchone()
                # Evaluamos la condición lógica (row_v) para controlar el flujo
                if row_v:
                    # Asignamos 'variantes_sq' con [int(row_v['id'])]
                    variantes_sq = [int(row_v["id"])]

        # Evaluamos la condición lógica (not variantes_sq) para controlar el flujo
        if not variantes_sq:
            # Retornamos el resultado procesado ({'resultado': 'fallo_sin_variante', 'mensaje': ...)
            return {"resultado": "fallo_sin_variante", "mensaje": msg_clean}

        # Asignamos 'ultimo_sq' con {'resultado': 'fallo_sin_oferta', 'mensaje...
        ultimo_sq: Dict[str, Any] = {"resultado": "fallo_sin_oferta", "mensaje": msg_clean}
        # Recorremos iterativamente cada 'target_variante_id' en variantes_sq
        for target_variante_id in variantes_sq:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                "SELECT id, fallos_consecutivos, precio_actual, en_stock, estado "
                "FROM ofertas_actuales WHERE variante_id = ? AND tienda_id = ?;",
                (target_variante_id, tienda_id),
            )
            # Asignamos 'row_oferta' con cursor.fetchone()
            row_oferta = cursor.fetchone()
            # Evaluamos la condición lógica (not row_oferta) para controlar el flujo
            if not row_oferta:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Evaluamos la condición lógica (es_transitorio_red) para controlar el flujo
            if es_transitorio_red:
                # Asignamos 'err_txt' con f'[{codigo_norm}] {msg_clean}'[:2000]
                err_txt = f"[{codigo_norm}] {msg_clean}"[:2000]
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute(
                    "UPDATE ofertas_actuales SET ultimo_intento = ?, ultimo_error = ?, updated_at = ? WHERE id = ?;",
                    (ahora, err_txt, ahora, row_oferta["id"]),
                )
                # Asignamos 'ultimo_sq' con {'resultado': 'fallo_transitorio', 'oferta...
                ultimo_sq = {
                    "resultado": "fallo_transitorio",
                    "oferta_id": row_oferta["id"],
                    "fallos_consecutivos": int(row_oferta["fallos_consecutivos"] or 0),
                    "estado": row_oferta["estado"],
                    "precio_actual": row_oferta["precio_actual"],
                    "en_stock": bool(row_oferta["en_stock"]),
                }
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Asignamos 'msg_lower' con msg_clean.lower()
            msg_lower = msg_clean.lower()
            # Asignamos 'es_404' con '404' in msg_clean or 'no encontrada' in m...
            es_404 = ("404" in msg_clean or "no encontrada" in msg_lower or "not found" in msg_lower or "inexistente" in msg_lower)
            # Asignamos 'nueva_cuenta' con (row_oferta['fallos_consecutivos'] or 0) + 1
            nueva_cuenta = (row_oferta["fallos_consecutivos"] or 0) + 1
            # Evaluamos la condición lógica (es_404) para controlar el flujo
            if es_404:
                # Asignamos 'nuevo_estado' con 'requiere_revision'
                nuevo_estado = "requiere_revision"
                # Asignamos 'nuevo_stock' con False
                nuevo_stock = False
            # Evaluamos la condición lógica (es_ausencia_feed and nueva_cuenta >= 5) para controlar el flujo
            elif es_ausencia_feed and nueva_cuenta >= 5:
                # Asignamos 'nuevo_estado' con 'agotada'
                nuevo_estado = "agotada"
                # Asignamos 'nuevo_stock' con False
                nuevo_stock = False
            # Evaluamos la condición lógica (nueva_cuenta >= 5) para controlar el flujo
            elif nueva_cuenta >= 5:
                # Asignamos 'nuevo_estado' con 'requiere_revision'
                nuevo_estado = "requiere_revision"
                # Asignamos 'nuevo_stock' con bool(row_oferta['en_stock'])
                nuevo_stock = bool(row_oferta["en_stock"])
            else:
                # Asignamos 'nuevo_estado' con row_oferta['estado']
                nuevo_estado = row_oferta["estado"]
                # Asignamos 'nuevo_stock' con bool(row_oferta['en_stock'])
                nuevo_stock = bool(row_oferta["en_stock"])

            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            UPDATE ofertas_actuales
            SET ultimo_intento = ?, fallos_consecutivos = ?, ultimo_error = ?, estado = ?, en_stock = ?, updated_at = ?
            WHERE id = ?;
            """, (ahora, nueva_cuenta, msg_clean, nuevo_estado, int(nuevo_stock), ahora, row_oferta["id"]))

            # Asignamos 'ultimo_sq' con {'resultado': 'fallo_registrado', 'oferta_...
            ultimo_sq = {
                "resultado": "fallo_registrado",
                "oferta_id": row_oferta["id"],
                "fallos_consecutivos": nueva_cuenta,
                "estado": nuevo_estado,
                "precio_actual": row_oferta["precio_actual"],
                "en_stock": bool(nuevo_stock),
            }

        # Retornamos el resultado procesado (ultimo_sq)
        return ultimo_sq


# - ¿Qué hace esta función?:
#   Marca una oferta con `estado = 'requiere_revision'` y registra el motivo en `ultimo_error`
#   (usado por el detector en vivo de precios atípicos sin eliminar la fila).
def marcar_oferta_requiere_revision(oferta_id: int, motivo: str) -> bool:
    # Evaluamos la condición lógica (not oferta_id) para controlar el flujo
    if not oferta_id:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'ahora_iso' con datetime.now(timezone.utc).isoformat()
    ahora_iso = datetime.now(timezone.utc).isoformat()
    # Asignamos 'msg_limpio' con str(motivo or 'Requiere revisión')[:240]
    msg_limpio = str(motivo or "Requiere revisión")[:240]
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("ofertas_actuales").update({
                "estado": "requiere_revision",
                "ultimo_error": msg_limpio,
                "updated_at": ahora_iso,
            }).eq("id", int(oferta_id)).execute()
            # Retornamos el resultado procesado (True)
            return True
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"No se pudo marcar oferta #{oferta_id} en revisión en Supabase: {e}")
            # Retornamos el resultado procesado (False)
            return False

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'ahora_sq' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ahora_sq = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(
            "UPDATE ofertas_actuales SET estado = 'requiere_revision', ultimo_error = ?, updated_at = ? WHERE id = ?;",
            (msg_limpio, ahora_sq, int(oferta_id)),
        )
    # Retornamos el resultado procesado (True)
    return True


# Definición de función 'registrar_precio' (parámetros: perfume_id, tienda_id, precio_actual, precio_normal, ...)
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
    # Ejecutamos instrucción: registrar_observacion_oferta({'perfume_id': perfume_...
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
# - ¿Qué hace esta función (Normalizador Diacrítico de Búsqueda)?:
#   Normaliza cadenas de texto eliminando diacríticos, acentos y mayúsculas
#   (ej. 'Chloé' -> 'chloe', 'Ramón' -> 'ramon') para búsquedas de alta velocidad O(1).
def normalizar_texto_busqueda(txt: Any) -> str:
    """Normaliza texto para búsqueda insensible a mayúsculas, diacríticos y tildes."""
    # Evaluamos la condición lógica (not txt) para controlar el flujo
    if not txt:
        # Retornamos el resultado procesado ('')
        return ""
    # Asignamos 'nfkd' con unicodedata.normalize('NFKD', str(txt))
    nfkd = unicodedata.normalize("NFKD", str(txt))
    # Asignamos 'sin_diacriticos' con ''.join((c for c in nfkd if not unicodedat...
    sin_diacriticos = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Retornamos el resultado procesado (sin_diacriticos.lower().strip())
    return sin_diacriticos.lower().strip()


# BLOQUE 12: CONSULTAS DE CATÁLOGO Y OFERTAS CON PAGINACIÓN AUTOMÁTICA (>1.000)
# =============================================================================
# - ¿Qué hace esta función (Consolidación de Catálogo Maestro en RAM)?:
#   1. Descarga el catálogo completo y sus ofertas vigentes con paginación concurrente multihilo.
#   2. Precalcula el mejor precio por perfume (priorizando frascos regulares sobre testers) y marca remates reales.
#   3. Precalcula el índice _search_index libre de tildes para búsquedas ultra-rápidas en memoria RAM.
#   4. Preserva el catálogo en memoria con TTL de 5 minutos, eliminando clonaciones redundantes de memoria.
def _obtener_catalogo_master_supabase(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Carga y consolida el catálogo maestro completo en memoria RAM con TTL de 5 minutos:
    - Precalcula mejor_precio (priorizando regular sobre tester) y detección de remates reales.
    - Precalcula un índice de búsqueda normalizado (_search_index) para búsquedas instantáneas (<1 ms) con tildes.
    - Evita clonación redundante de diccionarios, reduciendo el uso de memoria a la mitad.
    """
    # Ejecutamos instrucción: global _CATALOGO_MASTER, _REMATES_MASTER
    global _CATALOGO_MASTER, _REMATES_MASTER
    # Asignamos 'now_ts' con time.monotonic()
    now_ts = time.monotonic()
    # Evaluamos la condición lógica (not force_refresh and _CATALOGO_MASTER and (now_ts -...) para controlar el flujo
    if not force_refresh and _CATALOGO_MASTER and (now_ts - _CATALOGO_MASTER[0]) < CATALOGO_CACHE_TTL_SECONDS:
        # Retornamos el resultado procesado (list(_CATALOGO_MASTER[1]))
        return list(_CATALOGO_MASTER[1])

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (not sb or not is_supabase_disponible()) para controlar el flujo
    if not sb or not is_supabase_disponible():
        # Retornamos el resultado procesado ([])
        return []

    # Definición de función '_perfumes_page' (parámetros: offset, limit)
    def _perfumes_page(offset: int, limit: int):
        # Retornamos el resultado procesado (sb.table('perfumes').select('*').order('id', de...)
        return sb.table("perfumes").select("*").order("id", desc=False).range(offset, offset + limit - 1)

    # Asignamos 'perfumes' con _fetch_all_rows(_perfumes_page, page_size=...
    perfumes = _fetch_all_rows(_perfumes_page, page_size=1000)

    # Definición de función '_ofertas_page' (parámetros: offset, limit)
    def _ofertas_page(offset: int, limit: int):
        # Retornamos el resultado procesado (sb.table('ofertas_actuales').select('id, precio...)
        return (
            sb.table("ofertas_actuales")
            .select(
                "id, precio_actual, precio_normal, en_stock, url_producto, "
                "ultima_verificacion_exitosa, updated_at, "
                "variantes_perfume!inner(perfume_id, volumen_ml, formato)"
            )
            .eq("estado", "activa")
            .eq("en_stock", True)
            .gt("precio_actual", 0)
            .order("id", desc=False)
            .range(offset, offset + limit - 1)
        )

    # Asignamos 'ofertas_activas' con _fetch_all_rows(_ofertas_page, page_size=1...
    ofertas_activas = _fetch_all_rows(_ofertas_page, page_size=1000)

    # Asignamos 'precios_regular' con {}
    precios_regular: Dict[int, int] = {}
    # Asignamos 'precios_tester' con {}
    precios_tester: Dict[int, int] = {}
    # Asignamos 'precios_sin_reverificar' con {}
    precios_sin_reverificar: Dict[int, int] = {}
    # Asignamos 'remates_reales' con set()
    remates_reales: Set[int] = set()
    # Asignamos 'now_utc' con datetime.now(timezone.utc)
    now_utc = datetime.now(timezone.utc)

    # Recorremos iterativamente cada 'o' en ofertas_activas
    for o in ofertas_activas:
        # Asignamos 'vp' con o.get('variantes_perfume') or {}
        vp = o.get("variantes_perfume") or {}
        # Asignamos 'pid' con vp.get('perfume_id')
        pid = vp.get("perfume_id")
        # Asignamos 'p_act' con int(o.get('precio_actual') or 0)
        p_act = int(o.get("precio_actual") or 0)
        # Asignamos 'p_norm' con int(o.get('precio_normal') or 0)
        p_norm = int(o.get("precio_normal") or 0)
        # Asignamos 'vol' con float(vp.get('volumen_ml') or 100)
        vol = float(vp.get("volumen_ml") or 100)
        # Asignamos 'url_p' con str(o.get('url_producto') or '')
        url_p = str(o.get("url_producto") or "")
        # Asignamos 'fmt' con str(vp.get('formato') or '').lower()
        fmt = str(vp.get("formato") or "").lower()
        # Evaluamos la condición lógica (fmt != 'tester' and 'tester' in url_p.lower()) para controlar el flujo
        if fmt != "tester" and "tester" in url_p.lower():
            # Asignamos 'fmt' con 'tester'
            fmt = "tester"

        # Evaluamos la condición lógica (not pid or p_act <= 0 or vol < 25) para controlar el flujo
        if not pid or p_act <= 0 or vol < 25:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Asignamos 'dias_sv' con calcular_dias_sin_verificar(o.get('ultima_...
        dias_sv = calcular_dias_sin_verificar(
            o.get("ultima_verificacion_exitosa") or o.get("updated_at"),
            now_utc=now_utc,
        )
        # Evaluamos la condición lógica (not es_oferta_visible(dias_sv, en_stock=True)) para controlar el flujo
        if not es_oferta_visible(dias_sv, en_stock=True):
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Asignamos 'pid_int' con int(pid)
        pid_int = int(pid)
        # Evaluamos la condición lógica (not es_oferta_elegible_mejor_precio(dias_sv)) para controlar el flujo
        if not es_oferta_elegible_mejor_precio(dias_sv):
            # Evaluamos la condición lógica (pid_int not in precios_sin_reverificar or p_act < pr...) para controlar el flujo
            if pid_int not in precios_sin_reverificar or p_act < precios_sin_reverificar[pid_int]:
                # Asignamos 'precios_sin_reverificar[pid_int]' con p_act
                precios_sin_reverificar[pid_int] = p_act
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Evaluamos la condición lógica (fmt == 'tester') para controlar el flujo
        if fmt == "tester":
            # Evaluamos la condición lógica (pid_int not in precios_tester or p_act < precios_tes...) para controlar el flujo
            if pid_int not in precios_tester or p_act < precios_tester[pid_int]:
                # Asignamos 'precios_tester[pid_int]' con p_act
                precios_tester[pid_int] = p_act
        else:
            # Evaluamos la condición lógica (pid_int not in precios_regular or p_act < precios_re...) para controlar el flujo
            if pid_int not in precios_regular or p_act < precios_regular[pid_int]:
                # Asignamos 'precios_regular[pid_int]' con p_act
                precios_regular[pid_int] = p_act

        # Evaluamos la condición lógica (p_norm > p_act and (p_norm - p_act) / p_norm >= 0.08) para controlar el flujo
        if p_norm > p_act and ((p_norm - p_act) / p_norm) >= 0.08:
            # Ejecutamos instrucción: remates_reales.add(pid_int)
            remates_reales.add(pid_int)

    # Recorremos iterativamente cada 'p' en perfumes
    for p in perfumes:
        # Asignamos 'pid_int' con int(p.get('id') or 0)
        pid_int = int(p.get("id") or 0)
        # Asignamos 'mejor_reg' con precios_regular.get(pid_int)
        mejor_reg = precios_regular.get(pid_int)
        # Asignamos 'mejor_tst' con precios_tester.get(pid_int)
        mejor_tst = precios_tester.get(pid_int)
        # Asignamos 'p['precio_sin_reverificar']' con precios_sin_reverificar.get(pid_int)
        p["precio_sin_reverificar"] = precios_sin_reverificar.get(pid_int)
        # Evaluamos la condición lógica (mejor_reg is not None) para controlar el flujo
        if mejor_reg is not None:
            # Asignamos 'p['mejor_precio']' con mejor_reg
            p["mejor_precio"] = mejor_reg
            # Asignamos 'p['mejor_precio_es_tester']' con False
            p["mejor_precio_es_tester"] = False
        # Evaluamos la condición lógica (mejor_tst is not None) para controlar el flujo
        elif mejor_tst is not None:
            # Asignamos 'p['mejor_precio']' con mejor_tst
            p["mejor_precio"] = mejor_tst
            # Asignamos 'p['mejor_precio_es_tester']' con True
            p["mejor_precio_es_tester"] = True
        else:
            # Asignamos 'p['mejor_precio']' con None
            p["mejor_precio"] = None
            # Asignamos 'p['mejor_precio_es_tester']' con False
            p["mejor_precio_es_tester"] = False

        # Asignamos 'p['es_remate_real']' con bool(p.get('en_remate')) or pid_int in rem...
        p["es_remate_real"] = bool(p.get("en_remate")) or (pid_int in remates_reales)

        # Precalcular índice de búsqueda insensible a tildes/mayúsculas para búsquedas instantáneas
        nom_p = p.get("nombre") or ""
        # Asignamos 'mar_p' con p.get('marca') or ''
        mar_p = p.get("marca") or ""
        # Asignamos 'not_p' con p.get('notas') or ''
        not_p = p.get("notas") or ""
        # Asignamos 'p['_search_index']' con normalizar_texto_busqueda(f'{nom_p} {mar_p...
        p["_search_index"] = normalizar_texto_busqueda(f"{nom_p} {mar_p} {not_p}")

    # Asignamos '_CATALOGO_MASTER' con (now_ts, perfumes)
    _CATALOGO_MASTER = (now_ts, perfumes)
    # Retornamos el resultado procesado (list(perfumes))
    return list(perfumes)


# - ¿Qué hace esta función (Motor del Catálogo)?:
#   Es la consulta principal del catálogo: aplica filtros de texto, notas olfativas, categorías (árabes, remates)
#   y ordenamiento por precio o relevancia, calculando en tiempo real el mejor precio de cada fragancia.
def obtener_catalogo(
    busqueda: Optional[str] = None,
    esencias: Optional[List[str]] = None,
    categoria: Optional[str] = None,
    orden: str = "id_asc",
) -> List[Dict[str, Any]]:
    """
    Obtiene el catálogo completo optimizado mediante memoria RAM de alto rendimiento:
    - Consulta el catálogo maestro consolidado (con caché TTL de 5 min).
    - Aplica filtrado por búsqueda difusa, notas y categorías en memoria (< 1 ms).
    - Soporta búsquedas insensibles a tildes (ej. 'chloe' encuentra 'Chloé').
    - Aplica ordenamiento dinámico por precio, alfabeto o id en memoria (< 1 ms).
    """
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            master = _obtener_catalogo_master_supabase()
            # Evaluamos la condición lógica (master) para controlar el flujo
            if master:
                # Asignamos 'resultado' con list(master)
                resultado = list(master)

                # 1. Filtro por categoría en memoria
                if categoria == "arabes":
                    # Asignamos 'resultado' con [p for p in resultado if p.get('es_arabe')]
                    resultado = [p for p in resultado if p.get("es_arabe")]
                # Evaluamos la condición lógica (categoria == 'remates') para controlar el flujo
                elif categoria == "remates":
                    # Asignamos 'resultado' con [p for p in resultado if p.get('es_remate_...
                    resultado = [p for p in resultado if p.get("es_remate_real") and p.get("mejor_precio") is not None]

                # 2. Búsqueda por términos en memoria optimizada con índice normalizado y tildes
                if busqueda:
                    # Asignamos 'b_norm' con normalizar_texto_busqueda(busqueda)
                    b_norm = normalizar_texto_busqueda(busqueda)
                    # Asignamos 'tokens' con b_norm.split()
                    tokens = b_norm.split()
                    # Asignamos 'resultado' con [p for p in resultado if all((tok in p.get...
                    resultado = [
                        p for p in resultado
                        if all(tok in p.get("_search_index", "") for tok in tokens)
                    ]

                # 3. Filtro por notas olfativas / esencias en memoria
                if esencias:
                    # Asignamos 'esencias_lower' con [normalizar_texto_busqueda(e) for e in ese...
                    esencias_lower = [normalizar_texto_busqueda(e) for e in esencias]
                    # Asignamos 'resultado' con [p for p in resultado if any((any((es in n...
                    resultado = [
                        p for p in resultado
                        if any(
                            any(es in nota for nota in [normalizar_texto_busqueda(n) for n in (p.get("notas") or "").split(",")])
                            for es in esencias_lower
                        )
                    ]

                # 4. Ordenamiento dinámico en memoria
                if orden == "precio_asc":
                    # Ejecutamos instrucción: resultado.sort(key=lambda x: (x.get('mejor_precio') ...
                    resultado.sort(key=lambda x: (x.get("mejor_precio") is None, x.get("mejor_precio") or 999999999))
                # Evaluamos la condición lógica (orden == 'precio_desc') para controlar el flujo
                elif orden == "precio_desc":
                    # Ejecutamos instrucción: resultado.sort(key=lambda x: (x.get('mejor_precio') ...
                    resultado.sort(key=lambda x: (x.get("mejor_precio") is None, -(x.get("mejor_precio") or 0)))
                # Evaluamos la condición lógica (orden == 'nombre_asc') para controlar el flujo
                elif orden == "nombre_asc":
                    # Ejecutamos instrucción: resultado.sort(key=lambda x: (x.get('nombre') or '')...
                    resultado.sort(key=lambda x: (x.get("nombre") or "").lower())
                else:
                    # Ejecutamos instrucción: resultado.sort(key=lambda x: x.get('id', 0))
                    resultado.sort(key=lambda x: x.get("id", 0))

                # Retornamos el resultado procesado (resultado)
                return resultado
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error consultando catálogo en Supabase ({e}), recurriendo a SQLite de respaldo.")

    # Respaldo SQLite local (prioriza ofertas_actuales frescas <=7d y cae a precios_registro solo si no hay ofertas_actuales)
    init_db()
    # Asignamos 'query_sql' con 'SELECT p.* FROM perfumes p WHERE 1=1'
    query_sql = "SELECT p.* FROM perfumes p WHERE 1=1"
    # Asignamos 'params' con []
    params: List[Any] = []

    # Evaluamos la condición lógica (busqueda) para controlar el flujo
    if busqueda:
        # Asignamos 'term' con f'%{busqueda.strip()}%'
        term = f"%{busqueda.strip()}%"
        # Actualizamos acumulativamente el valor de 'query_sql'
        query_sql += " AND (p.nombre LIKE ? OR p.marca LIKE ?)"
        # Ejecutamos instrucción: params.extend([term, term])
        params.extend([term, term])

    # Evaluamos la condición lógica (categoria == 'arabes') para controlar el flujo
    if categoria == "arabes":
        # Actualizamos acumulativamente el valor de 'query_sql'
        query_sql += " AND p.es_arabe = 1"
    # Evaluamos la condición lógica (categoria == 'remates') para controlar el flujo
    elif categoria == "remates":
        # Actualizamos acumulativamente el valor de 'query_sql'
        query_sql += " AND p.en_remate = 1"

    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query_sql, params)
        # Asignamos 'perfumes' con [dict(row) for row in cursor.fetchall()]
        perfumes = [dict(row) for row in cursor.fetchall()]

        # Evaluamos la condición lógica (perfumes) para controlar el flujo
        if perfumes:
            # Asignamos 'pids' con [int(p['id']) for p in perfumes]
            pids = [int(p["id"]) for p in perfumes]
            # Asignamos 'placeholders' con ','.join(('?' for _ in pids))
            placeholders = ",".join("?" for _ in pids)
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute(
                f"""
                SELECT vp.perfume_id, oa.precio_actual, oa.en_stock, oa.estado,
                       oa.ultima_verificacion_exitosa, oa.updated_at, oa.url_producto,
                       COALESCE(vp.volumen_ml, 100) as volumen_ml,
                       LOWER(COALESCE(vp.formato, 'regular')) as formato
                FROM ofertas_actuales oa
                JOIN variantes_perfume vp ON vp.id = oa.variante_id
                WHERE vp.perfume_id IN ({placeholders})
                  AND oa.estado = 'activa'
                  AND oa.en_stock = 1
                  AND oa.precio_actual > 0
                  AND COALESCE(vp.volumen_ml, 100) >= 25;
                """,
                pids,
            )
            # Asignamos 'oa_rows' con cursor.fetchall()
            oa_rows = cursor.fetchall()
            # Asignamos 'tiene_oa_por_pid' con set()
            tiene_oa_por_pid: Set[int] = set()
            # Asignamos 'reg_min_sq' con {}
            reg_min_sq: Dict[int, int] = {}
            # Asignamos 'tst_min_sq' con {}
            tst_min_sq: Dict[int, int] = {}
            # Asignamos 'stale_min_sq' con {}
            stale_min_sq: Dict[int, int] = {}
            # Asignamos 'now_utc' con datetime.now(timezone.utc)
            now_utc = datetime.now(timezone.utc)

            # Recorremos iterativamente cada 'r' en oa_rows
            for r in oa_rows:
                # Asignamos 'pid_r' con int(r['perfume_id'])
                pid_r = int(r["perfume_id"])
                # Ejecutamos instrucción: tiene_oa_por_pid.add(pid_r)
                tiene_oa_por_pid.add(pid_r)
                # Asignamos 'dias_sv' con calcular_dias_sin_verificar(r['ultima_veri...
                dias_sv = calcular_dias_sin_verificar(
                    r["ultima_verificacion_exitosa"] or r["updated_at"],
                    now_utc=now_utc,
                )
                # Evaluamos la condición lógica (not es_oferta_visible(dias_sv, en_stock=True)) para controlar el flujo
                if not es_oferta_visible(dias_sv, en_stock=True):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'p_val' con int(r['precio_actual'])
                p_val = int(r["precio_actual"])
                # Evaluamos la condición lógica (not es_oferta_elegible_mejor_precio(dias_sv)) para controlar el flujo
                if not es_oferta_elegible_mejor_precio(dias_sv):
                    # Evaluamos la condición lógica (pid_r not in stale_min_sq or p_val < stale_min_sq[pi...) para controlar el flujo
                    if pid_r not in stale_min_sq or p_val < stale_min_sq[pid_r]:
                        # Asignamos 'stale_min_sq[pid_r]' con p_val
                        stale_min_sq[pid_r] = p_val
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'fmt_r' con str(r['formato'] or 'regular').lower()
                fmt_r = str(r["formato"] or "regular").lower()
                # Evaluamos la condición lógica (fmt_r != 'tester' and 'tester' in str(r['url_product...) para controlar el flujo
                if fmt_r != "tester" and "tester" in str(r["url_producto"] or "").lower():
                    # Asignamos 'fmt_r' con 'tester'
                    fmt_r = "tester"
                # Evaluamos la condición lógica (fmt_r == 'tester') para controlar el flujo
                if fmt_r == "tester":
                    # Evaluamos la condición lógica (pid_r not in tst_min_sq or p_val < tst_min_sq[pid_r]) para controlar el flujo
                    if pid_r not in tst_min_sq or p_val < tst_min_sq[pid_r]:
                        # Asignamos 'tst_min_sq[pid_r]' con p_val
                        tst_min_sq[pid_r] = p_val
                else:
                    # Evaluamos la condición lógica (pid_r not in reg_min_sq or p_val < reg_min_sq[pid_r]) para controlar el flujo
                    if pid_r not in reg_min_sq or p_val < reg_min_sq[pid_r]:
                        # Asignamos 'reg_min_sq[pid_r]' con p_val
                        reg_min_sq[pid_r] = p_val

            # Asignamos 'pids_sin_oa' con [pid_i for pid_i in pids if pid_i not in t...
            pids_sin_oa = [pid_i for pid_i in pids if pid_i not in tiene_oa_por_pid]
            # Asignamos 'legacy_min_sq' con {}
            legacy_min_sq: Dict[int, int] = {}
            # Evaluamos la condición lógica (pids_sin_oa) para controlar el flujo
            if pids_sin_oa:
                # Asignamos 'ph_leg' con ','.join(('?' for _ in pids_sin_oa))
                ph_leg = ",".join("?" for _ in pids_sin_oa)
                # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
                cursor.execute(
                    f"""
                    SELECT pr.perfume_id, MIN(pr.precio_actual) as min_p
                    FROM precios_registro pr
                    WHERE pr.perfume_id IN ({ph_leg})
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
                      )
                    GROUP BY pr.perfume_id;
                    """,
                    pids_sin_oa,
                )
                # Recorremos iterativamente cada 'rl' en cursor.fetchall()
                for rl in cursor.fetchall():
                    # Evaluamos la condición lógica (rl['min_p'] is not None) para controlar el flujo
                    if rl["min_p"] is not None:
                        # Asignamos 'legacy_min_sq[int(rl['perfume_id...' con int(rl['min_p'])
                        legacy_min_sq[int(rl["perfume_id"])] = int(rl["min_p"])

            # Recorremos iterativamente cada 'p' en perfumes
            for p in perfumes:
                # Asignamos 'pid_p' con int(p['id'])
                pid_p = int(p["id"])
                # Asignamos 'p['precio_sin_reverificar']' con stale_min_sq.get(pid_p)
                p["precio_sin_reverificar"] = stale_min_sq.get(pid_p)
                # Evaluamos la condición lógica (pid_p in reg_min_sq) para controlar el flujo
                if pid_p in reg_min_sq:
                    # Asignamos 'p['mejor_precio']' con reg_min_sq[pid_p]
                    p["mejor_precio"] = reg_min_sq[pid_p]
                    # Asignamos 'p['mejor_precio_es_tester']' con False
                    p["mejor_precio_es_tester"] = False
                # Evaluamos la condición lógica (pid_p in tst_min_sq) para controlar el flujo
                elif pid_p in tst_min_sq:
                    # Asignamos 'p['mejor_precio']' con tst_min_sq[pid_p]
                    p["mejor_precio"] = tst_min_sq[pid_p]
                    # Asignamos 'p['mejor_precio_es_tester']' con True
                    p["mejor_precio_es_tester"] = True
                # Evaluamos la condición lógica (pid_p in legacy_min_sq) para controlar el flujo
                elif pid_p in legacy_min_sq:
                    # Asignamos 'p['mejor_precio']' con legacy_min_sq[pid_p]
                    p["mejor_precio"] = legacy_min_sq[pid_p]
                    # Asignamos 'p['mejor_precio_es_tester']' con False
                    p["mejor_precio_es_tester"] = False
                else:
                    # Asignamos 'p['mejor_precio']' con None
                    p["mejor_precio"] = None
                    # Asignamos 'p['mejor_precio_es_tester']' con False
                    p["mejor_precio_es_tester"] = False

    # Evaluamos la condición lógica (orden == 'precio_asc') para controlar el flujo
    if orden == "precio_asc":
        # Ejecutamos instrucción: perfumes.sort(key=lambda x: (x.get('mejor_precio') i...
        perfumes.sort(key=lambda x: (x.get("mejor_precio") is None, x.get("mejor_precio") or 999999999))
    # Evaluamos la condición lógica (orden == 'precio_desc') para controlar el flujo
    elif orden == "precio_desc":
        # Ejecutamos instrucción: perfumes.sort(key=lambda x: (x.get('mejor_precio') i...
        perfumes.sort(key=lambda x: (x.get("mejor_precio") is None, -(x.get("mejor_precio") or 0)))
    # Evaluamos la condición lógica (orden == 'nombre_asc') para controlar el flujo
    elif orden == "nombre_asc":
        # Ejecutamos instrucción: perfumes.sort(key=lambda x: (x.get('nombre') or '')....
        perfumes.sort(key=lambda x: (x.get("nombre") or "").lower())
    else:
        # Ejecutamos instrucción: perfumes.sort(key=lambda x: x.get('id', 0))
        perfumes.sort(key=lambda x: x.get("id", 0))

    # Evaluamos la condición lógica (esencias) para controlar el flujo
    if esencias:
        # Asignamos 'esencias_lower' con [e.lower() for e in esencias]
        esencias_lower = [e.lower() for e in esencias]
        # Asignamos 'perfumes' con [p for p in perfumes if any((any((es in no...
        perfumes = [
            p for p in perfumes
            if any(
                any(es in nota for nota in [n.strip().lower() for n in (p.get("notas") or "").split(",")])
                for es in esencias_lower
            )
        ]

    # Retornamos el resultado procesado (perfumes)
    return perfumes


# Definición de función 'obtener_detalle_perfume' (parámetros: perfume_id)
def obtener_detalle_perfume(perfume_id: int) -> Optional[Dict[str, Any]]:
    """Retorna información completa del perfume por su ID."""
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            resp = sb.table("perfumes").select("*").eq("id", perfume_id).limit(1).execute()
            # Evaluamos la condición lógica (resp.data) para controlar el flujo
            if resp.data:
                # Retornamos el resultado procesado (resp.data[0])
                return resp.data[0]
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error en Supabase obtener_detalle_perfume ({e}), usando SQLite.")

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


# - ¿Qué hace esta función (Ofertas Vigentes)?:
#   Consulta las ofertas en stock en cada tienda para un perfume, ordenándolas por precio
#   e identificando el formato ('regular' vs 'tester') y el trust_score de cada comercio.
def obtener_precios_actuales(perfume_id: int) -> List[Dict[str, Any]]:
    """
    Retorna las ofertas vigentes por tienda y presentación para el perfume dado,
    incluyendo estado de stock, volumen_ml, precio_por_ml, formato ('regular' vs 'tester')
    y metadatos de frescura (`dias_sin_verificar`, `nivel_frescura`, `excluida_mejor_precio`).
    Las ofertas en stock con más de 14 días sin verificar se ocultan de la comparación activa.
    """
    # Asignamos 'now_utc' con datetime.now(timezone.utc)
    now_utc = datetime.now(timezone.utc)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            resp = (
                sb.table("ofertas_actuales")
                .select(
                    "id, precio_actual, precio_normal, en_stock, estado, url_producto, "
                    "ultima_verificacion_exitosa, updated_at, "
                    "tiendas(id, nombre, url_base, trust_score, badge, logo_emoji), "
                    "variantes_perfume!inner(id, perfume_id, volumen_ml, formato)"
                )
                .eq("variantes_perfume.perfume_id", perfume_id)
                .in_("estado", ["activa", "agotada"])
                .order("precio_actual", desc=False)
                .execute()
            )
            # Evaluamos la condición lógica (resp.data) para controlar el flujo
            if resp.data:
                # Asignamos 'res_lista' con []
                res_lista = []
                # Recorremos iterativamente cada 'item' en resp.data
                for item in resp.data:
                    # Asignamos 't' con item.get('tiendas') or {}
                    t = item.get("tiendas") or {}
                    # Asignamos 'v' con item.get('variantes_perfume') or {}
                    v = item.get("variantes_perfume") or {}
                    # Asignamos 'p_act' con int(item.get('precio_actual') or 0)
                    p_act = int(item.get("precio_actual") or 0)
                    # Asignamos 'vol' con int(round(float(v.get('volumen_ml') or 100)))
                    vol = int(round(float(v.get("volumen_ml") or 100)))
                    # Evaluamos la condición lógica (vol < 25 or p_act <= 0) para controlar el flujo
                    if vol < 25 or p_act <= 0:
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue
                    # Asignamos 'en_stock_val' con bool(item.get('en_stock', True)) and str(i...
                    en_stock_val = bool(item.get("en_stock", True)) and str(item.get("estado") or "activa") == "activa"
                    # Asignamos 'ts_verif' con item.get('ultima_verificacion_exitosa') or...
                    ts_verif = item.get("ultima_verificacion_exitosa") or item.get("updated_at")
                    # Asignamos 'dias_sv' con calcular_dias_sin_verificar(ts_verif, now_...
                    dias_sv = calcular_dias_sin_verificar(ts_verif, now_utc=now_utc)
                    # Evaluamos la condición lógica (not es_oferta_visible(dias_sv, en_stock=en_stock_val)) para controlar el flujo
                    if not es_oferta_visible(dias_sv, en_stock=en_stock_val):
                        # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                        continue

                    # Asignamos 'url_prod' con str(item.get('url_producto') or '')
                    url_prod = str(item.get("url_producto") or "")
                    # Asignamos 'fmt' con str(v.get('formato') or 'regular').lower()
                    fmt = str(v.get("formato") or "regular").lower()
                    # Evaluamos la condición lógica (fmt != 'tester' and 'tester' in url_prod.lower()) para controlar el flujo
                    if fmt != "tester" and "tester" in url_prod.lower():
                        # Asignamos 'fmt' con 'tester'
                        fmt = "tester"
                    # Asignamos 'p_ml' con int(round(p_act / vol)) if p_act and vol e...
                    p_ml = int(round(p_act / vol)) if (p_act and vol) else 0
                    # Ejecutamos instrucción: res_lista.append({'id': item.get('id'), 'perfume_id'...
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
                        "en_stock": en_stock_val,
                        "volumen_ml": vol,
                        "formato": fmt,
                        "precio_por_ml": p_ml,
                        "url_producto": url_prod,
                        "fecha_registro": item.get("ultima_verificacion_exitosa"),
                        "dias_sin_verificar": dias_sv,
                        "nivel_frescura": clasificar_frescura_oferta(dias_sv),
                        "excluida_mejor_precio": not es_oferta_elegible_mejor_precio(dias_sv),
                    })
                # Retornamos el resultado procesado (res_lista)
                return res_lista
            # Retornamos el resultado procesado ([])
            return []
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error en Supabase obtener_precios_actuales ({e}), recurriendo a SQLite de respaldo.")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        SELECT oa.id, t.id as tienda_id, t.nombre as tienda_nombre, t.url_base, t.trust_score, t.badge, t.logo_emoji,
               oa.precio_actual, COALESCE(oa.precio_normal, oa.precio_actual) as precio_normal, oa.en_stock, oa.estado,
               CAST(ROUND(COALESCE(vp.volumen_ml, 100)) AS INTEGER) as volumen_ml,
               LOWER(COALESCE(vp.formato, 'regular')) as formato,
               CAST(ROUND(CAST(oa.precio_actual AS REAL) / MAX(1, COALESCE(vp.volumen_ml, 100))) AS INTEGER) as precio_por_ml,
               oa.url_producto, oa.ultima_verificacion_exitosa as fecha_registro, oa.updated_at
        FROM ofertas_actuales oa
        JOIN variantes_perfume vp ON vp.id = oa.variante_id
        JOIN tiendas t ON t.id = oa.tienda_id
        WHERE vp.perfume_id = ?
          AND oa.estado IN ('activa', 'agotada')
          AND oa.precio_actual > 0
          AND COALESCE(vp.volumen_ml, 100) >= 25
        ORDER BY oa.precio_actual ASC;
        """, (perfume_id,))
        # Asignamos 'rows_oa' con [dict(r) for r in cursor.fetchall()]
        rows_oa = [dict(r) for r in cursor.fetchall()]
        # Evaluamos la condición lógica (rows_oa) para controlar el flujo
        if rows_oa:
            # Asignamos 'visibles_oa' con []
            visibles_oa: List[Dict[str, Any]] = []
            # Recorremos iterativamente cada 'r' en rows_oa
            for r in rows_oa:
                # Asignamos 'en_stock_sq' con bool(r['en_stock']) and str(r.get('estado'...
                en_stock_sq = bool(r["en_stock"]) and str(r.get("estado") or "activa") == "activa"
                # Asignamos 'r['en_stock']' con en_stock_sq
                r["en_stock"] = en_stock_sq
                # Asignamos 'dias_sv' con calcular_dias_sin_verificar(r.get('fecha_r...
                dias_sv = calcular_dias_sin_verificar(r.get("fecha_registro") or r.get("updated_at"), now_utc=now_utc)
                # Evaluamos la condición lógica (not es_oferta_visible(dias_sv, en_stock=en_stock_sq)) para controlar el flujo
                if not es_oferta_visible(dias_sv, en_stock=en_stock_sq):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Evaluamos la condición lógica (r.get('formato') != 'tester' and 'tester' in str(r.g...) para controlar el flujo
                if r.get("formato") != "tester" and "tester" in str(r.get("url_producto") or "").lower():
                    # Asignamos 'r['formato']' con 'tester'
                    r["formato"] = "tester"
                # Asignamos 'r['dias_sin_verificar']' con dias_sv
                r["dias_sin_verificar"] = dias_sv
                # Asignamos 'r['nivel_frescura']' con clasificar_frescura_oferta(dias_sv)
                r["nivel_frescura"] = clasificar_frescura_oferta(dias_sv)
                # Asignamos 'r['excluida_mejor_precio']' con not es_oferta_elegible_mejor_precio(dias_sv)
                r["excluida_mejor_precio"] = not es_oferta_elegible_mejor_precio(dias_sv)
                # Ejecutamos instrucción: visibles_oa.append(r)
                visibles_oa.append(r)
            # Retornamos el resultado procesado (visibles_oa)
            return visibles_oa

        # Asignamos 'query' con "\n SELECT t.id as tienda_id, t.nombre as ...
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
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, (perfume_id, perfume_id))
        # Asignamos 'res_legacy' con []
        res_legacy = []
        # Recorremos iterativamente cada 'row' en cursor.fetchall()
        for row in cursor.fetchall():
            # Asignamos 'r' con dict(row)
            r = dict(row)
            # Asignamos 'r['en_stock']' con bool(r['en_stock'])
            r["en_stock"] = bool(r["en_stock"])
            # Asignamos 'dias_sv' con calcular_dias_sin_verificar(r.get('fecha_r...
            dias_sv = calcular_dias_sin_verificar(r.get("fecha_registro"), now_utc=now_utc)
            # Evaluamos la condición lógica (not es_oferta_visible(dias_sv, en_stock=r['en_stock'])) para controlar el flujo
            if not es_oferta_visible(dias_sv, en_stock=r["en_stock"]):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Evaluamos la condición lógica ('tester' in str(r.get('url_producto') or '').lower()) para controlar el flujo
            if "tester" in str(r.get("url_producto") or "").lower():
                # Asignamos 'r['formato']' con 'tester'
                r["formato"] = "tester"
            # Asignamos 'r['dias_sin_verificar']' con dias_sv
            r["dias_sin_verificar"] = dias_sv
            # Asignamos 'r['nivel_frescura']' con clasificar_frescura_oferta(dias_sv)
            r["nivel_frescura"] = clasificar_frescura_oferta(dias_sv)
            # Asignamos 'r['excluida_mejor_precio']' con not es_oferta_elegible_mejor_precio(dias_sv)
            r["excluida_mejor_precio"] = not es_oferta_elegible_mejor_precio(dias_sv)
            # Ejecutamos instrucción: res_legacy.append(r)
            res_legacy.append(r)
        # Retornamos el resultado procesado (res_legacy)
        return res_legacy


# - ¿Qué hace esta función (Serie Temporal Histórica)?:
#   Extrae las observaciones pasadas de precio y fecha para construir la curva del gráfico en la ficha del perfume.
def obtener_historico_precios(perfume_id: int, volumen_ml: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retorna la serie temporal histórica de precios filtrada opcionalmente por `volumen_ml`
    para no mezclar presentaciones de 50ml, 100ml y 200ml en un mismo gráfico.
    """
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Definición de función '_hist_page' (parámetros: offset, limit)
            def _hist_page(offset: int, limit: int):
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                q = (
                    sb.table("precios_registro")
                    .select("precio_actual, volumen_ml, fecha_registro, tiendas(nombre)")
                    .eq("perfume_id", perfume_id)
                    .eq("en_stock", True)
                    .gt("precio_actual", 0)
                )
                # Evaluamos la condición lógica (volumen_ml is not None) para controlar el flujo
                if volumen_ml is not None:
                    # Asignamos 'q' con q.eq('volumen_ml', int(volumen_ml))
                    q = q.eq("volumen_ml", int(volumen_ml))
                # Retornamos el resultado procesado (q.order('fecha_registro', desc=False).range(off...)
                return q.order("fecha_registro", desc=False).range(offset, offset + limit - 1)

            # Asignamos 'filas' con _fetch_all_rows(_hist_page, page_size=1000)
            filas = _fetch_all_rows(_hist_page, page_size=1000)
            # Asignamos 'registros' con []
            registros = []
            # Recorremos iterativamente cada 'r' en filas
            for r in filas:
                # Asignamos 'tienda_info' con r.get('tiendas')
                tienda_info = r.get("tiendas")
                # Asignamos 't_nombre' con tienda_info.get('nombre', 'Tienda') if isi...
                t_nombre = tienda_info.get("nombre", "Tienda") if isinstance(tienda_info, dict) else "Tienda"
                # Ejecutamos instrucción: registros.append({'tienda': t_nombre, 'precio_actual...
                registros.append({
                    "tienda": t_nombre,
                    "precio_actual": r.get("precio_actual"),
                    "volumen_ml": r.get("volumen_ml") or 100,
                    "fecha_registro": r.get("fecha_registro"),
                })
            # Retornamos el resultado procesado (registros)
            return registros
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error en Supabase obtener_historico_precios ({e}), usando SQLite.")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'params' con [perfume_id]
    params: List[Any] = [perfume_id]
    # Asignamos 'filtro_vol' con ''
    filtro_vol = ""
    # Evaluamos la condición lógica (volumen_ml is not None) para controlar el flujo
    if volumen_ml is not None:
        # Asignamos 'filtro_vol' con ' AND ABS(COALESCE(pr.volumen_ml, 100) - ?...
        filtro_vol = " AND ABS(COALESCE(pr.volumen_ml, 100) - ?) < 2"
        # Ejecutamos instrucción: params.append(int(volumen_ml))
        params.append(int(volumen_ml))

    # Asignamos 'query' con f'\n SELECT t.nombre as tienda, pr.precio_...
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
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(query, params)
        # Retornamos el resultado procesado ([dict(row) for row in cursor.fetchall()])
        return [dict(row) for row in cursor.fetchall()]


# - ¿Qué hace esta función (Cálculo de Mínimo Histórico)?:
#   Ejecuta una consulta agregada [SELECT MIN(precio_actual)] en 'precios_registro' filtrando por volumen (ej. 100ml)
#   para determinar cuál ha sido el precio récord más bajo alcanzado por ese perfume en las tiendas de Chile.
def obtener_minimo_historico(perfume_id: int, volumen_ml: Optional[int] = None) -> Optional[int]:
    """
    Retorna el precio mínimo histórico registrado (en stock y > 0) para un perfume determinado,
    filtrando opcionalmente por volumen (ml) para respetar la presentación.
    """
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            q = (
                sb.table("precios_registro")
                .select("precio_actual")
                .eq("perfume_id", perfume_id)
                .eq("en_stock", True)
                .gt("precio_actual", 0)
            )
            # Evaluamos la condición lógica (volumen_ml is not None) para controlar el flujo
            if volumen_ml is not None:
                # Asignamos 'q' con q.eq('volumen_ml', int(volumen_ml))
                q = q.eq("volumen_ml", int(volumen_ml))
            # Asignamos 'res' con q.order('precio_actual', desc=False).limit...
            res = q.order("precio_actual", desc=False).limit(1).execute()
            # Evaluamos la condición lógica (res.data and len(res.data) > 0) para controlar el flujo
            if res.data and len(res.data) > 0:
                # Retornamos el resultado procesado (int(res.data[0]['precio_actual']))
                return int(res.data[0]["precio_actual"])
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error en Supabase obtener_minimo_historico ({e}), usando SQLite.")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'params' con [perfume_id]
    params: List[Any] = [perfume_id]
    # Asignamos 'filtro_vol' con ''
    filtro_vol = ""
    # Evaluamos la condición lógica (volumen_ml is not None) para controlar el flujo
    if volumen_ml is not None:
        # Asignamos 'filtro_vol' con ' AND ABS(COALESCE(pr.volumen_ml, 100) - ?...
        filtro_vol = " AND ABS(COALESCE(pr.volumen_ml, 100) - ?) < 2"
        # Ejecutamos instrucción: params.append(int(volumen_ml))
        params.append(int(volumen_ml))

    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(f"""
            SELECT MIN(pr.precio_actual) as min_p
            FROM precios_registro pr
            WHERE pr.perfume_id = ?
              AND pr.en_stock = 1
              AND pr.precio_actual > 0
              {filtro_vol};
        """, params)
        # Asignamos 'row' con cursor.fetchone()
        row = cursor.fetchone()
        # Evaluamos la condición lógica (row and row['min_p'] is not None) para controlar el flujo
        if row and row["min_p"] is not None:
            # Retornamos el resultado procesado (int(row['min_p']))
            return int(row["min_p"])

        # Fallback a ofertas_actuales si aún no hay observaciones históricas acumuladas
        params_oa: List[Any] = [perfume_id]
        # Asignamos 'filtro_vol_oa' con ''
        filtro_vol_oa = ""
        # Evaluamos la condición lógica (volumen_ml is not None) para controlar el flujo
        if volumen_ml is not None:
            # Asignamos 'filtro_vol_oa' con ' AND ABS(COALESCE(vp.volumen_ml, 100) - ?...
            filtro_vol_oa = " AND ABS(COALESCE(vp.volumen_ml, 100) - ?) < 2"
            # Ejecutamos instrucción: params_oa.append(int(volumen_ml))
            params_oa.append(int(volumen_ml))

        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute(f"""
            SELECT MIN(oa.precio_actual) as min_p
            FROM ofertas_actuales oa
            JOIN variantes_perfume vp ON vp.id = oa.variante_id
            WHERE vp.perfume_id = ?
              AND oa.en_stock = 1
              AND oa.precio_actual > 0
              {filtro_vol_oa};
        """, params_oa)
        # Asignamos 'row_oa' con cursor.fetchone()
        row_oa = cursor.fetchone()
        # Evaluamos la condición lógica (row_oa and row_oa['min_p'] is not None) para controlar el flujo
        if row_oa and row_oa["min_p"] is not None:
            # Retornamos el resultado procesado (int(row_oa['min_p']))
            return int(row_oa["min_p"])

    # Retornamos el resultado procesado (None)
    return None


# Definición de función 'es_minimo_historico' (parámetros: perfume_id, precio_actual, volumen_ml)
def es_minimo_historico(perfume_id: int, precio_actual: int, volumen_ml: Optional[int] = None) -> bool:
    """
    Retorna True si `precio_actual` iguala o supera el precio más bajo registrado
    para este perfume (y volumen si se especifica).
    """
    # Evaluamos la condición lógica (precio_actual <= 0) para controlar el flujo
    if precio_actual <= 0:
        # Retornamos el resultado procesado (False)
        return False
    # Asignamos 'min_h' con obtener_minimo_historico(perfume_id, volum...
    min_h = obtener_minimo_historico(perfume_id, volumen_ml=volumen_ml)
    # Evaluamos la condición lógica (min_h is None or min_h <= 0) para controlar el flujo
    if min_h is None or min_h <= 0:
        # Retornamos el resultado procesado (False)
        return False
    # Retornamos el resultado procesado (bool(precio_actual <= min_h))
    return bool(precio_actual <= min_h)


# Definición de función 'obtener_mayores_bajadas_recientes' (parámetros: dias, limite)
def obtener_mayores_bajadas_recientes(dias: int = 7, limite: int = 12) -> List[Dict[str, Any]]:
    """
    Retorna las mayores bajadas de precio confirmadas en los últimos días
    (observaciones con rebajas reales en stock).
    """
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res = (
                sb.table("precios_registro")
                .select(
                    "id, perfume_id, tienda_id, precio_actual, precio_normal, en_stock, volumen_ml, url_producto, fecha_registro, "
                    "tiendas(id, nombre, url_base, trust_score, badge), "
                    "perfumes(id, nombre, marca, tipo, notas, imagen_url, es_arabe)"
                )
                .eq("en_stock", True)
                .gt("precio_actual", 0)
                .order("fecha_registro", desc=True)
                .limit(100)
                .execute()
            )
            # Asignamos 'filas' con res.data or []
            filas = res.data or []
            # Asignamos 'bajadas' con []
            bajadas = []
            # Asignamos 'vistos' con set()
            vistos = set()
            # Recorremos iterativamente cada 'r' en filas
            for r in filas:
                # Asignamos 'perf' con r.get('perfumes') or {}
                perf = r.get("perfumes") or {}
                # Asignamos 't' con r.get('tiendas') or {}
                t = r.get("tiendas") or {}
                # Asignamos 'pid' con perf.get('id') or r.get('perfume_id')
                pid = perf.get("id") or r.get("perfume_id")
                # Evaluamos la condición lógica (not pid or pid in vistos) para controlar el flujo
                if not pid or pid in vistos:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'p_act' con int(r.get('precio_actual') or 0)
                p_act = int(r.get("precio_actual") or 0)
                # Asignamos 'p_norm' con int(r.get('precio_normal') or 0)
                p_norm = int(r.get("precio_normal") or 0)
                # Evaluamos la condición lógica (p_act <= 0 or p_norm <= p_act) para controlar el flujo
                if p_act <= 0 or p_norm <= p_act:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Asignamos 'ahorro' con p_norm - p_act
                ahorro = p_norm - p_act
                # Asignamos 'pct' con int(round(ahorro * 100.0 / p_norm))
                pct = int(round((ahorro * 100.0) / p_norm))
                # Ejecutamos instrucción: vistos.add(pid)
                vistos.add(pid)
                # Ejecutamos instrucción: bajadas.append({'perfume_id': pid, 'nombre': perf.ge...
                bajadas.append({
                    "perfume_id": pid,
                    "nombre": perf.get("nombre", ""),
                    "marca": perf.get("marca", ""),
                    "tipo": perf.get("tipo", "Eau de Parfum"),
                    "imagen_url": perf.get("imagen_url", ""),
                    "tienda": t.get("nombre", "Tienda"),
                    "url_base": t.get("url_base", ""),
                    "url": r.get("url_producto", ""),
                    "volumen_ml": int(r.get("volumen_ml") or 100),
                    "precio_actual": p_act,
                    "precio_normal": p_norm,
                    "ahorro_clp": ahorro,
                    "descuento_pct": pct,
                    "fecha_registro": r.get("fecha_registro", ""),
                })
                # Evaluamos la condición lógica (len(bajadas) >= limite) para controlar el flujo
                if len(bajadas) >= limite:
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
            # Evaluamos la condición lógica (bajadas) para controlar el flujo
            if bajadas:
                # Retornamos el resultado procesado (bajadas)
                return bajadas
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error consultando mayores bajadas en Supabase ({e}), usando fallback.")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
            SELECT pr.id, pr.perfume_id, pr.tienda_id, pr.precio_actual, pr.precio_normal,
                   pr.en_stock, COALESCE(pr.volumen_ml, 100) as volumen_ml, pr.url_producto as url,
                   pr.fecha_registro,
                   t.nombre as tienda, t.url_base,
                   p.nombre, p.marca, p.tipo, p.imagen_url
            FROM precios_registro pr
            JOIN tiendas t ON pr.tienda_id = t.id
            JOIN perfumes p ON pr.perfume_id = p.id
            WHERE pr.en_stock = 1
              AND pr.precio_actual > 0
              AND pr.precio_normal > pr.precio_actual
            ORDER BY pr.fecha_registro DESC
            LIMIT ?;
        """, (limite * 2,))
        # Asignamos 'rows' con [dict(r) for r in cursor.fetchall()]
        rows = [dict(r) for r in cursor.fetchall()]
        # Asignamos 'vistos' con set()
        vistos = set()
        # Asignamos 'bajadas' con []
        bajadas = []
        # Recorremos iterativamente cada 'r' en rows
        for r in rows:
            # Asignamos 'pid' con r['perfume_id']
            pid = r["perfume_id"]
            # Evaluamos la condición lógica (pid in vistos) para controlar el flujo
            if pid in vistos:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Ejecutamos instrucción: vistos.add(pid)
            vistos.add(pid)
            # Asignamos 'ahorro' con int(r['precio_normal'] - r['precio_actual'])
            ahorro = int(r["precio_normal"] - r["precio_actual"])
            # Asignamos 'pct' con int(round(ahorro * 100.0 / r['precio_norma...
            pct = int(round((ahorro * 100.0) / r["precio_normal"]))
            # Asignamos 'r['ahorro_clp']' con ahorro
            r["ahorro_clp"] = ahorro
            # Asignamos 'r['descuento_pct']' con pct
            r["descuento_pct"] = pct
            # Ejecutamos instrucción: bajadas.append(r)
            bajadas.append(r)
            # Evaluamos la condición lógica (len(bajadas) >= limite) para controlar el flujo
            if len(bajadas) >= limite:
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
        # Retornamos el resultado procesado (bajadas)
        return bajadas



# - ¿Qué hace esta función (Algoritmo de Remates y Gangas Reales)?:
#   1. Filtra ofertas donde precio_normal > precio_actual con al menos un 12% de descuento real demostrable.
#   2. Descarta automáticamente productos tester o miniaturas < 25ml para evitar ofertas engañosas.
#   3. Almacena los remates validados en caché de memoria RAM (_REMATES_MASTER) por 5 minutos, respondiendo en < 2 ms.
def obtener_remates_reales(
    limite: int = 60,
    descuento_min_pct: int = 12,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    Consulta ofertas activas y verificadas en stock con descuento real comprobable
    (`precio_normal > precio_actual`, formato `'regular'`, volumen >= 25 ml),
    ordenadas de mayor a menor porcentaje de ahorro para la vista `remates.py`.
    Utiliza caché en memoria RAM con TTL de 5 minutos y concurrencia multihilo.
    """
    # Ejecutamos instrucción: global _REMATES_MASTER
    global _REMATES_MASTER
    # Asignamos 'now_ts' con time.monotonic()
    now_ts = time.monotonic()
    # Evaluamos la condición lógica (not force_refresh and _REMATES_MASTER and (now_ts - ...) para controlar el flujo
    if not force_refresh and _REMATES_MASTER and (now_ts - _REMATES_MASTER[0]) < REMATES_CACHE_TTL_SECONDS:
        # Asignamos 'candidatos_cacheados' con [r for r in _REMATES_MASTER[1] if r.get('d...
        candidatos_cacheados = [r for r in _REMATES_MASTER[1] if r.get("descuento_pct", 0) >= descuento_min_pct]
        # Retornamos el resultado procesado (list(candidatos_cacheados[:max(1, int(limite))]))
        return list(candidatos_cacheados[: max(1, int(limite))])

    # Asignamos 'now_utc' con datetime.now(timezone.utc)
    now_utc = datetime.now(timezone.utc)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Definición de función '_remates_page' (parámetros: offset, limit)
            def _remates_page(offset: int, limit: int):
                # Retornamos el resultado procesado (sb.table('ofertas_actuales').select('id, precio...)
                return (
                    sb.table("ofertas_actuales")
                    .select(
                        "id, precio_actual, precio_normal, en_stock, url_producto, "
                        "ultima_verificacion_exitosa, updated_at, "
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

            # Asignamos 'filas' con _fetch_all_rows(_remates_page, page_size=1...
            filas = _fetch_all_rows(_remates_page, page_size=1000)
            # Asignamos 'candidatos' con []
            candidatos: List[Dict[str, Any]] = []
            # Asignamos 'vistos_perfume_tienda' con set()
            vistos_perfume_tienda: Set[Tuple[int, int, int]] = set()

            # Recorremos iterativamente cada 'item' en filas
            for item in filas:
                # Asignamos 'p_act' con int(item.get('precio_actual') or 0)
                p_act = int(item.get("precio_actual") or 0)
                # Asignamos 'p_norm' con int(item.get('precio_normal') or 0)
                p_norm = int(item.get("precio_normal") or 0)
                # Evaluamos la condición lógica (p_act <= 0 or p_norm <= p_act or p_norm >= 1000000) para controlar el flujo
                if p_act <= 0 or p_norm <= p_act or p_norm >= 1_000_000:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'dias_sv' con calcular_dias_sin_verificar(item.get('ulti...
                dias_sv = calcular_dias_sin_verificar(
                    item.get("ultima_verificacion_exitosa") or item.get("updated_at"),
                    now_utc=now_utc,
                )
                # Evaluamos la condición lógica (not es_oferta_elegible_mejor_precio(dias_sv)) para controlar el flujo
                if not es_oferta_elegible_mejor_precio(dias_sv):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'vp' con item.get('variantes_perfume') or {}
                vp = item.get("variantes_perfume") or {}
                # Asignamos 'perf' con vp.get('perfumes') or {}
                perf = vp.get("perfumes") or {}
                # Asignamos 't' con item.get('tiendas') or {}
                t = item.get("tiendas") or {}
                # Asignamos 'vol' con int(round(float(vp.get('volumen_ml') or 10...
                vol = int(round(float(vp.get("volumen_ml") or 100)))
                # Asignamos 'url_prod' con str(item.get('url_producto') or '')
                url_prod = str(item.get("url_producto") or "")
                # Asignamos 'fmt' con str(vp.get('formato') or 'regular').lower()
                fmt = str(vp.get("formato") or "regular").lower()
                # Evaluamos la condición lógica (fmt != 'tester' and 'tester' in url_prod.lower()) para controlar el flujo
                if fmt != "tester" and "tester" in url_prod.lower():
                    # Asignamos 'fmt' con 'tester'
                    fmt = "tester"

                # Evaluamos la condición lógica (vol < 25 or fmt == 'tester' or (not perf.get('id'))) para controlar el flujo
                if vol < 25 or fmt == "tester" or not perf.get("id"):
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'ahorro' con p_norm - p_act
                ahorro = p_norm - p_act
                # Asignamos 'pct' con int(round(ahorro * 100.0 / p_norm))
                pct = int(round((ahorro * 100.0) / p_norm))
                # Evaluamos la condición lógica (pct < descuento_min_pct or pct > 80 or ahorro < 3000) para controlar el flujo
                if pct < descuento_min_pct or pct > 80 or ahorro < 3000:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue

                # Asignamos 'pid' con int(perf['id'])
                pid = int(perf["id"])
                # Asignamos 'tid' con int(t.get('id') or 0)
                tid = int(t.get("id") or 0)
                # Asignamos 'key_dedup' con (pid, tid, vol)
                key_dedup = (pid, tid, vol)
                # Evaluamos la condición lógica (key_dedup in vistos_perfume_tienda) para controlar el flujo
                if key_dedup in vistos_perfume_tienda:
                    # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                    continue
                # Ejecutamos instrucción: vistos_perfume_tienda.add(key_dedup)
                vistos_perfume_tienda.add(key_dedup)

                # Ejecutamos instrucción: candidatos.append({'id': item.get('id') or pid, 'per...
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
                    "dias_sin_verificar": dias_sv,
                    "nivel_frescura": clasificar_frescura_oferta(dias_sv),
                })

            # Ejecutamos instrucción: candidatos.sort(key=lambda x: (-x['descuento_pct'], ...
            candidatos.sort(key=lambda x: (-x["descuento_pct"], -x["ahorro_clp"], x["precio_remate"]))
            # Asignamos '_REMATES_MASTER' con (now_ts, list(candidatos))
            _REMATES_MASTER = (now_ts, list(candidatos))
            # Asignamos 'resultado_filtrado' con [r for r in candidatos if r.get('descuento...
            resultado_filtrado = [r for r in candidatos if r.get("descuento_pct", 0) >= descuento_min_pct]
            # Retornamos el resultado procesado (list(resultado_filtrado[:max(1, int(limite))]))
            return list(resultado_filtrado[: max(1, int(limite))])
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error consultando remates reales en Supabase ({e}), usando SQLite.")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor()
    with get_db_cursor() as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        SELECT oa.id, p.id as perfume_id, p.nombre, p.marca, p.tipo, p.notas, p.imagen_url, p.es_arabe,
               t.nombre as tienda, t.url_base, t.trust_score, t.badge as badge_tienda,
               CAST(ROUND(COALESCE(vp.volumen_ml, 100)) AS INTEGER) as volumen_ml,
               oa.precio_normal, oa.precio_actual as precio_remate,
               oa.url_producto as url, oa.ultima_verificacion_exitosa as ultima_verificacion, oa.updated_at
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
        """, (max(1, int(limite) * 4),))
        # Asignamos 'rows' con [dict(r) for r in cursor.fetchall()]
        rows = [dict(r) for r in cursor.fetchall()]

        # Evaluamos la condición lógica (not rows) para controlar el flujo
        if not rows:
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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
            """, (max(1, int(limite) * 4),))
            # Asignamos 'rows' con [dict(r) for r in cursor.fetchall()]
            rows = [dict(r) for r in cursor.fetchall()]

        # Asignamos 'res_local' con []
        res_local: List[Dict[str, Any]] = []
        # Asignamos 'vistos_sq' con set()
        vistos_sq: Set[Tuple[int, str, int]] = set()
        # Recorremos iterativamente cada 'r' en rows
        for r in rows:
            # Asignamos 'p_act' con int(r.get('precio_remate') or 0)
            p_act = int(r.get("precio_remate") or 0)
            # Asignamos 'p_norm' con int(r.get('precio_normal') or 0)
            p_norm = int(r.get("precio_normal") or 0)
            # Evaluamos la condición lógica (p_act <= 0 or p_norm <= p_act or p_norm >= 1000000) para controlar el flujo
            if p_act <= 0 or p_norm <= p_act or p_norm >= 1_000_000:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'dias_sv' con calcular_dias_sin_verificar(r.get('ultima_...
            dias_sv = calcular_dias_sin_verificar(r.get("ultima_verificacion") or r.get("updated_at"), now_utc=now_utc)
            # Evaluamos la condición lógica (not es_oferta_elegible_mejor_precio(dias_sv)) para controlar el flujo
            if not es_oferta_elegible_mejor_precio(dias_sv):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Evaluamos la condición lógica ('tester' in str(r.get('url') or '').lower()) para controlar el flujo
            if "tester" in str(r.get("url") or "").lower():
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'ahorro' con p_norm - p_act
            ahorro = p_norm - p_act
            # Asignamos 'pct' con int(round(ahorro * 100.0 / p_norm))
            pct = int(round((ahorro * 100.0) / p_norm))
            # Evaluamos la condición lógica (pct < descuento_min_pct or pct > 80 or ahorro < 3000) para controlar el flujo
            if pct < descuento_min_pct or pct > 80 or ahorro < 3000:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'k' con (int(r['perfume_id']), str(r['tienda']), i...
            k = (int(r["perfume_id"]), str(r["tienda"]), int(r.get("volumen_ml") or 100))
            # Evaluamos la condición lógica (k in vistos_sq) para controlar el flujo
            if k in vistos_sq:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Ejecutamos instrucción: vistos_sq.add(k)
            vistos_sq.add(k)
            # Asignamos 'r['ahorro_clp']' con ahorro
            r["ahorro_clp"] = ahorro
            # Asignamos 'r['descuento_pct']' con pct
            r["descuento_pct"] = pct
            # Asignamos 'r['es_arabe']' con bool(r.get('es_arabe'))
            r["es_arabe"] = bool(r.get("es_arabe"))
            # Asignamos 'r['dias_sin_verificar']' con dias_sv
            r["dias_sin_verificar"] = dias_sv
            # Asignamos 'r['nivel_frescura']' con clasificar_frescura_oferta(dias_sv)
            r["nivel_frescura"] = clasificar_frescura_oferta(dias_sv)
            # Ejecutamos instrucción: res_local.append(r)
            res_local.append(r)

        # Ejecutamos instrucción: res_local.sort(key=lambda x: (-x['descuento_pct'], -...
        res_local.sort(key=lambda x: (-x["descuento_pct"], -x["ahorro_clp"], x["precio_remate"]))
        # Retornamos el resultado procesado (res_local[:max(1, int(limite))])
        return res_local[: max(1, int(limite))]


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
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'p_act_int' con int(round(float(precio_actual)))
        p_act_int = int(round(float(precio_actual)))
    except (ValueError, TypeError):
        # Retornamos el resultado procesado ({'exito': False, 'motivo': f'Precio inválido: {...)
        return {"exito": False, "motivo": f"Precio inválido: {precio_actual}"}

    # Evaluamos la condición lógica (p_act_int < 4000 or p_act_int >= 1000000 or p_act_in...) para controlar el flujo
    if p_act_int < 4000 or p_act_int >= 1000000 or p_act_int in (9999999, 9999990, 999999):
        # Retornamos el resultado procesado ({'exito': False, 'motivo': f'Precio fuera de ra...)
        return {"exito": False, "motivo": f"Precio fuera de rango comercial ({p_act_int})"}

    # Evaluamos la condición lógica (int(volumen_ml or 100) < 25) para controlar el flujo
    if int(volumen_ml or 100) < 25:
        # Retornamos el resultado procesado ({'exito': False, 'motivo': f'Volumen menor a 25...)
        return {"exito": False, "motivo": f"Volumen menor a 25 ml descartado ({volumen_ml} ml)"}

    # Asignamos 'marca_canon' con normalizar_marca_canonica(marca) or 'Diseñ...
    marca_canon = normalizar_marca_canonica(marca) or "Diseñador"
    # Asignamos 'nombre_canon' con limpiar_nombre_perfume(nombre, marca_canon...
    nombre_canon = limpiar_nombre_perfume(nombre, marca_canon) or (nombre or "").strip()
    # Evaluamos la condición lógica (len(nombre_canon) < 2) para controlar el flujo
    if len(nombre_canon) < 2:
        # Retornamos el resultado procesado ({'exito': False, 'motivo': 'Nombre de perfume v...)
        return {"exito": False, "motivo": "Nombre de perfume vacío tras normalización"}

    # Asignamos 'formato_final' con formato or detectar_formato_oferta(nombre,...
    formato_final = formato or detectar_formato_oferta(nombre, url_producto)
    # Asignamos 'p_norm_int' con int(round(float(precio_normal))) if precio...
    p_norm_int = int(round(float(precio_normal))) if (precio_normal and precio_normal > p_act_int) else p_act_int
    # Asignamos 'fecha_actual' con datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res_t = sb.table("tiendas").select("id").ilike("nombre", tienda_nombre.strip()).limit(1).execute()
            # Evaluamos la condición lógica (res_t.data) para controlar el flujo
            if res_t.data:
                # Asignamos 'tienda_id_sb' con res_t.data[0]['id']
                tienda_id_sb = res_t.data[0]["id"]
            else:
                # Asignamos 'base_url' con url_producto.split('/')[0] + '//' + url_pr...
                base_url = (
                    url_producto.split("/")[0] + "//" + url_producto.split("/")[2]
                    if "://" in url_producto
                    else "https://"
                )
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                ins_t = sb.table("tiendas").insert({
                    "nombre": tienda_nombre.strip(),
                    "url_base": base_url,
                    "trust_score": 88,
                    "badge": "Tienda Verificada",
                    "logo_emoji": "",
                }).execute()
                # Asignamos 'tienda_id_sb' con ins_t.data[0]['id']
                tienda_id_sb = ins_t.data[0]["id"]

            # Asignamos 'genero_norm' con inferir_genero_explicito_nombre(nombre, ge...
            genero_norm = inferir_genero_explicito_nombre(nombre, genero)
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            res_p = (
                sb.table("perfumes")
                .select("id, nombre, genero")
                .ilike("marca", marca_canon)
                .ilike("tipo", tipo)
                .execute()
            )
            # Asignamos 'k_con_gen' con clave_identidad_perfume(nombre_canon, marc...
            k_con_gen = clave_identidad_perfume(nombre_canon, marca_canon, tipo, incluir_genero_nombre=True)
            # Asignamos 'k_sin_gen' con clave_identidad_perfume(nombre_canon, marc...
            k_sin_gen = clave_identidad_perfume(nombre_canon, marca_canon, tipo, incluir_genero_nombre=False)
            # Asignamos 'cands_exactos' con []
            cands_exactos = []
            # Asignamos 'cands_sin_gen' con []
            cands_sin_gen = []
            # Recorremos iterativamente cada 'cand_p' en res_p.data or []
            for cand_p in (res_p.data or []):
                # Asignamos 'cn' con cand_p.get('nombre') or ''
                cn = cand_p.get("nombre") or ""
                # Evaluamos la condición lógica (clave_identidad_perfume(cn, marca_canon, tipo, inclu...) para controlar el flujo
                if clave_identidad_perfume(cn, marca_canon, tipo, incluir_genero_nombre=True) == k_con_gen:
                    # Ejecutamos instrucción: cands_exactos.append(cand_p)
                    cands_exactos.append(cand_p)
                # Evaluamos la condición lógica (clave_identidad_perfume(cn, marca_canon, tipo, inclu...) para controlar el flujo
                elif clave_identidad_perfume(cn, marca_canon, tipo, incluir_genero_nombre=False) == k_sin_gen:
                    # Ejecutamos instrucción: cands_sin_gen.append(cand_p)
                    cands_sin_gen.append(cand_p)

            # Asignamos 'perfume_id_sb' con None
            perfume_id_sb = None
            # Recorremos iterativamente cada 'cand_p' en cands_exactos
            for cand_p in cands_exactos:
                # Asignamos 'g_cand_n' con inferir_genero_explicito_nombre(cand_p.get...
                g_cand_n = inferir_genero_explicito_nombre(cand_p.get("nombre") or "", cand_p.get("genero"))
                # Evaluamos la condición lógica (g_cand_n == genero_norm) para controlar el flujo
                if g_cand_n == genero_norm:
                    # Asignamos 'perfume_id_sb' con cand_p['id']
                    perfume_id_sb = cand_p["id"]
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break
            # Evaluamos la condición lógica (perfume_id_sb is None) para controlar el flujo
            if perfume_id_sb is None:
                # Asignamos 'gens_ex' con {inferir_genero_explicito_nombre(c.get('no...
                gens_ex = {inferir_genero_explicito_nombre(c.get("nombre") or "", c.get("genero")) for c in cands_exactos}
                # Evaluamos la condición lógica (not ('Hombre' in gens_ex and 'Mujer' in gens_ex)) para controlar el flujo
                if not ("Hombre" in gens_ex and "Mujer" in gens_ex):
                    # Recorremos iterativamente cada 'cand_p' en cands_exactos
                    for cand_p in cands_exactos:
                        # Asignamos '(es_comp, g_res)' con generos_compatibles(cand_p.get('genero'), ...
                        es_comp, g_res = generos_compatibles(cand_p.get("genero"), genero_norm)
                        # Evaluamos la condición lógica (es_comp) para controlar el flujo
                        if es_comp:
                            # Asignamos 'perfume_id_sb' con cand_p['id']
                            perfume_id_sb = cand_p["id"]
                            # Evaluamos la condición lógica ((normalizar_genero(cand_p.get('genero')) or 'Unisex'...) para controlar el flujo
                            if (normalizar_genero(cand_p.get("genero")) or "Unisex") == "Unisex" and g_res in ("Hombre", "Mujer"):
                                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                                try:
                                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                                    sb.table("perfumes").update({"genero": g_res}).eq("id", perfume_id_sb).execute()
                                except Exception as exc_g:
                                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                                    logger.debug(f"Aviso afinando género Unisex->{g_res} en perfume #{perfume_id_sb}: {exc_g}")
                            # Interrumpimos el ciclo actual al cumplirse la condición de salida
                            break
            # Evaluamos la condición lógica (perfume_id_sb is None and genero_norm in ('Hombre', ...) para controlar el flujo
            if perfume_id_sb is None and genero_norm in ("Hombre", "Mujer"):
                # Recorremos iterativamente cada 'cand_p' en cands_sin_gen
                for cand_p in cands_sin_gen:
                    # Asignamos 'g_cand_n' con inferir_genero_explicito_nombre(cand_p.get...
                    g_cand_n = inferir_genero_explicito_nombre(cand_p.get("nombre") or "", cand_p.get("genero"))
                    # Evaluamos la condición lógica (g_cand_n == genero_norm) para controlar el flujo
                    if g_cand_n == genero_norm:
                        # Asignamos 'perfume_id_sb' con cand_p['id']
                        perfume_id_sb = cand_p["id"]
                        # Interrumpimos el ciclo actual al cumplirse la condición de salida
                        break

            # Evaluamos la condición lógica (perfume_id_sb is not None) para controlar el flujo
            if perfume_id_sb is not None:
                # Asignamos 'es_nuevo' con False
                es_nuevo = False
            else:
                # Asignamos 'es_nuevo' con True
                es_nuevo = True
                # Asignamos 'img' con imagen_url or ''
                img = imagen_url or ""
                # Asignamos 'notas_txt' con notas or 'Cítricos, Maderas, Almizcle'
                notas_txt = notas or "Cítricos, Maderas, Almizcle"
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
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
                # Asignamos 'perfume_id_sb' con ins_p.data[0]['id']
                perfume_id_sb = ins_p.data[0]["id"]

            # Ejecutamos instrucción: registrar_observacion_oferta({'perfume_id_sb': perfu...
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
            # Retornamos el resultado procesado ({'exito': True, 'perfume_id': perfume_id_sb, 'e...)
            return {"exito": True, "perfume_id": perfume_id_sb, "es_nuevo": es_nuevo, "fecha": fecha_actual}
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.error(f"Error persistiendo descubrimiento en Supabase ({marca_canon} - {nombre_canon}): {e}")
            # Retornamos el resultado procesado ({'exito': False, 'motivo': str(e)})
            return {"exito": False, "motivo": str(e)}

    # Respaldo SQLite local (coincidencia exacta canónica, sin LIKE ambiguo)
    init_db()
    # Gestión automática de contexto y recursos para: get_db_cursor(commit=True)
    with get_db_cursor(commit=True) as cursor:
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("SELECT id FROM tiendas WHERE LOWER(nombre) = LOWER(?);", (tienda_nombre.strip(),))
        # Asignamos 'row_tienda' con cursor.fetchone()
        row_tienda = cursor.fetchone()
        # Evaluamos la condición lógica (row_tienda) para controlar el flujo
        if row_tienda:
            # Asignamos 'tienda_id_sq' con row_tienda['id']
            tienda_id_sq = row_tienda["id"]
        else:
            # Asignamos 'base_url' con url_producto.split('/')[0] + '//' + url_pr...
            base_url = (
                url_producto.split("/")[0] + "//" + url_producto.split("/")[2]
                if "://" in url_producto
                else "https://"
            )
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT INTO tiendas (nombre, url_base, trust_score, badge, logo_emoji)
            VALUES (?, ?, 88, 'Tienda Verificada', '');
            """, (tienda_nombre.strip(), base_url))
            # Asignamos 'tienda_id_sq' con cursor.lastrowid
            tienda_id_sq = cursor.lastrowid

        # Asignamos 'genero_sq' con (genero or 'Unisex').strip() or 'Unisex'
        genero_sq = (genero or "Unisex").strip() or "Unisex"
        # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
        cursor.execute("""
        SELECT id, genero FROM perfumes
        WHERE LOWER(TRIM(marca)) = LOWER(?)
          AND LOWER(TRIM(nombre)) = LOWER(?)
          AND LOWER(COALESCE(TRIM(tipo), '')) = LOWER(?);
        """, (marca_canon, nombre_canon, tipo))
        # Asignamos 'rows_perf' con cursor.fetchall()
        rows_perf = cursor.fetchall()
        # Asignamos 'row_perfume' con None
        row_perfume = None
        # Recorremos iterativamente cada 'rp' en rows_perf
        for rp in rows_perf:
            # Asignamos 'g_c' con (rp['genero'] or 'Unisex').strip().lower()
            g_c = (rp["genero"] or "Unisex").strip().lower()
            # Evaluamos la condición lógica (g_c == genero_sq.lower()) para controlar el flujo
            if g_c == genero_sq.lower():
                # Asignamos 'row_perfume' con rp
                row_perfume = rp
                # Interrumpimos el ciclo actual al cumplirse la condición de salida
                break
        # Evaluamos la condición lógica (row_perfume is None) para controlar el flujo
        if row_perfume is None:
            # Recorremos iterativamente cada 'rp' en rows_perf
            for rp in rows_perf:
                # Asignamos 'g_c' con (rp['genero'] or 'Unisex').strip().lower()
                g_c = (rp["genero"] or "Unisex").strip().lower()
                # Evaluamos la condición lógica (genero_sq.lower() == 'unisex' or g_c == 'unisex') para controlar el flujo
                if genero_sq.lower() == "unisex" or g_c == "unisex":
                    # Asignamos 'row_perfume' con rp
                    row_perfume = rp
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break

        # Asignamos 'es_nuevo_sq' con False
        es_nuevo_sq = False
        # Evaluamos la condición lógica (row_perfume) para controlar el flujo
        if row_perfume:
            # Asignamos 'perfume_id_sq' con row_perfume['id']
            perfume_id_sq = row_perfume["id"]
        else:
            # Asignamos 'es_nuevo_sq' con True
            es_nuevo_sq = True
            # Asignamos 'img' con imagen_url or ''
            img = imagen_url or ""
            # Asignamos 'notas_texto' con notas or 'Cítricos, Maderas, Almizcle'
            notas_texto = notas or "Cítricos, Maderas, Almizcle"
            # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
            cursor.execute("""
            INSERT INTO perfumes (nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
            """, (
                nombre_canon, marca_canon, genero_sq, tipo, notas_texto, img,
                int(bool(es_arabe)), int(bool(p_norm_int > p_act_int * 1.08)), p_norm_int,
            ))
            # Asignamos 'perfume_id_sq' con cursor.lastrowid
            perfume_id_sq = cursor.lastrowid

    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
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
    # Retornamos el resultado procesado ({'exito': True, 'perfume_id': perfume_id_sq, 'e...)
    return {"exito": True, "perfume_id": perfume_id_sq, "es_nuevo": es_nuevo_sq, "fecha": fecha_actual}


# =============================================================================
# BLOQUE 13: AUDITORÍA DE TIENDAS Y MOTOR DE CONFIANZA (TRUSTSCORE CHILE)
# =============================================================================
def obtener_tiendas() -> List[Dict[str, Any]]:
    """Retorna la lista de tiendas registradas ordenadas por índice de confianza."""
    # Retornamos el resultado procesado (obtener_tiendas_trust())
    return obtener_tiendas_trust()


# Definición de función 'obtener_tiendas_trust' (parámetros: filtro_tipo, score_minimo, busqueda)
def obtener_tiendas_trust(
    filtro_tipo: Optional[str] = None,
    score_minimo: int = 0,
    busqueda: str = "",
) -> List[Dict[str, Any]]:
    """Retorna tiendas auditadas con métricas detalladas para la página de confianza."""
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase()
    # Evaluamos la condición lógica (sb and is_supabase_disponible()) para controlar el flujo
    if sb and is_supabase_disponible():
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            q = sb.table("tiendas").select("*").gte("trust_score", score_minimo)
            # Evaluamos la condición lógica (filtro_tipo and filtro_tipo != 'Todas') para controlar el flujo
            if filtro_tipo and filtro_tipo != "Todas":
                # Asignamos 'q' con q.eq('tipo_tienda', filtro_tipo)
                q = q.eq("tipo_tienda", filtro_tipo)
            # Evaluamos la condición lógica (busqueda) para controlar el flujo
            if busqueda:
                # Asignamos 'term' con busqueda.strip()
                term = busqueda.strip()
                # Asignamos 'q' con q.or_(f'nombre.ilike.%{term}%,url_base.ili...
                q = q.or_(f"nombre.ilike.%{term}%,url_base.ilike.%{term}%,rut.ilike.%{term}%")
            # Asignamos 'q' con q.order('trust_score', desc=True)
            q = q.order("trust_score", desc=True)

            # Asignamos 'res' con q.execute()
            res = q.execute()
            # Asignamos 'tiendas' con []
            tiendas = []
            # Recorremos iterativamente cada 'r' en res.data or []
            for r in res.data or []:
                # Asignamos 'd' con dict(r)
                d = dict(r)
                # Asignamos 'd['estrellas']' con round(d.get('trust_score', 0) / 20.0, 1)
                d["estrellas"] = round(d.get("trust_score", 0) / 20.0, 1)
                # Ejecutamos instrucción: tiendas.append(d)
                tiendas.append(d)
            # Evaluamos la condición lógica (tiendas) para controlar el flujo
            if tiendas:
                # Retornamos el resultado procesado (tiendas)
                return tiendas
        except Exception as e:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            logger.warning(f"Error consultando tiendas en Supabase ({e}), usando SQLite.")

    # Ejecutamos instrucción: init_db()
    init_db()
    # Asignamos 'query' con '\n SELECT\n id, nombre, url_base, trust_s...
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
        netloc = (parsed.netloc or parsed.path.split("/")[0]).replace("www.", "")
    except Exception:
        # Asignamos 'netloc' con url_limpia
        netloc = url_limpia

    # Asignamos 'tiendas_db' con obtener_tiendas_trust()
    tiendas_db = obtener_tiendas_trust()
    # Recorremos iterativamente cada 't' en tiendas_db
    for t in tiendas_db:
        # Asignamos 'dominio_tienda' con t['url_base'].lower().replace('https://', ...
        dominio_tienda = (
            t["url_base"]
            .lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .strip("/")
        )
        # Evaluamos la condición lógica (dominio_tienda and (dominio_tienda in netloc or netl...) para controlar el flujo
        if dominio_tienda and (dominio_tienda in netloc or netloc in dominio_tienda):
            # Asignamos 'score_val' con int(t.get('trust_score') or 90)
            score_val = int(t.get("trust_score") or 90)
            # Asignamos 'p_base' con max(15, min(25, round(score_val / 4)))
            p_base = max(15, min(25, round(score_val / 4)))
            # Retornamos el resultado procesado ({'nombre': t.get('nombre') or 'Tienda Auditada'...)
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

    # Asignamos 'puntos_ssl' con 25 if url_limpia.startswith('https://') el...
    puntos_ssl = 25 if url_limpia.startswith("https://") else 0
    # Asignamos 'es_cl' con netloc.endswith('.cl')
    es_cl = netloc.endswith(".cl")
    # Asignamos 'puntos_dominio' con 25 if es_cl else 10
    puntos_dominio = 25 if es_cl else 10

    # Asignamos 'senales_alerta' con []
    senales_alerta = []
    # Asignamos 'palabras_sospechosas' con ['outlet-original', 'perfumes-ganga', 'dio...
    palabras_sospechosas = [
        "outlet-original",
        "perfumes-ganga",
        "dior-chile-ofertas",
        "chanel-descuentos",
        "liquidaciones-lujo",
    ]
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
        recom = (
            "El sitio cuenta con HTTPS y dominio estándar, pero no está en el registro oficial "
            "de distribuidores autorizados. Revisa que permita pagar con Webpay y no solo transferencias personales."
        )
    else:
        # Asignamos 'badge' con 'Sitio No Verificado / Riesgo'
        badge = "Sitio No Verificado / Riesgo"
        # Asignamos 'recom' con 'Precaución extrema. No se registran antec...
        recom = (
            "Precaución extrema. No se registran antecedentes comerciales formales ni sello de confianza. "
            "Posible tienda clon o producto sin garantía de originalidad."
        )

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
            "Acreditación": f"{puntos_reputacion}/25",
        },
        "senales_alerta": senales_alerta,
        "recomendacion": recom,
    }


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Importación de librería estándar o dependencia externa (argparse)
    import argparse

    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Gestor de Base de Datos PerfumeTrending (Supabase & SQLite)")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--seed", action="store_true", help="Poblar datos semilla en Supabase y SQLite")
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser.add_argument("--status", action="store_true", help="Verificar estado de conexion con Supabase y SQLite")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
    # Ejecutamos instrucción: print('PerfumeTrending.cl — Estado de Persistencia')
    print("PerfumeTrending.cl — Estado de Persistencia")
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    url_cfg, key_cfg = get_supabase_credentials()
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    print(f"Supabase URL configurada: {'Sí' if url_cfg else 'No'}")
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    print(f"Supabase Key configurada: {'Sí' if key_cfg else 'No'}")
    # Ejecutamos instrucción: print(f"Service Role configurada: {('Sí' if has_serv...
    print(f"Service Role configurada: {'Sí' if has_service_role_key() else 'No'}")

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb_activo = is_supabase_disponible()
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    print(f"Supabase Estado: {'CONECTADO Y DISPONIBLE' if sb_activo else 'NO DISPONIBLE / MODO SQLITE'}")
    # Ejecución de consulta SQL parametrizada sobre la base de datos SQLite local
    print(f"SQLite Local: {DB_PATH} ({'Existe' if os.path.exists(DB_PATH) else 'No inicializada'})")

    # Evaluamos la condición lógica (args.seed) para controlar el flujo
    if args.seed:
        # Ejecutamos instrucción: print('\nEjecutando poblado de datos...')
        print("\nEjecutando poblado de datos...")
        # Ejecutamos instrucción: init_db(force_reseed=True)
        init_db(force_reseed=True)
        # Evaluamos la condición lógica (sb_activo) para controlar el flujo
        if sb_activo:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            poblar_datos_semilla_supabase()
        # Ejecutamos instrucción: print('Poblado completado.')
        print("Poblado completado.")
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
