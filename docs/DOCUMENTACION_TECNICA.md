# Documentación Técnica — `geih_2025` v4.3.0

**Paquete modular de Python para análisis de la Gran Encuesta Integrada de Hogares (GEIH) del DANE — Colombia**

*ProColombia · Gerencia de Inteligencia Comercial · Equipo de Analítica de Datos*

---

## Tabla de contenido

1. [Descripción general](#1-descripción-general)
2. [Instalación](#2-instalación)
3. [Inicio rápido](#3-inicio-rápido)
4. [Arquitectura del paquete](#4-arquitectura-del-paquete)
5. [Estándares de programación](#5-estándares-de-programación)
6. [Gestión de RAM en Google Colab](#6-gestión-de-ram-en-google-colab)
7. [Configuración](#7-configuración)
8. [Consolidación de datos](#8-consolidación-de-datos)
9. [Preparación de datos](#9-preparación-de-datos)
10. [Diagnóstico de calidad](#10-diagnóstico-de-calidad)
11. [Indicadores laborales](#11-indicadores-laborales)
12. [Análisis avanzados](#12-análisis-avanzados)
13. [Análisis poblacionales](#13-análisis-poblacionales)
14. [Análisis complementarios](#14-análisis-complementarios)
15. [Análisis por 32 ciudades](#15-análisis-por-32-ciudades)
16. [Visualización matplotlib](#16-visualización-matplotlib)
17. [Visualización interactiva Plotly](#17-visualización-interactiva-plotly)
18. [Exportación](#18-exportación)
19. [Comparativo multi-año](#19-comparativo-multi-año)
20. [Flujo comparativo completo en el notebook](#20-flujo-comparativo-completo-en-el-notebook)
21. [Descarga de datos DANE](#21-descarga-de-datos-dane)
22. [Utilidades](#22-utilidades)
23. [Logging y Profiling](#23-logging-y-profiling)
24. [Dashboard Streamlit en Colab](#24-dashboard-streamlit-en-colab)
25. [Análisis personalizados fuera del paquete](#25-análisis-personalizados-fuera-del-paquete)
26. [Testing](#26-testing)
27. [Variables GEIH de referencia](#27-variables-geih-de-referencia)
28. [Variables de alto valor para ProColombia](#28-variables-de-alto-valor-para-procolombia)
29. [La regla del FEX](#29-la-regla-del-fex)
30. [Flujo de trabajo mes a mes](#30-flujo-de-trabajo-mes-a-mes)
31. [Cómo agregar un año nuevo](#31-cómo-agregar-un-año-nuevo)
32. [Convenciones de nombres](#32-convenciones-de-nombres)
33. [Preguntas frecuentes](#33-preguntas-frecuentes)

---

## 1. Descripción general

`geih_2025` transforma los microdatos crudos de la GEIH del DANE (8 módulos CSV × 12 meses × ~5 millones de registros) en indicadores publicables del mercado laboral colombiano. Incluye 74 clases con 142 métodos públicos, 71 tests automatizados y ~10,300 líneas de código en 19 módulos Python.

---

## 2. Instalación

**Google Colab:**
```python
from google.colab import drive
drive.mount('/content/drive')
import sys
sys.path.insert(0, '/content/drive/MyDrive/ProColombia/GEIH')
from geih_2025 import __version__
print(f"geih_2025 v{__version__}")
```

**Local:** `pip install -e ".[dev]"`

---

## 3. Inicio rápido

```python
from geih_2025 import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

config = ConfigGEIH(anio=2025, n_meses=12)
geih   = ConsolidadorGEIH.cargar(f'{RUTA}/GEIH_2025_Consolidado.parquet')
df     = PreparadorGEIH(config=config).preparar_base(geih)
df     = PreparadorGEIH(config=config).agregar_variables_derivadas(df)
r      = IndicadoresLaborales(config=config).calcular(df)
# → TD=8.9%, TGP=64.3%, TO=58.6%
```

---

## 4. Arquitectura del paquete

19 módulos independientes. La única dependencia obligatoria entre módulos es `config.py`.

```
geih_2025/
├── config.py                    ← Año, SMMLV, carpetas, constantes
├── utils.py                     ← EstadisticasPonderadas, GestorMemoria
├── consolidador.py              ← CSVs → DataFrame + checkpointing
├── preparador.py                ← 515 cols → 60 cols + FEX_ADJ
├── diagnostico.py               ← Missing values, tipos, identidades
├── indicadores.py               ← TD, TGP, TO, ingresos, brecha, Gini
├── analisis_avanzado.py         ← ICE, ICI, ITAT, IVI, Mincer (18 clases)
├── analisis_poblacional.py      ← Campesinos, discapacidad, migración (10)
├── analisis_complementario.py   ← Duración desempleo, forma pago, canal (5)
├── analisis_area.py             ← 32 ciudades × CIIU
├── visualizacion.py             ← 9 gráficos matplotlib
├── visualizacion_interactiva.py ← 8 gráficos Plotly
├── exportador.py                ← CSVs, Excel, PNGs organizados
├── comparativo.py               ← Comparación inter-anual
├── descargador.py               ← Organizar ZIPs del DANE
├── logger.py                    ← Logging centralizado
├── profiler.py                  ← Profiling de RAM y tiempo
└── dashboard.py                 ← Dashboard Streamlit
```

---

## 5. Estándares de programación

El notebook sigue estándares de ingeniería optimizados para Colab (~12GB RAM, límite 12h).

**Principios:** KISS (una sola responsabilidad), DRY (configuración centralizada), Fail Fast (validar ANTES de procesar), Trust but Verify (verificar tamaño después de cada operación).

**Regla de oro:** NUNCA `apply`, `iterrows` ni `for` sobre DataFrames >100k filas. SIEMPRE operaciones vectorizadas.

**Organización del notebook:** Celdas EXTRAS (definiciones, ejecutar UNA vez) y celdas EJECUTAR (máximo 10 líneas, solo configuración + llamada a función).

**Emojis:** ✅ = ejecutar siempre, 🟨 = opcional, 🛑 = precaución, ♻️ = reutilizable, 🚧 = pendiente.

---

## 6. Gestión de RAM en Google Colab

### Regla cardinal

Nunca retener dos DataFrames de año completo en RAM simultáneamente. Un año crudo (515 cols) ocupa ~2 GB. Dos = crash.

**Patrón correcto:** Cargar → procesar → guardar a disco → `del df; gc.collect()` → cargar el siguiente.

### Preparación reduce 10x la memoria

```
Parquet raw  : 515 cols, ~2.0 GB RAM, sin FEX_ADJ → crash probable
Parquet prep :  ~60 cols, ~300 MB RAM, con FEX_ADJ → funciona bien
```

### Verificar siempre

```python
from geih_2025 import GestorMemoria
GestorMemoria.estado()                      # RAM usada/libre
GestorMemoria.tamano_df(df, 'mi_base')      # MB del DataFrame
```

### PyArrow predicate pushdown

Para extraer un subconjunto de un Parquet grande sin cargarlo completo en RAM:

```python
import pyarrow.parquet as pq
table = pq.read_table('GEIH_2025.parquet', filters=[('MES_NUM', 'in', [1])])
df_enero = table.to_pandas()
del table; gc.collect()
# RAM: ~50 MB (solo enero) vs ~2 GB (todo el archivo)
```

---

## 7. Configuración

### `ConfigGEIH` — Configuración del paquete

```python
from geih_2025 import ConfigGEIH
config = ConfigGEIH(anio=2025, n_meses=12)
config.resumen()
```

**Atributos:** `anio`, `n_meses`, `smmlv` (auto-seleccionado), `carpetas_mensuales`, `periodo_etiqueta`, `referencia_dane`.

**`n_meses` es el divisor del FEX**, no un contador de meses. Si tiene 12 meses en el Parquet pero carga con `n_meses=1`, los pesos se multiplican por 12.

### Variables del notebook para comparaciones

```python
ANIO_BASE    = 2025     # Año de referencia
N_MESES_BASE = 12       # Meses del año base
ANIO_COMP    = 2026     # Año en curso
N_MESES_COMP = 1        # ← ÚNICO valor que cambia mes a mes
RUTA         = '/content/drive/MyDrive/ProColombia/GEIH'
RUTA_CIIU    = '/content/drive/.../Correlativa CIIU Rev4.xlsx'
```

### Constantes disponibles

```python
from geih_2025 import SMMLV_POR_ANIO, DEPARTAMENTOS, RAMAS_DANE, TAMANO_EMPRESA, REF_DANE
```

---

## 8. Consolidación de datos

```python
from geih_2025 import ConsolidadorGEIH
consolidador = ConsolidadorGEIH(ruta_base=RUTA, config=config, incluir_area=True)
consolidador.verificar_estructura()
geih = consolidador.consolidar(checkpoint=True)  # se recupera si falla
consolidador.exportar(geih)
# Cargar existente: geih = ConsolidadorGEIH.cargar('GEIH_2025_Consolidado.parquet')
```

**Agregar mes nuevo:** `consolidador.agregar_mes('Abril 2026', 'GEIH_2026_Consolidado.parquet')`

---

## 9. Preparación de datos

```python
from geih_2025 import PreparadorGEIH, MergeCorrelativas
prep = PreparadorGEIH(config=config)
df = prep.preparar_base(geih)                    # 515 → ~60 cols + FEX_ADJ
df = prep.agregar_variables_derivadas(df)         # RAMA, RANGO_SMMLV, ZONA...
# Mes puntual: df_dic = prep.preparar_base(geih, mes_filtro=12)
# CIIU descriptivo: df = MergeCorrelativas().merge_ciiu(df, ruta_ciiu=RUTA_CIIU)
```

---

## 10. Diagnóstico de calidad

```python
from geih_2025 import DiagnosticoCalidad, Top20Sectores
diag = DiagnosticoCalidad()
diag.resumen_rapido(geih); diag.verificar_tipos(geih); diag.validar_identidades(geih)
Top20Sectores(config=config).calcular(df, ruta_ciiu=RUTA_CIIU)
```

---

## 11. Indicadores laborales

```python
from geih_2025 import IndicadoresLaborales, DistribucionIngresos, AnalisisRamaSexo
from geih_2025 import AnalisisSalarios, BrechaGenero, IndicesCompuestos

ind = IndicadoresLaborales(config=config)
r = ind.calcular(df);  ind.sanity_check(r, "Anual 2025")
td_dpto = ind.por_departamento(df)

DistribucionIngresos(config=config).calcular(df)
AnalisisRamaSexo().calcular(df)
AnalisisSalarios(config=config).por_rama(df)
BrechaGenero().calcular(df)
IndicesCompuestos(config=config).gini(df)
```

---

## 12. Análisis avanzados

```python
from geih_2025 import (
    CalidadEmpleo, FormalidadSectorial, CompetitividadLaboral,
    VulnerabilidadLaboral, CostoLaboral, ContribucionSectorial,
    MapaTalento, BonoDemografico, Estacionalidad, EcuacionMincer,
    FuerzaLaboralJoven, AnalisisUrbanoRural, EtnicoRacial, ProxyBilinguismo,
)

CalidadEmpleo(config=config).calcular_por_departamento(df)   # ICE
FormalidadSectorial(config=config).calcular(df)               # ICF
CompetitividadLaboral(config=config).calcular(df)             # ICI
VulnerabilidadLaboral(config=config).calcular(df)             # IVI
MapaTalento(config=config).calcular(df)                       # ITAT
CostoLaboral(config=config).calcular(df)
BonoDemografico(config=config).calcular(df)
Estacionalidad().calcular(geih)        # ← usa geih crudo, NO df
ContribucionSectorial().calcular(geih)
EcuacionMincer(config=config).estimar_todos(df)
FuerzaLaboralJoven(config=config).calcular(df)
AnalisisUrbanoRural(config=config).calcular(df)
EtnicoRacial().calcular(df)
ProxyBilinguismo().calcular(df)
```

**Fórmulas:** ICE = 0.30×Pensión + 0.25×Salud + 0.25×Horas + 0.20×Ingreso. ICI = 0.25×TD + 0.20×Costo + 0.25×Talento + 0.20×Formalidad + 0.10×Jóvenes. ITAT = 0.35×Oferta + 0.35×Costo + 0.30×Calidad.

---

## 13. Análisis poblacionales

```python
from geih_2025 import (
    AnalisisCampesino, AnalisisDiscapacidad, AnalisisMigracion,
    AnalisisOtrasFormas, AnalisisOtrosIngresos, AnalisisSobrecalificacion,
    AnalisisContractual, AnalisisAutonomia, AnalisisAlcanceMercado,
    AnalisisDesanimados,
)
AnalisisCampesino(config=config).calcular(df)          # P2057
AnalisisDiscapacidad().calcular(df)                     # P1906S1-S8
AnalisisMigracion(config=config).calcular(df)           # P3370/P3376
AnalisisOtrasFormas().calcular(df)                      # P3054-P3057
AnalisisOtrosIngresos().calcular(df)                    # P7422/P7500
AnalisisSobrecalificacion(config=config).calcular(df)   # P3042 × P6430
AnalisisContractual().calcular(df)                      # P6440/P6450/P6460
AnalisisAutonomia().calcular(df)                        # P3047-P3049
AnalisisAlcanceMercado().calcular(df)                   # P1802
AnalisisDesanimados().calcular(df)                      # P6300/P6310
```

**Regla:** Las que necesitan SMMLV llevan `config=config`. Las demás se instancian con `()`.

---

## 14. Análisis complementarios

```python
from geih_2025 import DuracionDesempleo, DashboardSectoresProColombia
from geih_2025 import AnatomaSalario, FormaPago, CanalEmpleo

dur = DuracionDesempleo(config=config)
dur.calcular(df); dur.por_sexo(df); dur.por_educacion(df); dur.por_departamento(df)

DashboardSectoresProColombia(config=config).calcular(df)

anat = AnatomaSalario(config=config)
anat.resumen_nacional(df); anat.por_rama(df); anat.por_tamano_empresa(df)

fp = FormaPago(config=config)
fp.calcular(df); fp.cruce_formalidad(df)

ce = CanalEmpleo(config=config)
ce.calcular(df); ce.por_nivel_educativo(df)
```

---

## 15. Análisis por 32 ciudades

```python
from geih_2025 import AnalisisOcupadosCiudad
area = AnalisisOcupadosCiudad(config=config)
tablas = area.calcular(df, ruta_ciiu=RUTA_CIIU)  # ← calcular(), NO calcular_tablas()
area.imprimir(tablas); area.graficar(tablas)
area.exportar_excel(tablas, f'{RUTA}/resultados/CIIU_Area_{config.anio}.xlsx')
```

---

## 16. Visualización matplotlib

```python
from geih_2025 import (
    GraficoCurvaLorenz, GraficoBoxPlotSalarios, GraficoBrechaGenero,
    GraficoDistribucionIngresos, GraficoICIBubble, GraficoEstacionalidad,
    GraficoContribucionHeatmap, GraficoRamaSexo,
)
fig = GraficoCurvaLorenz().graficar(df[(df['OCI']==1) & (df['INGLABO']>0)])
exp.guardar_grafica(fig, 'Lorenz'); plt.show()
```

---

## 17. Visualización interactiva Plotly

Requiere `pip install plotly`. Retornan `plotly.graph_objects.Figure`.

```python
from geih_2025 import PlotlyLorenz, PlotlyEstacionalidad, PlotlyComparativoAnual
fig = PlotlyLorenz().graficar(df_ocu); fig.show()
```

---

## 18. Exportación

```python
from geih_2025 import Exportador
exp = Exportador(ruta_base=RUTA)
exp.guardar_tabla(td_dpto, 'indicadores_dpto')
exp.guardar_grafica(fig, 'Lorenz_2025')
exp.guardar_excel({'Hoja1': df1}, 'nombre')
exp.guardar_metadata(config, {'registros': len(geih)})
exp.resumen()
```

---

## 19. Comparativo multi-año

```python
from geih_2025 import ComparadorMultiAnio, ConfigGEIH
comp = ComparadorMultiAnio()
comp.agregar_anio(2025, f'{RUTA}/GEIH_2025_M01.parquet', ConfigGEIH(anio=2025, n_meses=1))
comp.agregar_anio(2026, f'{RUTA}/GEIH_2026_M01.parquet', ConfigGEIH(anio=2026, n_meses=1))
comp.comparar_indicadores(); comp.comparar_departamentos(); comp.evolucion_ingresos()
comp.comparar_ramas(); comp.comparar_brecha_genero()
```

---

## 20. Flujo comparativo completo en el notebook

El notebook real usa un patrón más sofisticado. Define un `ConfigComparativo` (dataclass en el notebook, no en el paquete) que orquesta la comparación entre dos años con gestión estricta de RAM.

### ConfigComparativo

```python
@dataclass
class ConfigComparativo:
    ruta: str; ruta_ciiu: str; ruta_divipola: str
    anio_base: int = 2025; n_meses_base: int = 12
    anio_comp: int = 2026; n_meses_comp: int = 1  # ← cambiar mes a mes
```

### Funciones auxiliares del notebook

`asegurar_parquet(cfg, anio, n_meses)` — Garantiza que un Parquet existe en disco con jerarquía de eficiencia: (1) ya existe → retorna ruta. (2) Existe parquet completo → extrae meses vía PyArrow predicate pushdown (sin cargar todo en RAM). (3) Nada existe → consolida desde CSV. Al retornar: CERO DataFrames en RAM.

`garantizar_parquets(cfg)` — Garantiza los 3 Parquets necesarios: período base, período comp, año base completo.

`agregar_mes_nuevo(cfg, n_meses_nuevo)` — Agrega un mes sin re-consolidar.

### Flujo de ejecución

```python
cfg = ConfigComparativo(ruta=RUTA, ruta_ciiu=RUTA_CIIU, ruta_divipola=RUTA_DIVIPOLA,
    anio_base=2025, n_meses_base=12, anio_comp=2026, n_meses_comp=1)
PATH_BASE_COMP, PATH_COMP_COMP, PATH_BASE_FULL = garantizar_parquets(cfg)

comp = ComparadorMultiAnio()
comp.agregar_anio(2025, PATH_BASE_COMP, ConfigGEIH(anio=2025, n_meses=1))
gc.collect()
comp.agregar_anio(2026, PATH_COMP_COMP, ConfigGEIH(anio=2026, n_meses=1))
comp.comparar_indicadores()
```

---

## 21. Descarga de datos DANE

La descarga automática no funciona (el DANE requiere aceptar términos). Lo que sí funciona es organizar ZIPs descargados manualmente.

```python
from geih_2025 import DescargadorDANE
desc = DescargadorDANE(config=ConfigGEIH(anio=2025, n_meses=12), ruta_destino=RUTA)
desc.instrucciones_descarga_manual()
desc.organizar_zips(f'{RUTA}/zips_dane_2025')
desc.verificar()
```

**IDs catálogo:** 2022→771, 2023→782, 2024→819, 2025→853.

---

## 22. Utilidades

```python
from geih_2025 import EstadisticasPonderadas as EP
EP.media(df['INGLABO'], df['FEX_ADJ'])
EP.mediana(df['INGLABO'], df['FEX_ADJ'])
EP.percentil(df['INGLABO'], df['FEX_ADJ'], 0.25)
EP.gini(df['INGLABO'], df['FEX_ADJ'])

from geih_2025 import GestorMemoria
GestorMemoria.estado(); GestorMemoria.tamano_df(df, 'mi_base')

from geih_2025 import ConversorTipos
ConversorTipos.estandarizar_dpto(serie)  # '5' → '05'
```

---

## 23. Logging y Profiling

```python
from geih_2025 import configurar_logging, PerfilMemoria, medir_tiempo

configurar_logging(nivel='INFO', archivo='geih.log')

perf = PerfilMemoria()
perf.snapshot("Inicio")
with medir_tiempo("Consolidar"):
    geih = consolidador.consolidar()
perf.snapshot("Post-consolidar")
perf.reporte()
```

---

## 24. Dashboard Streamlit en Colab

**Opción simple:** `from geih_2025 import ejecutar_dashboard; ejecutar_dashboard(ruta_base=RUTA)`

**Opción producción (con túnel):** El notebook incluye `lanzar_dashboard_prep()` que prepara Parquets livianos y abre túnel Cloudflare:

```python
lanzar_dashboard_prep(cfg=cfg, modo='comparacion', metodo='cloudflare')
```

| Modo | Qué carga | RAM |
|---|---|---|
| `'enero'` | Solo enero año comp | ~40 MB |
| `'comparacion'` | Enero de ambos años | ~80 MB |
| `'anio_comp'` | Meses acumulados | ~40-400 MB |
| `'anio_base'` | Año base completo (preparado) | ~400 MB |

---

## 25. Análisis personalizados fuera del paquete

El notebook incluye análisis que van más allá del paquete, escritos directamente en celdas usando `EstadisticasPonderadas`:

**Salario por educación × industria** — Mapeo granular P3042 con 9 niveles (separando Especialización, Maestría, Doctorado), tabla nacional + heatmap cruzado con top 8 ramas. Prima salarial vs universitaria.

**Análisis de altos ingresos (P90/P95/P99/P99.9)** — Umbrales percentiles, perfiles demográficos de cada segmento (sexo, educación, industria, ciudad, posición, tamaño empresa), 8 tablas comparativas + 4 gráficos (distribución log, stack bars, paneles dobles, heatmap edad × percentil).

**Box plot ponderado completo** — Versión expandida de ~150 líneas con 11 estadísticas por rama, gradiente de color, segundo eje SMMLV, etiquetas dentro de las cajas.

Estos análisis usan `EstadisticasPonderadas` del paquete y se pueden replicar con:

```python
from geih_2025.utils import EstadisticasPonderadas as EP
mediana = EP.mediana(df.loc[mask, 'INGLABO'], df.loc[mask, 'FEX_ADJ'])
```

---

## 26. Testing

```bash
python -m pytest tests/ -v     # 71 tests
python tests/smoke_test.py      # validación rápida
```

Golden set: 1,000 registros sintéticos (TD=11.76%, TGP=68.0%, TO=60.0%).

---

## 27. Variables GEIH de referencia

| Variable | Significado | Valores |
|---|---|---|
| `FEX_C18` | Factor expansión | float |
| `P3271` | Sexo | 1=H, 2=M |
| `P6040` | Edad | entero |
| `P3042` | Nivel educativo | 1-13 |
| `CLASE` | Zona | 1=Urbano, 2=Rural |
| `DPTO` | Departamento | 2 dígitos |
| `OCI` | Ocupado | 1=Sí |
| `DSI` | Desocupado | 1=Sí |
| `FT` | PEA | 1=Sí |
| `FFT` | Fuera FT | 1=Sí |
| `PET` | Edad trabajar | 1=Sí |
| `INGLABO` | Ingreso laboral | COP |
| `P6500` | Salario declarado | COP |
| `P6800` | Horas semanales | entero |
| `P6920` | Cotiza pensión | 1=Sí |
| `RAMA2D_R4` | CIIU 2 dígitos | string |
| `P6430` | Posición ocupacional | 1-9 |
| `P7250` | Semanas buscando | entero |
| `P6765` | Forma de pago | numérico |
| `P3363` | Canal empleo | 1-7 |
| `P1802` | Alcance mercado | 1-6 |
| `P2057` | ¿Campesino? | 1=Sí |
| `P1906S1-S8` | Discapacidad | 1-4 |
| `AREA` | Municipio | 5 dígitos |

---

## 28. Variables de alto valor para ProColombia

| Variable | Valor para IED/Exportaciones |
|---|---|
| `P1802=6` | Empleo DIRECTO en comercio exterior |
| `P3047-P3049` | Contratistas dependientes (evasión laboral) |
| `P3363` | Digitalización del mercado laboral |
| `P6765` | Precariedad: destajo, honorarios, comisión |
| `P3364` | Proxy tributación formal DIAN |
| `P3042 × P6430` | Talento subutilizado (sobrecalificación) |
| `P2057` | Política pública rural |
| `P1906S1-S8` | ESG para IED europea |
| `P3376` | Migración venezolana |

---

## 29. La regla del FEX

| Período | ConfigGEIH | FEX_ADJ |
|---|---|---|
| Mes puntual | `n_meses=1` | FEX_C18 ÷ 1 |
| Trimestre | `n_meses=3` | FEX_C18 ÷ 3 |
| Anual | `n_meses=12` | FEX_C18 ÷ 12 |

**Alarma:** PEA > 40M → FEX no se dividió. `sanity_check()` lo detecta.

**Excepción:** `Estacionalidad().calcular(geih)` usa FEX_C18 sin dividir.

---

## 30. Flujo de trabajo mes a mes

Cuando el DANE publica un nuevo mes (ej: febrero 2026):

1. Descargar ZIPs del DANE y `desc.organizar_zips()`
2. `consolidador.agregar_mes('Febrero 2026', 'GEIH_2026_Consolidado.parquet')`
3. Cambiar `N_MESES_COMP = 2` en la celda de configuración
4. Re-ejecutar desde la celda de comparaciones

---

## 31. Cómo agregar un año nuevo

En `config.py`: `SMMLV_POR_ANIO[2027] = 1_800_000`

Opcional: `REF_DANE[2027] = ReferenciaDane(td_anual_pct=...)` cuando DANE publique.

En `descargador.py`: `CATALOGO_DANE[2027] = {"catalog_id": 920}`

---

## 32. Convenciones de nombres

| Nombre archivo | Contenido |
|---|---|
| `GEIH_2025_M01.parquet` | Solo enero |
| `GEIH_2025_M01_M03.parquet` | Enero a marzo |
| `GEIH_2025_M01_M12.parquet` | Año completo |
| `GEIH_2025_Consolidado.parquet` | Alias año completo |
| `*_prep.parquet` | Preparado (60 cols + FEX_ADJ) para dashboard |

**Variables en memoria:** `geih` = crudo (515 cols), `df` = preparado (60 cols), `config` = ConfigGEIH, `exp` = Exportador.

**Recálculo seguro:** `if 'salarios_rama' not in dir(): salarios_rama = AnalisisSalarios(config=config).por_rama(df)`

---

## 33. Preguntas frecuentes

**¿Tabla vacía?** → `print(df['P6765'].value_counts().head())` para ver la codificación real.

**¿PEA > 40M?** → FEX no dividido. Verificar `config.n_meses`.

**¿Un solo mes?** → `ConfigGEIH(n_meses=1)` + `preparar_base(geih, mes_filtro=3)`.

**¿Cuánta RAM?** → Preparado: ~300 MB. Crudo: ~2 GB. Dos crudos: crash.

**¿`config=config` o `()`?** → Con SMMLV: `config=config`. Sin SMMLV: `()`.

**¿Colab se cayó?** → `checkpoint=True` retoma desde donde quedó.

**¿Dashboard desde Colab?** → `lanzar_dashboard_prep(cfg, modo='comparacion', metodo='cloudflare')`.

**¿Comparar enero 2025 vs enero 2026?** → Ambos con `ConfigGEIH(n_meses=1)` en `ComparadorMultiAnio`.

---

*geih_2025 v4.3.0 — 74 clases, 142 métodos, 19 módulos · ProColombia · GIC · Bogotá, 2026*
