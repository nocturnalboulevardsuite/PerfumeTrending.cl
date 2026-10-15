-- =====================================================================
-- PerfumeTrending.cl — Migración 20261015000008
-- Poblado de Variantes Iniciales, Mapeo de Historial y Actualización de Vistas
-- =====================================================================

BEGIN;

-- 1. Generar Variantes Base desde el Historial y Catálogo Existente
-- (Agrupación determinista por perfume y volumen real)
INSERT INTO public.variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa)
SELECT DISTINCT
    p.id AS perfume_id,
    p.tipo AS concentracion,
    COALESCE(pr.volumen_ml, 100)::numeric(8,2) AS volumen_ml,
    'regular' AS formato,
    lower(regexp_replace(p.nombre || '-' || COALESCE(pr.volumen_ml, 100)::text || 'ml', '[^a-z0-9]+', '-', 'g')) AS slug,
    true AS activa
FROM public.perfumes p
LEFT JOIN public.precios_registro pr ON p.id = pr.perfume_id
WHERE pr.volumen_ml IS NOT NULL AND pr.volumen_ml > 0
ON CONFLICT (slug) DO NOTHING;

-- Si algún perfume no tenía precios aún, asegurar al menos su variante de 100ml
INSERT INTO public.variantes_perfume (perfume_id, concentracion, volumen_ml, formato, slug, activa)
SELECT
    p.id,
    p.tipo,
    100.00,
    'regular',
    lower(regexp_replace(p.nombre || '-100ml', '[^a-z0-9]+', '-', 'g')),
    true
FROM public.perfumes p
WHERE NOT EXISTS (SELECT 1 FROM public.variantes_perfume vp WHERE vp.perfume_id = p.id)
ON CONFLICT (slug) DO NOTHING;

-- 2. Vincular variante_id en precios_registro
UPDATE public.precios_registro pr
SET variante_id = vp.id
FROM public.variantes_perfume vp
WHERE pr.perfume_id = vp.perfume_id
  AND pr.volumen_ml = vp.volumen_ml
  AND pr.variante_id IS NULL;

-- 3. Poblar ofertas_actuales con el último estado confirmado por variante y tienda
-- (Sin filtrar stock antes de ordenar, para reflejar fielmente si está activa o agotada)
WITH ultimos_estados AS (
    SELECT DISTINCT ON (pr.variante_id, pr.tienda_id)
        pr.variante_id,
        pr.tienda_id,
        pr.precio_actual,
        pr.precio_normal,
        pr.en_stock,
        pr.url_producto,
        CASE WHEN pr.en_stock = TRUE THEN 'activa' ELSE 'agotada' END AS estado,
        pr.fecha_registro
    FROM public.precios_registro pr
    WHERE pr.variante_id IS NOT NULL
      AND pr.precio_actual > 0
      AND pr.url_producto IS NOT NULL
    ORDER BY pr.variante_id, pr.tienda_id, pr.fecha_registro DESC, pr.id DESC
)
INSERT INTO public.ofertas_actuales (
    variante_id, tienda_id, precio_actual, precio_normal, en_stock,
    url_producto, estado, ultima_verificacion_exitosa, ultimo_intento,
    ultimo_cambio_confirmado, fallos_consecutivos
)
SELECT
    ue.variante_id,
    ue.tienda_id,
    ue.precio_actual,
    ue.precio_normal,
    ue.en_stock,
    ue.url_producto,
    ue.estado,
    ue.fecha_registro,
    ue.fecha_registro,
    ue.fecha_registro,
    0
FROM ultimos_estados ue
ON CONFLICT (variante_id, tienda_id) DO UPDATE SET
    precio_actual = EXCLUDED.precio_actual,
    precio_normal = EXCLUDED.precio_normal,
    en_stock = EXCLUDED.en_stock,
    url_producto = EXCLUDED.url_producto,
    estado = EXCLUDED.estado,
    ultima_verificacion_exitosa = EXCLUDED.ultima_verificacion_exitosa;

-- 4. Actualizar la Vista de Precios Actuales para consultar directamente ofertas_actuales
CREATE OR REPLACE VIEW public.vista_precios_actuales AS
SELECT 
    oa.id,
    p.id AS perfume_id,
    oa.tienda_id,
    oa.precio_actual,
    oa.precio_normal,
    oa.en_stock,
    COALESCE(vp.volumen_ml, 100)::integer AS volumen_ml,
    ROUND(CAST(oa.precio_actual AS NUMERIC) / GREATEST(1, COALESCE(vp.volumen_ml, 100))) AS precio_por_ml,
    oa.url_producto,
    oa.ultima_verificacion_exitosa AS fecha_registro,
    t.nombre AS tienda_nombre,
    t.url_base,
    t.trust_score,
    t.badge,
    t.logo_emoji
FROM public.ofertas_actuales oa
JOIN public.variantes_perfume vp ON vp.id = oa.variante_id
JOIN public.perfumes p ON p.id = vp.perfume_id
JOIN public.tiendas t ON t.id = oa.tienda_id
WHERE oa.estado = 'activa' AND oa.en_stock = TRUE;

GRANT SELECT ON public.vista_precios_actuales TO anon, authenticated, service_role;

COMMIT;
