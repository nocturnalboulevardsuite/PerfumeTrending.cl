-- =====================================================================
-- PerfumeTrending.cl — MIGRACIÓN: Vistas Optimizadas, Índices Únicos y RPC upsert_oferta
-- =====================================================================
-- Este script complementario añade las vistas de alto rendimiento con security_invoker,
-- índices únicos condicionales y la función RPC upsert_oferta.
-- Puede ejecutarse en el SQL Editor de Supabase:
-- https://supabase.com/dashboard/project/miqscdupnknhjemvcjil/sql/new
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- PASO 1: Restricciones e índices únicos
-- ---------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS ux_ofertas_variante_tienda
  ON public.ofertas_actuales (variante_id, tienda_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_perfume_notas
  ON public.perfume_notas (perfume_id, nota_id, etapa);

CREATE UNIQUE INDEX IF NOT EXISTS ux_perfume_familia
  ON public.perfume_familias_olfativas (perfume_id, familia_id);

-- Solo una familia principal por perfume
CREATE UNIQUE INDEX IF NOT EXISTS ux_perfume_familia_principal
  ON public.perfume_familias_olfativas (perfume_id)
  WHERE es_principal;

-- ---------------------------------------------------------------------
-- PASO 2: Índices en claves foráneas y consultas frecuentes
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_precios_variante_tienda_fecha
  ON public.precios_registro (variante_id, tienda_id, fecha_registro DESC);
CREATE INDEX IF NOT EXISTS ix_precios_perfume      ON public.precios_registro (perfume_id);
CREATE INDEX IF NOT EXISTS ix_precios_tienda       ON public.precios_registro (tienda_id);
CREATE INDEX IF NOT EXISTS ix_precios_scraping_run ON public.precios_registro (scraping_run_id);

CREATE INDEX IF NOT EXISTS ix_ofertas_tienda       ON public.ofertas_actuales (tienda_id);
CREATE INDEX IF NOT EXISTS ix_variantes_perfume    ON public.variantes_perfume (perfume_id);
CREATE INDEX IF NOT EXISTS ix_perfume_notas_nota   ON public.perfume_notas (nota_id);
CREATE INDEX IF NOT EXISTS ix_notas_familia        ON public.notas_olfativas (familia_id);
CREATE INDEX IF NOT EXISTS ix_pfo_familia          ON public.perfume_familias_olfativas (familia_id);
CREATE INDEX IF NOT EXISTS ix_familias_olf_padre   ON public.familias_olfativas (padre_id);
CREATE INDEX IF NOT EXISTS ix_tendencias_perfume_fecha
  ON public.tendencias_metricas (perfume_id, fecha_analisis DESC);
CREATE INDEX IF NOT EXISTS ix_runs_tienda_fecha
  ON public.scraping_runs (tienda_id, fecha_inicio DESC);

-- ---------------------------------------------------------------------
-- PASO 3: Row Level Security
-- ---------------------------------------------------------------------
-- 3a) Datos públicos: lectura abierta, escritura solo con service_role
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'perfumes','tiendas','variantes_perfume','ofertas_actuales',
    'precios_registro','perfume_notas','notas_olfativas','familias_notas',
    'familias_olfativas','perfume_familias_olfativas','tendencias_metricas'
  ] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS "lectura publica" ON public.%I', t);
    EXECUTE format('CREATE POLICY "lectura publica" ON public.%I FOR SELECT USING (true)', t);
  END LOOP;
END $$;

-- 3b) Datos internos: RLS activado y SIN políticas
--     (anon/authenticated no ven nada; service_role se salta el RLS)
ALTER TABLE public.scraping_runs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scraping_logs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfume_notas_importacion ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- PASO 4: Vistas de salida (security_invoker = true => respetan el RLS)
-- ---------------------------------------------------------------------

-- 4a) Mejor precio vigente por variante
CREATE OR REPLACE VIEW public.mejor_precio_por_variante
WITH (security_invoker = true) AS
SELECT DISTINCT ON (o.variante_id)
  o.variante_id,
  p.id            AS perfume_id,
  p.nombre,
  p.marca,
  v.volumen_ml,
  v.concentracion,
  t.id            AS tienda_id,
  t.nombre        AS tienda,
  t.trust_score,
  o.precio_actual,
  o.precio_normal,
  CASE WHEN o.precio_normal > 0
       THEN round((1 - o.precio_actual::numeric / o.precio_normal) * 100, 1)
  END             AS descuento_pct,
  o.url_producto,
  o.ultima_verificacion_exitosa
FROM public.ofertas_actuales o
JOIN public.variantes_perfume v ON v.id = o.variante_id AND v.activa
JOIN public.perfumes p          ON p.id = v.perfume_id
JOIN public.tiendas t           ON t.id = o.tienda_id
WHERE o.estado = 'activa'
  AND coalesce(o.en_stock, false)
  AND o.precio_actual IS NOT NULL
ORDER BY o.variante_id, o.precio_actual ASC;

-- 4b) Ofertas con descuento real (reemplaza el flag perfumes.en_remate)
CREATE OR REPLACE VIEW public.ofertas_con_descuento
WITH (security_invoker = true) AS
SELECT *
FROM public.mejor_precio_por_variante
WHERE precio_normal IS NOT NULL
  AND precio_actual < precio_normal
ORDER BY descuento_pct DESC;

-- 4c) Historial de precios para gráficos
CREATE OR REPLACE VIEW public.historial_precio_variante
WITH (security_invoker = true) AS
SELECT
  r.variante_id,
  r.tienda_id,
  t.nombre AS tienda,
  r.precio_actual,
  r.precio_normal,
  r.en_stock,
  r.fecha_registro
FROM public.precios_registro r
JOIN public.tiendas t ON t.id = r.tienda_id
WHERE r.variante_id IS NOT NULL;

-- 4d) Perfumes por nota olfativa
CREATE OR REPLACE VIEW public.perfumes_por_nota
WITH (security_invoker = true) AS
SELECT
  n.id     AS nota_id,
  n.slug   AS nota_slug,
  n.nombre AS nota,
  g.nombre AS grupo_nota,
  pn.etapa,
  p.id     AS perfume_id,
  p.nombre,
  p.marca,
  p.imagen_url
FROM public.perfume_notas pn
JOIN public.notas_olfativas n ON n.id = pn.nota_id AND n.activa
JOIN public.familias_notas g  ON g.id = n.familia_id
JOIN public.perfumes p        ON p.id = pn.perfume_id;

-- 4e) Ranking de tendencias (última métrica por perfume)
CREATE OR REPLACE VIEW public.ranking_tendencias
WITH (security_invoker = true) AS
SELECT DISTINCT ON (m.perfume_id)
  m.perfume_id,
  p.nombre,
  p.marca,
  p.imagen_url,
  m.score_hype,
  m.menciones_semanales,
  m.tasa_crecimiento,
  m.plataforma,
  m.fecha_analisis
FROM public.tendencias_metricas m
JOIN public.perfumes p ON p.id = m.perfume_id
ORDER BY m.perfume_id, m.fecha_analisis DESC;

-- 4f) Salud de scrapers (INTERNA: solo service_role)
CREATE OR REPLACE VIEW public.salud_scrapers
WITH (security_invoker = true) AS
SELECT DISTINCT ON (r.tienda_id, r.tipo_scraper)
  t.nombre AS tienda,
  r.tipo_scraper,
  r.estado,
  r.fecha_inicio,
  r.fecha_fin,
  r.productos_procesados,
  r.ofertas_nuevas,
  r.cambios_precio,
  r.cambios_stock,
  r.errores,
  r.mensaje_detalle
FROM public.scraping_runs r
LEFT JOIN public.tiendas t ON t.id = r.tienda_id
ORDER BY r.tienda_id, r.tipo_scraper, r.fecha_inicio DESC;

REVOKE ALL ON public.salud_scrapers FROM anon, authenticated;

-- ---------------------------------------------------------------------
-- PASO 5: RPC para scrapers (actualiza oferta + historial en 1 transacción)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.upsert_oferta(
  p_variante_id   bigint,
  p_tienda_id     bigint,
  p_precio_actual integer,
  p_precio_normal integer,
  p_en_stock      boolean,
  p_url_producto  text,
  p_run_id        bigint default null
) RETURNS text
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  v_old     public.ofertas_actuales%rowtype;
  v_perfume bigint;
  v_vol     numeric;
  v_campos  text[] := '{}';
  v_evento  text;
BEGIN
  SELECT perfume_id, volumen_ml INTO v_perfume, v_vol
  FROM public.variantes_perfume WHERE id = p_variante_id;

  IF v_perfume IS NULL THEN
    RAISE EXCEPTION 'Variante % no existe', p_variante_id;
  END IF;

  SELECT * INTO v_old
  FROM public.ofertas_actuales
  WHERE variante_id = p_variante_id AND tienda_id = p_tienda_id
  FOR UPDATE;

  IF NOT FOUND THEN
    INSERT INTO public.ofertas_actuales (
      variante_id, tienda_id, precio_actual, precio_normal, en_stock,
      url_producto, estado, ultima_verificacion_exitosa, ultimo_intento,
      ultimo_cambio_confirmado, fallos_consecutivos, ultimo_error
    ) VALUES (
      p_variante_id, p_tienda_id, p_precio_actual, p_precio_normal, p_en_stock,
      p_url_producto,
      CASE WHEN coalesce(p_en_stock, true) THEN 'activa' ELSE 'agotada' END,
      NOW(), NOW(), NOW(), 0, NULL
    );
    v_evento := 'nueva';
    v_campos := ARRAY['precio_actual','precio_normal','en_stock','url_producto'];
  ELSE
    IF v_old.precio_actual IS DISTINCT FROM p_precio_actual THEN
      v_campos := v_campos || 'precio_actual'; END IF;
    IF v_old.precio_normal IS DISTINCT FROM p_precio_normal THEN
      v_campos := v_campos || 'precio_normal'; END IF;
    IF v_old.en_stock IS DISTINCT FROM p_en_stock THEN
      v_campos := v_campos || 'en_stock'; END IF;
    IF v_old.url_producto IS DISTINCT FROM p_url_producto THEN
      v_campos := v_campos || 'url_producto'; END IF;

    UPDATE public.ofertas_actuales SET
      precio_actual = p_precio_actual,
      precio_normal = p_precio_normal,
      en_stock      = p_en_stock,
      url_producto  = p_url_producto,
      estado        = CASE WHEN coalesce(p_en_stock, true) THEN 'activa' ELSE 'agotada' END,
      ultima_verificacion_exitosa = NOW(),
      ultimo_intento = NOW(),
      ultimo_cambio_confirmado =
        CASE WHEN cardinality(v_campos) > 0 THEN NOW() ELSE ultimo_cambio_confirmado END,
      fallos_consecutivos = 0,
      ultimo_error  = NULL,
      updated_at    = NOW()
    WHERE id = v_old.id;

    v_evento := CASE WHEN cardinality(v_campos) > 0 THEN 'cambio' ELSE 'sin_cambio' END;
  END IF;

  -- Solo se escribe historial cuando hubo algo nuevo
  IF v_evento <> 'sin_cambio' THEN
    INSERT INTO public.precios_registro (
      perfume_id, tienda_id, variante_id, precio_actual, precio_normal,
      en_stock, volumen_ml, url_producto, tipo_evento, campos_modificados,
      scraping_run_id
    ) VALUES (
      v_perfume, p_tienda_id, p_variante_id, p_precio_actual, p_precio_normal,
      p_en_stock, round(v_vol)::int, p_url_producto, v_evento, v_campos,
      p_run_id
    );
  END IF;

  RETURN v_evento;
END;
$$;

-- Permisos
REVOKE EXECUTE ON FUNCTION public.upsert_oferta(
  bigint, bigint, integer, integer, boolean, text, bigint
) FROM public, anon, authenticated;

COMMIT;
