"""
geih.visualizacion_interactiva — Gráficos interactivos con Plotly.

Versiones interactivas de los gráficos matplotlib con:
  - Tooltips detallados en hover
  - Zoom, pan, selección
  - Filtros dinámicos
  - Exportación PNG/SVG desde el navegador

Requiere: pip install plotly
Si plotly no está disponible, los imports fallan con mensaje claro.

Cada clase replica un gráfico de visualizacion.py pero con interactividad.
Los métodos retornan objetos plotly.graph_objects.Figure que se pueden
mostrar con .show() en Colab/Jupyter o guardar con .write_html().

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "PlotlyLorenz",
    "PlotlyICIBubble",
    "PlotlyEstacionalidad",
    "PlotlyDistribucionIngresos",
    "PlotlyBrechaGenero",
    "PlotlyBoxPlotSalarios",
    "PlotlySalarioRama",
    "PlotlyComparativoAnual",
]


import numpy as np
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    _PLOTLY_DISPONIBLE = True
except ImportError:
    _PLOTLY_DISPONIBLE = False


def _verificar_plotly():
    """Verifica que plotly esté instalado."""
    if not _PLOTLY_DISPONIBLE:
        raise ImportError(
            "plotly no está instalado. Instale con:\n"
            "  !pip install plotly\n"
            "O use los gráficos de visualizacion.py (matplotlib, sin interactividad)."
        )


# Paleta de colores institucional
_C = {
    "azul": "#2E6DA4",
    "rojo": "#C0392B",
    "verde": "#1E8449",
    "morado": "#7D3C98",
    "naranja": "#E67E22",
    "gris": "#7F8C8D",
    "cyan": "#1ABC9C",
    "amarillo": "#F39C12",
    "fondo": "#F7F9FC",
}

_LAYOUT_BASE = dict(
    template="plotly_white",
    paper_bgcolor=_C["fondo"],
    font=dict(family="Arial", size=13),
    margin=dict(l=60, r=40, t=80, b=60),
)


# ═════════════════════════════════════════════════════════════════════
# CURVA DE LORENZ INTERACTIVA
# ═════════════════════════════════════════════════════════════════════


class PlotlyLorenz:
    """Curva de Lorenz interactiva con hover que muestra % población y % ingreso."""

    def graficar(
        self,
        df: pd.DataFrame,
        col_val: str = "INGLABO",
        col_peso: str = "FEX_ADJ",
        titulo: str = "Curva de Lorenz del ingreso laboral",
    ) -> "go.Figure":
        _verificar_plotly()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode="lines",
                line=dict(dash="dash", color="gray", width=1.5),
                name="Igualdad perfecta",
                hoverinfo="skip",
            )
        )

        _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

        configs = [
            (df, _C["azul"], "Nacional"),
        ]
        if "ZONA" in df.columns:
            configs.append((df[df["ZONA"] == "Urbano"], _C["verde"], "Urbano"))
            configs.append((df[df["ZONA"] == "Rural"], _C["naranja"], "Rural"))
        if "P3271" in df.columns:
            configs.append((df[df["P3271"] == 1], "#1A5276", "Hombres"))
            configs.append((df[df["P3271"] == 2], "#922B21", "Mujeres"))

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
            w_c = np.insert(w_cum, 0, 0)
            vw_c = np.insert(vw_cum, 0, 0)
            gini = 1.0 - 2.0 * _trapz(vw_c, w_c) if _trapz else np.nan

            # Reducir puntos para rendimiento (max 200)
            step = max(1, len(w_c) // 200)
            w_s, vw_s = w_c[::step], vw_c[::step]

            fig.add_trace(
                go.Scatter(
                    x=w_s,
                    y=vw_s,
                    mode="lines",
                    line=dict(color=color, width=2.5),
                    name=f"{lbl} (Gini={gini:.3f})",
                    hovertemplate=(
                        f"<b>{lbl}</b><br>"
                        "Población acumulada: %{x:.1%}<br>"
                        "Ingreso acumulado: %{y:.1%}<br>"
                        "<extra></extra>"
                    ),
                )
            )
            if lbl == "Nacional":
                fig.add_trace(
                    go.Scatter(
                        x=np.concatenate([w_s, w_s[::-1]]),
                        y=np.concatenate([w_s, vw_s[::-1]]),
                        fill="toself",
                        fillcolor="rgba(46,109,164,0.08)",
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(title="% acumulado de ocupados", tickformat=".0%", range=[0, 1]),
            yaxis=dict(title="% acumulado del ingreso", tickformat=".0%", range=[0, 1]),
            legend=dict(x=0.05, y=0.95),
            width=700,
            height=600,
        )
        return fig


# ═════════════════════════════════════════════════════════════════════
# ICI BUBBLE INTERACTIVO
# ═════════════════════════════════════════════════════════════════════


class PlotlyICIBubble:
    """Gráfico de burbujas ICI con hover que muestra todos los indicadores."""

    def graficar(
        self,
        ici: pd.DataFrame,
        col_x: str = "Costo_efectivo",
        col_y: str = "Talento_univ_%",
        col_size: str = "Oferta_miles",
        titulo: str = "Competitividad laboral (ICI) por departamento",
    ) -> "go.Figure":
        _verificar_plotly()

        df = ici.copy()
        size_col = col_size if col_size in df.columns else None
        sizes = df[size_col].fillna(1) if size_col else pd.Series(20, index=df.index)
        sizes = (sizes / sizes.max() * 60).clip(lower=8)

        colors = df["ICI"] if "ICI" in df.columns else pd.Series(50, index=df.index)

        fig = px.scatter(
            df,
            x=col_x,
            y=col_y,
            size=sizes.values,
            color=colors.values,
            hover_name="Departamento",
            hover_data={
                col_x: ":,.0f",
                col_y: ":.1f",
                "ICI": ":.1f" if "ICI" in df.columns else False,
            },
            color_continuous_scale="RdYlGn",
            text="Departamento",
        )
        fig.update_traces(
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(line=dict(width=1, color="white")),
        )

        # Líneas de referencia (medianas)
        med_x = df[col_x].median()
        med_y = df[col_y].median()
        fig.add_vline(x=med_x, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=med_y, line_dash="dash", line_color="gray", opacity=0.5)

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(title="Costo laboral efectivo (COP)"),
            yaxis=dict(title="% universitarios"),
            coloraxis_colorbar=dict(title="ICI"),
            width=900,
            height=700,
        )
        return fig


# ═════════════════════════════════════════════════════════════════════
# ESTACIONALIDAD INTERACTIVA
# ═════════════════════════════════════════════════════════════════════


class PlotlyEstacionalidad:
    """Líneas mensuales TD/TGP/TO con hover detallado."""

    def graficar(
        self,
        estac: pd.DataFrame,
        titulo: str = "Estacionalidad del mercado laboral",
    ) -> "go.Figure":
        _verificar_plotly()

        from .config import MESES_NOMBRES

        col_mes = "MES" if "MES" in estac.columns else "MES_NUM"
        meses_labels = []
        for m in estac[col_mes]:
            try:
                meses_labels.append(MESES_NOMBRES[int(m) - 1][:3])
            except (ValueError, IndexError):
                meses_labels.append(str(m))

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=estac["TD_%"],
                mode="lines+markers",
                name="TD %",
                line=dict(color=_C["rojo"], width=3),
                marker=dict(size=10),
                hovertemplate="<b>%{x}</b><br>TD: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=estac["TGP_%"],
                mode="lines+markers",
                name="TGP %",
                line=dict(color=_C["azul"], width=2),
                marker=dict(size=7, symbol="square"),
                hovertemplate="<b>%{x}</b><br>TGP: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=estac["TO_%"],
                mode="lines+markers",
                name="TO %",
                line=dict(color=_C["verde"], width=2),
                marker=dict(size=7, symbol="triangle-up"),
                hovertemplate="<b>%{x}</b><br>TO: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            legend=dict(x=0.01, y=0.99),
            width=900,
            height=500,
        )
        fig.update_yaxes(
            title_text="Tasa de Desempleo (%)", secondary_y=False, titlefont=dict(color=_C["rojo"])
        )
        fig.update_yaxes(title_text="TGP y TO (%)", secondary_y=True)

        return fig


# ═════════════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE INGRESOS INTERACTIVA
# ═════════════════════════════════════════════════════════════════════


class PlotlyDistribucionIngresos:
    """Barras apiladas H/M por rango SMMLV con hover detallado."""

    def graficar(
        self,
        dist_sexo: pd.DataFrame,
        titulo: str = "Distribución de ingresos por sexo",
    ) -> "go.Figure":
        _verificar_plotly()

        fig = go.Figure()
        if "H_M" in dist_sexo.columns and "M_M" in dist_sexo.columns:
            rangos = dist_sexo["RANGO"].astype(str).tolist()
            fig.add_trace(
                go.Bar(
                    x=rangos,
                    y=dist_sexo["H_M"],
                    name="Hombres",
                    marker_color=_C["azul"],
                    hovertemplate="<b>%{x}</b><br>Hombres: %{y:.2f}M<extra></extra>",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=rangos,
                    y=dist_sexo["M_M"],
                    name="Mujeres",
                    marker_color=_C["rojo"],
                    hovertemplate="<b>%{x}</b><br>Mujeres: %{y:.2f}M<extra></extra>",
                )
            )
            fig.update_layout(barmode="stack")

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(title="Rango SMMLV"),
            yaxis=dict(title="Millones de personas"),
            width=800,
            height=500,
        )
        return fig


# ═════════════════════════════════════════════════════════════════════
# BRECHA DE GÉNERO INTERACTIVA
# ═════════════════════════════════════════════════════════════════════


class PlotlyBrechaGenero:
    """Barras dobles H/M con línea de brecha % en hover."""

    def graficar(
        self,
        pivot_edu: pd.DataFrame,
        smmlv: int = 1_423_500,
        titulo: str = "Brecha salarial de género por educación",
    ) -> "go.Figure":
        _verificar_plotly()

        niveles = pivot_edu.index.tolist()
        h_vals = (pivot_edu["Hombres"] / smmlv).values
        m_vals = (pivot_edu["Mujeres"] / smmlv).values
        brecha = pivot_edu.get("Brecha_%", pd.Series(dtype=float)).values

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(
                x=niveles,
                y=h_vals,
                name="Hombres",
                marker_color=_C["azul"],
                opacity=0.85,
                hovertemplate="<b>%{x}</b><br>Hombres: %{y:.2f}× SMMLV<extra></extra>",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Bar(
                x=niveles,
                y=m_vals,
                name="Mujeres",
                marker_color=_C["rojo"],
                opacity=0.85,
                hovertemplate="<b>%{x}</b><br>Mujeres: %{y:.2f}× SMMLV<extra></extra>",
            ),
            secondary_y=False,
        )

        if len(brecha) > 0 and not np.all(np.isnan(brecha)):
            fig.add_trace(
                go.Scatter(
                    x=niveles,
                    y=brecha,
                    mode="lines+markers",
                    name="Brecha %",
                    line=dict(color=_C["morado"], width=2.5),
                    marker=dict(size=8, symbol="square"),
                    hovertemplate="<b>%{x}</b><br>Brecha: %{y:+.1f}%<extra></extra>",
                ),
                secondary_y=True,
            )

        fig.update_layout(
            **_LAYOUT_BASE,
            barmode="group",
            title=dict(text=titulo, font=dict(size=16)),
            width=900,
            height=550,
        )
        fig.update_yaxes(title_text="Mediana (× SMMLV)", secondary_y=False)
        fig.update_yaxes(
            title_text="Brecha % (M−H)/H", secondary_y=True, titlefont=dict(color=_C["morado"])
        )
        return fig


# ═════════════════════════════════════════════════════════════════════
# BOX PLOT SALARIOS INTERACTIVO
# ═════════════════════════════════════════════════════════════════════


class PlotlyBoxPlotSalarios:
    """Box plot interactivo de salarios por rama (muestra ponderada)."""

    def graficar(
        self,
        df: pd.DataFrame,
        smmlv: int = 1_423_500,
        muestra: int = 30_000,
        titulo: str = "Distribución del ingreso por rama",
    ) -> "go.Figure":
        _verificar_plotly()

        df_ocu = df[(df["OCI"] == 1) & (df["INGLABO"] > 0) & df["RAMA"].notna()].copy()
        df_ocu["INGLABO_SML"] = df_ocu["INGLABO"] / smmlv

        if len(df_ocu) > muestra:
            df_s = df_ocu.sample(muestra, weights="FEX_ADJ", random_state=42, replace=True)
        else:
            df_s = df_ocu

        fig = px.box(
            df_s,
            x="INGLABO_SML",
            y="RAMA",
            color="RAMA",
            orientation="h",
            points=False,
            labels={"INGLABO_SML": "Ingreso (× SMMLV)", "RAMA": ""},
        )
        fig.add_vline(x=1, line_dash="dash", line_color=_C["verde"], annotation_text="1 SMMLV")
        fig.add_vline(x=2, line_dash="dot", line_color=_C["naranja"], annotation_text="2 SMMLV")

        fig.update_layout(
            **_LAYOUT_BASE,
            showlegend=False,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(range=[0, 10]),
            height=max(500, len(df_s["RAMA"].unique()) * 45),
            width=900,
        )
        return fig


# ═════════════════════════════════════════════════════════════════════
# SALARIO POR RAMA (BARRAS HORIZONTALES)
# ═════════════════════════════════════════════════════════════════════


class PlotlySalarioRama:
    """Barras horizontales de mediana salarial por rama con tooltip completo."""

    def graficar(
        self,
        tabla: pd.DataFrame,
        smmlv: int = 1_423_500,
        titulo: str = "Mediana salarial por rama de actividad",
    ) -> "go.Figure":
        _verificar_plotly()

        df = tabla.sort_values("Mediana", ascending=True).copy()

        fig = go.Figure(
            go.Bar(
                y=df.index if df.index.name else df.iloc[:, 0],
                x=df["Mediana"] / smmlv,
                orientation="h",
                marker_color=_C["azul"],
                hovertemplate=("<b>%{y}</b><br>" "Mediana: %{x:.2f}× SMMLV<br>" "<extra></extra>"),
            )
        )

        fig.add_vline(x=1, line_dash="dash", line_color=_C["verde"], annotation_text="1 SMMLV")

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(title="Mediana ingreso (× SMMLV)"),
            height=max(400, len(df) * 35),
            width=800,
        )
        return fig


# ═════════════════════════════════════════════════════════════════════
# COMPARATIVO ANUAL INTERACTIVO
# ═════════════════════════════════════════════════════════════════════


class PlotlyComparativoAnual:
    """Gráficos interactivos para comparación multi-año.

    Diseñado para usarse con ComparadorMultiAnio.

    Uso:
        comp = ComparadorMultiAnio()
        comp.agregar_anio(2025, ..., ...)
        comp.agregar_anio(2026, ..., ...)

        vis = PlotlyComparativoAnual()
        fig = vis.indicadores(comp.comparar_indicadores())
        fig.show()
    """

    def indicadores(
        self,
        df_ind: pd.DataFrame,
        titulo: str = "Evolución de indicadores laborales",
    ) -> "go.Figure":
        """Líneas TD/TGP/TO por año."""
        _verificar_plotly()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        anios = df_ind["ANIO"].astype(str).tolist()

        fig.add_trace(
            go.Scatter(
                x=anios,
                y=df_ind["TD_%"],
                mode="lines+markers+text",
                name="TD %",
                line=dict(color=_C["rojo"], width=3),
                marker=dict(size=12),
                text=[f"{v:.1f}%" for v in df_ind["TD_%"]],
                textposition="top center",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=anios,
                y=df_ind["TGP_%"],
                mode="lines+markers",
                name="TGP %",
                line=dict(color=_C["azul"], width=2),
            ),
            secondary_y=True,
        )

        fig.add_trace(
            go.Scatter(
                x=anios,
                y=df_ind["TO_%"],
                mode="lines+markers",
                name="TO %",
                line=dict(color=_C["verde"], width=2),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(title="Año"),
            width=800,
            height=500,
        )
        fig.update_yaxes(title_text="TD (%)", secondary_y=False)
        fig.update_yaxes(title_text="TGP / TO (%)", secondary_y=True)
        return fig

    def ingresos(
        self,
        df_ing: pd.DataFrame,
        titulo: str = "Evolución de la mediana salarial",
    ) -> "go.Figure":
        """Barras de mediana en SMMLV + línea en COP."""
        _verificar_plotly()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        anios = df_ing["ANIO"].astype(str).tolist()

        fig.add_trace(
            go.Bar(
                x=anios,
                y=df_ing["Mediana_SMMLV"],
                name="Mediana (× SMMLV)",
                marker_color=_C["azul"],
                opacity=0.8,
                text=[f"{v:.2f}×" for v in df_ing["Mediana_SMMLV"]],
                textposition="outside",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=anios,
                y=df_ing["Mediana_COP"] / 1e6,
                mode="lines+markers",
                name="Mediana (M COP)",
                line=dict(color=_C["rojo"], width=2),
                marker=dict(size=8),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            **_LAYOUT_BASE,
            title=dict(text=titulo, font=dict(size=16)),
            xaxis=dict(title="Año"),
            width=800,
            height=500,
        )
        fig.update_yaxes(title_text="× SMMLV", secondary_y=False)
        fig.update_yaxes(title_text="Millones COP", secondary_y=True)
        return fig
