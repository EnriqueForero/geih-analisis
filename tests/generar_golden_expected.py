# -*- coding: utf-8 -*-
"""
tests/generar_golden_expected.py — Genera el baseline de valores esperados.

Procesa tests/golden_set.parquet con la versión ACTUAL de la librería y
escribe tests/golden_expected.json con los valores de los indicadores.

USO NORMAL
──────────
Este script se corre EXACTAMENTE en dos ocasiones:

  1. BOOTSTRAP: una única vez al inicio, para crear el baseline inicial.

         python tests/generar_golden_expected.py

  2. CORRECCIÓN DELIBERADA: cuando un refactor CORRIGE un bug de la
     lógica legacy y los valores esperados deben actualizarse.

         python tests/generar_golden_expected.py

     Luego documentar en CHANGELOG.md qué cambió y por qué.

NO SE USA para "pasar los tests" después de un refactor que rompió la
paridad por error. En ese caso el refactor está mal y debe revertirse.

PROCEDIMIENTO
─────────────
Al correrlo, imprime:
  - Los valores que capturó (para revisión humana antes de commit).
  - Metadata (versión de librería, número de filas procesadas).
  - Archivo escrito en tests/golden_expected.json.

Después del bootstrap, ese archivo se commitea a git y se vuelve la
verdad de referencia para test_paridad_golden.py.

Autor: Néstor Enrique Forero Herrera
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


AQUI = Path(__file__).parent
GOLDEN_SET = AQUI / "golden_set.parquet"
GOLDEN_EXPECTED = AQUI / "golden_expected.json"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _num(x):
    """Coacciona a tipo serializable en JSON (float nativo)."""
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return x


def _capturar(baseline: dict, clave: str, fn, warnings: list):
    """Ejecuta fn() y guarda el resultado en baseline bajo 'clave'.

    Si la función falla, se registra el warning pero el baseline sigue
    generándose (el indicador quedará ausente y el test correspondiente
    skipeará hasta que se repare).
    """
    try:
        valor = fn()
        if valor is not None:
            baseline[clave] = _num(valor)
            print(f"  ✅ {clave:40s} = {baseline[clave]!r}")
        else:
            warnings.append(f"{clave}: fn() devolvió None")
    except Exception as e:
        warnings.append(f"{clave}: {type(e).__name__}: {e}")
        print(f"  ⚠️  {clave:40s} no capturado ({type(e).__name__})")


# ─────────────────────────────────────────────────────────────
# GENERACIÓN DEL BASELINE
# ─────────────────────────────────────────────────────────────
def generar_baseline() -> tuple[dict, list]:
    """Ejecuta la librería sobre el golden set y captura los valores.

    Returns:
        (baseline_dict, warnings_list)
    """
    if not GOLDEN_SET.exists():
        raise FileNotFoundError(
            f"No se encontró {GOLDEN_SET}. El golden set debe existir en "
            f"tests/ y estar versionado en git."
        )

    from geih import (
        ConfigGEIH,
        PreparadorGEIH,
        IndicadoresLaborales,
        IndicesCompuestos,
        BrechaGenero,
        __version__,
    )

    print(f"\n→ Cargando golden set: {GOLDEN_SET}")
    raw = pd.read_parquet(GOLDEN_SET)
    print(f"  {len(raw):,} filas, {raw.shape[1]} columnas")

    print(f"\n→ Preparando base con ConfigGEIH(anio=2025, n_meses=12)")
    config = ConfigGEIH(anio=2025, n_meses=12)
    prep = PreparadorGEIH(config=config)
    df = prep.preparar_base(raw)
    if hasattr(prep, "agregar_variables_derivadas"):
        df = prep.agregar_variables_derivadas(df)
    print(f"  {len(df):,} filas preparadas, {df.shape[1]} columnas")

    baseline: dict = {
        "_meta": {
            "version_libreria": __version__,
            "n_filas_raw": int(len(raw)),
            "n_filas_preparado": int(len(df)),
            "n_columnas_preparado": int(df.shape[1]),
            "generado_con": "tests/generar_golden_expected.py",
        },
        "dataset.n_filas": int(len(raw)),
    }

    warnings: list = []
    print(f"\n→ Capturando valores de indicadores:")

    # ── Indicadores laborales fundamentales ──────────────────
    ind = IndicadoresLaborales(config=config).calcular(df)
    for clave in ("TD_%", "TGP_%", "TO_%", "PEA_M"):
        if clave in ind:
            _capturar(baseline, f"indicadores.{clave}",
                      lambda k=clave: ind[k], warnings)
        else:
            warnings.append(f"indicadores.{clave}: no presente en resultado")

    # ── Índices compuestos ───────────────────────────────────
    _capturar(
        baseline, "indices.gini",
        lambda: IndicesCompuestos(config=config).gini(df),
        warnings,
    )

    # ── Brecha de género ─────────────────────────────────────
    def _extraer_brecha():
        r = BrechaGenero().calcular(df)
        if isinstance(r, dict):
            return r.get("brecha_%") or r.get("brecha_pct")
        return getattr(r, "brecha_%", None)

    _capturar(baseline, "brecha_genero.brecha_%", _extraer_brecha, warnings)

    return baseline, warnings


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main() -> int:
    print("═" * 65)
    print(f"  GENERADOR DE BASELINE — golden_expected.json")
    print("═" * 65)

    baseline, warnings = generar_baseline()

    # ── Serialización ────────────────────────────────────────
    GOLDEN_EXPECTED.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    n_claves = sum(1 for k in baseline if not k.startswith("_"))
    print(f"\n→ Archivo escrito: {GOLDEN_EXPECTED}")
    print(f"  Claves congeladas: {n_claves}")

    if warnings:
        print(f"\n⚠️  {len(warnings)} indicadores no se capturaron:")
        for w in warnings:
            print(f"     - {w}")
        print("   (Los tests correspondientes harán skip hasta que se reparen.)")

    print(f"\n" + "─" * 65)
    print("  SIGUIENTE PASO")
    print("─" * 65)
    print("  1. Revisar golden_expected.json: los números tienen sentido?")
    print("  2. git add tests/golden_expected.json")
    print("  3. git commit -m 'test(paridad): baseline inicial — bootstrap'")
    print("  4. Ejecutar: pytest -m paridad")
    print("─" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(main())
