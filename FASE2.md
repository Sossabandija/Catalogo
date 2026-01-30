# 🔧 FASE 2: VALIDACIÓN, NORMALIZACIÓN Y AGRUPACIÓN

Documentación detallada de los módulos de la Fase 2.

---

## 📋 Módulos de Fase 2

### 1. attributes.py - Validación de Atributos

**Responsabilidad**: Asegurar que atributos extraídos sean válidos y normalizados.

**Inputs**: DataFrame con atributos extraídos por patterns.py

**Outputs**: DataFrame con columnas `*_validado` conteniendo:
- `normalized`: Valor normalizado a estándar
- `is_valid`: True/False/None (desconocido)
- `confidence`: Score 0-1
- `notes`: Razón de la decisión

#### Validadores Específicos

**Diámetro**:
- Busca en tabla de estándares: 1/4", 3/8", 1/2", etc.
- Normaliza variantes: "1/4" vs "0.25" vs "1/4"
- Rango válido: 0-100 (en mm o pulgadas)
- Confianza alta (95%) si está en tabla estándar

**Largo**:
- Estándares: 5cm, 10cm, 20cm, 1m, 2m, 5m, etc.
- Convierte unidades: 100mm → 10cm (si está en rango)
- Tolerancia: ±5cm para emparejar a estándar más cercano

**Grosor**:
- Solo acepta mm
- Rango: 0.5-50mm típicamente
- Rechaza si unidad no es mm

**Material**:
- Tabla conocida: acero, inox, cobre, aluminio, galvanizado, etc.
- Búsqueda parcial: "acero inoxidable" → "inox"
- Muy permisivo (confianza 0.3 incluso si no reconoce)

**Marca**:
- Valida formato: 2+ caracteres, mayúsculas
- Confianza 0.85 si formato correcto
- Normaliza a uppercase

**Cantidad**:
- Solo números enteros 1-10000
- Confianza 0.95 si válido

#### Uso

```python
from src.attributes import validate_attributes

df = extract_attributes(df)
df_validated = validate_attributes(df)

# Acceder a validación
for idx, row in df_validated.iterrows():
    if row['Atributo_diametro_validado']:
        val = row['Atributo_diametro_validado']
        print(f"Diámetro: {val['normalized']} (confianza: {val['confidence']})")
```

---

### 2. grouping.py - Agrupación en Padre + Variaciones

**Responsabilidad**: Detectar productos padre y agrupar variaciones.

**Inputs**: DataFrame con atributos validados

**Outputs**: DataFrame con columnas:
- `Tipo`: "simple" o "variable"
- `SKU`: Código único del producto
- `SKU_Parent`: SKU del padre (si es variación)

#### Algoritmo de Agrupación

1. **Detección de Padre Potencial**
   - Busca palabras clave: kit, pack, surtido, set, etc.
   - O productos sin medidas (más probable ser padre)

2. **Extracción de Nombre Base**
   - Remueve fracciones al final
   - Remueve medidas entre paréntesis
   - Ejemplo: "ABRAZADERA TITAN MINI T10 1/4"" → "ABRAZADERA TITAN MINI T10"

3. **Agrupación por Nombre Base**
   - Si hay 2+ productos con mismo nombre base → grupo de variaciones
   - Selecciona padre: si hay "kit" → padre; si no → el sin medidas; si no → primero

4. **Generación de SKU**
   - **Padre**: `FAMILIA-MARCA-MODELO`
     - Ejemplo: `ABR-TITAN-MINI` (primeras 3-4 letras de palabras significativas)
   - **Variación**: `PADRE-ATRIBUTO`
     - Ejemplo: `ABR-TITAN-MINI-1-8` (para diámetro 1/8")

#### Estructura Generada

```
Abrazadera TITAN MINI T10  (PADRE, sin precio)
├─ Diámetro 1 1/8"        (variación 1, con precio)
├─ Diámetro 3/8"          (variación 2, con precio)
└─ Diámetro 1/2"          (variación 3, con precio)
```

#### Validación de Estructura

- ✓ SKU único por producto
- ⚠️ Variaciones sin padre → advertencia
- ⚠️ Padre con 1 sola variación → podría ser simple

#### Uso

```python
from src.grouping import group_products

df_grouped = group_products(df_validated)

# Ver estructura
simple_count = (df_grouped['Tipo'] == 'simple').sum()
variable_count = (df_grouped['Tipo'] == 'variable').sum()
variation_count = df_grouped['SKU_Parent'].notna().sum()

print(f"Simples: {simple_count}")
print(f"Padres variables: {variable_count - variation_count}")
print(f"Variaciones: {variation_count}")
```

---

### 3. review.py - Formato Maestro WooCommerce

**Responsabilidad**: Generar Excel exacto para revisión humana.

**Inputs**: DataFrame con productos agrupados

**Outputs**: Excel en `data/processed/maestro_revision_*.xlsx`

#### Columnas Generadas

**Básicas**:
- Tipo, SKU, SKU_Parent, Nombre, Slug
- Publicado (No), Visibilidad (Visible)

**Contenido**:
- Descripción (vacía, usuario completa)
- Descripción_Corta (por defecto = Nombre)
- Categoría (de familia detectada)
- Etiquetas (generadas de atributos)
- Marca (extraída automáticamente)

**Comerciales**:
- Precio (vacío, usuario ingresa)
- Precio_Oferta (opcional)
- Stock (vacío)
- Estado_Stock (En stock por defecto)
- Gestionar_Stock (Sí)
- Permitir_Reservas (No)

**Dimensiones**:
- Peso, Largo, Ancho, Alto (vacíos)

**Atributos** (3 principales):
- Atributo_N: Nombre (Diámetro, Largo, etc.)
- Valor_Atributo_N: Valor (1/4", 10cm, etc.)
- Visible_Atributo_N: Mostrar en ficha (Sí/No)
- Global_Atributo_N: Compartir en catálogo (Sí/No)
- Usado_Variacion_N: Define variación (Sí/No para variables)

**Auditoría**:
- Confianza_Automática: 0-100 (basada en limpieza + atributos + marca)
- Revisado_Humano: Sí/No (usuario marca después de revisar)
- Notas_Revisión: Cambios realizados por usuario

#### Cálculo de Confianza

Puntuación 0-100:

```
Nombre limpio:        30% máximo
  - Sin cambios: +30
  - Cambios mínimos (<30%): +20
  - Cambios importantes: +10

Atributos detectados: 20% máximo
  - +5 por atributo (máx 4 atributos = 20%)

Marca detectada:      20% máximo
  - Sí: +20
  - No: +0

Sin ambigüedad:       30% máximo
  - Familia clara: +15
  - Tiene medidas: +15
```

**Ejemplo**: ABRAZADERA TITAN MINI T10 1/4"
- Nombre: +25 (cambios mínimos)
- Atributos: +20 (3 detectados: diámetro, material, marca)
- Marca: +20 (TITAN detectado)
- Sin ambigüedad: +20 (familia abrazaderas, tiene medida)
- **Total: 85/100**

#### Estructura de Salida

Genera archivo Excel con 2 hojas:

1. **Maestro**: Datos completos en formato WooCommerce
2. **Instrucciones**: Guía para usuario

#### Uso

```python
from src.review import generate_master_format

df_maestro, output_file = generate_master_format(df_grouped)

print(f"Archivo generado: {output_file}")
print(f"Total registros: {len(df_maestro)}")
print(f"Confianza promedio: {df_maestro['Confianza_Automática'].mean():.0f}/100")
```

---

## 🔄 Flujo de Fase 2

```
┌─────────────────────────────────────────┐
│  DataFrame de Fase 1                    │
│  (nombres limpios + atributos extraídos)│
└──────────────┬──────────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ validate_attributes  │ (attributes.py)
    │                      │
    │ • Valida diámetros   │
    │ • Normaliza unidades │
    │ • Calcula confianza  │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  group_products      │ (grouping.py)
    │                      │
    │ • Agrupa variaciones │
    │ • Genera SKU         │
    │ • Define padre/hijo  │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ generate_master_fmt  │ (review.py)
    │                      │
    │ • Mapea a WooComm    │
    │ • Calcula confianza  │
    │ • Genera Excel       │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Excel Maestro       │
    │  data/processed/     │
    │                      │
    │  PARADA OBLIGATORIA  │
    │  (revisión humana)   │
    └──────────────────────┘
```

---

## 📊 Ejemplo Completo

### Entrada

```
Nombre: ABRAZADERA TITAN MINI CRBON T10 1.1/8 (22-36)
```

### Fase 1 (previo)
- ✓ Nombre limpiado: `ABRAZADERA TITAN MINI CARBON T10`
- ✓ Familia: `abrazaderas`
- ✓ Marca: `TITAN`
- ✓ Atributo_diametro: `1 1/8"`

### Fase 2: Validación
```
Atributo_diametro_validado:
  normalized: "1 1/8""
  is_valid: True
  confidence: 0.95
  notes: "Diámetro estándar validado"
```

### Fase 2: Agrupación
```
Tipo: variable
Nombre_Base: ABRAZADERA TITAN MINI T10
SKU: ABR-TITAN-MINI-T10
SKU_Parent: null (es el padre)
```

### Fase 2: Variaciones hermanas
```
1. SKU: ABR-TITAN-MINI-T10-1-8, SKU_Parent: ABR-TITAN-MINI-T10
2. SKU: ABR-TITAN-MINI-T10-3-8, SKU_Parent: ABR-TITAN-MINI-T10
3. SKU: ABR-TITAN-MINI-T10-1-2, SKU_Parent: ABR-TITAN-MINI-T10
```

### Fase 2: Formato Maestro
```
Tipo: variable
SKU: ABR-TITAN-MINI-T10
SKU_Parent: (vacío - es padre)
Nombre: ABRAZADERA TITAN MINI T10
Slug: abrazadera-titan-mini-t10
Precio: (vacío - padre no tiene precio)
Atributo_1: Diámetro
Valor_Atributo_1: (vacío - variaciones rellenan)
Usado_Variacion_1: Sí
Confianza_Automática: 85
Revisado_Humano: No
Notas_Revisión: (usuario rellena)
```

---

## ⚠️ Decisiones Críticas

### Productos Padre NO Tienen Precio
```
✓ CORRECTO:
  Padre (ABR-TITAN-MINI-T10):      Precio: (vacío)
  Variación 1/4":                   Precio: $10
  Variación 3/8":                   Precio: $12

✗ INCORRECTO:
  Padre (ABR-TITAN-MINI-T10):      Precio: $10 ← ¡ERROR!
```

Razón: WooCommerce suma precio del padre + variación. Los clientes deben elegir variación.

### SKU Inmutable
```
✓ El usuario NO debe cambiar SKU ni SKU_Parent
✗ Si detecta SKU incorrectos, reportar en Notas_Revisión

Razón: SKU es identificador único del sistema, cambiar crea duplicados
```

### Atributos Definen Variaciones
```
Usado_Variacion_1: Sí
  ↓
  Este atributo diferencia las variaciones del padre

El usuario marca "Sí" solo en atributos que varían
```

---

## 🐛 Errores Comunes y Mitigaciones

| Situación | Problema | Mitigation |
|-----------|----------|-----------|
| Diámetro no reconocido | Confianza baja | Usuario verifica/corrige en revisión |
| Nombre muy ambiguo | Agrupación incorrecta | Usuario separa en Notas_Revisión |
| Múltiples atributos variables | ¿Cuál es principal? | Usuario elige en Usado_Variacion_N |
| Padre sin variaciones | SKU sin sentido | Cambiar Tipo a "simple" en revisión |

---

## 🧪 Testing Fase 2

### Test: Validación de Diámetros

```python
from src.attributes import AttributeValidator

val = AttributeValidator()

test_cases = [
    ("1/4\"", True, 0.95),      # Estándar
    ("1/4", True, 0.9),          # Sin comilla
    ("6mm", True, 0.95),         # Métrico estándar
    ("6.5mm", True, 0.85),       # Métrico variante
    ("xyz", False, 0.2),         # Inválido
]

for value, expected_valid, expected_conf in test_cases:
    result = val._validate_diameter(value)
    assert result['is_valid'] == expected_valid
    assert abs(result['confidence'] - expected_conf) < 0.1
    print(f"✓ {value}")
```

### Test: Agrupación de Variaciones

```python
from src.grouping import ProductGrouper

grouper = ProductGrouper()

# Crear datos de prueba
df = pd.DataFrame({
    'Nombre_Limpio': [
        'ABRAZADERA TITAN MINI T10',
        'ABRAZADERA TITAN MINI T10 1/4',
        'ABRAZADERA TITAN MINI T10 3/8',
    ]
})

df_grouped = grouper.group_products(df)

# Validar
assert df_grouped.loc[0, 'Tipo'] == 'variable'
assert df_grouped.loc[0, 'SKU'] == df_grouped.loc[1, 'SKU_Parent']
print("✓ Agrupación correcta")
```

---

## 📞 Soporte

- Cada validador tiene logging detallado
- Revisa `logs/pipeline_*.log` para debugging
- Usa `--loglevel DEBUG` para más detalle

```bash
python main.py --loglevel DEBUG
```
