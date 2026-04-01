# -*- coding: utf-8 -*-
"""
geih.preparador — Preparación y enriquecimiento de la base GEIH.

Transforma la base consolidada cruda en datos listos para análisis:
  1. Ajusta el factor de expansión según el período
  2. Mapea códigos CIIU a ramas de actividad
  3. Hace merge con correlativas externas (CIIU descriptivo, DIVIPOLA)
  4. Crea variables derivadas (SEXO, CIUDAD, NIVEL_GRUPO, etc.)

CAMBIO v5.1 — Flexibilidad y extensibilidad:
  - `columnas_extra`: el usuario puede agregar variables desde el notebook
    sin modificar el código fuente del paquete. Abierto a extensión,
    cerrado a modificación (Principio Abierto/Cerrado de SOLID).
  - `meses_filtro`: soporta un solo mes (int) o un rango (list[int])
    para análisis semestral, trimestral o cualquier período arbitrario.
  - Todas las columnas se documentan con comentarios sobre el módulo DANE.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "PreparadorGEIH",
    "MergeCorrelativas",
    "COLUMNAS_DEFAULT",
]


import gc
from pathlib import Path
from typing import Optional, List, Union

import numpy as np
import pandas as pd

from .config import (
    ConfigGEIH,
    RAMAS_DANE,
    TABLA_CIIU_RAMAS,
    DEPARTAMENTOS,
    DPTO_A_CIUDAD,
    AREA_A_CIUDAD,
    NIVELES_AGRUPADOS,
    P3042_A_ANOS,
    CIIU_DESCRIPCION_FALLBACK,
)
from .utils import ConversorTipos


# ═════════════════════════════════════════════════════════════════════
# COLUMNAS POR DEFECTO — EXTENSIBLE DESDE EL NOTEBOOK
# ═════════════════════════════════════════════════════════════════════

COLUMNAS_DEFAULT: List[str] = [
    # ── Identificación y factor de expansión ──────────────────
    "FEX_C18", "MES_NUM",
    # ── Características generales (E/F/G) ─────────────────────
    "P3271",      # Sexo (1=H, 2=M)
    "P6040",      # Edad
    "P6080",      # Autorreconocimiento étnico
    "P3042",      # Nivel educativo (1-13)
    "P3043S1",    # Campo de formación (CINE-F) — para proxy bilingüismo
    "P6090",      # Afiliado salud (1=Sí)
    "CLASE",      # Zona (1=Cabecera/Urbano, 2=Rural)
    "DPTO",       # Departamento (código 2 dígitos)
    "P2057",      # ¿Se considera campesino?
    "P2059",      # ¿Alguna vez fue campesino?
    # Discapacidad — Escala Washington (8 dimensiones)
    "P1906S1", "P1906S2", "P1906S3", "P1906S4",
    "P1906S5", "P1906S6", "P1906S7", "P1906S8",
    # ── Fuerza de trabajo (H) ─────────────────────────────────
    "FT", "PET", "OCI", "DSI", "FFT",
    "P6240",      # Actividad semana pasada
    # ── Ocupados (I) ──────────────────────────────────────────
    "INGLABO",    # Ingreso laboral mensual
    "P6500",      # Salario bruto declarado
    "P6430",      # Posición ocupacional (1-9)
    "P6800",      # Horas normales semana
    "P6850",      # Horas reales semana pasada
    "P6920",      # Cotiza pensión
    "P3069",      # Tamaño empresa
    "P7130",      # Desea cambiar trabajo
    "RAMA2D_R4",  # CIIU 2 dígitos
    "RAMA4D_R4",  # CIIU 4 dígitos
    "AREA",       # Municipio 5 dígitos (32 ciudades)
    # Autonomía laboral
    "P3047",      # ¿Quién decide horario?
    "P3048",      # ¿Quién decide qué producir?
    "P3049",      # ¿Quién decide precio?
    # Formalidad contractual
    "P6440",      # ¿Tiene contrato?
    "P6450",      # ¿Contrato escrito?
    "P6460",      # ¿Contrato indefinido?
    # Variables de alto valor analítico
    "P1802",      # Alcance mercado (1-6, 6=Exportación)
    "P6765",      # Forma de trabajo (destajo, honorarios...)
    "P3363",      # ¿Cómo consiguió empleo?
    "P3364",      # ¿Retención en la fuente?
    "P6400",      # ¿Trabaja donde lo contrataron?
    "P6410",      # Tipo intermediación (EST, CTA)
    # Compensación
    "P6510S1",    # Horas extras
    "P6580S1",    # Bonificaciones
    "P6585S1A1",  # Auxilio alimentación
    "P6585S2A1",  # Auxilio transporte
    # ── Tenencia de tierra y actividad agropecuaria (v5.1) ────
    "P3056",      # Tipo actividad negocio (1=mercancías, 2=agropecuario)
    "P3064",      # ¿Propietario de la tierra? (1=Sí, 2=No)
    "P3064S1",    # Valor estimado arriendo terreno (COP/mes)
    # ── No ocupados (J) ───────────────────────────────────────
    "P7250",      # Semanas buscando trabajo
    "P6300",      # ¿Desea trabajar? (FFT con deseo)
    "P6310",      # ¿Disponible para trabajar?
    "P7140S2",    # Razón: mejorar ingresos
    # ── Otras formas de trabajo (K) ───────────────────────────
    "P3054",      # Autoconsumo bienes
    "P3054S1",    # Horas autoconsumo bienes
    "P3055",      # Autoconsumo servicios
    "P3055S1",    # Horas autoconsumo servicios
    "P3057",      # Formación no remunerada
    # ── Migración (L) ─────────────────────────────────────────
    "P3370",      # ¿Dónde vivía hace 12 meses?
    "P3370S1",    # Departamento hace 12 meses
    "P3376",      # País de nacimiento
    "P3378S1",    # Año de llegada a Colombia
    # ── Otros ingresos (M) ────────────────────────────────────
    "P7422",      # Arriendos recibidos
    "P7500S1",    # Pensiones
    "P7500S1A1",  # Monto pensiones
    "P7500S2",    # Ayudas hogares nacionales
    "P7500S2A1",  # Monto ayudas
    "P7500S3",    # Ayudas institucionales
    "P7510S2",    # Remesas del exterior
    "P7510S2A1",  # Monto remesas
]
"""Columnas extraídas por defecto en preparar_base().

Para agregar variables adicionales desde el notebook sin modificar
este archivo, use el parámetro `columnas_extra`:

    prep = PreparadorGEIH(config=config)
    df = prep.preparar_base(geih, columnas_extra=["P6870", "P6880"])

Las columnas extra se fusionan con esta lista. Si una columna no
existe en la base, se ignora silenciosamente (sin error).
"""


class PreparadorGEIH:
    """Prepara la base GEIH consolidada para análisis.

    Responsabilidad única: transformar datos crudos en datos analíticos.
    No calcula indicadores ni genera gráficos.

    CAMBIO v5.1:
      - `columnas_extra`: agregar variables sin tocar código fuente.
      - `meses_filtro`: acepta int (un mes) o list[int] (rango semestral).
      - Variables de tenencia de tierra incluidas en defaults.

    Uso típico:
        prep = PreparadorGEIH(config=ConfigGEIH(anio=2025, n_meses=12))

        # Análisis anual completo
        df = prep.preparar_base(geih)

        # Primer semestre
        df_s1 = prep.preparar_base(geih, meses_filtro=[1,2,3,4,5,6])

        # Segundo semestre
        df_s2 = prep.preparar_base(geih, meses_filtro=[7,8,9,10,11,12])

        # Con variables adicionales del usuario
        df = prep.preparar_base(geih, columnas_extra=["P6870", "P3376S1"])
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()
        self._conversor = ConversorTipos()

    # ── Método principal ───────────────────────────────────────

    def preparar_base(
        self,
        df_raw: pd.DataFrame,
        columnas: Optional[List[str]] = None,
        columnas_extra: Optional[List[str]] = None,
        meses_filtro: Optional[Union[int, List[int]]] = None,
        solo_ocupados: bool = False,
        solo_ingreso_positivo: bool = False,
    ) -> pd.DataFrame:
        """Prepara un subconjunto de la base con tipos correctos y FEX ajustado.

        Estrategia de memoria: extrae solo las columnas necesarias ANTES
        de copiar, reduciendo el footprint de RAM.

        Args:
            df_raw: Base GEIH consolidada (cruda).
            columnas: Columnas a extraer. Si None, usa COLUMNAS_DEFAULT.
            columnas_extra: Columnas adicionales del usuario. Se fusionan
                con `columnas` sin duplicados. Permite extensión sin
                modificar el código fuente (Principio Abierto/Cerrado).
            meses_filtro: Filtro de meses. Acepta:
                - None → todos los meses (análisis anual).
                - int → un solo mes (ej: 12 para diciembre).
                - list[int] → rango de meses (ej: [1,2,3,4,5,6] semestre 1).
                Si se usa ConfigGEIH.meses_rango y meses_filtro es None,
                se aplica el rango de la configuración.
            solo_ocupados: Si True, filtra OCI == 1.
            solo_ingreso_positivo: Si True, filtra INGLABO > 0.

        Returns:
            DataFrame preparado con FEX_ADJ y columnas estandarizadas.

        Ejemplo:
            # Agregar variables sin tocar el paquete:
            df = prep.preparar_base(geih, columnas_extra=["P6870", "P6880"])

            # Análisis semestral:
            df_s1 = prep.preparar_base(geih, meses_filtro=[1,2,3,4,5,6])
        """
        # ── Construir lista final de columnas ──────────────────
        if columnas is None:
            columnas = list(COLUMNAS_DEFAULT)

        if columnas_extra:
            # Fusionar sin duplicados, preservando orden
            existentes = set(columnas)
            for col in columnas_extra:
                if col not in existentes:
                    columnas.append(col)
                    existentes.add(col)

        # Solo tomar columnas que existan en la base
        cols_ok = [c for c in columnas if c in df_raw.columns]
        cols_faltantes = set(columnas) - set(cols_ok)

        if cols_faltantes:
            # Reportar solo columnas extra que falten (las default pueden faltar
            # legítimamente si no se consolidó con todos los módulos)
            extra_faltantes = cols_faltantes & set(columnas_extra or [])
            if extra_faltantes:
                print(
                    f"⚠️  Columnas extra no encontradas en la base: "
                    f"{sorted(extra_faltantes)}"
                )

        # ── Resolver filtro de meses ───────────────────────────
        # Prioridad: meses_filtro explícito > config.meses_rango > None
        filtro_final: Optional[Union[int, List[int]]] = meses_filtro
        if filtro_final is None and self.config.meses_rango:
            filtro_final = self.config.meses_rango

        # ── Filtrar meses ANTES de copiar (ahorra RAM) ─────────
        if filtro_final is not None and "MES_NUM" in df_raw.columns:
            if isinstance(filtro_final, int):
                mask = df_raw["MES_NUM"] == filtro_final
            elif isinstance(filtro_final, list):
                # Vectorizado: .isin() es O(n), mucho mejor que loop
                mask = df_raw["MES_NUM"].isin(filtro_final)
            else:
                raise TypeError(
                    f"meses_filtro debe ser int o list[int], "
                    f"recibido: {type(filtro_final)}"
                )
            df = df_raw.loc[mask, cols_ok].copy()
        else:
            df = df_raw[cols_ok].copy()

        gc.collect()

        # ── Convertir tipos numéricos ──────────────────────────
        cols_str = {"DPTO", "RAMA2D_R4", "RAMA4D_R4", "AREA", "CLASE"}
        self._conversor.convertir_columnas_numericas(
            df, cols_ok, excluir=list(cols_str)
        )

        # ── Factor de expansión ajustado ───────────────────────
        # NOTA IMPORTANTE: El divisor del FEX depende de cuántos meses
        # tiene el Parquet consolidado (n_meses), NO del filtro aplicado.
        # Si el Parquet tiene 12 meses y se filtra un semestre, el FEX
        # sigue dividiéndose entre 12. La reducción del universo se
        # refleja en que se suman menos registros.
        #
        # Excepción: si meses_filtro es un entero (mes puntual), se
        # asume que el usuario quiere la estimación de ESE mes con
        # FEX sin dividir (divisor = 1).
        if isinstance(filtro_final, int):
            n_meses_divisor = 1
        else:
            n_meses_divisor = self.config.n_meses

        df["FEX_ADJ"] = df["FEX_C18"] / n_meses_divisor

        # ── Filtros opcionales ─────────────────────────────────
        if solo_ocupados and "OCI" in df.columns:
            df = df[df["OCI"] == 1].copy()
        if solo_ingreso_positivo and "INGLABO" in df.columns:
            df = df[df["INGLABO"] > 0].copy()

        gc.collect()

        # ── Reporte ────────────────────────────────────────────
        n = len(df)
        fex_total = df["FEX_ADJ"].sum() / 1e6

        filtro_desc = "todos los meses"
        if isinstance(filtro_final, int):
            from .config import MESES_NOMBRES
            filtro_desc = f"mes {filtro_final} ({MESES_NOMBRES[filtro_final - 1]})"
        elif isinstance(filtro_final, list):
            filtro_desc = f"meses {filtro_final}"

        print(f"   ✅ Base preparada: {n:,} registros → {fex_total:.2f}M personas expandidas")
        print(f"      Período: {filtro_desc} | FEX divisor: ÷{n_meses_divisor}")

        if cols_faltantes:
            n_falt = len(cols_faltantes)
            print(f"      ℹ️  {n_falt} columnas solicitadas no encontradas en la base")

        return df

    # ── Mapeo de CIIU a ramas ──────────────────────────────────

    @staticmethod
    def mapear_rama_ciiu(serie_ciiu: pd.Series) -> pd.Series:
        """Mapea CIIU 2 dígitos a las 13 ramas estándar DANE.

        Implementación 100% vectorizada con np.select (sin .apply()).

        Args:
            serie_ciiu: Serie con códigos CIIU 2 dígitos (string o numérico).

        Returns:
            Serie con nombres de rama de actividad.
        """
        s = pd.to_numeric(serie_ciiu, errors="coerce").astype("float64")

        condiciones = []
        etiquetas = []
        for lo, hi, clave in TABLA_CIIU_RAMAS:
            condiciones.append(s.between(lo, hi))
            etiquetas.append(RAMAS_DANE.get(clave, clave))

        resultado = np.select(
            condiciones,
            np.array(etiquetas, dtype=object),
            default=None,
        )
        return pd.Series(resultado, index=serie_ciiu.index, dtype=object)

    # ── Variables derivadas ────────────────────────────────────

    def agregar_variables_derivadas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Agrega variables derivadas estándar para análisis.

        Variables creadas:
          - DPTO_STR: código departamento estandarizado (2 dígitos)
          - NOMBRE_DPTO: nombre del departamento
          - SEXO: 'Hombres' / 'Mujeres'
          - RAMA: rama de actividad DANE
          - RAMA_INT: CIIU 2 dígitos como entero
          - CIUDAD: nombre de ciudad/AM
          - NIVEL_GRUPO: nivel educativo agrupado
          - ANOS_EDUC: años de educación (para Mincer)
          - INGLABO_SML: ingreso en múltiplos de SMMLV

        Args:
            df: DataFrame preparado.

        Returns:
            El mismo DataFrame con columnas nuevas.
        """
        # Departamento
        if "DPTO" in df.columns:
            df["DPTO_STR"] = self._conversor.estandarizar_dpto(df["DPTO"])
            df["NOMBRE_DPTO"] = df["DPTO_STR"].map(DEPARTAMENTOS)

        # Sexo
        if "P3271" in df.columns:
            df["SEXO"] = df["P3271"].map({1: "Hombres", 2: "Mujeres"})

        # Rama CIIU
        if "RAMA2D_R4" in df.columns:
            df["RAMA_INT"] = pd.to_numeric(
                df["RAMA2D_R4"], errors="coerce"
            ).round(0).astype("Int64")
            df["RAMA"] = self.mapear_rama_ciiu(df["RAMA2D_R4"])

        # Ciudad
        if "DPTO_STR" in df.columns:
            df["CIUDAD"] = df["DPTO_STR"].map(DPTO_A_CIUDAD)

        if "AREA" in df.columns:
            area_str = self._conversor.estandarizar_area(df["AREA"])
            ciudad_area = area_str.map(AREA_A_CIUDAD)
            if "CIUDAD" in df.columns:
                df["CIUDAD"] = ciudad_area.combine_first(df["CIUDAD"])
            else:
                df["CIUDAD"] = ciudad_area

        # Nivel educativo
        if "P3042" in df.columns:
            df["NIVEL_GRUPO"] = df["P3042"].map(NIVELES_AGRUPADOS)
            df["ANOS_EDUC"] = df["P3042"].map(P3042_A_ANOS)

        # Ingreso en SMMLV
        if "INGLABO" in df.columns:
            df["INGLABO_SML"] = df["INGLABO"] / self.config.smmlv

        return df


class MergeCorrelativas:
    """Hace merge con las correlativas externas CIIU y DIVIPOLA.

    Las correlativas agregan descripciones legibles a los códigos
    numéricos de la GEIH. Son archivos Excel mantenidos por el autor.

    Uso típico:
        merger = MergeCorrelativas()
        df = merger.merge_ciiu(df, ruta_ciiu)
        df = merger.merge_divipola(df, ruta_divipola)
    """

    def __init__(self):
        self._conversor = ConversorTipos()

    def merge_ciiu(
        self,
        df: pd.DataFrame,
        ruta_ciiu: str,
        sheet_name: str = "CIIU 2022",
    ) -> pd.DataFrame:
        """Hace merge con la correlativa CIIU Rev.4 adaptada para Colombia.

        Agrega la columna DESCRIPCION_CIIU al DataFrame.
        Si el merge deja registros sin descripción, aplica un fallback
        usando el código de 2 dígitos.

        Args:
            df: DataFrame con columna RAMA4D_R4.
            ruta_ciiu: Ruta al archivo Excel de la correlativa.
            sheet_name: Nombre de la hoja en el Excel.

        Returns:
            DataFrame enriquecido con DESCRIPCION_CIIU.
        """
        if "RAMA4D_R4" not in df.columns:
            print("⚠️ Columna RAMA4D_R4 no encontrada. Saltando merge CIIU.")
            return df

        print("\n🔗 Merge con correlativa CIIU Rev.4...")

        df_ciiu = pd.read_excel(
            ruta_ciiu, sheet_name=sheet_name,
            converters={"RAMA4D_R4": str},
        )

        df["RAMA4D_STD"] = self._conversor.estandarizar_ciiu4(df["RAMA4D_R4"])
        df_ciiu["RAMA4D_STD"] = self._conversor.estandarizar_ciiu4(
            df_ciiu["RAMA4D_R4"]
        )

        rama_df = set(df["RAMA4D_STD"].dropna().unique())
        rama_ciiu = set(df_ciiu["RAMA4D_STD"].dropna().unique())
        match = rama_df & rama_ciiu
        sin_match = rama_df - rama_ciiu
        print(f"   Códigos en base   : {len(rama_df)}")
        print(f"   Códigos en CIIU   : {len(rama_ciiu)}")
        print(f"   Con match         : {len(match)} ({len(match)/max(len(rama_df),1)*100:.0f}%)")
        if sin_match:
            print(f"   Sin match (top 10): {sorted(sin_match)[:10]}")

        ciiu_slim = df_ciiu[["RAMA4D_STD", "DESCRIPCION_CIIU"]].drop_duplicates(
            "RAMA4D_STD"
        )
        df = df.merge(ciiu_slim, on="RAMA4D_STD", how="left")

        n_con = df["DESCRIPCION_CIIU"].notna().sum()
        n_sin = df["DESCRIPCION_CIIU"].isna().sum()
        print(f"   Con descripción   : {n_con:,} ({n_con/len(df)*100:.1f}%)")
        print(f"   Sin descripción   : {n_sin:,} ({n_sin/len(df)*100:.1f}%)")

        if n_sin > 0 and "RAMA2D_R4" in df.columns:
            df = self._aplicar_fallback_ciiu(df)

        return df

    def merge_divipola(
        self,
        df: pd.DataFrame,
        ruta_divipola: str,
        sheet_name: str = "Departamentos",
        skiprows: int = 9,
    ) -> pd.DataFrame:
        """Hace merge con DIVIPOLA para agregar nombres de departamento.

        Args:
            df: DataFrame con columna DPTO.
            ruta_divipola: Ruta al archivo Excel DIVIPOLA.
            sheet_name: Hoja del Excel.
            skiprows: Filas a saltar en el Excel.

        Returns:
            DataFrame con columna NOMBRE_DPTO.
        """
        if "DPTO" not in df.columns:
            print("⚠️ Columna DPTO no encontrada. Saltando merge DIVIPOLA.")
            return df

        print("\n🔗 Merge con DIVIPOLA...")

        df_depto = pd.read_excel(
            ruta_divipola, sheet_name=sheet_name,
            skiprows=skiprows, converters={"Código": str},
        )

        df["DPTO_STR"] = self._conversor.estandarizar_dpto(df["DPTO"])

        df = df.merge(
            df_depto[["Código", "Nombre"]].rename(
                columns={"Código": "DPTO_STR", "Nombre": "NOMBRE_DPTO"}
            ),
            on="DPTO_STR",
            how="left",
        )

        n_ok = df["NOMBRE_DPTO"].notna().sum()
        print(f"   Departamentos mapeados: {n_ok:,} ({n_ok/len(df)*100:.1f}%)")

        return df

    def _aplicar_fallback_ciiu(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica descripción CIIU de fallback usando el código de 2 dígitos."""
        sin_desc = df["DESCRIPCION_CIIU"].isna()
        rama2d = pd.to_numeric(df.loc[sin_desc, "RAMA2D_R4"], errors="coerce")

        for rango, desc in CIIU_DESCRIPCION_FALLBACK:
            mask_rango = rama2d.apply(lambda x: x in rango if pd.notna(x) else False)
            if mask_rango.any():
                df.loc[sin_desc & mask_rango.reindex(df.index, fill_value=False),
                       "DESCRIPCION_CIIU"] = desc

        n_recuperados = sin_desc.sum() - df["DESCRIPCION_CIIU"].isna().sum()
        if n_recuperados > 0:
            print(f"   Fallback CIIU 2D  : {n_recuperados:,} registros recuperados")

        return df
