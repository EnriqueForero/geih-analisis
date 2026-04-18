"""Tests para geih.indicadores — Indicadores laborales."""

import pandas as pd
import pytest

from geih.config import ConfigGEIH
from geih.indicadores import IndicadoresLaborales


class TestIndicadoresLaboralesSinteticos:
    """Tests con datos sintéticos de resultado conocido."""

    @pytest.fixture
    def df_sintetico(self):
        """100 personas: 60 OCI, 20 DSI, 20 FFT → TD=25%, TGP=80%, TO=60%."""
        n = 100
        df = pd.DataFrame(
            {
                "FEX_ADJ": [100.0] * n,
                "OCI": [1] * 60 + [0] * 40,
                "FT": [1] * 80 + [0] * 20,  # PEA = 80
                "DSI": [0] * 60 + [1] * 20 + [0] * 20,
                "PET": [1] * n,
                "FFT": [0] * 80 + [1] * 20,
            }
        )
        return df

    def test_td_conocida(self, df_sintetico):
        """TD = DSI/PEA = 20/80 = 25.0%."""
        config = ConfigGEIH(anio=2025, n_meses=1)
        ind = IndicadoresLaborales(config=config)
        r = ind.calcular(df_sintetico)
        assert r["TD_%"] == pytest.approx(25.0, abs=0.1)

    def test_tgp_conocida(self, df_sintetico):
        """TGP = PEA/PET = 80/100 = 80.0%."""
        config = ConfigGEIH(anio=2025, n_meses=1)
        ind = IndicadoresLaborales(config=config)
        r = ind.calcular(df_sintetico)
        assert r["TGP_%"] == pytest.approx(80.0, abs=0.1)

    def test_to_conocida(self, df_sintetico):
        """TO = OCI/PET = 60/100 = 60.0%."""
        config = ConfigGEIH(anio=2025, n_meses=1)
        ind = IndicadoresLaborales(config=config)
        r = ind.calcular(df_sintetico)
        assert r["TO_%"] == pytest.approx(60.0, abs=0.1)

    def test_identidad_pea(self, df_sintetico):
        """PEA = OCI + DSI debe cumplirse."""
        config = ConfigGEIH(anio=2025, n_meses=1)
        ind = IndicadoresLaborales(config=config)
        r = ind.calcular(df_sintetico)
        pea = r["PEA_M"]
        ocu = r["Ocupados_M"]
        dsi = r["Desocupados_M"]
        assert pea == pytest.approx(ocu + dsi, rel=0.01)


class TestSanityCheck:
    """Tests del sanity check multi-año."""

    def test_sanity_check_2025_pasa(self):
        """Con TD=8.9% y config 2025, sanity check debe pasar."""
        config = ConfigGEIH(anio=2025, n_meses=12)
        ind = IndicadoresLaborales(config=config)
        resultado = {
            "TD_%": 8.9,
            "TGP_%": 64.3,
            "TO_%": 58.6,
            "PET_M": 40.0,
            "PEA_M": 26.3,
            "Ocupados_M": 23.8,
            "Desocupados_M": 2.1,
        }
        ok = ind.sanity_check(resultado, "Anual 2025")
        assert ok is True

    def test_sanity_check_pea_inflada(self):
        """PEA > 40M debe disparar alerta."""
        config = ConfigGEIH(anio=2025, n_meses=12)
        ind = IndicadoresLaborales(config=config)
        resultado = {
            "TD_%": 8.9,
            "TGP_%": 64.3,
            "TO_%": 58.6,
            "PET_M": 400.0,
            "PEA_M": 56.0,
            "Ocupados_M": 50.0,
            "Desocupados_M": 6.0,
        }
        ok = ind.sanity_check(resultado, "Anual 2025")
        assert ok is False

    def test_sanity_check_2026_sin_ref(self):
        """2026 sin referencia DANE → no falla, solo advierte."""
        config = ConfigGEIH(anio=2026, n_meses=3)
        ind = IndicadoresLaborales(config=config)
        resultado = {
            "TD_%": 10.0,
            "TGP_%": 65.0,
            "TO_%": 58.0,
            "PET_M": 40.0,
            "PEA_M": 26.0,
            "Ocupados_M": 23.5,
            "Desocupados_M": 2.5,
        }
        # No debe lanzar excepción aunque no haya ref DANE
        ok = ind.sanity_check(resultado, "Trimestre 2026")
        assert ok is True  # PEA < 40M → pasa el check de seguridad


class TestIndicadoresGoldenSet:
    """Tests con el golden set sintético."""

    def test_td_golden(self, golden_set, config_2025):
        """TD del golden set debe coincidir con el valor esperado."""
        from geih.preparador import PreparadorGEIH
        from tests.generar_golden_set import GOLDEN_EXPECTED

        prep = PreparadorGEIH(config=config_2025)
        df = prep.preparar_base(golden_set)

        ind = IndicadoresLaborales(config=config_2025)
        r = ind.calcular(df)

        # Con FEX uniforme, TD debe coincidir con la proporción del golden set
        td_esperada = GOLDEN_EXPECTED["td_pct"]
        assert r["TD_%"] == pytest.approx(td_esperada, abs=0.5)

    def test_tgp_golden(self, golden_set, config_2025):
        """TGP del golden set debe coincidir."""
        from geih.preparador import PreparadorGEIH
        from tests.generar_golden_set import GOLDEN_EXPECTED

        prep = PreparadorGEIH(config=config_2025)
        df = prep.preparar_base(golden_set)

        ind = IndicadoresLaborales(config=config_2025)
        r = ind.calcular(df)

        tgp_esperada = GOLDEN_EXPECTED["tgp_pct"]
        assert r["TGP_%"] == pytest.approx(tgp_esperada, abs=0.5)
