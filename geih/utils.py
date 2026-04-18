"""
geih.utils — Funciones utilitarias transversales.

Contiene tres grupos de funciones:
  1. Gestión de memoria RAM (para Google Colab ~12GB)
  2. Conversión de tipos de datos (el DANE entrega formatos mixtos)
  3. Estadísticas ponderadas (el corazón metodológico de la GEIH)

Todas son funciones puras o casi puras: reciben datos, devuelven datos.
No modifican estado global ni acceden a disco.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "GestorMemoria",
    "ConversorTipos",
    "EstadisticasPonderadas",
]


import gc
import os
from typing import Any, Optional

import numpy as np
import pandas as pd

# ═════════════════════════════════════════════════════════════════════
# 1. GESTIÓN DE MEMORIA RAM
# ═════════════════════════════════════════════════════════════════════


class GestorMemoria:
    """Monitoreo y liberación de memoria RAM en Google Colab.

    En Colab Free (~12GB), la memoria es el recurso más escaso.
    Esta clase encapsula la lógica de monitoreo y limpieza.

    Uso típico:
        mem = GestorMemoria()
        mem.estado()                           # ver RAM disponible
        mem.liberar(['df_temp', 'resultado'])   # eliminar variables
    """

    @staticmethod
    def estado() -> dict[str, float]:
        """Muestra y retorna el uso actual de RAM en GB.

        Returns:
            Dict con 'usada', 'libre', 'total' en GB.
            Retorna dict vacío si psutil no está disponible.
        """
        try:
            import psutil

            proceso = psutil.Process(os.getpid())
            ram_usada = proceso.memory_info().rss / 1e9
            vm = psutil.virtual_memory()
            ram_libre = vm.available / 1e9
            ram_total = vm.total / 1e9
            print(f"   RAM usada : {ram_usada:.2f} GB")
            print(f"   RAM libre : {ram_libre:.2f} GB  /  Total: {ram_total:.2f} GB")
            return {"usada": ram_usada, "libre": ram_libre, "total": ram_total}
        except ImportError:
            print("   (instala psutil para ver RAM: !pip install psutil)")
            return {}

    @staticmethod
    def liberar(
        variables: Optional[list[str]] = None, scope: Optional[dict] = None, verbose: bool = True
    ) -> None:
        """Libera memoria eliminando variables del scope dado.

        Args:
            variables: Nombres de variables a eliminar.
            scope: Diccionario del scope (usar globals() desde el notebook).
            verbose: Si True, muestra RAM después de limpiar.

        Nota:
            Desde un notebook llamar así:
            GestorMemoria.liberar(['df_temp'], scope=globals())
        """
        if variables and scope:
            for var in variables:
                if var in scope:
                    del scope[var]
        gc.collect()
        if verbose:
            GestorMemoria.estado()

    @staticmethod
    def tamano_df(df: pd.DataFrame, nombre: str = "DataFrame") -> None:
        """Imprime el tamaño en memoria de un DataFrame."""
        mb = df.memory_usage(deep=True).sum() / 1e6
        print(f"   {nombre}: {len(df):,} filas × {df.shape[1]} cols → {mb:.1f} MB")


# ═════════════════════════════════════════════════════════════════════
# 2. CONVERSIÓN DE TIPOS DE DATOS
# ═════════════════════════════════════════════════════════════════════


class ConversorTipos:
    """Convierte columnas GEIH al tipo de dato correcto.

    El DANE entrega archivos CSV con formatos inconsistentes:
    - Números con comas como separador decimal ('1.234,56')
    - Códigos numéricos que deben ser strings ('05' → Antioquia)
    - Floats que representan enteros (1.0 → '1')

    Esta clase estandariza todo de forma vectorizada.
    """

    @staticmethod
    def a_numerico(serie: pd.Series) -> pd.Series:
        """Convierte una serie a numérico, manejando comas y formatos mixtos.

        Ejemplo: '1.234,56' → 1234.56 ; 'nan' → NaN ; '1.0' → 1.0

        Args:
            serie: Columna con valores potencialmente numéricos.

        Returns:
            Serie con dtype float64 o Int64.
        """
        if pd.api.types.is_numeric_dtype(serie):
            return serie
        try:
            return pd.to_numeric(
                serie.astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            )
        except Exception:
            return pd.to_numeric(serie, errors="coerce")

    @staticmethod
    def estandarizar_ciiu4(serie: pd.Series) -> pd.Series:
        """Estandariza códigos CIIU de 4 dígitos para merge con correlativa.

        Problema: GEIH trae '111', '4711.0', '111.5', etc.
        Solución: quitar .0, tomar parte entera, rellenar a 4 dígitos.

        Args:
            serie: Columna RAMA4D_R4 en cualquier formato.

        Returns:
            Serie con códigos de exactamente 4 dígitos o NaN.
        """
        s = serie.astype(str).str.strip()
        s = s.str.replace(r"\.0$", "", regex=True)  # quitar .0
        s = s.str.split(".").str[0]  # parte entera
        s = s.str.zfill(4)  # rellenar ceros
        s = s.where(s.str.match(r"^\d{4}$"), other=np.nan)
        return s

    @staticmethod
    def estandarizar_dpto(serie: pd.Series) -> pd.Series:
        """Estandariza código de departamento a 2 dígitos con cero líder.

        Crítico: '5' debe ser '05' (Antioquia), no '5'.

        Args:
            serie: Columna DPTO.

        Returns:
            Serie con códigos de exactamente 2 dígitos.
        """
        return serie.astype(str).str.strip().str.zfill(2)

    @staticmethod
    def estandarizar_area(serie: pd.Series) -> pd.Series:
        """Estandariza código AREA (municipio) a 5 dígitos.

        Args:
            serie: Columna AREA.

        Returns:
            Serie con códigos de exactamente 5 dígitos.
        """
        return serie.astype(str).str.strip().str.zfill(5)

    @staticmethod
    def convertir_columnas_numericas(
        df: pd.DataFrame,
        columnas: list[str],
        excluir: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """Convierte múltiples columnas a numérico in-place.

        Args:
            df: DataFrame a modificar.
            columnas: Lista de columnas a convertir.
            excluir: Columnas que deben permanecer como string.

        Returns:
            El mismo DataFrame modificado.
        """
        excluir = set(excluir or [])
        for col in columnas:
            if col in df.columns and col not in excluir:
                df[col] = ConversorTipos.a_numerico(df[col])
        return df


# ═════════════════════════════════════════════════════════════════════
# 3. ESTADÍSTICAS PONDERADAS
# ═════════════════════════════════════════════════════════════════════


class EstadisticasPonderadas:
    """Calcula estadísticas descriptivas usando pesos de frecuencia (FEX).

    La GEIH es una encuesta con diseño muestral complejo.
    Cada registro representa a FEX_C18 personas de la población real.
    Ignorar los pesos produce estimaciones sesgadas.

    Todas las funciones:
      - Son vectorizadas (no usan loops sobre filas)
      - Manejan NaN y pesos ≤ 0 de forma segura
      - Retornan np.nan si no hay datos válidos
    """

    @staticmethod
    def media(valores: pd.Series, pesos: pd.Series) -> float:
        """Media aritmética ponderada.

        Fórmula: Σ(valor_i × peso_i) / Σ(peso_i)
        """
        mask = valores.notna() & pesos.notna() & (pesos > 0)
        v, w = valores[mask], pesos[mask]
        total_peso = w.sum()
        if total_peso == 0:
            return np.nan
        return float((v * w).sum() / total_peso)

    @staticmethod
    def mediana(valores: pd.Series, pesos: pd.Series) -> float:
        """Mediana ponderada (percentil 50).

        Ordena por valor, acumula pesos, busca donde la acumulación
        cruza el 50% del peso total.
        """
        return EstadisticasPonderadas.percentil(valores, pesos, 0.5)

    @staticmethod
    def percentil(valores: pd.Series, pesos: pd.Series, p: float) -> float:
        """Percentil ponderado.

        Args:
            valores: Datos observados.
            pesos: Pesos de frecuencia (FEX_ADJ).
            p: Percentil deseado en [0, 1]. Ej: 0.25 para P25.

        Returns:
            Valor en la posición del percentil ponderado.
        """
        mask = valores.notna() & pesos.notna() & (pesos > 0)
        v = valores[mask].values
        w = pesos[mask].values
        if len(v) == 0:
            return np.nan
        idx = np.argsort(v)
        v, w = v[idx], w[idx]
        acum = np.cumsum(w)
        corte = p * acum[-1]
        pos = np.searchsorted(acum, corte)
        return float(v[min(pos, len(v) - 1)])

    @staticmethod
    def desviacion_estandar(valores: pd.Series, pesos: pd.Series) -> float:
        """Desviación estándar ponderada."""
        media = EstadisticasPonderadas.media(valores, pesos)
        if np.isnan(media):
            return np.nan
        mask = valores.notna() & pesos.notna() & (pesos > 0)
        v, w = valores[mask], pesos[mask]
        var = ((v - media) ** 2 * w).sum() / w.sum()
        return float(np.sqrt(var))

    @staticmethod
    def coeficiente_variacion(valores: pd.Series, pesos: pd.Series) -> float:
        """CV% = (Desv.Std / Media) × 100.

        CV > 100% indica alta dispersión (ej: sector financiero).
        """
        media = EstadisticasPonderadas.media(valores, pesos)
        if np.isnan(media) or media == 0:
            return np.nan
        std = EstadisticasPonderadas.desviacion_estandar(valores, pesos)
        return float(std / media * 100)

    @staticmethod
    def suma(df: pd.DataFrame, mask: pd.Series, col_peso: str = "FEX_ADJ") -> float:
        """Suma ponderada filtrada por una máscara.

        Uso típico: w_sum(df, df['OCI']==1) → total de ocupados expandidos.
        """
        return float(df.loc[mask, col_peso].sum())

    @staticmethod
    def resumen_completo(
        valores: pd.Series,
        pesos: pd.Series,
        smmlv: int = 1_423_500,
    ) -> dict[str, Any]:
        """Calcula todas las estadísticas descriptivas ponderadas.

        Retorna un diccionario listo para convertir en fila de DataFrame.

        Args:
            valores: Serie con la variable de interés (ej: INGLABO).
            pesos: Serie con los pesos (FEX_ADJ).
            smmlv: SMMLV para expresar en múltiplos.

        Returns:
            Dict con N_personas, Media, Mediana, P10-P90, Std, CV%, etc.
        """
        ep = EstadisticasPonderadas
        n_pond = pesos[pesos.notna() & (pesos > 0)].sum()
        if n_pond == 0:
            return {}
        media = ep.media(valores, pesos)
        mediana = ep.mediana(valores, pesos)
        std = ep.desviacion_estandar(valores, pesos)
        cv = ep.coeficiente_variacion(valores, pesos)
        p10 = ep.percentil(valores, pesos, 0.10)
        p25 = ep.percentil(valores, pesos, 0.25)
        p75 = ep.percentil(valores, pesos, 0.75)
        p90 = ep.percentil(valores, pesos, 0.90)
        return {
            "N_personas": round(n_pond / 1_000),
            "Media": round(media),
            "Mediana": round(mediana),
            "P10": round(p10),
            "P25": round(p25),
            "P75": round(p75),
            "P90": round(p90),
            "Std": round(std),
            "CV_%": round(cv, 1),
            "IQR": round(p75 - p25),
            "Media_SMMLV": round(media / smmlv, 2),
            "Mediana_SMMLV": round(mediana / smmlv, 2),
        }

    @staticmethod
    def gini(valores: pd.Series, pesos: pd.Series) -> float:
        """Coeficiente de Gini del ingreso laboral (ponderado).

        Gini = 1 − 2 × ∫₀¹ L(p) dp
        Donde L(p) es la curva de Lorenz.

        Returns:
            Float entre 0 (igualdad perfecta) y 1 (máxima desigualdad).
        """
        mask = valores.notna() & pesos.notna() & (pesos > 0) & (valores > 0)
        v = valores[mask].values
        w = pesos[mask].values
        if len(v) < 2:
            return np.nan
        idx = np.argsort(v)
        v, w = v[idx], w[idx]
        acum_w = np.cumsum(w)
        acum_vw = np.cumsum(v * w)
        total_w = acum_w[-1]
        total_vw = acum_vw[-1]
        # Proporción acumulada de población y de ingreso
        p = acum_w / total_w
        # l = acum_vw / total_vw
        lorenz = acum_vw / total_vw
        # Gini usando la regla del trapecio
        # np.trapz fue renombrado a np.trapezoid en NumPy ≥ 2.0
        _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))
        gini_val = 1.0 - 2.0 * _trapz(lorenz, p)
        return float(gini_val)


# ════════════════════════════════════════════════════════════════════════════
# 📄 geih/visualizacion.py
#    Categoría: codigo
