# Extracción y validación del catálogo PDF Mamut

## Resumen

Se extrae del PDF **Catalogo_Mamut_2025.pdf**:

1. **Estructura del catálogo**: árbol de categorías con **nodos finales = SKU (CODIGO)**.
2. **Por cada SKU**: atributos con **Nombre del atributo 1, 2, 3...** y **Valor(es) del atributo 1, 2, 3...**, listos para WooCommerce.
3. **Validador**: elegir por SKU si **Aceptar** (usar extraídos), **Mantener anterior** (maestro) o **Borrar** atributos.

---

## 1. Extraer del PDF

### Opción A: LLMWhisper (extracción espacial, recomendada)

Si instalas **LLMWhisper**, el texto se extrae con modo **layout_preserving** y se guarda en un **.txt** junto al PDF. En las siguientes ejecuciones se usa ese .txt y **no se vuelve a llamar a la API**.

```bash
pip install llmwhisperer-client
```

Configura la API (opcional; hay valor por defecto en código):

```bash
set LLMWHISPERER_API_KEY=tu_api_key
set LLMWHISPERER_BASE_URL_V2=https://llmwhisperer-api.us-central.unstract.com/api/v2
```

Ejecutar extracción (la primera vez extrae con LLMWhisper y guarda `pdf/Catalogo_Mamut_2025.txt`; después usa ese .txt):

```bash
python src/catalogo_pdf.py pdf/Catalogo_Mamut_2025.pdf data/catalogo_mamut_2025_extracted.json
```

Si ya tienes el .txt generado, puedes pasarlo directamente:

```bash
python src/catalogo_pdf.py pdf/Catalogo_Mamut_2025.txt data/catalogo_mamut_2025_extracted.json
```

Para forzar reextraer con LLMWhisper y sobrescribir el .txt:

```python
from src.catalogo_pdf import extract_catalogo, save_catalogo_json
data = extract_catalogo("pdf/Catalogo_Mamut_2025.pdf", force_extract=True)
save_catalogo_json(data, "data/catalogo_mamut_2025_extracted.json")
```

### Opción B: PyMuPDF (sin LLMWhisper)

Si no instalas `llmwhisperer-client`, se usa PyMuPDF para leer el PDF. Opcionalmente se guarda un .txt la primera vez.

```bash
pip install pymupdf
python src/catalogo_pdf.py pdf/Catalogo_Mamut_2025.pdf data/catalogo_mamut_2025_extracted.json
```

Salida en `data/catalogo_mamut_2025_extracted.json`:

- **`structure`**: árbol de categorías; cada rama puede tener `"skus": ["52ATPF", ...]` en los nodos finales.
- **`products`**: por cada SKU, `category_path` y `attributes` (lista de `{ "name", "value" }`).
- **`attributes_woocommerce`**: por cada SKU, `Nombre del atributo 1`, `Valor(es) del atributo 1`, ..., hasta 6 atributos.

---

## 2. Validar atributos (Aceptar / Mantener / Borrar)

Abrir el validador:

```bash
python validador_atributos_catalogo.py
```

O con archivos por defecto:

```bash
python validador_atributos_catalogo.py data/catalogo_mamut_2025_extracted.json data/processed/maestro_revision_*.xlsx
```

En la ventana:

1. **Archivo → Abrir catálogo extraído (JSON)**: el JSON generado en el paso 1.
2. **Archivo → Abrir maestro (Excel/CSV)**: tu maestro WooCommerce (opcional).
3. Selecciona un SKU en la lista.
4. Revisa **Extraídos (PDF)** vs **Actuales (Maestro)**.
5. Elige:
   - **Aceptar (usar extraídos)**: guardar en el resultado los atributos del PDF.
   - **Mantener anterior**: guardar los atributos actuales del maestro.
   - **Borrar atributos**: dejar atributos vacíos para ese SKU.
6. **Archivo → Exportar decisiones a JSON**: guarda decisiones y atributos mergeados.
7. **Archivo → Aplicar al maestro y guardar**: actualiza el Excel/CSV con los atributos validados y guarda en un nuevo archivo.

---

## Estructura del JSON extraído

Ejemplo de **`structure`** (árbol con nodos finales = SKUs):

```json
{
  "FIJACIONES": {
    "Tornillos para Metalcon": {
      "FRAMER": {
        "PUNTA FINA": { "skus": ["B30ATPF-G", "B30ATPF", "30ATPF-G", "30ATPF", "30ATPF-L"] },
        "PUNTA BROCA": { "skus": ["40ATPF-G", "40ATPF", "F40ATPF-G", "F40ATPF", "40ATPF-L"] }
      },
      "TORNILLO CABEZA LENTEJA": {
        "C/GOLILLA PUNTA FINA": { "skus": ["52ATPF", "65ATPF-G", "70ATPF-G", ...] }
      }
    }
  }
}
```

Ejemplo de **`products`** y **`attributes_woocommerce`** para un SKU:

```json
"52ATPF": {
  "category_path": ["FIJACIONES", "Tornillos para Metalcon"],
  "attributes": [
    { "name": "NOMINAL", "value": "#8" },
    { "name": "LARGO", "value": "1/2" },
    { "name": "ENVASE", "value": "500 U" },
    { "name": "Subcategoría / Acabado", "value": "Zincado Brillante" }
  ]
}
```

Formato WooCommerce (para importar/editar):

```json
"attributes_woocommerce": {
  "52ATPF": {
    "Nombre del atributo 1": "NOMINAL",
    "Valor(es) del atributo 1": "#8",
    "Nombre del atributo 2": "LARGO",
    "Valor(es) del atributo 2": "1/2",
    ...
  }
}
```

---

## Archivos creados

| Archivo | Descripción |
|--------|-------------|
| `src/catalogo_pdf.py` | Extracción del PDF: estructura + productos + atributos WooCommerce. |
| `validador_atributos_catalogo.py` | GUI para validar atributos: Aceptar / Mantener / Borrar y aplicar al maestro. |
| `data/catalogo_mamut_2025_extracted.json` | Salida de la extracción (se genera al ejecutar el script). |
| `requirements.txt` | Incluye `pymupdf` para lectura del PDF. |
