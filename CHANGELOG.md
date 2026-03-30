# Changelog — geih-analisis

Formato: [Semantic Versioning](https://semver.org/lang/es/)

---

## [5.0.0] — 2026-03-29

### Cambios de ruptura (MAJOR)
- **Renombrado**: el paquete Python ahora se llama `geih` en vez de `geih_2025`.
  - `pip install geih-analisis` (antes `geih-2025`)
  - `from geih import ConfigGEIH` (antes `from geih import`)
  - El shim `geih_2025` garantiza compatibilidad hasta v6.0.0.
- **Exportador**: el parámetro `nombre_carpeta` ahora es opcional.
  Si se pasa `config`, la carpeta se genera automáticamente como
  `resultados_geih_{anio}` (antes siempre era `resultados_geih_2025`).

### Nuevas funcionalidades
- `py.typed` agregado: soporte completo de type hints para IDEs.
- Exports faltantes agregados a `__init__.py`:
  `TAMANO_EMPRESA`, `NIVELES_AGRUPADOS`, `NIVELES_EDUCATIVOS`,
  `P3042_A_ANOS`, `AGRUPACION_DANE_8`, `LLAVES_PERSONA`,
  `LLAVES_HOGAR`, `CONVERTERS_BASE`, `CONVERTERS_CON_AREA`, `MODULOS_CSV`.
- Logger: nombre raíz cambiado de `geih_2025` a `geih`.

### Migración desde v4.x

```python
# Opción A — Código antiguo sigue funcionando (con DeprecationWarning):
from geih import ConfigGEIH  # emite warning, funciona

# Opción B — Código nuevo (recomendado):
from geih import ConfigGEIH       # limpio, sin warning

# Exportador con año automático (nuevo parámetro config):
exp = Exportador(ruta_base=RUTA, config=config)
# → crea resultados_geih_2025/ o resultados_geih_2026/ según config.anio

# Antes era necesario:
from geih_2025.config import TAMANO_EMPRESA  # workaround
# Ahora disponible directamente:
from geih import TAMANO_EMPRESA              # limpio
```

---

## [4.3.0] — 2026-03-28

### Nuevas funcionalidades
- `ComparadorMultiAnio`: comparación inter-anual TD 2025 vs 2026.
- `ConfigComparativo`: `@dataclass` para parámetros del comparativo.
- `asegurar_parquet()`: extracción RAM-eficiente con PyArrow predicate pushdown.
- Dashboard Streamlit con túnel cloudflared para Google Colab.
- 70+ clases de análisis (antes 57).

### Correcciones
- `Estacionalidad.calcular()`: acepta `geih` crudo (con `MES_NUM`), no `df`.
- `AnalisisOcupadosCiudad.calcular()`: método correcto (`calcular`, no `calcular_tablas`).
- `ComparadorMultiAnio`: separación de período de comparación para evitar
  inflación del FEX_ADJ al mezclar 12 meses con 1 mes.

---

## [4.0.0] — 2025-12-01

### Cambios de ruptura
- `ConfigGEIH` ahora recibe `anio` y auto-selecciona SMMLV y carpetas.
- `MESES_CARPETAS` migró de constante a función dinámica.
- Soporte multi-año (2022–presente).

### Nuevas funcionalidades
- 57 clases de análisis (antes 22).
- 8 módulos CSV del DANE (antes 5).
- Checkpointing en consolidación.
- DescargadorDANE para descarga automática.
