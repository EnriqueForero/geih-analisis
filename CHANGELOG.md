# Changelog — geih-analisis

Formato: [Semantic Versioning](https://semver.org/lang/es/)

---

## [5.1.0] — 2026-04-01

### Nuevas funcionalidades

- **Configuración externa (`geih_config.json`)**: Actualizar SMMLV y referencias
  DANE sin lanzar un nuevo release a PyPI. El paquete busca el archivo en:
  ruta explícita → variable de entorno → directorio de trabajo → `~/.geih/`.

- **Análisis departamental consolidado (`AnalisisDepartamental`)**: Consolida
  indicadores de 6+ clases en un solo reporte con evaluación de precisión
  muestral (CV, IC 95%, clasificación DANE). Soporta análisis semestral.

- **Análisis de tierras agropecuarias (`AnalisisTierraAgropecuario`)**: Cruza
  distribución salarial con tenencia de tierra (P3064) del sector primario.
  Incluye: brecha propietario/no propietario, costo de oportunidad (renta vs
  ingreso), distribución por género, formalidad por tenencia, subcategoría CIIU,
  y desagregación departamental.

- **Módulo de muestreo (`geih.muestreo`)**: Infraestructura transversal para
  cálculo de errores muestrales, coeficientes de variación, intervalos de
  confianza y advertencias de muestra insuficiente. Clasificación estándar DANE
  (CV < 7% preciso, 7-15% aceptable, 15-20% bajo, > 20% no confiable).

- **33 departamentos completos**: Agregados Arauca (81), Casanare (85),
  Putumayo (86), San Andrés (88), Amazonas (91), Guainía (94), Guaviare (95),
  Vaupés (97), Vichada (99) — antes solo 24 departamentos.

- **`meses_rango` en ConfigGEIH**: Filtrar meses arbitrarios para análisis
  semestral ([1..6] o [7..12]), trimestral o cualquier período.

- **`columnas_extra` en PreparadorGEIH**: Agregar variables desde el notebook
  sin modificar el código fuente (Principio Abierto/Cerrado de SOLID).

- **Variables de tierra en defaults**: P3064 (tenencia), P3064S1 (renta
  estimada), P3056 (tipo de actividad) ahora se extraen por defecto.

- **Subcategorías CIIU sector primario**: `CIIU_SECTOR_PRIMARIO` (01-03) y
  `CIIU_AGRICULTURA_DETALLE` (4 dígitos: 0111-0170) para análisis granular.

### Mejoras

- `generar_etiqueta_periodo()` ahora soporta rangos arbitrarios de meses.
- `AREA_A_CIUDAD` incluye capitales de Amazonía/Orinoquía.
- `DPTO_A_CIUDAD` incluye todas las capitales departamentales.
- Cache de configuración externa (`_CONFIG_EXTERNA_CACHE`) para evitar
  lecturas repetidas del archivo JSON.
- Documentación actualizada con secciones de análisis departamental,
  tierras, configuración externa y precisión muestral.

### Notas de migración

- **100% backward compatible**: Todos los valores por defecto se mantienen.
  Código existente funciona sin cambios.
- `ConfigGEIH.meses_rango` es `None` por defecto (= todos los meses).
- `columnas_extra` es `None` por defecto (= solo COLUMNAS_DEFAULT).
- Si `geih_config.json` no existe, el paquete usa valores hardcodeados.

---

## [5.0.0] — 2026-03-29

### Cambios de ruptura (MAJOR)
- **Renombrado**: el paquete Python ahora se llama `geih` en vez de `geih_2025`.
  - `pip install geih-analisis` (antes `geih-2025`)
  - `from geih import ConfigGEIH` (antes `from geih import`)
  - El shim `geih_2025` garantiza compatibilidad hasta v6.0.0.

### Nuevas funcionalidades
- `py.typed` agregado: soporte completo de type hints para IDEs.
- Exports faltantes agregados a `__init__.py`.
- Logger: nombre raíz cambiado de `geih_2025` a `geih`.
