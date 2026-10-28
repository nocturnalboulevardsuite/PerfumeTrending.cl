-- =====================================================================
-- PerfumeTrending.cl — Migración 20261027000010
-- Endurecimiento Integral de Seguridad (RLS + Storage + RPCs),
-- Corrección Transaccional de Precios y Tablas de Usuarios/Favoritos
-- =====================================================================
-- Idempotente y segura para ejecutar en el SQL Editor de Supabase.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. ELIMINAR POLÍTICAS RLS ABIERTAS DE ESCRITURA / LECTURA INTERNA
-- ---------------------------------------------------------------------
-- Migración 00 dejó políticas FOR ALL USING (true) abiertas a anon/authenticated:
DROP POLICY IF EXISTS "Escritura tiendas" ON public.tiendas;
DROP POLICY IF EXISTS "Escritura perfumes" ON public.perfumes;
DROP POLICY IF EXISTS "Escritura precios" ON public.precios_registro;
DROP POLICY IF EXISTS "Escritura tendencias" ON public.tendencias_metricas;
DROP POLICY IF EXISTS "Lectura publica scraping_logs" ON public.scraping_logs;
DROP POLICY IF EXISTS "Escritura scraping_logs" ON public.scraping_logs;

-- Migración 07 dejó lectura pública en tablas internas de auditoría/staging:
DROP POLICY IF EXISTS "Lectura interna importacion notas" ON public.perfume_notas_importacion;
DROP POLICY IF EXISTS "Lectura scraping_runs" ON public.scraping_runs;

-- Asegurar políticas explícitas de escritura SOLO para service_role
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tiendas','perfumes','variantes_perfume','ofertas_actuales',
    'precios_registro','tendencias_metricas','scraping_runs',
    'scraping_logs','perfume_notas_importacion'
  ] LOOP
    IF to_regclass('public.' || t) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
      EXECUTE format('DROP POLICY IF EXISTS "service_role_full_access" ON public.%I', t);
      EXECUTE format(
        'CREATE POLICY "service_role_full_access" ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)',
        t
      );
    END IF;
  END LOOP;
END $$;

-- Revocar privilegios directos de escritura/lectura interna a anon y authenticated
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM anon, authenticated;

DO $$
DECLARE t_int text;
BEGIN
  FOREACH t_int IN ARRAY ARRAY['scraping_runs', 'scraping_logs', 'perfume_notas_importacion'] LOOP
    IF to_regclass('public.' || t_int) IS NOT NULL THEN
      EXECUTE format('REVOKE SELECT ON public.%I FROM anon, authenticated', t_int);
    END IF;
  END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- 2. ENDURECER BUCKET DE IMÁGENES EN SUPABASE STORAGE (IMG_perfumes)
-- ---------------------------------------------------------------------
-- Mantener lectura pública de imágenes de catálogo, pero restringir
-- subida, modificación y borrado exclusivamente a service_role.
DROP POLICY IF EXISTS "Permitir subida IMG_perfumes" ON storage.objects;
DROP POLICY IF EXISTS "Permitir actualizacion IMG_perfumes" ON storage.objects;
DROP POLICY IF EXISTS "Permitir borrado IMG_perfumes" ON storage.objects;
DROP POLICY IF EXISTS "Permitir subida IMG_perfumes service_role" ON storage.objects;
DROP POLICY IF EXISTS "Permitir actualizacion IMG_perfumes service_role" ON storage.objects;
DROP POLICY IF EXISTS "Permitir borrado IMG_perfumes service_role" ON storage.objects;

CREATE POLICY "Permitir subida IMG_perfumes service_role"
ON storage.objects FOR INSERT TO service_role
WITH CHECK (bucket_id = 'IMG_perfumes');

CREATE POLICY "Permitir actualizacion IMG_perfumes service_role"
ON storage.objects FOR UPDATE TO service_role
USING (bucket_id = 'IMG_perfumes')
WITH CHECK (bucket_id = 'IMG_perfumes');

CREATE POLICY "Permitir borrado IMG_perfumes service_role"
ON storage.objects FOR DELETE TO service_role
USING (bucket_id = 'IMG_perfumes');

-- ---------------------------------------------------------------------
-- 3. INTEGRIDAD ESQUEMÁTICA Y DOMINIO OFICIAL DE TIENDAS
-- ---------------------------------------------------------------------
-- Permitir precio_normal NULL en precios_registro o usar precio_actual como respaldo
ALTER TABLE public.precios_registro
    ALTER COLUMN precio_normal DROP NOT NULL;

-- Actualizar dominio oficial de Alisha Perfumes
UPDATE public.tiendas
SET url_base = 'https://alishaperfumes.cl'
WHERE nombre = 'Alisha Perfumes' AND url_base = 'https://www.alisha.cl';

-- Índice único funcional de catálogo respetando ediciones por género
-- (ej. Afnan 9 PM Hombre != Afnan 9 PM Mujer; Versace Eros Hombre != Mujer; D&G Light Blue Hombre != Mujer)
DROP INDEX IF EXISTS public.ux_perfumes_marca_nombre_tipo;
CREATE UNIQUE INDEX IF NOT EXISTS ux_perfumes_marca_nombre_tipo_genero
    ON public.perfumes (
        LOWER(TRIM(marca)),
        LOWER(TRIM(nombre)),
        LOWER(COALESCE(TRIM(tipo), '')),
        LOWER(COALESCE(NULLIF(TRIM(genero), ''), 'unisex'))
    );

CREATE UNIQUE INDEX IF NOT EXISTS ux_variantes_perfume_presentacion
    ON public.variantes_perfume (
        perfume_id,
        COALESCE(ROUND(volumen_ml, 2), 100),
        LOWER(COALESCE(NULLIF(TRIM(formato), ''), 'regular'))
    );

-- ---------------------------------------------------------------------
-- 4. REPARAR FUNCIONES RPC TRANSACCIONALES Y REVOCAR ACCESO PÚBLICO
-- ---------------------------------------------------------------------
-- Eliminar función duplicada legado upsert_oferta
DROP FUNCTION IF EXISTS public.upsert_oferta(BIGINT, BIGINT, INTEGER, INTEGER, BOOLEAN, TEXT, BIGINT);

-- Reparar registrar_observacion_oferta:
-- 1) Resuelve COALESCE(p_precio_normal, v_oferta.precio_normal, p_precio_actual) evitando rollbacks.
-- 2) Descarta precios fuera de rango comercial (< 4000 o >= 1000000).
CREATE OR REPLACE FUNCTION public.registrar_observacion_oferta(
    p_variante_id BIGINT,
    p_tienda_id BIGINT,
    p_precio_actual INTEGER,
    p_precio_normal INTEGER,
    p_en_stock BOOLEAN,
    p_url_producto TEXT,
    p_scraping_run_id BIGINT DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_oferta public.ofertas_actuales%ROWTYPE;
    v_perfume_id BIGINT;
    v_volumen_ml NUMERIC(8,2);
    v_campos TEXT[] := ARRAY[]::TEXT[];
    v_tipo_evento TEXT;
    v_resultado TEXT;
    v_precio_anterior INTEGER;
    v_stock_anterior BOOLEAN;
    v_url_anterior TEXT;
    v_es_nueva BOOLEAN := FALSE;
    v_observacion_id UUID := gen_random_uuid();
    v_precio_normal_final INTEGER;
BEGIN
    IF p_variante_id IS NULL OR p_tienda_id IS NULL THEN
        RAISE EXCEPTION 'variante_id y tienda_id son obligatorios';
    END IF;
    IF p_precio_actual IS NULL OR p_precio_actual < 4000 OR p_precio_actual >= 1000000 THEN
        RAISE EXCEPTION 'El precio actual confirmado está fuera de rango comercial válido';
    END IF;
    IF p_precio_normal IS NOT NULL AND p_precio_normal <= 0 THEN
        RAISE EXCEPTION 'El precio normal debe ser positivo o NULL';
    END IF;
    IF p_en_stock IS NULL THEN
        RAISE EXCEPTION 'El stock debe ser explícito (TRUE o FALSE)';
    END IF;
    IF p_url_producto IS NULL OR length(trim(p_url_producto)) = 0
       OR p_url_producto !~* '^https?://' THEN
        RAISE EXCEPTION 'Se requiere una URL HTTP(S) válida';
    END IF;

    SELECT perfume_id, volumen_ml
      INTO v_perfume_id, v_volumen_ml
    FROM public.variantes_perfume
    WHERE id = p_variante_id AND activa = TRUE;

    IF v_perfume_id IS NULL THEN
        RAISE EXCEPTION 'La variante no existe o está inactiva';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.tiendas WHERE id = p_tienda_id) THEN
        RAISE EXCEPTION 'La tienda no existe';
    END IF;

    v_precio_normal_final := COALESCE(p_precio_normal, p_precio_actual);

    SELECT * INTO v_oferta
    FROM public.ofertas_actuales
    WHERE variante_id = p_variante_id AND tienda_id = p_tienda_id
    FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO public.ofertas_actuales (
            variante_id, tienda_id, precio_actual, precio_normal, en_stock, url_producto,
            estado, ultima_verificacion_exitosa, ultimo_intento, ultimo_cambio_confirmado,
            fallos_consecutivos, ultimo_error, created_at, updated_at
        ) VALUES (
            p_variante_id, p_tienda_id, p_precio_actual, v_precio_normal_final, p_en_stock, trim(p_url_producto),
            CASE WHEN p_en_stock THEN 'activa' ELSE 'agotada' END,
            NOW(), NOW(), NOW(), 0, NULL, NOW(), NOW()
        )
        ON CONFLICT (variante_id, tienda_id) DO NOTHING
        RETURNING * INTO v_oferta;

        IF FOUND THEN
            v_es_nueva := TRUE;
            v_resultado := 'creada';
            v_tipo_evento := 'observacion_inicial';
            v_campos := ARRAY['precio_actual', 'en_stock', 'url_producto'];
            IF p_precio_normal IS NOT NULL THEN
                v_campos := array_append(v_campos, 'precio_normal');
            END IF;
        ELSE
            SELECT * INTO v_oferta
            FROM public.ofertas_actuales
            WHERE variante_id = p_variante_id AND tienda_id = p_tienda_id
            FOR UPDATE;
        END IF;
    END IF;

    IF NOT v_es_nueva THEN
        v_precio_anterior := v_oferta.precio_actual;
        v_stock_anterior := v_oferta.en_stock;
        v_url_anterior := v_oferta.url_producto;
        v_precio_normal_final := COALESCE(p_precio_normal, v_oferta.precio_normal, p_precio_actual);

        IF v_oferta.precio_actual IS DISTINCT FROM p_precio_actual THEN
            v_campos := array_append(v_campos, 'precio_actual');
        END IF;
        IF v_oferta.en_stock IS DISTINCT FROM p_en_stock THEN
            v_campos := array_append(v_campos, 'en_stock');
        END IF;
        IF v_oferta.url_producto IS DISTINCT FROM trim(p_url_producto) THEN
            v_campos := array_append(v_campos, 'url_producto');
        END IF;
        IF p_precio_normal IS NOT NULL AND v_oferta.precio_normal IS DISTINCT FROM p_precio_normal THEN
            v_campos := array_append(v_campos, 'precio_normal');
        END IF;

        IF cardinality(v_campos) = 0 THEN
            UPDATE public.ofertas_actuales
            SET ultima_verificacion_exitosa = NOW(), ultimo_intento = NOW(),
                fallos_consecutivos = 0, ultimo_error = NULL,
                estado = CASE WHEN p_en_stock THEN 'activa' ELSE 'agotada' END,
                updated_at = NOW()
            WHERE id = v_oferta.id;

            RETURN jsonb_build_object(
                'oferta_id', v_oferta.id, 'resultado', 'sin_cambios',
                'tipo_evento', NULL, 'campos_modificados', v_campos
            );
        END IF;

        IF cardinality(v_campos) > 1 THEN
            v_tipo_evento := 'cambio_multiple';
        ELSIF v_campos[1] = 'precio_actual' THEN
            v_tipo_evento := 'cambio_precio';
        ELSIF v_campos[1] = 'en_stock' THEN
            v_tipo_evento := 'cambio_stock';
        ELSIF v_campos[1] = 'url_producto' THEN
            v_tipo_evento := 'cambio_url';
        ELSE
            v_tipo_evento := 'cambio_datos';
        END IF;

        UPDATE public.ofertas_actuales
        SET precio_actual = p_precio_actual,
            precio_normal = v_precio_normal_final,
            en_stock = p_en_stock,
            url_producto = trim(p_url_producto),
            estado = CASE WHEN p_en_stock THEN 'activa' ELSE 'agotada' END,
            ultima_verificacion_exitosa = NOW(), ultimo_intento = NOW(),
            ultimo_cambio_confirmado = NOW(), fallos_consecutivos = 0,
            ultimo_error = NULL, updated_at = NOW()
        WHERE id = v_oferta.id
        RETURNING * INTO v_oferta;
        v_resultado := 'actualizada';
    END IF;

    INSERT INTO public.precios_registro (
        perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
        volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento,
        campos_modificados, observacion_id, scraping_run_id
    ) VALUES (
        v_perfume_id, p_tienda_id, p_precio_actual,
        COALESCE(v_precio_normal_final, p_precio_actual),
        p_en_stock, ROUND(COALESCE(v_volumen_ml, 100))::INTEGER, trim(p_url_producto), NOW(),
        p_variante_id, v_tipo_evento, v_campos, v_observacion_id, p_scraping_run_id
    );

    RETURN jsonb_build_object(
        'oferta_id', v_oferta.id, 'resultado', v_resultado, 'tipo_evento', v_tipo_evento,
        'campos_modificados', v_campos, 'precio_anterior', v_precio_anterior,
        'precio_nuevo', p_precio_actual, 'stock_anterior', v_stock_anterior,
        'stock_nuevo', p_en_stock, 'url_anterior', v_url_anterior,
        'url_nueva', trim(p_url_producto)
    );
END;
$$;

-- Reparar registrar_fallo_scraping:
-- Tras 5 fallos consecutivos retira la oferta a 'requiere_revision' sin borrar el último precio histórico.
CREATE OR REPLACE FUNCTION public.registrar_fallo_scraping(
    p_variante_id BIGINT,
    p_tienda_id BIGINT,
    p_mensaje TEXT
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_oferta public.ofertas_actuales%ROWTYPE;
    v_nuevos_fallos INTEGER;
BEGIN
    IF p_tienda_id IS NULL THEN
        RAISE EXCEPTION 'tienda_id es obligatorio';
    END IF;
    IF p_mensaje IS NULL OR length(trim(p_mensaje)) = 0 THEN
        RAISE EXCEPTION 'Debe indicarse el motivo del fallo';
    END IF;
    IF p_variante_id IS NULL THEN
        RETURN jsonb_build_object('resultado', 'fallo_sin_variante');
    END IF;

    SELECT * INTO v_oferta
    FROM public.ofertas_actuales
    WHERE variante_id = p_variante_id AND tienda_id = p_tienda_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('resultado', 'fallo_sin_oferta', 'mensaje', left(p_mensaje, 2000));
    END IF;

    v_nuevos_fallos := COALESCE(v_oferta.fallos_consecutivos, 0) + 1;

    UPDATE public.ofertas_actuales
    SET ultimo_intento = NOW(),
        fallos_consecutivos = v_nuevos_fallos,
        ultimo_error = left(p_mensaje, 2000),
        estado = CASE WHEN v_nuevos_fallos >= 5 THEN 'requiere_revision' ELSE estado END,
        updated_at = NOW()
    WHERE id = v_oferta.id
    RETURNING * INTO v_oferta;

    RETURN jsonb_build_object(
        'resultado', 'fallo_registrado',
        'oferta_id', v_oferta.id,
        'fallos_consecutivos', v_oferta.fallos_consecutivos,
        'estado', v_oferta.estado,
        'precio_actual', v_oferta.precio_actual,
        'en_stock', v_oferta.en_stock
    );
END;
$$;

-- Restringir ejecución de RPCs exclusivamente a service_role
REVOKE EXECUTE ON FUNCTION public.registrar_observacion_oferta(BIGINT, BIGINT, INTEGER, INTEGER, BOOLEAN, TEXT, BIGINT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registrar_observacion_oferta(BIGINT, BIGINT, INTEGER, INTEGER, BOOLEAN, TEXT, BIGINT)
    TO service_role;

REVOKE EXECUTE ON FUNCTION public.registrar_fallo_scraping(BIGINT, BIGINT, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registrar_fallo_scraping(BIGINT, BIGINT, TEXT)
    TO service_role;

-- ---------------------------------------------------------------------
-- 5. TABLAS CLOUD DE PERFILES Y FAVORITOS CON RLS POR auth.uid()
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.perfiles_usuario (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL UNIQUE,
    telefono TEXT NOT NULL DEFAULT '',
    ubicacion TEXT NOT NULL DEFAULT 'Santiago, Chile',
    bio TEXT NOT NULL DEFAULT '',
    foto_perfil TEXT NOT NULL DEFAULT '',
    alerta_email BOOLEAN NOT NULL DEFAULT TRUE,
    notif_stock BOOLEAN NOT NULL DEFAULT TRUE,
    notif_resumen BOOLEAN NOT NULL DEFAULT FALSE,
    umbral_descuento INTEGER NOT NULL DEFAULT 10 CHECK (umbral_descuento BETWEEN 1 AND 90),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.favoritos_usuario (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    perfume_id BIGINT NOT NULL REFERENCES public.perfumes(id) ON DELETE CASCADE,
    precio_guardado INTEGER,
    fecha_agregado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_favoritos_usuario_perfume UNIQUE (usuario_id, perfume_id)
);

CREATE INDEX IF NOT EXISTS idx_favoritos_usuario_uid ON public.favoritos_usuario(usuario_id);

ALTER TABLE public.perfiles_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.favoritos_usuario ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "perfil_propio_select" ON public.perfiles_usuario;
CREATE POLICY "perfil_propio_select" ON public.perfiles_usuario
    FOR SELECT TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "perfil_propio_insert" ON public.perfiles_usuario;
CREATE POLICY "perfil_propio_insert" ON public.perfiles_usuario
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "perfil_propio_update" ON public.perfiles_usuario;
CREATE POLICY "perfil_propio_update" ON public.perfiles_usuario
    FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "service_role_perfiles" ON public.perfiles_usuario;
CREATE POLICY "service_role_perfiles" ON public.perfiles_usuario
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "favoritos_propios_all" ON public.favoritos_usuario;
CREATE POLICY "favoritos_propios_all" ON public.favoritos_usuario
    FOR ALL TO authenticated USING (auth.uid() = usuario_id) WITH CHECK (auth.uid() = usuario_id);

DROP POLICY IF EXISTS "service_role_favoritos" ON public.favoritos_usuario;
CREATE POLICY "service_role_favoritos" ON public.favoritos_usuario
    FOR ALL TO service_role USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON public.perfiles_usuario TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.favoritos_usuario TO authenticated;
GRANT ALL ON public.perfiles_usuario, public.favoritos_usuario TO service_role;

COMMIT;

