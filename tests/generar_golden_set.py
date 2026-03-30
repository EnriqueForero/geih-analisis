# -*- coding: utf-8 -*-
"""
tests/generar_golden_set.py — Genera un dataset sintético de referencia.

Produce 1,000 registros que simulan la estructura de la GEIH con
distribuciones controladas para que los resultados sean verificables.

Estructura de la población sintética (1,000 personas):
  - 600 ocupados (OCI=1), 80 desocupados (DSI=1), 320 inactivos (FFT=1)
  - PEA = 680, PET = 1,000
  - TD esperada = 80/680 ≈ 11.76%
  - TGP esperada = 680/1,000 = 68.0%
  - TO esperada = 600/1,000 = 60.0%
  - 500 urbanos, 500 rurales
  - 500 hombres, 500 mujeres
  - Ingresos: media conocida para validar estadísticas ponderadas

Ejecutar:
    python tests/generar_golden_set.py
    → genera tests/golden_set.parquet

ProColombia · GIC · Analítica
"""

import numpy as np
import pandas as pd
from pathlib import Path


def generar_golden_set(
    n: int = 1_000,
    seed: int = 42,
    ruta_salida: str = "golden_set.parquet",
) -> pd.DataFrame:
    """Genera el golden set con distribuciones controladas."""
    rng = np.random.default_rng(seed)

    # ── Distribución de la población ───────────────────────────
    n_ocu = 600   # OCI=1
    n_dsi = 80    # DSI=1 (desocupados)
    n_fft = 320   # FFT=1 (fuera fuerza de trabajo)
    assert n_ocu + n_dsi + n_fft == n

    # Clasificación laboral
    OCI = np.zeros(n, dtype=int)
    DSI = np.zeros(n, dtype=int)
    FT  = np.zeros(n, dtype=int)
    FFT = np.zeros(n, dtype=int)
    PET = np.ones(n, dtype=int)

    OCI[:n_ocu] = 1
    DSI[n_ocu:n_ocu+n_dsi] = 1
    FFT[n_ocu+n_dsi:] = 1
    FT[:n_ocu+n_dsi] = 1  # PEA = ocupados + desocupados

    # ── Factor de expansión ────────────────────────────────────
    # Todos con FEX=1000 → poblacion expandida = 1,000,000
    FEX_C18 = np.full(n, 1_000.0)

    # ── Demografía ─────────────────────────────────────────────
    P3271 = np.array([1]*500 + [2]*500)           # 500H + 500M
    P6040 = rng.integers(15, 65, size=n)           # Edad 15-64
    CLASE = np.array([1]*500 + [2]*500)            # 500 urbano + 500 rural
    DPTO  = rng.choice(['05','08','11','13','76'], size=n)
    MES_NUM = rng.integers(1, 13, size=n)

    # ── Educación ──────────────────────────────────────────────
    P3042 = rng.choice([1,3,4,5,8,9,10,11,12,13], size=n, 
                       p=[0.05,0.10,0.15,0.20,0.10,0.10,0.15,0.08,0.05,0.02])
    P6080 = rng.choice([1,5,6], size=n, p=[0.03, 0.10, 0.87])
    P6090 = np.where(rng.random(n) < 0.85, 1, 2)  # 85% afiliado salud

    # ── Variables de ocupados (solo las primeras 600 filas) ────
    INGLABO = np.full(n, np.nan)
    P6500   = np.full(n, np.nan)
    P6430   = np.full(n, np.nan)
    P6800   = np.full(n, np.nan)
    P6850   = np.full(n, np.nan)
    P6920   = np.full(n, np.nan)
    P3069   = np.full(n, np.nan)
    P7130   = np.full(n, np.nan)
    RAMA2D_R4 = np.full(n, np.nan, dtype=object)
    RAMA4D_R4 = np.full(n, np.nan, dtype=object)
    AREA      = np.full(n, np.nan, dtype=object)
    P1802     = np.full(n, np.nan)
    P6765     = np.full(n, np.nan, dtype=object)
    P3363     = np.full(n, np.nan)
    P3364     = np.full(n, np.nan)
    P6440     = np.full(n, np.nan)
    P6450     = np.full(n, np.nan)
    P6460     = np.full(n, np.nan)
    P3047     = np.full(n, np.nan)
    P3048     = np.full(n, np.nan)
    P3049     = np.full(n, np.nan)

    # Ingresos controlados para ocupados
    # Media esperada ≈ 1,800,000 COP, mediana ≈ 1,400,000
    ingresos_ocu = rng.lognormal(mean=14.15, sigma=0.65, size=n_ocu)
    ingresos_ocu = np.clip(ingresos_ocu, 200_000, 30_000_000)
    INGLABO[:n_ocu] = ingresos_ocu
    P6500[:n_ocu] = ingresos_ocu * rng.uniform(0.80, 0.95, size=n_ocu)

    # Horas: la mayoría 40-48, algunos subempleo
    P6800[:n_ocu] = rng.choice(
        [20, 30, 35, 40, 42, 44, 46, 48, 50, 55, 60],
        size=n_ocu, p=[0.05,0.05,0.05,0.15,0.15,0.15,0.10,0.10,0.08,0.07,0.05]
    )
    P6850[:n_ocu] = P6800[:n_ocu] + rng.integers(-5, 6, size=n_ocu)
    P6850[:n_ocu] = np.clip(P6850[:n_ocu], 1, 80)

    # Cotiza pensión: 45% sí
    P6920[:n_ocu] = np.where(rng.random(n_ocu) < 0.45, 1, 2)

    # Posición ocupacional
    P6430[:n_ocu] = rng.choice([1,2,3,4,5,6], size=n_ocu, p=[0.30,0.10,0.05,0.35,0.10,0.10])

    # Tamaño empresa
    P3069[:n_ocu] = rng.choice(range(1,11), size=n_ocu,
        p=[0.25,0.15,0.10,0.10,0.08,0.07,0.06,0.07,0.06,0.06])

    # Deseo cambiar trabajo
    P7130[:n_ocu] = np.where(rng.random(n_ocu) < 0.30, 1, 2)

    # CIIU
    ciiu_2d = rng.choice(['01','10','41','47','55','58','64','85','86','96'], size=n_ocu,
        p=[0.10,0.08,0.07,0.20,0.08,0.05,0.05,0.12,0.10,0.15])
    RAMA2D_R4[:n_ocu] = ciiu_2d
    RAMA4D_R4[:n_ocu] = [f'{c}11' for c in ciiu_2d]

    # AREA (municipios)
    AREA[:n_ocu] = rng.choice(['11001','05001','76001','08001','68001'], size=n_ocu)

    # Alcance de mercado
    P1802[:n_ocu] = rng.choice([1,2,3,4,5,6], size=n_ocu, p=[0.50,0.20,0.10,0.10,0.05,0.05])

    # Forma de pago
    P6765[:n_ocu] = rng.choice(['a','b','c','d','f','g'], size=n_ocu,
        p=[0.15,0.10,0.05,0.05,0.50,0.15])

    # Canal empleo
    P3363[:n_ocu] = rng.choice([1,2,3,4,5,6,7], size=n_ocu,
        p=[0.55,0.05,0.05,0.10,0.05,0.15,0.05])

    # Retención fuente
    P3364[:n_ocu] = np.where(rng.random(n_ocu) < 0.25, 1, 2)

    # Contrato
    P6440[:n_ocu] = np.where(rng.random(n_ocu) < 0.55, 1, 2)
    P6450[:n_ocu] = np.where((P6440[:n_ocu] == 1) & (rng.random(n_ocu) < 0.85), 1, 2)
    P6460[:n_ocu] = np.where((P6450[:n_ocu] == 1) & (rng.random(n_ocu) < 0.60), 1, 2)

    # Autonomía (cuenta propia)
    mask_cp = P6430[:n_ocu] == 4
    P3047[:n_ocu] = np.where(mask_cp, rng.choice([1,2,3,4], size=n_ocu), np.nan)
    P3048[:n_ocu] = np.where(mask_cp, rng.choice([1,2,3,4], size=n_ocu), np.nan)
    P3049[:n_ocu] = np.where(mask_cp, rng.choice([1,2,3,4], size=n_ocu), np.nan)

    # ── Variables de desocupados ───────────────────────────────
    P7250 = np.full(n, np.nan)
    P7250[n_ocu:n_ocu+n_dsi] = rng.choice(
        [2, 4, 8, 12, 16, 20, 30, 52], size=n_dsi,
        p=[0.15, 0.20, 0.20, 0.15, 0.10, 0.08, 0.07, 0.05]
    )

    # ── Variables de FFT ──────────────────────────────────────
    P6300 = np.full(n, np.nan)
    P6310 = np.full(n, np.nan)
    P6300[n_ocu+n_dsi:] = np.where(rng.random(n_fft) < 0.15, 1, 2)
    P6310[n_ocu+n_dsi:] = np.where(P6300[n_ocu+n_dsi:] == 1, 
                                     np.where(rng.random(n_fft) < 0.70, 1, 2), 2)

    # ── Discapacidad (Washington Scale) ───────────────────────
    disc_cols = {}
    for i in range(1, 9):
        vals = rng.choice([1,2,3,4], size=n, p=[0.85, 0.08, 0.04, 0.03])
        disc_cols[f'P1906S{i}'] = vals

    # ── Campesino ─────────────────────────────────────────────
    P2057 = np.where(rng.random(n) < 0.12, 1, 2)   # 12% campesino
    P2059 = np.where((P2057 == 2) & (rng.random(n) < 0.08), 1, 2)

    # ── Migración ─────────────────────────────────────────────
    P3370 = rng.choice([1,2,3], size=n, p=[0.85, 0.10, 0.05])
    P3376 = rng.choice([1,2], size=n, p=[0.95, 0.05])  # 5% nacido exterior

    # ── Otras formas de trabajo ───────────────────────────────
    P3054 = np.where(rng.random(n) < 0.08, 1, 2)
    P3055 = np.where(rng.random(n) < 0.05, 1, 2)
    P3056 = np.where(rng.random(n) < 0.03, 1, 2)

    # ── Otros ingresos ────────────────────────────────────────
    P7422 = np.where(rng.random(n) < 0.10, 1, 2)
    P7500S1 = np.where(rng.random(n) < 0.08, 1, 2)
    P7500S2 = np.where(rng.random(n) < 0.06, 1, 2)

    # ── Construir DataFrame ────────────────────────────────────
    data = {
        'DIRECTORIO':  [f'D{i:06d}' for i in range(n)],
        'SECUENCIA_P': [f'S{i:04d}' for i in range(n)],
        'ORDEN':       [f'{(i%5)+1}' for i in range(n)],
        'FEX_C18': FEX_C18, 'MES_NUM': MES_NUM,
        'P3271': P3271, 'P6040': P6040, 'CLASE': CLASE, 'DPTO': DPTO,
        'P3042': P3042, 'P6080': P6080, 'P6090': P6090,
        'FT': FT, 'PET': PET, 'OCI': OCI, 'DSI': DSI, 'FFT': FFT,
        'INGLABO': INGLABO, 'P6500': P6500,
        'P6430': P6430, 'P6800': P6800, 'P6850': P6850,
        'P6920': P6920, 'P3069': P3069, 'P7130': P7130,
        'RAMA2D_R4': RAMA2D_R4, 'RAMA4D_R4': RAMA4D_R4, 'AREA': AREA,
        'P1802': P1802, 'P6765': P6765, 'P3363': P3363, 'P3364': P3364,
        'P6440': P6440, 'P6450': P6450, 'P6460': P6460,
        'P3047': P3047, 'P3048': P3048, 'P3049': P3049,
        'P7250': P7250, 'P6300': P6300, 'P6310': P6310,
        'P2057': P2057, 'P2059': P2059,
        'P3370': P3370, 'P3376': P3376,
        'P3054': P3054, 'P3055': P3055, 'P3056': P3056,
        'P7422': P7422, 'P7500S1': P7500S1, 'P7500S2': P7500S2,
        'P6240': np.where(FT, rng.choice([1,2,3], size=n), rng.choice([3,4,5,6], size=n)),
    }
    data.update(disc_cols)

    df = pd.DataFrame(data)

    # Shuffle para no tener orden previsible
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # Guardar
    ruta = Path(ruta_salida)
    df.to_parquet(ruta, index=False)
    print(f"✅ Golden set generado: {ruta} ({len(df):,} filas × {df.shape[1]} cols)")

    # ── Resultados esperados ───────────────────────────────────
    print(f"\n  RESULTADOS ESPERADOS (FEX=1000, N={n}):")
    pea = n_ocu + n_dsi
    print(f"  TD  = {n_dsi}/{pea} = {n_dsi/pea*100:.2f}%")
    print(f"  TGP = {pea}/{n} = {pea/n*100:.1f}%")
    print(f"  TO  = {n_ocu}/{n} = {n_ocu/n*100:.1f}%")
    print(f"  PEA expandida = {pea * 1000 / 1e6:.3f}M")
    print(f"  Ocupados expandidos = {n_ocu * 1000 / 1e6:.3f}M")

    return df


# Resultados esperados como constantes para los tests
GOLDEN_EXPECTED = {
    "n_total": 1_000,
    "n_ocu": 600,
    "n_dsi": 80,
    "n_fft": 320,
    "n_pea": 680,
    "td_pct": 80 / 680 * 100,      # ≈ 11.76%
    "tgp_pct": 680 / 1000 * 100,    # 68.0%
    "to_pct": 600 / 1000 * 100,     # 60.0%
    "fex_uniforme": 1_000.0,
    "pea_expandida_m": 0.680,       # millones
}


if __name__ == "__main__":
    generar_golden_set()
