"""Tests para geih.analisis_dpto_rama.OcupadosDptoRama."""
import numpy as np
import pandas as pd
import pytest

from geih.analisis_dpto_rama import OcupadosDptoRama


# ═════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════

@pytest.fixture
def df_sintetico():
    """Mini-consolidado con 3 dptos, 3 ramas, 12 meses, FEX constante."""
    rng = np.random.default_rng(42)
    filas = []
    dptos = ["05", "11", "76"]
    ramas_2d = ["01", "47", "85"]
    ramas_4d = ["0111", "4711", "8510"]

    for mes in range(1, 13):
        for dpto in dptos:
            for r2, r4 in zip(ramas_2d, ramas_4d):
                n_personas = rng.integers(20, 60)
                for _ in range(n_personas):
                    filas.append({
                        "DPTO": dpto,
                        "RAMA2D_R4": r2,
                        "RAMA4D_R4": r4,
                        "FEX_C18": float(rng.integers(800, 2500)),
                        "MES_NUM": mes,
                    })
    return pd.DataFrame(filas)


@pytest.fixture
def analisis():
    return OcupadosDptoRama()


# ═════════════════════════════════════════════════════════════════════
# TESTS DE VALIDACIÓN DE ENTRADA
# ═════════════════════════════════════════════════════════════════════

def test_nivel_invalido_lanza_error(analisis, df_sintetico):
    with pytest.raises(ValueError, match="nivel_ciiu"):
        analisis.calcular(df_sintetico, nivel_ciiu="3d")


def test_columna_faltante_lanza_error(analisis):
    df_malo = pd.DataFrame({"DPTO": ["05"], "FEX_C18": [1000.0]})
    with pytest.raises(KeyError, match="Faltan columnas"):
        analisis.calcular(df_malo, nivel_ciiu="2d")


# ═════════════════════════════════════════════════════════════════════
# TESTS DE CÁLCULO
# ═════════════════════════════════════════════════════════════════════

def test_salida_tiene_columnas_esperadas(analisis, df_sintetico):
    out = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    esperadas = {"DPTO", "ciiu_2d", "ocupados_promedio", "desv_mensual",
                 "meses_con_dato", "n_anual", "ee_aprox", "cv_aprox",
                 "calidad"}
    assert esperadas.issubset(out.columns)


def test_total_nacional_coincide_con_promedio_directo(analisis, df_sintetico):
    """El total de la tabla debe igualar el promedio directo de 12 meses."""
    out = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    total_tabla = out["ocupados_promedio"].sum()
    total_directo = (df_sintetico
                     .groupby("MES_NUM")["FEX_C18"].sum().mean())
    assert abs(total_tabla - total_directo) < 1.0


def test_2d_y_4d_dan_mismo_total(analisis, df_sintetico):
    """Cambiar el nivel no debe alterar el total nacional."""
    t2 = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    t4 = analisis.calcular(df_sintetico, nivel_ciiu="4d", verbose=False)
    assert abs(t2["ocupados_promedio"].sum()
               - t4["ocupados_promedio"].sum()) < 1.0


def test_suma_por_dpto_coincide_entre_niveles(analisis, df_sintetico):
    t2 = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    t4 = analisis.calcular(df_sintetico, nivel_ciiu="4d", verbose=False)
    s2 = t2.groupby("DPTO")["ocupados_promedio"].sum().sort_index()
    s4 = t4.groupby("DPTO")["ocupados_promedio"].sum().sort_index()
    pd.testing.assert_series_equal(s2, s4, check_exact=False, rtol=1e-6)


def test_descarta_filas_sin_rama(analisis, df_sintetico):
    df_con_nulos = df_sintetico.copy()
    df_con_nulos.loc[:10, "RAMA2D_R4"] = None
    out = analisis.calcular(df_con_nulos, nivel_ciiu="2d", verbose=False)
    assert out["ciiu_2d"].notna().all()


def test_descarta_fex_no_positivo(analisis, df_sintetico):
    df_malo = df_sintetico.copy()
    df_malo.loc[:5, "FEX_C18"] = 0
    df_malo.loc[5:10, "FEX_C18"] = np.nan
    out = analisis.calcular(df_malo, nivel_ciiu="2d", verbose=False)
    assert out["ocupados_promedio"].sum() > 0


# ═════════════════════════════════════════════════════════════════════
# TESTS DE CALIDAD ESTADÍSTICA
# ═════════════════════════════════════════════════════════════════════

def test_etiquetas_calidad_son_validas(analisis, df_sintetico):
    out = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    validas = {"Confiable", "Aceptable con reserva",
               "No publicable", "Sin dato"}
    assert set(out["calidad"].unique()).issubset(validas)


def test_cv_no_negativo(analisis, df_sintetico):
    out = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    cv_validos = out["cv_aprox"].dropna()
    assert (cv_validos >= 0).all()


# ═════════════════════════════════════════════════════════════════════
# TESTS DE REPONDERACIÓN POR MESES FALTANTES
# ═════════════════════════════════════════════════════════════════════

def test_celda_con_meses_faltantes_se_reponderán(analisis):
    """Una celda con solo 6 meses debe quedar dividida entre 12, no entre 6."""
    filas = []
    for mes in [1, 2, 3, 4, 5, 6]:  # solo medio año
        for _ in range(30):
            filas.append({"DPTO": "05", "RAMA2D_R4": "01",
                          "RAMA4D_R4": "0111", "FEX_C18": 1000.0,
                          "MES_NUM": mes})
    df = pd.DataFrame(filas)
    out = analisis.calcular(df, nivel_ciiu="2d", verbose=False)
    # Cada mes tiene 30 personas × 1000 = 30.000 expandidos
    # 6 meses con dato, promedio reponderado = 30.000 × 6/12 = 15.000
    assert abs(out["ocupados_promedio"].iloc[0] - 15_000) < 1.0
    assert out["meses_con_dato"].iloc[0] == 6


# ═════════════════════════════════════════════════════════════════════
# TESTS DE EXPORTACIÓN
# ═════════════════════════════════════════════════════════════════════

def test_exportar_excel_crea_archivo(analisis, df_sintetico, tmp_path):
    t2 = analisis.calcular(df_sintetico, nivel_ciiu="2d", verbose=False)
    # Simular enriquecimiento mínimo para que la matriz funcione
    t2_enr = t2.assign(
        dpto_codigo=t2["DPTO"],
        dpto_nombre=t2["DPTO"].map({"05": "Antioquia", "11": "Bogotá",
                                    "76": "Valle del Cauca"}),
        ciiu_2d_desc=t2["ciiu_2d"].map({"01": "Agricultura",
                                        "47": "Comercio",
                                        "85": "Educación"}),
        seccion_letra="X",
        seccion_desc="Prueba",
    )
    ruta = tmp_path / "salida.xlsx"
    resultado = analisis.exportar_excel({"2d": t2_enr}, ruta=ruta)

    assert resultado.exists()
    hojas = pd.ExcelFile(resultado).sheet_names
    assert "metadatos" in hojas
    assert "2d_largo_completo" in hojas
    assert "2d_matriz_dpto_x_rama" in hojas