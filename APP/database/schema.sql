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
    logo_emoji TEXT DEFAULT '🏬',
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

-- 3. Registro Histórico de Precios (Time-Series & ETL Ingestion)
CREATE TABLE IF NOT EXISTS precios_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfume_id INTEGER NOT NULL,
    tienda_id INTEGER NOT NULL,
    precio_actual INTEGER NOT NULL,
    precio_normal INTEGER NOT NULL,
    en_stock BOOLEAN DEFAULT 1,
    volumen_ml INTEGER DEFAULT 100,
    url_producto TEXT NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (perfume_id) REFERENCES perfumes (id) ON DELETE CASCADE,
    FOREIGN KEY (tienda_id) REFERENCES tiendas (id) ON DELETE CASCADE
);

-- 4. Índices B-Tree de Alto Rendimiento (Optimización de Consultas)
CREATE INDEX IF NOT EXISTS idx_precios_perfume ON precios_registro(perfume_id);
CREATE INDEX IF NOT EXISTS idx_precios_tienda ON precios_registro(tienda_id);
CREATE INDEX IF NOT EXISTS idx_precios_fecha ON precios_registro(fecha_registro);
CREATE INDEX IF NOT EXISTS idx_precios_volumen ON precios_registro(perfume_id, volumen_ml);
CREATE INDEX IF NOT EXISTS idx_precios_stock_act ON precios_registro(en_stock, precio_actual);
CREATE INDEX IF NOT EXISTS idx_perfumes_marca ON perfumes(marca);
CREATE INDEX IF NOT EXISTS idx_perfumes_genero ON perfumes(genero);
CREATE INDEX IF NOT EXISTS idx_perfumes_arabe ON perfumes(es_arabe);
CREATE INDEX IF NOT EXISTS idx_tiendas_trust ON tiendas(trust_score DESC);
