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

# Logos/marcas que aparecen en el PDF pero NO son parte del texto del catálogo
LOGO_BLACKLIST = frozenset({
    "ESSVE",  # Marca de herramientas que aparece como logotipo
    "KNAPP",  # connectors.com
})

# Palabras que NO son SKUs
SKU_BLACKLIST = frozenset({
    "BALDE", "NUEVO", "CODIGO", "CÓDIGO", "NOMINAL", "LARGO", "ENVASE",
    "PHILLIPS", "POZI", "TORX", "ENTRE", "CARAS", "COLOR", "DESCRIPCIÓN",
    "DIÁMETRO", "ESPESOR", "ANCHO", "ALTO", "INOX", "ACERO", "BRONCE",
    "NYLON", "ZINC", "ZINCADO", "FOSFATIZADO", "RUSPERT", "DACROMET",
    "IRIDISCENTE", "BRILLANTE", "ESPECIAL", "CONTINUACIÓN", "CONTINUACION",
    "PTA", "ENVASE", "U", "TORNILLO", "PERNO", "TUERCA", "GOLILLA",
    "AUTOPERFORANTE", "AUTOP", "HEX", "HEXAGONAL", "CAB", "CABEZA",
    # Tipos de soldadura AWS - son parte del nombre, no SKUs
    "E6010", "E6011", "E7018", "E6010/6011/7018",
    # Valores de PTA TORX (punta Torx) - NO son SKUs
    "T10", "T15", "T20", "T25", "T30", "T40", "T50", "T55", "T60",
})


def fix_ocr_errors(sku: str) -> str:
    """
    Corrige errores comunes de OCR en códigos SKU.
    
    Problema: La letra "O" se confunde con el número "0".
    Ejemplo: "NO4RLBC" debería ser "N04RLBC"
    
    Regla: Si hay un patrón "O" seguido de dígito, es probable que sea "0"+dígito.
    """
    if not sku:
        return sku
    # Reemplazar O seguido de dígito por 0 seguido de dígito
    # Ejemplo: NO4 -> N04, O1ABC -> 01ABC
    corrected = re.sub(r'O([0-9])', r'0\1', sku)
    return corrected


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


def clean_logo_text(text: str) -> str:
    """
    Elimina logos/marcas del texto.
    Por ejemplo: "TORNILLO PARA ESSVE" -> "TORNILLO PARA"
                 "ESSVE" -> ""
    """
    if not text:
        return text
    words = text.split()
    cleaned = [w for w in words if w.upper() not in LOGO_BLACKLIST]
    return " ".join(cleaned)


def split_line_halves(line: str, gap_end_pos: int = 56) -> tuple[str, str]:
    """
    Divide una línea en mitad izquierda y derecha.
    Usa gap_end_pos como referencia para la posición donde termina la tabla izquierda.
    """
    import re
    
    if len(line) <= gap_end_pos:
        return line.rstrip(), ""
    
    # Buscar el gap que termina cerca de gap_end_pos (tolerancia de ±10 caracteres)
    gaps = list(re.finditer(r' {4,}', line))
    
    # Buscar un gap cuyo final esté cerca de gap_end_pos
    best_gap = None
    best_dist = float('inf')
    for g in gaps:
        # Preferir gaps que terminen cerca de gap_end_pos
        dist = abs(g.end() - gap_end_pos)
        if dist < best_dist and dist < 15:  # Tolerancia de 15 caracteres
            best_dist = dist
            best_gap = g
    
    if best_gap:
        left = line[:best_gap.start()].rstrip()
        right = line[best_gap.end():].strip()
        return left, right
    
    # Fallback: cortar en gap_end_pos buscando hacia atrás un espacio
    gap_start = gap_end_pos
    i = gap_end_pos - 1
    while i >= 0 and line[i:i+1] == ' ':
        gap_start = i
        i -= 1
    
    left = line[:gap_start].rstrip()
    right = line[gap_end_pos:].strip() if len(line) > gap_end_pos else ""
    return left, right


def parse_row_parts(parts: list[str]) -> dict[str, str] | None:
    """
    Parsea las partes de una fila y las asigna a columnas.
    Maneja casos donde NOMINAL y LARGO están juntos debido al OCR.
    También maneja casos donde SKU y NOMINAL están unidos en el primer part.
    Formato esperado: CODIGO [NOMINAL] LARGO ENVASE [ENTRE_CARAS]
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
    
    # Buscar ENVASE en cualquier posición (contiene " U" o termina con "U")
    # El formato típico es: CODIGO [NOMINAL] LARGO ENVASE [ENTRE_CARAS/COD_TECFI]
    # ENTRE_CARAS solo existe si ENVASE estaba en penúltima posición (antes del último elemento)
    envase = ""
    envase_idx = -1
    original_len = len(remaining)
    
    # Primero, manejar caso donde ENVASE viene separado: ['100', 'U', ...]
    # Buscar un número seguido de 'U' suelto
    for i in range(len(remaining) - 1):
        if re.match(r'^[\d,\.]+$', remaining[i]) and remaining[i + 1] == 'U':
            # Combinar número + U
            envase = remaining[i] + ' U'
            # Eliminar el número y la U, y todo lo que venga después (Cod Tecfi, etc.)
            # El último elemento después de "U" es típicamente Cod Tecfi que debemos ignorar
            if i + 2 < len(remaining):
                # Hay algo después de "U" (como Cod Tecfi) - ignorarlo
                remaining = remaining[:i] + remaining[i+2:i+3] if (i+3 <= len(remaining) and re.match(r'^[\d/]+$', remaining[i+2])) else remaining[:i]
            else:
                remaining = remaining[:i]
            result["ENVASE"] = envase
            break
    
    if not envase:
        for i, part in enumerate(remaining):
            # ENVASE típico: "500 U", "100 U", "1,000 U", "200 U b/BL2Eu"
            # También puede venir con Cod Tecfi pegado: "100 U AB0106180"
            if " U" in part:
                # Extraer solo la parte del ENVASE (número + U)
                envase_match = re.match(r'^([\d,\.]+\s*U)\b', part)
                if envase_match:
                    envase = envase_match.group(1)
                    # El resto después de "U " es Cod Tecfi - ignorar
                else:
                    envase = part
                envase_idx = i
                break
            elif part.endswith("U") and re.match(r'^[\d,\.]+\s*U$', part):
                envase = part
                envase_idx = i
                break
        
        # ENTRE_CARAS solo existe si ENVASE era el penúltimo elemento original
        # Es decir, ENVASE estaba en posición len-2 y ENTRE_CARAS en len-1
        entre_caras = ""
        if envase_idx >= 0:
            # Si ENVASE era penúltimo y el último es una fracción sin ", es ENTRE_CARAS
            if envase_idx == original_len - 2:
                last = remaining[-1]
                if re.match(r'^[\d/]+$', last) and '"' not in last and len(last) <= 5:
                    entre_caras = remaining.pop()
            remaining.pop(envase_idx)
        
        result["ENVASE"] = envase
        if entre_caras:
            result["ENTRE_CARAS"] = entre_caras
    
    # Filtrar elementos que parezcan códigos Tecfi (SKU-like al final que no es ENTRE_CARAS)
    # Típicamente son como "AB0106180", "TX0163080" al final
    if remaining and looks_like_sku(remaining[-1]) and len(remaining) > 2:
        cod_tecfi = remaining.pop()  # Ignorar Cod Tecfi
    
    # Ahora remaining tiene [NOMINAL, LARGO] o [LARGO] o [NOMINAL+LARGO combinado]
    if not remaining:
        return result
    
    if len(remaining) == 1:
        val = remaining[0]
        # Verificar si es NOMINAL + LARGO combinado (ej: "#6-9[CRS] 5/8", "#5(3.70) 60", "#10-24[3/16] 3/4")
        # NOMINAL típico: #X-Y, #X-Y[CRS], #X(valor), #X-Y[fracción], números como M5, 5.2, 6.3[1/4-14]
        # LARGO típico: fracciones, medidas con ", números
        
        # Patrón 1: # seguido de dígitos, guiones, corchetes, paréntesis, barras, decimales
        match = re.match(r'^(#[\d\-\[\]A-Za-z\(\)\.\,\/]+)\s+(.+)$', val)
        if match:
            result["NOMINAL"] = match.group(1)
            result["LARGO"] = match.group(2)
        else:
            # Patrón 2: M seguido de número (métrico)
            match2 = re.match(r'^(M\d+[xX]?\d*[\.\d]*)\s+(.+)$', val)
            if match2:
                result["NOMINAL"] = match2.group(1)
                result["LARGO"] = match2.group(2)
            else:
                # Patrón 3: Número con corchetes como 6.3[1/4-14] seguido de espacio y LARGO
                # Formato: número.decimal[fracción-número] espacio largo
                match3 = re.match(r'^([\d\.]+\[[\d/\-]+\])\s+(.+)$', val)
                if match3:
                    result["NOMINAL"] = match3.group(1)
                    result["LARGO"] = match3.group(2)
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
        "acabado especial", "revestimiento", "bronce", "pavonado",
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
                "CADENA", "CABLE", "FRAMER", "CONECTOR"]
    upper = stripped.upper()
    # Ignorar líneas que son solo logos
    if upper in LOGO_BLACKLIST:
        return False
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


def is_incomplete_title(title: str) -> bool:
    """
    Detecta si un título está incompleto y necesita continuación.
    Por ejemplo: "TORNILLO PARA" necesita más texto.
    """
    if not title:
        return False
    words = title.strip().upper().split()
    if not words:
        return False
    # Palabras que indican título incompleto
    incomplete_endings = ["PARA", "DE", "CON", "EN", "A", "Y"]
    return words[-1] in incomplete_endings


def is_title_continuation(text: str) -> bool:
    """
    Detecta si un texto puede ser continuación de un título incompleto.
    Por ejemplo: "TERRAZAS", "DECK", "MADERA", etc.
    """
    stripped = text.strip()
    if not stripped or len(stripped) < 3 or len(stripped) > 30:
        return False
    upper = stripped.upper()
    # No puede ser un header, acabado, o tener dígitos (sería datos)
    if is_header_line(text) or is_finish_line(text):
        return False
    if re.search(r'\d', stripped):
        return False
    # No puede ser un logo
    if upper in LOGO_BLACKLIST:
        return False
    # Palabras que típicamente continúan títulos
    continuations = ["TERRAZAS", "DECK", "MADERA", "METALCON", "VOLCANITA",
                     "FACHADAS", "MOLDURAS", "AGLOMERADA", "DRYWALL"]
    return upper in continuations or (len(stripped) > 3 and stripped.isupper())


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
            current_product_type = clean_logo_text(stripped)
            current_subtype = ""
            continue
        
        # Subtipo
        if is_subtype_line(line) and not looks_like_sku(stripped.split()[0] if stripped.split() else ""):
            current_subtype = clean_logo_text(stripped)
            continue
        
        # Fila de datos
        row = parse_table_row(line, current_columns if current_columns else None)
        if row and row.get("CODIGO"):
            sku = fix_ocr_errors(row["CODIGO"])
            
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
    
    # Variable para detectar si acabamos de pasar un cambio de página
    after_page_break = False
    
    for line in lines:
        # Saltar marcadores de página
        if "Página" in line and " de " in line:
            continue
        if line.strip() == "<<<" or line.strip().startswith("<<<"):
            after_page_break = True
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
                    after_page_break = False
                    continue
        
        # Detectar recordatorio de subcategoría o nueva sección principal después de cambio de página
        # Ej: "TORNILLOS PARA MADERA" sola después de "<<<"
        stripped = line.strip()
        if stripped and after_page_break:
            # Normalizar para comparación
            stripped_upper = " ".join(stripped.upper().split())  # Normalizar espacios
            
            # Lista de secciones principales que pueden aparecer después de page breaks
            # Estas son secciones de la página índice del catálogo
            KNOWN_MAIN_SECTIONS = [
                "TORNILLOS PARA VOLCANITA",
                "TORNILLOS PARA METALCON", 
                "TORNILLOS PARA FIBROCEMENTO",
                "TORNILLOS PARA DECK",
                "TORNILLOS PARA VENTANAS DE PVC",
                "TORNILLOS PARA MADERA",
                "TORNILLOS PARA MADERAS",
                "TORNILLOS WINGER",
                "TORNILLOS PARA FACHADAS",
                "TORNILLOS AUTOPERFORANTES",
                "ROSCALATAS Y ATERRAJADORES",
                "PUNTAS E INSERTOS",
                "PUNTAS, INSERTOS Y DADOS",
                "PERNOS HEXAGONALES",
                "PRODUCTOS PARA TECHO",
                "ANCLAJES",
                "TARUGOS",
                "CLAVOS",
                "CABLES, CADENAS Y ACCESORIOS",
                "BROCAS, DISCOS Y SOLDADURAS",
                "HERRAMIENTAS",
                "CONECTORES PARA MADERA",
                "PERNOS MÁQUINA",
                "COMPLEMENTOS DE LINEA",
            ]
            
            # Verificar si es una sección principal conocida
            for section in KNOWN_MAIN_SECTIONS:
                if section in stripped_upper or stripped_upper in section:
                    # Actualizar subcategoría a esta sección
                    current_subcategory = stripped.strip()
                    product_type_left = ""
                    product_type_right = ""
                    subtype_left = ""
                    subtype_right = ""
                    pending_title_left = ""
                    pending_title_right = ""
                    after_page_break = False
                    break
            else:
                # Si no matchea ninguna sección conocida, verificar si es recordatorio
                subcat_upper = " ".join(current_subcategory.upper().split())
                if stripped_upper in subcat_upper or subcat_upper in stripped_upper:
                    # Es un recordatorio de subcategoría, ignorar
                    pending_title_left = ""
                    pending_title_right = ""
                    after_page_break = False
            if not after_page_break:
                continue
        
        # Si ya procesamos una línea no vacía después del page break, desactivar flag
        if stripped:
            after_page_break = False
        
        # Detectar header de tabla en la línea COMPLETA
        # NOTA: No resetear nominales aquí, hacerlo después del split para cada lado
        if is_header_line(line):
            # Consolidar títulos pendientes
            if pending_title_left:
                product_type_left = clean_logo_text(pending_title_left)
                pending_title_left = ""
            if pending_title_right:
                product_type_right = clean_logo_text(pending_title_right)
                pending_title_right = ""
            # Solo continuar si la línea SOLO tiene header (no datos)
            # Si hay datos en un lado, procesar normalmente
            left_test, right_test = split_line_halves(line, gap_end_pos)
            if is_header_line(left_test) and (not right_test or is_header_line(right_test)):
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
                    product_type_left = clean_logo_text(pending_title_left)
                    pending_title_left = ""
                last_nominal_left = ""
                # Resetear subtipo cuando hay nueva tabla (nuevo header)
                subtype_left = ""
            # Detectar acabado en izquierda
            elif is_finish_line(left_part):
                finish_left = left_stripped
                # Si el acabado NO es "continuación", resetear subtipo
                if "continuaci" not in left_stripped.lower():
                    subtype_left = ""
            # Detectar título en izquierda
            elif is_title_line(left_part) and not looks_like_sku(left_stripped.split()[0] if left_stripped.split() else ""):
                if pending_title_left:
                    pending_title_left += " " + left_stripped
                else:
                    pending_title_left = left_stripped
            # Detectar continuación de título incompleto (ej: "TERRAZAS" después de "TORNILLO PARA")
            elif pending_title_left and is_incomplete_title(pending_title_left) and is_title_continuation(left_stripped):
                pending_title_left += " " + left_stripped
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
                    sku = fix_ocr_errors(row_left["CODIGO"])
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
                    product_type_right = clean_logo_text(pending_title_right)
                    pending_title_right = ""
                last_nominal_right = ""
                # Resetear subtipo cuando hay nueva tabla (nuevo header)
                subtype_right = ""
            # Detectar acabado en derecha
            elif is_finish_line(right_part):
                finish_right = right_stripped
                # Si el acabado NO es "continuación", resetear subtipo
                # porque es una nueva sección de acabado
                if "continuaci" not in right_stripped.lower():
                    subtype_right = ""
            # Detectar título en derecha
            elif is_title_line(right_part) and not looks_like_sku(right_stripped.split()[0] if right_stripped.split() else ""):
                if pending_title_right:
                    pending_title_right += " " + right_stripped
                else:
                    pending_title_right = right_stripped
            # Detectar continuación de título incompleto (ej: "DECK DE MADERA" después de "TORNILLO PARA")
            elif pending_title_right and is_incomplete_title(pending_title_right) and is_title_continuation(right_stripped):
                pending_title_right += " " + right_stripped
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
                    sku = fix_ocr_errors(row_right["CODIGO"])
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
