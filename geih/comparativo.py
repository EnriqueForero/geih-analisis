# -*- coding: utf-8 -*-
"""
geih.comparativo — Análisis comparativo multi-año de la GEIH.

Permite cargar múltiples años, agregarles columna ANIO, y calcular
comparaciones inter-anuales: variaciones de TD, evolución de ingresos,
cambios en la estructura sectorial, convergencia departamental, etc.

Flujo típico:
    comp = ComparadorMultiAnio()
    comp.agregar_anio(2025, '/ruta/GEIH_2025.parquet', config_2025)
    comp.agregar_anio(2026, '/ruta/GEIH_2026.parquet', config_2026)
    comp.comparar_indicadores()
    comp.evolucion_ingresos()

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "ComparadorMultiAnio",
]

import gc
from typing import Optional, Dict, List, Any

import numpy as np
import pandas as pd

from .config import ConfigGEIH, DEPARTAMENTOS, RAMAS_DANE
from .preparador import PreparadorGEIH
from .indicadores import IndicadoresLaborales
from .utils import EstadisticasPonderadas as EP


class ComparadorMultiAnio:
    """Compara indicadores laborales entre múltiples años GEIH.

    Carga bases de diferentes años, les agrega la columna ANIO,
    y produce tablas comparativas listas para reportes y gráficos.

    Cada año se carga con su propia ConfigGEIH (SMMLV, n_meses, etc.)
    para que los cálculos sean correctos según el período.

    Uso:
        comp = ComparadorMultiAnio()
        comp.agregar_anio(2025, 'GEIH_2025.parquet', ConfigGEIH(anio=2025))
        comp.agregar_anio(2026, 'GEIH_2026.parquet', ConfigGEIH(anio=2026, n_meses=3))

        tabla_ind = comp.comparar_indicadores()         # TD, TGP, TO por año
        tabla_dpto = comp.comparar_departamentos()       # TD por dpto × año
        tabla_ing = comp.evolucion_ingresos()            # mediana salarial por año
        tabla_rama = comp.comparar_ramas()               # empleo por rama × año
        df_combo = comp.obtener_base_combinada()         # base unificada con ANIO
    """

    def __init__(self):
        """Inicializa el comparador sin datos."""
        self._anios: Dict[int, Dict[str, Any]] = {}
        # {anio: {'df': DataFrame, 'config': ConfigGEIH, 'geih_raw': DataFrame}}

    def agregar_anio(
        self,
        anio: int,
        ruta_parquet: str,
        config: Optional[ConfigGEIH] = None,
        preparar: bool = True,
    ) -> None:
        """Carga un año y lo registra para comparación.

        Args:
            anio: Año de los datos (2025, 2026, ...).
            ruta_parquet: Ruta al archivo Parquet consolidado.
            config: ConfigGEIH del año. Si None, se crea con defaults.
            preparar: Si True, prepara la base (FEX_ADJ, variables derivadas).
        """
        config = config or ConfigGEIH(anio=anio)

        print(f"\n📂 Cargando {anio}: {ruta_parquet}")
        geih_raw = pd.read_parquet(ruta_parquet)
        print(f"   {geih_raw.shape[0]:,} filas × {geih_raw.shape[1]} cols")

        if preparar:
            prep = PreparadorGEIH(config=config)
            df = prep.preparar_base(geih_raw)
            df = prep.agregar_variables_derivadas(df)
        else:
            df = geih_raw.copy()
            df["FEX_ADJ"] = df["FEX_C18"] / config.n_meses

        # Agregar columna ANIO
        df["ANIO"] = anio

        self._anios[anio] = {
            "df": df,
            "config": config,
            "n_registros": len(df),
        }

        print(f"   ✅ {anio} registrado ({len(df):,} filas, "
              f"SMMLV=${config.smmlv:,})")

        # Liberar raw
        del geih_raw
        gc.collect()

    @property
    def anios_disponibles(self) -> List[int]:
        """Lista de años cargados, ordenados."""
        return sorted(self._anios.keys())

    def obtener_base_combinada(self) -> pd.DataFrame:
        """Retorna un DataFrame unificado con todos los años y columna ANIO.

        Útil para análisis ad-hoc que no están cubiertos por los métodos
        predefinidos del comparador.

        Returns:
            DataFrame con todos los años concatenados y columna ANIO.
        """
        if not self._anios:
            print("⚠️  No hay años cargados. Use agregar_anio() primero.")
            return pd.DataFrame()

        dfs = [data["df"] for data in self._anios.values()]
        combinado = pd.concat(dfs, ignore_index=True)
        print(f"✅ Base combinada: {combinado.shape[0]:,} filas × "
              f"{combinado.shape[1]} cols — Años: {self.anios_disponibles}")
        return combinado

    # ═════════════════════════════════════════════════════════════
    # COMPARACIONES PREDEFINIDAS
    # ═════════════════════════════════════════════════════════════

    def comparar_indicadores(self) -> pd.DataFrame:
        """Compara TD, TGP, TO nacionales entre años.

        Returns:
            DataFrame con una fila por año y columnas:
            ANIO, TD_%, TGP_%, TO_%, PEA_M, Ocupados_M, Desocupados_M,
            y columnas de variación (Δ) respecto al año anterior.
        """
        filas = []
        for anio in self.anios_disponibles:
            data = self._anios[anio]
            ind = IndicadoresLaborales(config=data["config"])
            r = ind.calcular(data["df"])
            r["ANIO"] = anio
            r["SMMLV"] = data["config"].smmlv
            r["N_meses"] = data["config"].n_meses
            filas.append(r)

        df = pd.DataFrame(filas).sort_values("ANIO")

        # Calcular variaciones inter-anuales
        for col in ["TD_%", "TGP_%", "TO_%"]:
            df[f"Δ_{col}"] = df[col].diff().round(2)

        for col in ["Ocupados_M", "Desocupados_M", "PEA_M"]:
            df[f"Var_{col}_%"] = (df[col].pct_change() * 100).round(1)

        self._imprimir_indicadores(df)
        return df

    def comparar_departamentos(
        self,
        top_n: int = 10,
    ) -> pd.DataFrame:
        """TD por departamento × año (panel).

        Args:
            top_n: Mostrar solo los top N departamentos por TD del último año.

        Returns:
            DataFrame pivotado: filas=departamento, columnas=año, valores=TD_%.
        """
        filas = []
        for anio in self.anios_disponibles:
            data = self._anios[anio]
            ind = IndicadoresLaborales(config=data["config"])
            td_dpto = ind.por_departamento(data["df"])
            td_dpto["ANIO"] = anio
            filas.append(td_dpto[["Departamento", "TD_%", "ANIO"]])

        df = pd.concat(filas, ignore_index=True)
        pivot = df.pivot_table(
            index="Departamento", columns="ANIO", values="TD_%"
        )

        # Calcular variación entre el primer y último año
        anios = sorted(pivot.columns)
        if len(anios) >= 2:
            pivot[f"Δ_{anios[0]}→{anios[-1]}"] = (
                pivot[anios[-1]] - pivot[anios[0]]
            ).round(1)

        # Ordenar por TD del último año
        pivot = pivot.sort_values(anios[-1], ascending=False)

        if top_n:
            pivot = pivot.head(top_n)

        return pivot

    def evolucion_ingresos(self) -> pd.DataFrame:
        """Mediana salarial (en SMMLV y COP) por año.

        Calcula la mediana ponderada del ingreso laboral para
        cada año, expresada en COP corrientes y en SMMLV del año.

        Returns:
            DataFrame con ANIO, Mediana_COP, Mediana_SMMLV, SMMLV_anio.
        """
        filas = []
        for anio in self.anios_disponibles:
            data = self._anios[anio]
            df = data["df"]
            smmlv = data["config"].smmlv
            mask_ocu = (df["OCI"] == 1) & (df["INGLABO"] > 0)
            med_cop = EP.mediana(
                df.loc[mask_ocu, "INGLABO"], df.loc[mask_ocu, "FEX_ADJ"]
            )
            filas.append({
                "ANIO": anio,
                "Mediana_COP": round(med_cop),
                "Mediana_SMMLV": round(med_cop / smmlv, 2),
                "SMMLV_anio": smmlv,
            })

        df = pd.DataFrame(filas).sort_values("ANIO")

        if len(df) >= 2:
            df["Var_COP_%"] = (df["Mediana_COP"].pct_change() * 100).round(1)
            df["Var_SMMLV"] = df["Mediana_SMMLV"].diff().round(2)

        return df

    def comparar_ramas(self) -> pd.DataFrame:
        """Empleo por rama de actividad × año.

        Returns:
            DataFrame pivotado: filas=rama, columnas=año, valores=ocupados (miles).
        """
        filas = []
        for anio in self.anios_disponibles:
            df = self._anios[anio]["df"]
            df_ocu = df[(df["OCI"] == 1) & df["RAMA"].notna()]
            rama_emp = (
                df_ocu.groupby("RAMA")["FEX_ADJ"]
                .sum().div(1_000).round(1)
                .reset_index()
                .rename(columns={"FEX_ADJ": "Ocupados_miles"})
            )
            rama_emp["ANIO"] = anio
            filas.append(rama_emp)

        df = pd.concat(filas, ignore_index=True)
        pivot = df.pivot_table(
            index="RAMA", columns="ANIO", values="Ocupados_miles"
        )

        anios = sorted(pivot.columns)
        if len(anios) >= 2:
            pivot[f"Var_{anios[0]}→{anios[-1]}_%"] = (
                (pivot[anios[-1]] - pivot[anios[0]]) / pivot[anios[0]] * 100
            ).round(1)

        return pivot.sort_values(anios[-1], ascending=False)

    def comparar_brecha_genero(self) -> pd.DataFrame:
        """Brecha salarial de género por año (nacional).

        Calcula mediana hombres, mediana mujeres, y brecha %.

        Returns:
            DataFrame con ANIO, Mediana_H, Mediana_M, Brecha_%.
        """
        filas = []
        for anio in self.anios_disponibles:
            df = self._anios[anio]["df"]
            smmlv = self._anios[anio]["config"].smmlv
            mask = (df["OCI"] == 1) & (df["INGLABO"] > 0) & df["P3271"].notna()
            for sexo_val, sexo_lab in [(1, "H"), (2, "M")]:
                m = mask & (df["P3271"] == sexo_val)
                med = EP.mediana(df.loc[m, "INGLABO"], df.loc[m, "FEX_ADJ"])
                filas.append({
                    "ANIO": anio, "Sexo": sexo_lab,
                    "Mediana_COP": round(med),
                    "Mediana_SMMLV": round(med / smmlv, 2),
                })

        df = pd.DataFrame(filas)
        pivot = df.pivot_table(
            index="ANIO", columns="Sexo",
            values=["Mediana_COP", "Mediana_SMMLV"],
        )
        pivot.columns = ["_".join(c) for c in pivot.columns]

        if "Mediana_COP_H" in pivot.columns and "Mediana_COP_M" in pivot.columns:
            pivot["Brecha_%"] = (
                (pivot["Mediana_COP_M"] - pivot["Mediana_COP_H"])
                / pivot["Mediana_COP_H"] * 100
            ).round(1)

        return pivot

    def resumen(self) -> None:
        """Imprime resumen de los años cargados."""
        print(f"\n{'='*60}")
        print(f"  COMPARADOR MULTI-AÑO — {len(self._anios)} años cargados")
        print(f"{'='*60}")
        for anio in self.anios_disponibles:
            data = self._anios[anio]
            print(f"  {anio}: {data['n_registros']:,} filas | "
                  f"SMMLV=${data['config'].smmlv:,} | "
                  f"{data['config'].n_meses} meses")
        print(f"{'='*60}")

    # ═════════════════════════════════════════════════════════════
    # IMPRESIÓN
    # ═════════════════════════════════════════════════════════════

    def _imprimir_indicadores(self, df: pd.DataFrame) -> None:
        print(f"\n{'='*75}")
        print(f"  COMPARACIÓN INTER-ANUAL DE INDICADORES LABORALES")
        print(f"{'='*75}")
        for _, r in df.iterrows():
            anio = int(r["ANIO"])
            delta_td = f"  Δ={r.get('Δ_TD_%', 'N/A')}" if "Δ_TD_%" in r else ""
            print(f"  {anio}: TD={r['TD_%']:.1f}%{delta_td}  |  "
                  f"TGP={r['TGP_%']:.1f}%  |  TO={r['TO_%']:.1f}%  |  "
                  f"OCI={r['Ocupados_M']:.2f}M  |  "
                  f"SMMLV=${int(r['SMMLV']):,}")
