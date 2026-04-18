"""
tests/test_replicacion_seguridad_social_excel.py — Tests de replicación
de las 4 hojas de seguridad social.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geih.replicacion_dane_common import (
    PeriodoMovil,
    ResultadoReplicacion,
)
from geih.replicacion_dane_seguridad_social import (
    DOMINIOS_POR_HOJA_SS,
    HOJAS_SEGURIDAD_SOCIAL,
    LINEAS_SS,
    ReplicadorSeguridadSocial,
)

EXCEL_OFICIAL = Path("/mnt/user-data/uploads/1776399661404_anex-GEIHEISS-dic2025-feb2026.xlsx")


@pytest.fixture
def df_sintetico_ss():
    """DF sintético con las columnas de SS."""
    rng = np.random.default_rng(seed=42)
    n = 2000
    return pd.DataFrame(
        {
            "FEX_ADJ": rng.uniform(500, 2000, n),
            "OCI": np.ones(n, dtype=int),
            "DOMINIO": rng.choice(
                ["13_AM", "10_ciudades", "otras_cab", "rural"],
                n,
            ),
            "SEXO": rng.choice(["Hombres", "Mujeres"], n),
            "P6090": rng.choice([1, 2, 9], n, p=[0.9, 0.08, 0.02]),
            "P6100": rng.choice([1, 2, 3, 9], n, p=[0.45, 0.05, 0.45, 0.05]),
            "P6110": rng.choice([1, 2, 3, 4, 9], n),
            "P6920": rng.choice([1, 2, 3], n, p=[0.4, 0.55, 0.05]),
        }
    )


class TestAPISS:
    def test_hojas_ss_son_4(self):
        assert len(HOJAS_SEGURIDAD_SOCIAL) == 4

    def test_lineas_ss_son_10(self):
        assert len(LINEAS_SS) == 10
        assert LINEAS_SS[0] == "Población ocupada"
        assert LINEAS_SS[-1] == "Cotiza a pensión"

    def test_dominios_por_hoja_cubren_todas(self):
        for hoja in HOJAS_SEGURIDAD_SOCIAL:
            assert hoja in DOMINIOS_POR_HOJA_SS
            assert len(DOMINIOS_POR_HOJA_SS[hoja]) >= 2


@pytest.mark.skipif(
    not EXCEL_OFICIAL.exists(),
    reason="Excel no disponible",
)
class TestReplicacionSSSintetico:
    def test_replicar_tnal_produce_bloques_miles_y_pct(
        self,
        df_sintetico_ss,
    ):
        rep = ReplicadorSeguridadSocial(EXCEL_OFICIAL)
        periodo = PeriodoMovil(
            etiqueta_original="Dic 25 - feb 26",
            meses=[(2025, 12), (2026, 1), (2026, 2)],
            es_mensual=False,
        )
        res = rep.replicar(
            df_sintetico_ss,
            periodo,
            hojas=["Seguridad social Tnal"],
        )
        assert isinstance(res, ResultadoReplicacion)
        h = res.hojas[0]
        # 3 dominios × 2 bloques × 10 líneas = 60 celdas esperadas
        # (pero el parser puede recoger filas extras que quedan NA)
        assert h.n_celdas >= 60, f"got {h.n_celdas}"

        # Debe haber celdas con condición "Miles" y condición "%"
        condiciones = {c.condicion for c in h.celdas}
        assert "Miles" in condiciones or "miles" in {c.lower() for c in condiciones}
        assert "%" in condiciones

    def test_replicar_tnal_sexo(self, df_sintetico_ss):
        rep = ReplicadorSeguridadSocial(EXCEL_OFICIAL)
        periodo = PeriodoMovil(
            etiqueta_original="Dic 25 - feb 26",
            meses=[(2025, 12), (2026, 1), (2026, 2)],
            es_mensual=False,
        )
        res = rep.replicar(
            df_sintetico_ss,
            periodo,
            hojas=["Seguridad social Tnal sexo"],
        )
        h = res.hojas[0]
        # 6 dominios (3 dom × 2 sexos) × 2 bloques × 10 líneas = 120
        assert h.n_celdas >= 100, f"got {h.n_celdas}"

    def test_replicar_13C_sexo(self, df_sintetico_ss):
        rep = ReplicadorSeguridadSocial(EXCEL_OFICIAL)
        periodo = PeriodoMovil(
            etiqueta_original="Dic 25 - feb 26",
            meses=[(2025, 12), (2026, 1), (2026, 2)],
            es_mensual=False,
        )
        res = rep.replicar(
            df_sintetico_ss,
            periodo,
            hojas=["Seguridad social 13C sexo"],
        )
        h = res.hojas[0]
        # 4 dominios × 2 bloques × 10 líneas = 80
        assert h.n_celdas >= 70, f"got {h.n_celdas}"


class TestCalculoLineasSS:
    """Unit tests del cálculo interno de líneas."""

    def test_calculo_con_df_minimo(self):
        """DF pequeño para verificar la aritmética."""
        if not EXCEL_OFICIAL.exists():
            pytest.skip("Excel no disponible")
        # 10 personas, todas en 13_AM, 5 contributivo, 5 subsidiado
        df = pd.DataFrame(
            {
                "FEX_ADJ": [1000] * 10,
                "OCI": [1] * 10,
                "DOMINIO": ["13_AM"] * 10,
                "P6090": [1] * 10,  # todas afiliadas
                "P6100": [1] * 5 + [3] * 5,  # 5 contrib + 5 subs
                "P6110": [1] * 5 + [9] * 5,
                "P6920": [1] * 10,  # todas cotizan
            }
        )
        rep = ReplicadorSeguridadSocial(EXCEL_OFICIAL)
        mask = pd.Series(True, index=df.index)
        res = rep._calcular_lineas_ss(df, mask, en_miles=True)
        # Todas 10 personas × 1000 FEX = 10000 → 10 en miles
        assert res["Población ocupada"] == 10.0
        assert res["Afiliada a salud"] == 10.0
        assert res["Régimen contributivo"] == 5.0
        assert res["Régimen subsidiado"] == 5.0
        assert res["Cotiza a pensión"] == 10.0

    def test_calculo_distribucion_pct_suma_razonable(self):
        """Los % deben tener Población ocupada = 100."""
        if not EXCEL_OFICIAL.exists():
            pytest.skip("Excel no disponible")
        df = pd.DataFrame(
            {
                "FEX_ADJ": [1000] * 10,
                "OCI": [1] * 10,
                "DOMINIO": ["13_AM"] * 10,
                "P6090": [1] * 10,
                "P6100": [1] * 5 + [3] * 5,
                "P6110": [1] * 5 + [9] * 5,
                "P6920": [1] * 10,
            }
        )
        rep = ReplicadorSeguridadSocial(EXCEL_OFICIAL)
        mask = pd.Series(True, index=df.index)
        res = rep._calcular_lineas_ss(df, mask, en_miles=False)
        # Población ocupada debe ser 100% del denominador
        assert res["Población ocupada"] == 100.0
        # 100% afiliada
        assert res["Afiliada a salud"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
