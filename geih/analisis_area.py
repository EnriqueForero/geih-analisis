# -*- coding: utf-8 -*-
"""
geih.analisis_area — Ocupados por CIIU y 32 ciudades/áreas metropolitanas.

Replica y mejora el módulo del notebook original (script histórico 2022–2024):
  - 6 tablas: total nacional, agrupación DANE, dominio geográfico,
    ciudad/AM, granular CIIU×ciudad, CIIU nacional
  - 3 gráficos: barras agrupación, barras ciudades, heatmap rama×ciudad
  - Exportación a Excel multi-hoja

Usa la variable AREA (código DIVIPOLA de 5 dígitos del módulo Ocupados)
para identificar 32 ciudades y áreas metropolitanas del DANE.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "AnalisisOcupadosCiudad",
]


import gc
from pathlib import Path
from typing import Optional, Dict, List

import numpy as np
import pandas as pd

from .config import (
    ConfigGEIH,
    AREA_A_CIUDAD,
    DPTO_A_CIUDAD,
    CIUDADES_13_PRINCIPALES,
    CIUDADES_10_INTERMEDIAS,
    _AGRUP_DANE_POR_DIVISION,
    REF_DANE_2025,
    REF_DANE,
)
from .utils import ConversorTipos


class AnalisisOcupadosCiudad:
    """Ocupados por actividad económica CIIU y 32 ciudades DANE.

    Produce 6 tablas que replican la estructura del script GEIH 2022–2024:
      tabla1: Total nacional de ocupados (con validación DANE)
      tabla2: Ocupados por Agrupación DANE (8 grupos CIIU)
      tabla3: Ocupados por dominio geográfico (13 ciudades, 10 intermedias, otras)
      tabla4: Ocupados por ciudad y área metropolitana (top 23)
      tabla5: Granular → Agrupación × División × CIIU × Ciudad
      tabla6: Agrupación × División × CIIU (nacional, sin ciudad)

    Uso típico:
        analisis = AnalisisOcupadosCiudad(config=ConfigGEIH(n_meses=12))
        tablas = analisis.calcular(geih_2025_final)
        analisis.imprimir(tablas)
        analisis.exportar_excel(tablas, exportador)
        fig = analisis.graficar(tablas)
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()

    # ═══════════════════════════════════════════════════════════════
    # MÉTODO PRINCIPAL
    # ═══════════════════════════════════════════════════════════════

    def calcular(
        self,
        df_raw: pd.DataFrame,
        ruta_ciiu: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Calcula las 6 tablas de ocupados por CIIU y área geográfica.

        Args:
            df_raw: Base GEIH consolidada (cruda o preparada).
            ruta_ciiu: Ruta al Excel de correlativa CIIU (opcional).
                      Si se provee, agrega DESCRIPCION_CIIU a tablas 5 y 6.

        Returns:
            Dict con 'tabla1' a 'tabla6', más 'df_trabajo' para gráficos.
        """
        df = self._preparar(df_raw)

        # Merge CIIU descriptivo si hay correlativa
        if ruta_ciiu:
            df = self._merge_ciiu(df, ruta_ciiu)

        total = df["FEX_ADJ"].sum()

        tablas = {
            "tabla1": self._tabla1_total(total),
            "tabla2": self._tabla2_agrupacion(df, total),
            "tabla3": self._tabla3_dominio(df, total),
            "tabla4": self._tabla4_ciudad(df, total),
            "tabla5": self._tabla5_granular(df),
            "tabla6": self._tabla6_nacional(df),
            "df_trabajo": df,
        }

        print(f"\n   ✅ 6 tablas calculadas — {len(df):,} ocupados, "
              f"{total/1e6:.2f}M expandidos")
        return tablas

    # ═══════════════════════════════════════════════════════════════
    # PREPARACIÓN DE DATOS
    # ═══════════════════════════════════════════════════════════════

    def _preparar(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Extrae columnas necesarias, filtra ocupados, mapea área y CIIU."""
        cols = ["FEX_C18", "OCI", "DPTO", "RAMA2D_R4", "RAMA4D_R4", "MES_NUM"]
        if "AREA" in df_raw.columns:
            cols.append("AREA")
        cols_ok = [c for c in cols if c in df_raw.columns]
        df = df_raw[cols_ok].copy()

        # Tipos
        df["FEX_C18"] = ConversorTipos.a_numerico(df["FEX_C18"]).fillna(0)
        df["OCI"] = ConversorTipos.a_numerico(df["OCI"])
        df["FEX_ADJ"] = df["FEX_C18"] / self.config.n_meses

        # Solo ocupados
        df = df[df["OCI"] == 1].copy()
        gc.collect()

        n_total = df["FEX_ADJ"].sum()
        ref = self.config.referencia_dane
        ref_ocu = f"~{ref.ocupados_anual_m} M" if ref else "N/D"
        print(f"   Ocupados totales (anual): {n_total/1e6:.2f} M  "
              f"(ref. DANE: {ref_ocu})")

        # Área geográfica → Ciudad/AM
        df["DPTO_STR"] = ConversorTipos.estandarizar_dpto(df["DPTO"])

        if "AREA" in df.columns:
            df["AREA_STR"] = ConversorTipos.estandarizar_area(df["AREA"])
            df["CIUDAD_AM"] = df["AREA_STR"].map(AREA_A_CIUDAD)
            # Fallback con DPTO para registros sin match en AREA
            fallback = df["DPTO_STR"].map(DPTO_A_CIUDAD)
            df["CIUDAD_AM"] = df["CIUDAD_AM"].fillna(fallback)
            print(f"   ✅ Variable AREA disponible — análisis por 32 ciudades habilitado")
        else:
            df["CIUDAD_AM"] = df["DPTO_STR"].map(DPTO_A_CIUDAD)
            print(f"   ⚠️ AREA no disponible — usando DPTO como proxy")

        # Dominio geográfico
        df["DOMINIO"] = df["CIUDAD_AM"].apply(self._asignar_dominio)

        # CIIU: División (2 dígitos) y Agrupación DANE (8 grupos)
        df["DIVISION"] = self._extraer_division(df["RAMA2D_R4"])
        df["AGRUPACION_DANE"] = df["DIVISION"].map(_AGRUP_DANE_POR_DIVISION).fillna("No informa")

        # CIIU 4 dígitos estandarizado
        df["RAMA4D_STD"] = ConversorTipos.estandarizar_ciiu4(df["RAMA4D_R4"])

        return df

    @staticmethod
    def _extraer_division(serie: pd.Series) -> pd.Series:
        """Extrae código de División CIIU (2 dígitos) de RAMA2D_R4."""
        num = pd.to_numeric(serie, errors="coerce")
        return num.round(0).astype("Int64").astype(str).str.zfill(2).where(num.notna())

    @staticmethod
    def _asignar_dominio(ciudad: str) -> str:
        if ciudad in CIUDADES_13_PRINCIPALES:
            return "13 ciudades y A.M."
        elif ciudad in CIUDADES_10_INTERMEDIAS:
            return "10 ciudades intermedias"
        elif pd.notna(ciudad):
            return "Otras cabeceras / Rural"
        return "No identificado"

    def _merge_ciiu(self, df: pd.DataFrame, ruta_ciiu: str) -> pd.DataFrame:
        """Merge con correlativa CIIU para agregar descripción textual."""
        try:
            df_ciiu = pd.read_excel(
                ruta_ciiu, sheet_name="CIIU 2022",
                converters={"RAMA4D_R4": str},
            )
            df_ciiu["RAMA4D_STD"] = ConversorTipos.estandarizar_ciiu4(df_ciiu["RAMA4D_R4"])
            slim = df_ciiu[["RAMA4D_STD", "DESCRIPCION_CIIU"]].drop_duplicates("RAMA4D_STD")
            df = df.merge(slim, on="RAMA4D_STD", how="left")
            pct = df["DESCRIPCION_CIIU"].notna().mean() * 100
            print(f"   ✅ CIIU descripción: {pct:.0f}% con match")
        except Exception as e:
            print(f"   ⚠️ Sin correlativa CIIU: {e}")
            df["DESCRIPCION_CIIU"] = df["AGRUPACION_DANE"]
        return df

    # ═══════════════════════════════════════════════════════════════
    # LAS 6 TABLAS
    # ═══════════════════════════════════════════════════════════════

    def _tabla1_total(self, total: float) -> pd.DataFrame:
        ref_dane = self.config.referencia_dane
        if ref_dane and ref_dane.ocupados_anual_m > 0:
            ref = round(ref_dane.ocupados_anual_m * 1_000)
            diff_pct = round((round(total / 1_000) - ref) / ref * 100, 1)
        else:
            ref = 0
            diff_pct = 0.0
        calc = round(total / 1_000)
        return pd.DataFrame([{
            "Período": self.config.periodo_etiqueta,
            "Ocupados_miles": calc,
            "Referencia_DANE_miles": ref if ref > 0 else "N/D",
            "Diferencia_%": diff_pct if ref > 0 else "N/D",
        }])

    @staticmethod
    def _tabla2_agrupacion(df: pd.DataFrame, total: float) -> pd.DataFrame:
        t = (
            df.groupby("AGRUPACION_DANE")["FEX_ADJ"]
            .sum().reset_index()
            .rename(columns={"FEX_ADJ": "Ocupados"})
            .sort_values("Ocupados", ascending=False)
        )
        t["Ocupados_miles"] = (t["Ocupados"] / 1_000).round(0).astype(int)
        t["Pct_%"] = (t["Ocupados"] / total * 100).round(1)
        return t

    @staticmethod
    def _tabla3_dominio(df: pd.DataFrame, total: float) -> pd.DataFrame:
        t = (
            df.groupby("DOMINIO")["FEX_ADJ"]
            .sum().reset_index()
            .rename(columns={"FEX_ADJ": "Ocupados"})
            .sort_values("Ocupados", ascending=False)
        )
        t["Ocupados_miles"] = (t["Ocupados"] / 1_000).round(0).astype(int)
        t["Pct_%"] = (t["Ocupados"] / total * 100).round(1)
        return t

    @staticmethod
    def _tabla4_ciudad(df: pd.DataFrame, total: float) -> pd.DataFrame:
        t = (
            df[df["CIUDAD_AM"].notna()]
            .groupby("CIUDAD_AM")["FEX_ADJ"]
            .sum().reset_index()
            .rename(columns={"CIUDAD_AM": "Ciudad_AM", "FEX_ADJ": "Ocupados"})
            .sort_values("Ocupados", ascending=False)
        )
        t["Ocupados_miles"] = (t["Ocupados"] / 1_000).round(0).astype(int)
        t["Pct_%"] = (t["Ocupados"] / total * 100).round(1)
        t["Dominio"] = t["Ciudad_AM"].apply(AnalisisOcupadosCiudad._asignar_dominio)
        return t

    @staticmethod
    def _tabla5_granular(df: pd.DataFrame) -> pd.DataFrame:
        cols = ["AGRUPACION_DANE", "DIVISION", "RAMA4D_STD", "CIUDAD_AM"]
        if "DESCRIPCION_CIIU" in df.columns:
            cols = ["AGRUPACION_DANE", "DIVISION", "RAMA4D_STD",
                    "DESCRIPCION_CIIU", "CIUDAD_AM"]
        t = (
            df[df["CIUDAD_AM"].notna() & df["DIVISION"].notna()]
            .groupby(cols, dropna=True)["FEX_ADJ"]
            .sum().reset_index()
            .rename(columns={"FEX_ADJ": "Ocupados_miles"})
        )
        t["Ocupados_miles"] = (t["Ocupados_miles"] / 1_000).round(1)
        return t.sort_values(["AGRUPACION_DANE", "Ocupados_miles"], ascending=[True, False])

    @staticmethod
    def _tabla6_nacional(df: pd.DataFrame) -> pd.DataFrame:
        cols = ["AGRUPACION_DANE", "DIVISION", "RAMA4D_STD"]
        if "DESCRIPCION_CIIU" in df.columns:
            cols = ["AGRUPACION_DANE", "DIVISION", "RAMA4D_STD", "DESCRIPCION_CIIU"]
        t = (
            df[df["DIVISION"].notna()]
            .groupby(cols, dropna=True)["FEX_ADJ"]
            .sum().reset_index()
            .rename(columns={"FEX_ADJ": "Ocupados_miles"})
        )
        t["Ocupados_miles"] = (t["Ocupados_miles"] / 1_000).round(1)
        return t.sort_values("Ocupados_miles", ascending=False)

    # ═══════════════════════════════════════════════════════════════
    # IMPRESIÓN DE TABLAS
    # ═══════════════════════════════════════════════════════════════

    def imprimir(self, tablas: Dict[str, pd.DataFrame]) -> None:
        """Imprime las 6 tablas en formato legible para el notebook."""
        print(f"\n{'='*70}")
        print(f"  OCUPADOS POR CIIU Y ÁREA — GEIH {self.config.periodo_etiqueta}")
        print(f"  FEX_C18 / {self.config.n_meses} | Miles de personas")
        print(f"{'='*70}")

        # Tabla 1
        print(f"\n{'─'*50}")
        print(f"  TABLA 1: Total nacional")
        print(f"{'─'*50}")
        print(tablas["tabla1"].to_string(index=False))

        # Tabla 2
        t2 = tablas["tabla2"]
        print(f"\n{'─'*70}")
        print(f"  TABLA 2: Agrupación DANE (8 grupos CIIU)")
        print(f"{'─'*70}")
        print(f"  {'Agrupación DANE':<55} {'Miles':>7} {'%':>6}")
        print(f"  {'─'*55} {'─'*7} {'─'*6}")
        for _, row in t2.iterrows():
            print(f"  {str(row['AGRUPACION_DANE']):<55} "
                  f"{row['Ocupados_miles']:>7,} {row['Pct_%']:>5.1f}%")
        print(f"  {'─'*55} {'─'*7}")
        print(f"  {'TOTAL':<55} {t2['Ocupados_miles'].sum():>7,}")

        # Tabla 3
        print(f"\n{'─'*60}")
        print(f"  TABLA 3: Dominio geográfico DANE")
        print(f"{'─'*60}")
        print(tablas["tabla3"][["DOMINIO", "Ocupados_miles", "Pct_%"]].to_string(index=False))

        # Tabla 4
        t4 = tablas["tabla4"]
        print(f"\n{'─'*65}")
        print(f"  TABLA 4: Top 23 ciudades y áreas metropolitanas")
        print(f"{'─'*65}")
        print(f"  {'Ciudad / AM':<35} {'Miles':>7} {'%':>6} {'Dominio'}")
        print(f"  {'─'*35} {'─'*7} {'─'*6} {'─'*25}")
        for _, row in t4.head(23).iterrows():
            print(f"  {str(row['Ciudad_AM']):<35} {row['Ocupados_miles']:>7,} "
                  f"{row['Pct_%']:>5.1f}%  {row['Dominio']}")

        # Tablas 5 y 6 (resumen)
        print(f"\n{'─'*50}")
        print(f"  TABLA 5: Granular (Agrupación × CIIU × Ciudad)")
        print(f"  {len(tablas['tabla5']):,} combinaciones únicas")
        print(f"{'─'*50}")
        print(tablas["tabla5"].head(10).to_string(index=False))

        print(f"\n{'─'*65}")
        print(f"  TABLA 6: Top 20 actividades CIIU nacional")
        print(f"{'─'*65}")
        print(tablas["tabla6"].head(20).to_string(index=False))

    # ═══════════════════════════════════════════════════════════════
    # GRÁFICOS
    # ═══════════════════════════════════════════════════════════════

    def graficar(self, tablas: Dict[str, pd.DataFrame]):
        """Genera panel de 3 gráficos: agrupación, ciudades, heatmap.

        Returns:
            Figura matplotlib.
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import matplotlib.colors as mcolors
        from matplotlib.gridspec import GridSpec

        FONDO = "#F7F9FC"
        COLORES_AGRUP = [
            "#2E6DA4", "#C0392B", "#1E8449", "#8E44AD",
            "#E67E22", "#1ABC9C", "#F39C12", "#7F8C8D",
        ]

        fig = plt.figure(figsize=(20, 12))
        fig.patch.set_facecolor(FONDO)
        gs = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.38)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, :])
        for ax in [ax1, ax2, ax3]:
            ax.set_facecolor("white")
            ax.spines[["top", "right"]].set_visible(False)

        t2 = tablas["tabla2"]
        t4 = tablas["tabla4"]

        # ── Panel 1: Agrupación DANE ───────────────────────────
        t2p = t2.sort_values("Ocupados_miles", ascending=True)
        y1 = range(len(t2p))
        ax1.barh(y1, t2p["Ocupados_miles"], 0.65,
                 color=COLORES_AGRUP[:len(t2p)], alpha=0.88)
        for i, (_, row) in enumerate(t2p.iterrows()):
            ax1.text(row["Ocupados_miles"] + 30, i,
                     f"{row['Ocupados_miles']:,.0f}K  ({row['Pct_%']:.1f}%)",
                     va="center", fontsize=8.5)
        ax1.set_yticks(y1)
        ax1.set_yticklabels([str(r)[:35] for r in t2p["AGRUPACION_DANE"]], fontsize=8.5)
        ax1.set_xlabel("Miles de ocupados", fontsize=10)
        ax1.set_title("Agrupación DANE — 8 grupos CIIU", fontsize=11, fontweight="bold")
        ax1.grid(axis="x", alpha=0.3)

        # ── Panel 2: Top 15 ciudades ──────────────────────────
        t4top = t4.head(15).sort_values("Ocupados_miles", ascending=True)
        col_c = [
            "#2E6DA4" if d == "13 ciudades y A.M."
            else ("#1ABC9C" if d == "10 ciudades intermedias" else "#7F8C8D")
            for d in t4top["Dominio"]
        ]
        ax2.barh(range(len(t4top)), t4top["Ocupados_miles"], 0.65, color=col_c, alpha=0.88)
        for i, (_, row) in enumerate(t4top.iterrows()):
            ax2.text(row["Ocupados_miles"] + 10, i, f"{row['Ocupados_miles']:,.0f}K",
                     va="center", fontsize=8.5)
        ax2.set_yticks(range(len(t4top)))
        ax2.set_yticklabels(t4top["Ciudad_AM"], fontsize=9)
        ax2.set_xlabel("Miles de ocupados", fontsize=10)
        ax2.set_title("Top 15 ciudades y AM", fontsize=11, fontweight="bold")
        leyenda = [
            mpatches.Patch(color="#2E6DA4", alpha=0.88, label="13 ciudades principales"),
            mpatches.Patch(color="#1ABC9C", alpha=0.88, label="10 ciudades intermedias"),
            mpatches.Patch(color="#7F8C8D", alpha=0.88, label="Otras"),
        ]
        ax2.legend(handles=leyenda, fontsize=8, loc="lower right")
        ax2.grid(axis="x", alpha=0.3)

        # ── Panel 3: Heatmap Agrupación × Ciudad ─────────────
        df = tablas["df_trabajo"]
        ciudades_top = t4.head(8)["Ciudad_AM"].tolist()
        agrup_orden = t2.sort_values("Ocupados", ascending=False)["AGRUPACION_DANE"].tolist()

        hm = np.zeros((len(agrup_orden), len(ciudades_top)))
        for i, agrup in enumerate(agrup_orden):
            for j, ciudad in enumerate(ciudades_top):
                m = (df["AGRUPACION_DANE"] == agrup) & (df["CIUDAD_AM"] == ciudad)
                hm[i, j] = df.loc[m, "FEX_ADJ"].sum() / 1_000

        cmap = mcolors.LinearSegmentedColormap.from_list("bw", ["#FFFFFF", "#2E6DA4"])
        im = ax3.imshow(hm, cmap=cmap, aspect="auto", vmin=0)
        plt.colorbar(im, ax=ax3, label="Miles de ocupados", pad=0.01)
        for i in range(len(agrup_orden)):
            for j in range(len(ciudades_top)):
                v = hm[i, j]
                if v >= 10:
                    ax3.text(j, i, f"{v:,.0f}K", ha="center", va="center",
                             fontsize=7.5, fontweight="bold",
                             color="white" if v > hm.max() * 0.5 else "#1A1A1A")
        ax3.set_xticks(range(len(ciudades_top)))
        ax3.set_xticklabels(ciudades_top, fontsize=9, rotation=20, ha="right")
        ax3.set_yticks(range(len(agrup_orden)))
        ax3.set_yticklabels([str(a)[:40] for a in agrup_orden], fontsize=8.5)
        ax3.set_title("Heatmap: Agrupación DANE × Ciudad principal",
                       fontsize=11, fontweight="bold")

        fig.suptitle(
            f"Ocupados por CIIU y Área Geográfica — GEIH {self.config.periodo_etiqueta}\n"
            f"Ponderado FEX_C18/{self.config.n_meses} | 8 grupos DANE | 32 ciudades",
            fontsize=13, fontweight="bold",
        )
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        return fig

    # ═══════════════════════════════════════════════════════════════
    # EXPORTACIÓN A EXCEL
    # ═══════════════════════════════════════════════════════════════

    def exportar_excel(
        self,
        tablas: Dict[str, pd.DataFrame],
        ruta: str = "Resultados_CIIU_Area_GEIH2025.xlsx",
    ) -> None:
        """Exporta las 6 tablas a un Excel con una hoja por tabla.

        Args:
            tablas: Output de calcular().
            ruta: Path completo del archivo Excel de salida.
        """
        hojas = {
            "Total Nacional":           tablas["tabla1"],
            "Agrupación DANE":          tablas["tabla2"][["AGRUPACION_DANE", "Ocupados_miles", "Pct_%"]],
            "Dominio Geográfico":       tablas["tabla3"][["DOMINIO", "Ocupados_miles", "Pct_%"]],
            "Ciudad-AM":                tablas["tabla4"][["Ciudad_AM", "Dominio", "Ocupados_miles", "Pct_%"]],
            "Agrupación-CIIU-Ciudad":   tablas["tabla5"],
            "Agrupación-CIIU":          tablas["tabla6"],
        }

        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            for nombre_hoja, df in hojas.items():
                df.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)

        print(f"   ✅ Excel: {Path(ruta).name} ({len(hojas)} hojas)")
        for nombre in hojas:
            print(f"      • {nombre}")
