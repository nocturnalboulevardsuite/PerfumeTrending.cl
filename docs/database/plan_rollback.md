# PerfumeTrending.cl — Plan de Rollback y Contingencia
**Procedimientos de Reversión Segura por Fase de Despliegue**

---

## 1. Reglas Generales de Rollback
1. Dado que la arquitectura de migración es estrictamente aditiva, ninguna reversión destruye registros preexistentes en `perfumes`, `tiendas` o `precios_registro`.
2. Todo script de rollback se ejecuta en orden inverso a las migraciones aplicadas.
3. Antes de cualquier reversión, se extrae un volcado lógico (`pg_dump` o export JSON) de las tablas involucradas.

---

## 2. Procedimiento de Reversión por Migración

### Reversión de Fase 5 (Vistas):
Si la nueva `vista_precios_actuales` presenta inconvenientes de compatibilidad con Streamlit:
```sql
-- Restaurar vista original basada en precios_registro
CREATE OR REPLACE VIEW public.vista_precios_actuales AS
WITH ultimos_precios AS (
    SELECT DISTINCT ON (perfume_id, tienda_id)
        pr.id,
        pr.perfume_id,
        pr.tienda_id,
        pr.precio_actual,
        pr.precio_normal,
        pr.en_stock,
        COALESCE(pr.volumen_ml, 100) as volumen_ml,
        ROUND(CAST(pr.precio_actual AS NUMERIC) / GREATEST(1, COALESCE(pr.volumen_ml, 100))) as precio_por_ml,
        pr.url_producto,
        pr.fecha_registro
    FROM public.precios_registro pr
    WHERE pr.en_stock = TRUE AND pr.precio_actual > 0 AND pr.url_producto IS NOT NULL
    ORDER BY pr.perfume_id, pr.tienda_id, pr.fecha_registro DESC
)
SELECT 
    up.*,
    t.nombre as tienda_nombre,
    t.url_base,
    t.trust_score,
    t.badge,
    t.logo_emoji
FROM ultimos_precios up
JOIN public.tiendas t ON up.tienda_id = t.id;
```

### Reversión de Fase 4 (Datos Migrados):
Si el poblado de `ofertas_actuales` o el enlace de `variante_id` requiere ajuste:
```sql
-- Limpiar enlaces sin borrar filas históricas
UPDATE public.precios_registro SET variante_id = NULL WHERE variante_id IS NOT NULL;
TRUNCATE TABLE public.ofertas_actuales;
TRUNCATE TABLE public.variantes_perfume CASCADE;
```

### Reversión de Fase 3 (Funciones y RLS):
```sql
DROP FUNCTION IF EXISTS public.registrar_observacion_oferta(bigint, bigint, integer, integer, boolean, text, bigint);
DROP FUNCTION IF EXISTS public.registrar_fallo_scraping(bigint, bigint, text);
```

### Reversión de Fase 2 (Catálogos y Staging):
```sql
DROP TABLE IF EXISTS public.perfume_notas_importacion;
DROP TABLE IF EXISTS public.perfume_familias_olfativas;
DROP TABLE IF EXISTS public.familias_olfativas;
DROP TABLE IF EXISTS public.perfume_notas;
DROP TABLE IF EXISTS public.notas_olfativas;
DROP TABLE IF EXISTS public.familias_notas;
```

### Reversión de Fase 1 (Tablas Nuevas y Columnas Aditivas):
```sql
ALTER TABLE public.precios_registro DROP COLUMN IF EXISTS variante_id;
ALTER TABLE public.precios_registro DROP COLUMN IF EXISTS tipo_evento;
ALTER TABLE public.precios_registro DROP COLUMN IF EXISTS campos_modificados;
ALTER TABLE public.precios_registro DROP COLUMN IF EXISTS observacion_id;
ALTER TABLE public.precios_registro DROP COLUMN IF EXISTS scraping_run_id;

DROP TABLE IF EXISTS public.ofertas_actuales;
DROP TABLE IF EXISTS public.scraping_runs;
DROP TABLE IF EXISTS public.variantes_perfume;
```

---

## 3. Plan de Contingencia en la Aplicación Python
Si el conector Supabase falla en producción:
- La aplicación cuenta con un interruptor automático hacia SQLite local (`get_connection()`).
- Los scrapers reportan el fallo en log y suspenden la sincronización sin corromper el estado anterior.
- Los usuarios de Streamlit continúan visualizando el catálogo y precios desde la réplica local sin downtime.
