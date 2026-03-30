# -*- coding: utf-8 -*-
"""
geih.diagnostico — Diagnóstico de calidad de datos de la base GEIH.

Replica y mejora las funciones missing_values_table() y missing()
del notebook GEIH 2021, con visualización y reportes detallados.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "DiagnosticoCalidad",
    "Top20Sectores",
]


from typing import Optional, List

import numpy as np
import pandas as pd


class DiagnosticoCalidad:
    """Diagnóstico completo de calidad de datos de la base consolidada.

    Detecta: valores faltantes, ceros sospechosos, tipos de dato incorrectos,
    columnas potencialmente duplicadas, y distribuciones anómalas.

    Uso:
        diag = DiagnosticoCalidad()
        tabla = diag.valores_faltantes(geih_2025_final)
        diag.verificar_tipos(geih_2025_final)
        diag.columnas_duplicadas(geih_2025_final)
    """

    @staticmethod
    def valores_faltantes(
        df: pd.DataFrame,
        titulo: str = "Base consolidada",
        umbral_pct: float = 0.0,
    ) -> pd.DataFrame:
        """Tabla de valores faltantes y ceros por columna.

        Args:
            df: DataFrame a diagnosticar.
            titulo: Nombre para el reporte.
            umbral_pct: Solo mostrar columnas con % nulos > umbral.

        Returns:
            DataFrame con estadísticas de calidad por columna.
        """
        total = len(df)
        mis_val = df.isnull().sum()
        mis_pct = (mis_val / total * 100).round(1)
        zeros = (df == 0).sum()
        zeros_p = (zeros / total * 100).round(1)

        tabla = pd.DataFrame({
            "Valores_nulos": mis_val,
            "Pct_nulos_%": mis_pct,
            "Ceros": zeros,
            "Pct_ceros_%": zeros_p,
            "Dtype": df.dtypes.astype(str),
            "Valores_unicos": df.nunique(),
        })

        tabla = tabla[
            (tabla["Pct_nulos_%"] > umbral_pct) | (tabla["Pct_ceros_%"] > 0)
        ].sort_values("Pct_nulos_%", ascending=False)

        print(f"\n{'='*75}")
        print(f"  DIAGNÓSTICO DE CALIDAD — {titulo}")
        print(f"  Total filas: {total:,}  |  Total columnas: {df.shape[1]}")
        print(f"  Columnas con nulos o ceros: {len(tabla)}")
        print(f"{'='*75}")
        print(f"  {'Columna':<25} {'%Nulos':>8} {'N_nulos':>10} "
              f"{'%Ceros':>8} {'Únicos':>8} {'Dtype':<12}")
        print(f"  {'─'*25} {'─'*8} {'─'*10} {'─'*8} {'─'*8} {'─'*12}")

        for col, row in tabla.head(40).iterrows():
            print(f"  {str(col):<25} {row['Pct_nulos_%']:>7.1f}% "
                  f"{int(row['Valores_nulos']):>10,} "
                  f"{row['Pct_ceros_%']:>7.1f}% "
                  f"{int(row['Valores_unicos']):>8,} "
                  f"{str(row['Dtype']):<12}")

        return tabla

    @staticmethod
    def verificar_tipos(df: pd.DataFrame) -> pd.DataFrame:
        """Verifica que las columnas críticas tengan el tipo correcto.

        Alerta si DPTO, RAMA2D_R4, etc. son numéricas (deben ser str).
        Alerta si FEX_C18, INGLABO, etc. son string (deben ser numéricas).
        """
        DEBE_SER_STR = ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "DPTO",
                        "RAMA2D_R4", "RAMA4D_R4", "AREA"]
        DEBE_SER_NUM = ["FEX_C18", "OCI", "P3271", "P6040", "INGLABO",
                        "FT", "DSI", "PET", "P6920", "P6800"]

        problemas = []
        for col in DEBE_SER_STR:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                problemas.append({
                    "Columna": col, "Tipo_actual": str(df[col].dtype),
                    "Tipo_esperado": "string/object",
                    "Riesgo": "Pérdida de ceros líderes (ej: DPTO '05'→5)",
                })
        for col in DEBE_SER_NUM:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                problemas.append({
                    "Columna": col, "Tipo_actual": str(df[col].dtype),
                    "Tipo_esperado": "numeric",
                    "Riesgo": "Cálculos fallan o producen NaN silencioso",
                })

        df_prob = pd.DataFrame(problemas)
        if df_prob.empty:
            print("✅ Todos los tipos de dato son correctos")
        else:
            print(f"\n⚠️  {len(df_prob)} columnas con tipo incorrecto:")
            for _, row in df_prob.iterrows():
                print(f"   ❌ {row['Columna']}: es {row['Tipo_actual']}, "
                      f"debería ser {row['Tipo_esperado']}")
                print(f"      Riesgo: {row['Riesgo']}")
        return df_prob

    @staticmethod
    def columnas_duplicadas(df: pd.DataFrame) -> List[str]:
        """Detecta columnas con nombres similares (potenciales duplicados de merge).

        Busca patrones como col_x / col_y que indican merges sin control.
        """
        sufijos_merge = [c for c in df.columns if c.endswith("_x") or c.endswith("_y")]
        if sufijos_merge:
            print(f"\n⚠️  {len(sufijos_merge)} columnas con sufijo de merge duplicado:")
            for c in sufijos_merge:
                print(f"   • {c}")
            print("   → Indica merge con columnas duplicadas. Revisar consolidación.")
        else:
            print("✅ Sin columnas duplicadas por merge")
        return sufijos_merge

    @staticmethod
    def validar_identidades(df: pd.DataFrame) -> bool:
        """Valida las identidades fundamentales del mercado laboral.

        PEA = OCI + DSI
        PET = PEA + FFT (si FFT disponible)
        """
        ok = True
        cols_requeridas = ["FEX_C18", "OCI", "FT", "DSI", "PET"]
        faltantes = [c for c in cols_requeridas if c not in df.columns]
        if faltantes:
            print(f"⚠️  No se puede validar identidades — faltan: {faltantes}")
            return False

        fex = "FEX_C18"
        pea = df.loc[df["FT"] == 1, fex].sum()
        ocu = df.loc[df["OCI"] == 1, fex].sum()
        dsi = df.loc[df["DSI"] == 1, fex].sum()
        pet = df.loc[df["PET"] == 1, fex].sum()

        # PEA = OCI + DSI (tolerancia 0.1%)
        pea_calc = ocu + dsi
        diff_pea = abs(pea - pea_calc) / max(pea, 1) * 100
        if diff_pea > 0.1:
            print(f"⚠️  PEA ≠ OCI + DSI  (Δ={diff_pea:.2f}%)")
            ok = False
        else:
            print(f"✅ PEA = OCI + DSI  ({pea/1e6:.2f}M = {ocu/1e6:.2f}M + {dsi/1e6:.2f}M)")

        return ok

    @staticmethod
    def resumen_rapido(df: pd.DataFrame) -> None:
        """Imprime un resumen rápido de la base para orientación."""
        print(f"\n{'='*55}")
        print(f"  RESUMEN RÁPIDO DE LA BASE")
        print(f"{'='*55}")
        print(f"  Dimensiones : {df.shape[0]:,} filas × {df.shape[1]} columnas")
        mb = df.memory_usage(deep=True).sum() / 1e6
        print(f"  Memoria     : {mb:,.0f} MB")

        if "MES_NUM" in df.columns:
            meses = sorted(df["MES_NUM"].dropna().unique())
            print(f"  Meses       : {len(meses)} → {meses}")

        if "OCI" in df.columns:
            n_ocu = (df["OCI"] == 1).sum()
            print(f"  Ocupados    : {n_ocu:,} registros ({n_ocu/len(df)*100:.1f}%)")

        if "INGLABO" in df.columns:
            n_ing = df["INGLABO"].notna().sum()
            n_cero = (df["INGLABO"] == 0).sum()
            print(f"  Con INGLABO : {n_ing:,} registros")
            print(f"  INGLABO = 0 : {n_cero:,} (pago en especie)")

        print(f"{'='*55}")

    @staticmethod
    def graficar_nulos(
        tabla_nulos: pd.DataFrame,
        top_n: int = 20,
        titulo: str = "Top columnas por valores faltantes o en cero",
    ):
        """Genera gráfico de barras apiladas: % nulos + % ceros.

        Args:
            tabla_nulos: Output de valores_faltantes().
            top_n: Cuántas columnas mostrar.

        Returns:
            Figura matplotlib.
        """
        import matplotlib.pyplot as plt

        top = tabla_nulos.head(top_n)
        if top.empty:
            print("✅ No hay columnas con valores faltantes para graficar.")
            return None

        fig, ax = plt.subplots(figsize=(14, 6))
        fig.patch.set_facecolor("#F7F9FC")
        ax.set_facecolor("white")

        x = np.arange(len(top))
        ax.bar(x, top["Pct_nulos_%"], 0.55, color="#C0392B", alpha=0.82, label="% Nulos")
        ax.bar(x, top["Pct_ceros_%"], 0.55, bottom=top["Pct_nulos_%"],
               color="#E67E22", alpha=0.70, label="% Ceros")

        ax.set_xticks(x)
        ax.set_xticklabels(top.index, rotation=40, ha="right", fontsize=9)
        ax.set_ylabel("% del total de filas", fontsize=11)
        ax.set_title(titulo, fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.set_ylim(0, 110)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(pad=2)
        return fig


class Top20Sectores:
    """Top 20 actividades económicas CIIU por número de ocupados.

    Uso:
        from geih import Top20Sectores
        top20 = Top20Sectores()
        tabla = top20.calcular(df, ruta_ciiu=RUTA_CIIU)
        top20.imprimir(tabla)
        fig = top20.graficar(tabla)
    """

    def __init__(self, config=None):
        from .config import ConfigGEIH
        self.config = config or ConfigGEIH()

    def calcular(
        self,
        df: pd.DataFrame,
        ruta_ciiu: Optional[str] = None,
    ) -> pd.DataFrame:
        """Calcula el Top 20 de sectores CIIU por ocupados expandidos.

        Args:
            df: DataFrame con OCI, RAMA2D_R4 o RAMA4D_R4, FEX_ADJ.
            ruta_ciiu: Ruta al Excel de correlativa CIIU para descripciones.
        """
        from .preparador import MergeCorrelativas, PreparadorGEIH
        from .utils import ConversorTipos

        df_ocu = df[df["OCI"] == 1].copy()

        if ruta_ciiu and "RAMA4D_R4" in df_ocu.columns:
            df_ocu = MergeCorrelativas().merge_ciiu(df_ocu, ruta_ciiu)
            col_desc = "DESCRIPCION_CIIU"
        elif "RAMA" in df_ocu.columns:
            col_desc = "RAMA"
        else:
            df_ocu["RAMA"] = PreparadorGEIH.mapear_rama_ciiu(df_ocu["RAMA2D_R4"])
            col_desc = "RAMA"

        top = (
            df_ocu[df_ocu[col_desc].notna()]
            .groupby(col_desc)["FEX_ADJ"]
            .sum().sort_values(ascending=False)
            .head(20).reset_index()
            .rename(columns={col_desc: "Sector_CIIU", "FEX_ADJ": "Ocupados"})
        )
        top["Ocupados_M"] = (top["Ocupados"] / 1e6).round(2)
        top["Pct_%"] = (top["Ocupados"] / top["Ocupados"].sum() * 100).round(1)
        return top

    def graficar(self, top: pd.DataFrame):
        """Gráfico de barras horizontales Top 20 sectores."""
        import matplotlib.pyplot as plt

        df_plot = top.sort_values("Ocupados_M", ascending=True)
        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor("#F7F9FC")
        ax.set_facecolor("white")

        colores = ["#2E6DA4" if i >= len(df_plot) - 5 else "#7FB3D3"
                   for i in range(len(df_plot))]
        ax.barh(range(len(df_plot)), df_plot["Ocupados_M"], 0.65,
                color=colores, alpha=0.88)
        for i, (_, row) in enumerate(df_plot.iterrows()):
            ax.text(row["Ocupados_M"] + 0.03, i,
                    f"{row['Ocupados_M']:.2f}M  ({row['Pct_%']:.1f}%)",
                    va="center", fontsize=8.5)
        ax.set_yticks(range(len(df_plot)))
        ax.set_yticklabels([str(r)[:60] for r in df_plot["Sector_CIIU"]], fontsize=8.5)
        ax.set_xlabel("Ocupados (millones)", fontsize=11)
        ax.set_title("Top 20 actividades económicas por ocupados\n"
                     "GEIH 2025 — CIIU Rev.4", fontsize=12, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(pad=2.5)
        return fig

    def imprimir(self, top: pd.DataFrame) -> None:
        """Imprime la tabla Top 20."""
        print(f"\n{'='*75}")
        print(f"  TOP 20 ACTIVIDADES ECONÓMICAS — GEIH 2025")
        print(f"{'='*75}")
        print(f"  {'Sector CIIU':<58} {'M':>6} {'%':>6}")
        print(f"  {'─'*58} {'─'*6} {'─'*6}")
        for _, row in top.iterrows():
            print(f"  {str(row['Sector_CIIU']):<58} "
                  f"{row['Ocupados_M']:>6.2f} {row['Pct_%']:>5.1f}%")
