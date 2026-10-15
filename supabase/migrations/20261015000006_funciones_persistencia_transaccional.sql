-- =====================================================================
-- PerfumeTrending.cl — Migración 20261015000006
-- Funciones PL/pgSQL de Persistencia Transaccional Atómica
-- =====================================================================

-- 1. Función Atómica de Registro de Observación de Oferta
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
    -- Validaciones de Dominio Estrictas
    IF p_variante_id IS NULL OR p_tienda_id IS NULL THEN
        RAISE EXCEPTION 'variante_id y tienda_id son obligatorios';
    END IF;
    IF p_precio_actual IS NULL OR p_precio_actual <= 0 THEN
        RAISE EXCEPTION 'El precio actual confirmado debe ser positivo';
    END IF;
    IF p_precio_normal IS NOT NULL AND p_precio_normal <= 0 THEN
        RAISE EXCEPTION 'El precio normal debe ser positivo o NULL';
    END IF;
    IF p_en_stock IS NULL THEN
        RAISE EXCEPTION 'El stock debe ser explícito (TRUE o FALSE), no desconocido';
    END IF;
    IF p_url_producto IS NULL OR length(trim(p_url_producto)) = 0
       OR p_url_producto !~* '^https?://' THEN
        RAISE EXCEPTION 'Se requiere una URL HTTP(S) válida';
    END IF;

    -- Verificar existencia de variante activa y tienda
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

    -- Bloqueo pesimista para evitar carreras entre scrapers concurrentes
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
            p_variante_id, p_tienda_id, p_precio_actual, p_precio_normal, p_en_stock, trim(p_url_producto),
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
        v_precio_normal_final := COALESCE(p_precio_normal, v_oferta.precio_normal);

        IF v_oferta.precio_actual IS DISTINCT FROM p_precio_actual THEN
            v_campos := array_append(v_campos, 'precio_actual');
        END IF;
        IF v_oferta.en_stock IS DISTINCT FROM p_en_stock THEN
            v_campos := array_append(v_campos, 'en_stock');
        END IF;
        IF v_oferta.url_producto IS DISTINCT FROM trim(p_url_producto) THEN
            v_campos := array_append(v_campos, 'url_producto');
        END IF;
        IF v_oferta.precio_normal IS DISTINCT FROM v_precio_normal_final THEN
            v_campos := array_append(v_campos, 'precio_normal');
        END IF;

        -- Si no hubo ningún cambio, solo actualizar verificación sin registrar historial
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

    -- Inserción inmutable en precios_registro (misma transacción)
    INSERT INTO public.precios_registro (
        perfume_id, tienda_id, precio_actual, precio_normal, en_stock,
        volumen_ml, url_producto, fecha_registro, variante_id, tipo_evento,
        campos_modificados, observacion_id, scraping_run_id
    ) VALUES (
        v_perfume_id, p_tienda_id, p_precio_actual,
        COALESCE(p_precio_normal, v_oferta.precio_normal),
        p_en_stock, v_volumen_ml, trim(p_url_producto), NOW(),
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

-- 2. Función Atómica para Registrar Fallos de Scraping Sin Alterar Datos Confirmados
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
        -- No crear oferta ficticia
        RETURN jsonb_build_object('resultado', 'fallo_sin_oferta', 'mensaje', left(p_mensaje, 2000));
    END IF;

    UPDATE public.ofertas_actuales
    SET ultimo_intento = NOW(),
        fallos_consecutivos = fallos_consecutivos + 1,
        ultimo_error = left(p_mensaje, 2000),
        updated_at = NOW()
    WHERE id = v_oferta.id
    RETURNING * INTO v_oferta;

    RETURN jsonb_build_object(
        'resultado', 'fallo_registrado',
        'oferta_id', v_oferta.id,
        'fallos_consecutivos', v_oferta.fallos_consecutivos,
        'precio_actual', v_oferta.precio_actual,
        'en_stock', v_oferta.en_stock
    );
END;
$$;
