# 🛠️ GUÍA DE INSTALACIÓN

## Requisitos Previos

- **Windows 10+**, **macOS 10.14+**, o **Linux** (Ubuntu 18.04+)
- **Python 3.7+** instalado ([descargar aquí](https://www.python.org/downloads/))
- **Excel** (cualquier versión moderna) o compatible (LibreOffice Calc, etc.)

---

## Paso 1: Verificar Python

Abre **PowerShell** (Windows) o **Terminal** (Mac/Linux) y verifica:

```bash
python --version
```

Deberías ver: `Python 3.7.x` o superior.

Si no aparece nada, [instala Python](https://www.python.org/downloads/).

---

## Paso 2: Descargar el Proyecto

### Opción A: Git
```bash
git clone <url-del-repositorio> catalogo
cd catalogo
```

### Opción B: Descargar ZIP
1. Descarga el proyecto como ZIP
2. Descomprime en `C:\Users\[Tu-Usuario]\source\repos\Catalogo`
3. Abre PowerShell
4. Navega: `cd C:\Users\[Tu-Usuario]\source\repos\Catalogo`

---

## Paso 3: Crear Entorno Virtual (Recomendado)

### Windows
```bash
python -m venv venv
.\venv\Scripts\activate
```

### Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

Deberías ver `(venv)` al inicio de tu línea de comandos.

---

## Paso 4: Instalar Dependencias

```bash
pip install -r requirements.txt
```

Espera a que termine (2-3 minutos).

---

## Paso 5: Preparar Datos

### A. Generar Ejemplo (Prueba)

```bash
python create_example.py
```

Esto crea `productos_ejemplo.xlsx` con datos de demostración.

### B. Usar Tus Datos Reales

1. Coloca tu Excel en: `data/raw/`
2. Renómbralo a: `productos.xlsx`
3. Asegúrate que tenga estas columnas:
   - `Nombre_Producto` (o similar)
   - `Descripción` (opcional)
   - `Precio` (opcional)
   - `Stock` (opcional)

---

## Paso 6: Ejecutar el Pipeline

```bash
python main.py
```

### Esperado:
```
═══════════════════════════════════════════════════════════════
              CATALOGO TRANSFORMER v0.2.0
                     FASE 2: VALIDATION
═══════════════════════════════════════════════════════════════

[FASE 0] VALIDACIÓN DEL ENTORNO ✓
  ✓ Python 3.x
  ✓ Librerías: pandas, openpyxl, pyyaml
  ✓ Directorio data/raw/ existe
  ✓ Archivo productos.xlsx encontrado

[FASE 1] CARGA DE DATOS ✓
  Registros leídos: 150
  Checksums generados
  Copia de seguridad: data/raw/backup.xlsx

[FASE 2] LIMPIEZA DE NOMBRES ✓
  Normalizados: 150/150
  Familias detectadas: 6
  Marcas extraídas: 12

[FASE 3] EXTRACCIÓN DE ATRIBUTOS ✓
  Diámetros extraídos: 45
  Largos extraídos: 38
  Grosores extraídos: 15
  Materiales detectados: 8

[FASE 4] VALIDACIÓN DE ATRIBUTOS ✓
  Confianza promedio: 82.5%

[FASE 5] AGRUPACIÓN DE PRODUCTOS ✓
  Productos simples: 120
  Productos variables: 30
  Total SKUs generados: 180

[FASE 6] GENERACIÓN DE FORMATO MAESTRO ✓
  Archivo guardado: data/processed/maestro_revision_YYYYMMDD_HHMMSS.xlsx
  Listo para revisar en Excel ✓

═══════════════════════════════════════════════════════════════
                      ✓ PIPELINE EXITOSO
═══════════════════════════════════════════════════════════════

Abre: data/processed/maestro_revision_*.xlsx en Excel
```

---

## Paso 7: Revisar en Excel

1. Abre el archivo generado:
   - `data/processed/maestro_revision_YYYYMMDD_HHMMSS.xlsx`

2. Verás 2 hojas:
   - **Maestro**: Los 150 productos transformados
   - **Instrucciones**: Guía de qué significa cada columna

3. Para cada producto, revisa:
   - ✅ Nombre correcto
   - ✅ SKU único
   - ✅ Atributos válidos
   - ✅ Confianza >= 75%

4. **Muy importante**: Marca la columna `Revisado_Humano`:
   - Escribe **"Sí"** si todo está correcto
   - Escribe **"No"** si hay errores
   - Escribe **"Revisar"** si necesita ajustes

5. **Guarda el archivo** con tus cambios

---

## Paso 8: Siguiente Fase (Próximamente)

Una vez hayas revisado todos los productos:

```bash
python exporter.py
```

Esto exportará a WooCommerce CSV (cuando esté disponible en Fase 3).

---

## 🧪 Testear Sin Datos Reales

Para probar sin usar tu catálogo real:

```bash
# Generar datos de ejemplo
python create_example.py

# Ejecutar pipeline con ejemplo
python main.py
```

---

## ❌ Troubleshooting

### Error: "python: command not found"
**Solución**: Python no está instalado o no en PATH.
- [Descargar Python](https://www.python.org/downloads/)
- Reinstala marcando **"Add Python to PATH"**

### Error: "ModuleNotFoundError: No module named 'pandas'"
**Solución**: Las dependencias no se instalaron.
```bash
pip install -r requirements.txt
```

### Error: "products.xlsx not found"
**Solución**: El archivo no está en la ruta correcta.
```
✓ Debe estar en: catalogo/data/raw/productos.xlsx
✓ O genera ejemplo: python create_example.py
```

### Error: "columns do not match"
**Solución**: Tu Excel no tiene las columnas esperadas.
- Verifica el archivo tenga columnas básicas (nombre, etc.)
- Ver [README.md](README.md) para formato esperado

### Archivo gigante demora mucho
**Normal si >10.000 registros**. El procesamiento es:
- 150 registros: ~2-3 segundos
- 1.000 registros: ~15-20 segundos
- 5.000 registros: ~60-90 segundos

---

## ✅ Verificar Instalación

Corre este test rápido:

```bash
python -m pytest test_pipeline.py -v
```

Deberías ver:
```
test_cleaner PASSED
test_patterns PASSED
test_attributes PASSED
test_grouping PASSED
test_review PASSED
test_integration PASSED

====== 6 passed in 2.34s ======
```

---

## 📁 Estructura Esperada Después de Instalar

```
catalogo/
├── src/
│   ├── loader.py
│   ├── cleaner.py
│   ├── patterns.py
│   ├── attributes.py
│   ├── grouping.py
│   ├── review.py
│   └── __init__.py
│
├── config/
│   └── rules.yaml
│
├── data/
│   ├── raw/
│   │   └── productos.xlsx
│   ├── processed/
│   │   └── (archivos generados)
│   └── reviewed/
│       └── (próxima fase)
│
├── logs/
│   └── (generado automáticamente)
│
├── venv/
│   └── (tu entorno virtual)
│
├── main.py
├── create_example.py
├── test_pipeline.py
├── requirements.txt
├── README.md
├── INSTALLATION_GUIDE.md  ← Estás aquí
└── (documentación adicional)
```

---

## 🚀 Próximos Pasos

1. ✅ Instalar (este documento)
2. ✅ Ejecutar pipeline
3. ⬜ Revisar en Excel
4. ⬜ Aprobar cambios
5. ⬜ Exportar a WooCommerce (Fase 3)

---

## 📞 ¿Necesitas Ayuda?

- **Errores de instalación**: Ver sección Troubleshooting arriba
- **Preguntas sobre datos**: Ver [README.md](README.md)
- **Detalle técnico**: Ver [FASE2.md](FASE2.md)
- **Quick start**: Ver [INICIO_RAPIDO.md](INICIO_RAPIDO.md)

---

## 💡 Tips Importantes

### Entorno Virtual
```bash
# Para activar cada vez que uses el proyecto
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Para desactivar
deactivate
```

### Mantener Datos Seguros
```
✓ Original NUNCA se modifica (data/raw/)
✓ Siempre hay backup automático
✓ data/processed/ es temporal
✓ data/reviewed/ es tu salida final
```

### Reglas Personalizadas
Si necesitas cambiar cómo se validan atributos, edita:
```
config/rules.yaml
```

No necesitas tocar Python. Las reglas están en YAML.

---

## 🎉 ¡Listo!

Si llegaste hasta acá sin errores, ¡tu instalación está **100% lista**!

**Próximo paso**: Abre [INICIO_RAPIDO.md](INICIO_RAPIDO.md) para correr tu primer pipeline.

---

*Última actualización: 27 de Enero, 2026*
*Versión: 0.2.0*
