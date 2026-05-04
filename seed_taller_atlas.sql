DO $$
DECLARE
    v_persona_id BIGINT;
    v_taller_id BIGINT;
BEGIN
    INSERT INTO public.persona (
        nombre,
        apellido,
        ci,
        telefono,
        direccion
    )
    VALUES (
        'Admin',
        'Atlas',
        'CI-ATLAS-001',
        '70000999',
        'Santa Cruz de la Sierra'
    )
    RETURNING id_persona INTO v_persona_id;

    INSERT INTO public.usuario (
        id_persona,
        email,
        password_hash,
        tipo_usuario,
        activo,
        intentos,
        bloqueado
    )
    VALUES (
        v_persona_id,
        'admin.atlas@taller.com',
        'pbkdf2_sha256$390000$aGK9LXP1J3-pWhjYQjp-7A==$FzZADSNdtkm0SVuzHBu8ahmvLyxQrCLo0laRja-uRrQ=',
        'ADMINISTRADOR',
        true,
        0,
        false
    );

    INSERT INTO public.taller (
        nombre_comercial,
        descripcion,
        latitud,
        longitud,
        radio_accion_km,
        reputacion_prom,
        acepta_seguro_propio,
        activo
    )
    VALUES (
        'Taller Atlas',
        'Taller demo alternativo para pruebas de matchmaking.',
        -17.7900,
        -63.1800,
        20.00,
        4.80,
        true,
        true
    )
    RETURNING id_taller INTO v_taller_id;

    INSERT INTO public.administrador (
        id_persona,
        id_taller,
        activo
    )
    VALUES (
        v_persona_id,
        v_taller_id,
        true
    );

    INSERT INTO public.taller_especialidad (
        id_taller,
        id_especialidad,
        activo
    )
    VALUES
        (v_taller_id, 2, true), -- Electricidad
        (v_taller_id, 4, true), -- Llantas
        (v_taller_id, 7, true), -- Mecánica
        (v_taller_id, 8, true); -- Aire acondicionado

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
            4,
            'Cambio de llantas y parches',
            'Servicio de auxilio para pinchaduras, cambio de llanta y revisión básica.',
            55.00,
            85.00,
            true,
            true
        ),
        (
            v_taller_id,
            2,
            'Revisión eléctrica básica',
            'Diagnóstico inicial de batería, fusibles y sistema eléctrico.',
            60.00,
            110.00,
            false,
            true
        ),
        (
            v_taller_id,
            7,
            'Auxilio mecánico básico',
            'Revisión mecánica inicial para fallas generales del vehículo.',
            70.00,
            140.00,
            false,
            true
        ),
        (
            v_taller_id,
            8,
            'Revisión de aire acondicionado',
            'Diagnóstico básico del sistema de aire acondicionado vehicular.',
            65.00,
            120.00,
            false,
            true
        );

END $$;