"""
geih — Paquete Python para análisis de microdatos GEIH (DANE, Colombia).

Convierte los archivos CSV crudos del DANE en indicadores del mercado
laboral listos para reportar: desempleo, salarios, brecha de género,
formalidad, educación y más — con pocas líneas de código.

Incluye módulos de replicación oficial DANE (IT1 v2) para contraste
y validación de cifras frente a publicaciones institucionales.

Uso rápido:
    from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

    config = ConfigGEIH(anio=2025, n_meses=12)
    geih   = ConsolidadorGEIH.cargar('GEIH_2025_Consolidado.parquet')
    df     = PreparadorGEIH(config=config).preparar_base(geih)
    r      = IndicadoresLaborales(config=config).calcular(df)

Política de importación (Fail Fast):
  - Módulos internos del paquete: importación directa. Un fallo es un bug
    del paquete; debe surfacear inmediatamente con su traceback real.
  - Dependencias externas opcionales (matplotlib/plotly, streamlit):
    try/except con DISCRIMINACIÓN por ImportError.name. Solo se silencia
    cuando la causa raíz es la dependencia opcional faltante; cualquier
    otro ImportError (bug interno) propaga. Fail Fast preservado.

Política de versión (Single Source of Truth):
  - __version__ se lee de los metadatos de la distribución instalada
    mediante importlib.metadata. La fuente canónica es pyproject.toml.
  - En checkout fuente sin instalar (p. ej. `python -c "import geih"`
    desde un clon sin `pip install -e .`), reporta "0.0.0+dev" para
    impedir confusión con una versión publicada.

Autor: Néstor Enrique Forero Herrera
Licencia: MIT
"""

from __future__ import annotations

import warnings as _warnings
from importlib.metadata import (
    PackageNotFoundError as _PackageNotFoundError,
)
from importlib.metadata import (
    version as _pkg_version,
)

# ══════════════════════════════════════════════════════════════
# ── Versión — derivada de los metadatos de la distribución ────
# ── Única fuente de verdad: pyproject.toml                     ─
# ══════════════════════════════════════════════════════════════
try:
    __version__ = _pkg_version("geih-analisis")
except _PackageNotFoundError:
    # Ejecutando desde checkout sin `pip install`.
    # Se marca explícitamente como "dev" para evitar confusión
    # con una versión publicada.
    __version__ = "0.1.7"


# ══════════════════════════════════════════════════════════════
# ── Configuración — constantes núcleo ─────────────────────────
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
# ── Análisis geográficos ──────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .analisis_area import AnalisisOcupadosCiudad

# ══════════════════════════════════════════════════════════════
# ── Análisis avanzados ────────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .analisis_avanzado import (
    AnalisisFFT,
    AnalisisHoras,
    AnalisisSubempleo,
    AnalisisUrbanoRural,
    BonoDemografico,
    CalidadEmpleo,
    CompetitividadLaboral,
    ContribucionSectorial,
    CostoLaboral,
    EcuacionMincer,
    Estacionalidad,
    EtnicoRacial,
    FormalidadSectorial,
    FuerzaLaboralJoven,
    MapaTalento,
    ProductividadTamano,
    ProxyBilinguismo,
    VulnerabilidadLaboral,
)

# ══════════════════════════════════════════════════════════════
# ── Análisis complementarios ──────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .analisis_complementario import (
    AnatomaSalario,
    CanalEmpleo,
    DashboardSectoresProColombia,
    DuracionDesempleo,
    FormaPago,
)
from .analisis_departamental import AnalisisDepartamental
from .analisis_dpto_rama import OcupadosDptoRama

# ══════════════════════════════════════════════════════════════
# ── Análisis poblacionales ────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .analisis_poblacional import (
    AnalisisAutonomia,
    AnalisisCampesino,
    AnalisisContractual,
    AnalisisDiscapacidad,
    AnalisisMigracion,
    AnalisisSobrecalificacion,
)

# ══════════════════════════════════════════════════════════════
# ── Análisis sectorial especializado ─────────────────────────
# ══════════════════════════════════════════════════════════════
from .analisis_tierra import AnalisisTierraAgropecuario

# ══════════════════════════════════════════════════════════════
# ── Comparativo multi-año ─────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .comparativo import ComparadorMultiAnio
from .config import (
    AGRUPACION_DANE_8,
    AREA_A_CIUDAD,
    AREA_GEIH_A_CIUDAD,
    CARGA_PRESTACIONAL,
    CIIU_AGRICULTURA_DETALLE,
    CIIU_DESCRIPCION_FALLBACK,
    CIIU_SECTOR_PRIMARIO,
    CIUDADES_10_INTERMEDIAS,
    CIUDADES_13_PRINCIPALES,
    # Helpers y referencias
    COLORES,
    CONVERTERS_BASE,
    CONVERTERS_CON_AREA,
    # Clasificaciones geográficas
    DEPARTAMENTOS,
    DPTO_A_CIUDAD,
    DPTOS_10_CIUDADES,
    DPTOS_13_CIUDADES,
    LLAVES_HOGAR,
    LLAVES_PERSONA,
    MESES_CARPETAS,
    MESES_NOMBRES,
    MODULOS_CSV,
    NIVELES_AGRUPADOS,
    # Clasificaciones educativas y empresariales
    NIVELES_EDUCATIVOS,
    P3042_A_ANOS,
    POSICION_OCUPACIONAL,
    # Clasificaciones sectoriales y laborales
    RAMAS_DANE,
    RANGOS_SMMLV_ETIQUETAS,
    RANGOS_SMMLV_LIMITES,
    REF_DANE,
    REF_DANE_2025,
    SMMLV_2025,
    # Salarios y rangos
    SMMLV_POR_ANIO,
    TABLA_CIIU_RAMAS,
    TAMANO_EMPRESA,
    VARIABLES_POR_MODULO,
    # Infraestructura base
    ConfigGEIH,
    ReferenciaDane,
    cargar_config_externa,
    generar_carpetas_mensuales,
    generar_etiqueta_periodo,
)
from .consolidador import ConsolidadorGEIH
from .descargador import DescargadorDANE

# ══════════════════════════════════════════════════════════════
# ── Diagnóstico y profiling ───────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .diagnostico import DiagnosticoCalidad, Top20Sectores

# ══════════════════════════════════════════════════════════════
# ── Exportación y descarga ────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .exportador import Exportador

# ══════════════════════════════════════════════════════════════
# ── Indicadores laborales ─────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .indicadores import (
    AnalisisArea,
    AnalisisCruzado,
    AnalisisRamaSexo,
    AnalisisSalarios,
    BrechaGenero,
    DistribucionIngresos,
    IndicadoresLaborales,
    IndicesCompuestos,
)

# ══════════════════════════════════════════════════════════════
# ── Pipeline principal ────────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .informalidad import clasificar_informalidad_dane

# ══════════════════════════════════════════════════════════════
# ── Muestreo ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .muestreo import (
    ConfigMuestreo,
    PrecisionEstimacion,
    advertencia_muestral,
    clasificar_precision,
    evaluar_media,
    evaluar_proporcion,
    evaluar_total,
)
from .preparador import COLUMNAS_DEFAULT, MergeCorrelativas, PreparadorGEIH
from .profiler import PerfilMemoria, medir_tiempo, tamano_objeto

# ══════════════════════════════════════════════════════════════
# ── Replicación DANE (IT1 v2) ─────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .replicacion_dane_common import (
    CeldaComparada,
    ExcelLayoutParser,
    LoaderGEIH,
    ParametrosValidacion,
    PeriodoMovil,
    ResolvedTrimestre,
    ResultadoHoja,
    ResultadoReplicacion,
    RutasProyecto,
    ValidadorParidad,
    hash_archivo,
    normalizar_texto,
)
from .replicacion_dane_informalidad import (
    HOJAS_INFORMALIDAD,
    ReplicadorInformalidad,
    replicar_informalidad_excel,
)
from .replicacion_dane_seguridad_social import (
    HOJAS_SEGURIDAD_SOCIAL,
    LINEAS_SS,
    ReplicadorSeguridadSocial,
    replicar_seguridad_social_excel,
)

# ══════════════════════════════════════════════════════════════
# ── Utilidades ────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════
from .utils import ConversorTipos, EstadisticasPonderadas, GestorMemoria

# ══════════════════════════════════════════════════════════════
# ── Visualización — OPCIONAL (extras [viz])                  ──
# ── try/except JUSTIFICADO: dependencia externa.             ──
# ── Discriminación por ImportError.name:                     ──
# ──   • Si falta matplotlib/plotly → warning + seguir.       ──
# ──   • Cualquier otro ImportError (bug) → PROPAGA.          ──
# ══════════════════════════════════════════════════════════════
_VIZ_DEPS = ("matplotlib", "plotly")

try:
    from .visualizacion import (
        GraficoBoxPlotSalarios,
        GraficoBrechaGenero,
        GraficoContribucionHeatmap,
        GraficoCurvaLorenz,
        GraficoDistribucionIngresos,
        GraficoEstacionalidad,
        GraficoICIBubble,
        GraficoRamaSexo,
    )
except ImportError as _e:
    _missing = _e.name or ""
    if not any(_missing.startswith(_dep) for _dep in _VIZ_DEPS):
        # ImportError NO es por la dependencia opcional → es un bug.
        # Propagar para que Fail Fast surfacee el problema real.
        raise
    _warnings.warn(
        f"Módulo de visualización no disponible: falta '{_missing}'. "
        "Instala con: pip install geih-analisis[viz]",
        ImportWarning,
        stacklevel=2,
    )


# ══════════════════════════════════════════════════════════════
# ── Dashboard interactivo — OPCIONAL (extras [dashboard])    ──
# ── try/except JUSTIFICADO: dependencia externa.             ──
# ══════════════════════════════════════════════════════════════
_DASHBOARD_DEPS = ("streamlit", "plotly")

try:
    from .dashboard import ejecutar_dashboard
except ImportError as _e:
    _missing = _e.name or ""
    if not any(_missing.startswith(_dep) for _dep in _DASHBOARD_DEPS):
        # ImportError NO es por la dependencia opcional → es un bug.
        raise
    _warnings.warn(
        f"Dashboard no disponible: falta '{_missing}'. "
        "Instala con: pip install geih-analisis[dashboard]",
        ImportWarning,
        stacklevel=2,
    )
