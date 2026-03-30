[![PyPI version](https://badge.fury.io/py/geih-analisis.svg)](https://pypi.org/project/geih-analisis/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# geih_2025

**Paquete modular de Python para análisis de la Gran Encuesta Integrada de Hogares (GEIH) del DANE — Colombia.**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 71 passed](https://img.shields.io/badge/tests-71%20passed-green.svg)]()
[![Version 4.3.0](https://img.shields.io/badge/version-4.3.0-green.svg)]()

---

## ¿Qué hace este paquete?

Transforma los microdatos crudos de la GEIH (8 módulos CSV × 12 meses × ~5 millones de registros) en **indicadores publicables del mercado laboral colombiano**. Incluye 70+ clases que cubren empleo, desempleo, ingresos, formalidad, brechas de género, competitividad departamental, migración, discapacidad y más.

## Compatibilidad con versiones anteriores

Si tienes código con `from geih import ...`, sigue funcionando.
El módulo `geih_2025` actúa como alias que redirige a `geih`.
Recibirás un `DeprecationWarning` recordándote actualizar el import.

```python
# Antes (sigue funcionando, emite DeprecationWarning):
from geih import ConfigGEIH

# Ahora (recomendado):
from geih import ConfigGEIH
```


## Instalación

### En Google Colab (recomendado)

```python
from google.colab import drive
drive.mount('/content/drive')

import sys
sys.path.insert(0, '/content/drive/MyDrive/GEIH')  # ← ajustar a tu ruta

from geih import __version__
print(f"geih v{__version__}")
```

### Local con pip

```bash
git clone https://github.com/enriqueforero/geih-2025.git
cd geih-2025
pip install -e ".[dev]"
```

## Uso rápido (5 líneas)

```python
from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

config = ConfigGEIH(anio=2025, n_meses=12)          # ← cambiar año aquí
geih = ConsolidadorGEIH.cargar('GEIH_2025_Consolidado.parquet')
df = PreparadorGEIH(config=config).preparar_base(geih)
r = IndicadoresLaborales(config=config).calcular(df)
print(f"TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
```

## Características principales

| Característica | Detalle |
|---|---|
| **Multi-año** | `ConfigGEIH(anio=2026, n_meses=3)` — procesa cualquier año sin cambiar código |
| **70+ clases** | TD/TGP/TO, Gini, Mincer, ICE, ICI, ITAT, IVI, 32 ciudades, y más |
| **Checkpointing** | Si Colab se cae en mes 8, re-ejecutar retoma desde mes 9 |
| **Descarga DANE** | `DescargadorDANE` organiza ZIPs del portal de microdatos |
| **Comparativo inter-anual** | `ComparadorMultiAnio` compara TD 2025 vs 2026 |
| **Gráficos Plotly** | 8 gráficos interactivos con tooltips + zoom |
| **Dashboard Streamlit** | Exploración visual sin código para usuarios no-técnicos |
| **71 tests** | pytest + golden set de 1,000 registros con resultados verificables |
| **Logging** | Trazabilidad a archivo con timestamps y niveles |
| **Profiling RAM** | Snapshots de memoria para identificar cuellos de botella |
| **Exportación organizada** | graficas/, tablas/, excel/ + metadata.json |

## Estructura del proyecto

```
geih-analisis/
├── geih/                       ← 19 módulos Python
│   ├── __init__.py                  ← v5.0.0, 70+ clases exportadas
│   ├── config.py                    ← Configuración multi-año centralizada
│   ├── utils.py                     ← Estadísticas ponderadas, memoria
│   ├── consolidador.py              ← Lectura CSV + checkpointing
│   ├── preparador.py                ← FEX_ADJ, variables derivadas
│   ├── diagnostico.py               ← Missing values, tipos, identidades
│   ├── indicadores.py               ← TD, TGP, TO, ingresos, Gini, brecha
│   ├── analisis_avanzado.py         ← ICE, ICI, ITAT, IVI, Mincer, etc.
│   ├── analisis_poblacional.py      ← Campesinos, discapacidad, migración
│   ├── analisis_complementario.py   ← M8 duración, M14 dashboard, MX1-3
│   ├── analisis_area.py             ← 32 ciudades × CIIU
│   ├── visualizacion.py             ← 9 gráficos matplotlib
│   ├── visualizacion_interactiva.py ← 8 gráficos Plotly
│   ├── exportador.py                ← Carpetas + Excel formato ProColombia
│   ├── descargador.py               ← Descarga/organización microdatos DANE
│   ├── comparativo.py               ← Comparación inter-anual
│   ├── logger.py                    ← Logging centralizado
│   ├── profiler.py                  ← Profiling de memoria
│   └── dashboard.py                 ← Dashboard Streamlit
├── tests/                           ← 71 tests automatizados
├── docs/                            ← Guía metodológica
├── notebooks/Pipeline_GEIH.py       ← Notebook ejecutable (15 celdas)
├── pyproject.toml                   ← Packaging
├── requirements.txt                 ← Dependencias
└── README.md                        ← Este archivo
```

## Agregar un año nuevo (2027+)

Solo 2 líneas en `config.py`:

```python
# En SMMLV_POR_ANIO:
2027: 1_800_000,

# En REF_DANE (cuando DANE publique):
2027: ReferenciaDane(td_anual_pct=..., tgp_anual_pct=..., ...),
```

## Tests

```bash
python -m pytest tests/ -v        # 71 tests
python tests/smoke_test.py         # Validación rápida del pipeline
```

## Dashboard

```bash
pip install streamlit plotly
streamlit run geih_2025/dashboard.py
```

## Licencia

MIT — Néstor Enrique Forero Herrera · ProColombia · GIC
