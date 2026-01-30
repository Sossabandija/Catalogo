"""
MAIN.PY - Orquestación del pipeline
Punto de entrada único del sistema
Flujo: Load → Clean → Extract → STOP (esperando revisión humana)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Asegurar que logs/ existe ANTES de crear FileHandler
Path('logs').mkdir(exist_ok=True)

# Configurar logging global
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def print_banner():
    """Imprime banner del proyecto."""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║        🔧 CATÁLOGO FERRETERÍA → WOOCOMMERCE PIPELINE        ║
    ║                                                               ║
    ║      Transformación Auditable con Revisión Humana Obligatoria║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def print_phase(phase_num: int, phase_name: str):
    """Imprime separador de fase."""
    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║  FASE {phase_num}: {phase_name.upper():<49} ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def main(input_excel: str = None):
    """
    Ejecuta pipeline completo de transformación.
    
    FLUJO:
    1. Cargar Excel original (sin modificar)
    2. Limpiar y normalizar nombres
    3. Extraer atributos técnicos
    4. STOP - Esperar revisión humana
    
    Args:
        input_excel: Path al archivo Excel (si no se proporciona, pide interactivamente)
    """
    
    print_banner()
    
    # 0. Validar entrada
    print_phase(0, "Validación y Configuración")
    
    if input_excel is None:
        # Buscar archivos Excel en data/raw/
        raw_dir = Path('data/raw')
        if raw_dir.exists():
            excel_files = list(raw_dir.glob('*.xlsx')) + list(raw_dir.glob('*.xls'))
            if excel_files:
                print(f"\n📁 Archivos Excel encontrados en {raw_dir}:")
                for i, f in enumerate(excel_files, 1):
                    print(f"   {i}. {f.name}")
                idx = input(f"\n¿Cuál deseas procesar? (1-{len(excel_files)}): ").strip()
                try:
                    input_excel = str(excel_files[int(idx)-1])
                except (ValueError, IndexError):
                    input_excel = input("Ingresa la ruta al archivo Excel: ").strip()
            else:
                input_excel = input("📁 ¿Ruta del archivo Excel? (data/raw/productos.xlsx): ").strip()
        else:
            input_excel = input("📁 ¿Ruta del archivo Excel? (data/raw/productos.xlsx): ").strip()
    
    input_path = Path(input_excel)
    if not input_path.exists():
        logger.error(f"❌ Archivo no encontrado: {input_path}")
        sys.exit(1)
    
    logger.info(f"✓ Archivo de entrada: {input_path}")
    
    # 1. CARGAR DATOS
    print_phase(1, "Cargando datos originales")
    
    try:
        from src.loader import load_products_excel
        
        df, metadata = load_products_excel(str(input_path))
        
    except Exception as e:
        logger.error(f"❌ Error cargando datos: {str(e)}")
        sys.exit(1)
    
    # 2. LIMPIAR NOMBRES Y DETECTAR PATRONES
    print_phase(2, "Normalizando nombres y detectando patrones")
    
    try:
        from src.cleaner import clean_products
        
        df_clean = clean_products(df, rules_path='config/rules.yaml')
        
    except Exception as e:
        logger.error(f"❌ Error limpiando datos: {str(e)}")
        sys.exit(1)
    
    # 3. EXTRAER ATRIBUTOS TÉCNICOS
    print_phase(3, "Extrayendo atributos técnicos")
    
    try:
        from src.patterns import extract_attributes
        
        df_enriched = extract_attributes(df_clean, rules_path='config/rules.yaml')
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo atributos: {str(e)}")
        sys.exit(1)
    
    # 4. VALIDAR ATRIBUTOS
    print_phase(4, "Validando y normalizando atributos")
    
    try:
        from src.attributes import validate_attributes
        
        df_validated = validate_attributes(df_enriched, rules_path='config/rules.yaml')
        
    except Exception as e:
        logger.error(f"❌ Error validando atributos: {str(e)}")
        sys.exit(1)
    
    # 5. AGRUPAR PRODUCTOS (PADRE + VARIACIONES)
    print_phase(5, "Agrupando productos y detectando variaciones")
    
    try:
        from src.grouping import group_products
        
        df_grouped = group_products(df_validated, rules_path='config/rules.yaml')
        
    except Exception as e:
        logger.error(f"❌ Error agrupando productos: {str(e)}")
        sys.exit(1)
    
    # 6. GENERAR FORMATO MAESTRO
    print_phase(6, "Generando formato maestro para revisión humana")
    
    try:
        from src.review import generate_master_format
        
        df_maestro, output_file_xlsx, output_file_csv, output_file_woo = generate_master_format(df_grouped)
        
    except Exception as e:
        logger.error(f"❌ Error generando formato maestro: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Contar tipos de productos
    n_simple = (df_maestro['Tipo'] == 'simple').sum()
    n_variable = (df_maestro['Tipo'] == 'variable').sum()
    n_variation = (df_maestro['Tipo'] == 'variation').sum()
    
    # ⏸️ PARADA OBLIGATORIA - REVISIÓN HUMANA
    print_phase("!", "DETENCIÓN OBLIGATORIA PARA REVISIÓN HUMANA")
    
    print(f"""
    ⏸️  EL PIPELINE SE HA DETENIDO PARA REVISIÓN HUMANA OBLIGATORIA
    
    📋 PRÓXIMOS PASOS:
    
    1️⃣  Abre el archivo procesado (Excel o CSV):
        → Excel: {output_file_xlsx}
        → CSV:   {output_file_csv}
    
    2️⃣  Revisa y corrige:
        ✓ Nombres y familias de productos
        ✓ Marcas detectadas
        ✓ Atributos extraídos
        ✓ Categorías (familia/grupo)
        ✓ Precios y stock
        ✓ SKU y estructura de variaciones
    
    3️⃣  En la columna "Revisado Humano":
        - Marca "Sí" para productos aprobados
        - Marca "No" para productos rechazados
        - Agrega notas en "Notas Revisión"
    
    4️⃣  Completa datos faltantes:
        - Descripciones (si es necesario)
        - Precios y stock
        - Imágenes
        - Otros campos según necesidad
    
    5️⃣  Guarda el archivo con los cambios
    
    6️⃣  Importa directamente en WooCommerce:
        📦 Archivo listo para importar: {output_file_woo}
    
    ⚠️  IMPORTANTE (Reglas WooCommerce):
    - ✅ Tipo 'variable' = Producto padre (SIN precio ni stock)
    - ✅ Tipo 'variation' = Hijo (CON precio y stock)
    - ✅ Tipo 'simple' = Producto independiente
    - ✅ Columna 'Principal' = Referencia al padre (id:XX)
    - ✅ NO MODIFICAR SKU ni estructura de IDs
    
    📊 Estadísticas de procesamiento:
        • Total de registros: {len(df_maestro)}
        • Productos simples: {n_simple}
        • Productos variables (padre): {n_variable}
        • Variaciones (hijo): {n_variation}
        • Confianza promedio: {df_maestro['Confianza_Automática'].mean():.0f}/100
    
    📁 Archivos generados:
       Excel (revisión):  {output_file_xlsx}
       CSV (revisión):    {output_file_csv}
       CSV (WooCommerce): {output_file_woo}
    
    Presiona Enter para terminar...
    """)
    
    input()
    
    print("\n✅ Pipeline completado. Esperando revisión humana.")
    logger.info("Pipeline detenido en fase de revisión humana")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Catálogo WooCommerce Pipeline')
    parser.add_argument('--input', help='Path al archivo Excel', default=None)
    parser.add_argument('--export', help='Path al archivo revisado para exportar', default=None)
    
    args = parser.parse_args()
    
    if args.export:
        print("❌ Exportación WooCommerce no implementada aún (phase 2)")
        print(f"   Archivo a exportar: {args.export}")
        sys.exit(1)
    else:
        main(input_excel=args.input)
