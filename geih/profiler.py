"""
geih.profiler — Profiling de memoria y rendimiento del pipeline.

Herramientas para identificar cuellos de botella de RAM y tiempo:
  - PerfilMemoria: snapshots antes/después de cada operación
  - medir_tiempo: decorador y context manager para cronometrar
  - reporte_memoria: resumen de consumo por etapa

Diseñado para Google Colab (~12GB RAM) donde la memoria es el
recurso más escaso. Los reportes son visibles e informativos.

Uso desde el notebook:
    from geih.profiler import PerfilMemoria, medir_tiempo

    # Context manager para bloques de código
    with medir_tiempo("Consolidar 12 meses"):
        geih = consolidador.consolidar()

    # Profiling de memoria paso a paso
    perf = PerfilMemoria()
    perf.snapshot("Antes de consolidar")
    geih = consolidador.consolidar()
    perf.snapshot("Después de consolidar")
    perf.snapshot("Después de preparar", df=df)
    perf.reporte()

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "PerfilMemoria",
    "medir_tiempo",
    "tamano_objeto",
]

import functools
import gc
import os
import sys
import time
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Optional

import pandas as pd

from .logger import get_logger

log = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════
# PERFIL DE MEMORIA
# ═════════════════════════════════════════════════════════════════════


class PerfilMemoria:
    """Registra snapshots de uso de RAM a lo largo del pipeline.

    Cada snapshot captura: timestamp, RAM usada por el proceso,
    RAM libre del sistema, y opcionalmente el tamaño de un DataFrame.

    Al final, reporte() imprime una tabla con la evolución de RAM
    y destaca las etapas donde más creció el consumo.

    Uso:
        perf = PerfilMemoria()
        perf.snapshot("Inicio")
        geih = consolidador.consolidar()
        perf.snapshot("Post-consolidar")
        df = prep.preparar_base(geih)
        perf.snapshot("Post-preparar", df=df)
        perf.reporte()

    Output:
        ┌───────────────────┬──────────┬──────────┬──────────┬──────────┐
        │ Etapa             │ RAM (GB) │ Δ RAM    │ DF (MB)  │ Tiempo   │
        ├───────────────────┼──────────┼──────────┼──────────┼──────────┤
        │ Inicio            │ 0.42     │ —        │ —        │ 0:00     │
        │ Post-consolidar   │ 3.85     │ +3.43    │ —        │ 2:30     │
        │ Post-preparar     │ 4.12     │ +0.27    │ 847 MB   │ 0:05     │
        └───────────────────┴──────────┴──────────┴──────────┴──────────┘
    """

    def __init__(self):
        self._snapshots: list[dict[str, Any]] = []
        self._inicio = time.time()

    def snapshot(
        self,
        etapa: str,
        df: Optional[pd.DataFrame] = None,
        gc_collect: bool = True,
    ) -> dict[str, Any]:
        """Captura un snapshot de memoria.

        Args:
            etapa: Nombre descriptivo de la etapa.
            df: DataFrame para medir su tamaño en memoria (opcional).
            gc_collect: Si True, ejecuta gc.collect() antes de medir
                       (más preciso pero ligeramente más lento).

        Returns:
            Dict con los valores capturados.
        """
        if gc_collect:
            gc.collect()

        ram_usada = self._ram_proceso_gb()
        ram_libre = self._ram_libre_gb()
        df_mb = df.memory_usage(deep=True).sum() / 1e6 if df is not None else None
        elapsed = time.time() - self._inicio

        snap = {
            "etapa": etapa,
            "ram_usada_gb": round(ram_usada, 2),
            "ram_libre_gb": round(ram_libre, 2),
            "df_mb": round(df_mb, 1) if df_mb else None,
            "timestamp": elapsed,
        }
        self._snapshots.append(snap)

        # Log en tiempo real
        delta = ""
        if len(self._snapshots) > 1:
            prev = self._snapshots[-2]["ram_usada_gb"]
            diff = snap["ram_usada_gb"] - prev
            delta = f"  Δ={diff:+.2f} GB"
        df_info = f"  DF={df_mb:.0f}MB" if df_mb else ""

        log.info(f"  📊 {etapa}: RAM={ram_usada:.2f}GB{delta}{df_info}")
        return snap

    def reporte(self) -> pd.DataFrame:
        """Imprime y retorna un resumen de todos los snapshots.

        Returns:
            DataFrame con la tabla de profiling.
        """
        if not self._snapshots:
            log.warning("No hay snapshots registrados.")
            return pd.DataFrame()

        log.info(f"\n{'=' * 70}")
        log.info(f"  PERFIL DE MEMORIA — {len(self._snapshots)} snapshots")
        log.info(f"{'=' * 70}")
        log.info(f"  {'Etapa':<25} {'RAM(GB)':>8} {'Δ RAM':>8} {'DF(MB)':>8} {'Tiempo':>10}")
        log.info(f"  {'─' * 25} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 10}")

        rows = []
        for i, snap in enumerate(self._snapshots):
            delta = "—"
            if i > 0:
                diff = snap["ram_usada_gb"] - self._snapshots[i - 1]["ram_usada_gb"]
                delta = f"{diff:+.2f}"

            t_prev = self._snapshots[i - 1]["timestamp"] if i > 0 else 0
            dt = snap["timestamp"] - t_prev
            tiempo_str = str(timedelta(seconds=int(dt)))

            df_str = f"{snap['df_mb']:.0f}" if snap["df_mb"] else "—"

            log.info(
                f"  {snap['etapa']:<25} {snap['ram_usada_gb']:>7.2f} "
                f"{delta:>8} {df_str:>8} {tiempo_str:>10}"
            )

            rows.append(
                {
                    "Etapa": snap["etapa"],
                    "RAM_GB": snap["ram_usada_gb"],
                    "Delta_GB": float(delta) if delta != "—" else 0,
                    "DF_MB": snap["df_mb"],
                    "Tiempo_s": dt,
                }
            )

        # Alerta si RAM > 80% del total
        total = self._ram_total_gb()
        ultimo = self._snapshots[-1]["ram_usada_gb"]
        pct = ultimo / total * 100 if total > 0 else 0
        if pct > 80:
            log.warning(f"\n  ⚠️  RAM al {pct:.0f}% de capacidad ({ultimo:.1f}/{total:.1f} GB)")
            log.warning("     Considere liberar DataFrames intermedios con del df; gc.collect()")
        elif pct > 60:
            log.info(f"\n  RAM al {pct:.0f}% ({ultimo:.1f}/{total:.1f} GB)")
        else:
            log.info(f"\n  ✅ RAM al {pct:.0f}% ({ultimo:.1f}/{total:.1f} GB) — holgado")

        log.info(f"{'=' * 70}")
        return pd.DataFrame(rows)

    @property
    def pico_ram_gb(self) -> float:
        """Máxima RAM usada durante la sesión."""
        if not self._snapshots:
            return 0
        return max(s["ram_usada_gb"] for s in self._snapshots)

    @staticmethod
    def _ram_proceso_gb() -> float:
        """RAM usada por el proceso actual en GB."""
        try:
            import psutil

            return psutil.Process(os.getpid()).memory_info().rss / 1e9
        except ImportError:
            return 0.0

    @staticmethod
    def _ram_libre_gb() -> float:
        """RAM libre del sistema en GB."""
        try:
            import psutil

            return psutil.virtual_memory().available / 1e9
        except ImportError:
            return 0.0

    @staticmethod
    def _ram_total_gb() -> float:
        """RAM total del sistema en GB."""
        try:
            import psutil

            return psutil.virtual_memory().total / 1e9
        except ImportError:
            return 12.0  # default Colab


# ═════════════════════════════════════════════════════════════════════
# MEDICIÓN DE TIEMPO
# ═════════════════════════════════════════════════════════════════════


@contextmanager
def medir_tiempo(nombre: str = "Operación"):
    """Context manager que mide y reporta el tiempo de ejecución.

    Uso como context manager:
        with medir_tiempo("Consolidar"):
            geih = consolidador.consolidar()
        # Output: ⏱️  Consolidar: 2:30.4

    Args:
        nombre: Nombre descriptivo de la operación.

    Yields:
        None — usar solo como context manager.
    """
    inicio = time.time()
    log.info(f"🔄 {nombre}...")
    try:
        yield
    finally:
        elapsed = time.time() - inicio
        tiempo_str = str(timedelta(seconds=round(elapsed, 1)))
        log.info(f"⏱️  {nombre}: {tiempo_str}")


def cronometrar(func):
    """Decorador que mide el tiempo de ejecución de una función.

    Uso:
        @cronometrar
        def mi_funcion_pesada():
            ...

    Output: ⏱️  mi_funcion_pesada: 0:01:23
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        elapsed = time.time() - inicio
        tiempo_str = str(timedelta(seconds=round(elapsed, 1)))
        log.info(f"⏱️  {func.__name__}: {tiempo_str}")
        return resultado

    return wrapper


# ═════════════════════════════════════════════════════════════════════
# UTILIDADES DE TAMAÑO
# ═════════════════════════════════════════════════════════════════════


def tamano_objeto(obj, nombre: str = "Objeto") -> float:
    """Mide y reporta el tamaño en memoria de un objeto.

    Para DataFrames usa memory_usage(deep=True).
    Para otros objetos usa sys.getsizeof().

    Args:
        obj: Objeto a medir.
        nombre: Nombre para el reporte.

    Returns:
        Tamaño en MB.
    """
    if isinstance(obj, pd.DataFrame):
        mb = obj.memory_usage(deep=True).sum() / 1e6
        log.info(f"  📦 {nombre}: {obj.shape[0]:,} × {obj.shape[1]} → {mb:.1f} MB")
    else:
        mb = sys.getsizeof(obj) / 1e6
        log.info(f"  📦 {nombre}: {mb:.1f} MB")
    return mb
