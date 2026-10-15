# PerfumeTrending.cl — Plan de Migración de Esquema y Datos
**Estrategia Zero-Downtime, Migración Aditiva y Verificación Paso a Paso**

---

## 1. Principios Rectores
1. **No Destructivo:** No se eliminan tablas, columnas ni datos históricos. Toda alteración de esquema es aditiva (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`).
2. **Sin Cambios No Autorizados en Producción:** Las migraciones se versionan en scripts SQL idempotentes en `supabase/migrations/` para ser aplicadas en un entorno de staging/prueba primero.
3. **Preservación de Columnas Legadas:** `perfumes.notas` se conserva durante todo el periodo de transición. Las lecturas de frontend solo se actualizarán tras validar el 100% de consistencia.
4. **Idempotencia:** Toda migración y seed puede ejecutarse múltiples veces sin duplicar registros ni fallar con error de clave.

---

## 2. Fases de Migración

### Fase 1: Creación de Esquema Aditivo (DDL)
- **Script:** `20261015000002_tablas_variantes_ofertas_auditoria.sql`
  - Crear `variantes_perfume` con FK a `perfumes`.
  - Crear `ofertas_actuales` con `UNIQUE (variante_id, tienda_id)`.
  - Crear `scraping_runs`.
  - Ampliar `precios_registro` con columnas: `variante_id`, `tipo_evento`, `campos_modificados`, `observacion_id`, `scraping_run_id`.
  - Índices de rendimiento correspondientes.
- **Script:** `20261015000003_catalogo_notas_familias_olfativas.sql`
  - Crear `familias_notas`, `notas_olfativas`, `perfume_notas`.
  - Crear `familias_olfativas`, `perfume_familias_olfativas`.

### Fase 2: Ingesta de Catálogo Canónico y Staging (Seeds)
- **Script:** `20261015000004_seed_familias_y_notas.sql`
  - Inserción de las 12 familias de notas y las 107 notas normalizadas con `ON CONFLICT (slug) DO UPDATE`.
  - Inserción de las 10 familias olfativas generales.
- **Script:** `20261015000005_staging_notas_migracion.sql`
  - Crear `perfume_notas_importacion`.
  - Cargar el texto de `perfumes.notas` hacia `perfume_notas_importacion` sin eliminar la columna origen.

### Fase 3: Persistencia Transaccional y Lógica de Negocio
- **Script:** `20261015000006_funciones_persistencia_transaccional.sql`
  - Función PL/pgSQL `registrar_observacion_oferta`.
  - Función PL/pgSQL `registrar_fallo_scraping`.
- **Script:** `20261015000007_seguridad_rls_politicas.sql`
  - Habilitar RLS en tablas nuevas.
  - Políticas de lectura pública (`SELECT`) para clientes anónimos y autenticados.
  - Políticas restrictivas de escritura para roles privilegiados (`service_role`).

### Fase 4: Migración del Historial Existente
- **Script:** `20261015000008_migracion_datos_historicos.sql`
  1. **Generación de Variantes Base:** Por cada perfume y volumen distinto presente en `precios_registro` (o en `perfumes`), generar una fila en `variantes_perfume` con formato `'regular'`.
  2. **Enlace de `precios_registro.variante_id`:** Actualizar `precios_registro` vinculando su `variante_id` según `(perfume_id, volumen_ml)`.
  3. **Poblado de `ofertas_actuales`:** Obtener la última observación confirmada por `(variante_id, tienda_id)` ordenada por `fecha_registro DESC, id DESC`, e insertarla en `ofertas_actuales`.
  4. **Reporte de Casos Ambiguos:** Documentar cualquier registro donde `volumen_ml` sea inconsistente.

### Fase 5: Actualización de Vistas y Conmutación de Consultas
- Actualizar `vista_precios_actuales` para consultar directamente sobre `ofertas_actuales`.
- Validar equivalencia de resultados con datos sintéticos.
