# -*- coding: utf-8 -*-
"""
geih.analisis_poblacional — Análisis de poblaciones y módulos especiales.

Cubre los grupos poblacionales y módulos que la GEIH mide pero que
rara vez se explotan en los análisis estándar de mercado laboral:

  - AnalisisCampesino    → P2057/P2059 (autodefinición campesina)
  - AnalisisDiscapacidad → P1906S1-S8 (escala Washington)
  - AnalisisMigracion    → P3370-P3379 (migración interna e internacional)
  - AnalisisOtrasFormas  → P3054-P3057 (autoconsumo, voluntariado, formación)
  - AnalisisOtrosIngresos → P7422-P7510 (ingresos no laborales)
  - AnalisisSobrecalificacion → P3042 × P6430 (universitarios en empleos simples)
  - AnalisisContractual  → P6440/P6450/P6460/P6765 (formalidad contractual real)
  - AnalisisAutonomia    → P3047/P3048/P3049 (contratista dependiente)
  - AnalisisAlcanceMercado → P1802 (local → exportación)
  - AnalisisDesanimados  → P6300/P6310 (FFT pero desean trabajar)

Cada clase sigue el patrón: recibe DataFrame preparado → retorna DataFrame de resultados.
No modifica el DataFrame original. No genera gráficos.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "AnalisisCampesino",
    "AnalisisDiscapacidad",
    "AnalisisMigracion",
    "AnalisisOtrasFormas",
    "AnalisisOtrosIngresos",
    "AnalisisSobrecalificacion",
    "AnalisisContractual",
    "AnalisisAutonomia",
    "AnalisisAlcanceMercado",
    "AnalisisDesanimados",
]


import gc
from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd

from .config import ConfigGEIH, SMMLV_2025, DEPARTAMENTOS
from .utils import EstadisticasPonderadas as EP


def _tasa(df, mask_num, mask_den, col_peso="FEX_ADJ"):
    n = df.loc[mask_num, col_peso].sum()
    d = df.loc[mask_den, col_peso].sum()
    return (n / d * 100) if d > 0 else np.nan


# ═════════════════════════════════════════════════════════════════════
# POBLACIÓN CAMPESINA (P2057 / P2059)
# ═════════════════════════════════════════════════════════════════════

class AnalisisCampesino:
    """Análisis del mercado laboral de la población campesina.

    P2057: ¿Usted se considera campesino(a)? (1=Sí, 2=No)
    P2059: ¿Alguna vez fue campesino? (1=Sí, 2=No)

    Incluido en GEIH desde el rediseño 2022 por mandato del PND.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Indicadores laborales para campesinos vs no campesinos."""
        if "P2057" not in df.columns:
            print("⚠️ P2057 no disponible. Incluir módulo Características generales.")
            return pd.DataFrame()

        filas = []
        for val, etiq in [(1, "Se considera campesino"), (2, "No se considera campesino")]:
            m = df["P2057"] == val
            pea = df.loc[m & (df.get("FT", 0) == 1), "FEX_ADJ"].sum()
            ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
            mediana = EP.mediana(
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "INGLABO"],
                df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "FEX_ADJ"]
            )
            pct_pen = _tasa(df, m & (df.get("P6920", 0) == 1) & (df["OCI"] == 1), m & (df["OCI"] == 1))
            filas.append({
                "Grupo": etiq, "Poblacion_M": round(df.loc[m, "FEX_ADJ"].sum() / 1e6, 2),
                "TD_%": round(des / pea * 100, 1) if pea > 0 else np.nan,
                "Mediana_SMMLV": round(mediana / self.config.smmlv, 2) if not np.isnan(mediana) else np.nan,
                "Formalidad_%": round(pct_pen, 1),
            })
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# DISCAPACIDAD (P1906S1-S8 — ESCALA WASHINGTON)
# ═════════════════════════════════════════════════════════════════════

class AnalisisDiscapacidad:
    """Indicadores laborales por condición de discapacidad.

    P1906S1-S8: 8 dimensiones de dificultad funcional.
    Valores: 1=Sin dificultad, 2=Alguna, 3=Mucha, 4=No puede.
    Criterio ONU: discapacidad = al menos una dimensión con valor 3 o 4.
    """

    DIMENSIONES = {
        "P1906S1": "Oír",      "P1906S2": "Hablar",
        "P1906S3": "Ver",      "P1906S4": "Moverse",
        "P1906S5": "Agarrar",  "P1906S6": "Entender",
        "P1906S7": "Autocuidado", "P1906S8": "Relacionarse",
    }

    def calcular(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Indicadores por presencia de discapacidad (criterio ONU)."""
        dims_ok = [d for d in self.DIMENSIONES if d in df.columns]
        if not dims_ok:
            print("⚠️ Variables P1906S1-S8 no disponibles.")
            return {}

        # Criterio ONU: al menos una dimensión con mucha dificultad (3) o no puede (4)
        mask_disca = pd.Series(False, index=df.index)
        for dim in dims_ok:
            mask_disca = mask_disca | (df[dim].isin([3, 4]))

        resultado = {"dimensiones_disponibles": len(dims_ok)}
        for etiq, m in [("Con discapacidad", mask_disca), ("Sin discapacidad", ~mask_disca)]:
            pea = df.loc[m & (df.get("FT", 0) == 1), "FEX_ADJ"].sum()
            ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
            des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
            td = (des / pea * 100) if pea > 0 else np.nan
            resultado[f"{etiq}_poblacion_M"] = round(df.loc[m, "FEX_ADJ"].sum() / 1e6, 2)
            resultado[f"{etiq}_TD_%"] = round(td, 1)
            resultado[f"{etiq}_ocupados_M"] = round(ocu / 1e6, 2)

        # Prevalencia por dimensión
        prev = {}
        for dim, nombre in self.DIMENSIONES.items():
            if dim in df.columns:
                pct = _tasa(df, df[dim].isin([3, 4]), pd.Series(True, index=df.index))
                prev[nombre] = round(pct, 2)
        resultado["prevalencia_por_dimension"] = prev

        return resultado


# ═════════════════════════════════════════════════════════════════════
# MIGRACIÓN (P3370-P3379)
# ═════════════════════════════════════════════════════════════════════

class AnalisisMigracion:
    """Análisis del mercado laboral por condición migratoria.

    P3370: ¿Dónde vivía hace 12 meses? (1=Mismo municipio, 2=Otro, 3=Otro país)
    P3376: País de nacimiento (170=Colombia, otro=Extranjero)
    P3378S1: Año de llegada a Colombia
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Indicadores por condición migratoria."""
        filas = []

        # Migración reciente (12 meses)
        if "P3370" in df.columns:
            for val, etiq in [(1, "Mismo municipio"), (2, "Otro municipio/dpto"), (3, "Otro país")]:
                m = df["P3370"] == val
                n = df.loc[m, "FEX_ADJ"].sum()
                if n < 5_000:
                    continue
                ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
                des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
                pea = df.loc[m & (df.get("FT", 0) == 1), "FEX_ADJ"].sum()
                td = (des / pea * 100) if pea > 0 else np.nan
                filas.append({
                    "Tipo_migracion": etiq, "Periodo": "12 meses",
                    "Poblacion_M": round(n / 1e6, 2), "TD_%": round(td, 1),
                    "Ocupados_M": round(ocu / 1e6, 2),
                })

        # Nacidos en el extranjero
        if "P3376" in df.columns:
            m_ext = df["P3376"] != 170  # 170 = Colombia
            m_col = df["P3376"] == 170
            for etiq, m in [("Nacido en Colombia", m_col), ("Nacido en el extranjero", m_ext)]:
                n = df.loc[m, "FEX_ADJ"].sum()
                if n < 1_000:
                    continue
                ocu = df.loc[m & (df["OCI"] == 1), "FEX_ADJ"].sum()
                pea = df.loc[m & (df.get("FT", 0) == 1), "FEX_ADJ"].sum()
                des = df.loc[m & (df.get("DSI", 0) == 1), "FEX_ADJ"].sum()
                td = (des / pea * 100) if pea > 0 else np.nan
                mediana = EP.mediana(
                    df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "INGLABO"],
                    df.loc[m & (df["OCI"] == 1) & (df["INGLABO"] > 0), "FEX_ADJ"]
                )
                filas.append({
                    "Tipo_migracion": etiq, "Periodo": "Nacimiento",
                    "Poblacion_M": round(n / 1e6, 2), "TD_%": round(td, 1),
                    "Mediana_SMMLV": round(mediana / self.config.smmlv, 2) if not np.isnan(mediana) else np.nan,
                })

        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# OTRAS FORMAS DE TRABAJO (P3054-P3057)
# ═════════════════════════════════════════════════════════════════════

class AnalisisOtrasFormas:
    """Trabajo no remunerado: autoconsumo, voluntariado, formación.

    P3054: Producción de bienes para autoconsumo (1=Sí)
    P3055: Producción de servicios para autoconsumo (1=Sí)
    P3056: Trabajo voluntario (1=Sí)
    P3057: Trabajo en formación no remunerado (1=Sí)
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prevalencia de otras formas de trabajo."""
        formas = {
            "P3054": "Autoconsumo bienes",
            "P3055": "Autoconsumo servicios",
            "P3056": "Voluntariado",
            "P3057": "Formación no remunerada",
        }
        filas = []
        total = df["FEX_ADJ"].sum()
        for var, nombre in formas.items():
            if var in df.columns:
                n = df.loc[df[var] == 1, "FEX_ADJ"].sum()
                filas.append({
                    "Forma_trabajo": nombre, "Variable": var,
                    "Personas_M": round(n / 1e6, 2),
                    "Pct_%": round(n / total * 100, 1),
                })
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# OTROS INGRESOS (P7422-P7510)
# ═════════════════════════════════════════════════════════════════════

class AnalisisOtrosIngresos:
    """Ingresos no laborales del hogar — insumo para pobreza monetaria.

    P7500S1: Pensiones/jubilaciones
    P7500S2: Ayudas de otros hogares nacionales
    P7510S2: Remesas del exterior
    P7422:   Arriendos recibidos
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prevalencia y monto de ingresos no laborales."""
        fuentes = {
            "P7500S1": ("Pensiones/jubilaciones", "P7500S1A1"),
            "P7500S2": ("Ayudas hogares nacionales", "P7500S2A1"),
            "P7500S3": ("Ayudas institucionales", "P7500S3A1"),
            "P7510S2": ("Remesas del exterior", "P7510S2A1"),
            "P7422":   ("Arriendos recibidos", "P7422S1"),
        }
        filas = []
        total = df["FEX_ADJ"].sum()
        for var_si, (nombre, var_monto) in fuentes.items():
            if var_si in df.columns:
                m = df[var_si] == 1
                n = df.loc[m, "FEX_ADJ"].sum()
                monto_med = np.nan
                if var_monto in df.columns:
                    monto_med = EP.mediana(df.loc[m, var_monto], df.loc[m, "FEX_ADJ"])
                filas.append({
                    "Fuente": nombre, "Receptores_M": round(n / 1e6, 2),
                    "Pct_%": round(n / total * 100, 1),
                    "Mediana_monto": round(monto_med) if not np.isnan(monto_med) else np.nan,
                })
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# SOBRECALIFICACIÓN (P3042 × P6430)
# ═════════════════════════════════════════════════════════════════════

class AnalisisSobrecalificacion:
    """Universitarios en empleos de baja complejidad.

    Detecta P3042 ≥ 10 (universitarios+) en posiciones P6430 = 4 (cuenta propia)
    o P6430 = 9 (servicio doméstico) con INGLABO < 2 SMMLV.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "P3042" not in df.columns or "P6430" not in df.columns:
            return {}
        df_ocu = df[(df["OCI"] == 1)].copy()
        m_univ = df_ocu["P3042"] >= 10
        m_baja = df_ocu["P6430"].isin([4, 5, 6, 9])  # cuenta propia, jornalero, sin pago, doméstico
        m_sobre = m_univ & m_baja
        total_univ = df_ocu.loc[m_univ, "FEX_ADJ"].sum()
        n_sobre = df_ocu.loc[m_sobre, "FEX_ADJ"].sum()
        pct = (n_sobre / total_univ * 100) if total_univ > 0 else np.nan

        # Por rama
        por_rama = []
        if "RAMA" in df_ocu.columns:
            for rama in df_ocu["RAMA"].dropna().unique():
                m_r = df_ocu["RAMA"] == rama
                n_u_r = df_ocu.loc[m_r & m_univ, "FEX_ADJ"].sum()
                n_s_r = df_ocu.loc[m_r & m_sobre, "FEX_ADJ"].sum()
                if n_u_r > 5_000:
                    por_rama.append({
                        "Rama": rama,
                        "Universitarios_miles": round(n_u_r / 1_000),
                        "Sobrecalificados_%": round(n_s_r / n_u_r * 100, 1),
                    })

        return {
            "total_universitarios_M": round(total_univ / 1e6, 2),
            "sobrecalificados_M": round(n_sobre / 1e6, 2),
            "pct_sobrecalificacion": round(pct, 1),
            "por_rama": pd.DataFrame(por_rama).sort_values("Sobrecalificados_%", ascending=False) if por_rama else pd.DataFrame(),
        }


# ═════════════════════════════════════════════════════════════════════
# FORMALIDAD CONTRACTUAL REAL (P6440/P6450/P6460/P6765)
# ═════════════════════════════════════════════════════════════════════

class AnalisisContractual:
    """Mapa de formalidad contractual real.

    P6440: ¿Tiene contrato? (1=Sí)
    P6450: ¿Escrito? (1=Sí)
    P6460: ¿Indefinido? (1=Sí)
    P6765: Forma de trabajo (a=honorarios, c=destajo, g=negocio propio)
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df_ocu = df[(df["OCI"] == 1)].copy()
        total = df_ocu["FEX_ADJ"].sum()
        filas = []

        niveles = [
            ("Contrato escrito indefinido",
             lambda d: (d.get("P6440", 0) == 1) & (d.get("P6450", 0) == 1) & (d.get("P6460", 0) == 1)),
            ("Contrato escrito temporal",
             lambda d: (d.get("P6440", 0) == 1) & (d.get("P6450", 0) == 1) & (d.get("P6460", 0) != 1)),
            ("Contrato verbal",
             lambda d: (d.get("P6440", 0) == 1) & (d.get("P6450", 0) != 1)),
            ("Sin contrato",
             lambda d: (d.get("P6440", 0) != 1)),
        ]

        for nombre, fn_mask in niveles:
            try:
                m = fn_mask(df_ocu)
                n = df_ocu.loc[m, "FEX_ADJ"].sum()
                filas.append({"Tipo_contrato": nombre, "Personas_M": round(n / 1e6, 2), "Pct_%": round(n / total * 100, 1)})
            except Exception:
                continue

        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# AUTONOMÍA LABORAL (P3047/P3048/P3049)
# ═════════════════════════════════════════════════════════════════════

class AnalisisAutonomia:
    """Identifica contratistas dependientes disfrazados de independientes.

    P3047: ¿Quién decide horario? (1=Usted, 3=Empleador)
    P3048: ¿Quién decide qué producir? (1=Usted, 3=Empleador)
    P3049: ¿Quién decide precio? (1=Usted, 3=Empleador)

    Cuenta propia (P6430=4) con P3047/P3048=3 → asalariado disfrazado.
    """

    def calcular(self, df: pd.DataFrame) -> Dict[str, Any]:
        vars_req = ["P3047", "P3048", "P6430"]
        if not all(v in df.columns for v in vars_req):
            return {}

        df_ocu = df[(df["OCI"] == 1)].copy()
        m_cta = df_ocu["P6430"] == 4  # cuenta propia
        m_depend = m_cta & ((df_ocu["P3047"] == 3) | (df_ocu["P3048"] == 3))

        n_cta = df_ocu.loc[m_cta, "FEX_ADJ"].sum()
        n_dep = df_ocu.loc[m_depend, "FEX_ADJ"].sum()

        return {
            "cuenta_propia_M": round(n_cta / 1e6, 2),
            "cta_propia_dependiente_M": round(n_dep / 1e6, 2),
            "pct_dependientes": round(n_dep / n_cta * 100, 1) if n_cta > 0 else np.nan,
            "interpretacion": "Asalariados disfrazados de independientes — evasión laboral",
        }


# ═════════════════════════════════════════════════════════════════════
# ALCANCE DE MERCADO (P1802)
# ═════════════════════════════════════════════════════════════════════

class AnalisisAlcanceMercado:
    """Alcance geográfico del mercado de la empresa del trabajador.

    P1802: 1=Hogar/vecinos, 2=Barrio, 3=Municipio, 4=Dpto, 5=Nacional, 6=Exportación
    Código 6 = empleo directamente vinculado a comercio exterior.
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        if "P1802" not in df.columns:
            return pd.DataFrame()

        ALCANCES = {
            1: "Hogar/vecinos", 2: "Barrio", 3: "Municipio",
            4: "Departamento", 5: "Nacional", 6: "Exportación ★",
        }
        df_ocu = df[(df["OCI"] == 1)].copy()
        total = df_ocu["FEX_ADJ"].sum()
        filas = []
        for cod, nombre in ALCANCES.items():
            m = df_ocu["P1802"] == cod
            n = df_ocu.loc[m, "FEX_ADJ"].sum()
            mediana = EP.mediana(
                df_ocu.loc[m & (df_ocu["INGLABO"] > 0), "INGLABO"],
                df_ocu.loc[m & (df_ocu["INGLABO"] > 0), "FEX_ADJ"]
            )
            filas.append({
                "Alcance": nombre, "Personas_M": round(n / 1e6, 2),
                "Pct_%": round(n / total * 100, 1),
                "Mediana_COP": round(mediana) if not np.isnan(mediana) else np.nan,
            })
        return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════
# DESANIMADOS / POTENCIAL LATENTE (P6300/P6310)
# ═════════════════════════════════════════════════════════════════════

class AnalisisDesanimados:
    """Personas fuera de la FT que desean trabajar (potencial laboral latente).

    P6300=1: Fuera de la FT pero desearía trabajar.
    P6310: ¿Disponible para trabajar? (1=Sí, semana pasada)
    """

    def calcular(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "P6300" not in df.columns:
            return {}

        m_fft = df.get("FFT", pd.Series(dtype=float)) == 1
        m_desea = (df["P6300"] == 1)
        m_disponible = (df.get("P6310", pd.Series(dtype=float)) == 1)

        n_fft = df.loc[m_fft, "FEX_ADJ"].sum()
        n_desea = df.loc[m_fft & m_desea, "FEX_ADJ"].sum()
        n_disp = df.loc[m_fft & m_desea & m_disponible, "FEX_ADJ"].sum()

        return {
            "FFT_total_M": round(n_fft / 1e6, 2),
            "Desean_trabajar_M": round(n_desea / 1e6, 2),
            "Disponibles_inmediato_M": round(n_disp / 1e6, 2),
            "Pct_desanimados": round(n_desea / n_fft * 100, 1) if n_fft > 0 else np.nan,
        }
