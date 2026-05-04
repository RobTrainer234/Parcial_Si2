DO $$
DECLARE
    v_taller_id BIGINT;
BEGIN
    SELECT id_taller
    INTO v_taller_id
    FROM public.taller
    WHERE nombre_comercial = 'Taller Atlas';

    IF v_taller_id IS NULL THEN
        RAISE EXCEPTION 'Taller Atlas no existe.';
    END IF;

    DELETE FROM public.catalogo_servicio_taller
    WHERE id_taller = v_taller_id;

    DELETE FROM public.taller_especialidad
    WHERE id_taller = v_taller_id;

    INSERT INTO public.taller_especialidad (
        id_taller,
        id_especialidad,
        activo
    )
    VALUES
        (v_taller_id, 1, true), -- MECANICA_GENERAL
        (v_taller_id, 3, true), -- GRUA
        (v_taller_id, 5, true), -- BATERIA
        (v_taller_id, 6, true); -- DIAGNOSTICO_GENERAL

    INSERT INTO public.catalogo_servicio_taller (
        id_taller,
        id_especialidad,
        nombre,
        descripcion,
        precio_base_min,
        precio_base_max,
        incluye_repuestos_basicos,
        activo
    )
    VALUES
        (
            v_taller_id,
            5,
            'Auxilio por batería',
            'Servicio para batería descargada, revisión básica y apoyo de encendido.',
            50.00,
            90.00,
            false,
            true
        ),
        (
            v_taller_id,
            3,
            'Servicio de grúa',
            'Traslado del vehículo cuando no puede continuar circulando.',
            120.00,
            250.00,
            false,
            true
        ),
        (
            v_taller_id,
            1,
            'Revisión mecánica general',
            'Diagnóstico mecánico inicial para fallas generales del vehículo.',
            70.00,
            140.00,
            false,
            true
        ),
        (
            v_taller_id,
            6,
            'Diagnóstico general vehicular',
            'Evaluación inicial para identificar el tipo de problema reportado.',
            40.00,
            80.00,
            false,
            false
        );
END $$;