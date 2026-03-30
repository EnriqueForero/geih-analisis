# -*- coding: utf-8 -*-
"""
geih — Análisis de microdatos GEIH del DANE.

Gran Encuesta Integrada de Hogares | DANE | Marco Muestral 2018
Autor: Néstor Enrique Forero Herrera

Paquete multi-año: soporta GEIH 2022–presente. No está atado a ningún
año específico — el nombre 'geih_2025' era la versión anterior.

Instalación:
    pip install geih-analisis
    # o desde GitHub:
    pip install git+https://github.com/enriqueforero/geih-analisis.git

Uso rápido:
    from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH
    config = ConfigGEIH(anio=2025, n_meses=12)

Compatibilidad hacia atrás:
    'from geih_2025 import ...' sigue funcionando gracias al shim
    incluido en este paquete. Recibirás un DeprecationWarning.

CAMBIO v5.0 — Renombrado geih_2025 → geih:
  El paquete ahora se llama 'geih' (nombre de importación) y
  'geih-analisis' (nombre de distribución en PyPI).
  El shim geih_2025/ garantiza compatibilidad durante la transición.

Módulos del paquete (17 archivos):
  config.py                → Constantes, mapeos, configuración centralizada
  utils.py                 → Memoria, conversión de tipos, estadísticas ponderadas
  consolidador.py          → Lectura y unión de módulos CSV mensuales
  preparador.py            → Preparación de datos, merge con correlativas
  diagnostico.py           → Diagnóstico de calidad de datos
  indicadores.py           → Indicadores básicos (TD, TGP, TO, ingresos, rama)
  analisis_avanzado.py     → Módulos avanzados (ICE, ICI, ITAT, Mincer, etc.)
  analisis_area.py         → 32 ciudades × CIIU
  analisis_poblacional.py  → Campesinos, discapacidad, migración
  analisis_complementario.py → M8, M14, MX1–MX3
  exportador.py            → Exportación organizada a carpetas
  visualizacion.py         → Gráficos matplotlib
  visualizacion_interactiva.py → Gráficos Plotly
  comparativo.py           → Comparación inter-anual
  descargador.py           → Descarga automática DANE
  logger.py                → Logging centralizado
  profiler.py              → Profiling de memoria
  dashboard.py             → Dashboard Streamlit
"""

__version__ = "0.1.0"
__author__  = "Néstor Enrique Forero Herrera"
__email__   = "nforero@procolombia.co"
__url__     = "https://github.com/enriqueforero/geih-analisis"
__license__ = "MIT"

# ── Configuración ──────────────────────────────────────────────────
from .config import (
    # Configuración principal
    ConfigGEIH,
    # SMMLV
    SMMLV_2025, SMMLV_POR_ANIO,
    # Colores
    COLORES,
    # Períodos
    MESES_CARPETAS, MESES_NOMBRES,
    generar_carpetas_mensuales, generar_etiqueta_periodo,
    # Geografía
    DEPARTAMENTOS, DPTO_A_CIUDAD, AREA_A_CIUDAD,
    CIUDADES_13_PRINCIPALES, CIUDADES_10_INTERMEDIAS,
    # Clasificaciones económicas
    RAMAS_DANE, TABLA_CIIU_RAMAS, AGRUPACION_DANE_8,
    # Referencias DANE
    REF_DANE_2025, REF_DANE, ReferenciaDane,
    # Constantes laborales — antes faltaban, causaban ImportError
    CARGA_PRESTACIONAL, TAMANO_EMPRESA,
    RANGOS_SMMLV_LIMITES, RANGOS_SMMLV_ETIQUETAS,
    # Educación — antes faltaban
    NIVELES_AGRUPADOS, NIVELES_EDUCATIVOS, P3042_A_ANOS,
    # Llaves y converters
    LLAVES_PERSONA, LLAVES_HOGAR,
    CONVERTERS_BASE, CONVERTERS_CON_AREA,
    MODULOS_CSV,
)

# ── Utilidades ─────────────────────────────────────────────────────
from .utils import GestorMemoria, ConversorTipos, EstadisticasPonderadas

# ── Consolidación ──────────────────────────────────────────────────
from .consolidador import ConsolidadorGEIH

# ── Preparación ────────────────────────────────────────────────────
from .preparador import PreparadorGEIH, MergeCorrelativas

# ── Diagnóstico ────────────────────────────────────────────────────
from .diagnostico import DiagnosticoCalidad, Top20Sectores

# ── Exportación organizada ─────────────────────────────────────────
from .exportador import Exportador

# ── Indicadores básicos ────────────────────────────────────────────
from .indicadores import (
    IndicadoresLaborales, DistribucionIngresos, AnalisisRamaSexo,
    AnalisisSalarios, BrechaGenero, AnalisisCruzado,
    IndicesCompuestos, AnalisisArea,
)

# ── Análisis por 32 ciudades ───────────────────────────────────────
from .analisis_area import AnalisisOcupadosCiudad

# ── Análisis avanzado ──────────────────────────────────────────────
from .analisis_avanzado import (
    CalidadEmpleo, FormalidadSectorial, VulnerabilidadLaboral,
    CompetitividadLaboral, AnalisisSubempleo, AnalisisHoras,
    Estacionalidad, FuerzaLaboralJoven, EtnicoRacial,
    BonoDemografico, CostoLaboral, AnalisisFFT,
    AnalisisUrbanoRural, ProductividadTamano,
    ContribucionSectorial, MapaTalento, EcuacionMincer,
    ProxyBilinguismo,
)

# ── Visualización matplotlib ───────────────────────────────────────
from .visualizacion import (
    GraficoDistribucionIngresos, GraficoBoxPlotSalarios,
    GraficoBrechaGenero, GraficoRamaSexo,
    GraficoCurvaLorenz, GraficoICIBubble,
    GraficoEstacionalidad, GraficoContribucionHeatmap,
)

# ── Análisis poblacional ───────────────────────────────────────────
from .analisis_poblacional import (
    AnalisisCampesino, AnalisisDiscapacidad, AnalisisMigracion,
    AnalisisOtrasFormas, AnalisisOtrosIngresos,
    AnalisisSobrecalificacion, AnalisisContractual,
    AnalisisAutonomia, AnalisisAlcanceMercado, AnalisisDesanimados,
)

# ── Análisis complementarios ───────────────────────────────────────
from .analisis_complementario import (
    DuracionDesempleo, DashboardSectoresProColombia,
    AnatomaSalario, FormaPago, CanalEmpleo,
)

# ── Descarga automática DANE ───────────────────────────────────────
from .descargador import DescargadorDANE

# ── Comparativo multi-año ──────────────────────────────────────────
from .comparativo import ComparadorMultiAnio

# ── Visualización interactiva Plotly ───────────────────────────────
try:
    from .visualizacion_interactiva import (
        PlotlyLorenz, PlotlyICIBubble, PlotlyEstacionalidad,
        PlotlyDistribucionIngresos, PlotlyBrechaGenero,
        PlotlyBoxPlotSalarios, PlotlySalarioRama,
        PlotlyComparativoAnual,
    )
except ImportError:
    pass  # plotly no instalado — instalar con: pip install geih-analisis[viz]

# ── Logging centralizado ───────────────────────────────────────────
from .logger import get_logger, configurar_logging, LoggerGEIH

# ── Profiling de memoria ───────────────────────────────────────────
from .profiler import PerfilMemoria, medir_tiempo, tamano_objeto

# ── Dashboard Streamlit ────────────────────────────────────────────
from .dashboard import ejecutar_dashboard
