# 🚀 START HERE - COMIENZA AQUÍ

Bienvenido a **Catalogo Transformer v0.2.0**.

Este archivo te guiará en los primeros 5 minutos.

---

## ¿Qué es esto?

Un sistema que transforma catálogos Excel desorganizados en datos estructurados listos para WooCommerce.

```
Input:   Excel plano con 5.000 productos
         └─ "ABRAZADERA TITAN 1/4""

Output:  Excel maestro con datos estructurados
         └─ SKU: ABR-TITAN-MINI-T10-1-4
         └─ Atributos validados
         └─ Pronto: Importable en WooCommerce
```

---

## ⚡ 5 Pasos Rápidos

### Paso 1: Verificar Python (1 min)
```bash
python --version
```
Debe ser **3.7 o superior**. Si no aparece nada, [instala Python](https://www.python.org/downloads/).

### Paso 2: Instalar (3 minutos)
```bash
pip install -r requirements.txt
```

### Paso 3: Datos de Prueba (1 minuto)
```bash
python create_example.py
```
Crea `productos_ejemplo.xlsx` para probar sin tus datos reales.

### Paso 4: Ejecutar (30 segundos)
```bash
python main.py
```
Verás progreso en pantalla.

### Paso 5: Revisar (15-30 minutos)
Abre el archivo generado: `data/processed/maestro_revision_*.xlsx`

Sigue las instrucciones en la Hoja 2.

---

## 🎯 Próximo Paso Según Tu Situación

### 👤 "Soy usuario final, quiero empezar AHORA"
→ Ir a: [INICIO_RAPIDO.md](INICIO_RAPIDO.md) (5 minutos)

### 💻 "Soy desarrollador, quiero entender el código"
→ Ir a: [README.md](README.md) (10 minutos)

### 🏗️ "Soy arquitecto/PM, quiero overview"
→ Ir a: [FINAL_SUMMARY.md](FINAL_SUMMARY.md) (10 minutos)

### 🔧 "Tengo problemas instalando"
→ Ir a: [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md#-troubleshooting) (5 minutos)

### 📚 "Quiero saber TODO"
→ Ir a: [INDEX.md](INDEX.md) (15 minutos)

---

## 📁 Carpetas Importantes

```
catalogo/
├── data/raw/           ← TU EXCEL VA AQUÍ (o usa ejemplo)
├── data/processed/     ← RESULTADO AQUÍ (abrir en Excel)
├── src/                ← Código Python (no tocar)
└── config/             ← Configuración (rules.yaml - PERSONALIZAR)
```

---

## ✅ Checklist de Validación

Para verificar que está todo OK:

```bash
# 1. Python instalado
python --version
# Debe ser 3.7+

# 2. Dependencias instaladas
python -c "import pandas, openpyxl, yaml; print('OK')"
# Debe salir: OK

# 3. Tests pasan
python test_pipeline.py
# Debe salir: 6 passed

# 4. Ejemplo funciona
python create_example.py
python main.py
# Debe completar sin errores
```

Si todo dice "OK", ¡estás listo para usar tus datos!

---

## 🎬 Flujo Típico (15 minutos)

```
1. Instalar (3 min)
   └─ pip install -r requirements.txt

2. Preparar Excel (2 min)
   └─ Copiar a: data/raw/productos.xlsx
   └─ O: python create_example.py

3. Ejecutar (1 min)
   └─ python main.py

4. Revisar en Excel (9 min)
   └─ Abrir data/processed/maestro_revision_*.xlsx
   └─ Verificar productos
   └─ Marcar Revisado_Humano = "Sí"
   └─ Guardar

5. Siguiente paso (próximo)
   └─ Fase 3: Exportar a WooCommerce (en desarrollo)
```

---

## 🎓 3 Conceptos Clave

### 1️⃣ SKU (Identificador)
```
Único por producto. Generado automáticamente.

PADRE (si tiene variaciones):
  ABR-TITAN-MINI-T10
  
VARIACIÓN:
  ABR-TITAN-MINI-T10-1-4  (1/4")
  ABR-TITAN-MINI-T10-3-8  (3/8")
```

### 2️⃣ Confianza (0-100)
```
Qué tan seguro está el sistema sobre los datos.

85 = Muy bien
75 = Está OK
50 = Revisar
```

### 3️⃣ Revisado_Humano
```
OBLIGATORIO antes de exportar.

Tú marcas "Sí" = Aprobado
Tú marcas "No" = Rechazado
Tú marcas "Revisar" = Pendiente

El sistema NUNCA exporta sin "Sí"
```

---

## ⚠️ Reglas Importantes

```
1. NUNCA se modifica el Excel original
   └─ Siempre hay backup automático

2. Revisión humana es OBLIGATORIA
   └─ El sistema requiere tu aprobación

3. Configuración en YAML
   └─ Personalizar sin tocar código Python

4. Logs detallados
   └─ Ver en: logs/ para debugging
```

---

## 🔧 Primeras Personalizaciones

### 1. Cambiar Familia de Productos
Editar: `config/rules.yaml`
```yaml
families:
  - tu_nueva_familia  # Agregar aquí
```

### 2. Agregar Diámetro Válido
Editar: `config/rules.yaml`
```yaml
ranges:
  valid_diameters:
    - 3/4"  # Agregar aquí
```

### 3. Cambiar Peso de Confianza
Editar: `config/rules.yaml`
```yaml
confidence:
  name_clean: 35%     # Cambiar de 30% a 35%
```

Luego ejecutar:
```bash
python main.py
```

---

## 📱 Atajos Útiles

```
Ver documentación general:
  → README.md

Primeros pasos:
  → INICIO_RAPIDO.md

Toda la documentación:
  → INDEX.md

Futuro del proyecto:
  → ROADMAP.md

Qué cambió:
  → CHANGELOG.md

Detalles técnicos:
  → FASE2.md

Estado actual:
  → STATUS.txt
```

---

## ❓ Preguntas Frecuentes

### P: ¿Cuánto tarda procesar 5.000 productos?
**R**: ~60-90 segundos. El sistema es rápido.

### P: ¿Se modifican mis datos originales?
**R**: NO. Nunca. Archivo original en data/raw/ nunca cambia.

### P: ¿Puedo personalizar las reglas?
**R**: SÍ. Todo en config/rules.yaml. Sin código Python necesario.

### P: ¿Qué es Confianza?
**R**: Puntuación 0-100 de qué tan bien el sistema cree que tiene los datos. TÚ revisas y apruebas.

### P: ¿Puedo agregar mis propios atributos?
**R**: SÍ. Editar config/rules.yaml en sección `attributes`.

### P: ¿Funciona en Windows/Mac/Linux?
**R**: SÍ. Python funciona en todos.

### P: ¿Qué sucede después?
**R**: Fase 3 (Exportar a WooCommerce) en Q1 2026.

---

## 🆘 Ayuda Rápida

| Problema | Solución |
|----------|----------|
| "python: command not found" | Instala Python desde https://www.python.org/ |
| "ModuleNotFoundError" | Ejecuta: `pip install -r requirements.txt` |
| "Archivo no encontrado" | Copia Excel a: `data/raw/productos.xlsx` |
| "Tests fallan" | Ver [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md#-troubleshooting) |
| "Confianza muy baja" | Revisar config/rules.yaml, maybe ajustar pesos |

Más help: [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

---

## 📊 Estado Actual

```
Versión:      0.2.0
Fase Actual:  2 (Validación ✅)
Completitud:  66% (2 de 3 fases)

Próximo:      Fase 3 - Exportar a WooCommerce
Lanzamiento:  Q1 2026
```

---

## 🚀 Comienza Ahora

### Opción A: 5 minutos (prueba rápida)
```bash
python create_example.py
python main.py
# Abre: data/processed/maestro_revision_*.xlsx
```

### Opción B: 15 minutos (tus datos)
```bash
# 1. Copiar Excel a: data/raw/productos.xlsx
# 2. Ejecutar:
python main.py
# 3. Revisar Excel generado
```

### Opción C: Aprender primero (20 minutos)
```bash
# Leer documentación:
# 1. README.md (¿Qué es?)
# 2. INICIO_RAPIDO.md (¿Cómo usar?)
# 3. FASE2.md (¿Cómo funciona?)
```

---

## 📌 Recuerda

✅ El archivo original NUNCA se modifica  
✅ Siempre hay copia de seguridad  
✅ Revisión humana es OBLIGATORIA  
✅ Configuración en YAML (fácil de cambiar)  
✅ Determinista (mismo input = mismo output)  

---

## 🎯 Siguiente Paso

**Elige uno:**

1. **Quiero empezar AHORA** → [INICIO_RAPIDO.md](INICIO_RAPIDO.md)
2. **Quiero entender primero** → [README.md](README.md)
3. **Tengo problemas** → [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
4. **Quiero ver documentación** → [INDEX.md](INDEX.md)

---

## 💬 Final

¡Bienvenido a Catalogo Transformer!

Transforma tu catálogo en minutos.  
Revisa antes de exportar.  
Exporta a WooCommerce cuando esté listo.

**¡Vamos!** 🚀

---

*v0.2.0 • 27 de Enero, 2026*
