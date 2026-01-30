"""
EJEMPLO DE PIPELINE COMPLETO CON DATOS REALES
Demostración de transformación: Excel real → Formato maestro WooCommerce
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Crear datos de ejemplo con todas las columnas reales
ejemplo_data = {
    'Categoría': [
        'Tuercas y Tornillos',
        'Ferreteria Varios',
        'Ferreteria Varios',
        'Tuercas y Tornillos',
        'Tuercas y Tornillos',
        'Tuercas y Tornillos',
        'Ferreteria Varios',
        'Eléctrico'
    ],
    'Nombre': [
        '3.7x1.1/4"(Steelfix)',
        'ABRAZADERA 1/2 Aluminio OMEGA',
        'ABRAZADERA 1/2 COBRE OMEGA',
        'TORNILLO HEXAGONAL INOX M6 x 30mm',
        'TORNILLO HEXAGONAL INOX M8 x 40mm',
        'TUERCA M6 ACERO GALVANIZADO',
        'TARUGO PLÁSTICO 6mm (pack 100)',
        'CABLE COBRE 2.5mm 5 metros',
    ],
    'SKU': [
        '29068',
        '22220',
        '21638',
        '15001',
        '15002',
        '16001',
        '18001',
        '20001'
    ],
    'Marca': [
        'fijaciones de acero Steelfix',
        'ELPROIN',
        'ELPROIN',
        'INOX PRO',
        'INOX PRO',
        'FERRACERO',
        'PLASTIFIX',
        'COBRE ELITE'
    ],
    'Modelo': [
        '',
        '',
        '',
        'HEX-M6-30',
        'HEX-M8-40',
        'TUE-M6',
        'TAR-6',
        'CAB-2.5-5M'
    ],
    'Unidad': [
        'UN',
        'UN',
        'UN',
        'UN',
        'UN',
        'UN',
        'PACK',
        'ROLLO'
    ],
    'Código de barras': [
        '7701234567890',
        '7701234567891',
        '7701234567892',
        '',
        '',
        '',
        '',
        ''
    ],
    'Producto / Servicio': [
        'producto',
        'producto',
        'producto',
        'producto',
        'producto',
        'producto',
        'producto',
        'producto'
    ],
    'Costo neto': [
        10,
        0,
        0,
        5.50,
        7.25,
        2.30,
        1.50,
        8.00
    ],
    'Venta: Precio neto': [
        18.067227,
        168.067227,
        672.268908,
        15.50,
        21.25,
        8.50,
        12.99,
        35.99
    ],
    'Venta: afecto/exento de IVA': [
        'afecto',
        'afecto',
        'afecto',
        'afecto',
        'afecto',
        'afecto',
        'afecto',
        'afecto'
    ],
    'Venta: Monto IVA': [
        3.432773,
        31.932773,
        127.731092,
        2.945,
        4.0375,
        1.615,
        2.4681,
        6.8381
    ],
    'Venta: Código Impuesto específico': [
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ],
    'Venta: Monto impuesto específico': [
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ],
    'Venta: Precio total': [
        22,
        200,
        800,
        18.45,
        25.29,
        10.12,
        15.46,
        42.84
    ],
    'Stock mínimo': [
        0,
        10,
        10,
        5,
        5,
        10,
        20,
        0
    ],
    'Descripción': [
        'Tornillo pequeño para fijaciones de acero',
        'Abrazadera de aluminio media pulgada',
        'Abrazadera de cobre media pulgada',
        'Tornillo hexagonal acero inoxidable',
        'Tornillo hexagonal acero inoxidable',
        'Tuerca acero galvanizado',
        'Tarugos plásticos 6mm color blanco',
        'Cable de cobre 2.5 mm² rollo 5 metros'
    ],
    'Descripción ecommerce': [
        'Tornillo 3.7x1.1/4 Steelfix para fijaciones precisas',
        'Abrazadera de aluminio 1/2 pulgada OMEGA',
        'Abrazadera de cobre 1/2 pulgada OMEGA',
        'Tornillo hexagonal acero inoxidable M6 x 30mm',
        'Tornillo hexagonal acero inoxidable M8 x 40mm',
        'Tuerca M6 acero galvanizado',
        'Tarugo plástico 6mm pack 100 unidades',
        'Cable cobre 2.5mm² 5 metros calidad premium'
    ],
    'Seriales': [
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ],
    'Información Adicional 1': [
        'Alta precisión',
        'Resistente a corrosión',
        'Excelente conductividad',
        'Acero inoxidable 304',
        'Acero inoxidable 304',
        'Galvanizado en caliente',
        'Material: PVC',
        'Conductor cobre 99.9%'
    ],
    'Información Adicional 2': [
        'Cantidad: 1 unidad',
        'Carga máxima: 50kg',
        'Carga máxima: 75kg',
        'DIN 933',
        'DIN 933',
        'ISO 7040',
        'Resistencia a UV',
        'Aislamiento: PVC'
    ],
    'Información Adicional 3': [
        'Empaque: Caja de 100',
        'Temperatura: -20 a 80°C',
        'Temperatura: -20 a 80°C',
        'Longitud: 30mm',
        'Longitud: 40mm',
        'Diámetro: 6mm',
        'Largo: 1 metro',
        'Voltaje: 1000V máx'
    ],
    'Disponibilidad en: Bodega de Cajas': [
        '',
        '-79',
        '-6',
        '100',
        '80',
        '150',
        '200',
        '50'
    ],
    'Disponibilidad en: Bodega general': [
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ],
    'Disponibilidad en: Otros productos': [
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ]
}

df_ejemplo = pd.DataFrame(ejemplo_data)

# Guardar archivo de ejemplo
output_dir = Path('data/raw')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'ejemplo_productos.xlsx'

df_ejemplo.to_excel(output_file, index=False)

print(f"""
╔════════════════════════════════════════════════════════════════╗
║    ARCHIVO DE EJEMPLO CREADO CON DATOS REALES                ║
╚════════════════════════════════════════════════════════════════╝

✓ Archivo: {output_file}

📊 Contenido (8 registros de ejemplo):

Nº | Categoría           | Nombre                              | SKU    | Marca
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

for i, row in df_ejemplo.iterrows():
    print(f"{i+1:2} | {row['Categoría']:19} | {row['Nombre']:35} | {row['SKU']:6} | {row['Marca']}")

print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 COLUMNAS INCLUIDAS:
   ✓ Categoría, Nombre, SKU, Marca, Modelo, Unidad
   ✓ Precios (Costo neto, Venta: Precio neto, Venta: Precio total)
   ✓ Impuestos (Monto IVA, afecto/exento)
   ✓ Stock (Stock mínimo)
   ✓ Descripciones (general y ecommerce)
   ✓ Información adicional y Disponibilidades

🚀 PARA EJECUTAR EL PIPELINE CON ESTOS DATOS:

  python main.py

   (selecciona opción 1 cuando se te pida)

⏸️  El pipeline se detendrá en formato maestro para revisión humana.

✅ Prueba completa de todas las columnas y funcionalidades del sistema.
""")
