"""
tests/test_paridad_golden.py — Tests de paridad binaria contra el golden set.

REGLA 1 DEL PLAYBOOK: la lógica legacy manda. Cualquier refactor de los
nudos críticos (config, preparador, utils, informalidad, indicadores)
DEBE producir los mismos números que la versión legacy sobre el golden set.

ESTRATEGIA
──────────
- tests/golden_set.parquet    : microdataset sintético versionado en git.
- tests/golden_expected.json  : valores esperados congelados (baseline).

Cuando un test falla, hay EXACTAMENTE dos rutas válidas:

  1. El refactor introdujo una regresión → revertir el commit culpable.
  2. El refactor CORRIGE un bug de la lógica legacy → actualizar el
     valor esperado regenerando golden_expected.json en el MISMO
     commit, documentando la razón en CHANGELOG.md.

Jamás "ajustar" silenciosamente un valor esperado para que pase un test.

BOOTSTRAP
─────────
La primera vez que se corre en un entorno nuevo, golden_expected.json
no existe y TODOS los tests de este archivo se skipean. Para crear el
baseline:

    python tests/generar_golden_expected.py

Eso escribe el JSON. Luego los tests ejecutan contra esos valores.

EJECUCIÓN
─────────
    pytest -m paridad                        # solo los tests de paridad
    pytest tests/test_paridad_golden.py -v   # con verbose y stack completo

Autor: Néstor Enrique Forero Herrera
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
AQUI = Path(__file__).parent
GOLDEN_SET = AQUI / "golden_set.parquet"
GOLDEN_EXPECTED = AQUI / "golden_expected.json"

# Tolerancias:
# - REL_TOL absorbe ruido de punto flotante entre versiones de pandas/numpy.
# - ABS_TOL protege cuando el valor esperado es cercano a 0.
REL_TOL = 1e-6
ABS_TOL = 1e-9


# ─────────────────────────────────────────────────────────────
# MODULE-LEVEL SKIP si no hay baseline
# ─────────────────────────────────────────────────────────────
pytestmark = pytest.mark.skipif(
    not GOLDEN_EXPECTED.exists(),
    reason=(
        f"{GOLDEN_EXPECTED.name} no existe. Ejecute primero: "
        "python tests/generar_golden_expected.py"
    ),
)


# ─────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def expected() -> dict:
    """Carga el JSON de valores esperados congelados."""
    return json.loads(GOLDEN_EXPECTED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def df_preparado() -> pd.DataFrame:
    """Dataframe GEIH preparado listo para cualquier indicador."""
    from geih import ConfigGEIH, PreparadorGEIH

    raw = pd.read_parquet(GOLDEN_SET)
    config = ConfigGEIH(anio=2025, n_meses=12)
    prep = PreparadorGEIH(config=config)
    df = prep.preparar_base(raw)
    if hasattr(prep, "agregar_variables_derivadas"):
        df = prep.agregar_variables_derivadas(df)
    return df


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _assert_paridad(actual: float, expected_val: float, nombre: str) -> None:
    """Aserción con mensaje claro en caso de regresión."""
    if not math.isclose(actual, expected_val, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        diff_abs = abs(actual - expected_val)
        diff_rel = diff_abs / (abs(expected_val) or 1)
        pytest.fail(
            f"\n  REGRESIÓN DETECTADA en {nombre}:\n"
            f"    esperado : {expected_val!r}\n"
            f"    obtenido : {actual!r}\n"
            f"    diff abs : {diff_abs:.2e}\n"
            f"    diff rel : {diff_rel:.2e}  (tolerancia: {REL_TOL:.0e})\n"
            f"\n"
            f"  ACCIONES VÁLIDAS:\n"
            f"    1) Si el refactor introdujo un bug → revertir el commit.\n"
            f"    2) Si corrige la lógica legacy deliberadamente →\n"
            f"       regenerar golden_expected.json Y documentar en CHANGELOG.md\n"
            f"       EN EL MISMO COMMIT.\n"
        )


def _extraer(dic: dict, clave: str):
    """Obtiene un valor esperado o skipea si aún no está en el baseline."""
    if clave not in dic:
        pytest.skip(
            f"'{clave}' no está en golden_expected.json. "
            f"Regenere con: python tests/generar_golden_expected.py"
        )
    return dic[clave]


# ─────────────────────────────────────────────────────────────
# TESTS — INDICADORES LABORALES FUNDAMENTALES
# ─────────────────────────────────────────────────────────────
@pytest.mark.paridad
def test_paridad_td(df_preparado, expected):
    """Tasa de desempleo: paridad binaria con el baseline."""
    from geih import ConfigGEIH, IndicadoresLaborales

    r = IndicadoresLaborales(config=ConfigGEIH(anio=2025)).calcular(df_preparado)
    _assert_paridad(r["TD_%"], _extraer(expected, "indicadores.TD_%"), "TD_%")


@pytest.mark.paridad
def test_paridad_tgp(df_preparado, expected):
    """Tasa global de participación: paridad binaria con el baseline."""
    from geih import ConfigGEIH, IndicadoresLaborales

    r = IndicadoresLaborales(config=ConfigGEIH(anio=2025)).calcular(df_preparado)
    _assert_paridad(r["TGP_%"], _extraer(expected, "indicadores.TGP_%"), "TGP_%")


@pytest.mark.paridad
def test_paridad_to(df_preparado, expected):
    """Tasa de ocupación: paridad binaria con el baseline."""
    from geih import ConfigGEIH, IndicadoresLaborales

    r = IndicadoresLaborales(config=ConfigGEIH(anio=2025)).calcular(df_preparado)
    _assert_paridad(r["TO_%"], _extraer(expected, "indicadores.TO_%"), "TO_%")


@pytest.mark.paridad
def test_paridad_pea(df_preparado, expected):
    """PEA en millones: paridad binaria con el baseline."""
    from geih import ConfigGEIH, IndicadoresLaborales

    r = IndicadoresLaborales(config=ConfigGEIH(anio=2025)).calcular(df_preparado)
    _assert_paridad(r["PEA_M"], _extraer(expected, "indicadores.PEA_M"), "PEA_M")


# ─────────────────────────────────────────────────────────────
# TESTS — ÍNDICES COMPUESTOS
# ─────────────────────────────────────────────────────────────
@pytest.mark.paridad
def test_paridad_gini(df_preparado, expected):
    """Coeficiente de Gini: paridad binaria con el baseline."""
    from geih import ConfigGEIH, IndicesCompuestos

    g = IndicesCompuestos(config=ConfigGEIH(anio=2025)).gini(df_preparado)
    _assert_paridad(g, _extraer(expected, "indices.gini"), "gini")


# ─────────────────────────────────────────────────────────────
# TESTS — BRECHA DE GÉNERO
# ─────────────────────────────────────────────────────────────
@pytest.mark.paridad
def test_paridad_brecha_genero(df_preparado, expected):
    """Brecha salarial de género: paridad binaria con el baseline."""
    from geih import BrechaGenero

    r = BrechaGenero().calcular(df_preparado)
    val = r.get("brecha_%") or r.get("brecha_pct") if isinstance(r, dict) else None
    if val is None:
        pytest.skip("BrechaGenero.calcular() no expone 'brecha_%' en este layout")

    _assert_paridad(val, _extraer(expected, "brecha_genero.brecha_%"), "brecha_genero.brecha_%")


# ─────────────────────────────────────────────────────────────
# TESTS — INTEGRIDAD DEL GOLDEN SET
# ─────────────────────────────────────────────────────────────
@pytest.mark.paridad
def test_integridad_golden_set(expected):
    """Verifica que el golden set no se modificó sin actualizar baseline.

    Si n_filas del parquet cambia, alguien sobrescribió golden_set.parquet
    sin regenerar golden_expected.json. Ese desincronismo es un bug de
    procedimiento y debe marcarse como tal.
    """
    raw = pd.read_parquet(GOLDEN_SET)
    n_filas_esperado = _extraer(expected, "dataset.n_filas")
    assert len(raw) == n_filas_esperado, (
        f"\n  golden_set.parquet cambió sin actualizar baseline:\n"
        f"    filas actuales   : {len(raw)}\n"
        f"    filas esperadas  : {n_filas_esperado}\n"
        f"\n"
        f"  Si la modificación fue intencional, regenere:\n"
        f"    python tests/generar_golden_expected.py\n"
    )
