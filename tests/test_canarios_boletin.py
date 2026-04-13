# -*- coding: utf-8 -*-
"""
tests/test_canarios_boletin.py — Tests "canario" del Boletín DANE.

Estos tests no validan funciones aisladas: validan que la salida
end-to-end de la librería reproduce cifras del Boletín GEIH
Diciembre 2025 dentro de tolerancias estrictas.

Son los detectores más sensibles que tenemos para regresiones:
si cualquiera de ellos falla, algún cambio en config.py, preparador.py
o indicadores.py rompió la replicación del boletín oficial.

Diseño:
  - Cada test es un "canario": una sola condición numérica con
    semántica clara contra la fuente DANE.
  - Las fixtures cargan microdatos GEIH 2025 desde una ruta
    parametrizable (variable de entorno GEIH_TEST_DATA).
  - Si la ruta no existe, los tests se SKIPEAN, no fallan.
    Esto permite correrlos en CI cuando los datos están disponibles
    y simplemente saltarlos en el dev local sin acceso al consolidado.

Uso:
    # Local con datos en /data/geih/2025
    GEIH_TEST_DATA=/data/geih/2025 pytest tests/test_canarios_boletin.py -v

    # CI con datos en otra ubicación
    GEIH_TEST_DATA=/mnt/datalake/geih/2025 pytest -v

    # Sin datos → todos los tests se skipean limpiamente
    pytest tests/test_canarios_boletin.py -v

Referencia: pres-GEIH-dic2025.pdf y anex-GEIH-dic2025.xlsx (DANE).

Autor: Néstor Enrique Forero Herrera
Versión: v6.0 (abril 2026)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────

# Ruta a los microdatos consolidados GEIH 2025. Si no está disponible,
# todos los tests de este módulo se skipean.
RUTA_DATA_ENV = os.environ.get("GEIH_TEST_DATA", "")
RUTA_DATA = Path(RUTA_DATA_ENV) if RUTA_DATA_ENV else None

# Tolerancias estrictas alineadas con el contrato del notebook de verificación
TOL_TASA_PP = 0.05      # ±0.05 puntos porcentuales
TOL_POB_MILES = 1.0     # ±1 mil personas
TOL_INFORMALIDAD = 0.5  # ±0.5 p.p. (ligeramente más laxo: la def. oficial
                        # incluye reglas de registro mercantil que la
                        # librería no puede replicar sin metadatos extra)


# ─────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────

pytestmark = pytest.mark.skipif(
    RUTA_DATA is None or not RUTA_DATA.exists(),
    reason=(
        "GEIH_TEST_DATA no apunta a un consolidado válido. "
        "Para correr estos tests, exporte la variable de entorno apuntando "
        "al directorio con los microdatos GEIH 2025."
    ),
)


@pytest.fixture(scope="module")
def geih_raw():
    """Carga el consolidado crudo GEIH 2025 (los 12 meses)."""
    from geih import ConfigGEIH, ConsolidadorGEIH
    cfg = ConfigGEIH(anio=2025, n_meses=12)
    cons = ConsolidadorGEIH(cfg)
    return cons.consolidar(RUTA_DATA)


@pytest.fixture(scope="module")
def df_dic(geih_raw):
    """Vista preparada de Diciembre 2025 (mes puntual, divisor FEX = 1)."""
    from geih import ConfigGEIH, PreparadorGEIH
    cfg = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[12])
    return PreparadorGEIH(cfg).preparar_base(geih_raw)


@pytest.fixture(scope="module")
def df_trm(geih_raw):
    """Vista preparada del trimestre Oct-Dic 2025 (divisor FEX = 3)."""
    from geih import ConfigGEIH, PreparadorGEIH
    cfg = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[10, 11, 12])
    return PreparadorGEIH(cfg).preparar_base(geih_raw)


@pytest.fixture(scope="module")
def df_anu(geih_raw):
    """Vista preparada Ene-Dic 2025 (divisor FEX = 12)."""
    from geih import ConfigGEIH, PreparadorGEIH
    cfg = ConfigGEIH(anio=2025, n_meses=12, meses_rango=list(range(1, 13)))
    return PreparadorGEIH(cfg).preparar_base(geih_raw)


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def _tasas_crudas(df):
    """Recalcula TD/TGP/TO a precisión completa.

    No usa IndicadoresLaborales.calcular() porque ese método redondea
    a 1 decimal y aquí necesitamos resolución para validar contra ±0.05.
    """
    fex = "FEX_ADJ"
    pet = df.loc[df["PET"] == 1, fex].sum()
    pea = df.loc[df["FT"] == 1, fex].sum()
    oci = df.loc[df["OCI"] == 1, fex].sum()
    dsi = df.loc[df["DSI"] == 1, fex].sum()
    return {
        "td": 100 * dsi / pea if pea > 0 else float("nan"),
        "tgp": 100 * pea / pet if pet > 0 else float("nan"),
        "to": 100 * oci / pet if pet > 0 else float("nan"),
        "pet_k": pet / 1e3,
        "pea_k": pea / 1e3,
        "oci_k": oci / 1e3,
        "dsi_k": dsi / 1e3,
    }


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE EXPANSIÓN — divisor FEX correcto en todas las vistas
# ─────────────────────────────────────────────────────────────────────

class TestCanarioPET:
    """PET nacional 2025 ≈ 40.9M en CUALQUIER vista temporal.

    Este es el detector más sensible de bugs de expansión: la PET
    apenas varía mes a mes (~0.1%), así que si una vista da otro
    valor, el divisor FEX está mal aplicado.
    """

    def test_pet_diciembre(self, df_dic):
        r = _tasas_crudas(df_dic)
        assert 40_500 < r["pet_k"] < 41_300, (
            f"PET Dic 2025 = {r['pet_k']:.0f} mil fuera de [40500, 41300]. "
            f"Esperado ~40,925 mil (Boletín pág. 8). Divisor FEX mal aplicado."
        )

    def test_pet_trimestre(self, df_trm):
        r = _tasas_crudas(df_trm)
        assert 40_500 < r["pet_k"] < 41_300, (
            f"PET Oct-Dic 2025 = {r['pet_k']:.0f} mil. "
            f"BUG TÍPICO: si da ~13,600, el divisor FEX se quedó en 12 "
            f"en lugar de 3 (no se sincronizó con meses_rango)."
        )

    def test_pet_anual(self, df_anu):
        r = _tasas_crudas(df_anu)
        assert 40_500 < r["pet_k"] < 41_300, (
            f"PET Ene-Dic 2025 = {r['pet_k']:.0f} mil fuera de [40500, 41300]."
        )


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE TASAS — TD/TGP/TO contra Boletín pág. 3
# ─────────────────────────────────────────────────────────────────────

class TestCanarioTasasNacionales:
    """TD/TGP/TO Total Nacional Dic 2025 dentro de ±0.05 p.p."""

    def test_td_diciembre(self, df_dic):
        r = _tasas_crudas(df_dic)
        assert abs(r["td"] - 8.0) <= TOL_TASA_PP, (
            f"TD Dic 2025 = {r['td']:.4f}%, esperado 8.0% ±{TOL_TASA_PP}"
        )

    def test_tgp_diciembre(self, df_dic):
        r = _tasas_crudas(df_dic)
        assert abs(r["tgp"] - 64.3) <= TOL_TASA_PP, (
            f"TGP Dic 2025 = {r['tgp']:.4f}%, esperado 64.3% ±{TOL_TASA_PP}"
        )

    def test_to_diciembre(self, df_dic):
        r = _tasas_crudas(df_dic)
        assert abs(r["to"] - 59.2) <= TOL_TASA_PP, (
            f"TO Dic 2025 = {r['to']:.4f}%, esperado 59.2% ±{TOL_TASA_PP}"
        )

    def test_td_anual(self, df_anu):
        r = _tasas_crudas(df_anu)
        assert abs(r["td"] - 8.9) <= TOL_TASA_PP, (
            f"TD anual 2025 = {r['td']:.4f}%, esperado 8.9% ±{TOL_TASA_PP}"
        )


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE BRECHA POR SEXO — pág. 5-6
# ─────────────────────────────────────────────────────────────────────

class TestCanarioSexo:
    """Sexo derivado existe y reproduce las tasas del Boletín."""

    def test_sexo_es_columna_textual(self, df_dic):
        """Protege contra la regresión P3271 → SEXO no derivada."""
        assert "SEXO" in df_dic.columns, (
            "Falta columna SEXO. PreparadorGEIH.agregar_variables_derivadas "
            "no se ejecutó (parametro derivar=True default) o el método no "
            "está mapeando P3271 → SEXO correctamente."
        )
        valores = set(df_dic["SEXO"].dropna().unique())
        assert valores == {"Hombres", "Mujeres"}, (
            f"SEXO tiene valores inesperados: {valores}"
        )

    def test_td_hombres_diciembre(self, df_dic):
        r = _tasas_crudas(df_dic[df_dic["SEXO"] == "Hombres"])
        assert abs(r["td"] - 6.4) <= TOL_TASA_PP

    def test_td_mujeres_diciembre(self, df_dic):
        r = _tasas_crudas(df_dic[df_dic["SEXO"] == "Mujeres"])
        assert abs(r["td"] - 10.1) <= TOL_TASA_PP

    def test_brecha_td_diciembre(self, df_dic):
        tdh = _tasas_crudas(df_dic[df_dic["SEXO"] == "Hombres"])["td"]
        tdm = _tasas_crudas(df_dic[df_dic["SEXO"] == "Mujeres"])["td"]
        brecha = tdm - tdh
        assert abs(brecha - 3.7) <= TOL_TASA_PP, (
            f"Brecha TD M-H = {brecha:.4f} p.p., esperado 3.7 ±{TOL_TASA_PP}"
        )


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE DOMINIO GEOGRÁFICO — pág. 7-9
# ─────────────────────────────────────────────────────────────────────

class TestCanarioDominio:
    """DOMINIO clasificado correctamente contra Boletín DANE pág. 7."""

    def test_dominio_existe(self, df_dic):
        assert "DOMINIO" in df_dic.columns, (
            "Falta columna DOMINIO. agregar_variables_derivadas no la creó."
        )

    def test_dominio_sin_residuales(self, df_dic):
        """No deben quedar registros sin clasificar (categoría 'otros')."""
        n_otros = (df_dic["DOMINIO"] == "otros").sum()
        assert n_otros < 100, (
            f"{n_otros} filas en DOMINIO='otros'. La clasificación dejó "
            f"residuales — revise la regla en agregar_variables_derivadas."
        )

    def test_ocupados_13_am(self, df_dic):
        """13 A.M. Dic 2025: 11,525 mil ocupados (Boletín pág. 9)."""
        oci = df_dic[(df_dic["OCI"] == 1) & (df_dic["DOMINIO"] == "13_AM")]
        suma = oci["FEX_ADJ"].sum() / 1e3
        assert abs(suma - 11_525) <= TOL_POB_MILES * 5, (
            f"Ocupados 13_AM Dic = {suma:.1f} mil, esperado 11,525 ±5. "
            f"BUG TÍPICO: si da ~10,950, DPTOS_13_CIUDADES quedó incompleto "
            f"o se está usando AREA_A_CIUDAD (DIVIPOLA) en vez de AREA "
            f"(2 dígitos) para clasificar."
        )

    def test_ocupados_rural(self, df_dic):
        """Rural Dic 2025: 4,835 mil ocupados (Boletín pág. 9)."""
        oci = df_dic[(df_dic["OCI"] == 1) & (df_dic["DOMINIO"] == "rural")]
        suma = oci["FEX_ADJ"].sum() / 1e3
        assert abs(suma - 4_835) <= TOL_POB_MILES * 5

    def test_dominio_suma_total(self, df_dic):
        """La suma de los 4 dominios debe dar el total nacional ocupado."""
        oci = df_dic[df_dic["OCI"] == 1]
        total_dominios = oci.groupby("DOMINIO")["FEX_ADJ"].sum().sum() / 1e3
        total_nacional = oci["FEX_ADJ"].sum() / 1e3
        assert abs(total_dominios - total_nacional) <= TOL_POB_MILES, (
            f"Suma por dominio ({total_dominios:.1f}) != total nacional "
            f"({total_nacional:.1f}). Hay registros sin clasificar o duplicados."
        )


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE RAMAS CIIU — pág. 12 y hoja Excel anexo
# ─────────────────────────────────────────────────────────────────────

class TestCanarioRamasCIIU:
    """RAMA derivada colapsa a las 13 ramas exactas del Boletín."""

    def test_rama_existe(self, df_dic):
        assert "RAMA" in df_dic.columns

    def test_rama_son_exactamente_13(self, df_dic):
        """El Boletín DANE publica 13 ramas (Minas colapsada en Sum.Eléct.)."""
        oci = df_dic[df_dic["OCI"] == 1]
        ramas = oci["RAMA"].dropna().unique()
        assert len(ramas) == 13, (
            f"Esperaba 13 ramas, obtuve {len(ramas)}: {sorted(ramas)}. "
            f"Si son 14, RAMA2D_R4 no está colapsando 'Explotación de minas' "
            f"dentro de 'Suministro de electricidad...'."
        )

    def test_rama_industrias_manufactureras(self, df_dic):
        """Manufacturas Dic 2025: 2,885 mil (anexo Excel, hoja TN_T13_rama)."""
        oci = df_dic[df_dic["OCI"] == 1]
        suma = oci.loc[oci["RAMA"] == "Industrias manufactureras", "FEX_ADJ"].sum() / 1e3
        assert abs(suma - 2_885) <= TOL_POB_MILES * 5


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE POSICIÓN OCUPACIONAL — pág. 15
# ─────────────────────────────────────────────────────────────────────

class TestCanarioPosicionOcupacional:
    """POSICION_OCU usa el código CISE-93 correcto (jornalero=7, no 8)."""

    def test_posicion_ocu_existe(self, df_dic):
        assert "POSICION_OCU" in df_dic.columns

    def test_jornalero_es_codigo_7(self, df_dic):
        """REGRESIÓN: jornalero debe ser P6430=7, no P6430=8.

        Si este test falla, el mapa de POSICION_OCU está cruzado:
        está usando el orden alfabético del cuestionario en vez del
        código CISE-93 que usan los microdatos publicados.

        Cifra de control: jornaleros Dic 2025 ≈ 849 mil (Boletín pág. 15).
        """
        oci = df_dic[df_dic["OCI"] == 1]
        jornaleros = oci.loc[oci["POSICION_OCU"] == "Jornalero o Peón", "FEX_ADJ"].sum() / 1e3
        assert abs(jornaleros - 849) <= TOL_POB_MILES * 10, (
            f"Jornaleros = {jornaleros:.0f} mil, esperado 849 ±10. "
            f"Si da ~12 (≈ 'Otro'), el código jornalero está mapeado a P6430=8 "
            f"en vez de P6430=7. Use POSICION_OCUPACIONAL del config.py."
        )

    def test_obrero_empleado_particular(self, df_dic):
        """Obrero particular Dic 2025 ≈ 11,063 mil (Boletín pág. 15)."""
        oci = df_dic[df_dic["OCI"] == 1]
        obreros = oci.loc[oci["POSICION_OCU"] == "Obrero, empleado particular", "FEX_ADJ"].sum() / 1e3
        assert abs(obreros - 11_063) <= TOL_POB_MILES * 10


# ─────────────────────────────────────────────────────────────────────
# CANARIOS DE INFORMALIDAD — pág. 42
# ─────────────────────────────────────────────────────────────────────

class TestCanarioInformalidad:
    """INFORMAL aproximada con tolerancia laxa (±0.5 p.p.).

    La definición oficial DANE incluye registro mercantil de la empresa,
    metadato que la GEIH no expone. El cálculo de la librería usa la
    aproximación 17ª CIET con P6430+P6920+P6870 y se espera que quede
    dentro de ±0.5 p.p. del Boletín.
    """

    def _prop_inf(self, sub):
        oci = sub[sub["OCI"] == 1]
        fex = oci["FEX_ADJ"].sum()
        if fex == 0:
            return float("nan")
        inf = oci.loc[oci["INFORMAL"] == 1, "FEX_ADJ"].sum()
        return 100 * inf / fex

    def test_informal_existe(self, df_dic):
        assert "INFORMAL" in df_dic.columns, (
            "Falta columna INFORMAL. Verifique que P6430 y P6920 estén en "
            "COLUMNAS_DEFAULT y que agregar_variables_derivadas las use."
        )

    def test_informalidad_nacional(self, df_dic):
        prop = self._prop_inf(df_dic)
        assert abs(prop - 55.5) <= TOL_INFORMALIDAD, (
            f"Informalidad nacional Dic = {prop:.2f}%, esperado 55.5% ±0.5"
        )

    def test_informalidad_rural(self, df_dic):
        prop = self._prop_inf(df_dic[df_dic["DOMINIO"] == "rural"])
        # Rural tolera más variación (concentración de patrones pequeños)
        assert abs(prop - 83.2) <= 1.0, (
            f"Informalidad rural Dic = {prop:.2f}%, esperado 83.2% ±1.0"
        )


# ─────────────────────────────────────────────────────────────────────
# CANARIO DEL VALOR CRUDO — Issue C2 indicadores.py
# ─────────────────────────────────────────────────────────────────────

class TestCanarioIndicadoresRaw:
    """IndicadoresLaborales.calcular debe exponer valores sin redondear."""

    def test_calcular_devuelve_raw(self, df_dic):
        from geih import IndicadoresLaborales
        r = IndicadoresLaborales().calcular(df_dic)
        assert "TD_raw" in r and "TGP_raw" in r and "TO_raw" in r, (
            "calcular() no expone *_raw. Sin esos valores no se puede "
            "validar contra el anexo Excel del DANE con tolerancia ±0.05 p.p."
        )
        # El raw debe diferir del display por algún decimal en al menos
        # uno de los tres
        diferencias = [
            abs(r["TD_raw"] - r["TD_%"]),
            abs(r["TGP_raw"] - r["TGP_%"]),
            abs(r["TO_raw"] - r["TO_%"]),
        ]
        assert max(diferencias) < 0.5, (
            "Los valores raw difieren demasiado del display — uno de los "
            "dos está mal calculado."
        )
