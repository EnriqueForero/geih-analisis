# -*- coding: utf-8 -*-
"""Tests para geih.config — Configuración multi-año."""

import pytest
from geih.config import (
    ConfigGEIH, SMMLV_POR_ANIO, REF_DANE, SMMLV_2025,
    MESES_CARPETAS, REF_DANE_2025, MESES_NOMBRES,
    generar_carpetas_mensuales, generar_etiqueta_periodo,
)


class TestConfigGEIH:
    """Tests del dataclass ConfigGEIH."""

    def test_defaults_2025(self):
        """Config por defecto debe ser 2025, 12 meses."""
        c = ConfigGEIH()
        assert c.anio == 2025
        assert c.n_meses == 12
        assert c.smmlv == 1_423_500

    def test_smmlv_auto_seleccion(self):
        """SMMLV se auto-selecciona según el año."""
        c25 = ConfigGEIH(anio=2025)
        c26 = ConfigGEIH(anio=2026)
        assert c25.smmlv == SMMLV_POR_ANIO[2025]
        assert c26.smmlv == SMMLV_POR_ANIO[2026]
        assert c26.smmlv > c25.smmlv

    def test_smmlv_manual_override(self):
        """SMMLV manual tiene prioridad sobre auto-selección."""
        c = ConfigGEIH(anio=2025, smmlv=2_000_000)
        assert c.smmlv == 2_000_000

    def test_carpetas_mensuales_12(self):
        """12 meses genera 12 carpetas."""
        c = ConfigGEIH(anio=2025, n_meses=12)
        carpetas = c.carpetas_mensuales
        assert len(carpetas) == 12
        assert carpetas[0] == "Enero 2025"
        assert carpetas[-1] == "Diciembre 2025"

    def test_carpetas_mensuales_3(self):
        """3 meses genera solo 3 carpetas."""
        c = ConfigGEIH(anio=2026, n_meses=3)
        carpetas = c.carpetas_mensuales
        assert len(carpetas) == 3
        assert carpetas[0] == "Enero 2026"
        assert carpetas[-1] == "Marzo 2026"

    def test_carpetas_mensuales_1(self):
        """1 mes genera 1 carpeta."""
        c = ConfigGEIH(anio=2026, n_meses=1)
        assert len(c.carpetas_mensuales) == 1
        assert c.carpetas_mensuales[0] == "Enero 2026"

    def test_periodo_etiqueta_auto(self):
        """Etiqueta de período se genera automáticamente."""
        c12 = ConfigGEIH(anio=2025, n_meses=12)
        assert c12.periodo_etiqueta == "Enero – Diciembre 2025"

        c3 = ConfigGEIH(anio=2026, n_meses=3)
        assert c3.periodo_etiqueta == "Enero – Marzo 2026"

        c1 = ConfigGEIH(anio=2026, n_meses=1)
        assert c1.periodo_etiqueta == "Enero 2026"

    def test_referencia_dane_2025(self):
        """2025 tiene referencia DANE disponible."""
        c = ConfigGEIH(anio=2025)
        ref = c.referencia_dane
        assert ref is not None
        assert ref.td_anual_pct == 8.9

    def test_referencia_dane_2026_none(self):
        """2026 no tiene referencia DANE (aún no publicada)."""
        c = ConfigGEIH(anio=2026)
        assert c.referencia_dane is None

    def test_validacion_n_meses_0(self):
        """n_meses=0 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="n_meses=0"):
            ConfigGEIH(n_meses=0)

    def test_validacion_n_meses_13(self):
        """n_meses=13 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="n_meses=13"):
            ConfigGEIH(n_meses=13)

    def test_validacion_anio_2010(self):
        """anio=2010 debe lanzar ValueError (antes del marco 2018)."""
        with pytest.raises(ValueError, match="anio=2010"):
            ConfigGEIH(anio=2010)

    def test_validacion_smmlv_bajo(self):
        """SMMLV < 100,000 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="parece demasiado bajo"):
            ConfigGEIH(smmlv=50_000)


class TestRetrocompatibilidad:
    """Verifica que los símbolos antiguos siguen funcionando."""

    def test_smmlv_2025_existe(self):
        assert SMMLV_2025 == 1_423_500

    def test_ref_dane_2025_existe(self):
        assert REF_DANE_2025 is not None
        assert REF_DANE_2025 == REF_DANE[2025]

    def test_meses_carpetas_existe(self):
        assert len(MESES_CARPETAS) == 12
        assert MESES_CARPETAS[0] == "Enero 2025"


class TestFuncionesAuxiliares:
    """Tests de generar_carpetas_mensuales y generar_etiqueta_periodo."""

    def test_generar_carpetas_basico(self):
        result = generar_carpetas_mensuales(2027, 6)
        assert len(result) == 6
        assert result[0] == "Enero 2027"
        assert result[-1] == "Junio 2027"

    def test_generar_carpetas_clamp(self):
        """n_meses se clampea a [1, 12]."""
        assert len(generar_carpetas_mensuales(2025, 0)) == 1   # clamp a 1
        assert len(generar_carpetas_mensuales(2025, 99)) == 12  # clamp a 12

    def test_etiqueta_1_mes(self):
        assert generar_etiqueta_periodo(2026, 1) == "Enero 2026"

    def test_etiqueta_12_meses(self):
        assert generar_etiqueta_periodo(2025, 12) == "Enero – Diciembre 2025"
