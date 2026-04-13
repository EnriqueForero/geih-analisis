# geih-analisis

[![PyPI version](https://badge.fury.io/py/geih-analisis.svg)](https://pypi.org/project/geih-analisis/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.5-brightgreen.svg)]()
[![AI Assisted](https://img.shields.io/badge/AI%20Assisted-Claude%20%7C%20Gemini-blue)]()

**Paquete Python para analizar los microdatos de la Gran Encuesta Integrada de Hogares (GEIH) del DANE — Colombia.**

Convierte los archivos `.zip` crudos del DANE en indicadores del mercado laboral listos para reportar: desempleo, salarios, brecha de género, formalidad, educación, tenencia de tierra y más — con pocas líneas de código.

---

> **English summary:** Python package for Colombia's GEIH household survey microdata (DANE). Reads DANE ZIPs directly into RAM, builds a 5M-row Data Lake, and computes labor indicators (unemployment, wages, gender gap, formality, regional CIIU × department). `pip install geih-analisis` → `from geih import ConfigGEIH`.

---

## Tabla de contenidos

1. [¿Para quién es este paquete?](#1-para-quién-es-este-paquete)
2. [Novedades en la v0.1.5](#2-novedades-en-la-v016)
3. [Instalación](#3-instalación)
4. [Paso 0 — Descargar los datos del DANE](#4-paso-0--descargar-los-datos-del-dane)
5. [Inicio rápido](#5-inicio-rápido)
6. [Flujo de trabajo completo](#6-flujo-de-trabajo-completo)
7. [Análisis disponibles](#7-análisis-disponibles)
8. [Ejemplos de análisis](#8-ejemplos-de-análisis)
9. [Análisis departamental × rama CIIU](#9-análisis-departamental--rama-ciiu)
10. [Análisis por 32 ciudades y áreas metropolitanas](#10-análisis-por-32-ciudades-y-áreas-metropolitanas)
11. [Análisis de tierras agropecuarias](#11-análisis-de-tierras-agropecuarias)
12. [Configuración externa y precisión muestral](#12-configuración-externa-y-precisión-muestral)
13. [Herramientas auxiliares](#12bis-herramientas-auxiliares)
14. [Verificación contra el Boletín DANE (NUEVO v0.1.5)](#13-verificación-contra-el-boletín-dane)
15. [Desestacionalización de series mensuales (NUEVO v0.1.5)](#14-desestacionalización-de-series-mensuales)
16. [Notebooks de replicación y validación](#15-notebooks-de-replicación-y-validación)
17. [FAQ](#16-faq)
18. [Cómo citar](#17-cómo-citar)
19. [Licencia y metodología](#18-licencia-y-metodología)

---

## 1. ¿Para quién es este paquete?

Este paquete es para ti si:

- Eres **economista, analista laboral o investigador** y necesitas calcular tasas de desempleo, ingresos medianos o brechas salariales a partir de la GEIH.
- Eres **estudiante de pregrado o posgrado** y quieres explorar el mercado laboral colombiano sin procesar manualmente millones de filas.
- Trabajas en **gobiernos regionales** y necesitas indicadores departamentales con evaluación de confiabilidad estadística.
- Investigas **política pública agraria** y quieres cruzar ingresos con tenencia de tierra.
- Usas **Google Colab** o Python local y no quieres perder tiempo descomprimiendo archivos.

**No necesitas:** experiencia avanzada en programación, conocer la estructura interna de la GEIH, ni saber qué es un factor de expansión. El paquete maneja todo eso por ti.

---

## 2. Novedades en la v0.1.5

Esta versión está orientada a **rigor de validación contra el Boletín DANE**. Durante la replicación verbatim del Boletín GEIH Diciembre 2025 con tolerancia ±0.05 p.p., se identificaron seis bugs latentes que producían cifras silenciosamente incorrectas en clasificaciones geográficas y de informalidad. Todos están corregidos, blindados con tests "canario" y documentados.

### 🛡️ Correcciones críticas

- **`DOMINIO` ahora se calcula bien.** Antes el filtro `df['DOMINIO']=='13_AM'` devolvía 0 filas porque la clasificación usaba `AREA_A_CIUDAD.keys()` (DIVIPOLA de 5 dígitos) en vez de `DPTOS_13_CIUDADES` (códigos AREA de 2 dígitos del microdato). Ahora produce 4 categorías mutuamente excluyentes que cuadran con el Boletín al primer mil: `13_AM`, `10_ciudades`, `otras_cab`, `rural`.
- **`POSICION_OCU` con código CISE-93 correcto.** El mapa anterior tenía cruzados los códigos 7 y 8: jornalero quedaba como código 8 (orden alfabético del cuestionario) en vez del 7 oficial CISE-93 que usan los microdatos publicados. Cifra de control: jornaleros Dic-2025 ≈ 849 mil — ahora cuadra exacto.
- **`INFORMAL` con definición oficial 17ª CIET.** Ahora incorpora `P6870` (tamaño establecimiento) en la regla de patrones, eliminando el sesgo de +1 a +3 p.p. en zonas rurales.
- **`ConfigGEIH` ya no rechaza meses no contiguos.** `ConfigGEIH(meses_rango=[12])`, `[10,11,12]` y cualquier subconjunto del calendario funcionan. Antes la validación comparaba el rango contra su propio tamaño y siempre fallaba.
- **`PreparadorGEIH.preparar_base` deriva variables automáticamente.** Antes había que recordar llamar `agregar_variables_derivadas` manualmente; ahora es automático con el parámetro `derivar=True` por defecto.

### ⚙️ Nuevas funcionalidades

- **`IndicadoresLaborales.calcular()` expone `TD_raw`, `TGP_raw`, `TO_raw`** sin redondear. Necesario para validar contra el anexo Excel del DANE (precisión 4 decimales) cuando el round a 1 decimal del display destruiría la resolución.
- **Módulo `geih.estacional`** con `desestacionalizar()` (STL por defecto, X-13 opcional). Permite replicar la pág. 25 del Boletín DANE — TD desestacionalizada mensual.
- **`P6870` añadida a `COLUMNAS_DEFAULT`** y nuevo alias `COLUMNAS_BOLETIN` para documentar la intención cuando se replica el boletín.
- **`tests/test_canarios_boletin.py`** — batería de 26 tests "canario" que validan end-to-end la replicación del Boletín. Si cualquier cambio futuro rompe la replicación, el test correspondiente lo detecta con un mensaje que indica exactamente qué bug ha vuelto y dónde mirar.
- **Notebook `Verificacion_GEIH_2025_vs_Boletin_DANE_v3.ipynb`** — replicación verbatim del Boletín Dic-2025 contra el anexo Excel oficial, con CSV maestro de 73+ comparaciones y tolerancia estricta ±0.05 p.p. Plantilla reutilizable para validar futuros boletines.

### 📋 Migración desde 0.1.5

1. **Reinstale** y **reinicie el kernel** de Colab/Jupyter (Python cachea módulos).
2. Si su código llamaba `agregar_variables_derivadas` manualmente, ya no es necesario — pero mantenerlo no rompe nada (el método es idempotente).
3. Si dependía de `df['DOMINIO']=='13_AM'` antes y obtenía cifras anómalas, **revise sus reportes** — la lógica anterior producía basura silenciosa.
4. Para informalidad oficial: si su Parquet fue consolidado antes de 0.1.5, considere reconsolidar para que `P6870` entre en la base. Sin ella, `INFORMAL` cae a la versión aproximada y avisa con un warning.

👉 Detalle completo en [`CHANGELOG.md`](CHANGELOG.md).

---

## 2.bis Novedades en la v0.1.5

Esta versión reorganiza el pipeline de ingesta y añade un nuevo módulo analítico clave:

- **📦 Lectura directa de `.zip` → RAM.** El `ConsolidadorGEIH` ahora lee los ZIP mensuales del DANE sin descomprimirlos a disco. Ya **no es necesario** extraer los CSV manualmente ni crear carpetas `CSV/`. Coloca los ZIP tal como los descargas y listo.
- **🗺️ Nueva clase `OcupadosDptoRama`** (`geih.analisis_dpto_rama`) — Ocupados promedio anual por Departamento × Rama CIIU (2 o 4 dígitos) con evaluación de CV bajo diseño complejo (Cochran 1977, Kish 1965).
- **🏙️ `AnalisisOcupadosCiudad` refactorizado** — 6 tablas (nacional, agrupación DANE, dominio geográfico, ciudad/AM, granular CIIU×ciudad, CIIU nacional) + exportación Excel multi-hoja.
- **🧱 Separación Data Lake / Data Mart.** `ConsolidadorGEIH` construye el universo completo (~515 columnas, ~5M filas). `PreparadorGEIH` filtra al Data Mart analítico. Esto permite reutilizar el Parquet consolidado para análisis no previstos.
- **🧩 `append_mes()`** — agrega un mes nuevo al Parquet existente sin reconsolidar todo el año.

👉 Cambios completos en [`CHANGELOG.md`](CHANGELOG.md).

---

## 3. Instalación

### Opción A — pip (recomendado)

```bash
pip install geih-analisis
```

Con el dashboard Streamlit opcional:

```bash
pip install "geih-analisis[dashboard]"
```

### Opción B — Google Colab desde Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')
!pip install geih-analisis -q

from geih import __version__
print(f"geih v{__version__} listo")
```

### Requisitos

| Dependencia | Versión mínima |
|---|---|
| Python | 3.9+ |
| pandas | 1.5+ |
| numpy  | 1.21+ |
| pyarrow | 10.0+ |
| scipy  | 1.7+ |
| openpyxl | 3.0+ |

---

## 4. Paso 0 — Descargar los datos del DANE

> ⚠️ **Este paquete no incluye los datos.** Los microdatos de la GEIH son públicos y gratuitos, pero debes descargarlos del portal oficial del DANE.

### 4.1 Dónde descargar

#### Microdatos GEIH (lo único obligatorio para usar el paquete)

**Portal oficial:** 🔗 [https://microdatos.dane.gov.co](https://microdatos.dane.gov.co/index.php/catalog/central/about)

1. Abrir el portal y buscar `Gran Encuesta Integrada de Hogares`.
2. Seleccionar el año (ej. `GEIH 2025`) → **"Obtener microdatos"**.
3. Descargar el **ZIP mensual** de cada mes que quieras analizar. El ZIP contiene los 8 módulos CSV que define el DANE (Características generales, Datos del hogar, Fuerza de trabajo, Ocupados, No ocupados, Otras formas de trabajo, Migración, Otros ingresos).

> Los archivos `.DAT` y `.SAV` son para software estadístico especializado (SPSS, SAS) y no se usan aquí. Solo necesitas el ZIP que contiene los CSV.

#### Documentación técnica oficial — leerla evita errores graves

| Recurso | Para qué sirve | Dónde |
|---|---|---|
| **Manual DDI-853** | Diccionario completo de variables del microdato (`P3271`=sexo, `P6430`=posición ocupacional, etc.). Indispensable para entender qué codifica cada columna. | [https://microdatos.dane.gov.co/index.php/catalog/853](https://microdatos.dane.gov.co/index.php/catalog/853) |
| **Boletín mensual GEIH** | Cifras oficiales publicadas. **Use siempre el más reciente como fuente-de-verdad cuando valide cálculos propios.** Trae el PDF de "Principales resultados" + el anexo Excel con precisión completa. | [https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo](https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo) |
| **DIVIPOLA** | División Político-Administrativa (códigos de departamento y municipio). Crítica si va a cruzar GEIH con otras fuentes. | [https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/?cod=112](https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/?cod=112) |
| **CIIU Rev. 4 A.C.** | Clasificación Industrial Internacional Uniforme adaptada para Colombia. Define qué significa cada código de `RAMA2D_R4` y `RAMA4D_R4`. | [https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/clasificaciones/clasificacion-industrial-internacional-uniforme-de-todas-las-actividades-economicas-ciiu](https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/clasificaciones/clasificacion-industrial-internacional-uniforme-de-todas-las-actividades-economicas-ciiu) |
| **Tablas correlativas** | Conversiones entre clasificaciones (CIIU↔CPC, CIIU↔CIUO). Útiles si va a cruzar con Censo Económico, EAM, EAS. | [https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/tablas-correlativas](https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/tablas-correlativas) |
| **Nota metodológica de Informalidad** | Definición operativa de la 17ª CIET aplicada por el DANE. Lectura recomendada antes de interpretar la columna `INFORMAL`. | [https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/Nueva_medicion_informalidad.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/Nueva_medicion_informalidad.pdf) |

> 🛑 **Regla de oro:** cualquier indicador que produzca con esta librería **debe** validarse contra el boletín DANE más reciente antes de publicarse o enviarse a un tomador de decisiones. La librería es una herramienta de cálculo, no una fuente oficial. Si una cifra suya difiere del boletín en más de la tolerancia que tenga el indicador (típicamente ±0.05 p.p. para tasas, ±1 mil para poblaciones), **algo está mal en su consolidado o en su código** — no en el boletín. Use el notebook de verificación de la sección 13 como plantilla de validación.

### 4.2 Organización de los archivos — carpeta `data/`

A partir de la v0.1.5 la estructura es **radicalmente más simple**. Crea una carpeta `data/` (o como prefieras) y coloca **los ZIP tal como los descargaste**, renombrándolos con el patrón `<Mes> <Año>.zip`:

```
data/                            ← tu variable RUTA
│
├── Enero 2025.zip               ← ZIP descargado del DANE, sin extraer
├── Febrero 2025.zip
├── Marzo 2025.zip
├── Abril 2025.zip
├── Mayo 2025.zip
├── Junio 2025.zip
├── Julio 2025.zip
├── Agosto 2025.zip
├── Septiembre 2025.zip
├── Octubre 2025.zip
├── Noviembre 2025.zip
└── Diciembre 2025.zip
```

> **Nombres exactos:** `Enero 2025.zip`, `Febrero 2025.zip`, … `Diciembre 2025.zip`. Mayúscula inicial, espacio, año, extensión `.zip`. Esta es la nomenclatura que el paquete busca.
>
> **Compatibilidad hacia atrás:** si ya tienes los CSV extraídos en carpetas `Enero 2025/CSV/...`, el paquete sigue reconociéndolas como fallback. Pero para nuevos usuarios, **lo recomendado es dejar los ZIP tal cual**.

### 4.3 Verificar que todo está en orden

```python
from geih import ConsolidadorGEIH, ConfigGEIH

config = ConfigGEIH(anio=2025, n_meses=12)
cons   = ConsolidadorGEIH(ruta_base='data', config=config)
cons.verificar_estructura()
# ✅ Enero 2025.zip: 8 módulos — OK
# ✅ Febrero 2025.zip: 8 módulos — OK
# ...
```

Si falta un ZIP, está corrupto, o le falta un módulo adentro, el verificador te lo dice exactamente.

---

## 5. Inicio rápido

### Ultra-rápido — 3 líneas (si ya consolidaste antes)

```python
from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

config = ConfigGEIH(anio=2025, n_meses=12)
geih   = ConsolidadorGEIH.cargar('data/GEIH_2025_Consolidado.parquet')
df     = PreparadorGEIH(config=config).preparar_base(geih)
r      = IndicadoresLaborales(config=config).calcular(df)
print(f"TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
```

### Completo — desde los ZIP hasta los resultados

```python
from geih import (
    ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH,
    IndicadoresLaborales, AnalisisSalarios, BrechaGenero, Exportador,
)
import os

# 1. Configurar
RUTA   = 'data'                                 # carpeta con los ZIP
config = ConfigGEIH(anio=2025, n_meses=12)
config.resumen()                                 # muestra SMMLV, período y ZIP esperados

# 2. Consolidar los ZIP del DANE (primera vez: ~5 min; luego instantáneo)
PARQUET = f'{RUTA}/GEIH_{config.anio}_Consolidado.parquet'
if os.path.exists(PARQUET):
    geih = ConsolidadorGEIH.cargar(PARQUET)
else:
    cons = ConsolidadorGEIH(ruta_base=RUTA, config=config, incluir_area=True)
    cons.verificar_estructura()
    geih = cons.consolidar(checkpoint=True)      # retoma si Colab se cae
    cons.exportar(geih, PARQUET)

# 3. Preparar el Data Mart
prep = PreparadorGEIH(config=config)
df   = prep.preparar_base(geih)
df   = prep.agregar_variables_derivadas(df)

# 4. Calcular y exportar
ind = IndicadoresLaborales(config=config)
r   = ind.calcular(df)
ind.sanity_check(r, f"Anual {config.anio}")     # valida contra cifras DANE

exp = Exportador(ruta_base=RUTA, config=config)
exp.guardar_tabla(ind.por_departamento(df), f'desempleo_dptos_{config.anio}')
print(f"✅ TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
```

---

## 6. Flujo de trabajo completo

```
ZIP mensuales del DANE (data/Enero 2025.zip, Febrero 2025.zip, ...)
          ↓
  ConsolidadorGEIH     → lee los ZIP a RAM, hace LEFT JOIN de los 8 módulos
          ↓               sobre el módulo ancla "Características generales".
          ↓               Guarda GEIH_2025_Consolidado.parquet  (Data Lake, ~515 col)
  PreparadorGEIH       → filtra columnas analíticas (Data Mart),
          ↓               calcula FEX_ADJ, mapea ramas y departamentos,
          ↓               agrega variables derivadas (INGLABO_SML, MES_NUM, etc.)
  Clases de análisis   → TD, salarios, brecha, Gini, ICE, ICI, ITAT,
          ↓               OcupadosDptoRama, AnalisisOcupadosCiudad, ...
  Exportador           → resultados_geih_2025/
                           ├── graficas/   (PNG)
                           ├── tablas/     (CSV)
                           └── excel/      (XLSX multi-hoja)
```

### El único parámetro que cambia: `ConfigGEIH`

```python
ConfigGEIH(anio=2025, n_meses=12)                                    # año completo
ConfigGEIH(anio=2026, n_meses=3)                                     # primer trimestre
ConfigGEIH(anio=2026, n_meses=1)                                     # solo enero
ConfigGEIH(anio=2025, n_meses=12, meses_rango=[1,2,3,4,5,6])         # primer semestre
```

`ConfigGEIH` selecciona automáticamente el SMMLV del año, genera la lista de ZIP esperados y controla cómo se calcula el factor de expansión ajustado.

---

## 7. Análisis disponibles

### Indicadores fundamentales

| Clase | Qué produce |
|---|---|
| `IndicadoresLaborales` | TD, TGP, TO — nacional y por departamento |
| `DistribucionIngresos` | Distribución de ingresos por rangos de SMMLV |
| `AnalisisSalarios`     | Mediana, media, percentiles por rama y edad |
| `BrechaGenero`         | Diferencia salarial H/M por nivel educativo |
| `IndicesCompuestos`    | Coeficiente de Gini del ingreso laboral |
| `AnalisisRamaSexo`     | Composición del empleo por industria y sexo |

### Índices compuestos y análisis avanzado

| Clase | Qué produce |
|---|---|
| `CalidadEmpleo` (ICE) | Pensión + salud + horas + salario |
| `CompetitividadLaboral` (ICI) | Competitividad laboral por departamento |
| `VulnerabilidadLaboral` (IVI) | Vulnerabilidad por rama |
| `MapaTalento` (ITAT) | Oferta, costo y calidad por departamento |
| `FormalidadSectorial` (ICF) | Formalidad por sector económico |
| `EcuacionMincer` | Retorno salarial por año de educación |
| `Estacionalidad` | Variación mensual de TD, TGP, TO |
| `FuerzaLaboralJoven` | Indicadores para jóvenes 15–28 |
| `CostoLaboral` | Costo total incluyendo prestaciones (~54%) |

### Poblaciones especiales

`AnalisisCampesino`, `AnalisisDiscapacidad` (Washington ONU), `AnalisisMigracion`, `AnalisisSobrecalificacion`, `AnalisisContractual`, `AnalisisAutonomia`, `DuracionDesempleo`, `DashboardSectoresProColombia`.

### Nuevos / refactorizados en v0.1.5

| Clase | Módulo | Qué produce |
|---|---|---|
| `OcupadosDptoRama` | `geih.analisis_dpto_rama` | **Ocupados promedio anual** por Departamento × Rama CIIU (2 o 4 dígitos) con CV, IC 95% y clasificación DANE |
| `AnalisisOcupadosCiudad` | `geih.analisis_area` | 6 tablas CIIU × 32 ciudades/AM + Excel multi-hoja |
| `AnalisisDepartamental` | `geih.analisis_dpto` | Reporte integral por departamento con precisión muestral |
| `AnalisisTierraAgropecuario` | `geih.analisis_tierra` | Distribución salarial × tenencia de tierra (P3064) |

### Otras clases disponibles en el paquete (no listadas arriba)

| Clase | Qué produce |
|---|---|
| `DiagnosticoCalidad` | Valores faltantes, ceros sospechosos, tipos incorrectos y columnas duplicadas sobre la base consolidada |
| `Top20Sectores` | Ranking de las 20 ramas CIIU con mayor ocupación |
| `AnalisisHoras`, `AnalisisSubempleo` | Horas trabajadas y subempleo subjetivo/objetivo |
| `AnalisisFFT` | Fuerza de trabajo potencial (extendida) |
| `AnalisisUrbanoRural` | Brecha cabecera vs resto |
| `ProductividadTamano` | Productividad aproximada por tamaño de empresa |
| `ContribucionSectorial` | Aporte de cada sector al empleo total |
| `AnatomaSalario`, `FormaPago` | Descomposición del salario y forma de pago (efectivo, transferencia, especie) |
| `CanalEmpleo` | Cómo consiguieron el empleo los ocupados |
| `EtnicoRacial`, `BonoDemografico` | Composición étnica y ventana demográfica |
| `ProxyBilinguismo` | Proxy de bilingüismo vía P3041 |
| `AnalisisOtrasFormas`, `AnalisisOtrosIngresos` | Módulos DANE "Otras formas de trabajo" y "Otros ingresos" |
| `AnalisisAlcanceMercado`, `AnalisisDesanimados` | Alcance geográfico de la empresa y trabajadores desanimados |
| `MergeCorrelativas` | Enriquece el DataFrame con descripciones CIIU Rev.4 y DIVIPOLA legibles |

### Comparación entre años

```python
from geih import ComparadorMultiAnio, ConfigGEIH

comp = ComparadorMultiAnio()
comp.agregar_anio(2025, 'data/GEIH_2025_M01.parquet', ConfigGEIH(anio=2025, n_meses=1))
comp.agregar_anio(2026, 'data/GEIH_2026_M01.parquet', ConfigGEIH(anio=2026, n_meses=1))
comp.comparar_indicadores()      # TD / TGP / TO con variación anual
comp.comparar_departamentos()    # TD por departamento × año
comp.comparar_brecha_genero()    # brecha H/M por año
```

---

## 8. Ejemplos de análisis

### Tasa de desempleo nacional y por departamento

```python
from geih import IndicadoresLaborales

ind = IndicadoresLaborales(config=config)
r   = ind.calcular(df)
print(f"TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
# → TD=9.8%  TGP=63.4%  TO=57.2%

td_dpto = ind.por_departamento(df)
print(td_dpto[['Departamento', 'TD_%', 'Ocupados_M']].head(10).to_string(index=False))
```

### Salarios por nivel educativo

```python
from geih.utils import EstadisticasPonderadas as EP

niveles = {10: 'Universitaria', 11: 'Especialización', 12: 'Maestría', 13: 'Doctorado'}
df_edu  = df[(df['OCI'] == 1) & (df['INGLABO'] > 0)].copy()
df_edu['NIVEL'] = df_edu['P3042'].map(niveles)

for nivel in niveles.values():
    m   = df_edu['NIVEL'] == nivel
    med = EP.mediana(df_edu.loc[m, 'INGLABO'], df_edu.loc[m, 'FEX_ADJ'])
    print(f"{nivel:20s}: ${med:>12,.0f}  ({med/config.smmlv:.1f}× SMMLV)")
```

### Brecha salarial de género

```python
from geih import BrechaGenero
print(BrechaGenero().calcular(df))
#                 Hombres  Mujeres  Brecha_%
# Media             1.35     1.18     -12.6
# Universitaria     2.10     1.95      -7.1
# Maestría          4.82     4.41      -8.5
```

---

## 9. Análisis departamental × rama CIIU

Replica la metodología oficial del DANE para estimar ocupados por Departamento (DIVIPOLA) y Rama CIIU Rev. 4 adaptada (2 dígitos: 88 divisiones, o 4 dígitos: ~500 clases).

```python
from geih import OcupadosDptoRama, ConfigGEIH

config = ConfigGEIH(anio=2025, n_meses=12)
odr    = OcupadosDptoRama(config=config)

tabla_2d = odr.calcular(df, nivel="2d")   # 88 divisiones
tabla_4d = odr.calcular(df, nivel="4d")   # ~500 clases

odr.exportar_excel(tabla_2d, "ocupados_dpto_rama_2d_2025.xlsx")
```

**Metodología:** para cada mes y celda `(DPTO, rama)`, se calcula el total expandido `T_m = Σ FEX_C18` y el conteo muestral `n_m`. El promedio anual es la media de los 12 totales mensuales reponderada por meses con dato. El CV se estima con la fórmula de varianza bajo diseño complejo:

```
Var(p̂) ≈ DEFF × p(1−p) / n_base
```

donde `n_base` es el tamaño muestral del **departamento** (no de la celda), porque todos los registros del dominio contribuyen a estimar la proporción. Cada celda lleva su clasificación DANE (precisión alta / aceptable / baja / no confiable).

---

## 10. Análisis por 32 ciudades y áreas metropolitanas

```python
from geih import AnalisisOcupadosCiudad

area   = AnalisisOcupadosCiudad(config=config)
tablas = area.calcular(df)              # 6 tablas
area.imprimir(tablas)
area.exportar_excel(tablas, "CIIU_Area_2025.xlsx")
```

Produce 6 tablas: total nacional, agrupación DANE, dominio geográfico, ciudad/AM, granular CIIU×ciudad, y CIIU nacional. Incluye 3 gráficos (barras por agrupación, barras por ciudades, heatmap rama×ciudad) y exportación Excel multi-hoja. Usa la variable `AREA` (DIVIPOLA de 5 dígitos del módulo Ocupados) para identificar las 13 ciudades principales, las 10 áreas intermedias y 9 adicionales.

---

## 11. Análisis de tierras agropecuarias

```python
from geih import AnalisisTierraAgropecuario

tierra  = AnalisisTierraAgropecuario(config=config)
reporte = tierra.reporte_completo(df)
tierra.exportar_excel(reporte, "tierras_2025.xlsx")
```

Explota P3064 (tenencia), P3064S1 (renta estimada) y P3056 (tipo de actividad) para: brecha de ingresos propietario vs no propietario, costo de oportunidad (ingreso laboral vs renta de la tierra), distribución por género, formalidad agropecuaria, CIIU a 4 dígitos (Agricultura/Silvicultura/Pesca), y desagregación departamental con evaluación de confiabilidad en cada celda.

---

## 12. Configuración externa y precisión muestral

### `geih_config.json` — actualizar SMMLV sin esperar un release

```json
{
  "smmlv_por_anio":  { "2027": 1900000 },
  "ref_dane": {
    "2026": { "td_anual_pct": 9.2, "tgp_anual_pct": 64.0, "to_anual_pct": 58.0 }
  },
  "muestreo": { "deff_default": 2.5, "cv_preciso_pct": 7.0, "cv_aceptable_pct": 15.0 }
}
```

Orden de búsqueda: ruta explícita → `GEIH_CONFIG_PATH` (env) → `./geih_config.json` → `~/.geih/geih_config.json`.

### Evaluar precisión de cualquier estimación

```python
from geih import evaluar_proporcion

p = evaluar_proporcion(proporcion=0.089, n_registros=50_000,
                       n_expandido=26_000_000, dominio="Nacional")
print(p.resumen())
# Nacional  Est=8.90  EE=0.20  CV=2.3%  IC=[8.51, 9.29]  ✅ Precisión alta
```

| CV | Clasificación | Uso |
|---|---|---|
| < 7 %  | ✅ Precisión alta      | Publicable |
| 7–15 % | ⚠️ Precisión aceptable | Usar con precaución |
| 15–20 %| ⚠️⚠️ Precisión baja    | Solo referencia |
| > 20 % | ❌ No confiable        | No publicar |

`AnalisisDepartamental`, `OcupadosDptoRama` y `AnalisisTierraAgropecuario` integran esta evaluación en cada fila.

---

## 12.bis. Herramientas auxiliares

Además de las clases de análisis, el paquete incluye utilidades técnicas para todo el ciclo de vida del dato:

### Diagnóstico de calidad de la base

```python
from geih import DiagnosticoCalidad

diag  = DiagnosticoCalidad()
tabla = diag.valores_faltantes(geih, titulo="Base consolidada 2025", umbral_pct=1.0)
diag.verificar_tipos(geih)        # detecta tipos incorrectos
diag.columnas_duplicadas(geih)    # columnas con contenido idéntico o colineal
```

Reporta valores faltantes y ceros por columna, tipos de dato sospechosos y columnas potencialmente duplicadas sobre el Data Lake antes de pasar al análisis.

### Merge con correlativas CIIU y DIVIPOLA

```python
from geih import MergeCorrelativas

merger = MergeCorrelativas()
df = merger.merge_ciiu(df, ruta_ciiu="correlativas/CIIU_Rev4_Col.xlsx",
                      sheet_name="CIIU 2022")
df = merger.merge_divipola(df, ruta_divipola="correlativas/DIVIPOLA.xlsx")
```

Agrega las columnas `DESCRIPCION_CIIU` y el nombre legible del departamento/municipio a partir de archivos Excel externos. Útil para exportar tablas con etiquetas en lugar de códigos.

### Módulo muestral completo

Además de `evaluar_proporcion()` (§12), el módulo `geih.muestreo` expone:

```python
from geih import evaluar_media, evaluar_total, clasificar_precision

# Media muestral con IC bajo diseño complejo
evaluar_media(media=2_100_000, desv_est=1_450_000,
              n_registros=38_000, n_expandido=22_000_000, dominio="Ocupados").resumen()

# Total expandido (ocupados, desocupados, PEA)
evaluar_total(total=24_500_000, n_registros=50_000,
              n_expandido=26_000_000, dominio="Ocupados").resumen()

# Clasificación directa a partir de un CV
clasificar_precision(cv_pct=8.3)   # → "⚠️ Precisión aceptable"
```

Todas las rutinas aplican la fórmula de varianza bajo diseño complejo con `DEFF` configurable (default 2,5 para GEIH).

### Logging estructurado

```python
from geih import configurar_logging, get_logger

configurar_logging(nivel="INFO", archivo="logs/geih_2025.log")
log = get_logger("mi_analisis")
log.info("Inicio del pipeline")
```

El `LoggerGEIH` centraliza mensajes del consolidador y los análisis en un único archivo reutilizable desde notebooks.

### Dashboard Streamlit (opcional)

```python
from geih import ejecutar_dashboard
ejecutar_dashboard(ruta_base="data", puerto=8501)
# 🌐 Dashboard disponible en http://localhost:8501
```

Lanza la interfaz Streamlit en segundo plano con filtros y gráficos básicos sobre los Parquet consolidados. Requiere `pip install "geih-analisis[dashboard]"`.

### Exportador unificado

```python
from geih import Exportador
exp = Exportador(ruta_base="data", config=config)
exp.guardar_tabla(td_dpto, "desempleo_dptos_2025")   # CSV + XLSX
exp.guardar_grafico(fig, "td_por_rama")              # PNG en graficas/
```

Crea automáticamente las subcarpetas `resultados_geih_<anio>/tablas/`, `graficas/` y `excel/`.

---

## 13. Verificación contra el Boletín DANE

> 🆕 **Nuevo en v0.1.5.** Esta sección documenta el flujo recomendado para validar que sus cálculos reproducen el Boletín DANE oficial dentro de tolerancia estricta.

### Por qué es obligatorio validar

La librería implementa cientos de operaciones sobre microdatos complejos. Aunque la suite de tests garantiza que los cálculos son matemáticamente correctos contra cifras hardcoded del boletín, **su consolidado puede tener problemas que la librería no puede detectar**: meses faltantes, factores de expansión corruptos, columnas renombradas, joins mal hechos en el módulo de consolidación. La única defensa real es validar el resultado final contra el boletín publicado por el DANE para el mismo período.

### El flujo de 5 pasos

1. **Descargue el boletín mensual del DANE** para el período que está analizando (PDF + anexo Excel) desde el portal oficial. El anexo Excel es la fuente-de-verdad: el PDF redondea a 1 decimal y no sirve para validación estricta.
2. **Identifique 5-10 cifras de control** del boletín — típicamente: TD nacional, TGP nacional, ocupados totales, ocupados por dominio (13_AM, rural), tasas por sexo. Estas son sus "canarios".
3. **Calcule las mismas cifras con la librería**, usando `IndicadoresLaborales.calcular()` con los campos `_raw` (sin redondear).
4. **Compare con tolerancia estricta** — ±0.05 p.p. para tasas, ±1 mil para poblaciones. Cualquier diferencia mayor es señal de problema.
5. **Si todo cuadra**, su consolidado es confiable y los demás indicadores que calcule sobre la misma base heredan esa confianza. Si no cuadra, **no avance** hasta entender por qué.

### Plantilla mínima de verificación

```python
from geih import ConfigGEIH, PreparadorGEIH, IndicadoresLaborales

# Vista de Diciembre 2025
cfg = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[12])
df_dic = PreparadorGEIH(cfg).preparar_base(geih_raw)

r = IndicadoresLaborales().calcular(df_dic)

# Cifras del Boletín DANE Dic-2025 (anexo Excel, no del PDF redondeado)
TOLERANCIA_PP = 0.05
referencias = {
    'TD_raw':  8.0,
    'TGP_raw': 64.3,
    'TO_raw':  59.2,
}
for clave, ref in referencias.items():
    diff = abs(r[clave] - ref)
    estado = '✅' if diff <= TOLERANCIA_PP else '❌'
    print(f'{estado} {clave}: {r[clave]:.4f}  (DANE: {ref}  Δ={diff:.4f})')

# Sanity check ácido: PET expandido debe estar ~40.9 M en CUALQUIER vista
# Es el "canario" más sensible: detecta divisores FEX mal aplicados.
pet_M = df_dic.loc[df_dic['PET']==1, 'FEX_ADJ'].sum() / 1e6
assert 40.5 < pet_M < 41.3, f'PET = {pet_M:.2f}M fuera de rango — divisor FEX mal'
```

### Tests "canario" automatizados

El paquete incluye `tests/test_canarios_boletin.py` — 26 tests organizados en 8 clases que validan **end-to-end** la replicación del Boletín Dic-2025. Si cualquier cambio en su consolidado (o en una versión futura de la librería) rompe una cifra del boletín, el test correspondiente falla con un mensaje que indica exactamente qué métrica difiere y dónde mirar.

```bash
# Correr los canarios contra su consolidado
GEIH_TEST_DATA=/ruta/a/su/consolidado/2025     pytest tests/test_canarios_boletin.py -v
```

Si la variable de entorno no está definida, los tests se **skipean limpiamente** — no falla la suite por falta de datos. Esto permite incluirlos en CI sin necesidad de subir microdatos al repositorio.

### Tolerancias recomendadas

| Tipo de indicador | Tolerancia | Justificación |
|---|---|---|
| Tasas (TD, TGP, TO, informalidad) | **±0.05 p.p.** | Mitad del último decimal publicado por DANE |
| Poblaciones (miles) | **±1 mil** | Precisión declarada del anexo Excel |
| Ingresos (pesos/mes) | **±500 COP** | ~0.05% del SMMLV |
| Informalidad (rural) | **±0.5 p.p.** | Definición oficial DANE incluye registro mercantil que la librería no puede replicar sin metadato extra |

---

## 14. Desestacionalización de series mensuales

> 🆕 **Nuevo en v0.1.5.** El módulo `geih.estacional` permite reproducir la sección "TD desestacionalizada" del Boletín DANE (página 25), que separa la tendencia de los efectos estacionales en la serie mensual.

### Cuándo usarla

La TD cruda mensual tiene patrones estacionales fuertes: pico en enero (fin de contratos navideños), valle en noviembre (alta contratación pre-navideña). Comparar `TD(noviembre)` con `TD(enero)` directamente lleva a conclusiones erróneas. La serie desestacionalizada permite ver la tendencia subyacente.

### Uso básico

```python
from geih import ConfigGEIH, PreparadorGEIH
from geih.estacional import desestacionalizar_td_mensual
import pandas as pd

# Vista anual completa
cfg = ConfigGEIH(anio=2025, n_meses=12)
df_anu = PreparadorGEIH(cfg).preparar_base(geih_raw)

# STL requiere ≥24 meses → necesitamos histórico del año anterior.
# Lo más simple es usar las cifras del boletín del año previo:
td_2024 = pd.Series(
    [12.1, 11.5, 11.3, 10.6, 10.3, 10.3, 10.0, 9.8, 9.1, 8.4, 8.2, 9.1],
    index=pd.period_range('2024-01', '2024-12', freq='M').to_timestamp(),
)

resultado = desestacionalizar_td_mensual(
    df_anu, anio=2025, incluir_historico=td_2024,
)
print(resultado.tail(3))
#             td_cruda  td_desest
# 2025-10-01      7.20       7.51
# 2025-11-01      7.00       7.43
# 2025-12-01      8.00       7.62
```

### Limitación importante

El método por defecto es **STL** (Seasonal-Trend LOESS), que está siempre disponible vía `statsmodels`. El DANE usa internamente **X-13-ARIMA-SEATS** con calendario laboral colombiano (días hábiles, Semana Santa, festivos), parámetros que no exponemos en esta librería. Esperar diferencias de **±0.1 a ±0.3 p.p.** entre la curva desestacionalizada por la librería y la publicada por el DANE en el boletín. La forma general (tendencia, picos, valles) sí es reproducible.

---

## 15. Notebooks de replicación y validación

> 🆕 **Nuevo en v0.1.5.** El proyecto incluye notebooks de ejemplo listos para correr en Google Colab, que sirven como plantillas de validación y como referencia ejecutable de las mejores prácticas.

### `Verificacion_GEIH_2025_vs_Boletin_DANE_v3.ipynb`

Notebook de **replicación verbatim del Boletín GEIH Diciembre 2025** contra el anexo Excel oficial del DANE. 9 secciones (A-I) que cubren:

- **A — Diciembre mensual:** TD/TGP/TO nacional, brecha por sexo, dominio geográfico, ramas CIIU (las 13), posición ocupacional.
- **B — Trimestre Oct-Dic:** TD por las 23 ciudades del boletín extendido.
- **C — Anual Ene-Dic:** totales y brechas por sexo.
- **D — Informalidad:** 6 desagregaciones contra Boletín pág. 42.
- **E — Juventud (15-28):** TGP/TO/TD por sexo y período.
- **F — Étnico:** indígenas, negro/afro, sin grupo étnico.
- **G — Ingresos laborales** (IML por sexo).
- **H — Errores muestrales:** documenta el gap conocido de la librería.
- **I — Replicación de gráficas:** TD mensual cruda + desestacionalizada (pág. 25) y dispersión TGP H/M de 23 ciudades (pág. 29).

Produce un CSV maestro (`verificacion_maestra.csv`) con 73+ comparaciones individuales contra el boletín, cada una marcada como ✅/⚠️/❌ con su diferencia exacta. **Úselo como plantilla** para validar futuros boletines: solo cambie las cifras de referencia y el período.

**Uso en Colab:**
```python
# Celda 1: montar drive e instalar
from google.colab import drive
drive.mount('/content/drive')
!pip install geih-analisis --upgrade

# Celda 2..N: el resto del notebook ya ejecutable
```

### Otros notebooks que vienen en el repositorio

| Notebook | Para qué sirve |
|---|---|
| `01_consolidacion_anual.ipynb` | Pipeline de consolidación de los 12 ZIP mensuales del DANE a Parquet único. Incluye `verificar_estructura()` y diagnóstico de calidad. |
| `02_indicadores_basicos.ipynb` | Cálculo de TD/TGP/TO nacional y por departamento. Es el "Hello World" del paquete. |
| `03_analisis_dpto_rama.ipynb` | Uso de `OcupadosDptoRama` para producir el Excel multi-hoja del entregable principal (Departamento × CIIU 2d/4d con CV). |
| `04_brecha_genero.ipynb` | Brecha salarial controlada por nivel educativo y experiencia. |

> Todos los notebooks están en la carpeta `notebooks/` del repositorio. Si va a contribuir, **siempre añada un notebook de ejemplo** que muestre la nueva funcionalidad — es el mejor seguro contra el bit-rot de la documentación.

### Recomendación de flujo para usuarios nuevos

1. **Descargar microdatos GEIH** del año más reciente del portal DANE.
2. **Ejecutar `01_consolidacion_anual.ipynb`** para construir el Parquet base. Verificar que `cons.verificar_estructura()` reporta los 12 meses OK.
3. **Ejecutar `Verificacion_GEIH_2025_vs_Boletin_DANE_v3.ipynb`** (ajustando el año si necesario). Si llega al final con ≥95% ✅, su consolidado es confiable.
4. **Solo entonces** empezar a calcular indicadores nuevos para sus reportes. Validar siempre el resultado contra alguna cifra publicada por el DANE.

---

## 16. FAQ

**¿Tengo que descomprimir los ZIP del DANE?**
No. Desde la v0.1.5 el paquete lee directamente desde `.zip` a RAM. Coloca los ZIP en `data/` con el nombre `Enero 2025.zip`, etc.

**¿Qué pasa si ya tenía la estructura vieja con carpetas `CSV/`?**
Sigue funcionando — el consolidador la reconoce como fallback. Pero los nuevos usuarios deberían usar ZIP directamente.

**¿Qué es la GEIH?**
La Gran Encuesta Integrada de Hogares del DANE. Encuesta mensual con más de 250 000 hogares al año. Es la fuente oficial de las tasas de desempleo y empleo de Colombia.

**¿Qué es el SMMLV?**
El Salario Mínimo Mensual Legal Vigente. El paquete lo usa para expresar ingresos en múltiplos comprensibles (ej. "2,3× SMMLV"). Se fija por decreto cada diciembre.

**¿Por qué la primera consolidación tarda ~5 minutos?**
Está leyendo y uniendo ~96 archivos CSV (8 módulos × 12 meses) con ~5 M filas × ~515 columnas, dentro de los ZIP. El resultado se guarda en Parquet: las siguientes veces carga en segundos.

**¿Y si Colab se desconecta?**
`consolidar(checkpoint=True)` guarda el avance mes a mes y retoma automáticamente.

**¿Puedo analizar un solo mes?**
Sí: `ConfigGEIH(anio=2026, n_meses=1)`. Solo necesitas `data/Enero 2026.zip`.

**¿Puedo agregar un mes nuevo sin reconsolidar?**
Sí: `ConsolidadorGEIH.append_mes()` añade un mes al Parquet existente.

**¿Los datos tienen costo?** No. Son públicos y gratuitos en [microdatos.dane.gov.co](https://microdatos.dane.gov.co) sin registro.

**¿Funciona con años anteriores (2022–2024)?** Sí, desde 2022 (Marco Muestral 2018).

**¿Los 33 departamentos están incluidos?** Sí, los 32 + Bogotá D.C. Para departamentos pequeños (Amazonía, Orinoquía), el paquete advierte automáticamente cuando la muestra es insuficiente.

**¿Hay un dashboard visual?**
Sí. `ejecutar_dashboard(ruta_base="data")` lanza una interfaz Streamlit con filtros y gráficos básicos sobre los Parquet consolidados. Requiere `pip install "geih-analisis[dashboard]"`.

**¿Puedo enriquecer los códigos CIIU y DIVIPOLA con descripciones legibles?**
Sí, con `MergeCorrelativas`. Agrega `DESCRIPCION_CIIU` y los nombres de departamento/municipio a partir de archivos Excel de correlativas (§12.bis).

**¿Puedo diagnosticar la calidad de la base antes de analizarla?**
Sí, con `DiagnosticoCalidad`: reporta valores faltantes, ceros sospechosos, tipos incorrectos y columnas duplicadas.

**¿Puedo agregar variables sin modificar el paquete?**
Sí: `prep.preparar_base(geih, columnas_extra=["P6870", "P7310", ...])`.

---

## 17. Cómo citar

```bibtex
@software{forero2026geih,
  author  = {Forero Herrera, Néstor Enrique},
  title   = {geih-analisis: Paquete Python para análisis de microdatos GEIH},
  year    = {2026},
  version = {0.1.5},
  url     = {https://github.com/enriqueforero/geih-analisis},
  note    = {Datos fuente: Gran Encuesta Integrada de Hogares — DANE, Colombia}
}
```

> Forero Herrera, N. E. (2026). *geih-analisis* (v0.1.5) [Software]. https://github.com/enriqueforero/geih-analisis

---

## 18. Licencia y metodología

**MIT** — Néstor Enrique Forero Herrera · Colombia · 2026

Los datos de la GEIH son propiedad del **DANE** (Departamento Administrativo Nacional de Estadística). Este paquete es una herramienta independiente sin afiliación oficial.

**Metodología de desarrollo.** La arquitectura, la lógica de negocio y los requerimientos son de autoría humana; el autor asume responsabilidad total del código publicado. Se utilizaron modelos de IA generativa (Claude y Gemini) como asistencia técnica para código boilerplate, optimización y refactorización. Ningún bloque asistido por IA se integró sin revisión crítica y validación funcional.

**Agradecimientos.** El diseño de esta librería se inspiró en notebooks previos compartidos por colegas, cuyo aporte se reconoce explícitamente:

- **[Lina María Castro](https://co.linkedin.com/in/lina-maria-castro)** compartió notebooks propios sobre **consolidación multi-módulo de la GEIH** y sobre **análisis por municipios**, que sirvieron como referencia metodológica inicial para el `ConsolidadorGEIH` y para `AnalisisOcupadosCiudad`. Aunque la implementación final reescribió ambos módulos desde cero, el enfoque original de Lina fue el punto de partida conceptual.
- **[Nicolás Rivera](https://co.linkedin.com/in/nicol%C3%A1s-rivera-garz%C3%B3n-7a8b23201)** extendió el trabajo anterior al incorporar mejoras de programación en los notebooks y **validó los cálculos de ocupados por municipio × rama de actividad económica**, contrastando cifras contra los boletines oficiales del DANE.

Ambos aportes son anteriores al paquete y se reconocen como contribuciones intelectuales al proyecto.
