# -*- coding: utf-8 -*-
"""
tests/conftest.py — Fixtures compartidos para pytest.

Provee el golden set y la configuración base para todos los tests.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Agregar la ruta del paquete al path (para que funcione sin pip install)
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="session")
def golden_set():
    """Genera o carga el golden set sintético.

    scope='session' = se genera una sola vez para todos los tests.
    """
    from tests.generar_golden_set import generar_golden_set
    ruta = Path(__file__).parent / "golden_set.parquet"
    if not ruta.exists():
        generar_golden_set(ruta_salida=str(ruta))
    return pd.read_parquet(ruta)


@pytest.fixture(scope="session")
def config_2025():
    """ConfigGEIH para año 2025, 12 meses."""
    from geih.config import ConfigGEIH
    return ConfigGEIH(anio=2025, n_meses=12)


@pytest.fixture(scope="session")
def config_2026_parcial():
    """ConfigGEIH para año 2026, 3 meses."""
    from geih.config import ConfigGEIH
    return ConfigGEIH(anio=2026, n_meses=3)


@pytest.fixture
def df_simple():
    """DataFrame mínimo para tests de estadísticas ponderadas."""
    return pd.DataFrame({
        "valor": [100, 200, 300, 400, 500],
        "peso":  [1.0, 1.0, 1.0, 1.0, 1.0],
    })


@pytest.fixture
def df_pesos_desiguales():
    """DataFrame con pesos desiguales para validar ponderación."""
    return pd.DataFrame({
        "valor": [100, 200, 300],
        "peso":  [10.0, 1.0, 1.0],
    })


@pytest.fixture
def df_merge_izq():
    """DataFrame izquierdo para tests de merge."""
    return pd.DataFrame({
        "DIRECTORIO": ["D1", "D2", "D3"],
        "SECUENCIA_P": ["S1", "S1", "S1"],
        "ORDEN": ["1", "2", "3"],
        "COL_A": [10, 20, 30],
    })


@pytest.fixture
def df_merge_der():
    """DataFrame derecho para tests de merge (subconjunto)."""
    return pd.DataFrame({
        "DIRECTORIO": ["D1", "D2"],
        "SECUENCIA_P": ["S1", "S1"],
        "ORDEN": ["1", "2"],
        "COL_A": [10, 20],        # duplicada → no debe traerse
        "COL_B": [100, 200],      # nueva → sí debe traerse
    })
