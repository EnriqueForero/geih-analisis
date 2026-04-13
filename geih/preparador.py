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
    "COLUMNAS_BOLETIN",
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
    AREA_GEIH_A_CIUDAD,    # v6.0 — mapeo correcto de AREA (2 dígitos)
    DPTOS_13_CIUDADES,     # v6.0 — set oficial de las 13 A.M. del boletín
    DPTOS_10_CIUDADES,     # v6.0 — set oficial de las 10 ciudades intermedias
    POSICION_OCUPACIONAL,  # v6.0 — mapa CISE-93 (jornalero=7, no 8)
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
    "P3069",      # Tamaño empresa (independientes)
    "P6870",      # Tamaño establecimiento (asalariados) — informalidad oficial v6.0
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

# v6.0 — Alias semántico: COLUMNAS_DEFAULT ya contiene todas las
# variables necesarias para replicar el Boletín DANE. Se expone como
# COLUMNAS_BOLETIN para que el código del usuario sea explícito sobre
# su intención cuando esté replicando indicadores oficiales.
COLUMNAS_BOLETIN: List[str] = COLUMNAS_DEFAULT
"""Preset documentado para replicar el Boletín GEIH del DANE.

Equivale a COLUMNAS_DEFAULT pero el nombre comunica la intención al
lector del código:

    df = prep.preparar_base(geih, columnas=COLUMNAS_BOLETIN)
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
        derivar: bool = True,
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
        # Regla unificada (v6.0): el divisor FEX es siempre el número de
        # meses realmente analizados. Casos:
        #
        #   1. meses_filtro=int (ej: 12)             → divisor = 1
        #   2. meses_filtro=list (ej: [10,11,12])    → divisor = len(lista)
        #   3. meses_filtro=None, config.meses_rango → divisor = n_meses del config
        #      (que ya fue sincronizado a len(meses_rango) en __post_init__)
        #   4. meses_filtro=None, config sin rango   → divisor = config.n_meses
        #
        # Antes (v5.x): había una rama "if int then divisor=1 else config.n_meses"
        # que era correcta solo cuando meses_filtro y config.meses_rango eran
        # mutuamente excluyentes. Con meses_rango sincronizado en config, la
        # rama vieja sobre-dividía cuando el usuario pasaba meses_filtro=list
        # y al mismo tiempo tenía config.meses_rango configurado. El cálculo
        # unificado es estable bajo cualquier combinación.
        if isinstance(filtro_final, int):
            n_meses_divisor = 1
        elif isinstance(filtro_final, list):
            n_meses_divisor = len(filtro_final)
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

        # ── Derivación automática de variables de análisis ──
        # v6.0: antes el usuario tenía que llamar agregar_variables_derivadas
        # manualmente después de preparar_base, lo cual era fuente frecuente
        # de KeyError en celdas que usaban 'RAMA', 'DOMINIO', 'SEXO', etc.
        # Ahora es automático. Usuarios que quieran el DataFrame mínimo
        # (solo tipos convertidos + FEX_ADJ) pueden pasar derivar=False.
        if derivar:
            df = self.agregar_variables_derivadas(df)

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

        v6.0 (abril 2026) — expande el set de columnas derivadas para
        cubrir todas las que necesita la replicación del Boletín DANE:

        Columnas siempre añadidas (si las fuentes existen):
          - DPTO_STR       : código departamento estandarizado (2 dígitos)
          - NOMBRE_DPTO    : nombre del departamento
          - SEXO           : 'Hombres' / 'Mujeres' (P3271 — marco 2018)
          - RAMA           : rama de actividad DANE (14 categorías)
          - RAMA_INT       : CIIU 2 dígitos como Int64
          - CIUDAD         : nombre de ciudad/AM
          - NIVEL_GRUPO    : nivel educativo agrupado
          - ANOS_EDUC      : años de educación (para Mincer)
          - INGLABO_SML    : ingreso en múltiplos de SMMLV

        Columnas nuevas en v6.0 (necesarias para el Boletín DANE):
          - DOMINIO        : '13_AM' | 'otras_cab' | 'rural'
          - POSICION_OCU   : 9 categorías CISE-93 publicadas por DANE
          - EDAD_RANGO     : '15-24', '25-54', '55+' (rangos del boletín)
          - INFORMAL       : 1 si informal según 17ª CIET, 0 formal, NaN
                             si la base no tiene las variables requeridas

        Args:
            df: DataFrame preparado.

        Returns:
            El mismo DataFrame con columnas derivadas añadidas.
        """
        # ── Departamento ──────────────────────────────────────
        if "DPTO" in df.columns:
            df["DPTO_STR"] = self._conversor.estandarizar_dpto(df["DPTO"])
            df["NOMBRE_DPTO"] = df["DPTO_STR"].map(DEPARTAMENTOS)

        # ── Sexo (marco 2018: P3271) ──────────────────────────
        if "P3271" in df.columns:
            df["SEXO"] = df["P3271"].map({1: "Hombres", 2: "Mujeres"})

        # ── Rama CIIU ─────────────────────────────────────────
        if "RAMA2D_R4" in df.columns:
            df["RAMA_INT"] = pd.to_numeric(
                df["RAMA2D_R4"], errors="coerce"
            ).round(0).astype("Int64")
            df["RAMA"] = self.mapear_rama_ciiu(df["RAMA2D_R4"])

        # ── Ciudad (por DPTO y AREA) ──────────────────────────
        if "DPTO_STR" in df.columns:
            df["CIUDAD"] = df["DPTO_STR"].map(DPTO_A_CIUDAD)

        if "AREA" in df.columns:
            area_str = self._conversor.estandarizar_area(df["AREA"])
            ciudad_area = area_str.map(AREA_A_CIUDAD)
            if "CIUDAD" in df.columns:
                df["CIUDAD"] = ciudad_area.combine_first(df["CIUDAD"])
            else:
                df["CIUDAD"] = ciudad_area

        # ── DOMINIO geográfico del Boletín DANE (v6.0) ───────
        # Los 4 dominios mutuamente excluyentes que define el Boletín:
        #   1. "13_AM"      → AREA ∈ DPTOS_13_CIUDADES y CLASE == 1
        #   2. "10_ciudades"→ AREA ∈ DPTOS_10_CIUDADES y CLASE == 1
        #   3. "otras_cab"  → CLASE == 1 y AREA fuera de los dos sets
        #   4. "rural"      → CLASE == 2 (centros poblados y rural disperso)
        #
        # FIX v6.0: Antes se usaba `AREA_A_CIUDAD.keys()` como set de las
        # 13 A.M. — pero ese diccionario contiene DIVIPOLA de 5 dígitos
        # (no AREA de 2 dígitos del microdato GEIH) y además incluye TODAS
        # las ciudades, no solo las 13 principales. Resultado del bug:
        # el filtro DOMINIO=='13_AM' devolvía 0 filas. Se reemplaza por
        # DPTOS_13_CIUDADES, set oficial de 2 dígitos del Boletín.
        if "AREA" in df.columns and "CLASE" in df.columns:
            area_str = df["AREA"].astype(str).str.strip().str.zfill(2)
            clase_num = pd.to_numeric(df["CLASE"], errors="coerce")
            es_13 = area_str.isin(DPTOS_13_CIUDADES)
            es_10 = area_str.isin(DPTOS_10_CIUDADES)

            dominio = pd.Series("otros", index=df.index, dtype="object")
            dominio[(clase_num == 1) & es_13] = "13_AM"
            dominio[(clase_num == 1) & es_10] = "10_ciudades"
            dominio[(clase_num == 1) & ~es_13 & ~es_10] = "otras_cab"
            dominio[clase_num == 2] = "rural"
            df["DOMINIO"] = dominio

        # ── Posición ocupacional CISE-93 (v6.0) ──────────────
        # FIX v6.0: el mapa inline anterior tenía cruzados los códigos
        # 7 y 8. La codificación CISE-93 oficial (confirmada con la hoja
        # "Ocupados TN_posición" del anexo DANE) es:
        #   7 = Jornalero o peón                              (no 8)
        #   8 = Trabajador sin remuneración en otras empresas (no 7)
        # Se usa el diccionario POSICION_OCUPACIONAL del config para
        # mantener una sola fuente de verdad.
        if "P6430" in df.columns:
            df["POSICION_OCU"] = pd.to_numeric(
                df["P6430"], errors="coerce"
            ).map(POSICION_OCUPACIONAL)

        # ── Rango de edad (rangos del boletín DANE) ──────────
        if "P6040" in df.columns:
            edad = pd.to_numeric(df["P6040"], errors="coerce")
            rango = pd.Series(pd.NA, index=df.index, dtype="object")
            rango[(edad >= 15) & (edad <= 24)] = "15-24"
            rango[(edad >= 25) & (edad <= 54)] = "25-54"
            rango[edad >= 55] = "55+"
            df["EDAD_RANGO"] = rango

        # ── Informalidad 17ª CIET (v6.0 — definición DANE) ───
        # Nota metodológica DANE:
        # https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/
        #   Nueva_medicion_informalidad.pdf
        #
        # Variables requeridas:
        #   P6430 — posición ocupacional (CISE-93, jornalero=7)
        #   P6920 — cotización a pensión (1=sí, 2=no, 3=ya pensionado)
        #   P6870 — tamaño del establecimiento (1=solo, 2..9 = rangos)
        #
        # Reglas de clasificación:
        #  (a) Asalariados (P6430 ∈ {1,2}): formales si cotizan pensión.
        #  (b) Empleada doméstica (P6430 = 3): misma regla que (a).
        #  (c) Cuenta propia (P6430 = 4): formales si cotizan pensión.
        #  (d) Patrón/empleador (P6430 = 5): formales si empresa > 5
        #      empleados (P6870 ∈ {6..9}, códigos 11+ trabajadores) Y
        #      cotizan a pensión.
        #  (e) Jornalero o peón (P6430 = 7): regla (a).
        #  (f) Trabajador familiar sin remuneración (6), trabajador sin
        #      remuneración en otras empresas (8) y "Otro" (9):
        #      informales por definición.
        #
        # FIX v6.0 vs versión anterior:
        #   - Código jornalero corregido: P6430=7 (CISE-93), no 8.
        #   - Patrones grandes ahora se clasifican como formales si cumplen
        #     ambas condiciones (tamaño + cotización), reduciendo el sesgo
        #     de +1-3 p.p. en la medición rural.
        #   - Si P6870 no está, se aplica la versión sin tamaño y se avisa.
        if "P6430" in df.columns and "P6920" in df.columns:
            pos = pd.to_numeric(df["P6430"], errors="coerce")
            cot = pd.to_numeric(df["P6920"], errors="coerce")
            tam = (pd.to_numeric(df["P6870"], errors="coerce")
                   if "P6870" in df.columns else None)

            informal = pd.Series(pd.NA, index=df.index, dtype="Int8")

            # (a)+(b)+(e) Asalariados, doméstica y jornaleros: cotización
            es_empleado = pos.isin([1, 2, 3, 7])
            informal[es_empleado & (cot == 1)] = 0
            informal[es_empleado & (cot != 1)] = 1

            # (c) Cuenta propia: cotización pensional
            informal[(pos == 4) & (cot == 1)] = 0
            informal[(pos == 4) & (cot != 1)] = 1

            # (d) Patrón / empleador: tamaño + cotización
            if tam is not None:
                empresa_grande = tam >= 6  # P6870: 6 = "11 a 19 personas"+
                informal[(pos == 5) & empresa_grande & (cot == 1)] = 0
                informal[(pos == 5) & ~(empresa_grande & (cot == 1))] = 1
            else:
                # Sin P6870 caemos a la regla simple (sesgo conocido)
                informal[(pos == 5) & (cot == 1)] = 0
                informal[(pos == 5) & (cot != 1)] = 1

            # (f) Informales por definición: familiares sin rem., otro
            informal[pos.isin([6, 8, 9])] = 1

            df["INFORMAL"] = informal

            if tam is None:
                print(
                    "ℹ️  INFORMAL calculada SIN P6870 (tamaño de empresa). "
                    "Esperable sesgo de +1-3 p.p. vs Boletín DANE en rural. "
                    "Agregue P6870 vía columnas_extra para definición exacta."
                )
        else:
            faltantes = sorted({"P6430", "P6920"} - set(df.columns))
            print(
                f"ℹ️  INFORMAL no derivada: faltan {faltantes}. "
                f"Agréguelas vía columnas_extra al consolidar."
            )

        # ── Nivel educativo ──────────────────────────────────
        if "P3042" in df.columns:
            df["NIVEL_GRUPO"] = df["P3042"].map(NIVELES_AGRUPADOS)
            df["ANOS_EDUC"] = df["P3042"].map(P3042_A_ANOS)

        # ── Ingreso en SMMLV ─────────────────────────────────
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
