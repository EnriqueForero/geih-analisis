"""
tests/smoke_test.py — Smoke test del pipeline GEIH.

Ejecuta el pipeline completo sobre una muestra mínima (0.1% de la base
o el golden set) para validar que todo funciona antes de procesar
los 5 millones de registros (~10 segundos vs ~10 minutos).

CÓMO USAR EN EL NOTEBOOK — Insertar como Celda 0 antes del pipeline:

    # ══════════════════════════════════════════════════════════════
    # CELDA 0 · Smoke test (ejecutar ANTES del pipeline completo)
    # ══════════════════════════════════════════════════════════════
    import sys
    sys.path.insert(0, '/content/drive/MyDrive/ProColombia/GEIH')
    from tests.smoke_test import ejecutar_smoke_test
    ejecutar_smoke_test(ruta_base='/content/drive/MyDrive/ProColombia/GEIH')
    # Si imprime "✅ SMOKE TEST PASADO", es seguro correr el pipeline completo.
    # Si imprime "❌ SMOKE TEST FALLIDO", NO proceder.

También se puede ejecutar standalone:
    python tests/smoke_test.py

Autor: Néstor Enrique Forero Herrera
"""

import sys
import time
import traceback
from pathlib import Path
from typing import Optional


def ejecutar_smoke_test(
    ruta_base: Optional[str] = None,
    anio: int = 2025,
    n_meses: int = 12,
    muestra_n: int = 5_000,
) -> bool:
    """Ejecuta el pipeline completo sobre una muestra mínima.

    Args:
        ruta_base: Ruta al directorio GEIH. Si None, usa golden set.
        anio: Año para ConfigGEIH.
        n_meses: Meses para ConfigGEIH.
        muestra_n: Tamaño de la muestra (0 = usar golden set completo).

    Returns:
        True si todos los checks pasan, False si alguno falla.
    """
    inicio = time.time()
    errores = []

    print(f"\n{'=' * 65}")
    print(f"  🧪 SMOKE TEST — Pipeline GEIH {anio}")
    print(f"{'=' * 65}")

    # ── 1. Importar paquete ────────────────────────────────────
    try:
        from geih import (
            AnalisisCampesino,
            AnatomaSalario,
            BrechaGenero,
            CanalEmpleo,
            ConfigGEIH,
            DashboardSectoresProColombia,
            DistribucionIngresos,
            DuracionDesempleo,
            FormaPago,
            GraficoCurvaLorenz,
            IndicadoresLaborales,
            IndicesCompuestos,
            PreparadorGEIH,
            __version__,
        )

        print(f"  ✅ 1/7 Paquete importado (v{__version__})")
    except Exception as e:
        errores.append(f"Importación: {e}")
        print(f"  ❌ 1/7 Error importando paquete: {e}")
        _resultado_final(errores, inicio)
        return False

    # ── 2. Configuración ──────────────────────────────────────
    try:
        config = ConfigGEIH(anio=anio, n_meses=n_meses)
        assert config.smmlv > 100_000
        assert len(config.carpetas_mensuales) == n_meses
        print(f"  ✅ 2/7 ConfigGEIH OK (SMMLV=${config.smmlv:,})")
    except Exception as e:
        errores.append(f"Config: {e}")
        print(f"  ❌ 2/7 Error config: {e}")

    # ── 3. Cargar datos (golden set o muestra) ────────────────
    try:
        golden_path = Path(__file__).parent / "golden_set.parquet"
        if golden_path.exists():
            import pandas as pd

            df_raw = pd.read_parquet(golden_path)
            print(f"  ✅ 3/7 Golden set cargado ({len(df_raw):,} filas)")
        elif ruta_base:
            parquet = Path(ruta_base) / f"GEIH_{anio}_Consolidado.parquet"
            if parquet.exists():
                import pandas as pd

                df_raw = pd.read_parquet(parquet)
                if muestra_n > 0 and len(df_raw) > muestra_n:
                    df_raw = df_raw.sample(muestra_n, random_state=42)
                print(f"  ✅ 3/7 Muestra cargada ({len(df_raw):,} filas)")
            else:
                print("  ⚠️  3/7 No hay Parquet ni golden set — generando golden set...")
                from tests.generar_golden_set import generar_golden_set

                df_raw = generar_golden_set(ruta_salida=str(golden_path))
                print(f"  ✅ 3/7 Golden set generado ({len(df_raw):,} filas)")
        else:
            from tests.generar_golden_set import generar_golden_set

            df_raw = generar_golden_set(ruta_salida=str(golden_path))
            print(f"  ✅ 3/7 Golden set generado ({len(df_raw):,} filas)")
    except Exception as e:
        errores.append(f"Carga datos: {e}")
        print(f"  ❌ 3/7 Error cargando datos: {e}")
        _resultado_final(errores, inicio)
        return False

    # ── 4. Preparar datos ─────────────────────────────────────
    try:
        prep = PreparadorGEIH(config=config)
        df = prep.preparar_base(df_raw)
        df = prep.agregar_variables_derivadas(df)
        assert "FEX_ADJ" in df.columns
        assert "RAMA" in df.columns or "RAMA2D_R4" in df.columns
        print(f"  ✅ 4/7 Datos preparados ({df.shape[1]} columnas)")
    except Exception as e:
        errores.append(f"Preparación: {e}")
        print(f"  ❌ 4/7 Error preparando datos: {e}")
        traceback.print_exc()
        _resultado_final(errores, inicio)
        return False

    # ── 5. Indicadores fundamentales ──────────────────────────
    try:
        ind = IndicadoresLaborales(config=config)
        r = ind.calcular(df)
        assert "TD_%" in r
        assert "TGP_%" in r
        assert "TO_%" in r
        assert 0 < r["TD_%"] < 100
        assert 0 < r["TGP_%"] < 100
        assert r["PEA_M"] < 40  # no debe estar inflado
        print(
            f"  ✅ 5/7 Indicadores OK (TD={r['TD_%']:.1f}%, "
            f"TGP={r['TGP_%']:.1f}%, TO={r['TO_%']:.1f}%)"
        )
    except Exception as e:
        errores.append(f"Indicadores: {e}")
        print(f"  ❌ 5/7 Error indicadores: {e}")

    # ── 6. Módulos de análisis (subset) ───────────────────────
    modulos_ok = 0
    modulos_total = 0
    clases_test = [
        ("DistribucionIngresos", lambda: DistribucionIngresos(config=config).calcular(df)),
        ("BrechaGenero", lambda: BrechaGenero().calcular(df)),
        ("Gini", lambda: IndicesCompuestos(config=config).gini(df)),
        ("DuracionDesempleo", lambda: DuracionDesempleo(config=config).calcular(df)),
        ("DashboardSectores", lambda: DashboardSectoresProColombia(config=config).calcular(df)),
        ("AnatomaSalario", lambda: AnatomaSalario(config=config).resumen_nacional(df)),
        ("FormaPago", lambda: FormaPago(config=config).calcular(df)),
        ("CanalEmpleo", lambda: CanalEmpleo(config=config).calcular(df)),
        ("Campesino", lambda: AnalisisCampesino(config=config).calcular(df)),
    ]
    for nombre, fn in clases_test:
        modulos_total += 1
        try:
            # resultado = fn()
            fn()
            modulos_ok += 1
        except Exception as e:
            errores.append(f"{nombre}: {e}")

    if modulos_ok == modulos_total:
        print(f"  ✅ 6/7 {modulos_ok}/{modulos_total} módulos ejecutados sin error")
    else:
        print(
            f"  ⚠️  6/7 {modulos_ok}/{modulos_total} módulos OK "
            f"({modulos_total - modulos_ok} fallaron)"
        )

    # ── 7. Gráfico de prueba ──────────────────────────────────
    try:
        import matplotlib

        matplotlib.use("Agg")  # No mostrar ventana
        df_ocu = df[(df["OCI"] == 1) & (df["INGLABO"] > 0)]
        if len(df_ocu) > 10:
            fig = GraficoCurvaLorenz().graficar(df_ocu)
            import matplotlib.pyplot as plt

            plt.close(fig)
            print("  ✅ 7/7 Gráfico Lorenz generado sin error")
        else:
            print(f"  ⚠️  7/7 Pocos ocupados para gráfico ({len(df_ocu)})")
    except Exception as e:
        errores.append(f"Gráfico: {e}")
        print(f"  ❌ 7/7 Error generando gráfico: {e}")

    return _resultado_final(errores, inicio)


def _resultado_final(errores, inicio):
    """Imprime resultado final del smoke test."""
    elapsed = time.time() - inicio
    print(f"\n{'─' * 65}")
    if not errores:
        print(f"  ✅ SMOKE TEST PASADO en {elapsed:.1f}s")
        print("  → Es seguro ejecutar el pipeline completo.")
        print(f"{'─' * 65}")
        return True
    else:
        print(f"  ❌ SMOKE TEST FALLIDO — {len(errores)} errores en {elapsed:.1f}s")
        for i, err in enumerate(errores, 1):
            print(f"     {i}. {err}")
        print("\n  → NO proceder con el pipeline hasta corregir los errores.")
        print(f"{'─' * 65}")
        return False


if __name__ == "__main__":
    # Ejecutar standalone
    import sys

    ruta = sys.argv[1] if len(sys.argv) > 1 else None
    ok = ejecutar_smoke_test(ruta_base=ruta)
    sys.exit(0 if ok else 1)
