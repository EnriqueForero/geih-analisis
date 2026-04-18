"""
geih.estacional — Desestacionalización de series mensuales GEIH.

Reproduce la sección "Tasa de desocupación desestacionalizada" del
Boletín DANE (pág. 25 del boletín pres-GEIH-dic2025.pdf), que publica
la TD mensual desestacionalizada para Total Nacional y 13 ciudades A.M.

Métodos disponibles:
  - 'stl'  → Seasonal-Trend decomposition using LOESS (statsmodels nativo,
             siempre disponible). Robusto a outliers, sin dependencias
             binarias externas. ES EL DEFAULT.
  - 'x13'  → X-13-ARIMA-SEATS (US Census Bureau). Es el método oficial
             del DANE pero requiere el binario X-13 instalado en el
             sistema, lo cual no es trivial en Colab/contenedores.

Limitación documentada: el DANE usa X-13 con calendario laboral
colombiano (días hábiles, semana santa, festivos), parámetros que
no son replicables exactamente con STL. Esperar diferencias de
±0.1 a ±0.3 p.p. frente a la serie oficial publicada.

Autor: Néstor Enrique Forero Herrera
Versión: v6.0 (abril 2026)
"""

from __future__ import annotations

__all__ = [
    "desestacionalizar",
    "desestacionalizar_td_mensual",
    "validar_serie_mensual",
]

from typing import Literal, Optional

import numpy as np
import pandas as pd


def validar_serie_mensual(serie: pd.Series, min_periodos: int = 24) -> None:
    """Valida que una serie sea apta para desestacionalización mensual.

    Args:
        serie: Serie con DatetimeIndex mensual o PeriodIndex mensual.
        min_periodos: Mínimo de observaciones requeridas (default: 24,
            equivale a 2 años — el mínimo razonable para STL mensual).

    Raises:
        ValueError: si la serie no cumple los requisitos.
    """
    if not isinstance(serie, pd.Series):
        raise ValueError(f"Se esperaba pd.Series, recibido {type(serie).__name__}")

    if len(serie) < min_periodos:
        raise ValueError(
            f"Serie demasiado corta para desestacionalización mensual: "
            f"{len(serie)} observaciones, mínimo {min_periodos} (2 años). "
            f"Use al menos 24 meses para que STL identifique el patrón estacional."
        )

    # El índice debe ser temporal y sin huecos
    if not isinstance(serie.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        raise ValueError(
            f"El índice de la serie debe ser DatetimeIndex o PeriodIndex, "
            f"recibido {type(serie.index).__name__}. Convierta con "
            f"pd.to_datetime() antes de llamar a esta función."
        )

    if serie.isna().any():
        n_na = int(serie.isna().sum())
        raise ValueError(
            f"La serie contiene {n_na} valores NaN. Imputar o interpolar "
            f"antes de desestacionalizar (los métodos STL y X-13 no "
            f"toleran huecos)."
        )


def desestacionalizar(
    serie_mensual: pd.Series,
    metodo: Literal["stl", "x13"] = "stl",
    periodo: int = 12,
    robust: bool = True,
) -> pd.Series:
    """Desestacionaliza una serie mensual.

    Devuelve el componente tendencia + residual (= serie original menos
    componente estacional), que es lo que el DANE publica como "serie
    desestacionalizada" en el Boletín GEIH.

    Args:
        serie_mensual: Serie con DatetimeIndex/PeriodIndex mensual.
        metodo:
            - 'stl' (default): Seasonal-Trend LOESS, siempre disponible.
            - 'x13': X-13-ARIMA-SEATS, requiere binario externo.
        periodo: Período estacional. Para serie mensual = 12.
        robust: Si True, usa la versión robusta de STL (resistente a
            outliers como el shock COVID-2020). Default True.

    Returns:
        Serie desestacionalizada, con el mismo índice que la entrada.

    Raises:
        ValueError: si la serie no es apta (ver validar_serie_mensual).
        ImportError: si se solicita 'x13' pero statsmodels no encuentra
            el binario X-13.

    Ejemplo:
        >>> td_mensual = pd.Series(
        ...     [11.6, 10.3, 9.8, 9.3, 8.8, 8.6, 8.7, 8.8, 8.2, 7.2, 7.0, 8.0],
        ...     index=pd.period_range('2025-01', '2025-12', freq='M'),
        ... )
        >>> # Necesitamos al menos 24 meses para STL — concatenar con 2024
        >>> td_2024 = pd.Series([10.5]*12, index=pd.period_range('2024-01','2024-12',freq='M'))
        >>> serie = pd.concat([td_2024, td_mensual])
        >>> td_desest = desestacionalizar(serie)
        >>> td_desest.tail(3)
        2025-10    7.5
        2025-11    7.4
        2025-12    7.6
        Freq: M, dtype: float64
    """
    validar_serie_mensual(serie_mensual)

    # Convertir PeriodIndex a DatetimeIndex si es necesario (statsmodels
    # prefiere DatetimeIndex con frecuencia explícita)
    if isinstance(serie_mensual.index, pd.PeriodIndex):
        serie_mensual = serie_mensual.copy()
        serie_mensual.index = serie_mensual.index.to_timestamp()

    if metodo == "stl":
        from statsmodels.tsa.seasonal import STL

        resultado = STL(
            serie_mensual,
            period=periodo,
            robust=robust,
        ).fit()
        # serie desestacionalizada = original - estacional = tendencia + residual
        return resultado.trend + resultado.resid

    elif metodo == "x13":
        try:
            from statsmodels.tsa.x13 import x13_arima_analysis
        except ImportError as e:
            raise ImportError(
                "x13 requiere statsmodels.tsa.x13 y el binario X-13 de "
                "Census Bureau instalado en el sistema. En Colab no está "
                "disponible — use metodo='stl'."
            ) from e
        resultado = x13_arima_analysis(serie_mensual)
        return resultado.seasadj

    else:
        raise ValueError(f"metodo debe ser 'stl' o 'x13', recibido '{metodo}'")


def desestacionalizar_td_mensual(
    df_anual: pd.DataFrame,
    columna_mes: str = "MES_NUM",
    anio: int = 2025,
    incluir_historico: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Helper de alto nivel: calcula TD mensual + TD desestacionalizada.

    Wrapper conveniente para la replicación directa del gráfico de
    pág. 25 del Boletín DANE. Toma una base anual ya preparada,
    calcula TD para cada mes, y devuelve un DataFrame con TD cruda
    y TD desestacionalizada lado a lado.

    Args:
        df_anual: DataFrame preparado del año completo (de PreparadorGEIH).
            Debe tener columnas FEX_ADJ, FT, DSI y la columna_mes.
        columna_mes: Nombre de la columna de mes (default: 'MES_NUM').
        anio: Año del análisis (para construir el índice temporal).
        incluir_historico: Serie de TD mensuales históricas (al menos
            12 meses anteriores al df_anual). Necesario porque STL
            requiere mínimo 24 meses para identificar la estacionalidad.
            Si se pasa, los meses históricos se concatenan al inicio
            antes de desestacionalizar.

    Returns:
        DataFrame con índice mensual (DatetimeIndex) y dos columnas:
          - 'td_cruda'        : TD calculada cada mes
          - 'td_desest'       : TD desestacionalizada con STL

    Ejemplo:
        >>> # Asumiendo df_anu de PreparadorGEIH(meses_rango=range(1,13))
        >>> # y serie_2024 con TD mensual del año anterior:
        >>> resultado = desestacionalizar_td_mensual(
        ...     df_anu, anio=2025, incluir_historico=serie_2024,
        ... )
        >>> resultado.tail(3)
                    td_cruda  td_desest
        2025-10-01      7.20       7.51
        2025-11-01      7.00       7.43
        2025-12-01      8.00       7.62
    """
    # Calcular TD mensual del año en curso
    td_por_mes = []
    for m in sorted(df_anual[columna_mes].dropna().unique().astype(int)):
        sub = df_anual[df_anual[columna_mes] == m]
        pea = sub.loc[sub["FT"] == 1, "FEX_ADJ"].sum()
        dsi = sub.loc[sub["DSI"] == 1, "FEX_ADJ"].sum()
        td_m = (100 * dsi / pea) if pea > 0 else np.nan
        td_por_mes.append((pd.Timestamp(year=anio, month=m, day=1), td_m))

    serie_actual = pd.Series(
        dict(td_por_mes),
        name="td_cruda",
    ).sort_index()

    # Concatenar con histórico si se provee, para tener mínimo 24 meses
    if incluir_historico is not None:
        if isinstance(incluir_historico.index, pd.PeriodIndex):
            incluir_historico = incluir_historico.copy()
            incluir_historico.index = incluir_historico.index.to_timestamp()
        serie_completa = pd.concat([incluir_historico, serie_actual]).sort_index()
        # Eliminar duplicados de fecha si los hubiera
        serie_completa = serie_completa[~serie_completa.index.duplicated(keep="last")]
    else:
        serie_completa = serie_actual

    # Desestacionalizar la serie completa, luego recortar al año actual
    if len(serie_completa) >= 24:
        td_desest = desestacionalizar(serie_completa, metodo="stl")
        td_desest = td_desest.loc[serie_actual.index]
    else:
        # No hay suficientes meses → no se puede desestacionalizar
        td_desest = pd.Series(np.nan, index=serie_actual.index)
        print(
            f"⚠️  Solo {len(serie_completa)} meses disponibles. STL requiere "
            f"≥24 (2 años). Se devuelve td_desest vacía. Pase "
            f"incluir_historico con ≥12 meses anteriores para habilitarlo."
        )

    return pd.DataFrame(
        {
            "td_cruda": serie_actual,
            "td_desest": td_desest,
        }
    )
