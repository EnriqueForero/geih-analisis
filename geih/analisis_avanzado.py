"""
geih.analisis_avanzado — Módulos de análisis avanzado M5–M20 + A/B/C.

Contiene TODOS los módulos temáticos que faltaban en la primera versión:
  - CalidadEmpleo (ICE, ICF)
  - CompetitividadLaboral (ICI, ITAT)
  - VulnerabilidadLaboral (IVI)
  - AnalisisSubempleo (M9)
  - AnalisisHoras (M10)
  - Estacionalidad (M11)
  - FuerzaLaboralJoven (M12)
  - DashboardSectores (M14)
  - EtnicoRacial (M15)
  - BonoDesaparecido (M18)
  - CostoLaboral (M19)
  - AnalisisFFT (fuera fuerza de trabajo)
  - AnalisisUrbanoRural (M4 expandido)
  - ProductividadTamano (M3 expandido)
  - ContribucionSectorial (Módulo A)
  - MapaTalento (Módulo B — ITAT)
  - EcuacionMincer (Módulo C)
  - ProxyBilinguismo

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "CalidadEmpleo",
    "FormalidadSectorial",
    "VulnerabilidadLaboral",
    "CompetitividadLaboral",
    "AnalisisSubempleo",
    "AnalisisHoras",
    "Estacionalidad",
    "FuerzaLaboralJoven",
    "EtnicoRacial",
    "BonoDemografico",
    "CostoLaboral",
    "AnalisisFFT",
    "AnalisisUrbanoRural",
    "ProductividadTamano",
    "ContribucionSectorial",
    "MapaTalento",
    "EcuacionMincer",
    "ProxyBilinguismo",
]


from typing import Any, Optional

import numpy as np
import pandas as pd

from .config import (
    CARGA_PRESTACIONAL,
    DEPARTAMENTOS,
    TAMANO_EMPRESA,
    ConfigGEIH,
)
from .utils import EstadisticasPonderadas as EP

# ═════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES INTERNAS
# ═════════════════════════════════════════════════════════════════════


def _norm_min_max(serie: pd.Series, invertir: bool = False) -> pd.Series:
    """Normalización min-max [0, 100]. Invierte si menor = mejor."""
    mn, mx = serie.min(), serie.max()
    if mx == mn:
        return pd.Series(50.0, index=serie.index)
    norm = (serie - mn) / (mx - mn) * 100
    return 100 - norm if invertir else norm


def _tasa_ponderada(df, mask_condicion, mask_universo, col_peso="FEX_ADJ"):
    """Calcula % ponderado = Σ(FEX condición) / Σ(FEX universo) × 100."""
    num = df.loc[mask_condicion, col_peso].sum()
    den = df.loc[mask_universo, col_peso].sum()
    return (num / den * 100) if den > 0 else np.nan


# ═════════════════════════════════════════════════════════════════════
# M7 · ICE — ÍNDICE DE CALIDAD DEL EMPLEO
# ═════════════════════════════════════════════════════════════════════


class CalidadEmpleo:
    """ICE = 0.30×Pensión + 0.25×Salud + 0.25×Horas_adecuadas + 0.20×Ingreso≥SML.

    Calcula a nivel de departamento, rama, o nacional.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular_por_departamento(self, df: pd.DataFrame) -> pd.DataFrame:
        """ICE promedio por departamento."""
        df_ocu = df[df["OCI"] == 1].copy()
        filas = []
        for dpto, nombre in DEPARTAMENTOS.items():
            m = (
                df_ocu["DPTO_STR"] == dpto
                if "DPTO_STR" in df_ocu.columns
                else pd.Series(False, index=df_ocu.index)
            )
            n = df_ocu.loc[m, "FEX_ADJ"].sum()
            if n < 5_000:
                continue
            ice = self._calcular_ice(df_ocu[m])
            filas.append({"Departamento": nombre, "DPTO": dpto, "ICE": ice, "Ocupados_M": n / 1e6})
        return pd.DataFrame(filas).sort_values("ICE", ascending=False)

    def calcular_por_rama(self, df: pd.DataFrame) -> pd.DataFrame:
        """ICE promedio por rama de actividad."""
        df_ocu = df[(df["OCI"] == 1) & df["RAMA"].notna()].copy()
        filas = []
        for rama in df_ocu["RAMA"].unique():
            m = df_ocu["RAMA"] == rama
            ice = self._calcular_ice(df_ocu[m])
            n = df_ocu.loc[m, "FEX_ADJ"].sum()
            filas.append({"Rama": rama, "ICE": ice, "Ocupados_M": n / 1e6})
        return pd.DataFrame(filas).sort_values("ICE", ascending=False)

    def _calcular_ice(self, df_ocu: pd.DataFrame) -> float:
        """Calcula ICE promedio ponderado para un subconjunto."""
        fex = df_ocu["FEX_ADJ"]
        total = fex.sum()
        if total == 0:
            return np.nan
        d_pen = (df_ocu.get("P6920", pd.Series(dtype=float)) == 1).astype(float)
        d_sal = (df_ocu.get("P6090", pd.Series(dtype=float)) == 1).astype(float)
        d_hor = df_ocu.get("P6800", pd.Series(dtype=float)).between(20, 48).astype(float)
        d_ing = (df_ocu.get("INGLABO", pd.Series(dtype=float)) >= self.config.smmlv).astype(float)
        ice = 0.30 * d_pen + 0.25 * d_sal + 0.25 * d_hor + 0.20 * d_ing
        return float((ice * fex).sum() / total * 100)


# ═════════════════════════════════════════════════════════════════════
# M13 · ICF — ÍNDICE DE FORMALIDAD SECTORIAL
# ═════════════════════════════════════════════════════════════════════


class FormalidadSectorial:
    """ICF = Media(% cotiza pensión, % ingreso ≥ SMMLV, % afiliado salud)."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df_ocu = df[(df["OCI"] == 1) & df["RAMA"].notna()].copy()
        filas = []
        for rama in df_ocu["RAMA"].unique():
            m_r = df_ocu["RAMA"] == rama
            n = df_ocu.loc[m_r, "FEX_ADJ"].sum()
            if n < 5_000:
                continue
            pct_pen = _tasa_ponderada(df_ocu, m_r & (df_ocu.get("P6920", 0) == 1), m_r)
            pct_sal = _tasa_ponderada(df_ocu, m_r & (df_ocu.get("P6090", 0) == 1), m_r)
            pct_ing = _tasa_ponderada(
                df_ocu, m_r & (df_ocu.get("INGLABO", 0) >= self.config.smmlv), m_r
            )
            icf = np.nanmean([pct_pen, pct_sal, pct_ing])
            filas.append(
                {
                    "Rama": rama,
                    "ICF": round(icf, 1),
                    "Cotiza_pension_%": round(pct_pen, 1),
                    "Ingreso_SML_%": round(pct_ing, 1),
                    "Afiliado_salud_%": round(pct_sal, 1),
                }
            )
        return pd.DataFrame(filas).sort_values("ICF", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# M20 · IVI — ÍNDICE DE VULNERABILIDAD LABORAL
# ═════════════════════════════════════════════════════════════════════


class VulnerabilidadLaboral:
    """IVI = Media(% cta_propia sin pensión, % sin protección, % sobretrabajo, % <SMMLV)."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df_ocu = df[(df["OCI"] == 1) & df["RAMA"].notna()].copy()
        filas = []
        for rama in df_ocu["RAMA"].unique():
            m_r = df_ocu["RAMA"] == rama
            n = df_ocu.loc[m_r, "FEX_ADJ"].sum()
            if n < 5_000:
                continue
            pct_cta_sin_pen = _tasa_ponderada(
                df_ocu, m_r & (df_ocu.get("P6430", 0) == 4) & (df_ocu.get("P6920", 0) != 1), m_r
            )
            pct_sobretrab = _tasa_ponderada(df_ocu, m_r & (df_ocu.get("P6800", 0) > 48), m_r)
            pct_sub_sml = _tasa_ponderada(
                df_ocu,
                m_r
                & (df_ocu.get("INGLABO", 0) < self.config.smmlv)
                & (df_ocu.get("INGLABO", 0) > 0),
                m_r,
            )
            pct_sin_prot = _tasa_ponderada(
                df_ocu, m_r & (df_ocu.get("P6920", 0) != 1) & (df_ocu.get("P6090", 0) != 1), m_r
            )
            ivi = np.nanmean([pct_cta_sin_pen, pct_sobretrab, pct_sub_sml, pct_sin_prot])
            filas.append({"Rama": rama, "IVI": round(ivi, 1), "Ocupados_miles": round(n / 1_000)})
        return pd.DataFrame(filas).sort_values("IVI", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# M16 · ICI — COMPETITIVIDAD LABORAL DEPARTAMENTAL
# ═════════════════════════════════════════════════════════════════════


class CompetitividadLaboral:
    """ICI = 0.25·TD + 0.20·Costo + 0.25·Talento + 0.20·Formalidad + 0.10·Jóvenes.

    Scores normalizados min-max [0,100]. Costo INVERTIDO (menor=mejor).
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        filas = []
        for dpto, nombre in DEPARTAMENTOS.items():
            col_dpto = "DPTO_STR" if "DPTO_STR" in df.columns else "DPTO"
            m = df[col_dpto] == dpto
            n = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            if n < 10_000:
                continue
            df.loc[m & (df.get("PET", pd.Series(dtype=float)) == 1), "FEX_ADJ"].sum()
            pea = df.loc[m & (df.get("FT", pd.Series(dtype=float)) == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", pd.Series(dtype=float)) == 1), "FEX_ADJ"].sum()
            td = (des / pea * 100) if pea > 0 else np.nan
            mediana = EP.mediana(
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "INGLABO"],
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "FEX_ADJ"],
            )
            costo = mediana * (1 + CARGA_PRESTACIONAL) if not np.isnan(mediana) else np.nan
            pct_univ = _tasa_ponderada(
                df, m & (df.get("P3042", 0) >= 10) & (df["OCI"] == 1), m & (df["OCI"] == 1)
            )
            pct_pen = _tasa_ponderada(
                df, m & (df.get("P6920", 0) == 1) & (df["OCI"] == 1), m & (df["OCI"] == 1)
            )
            pct_jov = _tasa_ponderada(
                df,
                m & df.get("P6040", pd.Series(dtype=float)).between(15, 28) & (df["OCI"] == 1),
                m & (df["OCI"] == 1),
            )
            filas.append(
                {
                    "Departamento": nombre,
                    "DPTO": dpto,
                    "TD_%": round(td, 1) if not np.isnan(td) else np.nan,
                    "Costo_efectivo": round(costo) if not np.isnan(costo) else np.nan,
                    "Talento_univ_%": round(pct_univ, 1),
                    "Formalidad_%": round(pct_pen, 1),
                    "Jovenes_%": round(pct_jov, 1),
                    "Ocupados_miles": round(n / 1_000),
                }
            )

        resultado = pd.DataFrame(filas).dropna(subset=["TD_%", "Costo_efectivo"])
        if resultado.empty:
            return resultado
        resultado["Score_TD"] = _norm_min_max(resultado["TD_%"], invertir=True)
        resultado["Score_Costo"] = _norm_min_max(resultado["Costo_efectivo"], invertir=True)
        resultado["Score_Talento"] = _norm_min_max(resultado["Talento_univ_%"])
        resultado["Score_Formal"] = _norm_min_max(resultado["Formalidad_%"])
        resultado["Score_Joven"] = _norm_min_max(resultado["Jovenes_%"])
        resultado["ICI"] = (
            0.25 * resultado["Score_TD"]
            + 0.20 * resultado["Score_Costo"]
            + 0.25 * resultado["Score_Talento"]
            + 0.20 * resultado["Score_Formal"]
            + 0.10 * resultado["Score_Joven"]
        ).round(1)
        return resultado.sort_values("ICI", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# M9 · SUBEMPLEO
# ═════════════════════════════════════════════════════════════════════


class AnalisisSubempleo:
    """Subempleo por horas, ingresos y competencias."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> dict[str, Any]:
        df_ocu = df[df["OCI"] == 1].copy()
        n_ocu = df_ocu["FEX_ADJ"].sum()
        resultado = {"Ocupados_M": n_ocu / 1e6}
        if "P6800" in df_ocu.columns:
            sub_horas = _tasa_ponderada(
                df_ocu, (df_ocu["P6800"] < 32), pd.Series(True, index=df_ocu.index)
            )
            resultado["Subempleo_horas_%"] = round(sub_horas, 1)
        if "INGLABO" in df_ocu.columns:
            sub_ing = _tasa_ponderada(
                df_ocu,
                (df_ocu["INGLABO"] > 0) & (df_ocu["INGLABO"] < self.config.smmlv),
                (df_ocu["INGLABO"] > 0),
            )
            resultado["Sub_SMMLV_%"] = round(sub_ing, 1)
        return resultado


# ═════════════════════════════════════════════════════════════════════
# M10 · HORAS TRABAJADAS
# ═════════════════════════════════════════════════════════════════════


class AnalisisHoras:
    """Distribución de horas trabajadas (P6800 normales, P6850 reales)."""

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df_ocu = df[(df["OCI"] == 1) & df.get("P6800", pd.Series(dtype=float)).notna()].copy()
        rangos = [
            (0, 20, "<20h"),
            (20, 32, "20-32h"),
            (32, 40, "32-40h"),
            (40, 48, "40-48h"),
            (48, 60, "48-60h"),
            (60, 200, ">60h"),
        ]
        filas = []
        total = df_ocu["FEX_ADJ"].sum()
        for lo, hi, etiq in rangos:
            m = df_ocu["P6800"].between(lo, hi, inclusive="left")
            n = df_ocu.loc[m, "FEX_ADJ"].sum()
            filas.append(
                {
                    "Rango_horas": etiq,
                    "Personas_M": round(n / 1e6, 2),
                    "Pct": round(n / total * 100, 1),
                }
            )
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# M11 · ESTACIONALIDAD MENSUAL
# ═════════════════════════════════════════════════════════════════════


class Estacionalidad:
    """Serie mensual de TD, TO, TGP usando MES_NUM y FEX_C18 sin dividir."""

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "MES_NUM" not in df.columns:
            print("⚠️ MES_NUM no disponible")
            return pd.DataFrame()
        filas = []
        for mes in sorted(df["MES_NUM"].dropna().unique()):
            m = df["MES_NUM"] == mes
            # Usar FEX_C18 sin dividir para indicador puntual
            fex = "FEX_C18"
            pea = df.loc[m & (df.get("FT", 0) == 1), fex].sum()
            ocu = df.loc[m & (df["OCI"] == 1), fex].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), fex].sum()
            pet = df.loc[m & (df.get("PET", 0) == 1), fex].sum()
            filas.append(
                {
                    "MES": int(mes),
                    "PEA_M": round(pea / 1e6, 2),
                    "Ocupados_M": round(ocu / 1e6, 2),
                    "TD_%": round(des / pea * 100, 1) if pea > 0 else np.nan,
                    "TGP_%": round(pea / pet * 100, 1) if pet > 0 else np.nan,
                    "TO_%": round(ocu / pet * 100, 1) if pet > 0 else np.nan,
                }
            )
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# M12 · FUERZA LABORAL JOVEN (15-28 AÑOS)
# ═════════════════════════════════════════════════════════════════════


class FuerzaLaboralJoven:
    """TD, TO, TGP para jóvenes 15-28 años, nacional y por departamento."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> dict[str, Any]:
        m_jov = df.get("P6040", pd.Series(dtype=float)).between(15, 28)
        df_jov = df[m_jov].copy()
        pea = df_jov.loc[df_jov.get("FT", 0) == 1, "FEX_ADJ"].sum()
        ocu = df_jov.loc[df_jov["OCI"] == 1, "FEX_ADJ"].sum()
        des = df_jov.loc[df_jov.get("DSI", 0) == 1, "FEX_ADJ"].sum()
        td = (des / pea * 100) if pea > 0 else np.nan
        return {
            "TD_joven_%": round(td, 1),
            "Ocupados_joven_M": round(ocu / 1e6, 2),
            "PEA_joven_M": round(pea / 1e6, 2),
        }


# ═════════════════════════════════════════════════════════════════════
# M15 · AUTORRECONOCIMIENTO ÉTNICO-RACIAL
# ═════════════════════════════════════════════════════════════════════


class EtnicoRacial:
    """Indicadores laborales por grupo étnico (P6080)."""

    GRUPOS = {1: "Indígena", 3: "Raizal", 4: "Palenquero", 5: "Negro/Afrocolombiano", 6: "Ninguno"}

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "P6080" not in df.columns:
            print("⚠️ P6080 no disponible")
            return pd.DataFrame()
        filas = []
        for cod, nombre in self.GRUPOS.items():
            m = df["P6080"] == cod
            pea = df.loc[m & (df.get("FT", 0) == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
            ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            td = (des / pea * 100) if pea > 0 else np.nan
            mediana = EP.mediana(
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "INGLABO"],
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "FEX_ADJ"],
            )
            filas.append(
                {
                    "Grupo": nombre,
                    "TD_%": round(td, 1),
                    "Mediana_COP": round(mediana) if not np.isnan(mediana) else np.nan,
                    "Ocupados_M": round(ocu / 1e6, 2),
                }
            )
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# M18 · BONO DEMOGRÁFICO
# ═════════════════════════════════════════════════════════════════════


class BonoDemografico:
    """Ratio de dependencia económica = (Desocupados + FFT) / Ocupados."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        filas = []
        for dpto, nombre in DEPARTAMENTOS.items():
            col_dpto = "DPTO_STR" if "DPTO_STR" in df.columns else "DPTO"
            m = df[col_dpto] == dpto
            ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
            fft = df.loc[m & (df.get("FFT", 0) == 1), "FEX_ADJ"].sum() if "FFT" in df.columns else 0
            ratio = (des + fft) / ocu if ocu > 0 else np.nan
            if not np.isnan(ratio):
                filas.append(
                    {
                        "Departamento": nombre,
                        "Ratio_dependencia": round(ratio, 2),
                        "Ocupados_M": round(ocu / 1e6, 2),
                    }
                )
        return pd.DataFrame(filas).sort_values("Ratio_dependencia")


# ═════════════════════════════════════════════════════════════════════
# M19 · COSTO LABORAL EFECTIVO
# ═════════════════════════════════════════════════════════════════════


class CostoLaboral:
    """Costo_efectivo = Salario_mediano × (1 + 0.54 carga prestacional)."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df_ocu = df[(df["OCI"] == 1) & (df["INGLABO"] > 0) & df["RAMA"].notna()].copy()
        filas = []
        for rama in df_ocu["RAMA"].unique():
            m = df_ocu["RAMA"] == rama
            mediana = EP.mediana(df_ocu.loc[m, "INGLABO"], df_ocu.loc[m, "FEX_ADJ"])
            if np.isnan(mediana):
                continue
            costo = mediana * (1 + CARGA_PRESTACIONAL)
            filas.append(
                {
                    "Rama": rama,
                    "Mediana_COP": round(mediana),
                    "Costo_efectivo_COP": round(costo),
                    "Mediana_SMMLV": round(mediana / self.config.smmlv, 2),
                    "Costo_SMMLV": round(costo / self.config.smmlv, 2),
                }
            )
        return pd.DataFrame(filas).sort_values("Costo_efectivo_COP", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# FFT — FUERA DE LA FUERZA DE TRABAJO
# ═════════════════════════════════════════════════════════════════════


class AnalisisFFT:
    """Personas fuera de la fuerza de trabajo por tipo de actividad."""

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "FFT" not in df.columns:
            print("⚠️ FFT no disponible")
            return pd.DataFrame()
        df_fft = df[df["FFT"] == 1].copy()
        total = df_fft["FEX_ADJ"].sum()
        resultado = {"Total_FFT_M": round(total / 1e6, 2)}
        # Desagregación por sexo
        for sexo_val, sexo_lbl in [(1, "Hombres"), (2, "Mujeres")]:
            n = df_fft.loc[df_fft["P3271"] == sexo_val, "FEX_ADJ"].sum()
            resultado[f"FFT_{sexo_lbl}_M"] = round(n / 1e6, 2)
        return pd.DataFrame([resultado])


# ═════════════════════════════════════════════════════════════════════
# URBANO VS RURAL
# ═════════════════════════════════════════════════════════════════════


class AnalisisUrbanoRural:
    """Comparativo mercado laboral urbano (CLASE=1) vs rural (CLASE=2)."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "CLASE" not in df.columns:
            print("⚠️ CLASE no disponible")
            return pd.DataFrame()
        filas = []
        for clase, etiq in [(1, "Urbano"), (2, "Rural")]:
            # CLASE puede ser str o int
            m = df["CLASE"].astype(str) == str(clase)
            pea = df.loc[m & (df.get("FT", 0) == 1), "FEX_ADJ"].sum()
            ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
            pet = df.loc[m & (df.get("PET", 0) == 1), "FEX_ADJ"].sum()
            mediana = EP.mediana(
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "INGLABO"],
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "FEX_ADJ"],
            )
            filas.append(
                {
                    "Zona": etiq,
                    "TD_%": round(des / pea * 100, 1) if pea > 0 else np.nan,
                    "TGP_%": round(pea / pet * 100, 1) if pet > 0 else np.nan,
                    "TO_%": round(ocu / pet * 100, 1) if pet > 0 else np.nan,
                    "Mediana_SMMLV": round(mediana / self.config.smmlv, 2)
                    if not np.isnan(mediana)
                    else np.nan,
                    "Ocupados_M": round(ocu / 1e6, 2),
                }
            )
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# PRODUCTIVIDAD POR TAMAÑO DE EMPRESA
# ═════════════════════════════════════════════════════════════════════


class ProductividadTamano:
    """Salario mediano y formalidad por tamaño de empresa (P3069)."""

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "P3069" not in df.columns:
            print("⚠️ P3069 no disponible")
            return pd.DataFrame()
        df_ocu = df[(df["OCI"] == 1)].copy()
        filas = []
        for cod, etiq in TAMANO_EMPRESA.items():
            m = df_ocu["P3069"] == cod
            n = df_ocu.loc[m, "FEX_ADJ"].sum()
            if n < 5_000:
                continue
            mediana = EP.mediana(
                df_ocu.loc[m & (df_ocu["INGLABO"] > 0), "INGLABO"],
                df_ocu.loc[m & (df_ocu["INGLABO"] > 0), "FEX_ADJ"],
            )
            pct_pen = _tasa_ponderada(df_ocu, m & (df_ocu.get("P6920", 0) == 1), m)
            filas.append(
                {
                    "Tamano": etiq,
                    "Cod": cod,
                    "Mediana_SMMLV": round(mediana / self.config.smmlv, 2)
                    if not np.isnan(mediana)
                    else np.nan,
                    "Formalidad_%": round(pct_pen, 1),
                    "Ocupados_miles": round(n / 1_000),
                }
            )
        return pd.DataFrame(filas).sort_values("Cod")


# ═════════════════════════════════════════════════════════════════════
# MÓDULO A · CONTRIBUCIÓN SECTORIAL AL EMPLEO
# ═════════════════════════════════════════════════════════════════════


class ContribucionSectorial:
    """Contribución de cada rama al cambio mensual del empleo (en p.p.)."""

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "MES_NUM" not in df.columns or "RAMA" not in df.columns:
            print("⚠️ MES_NUM o RAMA no disponibles")
            return pd.DataFrame()
        # Empleo por rama y mes (usando FEX_C18 sin dividir)
        pivot = (
            df[(df["OCI"] == 1) & df["RAMA"].notna()]
            .groupby(["MES_NUM", "RAMA"])["FEX_C18"]
            .sum()
            .unstack(fill_value=0)
        )
        pea_mes = df[df.get("FT", pd.Series(dtype=float)) == 1].groupby("MES_NUM")["FEX_C18"].sum()
        # Contribución = (Emp_rama_t - Emp_rama_t-1) / PEA_t-1
        contrib = pivot.diff()
        for mes in contrib.index:
            if mes - 1 in pea_mes.index:
                contrib.loc[mes] = contrib.loc[mes] / pea_mes.loc[mes - 1] * 100
        return contrib.round(3)


# ═════════════════════════════════════════════════════════════════════
# MÓDULO B · MAPA DE TALENTO (ITAT)
# ═════════════════════════════════════════════════════════════════════


class MapaTalento:
    """ITAT = 0.35·Oferta + 0.35·Costo + 0.30·Calidad.

    Cada departamento es evaluado por: oferta (desocupados + subempleados),
    costo (mediana salarial invertida), calidad (% universitarios).
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        filas = []
        col_dpto = "DPTO_STR" if "DPTO_STR" in df.columns else "DPTO"
        for dpto, nombre in DEPARTAMENTOS.items():
            m = df[col_dpto] == dpto
            ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
            if ocu < 10_000:
                continue
            oferta = des  # + subempleados si disponible
            mediana = EP.mediana(
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "INGLABO"],
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "FEX_ADJ"],
            )
            pct_univ = _tasa_ponderada(
                df, m & (df.get("P3042", 0) >= 10) & (df["OCI"] == 1), m & (df["OCI"] == 1)
            )
            filas.append(
                {
                    "Departamento": nombre,
                    "Oferta_miles": round(oferta / 1_000),
                    "Costo_mediano": round(mediana) if not np.isnan(mediana) else np.nan,
                    "Calidad_univ_%": round(pct_univ, 1),
                }
            )
        resultado = pd.DataFrame(filas).dropna()
        if resultado.empty:
            return resultado
        resultado["Score_Oferta"] = _norm_min_max(resultado["Oferta_miles"])
        resultado["Score_Costo"] = _norm_min_max(resultado["Costo_mediano"], invertir=True)
        resultado["Score_Calidad"] = _norm_min_max(resultado["Calidad_univ_%"])
        resultado["ITAT"] = (
            0.35 * resultado["Score_Oferta"]
            + 0.35 * resultado["Score_Costo"]
            + 0.30 * resultado["Score_Calidad"]
        ).round(1)
        return resultado.sort_values("ITAT", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# MÓDULO C · ECUACIÓN DE MINCER
# ═════════════════════════════════════════════════════════════════════


class EcuacionMincer:
    """ln(W) = β₀ + β₁·Educ + β₂·Exp + β₃·Exp² (WLS con FEX como peso).

    β₁ = % de aumento salarial por cada año adicional de educación.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def estimar(self, df: pd.DataFrame, grupo: str = "Nacional") -> dict[str, Any]:
        """Estima la ecuación de Mincer para un subconjunto.

        Requiere: INGLABO > 0, ANOS_EDUC, P6040 (edad para calcular experiencia).

        Returns:
            Dict con beta_educacion, SE, R2, N.
        """
        df_calc = df[
            (df["OCI"] == 1) & (df["INGLABO"] > 0) & df["ANOS_EDUC"].notna() & df["P6040"].notna()
        ].copy()

        if len(df_calc) < 100:
            return {"Grupo": grupo, "beta_educacion": np.nan, "N": len(df_calc)}

        df_calc["LN_W"] = np.log(df_calc["INGLABO"])
        df_calc["EXP"] = (df_calc["P6040"] - df_calc["ANOS_EDUC"] - 6).clip(lower=0)
        df_calc["EXP2"] = df_calc["EXP"] ** 2

        try:
            from numpy.linalg import lstsq

            X = df_calc[["ANOS_EDUC", "EXP", "EXP2"]].values
            X = np.column_stack([np.ones(len(X)), X])
            y = df_calc["LN_W"].values
            w = np.sqrt(df_calc["FEX_ADJ"].values)
            Xw = X * w[:, np.newaxis]
            yw = y * w
            betas, residuals, rank, sv = lstsq(Xw, yw, rcond=None)
            y_pred = X @ betas
            ss_res = ((y - y_pred) ** 2 * df_calc["FEX_ADJ"].values).sum()
            y_mean = (y * df_calc["FEX_ADJ"].values).sum() / df_calc["FEX_ADJ"].sum()
            ss_tot = ((y - y_mean) ** 2 * df_calc["FEX_ADJ"].values).sum()
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
            return {
                "Grupo": grupo,
                "beta_educacion": round(betas[1] * 100, 1),
                "beta_exp": round(betas[2] * 100, 2),
                "R2": round(r2, 3),
                "N": len(df_calc),
            }
        except Exception as e:
            return {"Grupo": grupo, "beta_educacion": np.nan, "error": str(e), "N": len(df_calc)}

    def estimar_todos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Estima Mincer para: Nacional, H, M, Urbano, Rural, por rama."""
        resultados = [self.estimar(df, "Nacional")]

        if "P3271" in df.columns:
            resultados.append(self.estimar(df[df["P3271"] == 1], "Hombres"))
            resultados.append(self.estimar(df[df["P3271"] == 2], "Mujeres"))

        if "CLASE" in df.columns:
            resultados.append(self.estimar(df[df["CLASE"].astype(str) == "1"], "Urbano"))
            resultados.append(self.estimar(df[df["CLASE"].astype(str) == "2"], "Rural"))

        if "RAMA" in df.columns:
            for rama in df["RAMA"].dropna().unique():
                resultados.append(self.estimar(df[df["RAMA"] == rama], f"Rama: {rama}"))

        return pd.DataFrame(resultados).sort_values("beta_educacion", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# PROXY DE BILINGÜISMO
# ═════════════════════════════════════════════════════════════════════


class ProxyBilinguismo:
    """Tres proxies para estimar bilingüismo con los datos disponibles en GEIH.

    Proxy 1: Formación en idiomas (códigos CINE-F 22x en P3043S1)
    Proxy 2: Demanda laboral (sectores TIC/BPO + universidad)
    Proxy 3: Perfil alta exposición (asalariado privado + sector + universidad)
    """

    SECTORES_INGLES = [
        "TIC/Información",
        "Información y comunicaciones",
        "Financiero",
        "Actividades financieras y de seguros",
    ]

    def calcular(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Calcula los tres proxies por departamento/ciudad.

        Returns:
            Dict con 'proxy1', 'proxy2', 'proxy3' como DataFrames.
        """
        df_pet = df[df.get("P6040", pd.Series(dtype=float)) >= 15].copy()
        resultados = {}

        # Proxy 1: Códigos 22x (formación en idiomas)
        if "P3043S1" in df_pet.columns:
            cod_campo = pd.to_numeric(df_pet["P3043S1"], errors="coerce")
            df_pet["PROXY1"] = cod_campo.apply(
                lambda x: 1.0 if (not pd.isna(x) and str(int(x)).startswith("22")) else 0.0
            )
            n_p1 = (df_pet["PROXY1"] == 1).sum()
            print(f"   Proxy 1 (códigos 22x): {n_p1:,} registros")
            resultados["proxy1_total"] = n_p1

        # Proxy 2: Sectores + universidad
        if "RAMA" in df_pet.columns and "P3042" in df_pet.columns:
            mask_sector = df_pet["RAMA"].isin(self.SECTORES_INGLES)
            mask_univ = df_pet.get("P3042", pd.Series(dtype=float)) >= 10
            df_pet["PROXY2"] = ((mask_sector & mask_univ) & (df_pet["OCI"] == 1)).astype(float)
            n_p2 = (df_pet["PROXY2"] == 1).sum()
            print(f"   Proxy 2 (sector+univ): {n_p2:,} registros")
            resultados["proxy2_total"] = n_p2

        # Proxy 3: Asalariado privado + sector + universidad
        if "P6430" in df_pet.columns:
            mask_asalariado = df_pet.get("P6430", pd.Series(dtype=float)) == 1
            df_pet["PROXY3"] = (
                mask_asalariado
                & df_pet.get("PROXY2", pd.Series(0, index=df_pet.index)).astype(bool)
            ).astype(float)
            n_p3 = (df_pet["PROXY3"] == 1).sum()
            print(f"   Proxy 3 (asalariado): {n_p3:,} registros")
            resultados["proxy3_total"] = n_p3

        # Resumen por departamento
        if "NOMBRE_DPTO" in df_pet.columns:
            proxy_col = "PROXY2" if "PROXY2" in df_pet.columns else "PROXY1"
            if proxy_col in df_pet.columns:
                dept_resumen = []
                for dpto in df_pet["NOMBRE_DPTO"].dropna().unique():
                    m = df_pet["NOMBRE_DPTO"] == dpto
                    total = df_pet.loc[m & (df_pet["OCI"] == 1), "FEX_ADJ"].sum()
                    proxy = df_pet.loc[m & (df_pet[proxy_col] == 1), "FEX_ADJ"].sum()
                    if total > 10_000:
                        dept_resumen.append(
                            {
                                "Departamento": dpto,
                                f"Pct_{proxy_col}_%": round(proxy / total * 100, 1),
                                "Ocupados_miles": round(total / 1_000),
                            }
                        )
                resultados["por_departamento"] = pd.DataFrame(dept_resumen).sort_values(
                    f"Pct_{proxy_col}_%", ascending=False
                )

        return resultados
