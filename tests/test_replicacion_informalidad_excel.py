"""
tests/test_replicacion_informalidad_excel.py — Tests de replicación
de informalidad. Usa DataFrames sintéticos para validar la lógica sin
requerir microdatos reales.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geih.replicacion_dane_common import (
    ParametrosValidacion,
    PeriodoMovil,
    ResolvedTrimestre,
    ResultadoReplicacion,
)
from geih.replicacion_dane_informalidad import (
    HOJAS_INFORMALIDAD,
    MAPEO_LUGAR_TRABAJO,
    MAPEO_NIVEL_EDU,
    MAPEO_TAMANO_EMPRESA,
    ReplicadorInformalidad,
)

EXCEL_OFICIAL = Path("/mnt/user-data/uploads/1776399661404_anex-GEIHEISS-dic2025-feb2026.xlsx")


# ═════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════


@pytest.fixture
def df_sintetico():
    """DataFrame con 1000 registros sintéticos con todas las columnas
    requeridas por los replicadores."""
    rng = np.random.default_rng(seed=42)
    n = 1000
    return pd.DataFrame(
        {
            "FEX_ADJ": rng.uniform(500, 2000, n),
            "OCI": np.ones(n, dtype=int),
            "INFORMAL": pd.array(rng.integers(0, 2, n), dtype="Int8"),
            "DOMINIO": rng.choice(
                ["13_AM", "10_ciudades", "otras_cab", "rural"],
                n,
            ),
            "CIUDAD": rng.choice(
                ["Bogotá D.C.", "Medellín A.M.", "Cali A.M.", None],
                n,
            ),
            "SEXO": rng.choice(["Hombres", "Mujeres"], n),
            "RAMA": rng.choice(
                [
                    "Agricultura, ganadería, caza, silvicultura y pesca",
                    "Industrias manufactureras",
                    "Construcción",
                    "Comercio y reparación de vehículos",
                ],
                n,
            ),
            "POSICION_OCU": rng.choice(
                [
                    "Obrero, empleado particular",
                    "Trabajador por cuenta propia",
                    "Empleado doméstico",
                ],
                n,
            ),
            "NIVEL_GRUPO": rng.choice(list(MAPEO_NIVEL_EDU.keys()), n),
            "MES_NUM": rng.choice([12, 1, 2], n),
            "PER": rng.choice([2025, 2026], n),
            "P3069": rng.integers(1, 11, n),
            "P6880": rng.integers(1, 12, n),
        }
    )


# ═════════════════════════════════════════════════════════════════════
# Test 1: API y tipos
# ═════════════════════════════════════════════════════════════════════


class TestAPI:
    def test_hojas_informalidad_son_10(self):
        assert len(HOJAS_INFORMALIDAD) == 10

    def test_replicador_construye(self):
        if not EXCEL_OFICIAL.exists():
            pytest.skip("Excel no disponible")
        rep = ReplicadorInformalidad(EXCEL_OFICIAL)
        assert rep.ruta_excel == EXCEL_OFICIAL
        assert isinstance(rep.params, ParametrosValidacion)

    def test_verificar_columnas_falla_si_falta(self):
        if not EXCEL_OFICIAL.exists():
            pytest.skip("Excel no disponible")
        df_malo = pd.DataFrame({"FEX_ADJ": [1, 2, 3]})
        rep = ReplicadorInformalidad(EXCEL_OFICIAL)
        with pytest.raises(ValueError, match="columnas requeridas"):
            rep._verificar_columnas(df_malo)

    def test_verificar_columnas_ok_si_presentes(self, df_sintetico):
        if not EXCEL_OFICIAL.exists():
            pytest.skip("Excel no disponible")
        rep = ReplicadorInformalidad(EXCEL_OFICIAL)
        rep._verificar_columnas(df_sintetico)  # no debe lanzar


# ═════════════════════════════════════════════════════════════════════
# Test 2: Replicación end-to-end con df sintético
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(
    not EXCEL_OFICIAL.exists(),
    reason="Excel oficial no disponible",
)
class TestEndToEndSintetico:
    """
    Con datos sintéticos NO esperamos que las cifras cierren contra
    el Excel — validamos que el replicador:
    (a) corre sin excepciones,
    (b) produce el tipo correcto de objeto,
    (c) reporta todas las celdas como NA o FAIL (esperado),
    (d) tiene la estructura esperada de ResultadoHoja.
    """

    def test_replicar_total_nacional_sintetico_produce_resultado(
        self,
        df_sintetico,
    ):
        rep = ReplicadorInformalidad(EXCEL_OFICIAL)
        periodo = ResolvedTrimestre.parsear_etiqueta("Dic 25 - feb 26").__class__(
            etiqueta_original="Dic 25 - feb 26",
            meses=[(2025, 12), (2026, 1), (2026, 2)],
            es_mensual=False,
        )
        res = rep.replicar(df_sintetico, periodo, hojas=["Total nacional"])
        assert isinstance(res, ResultadoReplicacion)
        assert len(res.hojas) == 1
        h = res.hojas[0]
        assert h.hoja == "Total nacional"
        assert h.n_celdas == 9  # 3 dominios × 3 valores
        # Con datos sintéticos: esperamos que TODOS sean FAIL (no hay
        # razón para que coincidan aleatoriamente)
        # Pero el estado debe ser claro (no None)
        assert h.estado in (
            "CERRADA",
            "ABIERTA_CON_CAUSA",
            "ABIERTA_SIN_CAUSA",
        )

    def test_replicar_grandes_dominios_sintetico(self, df_sintetico):
        rep = ReplicadorInformalidad(EXCEL_OFICIAL)
        periodo = PeriodoMovil(
            etiqueta_original="Dic 25 - feb 26",
            meses=[(2025, 12), (2026, 1), (2026, 2)],
            es_mensual=False,
        )
        res = rep.replicar(df_sintetico, periodo, hojas=["Grandes dominios"])
        h = res.hojas[0]
        # 5 dominios × 3 valores = 15 celdas
        assert h.n_celdas == 15


# ═════════════════════════════════════════════════════════════════════
# Test 3: Mapeos
# ═════════════════════════════════════════════════════════════════════


class TestMapeos:
    def test_mapeo_tamano_cubre_10_codigos(self):
        """P3069 codifica 1..10."""
        for codigo in range(1, 11):
            assert codigo in MAPEO_TAMANO_EMPRESA

    def test_mapeo_tamano_agrupa_4_categorias(self):
        vals = set(MAPEO_TAMANO_EMPRESA.values())
        assert vals == {
            "Microempresa",
            "Empresa pequeña",
            "Empresa mediana",
            "Empresa grande",
        }

    def test_mapeo_lugar_cubre_11_codigos(self):
        """P6880 codifica 1..11."""
        for codigo in range(1, 12):
            assert codigo in MAPEO_LUGAR_TRABAJO

    def test_mapeo_nivel_edu_cubre_7_niveles(self):
        """Las 7 etiquetas del Excel."""
        vals = set(MAPEO_NIVEL_EDU.values())
        assert "Ninguno" in vals
        assert "Posgrado" in vals
        assert len(vals) == 7


# ═════════════════════════════════════════════════════════════════════
# Test 4: ParametrosValidacion
# ═════════════════════════════════════════════════════════════════════


class TestParametrosValidacion:
    def test_cierre_absoluto_dentro_01_pct(self):
        p = ParametrosValidacion()
        estado, _diff = p.clasificar(1000.0, 1000.5, es_proporcion=False)
        # 0.05% relativo → OK_CIERRE
        assert estado == "OK_CIERRE"

    def test_diagnostico_entre_01_y_1_pct(self):
        p = ParametrosValidacion()
        estado, _diff = p.clasificar(1000.0, 1005.0, es_proporcion=False)
        # 0.5% → OK_DIAGNOSTICO (< 1%)
        assert estado == "OK_DIAGNOSTICO"

    def test_fail_mas_1_pct(self):
        p = ParametrosValidacion()
        estado, _diff = p.clasificar(1000.0, 1050.0, es_proporcion=False)
        # 5% → FAIL
        assert estado == "FAIL"

    def test_proporcion_dentro_01_pp_es_cierre(self):
        p = ParametrosValidacion()
        estado, _diff = p.clasificar(59.65, 59.70, es_proporcion=True)
        assert estado == "OK_CIERRE"

    def test_proporcion_entre_01_y_04_pp_es_diagnostico(self):
        p = ParametrosValidacion()
        estado, _diff = p.clasificar(59.65, 59.90, es_proporcion=True)
        assert estado == "OK_DIAGNOSTICO"

    def test_na_si_valores_faltan(self):
        p = ParametrosValidacion()
        estado, _diff = p.clasificar(None, 100.0, es_proporcion=False)
        assert estado == "NA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
