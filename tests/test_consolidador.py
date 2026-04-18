"""Tests para geih.consolidador — Lógica de consolidación."""

import pandas as pd
import pytest

from geih.consolidador import ConsolidadorGEIH


class TestUnirSinDuplicados:
    """Tests de _unir_sin_duplicados (LEFT JOIN sin columnas repetidas)."""

    def test_no_multiplica_filas(self, df_merge_izq, df_merge_der):
        """LEFT JOIN no debe producir más filas que el DataFrame izquierdo."""
        llaves = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
        resultado = ConsolidadorGEIH._unir_sin_duplicados(df_merge_izq, df_merge_der, llaves)
        assert len(resultado) == len(df_merge_izq)

    def test_preserva_universo(self, df_merge_izq, df_merge_der):
        """LEFT JOIN debe preservar todas las filas del DataFrame izquierdo."""
        llaves = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
        resultado = ConsolidadorGEIH._unir_sin_duplicados(df_merge_izq, df_merge_der, llaves)
        # D3 no está en df_der → debe tener NaN en COL_B
        d3 = resultado[resultado["DIRECTORIO"] == "D3"]
        assert len(d3) == 1
        assert pd.isna(d3["COL_B"].iloc[0])

    def test_elimina_columnas_duplicadas(self, df_merge_izq, df_merge_der):
        """No debe traer COL_A del df_der (ya existe en df_izq)."""
        llaves = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
        resultado = ConsolidadorGEIH._unir_sin_duplicados(df_merge_izq, df_merge_der, llaves)
        # No debe haber COL_A_x ni COL_A_y
        assert "COL_A_x" not in resultado.columns
        assert "COL_A_y" not in resultado.columns
        # COL_A original se preserva
        assert "COL_A" in resultado.columns

    def test_trae_columnas_nuevas(self, df_merge_izq, df_merge_der):
        """Debe traer COL_B (nueva) del df_der."""
        llaves = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
        resultado = ConsolidadorGEIH._unir_sin_duplicados(df_merge_izq, df_merge_der, llaves)
        assert "COL_B" in resultado.columns
        # D1 debe tener COL_B=100
        d1 = resultado[resultado["DIRECTORIO"] == "D1"]
        assert d1["COL_B"].iloc[0] == 100


class TestNormalizar:
    """Tests de _normalizar (comparación sin tildes)."""

    def test_tildes(self):
        assert ConsolidadorGEIH._normalizar("Migración.CSV") == "migracion.csv"

    def test_mayusculas(self):
        assert ConsolidadorGEIH._normalizar("OCUPADOS.CSV") == "ocupados.csv"

    def test_mixto(self):
        result = ConsolidadorGEIH._normalizar(
            "Características generales, seguridad social en salud y educación.CSV"
        )
        assert "caracteristicas" in result
        assert "educacion" in result

    def test_sin_tildes_ya(self):
        assert ConsolidadorGEIH._normalizar("ocupados.csv") == "ocupados.csv"


class TestInferirNumeroMes:
    """Tests de _inferir_numero_mes."""

    def test_enero(self):
        assert ConsolidadorGEIH._inferir_numero_mes("Enero 2025") == 1

    def test_diciembre(self):
        assert ConsolidadorGEIH._inferir_numero_mes("Diciembre 2026") == 12

    def test_marzo_con_espacios(self):
        assert ConsolidadorGEIH._inferir_numero_mes("  Marzo 2025  ") == 3

    def test_invalido(self):
        with pytest.raises(ValueError, match="No se pudo inferir"):
            ConsolidadorGEIH._inferir_numero_mes("InvalidMonth 2025")
