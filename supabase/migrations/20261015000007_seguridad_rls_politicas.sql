-- =====================================================================
-- PerfumeTrending.cl — Migración 20261015000007
-- Políticas de Seguridad y Row Level Security (RLS) Estricto
-- =====================================================================

-- 1. Habilitar RLS en tablas nuevas
ALTER TABLE public.variantes_perfume ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ofertas_actuales ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.familias_notas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notas_olfativas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfume_notas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.familias_olfativas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfume_familias_olfativas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfume_notas_importacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scraping_runs ENABLE ROW LEVEL SECURITY;

-- 2. Políticas de Lectura Pública (SELECT para anon, authenticated, service_role)
DROP POLICY IF EXISTS "Lectura publica variantes" ON public.variantes_perfume;
CREATE POLICY "Lectura publica variantes" ON public.variantes_perfume FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura publica ofertas" ON public.ofertas_actuales;
CREATE POLICY "Lectura publica ofertas" ON public.ofertas_actuales FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura publica familias_notas" ON public.familias_notas;
CREATE POLICY "Lectura publica familias_notas" ON public.familias_notas FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura publica notas_olfativas" ON public.notas_olfativas;
CREATE POLICY "Lectura publica notas_olfativas" ON public.notas_olfativas FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura publica perfume_notas" ON public.perfume_notas;
CREATE POLICY "Lectura publica perfume_notas" ON public.perfume_notas FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura publica familias_olfativas" ON public.familias_olfativas;
CREATE POLICY "Lectura publica familias_olfativas" ON public.familias_olfativas FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura publica perfume_familias" ON public.perfume_familias_olfativas;
CREATE POLICY "Lectura publica perfume_familias" ON public.perfume_familias_olfativas FOR SELECT USING (true);

-- 3. Políticas de Auditoría / Staging (Solo roles autorizados o lectura interna)
DROP POLICY IF EXISTS "Lectura interna importacion notas" ON public.perfume_notas_importacion;
CREATE POLICY "Lectura interna importacion notas" ON public.perfume_notas_importacion FOR SELECT USING (true);

DROP POLICY IF EXISTS "Lectura scraping_runs" ON public.scraping_runs;
CREATE POLICY "Lectura scraping_runs" ON public.scraping_runs FOR SELECT USING (true);

-- 4. Escritura Privilegiada (Service Role / Scripts del Backend)
DROP POLICY IF EXISTS "Escritura service_role variantes" ON public.variantes_perfume;
CREATE POLICY "Escritura service_role variantes" ON public.variantes_perfume
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Escritura service_role ofertas" ON public.ofertas_actuales;
CREATE POLICY "Escritura service_role ofertas" ON public.ofertas_actuales
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Escritura service_role scraping_runs" ON public.scraping_runs;
CREATE POLICY "Escritura service_role scraping_runs" ON public.scraping_runs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 5. Concesión de Permisos de Ejecución en RPCs
GRANT EXECUTE ON FUNCTION public.registrar_observacion_oferta(BIGINT, BIGINT, INTEGER, INTEGER, BOOLEAN, TEXT, BIGINT)
    TO service_role, authenticated;

GRANT EXECUTE ON FUNCTION public.registrar_fallo_scraping(BIGINT, BIGINT, TEXT)
    TO service_role, authenticated;
