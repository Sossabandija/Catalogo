"""
Parser espacial para catálogo Mamut - Versión mejorada.

El texto tiene DOS tablas lado a lado. Cada tabla tiene:
- Título del producto (TORNILLO DRYWALL)
- Subtipo (ROSCA METAL, ROSCA MADERA)
- Header (CODIGO NOMINAL LARGO ENVASE [más columnas])
- Línea de acabado (Zincado Brillante, Fosfatizado, BALDE)
- Filas de datos (SKU valores...)

La separación entre tablas izquierda/derecha es aproximadamente en la posición 52-56.
"""

import re
from typing import Any

# Palabras que NO son SKUs
SKU_BLACKLIST = frozenset({
    "BALDE", "NUEVO", "CODIGO", "CÓDIGO", "NOMINAL", "LARGO", "ENVASE",
    "PHILLIPS", "POZI", "TORX", "ENTRE", "CARAS", "COLOR", "DESCRIPCIÓN",
    "DIÁMETRO", "ESPESOR", "ANCHO", "ALTO", "INOX", "ACERO", "BRONCE",
    "NYLON", "ZINC", "ZINCADO", "FOSFATIZADO", "RUSPERT", "DACROMET",
    "IRIDISCENTE", "BRILLANTE", "ESPECIAL", "CONTINUACIÓN", "CONTINUACION",
    "PTA", "ENVASE", "U", "TORNILLO", "PERNO", "TUERCA", "GOLILLA",
    "AUTOPERFORANTE", "AUTOP", "HEX", "HEXAGONAL", "CAB", "CABEZA",
})


def looks_like_sku(token: str) -> bool:
    """Determina si un token parece un código SKU."""
    if not token:
        return False
    t = token.upper().strip()
    if len(t) < 3 or len(t) > 20:
        return False
    if t in SKU_BLACKLIST:
        return False
    # Debe contener al menos un dígito
    if not re.search(r"\d", t):
        return False
    # No debe ser solo números
    if t.isdigit():
        return False
    # Patrón típico de SKU: comienza con letra o número, tiene letras y números
    if not re.match(r"^[A-Z0-9][A-Z0-9\-\.\[\]\/]*$", t):
        return False
    # Debe tener al menos una letra
    if not re.search(r"[A-Z]", t):
        return False
    return True


def split_line_halves(line: str, gap_end_pos: int = 56) -> tuple[str, str]:
    """
    Divide una línea en mitad izquierda y derecha.
    gap_end_pos es donde termina el gap central (donde empieza la tabla derecha).
    """
    # Buscar el inicio del gap (punto donde hay muchos espacios antes de gap_end_pos)
    gap_start = gap_end_pos
    i = gap_end_pos - 1
    while i >= 0 and line[i:i+1] == ' ':
        gap_start = i
        i -= 1
    
    if len(line) <= gap_start:
        return line.rstrip(), ""
    
    left = line[:gap_start].rstrip()
    right = line[gap_end_pos:].strip() if len(line) > gap_end_pos else ""
    return left, right


def parse_row_parts(parts: list[str]) -> dict[str, str] | None:
    """
    Parsea las partes de una fila y las asigna a columnas.
    Maneja casos donde NOMINAL y LARGO están juntos debido al OCR.
    También maneja casos donde SKU y NOMINAL están unidos en el primer part.
    """
    if not parts:
        return None
    
    first_part = parts[0]
    
    # El primer part puede ser "SKU" o "SKU NOMINAL" unidos por un solo espacio
    # Ej: "B01TAD-BM #6-18" donde B01TAD-BM es SKU y #6-18 es NOMINAL
    if ' ' in first_part:
        subparts = first_part.split(' ', 1)
        if looks_like_sku(subparts[0]):
            # El primer subpart es el SKU, el resto va al remaining
            result = {"CODIGO": subparts[0]}
            remaining = [subparts[1]] + parts[1:]
        else:
            return None
    else:
        # El primer elemento debe ser un SKU
        if not looks_like_sku(first_part):
            return None
        result = {"CODIGO": first_part}
        remaining = parts[1:]
    
    # El ENVASE siempre es el último (contiene "U" o es número)
    envase = ""
    if remaining:
        last = remaining[-1]
        # Detectar si es ENVASE (típicamente "X,XXX U" o similar)
        if " U" in last or last.endswith("U") or re.match(r'^[\d,\.]+$', last):
            envase = remaining.pop()
    
    result["ENVASE"] = envase
    
    # Ahora remaining tiene [NOMINAL, LARGO] o [LARGO] o [NOMINAL+LARGO combinado]
    if not remaining:
        return result
    
    if len(remaining) == 1:
        val = remaining[0]
        # Verificar si es NOMINAL + LARGO combinado (ej: "#6-9[CRS] 5/8")
        # NOMINAL típico: #X-Y, #X-Y[CRS], números como M5, 5.2
        # LARGO típico: fracciones, medidas con ", números
        match = re.match(r'^(#[\d\-\[\]A-Za-z]+)\s+(.+)$', val)
        if match:
            result["NOMINAL"] = match.group(1)
            result["LARGO"] = match.group(2)
        else:
            # También verificar patrón M/número seguido de espacio
            match2 = re.match(r'^(M\d+[xX]?\d*[\.\d]*)\s+(.+)$', val)
            if match2:
                result["NOMINAL"] = match2.group(1)
                result["LARGO"] = match2.group(2)
            else:
                # Asumir que es solo LARGO (NOMINAL heredado)
                result["LARGO"] = val
    
    elif len(remaining) == 2:
        result["NOMINAL"] = remaining[0]
        result["LARGO"] = remaining[1]
    
    elif len(remaining) >= 3:
        result["NOMINAL"] = remaining[0]
        result["LARGO"] = remaining[1]
        # El tercero podría ser ENTRE CARAS u otro atributo
        if len(remaining) > 2:
            result["EXTRA"] = remaining[2]
    
    return result


def parse_table_row(line: str, column_positions: list[tuple[int, int, str]] | None = None) -> dict[str, str] | None:
    """
    Parsea una fila de tabla usando división por espacios múltiples.
    Retorna dict con CODIGO, NOMINAL, LARGO, ENVASE, etc. o None si no es fila válida.
    """
    stripped = line.strip()
    if not stripped:
        return None
    
    # Dividir por espacios múltiples
    parts = re.split(r"\s{2,}", stripped)
    parts = [p.strip() for p in parts if p.strip()]
    
    if not parts:
        return None
    
    return parse_row_parts(parts)


def detect_column_positions(header_line: str) -> list[tuple[int, int, str]]:
    """
    Detecta las posiciones de las columnas basándose en el encabezado.
    Retorna lista de (inicio, fin, nombre_columna).
    Ahora detecta TODAS las ocurrencias de cada columna (para headers con dos tablas).
    """
    # Buscar palabras clave y TODAS sus posiciones
    keywords = ["CODIGO", "CÓDIGO", "NOMINAL", "LARGO", "ENVASE", "ENTRE CARAS", "PTA TORX", "COD TECFI"]
    upper = header_line.upper()
    
    positions = []
    for kw in keywords:
        kw_upper = kw.upper()
        # Buscar todas las ocurrencias
        idx = 0
        while True:
            idx = upper.find(kw_upper, idx)
            if idx < 0:
                break
            positions.append((idx, kw.replace("CÓDIGO", "CODIGO")))
            idx += len(kw)
    
    # Ordenar por posición
    positions.sort(key=lambda x: x[0])
    
    # Crear rangos de columnas
    columns = []
    for i, (pos, name) in enumerate(positions):
        if i + 1 < len(positions):
            end = positions[i + 1][0]
        else:
            end = pos + 15  # Última columna, dar espacio
        columns.append((pos, end, name))
    
    return columns


def is_header_line(line: str) -> bool:
    """Detecta línea de encabezado de tabla."""
    upper = line.upper().strip()
    return "CODIGO" in upper and ("NOMINAL" in upper or "LARGO" in upper)


def is_finish_line(line: str) -> bool:
    """Detecta línea de acabado."""
    stripped = line.strip().lower()
    finishes = [
        "zincado", "fosfatizado", "ruspert", "dacromet", "iridiscente",
        "balde", "envase pequeño", "acero inoxidable", "inox",
        "acabado especial", "revestimiento", "bronce",
    ]
    return any(stripped.startswith(f) for f in finishes)


def is_title_line(line: str) -> bool:
    """Detecta línea de título de producto."""
    stripped = line.strip()
    if not stripped or len(stripped) < 5:
        return False
    if is_header_line(line):
        return False
    if is_finish_line(line):
        return False
    # Títulos típicos
    keywords = ["TORNILLO", "PERNO", "TUERCA", "GOLILLA", "AUTOPERFORANTE", 
                "REMACHE", "ANCLAJE", "TARUGO", "CLAVO", "BROCA", "DISCO",
                "CADENA", "CABLE", "FRAMER", "CONECTOR", "ESSVE"]
    upper = stripped.upper()
    return any(kw in upper for kw in keywords)


def is_subtype_line(line: str) -> bool:
    """Detecta línea de subtipo (ROSCA METAL, PUNTA FINA, etc.)."""
    stripped = line.strip()
    if not stripped or len(stripped) < 3:
        return False
    if is_header_line(line) or is_finish_line(line):
        return False
    # Subtipos típicos
    keywords = ["ROSCA", "PUNTA", "CABEZA", "C/GOLILLA", "SIN GOLILLA", 
                "HEXAGONAL", "PHILLIPS", "CONTINUACIÓN", "CONTINUACION",
                "INOX", "PARA", "DOS CAPAS", "DENSIDAD", "MADERA", "METAL"]
    upper = stripped.upper()
    return any(kw in upper for kw in keywords) and len(stripped) < 80


def is_subtype_text(text: str) -> bool:
    """Detecta si un texto (ya dividido) es un subtipo."""
    stripped = text.strip()
    if not stripped or len(stripped) < 3 or len(stripped) > 40:
        return False
    # Subtipos típicos
    keywords = ["ROSCA", "PUNTA", "CABEZA", "C/GOLILLA", "SIN GOLILLA", 
                "HEXAGONAL", "PHILLIPS", "CONTINUACIÓN", "CONTINUACION",
                "INOX", "PARA", "DOS CAPAS", "DENSIDAD", "MADERA", "METAL"]
    upper = stripped.upper()
    return any(kw in upper for kw in keywords)


def parse_half(
    lines_half: list[str],
    category: str,
    subcategory: str,
) -> tuple[list[dict], str, str]:
    """
    Parsea una mitad (izquierda o derecha) de las líneas.
    Retorna (productos, product_type, finish).
    """
    products = []
    current_product_type = ""
    current_subtype = ""
    current_finish = ""
    current_columns: list[tuple[int, int, str]] = []
    last_nominal = ""  # Para heredar NOMINAL cuando está vacío
    
    for line in lines_half:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Detectar sección FIJACIONES - ...
        if " - " in stripped and not is_header_line(line):
            parts = stripped.split(" - ", 1)
            if len(parts) == 2 and "CODIGO" not in stripped.upper():
                continue  # Es título de sección, ignorar aquí
        
        # Header de tabla - detectar posiciones de columnas
        if is_header_line(line):
            current_columns = detect_column_positions(line)
            last_nominal = ""  # Reset al cambiar de tabla
            continue
        
        # Acabado
        if is_finish_line(line):
            current_finish = stripped
            continue
        
        # Título de producto
        if is_title_line(line) and not looks_like_sku(stripped.split()[0] if stripped.split() else ""):
            current_product_type = stripped
            current_subtype = ""
            continue
        
        # Subtipo
        if is_subtype_line(line) and not looks_like_sku(stripped.split()[0] if stripped.split() else ""):
            current_subtype = stripped
            continue
        
        # Fila de datos
        row = parse_table_row(line, current_columns if current_columns else None)
        if row and row.get("CODIGO"):
            sku = row["CODIGO"]
            
            # Heredar NOMINAL si está vacío
            nominal = row.get("NOMINAL", "").strip()
            if nominal:
                last_nominal = nominal
            else:
                row["NOMINAL"] = last_nominal
            
            # Construir atributos
            attrs = []
            for key in ["NOMINAL", "LARGO", "ENVASE", "ENTRE CARAS", "PTA TORX", "COD TECFI", "EXTRA1", "EXTRA2"]:
                if key in row and row[key]:
                    # Renombrar EXTRA a algo más descriptivo
                    name = key if not key.startswith("EXTRA") else f"Atributo {key[-1]}"
                    attrs.append({"name": name, "value": row[key]})
            
            # Agregar acabado
            if current_finish:
                attrs.append({"name": "Acabado", "value": current_finish})
            
            # Construir path
            cat_path = []
            if category:
                cat_path.append(category)
            if subcategory:
                cat_path.append(subcategory)
            if current_product_type:
                cat_path.append(current_product_type)
            if current_subtype:
                cat_path.append(current_subtype)
            
            products.append({
                "sku": sku,
                "category_path": cat_path,
                "attributes": attrs,
            })
    
    return products, current_product_type, current_finish


def parse_spatial_catalog(text: str) -> tuple[dict[str, Any], dict[str, dict]]:
    """
    Parsea el catálogo con dos columnas lado a lado.
    Procesa línea por línea dividiendo en el gap central.
    """
    lines = text.splitlines()
    
    structure: dict[str, Any] = {}
    products: dict[str, dict] = {}
    
    # Estado actual - separado para izquierda y derecha
    current_category = "FIJACIONES"
    current_subcategory = "Tornillos para Volcanita"
    # Tipo de producto separado para cada columna
    product_type_left = ""
    product_type_right = ""
    subtype_left = ""
    subtype_right = ""
    finish_left = ""
    finish_right = ""
    last_nominal_left = ""
    last_nominal_right = ""
    
    # Para acumular títulos de múltiples líneas
    pending_title_left = ""
    pending_title_right = ""
    
    # Posición del gap central (donde empieza la tabla derecha)
    # Detectar desde headers con doble CODIGO
    gap_end_positions = []
    for line in lines:
        upper = line.upper()
        if upper.count("CODIGO") >= 2:
            first = upper.find("CODIGO")
            second = upper.find("CODIGO", first + 6)
            if second > 0:
                gap_end_positions.append(second)
    
    gap_end_pos = int(sum(gap_end_positions) / len(gap_end_positions)) if gap_end_positions else 56
    has_two_tables = len(gap_end_positions) > 0
    
    for line in lines:
        # Saltar marcadores de página
        if "Página" in line and " de " in line:
            continue
        if line.strip() == "<<<":
            continue
        
        # Detectar cambio de sección (FIJACIONES - Tornillos para Volcanita)
        # Excluir líneas con "Continuación" que son continuación de tipos de producto
        if " - " in line and "CODIGO" not in line.upper() and "CONTINUACI" not in line.upper():
            stripped = line.strip()
            # Verificar que parece una sección real (empieza con categoría conocida)
            if stripped.upper().startswith(("FIJACIONES", "ANCLAJES", "HERRAMIENTAS", "CADENAS")):
                parts = stripped.split(" - ", 1)
                if len(parts) == 2:
                    current_category = parts[0].strip()
                    current_subcategory = parts[1].strip()
                    product_type_left = ""
                    product_type_right = ""
                    subtype_left = ""
                    subtype_right = ""
                    pending_title_left = ""
                    pending_title_right = ""
                    continue
        
        # Detectar header de tabla - esto finaliza títulos pendientes
        if is_header_line(line):
            # Consolidar títulos pendientes
            if pending_title_left:
                product_type_left = pending_title_left
                pending_title_left = ""
            if pending_title_right:
                product_type_right = pending_title_right
                pending_title_right = ""
            last_nominal_left = ""
            last_nominal_right = ""
            continue
        
        # Dividir línea en mitades para procesamiento INDEPENDIENTE
        left_part, right_part = split_line_halves(line, gap_end_pos)
        left_stripped = left_part.strip()
        right_stripped = right_part.strip()
        
        # ========== PROCESAR MITAD IZQUIERDA ==========
        if left_stripped:
            # Detectar header en izquierda
            if is_header_line(left_part):
                if pending_title_left:
                    product_type_left = pending_title_left
                    pending_title_left = ""
                last_nominal_left = ""
            # Detectar acabado en izquierda
            elif is_finish_line(left_part):
                finish_left = left_stripped
            # Detectar título en izquierda
            elif is_title_line(left_part) and not looks_like_sku(left_stripped.split()[0] if left_stripped.split() else ""):
                if pending_title_left:
                    pending_title_left += " " + left_stripped
                else:
                    pending_title_left = left_stripped
            # Detectar subtipo en izquierda
            elif is_subtype_text(left_stripped) and not looks_like_sku(left_stripped.split()[0] if left_stripped.split() else ""):
                if pending_title_left:
                    pending_title_left += " " + left_stripped
                else:
                    subtype_left = left_stripped
            # Fila de datos izquierda
            else:
                row_left = parse_table_row(left_part)
                if row_left and row_left.get("CODIGO"):
                    sku = row_left["CODIGO"]
                    nominal = row_left.get("NOMINAL", "").strip()
                    if nominal:
                        last_nominal_left = nominal
                    else:
                        row_left["NOMINAL"] = last_nominal_left
                    
                    _add_product(products, structure, sku, row_left, 
                                current_category, current_subcategory, 
                                product_type_left, subtype_left, finish_left)
        
        # ========== PROCESAR MITAD DERECHA ==========
        if has_two_tables and right_stripped:
            # Detectar header en derecha
            if is_header_line(right_part):
                if pending_title_right:
                    product_type_right = pending_title_right
                    pending_title_right = ""
                last_nominal_right = ""
            # Detectar acabado en derecha
            elif is_finish_line(right_part):
                finish_right = right_stripped
            # Detectar título en derecha
            elif is_title_line(right_part) and not looks_like_sku(right_stripped.split()[0] if right_stripped.split() else ""):
                if pending_title_right:
                    pending_title_right += " " + right_stripped
                else:
                    pending_title_right = right_stripped
            # Detectar subtipo en derecha
            elif is_subtype_text(right_stripped) and not looks_like_sku(right_stripped.split()[0] if right_stripped.split() else ""):
                if pending_title_right:
                    pending_title_right += " " + right_stripped
                else:
                    subtype_right = right_stripped
            # Fila de datos derecha
            else:
                row_right = parse_table_row(right_part)
                if row_right and row_right.get("CODIGO"):
                    sku = row_right["CODIGO"]
                    nominal = row_right.get("NOMINAL", "").strip()
                    if nominal:
                        last_nominal_right = nominal
                    else:
                        row_right["NOMINAL"] = last_nominal_right
                    
                    _add_product(products, structure, sku, row_right,
                                current_category, current_subcategory,
                                product_type_right, subtype_right, finish_right)
    
    return structure, products


def _extract_row_by_columns(line: str, columns: list[tuple[int, int, str]]) -> dict[str, str] | None:
    """Extrae valores de una línea usando posiciones absolutas de columnas. (Deprecated, usar parse_table_row)"""
    if not columns:
        return None
    
    result = {}
    for start, end, name in columns:
        value = line[start:end].strip() if start < len(line) else ""
        result[name] = value
    
    # Verificar que CODIGO sea válido
    sku = result.get("CODIGO", "")
    if not looks_like_sku(sku):
        return None
    
    return result


def _add_product(products, structure, sku, row, category, subcategory, product_type, subtype, finish):
    """Agrega un producto al diccionario y estructura."""
    # Normalizar y limpiar tipo de producto
    clean_product_type = product_type
    if clean_product_type:
        # Normalizar espacios múltiples
        clean_product_type = " ".join(clean_product_type.split())
        # Normalizar abreviaciones
        clean_product_type = clean_product_type.replace("R. METAL", "ROSCA METAL")
        clean_product_type = clean_product_type.replace("R. MAD.", "ROSCA MADERA")
        # Remover "- Continuación" del nombre (es la misma categoría)
        if "Continuación" in clean_product_type or "Continuacion" in clean_product_type:
            clean_product_type = clean_product_type.replace(" - Continuación", "").replace(" - Continuacion", "")
            clean_product_type = clean_product_type.strip()
    
    # Construir atributos
    attrs = []
    for key in ["NOMINAL", "LARGO", "ENVASE", "ENTRE CARAS", "PTA TORX", "COD TECFI"]:
        if key in row and row[key]:
            attrs.append({"name": key, "value": row[key]})
    
    if finish:
        attrs.append({"name": "Acabado", "value": finish})
    
    # Construir path de categoría
    cat_path = []
    if category:
        cat_path.append(category)
    if subcategory:
        cat_path.append(subcategory)
    if clean_product_type:
        cat_path.append(clean_product_type)
    if subtype:
        cat_path.append(subtype)
    
    # Guardar producto
    if sku not in products:
        products[sku] = {
            "category_path": cat_path,
            "attributes": attrs,
        }
    
    # Agregar a estructura
    node = structure
    for p in cat_path:
        if p not in node:
            node[p] = {}
        node = node[p]
    if "skus" not in node:
        node["skus"] = []
    if sku not in node["skus"]:
        node["skus"].append(sku)


def to_woocommerce_format(products: dict[str, dict]) -> dict[str, dict[str, str]]:
    """Convierte a formato WooCommerce."""
    woo = {}
    for sku, data in products.items():
        attrs = data.get("attributes", [])
        row = {}
        for i, attr in enumerate(attrs[:6], 1):
            row[f"Nombre del atributo {i}"] = attr["name"]
            row[f"Valor(es) del atributo {i}"] = attr["value"]
        woo[sku] = row
    return woo


def extract_catalog_from_text(text: str) -> dict[str, Any]:
    """Extrae el catálogo completo."""
    structure, products = parse_spatial_catalog(text)
    woo = to_woocommerce_format(products)
    
    return {
        "catalog_name": "Catalogo Mamut 2025",
        "total_products": len(products),
        "structure": structure,
        "products": products,
        "attributes_woocommerce": woo,
    }


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Uso: python catalogo_spatial_parser.py <archivo.txt> [salida.json]")
        sys.exit(1)
    
    txt_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "data/catalogo_extracted.json"
    
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    result = extract_catalog_from_text(text)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Extraídos {result['total_products']} productos")
    print(f"Guardado en: {out_path}")
    
    # Mostrar algunos ejemplos
    if result["products"]:
        print("\nEjemplos de productos extraídos:")
        for i, (sku, data) in enumerate(list(result["products"].items())[:5]):
            print(f"  {sku}: {[a['name']+'='+a['value'] for a in data['attributes'][:3]]}")
