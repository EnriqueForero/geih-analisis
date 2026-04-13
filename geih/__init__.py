# -*- coding: utf-8 -*-
"""
geih — Paquete Python para análisis de microdatos GEIH (DANE, Colombia).

Convierte los archivos CSV crudos del DANE en indicadores del mercado
laboral listos para reportar: desempleo, salarios, brecha de género,
formalidad, educación y más — con pocas líneas de código.

Uso rápido:
    from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

    config = ConfigGEIH(anio=2025, n_meses=12)
    geih   = ConsolidadorGEIH.cargar('GEIH_2025_Consolidado.parquet')
    df     = PreparadorGEIH(config=config).preparar_base(geih)
    r      = IndicadoresLaborales(config=config).calcular(df)

Autor: Néstor Enrique Forero Herrera
Licencia: MIT
"""

__version__ = "0.1.5"

# ── Configuración ─────────────────────────────────────────────
from .config import (
    ConfigGEIH,
    SMMLV_POR_ANIO,
    SMMLV_2025,
    CARGA_PRESTACIONAL,
    MESES_NOMBRES,
    MESES_CARPETAS,
    generar_carpetas_mensuales,
    generar_etiqueta_periodo,
    cargar_config_externa,
    COLORES,
    LLAVES_PERSONA,
    LLAVES_HOGAR,
    CONVERTERS_BASE,
    CONVERTERS_CON_AREA,
    MODULOS_CSV,
    VARIABLES_POR_MODULO,
    RAMAS_DANE,
    TABLA_CIIU_RAMAS,
    AGRUPACION_DANE_8,
    DEPARTAMENTOS,
    DPTO_A_CIUDAD,
    AREA_A_CIUDAD,
    CIUDADES_13_PRINCIPALES,
    CIUDADES_10_INTERMEDIAS,
    NIVELES_EDUCATIVOS,
    NIVELES_AGRUPADOS,
    P3042_A_ANOS,
    RANGOS_SMMLV_LIMITES,
    RANGOS_SMMLV_ETIQUETAS,
    TAMANO_EMPRESA,
    CIIU_DESCRIPCION_FALLBACK,
    CIIU_SECTOR_PRIMARIO,
    CIIU_AGRICULTURA_DETALLE,
    ReferenciaDane,
    REF_DANE,
    REF_DANE_2025,
)

# ── Utilidades ────────────────────────────────────────────────
from .utils import EstadisticasPonderadas, ConversorTipos, GestorMemoria

# ── Muestreo ─────────────────────────────────────────────────
from .muestreo import (
    ConfigMuestreo,
    PrecisionEstimacion,
    evaluar_proporcion,
    evaluar_media,
    evaluar_total,
    clasificar_precision,
    advertencia_muestral,
)

# ── Pipeline principal ────────────────────────────────────────
from .consolidador import ConsolidadorGEIH
from .preparador import PreparadorGEIH, MergeCorrelativas, COLUMNAS_DEFAULT
from .indicadores import (
    IndicadoresLaborales,
    DistribucionIngresos,
    AnalisisRamaSexo,
    AnalisisSalarios,
    BrechaGenero,
    AnalisisCruzado,
    IndicesCompuestos,
    AnalisisArea,
)

# ── Análisis avanzados ────────────────────────────────────────
from .analisis_avanzado import (
    CalidadEmpleo,
    FormalidadSectorial,
    VulnerabilidadLaboral,
    CompetitividadLaboral,
    AnalisisSubempleo,
    AnalisisHoras,
    Estacionalidad,
    FuerzaLaboralJoven,
    EtnicoRacial,
    BonoDemografico,
    CostoLaboral,
    AnalisisFFT,
    AnalisisUrbanoRural,
    ProductividadTamano,
    ContribucionSectorial,
    MapaTalento,
    EcuacionMincer,
    ProxyBilinguismo,
)

# ── Análisis complementarios ─────────────────────────────────
from .analisis_complementario import (
    DuracionDesempleo,
    DashboardSectoresProColombia,
    AnatomaSalario,
    FormaPago,
    CanalEmpleo,
)

# ── Análisis poblacionales ────────────────────────────────────
from .analisis_poblacional import (
    AnalisisCampesino,
    AnalisisDiscapacidad,
    AnalisisMigracion,
    AnalisisSobrecalificacion,
    AnalisisContractual,
    AnalisisAutonomia,
)

# ── Análisis por área geográfica ──────────────────────────────
from .analisis_area import AnalisisOcupadosCiudad

# ── Análisis departamental consolidado ────────────────────────
from .analisis_departamental import AnalisisDepartamental

# ── Análisis ocupados por depto y rama ────────────────────────
from .analisis_dpto_rama import OcupadosDptoRama

# ── Análisis de tierras agropecuarias ─────────────────────────
from .analisis_tierra import AnalisisTierraAgropecuario

# ── Comparativo multi-año ─────────────────────────────────────
from .comparativo import ComparadorMultiAnio

# ── Exportación ───────────────────────────────────────────────
from .exportador import Exportador

# ── Descargador ───────────────────────────────────────────────
from .descargador import DescargadorDANE

# ── Diagnóstico ───────────────────────────────────────────────
from .diagnostico import DiagnosticoCalidad, Top20Sectores

# ── Profiler ──────────────────────────────────────────────────
from .profiler import PerfilMemoria, medir_tiempo, tamano_objeto

# ── Visualización ─────────────────────────────────────────────
from .visualizacion import (
    GraficoDistribucionIngresos, GraficoBoxPlotSalarios,
    GraficoBrechaGenero, GraficoRamaSexo,
    GraficoCurvaLorenz, GraficoICIBubble,
    GraficoEstacionalidad, GraficoContribucionHeatmap,
)

# ── Dashboard (requiere extras) ───────────────────────────────
try:
    from .dashboard import ejecutar_dashboard
except ImportError:
    # streamlit no disponible → función no accesible, sin error
    pass
