"""
geih.dashboard — Dashboard interactivo Streamlit para exploración de resultados.

Permite a usuarios no-técnicos explorar los resultados de la GEIH
con filtros, gráficos interactivos y tablas descargables, sin
necesidad de escribir código Python.

REQUISITOS:
    pip install streamlit plotly

EJECUCIÓN:
    # Desde la carpeta del paquete:
    streamlit run geih_2025/dashboard.py

    # Desde Google Colab (con tunnel):
    !pip install streamlit plotly
    !streamlit run geih_2025/dashboard.py --server.headless true &
    # Usar el link que genera Streamlit

    # O con localtunnel:
    !npm install -g localtunnel
    !lt --port 8501

DATOS:
    El dashboard busca archivos Parquet consolidados en una ruta
    configurable. También puede cargar CSVs de la carpeta resultados/.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = ["ejecutar_dashboard"]

import sys
from pathlib import Path


def ejecutar_dashboard(
    ruta_base: str = ".",
    puerto: int = 8501,
) -> None:
    """Lanza el dashboard Streamlit programáticamente.

    Args:
        ruta_base: Carpeta con los Parquets y resultados.
        puerto: Puerto del servidor Streamlit.
    """
    import subprocess

    script = str(Path(__file__).resolve())
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            script,
            "--server.port",
            str(puerto),
            "--server.headless",
            "true",
            "--",
            ruta_base,
        ]
    )
    print(f"🌐 Dashboard disponible en http://localhost:{puerto}")


# ═════════════════════════════════════════════════════════════════════
# La siguiente sección se ejecuta SOLO cuando Streamlit carga el archivo.
# No se ejecuta al hacer `from geih.dashboard import ...`
# ═════════════════════════════════════════════════════════════════════


def _main():
    """Punto de entrada del dashboard Streamlit."""
    try:
        import plotly.express as px

        # import plotly.graph_objects as go
        import streamlit as st
    except ImportError:
        print("❌ Instale streamlit y plotly:")
        print("   pip install streamlit plotly")
        return

    from pathlib import Path

    import numpy as np
    import pandas as pd

    # ── Configuración de página ────────────────────────────────
    st.set_page_config(
        page_title="GEIH Dashboard — geih-analisis",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── CSS institucional ──────────────────────────────────────
    st.markdown(
        """
    <style>
    .main-header {
        font-size: 2rem; font-weight: bold; color: #1A3C6E;
        border-bottom: 3px solid #8B1A4A; padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #F7F9FC; border-radius: 8px; padding: 15px;
        border-left: 4px solid #2E6DA4; margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="main-header">📊 GEIH Dashboard</div>', unsafe_allow_html=True)

    # ── Sidebar: configuración ─────────────────────────────────
    st.sidebar.image(
        "https://procolombia.co/sites/default/files/logo_procolombia.png",
        width=200,
        use_container_width=False,
    )
    st.sidebar.title("⚙️ Configuración")

    # Ruta de datos
    ruta_default = sys.argv[-1] if len(sys.argv) > 1 and Path(sys.argv[-1]).exists() else "."
    ruta_base = st.sidebar.text_input("Ruta de datos", value=ruta_default)
    ruta = Path(ruta_base)

    # Buscar Parquets disponibles
    parquets = sorted(ruta.glob("GEIH_*_Consolidado*.parquet"))
    if not parquets:
        parquets = sorted(ruta.glob("*.parquet"))

    if not parquets:
        st.warning("⚠️ No se encontraron archivos Parquet en la ruta especificada.")
        st.info(f"Buscando en: {ruta.resolve()}")
        st.info("Suba un archivo .parquet o ajuste la ruta en el sidebar.")

        # Permitir subir archivo
        uploaded = st.file_uploader("📂 O suba un archivo Parquet", type=["parquet"])
        if uploaded:
            df = pd.read_parquet(uploaded)
            st.success(f"✅ Archivo cargado: {df.shape[0]:,} filas × {df.shape[1]} cols")
        else:
            st.stop()
    else:
        archivo_sel = st.sidebar.selectbox(
            "Archivo Parquet",
            parquets,
            format_func=lambda x: x.name,
        )
        df = _cargar_con_cache(str(archivo_sel))

    # ── Info del dataset ───────────────────────────────────────
    st.sidebar.markdown(f"**Registros:** {df.shape[0]:,}")
    st.sidebar.markdown(f"**Columnas:** {df.shape[1]}")
    if "MES_NUM" in df.columns:
        meses = sorted(df["MES_NUM"].unique())
        st.sidebar.markdown(f"**Meses:** {len(meses)}")

    # ── Tabs principales ───────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📈 Indicadores",
            "💰 Ingresos",
            "🏢 Sectores",
            "🗺️ Departamentos",
            "📋 Explorar datos",
        ]
    )

    # ── Preparar datos básicos ─────────────────────────────────
    col_peso = "FEX_ADJ" if "FEX_ADJ" in df.columns else "FEX_C18"
    tiene_ocu = "OCI" in df.columns
    tiene_ing = "INGLABO" in df.columns

    # ═══ TAB 1: INDICADORES ═══════════════════════════════════
    with tab1:
        st.subheader("Indicadores del Mercado Laboral")

        if all(c in df.columns for c in ["FT", "OCI", "DSI", "PET", col_peso]):
            pet = df.loc[df["PET"] == 1, col_peso].sum()
            pea = df.loc[df["FT"] == 1, col_peso].sum()
            ocu = df.loc[df["OCI"] == 1, col_peso].sum()
            dsi = df.loc[df["DSI"] == 1, col_peso].sum()

            td = dsi / pea * 100 if pea > 0 else 0
            tgp = pea / pet * 100 if pet > 0 else 0
            to = ocu / pet * 100 if pet > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tasa de Desempleo", f"{td:.1f}%")
            c2.metric("TGP", f"{tgp:.1f}%")
            c3.metric("Tasa de Ocupación", f"{to:.1f}%")
            c4.metric("Ocupados", f"{ocu / 1e6:.2f}M")

            # Indicadores por sexo
            if "P3271" in df.columns:
                st.markdown("#### Por sexo")
                sexo_data = []
                for sv, sl in [(1, "Hombres"), (2, "Mujeres")]:
                    m = df["P3271"] == sv
                    pea_s = df.loc[m & (df["FT"] == 1), col_peso].sum()
                    dsi_s = df.loc[m & (df["DSI"] == 1), col_peso].sum()
                    td_s = dsi_s / pea_s * 100 if pea_s > 0 else 0
                    ocu_s = df.loc[m & (df["OCI"] == 1), col_peso].sum()
                    sexo_data.append(
                        {"Sexo": sl, "TD_%": round(td_s, 1), "Ocupados_M": round(ocu_s / 1e6, 2)}
                    )
                st.dataframe(pd.DataFrame(sexo_data), use_container_width=True)

            # Gráfico estacionalidad si hay MES_NUM
            if "MES_NUM" in df.columns:
                st.markdown("#### Estacionalidad mensual")
                estac_rows = []
                for mes in sorted(df["MES_NUM"].unique()):
                    m = df["MES_NUM"] == mes
                    pea_m = df.loc[m & (df["FT"] == 1), "FEX_C18"].sum()
                    dsi_m = df.loc[m & (df["DSI"] == 1), "FEX_C18"].sum()
                    ocu_m = df.loc[m & (df["OCI"] == 1), "FEX_C18"].sum()
                    pet_m = df.loc[m & (df["PET"] == 1), "FEX_C18"].sum()
                    estac_rows.append(
                        {
                            "Mes": int(mes),
                            "TD_%": round(dsi_m / pea_m * 100, 1) if pea_m > 0 else 0,
                            "TGP_%": round(pea_m / pet_m * 100, 1) if pet_m > 0 else 0,
                            "TO_%": round(ocu_m / pet_m * 100, 1) if pet_m > 0 else 0,
                        }
                    )
                df_estac = pd.DataFrame(estac_rows)
                fig_e = px.line(
                    df_estac,
                    x="Mes",
                    y=["TD_%", "TGP_%", "TO_%"],
                    title="Indicadores mensuales",
                    markers=True,
                    color_discrete_map={"TD_%": "#C0392B", "TGP_%": "#2E6DA4", "TO_%": "#1E8449"},
                )
                st.plotly_chart(fig_e, use_container_width=True)
        else:
            st.info("Columnas FT, OCI, DSI, PET no disponibles para indicadores.")

    # ═══ TAB 2: INGRESOS ══════════════════════════════════════
    with tab2:
        st.subheader("Distribución de Ingresos Laborales")
        if tiene_ocu and tiene_ing:
            df_ocu = df[(df["OCI"] == 1) & (df["INGLABO"] > 0)].copy()

            smmlv_input = st.number_input("SMMLV (COP)", value=1_423_500, step=100_000)
            df_ocu["SMMLV_mult"] = df_ocu["INGLABO"] / smmlv_input

            # Histograma
            sample_n = min(50_000, len(df_ocu))
            df_sample = df_ocu.sample(sample_n, weights=col_peso, random_state=42, replace=True)
            if "P3271" in df_sample.columns:
                df_sample["Sexo"] = df_sample["P3271"].map({1: "Hombres", 2: "Mujeres"})
                fig_h = px.histogram(
                    df_sample,
                    x="SMMLV_mult",
                    color="Sexo",
                    nbins=60,
                    barmode="overlay",
                    opacity=0.7,
                    range_x=[0, 10],
                    color_discrete_map={"Hombres": "#2E6DA4", "Mujeres": "#C0392B"},
                    title="Distribución del ingreso (× SMMLV)",
                )
            else:
                fig_h = px.histogram(
                    df_sample,
                    x="SMMLV_mult",
                    nbins=60,
                    range_x=[0, 10],
                    title="Distribución del ingreso (× SMMLV)",
                )
            fig_h.add_vline(x=1, line_dash="dash", line_color="green", annotation_text="1 SMMLV")
            st.plotly_chart(fig_h, use_container_width=True)

            # Estadísticas
            med = (
                np.average(df_ocu["INGLABO"], weights=df_ocu[col_peso])
                if col_peso in df_ocu.columns
                else df_ocu["INGLABO"].mean()
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Media", f"${med:,.0f}")
            c2.metric("Mediana (aprox.)", f"${df_ocu['INGLABO'].median():,.0f}")
            c3.metric("En SMMLV", f"{med / smmlv_input:.2f}×")
        else:
            st.info("Columnas OCI e INGLABO no disponibles.")

    # ═══ TAB 3: SECTORES ══════════════════════════════════════
    with tab3:
        st.subheader("Empleo por Actividad Económica")
        rama_col = "RAMA" if "RAMA" in df.columns else "RAMA2D_R4"
        if tiene_ocu and rama_col in df.columns:
            df_rama = (
                df[df["OCI"] == 1]
                .groupby(rama_col)[col_peso]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
                .rename(columns={rama_col: "Rama", col_peso: "Ocupados"})
            )
            df_rama["Ocupados_M"] = (df_rama["Ocupados"] / 1e6).round(2)
            df_rama = df_rama.head(15)

            fig_r = px.bar(
                df_rama,
                y="Rama",
                x="Ocupados_M",
                orientation="h",
                title="Top 15 ramas por ocupados (M)",
                color="Ocupados_M",
                color_continuous_scale="Blues",
            )
            fig_r.update_layout(yaxis=dict(autorange="reversed"), height=500)
            st.plotly_chart(fig_r, use_container_width=True)

            st.dataframe(df_rama[["Rama", "Ocupados_M"]], use_container_width=True)
        else:
            st.info(f"Columna {rama_col} no disponible.")

    # ═══ TAB 4: DEPARTAMENTOS ═════════════════════════════════
    with tab4:
        st.subheader("Indicadores por Departamento")
        dpto_col = (
            "NOMBRE_DPTO"
            if "NOMBRE_DPTO" in df.columns
            else "DPTO_STR"
            if "DPTO_STR" in df.columns
            else "DPTO"
        )
        if dpto_col in df.columns and all(c in df.columns for c in ["FT", "OCI", "DSI", col_peso]):
            dptos = df[dpto_col].dropna().unique()
            filas_d = []
            for d in dptos:
                m = df[dpto_col] == d
                pea_d = df.loc[m & (df["FT"] == 1), col_peso].sum()
                dsi_d = df.loc[m & (df["DSI"] == 1), col_peso].sum()
                ocu_d = df.loc[m & (df["OCI"] == 1), col_peso].sum()
                if pea_d < 1_000:
                    continue
                filas_d.append(
                    {
                        "Departamento": str(d),
                        "TD_%": round(dsi_d / pea_d * 100, 1),
                        "Ocupados_miles": round(ocu_d / 1_000, 1),
                    }
                )
            df_dpto = pd.DataFrame(filas_d).sort_values("TD_%", ascending=False)

            fig_d = px.bar(
                df_dpto,
                x="TD_%",
                y="Departamento",
                orientation="h",
                title="Tasa de Desempleo por Departamento",
                color="TD_%",
                color_continuous_scale="RdYlGn_r",
            )
            fig_d.update_layout(
                yaxis=dict(autorange="reversed"), height=max(400, len(df_dpto) * 25)
            )
            st.plotly_chart(fig_d, use_container_width=True)

            st.dataframe(df_dpto, use_container_width=True)
        else:
            st.info("Columnas de departamento no disponibles.")

    # ═══ TAB 5: EXPLORAR DATOS ════════════════════════════════
    with tab5:
        st.subheader("Exploración libre de la base")

        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            cols_disponibles = df.columns.tolist()
            cols_sel = st.multiselect(
                "Columnas a mostrar", cols_disponibles, default=cols_disponibles[:10]
            )
        with col2:
            n_filas = st.slider("Filas a mostrar", 10, 1000, 100)

        if cols_sel:
            st.dataframe(df[cols_sel].head(n_filas), use_container_width=True)

        # Descarga
        st.markdown("#### 📥 Descargar datos")
        if st.button("Generar CSV (primeras 10,000 filas)"):
            csv = df.head(10_000).to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Descargar CSV", csv, "geih_muestra.csv", "text/csv")

    # ── Footer ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#7F8C8D; font-size:0.85rem;'>"
        "Autor: Néstor Enrique Forero Herrera · geih_2025 v4.3"
        "</div>",
        unsafe_allow_html=True,
    )


def _cargar_con_cache(ruta: str):
    """Carga Parquet con cache manual (compatible sin Streamlit)."""
    import pandas as pd

    return pd.read_parquet(ruta)


# Solo ejecutar la app Streamlit si se llama directamente
if __name__ == "__main__":
    _main()
