-- =====================================================================
-- PerfumeTrending.cl — Esquema Relacional DDL (SQLite 3)
-- =====================================================================
-- Definición formal de tablas, restricciones de integridad referencial
-- e índices de alto rendimiento para el motor de precios y catálogo.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- 1. Catálogo Maestro de Perfumes
CREATE TABLE IF NOT EXISTS perfumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    marca TEXT NOT NULL,
    genero TEXT DEFAULT 'Unisex',
    tipo TEXT DEFAULT 'Eau de Parfum',
    notas TEXT NOT NULL,
    imagen_url TEXT NOT NULL,
    es_arabe BOOLEAN DEFAULT 0,
    en_tendencia BOOLEAN DEFAULT 0,
    en_remate BOOLEAN DEFAULT 0,
    precio_referencia INTEGER NOT NULL
);

-- 2. Directorio de Tiendas Chilenas Auditadas (Pilar Antifraude & Trust Score)
CREATE TABLE IF NOT EXISTS tiendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    url_base TEXT NOT NULL,
    trust_score INTEGER DEFAULT 85,
    badge TEXT DEFAULT 'Verificado',
    logo_emoji TEXT DEFAULT '',
    rut TEXT DEFAULT '',
    tipo_tienda TEXT DEFAULT 'Comercio Especializado',
    ssl_seguro BOOLEAN DEFAULT 1,
    anios_antiguedad INTEGER DEFAULT 5,
    sello_ccs BOOLEAN DEFAULT 0,
    reclamos_sernac TEXT DEFAULT 'Bajo',
    politica_devolucion TEXT DEFAULT '30 días de satisfacción',
    direccion_fiscal TEXT DEFAULT 'Santiago, Chile',
    puntos_seguridad INTEGER DEFAULT 25,
    puntos_legalidad INTEGER DEFAULT 25,
    puntos_garantia INTEGER DEFAULT 20,
    puntos_reputacion INTEGER DEFAULT 20
);

-- 3. Variantes de Perfume (Presentación / SKU Físico)
CREATE TABLE IF NOT EXISTS variantes_perfume (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfume_id INTEGER NOT NULL,
    concentracion TEXT,
    volumen_ml REAL DEFAULT 100,
    formato TEXT NOT NULL DEFAULT 'regular',
    identificador_externo TEXT,
    slug TEXT UNIQUE,
    activa BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (perfume_id) REFERENCES perfumes (id) ON DELETE CASCADE
);

-- 4. Ofertas Actuales Vivas (Snapshot de Precios y Stock por Comercio)
CREATE TABLE IF NOT EXISTS ofertas_actuales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id INTEGER NOT NULL,
    tienda_id INTEGER NOT NULL,
    precio_actual INTEGER,
    precio_normal INTEGER,
    en_stock BOOLEAN,
    url_producto TEXT,
    estado TEXT NOT NULL DEFAULT 'no_verificada',
    ultima_verificacion_exitosa TIMESTAMP,
    ultimo_intento TIMESTAMP,
    ultimo_cambio_confirmado TIMESTAMP,
    fallos_consecutivos INTEGER NOT NULL DEFAULT 0,
    ultimo_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (variante_id, tienda_id),
    FOREIGN KEY (variante_id) REFERENCES variantes_perfume (id) ON DELETE CASCADE,
    FOREIGN KEY (tienda_id) REFERENCES tiendas (id) ON DELETE CASCADE
);

-- 5. Auditoría de Ejecuciones ETL (scraping_runs)
CREATE TABLE IF NOT EXISTS scraping_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_scraper TEXT NOT NULL,
    tienda_id INTEGER,
    estado TEXT NOT NULL DEFAULT 'iniciado',
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP,
    productos_procesados INTEGER NOT NULL DEFAULT 0,
    ofertas_nuevas INTEGER NOT NULL DEFAULT 0,
    cambios_precio INTEGER NOT NULL DEFAULT 0,
    cambios_stock INTEGER NOT NULL DEFAULT 0,
    cambios_url INTEGER NOT NULL DEFAULT 0,
    errores INTEGER NOT NULL DEFAULT 0,
    mensaje_detalle TEXT,
    FOREIGN KEY (tienda_id) REFERENCES tiendas (id) ON DELETE RESTRICT
);

-- 6. Registro Histórico de Precios (Time-Series & ETL Ingestion)
CREATE TABLE IF NOT EXISTS precios_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfume_id INTEGER NOT NULL,
    tienda_id INTEGER NOT NULL,
    precio_actual INTEGER NOT NULL,
    precio_normal INTEGER,
    en_stock BOOLEAN DEFAULT 1,
    volumen_ml INTEGER DEFAULT 100,
    url_producto TEXT NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    variante_id INTEGER,
    tipo_evento TEXT,
    campos_modificados TEXT,
    observacion_id TEXT,
    scraping_run_id INTEGER,
    FOREIGN KEY (perfume_id) REFERENCES perfumes (id) ON DELETE CASCADE,
    FOREIGN KEY (tienda_id) REFERENCES tiendas (id) ON DELETE CASCADE,
    FOREIGN KEY (variante_id) REFERENCES variantes_perfume (id) ON DELETE SET NULL,
    FOREIGN KEY (scraping_run_id) REFERENCES scraping_runs (id) ON DELETE SET NULL
);

-- 7. Usuarios Registrados y Autenticación (Respaldo Local con PBKDF2-HMAC-SHA256)
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    telefono TEXT DEFAULT '',
    ubicacion TEXT DEFAULT 'Santiago, Chile',
    bio TEXT DEFAULT '',
    foto_perfil TEXT DEFAULT '',
    alerta_email BOOLEAN DEFAULT 1,
    notif_stock BOOLEAN DEFAULT 1,
    notif_resumen BOOLEAN DEFAULT 0,
    umbral_descuento INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Favoritos y Alertas de Precios por Usuario
CREATE TABLE IF NOT EXISTS favoritos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    perfume_id INTEGER NOT NULL,
    precio_guardado INTEGER,
    fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, perfume_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    FOREIGN KEY (perfume_id) REFERENCES perfumes (id) ON DELETE CASCADE
);

-- 9. Índices B-Tree de Alto Rendimiento (Optimización de Consultas)
CREATE INDEX IF NOT EXISTS idx_precios_perfume ON precios_registro(perfume_id);
CREATE INDEX IF NOT EXISTS idx_precios_tienda ON precios_registro(tienda_id);
CREATE INDEX IF NOT EXISTS idx_precios_fecha ON precios_registro(fecha_registro);
CREATE INDEX IF NOT EXISTS idx_precios_volumen ON precios_registro(perfume_id, volumen_ml);
CREATE INDEX IF NOT EXISTS idx_precios_stock_act ON precios_registro(en_stock, precio_actual);
CREATE INDEX IF NOT EXISTS idx_precios_variante ON precios_registro(variante_id);
CREATE INDEX IF NOT EXISTS idx_variantes_lookup ON variantes_perfume(perfume_id, volumen_ml, formato);
CREATE INDEX IF NOT EXISTS idx_perfumes_marca ON perfumes(marca);
CREATE INDEX IF NOT EXISTS idx_perfumes_genero ON perfumes(genero);
CREATE INDEX IF NOT EXISTS idx_perfumes_arabe ON perfumes(es_arabe);
CREATE INDEX IF NOT EXISTS idx_tiendas_trust ON tiendas(trust_score DESC);
CREATE INDEX IF NOT EXISTS idx_ofertas_variante ON ofertas_actuales(variante_id);
CREATE INDEX IF NOT EXISTS idx_ofertas_tienda ON ofertas_actuales(tienda_id);
CREATE INDEX IF NOT EXISTS idx_favoritos_user ON favoritos(usuario_id);
