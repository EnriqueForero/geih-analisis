# geih-analisis

[![PyPI version](https://badge.fury.io/py/geih-analisis.svg)](https://pypi.org/project/geih-analisis/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-71%20passed-brightgreen.svg)]()
[![AI Assisted](https://img.shields.io/badge/AI%20Assisted-Claude%20%7C%20Gemini-blue)]()

**Paquete Python para analizar los microdatos de la Gran Encuesta Integrada de Hogares (GEIH) del DANE — Colombia.**

Convierte los archivos CSV crudos del DANE en indicadores del mercado laboral listos para reportar: desempleo, salarios, brecha de género, formalidad, educación y más — con pocas líneas de código.

---

> **English summary:** Python package for analyzing Colombia's GEIH household survey microdata (DANE). Computes labor market indicators (unemployment, wages, gender gap, formality) from raw CSV files. Supports 2022–present, 70+ analytical classes, Google Colab optimized. `pip install geih-analisis` → `from geih import ConfigGEIH`.

---

## Tabla de contenidos

1. [¿Para quién es este paquete?](#1-para-quién-es-este-paquete)
2. [Instalación](#2-instalación)
3. [Inicio rápido](#3-inicio-rápido)
4. [Paso 0 — Descargar los datos del DANE](#4-paso-0--descargar-los-datos-del-dane)
5. [Flujo de trabajo completo](#5-flujo-de-trabajo-completo)
6. [Análisis disponibles](#6-análisis-disponibles)
7. [Ejemplos de análisis](#7-ejemplos-de-análisis)
8. [Análisis departamental](#8-análisis-departamental)
9. [Análisis de tierras agropecuarias)](#9-análisis-de-tierras-agropecuarias)
10. [Configuración externa)](#10-configuración-externa)
11. [Precisión muestral)](#11-precisión-muestral)
12. [Agregar variables sin modificar el código](#12-agregar-variables-sin-modificar-el-código)
13. [Agregar un año nuevo](#13-agregar-un-año-nuevo)
14. [FAQ — Preguntas frecuentes](#14-faq--preguntas-frecuentes)
15. [Cómo citar](#15-cómo-citar)
16. [Licencia](#16-licencia)
17. [Metodología de desarrollo](#17-metodología-de-desarrollo)
18. [Créditos y agradecimientos](#18-créditos-y-agradecimientos)

---

## 1. ¿Para quién es este paquete?

Este paquete es para ti si:

- Eres **economista, analista laboral o investigador** y necesitas calcular tasas de desempleo, ingresos medianos o brechas salariales a partir de la GEIH.
- Eres **estudiante** y quieres explorar el mercado laboral colombiano sin procesar manualmente millones de filas.
- Trabajas en **regiones** y necesitas indicadores departamentales semestrales o trimestrales con evaluación de confiabilidad estadística.
- Investigas **política pública agraria** y quieres cruzar ingresos con tenencia de tierra.
- Tienes conocimiento de **Python básico** como saber instalar paquetes y ejecutar celdas es suficiente para empezar.
- Usas **Google Colab** y no quieres instalar nada en tu computador.

**No necesitas:** experiencia avanzada en programación, conocimiento de la estructura interna de la GEIH, ni saber qué es un factor de expansión. El paquete maneja todo eso por ti.

---

## 2. Instalación

### Opción A — pip (recomendado para uso local o Colab con pip)

```bash
pip install geih-analisis
```

Con gráficos interactivos y dashboard visual:

```bash
pip install "geih-analisis[all]"
```

### Opción B — Google Colab (sin instalación, desde Drive)

```python
from google.colab import drive
drive.mount('/content/drive')

import sys
sys.path.insert(0, '/content/drive/MyDrive/GEIH')  # ← ajustar a tu ruta

from geih import __version__
print(f"geih v{__version__} listo")
```

### Opción C — Última versión en desarrollo (desde GitHub)

```bash
pip install git+https://github.com/enriqueforero/geih-analisis.git
```

### Requisitos del sistema

| Dependencia | Versión mínima |
|---|---|
| Python | 3.9+ |
| pandas | 1.5+ |
| numpy | 1.21+ |
| pyarrow | 10.0+ |
| scipy | 1.7+ |
| openpyxl | 3.0+ |

---

## 3. Inicio rápido

### Ultra-rápido — 3 líneas (si ya tienes los datos consolidados)

```python
from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

config = ConfigGEIH(anio=2025, n_meses=12)
geih   = ConsolidadorGEIH.cargar('GEIH_2025_Consolidado.parquet')
df     = PreparadorGEIH(config=config).preparar_base(geih)
r      = IndicadoresLaborales(config=config).calcular(df)
print(f"Desempleo: {r['TD_%']:.1f}%  |  Participación: {r['TGP_%']:.1f}%  |  Ocupación: {r['TO_%']:.1f}%")
```

### Completo — desde los CSV hasta los resultados

```python
from geih import (
    ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH,
    IndicadoresLaborales, AnalisisSalarios, BrechaGenero, Exportador
)
import os

# ── 1. Configurar ─────────────────────────────────────────────────────
RUTA   = '/content/drive/MyDrive/GEIH'   # ← ajustar a tu ruta en Drive
config = ConfigGEIH(anio=2025, n_meses=12)
config.resumen()   # muestra SMMLV, período y carpetas esperadas

# ── 2. Consolidar los CSV del DANE ────────────────────────────────────
# Primera vez: ~5 minutos. Siguientes veces: instantáneo desde el archivo .Parquet.
PARQUET = f'{RUTA}/GEIH_{config.anio}_Consolidado.parquet'

if os.path.exists(PARQUET):
    geih = ConsolidadorGEIH.cargar(PARQUET)
else:
    cons = ConsolidadorGEIH(ruta_base=RUTA, config=config, incluir_area=True)
    cons.verificar_estructura()            # verifica que estén los 96 archivos CSV
    geih = cons.consolidar(checkpoint=True)  # retoma automáticamente si Colab se cae
    cons.exportar(geih)

# ── 3. Preparar datos ─────────────────────────────────────────────────
prep = PreparadorGEIH(config=config)
df   = prep.preparar_base(geih)
df   = prep.agregar_variables_derivadas(df)

# ── 4. Calcular y exportar ────────────────────────────────────────────
ind     = IndicadoresLaborales(config=config)
r       = ind.calcular(df)
ind.sanity_check(r, f"Anual {config.anio}")   # valida contra cifras DANE

exp     = Exportador(ruta_base=RUTA, config=config)
td_dpto = ind.por_departamento(df)
exp.guardar_tabla(td_dpto, f'desempleo_departamentos_{config.anio}')

print(f"✅  TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
```

---

## 4. Paso 0 — Descargar los datos del DANE

> ⚠️ **Este paquete no incluye los datos.** Los microdatos de la GEIH son públicos y gratuitos, pero debes descargarlos del portal oficial del DANE y organizarlos en la estructura de carpetas que el paquete espera.

### 4.1 Dónde descargar

**Portal oficial de microdatos del DANE:**
🔗 [https://microdatos.dane.gov.co](https://microdatos.dane.gov.co/index.php/catalog/central/about)

### 4.2 Paso a paso detallado

**Paso 1 — Ir al portal y buscar la encuesta**

1. Abrir [microdatos.dane.gov.co](https://microdatos.dane.gov.co)
2. En el buscador escribir: `Gran Encuesta Integrada de Hogares`
3. Seleccionar el año que necesitas (ej: `GEIH 2025`)
4. Hacer clic en **"Obtener microdatos"**

**Paso 2 — Descargar los archivos en formato .zip para cada mes**

La GEIH se publica en **8 archivos CSV por mes** que están todos en un archivo de formato .zip. Debes descargar los meses a analizar:

| # | Módulo | Nombre del archivo |
|---|---|---|
| 1 | Características generales | `Características generales, seguridad social en salud y educación.CSV` |
| 2 | Datos del hogar | `Datos del hogar y la vivienda.CSV` |
| 3 | Fuerza de trabajo | `Fuerza de trabajo.CSV` |
| 4 | Ocupados | `Ocupados.CSV` |
| 5 | No ocupados | `No ocupados.CSV` |
| 6 | Otras formas de trabajo | `Otras formas de trabajo.CSV` |
| 7 | Migración | `Migración.CSV` |
| 8 | Otros ingresos | `Otros ingresos e impuestos.CSV` |

**Paso 3 — Organizar los archivos en carpetas**

Crea una carpeta raíz (por ejemplo `GEIH`) y dentro organiza los archivos exactamente así:

```
GEIH/                                ← carpeta raíz (tu variable RUTA)
│
├── Enero 2025/
│   └── CSV/
│       ├── Características generales, seguridad social en salud y educación.CSV
│       ├── Datos del hogar y la vivienda.CSV
│       ├── Fuerza de trabajo.CSV
│       ├── Ocupados.CSV
│       ├── No ocupados.CSV
│       ├── Otras formas de trabajo.CSV
│       ├── Migración.CSV
│       └── Otros ingresos e impuestos.CSV
│
├── Febrero 2025/
│   └── CSV/
│       └── (mismos 8 archivos)
│
├── Marzo 2025/
│   └── CSV/
│       └── (mismos 8 archivos)
│
│   ... (una carpeta por cada mes)
│
└── Diciembre 2025/
    └── CSV/
        └── (mismos 8 archivos)
```

> **Importante — nombres exactos de carpetas:** deben ser `Enero 2025`, `Febrero 2025`, `Marzo 2025`, `Abril 2025`, `Mayo 2025`, `Junio 2025`, `Julio 2025`, `Agosto 2025`, `Septiembre 2025`, `Octubre 2025`, `Noviembre 2025`, `Diciembre 2025`. Con mayúscula inicial, espacio y año. El paquete busca estas carpetas con esa nomenclatura exacta. Las otras carpetas que genera el DANE como DAT y SAV, contienen formatos para programas estadísticos especializados, esos no se usan en esta librería. Sólo trabaje con los archivos en formato CSV. 

**Paso 5 — Verificar que todo está en orden**

Antes de consolidar, verifica que los archivos están correctamente ubicados:

```python
from geih import ConsolidadorGEIH, ConfigGEIH

config = ConfigGEIH(anio=2025, n_meses=12)
cons   = ConsolidadorGEIH(ruta_base='/tu/ruta/GEIH', config=config)
cons.verificar_estructura()
# ✅ Enero 2025: 8 archivos — OK
# ✅ Febrero 2025: 8 archivos — OK
# ✅ Marzo 2025: 8 archivos — OK
# ...
```

Si falta algún archivo, el verificador te indica exactamente cuál.

### 4.3 Descarga automática con `DescargadorDANE` (opcional)

Si prefieres que el paquete organice los ZIPs que descargaste manualmente:

```python
from geih import DescargadorDANE, ConfigGEIH

desc = DescargadorDANE(
    config=ConfigGEIH(anio=2025, n_meses=12),
    ruta_destino='/tu/ruta/GEIH',
)
# Si tienes los ZIPs descargados manualmente:
desc.organizar_zips('/ruta/donde/guardaste/los/zips')
# Verifica la estructura resultante:
desc.verificar()
```

---

## 5. Flujo de trabajo completo

```
Archivos CSV del DANE (8 módulos × N meses)
          ↓
  ConsolidadorGEIH     → une los módulos, concatena los meses
          ↓               guarda GEIH_2025_Consolidado.parquet
  PreparadorGEIH       → calcula FEX_ADJ, mapea ramas y departamentos
          ↓               agrega variables derivadas (INGLABO_SML, etc.)
  Clases de análisis   → TD, salarios, brecha, Gini, ICE, ICI, ITAT...
          ↓
  Exportador           → resultados_geih_2025/
                           ├── graficas/   (PNG)
                           ├── tablas/     (CSV)
                           └── excel/      (XLSX multi-hoja)
```

### El único parámetro que cambia: `ConfigGEIH`

```python
from geih import ConfigGEIH

# Año completo
config = ConfigGEIH(anio=2025, n_meses=12)

# Primer trimestre de 2026
config = ConfigGEIH(anio=2026, n_meses=3)

# Solo enero de 2026
config = ConfigGEIH(anio=2026, n_meses=1)

# Primer semestre (nuevo en v5.1)
config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[1,2,3,4,5,6])
```

`ConfigGEIH` selecciona automáticamente el SMMLV correcto, genera la lista de carpetas esperadas y controla cómo se calcula el factor de expansión. Cambiar `anio` y `n_meses` es todo lo que necesitas.

---

## 6. Análisis disponibles

### Indicadores fundamentales del mercado laboral

| Clase | Qué produce |
|---|---|
| `IndicadoresLaborales` | TD, TGP, TO — nacionales y por departamento |
| `DistribucionIngresos` | Distribución de ingresos por rangos de SMMLV |
| `AnalisisSalarios` | Mediana, media, percentiles por rama de actividad y edad |
| `BrechaGenero` | Diferencia salarial hombres/mujeres por nivel educativo |
| `IndicesCompuestos` | Coeficiente de Gini del ingreso laboral |
| `AnalisisRamaSexo` | Composición del empleo por industria y sexo |

### Análisis avanzados

| Clase | Qué produce |
|---|---|
| `CalidadEmpleo` | ICE: índice que combina pensión, salud, horas y salario |
| `CompetitividadLaboral` | ICI: competitividad laboral por departamento |
| `VulnerabilidadLaboral` | IVI: vulnerabilidad por rama de actividad |
| `MapaTalento` | ITAT: oferta laboral, costo y calidad por departamento |
| `EcuacionMincer` | Retorno salarial a cada año adicional de educación |
| `Estacionalidad` | Variación mensual de TD, TGP y TO durante el año |
| `FuerzaLaboralJoven` | Indicadores específicos para jóvenes de 15 a 28 años |
| `CostoLaboral` | Costo total incluyendo prestaciones sociales (~54% sobre salario) |
| `FormalidadSectorial` | ICF: formalidad del empleo por sector económico |

### Poblaciones especiales

- `AnalisisCampesino` — trabajadores que se autodeclaran campesinos
- `AnalisisDiscapacidad` — personas con discapacidad (escala Washington ONU, 8 dimensiones)
- `AnalisisMigracion` — migración interna e internacional
- `AnalisisSobrecalificacion` — universitarios ocupados en empleos que no requieren ese nivel
- `AnalisisContractual` — tipo de contrato: escrito indefinido, escrito fijo, verbal, sin contrato
- `AnalisisAutonomia` — trabajadores formalmente independientes pero en realidad dependientes
- `DuracionDesempleo` — semanas buscando empleo (friccional, cíclico, estructural, largo plazo)
- `DashboardSectoresProColombia` — 7 sectores estratégicos de actividad económica

### Nuevos en v0.1.3

| Clase | Qué produce |
|---|---|
| `AnalisisDepartamental` | **Reporte integral** por departamento con precisión muestral |
| `AnalisisTierraAgropecuario` | Distribución salarial × tenencia de tierra |

### 32 ciudades y áreas metropolitanas

```python
from geih import AnalisisOcupadosCiudad

area   = AnalisisOcupadosCiudad(config=config)
tablas = area.calcular(df)                  # 6 tablas: nacional, agrupación DANE, ciudad/AM
area.imprimir(tablas)
area.exportar_excel(tablas, 'CIIU_Area_2025.xlsx')
```

### Comparación entre años

```python
from geih import ComparadorMultiAnio, ConfigGEIH

comp = ComparadorMultiAnio()
comp.agregar_anio(2025, 'GEIH_2025_M01.parquet', ConfigGEIH(anio=2025, n_meses=1))
comp.agregar_anio(2026, 'GEIH_2026_M01.parquet', ConfigGEIH(anio=2026, n_meses=1))

comp.comparar_indicadores()    # TD / TGP / TO con variación anual
comp.evolucion_ingresos()      # mediana salarial por año en COP y SMMLV
comp.comparar_departamentos()  # TD por departamento × año
comp.comparar_brecha_genero()  # brecha salarial H/M por año
```

---

## 7. Ejemplos de análisis

### Tasa de desempleo nacional y por departamento

```python
from geih import IndicadoresLaborales

ind = IndicadoresLaborales(config=config)

# Nacional
r = ind.calcular(df)
print(f"TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
# → TD=9.8%  TGP=63.4%  TO=57.2%

# Por departamento
td_dpto = ind.por_departamento(df)
print(td_dpto[['Departamento', 'TD_%', 'Ocupados_M']].head(10).to_string(index=False))
```

### Salarios medianos por industria y nivel educativo

```python
from geih import AnalisisSalarios

# Mediana salarial por rama de actividad
salarios = AnalisisSalarios(config=config).por_rama(df)
print(salarios[['Mediana', 'Media', 'Mediana_SMMLV']].head(10))

# Por nivel educativo (diferenciando Especialización, Maestría y Doctorado)
from geih.utils import EstadisticasPonderadas as EP

niveles = {10: 'Universitaria', 11: 'Especialización', 12: 'Maestría', 13: 'Doctorado'}
df_edu  = df[(df['OCI'] == 1) & (df['INGLABO'] > 0)].copy()
df_edu['NIVEL'] = df_edu['P3042'].map(niveles)

for nivel in ['Universitaria', 'Especialización', 'Maestría', 'Doctorado']:
    m   = df_edu['NIVEL'] == nivel
    med = EP.mediana(df_edu.loc[m, 'INGLABO'], df_edu.loc[m, 'FEX_ADJ'])
    print(f"{nivel:20s}: ${med:>12,.0f}  ({med / config.smmlv:.1f}× SMMLV)")
# Universitaria       :   $2,100,000  (1.5× SMMLV)
# Especialización     :   $3,800,000  (2.7× SMMLV)
# Maestría            :   $5,200,000  (3.7× SMMLV)
# Doctorado           :   $7,500,000  (5.3× SMMLV)
```

### Brecha salarial de género

```python
from geih import BrechaGenero

brecha = BrechaGenero().calcular(df)
print(brecha)
#               Hombres    Mujeres  Brecha_%
# Media           1.35       1.18     -12.6
# Universitaria   2.10       1.95      -7.1
# Maestría        4.82       4.41      -8.5
```

### Comparación enero 2025 vs enero 2026

```python
from geih import ComparadorMultiAnio, ConfigGEIH

comp = ComparadorMultiAnio()
comp.agregar_anio(2025, 'GEIH_2025_M01.parquet', ConfigGEIH(anio=2025, n_meses=1))
comp.agregar_anio(2026, 'GEIH_2026_M01.parquet', ConfigGEIH(anio=2026, n_meses=1))

df_ind = comp.comparar_indicadores()
# ANIO   TD_%   Δ_TD_%   TGP_%   TO_%   Ocupados_M
# 2025   10.8      —      63.1   56.3      22.5
# 2026   11.4    +0.6     62.8   55.7      22.8
```

### Dashboard interactivo (sin código)

```python
from geih import ejecutar_dashboard

ejecutar_dashboard(ruta_base='/tu/ruta/GEIH')
# Abre un dashboard en tu navegador con filtros y gráficos
# Requiere: pip install "geih-analisis[dashboard]"
```

---

## 8. Análisis departamental

Consolida indicadores de 6+ clases en un solo reporte departamental con evaluación de precisión estadística. Soporta análisis semestral.

### Análisis anual

```python
from geih import AnalisisDepartamental, ConfigGEIH, PreparadorGEIH

config = ConfigGEIH(anio=2025, n_meses=12)
prep = PreparadorGEIH(config=config)
df = prep.preparar_base(geih)
df = prep.agregar_variables_derivadas(df)

ad = AnalisisDepartamental(config=config)
reporte = ad.calcular(df)
ad.exportar_excel(reporte, "departamentos_2025.xlsx")
```

### Análisis semestral (para regiones)

```python
# Primer semestre
config_s1 = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[1,2,3,4,5,6])
df_s1 = PreparadorGEIH(config=config_s1).preparar_base(geih)
df_s1 = PreparadorGEIH(config=config_s1).agregar_variables_derivadas(df_s1)
reporte_s1 = AnalisisDepartamental(config=config_s1).calcular(df_s1)

# Segundo semestre
config_s2 = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[7,8,9,10,11,12])
df_s2 = PreparadorGEIH(config=config_s2).preparar_base(geih)
df_s2 = PreparadorGEIH(config=config_s2).agregar_variables_derivadas(df_s2)
reporte_s2 = AnalisisDepartamental(config=config_s2).calcular(df_s2)
```

### 33 departamentos (completo)

La v5.1 incluye los 32 departamentos + Bogotá D.C. — antes faltaban Arauca, Casanare, Putumayo, San Andrés, Amazonas, Guainía, Guaviare, Vaupés y Vichada. Cada departamento lleva su evaluación de precisión muestral.

### Indicadores por departamento

Cada fila del reporte incluye: TD, TGP, TO, mediana salarial, formalidad (cotización pensión), CV de TD, intervalo de confianza al 95%, clasificación de precisión DANE, y advertencia de muestra insuficiente cuando aplica.

---

## 9. Análisis de tierras agropecuarias

Explota las variables P3064 (tenencia de tierra), P3064S1 (renta estimada) y P3056 (tipo de actividad) para análisis de política pública agraria.

```python
from geih import AnalisisTierraAgropecuario

tierra = AnalisisTierraAgropecuario(config=config)

# Brecha de ingresos: ¿ser propietario saca de la pobreza?
brecha = tierra.brecha_ingresos(df)

# Costo de oportunidad: ¿gana más trabajando o arrendando?
costo = tierra.costo_oportunidad(df)

# Inequidad de género en propiedad de la tierra
genero = tierra.por_genero(df)

# Por departamento con evaluación de confiabilidad
dept = tierra.por_departamento(df)

# Reporte completo
reporte = tierra.reporte_completo(df)
tierra.exportar_excel(reporte, "tierras_2025.xlsx")
```

### Análisis disponibles

1. **Brecha de ingresos Propietario vs. No propietario**: ¿La propiedad de la tierra correlaciona con mayores ingresos?
2. **Costo de oportunidad**: Ingreso laboral vs. renta estimada de la tierra (P3064S1). ¿El campesino gana más que si arrendara?
3. **Distribución de la tierra por género**: Inequidad en titularidad por sexo y departamento.
4. **Formalidad agropecuaria**: Cotización a pensión por tenencia.
5. **Por subcategoría CIIU**: Agricultura (01) vs. Silvicultura (02) vs. Pesca (03) con detalle a 4 dígitos.
6. **Por departamento**: Con evaluación de precisión muestral para cada celda.

### Nota muestral

P3064 solo aplica a trabajadores independientes del sector agropecuario. A nivel nacional hay suficiente muestra, pero al cruzar departamento + subcategoría + tenencia, las celdas pueden tener pocas observaciones. **Cada resultado lleva su indicador de confiabilidad.**

---

## 10. Configuración externa

### El problema

Cada vez que cambia el salario mínimo (decreto de diciembre), o cuando el DANE publica el boletín anual, había que modificar `config.py` y lanzar un nuevo release a PyPI. Para un dato que cambia una vez al año, eso es excesivo.

### La solución: `geih_config.json`

Ahora el paquete busca un archivo `geih_config.json` que sobreescribe los valores internos. El usuario lo coloca junto a sus datos y actualiza sin esperar un release:

```json
{
  "smmlv_por_anio": {
    "2027": 1900000
  },
  "ref_dane": {
    "2026": {
      "td_anual_pct": 9.2,
      "tgp_anual_pct": 64.0,
      "to_anual_pct": 58.0,
      "pea_anual_m": 26.5,
      "ocupados_anual_m": 24.0,
      "desocupados_anual_m": 2.5
    }
  },
  "muestreo": {
    "deff_default": 2.5,
    "cv_preciso_pct": 7.0,
    "cv_aceptable_pct": 15.0
  }
}
```

### Dónde colocar el archivo

El paquete busca en este orden:

1. Ruta explícita: `cargar_config_externa("/mi/ruta/geih_config.json")`
2. Variable de entorno: `GEIH_CONFIG_PATH`
3. Directorio de trabajo: `./geih_config.json`
4. Home del usuario: `~/.geih/geih_config.json`

Si no encuentra ningún archivo, usa los valores hardcodeados del paquete (sin error).

### Verificar configuración activa

```python
config = ConfigGEIH(anio=2025, n_meses=12)
config.resumen()
# Muestra: año, meses, SMMLV, si hay config externa cargada, etc.
```

---

## 11. Precisión muestral

### El problema

Sin errores muestrales, las desagregaciones finas producen cifras sin contexto de confiabilidad. Un usuario podría reportar "TD de Vaupés = 25%" sin saber que el CV es del 40%.

### La solución: módulo `geih.muestreo`

Toda estimación puede evaluarse con el módulo de muestreo:

```python
from geih import evaluar_proporcion, ConfigMuestreo

# Evaluar la precisión de una tasa de desempleo
precision = evaluar_proporcion(
    proporcion=0.089,        # TD = 8.9%
    n_registros=50000,       # registros en la muestra
    n_expandido=26_000_000,  # personas expandidas
    dominio="Nacional",
)
print(precision.resumen())
# Nacional  Est=8.90  EE=0.20  CV=2.3%  IC=[8.51, 9.29]  n=50,000  N̂=26.000M  ✅ Precisión alta
```

### Clasificación DANE

| CV | Clasificación | Uso |
|---|---|---|
| < 7% | ✅ Precisión alta | Publicable |
| 7–15% | ⚠️ Precisión aceptable | Usar con precaución |
| 15–20% | ⚠️⚠️ Precisión baja | Solo referencia |
| > 20% | ❌ No confiable | No publicar |

Las clases `AnalisisDepartamental` y `AnalisisTierraAgropecuario` integran automáticamente esta evaluación en cada fila de sus resultados.

---

## 12. Agregar variables sin modificar el código

El parámetro `columnas_extra` permite agregar cualquier variable de la GEIH desde el notebook, sin tocar el código fuente del paquete:

```python
prep = PreparadorGEIH(config=config)

# Agregar variables que no están en los defaults
df = prep.preparar_base(
    geih,
    columnas_extra=["P6870", "P6880", "P7310", "MI_VARIABLE_CUSTOM"]
)
```

Las columnas que no existan en la base se ignoran silenciosamente. Esto sigue el Principio Abierto/Cerrado de SOLID: abierto a extensión, cerrado a modificación.

---

## 13. Agregar un año nuevo

### Opción A — Sin tocar el código (recomendado)

Coloque un archivo `geih_config.json` junto a sus datos:

```json
{
  "smmlv_por_anio": {
    "2027": 1900000
  }
}
```

El paquete lo detecta automáticamente. No requiere un nuevo release a PyPI.

### Opción B — En el código fuente

Cuando el DANE publique los datos de un año nuevo, solo necesitas 2 cambios en `config.py`:

```python
# 1. Agregar el SMMLV del año nuevo (publicado por decreto en diciembre)
SMMLV_POR_ANIO = {
    2025: 1_423_500,
    2026: 1_750_905,
    2027: X_XXX_XXX,   # ← agregar aquí
}

# 2. Agregar la referencia DANE cuando publiquen el boletín oficial
REF_DANE = {
    2027: ReferenciaDane(td_anual_pct=..., tgp_anual_pct=..., to_anual_pct=...),
}
```

Si no agregas la referencia DANE, el paquete muestra un aviso pero los análisis siguen funcionando normalmente.

---

## 14. FAQ — Preguntas frecuentes

**¿Qué es la GEIH?**
La Gran Encuesta Integrada de Hogares es la encuesta mensual del DANE que mide el mercado laboral en Colombia. Encuesta a más de 250.000 hogares al año y es la fuente oficial de las tasas de desempleo y empleo del país.

**¿Qué es el SMMLV y por qué importa?**
El Salario Mínimo Mensual Legal Vigente es la referencia salarial de Colombia. El paquete lo usa para expresar ingresos en múltiplos comprensibles (ej: "gana 2,3× SMMLV"). Cada año tiene su propio valor fijado por decreto.

**¿Qué es el factor de expansión (FEX)?**
La GEIH encuesta una muestra, no a toda la población. El factor de expansión indica cuántas personas reales representa cada encuestado. El paquete lo calcula automáticamente tomando el factor de expansión que está en la base y con `ConfigGEIH(n_meses=...)` — no necesitas hacer nada.

**¿Por qué la primera consolidación tarda ~5 minutos?**
Está leyendo y uniendo ~96 archivos CSV (8 módulos × 12 meses) con cerca de 817.550 filas × 515 columnas. El resultado se guarda en formato Parquet que es un formato eficiente para gran volumen de datos en velocidad y espacio en disco: las siguientes veces carga en segundos.

**¿Qué pasa si Colab se desconecta durante la consolidación?**
El parámetro `checkpoint=True` guarda el avance después de cada mes procesado. Al volver a ejecutar, retoma automáticamente desde el último mes completado.

**¿Puedo analizar solo enero 2026 si aún no tengo todo el año?**
Sí. Usa `ConfigGEIH(anio=2026, n_meses=1)`. El paquete espera solo la carpeta `Enero 2026/CSV/` y calcula los factores de expansión correctamente para ese mes.

**¿Puedo comparar 2025 vs 2026 si solo tengo enero 2026?**
Sí, usando `n_meses=1` para ambos años en el `ComparadorMultiAnio`. Esto garantiza que los factores de expansión sean equivalentes entre años.

**¿Los datos del DANE tienen algún costo?**
No. Son públicos y gratuitos en [microdatos.dane.gov.co](https://microdatos.dane.gov.co) y no requieren registro o autenticación.

**¿Funciona con datos de años anteriores (2022, 2023, 2024)?**
Sí. El paquete soporta la GEIH desde 2022 (Marco Muestral 2018 del DANE) hasta el presente con `ConfigGEIH(anio=2022, ...)`.

**¿Qué significa el error "PEA > 40M"?**
Indica que el factor de expansión no se está calculando correctamente. Asegúrate de que `n_meses` en `ConfigGEIH` coincide con el número de meses reales en tu archivo Parquet:

```python
# Si el Parquet tiene 12 meses → n_meses=12 → FEX ÷ 12
config = ConfigGEIH(anio=2025, n_meses=12)

# Si el Parquet tiene solo enero → n_meses=1 → FEX ÷ 1
config = ConfigGEIH(anio=2026, n_meses=1)
```

**¿Se pueden hacer análisis departamentales semestrales?**
Sí, desde la v5.1. Use `meses_rango` en `ConfigGEIH` para filtrar meses. Cada departamento lleva su evaluación de precisión muestral. Para departamentos pequeños (Amazonía, Orinoquía), la muestra semestral puede ser insuficiente — el paquete lo advierte automáticamente.

**¿Se puede analizar la distribución salarial por tenencia de tierra?**
Sí, con `AnalisisTierraAgropecuario`. La GEIH incluye P3064 (propietario de la tierra) y P3064S1 (renta estimada) para trabajadores independientes del sector agropecuario. Cada resultado lleva su indicador de confiabilidad.

**¿Puedo agregar variables sin modificar el paquete?**
Sí. Use `columnas_extra` en `preparar_base()`. No necesita hacer fork ni modificar código fuente.

**¿Necesito lanzar un nuevo release para actualizar el SMMLV?**
No. Use `geih_config.json` para actualizar SMMLV y referencias DANE externamente.

**¿Los 33 departamentos están incluidos?**
Sí, desde la v5.1. Los departamentos de Amazonía/Orinoquía (Arauca, Casanare, Putumayo, Amazonas, Guainía, Guaviare, Vaupés, Vichada) y San Andrés ahora están incluidos. El paquete advierte cuando la muestra es insuficiente para estimaciones confiables.

---

## 15. Cómo citar

Si usas este paquete en un trabajo académico o publicación, puedes citarlo así:

**Formato BibTeX:**

```bibtex
@software{forero2026geih,
  author  = {Forero Herrera, Néstor Enrique},
  title   = {geih-analisis: Paquete Python para análisis de microdatos GEIH},
  year    = {2026},
  version = {0.1.3},
  url     = {https://github.com/enriqueforero/geih-analisis},
  note    = {Datos fuente: Gran Encuesta Integrada de Hogares — DANE, Colombia}
}
```

**Formato texto (APA):**

> Forero Herrera, N. E. (2026). *geih-analisis* (v0.1.3) [Software]. GitHub. https://github.com/enriqueforero/geih-analisis

---

## 16. Licencia

MIT — Néstor Enrique Forero Herrera · Colombia · 2026

Los **datos de la GEIH** son de acceso público y propiedad del DANE (Departamento Administrativo Nacional de Estadística de Colombia). Este paquete es una herramienta de análisis independiente y no tiene afiliación oficial con el DANE ni con ninguna entidad gubernamental.

---

## 17. Metodología de desarrollo

La arquitectura, la lógica de negocio y los requerimientos de este paquete son de autoría humana. El autor asume responsabilidad total sobre la integridad del código publicado.

Se utilizaron modelos de IA generativa (Claude y Gemini) como asistencia técnica para generación de código boilerplate, optimización de consultas y sugerencias de refactorización.

**Validación:** Ningún bloque asistido por IA fue integrado sin revisión crítica, ajuste al contexto del dominio y validación mediante pruebas funcionales.

---

## 18. Créditos y agradecimientos

Este paquete es resultado de un esfuerzo acumulativo que comenzó con trabajo exploratorio y operativo previo dentro de la Gerencia de Inteligencia Comercial (GIC) de ProColombia.

**Lina Castro y Nicolás Rivera** fueron los creadores del análisis pionero de ocupados por CIIU Rev 4 y área geográfica a partir de la GEIH 2023. Su notebook estableció el enfoque metodológico base del proyecto: la carga iterativa mes a mes del módulo de Ocupados, la selección de variables relevantes del módulo (`OCI`, `FEX_C18`, `RAMA4D_R4`, `AREA`, `DPTO`, `INGLABO`, `P6430`, entre otras), la aplicación del factor de expansión anual (`FEX_C18 / 12`) para estimar ocupados reales, y la construcción de tablas pivote desagregadas por agrupación DANE, división CIIU, área geográfica y sus cruces. También diseñaron el esquema de correlativas — DIVIPOLA, CIIU Rev4 y agrupaciones DANE — que permitió enriquecer semánticamente los códigos crudos del DANE. Los resultados fueron exportados a Excel multi-hoja para su uso operativo directo. Entre ambos participaron activamente en la definición del alcance analítico, la revisión de resultados y la validación de los cálculos, asegurando que los indicadores respondieran a las preguntas reales del equipo. Adicionalmente, Lina y Nicolás diseñaron y ejecutaron el proceso de consolidación completa de la GEIH 2025 (12 meses, Enero a Diciembre). Su aporte más técnico fue el desarrollo de la función `unir_modulos_sin_duplicados()`, que resolvió un problema central del proceso: el solapamiento de columnas entre los distintos módulos del DANE al hacer merges entre ellos. Esta función — que filtra las columnas del módulo derecho a las estrictamente nuevas antes del join — es el antecedente directo del `ConsolidadorGEIH` que hoy es el núcleo del paquete. También manejó las claves de cruce diferenciadas por módulo (`['DIRECTORIO', 'SECUENCIA_P', 'ORDEN']` para personas, `['DIRECTORIO', 'SECUENCIA_P']` para hogares) y exploró la integración posterior con las correlativas CIIU y DIVIPOLA.

**Enrique Forero** fue responsable de la arquitectura del sistema, el diseño técnico, la implementación del paquete `geih/`, la suite de pruebas (71 tests), la documentación y la publicación en PyPI. El trabajo de Nicolás y Lina fue la fuente de referencia que orientó las decisiones de diseño: qué variables incluir, cómo manejar los módulos del DANE, qué correlativas enriquecen la base y qué indicadores tienen valor analítico real para el equipo.
