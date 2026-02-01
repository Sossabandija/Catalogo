"""
Generador de archivos WooCommerce con atributos del catálogo Mamut.
Conserva los datos originales del Excel, actualiza atributos de hijos y crea padres si no existen.
"""

import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any


def load_catalog(catalog_path: str) -> dict[str, dict]:
    """Carga el catálogo JSON extraído."""
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    return catalog['products']


def find_sku_in_text(text: str, catalog_skus: set[str]) -> str | None:
    """Busca un SKU del catálogo dentro de un texto (nombre o SKU del Excel)."""
    text_upper = text.upper()
    # Ordenar SKUs por longitud descendente para encontrar el más específico primero
    for sku in sorted(catalog_skus, key=len, reverse=True):
        sku_escaped = re.escape(sku)
        patterns = [
            rf'\({sku_escaped}\)',  # (SKU)
            rf'\b{sku_escaped}\b',  # SKU como palabra
            rf'{sku_escaped}$',     # SKU al final
        ]
        for pattern in patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return sku
    return None


def aggregate_attributes(products_data: list[dict]) -> dict[str, list[str]]:
    """Agrega atributos de múltiples productos para crear padre variable."""
    aggregated = {}
    for product in products_data:
        for attr in product.get('attributes', []):
            name = attr['name']
            value = str(attr['value'])
            if name not in aggregated:
                aggregated[name] = []
            if value and value not in aggregated[name]:
                aggregated[name].append(value)
    return aggregated


def generate_woocommerce_from_catalog(
    excel_path: str,
    catalog_path: str,
    output_path: str | None = None
) -> tuple[pd.DataFrame, str, str]:
    """
    Genera archivo Excel y CSV de WooCommerce conservando datos originales
    y actualizando atributos desde el catálogo.
    
    - Conserva SKU, Nombre y demás datos del archivo original
    - Busca el SKU del catálogo en el Nombre del producto
    - Actualiza los atributos del producto con los del catálogo
    - Crea padres (variable) si no existen, agrupando por categoría del catálogo
    - Los hijos referencian al padre con "id:X"
    """
    # Cargar datos
    catalog = load_catalog(catalog_path)
    catalog_skus = set(catalog.keys())
    df_original = pd.read_excel(excel_path, sheet_name='Maestro')
    
    print(f"Productos en catálogo: {len(catalog_skus)}")
    print(f"Productos en Excel original: {len(df_original)}")
    
    # Copiar todas las columnas del original
    all_columns = list(df_original.columns)
    
    # Encontrar productos que coinciden con el catálogo
    matches = []  # Lista de (idx_original, catalog_sku, catalog_data)
    groups_by_category = {}  # category_path -> lista de (idx, catalog_data)
    
    total_rows = len(df_original)
    for idx, row in df_original.iterrows():
        if idx % 500 == 0:
            print(f"  Procesando fila {idx}/{total_rows}...")
        
        nombre = str(row['Nombre']) if pd.notna(row['Nombre']) else ""
        sku_excel = str(row['SKU']) if pd.notna(row['SKU']) else ""
        
        # Buscar SKU del catálogo en nombre o SKU
        found_sku = find_sku_in_text(nombre, catalog_skus)
        if not found_sku:
            found_sku = find_sku_in_text(sku_excel, catalog_skus)
        
        if found_sku:
            cat_data = catalog[found_sku]
            category_path = tuple(cat_data.get('category_path', []))
            
            matches.append({
                'idx': idx,
                'catalog_sku': found_sku,
                'catalog_data': cat_data,
                'category_path': category_path,
            })
            
            # Agrupar por categoría para crear padres
            if category_path not in groups_by_category:
                groups_by_category[category_path] = []
            groups_by_category[category_path].append({
                'idx': idx,
                'catalog_data': cat_data,
            })
    
    print(f"Coincidencias encontradas: {len(matches)}")
    print(f"Grupos de categoría (padres a crear): {len(groups_by_category)}")
    
    # Crear lista de filas para el nuevo DataFrame
    output_rows = []
    
    # ID máximo actual para crear nuevos padres
    max_id = df_original['ID'].max() if 'ID' in df_original.columns else 0
    max_id = int(max_id) if pd.notna(max_id) else 0
    parent_id_counter = max_id + 1000
    
    # Mapeo: category_path -> parent_id
    parent_ids = {}
    
    # 1. Primero crear los padres (tipo variable) para cada grupo de categoría
    for category_path, group_items in groups_by_category.items():
        if not category_path:
            continue
        
        # Agregar atributos de todos los hijos del grupo
        aggregated = aggregate_attributes([item['catalog_data'] for item in group_items])
        
        # Nombre del padre = última parte de la categoría (tipo de producto)
        parent_name = category_path[-1] if category_path else "Producto Variable"
        
        # SKU del padre
        parent_sku = f"GRP-{'-'.join(p[:10].upper().replace(' ', '-') for p in category_path[-2:])}"
        
        # Categorías WooCommerce
        categories_str = ' > '.join(category_path)
        
        parent_id = parent_id_counter
        parent_ids[category_path] = parent_id
        parent_id_counter += 1
        
        # Crear fila del padre con todas las columnas del original
        parent_row = {col: '' for col in all_columns}
        parent_row['ID'] = parent_id
        parent_row['Tipo'] = 'variable'
        parent_row['SKU'] = parent_sku
        parent_row['Nombre'] = parent_name
        parent_row['Publicado'] = 1
        parent_row['Visibilidad en el catálogo'] = 'visible'
        parent_row['Categorías'] = categories_str
        parent_row['¿En inventario?'] = 1
        parent_row['Marcas'] = 'MAMUT'
        parent_row['Principal'] = ''
        
        # Atributos agregados (todos los valores posibles separados por |)
        for i, (attr_name, values) in enumerate(list(aggregated.items())[:6], 1):
            parent_row[f'Nombre del atributo {i}'] = attr_name
            parent_row[f'Valor(es) del atributo {i}'] = '|'.join(str(v) for v in values)
            parent_row[f'Atributo visible {i}'] = 1
            parent_row[f'Atributo global {i}'] = 0
        
        output_rows.append(parent_row)
    
    print(f"Padres creados: {len(parent_ids)}")
    
    # 2. Ahora procesar los hijos - actualizar atributos y asignar padre
    children_updated = 0
    for match in matches:
        idx = match['idx']
        cat_data = match['catalog_data']
        category_path = match['category_path']
        
        # Obtener fila original
        original_row = df_original.iloc[idx].to_dict()
        
        # Actualizar tipo a variation
        original_row['Tipo'] = 'variation'
        
        # Asignar referencia al padre
        parent_id = parent_ids.get(category_path)
        if parent_id:
            original_row['Principal'] = f'id:{parent_id}'
        
        # Actualizar atributos con los del catálogo
        attrs = cat_data.get('attributes', [])
        for i, attr in enumerate(attrs[:6], 1):
            original_row[f'Nombre del atributo {i}'] = attr['name']
            original_row[f'Valor(es) del atributo {i}'] = attr['value']
            original_row[f'Atributo visible {i}'] = 1
            original_row[f'Atributo global {i}'] = 0
        
        # Limpiar atributos restantes si hay menos de 6
        for i in range(len(attrs) + 1, 7):
            if f'Nombre del atributo {i}' in original_row:
                original_row[f'Nombre del atributo {i}'] = ''
            if f'Valor(es) del atributo {i}' in original_row:
                original_row[f'Valor(es) del atributo {i}'] = ''
        
        output_rows.append(original_row)
        children_updated += 1
    
    print(f"Hijos actualizados: {children_updated}")
    
    # Crear DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Ordenar por ID
    if 'ID' in output_df.columns:
        output_df = output_df.sort_values('ID')
    
    # Generar rutas de salida
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/processed/maestro_revision_{timestamp}"
    
    excel_output = f"{output_path}.xlsx"
    csv_output = f"{output_path}.csv"
    
    # Guardar con hoja 'Maestro' para compatibilidad con revisor_gui
    with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
        output_df.to_excel(writer, sheet_name='Maestro', index=False)
    
    output_df.to_csv(csv_output, index=False, encoding='utf-8-sig')
    
    print(f"\nGenerados:")
    print(f"  Excel: {excel_output}")
    print(f"  CSV: {csv_output}")
    print(f"  Total filas: {len(output_df)} ({len(parent_ids)} padres + {children_updated} hijos)")
    
    return output_df, excel_output, csv_output


if __name__ == "__main__":
    import sys
    
    excel_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/maestro_revision_20260129_185533.xlsx"
    catalog_path = sys.argv[2] if len(sys.argv) > 2 else "data/catalogo_mamut_2025_spatial.json"
    
    df, excel_out, csv_out = generate_woocommerce_from_catalog(excel_path, catalog_path)
    
    print("\n=== EJEMPLOS DE PADRES CREADOS ===")
    padres = df[df['Tipo'] == 'variable'].head(3)
    for _, row in padres.iterrows():
        print(f"ID: {row['ID']}, SKU: {row['SKU']}")
        print(f"  Nombre: {row['Nombre'][:60] if pd.notna(row['Nombre']) else ''}")
        print(f"  Attr1: {row.get('Nombre del atributo 1', '')} = {row.get('Valor(es) del atributo 1', '')}")
        print()
    
    print("\n=== EJEMPLOS DE HIJOS ACTUALIZADOS ===")
    hijos = df[df['Tipo'] == 'variation'].head(5)
    for _, row in hijos.iterrows():
        print(f"ID: {row['ID']}, SKU: {row['SKU']}, Principal: {row.get('Principal', '')}")
        print(f"  Nombre: {row['Nombre'][:60] if pd.notna(row['Nombre']) else ''}")
        print(f"  Attr1: {row.get('Nombre del atributo 1', '')} = {row.get('Valor(es) del atributo 1', '')}")
        print()
