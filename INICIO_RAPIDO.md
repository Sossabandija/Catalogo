# 🚀 INICIO RÁPIDO - FASE 1 + FASE 2

## ⚡ 1 minuto de setup

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear datos de ejemplo (opcional)
python create_example.py

# Ejecutar pipeline
python main.py

# Revisar productos (interfaz gráfica)
python revisor_gui.py

# O revisar en consola
python revisor.py
```

---

## 📋 Flujo Paso a Paso

### Opción A: Con datos de ejemplo

```bash
# 1. Crear archivo de ejemplo
python create_example.py

# 2. Ejecutar pipeline
python main.py
# Selecciona opción 1 cuando se pida

# 3. Revisar formato maestro
# Abre: data/processed/maestro_revision_*.xlsx
```

### Opción B: Con tu propio Excel

```bash
# 1. Coloca tu Excel en:
data/raw/tu_archivo.xlsx

# 2. Ejecutar pipeline
python main.py --input data/raw/tu_archivo.xlsx

# 3. Revisar con herramienta interactiva
python revisor.py

# 4. O revisar en Excel
# Abre: data/processed/maestro_revision_*.xlsx
```

---

## 🔍 Herramienta de Revisión Interactiva

### Opción 1: Interfaz Gráfica (GUI) - Recomendada

```bash
# Abre la interfaz gráfica
python revisor_gui.py

# O especifica un archivo
python revisor_gui.py data/processed/maestro_revision_*.xlsx
```

**Características de la GUI:**
- 📋 Lista de productos con filtros y búsqueda
- ✏️ Edición visual de todos los campos
- 🏷️ Panel de atributos (agregar, editar, eliminar)
- 👨‍👧‍👦 Gestión de grupos y variaciones
- 💾 Guardado automático y exportación a WooCommerce

### Opción 2: Consola Interactiva

```bash
# Abre el revisor en consola
python revisor.py

# O especifica un archivo
python revisor.py data/processed/maestro_revision_20260129_131737.xlsx
```

### Funcionalidades

1. **Ver grupos (padre + variaciones)**
   - Lista todos los grupos creados
   - Muestra atributos del padre
   - Permite agregar/quitar variaciones

2. **Ver productos simples**
   - Detecta posibles familias
   - Permite crear nuevos grupos
   - Unir productos a grupos existentes

3. **Revisar productos pendientes**
   - Navega uno por uno
   - Aprobar (✓) o rechazar
   - Editar campos rápidamente

4. **Buscar producto**
   - Por SKU o nombre
   - Acceso directo a edición

---

## 📊 Qué Esperar

### Output del Pipeline

```
╔════════════════════════════════════════╗
║  FASE 1: CARGANDO DATOS ORIGINALES     ║
╚════════════════════════════════════════╝

✓ Cargados 5 registros
✓ Columnas: Nombre
✓ Checksum: abc123...

╔════════════════════════════════════════╗
║  FASE 2: NORMALIZANDO NOMBRES          ║
╚════════════════════════════════════════╝

✓ Limpieza completada
  • Nombres únicos detectados: 4
  • Familias detectadas: 2

[... más fases ...]

╔════════════════════════════════════════╗
║  PARADA OBLIGATORIA - REVISIÓN HUMANA  ║
╚════════════════════════════════════════╝

📁 Archivo maestro: data/processed/maestro_revision_20250127_120000.xlsx

Abre y revisa en Excel. Cuando termines, ejecuta:
python main.py --export data/processed/maestro_revision_20250127_120000.xlsx
```

---

## 📝 Cómo Revisar en Excel

### El Archivo Maestro

Archivo: `data/processed/maestro_revision_*.xlsx`

**Hoja 1: Maestro**
- Todas tus columnas WooCommerce
- Datos cargados y procesados automáticamente

**Hoja 2: Instrucciones**
- Guía completa de qué hacer

### Pasos de Revisión

1. **Abre el archivo maestro en Excel**

2. **Revisa cada fila:**
   ```
   ✓ Nombre: ¿Correcto?
   ✓ Categoría: ¿Familia asignada correcta?
   ✓ Marca: ¿Detectada correctamente?
   ✓ Atributos: ¿Valores extraídos bien?
   ✓ SKU: ¿Estructura padre/hijo correcta?
   ✓ Precio: ¿Necesita ser completado?
   ```

3. **Columna "Revisado_Humano":**
   - Escribe `Sí` si apruebas la fila
   - Escribe `No` si rechazas o necesita correcciones

4. **Columna "Notas_Revisión":**
   - Escribe qué cambiaste o por qué rechazaste
   - Ejemplo: "Corregida marca de TITAN a HEXAGON"

5. **Completa campos vacíos si es necesario:**
   - Precios
   - Descripciones (si falta)
   - Stock

6. **Guarda el archivo (Ctrl+S)**

---

## 🎯 Ejemplo Real

### Fila Original (Excel input)
```
Nombre: ABRAZADERA TITAN MINI CRBON T10 1.1/8 (22-36)
```

### Fila en Maestro (después del pipeline)
```
Tipo:                     variable
SKU:                      ABR-TITAN-MINI-T10-1-8
SKU_Parent:               ABR-TITAN-MINI-T10
Nombre:                   ABRAZADERA TITAN MINI CARBON T10 1 1/8"
Slug:                     abrazadera-titan-mini-t10-1-1-8
Publicado:                No
Categoría:                abrazaderas
Marca:                    TITAN
Atributo_1:               Diámetro
Valor_Atributo_1:         1 1/8"
Confianza_Automática:     92
Revisado_Humano:          No          ← TÚ COMPLETAS ESTO
Notas_Revisión:           (vacío)     ← Y ESTO SI ES NECESARIO
```

### Después de Revisar
```
Revisado_Humano:          Sí
Notas_Revisión:           SKU correcto, diámetro validado, listo para venta
```

---

## 🔄 Próximos Pasos (Fase 3)

Cuando termines la revisión y guardes:

```bash
# Exportar a WooCommerce (próximamente)
python main.py --export data/processed/maestro_revision_20250127_120000.xlsx

# Esto generará:
# - CSV con formato WooCommerce
# - Solo filas con Revisado_Humano = "Sí"
# - Importable directamente a WooCommerce
```

---

## 🆘 Troubleshooting

### Error: "Archivo no encontrado"
```bash
# Asegúrate de:
# 1. El archivo está en data/raw/
# 2. Es .xlsx o .xls
# 3. Especifica la ruta completa

python main.py --input data/raw/productos.xlsx
```

### Error: "Módulo no encontrado"
```bash
# Instalar dependencias
pip install pandas openpyxl pyyaml
```

### El maestro tiene pocos datos
```bash
# Esto es normal si:
# - El Excel original es muy básico (solo tiene Nombre)
# - El pipeline intenta extraer del nombre todo lo posible
# 
# Solución: Agrega más columnas (SKU, Marca, Descripción, etc.)
```

### ¿Cómo cambio las reglas?
```bash
# Edita: config/rules.yaml

# Ejemplo: Agregar nueva familia
families:
  mi_familia_nueva:
    keywords: ['palabra1', 'palabra2']
    category: 'Mi Categoría'
```

---

## 📚 Documentación Completa

- [README.md](README.md) - Arquitectura general
- [FASE2.md](FASE2.md) - Detalles técnicos de Phase 2
- [config/rules.yaml](config/rules.yaml) - Reglas deterministas

---

## ✅ Checklist Final

Antes de ejecutar en producción:

- [ ] Instalaste dependencias: `pip install -r requirements.txt`
- [ ] Pusiste datos en: `data/raw/*.xlsx`
- [ ] Ejecutaste: `python main.py`
- [ ] Revisa el archivo maestro en Excel
- [ ] Marcaste "Revisado_Humano: Sí" para las filas que apruebes
- [ ] Agregaste notas en "Notas_Revisión" si cambiaste datos
- [ ] Guardaste el archivo (Ctrl+S)

---

## 🎓 Para Aprender Más

### Testing
```bash
python test_pipeline.py
```

Ejecuta tests unitarios de todos los módulos.

### Logging Detallado
```bash
# Ver todos los detalles del procesamiento
tail -f logs/pipeline_*.log
```

### Python Interactivo
```python
from src.loader import load_products_excel
from src.cleaner import clean_products

df, metadata = load_products_excel('data/raw/ejemplo_productos.xlsx')
df = clean_products(df)

print(f"Total: {len(df)}")
print(f"Familias: {df['Familia_Detectada'].unique()}")
```

---

## 💡 Tips y Mejores Prácticas

### Tip 1: Revisar por Categoría
```
Filtra el maestro por Categoría en Excel
Esto te permite revisar productos similares juntos
```

### Tip 2: Usar Buscar & Reemplazar
```
Ctrl+H en Excel
Para cambios en lote (ej: "CARBON" → "CARBÓN")
```

### Tip 3: Copiar Datos Entre Filas
```
Si tienes productos muy similares:
1. Aprueba el primero (Revisado_Humano: Sí)
2. Copia la fila
3. Pega en otros similares (Excel lo mantiene)
```

### Tip 4: Validar Antes de Guardar
```
Excel > Datos > Validar
Para evitar typos en columnas críticas (SKU, Precio, etc.)
```

---

## 📞 Soporte

Si algo falla:

1. Revisa los logs:
   ```bash
   tail logs/pipeline_*.log
   ```

2. Ejecuta los tests:
   ```bash
   python test_pipeline.py
   ```

3. Verifica que el Excel de entrada sea válido:
   - Mínimo columna "Nombre"
   - Formato .xlsx o .xls
   - Sin caracteres especiales en nombres de columnas

---

## 🎉 ¡Listo!

Ejecuta:
```bash
python main.py
```

Y sigue las instrucciones en pantalla.

**¡Que disfrutes transformando tu catálogo!** 🚀
