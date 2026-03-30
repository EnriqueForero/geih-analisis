# Guía de Uso — Paquete `geih_2025` v4.3.0

**ProColombia · Gerencia de Inteligencia Comercial · Equipo de Analítica de Datos**
*Gran Encuesta Integrada de Hogares | DANE | Marco Muestral 2018*

---

## 1. Configuración inicial (una sola vez)

```python
# ═══ CELDA 1: Montar Drive y cargar paquete ═══
from google.colab import drive
drive.mount('/content/drive')

import sys
sys.path.insert(0, '/content/drive/MyDrive/ProColombia/GEIH')

from geih_2025 import __version__
print(f"geih_2025 v{__version__}")
```

## 2. Configuración del año (el ÚNICO lugar que se cambia)

```python
from geih_2025 import ConfigGEIH

# ┌──────────────────────────────────────────────────────┐
# │  Cambiar SOLO estas 2 líneas para procesar otro año  │
# └──────────────────────────────────────────────────────┘
config = ConfigGEIH(anio=2025, n_meses=12)
RUTA = '/content/drive/MyDrive/ProColombia/GEIH'

config.resumen()  # Muestra SMMLV, carpetas, período
```

**Ejemplos de configuración:**

| Caso | Código |
|---|---|
| Año 2025 completo | `ConfigGEIH(anio=2025, n_meses=12)` |
| Primer trimestre 2026 | `ConfigGEIH(anio=2026, n_meses=3)` |
| Solo enero 2026 | `ConfigGEIH(anio=2026, n_meses=1)` |

## 3. Consolidar datos (primera vez) o cargar existente

```python
from geih_2025 import ConsolidadorGEIH
import os

PARQUET = f'{RUTA}/GEIH_{config.anio}_Consolidado.parquet'

if os.path.exists(PARQUET):
    geih = ConsolidadorGEIH.cargar(PARQUET)
else:
    consolidador = ConsolidadorGEIH(ruta_base=RUTA, config=config, incluir_area=True)
    consolidador.verificar_estructura()
    geih = consolidador.consolidar(checkpoint=True)  # ← se recupera si falla
    consolidador.exportar(geih)
```

**Agregar un mes nuevo sin re-consolidar:**

```python
config_4m = ConfigGEIH(anio=2026, n_meses=4)
consolidador = ConsolidadorGEIH(ruta_base=RUTA, config=config_4m, incluir_area=True)
geih = consolidador.agregar_mes(
    mes_carpeta='Abril 2026',
    parquet_existente='GEIH_2026_Consolidado.parquet',
)
consolidador.exportar(geih)
```

## 4. Preparar datos

```python
from geih_2025 import PreparadorGEIH, Exportador

prep = PreparadorGEIH(config=config)
df = prep.preparar_base(geih)
df = prep.agregar_variables_derivadas(df)
exp = Exportador(ruta_base=RUTA)
```

## 5. Análisis disponibles (70+ clases)

### 5.1 Indicadores nacionales

```python
from geih_2025 import IndicadoresLaborales

ind = IndicadoresLaborales(config=config)
r = ind.calcular(df)
ind.sanity_check(r, f"Anual {config.anio}")
td_dpto = ind.por_departamento(df)
```

### 5.2 Los 10 análisis básicos

```python
from geih_2025 import (
    DistribucionIngresos, AnalisisRamaSexo, AnalisisSalarios,
    BrechaGenero, IndicesCompuestos, Estacionalidad,
    AnalisisUrbanoRural, FuerzaLaboralJoven, EcuacionMincer,
)
from geih_2025 import Top20Sectores

DistribucionIngresos(config=config).calcular(df)
AnalisisRamaSexo().calcular(df)
AnalisisSalarios(config=config).por_rama(df)
BrechaGenero().calcular(df)
IndicesCompuestos(config=config).gini(df)
Estacionalidad().calcular(geih)            # usa geih crudo
AnalisisUrbanoRural(config=config).calcular(df)
FuerzaLaboralJoven(config=config).calcular(df)
EcuacionMincer(config=config).estimar_todos(df)
Top20Sectores(config=config).calcular(df)
```

### 5.3 Los 8 análisis avanzados

```python
from geih_2025 import (
    CalidadEmpleo, FormalidadSectorial, CompetitividadLaboral,
    VulnerabilidadLaboral, CostoLaboral, ContribucionSectorial,
    MapaTalento, BonoDemografico,
)

CalidadEmpleo(config=config).calcular_por_departamento(df)     # ICE
FormalidadSectorial(config=config).calcular(df)                 # ICF
CompetitividadLaboral(config=config).calcular(df)               # ICI
VulnerabilidadLaboral(config=config).calcular(df)               # IVI
CostoLaboral(config=config).calcular(df)
ContribucionSectorial().calcular(geih)
MapaTalento(config=config).calcular(df)                         # ITAT
BonoDemografico(config=config).calcular(df)
```

### 5.4 Los 15 análisis poblacionales
```python
from geih_2025 import (
    AnalisisCampesino, AnalisisDiscapacidad, AnalisisMigracion,
    AnalisisOtrasFormas, AnalisisOtrosIngresos, AnalisisSobrecalificacion,
    AnalisisContractual, AnalisisAutonomia, AnalisisAlcanceMercado,
    AnalisisDesanimados,
    DuracionDesempleo, DashboardSectoresProColombia,
    AnatomaSalario, FormaPago, CanalEmpleo,
)

# ── Poblaciones especiales ───────────────────────────────
AnalisisCampesino(config=config).calcular(df)          # P2057 — ¿se considera campesino?
AnalisisDiscapacidad().calcular(df)                     # P1906S1-S8 — escala Washington
AnalisisMigracion(config=config).calcular(df)           # P3370/P3376 — migración interna e internacional
AnalisisOtrasFormas().calcular(df)                      # P3054-P3057 — autoconsumo, voluntariado, formación
AnalisisOtrosIngresos().calcular(df)                    # P7422/P7500 — pensiones, remesas, arriendos
AnalisisSobrecalificacion(config=config).calcular(df)   # P3042 × P6430 — universitarios en empleos simples
AnalisisContractual().calcular(df)                      # P6440/P6450/P6460 — contrato escrito/verbal/sin
AnalisisAutonomia().calcular(df)                        # P3047-P3049 — contratistas dependientes (asalariados disfrazados)
AnalisisAlcanceMercado().calcular(df)                   # P1802 — local/regional/nacional/exportación
AnalisisDesanimados().calcular(df)                      # P6300/P6310 — FFT que desean trabajar (potencial laboral latente)

# ── Análisis complementarios ────────────────────────────
DuracionDesempleo(config=config).calcular(df)           # P7250 — semanas buscando empleo (friccional→crónico)
DuracionDesempleo(config=config).por_departamento(df)   # Mediana semanas × dpto (proxy rigidez)
DashboardSectoresProColombia(config=config).calcular(df)# 7 sectores estratégicos para IED
AnatomaSalario(config=config).resumen_nacional(df)      # P6500 vs INGLABO — ingreso "invisible"
AnatomaSalario(config=config).por_rama(df)              # Brecha salarial por rama
FormaPago(config=config).calcular(df)                   # P6765 — destajo, honorarios, comisión
CanalEmpleo(config=config).calcular(df)                 # P3363 — contactos, internet, agencia
```

### 5.5 Análisis por 32 ciudades

```python
from geih_2025 import AnalisisOcupadosCiudad

area = AnalisisOcupadosCiudad(config=config)
tablas = area.calcular(df, ruta_ciiu=RUTA_CIIU)   # ← NO es calcular_tablas
area.imprimir(tablas)
area.exportar_excel(tablas, f'{RUTA}/resultados/CIIU_Area_{config.anio}.xlsx')
```

## 6. Gráficos

### Matplotlib (estáticos, para PNG)

```python
from geih_2025 import (
    GraficoBoxPlotSalarios, GraficoBrechaGenero,
    GraficoCurvaLorenz, GraficoICIBubble, GraficoEstacionalidad,
)

fig = GraficoCurvaLorenz().graficar(df[(df['OCI']==1) & (df['INGLABO']>0)])
exp.guardar_grafica(fig, f'Lorenz_{config.anio}')
```

### Plotly (interactivos, con tooltips y zoom)

```python
from geih_2025 import PlotlyLorenz, PlotlyICIBubble, PlotlyEstacionalidad

fig = PlotlyLorenz().graficar(df[(df['OCI']==1) & (df['INGLABO']>0)])
fig.show()  # interactivo en Colab
```

## 7. Comparación entre años

```python
from geih_2025 import ComparadorMultiAnio, ConfigGEIH

comp = ComparadorMultiAnio()
comp.agregar_anio(2025, f'{RUTA}/GEIH_2025_Consolidado.parquet', ConfigGEIH(anio=2025))
comp.agregar_anio(2026, f'{RUTA}/GEIH_2026_Consolidado.parquet', ConfigGEIH(anio=2026, n_meses=6))

comp.comparar_indicadores()        # TD/TGP/TO × año + variación
comp.comparar_departamentos()      # TD por dpto × año
comp.evolucion_ingresos()          # mediana salarial por año
comp.comparar_ramas()              # empleo por rama × año
comp.comparar_brecha_genero()      # brecha H/M por año
```

## 8. Dashboard interactivo (sin código)

```bash
pip install streamlit plotly
streamlit run geih_2025/dashboard.py
```

O desde el notebook:

```python
from geih_2025 import ejecutar_dashboard
ejecutar_dashboard(ruta_base=RUTA)
```

## 9. Profiling de memoria

```python
from geih_2025 import PerfilMemoria, medir_tiempo

perf = PerfilMemoria()
perf.snapshot("Inicio")

with medir_tiempo("Consolidar"):
    geih = consolidador.consolidar()
perf.snapshot("Post-consolidar")

perf.reporte()  # tabla RAM × etapa con alertas si > 80%
```

## 10. Logging con trazabilidad

```python
from geih_2025 import configurar_logging

# Al inicio del notebook (una vez)
configurar_logging(nivel='INFO', archivo='geih_pipeline.log')
# Desde ahora, todo se registra en consola + archivo
```

## 11. Exportar todo

```python
exp.guardar_excel({
    'Indicadores': td_dpto,
    'Salarios': salarios_rama,
    'ICE': ice_dpto,
    'ICI': ici,
}, f'GEIH_{config.anio}_Completo')

exp.guardar_metadata(config, {'registros': len(geih), 'version': '4.3.0'})
exp.resumen()
```

## 12. Agregar un año nuevo al sistema

Solo 2 cambios en `config.py`:

```python
# 1. SMMLV:
SMMLV_POR_ANIO = {
    ...
    2027: 1_800_000,   # ← agregar línea
}

# 2. Referencia DANE (cuando se publique):
REF_DANE = {
    ...
    2027: ReferenciaDane(td_anual_pct=..., tgp_anual_pct=..., ...),
}
```

Si no agrega las entradas, el sistema usa el último SMMLV conocido y el sanity_check advierte en vez de fallar.

## 13. Tests

```bash
python -m pytest tests/ -v           # 71 tests
python tests/smoke_test.py           # Validación rápida
```

## 14. La regla de oro del FEX

| Período | ConfigGEIH | FEX_ADJ |
|---|---|---|
| Mes puntual | `ConfigGEIH(anio=X, n_meses=1)` | FEX_C18 ÷ 1 |
| Trimestre | `ConfigGEIH(anio=X, n_meses=3)` | FEX_C18 ÷ 3 |
| Anual | `ConfigGEIH(anio=X, n_meses=12)` | FEX_C18 ÷ 12 |

**Si PEA > 40M → el factor NO se está dividiendo.** El `sanity_check()` lo detecta automáticamente.

---

*ProColombia · GIC · Coordinación de Analítica · Bogotá, 2026*
