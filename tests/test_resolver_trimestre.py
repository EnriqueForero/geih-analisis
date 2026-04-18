"""
tests/test_resolver_trimestre.py — Blindaje del parser de etiquetas
de trimestre del plan IT1 v2.

Cubre los 4 formatos observados en el Excel oficial del DANE:

    1. "Dic 25 - feb 26"     (con año embebido en ambos extremos)
    2. "Nov 25 - ene 26"     (cruza de año con año embebido)
    3. "Ene - mar"           (sin año, requiere ano_ancla)
    4. "Dic - feb"           (cruza de año, sin año, requiere ano_ancla)

Y el formato mensual de 'Grandes dominios':

    5. "Feb"                 (un solo mes)
    6. "Dic"                 (un solo mes)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from geih.replicacion_dane_common import (
    ResolvedTrimestre,
    normalizar_texto,
)

# ═════════════════════════════════════════════════════════════════════
# Test 1: los 4 formatos observados
# ═════════════════════════════════════════════════════════════════════


class TestParseo4Formatos:
    """Cubre los 4 formatos de etiqueta observados en el DANE."""

    def test_dic25_feb26_devuelve_3_meses_correctos(self):
        p = ResolvedTrimestre.parsear_etiqueta("Dic 25 - feb 26")
        assert p.meses == [(2025, 12), (2026, 1), (2026, 2)]
        assert p.es_mensual is False
        assert p.n_meses == 3

    def test_nov25_ene26_cruza_ano(self):
        p = ResolvedTrimestre.parsear_etiqueta("Nov 25 - ene 26")
        assert p.meses == [(2025, 11), (2025, 12), (2026, 1)]

    def test_ene_mar_requiere_ano_ancla(self):
        # Sin ancla debe fallar
        with pytest.raises(ValueError, match="ano_ancla"):
            ResolvedTrimestre.parsear_etiqueta("Ene - mar")
        # Con ancla 2025
        p = ResolvedTrimestre.parsear_etiqueta("Ene - mar", ano_ancla=2025)
        assert p.meses == [(2025, 1), (2025, 2), (2025, 3)]

    def test_dic_feb_cruza_ano_con_ancla(self):
        """'Dic - feb' sin año: se infiere que cruza de año.
        Con ancla 2026 debe ser Dic 2025, Ene 2026, Feb 2026."""
        p = ResolvedTrimestre.parsear_etiqueta("Dic - feb", ano_ancla=2026)
        assert p.meses == [(2025, 12), (2026, 1), (2026, 2)]

    def test_mayusculas_irrelevantes(self):
        """El parser debe ser case-insensitive."""
        a = ResolvedTrimestre.parsear_etiqueta("dic 25 - feb 26")
        b = ResolvedTrimestre.parsear_etiqueta("DIC 25 - FEB 26")
        c = ResolvedTrimestre.parsear_etiqueta("Dic 25 - feb 26")
        assert a.meses == b.meses == c.meses


# ═════════════════════════════════════════════════════════════════════
# Test 2: formato mensual (Grandes dominios)
# ═════════════════════════════════════════════════════════════════════


class TestParseoMensual:
    """Parseo de etiquetas mensuales de la hoja 'Grandes dominios'."""

    def test_feb_un_solo_mes(self):
        p = ResolvedTrimestre.parsear_etiqueta("Feb", ano_ancla=2026)
        assert p.meses == [(2026, 2)]
        assert p.es_mensual is True
        assert p.n_meses == 1

    def test_dic_un_solo_mes(self):
        p = ResolvedTrimestre.parsear_etiqueta("Dic", ano_ancla=2025)
        assert p.meses == [(2025, 12)]
        assert p.es_mensual is True

    def test_los_12_meses(self):
        """Los 12 meses deben parsearse correctamente."""
        abrev = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        for i, ab in enumerate(abrev, 1):
            p = ResolvedTrimestre.parsear_etiqueta(ab, ano_ancla=2026)
            assert p.meses == [(2026, i)], f"{ab} debe ser mes {i}, got {p.meses}"

    def test_mes_invalido_falla(self):
        with pytest.raises(ValueError, match="no reconocido|no reconocido"):
            ResolvedTrimestre.parsear_etiqueta("Xxx", ano_ancla=2026)


# ═════════════════════════════════════════════════════════════════════
# Test 3: propiedades del PeriodoMovil
# ═════════════════════════════════════════════════════════════════════


class TestPeriodoMovil:
    def test_etiqueta_corta_trimestre(self):
        p = ResolvedTrimestre.parsear_etiqueta("Dic 25 - feb 26")
        # Formato 'dic25_feb26' para nombres de archivo
        assert p.etiqueta_corta == "dic25_feb26"

    def test_mes_inicial_y_final(self):
        p = ResolvedTrimestre.parsear_etiqueta("Dic 25 - feb 26")
        assert p.mes_inicial == (2025, 12)
        assert p.mes_final == (2026, 2)


# ═════════════════════════════════════════════════════════════════════
# Test 4: integración contra el Excel real si está presente
# ═════════════════════════════════════════════════════════════════════

EXCEL_OFICIAL = Path("/mnt/user-data/uploads/1776399661404_anex-GEIHEISS-dic2025-feb2026.xlsx")


@pytest.mark.skipif(
    not EXCEL_OFICIAL.exists(),
    reason="Excel oficial no disponible en esta corrida",
)
class TestIntegracionExcelReal:
    """Tests que requieren el Excel oficial como insumo."""

    def test_total_nacional_resuelve_ultimo_trimestre(self):
        r = ResolvedTrimestre.desde_excel(EXCEL_OFICIAL, hoja="Total nacional")
        assert r.periodo.etiqueta_original == "Dic 25 - feb 26"
        assert r.periodo.meses == [(2025, 12), (2026, 1), (2026, 2)]

    def test_grandes_dominios_resuelve_mes_final(self):
        r = ResolvedTrimestre.desde_excel(EXCEL_OFICIAL, hoja="Grandes dominios ")
        assert r.periodo.es_mensual is True
        assert r.periodo.meses == [(2026, 2)]

    def test_tnal_sexo_autodetecta_fila_meses(self):
        """En 'Seguridad social Tnal sexo' la fila de meses no es 13."""
        r = ResolvedTrimestre.desde_excel(
            EXCEL_OFICIAL,
            hoja="Seguridad social Tnal sexo",
        )
        assert r.periodo.meses == [(2025, 12), (2026, 1), (2026, 2)]


# ═════════════════════════════════════════════════════════════════════
# Test 5: normalizar_texto
# ═════════════════════════════════════════════════════════════════════


class TestNormalizarTexto:
    def test_tildes(self):
        assert normalizar_texto("Básica primaria") == "basica primaria"
        assert normalizar_texto("Educación") == "educacion"

    def test_simbolos_decorativos(self):
        """El DANE marca con ^, *, ^^ ciertas categorías."""
        assert normalizar_texto("Básica secundaria^") == "basica secundaria"
        assert normalizar_texto("Educación media*^") == "educacion media"
        assert normalizar_texto("Técnica profesional^^") == "tecnica profesional"

    def test_espacios_colapsados(self):
        assert normalizar_texto("  13 Ciudades   y   A.M.  ") == "13 ciudades y a.m."

    def test_none_y_nan(self):
        import numpy as np

        assert normalizar_texto(None) == ""
        assert normalizar_texto(np.nan) == ""

    def test_idempotente(self):
        a = normalizar_texto("Régimen contributivo")
        b = normalizar_texto(a)
        assert a == b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
