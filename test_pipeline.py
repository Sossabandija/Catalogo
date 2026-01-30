"""
TEST_PIPELINE.PY - Tests unitarios del pipeline
Validar cada componente de Fase 1 + Fase 2
"""

import pandas as pd
import sys
from pathlib import Path

def test_cleaner():
    """Test: Limpieza de nombres"""
    from src.cleaner import DataCleaner
    
    cleaner = DataCleaner()
    
    test_cases = [
        ('ABRAZADERA TITAN  MINI', 'ABRAZADERA TITAN MINI'),  # Espacios múltiples
        ('abrazadera titan mini', 'ABRAZADERA TITAN MINI'),    # Lowercase
        ('ABRAZADERA "TITAN"', 'ABRAZADERA TITAN'),             # Comillas
    ]
    
    for original, expected in test_cases:
        result = cleaner.clean_name(original)
        assert result == expected, f"Esperado {expected}, got {result}"
        print(f"  ✓ {original} → {result}")
    
    return True


def test_patterns():
    """Test: Extracción de patrones"""
    from src.patterns import PatternExtractor
    
    extractor = PatternExtractor()
    
    test_cases = [
        ('1/4"', 'diametro', True),
        ('3/8"', 'diametro', True),
        ('10cm', 'largo', True),
        ('2.5mm', 'grosor', True),
        ('acero inoxidable', 'material', True),
    ]
    
    for text, attr, should_find in test_cases:
        result = extractor._extract_attribute(text.upper(), attr, extractor.patterns.get(attr, []))
        found = len(result) > 0
        assert found == should_find, f"Pattern {attr} en {text}: esperado {should_find}, got {found}"
        print(f"  ✓ Extraído {attr} de '{text}'")
    
    return True


def test_attributes():
    """Test: Validación de atributos"""
    from src.attributes import AttributeValidator
    
    validator = AttributeValidator()
    
    # Test diámetro
    result = validator._validate_diameter('1/4"')
    assert result['is_valid'] == True, "1/4\" debe ser válido"
    assert result['confidence'] >= 0.9, "Confianza debe ser alta"
    print(f"  ✓ Validación diámetro: 1/4\" → {result['normalized']}")
    
    # Test largo
    result = validator._validate_length('10cm')
    assert result['is_valid'] == True, "10cm debe ser válido"
    print(f"  ✓ Validación largo: 10cm → {result['normalized']}")
    
    # Test material
    result = validator._validate_material('acero')
    assert result['is_valid'] == True, "acero debe ser válido"
    print(f"  ✓ Validación material: acero → {result['normalized']}")
    
    return True


def test_grouping():
    """Test: Agrupación de productos"""
    from src.grouping import ProductGrouper
    
    grouper = ProductGrouper()
    
    # Crear datos de prueba
    df = pd.DataFrame({
        'Nombre_Limpio': [
            'ABRAZADERA TITAN MINI T10',
            'ABRAZADERA TITAN MINI T10 1/4',
            'ABRAZADERA TITAN MINI T10 3/8',
            'TORNILLO HEXAGONAL 6MM',
        ],
        'Tiene_Medidas': [False, True, True, True],
        'Es_Padre_Potencial': [False, False, False, False],
        'Familia_Detectada': ['abrazaderas', 'abrazaderas', 'abrazaderas', 'tornillos'],
        'Marca_Detectada': ['TITAN', 'TITAN', 'TITAN', None],
    })
    
    # Agregar columnas de atributos (requeridas)
    for col in df.columns:
        if not col.startswith('Atributo_'):
            continue
    
    df_grouped = grouper.group_products(df)
    
    # Validaciones
    assert 'Tipo' in df_grouped.columns, "Falta columna Tipo"
    assert 'SKU' in df_grouped.columns, "Falta columna SKU"
    
    # Verificar agrupación
    padres = df_grouped[df_grouped['Tipo'] == 'variable']
    variaciones = df_grouped[df_grouped['SKU_Parent'].notna()]
    
    print(f"  ✓ Detectados {len(padres)} productos variables")
    print(f"  ✓ Detectadas {len(variaciones)} variaciones")
    
    # SKU debe ser único
    assert df_grouped['SKU'].nunique() == len(df_grouped), "SKU no únicos"
    print(f"  ✓ Todos los SKU son únicos")
    
    return True


def test_review():
    """Test: Generación de formato maestro"""
    from src.review import ReviewFormatter
    
    formatter = ReviewFormatter()
    
    # Crear datos de prueba
    df = pd.DataFrame({
        'Tipo': ['variable', 'simple'],
        'SKU': ['ABR-001', 'TOR-001'],
        'SKU_Parent': [None, None],
        'Nombre_Limpio': ['ABRAZADERA TITAN', 'TORNILLO M6'],
        'Familia_Detectada': ['abrazaderas', 'tornillos'],
        'Marca_Detectada': ['TITAN', None],
        'Nombre_Original': ['ABRAZADERA TITAN', 'TORNILLO M6'],
        'Tiene_Medidas': [True, True],
        'Atributo_diametro_cantidad': [1, 1],
    })
    
    # Generar formato
    review_df = formatter.format_for_review(df)
    
    # Validaciones
    assert 'SKU' in review_df.columns, "Falta SKU"
    assert 'Confianza_Automática' in review_df.columns, "Falta confianza"
    assert 'Revisado_Humano' in review_df.columns, "Falta Revisado_Humano"
    
    # Verificar confianza
    conf = review_df['Confianza_Automática'].iloc[0]
    assert 0 <= conf <= 100, f"Confianza fuera de rango: {conf}"
    print(f"  ✓ Confianza calculada: {conf}/100")
    
    # Slug generado
    slug = review_df['Slug'].iloc[0]
    assert len(slug) > 0, "Slug vacío"
    assert ' ' not in slug, "Slug con espacios"
    print(f"  ✓ Slug generado: {slug}")
    
    return True


def test_integration():
    """Test: Pipeline completo integrado"""
    from src.loader import ExcelLoader
    from src.cleaner import clean_products
    from src.patterns import extract_attributes
    from src.attributes import validate_attributes
    from src.grouping import group_products
    from src.review import generate_master_format
    
    # Crear archivo de prueba
    df_test = pd.DataFrame({
        'Nombre': [
            'ABRAZADERA TITAN MINI T10 1/4"',
            'ABRAZADERA TITAN MINI T10 3/8"',
            'TORNILLO M6 ACERO 30mm',
        ]
    })
    
    test_file = Path('data/raw/test_data.xlsx')
    test_file.parent.mkdir(parents=True, exist_ok=True)
    df_test.to_excel(test_file, index=False)
    
    try:
        # Pipeline completo
        loader = ExcelLoader(str(test_file))
        df, metadata = loader.load()
        
        df_clean = clean_products(df)
        df_extracted = extract_attributes(df_clean)
        df_validated = validate_attributes(df_extracted)
        df_grouped = group_products(df_validated)
        df_maestro, output_file = generate_master_format(df_grouped)
        
        # Validaciones
        assert len(df_maestro) == 3, f"Expected 3 registros, got {len(df_maestro)}"
        assert df_maestro['Confianza_Automática'].min() >= 0, "Confianza negativa"
        assert df_maestro['Confianza_Automática'].max() <= 100, "Confianza > 100"
        
        print(f"  ✓ Pipeline completado exitosamente")
        print(f"  ✓ Maestro generado: {output_file}")
        print(f"  ✓ Total registros: {len(df_maestro)}")
        
        return True
    
    finally:
        # Limpiar archivo de prueba
        if test_file.exists():
            test_file.unlink()


def main():
    """Ejecuta todos los tests"""
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║          TESTS UNITARIOS - PIPELINE FASE 1 + FASE 2           ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        ('Limpieza de nombres', test_cleaner),
        ('Extracción de patrones', test_patterns),
        ('Validación de atributos', test_attributes),
        ('Agrupación de productos', test_grouping),
        ('Generación de formato maestro', test_review),
        ('Pipeline integrado', test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 {test_name}...")
            if test_func():
                print(f"   ✅ PASSOU")
                passed += 1
            else:
                print(f"   ❌ FALLO")
                failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            failed += 1
    
    # Resumen
    print(f"""
    ╔════════════════════════════════════════════════════════════════╗
    ║                      RESUMEN DE TESTS                         ║
    ╚════════════════════════════════════════════════════════════════╝
    
    ✅ PASSOU:  {passed}
    ❌ FALLO:   {failed}
    📊 TOTAL:   {passed + failed}
    
    """)
    
    if failed == 0:
        print("🎉 Todos los tests passaram!")
        return 0
    else:
        print(f"⚠️  {failed} tests fallaram")
        return 1


if __name__ == '__main__':
    sys.exit(main())
