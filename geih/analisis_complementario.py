"""
geih.analisis_complementario — Análisis complementarios M8, M14, MX1–MX3.

Clases que cubren funcionalidades presentes en la Versión Antigua del notebook
que no tenían clase dedicada en la Versión Nueva v3.0:

  - DuracionDesempleo (M8)         → P7250 semanas buscando empleo
  - DashboardSectoresProColombia   → 7 sectores estratégicos de actividad económica
  - AnatomaSalario (MX1)           → P6500 vs INGLABO, ingreso "invisible"
  - FormaPago (MX2)                → P6765 destajo/honorarios/comisión
  - CanalEmpleo (MX3)              → P3363 contactos/internet/agencia

Cada clase sigue el patrón: recibe DataFrame preparado → retorna DataFrame
de resultados. No modifica el DataFrame original. No genera gráficos.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "DuracionDesempleo",
    "DashboardSectoresProColombia",
    "AnatomaSalario",
    "FormaPago",
    "CanalEmpleo",
]


from typing import Any, Optional

import numpy as np
import pandas as pd

from .config import (
    DEPARTAMENTOS,
    NIVELES_AGRUPADOS,
    TAMANO_EMPRESA,
    ConfigGEIH,
)
from .utils import EstadisticasPonderadas as EP

# ═════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES INTERNAS
# ═════════════════════════════════════════════════════════════════════


def _tasa(df, mask_num, mask_den, col_peso="FEX_ADJ"):
    """Calcula % ponderado = Σ(FEX condición) / Σ(FEX universo) × 100."""
    n = df.loc[mask_num, col_peso].sum()
    d = df.loc[mask_den, col_peso].sum()
    return round(n / d * 100, 1) if d > 0 else np.nan


# ═════════════════════════════════════════════════════════════════════
# M8 · DURACIÓN DEL DESEMPLEO
# ═════════════════════════════════════════════════════════════════════


class DuracionDesempleo:
    """Análisis de duración del desempleo por semanas buscando empleo (P7250).

    Clasifica el desempleo en categorías según la teoría laboral:
      - Friccional  (< 4 semanas)  : transición normal entre empleos
      - Cíclico     (5–12 semanas) : asociado al ciclo económico
      - Estructural (13–26 semanas): desajuste de habilidades/geografía
      - Largo plazo (> 26 semanas) : riesgo de pérdida permanente de
                                     capital humano y exclusión laboral

    Produce:
      - Distribución nacional por rango de duración
      - Mediana ponderada de semanas por departamento (proxy de rigidez)
      - Cruces por sexo y nivel educativo

    Módulo M8 del notebook original.

    Uso:
        dur = DuracionDesempleo(config=config).calcular(df)
        dur_sexo = DuracionDesempleo(config=config).por_sexo(df)
        dur_educ = DuracionDesempleo(config=config).por_educacion(df)
        dur_dpto = DuracionDesempleo(config=config).por_departamento(df)
    """

    # Rangos en semanas y etiquetas
    BINS = [0, 4, 12, 26, 52, float("inf")]
    ETIQUETAS = [
        "< 1 mes (friccional)",
        "1–3 meses (cíclico)",
        "3–6 meses (estructural)",
        "6–12 meses (largo plazo)",
        "> 1 año (crónico)",
    ]
    ETIQUETAS_CORTAS = ["< 1 mes", "1–3 meses", "3–6 meses", "6–12 meses", "> 1 año"]

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def _filtrar_desocupados(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra desocupados con P7250 válido."""
        mask = (df["DSI"] == 1) & df["P7250"].notna() & (df["P7250"] > 0)
        return df[mask].copy()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución nacional por rango de duración.

        Returns:
            DataFrame con columnas: Rango, Personas, Personas_M, Pct.
        """
        df_dsi = self._filtrar_desocupados(df)
        if df_dsi.empty:
            print("⚠️  No hay desocupados con P7250 válido.")
            return pd.DataFrame()

        df_dsi["DUR_CAT"] = pd.cut(
            df_dsi["P7250"],
            bins=self.BINS,
            labels=self.ETIQUETAS_CORTAS,
            right=False,
            include_lowest=True,
        )

        dist = (
            df_dsi.groupby("DUR_CAT", observed=True)["FEX_ADJ"]
            .sum()
            .reset_index()
            .rename(columns={"DUR_CAT": "Rango", "FEX_ADJ": "Personas"})
        )
        dist["Personas_M"] = (dist["Personas"] / 1e6).round(3)
        dist["Pct"] = (dist["Personas"] / dist["Personas"].sum() * 100).round(1)

        # Mediana nacional
        med_nac = EP.mediana(df_dsi["P7250"], df_dsi["FEX_ADJ"])

        self._imprimir(dist, med_nac)
        return dist

    def por_sexo(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución de duración cruzada por sexo.

        Returns:
            DataFrame con Rango × Sexo y porcentajes.
        """
        df_dsi = self._filtrar_desocupados(df)
        if df_dsi.empty:
            return pd.DataFrame()

        df_dsi["DUR_CAT"] = pd.cut(
            df_dsi["P7250"],
            bins=self.BINS,
            labels=self.ETIQUETAS_CORTAS,
            right=False,
            include_lowest=True,
        )
        df_dsi["SEXO"] = df_dsi["P3271"].map({1: "Hombres", 2: "Mujeres"})

        filas = []
        for sexo in ["Hombres", "Mujeres"]:
            m_sexo = df_dsi["SEXO"] == sexo
            total_sexo = df_dsi.loc[m_sexo, "FEX_ADJ"].sum()
            med = EP.mediana(df_dsi.loc[m_sexo, "P7250"], df_dsi.loc[m_sexo, "FEX_ADJ"])
            for rango in self.ETIQUETAS_CORTAS:
                m_rango = m_sexo & (df_dsi["DUR_CAT"] == rango)
                n = df_dsi.loc[m_rango, "FEX_ADJ"].sum()
                filas.append(
                    {
                        "Sexo": sexo,
                        "Rango": rango,
                        "Personas": n,
                        "Pct": round(n / total_sexo * 100, 1),
                        "Mediana_semanas": round(med, 1),
                    }
                )
        return pd.DataFrame(filas)

    def por_educacion(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mediana de semanas y distribución por nivel educativo agrupado.

        Returns:
            DataFrame con Nivel, Desocupados_M, Mediana_semanas, Pct_largo_plazo.
        """
        df_dsi = self._filtrar_desocupados(df)
        if df_dsi.empty:
            return pd.DataFrame()

        df_dsi["NIVEL_GRUPO"] = df_dsi["P3042"].map(NIVELES_AGRUPADOS)

        filas = []
        for nivel in sorted(df_dsi["NIVEL_GRUPO"].dropna().unique()):
            m = df_dsi["NIVEL_GRUPO"] == nivel
            n = df_dsi.loc[m, "FEX_ADJ"].sum()
            if n < 1_000:
                continue
            med = EP.mediana(df_dsi.loc[m, "P7250"], df_dsi.loc[m, "FEX_ADJ"])
            # % largo plazo (> 26 semanas)
            m_lp = m & (df_dsi["P7250"] >= 26)
            pct_lp = df_dsi.loc[m_lp, "FEX_ADJ"].sum() / n * 100
            filas.append(
                {
                    "Nivel_educativo": nivel,
                    "Desocupados_M": round(n / 1e6, 3),
                    "Mediana_semanas": round(med, 1),
                    "Pct_largo_plazo_%": round(pct_lp, 1),
                }
            )
        return pd.DataFrame(filas)

    def por_departamento(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mediana ponderada de semanas por departamento (proxy de rigidez).

        Returns:
            DataFrame con Departamento, Mediana_semanas, Desocupados_miles.
        """
        df_dsi = self._filtrar_desocupados(df)
        if df_dsi.empty:
            return pd.DataFrame()

        if "DPTO_STR" not in df_dsi.columns:
            from .utils import ConversorTipos

            df_dsi["DPTO_STR"] = ConversorTipos.estandarizar_dpto(df_dsi["DPTO"])

        filas = []
        for dpto, nombre in DEPARTAMENTOS.items():
            m = df_dsi["DPTO_STR"] == dpto
            n = df_dsi.loc[m, "FEX_ADJ"].sum()
            if n < 1_000:
                continue
            med = EP.mediana(df_dsi.loc[m, "P7250"], df_dsi.loc[m, "FEX_ADJ"])
            filas.append(
                {
                    "Departamento": nombre,
                    "DPTO": dpto,
                    "Mediana_semanas": round(med, 1),
                    "Desocupados_miles": round(n / 1_000, 1),
                }
            )
        return pd.DataFrame(filas).sort_values("Mediana_semanas", ascending=False)

    def _imprimir(self, dist: pd.DataFrame, mediana: float) -> None:
        print(f"\n{'='*60}")
        print(f"  M8 · DURACIÓN DEL DESEMPLEO — {self.config.periodo_etiqueta}")
        print(f"{'='*60}")
        print(f"  Mediana nacional: {mediana:.1f} semanas")
        for _, row in dist.iterrows():
            print(f"  {row['Rango']:<16} → {row['Personas_M']:.3f}M  ({row['Pct']:.1f}%)")


# ═════════════════════════════════════════════════════════════════════
# M14 · DASHBOARD SECTORES ESTRATÉGICOS
# ═════════════════════════════════════════════════════════════════════

# Mapeo CIIU 2D → sector estratégico (rangos de códigos CIIU relevantes)
_SECTORES_PROCOLOMBIA: dict[str, list[range]] = {
    "TIC / Software": [range(58, 64)],  # Información y comunicaciones
    "Turismo y Hotelería": [range(55, 57), range(79, 80)],  # Alojamiento + agencias
    "Agroindustria": [range(1, 4), range(10, 13)],  # Agri + alimentos
    "Financiero y Seguros": [range(64, 67)],  # Finanzas y seguros
    "Química y Farmacéutica": [range(20, 22)],  # Químicos + farma
    "Textil y Confecciones": [range(13, 16)],  # Textil, confección, calzado
    "Manufactura Avanzada": [range(26, 31)],  # Electrónica, maquinaria, vehículos
}


class DashboardSectoresProColombia:
    """Dashboard de 7 sectores estratégicos para discurso IED.

    Para cada sector calcula:
      - Empleo total (miles)
      - Ingreso mediano en SMMLV
      - % universitarios (P3042 >= 10)
      - % jóvenes 15–28
      - Formalidad (% cotiza pensión P6920=1)
      - % mujeres

    Módulo M14 del notebook original.

    Uso:
        dash = DashboardSectoresProColombia(config=config).calcular(df)
        print(dash.to_string(index=False))
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    @staticmethod
    def _clasificar_sector(rama2d: pd.Series) -> pd.Series:
        """Clasifica RAMA2D_R4 en sector estratégico o NaN."""
        rama_num = pd.to_numeric(rama2d, errors="coerce")
        resultado = pd.Series(np.nan, index=rama2d.index, dtype=object)
        for sector, rangos in _SECTORES_PROCOLOMBIA.items():
            mask = pd.Series(False, index=rama2d.index)
            for rng in rangos:
                mask = mask | rama_num.between(rng.start, rng.stop - 1)
            resultado = resultado.where(~mask, sector)
        return resultado

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula el dashboard para los 7 sectores estratégicos.

        Args:
            df: DataFrame preparado con OCI, RAMA2D_R4, FEX_ADJ, INGLABO,
                P3042, P6040, P6920, P3271.

        Returns:
            DataFrame con una fila por sector y 7 columnas de indicadores.
        """
        df_ocu = df[df["OCI"] == 1].copy()
        df_ocu["SECTOR_PC"] = self._clasificar_sector(df_ocu["RAMA2D_R4"])
        df_ocu = df_ocu[df_ocu["SECTOR_PC"].notna()]

        smmlv = self.config.smmlv
        filas = []

        for sector in _SECTORES_PROCOLOMBIA:
            m = df_ocu["SECTOR_PC"] == sector
            n = df_ocu.loc[m, "FEX_ADJ"].sum()
            if n < 500:
                continue

            sub = df_ocu[m]
            med_ing = EP.mediana(sub["INGLABO"], sub["FEX_ADJ"])

            # % universitarios
            pct_univ = np.nan
            if "P3042" in sub.columns:
                m_univ = m & (df_ocu["P3042"] >= 10)
                pct_univ = round(df_ocu.loc[m_univ, "FEX_ADJ"].sum() / n * 100, 1)

            # % jóvenes 15-28
            pct_jov = np.nan
            if "P6040" in sub.columns:
                m_jov = m & df_ocu["P6040"].between(15, 28)
                pct_jov = round(df_ocu.loc[m_jov, "FEX_ADJ"].sum() / n * 100, 1)

            # Formalidad (cotiza pensión)
            pct_pen = np.nan
            if "P6920" in sub.columns:
                m_pen = m & (df_ocu["P6920"] == 1)
                pct_pen = round(df_ocu.loc[m_pen, "FEX_ADJ"].sum() / n * 100, 1)

            # % mujeres
            pct_muj = np.nan
            if "P3271" in sub.columns:
                m_muj = m & (df_ocu["P3271"] == 2)
                pct_muj = round(df_ocu.loc[m_muj, "FEX_ADJ"].sum() / n * 100, 1)

            filas.append(
                {
                    "Sector": sector,
                    "Empleo_miles": round(n / 1_000, 1),
                    "Mediana_SMMLV": round(med_ing / smmlv, 2) if med_ing else np.nan,
                    "Universitarios_%": pct_univ,
                    "Jóvenes_15_28_%": pct_jov,
                    "Formalidad_%": pct_pen,
                    "Mujeres_%": pct_muj,
                }
            )

        resultado = pd.DataFrame(filas).sort_values("Empleo_miles", ascending=False)
        self._imprimir(resultado)
        return resultado

    def _imprimir(self, df: pd.DataFrame) -> None:
        print(f"\n{'='*80}")
        print(f"  M14 · DASHBOARD SECTORES ESTRATÉGICOS — {self.config.periodo_etiqueta}")
        print(f"{'='*80}")
        print(
            f"  {'Sector':<28} {'Empleo':>8} {'Med.SML':>8} {'%Univ':>6} "
            f"{'%Jov':>5} {'%Form':>6} {'%Muj':>5}"
        )
        print(f"  {'─'*28} {'─'*8} {'─'*8} {'─'*6} {'─'*5} {'─'*6} {'─'*5}")
        for _, r in df.iterrows():
            print(
                f"  {r['Sector']:<28} {r['Empleo_miles']:>7.0f}K "
                f"{r['Mediana_SMMLV']:>7.2f}× {r['Universitarios_%']:>5.1f} "
                f"{r['Jóvenes_15_28_%']:>5.1f} {r['Formalidad_%']:>5.1f} "
                f"{r['Mujeres_%']:>5.1f}"
            )


# ═════════════════════════════════════════════════════════════════════
# MX1 · ANATOMÍA DEL SALARIO: P6500 vs INGLABO
# ═════════════════════════════════════════════════════════════════════


class AnatomaSalario:
    """Cruce P6500 (salario bruto declarado) vs INGLABO (ingreso consolidado DANE).

    La brecha (INGLABO − P6500) / P6500 revela el ingreso "invisible":
    bonificaciones, especie, comisiones, viáticos que el trabajador no
    identifica como "salario" pero el DANE sí imputa.

    Incluye también P3364 (retención en la fuente) como proxy de
    tributación formal ante la DIAN.

    Módulo MX1 del notebook original.

    Uso:
        anat = AnatomaSalario(config=config)
        por_rama = anat.por_rama(df)
        por_tamano = anat.por_tamano_empresa(df)
        resumen = anat.resumen_nacional(df)
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def _filtrar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra ocupados con ambos ingresos válidos y positivos."""
        mask = (
            (df["OCI"] == 1)
            & df["P6500"].notna()
            & (df["P6500"] > 0)
            & df["INGLABO"].notna()
            & (df["INGLABO"] > 0)
        )
        return df[mask].copy()

    def resumen_nacional(self, df: pd.DataFrame) -> dict[str, Any]:
        """Resumen nacional de la brecha P6500 vs INGLABO.

        Returns:
            Dict con medianas, brecha %, y % con retención en la fuente.
        """
        df_f = self._filtrar(df)
        if df_f.empty:
            return {}

        med_p6500 = EP.mediana(df_f["P6500"], df_f["FEX_ADJ"])
        med_inglabo = EP.mediana(df_f["INGLABO"], df_f["FEX_ADJ"])
        brecha_pct = (med_inglabo - med_p6500) / med_p6500 * 100

        # % con retención en la fuente (P3364=1)
        pct_retencion = np.nan
        if "P3364" in df_f.columns:
            n_ret = df_f.loc[df_f["P3364"] == 1, "FEX_ADJ"].sum()
            pct_retencion = round(n_ret / df_f["FEX_ADJ"].sum() * 100, 1)

        resultado = {
            "Registros_con_ambos": len(df_f),
            "Mediana_P6500": round(med_p6500),
            "Mediana_INGLABO": round(med_inglabo),
            "Brecha_%": round(brecha_pct, 1),
            "Pct_con_retencion_fuente": pct_retencion,
        }

        print(f"\n{'='*55}")
        print(f"  MX1 · ANATOMÍA SALARIAL — {self.config.periodo_etiqueta}")
        print(f"{'='*55}")
        print(f"  Mediana P6500 (bruto declarado): ${med_p6500:,.0f}")
        print(f"  Mediana INGLABO (consolidado) :  ${med_inglabo:,.0f}")
        print(f"  Brecha (ingreso invisible)    :  {brecha_pct:+.1f}%")
        if pct_retencion is not np.nan:
            print(f"  % con retención fuente (DIAN) :  {pct_retencion:.1f}%")

        return resultado

    def por_rama(self, df: pd.DataFrame) -> pd.DataFrame:
        """Brecha P6500 vs INGLABO por rama de actividad.

        Returns:
            DataFrame con Rama, Mediana_P6500, Mediana_INGLABO, Brecha_%.
        """
        df_f = self._filtrar(df)
        if df_f.empty or "RAMA" not in df_f.columns:
            return pd.DataFrame()

        filas = []
        for rama in df_f["RAMA"].dropna().unique():
            m = df_f["RAMA"] == rama
            n = df_f.loc[m, "FEX_ADJ"].sum()
            if n < 5_000:
                continue
            med_p = EP.mediana(df_f.loc[m, "P6500"], df_f.loc[m, "FEX_ADJ"])
            med_i = EP.mediana(df_f.loc[m, "INGLABO"], df_f.loc[m, "FEX_ADJ"])
            brecha = (med_i - med_p) / med_p * 100 if med_p > 0 else np.nan
            filas.append(
                {
                    "Rama": rama,
                    "Ocupados_miles": round(n / 1_000, 1),
                    "Mediana_P6500": round(med_p),
                    "Mediana_INGLABO": round(med_i),
                    "Brecha_%": round(brecha, 1),
                }
            )
        return pd.DataFrame(filas).sort_values("Brecha_%", ascending=False)

    def por_tamano_empresa(self, df: pd.DataFrame) -> pd.DataFrame:
        """Brecha P6500 vs INGLABO por tamaño de empresa (P3069).

        Returns:
            DataFrame con Tamano, Mediana_P6500, Mediana_INGLABO, Brecha_%.
        """
        df_f = self._filtrar(df)
        if df_f.empty or "P3069" not in df_f.columns:
            return pd.DataFrame()

        filas = []
        for cod, etiq in TAMANO_EMPRESA.items():
            m = df_f["P3069"] == cod
            n = df_f.loc[m, "FEX_ADJ"].sum()
            if n < 5_000:
                continue
            med_p = EP.mediana(df_f.loc[m, "P6500"], df_f.loc[m, "FEX_ADJ"])
            med_i = EP.mediana(df_f.loc[m, "INGLABO"], df_f.loc[m, "FEX_ADJ"])
            brecha = (med_i - med_p) / med_p * 100 if med_p > 0 else np.nan
            filas.append(
                {
                    "Tamaño": etiq,
                    "Cod": cod,
                    "Ocupados_miles": round(n / 1_000, 1),
                    "Mediana_P6500": round(med_p),
                    "Mediana_INGLABO": round(med_i),
                    "Brecha_%": round(brecha, 1),
                }
            )
        return pd.DataFrame(filas).sort_values("Cod")


# ═════════════════════════════════════════════════════════════════════
# MX2 · FORMA DE PAGO (P6765)
# ═════════════════════════════════════════════════════════════════════

# Mapeo P6765 → etiqueta.
# El DANE codifica esta variable de forma inconsistente entre años:
#   - Algunos años usan letras: 'a', 'b', 'c', ...
#   - Otros años usan números: 1, 2, 3, ...
# Este mapeo cubre AMBOS formatos para máxima compatibilidad.
_FORMA_PAGO_LETRAS: dict[str, str] = {
    "a": "Honorarios / Prestación de servicios",
    "b": "Jornal o diario",
    "c": "A destajo (pieza, maquila)",
    "d": "Por comisión",
    "e": "Porcentaje",
    "f": "Ingreso mensual",
    "g": "Negocio / finca propia",
    "h": "No recibe ingresos",
    "i": "Ganancia neta (negocio)",
}

_FORMA_PAGO_NUMEROS: dict[str, str] = {
    "1": "Honorarios / Prestación de servicios",
    "2": "Jornal o diario",
    "3": "A destajo (pieza, maquila)",
    "4": "Por comisión",
    "5": "Porcentaje",
    "6": "Ingreso mensual",
    "7": "Negocio / finca propia",
    "8": "No recibe ingresos",
    "9": "Ganancia neta (negocio)",
}

# Mapeo combinado: acepta '1', '1.0', 'a', etc.
_FORMA_PAGO: dict[str, str] = {
    **_FORMA_PAGO_LETRAS,
    **_FORMA_PAGO_NUMEROS,
    # Variantes con .0 (pandas lee floats como '1.0')
    **{f"{k}.0": v for k, v in _FORMA_PAGO_NUMEROS.items()},
}


class FormaPago:
    """Análisis de la forma real de pago/trabajo (P6765).

    Revela cómo se remunera realmente a los trabajadores, más allá
    de la clasificación formal/informal. El destajo (c) indica
    precariedad en manufactura; los honorarios (a) indican economía
    gig sin protección social.

    Módulo MX2 del notebook original.

    Uso:
        fp = FormaPago(config=config)
        dist = fp.calcular(df)              # distribución nacional
        cruce = fp.cruce_formalidad(df)      # forma × cotiza pensión
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución ponderada de ocupados por forma de pago.

        Auto-detecta la codificación del DANE (letras, números, o floats)
        y muestra diagnóstico si no logra mapear los valores.

        Returns:
            DataFrame con Forma_pago, Ocupados, Ocupados_M, Pct.
        """
        df_ocu = df[(df["OCI"] == 1) & df["P6765"].notna()].copy()
        if df_ocu.empty:
            print("⚠️  P6765 no disponible o vacía en la base.")
            return pd.DataFrame()

        # Normalizar: convertir a string, limpiar espacios, minúsculas
        df_ocu["P6765_STR"] = df_ocu["P6765"].astype(str).str.strip().str.lower()

        # Intentar mapeo
        df_ocu["FORMA_ETIQ"] = df_ocu["P6765_STR"].map(_FORMA_PAGO)
        n_mapeados = df_ocu["FORMA_ETIQ"].notna().sum()

        # Si el mapeo no funcionó, diagnosticar y usar valores crudos
        if n_mapeados == 0:
            valores_unicos = df_ocu["P6765_STR"].value_counts().head(10)
            print("⚠️  P6765: ningún valor coincide con el mapeo conocido.")
            print("   Valores encontrados en la base (top 10):")
            for val, count in valores_unicos.items():
                print(f"     '{val}' → {count:,} registros")
            print("   Usando valores crudos como etiqueta.")
            df_ocu["FORMA_ETIQ"] = df_ocu["P6765_STR"]

        dist = (
            df_ocu.groupby("FORMA_ETIQ", observed=True)["FEX_ADJ"]
            .sum()
            .reset_index()
            .rename(columns={"FORMA_ETIQ": "Forma_pago", "FEX_ADJ": "Ocupados"})
        )
        # Eliminar filas NaN (valores que no mapearon)
        dist = dist.dropna(subset=["Forma_pago"])
        if dist.empty:
            print("⚠️  No se pudo calcular distribución de forma de pago.")
            return pd.DataFrame()

        dist["Ocupados_M"] = (dist["Ocupados"] / 1e6).round(3)
        dist["Pct"] = (dist["Ocupados"] / dist["Ocupados"].sum() * 100).round(1)
        dist = dist.sort_values("Ocupados", ascending=False)

        self._imprimir(dist)
        return dist

    def cruce_formalidad(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cruce forma de pago × cotización a pensión (proxy formalidad).

        Returns:
            DataFrame con Forma_pago, Total, Cotiza_pension_%, No_cotiza_%.
        """
        df_ocu = df[(df["OCI"] == 1) & df["P6765"].notna()].copy()
        if df_ocu.empty or "P6920" not in df_ocu.columns:
            return pd.DataFrame()

        df_ocu["P6765_STR"] = df_ocu["P6765"].astype(str).str.strip().str.lower()
        df_ocu["FORMA_ETIQ"] = df_ocu["P6765_STR"].map(_FORMA_PAGO)
        # Fallback a valores crudos si nada mapea
        if df_ocu["FORMA_ETIQ"].notna().sum() == 0:
            df_ocu["FORMA_ETIQ"] = df_ocu["P6765_STR"]

        filas = []
        for forma in df_ocu["FORMA_ETIQ"].dropna().unique():
            m = df_ocu["FORMA_ETIQ"] == forma
            total = df_ocu.loc[m, "FEX_ADJ"].sum()
            if total < 5_000:
                continue
            n_pen = df_ocu.loc[m & (df_ocu["P6920"] == 1), "FEX_ADJ"].sum()
            filas.append(
                {
                    "Forma_pago": forma,
                    "Ocupados_miles": round(total / 1_000, 1),
                    "Cotiza_pension_%": round(n_pen / total * 100, 1),
                    "No_cotiza_%": round((1 - n_pen / total) * 100, 1),
                }
            )
        return pd.DataFrame(filas).sort_values("Cotiza_pension_%", ascending=False)

    def _imprimir(self, dist: pd.DataFrame) -> None:
        print(f"\n{'='*60}")
        print(f"  MX2 · FORMA DE PAGO — {self.config.periodo_etiqueta}")
        print(f"{'='*60}")
        for _, r in dist.iterrows():
            print(f"  {r['Forma_pago']!s:<45} " f"{r['Ocupados_M']:>6.3f}M  ({r['Pct']:>5.1f}%)")


# ═════════════════════════════════════════════════════════════════════
# MX3 · CANAL DE ACCESO AL EMPLEO (P3363)
# ═════════════════════════════════════════════════════════════════════

# Mapeo P3363 → etiqueta descriptiva
_CANAL_EMPLEO: dict[int, str] = {
    1: "Contactos / amigos / familiares",
    2: "Clasificados / avisos",
    3: "Agencia empleo (SENA/Cajas)",
    4: "Bolsa de empleo / internet",
    5: "Convocatoria / concurso",
    6: "Por cuenta propia (propio negocio)",
    7: "Otra forma",
}


class CanalEmpleo:
    """Análisis del canal por el cual se consiguió el empleo (P3363).

    Mide la digitalización y segmentación del mercado laboral:
    - Contactos > 60% → mercado segmentado, red social > productividad
    - Internet/bolsa creciendo → señal de modernización
    - SENA/Agencia bajo → sistema público de empleo subutilizado

    Módulo MX3 del notebook original.

    Uso:
        ce = CanalEmpleo(config=config)
        dist = ce.calcular(df)                   # distribución nacional
        por_educ = ce.por_nivel_educativo(df)     # cruce × educación
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución ponderada de ocupados por canal de empleo.

        Returns:
            DataFrame con Canal, Ocupados, Ocupados_M, Pct.
        """
        df_ocu = df[(df["OCI"] == 1) & df["P3363"].notna()].copy()
        if df_ocu.empty:
            print("⚠️  P3363 no disponible en la base.")
            return pd.DataFrame()

        df_ocu["CANAL_ETIQ"] = pd.to_numeric(df_ocu["P3363"], errors="coerce").map(_CANAL_EMPLEO)

        dist = (
            df_ocu[df_ocu["CANAL_ETIQ"].notna()]
            .groupby("CANAL_ETIQ", observed=True)["FEX_ADJ"]
            .sum()
            .reset_index()
            .rename(columns={"CANAL_ETIQ": "Canal", "FEX_ADJ": "Ocupados"})
        )
        dist["Ocupados_M"] = (dist["Ocupados"] / 1e6).round(3)
        dist["Pct"] = (dist["Ocupados"] / dist["Ocupados"].sum() * 100).round(1)
        dist = dist.sort_values("Ocupados", ascending=False)

        self._imprimir(dist)
        return dist

    def por_nivel_educativo(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución de canal × nivel educativo agrupado.

        Revela si los universitarios usan más internet y los menos
        educados dependen más de contactos personales.

        Returns:
            DataFrame con Nivel, Canal, Pct por nivel.
        """
        df_ocu = df[(df["OCI"] == 1) & df["P3363"].notna()].copy()
        if df_ocu.empty or "P3042" not in df_ocu.columns:
            return pd.DataFrame()

        df_ocu["CANAL_ETIQ"] = pd.to_numeric(df_ocu["P3363"], errors="coerce").map(_CANAL_EMPLEO)
        df_ocu["NIVEL_GRUPO"] = df_ocu["P3042"].map(NIVELES_AGRUPADOS)

        filas = []
        for nivel in sorted(df_ocu["NIVEL_GRUPO"].dropna().unique()):
            m_niv = df_ocu["NIVEL_GRUPO"] == nivel
            total_niv = df_ocu.loc[m_niv, "FEX_ADJ"].sum()
            if total_niv < 5_000:
                continue
            for canal in df_ocu["CANAL_ETIQ"].dropna().unique():
                m_can = m_niv & (df_ocu["CANAL_ETIQ"] == canal)
                n = df_ocu.loc[m_can, "FEX_ADJ"].sum()
                filas.append(
                    {
                        "Nivel_educativo": nivel,
                        "Canal": canal,
                        "Pct": round(n / total_niv * 100, 1),
                    }
                )
        return pd.DataFrame(filas)

    def _imprimir(self, dist: pd.DataFrame) -> None:
        print(f"\n{'='*60}")
        print(f"  MX3 · CANAL DE EMPLEO — {self.config.periodo_etiqueta}")
        print(f"{'='*60}")
        for _, r in dist.iterrows():
            print(f"  {r['Canal']!s:<42} " f"{r['Ocupados_M']:>6.3f}M  ({r['Pct']:>5.1f}%)")
