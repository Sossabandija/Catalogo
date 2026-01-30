# 📦 CATÁLOGO FERRETERÍA - WooCommerce Pipeline

Sistema determinista y auditable para transformar catálogos planos de ferretería en estructuras WooCommerce con validación humana obligatoria.

---

## 🎯 Objetivo

Convertir un Excel plano (~5.000 registros) de productos de ferretería en un catálogo estructurado para WooCommerce con:

- ✅ Productos variables (padre + variaciones)
- ✅ Atributos técnicos extraídos automáticamente
- ✅ Revisión humana obligatoria antes de exportación
- ✅ Auditoría completa del proceso
- ✅ Cero modificaciones destructivas

---

## 🏗️ Arquitectura

```
catalogo/
├── data/
│   ├── raw/              # Copias de entrada (audit trail)
│   ├── processed/        # Datos limpiados y enriquecidos
│   └── reviewed/         # Datos aprobados por humano
├── src/
│   ├── __init__.py
│   ├── loader.py         # Carga Excel sin modificar original
│   ├── cleaner.py        # Normalización y detección de patrones
│   ├── patterns.py       # Extracción de atributos técnicos (regex)
│   ├── attributes.py     # Agrupación de variaciones (próximo)
│   ├── grouping.py       # Detección de producto padre
│   ├── review.py         # Generación de formato maestro
│   └── exporter.py       # Exportación WooCommerce (bloqueado hasta aprobación)
├── config/
│   └── rules.yaml        # Reglas deterministas (sin ML)
├── main.py               # Orquestación del pipeline
└── README.md
```

---

## 📋 FORMATO MAESTRO DEFINITIVO

El sistema genera un Excel con estas columnas **exactas** para revisión humana:

### Columnas Obligatorias

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| **Tipo** | simple/variable | Tipo de producto | simple, variable |
| **SKU** | string | Código único del producto | AZA-TITAN-001 |
| **SKU Parent** | string | SKU del producto padre (si es variación) | AZA-TITAN |
| **Nombre** | string | Nombre limpio y estandarizado | ABRAZADERA TITAN MINI |
| **Slug** | string | URL amigable | abrazadera-titan-mini |
| **Publicado** | Sí/No | Visible en tienda | Sí |
| **Visibilidad** | Visible/Catálogo/Búsqueda/Oculto | | Visible |
| **Descripción** | text | Descripción larga | Abrazadera de carbono... |
| **Descripción Corta** | text | Resumen breve | Abrazadera pequeña |
| **Categoría** | string | Categoría WooCommerce | Fijaciones > Abrazaderas |
| **Etiquetas** | string | Tags separados por coma | acero, pequeño |
| **Marca** | string | Marca del producto | TITAN |
| **Imágenes** | URL | URL de imagen o ID | /img/abrazadera-001.jpg |
| **Posición** | número | Orden en categoría | 1 |

### Columnas de Precios y Stock

| Columna | Tipo | Descripción | Nota |
|---------|------|-------------|------|
| **Precio** | decimal | Precio base | Productos padre = vacío |
| **Precio Oferta** | decimal | Precio con descuento | Opcional |
| **Stock** | número | Cantidad en stock | |
| **Estado Stock** | En stock/Sin stock | | |
| **Gestionar Stock** | Sí/No | | Sí |
| **Permitir Reservas** | Sí/No | | No |

### Columnas de Dimensiones

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **Peso** | decimal | Kilogramos |
| **Largo** | decimal | Centímetros |
| **Ancho** | decimal | Centímetros |
| **Alto** | decimal | Centímetros |

### Columnas de Atributos (repetidas hasta 10)

Para cada atributo (hasta 10):

| Columna | Tipo | Descripción |
|---------|------|-------------|
| **Atributo N** | string | Nombre del atributo | Diámetro |
| **Valor Atributo N** | string | Valor del atributo | 1/4" |
| **Visible Atributo N** | Sí/No | Mostrar en ficha | Sí |
| **Global Atributo N** | Sí/No | Compartir en catálogo | Sí |
| **Usado para Variación N** | Sí/No | Define variaciones | Sí/No |

### Columnas de Auditoría

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| **Confianza Automática** | 0-100 | Score de extracción automática | 85 |
| **Revisado Humano** | Sí/No | ✓ Aprobado por humano | Sí |
| **Notas Revisión** | text | Cambios manuales realizados | Corregida marca, precio |

---

## 🔍 Reglas Deterministas (config/rules.yaml)

### 1. Familias de Productos

Detecta familia por palabras clave exactas:
```yaml
families:
  abrazaderas:
    keywords: ['abrazadera', 'abraza', 'clip']
    category: 'Fijaciones > Abrazaderas'
```

### 2. Atributos Técnicos (Regex)

Extrae medidas usando patrones deterministas:
```yaml
diametro:
  patterns:
    - '(\d+\.\d+/\d+)"'        # 1.1/8"
    - '(\d+)/(\d+)"'            # 1/4"
    - '(\d+(?:[.,]\d+)?)\s*mm'  # 10mm
```

### 3. Palabras Clave para Variaciones

Detecta qué atributos definen variaciones:
```yaml
variation_keywords:
  size: ['1/4', '3/8', '1/2', '5/8', '3/4', '7/8', '1"', 'mm']
  material: ['acero', 'galvanizado', 'inox']
```

---

## 🚀 Uso Básico

### Instalación

```bash
pip install pandas openpyxl pyyaml
```

### Ejecución del Pipeline

```bash
# Usar interfaz interactiva
python main.py

# O especificar archivo de entrada
python main.py --input data/raw/productos.xlsx

# Exportar después de revisión (fase 3)
python main.py --export data/processed/maestro_revision_*.xlsx
```

---

## 📊 Ejemplo de Transformación

### Entrada (Excel plano)

```
Nombre
ABRAZADERA TITAN MINI CRBON T10 1.1/8 (22-36)
ABRAZADERA TITAN MINI CRBON T10 3/8 (22-36)
ABRAZADERA TITAN MINI CRBON T10 1/2 (22-36)
```

### Paso 1: Limpieza (cleaner.py)

```
Nombre_Limpio: ABRAZADERA TITAN MINI CARBON T10
Familia_Detectada: abrazaderas
Marca_Detectada: TITAN
Tiene_Medidas: True
```

### Paso 2: Extracción de Atributos (patterns.py)

```
Atributo_diametro: 1.1/8", 3/8", 1/2"
Atributo_material: CARBON
Atributo_marca: TITAN
```

### Paso 3: Validación (attributes.py)

```
Atributo_diametro_validado:
  - Valor: 1 1/8", Válido: Sí, Confianza: 95%
  - Valor: 3/8", Válido: Sí, Confianza: 95%
  - Valor: 1/2", Válido: Sí, Confianza: 95%
```

### Paso 4: Agrupación (grouping.py)

```
Tipo: variable
SKU Parent: ABR-TITAN-MINI-T10
SKU (padre): ABR-TITAN-MINI-T10
SKU (var 1): ABR-TITAN-MINI-T10-1-8
SKU (var 2): ABR-TITAN-MINI-T10-3-8
SKU (var 3): ABR-TITAN-MINI-T10-1-2
```

### Paso 5: Formato Maestro (review.py)

```
Tipo,SKU,SKU_Parent,Nombre,Slug,Precio,Atributo_1,Valor_Atributo_1,Confianza_Automática,Revisado_Humano
variable,ABR-TITAN-MINI-T10,,ABRAZADERA TITAN MINI T10,abrazadera-titan-mini-t10,,Diámetro,,85,No
simple,ABR-TITAN-MINI-T10-1-8,ABR-TITAN-MINI-T10,ABRAZADERA TITAN MINI T10 1 1/8",abrazadera-titan-mini-t10-1-1-8,0,Diámetro,1 1/8",95,No
```

---

## ⚠️ Reglas Críticas

❌ **NUNCA:**
- Modificar archivo original
- Exportar sin revisión humana
- Usar machine learning o IA
- Inferir datos faltantes
- Asignar precio a productos padre

✅ **SIEMPRE:**
- Mantener trazabilidad completa
- Documentar cada decisión automática
- Detener flujo para revisión humana
- Usar reglas deterministas (regex, palabras clave)
- Calcular confianza automática

---

## 🧪 Módulos Implementados

### ✅ loader.py
- ✓ Cargar Excel original (solo lectura)
- ✓ Validar estructura y columnas
- ✓ Generar checksums para auditoría
- ✓ Guardar copias en data/raw/

### ✅ cleaner.py
- ✓ Normalizar nombres (espacios, mayúsculas)
- ✓ Remover ruido (stock, disponible, promo)
- ✓ Detectar familia por palabras clave
- ✓ Extraer marca preliminar
- ✓ Detectar si hay medidas

### ✅ patterns.py
- ✓ Extraer atributos por regex deterministas
- ✓ Diámetro (fracciones, mm)
- ✓ Largo (cm, m)
- ✓ Grosor (mm)
- ✓ Material (palabras clave)
- ✓ Cantidad (pack, caja, bolsa)

### ✅ attributes.py
- ✓ Validar atributos contra estándares
- ✓ Normalizar unidades (mm ↔ fracciones)
- ✓ Detectar inconsistencias
- ✓ Calcular confianza de validación

### ✅ grouping.py
- ✓ Detectar productos padre (kits, surtidos)
- ✓ Agrupar variaciones por atributos
- ✓ Generar SKU jerárquico
- ✓ Validar estructura padre-hijo

### ✅ review.py
- ✓ Generar formato maestro exacto
- ✓ Calcular confianza automática
- ✓ Crear Excel para revisión humana
- ✓ Guardar en data/processed/

### ⏳ Próximo (fase 3)
- [ ] exporter.py: Exportar CSV WooCommerce

---

## 📝 Decisiones Técnicas Documentadas

### Por qué regex en vez de ML

- ✅ **Determinista**: Mismo input = mismo output siempre
- ✅ **Auditable**: Cada match se puede rastrear al patrón usado
- ✅ **Sin datos**: No requiere entrenamiento
- ✅ **Controlable**: El usuario define reglas en YAML
- ❌ Menos flexible para casos extremos (por diseño)

### Por qué columnas de auditoría

- Trazabilidad completa del proceso
- Usuario ve qué fue automático vs. corregido
- Permite auditar decisiones disputadas

### Por qué parar antes de exportar

- Evita exportaciones con errores sistemáticos
- Permite correcciones en lote en Excel
- Garantiza calidad del catálogo final

---

## 🐛 Limitaciones Conocidas

| Limitación | Impacto | Mitigation |
|-----------|--------|-----------|
| Solo nombres para extraer | Bajo si hay datos buenos | Extender a descripciones |
| Fracciones solo en inglés | Bajo en ferretería | Agregar patrones españoles |
| Sin detección de sinonimos | Bajo con reglas.yaml buenas | Ampliar keywords |

---

## 📞 Soporte y Debugging

Cada módulo tiene logging completo:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Archivos de auditoría:
- `data/raw/metadata_*.json` - Checksums y metadatos
- `data/raw/raw_*.csv` - Copia exacta de entrada
- Logs en consola con timestamps

---

## 📄 Licencia

Uso interno. Código documentado y reproducible.

