"""Script para regenerar el catálogo JSON con estructura jerárquica."""
import sys
sys.path.insert(0, '.')
import json
from src.catalogo_spatial_parser import extract_catalog_from_text

# Leer texto del catálogo
with open('pdf/Catalogo_Mamut_2025.txt', encoding='utf-8') as f:
    text = f.read()

# Extraer con estructura completa
result = extract_catalog_from_text(text)

# Guardar
with open('data/catalogo_mamut_2025_spatial.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"Guardado: {result['total_products']} productos")
print(f"Estructura de categorías incluida")
