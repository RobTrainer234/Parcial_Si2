from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models import CategoriaProducto, Taller, TallerRepuesto

TALLER_ID = 1
DEMO_WORKSHOP_NAME = "Taller Demo SI2"

LOCAL_ENVIRONMENTS = {"local", "dev", "development"}


def _ensure_local_environment() -> None:
    from app.core.config import get_settings
    settings = get_settings()
    env = settings.environment.strip().lower()
    if env not in LOCAL_ENVIRONMENTS:
        raise RuntimeError(
            f"seed_product_catalog.py is restricted to local environments. Current APP_ENV={settings.environment!r}."
        )


CATEGORIES = [
    ("ACEITES Y LUBRICANTES", "Aceites de motor, transmisión, hidráulicos y lubricantes en general."),
    ("FILTROS", "Filtros de aceite, aire, combustible y habitáculo."),
    ("FRENOS", "Pastillas, discos, zapatas, líquido de frenos y componentes del sistema."),
    ("SUSPENSIÓN Y DIRECCIÓN", "Amortiguadores, rótulas, terminales, brazos y componentes."),
    ("MOTOR", "Partes internas y externas del motor, empaques, correas."),
    ("ELECTRICIDAD Y ELECTRÓNICA", "Baterías, bujías, cables, sensores, alternadores."),
    ("REFRIGERACIÓN", "Radiadores, ventiladores, termostatos, mangueras."),
    ("TRANSMISIÓN", "Aceite de transmisión, clutches, componentes de caja."),
    ("LLANTAS Y RUEDAS", "Neumáticos, cámaras, válvulas, balanceo."),
    ("CARROCERÍA Y ACCESORIOS", "Pintura, masilla, retrovisores, limpiabrisas."),
    ("HERRAMIENTAS Y EQUIPOS", "Herramientas manuales, neumáticas, equipos de diagnóstico."),
    ("OTROS INSUMOS", "Líquido refrigerante, anticongelante, limpiadores, trapos."),
]

PRODUCTS_BY_CATEGORY: dict[str, list[tuple[str, str, Decimal, str, Decimal, Decimal | None]]] = {
    "ACEITES Y LUBRICANTES": [
        ("ACE-MOT-001", "Aceite de motor 20W50 (1L)", "Aceite multigrado para motor gasolinero 20W50.", Decimal("35.00"), "LITRO", Decimal("50"), Decimal("10")),
        ("ACE-MOT-002", "Aceite de motor 15W40 (1L)", "Aceite multigrado semisintético 15W40.", Decimal("42.00"), "LITRO", Decimal("40"), Decimal("8")),
        ("ACE-MOT-003", "Aceite de motor 10W30 (1L)", "Aceite multigrado 10W30 para motor a gasolina.", Decimal("38.00"), "LITRO", Decimal("30"), Decimal("6")),
        ("ACE-MOT-004", "Aceite de motor 5W30 sintético (1L)", "Aceite sintético 5W30 para motores modernos.", Decimal("55.00"), "LITRO", Decimal("20"), Decimal("5")),
        ("ACE-TRA-001", "Aceite de transmisión ATF Dexron III (1L)", "Aceite para transmisión automática.", Decimal("40.00"), "LITRO", Decimal("25"), Decimal("5")),
        ("ACE-TRA-002", "Aceite de transmisión 75W90 (1L)", "Aceite para diferencial y transmisión manual.", Decimal("45.00"), "LITRO", Decimal("20"), Decimal("5")),
        ("ACE-HID-001", "Aceite hidráulico 32 (1L)", "Aceite para dirección hidráulica y sistemas hidráulicos.", Decimal("30.00"), "LITRO", Decimal("30"), Decimal("5")),
        ("ACE-GRA-001", "Grasa multipropósito (400g)", "Grasa para rodamientos y articulaciones.", Decimal("18.00"), "UNIDAD", Decimal("15"), Decimal("5")),
    ],
    "FILTROS": [
        ("FIL-ACE-001", "Filtro de aceite estándar", "Filtro de aceite rosca 3/4, compatible con la mayoría de vehículos.", Decimal("25.00"), "UNIDAD", Decimal("60"), Decimal("12")),
        ("FIL-ACE-002", "Filtro de aceite premium", "Filtro de aceite de alta capacidad, rosca 3/4.", Decimal("35.00"), "UNIDAD", Decimal("30"), Decimal("6")),
        ("FIL-AIR-001", "Filtro de aire rectangular", "Filtro de aire para motor, estándar.", Decimal("40.00"), "UNIDAD", Decimal("40"), Decimal("8")),
        ("FIL-AIR-002", "Filtro de aire cilíndrico", "Filtro de aire tipo cilindro para motores de alto rendimiento.", Decimal("55.00"), "UNIDAD", Decimal("20"), Decimal("4")),
        ("FIL-COM-001", "Filtro de combustible", "Filtro de combustible en línea, estándar.", Decimal("30.00"), "UNIDAD", Decimal("25"), Decimal("5")),
        ("FIL-HAB-001", "Filtro de habitáculo", "Filtro de cabina para aire acondicionado.", Decimal("35.00"), "UNIDAD", Decimal("15"), Decimal("3")),
    ],
    "FRENOS": [
        ("FRE-PAS-001", "Pastillas de freno delanteras", "Pastillas de freno semi-metálicas para eje delantero.", Decimal("120.00"), "JUEGO", Decimal("30"), Decimal("6")),
        ("FRE-PAS-002", "Pastillas de freno traseras", "Pastillas de freno semi-metálicas para eje trasero.", Decimal("100.00"), "JUEGO", Decimal("25"), Decimal("5")),
        ("FRE-PAS-003", "Pastillas de freno cerámicas", "Pastillas de freno cerámicas de alta duración.", Decimal("180.00"), "JUEGO", Decimal("10"), Decimal("3")),
        ("FRE-DIS-001", "Disco de freno delantero", "Disco de freno ventilado, estándar.", Decimal("150.00"), "UNIDAD", Decimal("20"), Decimal("4")),
        ("FRE-DIS-002", "Disco de freno trasero", "Disco de freno macizo, estándar.", Decimal("120.00"), "UNIDAD", Decimal("15"), Decimal("3")),
        ("FRE-ZAP-001", "Zapatas de freno trasero", "Zapatas de freno para sistema de tambor.", Decimal("80.00"), "JUEGO", Decimal("15"), Decimal("3")),
        ("FRE-LIQ-001", "Líquido de frenos DOT4 (1L)", "Líquido de frenos DOT4, punto de ebullición 260°C.", Decimal("25.00"), "LITRO", Decimal("40"), Decimal("8")),
        ("FRE-LIQ-002", "Líquido de frenos DOT5.1 (1L)", "Líquido de frenos DOT5.1 sintético.", Decimal("35.00"), "LITRO", Decimal("15"), Decimal("3")),
    ],
    "SUSPENSIÓN Y DIRECCIÓN": [
        ("SUS-AMO-001", "Amortiguador delantero estándar", "Amortiguador hidráulico para eje delantero.", Decimal("200.00"), "UNIDAD", Decimal("16"), Decimal("4")),
        ("SUS-AMO-002", "Amortiguador trasero estándar", "Amortiguador hidráulico para eje trasero.", Decimal("180.00"), "UNIDAD", Decimal("16"), Decimal("4")),
        ("SUS-AMO-003", "Amortiguador gas presurizado delantero", "Amortiguador a gas para mejor rendimiento.", Decimal("280.00"), "UNIDAD", Decimal("8"), Decimal("2")),
        ("SUS-ROT-001", "Rótula de suspensión", "Rótula de suspensión estándar, compatible múltiples modelos.", Decimal("65.00"), "UNIDAD", Decimal("30"), Decimal("6")),
        ("SUS-TER-001", "Terminal de dirección", "Terminal de dirección interna o externa.", Decimal("55.00"), "UNIDAD", Decimal("25"), Decimal("5")),
        ("SUS-BRA-001", "Brazo de suspensión inferior", "Brazo de control inferior con bujes.", Decimal("250.00"), "UNIDAD", Decimal("10"), Decimal("2")),
        ("SUS-BAR-001", "Barra estabilizadora", "Barra estabilizadora completa.", Decimal("180.00"), "UNIDAD", Decimal("6"), Decimal("2")),
    ],
    "MOTOR": [
        ("MOT-BUJ-001", "Bujía de encendido estándar", "Bujía de cobre para motores estándar.", Decimal("12.00"), "UNIDAD", Decimal("100"), Decimal("20")),
        ("MOT-BUJ-002", "Bujía de encendido iridio", "Bujía de iridio de alta duración (hasta 100.000 km).", Decimal("35.00"), "UNIDAD", Decimal("40"), Decimal("8")),
        ("MOT-COR-001", "Correa de distribución", "Correa de distribución dentada, estándar.", Decimal("90.00"), "UNIDAD", Decimal("15"), Decimal("3")),
        ("MOT-COR-002", "Correa de alternador", "Correa poly-V para alternador y accesorios.", Decimal("35.00"), "UNIDAD", Decimal("20"), Decimal("4")),
        ("MOT-EMP-001", "Empaque de tapa de válvulas", "Empaque de caucho para tapa de válvulas.", Decimal("30.00"), "UNIDAD", Decimal("12"), Decimal("3")),
        ("MOT-EMP-002", "Empaque de culata", "Empaque metálico multicapa para culata.", Decimal("150.00"), "UNIDAD", Decimal("8"), Decimal("2")),
        ("MOT-RET-001", "Retén de cigüeñal delantero", "Retén de aceite para cigüeñal lado delantero.", Decimal("20.00"), "UNIDAD", Decimal("15"), Decimal("3")),
        ("MOT-RET-002", "Retén de cigüeñal trasero", "Retén de aceite para cigüeñal lado trasero.", Decimal("25.00"), "UNIDAD", Decimal("10"), Decimal("3")),
    ],
    "ELECTRICIDAD Y ELECTRÓNICA": [
        ("ELE-BAT-001", "Batería 40Ah (MF)", "Batería de plomo-ácido 12V 40Ah, libre de mantenimiento.", Decimal("450.00"), "UNIDAD", Decimal("10"), Decimal("3")),
        ("ELE-BAT-002", "Batería 55Ah (MF)", "Batería de plomo-ácido 12V 55Ah, libre de mantenimiento.", Decimal("550.00"), "UNIDAD", Decimal("10"), Decimal("3")),
        ("ELE-BAT-003", "Batería 75Ah (MF)", "Batería de plomo-ácido 12V 75Ah, libre de mantenimiento.", Decimal("650.00"), "UNIDAD", Decimal("8"), Decimal("2")),
        ("ELE-ALT-001", "Alternador 70A estándar", "Alternador de 70 amperios, 12V.", Decimal("600.00"), "UNIDAD", Decimal("6"), Decimal("2")),
        ("ELE-ALT-002", "Alternador 90A estándar", "Alternador de 90 amperios, 12V.", Decimal("750.00"), "UNIDAD", Decimal("4"), Decimal("1")),
        ("ELE-CAB-001", "Juego de cables de bujías", "Juego de 4 cables de bujía de silicona.", Decimal("60.00"), "JUEGO", Decimal("15"), Decimal("3")),
        ("ELE-CAB-002", "Juego de cables de bujías (6 piezas)", "Juego de 6 cables de bujía de silicona.", Decimal("85.00"), "JUEGO", Decimal("10"), Decimal("2")),
        ("ELE-SEN-001", "Sensor de oxígeno (sonda lambda)", "Sensor de O2 universal, 4 hilos.", Decimal("180.00"), "UNIDAD", Decimal("8"), Decimal("2")),
        ("ELE-SEN-002", "Sensor de temperatura", "Sensor de temperatura de refrigerante.", Decimal("45.00"), "UNIDAD", Decimal("10"), Decimal("3")),
    ],
    "REFRIGERACIÓN": [
        ("REF-RAD-001", "Radiador estándar", "Radiador de aluminio para vehículo estándar.", Decimal("500.00"), "UNIDAD", Decimal("6"), Decimal("2")),
        ("REF-RAD-002", "Radiador de alto rendimiento", "Radiador de aluminio de doble núcleo.", Decimal("750.00"), "UNIDAD", Decimal("4"), Decimal("1")),
        ("REF-VEN-001", "Electroventilador 12V", "Ventilador eléctrico de radiador 12V 16 pulgadas.", Decimal("250.00"), "UNIDAD", Decimal("8"), Decimal("2")),
        ("REF-TER-001", "Termostato", "Termostato estándar de 82°C.", Decimal("25.00"), "UNIDAD", Decimal("20"), Decimal("5")),
        ("REF-MAN-001", "Manguera de radiador superior", "Manguela de caucho para radiador lado superior.", Decimal("35.00"), "UNIDAD", Decimal("15"), Decimal("3")),
        ("REF-MAN-002", "Manguera de radiador inferior", "Manguela de caucho para radiador lado inferior.", Decimal("35.00"), "UNIDAD", Decimal("15"), Decimal("3")),
    ],
    "TRANSMISIÓN": [
        ("TRA-CLU-001", "Kit de embrague (disco + plato + release)", "Kit completo de embrague para transmisión manual.", Decimal("600.00"), "KIT", Decimal("6"), Decimal("2")),
        ("TRA-CLU-002", "Disco de embrague individual", "Disco de embrague estándar.", Decimal("250.00"), "UNIDAD", Decimal("4"), Decimal("1")),
        ("TRA-ACE-001", "Aceite de transmisión CVT (4L)", "Aceite especial para transmisión variable continua.", Decimal("150.00"), "BIDON", Decimal("8"), Decimal("2")),
        ("TRA-ACE-002", "Aceite de transmisión manual 75W90 (4L)", "Aceite para transmisión manual y diferencial.", Decimal("120.00"), "BIDON", Decimal("10"), Decimal("2")),
        ("TRA-SEL-001", "Sello de transmisión", "Retén de aceite para transmisión.", Decimal("15.00"), "UNIDAD", Decimal("20"), Decimal("5")),
    ],
    "LLANTAS Y RUEDAS": [
        ("LLA-NEU-001", "Neumático 175/65R14", "Neumático radial para turismo.", Decimal("350.00"), "UNIDAD", Decimal("20"), Decimal("4")),
        ("LLA-NEU-002", "Neumático 185/65R15", "Neumático radial para turismo.", Decimal("400.00"), "UNIDAD", Decimal("20"), Decimal("4")),
        ("LLA-NEU-003", "Neumático 205/55R16", "Neumático radial para sedán mediano.", Decimal("480.00"), "UNIDAD", Decimal("16"), Decimal("4")),
        ("LLA-NEU-004", "Neumático 215/75R15 (4x4)", "Neumático todo terreno para camioneta.", Decimal("650.00"), "UNIDAD", Decimal("12"), Decimal("3")),
        ("LLA-CAM-001", "Cámara de llanta 13/14 pulgadas", "Cámara de caucho para llanta 13-14 pulg.", Decimal("40.00"), "UNIDAD", Decimal("30"), Decimal("6")),
        ("LLA-CAM-002", "Cámara de llanta 15/16 pulgadas", "Cámara de caucho para llanta 15-16 pulg.", Decimal("50.00"), "UNIDAD", Decimal("25"), Decimal("5")),
    ],
    "CARROCERÍA Y ACCESORIOS": [
        ("CAR-PIN-001", "Pintura automotriz negro (1L)", "Pintura acrílica automotriz color negro.", Decimal("80.00"), "LITRO", Decimal("10"), Decimal("3")),
        ("CAR-PIN-002", "Pintura automotriz blanco (1L)", "Pintura acrílica automotriz color blanco.", Decimal("80.00"), "LITRO", Decimal("10"), Decimal("3")),
        ("CAR-MAS-001", "Masilla automotriz (500g)", "Masilla poliéster para carrocería.", Decimal("35.00"), "UNIDAD", Decimal("15"), Decimal("3")),
        ("CAR-THU-001", "Limpiaparabrisas 21 pulgadas", "Hoja de limpiaparabrisas de 21 pulgadas.", Decimal("25.00"), "UNIDAD", Decimal("30"), Decimal("6")),
        ("CAR-THU-002", "Limpiaparabrisas 24 pulgadas", "Hoja de limpiaparabrisas de 24 pulgadas.", Decimal("30.00"), "UNIDAD", Decimal("25"), Decimal("5")),
        ("CAR-RET-001", "Retrovisor lateral izquierdo", "Retrovisor exterior lado conductor.", Decimal("120.00"), "UNIDAD", Decimal("8"), Decimal("2")),
    ],
    "HERRAMIENTAS Y EQUIPOS": [
        ("HER-LLV-001", "Juego de llaves mixtas (8-19mm)", "Juego de 12 llaves mixtas en acero cromo vanadio.", Decimal("150.00"), "JUEGO", Decimal("5"), Decimal("1")),
        ("HER-LLV-002", "Juego de dados (1/4, 3/8, 1/2 pulgadas)", "Juego de 30 dados con carraca.", Decimal("280.00"), "JUEGO", Decimal("3"), Decimal("1")),
        ("HER-DES-001", "Destornillador plano y estrella (6 piezas)", "Set de destornilladores profesionales.", Decimal("60.00"), "JUEGO", Decimal("5"), Decimal("1")),
        ("HER-MUL-001", "Multímetro digital", "Multímetro digital para diagnóstico eléctrico.", Decimal("120.00"), "UNIDAD", Decimal("3"), Decimal("1")),
    ],
    "OTROS INSUMOS": [
        ("OTR-REF-001", "Refrigerante/anticongelante (1L)", "Refrigerante concentrado para radiador.", Decimal("25.00"), "LITRO", Decimal("40"), Decimal("8")),
        ("OTR-REF-002", "Refrigerante/anticongelante (5L)", "Refrigerante concentrado en galón.", Decimal("90.00"), "BIDON", Decimal("15"), Decimal("3")),
        ("OTR-LIQ-001", "Líquido de dirección hidráulica (1L)", "Aceite para sistema de dirección hidráulica.", Decimal("30.00"), "LITRO", Decimal("20"), Decimal("5")),
        ("OTR-LAV-001", "Lavaparabrisas (1L)", "Líquido limpiador para parabrisas.", Decimal("10.00"), "LITRO", Decimal("50"), Decimal("10")),
        ("OTR-LIM-001", "Limpiador de frenos (400ml)", "Limpiador aerosol para piezas de freno.", Decimal("20.00"), "UNIDAD", Decimal("30"), Decimal("6")),
        ("OTR-SIL-001", "Sellador de radiador (300ml)", "Sellador químico para fugas de radiador.", Decimal("30.00"), "UNIDAD", Decimal("10"), Decimal("2")),
    ],
}


def _get_taller(db, taller_id: int) -> Taller | None:
    return db.get(Taller, taller_id)


def _seed_categories(db) -> dict[str, int]:
    existing = db.execute(
        select(CategoriaProducto).where(CategoriaProducto.id_taller == TALLER_ID)
    ).scalars().all()
    name_to_id = {c.nombre: c.id_categoria for c in existing}

    for cat_name, cat_desc in CATEGORIES:
        if cat_name not in name_to_id:
            cat = CategoriaProducto(
                id_taller=TALLER_ID,
                nombre=cat_name,
                descripcion=cat_desc,
            )
            db.add(cat)
            db.flush()
            name_to_id[cat_name] = cat.id_categoria
            print(f"  + Categoria: {cat_name}")
        else:
            print(f"  = Categoria existente: {cat_name}")
    return name_to_id


def _seed_products(db, cat_name_to_id: dict[str, int]) -> int:
    count = 0
    existing = db.execute(
        select(TallerRepuesto).where(TallerRepuesto.id_taller == TALLER_ID)
    ).scalars().all()
    existing_names = set(r.nombre for r in existing)

    for cat_name, products in PRODUCTS_BY_CATEGORY.items():
        cat_id = cat_name_to_id[cat_name]
        for codigo, nombre, desc, precio, unidad, stock, stock_min in products:
            if nombre in existing_names:
                print(f"  = Ya existe: {nombre}")
                continue
            p = TallerRepuesto(
                id_taller=TALLER_ID,
                id_categoria=cat_id,
                codigo=codigo,
                nombre=nombre,
                descripcion=desc,
                precio_unitario=precio,
                unidad_medida=unidad,
                stock_actual=stock,
                stock_minimo=stock_min,
            )
            db.add(p)
            count += 1
            if count % 10 == 0:
                db.flush()
    db.flush()
    return count


def main() -> None:
    _ensure_local_environment()
    db = SessionLocal()
    try:
        taller = _get_taller(db, TALLER_ID)
        if taller is None:
            print(f"Taller con id={TALLER_ID} no encontrado. Ejecuta seed_admin.py primero.")
            return

        print(f"Poblano catalogo de productos para: {taller.nombre_comercial} (id={TALLER_ID})")
        print()

        cat_map = _seed_categories(db)
        db.commit()
        print(f"Categoras creadas: {len(cat_map)}")
        print()

        new_products = _seed_products(db, cat_map)
        db.commit()
        print(f"Productos nuevos creados: {new_products}")

        total = db.execute(
            select(TallerRepuesto).where(TallerRepuesto.id_taller == TALLER_ID)
        ).scalars().all()
        print(f"Total productos en catalogo: {len(total)}")

        total_cats = db.execute(
            select(CategoriaProducto).where(CategoriaProducto.id_taller == TALLER_ID)
        ).scalars().all()
        print(f"Total categoras: {len(total_cats)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
