"""
geih.visualizacion — Generación de gráficos para el análisis GEIH.

Cada clase produce un tipo de gráfico. Las clases solo DIBUJAN;
nunca calculan indicadores (eso es responsabilidad de `indicadores.py`).

Convención: todos los métodos retornan la figura matplotlib para que
el usuario pueda ajustarla, guardarla o mostrarla desde el notebook.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "EstiloBase",
    "GraficoDistribucionIngresos",
    "GraficoBoxPlotSalarios",
    "GraficoBrechaGenero",
    "GraficoRamaSexo",
    "GraficoCurvaLorenz",
    "GraficoICIBubble",
    "GraficoEstacionalidad",
    "GraficoContribucionHeatmap",
]


import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from .config import COLORES, SMMLV_2025


class EstiloBase:
    """Configuración de estilo compartida por todos los gráficos."""

    FONDO = COLORES["fondo"]
    C = COLORES

    @staticmethod
    def configurar_ejes(ax, titulo: str = "", xlabel: str = "", ylabel: str = ""):
        """Aplica estilo base a un eje matplotlib."""
        ax.set_facecolor("white")
        ax.spines[["top", "right"]].set_visible(False)
        if titulo:
            ax.set_title(titulo, fontsize=12, fontweight="bold", pad=12)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=11)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11)
        ax.grid(axis="x", alpha=0.3, zorder=0)

    @staticmethod
    def crear_figura(ancho: float = 14, alto: float = 8):
        """Crea una figura con fondo institucional."""
        fig = plt.figure(figsize=(ancho, alto))
        fig.patch.set_facecolor(COLORES["fondo"])
        return fig


class GraficoDistribucionIngresos(EstiloBase):
    """Barras apiladas H+M por rango SMMLV con curva acumulada.

    Módulo M1 visual.
    """

    def graficar(
        self,
        dist: pd.DataFrame,
        dist_sexo: pd.DataFrame,
        titulo: str = "Distribución de ingresos laborales",
        smmlv: int = SMMLV_2025,
    ) -> plt.Figure:
        """Genera el gráfico de distribución de ingresos.

        Args:
            dist: DataFrame con RANGO, Personas_M, Pct, Acum_Pct.
            dist_sexo: DataFrame con RANGO, H_M, M_M.

        Returns:
            Figura matplotlib lista para .show() o .savefig().
        """
        fig, (ax1, ax2) = plt.subplots(
            1,
            2,
            figsize=(18, 7),
            gridspec_kw={"width_ratios": [1.8, 1]},
        )
        fig.patch.set_facecolor(self.FONDO)

        labels = [str(r) for r in dist["RANGO"]]
        x = np.arange(len(labels))
        w = 0.65

        # Panel izquierdo: barras apiladas
        self.configurar_ejes(ax1, titulo=titulo, ylabel="Millones de personas")
        h_vals = dist_sexo["H_M"].values
        m_vals = dist_sexo["M_M"].values
        tot = h_vals + m_vals

        ax1.bar(x, h_vals, w, label="Hombres", color=self.C["azul"], alpha=0.88, zorder=3)
        ax1.bar(
            x, m_vals, w, bottom=h_vals, label="Mujeres", color=self.C["rojo"], alpha=0.88, zorder=3
        )

        for i, (t, pct) in enumerate(zip(tot, dist["Pct"])):
            ax1.text(
                i,
                t + 0.03,
                f"{t:.2f}M\n{pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

        ax1.axvline(x=1.5, color=self.C["verde"], ls="--", lw=1.8, alpha=0.75)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=9, rotation=20, ha="right")
        ax1.legend(fontsize=10)

        # Panel derecho: curva acumulada
        self.configurar_ejes(ax2, titulo="Distribución acumulada", ylabel="% acumulado")
        ax2.plot(
            x, dist["Acum_Pct"], color=self.C["morado"], lw=2.5, marker="o", markersize=6, zorder=3
        )
        ax2.axhline(50, color=self.C["gris"], ls="--", lw=1, alpha=0.6)
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, fontsize=8, rotation=25, ha="right")
        ax2.set_ylim(0, 105)

        fig.tight_layout(pad=2.5)
        return fig


class GraficoBoxPlotSalarios(EstiloBase):
    """Box plot ponderado de salarios por rama de actividad.

    Cada "caja" se construye a partir de percentiles ponderados,
    no del método estándar de matplotlib (que ignora pesos).
    """

    def graficar(
        self,
        tabla: pd.DataFrame,
        titulo: str = "Distribución del ingreso laboral por rama",
        smmlv: int = SMMLV_2025,
        max_smmlv_eje: int = 8,
    ) -> plt.Figure:
        """Genera box plot con IQR, bigotes P10-P90, mediana y media.

        Args:
            tabla: DataFrame indexado por Rama con P10, P25, Mediana, P75, P90.
            smmlv: SMMLV para referencias verticales.
            max_smmlv_eje: Límite del eje X en múltiplos de SMMLV.

        Returns:
            Figura matplotlib.
        """
        ramas_orden = tabla.sort_values("Mediana").index.tolist()
        n = len(ramas_orden)
        limite = max_smmlv_eje * smmlv

        fig, ax = plt.subplots(figsize=(14, max(7, n * 0.7)))
        fig.patch.set_facecolor(self.FONDO)
        self.configurar_ejes(ax, titulo=titulo, xlabel="Ingreso laboral mensual (COP)")

        y_pos = np.arange(n)

        for i, rama in enumerate(ramas_orden):
            row = tabla.loc[rama]
            p10, p25 = min(row["P10"], limite), min(row["P25"], limite)
            med, mea = min(row["Mediana"], limite), min(row["Media"], limite)
            p75, p90 = min(row["P75"], limite), min(row["P90"], limite)

            # Bigotes P10–P90
            ax.plot([p10, p90], [i, i], color=self.C["gris"], lw=1.4, zorder=2)

            # Caja IQR
            rect = plt.Rectangle(
                (p25, i - 0.28),
                p75 - p25,
                0.56,
                facecolor=self.C["azul"],
                alpha=0.22,
                edgecolor=self.C["azul"],
                linewidth=1.6,
                zorder=3,
            )
            ax.add_patch(rect)

            # Mediana
            ax.plot([med, med], [i - 0.28, i + 0.28], color=self.C["azul"], lw=2.8, zorder=5)

            # Media (diamante)
            ax.scatter(
                mea,
                i,
                marker="D",
                s=38,
                color=self.C["rojo"],
                zorder=6,
                edgecolors="white",
                linewidth=0.8,
            )

            # Etiqueta
            ax.text(
                p90 + smmlv * 0.05,
                i,
                f'{row["Mediana_SMMLV"]:.1f}× | CV:{row["CV_%"]:.0f}%',
                va="center",
                fontsize=7.8,
                color=self.C["negro"],
            )

        # Líneas de referencia SMMLV
        for mult, alpha in [(1, 0.55), (2, 0.35), (3, 0.25), (4, 0.18)]:
            ax.axvline(mult * smmlv, color=self.C["verde"], ls="--", lw=1, alpha=alpha)
            ax.text(
                mult * smmlv,
                n - 0.3,
                f"{mult} SML",
                ha="center",
                fontsize=8,
                color=self.C["verde"],
                alpha=0.8,
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(ramas_orden, fontsize=9.5)
        ax.set_xlim(left=0, right=limite * 1.18)
        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"${v/1e6:.1f}M" if v >= 1e6 else f"${v/1e3:.0f}k")
        )

        # Leyenda
        leyenda = [
            mpatches.Patch(
                facecolor=self.C["azul"],
                alpha=0.22,
                edgecolor=self.C["azul"],
                label="Caja IQR (P25–P75)",
            ),
            plt.Line2D([0], [0], color=self.C["azul"], lw=2.8, label="Mediana (P50)"),
            plt.Line2D(
                [0],
                [0],
                marker="D",
                color="w",
                markerfacecolor=self.C["rojo"],
                markersize=8,
                label="Media ponderada",
            ),
            plt.Line2D([0], [0], color=self.C["gris"], lw=1.4, label="Bigotes P10–P90"),
        ]
        ax.legend(handles=leyenda, loc="lower right", fontsize=9, framealpha=0.92)
        fig.tight_layout(pad=2.5)
        return fig


class GraficoBrechaGenero(EstiloBase):
    """Gráfico de brecha salarial de género por nivel educativo."""

    def graficar(
        self,
        pivot_edu: pd.DataFrame,
        titulo: str = "Brecha salarial de género por nivel educativo",
        smmlv: int = SMMLV_2025,
    ) -> plt.Figure:
        """Barras dobles H/M con línea de brecha %.

        Args:
            pivot_edu: DataFrame con columnas Hombres, Mujeres, Brecha_%.

        Returns:
            Figura matplotlib.
        """
        niveles = pivot_edu.index.tolist()
        x = np.arange(len(niveles))
        w = 0.35

        fig, ax1 = plt.subplots(figsize=(14, 7))
        fig.patch.set_facecolor(self.FONDO)
        self.configurar_ejes(ax1, titulo=titulo)

        h_vals = (pivot_edu["Hombres"] / smmlv).values
        m_vals = (pivot_edu["Mujeres"] / smmlv).values

        ax1.bar(x - w / 2, h_vals, w, color=self.C["azul"], alpha=0.85, label="Hombres")
        ax1.bar(x + w / 2, m_vals, w, color=self.C["rojo"], alpha=0.85, label="Mujeres")

        ax1.set_xticks(x)
        ax1.set_xticklabels(niveles, fontsize=9, rotation=15, ha="right")
        ax1.set_ylabel("Mediana de ingreso (× SMMLV)", fontsize=11)
        ax1.legend(fontsize=10)

        # Eje secundario: brecha %
        if "Brecha_%" in pivot_edu.columns:
            ax2 = ax1.twinx()
            ax2.plot(
                x,
                pivot_edu["Brecha_%"],
                color=self.C["morado"],
                lw=2.5,
                marker="s",
                markersize=7,
                label="Brecha %",
            )
            ax2.axhline(0, color=self.C["gris"], ls="--", lw=0.8, alpha=0.5)
            ax2.set_ylabel("Brecha % (M − H) / H", fontsize=11, color=self.C["morado"])
            ax2.legend(fontsize=9, loc="upper left")

        fig.tight_layout(pad=2.5)
        return fig


class GraficoRamaSexo(EstiloBase):
    """Barras horizontales de ocupados por rama, desagregado por sexo."""

    def graficar(
        self,
        pivot: pd.DataFrame,
        titulo: str = "Ocupados por rama de actividad y sexo",
    ) -> plt.Figure:
        """Genera gráfico de barras horizontales apiladas H+M.

        Args:
            pivot: DataFrame con RAMA, Hombres_miles, Mujeres_miles.

        Returns:
            Figura matplotlib.
        """
        pivot = pivot.sort_values("Total_miles", ascending=True)
        n = len(pivot)

        fig, ax = plt.subplots(figsize=(14, max(7, n * 0.6)))
        fig.patch.set_facecolor(self.FONDO)
        self.configurar_ejes(ax, titulo=titulo, xlabel="Miles de personas")

        y = np.arange(n)
        h = pivot["Hombres_miles"].values
        m = pivot["Mujeres_miles"].values

        ax.barh(y, h, 0.65, color=self.C["azul"], alpha=0.85, label="Hombres")
        ax.barh(y, m, 0.65, left=h, color=self.C["rojo"], alpha=0.85, label="Mujeres")

        for i, (hv, mv) in enumerate(zip(h, m)):
            ax.text(hv + mv + 20, i, f"{hv+mv:,.0f}K", va="center", fontsize=8)

        ax.set_yticks(y)
        ax.set_yticklabels(pivot["RAMA"], fontsize=9)
        ax.legend(fontsize=10, loc="lower right")
        fig.tight_layout(pad=2.5)
        return fig


# ═════════════════════════════════════════════════════════════════════
# NUEVOS EN v4.0: 4 GRÁFICOS ADICIONALES
# ═════════════════════════════════════════════════════════════════════


class GraficoCurvaLorenz(EstiloBase):
    """Curva de Lorenz del ingreso laboral con shading de desigualdad.

    Dibuja la curva nacional + comparativos (sexo, zona) con el
    coeficiente de Gini en la leyenda. El área sombreada entre
    la línea de igualdad perfecta y la curva real representa
    visualmente la desigualdad.

    Módulo M5 visual — complementa IndicesCompuestos.gini().
    """

    def graficar(
        self,
        df: pd.DataFrame,
        col_val: str = "INGLABO",
        col_peso: str = "FEX_ADJ",
        titulo: str = "Curva de Lorenz del ingreso laboral",
    ) -> plt.Figure:
        """Genera curva de Lorenz con comparativos por sexo y zona.

        Args:
            df: DataFrame de ocupados con INGLABO > 0 y FEX_ADJ.
            col_val: Columna de ingresos.
            col_peso: Columna de pesos.

        Returns:
            Figura matplotlib.
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor(self.FONDO)
        ax.set_facecolor("white")

        # Línea de perfecta igualdad
        ax.plot([0, 1], [0, 1], "k--", lw=1.5, alpha=0.7, label="Perfecta igualdad")

        # Configuraciones: (subset, color, label)
        configs = [(df, self.C["azul"], "Nacional")]
        if "ZONA" in df.columns:
            configs.append((df[df["ZONA"] == "Urbano"], self.C["verde"], "Urbano"))
            configs.append((df[df["ZONA"] == "Rural"], self.C["naranja"], "Rural"))
        if "P3271" in df.columns:
            configs.append((df[df["P3271"] == 1], "#1A5276", "Hombres"))
            configs.append((df[df["P3271"] == 2], "#922B21", "Mujeres"))

        _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

        for sub, color, lbl in configs:
            m = sub[col_val].notna() & (sub[col_val] > 0) & sub[col_peso].notna()
            v = sub.loc[m, col_val].values
            w = sub.loc[m, col_peso].values
            if len(v) < 10:
                continue
            idx = np.argsort(v)
            v, w = v[idx], w[idx]
            w_cum = np.cumsum(w) / w.sum()
            vw_cum = np.cumsum(v * w) / (v * w).sum()
            # Insertar origen (0,0)
            w_c = np.insert(w_cum, 0, 0)
            vw_c = np.insert(vw_cum, 0, 0)
            gini = 1.0 - 2.0 * _trapz(vw_c, w_c) if _trapz else np.nan
            ax.plot(w_c, vw_c, lw=2.2, color=color, label=f"{lbl} (Gini={gini:.3f})")
            if lbl == "Nacional":
                ax.fill_between(w_c, w_c, vw_c, alpha=0.08, color=color)

        ax.set_xlabel("Proporción acumulada de ocupados", fontsize=11)
        ax.set_ylabel("Proporción acumulada del ingreso", fontsize=11)
        ax.set_title(titulo, fontsize=12, fontweight="bold")
        ax.legend(fontsize=10, framealpha=0.95)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(pad=2.5)
        return fig


class GraficoICIBubble(EstiloBase):
    """Gráfico de burbujas del ICI — Competitividad laboral por departamento.

    Eje X = Costo laboral efectivo (mediana × 1.54)
    Eje Y = Talento (% universitarios)
    Tamaño burbuja = Oferta disponible (desocupados + subempleados)

    Cuadrantes:
      Alto talento + Bajo costo → ideal para IED manufactura/servicios
      Alto talento + Alto costo → operaciones de alto valor agregado
    """

    def graficar(
        self,
        ici: pd.DataFrame,
        col_x: str = "Costo_efectivo",
        col_y: str = "Talento_univ_%",
        col_size: str = "Oferta_miles",
        titulo: str = "Competitividad laboral por departamento",
    ) -> plt.Figure:
        """Genera gráfico de burbujas del ICI.

        Args:
            ici: DataFrame del resultado de CompetitividadLaboral().calcular().
                 Requiere columnas: Departamento, Costo_efectivo, Talento_univ_%,
                 Oferta_miles (o similar), ICI.

        Returns:
            Figura matplotlib.
        """
        fig, ax = plt.subplots(figsize=(14, 9))
        fig.patch.set_facecolor(self.FONDO)
        ax.set_facecolor("white")

        if col_size in ici.columns:
            sizes = ici[col_size].fillna(1)
            sizes = (sizes / sizes.max() * 800).clip(lower=30)
        else:
            sizes = 150

        # Color por ICI
        ici_vals = ici["ICI"] if "ICI" in ici.columns else pd.Series(50, index=ici.index)
        colors = [
            self.C["verde"] if v > 55 else (self.C["naranja"] if v > 45 else self.C["rojo"])
            for v in ici_vals
        ]

        ax.scatter(
            ici[col_x],
            ici[col_y],
            s=sizes,
            c=colors,
            alpha=0.72,
            edgecolors="white",
            linewidth=1.2,
            zorder=3,
        )

        # Etiquetas de departamento
        for _, row in ici.iterrows():
            ax.annotate(
                row.get("Departamento", "")[:12],
                (row[col_x], row[col_y]),
                fontsize=7.5,
                ha="center",
                va="bottom",
                textcoords="offset points",
                xytext=(0, 6),
            )

        # Líneas de referencia (medianas)
        med_x = ici[col_x].median()
        med_y = ici[col_y].median()
        ax.axvline(med_x, color=self.C["gris"], ls="--", lw=1, alpha=0.5)
        ax.axhline(med_y, color=self.C["gris"], ls="--", lw=1, alpha=0.5)

        # Etiquetas de cuadrantes
        ax.text(
            ici[col_x].min(),
            ici[col_y].max(),
            " ★ Alto talento\n    Bajo costo",
            fontsize=9,
            color=self.C["verde"],
            fontweight="bold",
            va="top",
            ha="left",
        )
        ax.text(
            ici[col_x].max(),
            ici[col_y].max(),
            "Alto talento\nAlto costo ",
            fontsize=9,
            color=self.C["naranja"],
            fontweight="bold",
            va="top",
            ha="right",
        )

        ax.set_xlabel("Costo laboral efectivo (COP)", fontsize=11)
        ax.set_ylabel("% universitarios (proxy talento)", fontsize=11)
        ax.set_title(titulo, fontsize=12, fontweight="bold")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1e6:.1f}M"))
        ax.grid(alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(pad=2.5)
        return fig


class GraficoEstacionalidad(EstiloBase):
    """Líneas mensuales TD/TGP/TO con eje dual.

    Eje izquierdo: TD (%) — la serie más volátil
    Eje derecho: TGP y TO (%) — rango mayor pero más estables
    """

    def graficar(
        self,
        estac: pd.DataFrame,
        titulo: str = "Estacionalidad del mercado laboral",
    ) -> plt.Figure:
        """Genera gráfico de líneas mensuales.

        Args:
            estac: DataFrame con MES (o MES_NUM), TD_%, TGP_%, TO_%.
                   Output de Estacionalidad().calcular().

        Returns:
            Figura matplotlib.
        """
        fig, ax1 = plt.subplots(figsize=(14, 6))
        fig.patch.set_facecolor(self.FONDO)
        ax1.set_facecolor("white")

        # Determinar eje X
        col_mes = "MES" if "MES" in estac.columns else "MES_NUM"
        x = estac[col_mes].values
        x_pos = np.arange(len(x))

        # Eje izquierdo: TD
        color_td = self.C["rojo"]
        ax1.plot(
            x_pos,
            estac["TD_%"],
            color=color_td,
            lw=2.5,
            marker="o",
            markersize=7,
            label="TD %",
            zorder=3,
        )
        ax1.set_ylabel("Tasa de Desempleo (%)", fontsize=11, color=color_td)
        ax1.tick_params(axis="y", labelcolor=color_td)

        # Anotar valores TD
        for i, v in enumerate(estac["TD_%"]):
            ax1.text(
                i, v + 0.15, f"{v:.1f}", ha="center", fontsize=8, color=color_td, fontweight="bold"
            )

        # Eje derecho: TGP y TO
        ax2 = ax1.twinx()
        ax2.plot(
            x_pos,
            estac["TGP_%"],
            color=self.C["azul"],
            lw=2,
            marker="s",
            markersize=5,
            label="TGP %",
            zorder=2,
        )
        ax2.plot(
            x_pos,
            estac["TO_%"],
            color=self.C["verde"],
            lw=2,
            marker="^",
            markersize=5,
            label="TO %",
            zorder=2,
        )
        ax2.set_ylabel("TGP y TO (%)", fontsize=11)

        # Eje X
        ax1.set_xticks(x_pos)
        if col_mes == "MES":
            labels = [str(m)[:3] for m in x]
        else:
            from .config import MESES_NOMBRES

            labels = [MESES_NOMBRES[int(m) - 1][:3] if 1 <= m <= 12 else str(m) for m in x]
        ax1.set_xticklabels(labels, fontsize=10)

        ax1.set_title(titulo, fontsize=12, fontweight="bold")
        ax1.grid(axis="y", alpha=0.2)
        ax1.spines[["top"]].set_visible(False)
        ax2.spines[["top"]].set_visible(False)

        # Leyenda combinada
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(
            lines1 + lines2, labels1 + labels2, fontsize=10, loc="upper left", framealpha=0.92
        )

        fig.tight_layout(pad=2.5)
        return fig


class GraficoContribucionHeatmap(EstiloBase):
    """Heatmap de contribución sectorial al empleo (p.p.) por rama × mes.

    14 ramas CIIU en el eje Y, 12 meses en el eje X.
    El color indica contribución positiva (verde) o negativa (rojo).
    """

    def graficar(
        self,
        contrib: pd.DataFrame,
        col_rama: str = "Rama",
        col_mes: str = "MES_NUM",
        col_valor: str = "Contribucion_pp",
        titulo: str = "Contribución sectorial al empleo (p.p.)",
    ) -> plt.Figure:
        """Genera heatmap de contribución sectorial.

        Args:
            contrib: DataFrame con Rama, MES_NUM, Contribucion_pp.
                     Output de ContribucionSectorial().calcular().
                     Puede ser long format o wide format.

        Returns:
            Figura matplotlib.
        """
        # Si es long format, pivotar
        if col_valor in contrib.columns and col_rama in contrib.columns:
            pivot = contrib.pivot_table(
                index=col_rama, columns=col_mes, values=col_valor, aggfunc="sum"
            )
        else:
            # Asumir que ya está en formato wide (ramas como filas, meses como cols)
            pivot = contrib.copy()

        if pivot.empty:
            print("⚠️  No hay datos para generar el heatmap.")
            return plt.figure()

        fig, ax = plt.subplots(figsize=(16, max(8, len(pivot) * 0.55)))
        fig.patch.set_facecolor(self.FONDO)
        ax.set_facecolor("white")

        # Calcular límite simétrico para colores
        vmax = max(abs(pivot.values.min()), abs(pivot.values.max()), 0.5)

        import matplotlib.colors as mcolors

        cmap = mcolors.LinearSegmentedColormap.from_list(
            "contrib", [self.C["rojo"], "white", self.C["verde"]]
        )

        im = ax.imshow(pivot.values, cmap=cmap, aspect="auto", vmin=-vmax, vmax=vmax)

        # Etiquetas
        ax.set_xticks(np.arange(pivot.shape[1]))
        if hasattr(pivot.columns, "tolist"):
            from .config import MESES_NOMBRES

            cols = pivot.columns.tolist()
            x_labels = []
            for c in cols:
                try:
                    idx = int(c) - 1
                    x_labels.append(MESES_NOMBRES[idx][:3] if 0 <= idx < 12 else str(c))
                except (ValueError, IndexError):
                    x_labels.append(str(c)[:6])
            ax.set_xticklabels(x_labels, fontsize=9)
        ax.set_yticks(np.arange(pivot.shape[0]))
        ax.set_yticklabels([str(r)[:45] for r in pivot.index], fontsize=9)

        # Valores en las celdas
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    color = "white" if abs(val) > vmax * 0.6 else "black"
                    ax.text(
                        j,
                        i,
                        f"{val:+.2f}",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color=color,
                        fontweight="bold",
                    )

        ax.set_title(titulo, fontsize=12, fontweight="bold", pad=12)
        fig.colorbar(im, ax=ax, label="Contribución (p.p.)", shrink=0.8)
        fig.tight_layout(pad=2.5)
        return fig
