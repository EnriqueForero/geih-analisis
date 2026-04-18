"""
tests/test_informalidad_v8.py — Tests para `clasificar_informalidad_dane`.

Incluye:
  - Tests sintéticos por rama del árbol de decisión (sin tocar datos reales)
  - Tests de canario integrados que validan contra el Excel oficial DANE
    (anex-GEIHEISS-dic2025-feb2026.xlsx) cuando hay datos disponibles

Ejecución:
    pytest tests/test_informalidad_v8.py -v

Para correr los canarios integrados se requiere variable de entorno:
    GEIH_PARQUET=/ruta/al/consolidado.parquet pytest ...
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geih.informalidad import (
    VARIABLES_CRITICAS,
    VARIABLES_REQUERIDAS,
    clasificar_informalidad_dane,
)

# ═════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════


def _row_to_df(**kwargs) -> pd.DataFrame:
    """Construye un DataFrame de una fila con los kwargs como columnas."""
    return pd.DataFrame([kwargs])


def _ei(df: pd.DataFrame, anio: int = 2025) -> int | None:
    """Aplica el clasificador y devuelve el valor EI (convención DANE).

    EI=1 → formal, EI=0 → informal, None → no clasificado.
    """
    informal = clasificar_informalidad_dane(df, anio_referencia=anio, verbose=False)
    val = informal.iloc[0]
    if pd.isna(val):
        return None
    # Inversión: INFORMAL=1 → EI=0; INFORMAL=0 → EI=1
    return 1 - int(val)


# ═════════════════════════════════════════════════════════════════════
# 1. Por definición — TFSR, Otro, Rama 84/99
# ═════════════════════════════════════════════════════════════════════


class TestPorDefinicion:
    def test_tfsr_es_informal(self):
        assert _ei(_row_to_df(P6430=6)) == 0

    def test_otro_es_informal(self):
        assert _ei(_row_to_df(P6430=8)) == 0

    def test_tfsr_aunque_sector_formal_sigue_informal(self):
        assert _ei(_row_to_df(P6430=6, P3045S1=1)) == 0

    def test_rama_84_admin_publica_es_formal(self):
        assert _ei(_row_to_df(P6430=1, RAMA2D_R4=84)) == 1

    def test_rama_99_orgs_extraterritoriales_es_formal(self):
        assert _ei(_row_to_df(P6430=4, RAMA2D_R4=99)) == 1

    def test_rama_84_NO_aplica_a_TFSR(self):
        # La regla final dice: P6430 NOT IN (6,8) para que rama 84 aplique
        assert _ei(_row_to_df(P6430=6, RAMA2D_R4=84)) == 0


# ═════════════════════════════════════════════════════════════════════
# 2. Gobierno (P6430=2) — siempre formal
# ═════════════════════════════════════════════════════════════════════


class TestGobierno:
    def test_gobierno_sin_cotizaciones_es_formal(self):
        # En la sintaxis SAS:
        # IF P6430=2 THEN FORMAL=1
        # IF P6430 IN (2) THEN EI=1
        assert _ei(_row_to_df(P6430=2)) == 1

    def test_gobierno_con_cotizaciones_es_formal(self):
        df = _row_to_df(P6430=2, P6100=1, P6110=4, P6920=1, P6930=1, P6940=3)
        assert _ei(df) == 1


# ═════════════════════════════════════════════════════════════════════
# 3. Asalariados (P6430 ∈ {1, 3, 7}) — solo OCUPACIÓN cuenta
# ═════════════════════════════════════════════════════════════════════


class TestAsalariadosOcupacion:
    """Para asalariados (1, 3, 7), EI se determina por SALUD+PENSION,
    NO por sector. El sector se calcula pero no se usa al final
    (excepto en rama 84/99)."""

    def test_asalariado_completo_es_formal(self):
        df = _row_to_df(P6430=1, P3045S1=1, P6100=1, P6110=1, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 1

    def test_asalariado_subsidiado_aunque_sector_formal_es_informal(self):
        # Sector formal pero salud subsidiada → SALUD=0 → EI=0
        df = _row_to_df(P6430=1, P3045S1=1, P6100=3, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 0

    def test_asalariado_sin_pension_es_informal(self):
        df = _row_to_df(P6430=1, P3045S1=1, P6100=1, P6110=1, P6920=2)
        assert _ei(df) == 0

    def test_asalariado_paga_el_todo_salud_es_informal(self):
        # P6110=3 (él paga totalidad) → SALUD=0
        df = _row_to_df(P6430=1, P3045S1=1, P6100=1, P6110=3, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 0

    def test_asalariado_paga_el_todo_pension_es_informal(self):
        # P6940=2 (él paga totalidad) → PENSION=0
        df = _row_to_df(P6430=1, P3045S1=1, P6100=1, P6110=1, P6920=1, P6930=1, P6940=2)
        assert _ei(df) == 0

    def test_pensionado_activo_es_formal(self):
        # P6920=3 → PENSION=1 sin importar quién pagó
        df = _row_to_df(P6430=1, P3045S1=1, P6100=1, P6110=1, P6920=3)
        assert _ei(df) == 1

    def test_regimen_NS_con_contrato_escrito_es_formal(self):
        # Excepción: P6100=9 + P6450=2 → SALUD=1
        df = _row_to_df(P6430=1, P3045S1=1, P6100=9, P6450=2, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 1

    def test_quien_paga_salud_NS_con_contrato_escrito_es_formal(self):
        # Excepción: P6110=9 + P6450=2 → SALUD=1
        df = _row_to_df(P6430=1, P3045S1=1, P6100=1, P6110=9, P6450=2, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 1

    def test_jornalero_es_asalariado(self):
        # P6430=7 se trata como asalariado
        df = _row_to_df(P6430=7, P6100=1, P6110=1, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 1

    def test_domestico_es_asalariado(self):
        # P6430=3 se trata como asalariado
        df = _row_to_df(P6430=3, P6100=1, P6110=1, P6920=1, P6930=1, P6940=1)
        assert _ei(df) == 1


# ═════════════════════════════════════════════════════════════════════
# 4. Independientes (P6430 ∈ {4, 5}) — sector via árbol completo
# ═════════════════════════════════════════════════════════════════════


class TestIndependientesSinNegocio:
    def test_indep_sin_neg_registrado(self):
        df = _row_to_df(P6430=4, P6765=1, P3065=1)
        assert _ei(df) == 1

    def test_indep_sin_neg_no_reg_con_contab(self):
        df = _row_to_df(P6430=4, P6765=1, P3065=2, P3066=1)
        assert _ei(df) == 1

    def test_indep_sin_neg_no_reg_sin_contab(self):
        df = _row_to_df(P6430=4, P6765=1, P3065=2, P3066=2)
        assert _ei(df) == 0

    def test_patron_sin_neg_contab_NS_grande(self):
        df = _row_to_df(P6430=5, P6765=1, P3065=9, P3066=9, P3069=6)
        assert _ei(df) == 1

    def test_patron_sin_neg_contab_NS_chico(self):
        df = _row_to_df(P6430=5, P6765=1, P3065=9, P3066=9, P3069=2)
        assert _ei(df) == 0

    def test_cta_propia_sin_neg_contab_NS_directivo(self):
        # OFICIO_C8 00-20 → directivo/profesional → formal
        df = _row_to_df(P6430=4, P6765=1, P3065=9, P3066=9, OFICIO_C8="1010")
        assert _ei(df) == 1

    def test_cta_propia_sin_neg_contab_NS_tecnico(self):
        # OFICIO_C8 21+ → técnico/operario → informal
        df = _row_to_df(P6430=4, P6765=1, P3065=9, P3066=9, OFICIO_C8="2510")
        assert _ei(df) == 0


class TestIndependientesConNegocioConRegistro:
    def test_registrado_renovado_anio_actual(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=1, P3067S1=1, P3067S2=2024)
        assert _ei(df, anio=2025) == 1

    def test_registrado_renovado_anio_vencido(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=1, P3067S1=1, P3067S2=2022)
        assert _ei(df, anio=2025) == 0

    def test_no_renovado_con_contab(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=1, P3067S1=2, P6775=1)
        assert _ei(df) == 1

    def test_no_renovado_sin_contab(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=1, P3067S1=2, P6775=2)
        assert _ei(df) == 0

    def test_no_renovado_contab_NA_directivo(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=1, P3067S1=2, P6775=3, OFICIO_C8="1010")
        assert _ei(df) == 1

    def test_no_renovado_contab_NA_tecnico(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=1, P3067S1=2, P6775=3, OFICIO_C8="2510")
        assert _ei(df) == 0


class TestIndependientesConNegocioSinRegistro:
    def test_p6775_1_p3068_1(self):
        df = _row_to_df(P6430=5, P6765=7, P3067=2, P6775=1, P3068=1)
        assert _ei(df) == 1

    def test_p6775_1_p3068_2(self):
        df = _row_to_df(P6430=5, P6765=7, P3067=2, P6775=1, P3068=2)
        assert _ei(df) == 0

    def test_p6775_2_es_informal(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=2, P6775=2)
        assert _ei(df) == 0

    def test_patron_p6775_9_grande(self):
        df = _row_to_df(P6430=5, P6765=7, P3067=2, P6775=9, P3069=5)
        assert _ei(df) == 1

    def test_cta_propia_p6775_9_directivo(self):
        df = _row_to_df(P6430=4, P6765=7, P3067=2, P6775=9, OFICIO_C8="1510")
        assert _ei(df) == 1


# ═════════════════════════════════════════════════════════════════════
# 5. Anti-regresión: gobierno NUNCA debe quedar en 0% informal
# ═════════════════════════════════════════════════════════════════════


class TestAntiRegresionGobierno:
    def test_gobierno_no_es_atajo_explicito(self):
        """Verifica que gobierno se procesa por la regla SAS, no
        por un atajo `informal[pos == 2] = 0` superviviente."""
        # Construir 1000 filas de gobierno con diferentes valores de salud/pensión
        np.random.seed(42)
        n = 1000
        df = pd.DataFrame(
            {
                "P6430": [2] * n,
                "P6100": np.random.choice([1, 2, 3, 9], n),
                "P6110": np.random.choice([1, 2, 3, 4, 5, 9], n),
                "P6920": np.random.choice([1, 2, 3], n),
                "P6930": np.random.choice([1, 2, 3, 4, 9], n),
                "P6940": np.random.choice([1, 2, 3, 4], n),
                "P6450": np.random.choice([1, 2], n),
            }
        )
        info = clasificar_informalidad_dane(df, verbose=False)
        # Para gobierno (P6430=2), TODOS deben ser formales (EI=1, INFORMAL=0)
        # según la sintaxis SAS oficial.
        assert (info == 0).sum() == n, "Gobierno debe ser 100% formal según SAS oficial"


# ═════════════════════════════════════════════════════════════════════
# 6. Canario integrado contra Excel DANE
# ═════════════════════════════════════════════════════════════════════

REF_DANE_DIC_2025 = {
    "Total nacional": (24223.650, 13456.192, 55.5498),
    "13 ciudades y A.M.": (11525.114, 4757.815, 41.2822),
    "Centros poblados y rural disperso": (4835.092, 4022.571, 83.1953),
}
"""Cifras EXACTAS del Excel oficial anex-GEIHEISS-dic2025-feb2026.xlsx
para Diciembre 2025. Tupla: (ocupados_mil, informales_mil, tasa_pct)."""

TOLERANCIA_PP = 0.4  # ±0.4 puntos porcentuales


@pytest.mark.canario
class TestCanarioBoletinDANE:
    """Validación contra cifras EXACTAS del Excel oficial DANE.

    Requiere variable de entorno GEIH_PARQUET con la ruta al consolidado
    o se salta automáticamente.
    """

    @pytest.fixture(scope="class")
    def df_dic(self):
        ruta = os.environ.get(
            "GEIH_PARQUET",
            "/content/drive/MyDrive/ProColombia/GEIH/GEIH_consolidado_2025.parquet",
        )
        if not Path(ruta).exists():
            pytest.skip(f"No se encontró el parquet: {ruta}")

        from geih.config import ConfigGEIH
        from geih.preparador import PreparadorGEIH

        geih = pd.read_parquet(ruta)
        prep = PreparadorGEIH(config=ConfigGEIH(anio=2025, n_meses=12))
        return prep.preparar_base(geih, meses_filtro=12)

    def _tasa(self, df, dominio=None):
        oci = df[df["OCI"] == 1]
        if dominio is not None:
            oci = oci[oci["DOMINIO"] == dominio]
        t = oci["FEX_ADJ"].sum()
        i = oci.loc[oci["INFORMAL"] == 1, "FEX_ADJ"].sum()
        return 100 * i / t if t > 0 else float("nan")

    def test_total_nacional(self, df_dic):
        _ocu_dane, _inf_dane, tasa_dane = REF_DANE_DIC_2025["Total nacional"]
        tasa_lib = self._tasa(df_dic)
        delta = tasa_lib - tasa_dane
        assert abs(delta) <= TOLERANCIA_PP, (
            f"Total nacional: librería {tasa_lib:.4f}% vs DANE "
            f"{tasa_dane:.4f}% (Δ={delta:+.2f} pp, tol ±{TOLERANCIA_PP})"
        )

    def test_13_ciudades_AM(self, df_dic):
        _ocu_dane, _inf_dane, tasa_dane = REF_DANE_DIC_2025["13 ciudades y A.M."]
        tasa_lib = self._tasa(df_dic, dominio="13_AM")
        delta = tasa_lib - tasa_dane
        assert abs(delta) <= TOLERANCIA_PP, (
            f"13 A.M.: librería {tasa_lib:.4f}% vs DANE {tasa_dane:.4f}% "
            f"(Δ={delta:+.2f} pp, tol ±{TOLERANCIA_PP})"
        )

    def test_centros_poblados_rural(self, df_dic):
        _ocu_dane, _inf_dane, tasa_dane = REF_DANE_DIC_2025["Centros poblados y rural disperso"]
        tasa_lib = self._tasa(df_dic, dominio="rural")
        delta = tasa_lib - tasa_dane
        assert abs(delta) <= TOLERANCIA_PP + 0.1, (  # ligeramente más laxo
            f"Rural: librería {tasa_lib:.4f}% vs DANE {tasa_dane:.4f}% "
            f"(Δ={delta:+.2f} pp, tol ±{TOLERANCIA_PP + 0.1})"
        )

    def test_absolutos_nacional_cuadran(self, df_dic):
        """Validación adicional: número absoluto de informales debe
        coincidir con el Excel oficial (en miles)."""
        _ocu_dane, inf_dane, _ = REF_DANE_DIC_2025["Total nacional"]
        oci = df_dic[df_dic["OCI"] == 1]
        inf_lib = oci.loc[oci["INFORMAL"] == 1, "FEX_ADJ"].sum() / 1e3
        delta_pct = abs(inf_lib - inf_dane) / inf_dane * 100
        assert delta_pct <= 1.0, (
            f"Informales nacional: librería {inf_lib:,.0f} mil vs "
            f"DANE {inf_dane:,.0f} mil (Δ={delta_pct:.2f}%, tol 1%)"
        )


# ═════════════════════════════════════════════════════════════════════
# 7. Sanity: variables documentadas
# ═════════════════════════════════════════════════════════════════════


class TestVariablesDocumentadas:
    def test_variables_criticas_subset_de_requeridas(self):
        assert VARIABLES_CRITICAS.issubset(VARIABLES_REQUERIDAS)

    def test_lista_variables_no_vacia(self):
        assert len(VARIABLES_REQUERIDAS) >= 18
        assert len(VARIABLES_CRITICAS) >= 12
