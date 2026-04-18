"""
geih.indicadores — Cálculo de indicadores del mercado laboral.

Contiene todas las clases de análisis, cada una con responsabilidad única:
  - IndicadoresLaborales: TD, TGP, TO, sanity checks
  - DistribucionIngresos: rangos SMMLV, distribución por sexo
  - AnalisisRamaSexo: ocupados por rama CIIU y sexo
  - AnalisisSalarios: estadísticas salariales por rama y edad
  - BrechaGenero: brecha salarial por nivel educativo
  - AnalisisCruzado: empresa × departamento
  - IndiceFormalidad: ICE, ICF, IVI, ICI, ITAT
  - AnalisisArea: ocupados por CIIU y 32 ciudades

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "IndicadoresLaborales",
    "DistribucionIngresos",
    "AnalisisRamaSexo",
    "AnalisisSalarios",
    "BrechaGenero",
    "AnalisisCruzado",
    "IndicesCompuestos",
    "AnalisisArea",
]


import gc
from typing import Any, Optional

import numpy as np
import pandas as pd

from .config import (
    AGRUPACION_DANE_8,
    DEPARTAMENTOS,
    RANGOS_SMMLV_ETIQUETAS,
    RANGOS_SMMLV_LIMITES,
    ConfigGEIH,
)
from .utils import ConversorTipos
from .utils import EstadisticasPonderadas as EP

# ═════════════════════════════════════════════════════════════════════
# INDICADORES LABORALES FUNDAMENTALES
# ═════════════════════════════════════════════════════════════════════


class IndicadoresLaborales:
    """Calcula TD, TGP, TO y valida contra el boletín DANE.

    Módulo M0 del notebook original.

    Las tres tasas fundamentales:
      TD  = Desocupados / PEA       (tasa de desempleo)
      TGP = PEA / PET               (tasa global de participación)
      TO  = Ocupados / PET          (tasa de ocupación)

    Identidades que siempre deben cumplirse:
      PEA = OCI + DSI
      PET = PEA + FFT
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> dict[str, float]:
        """Calcula indicadores nacionales a partir de la base preparada.

        Args:
            df: DataFrame con columnas FEX_ADJ, OCI, FT, DSI, PET.

        Returns:
            Dict con PET, PEA, Ocupados, Desocupados, TD, TGP, TO.
        """
        fex = "FEX_ADJ"

        pet = df.loc[df["PET"] == 1, fex].sum() if "PET" in df.columns else 0
        pea = df.loc[df["FT"] == 1, fex].sum() if "FT" in df.columns else 0
        ocu = df.loc[df["OCI"] == 1, fex].sum() if "OCI" in df.columns else 0
        des = df.loc[df["DSI"] == 1, fex].sum() if "DSI" in df.columns else 0

        td = (des / pea * 100) if pea > 0 else np.nan
        tgp = (pea / pet * 100) if pet > 0 else np.nan
        to = (ocu / pet * 100) if pet > 0 else np.nan

        resultado = {
            "PET_M": pet / 1e6,
            "PEA_M": pea / 1e6,
            "Ocupados_M": ocu / 1e6,
            "Desocupados_M": des / 1e6,
            # Valores de display (1 decimal, como el Boletín DANE)
            "TD_%": round(td, 1),
            "TGP_%": round(tgp, 1),
            "TO_%": round(to, 1),
            # Valores crudos sin redondear (v6.0) — necesarios para
            # validación estricta contra anexo Excel del DANE, cuya
            # precisión es de 4 decimales. El round(_, 1) anterior
            # convertía 7.97 y 8.03 ambos en 8.0 e impedía verificar
            # con tolerancia ±0.05 p.p.
            "TD_raw": td,
            "TGP_raw": tgp,
            "TO_raw": to,
        }
        return resultado

    def sanity_check(
        self,
        resultado: dict[str, float],
        periodo: str = "Anual",
        tolerancia_pp: float = 0.5,
    ) -> bool:
        """Valida los indicadores contra las referencias DANE.

        Si las cifras difieren más de ±0.5 p.p., alerta al usuario.

        CAMBIO v4.0: Usa config.referencia_dane (multi-año) en vez de
        REF_DANE_2025 hardcoded. Si no hay referencia para el año
        configurado, advierte pero no falla — solo valida PEA < 40M.

        Returns:
            True si todos los indicadores pasan la validación.
        """
        ref = self.config.referencia_dane
        is_anual = "anual" in periodo.lower()

        print(f"\n{'─'*55}")
        print(f"  SANITY CHECK — {periodo} ({self.config.anio})")
        print(f"{'─'*55}")

        ok = True

        if ref is None:
            # Año sin referencia publicada (ej: 2026 parcial)
            print(f"  ⚠️  Sin referencia DANE para {self.config.anio}.")
            print("     No se puede validar TD/TGP/TO contra boletín oficial.")
            print("     Agregue la referencia en config.py → REF_DANE cuando")
            print("     el DANE publique las cifras oficiales del año.")
        else:
            refs = {
                "TD_%": ref.td_anual_pct if is_anual else ref.td_dic_pct,
                "TGP_%": ref.tgp_anual_pct if is_anual else ref.tgp_dic_pct,
                "TO_%": ref.to_anual_pct if is_anual else ref.to_dic_pct,
            }
            for key, ref_val in refs.items():
                if ref_val == 0.0:
                    print(f"  ⚠️  {key:>6} — ref. DANE no disponible para este período")
                    continue
                calc = resultado.get(key, np.nan)
                diff = abs(calc - ref_val)
                estado = "✅" if diff <= tolerancia_pp else "⚠️"
                if diff > tolerancia_pp:
                    ok = False
                print(
                    f"  {estado} {key:>6} = {calc:.1f}%  (ref. DANE: {ref_val:.1f}%  Δ={diff:.1f})"
                )

        for key in ["PET_M", "PEA_M", "Ocupados_M", "Desocupados_M"]:
            val = resultado.get(key, 0)
            print(f"     {key:>15} = {val:.2f} M")

        if resultado.get("PEA_M", 0) > 40:
            print("  ❌ ALERTA: PEA > 40M → El factor de expansión NO está siendo dividido.")
            ok = False

        return ok

    def por_departamento(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula TD, TGP, TO por departamento.

        Args:
            df: DataFrame con DPTO_STR, FEX_ADJ, OCI, FT, DSI, PET.

        Returns:
            DataFrame con indicadores por departamento.
        """
        if "DPTO_STR" not in df.columns:
            df["DPTO_STR"] = ConversorTipos.estandarizar_dpto(df["DPTO"])

        filas = []
        for dpto, nombre in DEPARTAMENTOS.items():
            m = df["DPTO_STR"] == dpto
            if m.sum() < 100:
                continue
            r = self.calcular(df[m])
            r["Departamento"] = nombre
            r["DPTO"] = dpto
            filas.append(r)

        return pd.DataFrame(filas).sort_values("TD_%", ascending=False)


# ═════════════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE INGRESOS
# ═════════════════════════════════════════════════════════════════════


class DistribucionIngresos:
    """Distribución del ingreso laboral por rangos de SMMLV.

    Módulo M1 del notebook original.
    Clasifica ~23M de ocupados según su ingreso en múltiplos de SMMLV.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def calcular(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Calcula la distribución de ingresos por rangos SMMLV.

        Args:
            df: DataFrame con OCI, INGLABO, P3271, FEX_ADJ.

        Returns:
            Dict con 'total' (distribución general) y 'por_sexo'.
        """
        # Filtrar ocupados con ingreso positivo
        df_ocu = df[(df["OCI"] == 1) & (df["INGLABO"] > 0)].copy()

        n_total = df.loc[df["OCI"] == 1, "FEX_ADJ"].sum()
        n_pos = df_ocu["FEX_ADJ"].sum()

        print(f"   Ocupados totales      : {n_total/1e6:.2f} M")
        print(f"   Con ingreso > 0       : {n_pos/1e6:.2f} M")
        print(f"   Sin ingreso / especie : {(n_total-n_pos)/1e6:.2f} M")

        # Clasificar en rangos (vectorizado con pd.cut)
        limites_cop = [lim * self.config.smmlv for lim in RANGOS_SMMLV_LIMITES]
        df_ocu["RANGO"] = pd.cut(
            df_ocu["INGLABO"],
            bins=limites_cop,
            labels=RANGOS_SMMLV_ETIQUETAS,
            right=False,
            include_lowest=True,
        )
        df_ocu["SEXO"] = df_ocu["P3271"].map({1: "Hombres", 2: "Mujeres"})

        # Agregación total
        dist = (
            df_ocu.groupby("RANGO", observed=True)["FEX_ADJ"]
            .sum()
            .reset_index()
            .rename(columns={"FEX_ADJ": "Personas"})
        )
        dist["Personas_M"] = dist["Personas"] / 1e6
        dist["Pct"] = dist["Personas"] / n_pos * 100
        dist["Acum_Pct"] = dist["Pct"].cumsum()

        # Por sexo
        dist_sexo = (
            df_ocu.groupby(["RANGO", "SEXO"], observed=True)["FEX_ADJ"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        for col in ["Hombres", "Mujeres"]:
            if col not in dist_sexo.columns:
                dist_sexo[col] = 0
        dist_sexo["H_M"] = dist_sexo["Hombres"] / 1e6
        dist_sexo["M_M"] = dist_sexo["Mujeres"] / 1e6

        del df_ocu
        gc.collect()

        return {"total": dist, "por_sexo": dist_sexo}

    def imprimir(self, resultado: dict[str, pd.DataFrame], titulo: str = "") -> None:
        """Imprime la tabla de distribución de ingresos."""
        dist = resultado["total"]
        resultado["por_sexo"]

        print(f"\n{'─'*70}")
        print(f"  DISTRIBUCIÓN DE INGRESOS LABORALES — {titulo}")
        print(f"  SMMLV 2025 = ${self.config.smmlv:,} COP")
        print(f"{'─'*70}")
        print(f"  {'Rango':<22} {'Personas':>10} {'%':>7}  {'Acum%':>7}")
        print(f"  {'─'*22} {'─'*10} {'─'*7}  {'─'*7}")

        for _, row in dist.iterrows():
            print(
                f"  {row['RANGO']!s:<22} {row['Personas_M']:>8.2f}M "
                f"{row['Pct']:>6.1f}%  {row['Acum_Pct']:>6.1f}%"
            )


# ═════════════════════════════════════════════════════════════════════
# ANÁLISIS POR RAMA Y SEXO
# ═════════════════════════════════════════════════════════════════════


class AnalisisRamaSexo:
    """Ocupados por rama de actividad económica y sexo.

    Módulo M3 del notebook original.
    Agrega ocupados expandidos por las 13 ramas DANE, desagregados por sexo.
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula la tabla pivote de ocupados por rama y sexo.

        Args:
            df: DataFrame con RAMA (ya mapeada), SEXO, FEX_ADJ, OCI.

        Returns:
            DataFrame con Total, Hombres, Mujeres, y distribuciones %.
        """
        df_calc = df[(df["OCI"] == 1) & df["RAMA"].notna() & df["SEXO"].notna()].copy()

        pivot = (
            df_calc.groupby(["RAMA", "SEXO"])["FEX_ADJ"].sum().unstack(fill_value=0).reset_index()
        )
        for col in ["Hombres", "Mujeres"]:
            if col not in pivot.columns:
                pivot[col] = 0

        pivot["Total"] = pivot["Hombres"] + pivot["Mujeres"]
        pivot = pivot.sort_values("Total", ascending=False).reset_index(drop=True)

        total_nac = pivot["Total"].sum()
        total_h = pivot["Hombres"].sum()
        total_m = pivot["Mujeres"].sum()

        pivot["Dist_%"] = (pivot["Total"] / total_nac * 100).round(1)
        pivot["Dist_H_%"] = (pivot["Hombres"] / total_h * 100).round(1)
        pivot["Dist_M_%"] = (pivot["Mujeres"] / total_m * 100).round(1)

        # Convertir a miles
        for col in ["Total", "Hombres", "Mujeres"]:
            pivot[f"{col}_miles"] = (pivot[col] / 1_000).round(0).astype(int)

        del df_calc
        gc.collect()

        return pivot


# ═════════════════════════════════════════════════════════════════════
# ESTADÍSTICAS SALARIALES POR RAMA Y EDAD
# ═════════════════════════════════════════════════════════════════════


class AnalisisSalarios:
    """Estadísticas de salario por rama y grupo de edad.

    Módulo M4 del notebook original.
    Calcula media, mediana, percentiles ponderados por FEX.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def por_rama(self, df: pd.DataFrame) -> pd.DataFrame:
        """Estadísticas salariales ponderadas por rama de actividad.

        Args:
            df: DataFrame con RAMA, INGLABO, FEX_ADJ.

        Returns:
            DataFrame con N, Media, Mediana, P10-P90, CV%, etc.
        """
        df_calc = df[df["INGLABO"] > 0].copy()
        filas = []
        for rama in df_calc["RAMA"].dropna().unique():
            m = df_calc["RAMA"] == rama
            est = EP.resumen_completo(
                df_calc.loc[m, "INGLABO"],
                df_calc.loc[m, "FEX_ADJ"],
                self.config.smmlv,
            )
            if est:
                est["Rama"] = rama
                filas.append(est)

        tabla = pd.DataFrame(filas)
        if not tabla.empty:
            tabla = tabla.set_index("Rama").sort_values("Mediana", ascending=False)
        return tabla

    def por_edad(
        self,
        df: pd.DataFrame,
        bin_size: int = 5,
        edad_min: int = 15,
        edad_max: int = 79,
    ) -> pd.DataFrame:
        """Estadísticas salariales por grupo de edad (ciclo vital).

        Args:
            df: DataFrame con P6040 (edad), INGLABO, FEX_ADJ.
            bin_size: Tamaño de los bins de edad (por defecto 5 años).

        Returns:
            DataFrame con estadísticas por grupo de edad.
        """
        df_calc = df[(df["INGLABO"] > 0) & df["P6040"].between(edad_min, edad_max)].copy()

        bins = [*list(range(edad_min, edad_max + 1, bin_size)), edad_max + 1]
        labels = [f"{b}–{b+bin_size-1}" for b in bins[:-1]]
        df_calc["GRUPO_EDAD"] = pd.cut(
            df_calc["P6040"],
            bins=bins,
            labels=labels,
            right=False,
            include_lowest=True,
        )

        filas = []
        for edad in df_calc["GRUPO_EDAD"].cat.categories:
            m = df_calc["GRUPO_EDAD"] == edad
            if m.sum() < 30:
                continue
            est = EP.resumen_completo(
                df_calc.loc[m, "INGLABO"],
                df_calc.loc[m, "FEX_ADJ"],
                self.config.smmlv,
            )
            if est:
                est["Grupo_edad"] = str(edad)
                filas.append(est)

        return pd.DataFrame(filas).dropna(subset=["Media"])


# ═════════════════════════════════════════════════════════════════════
# BRECHA SALARIAL DE GÉNERO
# ═════════════════════════════════════════════════════════════════════


class BrechaGenero:
    """Brecha salarial de género por nivel educativo.

    Módulo M6 del notebook original.
    Brecha% = (Mediana_M − Mediana_H) / Mediana_H × 100
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula la brecha salarial por nivel educativo agrupado.

        Args:
            df: DataFrame con NIVEL_GRUPO, P3271, INGLABO, FEX_ADJ.

        Returns:
            DataFrame con mediana por sexo y brecha %.
        """
        if "NIVEL_GRUPO" not in df.columns or "P3271" not in df.columns:
            print("⚠️ Columnas requeridas no disponibles.")
            return pd.DataFrame()

        df_calc = df[(df["OCI"] == 1) & (df["INGLABO"] > 0)].copy()

        filas = []
        for niv in sorted(df_calc["NIVEL_GRUPO"].dropna().unique()):
            for sexo_val, sexo_lbl in [(1, "Hombres"), (2, "Mujeres")]:
                m = (df_calc["NIVEL_GRUPO"] == niv) & (df_calc["P3271"] == sexo_val)
                med = EP.mediana(df_calc.loc[m, "INGLABO"], df_calc.loc[m, "FEX_ADJ"])
                mea = EP.media(df_calc.loc[m, "INGLABO"], df_calc.loc[m, "FEX_ADJ"])
                n = EP.suma(df_calc, m)
                filas.append(
                    {
                        "Nivel": niv,
                        "Sexo": sexo_lbl,
                        "Mediana": med,
                        "Media": mea,
                        "N_miles": n / 1_000,
                    }
                )

        df_edu = pd.DataFrame(filas).drop_duplicates(subset=["Nivel", "Sexo"])

        # Calcular brecha
        pivot = df_edu.pivot_table(index="Nivel", columns="Sexo", values="Mediana")
        if "Hombres" in pivot.columns and "Mujeres" in pivot.columns:
            pivot["Brecha_%"] = (pivot["Mujeres"] - pivot["Hombres"]) / pivot["Hombres"] * 100

        return pivot.dropna()


# ═════════════════════════════════════════════════════════════════════
# ANÁLISIS CRUZADO EMPRESA × DEPARTAMENTO
# ═════════════════════════════════════════════════════════════════════


class AnalisisCruzado:
    """Insatisfacción laboral y tamaño de empresa por departamento.

    Sección 3 del notebook original.
    """

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula deseo de cambio y distribución por tamaño de empresa.

        Args:
            df: DataFrame con NOMBRE_DPTO, P7130, P3069, P6920, FEX_ADJ, OCI.

        Returns:
            DataFrame con indicadores por departamento.
        """
        df_ocu = df[df["OCI"] == 1].copy()

        filas = []
        for dpto in df_ocu["NOMBRE_DPTO"].dropna().unique():
            m = df_ocu["NOMBRE_DPTO"] == dpto
            n_tot = df_ocu.loc[m, "FEX_ADJ"].sum()
            if n_tot < 5_000:
                continue

            fila: dict[str, Any] = {
                "Departamento": dpto,
                "Ocupados_M": round(n_tot / 1e6, 2),
            }

            # Deseo de cambio (P7130=1)
            if "P7130" in df_ocu.columns:
                n_cambia = df_ocu.loc[m & (df_ocu["P7130"] == 1), "FEX_ADJ"].sum()
                fila["Desea_cambiar_%"] = round(n_cambia / n_tot * 100, 1)

            # Formalidad (P6920=1 → cotiza pensión)
            if "P6920" in df_ocu.columns:
                n_pen = df_ocu.loc[m & (df_ocu["P6920"] == 1), "FEX_ADJ"].sum()
                fila["Cotiza_pension_%"] = round(n_pen / n_tot * 100, 1)

            filas.append(fila)

        resultado = pd.DataFrame(filas)
        if not resultado.empty:
            resultado = resultado.sort_values("Desea_cambiar_%", ascending=False)
        return resultado


# ═════════════════════════════════════════════════════════════════════
# ÍNDICES COMPUESTOS
# ═════════════════════════════════════════════════════════════════════


class IndicesCompuestos:
    """Calcula ICE, ICF, IVI, ICI e ITAT.

    Módulos M7, M13, M16, M20 del notebook original.
    Todos usan normalización min-max [0, 100].
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def ice(self, df: pd.DataFrame) -> pd.DataFrame:
        """Índice de Calidad del Empleo (ICE).

        ICE = 0.30×Pensión + 0.25×Salud + 0.25×Horas_adecuadas + 0.20×Ingreso≥SML
        """
        df_ocu = df[(df["OCI"] == 1)].copy()

        df_ocu["D_PENSION"] = (df_ocu["P6920"] == 1).astype(float)
        df_ocu["D_SALUD"] = (df_ocu["P6090"] == 1).astype(float) if "P6090" in df_ocu.columns else 0
        df_ocu["D_HORAS"] = (
            df_ocu["P6800"].between(20, 48).astype(float) if "P6800" in df_ocu.columns else 0
        )
        df_ocu["D_INGRESO"] = (df_ocu["INGLABO"] >= self.config.smmlv).astype(float)

        df_ocu["ICE"] = (
            0.30 * df_ocu["D_PENSION"]
            + 0.25 * df_ocu["D_SALUD"]
            + 0.25 * df_ocu["D_HORAS"]
            + 0.20 * df_ocu["D_INGRESO"]
        ) * 100

        return df_ocu

    def gini(self, df: pd.DataFrame) -> float:
        """Calcula el coeficiente de Gini del ingreso laboral.

        Módulo M5 del notebook original.
        """
        df_calc = df[(df["OCI"] == 1) & (df["INGLABO"] > 0)]
        return EP.gini(df_calc["INGLABO"], df_calc["FEX_ADJ"])


# ═════════════════════════════════════════════════════════════════════
# ANÁLISIS POR ÁREA GEOGRÁFICA (32 CIUDADES)
# ═════════════════════════════════════════════════════════════════════


class AnalisisArea:
    """Análisis de ocupados por CIIU y 32 ciudades/áreas metropolitanas.

    Produce las 6 tablas equivalentes al script GEIH 2022–2024.
    Requiere que AREA esté incluida en la consolidación.
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    def _mapear_agrupacion_dane_8(self, serie_ciiu: pd.Series) -> pd.Series:
        """Mapea CIIU numérico a la agrupación DANE de 8 grupos."""
        s = pd.to_numeric(serie_ciiu, errors="coerce").astype("float64")
        condiciones = []
        etiquetas = []
        for nombre, rangos in AGRUPACION_DANE_8.items():
            cond = pd.Series(False, index=s.index)
            for lo, hi in rangos:
                cond = cond | s.between(lo, hi)
            condiciones.append(cond)
            etiquetas.append(nombre)

        resultado = np.select(
            condiciones,
            np.array(etiquetas, dtype=object),
            default=None,
        )
        return pd.Series(resultado, index=serie_ciiu.index, dtype=object)

    def calcular_tablas(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Genera las 6 tablas de análisis por área.

        Returns:
            Dict con tabla1..tabla6.
        """
        df_ocu = df[(df["OCI"] == 1)].copy()
        df_ocu["AGRUPACION_DANE"] = self._mapear_agrupacion_dane_8(df_ocu["RAMA2D_R4"])

        tablas = {}

        # Tabla 1: Total nacional
        total = df_ocu["FEX_ADJ"].sum()
        tablas["tabla1"] = pd.DataFrame(
            [
                {
                    "Indicador": "Total Ocupados",
                    "Valor_miles": round(total / 1_000),
                }
            ]
        )

        # Tabla 2: Por agrupación DANE
        t2 = (
            df_ocu[df_ocu["AGRUPACION_DANE"].notna()]
            .groupby("AGRUPACION_DANE")["FEX_ADJ"]
            .sum()
            .reset_index()
            .rename(columns={"FEX_ADJ": "Ocupados"})
        )
        t2["Ocupados_miles"] = (t2["Ocupados"] / 1_000).round(0).astype(int)
        t2["Pct_%"] = (t2["Ocupados"] / total * 100).round(1)
        t2 = t2.sort_values("Ocupados", ascending=False)
        tablas["tabla2"] = t2

        # Tabla 4: Por ciudad
        if "CIUDAD" in df_ocu.columns:
            t4 = (
                df_ocu[df_ocu["CIUDAD"].notna()]
                .groupby("CIUDAD")["FEX_ADJ"]
                .sum()
                .reset_index()
                .rename(columns={"CIUDAD": "Ciudad_AM", "FEX_ADJ": "Ocupados"})
            )
            t4["Ocupados_miles"] = (t4["Ocupados"] / 1_000).round(0).astype(int)
            t4["Pct_%"] = (t4["Ocupados"] / total * 100).round(1)
            t4 = t4.sort_values("Ocupados", ascending=False)
            tablas["tabla4"] = t4

        # Tabla 6: Agrupación × División (sin ciudad)
        if "RAMA_INT" in df_ocu.columns:
            cols_grp = ["AGRUPACION_DANE", "RAMA_INT"]
            t6 = (
                df_ocu[df_ocu["AGRUPACION_DANE"].notna() & df_ocu["RAMA_INT"].notna()]
                .groupby(cols_grp, dropna=True)["FEX_ADJ"]
                .sum()
                .reset_index()
                .rename(columns={"FEX_ADJ": "Ocupados_miles", "RAMA_INT": "DIVISION"})
            )
            t6["Ocupados_miles"] = (t6["Ocupados_miles"] / 1_000).round(1)
            t6 = t6.sort_values("Ocupados_miles", ascending=False)
            tablas["tabla6"] = t6

        return tablas

    def exportar_excel(
        self,
        tablas: dict[str, pd.DataFrame],
        nombre: str = "Resultados_CIIU_Area_GEIH2025.xlsx",
    ) -> None:
        """Exporta todas las tablas a un archivo Excel con múltiples hojas."""
        nombres_hojas = {
            "tabla1": "Total Nacional",
            "tabla2": "Agrupación DANE",
            "tabla4": "Ciudad-AM",
            "tabla6": "Agrupación-CIIU",
        }

        with pd.ExcelWriter(nombre, engine="openpyxl") as writer:
            for key, hoja in nombres_hojas.items():
                if key in tablas:
                    tablas[key].to_excel(writer, sheet_name=hoja, index=False)

        print(f"✅ Excel exportado: {nombre}")
