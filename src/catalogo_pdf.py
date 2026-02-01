"""
Extracción del catálogo Mamut desde PDF.

- Estructura: árbol de categorías con nodos finales = SKU (CODIGO).
- Productos: por cada SKU, Nombre Atributo 1, 2, 3... y sus valores (listos para WooCommerce).
- Salida: JSON con estructura + productos para validar (aceptar / mantener anterior / borrar).

Opcionalmente usa LLMWhisper para extraer el PDF (extracción espacial) y guarda el texto en .txt
para no volver a llamar a la API si el archivo ya existe.
"""

import re
import json
from pathlib import Path
from typing import Any


def _get_llmwhisper_extract():
    """Import perezoso del módulo LLMWhisper para no fallar si no está instalado."""
    try:
        from src.llmwhisper_extract import get_pdf_text_as_txt
        return get_pdf_text_as_txt
    except ImportError:
        pass
    try:
        from llmwhisper_extract import get_pdf_text_as_txt
        return get_pdf_text_as_txt
    except ImportError:
        return None


def get_catalog_text(
    pdf_or_txt_path: str,
    txt_path: str | Path | None = None,
    use_llmwhisper: bool = True,
    force_extract: bool = False,
) -> str:
    """
    Obtiene el texto del catálogo para extracción espacial.

    - Si se pasa un .txt o existe el .txt asociado al PDF, se lee ese archivo (no se usa LLMWhisper).
    - Si se pasa un .pdf y no existe el .txt, se extrae con LLMWhisper (layout_preserving) y se guarda el .txt.
    - txt_path: dónde guardar/leer el .txt (por defecto mismo nombre que el PDF con extensión .txt).
    - use_llmwhisper: si True y hace falta extraer, usar LLMWhisper; si False, usar PyMuPDF (no guarda .txt).
    - force_extract: si True, reextraer siempre con LLMWhisper y sobrescribir el .txt.
    """
    path = Path(pdf_or_txt_path).resolve()
    if path.suffix.lower() == ".txt":
        if path.exists():
            return path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Archivo de texto no encontrado: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Se esperaba un PDF o TXT: {path}")

    if txt_path is None:
        txt_path = path.with_suffix(".txt")
    else:
        txt_path = Path(txt_path).resolve()

    if not force_extract and txt_path.exists():
        return txt_path.read_text(encoding="utf-8")

    get_txt = _get_llmwhisper_extract()
    if use_llmwhisper and get_txt is not None:
        return get_txt(
            str(path),
            txt_path=str(txt_path),
            force_extract=force_extract,
            use_llmwhisper=True,
        )

    # Fallback: PyMuPDF (no guarda .txt)
    pages = extract_text_from_pdf(str(path))
    all_text = "\n".join(t for _n, t in pages)
    if not force_extract and all_text.strip():
        try:
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            txt_path.write_text(all_text, encoding="utf-8")
        except OSError:
            pass
    return all_text


def extract_text_from_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Extrae texto de cada página del PDF con PyMuPDF. Retorna lista de (número_página, texto)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("Instala PyMuPDF: pip install pymupdf")

    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append((i + 1, text))
    doc.close()
    return pages


def _split_columns(line: str) -> list[str]:
    """Separa una línea en columnas (tabs o múltiples espacios)."""
    line = line.strip()
    if not line:
        return []
    parts = re.split(r"[\t]+|\s{2,}", line)
    return [p.strip() for p in parts if p.strip()]


def _normalize_line(s: str) -> str:
    return s.strip()


# Palabras que no son SKUs aunque coincidan con el patrón
_SKU_BLACKLIST = frozenset(
    {"BALDE", "NUEVO", "CODIGO", "CÓDIGO", "NOMINAL", "LARGO", "ENVASE", "PHILLIPS", "POZI", "TORX"}
)


def _looks_like_sku(token: str) -> bool:
    """Indica si un token parece un código SKU (ej. 52ATPF, 65ATPF-G, F52ATPF, 01TADB-J)."""
    if not token or len(token) < 2 or len(token) > 25:
        return False
    if token.upper() in _SKU_BLACKLIST:
        return False
    # Debe contener al menos un dígito o patrón típico (sufijo -G, -S, -L, número al inicio)
    t = token.upper()
    if not re.search(r"[0-9]|[\-\.]|[\[\]]", t):
        return False
    return bool(re.match(r"^[A-Z0-9][A-Z0-9\-\.\[\]]*$", t))


def _is_header_line(tokens: list[str]) -> bool:
    """Indica si la línea parece encabezado de tabla (CODIGO, NOMINAL, LARGO, ENVASE, etc.)."""
    if not tokens:
        return False
    first = (tokens[0] or "").upper()
    if first != "CODIGO" and first != "CÓDIGO":
        return False
    # Debe tener al menos 2 columnas
    return len(tokens) >= 2


def _is_data_row(tokens: list[str], attr_count: int) -> bool:
    """Indica si la línea parece fila de datos: primer token = SKU, resto = valores."""
    if not tokens or attr_count < 1:
        return False
    if not _looks_like_sku(tokens[0]):
        return False
    # Debe tener al menos SKU + algún valor (puede haber menos columnas que el header)
    return len(tokens) >= 1


def parse_index_pages(lines: list[str]) -> dict[str, Any]:
    """
    Parsea las primeras páginas (índice) para construir el árbol de categorías.
    El índice tiene ramas en mayúsculas y números de categoría.
    Retorna un árbol donde las hojas son listas de códigos de categoría (luego se rellenan con SKUs).
    """
    tree: dict[str, Any] = {}
    current_path: list[str] = []
    # Palabras que indican nueva rama principal (primera palabra de una línea en mayúsculas)
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # Saltar marcas de página
        if line.startswith("-- ") and " of " in line:
            continue
        if "Página " in line and " de " in line:
            continue
        # Línea en mayúsculas puede ser categoría
        upper = line.upper()
        if line == upper and len(line) > 2:
            tokens = line.split()
            if len(tokens) == 1:
                # Rama de un solo nombre
                current_path = [line]
            else:
                # Varias palabras: puede ser subcategoría
                if not current_path:
                    current_path = [line]
                else:
                    current_path = current_path[:1] + [line]
        # Líneas con números al final (1 1 2 2 2 2) son atributos del índice; no construimos hoja aquí
    # Por ahora el árbol del índice lo dejamos mínimo; la estructura real la armamos con las secciones
    return tree


_KNOWN_ATTR_HEADERS = frozenset({
    "NOMINAL", "LARGO", "ENVASE", "ENTRE CARAS", "COD TECFI", "COLOR", "DESCRIPCIÓN",
    "DIÁMETRO", "ESPESOR", "ANCHO", "ALTO", "PTA TORX", "PTA POZI", "PTA PHILLIPS",
})


def _find_header_block(lines: list[str], start: int) -> tuple[int, list[str]]:
    """
    En el PDF de Mamut, el encabezado de tabla viene como líneas sueltas:
    CODIGO \\n NOMINAL \\n LARGO \\n ENVASE (o más columnas).
    Retorna (índice siguiente al header, lista de nombres de atributos).
    """
    if start >= len(lines):
        return start, []
    if _normalize_line(lines[start]).upper() not in ("CODIGO", "CÓDIGO"):
        return start, []
    attr_names = []
    j = start + 1
    while j < len(lines):
        cell = _normalize_line(lines[j])
        if not cell:
            j += 1
            continue
        u2 = cell.upper()
        if u2 in ("CODIGO", "CÓDIGO"):
            j += 1
            continue
        if _looks_like_sku(cell):
            break
        added = False
        if u2 in _KNOWN_ATTR_HEADERS:
            attr_names.append(cell)
            j += 1
            added = True
        elif any(h in u2 for h in ("NOMINAL", "LARGO", "ENVASE", "ENTRE CARAS", "COD TECFI", "COLOR", "DESCRIPCIÓN", "ESPESOR", "ANCHO", "ALTO", "PTA ")):
            attr_names.append(cell)
            j += 1
            added = True
        if not added:
            break
    if not attr_names:
        attr_names = ["NOMINAL", "LARGO", "ENVASE"]
    return j, attr_names


def parse_product_pages(
    lines: list[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """
    Parsea páginas de productos. En el PDF Mamut cada celda viene en una línea;
    el encabezado es CODIGO \\n NOMINAL \\n LARGO \\n ENVASE y los datos en grupos de N líneas.

    Retorna:
    - tree: árbol categoría -> ... -> lista de SKUs (nodos finales).
    - products: { sku: { "category_path": [...], "attributes": [ {"name", "value"}, ... ] } }
    """
    tree: dict[str, Any] = {}
    products: dict[str, dict[str, Any]] = {}

    current_path: list[str] = []
    current_subheader: str = ""
    i = 0
    n_cols = 0
    attr_names: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = _normalize_line(line)
        if not stripped:
            i += 1
            continue
        if "Página " in stripped and " de " in stripped:
            i += 1
            continue

        # Sección "FIJACIONES - Tornillos para Metalcon"
        if " - " in stripped and not stripped.upper().startswith("CODIGO"):
            parts = stripped.split(" - ", 1)
            if len(parts) == 2:
                main, sub = parts[0].strip(), parts[1].strip()
                if main.upper() != "CODIGO":
                    current_path = [main, sub]
            i += 1
            continue

        # Encabezado de tabla: línea "CODIGO"
        if stripped.upper() in ("CODIGO", "CÓDIGO"):
            next_i, attr_names = _find_header_block(lines, i)
            n_cols = 1 + len(attr_names)
            i = next_i
            continue

        # Título de subsección (FRAMER, PUNTA FINA, TORNILLO CABEZA LENTEJA, Zincado Brillante, BALDE)
        if attr_names and _looks_like_sku(stripped):
            # Es un SKU: leer esta línea + (n_cols-1) siguientes = una fila
            sku = stripped
            values = []
            for k in range(1, n_cols):
                idx = i + k
                if idx < len(lines):
                    val = _normalize_line(lines[idx])
                    if val.upper() in ("CODIGO", "CÓDIGO"):
                        break
                    values.append(val)
                else:
                    values.append("")
            # Avanzar hasta después de la fila
            i += n_cols

            attrs = []
            for j, name in enumerate(attr_names):
                attrs.append({"name": name, "value": values[j] if j < len(values) else ""})
            if current_subheader:
                attrs.append({"name": "Subcategoría / Acabado", "value": current_subheader})

            if sku not in products:
                products[sku] = {"category_path": list(current_path), "attributes": attrs}
            else:
                existing = {a["name"]: a["value"] for a in products[sku]["attributes"]}
                for a in attrs:
                    if a["name"] not in existing:
                        products[sku]["attributes"].append(a)

            node = tree
            for p in current_path:
                if p not in node:
                    node[p] = {}
                node = node[p]
            if "_skus" not in node:
                node["_skus"] = []
            if sku not in node["_skus"]:
                node["_skus"].append(sku)
            continue

        # Subheader (Zincado Brillante, Fosfatizado, BALDE, etc.) antes de filas
        if not _looks_like_sku(stripped) and stripped.upper() not in ("CODIGO", "CÓDIGO", "NOMINAL", "LARGO", "ENVASE"):
            if len(stripped) < 60 and "Página" not in stripped:
                current_subheader = stripped
            i += 1
            continue

        # Título de subsección que empuja path (ej. FRAMER, PUNTA FINA, TORNILLO CABEZA LENTEJA)
        if current_path and not _looks_like_sku(stripped) and " - " not in stripped:
            if len(stripped) < 70 and stripped.upper() not in ("CODIGO", "NOMINAL", "LARGO", "ENVASE"):
                new_path = current_path + [stripped]
                if len(new_path) <= 5:
                    current_path = new_path
        i += 1
    return tree, products


def _tree_without_skus_key(node: dict) -> dict:
    """Copia el árbol quitando la clave interna '_skus' para exportar solo estructura con hijos."""
    out = {}
    for k, v in node.items():
        if k == "_skus":
            out["skus"] = v  # Nodos finales = lista de SKUs
            continue
        if isinstance(v, dict):
            out[k] = _tree_without_skus_key(v)
        else:
            out[k] = v
    return out


def extract_catalogo(
    pdf_path: str,
    txt_path: str | Path | None = None,
    use_llmwhisper: bool = True,
    force_extract: bool = False,
) -> dict[str, Any]:
    """
    Extrae del PDF (o del .txt ya generado) la estructura del catálogo y los productos con atributos.

    - Si existe un .txt asociado al PDF (mismo nombre con extensión .txt), se usa ese texto
      y no se llama a LLMWhisper.
    - Si no existe el .txt y use_llmwhisper=True, se extrae con LLMWhisper (layout_preserving)
      y se guarda el .txt para próximas ejecuciones.
    - pdf_path: ruta al PDF o al .txt (ej. pdf/Catalogo_Mamut_2025.pdf o pdf/Catalogo_Mamut_2025.txt).
    - txt_path: dónde guardar/leer el .txt (por defecto mismo que el PDF con .txt).
    - use_llmwhisper: si True, usar LLMWhisper cuando haga falta; si False, usar PyMuPDF.
    - force_extract: si True, reextraer con LLMWhisper y sobrescribir el .txt.

    Retorna un diccionario con:
    - "catalog_name": nombre del catálogo
    - "structure": árbol de categorías; los nodos finales tienen "skus": [lista de CODIGO]
    - "products": { "SKU": { "category_path": [...], "attributes": [ {"name", "value"}, ... ] } }
    - "attributes_woocommerce": por cada SKU, atributos en formato WooCommerce (Nombre Atributo 1, Valor 1, etc.)
    """
    text = get_catalog_text(
        pdf_path,
        txt_path=txt_path,
        use_llmwhisper=use_llmwhisper,
        force_extract=force_extract,
    )
    all_lines = text.splitlines()

    # Índice: primeras páginas (hasta que aparezca "CODIGO" en una línea de tabla)
    index_tree = parse_index_pages(all_lines)

    # Productos: todas las líneas
    structure_tree, products = parse_product_pages(all_lines)

    # Formato WooCommerce: hasta 6 atributos (Nombre del atributo 1, Valor(es) del atributo 1, ...)
    attributes_woocommerce = {}
    for sku, data in products.items():
        attrs = data.get("attributes", [])
        woo = {}
        for i in range(1, 7):
            name_key = f"Nombre del atributo {i}"
            val_key = f"Valor(es) del atributo {i}"
            if i <= len(attrs):
                woo[name_key] = attrs[i - 1].get("name", "")
                woo[val_key] = attrs[i - 1].get("value", "")
            else:
                woo[name_key] = ""
                woo[val_key] = ""
        attributes_woocommerce[sku] = woo

    return {
        "catalog_name": Path(pdf_path).stem,
        "structure": _tree_without_skus_key(structure_tree),
        "products": products,
        "attributes_woocommerce": attributes_woocommerce,
    }


def save_catalogo_json(data: dict[str, Any], out_path: str) -> None:
    """Guarda el resultado de extract_catalogo en un JSON."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_catalogo_json(json_path: str) -> dict[str, Any]:
    """Carga el JSON del catálogo extraído."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if a.startswith("--")]
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    pdf = pos[0] if len(pos) > 0 else "pdf/Catalogo_Mamut_2025.pdf"
    out = pos[1] if len(pos) > 1 else "data/catalogo_mamut_2025_extracted.json"
    force_extract = "--force-extract" in args
    use_llmwhisper = "--no-llmwhisper" not in args

    print(f"Extrayendo de {pdf} ...")
    if force_extract:
        print("(Forzando reextracción con LLMWhisper y sobrescribiendo .txt)")
    if not use_llmwhisper:
        print("(Usando PyMuPDF, no LLMWhisper)")
    data = extract_catalogo(pdf, use_llmwhisper=use_llmwhisper, force_extract=force_extract)
    save_catalogo_json(data, out)
    n_products = len(data.get("products", {}))
    print(f"Guardado en {out}. Productos: {n_products}.")
