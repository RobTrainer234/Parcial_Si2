
-- DROP TABLE IF EXISTS bitacora CASCADE;
-- DROP TABLE IF EXISTS notificacion CASCADE;
-- DROP TABLE IF EXISTS dispositivo_usuario CASCADE;
-- DROP TABLE IF EXISTS calificacion CASCADE;
-- DROP TABLE IF EXISTS pago CASCADE;
-- DROP TABLE IF EXISTS metodo_pago CASCADE;
-- DROP TABLE IF EXISTS servicio_ubicacion CASCADE;
-- DROP TABLE IF EXISTS servicio_repuesto CASCADE;
-- DROP TABLE IF EXISTS servicio_informe CASCADE;
-- DROP TABLE IF EXISTS evidencia CASCADE;
-- DROP TABLE IF EXISTS servicio CASCADE;
-- DROP TABLE IF EXISTS solicitud_servicio CASCADE;
-- DROP TABLE IF EXISTS catalogo_servicio_taller CASCADE;
-- DROP TABLE IF EXISTS incidente CASCADE;
-- DROP TABLE IF EXISTS seguro CASCADE;
-- DROP TABLE IF EXISTS cobertura_especialidad CASCADE;
-- DROP TABLE IF EXISTS tipo_cobertura CASCADE;
-- DROP TABLE IF EXISTS vehiculo CASCADE;
-- DROP TABLE IF EXISTS color CASCADE;
-- DROP TABLE IF EXISTS modelo CASCADE;
-- DROP TABLE IF EXISTS marca CASCADE;
-- DROP TABLE IF EXISTS operario_especialidad CASCADE;
-- DROP TABLE IF EXISTS taller_especialidad CASCADE;
-- DROP TABLE IF EXISTS especialidad CASCADE;
-- DROP TABLE IF EXISTS operario CASCADE;
-- DROP TABLE IF EXISTS administrador CASCADE;
-- DROP TABLE IF EXISTS cliente CASCADE;
-- DROP TABLE IF EXISTS usuario CASCADE;
-- DROP TABLE IF EXISTS taller CASCADE;
-- DROP TABLE IF EXISTS persona CASCADE;

-- =========================================================
-- FUNCIONES GENERICAS
-- =========================================================
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_bitacora_set_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.hash_evento := md5(
        concat_ws('|',
            coalesce(NEW.accion, ''),
            coalesce(NEW.tipo_evento, ''),
            coalesce(NEW.entidad_principal, ''),
            coalesce(NEW.id_entidad_principal::text, ''),
            coalesce(NEW.id_usuario::text, ''),
            coalesce(NEW.id_incidente::text, ''),
            coalesce(NEW.id_solicitud::text, ''),
            coalesce(NEW.id_servicio::text, ''),
            coalesce(NEW.id_pago::text, ''),
            coalesce(NEW.fecha_hora::text, now()::text),
            coalesce(NEW.datos_originales::text, ''),
            coalesce(NEW.datos_nuevos::text, '')
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_bitacora_block_changes()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'BITACORA es append-only: no se permiten %', TG_OP;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- TABLAS MAESTRAS DE PERSONAS / USUARIOS / TALLERES
-- =========================================================
CREATE TABLE persona (
    id_persona          BIGSERIAL PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL,
    apellido            VARCHAR(100) NOT NULL,
    ci                  VARCHAR(20) NOT NULL UNIQUE,
    telefono            VARCHAR(20),
    direccion           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE taller (
    id_taller               BIGSERIAL PRIMARY KEY,
    nombre_comercial        VARCHAR(150) NOT NULL,
    descripcion             TEXT,
    latitud                 NUMERIC(10,8) NOT NULL,
    longitud                NUMERIC(11,8) NOT NULL,
    radio_accion_km         NUMERIC(6,2) NOT NULL DEFAULT 10.00 CHECK (radio_accion_km > 0),
    reputacion_prom         NUMERIC(3,2) CHECK (reputacion_prom IS NULL OR (reputacion_prom >= 0 AND reputacion_prom <= 5)),
    acepta_seguro_propio    BOOLEAN NOT NULL DEFAULT FALSE,
    activo                  BOOLEAN NOT NULL DEFAULT TRUE,
    total_expirados         INTEGER NOT NULL DEFAULT 0 CHECK (total_expirados >= 0),
    total_aceptados         INTEGER NOT NULL DEFAULT 0 CHECK (total_aceptados >= 0),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE usuario (
    id_usuario           BIGSERIAL PRIMARY KEY,
    id_persona           BIGINT NOT NULL UNIQUE REFERENCES persona(id_persona) ON DELETE CASCADE,
    email                VARCHAR(150) NOT NULL,
    password_hash        VARCHAR(255) NOT NULL,
    tipo_usuario         VARCHAR(20) NOT NULL CHECK (tipo_usuario IN ('CLIENTE','OPERARIO','ADMINISTRADOR','SUPER_ADMIN')),
    activo               BOOLEAN NOT NULL DEFAULT TRUE,
    intentos             INTEGER NOT NULL DEFAULT 0 CHECK (intentos >= 0),
    bloqueado            BOOLEAN NOT NULL DEFAULT FALSE,
    reputacion_prom      NUMERIC(3,2) CHECK (reputacion_prom IS NULL OR (reputacion_prom >= 0 AND reputacion_prom <= 5)),
    ultimo_acceso        TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_usuario_email_lower ON usuario (LOWER(email));

CREATE TABLE cliente (
    id_persona           BIGINT PRIMARY KEY REFERENCES persona(id_persona) ON DELETE CASCADE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE administrador (
    id_persona           BIGINT PRIMARY KEY REFERENCES persona(id_persona) ON DELETE CASCADE,
    id_taller            BIGINT NOT NULL REFERENCES taller(id_taller) ON DELETE RESTRICT,
    activo               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE operario (
    id_persona               BIGINT PRIMARY KEY REFERENCES persona(id_persona) ON DELETE CASCADE,
    id_taller                BIGINT NOT NULL REFERENCES taller(id_taller) ON DELETE RESTRICT,
    estado_disponibilidad    VARCHAR(20) NOT NULL DEFAULT 'DISPONIBLE'
                            CHECK (estado_disponibilidad IN ('DISPONIBLE','EN_SERVICIO','NO_DISPONIBLE','BAJA')),
    activo                   BOOLEAN NOT NULL DEFAULT TRUE,
    latitud_actual           NUMERIC(10,8),
    longitud_actual          NUMERIC(11,8),
    ultima_ubicacion_at      TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- ESPECIALIDADES Y CAPACIDAD TECNICA
-- =========================================================
CREATE TABLE especialidad (
    id_especialidad      BIGSERIAL PRIMARY KEY,
    nombre               VARCHAR(100) NOT NULL UNIQUE,
    descripcion          TEXT,
    nivel_complejidad    INTEGER NOT NULL DEFAULT 1 CHECK (nivel_complejidad BETWEEN 1 AND 5),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE taller_especialidad (
    id_taller            BIGINT NOT NULL REFERENCES taller(id_taller) ON DELETE CASCADE,
    id_especialidad      BIGINT NOT NULL REFERENCES especialidad(id_especialidad) ON DELETE CASCADE,
    activo               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_taller, id_especialidad)
);

CREATE TABLE operario_especialidad (
    id_persona           BIGINT NOT NULL REFERENCES operario(id_persona) ON DELETE CASCADE,
    id_especialidad      BIGINT NOT NULL REFERENCES especialidad(id_especialidad) ON DELETE CASCADE,
    anios_experiencia    INTEGER NOT NULL DEFAULT 0 CHECK (anios_experiencia >= 0),
    certificacion_url    TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_persona, id_especialidad)
);

-- =========================================================
-- CATALOGO DE VEHICULOS
-- =========================================================
CREATE TABLE marca (
    id_marca             BIGSERIAL PRIMARY KEY,
    nombre               VARCHAR(50) NOT NULL UNIQUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE modelo (
    id_modelo            BIGSERIAL PRIMARY KEY,
    id_marca             BIGINT NOT NULL REFERENCES marca(id_marca) ON DELETE RESTRICT,
    nombre               VARCHAR(50) NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_modelo_por_marca UNIQUE (id_marca, nombre)
);

CREATE TABLE color (
    id_color             BIGSERIAL PRIMARY KEY,
    nombre               VARCHAR(30) NOT NULL UNIQUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE vehiculo (
    id_vehiculo          BIGSERIAL PRIMARY KEY,
    placa                VARCHAR(15) NOT NULL UNIQUE,
    id_modelo            BIGINT NOT NULL REFERENCES modelo(id_modelo) ON DELETE RESTRICT,
    anio                 INTEGER NOT NULL CHECK (anio BETWEEN 1900 AND 2100),
    id_color             BIGINT NOT NULL REFERENCES color(id_color) ON DELETE RESTRICT,
    id_persona           BIGINT NOT NULL REFERENCES cliente(id_persona) ON DELETE RESTRICT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- SEGUROS Y COBERTURAS
-- =========================================================
CREATE TABLE tipo_cobertura (
    id_cobertura         BIGSERIAL PRIMARY KEY,
    nombre               VARCHAR(50) NOT NULL UNIQUE,
    descripcion_plan     TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE cobertura_especialidad (
    id_cobertura         BIGINT NOT NULL REFERENCES tipo_cobertura(id_cobertura) ON DELETE CASCADE,
    id_especialidad      BIGINT NOT NULL REFERENCES especialidad(id_especialidad) ON DELETE CASCADE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_cobertura, id_especialidad)
);

CREATE TABLE seguro (
    id_seguro            BIGSERIAL PRIMARY KEY,
    id_cliente           BIGINT NOT NULL REFERENCES cliente(id_persona) ON DELETE RESTRICT,
    id_taller            BIGINT NOT NULL REFERENCES taller(id_taller) ON DELETE RESTRICT,
    id_cobertura         BIGINT NOT NULL REFERENCES tipo_cobertura(id_cobertura) ON DELETE RESTRICT,
    numero_poliza        VARCHAR(50),
    monto_maximo         NUMERIC(12,2) CHECK (monto_maximo IS NULL OR monto_maximo >= 0),
    fecha_inicio         TIMESTAMPTZ NOT NULL,
    fecha_fin            TIMESTAMPTZ,
    activo               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_seguro_fechas CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);

-- =========================================================
-- INCIDENTES Y TRIAJE IA
-- CU02: se guarda el criterio del cliente y tambien el diagnostico IA
-- =========================================================
CREATE TABLE incidente (
    id_incidente                         BIGSERIAL PRIMARY KEY,
    fecha_hora                           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latitud                              NUMERIC(10,8) NOT NULL,
    longitud                             NUMERIC(11,8) NOT NULL,
    descripcion_cliente                  TEXT NOT NULL,
    estado                               VARCHAR(30) NOT NULL DEFAULT 'REPORTADO'
                                        CHECK (estado IN (
                                            'REPORTADO',
                                            'EN_TRIAJE',
                                            'DIAGNOSTICADO',
                                            'EN_MATCHMAKING',
                                            'EN_PROCESO',
                                            'FINALIZADO',
                                            'CANCELADO'
                                        )),
    severidad                            VARCHAR(20)
                                        CHECK (severidad IS NULL OR severidad IN ('BAJA','MEDIA','ALTA','CRITICA')),
    id_cliente                           BIGINT NOT NULL REFERENCES cliente(id_persona) ON DELETE RESTRICT,
    id_vehiculo                          BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON DELETE RESTRICT,
    id_especialidad_reportada_cliente    BIGINT NOT NULL REFERENCES especialidad(id_especialidad) ON DELETE RESTRICT,
    id_especialidad_detectada            BIGINT REFERENCES especialidad(id_especialidad) ON DELETE RESTRICT,
    diagnostico_ia_resumen               TEXT,
    diagnostico_ia_json                  JSONB,
    confianza_ia                         NUMERIC(5,2)
                                        CHECK (confianza_ia IS NULL OR (confianza_ia >= 0 AND confianza_ia <= 100)),
    transcripcion_audio                  TEXT,
    etiquetas_imagen                     JSONB,
    fecha_triaje                         TIMESTAMPTZ,
    requiere_revision_manual             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_diagnostico_ia_json_obj
        CHECK (diagnostico_ia_json IS NULL OR jsonb_typeof(diagnostico_ia_json) = 'object'),
    CONSTRAINT ck_etiquetas_imagen_json_arr
        CHECK (etiquetas_imagen IS NULL OR jsonb_typeof(etiquetas_imagen) IN ('array','object'))
);

CREATE INDEX ix_incidente_cliente ON incidente(id_cliente);
CREATE INDEX ix_incidente_estado ON incidente(estado);
CREATE INDEX ix_incidente_especialidad_detectada ON incidente(id_especialidad_detectada);

-- =========================================================
-- CATALOGO DE SERVICIOS DEL TALLER (CU26)
-- =========================================================
CREATE TABLE catalogo_servicio_taller (
    id_catalogo_servicio     BIGSERIAL PRIMARY KEY,
    id_taller                BIGINT NOT NULL REFERENCES taller(id_taller) ON DELETE CASCADE,
    id_especialidad          BIGINT NOT NULL REFERENCES especialidad(id_especialidad) ON DELETE RESTRICT,
    nombre                   VARCHAR(120) NOT NULL,
    descripcion              TEXT,
    precio_base_min          NUMERIC(12,2) NOT NULL CHECK (precio_base_min >= 0),
    precio_base_max          NUMERIC(12,2) NOT NULL CHECK (precio_base_max >= 0),
    incluye_repuestos_basicos BOOLEAN NOT NULL DEFAULT FALSE,
    activo                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_catalogo_rango_precio CHECK (precio_base_max >= precio_base_min),
    CONSTRAINT uq_catalogo_taller_nombre UNIQUE (id_taller, nombre)
);

-- =========================================================
-- SOLICITUDES DEL MATCHMAKING
-- Se guardan scores y prioridad por seguro
-- Se evita doble solicitud viva por incidente
-- =========================================================
CREATE TABLE solicitud_servicio (
    id_solicitud             BIGSERIAL PRIMARY KEY,
    id_incidente             BIGINT NOT NULL REFERENCES incidente(id_incidente) ON DELETE CASCADE,
    id_taller                BIGINT NOT NULL REFERENCES taller(id_taller) ON DELETE RESTRICT,
    fecha_envio              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_expiracion         TIMESTAMPTZ NOT NULL,
    fecha_respuesta          TIMESTAMPTZ,
    estado                   VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                            CHECK (estado IN ('PENDIENTE','ACEPTADA','RECHAZADA','EXPIRADA','CANCELADA','DESCARTADA')),
    motivo_cierre            VARCHAR(200),
    prioridad_seguro         BOOLEAN NOT NULL DEFAULT FALSE,
    score_proximidad         NUMERIC(6,4) CHECK (score_proximidad IS NULL OR (score_proximidad >= 0 AND score_proximidad <= 1)),
    score_reputacion         NUMERIC(6,4) CHECK (score_reputacion IS NULL OR (score_reputacion >= 0 AND score_reputacion <= 1)),
    score_total              NUMERIC(6,4) CHECK (score_total IS NULL OR (score_total >= 0 AND score_total <= 1)),
    ranking_posicion         INTEGER CHECK (ranking_posicion IS NULL OR ranking_posicion > 0),
    intento_numero           INTEGER NOT NULL DEFAULT 1 CHECK (intento_numero > 0),
    es_actual                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_solicitud_fechas CHECK (fecha_expiracion >= fecha_envio),
    CONSTRAINT uq_solicitud_incidente_taller_intento UNIQUE (id_incidente, id_taller, intento_numero)
);

CREATE INDEX ix_solicitud_taller_estado ON solicitud_servicio(id_taller, estado);
CREATE INDEX ix_solicitud_incidente_estado ON solicitud_servicio(id_incidente, estado);

CREATE UNIQUE INDEX ux_solicitud_incidente_actual
ON solicitud_servicio(id_incidente)
WHERE es_actual = TRUE AND estado IN ('PENDIENTE','ACEPTADA');

CREATE UNIQUE INDEX ux_solicitud_incidente_aceptada
ON solicitud_servicio(id_incidente)
WHERE estado = 'ACEPTADA';

-- =========================================================
-- SERVICIO
-- Ya tiene estado propio y no obliga pago/operario demasiado pronto
-- =========================================================
CREATE TABLE servicio (
    id_servicio                     BIGSERIAL PRIMARY KEY,
    id_solicitud                    BIGINT NOT NULL UNIQUE REFERENCES solicitud_servicio(id_solicitud) ON DELETE RESTRICT,
    id_seguro                       BIGINT REFERENCES seguro(id_seguro) ON DELETE RESTRICT,
    id_persona_operario             BIGINT REFERENCES operario(id_persona) ON DELETE RESTRICT,
    estado                          VARCHAR(40) NOT NULL DEFAULT 'EN_ESPERA_ASIGNACION'
                                    CHECK (estado IN (
                                        'EN_ESPERA_ASIGNACION',
                                        'ASIGNADO',
                                        'EN_CAMINO',
                                        'EN_SITIO',
                                        'EN_DIAGNOSTICO_FISICO',
                                        'EN_REPARACION',
                                        'ESPERANDO_REPUESTOS',
                                        'COMPLETADO_PENDIENTE_CONFIRMACION',
                                        'FINALIZADO_PENDIENTE_PAGO',
                                        'PAGADO',
                                        'CANCELADO'
                                    )),
    codigo_precotizacion            VARCHAR(50) UNIQUE,
    monto_precotizado_min           NUMERIC(12,2) CHECK (monto_precotizado_min IS NULL OR monto_precotizado_min >= 0),
    monto_precotizado_max           NUMERIC(12,2) CHECK (monto_precotizado_max IS NULL OR monto_precotizado_max >= 0),
    costo_mano_obra                 NUMERIC(12,2) CHECK (costo_mano_obra IS NULL OR costo_mano_obra >= 0),
    costo_repuestos                 NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (costo_repuestos >= 0),
    costo_total                     NUMERIC(12,2) CHECK (costo_total IS NULL OR costo_total >= 0),
    comprobante                     TEXT,
    confirmacion_cliente            BOOLEAN,
    fecha_confirmacion_cliente      TIMESTAMPTZ,
    fecha_asignacion_operario       TIMESTAMPTZ,
    fecha_inicio                    TIMESTAMPTZ,
    fecha_llegada                   TIMESTAMPTZ,
    fecha_fin                       TIMESTAMPTZ,
    observaciones_cierre            TEXT,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_servicio_rango_precotizacion
        CHECK (
            monto_precotizado_min IS NULL
            OR monto_precotizado_max IS NULL
            OR monto_precotizado_max >= monto_precotizado_min
        ),
    CONSTRAINT ck_servicio_fechas
        CHECK (
            fecha_fin IS NULL
            OR fecha_inicio IS NULL
            OR fecha_fin >= fecha_inicio
        )
);

CREATE INDEX ix_servicio_estado ON servicio(estado);
CREATE INDEX ix_servicio_operario ON servicio(id_persona_operario);

-- =========================================================
-- EVIDENCIAS
-- Sirven tanto para incidente como para reparacion/cierre
-- =========================================================
CREATE TABLE evidencia (
    id_evidencia             BIGSERIAL PRIMARY KEY,
    tipo_evidencia           VARCHAR(20) NOT NULL
                            CHECK (tipo_evidencia IN ('IMAGEN','AUDIO','VIDEO','DOCUMENTO','OTRO')),
    categoria                VARCHAR(20) NOT NULL DEFAULT 'INCIDENTE'
                            CHECK (categoria IN ('INCIDENTE','REPARACION','CIERRE')),
    url_archivo              TEXT NOT NULL,
    mime_type                VARCHAR(100),
    tamano_bytes             BIGINT CHECK (tamano_bytes IS NULL OR tamano_bytes >= 0),
    fecha_registro           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id_incidente             BIGINT REFERENCES incidente(id_incidente) ON DELETE CASCADE,
    id_servicio              BIGINT REFERENCES servicio(id_servicio) ON DELETE CASCADE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_evidencia_relacion
        CHECK (id_incidente IS NOT NULL OR id_servicio IS NOT NULL)
);

CREATE INDEX ix_evidencia_incidente ON evidencia(id_incidente);
CREATE INDEX ix_evidencia_servicio ON evidencia(id_servicio);

-- =========================================================
-- INFORME TECNICO Y REPUESTOS (CU16)
-- =========================================================
CREATE TABLE servicio_informe (
    id_informe               BIGSERIAL PRIMARY KEY,
    id_servicio              BIGINT NOT NULL UNIQUE REFERENCES servicio(id_servicio) ON DELETE CASCADE,
    accion_realizada         TEXT NOT NULL,
    diagnostico_fisico       TEXT,
    observaciones            TEXT,
    foto_cierre_url          TEXT,
    fecha_registro           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE servicio_repuesto (
    id_servicio_repuesto     BIGSERIAL PRIMARY KEY,
    id_servicio              BIGINT NOT NULL REFERENCES servicio(id_servicio) ON DELETE CASCADE,
    descripcion              VARCHAR(150) NOT NULL,
    cantidad                 NUMERIC(10,2) NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    costo_unitario           NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (costo_unitario >= 0),
    evidencia_url            TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_servicio_repuesto_servicio ON servicio_repuesto(id_servicio);

-- =========================================================
-- GPS / SEGUIMIENTO EN TIEMPO REAL
-- =========================================================
CREATE TABLE servicio_ubicacion (
    id_ubicacion             BIGSERIAL PRIMARY KEY,
    id_servicio              BIGINT NOT NULL REFERENCES servicio(id_servicio) ON DELETE CASCADE,
    id_persona_operario      BIGINT NOT NULL REFERENCES operario(id_persona) ON DELETE RESTRICT,
    latitud                  NUMERIC(10,8) NOT NULL,
    longitud                 NUMERIC(11,8) NOT NULL,
    precision_metros         NUMERIC(8,2),
    velocidad_kmh            NUMERIC(8,2),
    fecha_hora               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_servicio_ubicacion_servicio_fecha ON servicio_ubicacion(id_servicio, fecha_hora);

-- =========================================================
-- PAGOS
-- Se separa de SERVICIO para registrar webhooks y trazabilidad real
-- =========================================================
CREATE TABLE metodo_pago (
    id_metodo               BIGSERIAL PRIMARY KEY,
    nombre                  VARCHAR(50) NOT NULL UNIQUE,
    activo                  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pago (
    id_pago                 BIGSERIAL PRIMARY KEY,
    id_servicio             BIGINT NOT NULL UNIQUE REFERENCES servicio(id_servicio) ON DELETE RESTRICT,
    id_metodo               BIGINT NOT NULL REFERENCES metodo_pago(id_metodo) ON DELETE RESTRICT,
    monto                   NUMERIC(12,2) NOT NULL CHECK (monto >= 0),
    moneda                  CHAR(3) NOT NULL DEFAULT 'BOB',
    estado                  VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                            CHECK (estado IN ('PENDIENTE','CONFIRMADO','RECHAZADO','ANULADO')),
    referencia_externa      VARCHAR(100),
    token_pago              VARCHAR(150),
    qr_url                  TEXT,
    payload_pasarela        JSONB,
    comprobante             TEXT,
    fecha_solicitud         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_confirmacion      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_pago_payload_json_obj
        CHECK (payload_pasarela IS NULL OR jsonb_typeof(payload_pasarela) = 'object')
);

CREATE INDEX ix_pago_estado ON pago(estado);

-- =========================================================
-- CALIFICACION
-- Se mantiene simple: solo estrellas
-- =========================================================
CREATE TABLE calificacion (
    id_calificacion         BIGSERIAL PRIMARY KEY,
    id_servicio             BIGINT NOT NULL REFERENCES servicio(id_servicio) ON DELETE CASCADE,
    id_emisor               BIGINT NOT NULL REFERENCES persona(id_persona) ON DELETE RESTRICT,
    id_receptor             BIGINT REFERENCES persona(id_persona) ON DELETE RESTRICT,
    id_taller_calif         BIGINT REFERENCES taller(id_taller) ON DELETE RESTRICT,
    emisor_tipo             VARCHAR(20) NOT NULL CHECK (emisor_tipo IN ('CLIENTE','OPERARIO','ADMINISTRADOR')),
    receptor_tipo           VARCHAR(20) NOT NULL CHECK (receptor_tipo IN ('PERSONA','TALLER')),
    estrellas               INTEGER NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
    comentario              TEXT,
    fecha                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_calificacion_destino
        CHECK (
            (receptor_tipo = 'PERSONA' AND id_receptor IS NOT NULL AND id_taller_calif IS NULL)
            OR
            (receptor_tipo = 'TALLER' AND id_receptor IS NULL AND id_taller_calif IS NOT NULL)
        )
);

CREATE UNIQUE INDEX uq_calificacion_persona
ON calificacion (id_servicio, id_emisor, id_receptor)
WHERE id_receptor IS NOT NULL;

CREATE UNIQUE INDEX uq_calificacion_taller
ON calificacion (id_servicio, id_emisor, id_taller_calif)
WHERE id_taller_calif IS NOT NULL;

-- =========================================================
-- NOTIFICACIONES
-- =========================================================
CREATE TABLE dispositivo_usuario (
    id_dispositivo          BIGSERIAL PRIMARY KEY,
    id_usuario              BIGINT NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    plataforma              VARCHAR(20) NOT NULL CHECK (plataforma IN ('ANDROID','IOS','WEB')),
    token_push              VARCHAR(255) NOT NULL UNIQUE,
    activo                  BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_registro         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notificacion (
    id_notificacion         BIGSERIAL PRIMARY KEY,
    id_usuario              BIGINT NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_servicio             BIGINT REFERENCES servicio(id_servicio) ON DELETE CASCADE,
    id_solicitud            BIGINT REFERENCES solicitud_servicio(id_solicitud) ON DELETE CASCADE,
    canal                   VARCHAR(20) NOT NULL DEFAULT 'PUSH' CHECK (canal IN ('PUSH','EMAIL','SMS','WEB')),
    titulo                  VARCHAR(150) NOT NULL,
    mensaje                 TEXT NOT NULL,
    payload                 JSONB,
    estado                  VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                            CHECK (estado IN ('PENDIENTE','ENVIADA','FALLIDA','LEIDA')),
    proveedor               VARCHAR(50),
    fecha_creacion          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_envio             TIMESTAMPTZ,
    fecha_lectura           TIMESTAMPTZ,
    CONSTRAINT ck_notificacion_payload_json
        CHECK (payload IS NULL OR jsonb_typeof(payload) IN ('object','array'))
);

CREATE INDEX ix_notificacion_usuario_estado ON notificacion(id_usuario, estado);

-- =========================================================
-- BITACORA APPEND-ONLY
-- Ya no depende obligatoriamente de id_servicio
-- Sirve para IA, pagos, cambios de estado, solicitudes y notificaciones
-- =========================================================
CREATE TABLE bitacora (
    id_bitacora             BIGSERIAL PRIMARY KEY,
    accion                  VARCHAR(100) NOT NULL,
    tipo_evento             VARCHAR(50) NOT NULL,
    descripcion             TEXT NOT NULL,
    entidad_principal       VARCHAR(30) NOT NULL
                            CHECK (entidad_principal IN (
                                'INCIDENTE',
                                'SOLICITUD',
                                'SERVICIO',
                                'PAGO',
                                'IA',
                                'NOTIFICACION',
                                'USUARIO',
                                'SISTEMA'
                            )),
    id_entidad_principal    BIGINT,
    datos_originales        JSONB,
    datos_nuevos            JSONB,
    ip_origen               VARCHAR(45),
    user_agent              TEXT,
    hash_evento             VARCHAR(32) NOT NULL,
    id_usuario              BIGINT REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    id_incidente            BIGINT REFERENCES incidente(id_incidente) ON DELETE SET NULL,
    id_solicitud            BIGINT REFERENCES solicitud_servicio(id_solicitud) ON DELETE SET NULL,
    id_servicio             BIGINT REFERENCES servicio(id_servicio) ON DELETE SET NULL,
    id_pago                 BIGINT REFERENCES pago(id_pago) ON DELETE SET NULL,
    fecha_hora              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_bitacora_datos_originales_json
        CHECK (datos_originales IS NULL OR jsonb_typeof(datos_originales) IN ('object','array','string','number','boolean','null')),
    CONSTRAINT ck_bitacora_datos_nuevos_json
        CHECK (datos_nuevos IS NULL OR jsonb_typeof(datos_nuevos) IN ('object','array','string','number','boolean','null'))
);

CREATE INDEX ix_bitacora_fecha ON bitacora(fecha_hora);
CREATE INDEX ix_bitacora_servicio ON bitacora(id_servicio);
CREATE INDEX ix_bitacora_incidente ON bitacora(id_incidente);
CREATE INDEX ix_bitacora_solicitud ON bitacora(id_solicitud);
CREATE INDEX ix_bitacora_pago ON bitacora(id_pago);
CREATE INDEX ix_bitacora_entidad ON bitacora(entidad_principal, id_entidad_principal);

-- =========================================================
-- TRIGGERS updated_at
-- =========================================================
CREATE TRIGGER trg_persona_updated_at
BEFORE UPDATE ON persona
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_taller_updated_at
BEFORE UPDATE ON taller
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_usuario_updated_at
BEFORE UPDATE ON usuario
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_cliente_updated_at
BEFORE UPDATE ON cliente
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_administrador_updated_at
BEFORE UPDATE ON administrador
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_operario_updated_at
BEFORE UPDATE ON operario
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_especialidad_updated_at
BEFORE UPDATE ON especialidad
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_marca_updated_at
BEFORE UPDATE ON marca
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_modelo_updated_at
BEFORE UPDATE ON modelo
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_color_updated_at
BEFORE UPDATE ON color
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_vehiculo_updated_at
BEFORE UPDATE ON vehiculo
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_tipo_cobertura_updated_at
BEFORE UPDATE ON tipo_cobertura
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_seguro_updated_at
BEFORE UPDATE ON seguro
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_incidente_updated_at
BEFORE UPDATE ON incidente
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_catalogo_servicio_taller_updated_at
BEFORE UPDATE ON catalogo_servicio_taller
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_solicitud_servicio_updated_at
BEFORE UPDATE ON solicitud_servicio
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_servicio_updated_at
BEFORE UPDATE ON servicio
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_servicio_informe_updated_at
BEFORE UPDATE ON servicio_informe
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_servicio_repuesto_updated_at
BEFORE UPDATE ON servicio_repuesto
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_metodo_pago_updated_at
BEFORE UPDATE ON metodo_pago
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_pago_updated_at
BEFORE UPDATE ON pago
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =========================================================
-- TRIGGERS DE BITACORA
-- =========================================================
CREATE TRIGGER trg_bitacora_hash
BEFORE INSERT ON bitacora
FOR EACH ROW EXECUTE FUNCTION fn_bitacora_set_hash();

CREATE TRIGGER trg_bitacora_no_update
BEFORE UPDATE ON bitacora
FOR EACH ROW EXECUTE FUNCTION fn_bitacora_block_changes();

CREATE TRIGGER trg_bitacora_no_delete
BEFORE DELETE ON bitacora
FOR EACH ROW EXECUTE FUNCTION fn_bitacora_block_changes();

-- =========================================================
-- SEMILLAS MINIMAS RECOMENDADAS
-- Puedes borrarlas si prefieres cargar catalogos desde tu app.
-- =========================================================
INSERT INTO metodo_pago (nombre) VALUES
('QR'),
('PAGO_MOVIL')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO especialidad (nombre, descripcion, nivel_complejidad) VALUES
('MECANICA_GENERAL', 'Servicios mecanicos generales', 1),
('ELECTRICIDAD', 'Fallas electricas y electronicas', 2),
('GRUA', 'Servicio de remolque y traslado', 2),
('LLANTAS', 'Pinchaduras, cambio y reparacion de llantas', 1),
('BATERIA', 'Arranque, bateria y carga', 1),
('AIRE_ACONDICIONADO', 'Aire acondicionado automotriz', 2),
('DIAGNOSTICO_GENERAL', 'Cuando el cliente no esta seguro del tipo de servicio', 1)
ON CONFLICT (nombre) DO NOTHING;

-- =========================================================
-- NOTAS PRACTICAS PARA DESARROLLO
-- 1) Cuando se cree un incidente, usa id_especialidad_reportada_cliente.
-- 2) Luego IA llena: id_especialidad_detectada, severidad, diagnostico_ia_json.
-- 3) Matchmaking inserta solicitud_servicio con scores y prioridad_seguro.
-- 4) Si una solicitud se acepta, crea servicio en estado EN_ESPERA_ASIGNACION.
-- 5) Pago vive en tabla pago; servicio solo guarda costos y estado operativo.
-- 6) Bitacora registra todo y no admite UPDATE/DELETE.
-- =========================================================
