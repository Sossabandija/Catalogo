# 🗺️ ROADMAP - FUTURO DEL PROYECTO

## 📌 Versión Actual: 0.2.0 (Fase 2)

```
Versión 0.1.0 (Fase 1) ✅ COMPLETADA
  ├─ loader.py       (cargar Excel)
  ├─ cleaner.py      (limpiar nombres)
  ├─ patterns.py     (extraer atributos)
  └─ main.py         (orquestador)

Versión 0.2.0 (Fase 2) ✅ COMPLETADA (ACTUAL)
  ├─ attributes.py   (validar)
  ├─ grouping.py     (agrupar)
  ├─ review.py       (maestro)
  ├─ config/rules.yaml (120 líneas → 150 líneas)
  ├─ Documentación   (9 archivos)
  └─ Tests           (6 suites)

Versión 0.3.0 (Fase 3) ⏳ PRÓXIMO
  ├─ exporter.py     (exportar CSV)
  ├─ woocommerce_import.py (opcional)
  ├─ api_connector.py (opcional)
  └─ Documentación   (2 archivos nuevos)
```

---

## 🎯 Fase 3: Exportación a WooCommerce (v0.3.0)

### 📅 Timeline Estimado
```
Fase 3a (Core):        1-2 semanas
  ├─ exporter.py      ← Archivo principal
  ├─ Validación pre-export
  └─ CSV generation

Fase 3b (Avanzado):    2-3 semanas
  ├─ API connector
  ├─ WooCommerce upload
  └─ Error recovery

Fase 3c (Polish):      1 semana
  ├─ Tests
  ├─ Documentación
  └─ Performance tune
```

### 🎁 Qué se Implementará

#### A. exporter.py (CRÍTICO)
```python
class CSVExporter:
    ├─ _validate_before_export()
    │   ├─ Verificar Revisado_Humano = "Sí"
    │   ├─ Validar SKUs únicos
    │   ├─ Validar columnas obligatorias
    │   └─ Resumen de errors
    │
    ├─ _filter_approved_products()
    │   └─ Solo Revisado_Humano = "Sí"
    │
    ├─ _format_for_woocommerce()
    │   ├─ Mapear 43 columnas → CSV WooCommerce
    │   ├─ Convertir tipos de datos
    │   ├─ Generar product IDs
    │   └─ Procesar imágenes (si aplica)
    │
    ├─ _generate_csv()
    │   ├─ Crear CSV UTF-8
    │   ├─ Validar encoding
    │   └─ Generar headers
    │
    └─ _generate_import_report()
        ├─ Resumen de productos exportados
        ├─ Warnings/errors encontrados
        ├─ Preview de primeras filas
        └─ Instrucciones de importación

# Entrada: maestro_revision_*.xlsx (con Revisado_Humano="Sí")
# Salida: woocommerce_import_*.csv
```

#### B. api_connector.py (OPCIONAL)
```python
class WooCommerceAPI:
    ├─ __init__(store_url, api_key, api_secret)
    │
    ├─ connect()              # Probar conexión
    ├─ get_categories()       # Descargar categorías
    ├─ get_attributes()       # Descargar atributos
    ├─ upload_products()      # Importar productos
    ├─ update_products()      # Actualizar existentes
    ├─ get_import_status()    # Estado de importación
    └─ rollback_last_import() # Deshacer última importación
```

#### C. Validaciones Pre-Export
```
✓ Revisado_Humano DEBE ser "Sí" para cada producto
✓ SKU DEBE ser único
✓ Nombre DEBE tener 3+ caracteres
✓ Precio DEBE ser positivo (si aplica)
✓ Stock DEBE ser >= 0
✓ Diámetro/Largo/Grosor DEBE estar en rango válido
✓ Marca DEBE estar en catálogo válido
✓ Categoría DEBE existir
```

### 📊 Mapeo de Columnas Excel → WooCommerce CSV

```
Excel Maestro (43 cols)          WooCommerce CSV
══════════════════════════════════════════════════════
Tipo                      →      Type (simple/variable)
SKU                       →      SKU
SKU_Parent (si variable)  →      Parent
Nombre                    →      Name
Slug                      →      Slug
Publicado                 →      Published
Visibilidad               →      Visibility
Descripción               →      Description
Descripción_Corta         →      Short Description
Categoría                 →      Categories
Etiquetas                 →      Tags
Marca                     →      Brand (atributo custom)
Precio                    →      Regular Price
Precio_Oferta             →      Sale Price
Stock                     →      Stock Quantity
Estado_Stock              →      Stock Status
Imágenes                  →      Images
Atributo_1_*              →      pa_atributo_1
Atributo_2_*              →      pa_atributo_2
Atributo_3_*              →      pa_atributo_3
Confianza_Automática      →      (no exportar)
Revisado_Humano           →      (filtro, no exportar)
Notas_Revisión            →      (no exportar)
```

### 🧪 Tests Fase 3

```python
def test_exporter():
    ✓ test_validate_approved_only()
    ✓ test_sku_uniqueness()
    ✓ test_csv_generation()
    ✓ test_column_mapping()
    ✓ test_data_types()
    ✓ test_special_characters()
    ✓ test_large_catalogs()
    ✓ test_error_reporting()

def test_api_connector():
    ✓ test_connection()
    ✓ test_get_categories()
    ✓ test_upload_single()
    ✓ test_upload_batch()
    ✓ test_update_existing()
    ✓ test_error_recovery()
    ✓ test_rollback()
```

### 📝 Documentación Fase 3

```
FASE3.md                     (450 líneas)
  ├─ Arquitectura exporter
  ├─ CSV format specifications
  ├─ API connector guide
  ├─ Error handling
  ├─ Performance tips
  └─ Troubleshooting

FASE3_API_GUIDE.md          (300 líneas)
  ├─ WooCommerce REST API
  ├─ Authentication
  ├─ Bulk operations
  ├─ Rate limiting
  └─ Examples

EXPORTER_USAGE.md            (200 líneas)
  ├─ Quick start
  ├─ CSV import manual
  ├─ API upload manual
  └─ Error codes
```

---

## 🎁 Fase 4: Características Avanzadas (v0.4.0)

### 🚀 Características Propuestas

#### A. Sincronización Automática
```python
class WooCommerceSyncManager:
    ├─ sync_from_woocommerce()   # Descargar cambios
    ├─ sync_to_woocommerce()     # Subir cambios
    ├─ detect_conflicts()        # Conflictos de edición
    ├─ merge_changes()           # Fusionar cambios
    └─ audit_trail()             # Registro de sincronizaciones
```

#### B. Machine Learning (OPCIONAL)
```
⚠️ FUTURE: Opción de activar ML para:
  • Detección automática de categorías
  • Sugerencia de atributos faltantes
  • Predicción de precios
  
NOTA: Requerirá opt-in explícito
      No será determinista
      Solo para sugerencias, humano decide
```

#### C. Importaciones desde APIs
```
Integración con APIs:
  ├─ Proveedores (cambios de precios, stock)
  ├─ Competidores (análisis de precios)
  ├─ Marketplaces (listados cruzados)
  └─ Logística (actualizaciones de stock)
```

#### D. Reportes Avanzados
```
Reportes generados:
  ├─ Dashboard de transformación
  ├─ Análisis de confianza
  ├─ Historial de cambios
  ├─ Métricas de performance
  └─ Auditoría completa
```

#### E. UI Web (FUTURO LEJANO)
```
Interface web (Fase 5+):
  ├─ Dashboard visual
  ├─ Editor de productos
  ├─ Revisión interactiva
  ├─ Upload de archivos
  └─ Reportes en vivo
```

### 📅 Timeline Estimado

```
v0.3.0 (Fase 3):  Q1 2026    ← Current target
v0.4.0 (Fase 4):  Q2 2026
v0.5.0 (UI):      Q3-Q4 2026
v1.0.0 (Release): Q4 2026
```

---

## 📈 Roadmap Visual

```
TIMELINE
═════════════════════════════════════════════════════════════════

2025
│
├─ v0.1.0 ✅
│  │ Phase 1: Load, Clean, Extract
│  └─ Deployment: December 2025
│
├─ v0.2.0 ✅ (ACTUAL: Enero 2026)
│  │ Phase 2: Validate, Group, Review
│  │ Tests, Documentación
│  └─ Deployment: January 2026
│
├─ v0.3.0 ⏳ (Fase 3)
│  │ Phase 3: Export to WooCommerce
│  │ CSV generator, API connector
│  └─ Target: Q1 2026 (2-3 meses)
│
├─ v0.4.0 🔮 (Fase 4)
│  │ Advanced features
│  │ Auto-sync, Analytics
│  └─ Target: Q2-Q3 2026
│
└─ v1.0.0 🎯 (General Release)
   │ Complete product
   │ UI Web (opcional)
   └─ Target: Q4 2026

2026-2027: Mantenimiento y soporte
```

---

## 🎯 Prioridades & Dependencias

### 🔴 CRÍTICO (Bloqueador)
```
[ ] Fase 3a: exporter.py
    └─ Dependencia: Fase 2 completa ✅
    └─ Bloqueador para: v0.3.0 release
```

### 🟡 IMPORTANTE (Muy útil)
```
[ ] Fase 3b: API connector
    └─ Dependencia: exporter.py completo
    └─ Nice-to-have: Automatizar uploads
```

### 🟢 NICE-TO-HAVE (Mejoras)
```
[ ] Fase 4: Advanced features
[ ] Fase 5: UI Web
[ ] Analytics dashboard
```

---

## 💡 Decisiones de Diseño

### ✅ Ya Decidido

1. **Determinista vs ML**
   - Decisión: Mantener determinista hasta v0.3.0
   - Razón: Confiabilidad, auditabilidad
   - ML: Opcional en Fase 4+

2. **Revisión Humana**
   - Decisión: OBLIGATORIA antes de export
   - Razón: Seguridad, control
   - Nunca remover esta validación

3. **Data Integrity**
   - Decisión: Nunca modificar original
   - Razón: Auditabilidad, recoverability
   - Mantener estrategia de copias

4. **Configuration**
   - Decisión: Todas las reglas en YAML
   - Razón: Sin hardcoding, extensible
   - Validar YAML en startup

### ⏳ Por Decidir (Fase 3+)

1. **API Batch Size**
   - Opciones: 10, 50, 100, 500 productos/batch
   - Decision punto: Performance vs Rate Limits

2. **Image Handling**
   - Opción A: URLs externas
   - Opción B: Upload directo
   - Opción C: No incluir (manual)

3. **Price Update Strategy**
   - Opción A: Usar precios de maestro
   - Opción B: Mantener precios WooCommerce
   - Opción C: Merge strategy (mayor precio)

---

## 📞 Feedback & Feature Requests

### Cómo Proponer Features

1. Crear issue en repositorio con:
   - Descripción clara
   - Caso de uso
   - Impacto estimado
   - Fase propuesta

2. Categoría por tipo:
   - **Bug Fix**: Fase actual
   - **Enhancement**: Próxima fase
   - **Feature**: Roadmap discussion

3. Votación:
   - 👍 Si te interesa
   - 👎 Si no es prioridad
   - 📝 Comentarios

---

## 🔄 Cambios Recientes

### v0.2.0 (Enero 2026)
```diff
✅ Completada Fase 2
  + attributes.py (validación)
  + grouping.py (agrupación)
  + review.py (maestro)
  + config/rules.yaml (150 líneas)
  + 6 test suites
  + 9 documentos
  + 5.000+ líneas código + doc
```

### v0.1.0 (Diciembre 2025)
```diff
✅ Completada Fase 1
  + loader.py
  + cleaner.py
  + patterns.py
  + main.py
  + README.md
  + requirements.txt
```

---

## 🚀 Cómo Contribuir

### Para Reportar Bugs
```
1. Reproducir el error
2. Documentar pasos
3. Crear issue con:
   - Python version
   - Excel file (sample)
   - Error output
   - Expected vs actual
```

### Para Proponer Features
```
1. Verificar no existe similar
2. Describir caso de uso
3. Proponer arquitectura
4. Estimar esfuerzo
5. Crear feature request
```

### Para Code Review
```
1. Fork repositorio
2. Crear branch: feature/xxx
3. Commit cambios
4. Push a branch
5. Crear Pull Request
6. Incluir:
   - Descripción
   - Tests nuevos
   - Documentación
```

---

## 📊 Métricas de Éxito

```
v0.3.0 (Fase 3):
  ✓ CSV export funcional
  ✓ 100% de tests pasando
  ✓ 0 datos perdidos
  ✓ < 5 segundos por 1000 productos
  ✓ 90%+ productos con confianza >= 75%

v0.4.0 (Fase 4):
  ✓ API sync bidireccional
  ✓ Auto-updates funcionando
  ✓ Reportes en tiempo real

v1.0.0 (Release):
  ✓ 5.000+ catálogos transformados
  ✓ 99.9% uptime
  ✓ < 1 segundo export
  ✓ 100 usuarios activos
```

---

## 🎯 Próximos Pasos Inmediatos

### Semana 1-2 (Fase 3 Prep)
```
[ ] Especificar WooCommerce CSV format exacto
[ ] Definir error codes y mensajes
[ ] Diseñar API connector interface
[ ] Crear test data con Revisado_Humano
```

### Semana 3-4 (Fase 3 Core)
```
[ ] Implementar exporter.py base
[ ] Tests unitarios
[ ] Documentación FASE3.md
[ ] Integration tests
```

### Semana 5-6 (Fase 3 Polish)
```
[ ] API connector
[ ] Performance optimization
[ ] Error handling refinement
[ ] Final documentation
```

---

## 💭 Visión a Largo Plazo

```
"De un catálogo Excel desordenado a un 
 sistema WooCommerce bien estructurado 
 en minutos, con revisión humana garantizada."

Meta 2026:
  • Soportar 50.000+ productos
  • Integración nativa con principales 
    plataformas (Shopify, Magento, etc.)
  • Analytics dashboard visual
  • API pública para integraciones custom

Meta 2027:
  • SaaS cloud-based
  • Multi-tienda
  • Multi-idioma
  • Marketplace sync (Amazon, eBay, etc.)
```

---

## 📋 Versiones y Compatibilidad

```
Python Support:     3.7, 3.8, 3.9, 3.10, 3.11, 3.12
OS Support:         Windows 10+, macOS 10.14+, Linux
Excel Support:      .xlsx (OpenPyXL)
CSV Support:        UTF-8, ISO-8859-1
WooCommerce:        v4.0+, v5.0+, v6.0+, v7.0+
```

---

## 🎉 Conclusión

El Catálogo Transformer está en **sólido camino** hacia v1.0.0.

**Fase 2** ✅ marca el 66% de completitud.
**Fase 3** 🚀 abrirá la exportación a WooCommerce.
**Fase 4+** 🔮 añadirá características avanzadas.

¡Gracias por ser parte de este viaje!

---

*Última actualización: 27 de Enero, 2026*
*Versión: 0.2.0*
*Next Major: 0.3.0 (v0.3.0)*
