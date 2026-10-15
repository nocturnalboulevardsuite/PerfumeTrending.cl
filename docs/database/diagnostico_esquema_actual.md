# PerfumeTrending.cl — Diagnóstico de Esquema Real y Estado de Persistencia
**Fecha de auditoría:** 15 de Octubre de 2026  
**Ambiente inspeccionado:** Supabase PostgreSQL (Producción / Staging) & SQLite Local (`APP/data/perfumes.db`)  
**Modo de ejecución:** Solo lectura (Read-Only), sin alteración ni eliminación de datos.

---

## 1. Resumen Ejecutivo del Diagnóstico

Se ejecutó una inspección exhaustiva de la base de datos Supabase conectada (`miqscdupnknhjemvcjil.supabase.co`) y del motor local SQLite de contingencia. 

### Hallazgos Principales:
1. **Supabase está activo y conectado**, con las tablas base de la Fase 2 operativas: `perfumes` (134 registros), `tiendas` (8 registros), `precios_registro` (460 registros), `tendencias_metricas` (0 registros), `scraping_logs` (3 registros).
2. **Las 9 tablas nuevas de la arquitectura robusta aún no existen en el esquema `public` de Supabase**:
   - `variantes_perfume` (No existe)
   - `ofertas_actuales` (No existe)
   - `familias_notas` (No existe)
   - `notas_olfativas` (No existe)
   - `perfume_notas` (No existe)
   - `familias_olfativas` (No existe)
   - `perfume_familias_olfativas` (No existe)
   - `perfume_notas_importacion` (No existe)
   - `scraping_runs` (No existe)
3. **Calidad de Datos Existentes en `precios_registro` (460 registros)**:
   - **Historiales con `volumen_ml` nulo o <= 0:** 0 (el 100% cuenta con volumen explícito registrado).
   - **Historiales con `precio_actual` <= 0 o nulo:** 0 (precios válidos).
   - **Historiales con `en_stock` nulo:** 0.
   - **Pares únicos `(perfume_id, tienda_id)`:** 163 combinaciones activas en el historial.
4. **Calidad de Datos en `perfumes` (134 registros)**:
   - **Duplicados exactos por `(marca, nombre)`:** 0. No hay colisiones de nombre idéntico.
   - **Perfumes con columna `notas` poblada:** 134 (100% tienen notas en texto plano tipo `"Cítricos, Pomelo, Menta..."`).
   - Ningún perfume perderá su columna `notas` original.
5. **Discrepancias Críticas Detectadas en Scrapers y Persistencia**:
   - `scraper_periodico.py` implementaba un fallback defensivo peligroso: ante timeouts o errores HTTP 403/429/404, insertaba el último precio conocido en `precios_registro` con `en_stock=True`, inventando observaciones en vivo inexistentes.
   - Los extractores nativos para Falabella, Paris y Ripley forzaban `"en_stock": True` en sus retornos sin validar de forma rigurosa si el producto estaba agotado o descatalogado.

---

## 2. Inventario Detallado de Tablas Existentes

### 2.1. Tabla `public.perfumes`
- **Total de registros en Supabase:** 134
- **Total en SQLite local:** 132
- **Columnas reales:**
  | Columna | Tipo Supabase | Tipo SQLite | Nulable | Propósito |
  | :--- | :--- | :--- | :--- | :--- |
  | `id` | `BIGINT GENERATED ALWAYS` | `INTEGER PK AUTO` | No | Identificador maestro conceptual |
  | `nombre` | `TEXT` | `TEXT` | No | Nombre comercial de la fragancia |
  | `marca` | `TEXT` | `TEXT` | No | Casa perfumista o diseñador |
  | `genero` | `TEXT` | `TEXT` | Sí (Default 'Unisex') | Público objetivo |
  | `tipo` | `TEXT` | `TEXT` | Sí (Default 'Eau de Parfum') | Concentración olfativa |
  | `notas` | `TEXT` | `TEXT` | No | Lista de notas en texto crudo |
  | `imagen_url` | `TEXT` | `TEXT` | No | URL pública o asset local |
  | `es_arabe` | `BOOLEAN` | `BOOLEAN` | Sí (Default false/0) | Flag de perfumería oriental |
  | `en_tendencia` | `BOOLEAN` | `BOOLEAN` | Sí (Default false/0) | Flag para módulo Hype |
  | `en_remate` | `BOOLEAN` | `BOOLEAN` | Sí (Default false/0) | Flag de descuento agresivo |
  | `precio_referencia` | `INTEGER` | `INTEGER` | No | Precio retail sugerido / base |
  | `created_at` | `TIMESTAMPTZ` | N/A | Sí (Default now()) | Auditoría de creación |

### 2.2. Tabla `public.tiendas`
- **Total de registros en Supabase:** 8
- **Total en SQLite local:** 8
- **Tiendas auditadas:** Falabella, Paris, Ripley, Silk Perfumes, Elite Perfumes, DBS Beauty Store, Alisha Perfumes, +1 comercio verificado.
- **Columnas reales:** `id`, `nombre`, `url_base`, `trust_score`, `badge`, `logo_emoji`, `rut`, `tipo_tienda`, `ssl_seguro`, `anios_antiguedad`, `sello_ccs`, `reclamos_sernac`, `politica_devolucion`, `direccion_fiscal`, `puntos_seguridad`, `puntos_legalidad`, `puntos_garantia`, `puntos_reputacion`, `created_at`.

### 2.3. Tabla `public.precios_registro`
- **Total de registros en Supabase:** 460
- **Total en SQLite local:** 509
- **Columnas reales actuales:**
  | Columna | Tipo Supabase | Tipo SQLite | Restricción / FK |
  | :--- | :--- | :--- | :--- |
  | `id` | `BIGINT` | `INTEGER` | PRIMARY KEY |
  | `perfume_id` | `BIGINT` | `INTEGER` | FK `perfumes(id)` ON DELETE CASCADE |
  | `tienda_id` | `BIGINT` | `INTEGER` | FK `tiendas(id)` ON DELETE CASCADE |
  | `precio_actual` | `INTEGER` | `INTEGER` | NOT NULL |
  | `precio_normal` | `INTEGER` | `INTEGER` | NOT NULL |
  | `en_stock` | `BOOLEAN` | `BOOLEAN` | DEFAULT TRUE |
  | `volumen_ml` | `INTEGER` | `INTEGER` | DEFAULT 100 |
  | `url_producto` | `TEXT` | `TEXT` | NOT NULL |
  | `fecha_registro` | `TIMESTAMPTZ` | `TIMESTAMP` | DEFAULT NOW() |

*Observación clave:* Faltan las columnas de auditoría y enlace a variantes: `variante_id`, `tipo_evento`, `campos_modificados`, `observacion_id`, `scraping_run_id`.

### 2.4. Vistas SQL Existentes
- `public.vista_catalogo`: Calculaba `MIN(precio_actual)` directamente sobre `precios_registro` donde `en_stock = TRUE`.
- `public.vista_precios_actuales`: Calculaba `DISTINCT ON (perfume_id, tienda_id)` ordenando por `fecha_registro DESC`. Filtraba `en_stock = TRUE` en la subconsulta interna, lo que provocaba que si una oferta pasaba a agotada, la vista resucitara la oferta antigua en stock en lugar de reflejar el estado actual.

---

## 3. Estado de RLS (Row Level Security) y Permisos

- En `20261014000000_init_supabase_schema.sql`, las tablas `tiendas`, `perfumes`, `precios_registro`, `tendencias_metricas` y `scraping_logs` tenían RLS activado pero con políticas ultra-permisivas:
  `CREATE POLICY "Escritura perfumes" ON public.perfumes FOR ALL USING (true) WITH CHECK (true);`
- Esto permitía que cualquier cliente anónimo pudiera potencialmente modificar registros.
- La nueva arquitectura define separación estricta: lectura pública (`SELECT` para `anon` y `authenticated`) y escritura exclusiva mediante funciones de seguridad/servidor (`service_role` o RPC autenticada).

---

## 4. Conclusiones y Próximos Pasos

1. Mantener las tablas `perfumes`, `tiendas` y `precios_registro` intactas.
2. Preparar migraciones aditivas:
   - Crear `variantes_perfume`, `ofertas_actuales`, `scraping_runs`.
   - Extender `precios_registro` con `variante_id`, `tipo_evento`, `campos_modificados`, `observacion_id`, `scraping_run_id`.
   - Crear el catálogo canónico de notas (12 familias, 107 notas) y familias olfativas.
   - Instalar funciones `registrar_observacion_oferta` y `registrar_fallo_scraping`.
3. Ningún dato histórico existente será eliminado ni truncado.
