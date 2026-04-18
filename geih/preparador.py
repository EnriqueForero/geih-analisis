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
    "COLUMNAS_BOLETIN",
    "COLUMNAS_DEFAULT",
    "MergeCorrelativas",
    "PreparadorGEIH",
]


import gc
from typing import Optional, Union

import numpy as np
import pandas as pd

from .config import (
    AREA_GEIH_A_CIUDAD,  # v6.0 — mapeo correcto de AREA (2 dígitos)
    CIIU_DESCRIPCION_FALLBACK,
    DEPARTAMENTOS,
    DPTO_A_CIUDAD,
    DPTOS_10_CIUDADES,  # v6.0 — set oficial de las 10 ciudades intermedias
    DPTOS_13_CIUDADES,  # v6.0 — set oficial de las 13 A.M. del boletín
    NIVELES_AGRUPADOS,
    P3042_A_ANOS,
    POSICION_OCUPACIONAL,  # v6.0 — mapa CISE-93 (jornalero=7, no 8)
    RAMAS_DANE,
    TABLA_CIIU_RAMAS,
    ConfigGEIH,
)
from .informalidad import clasificar_informalidad_dane
from .utils import ConversorTipos

# ═════════════════════════════════════════════════════════════════════
# COLUMNAS POR DEFECTO — EXTENSIBLE DESDE EL NOTEBOOK
# ═════════════════════════════════════════════════════════════════════

COLUMNAS_DEFAULT: list[str] = [
    # ── Identificación y factor de expansión ──────────────────────
    "FEX_C18",
    "MES_NUM",
    # ── Características generales (E/F/G) ─────────────────────────
    "P3271",  # Sexo (1=H, 2=M)
    "P6040",  # Edad
    "P6080",  # Autorreconocimiento étnico
    "P3042",  # Nivel educativo (1-13)
    "P3043S1",  # Campo de formación (CINE-F) — proxy bilingüismo
    "P6090",  # Afiliado salud (1=Sí)
    "CLASE",  # Zona (1=Cabecera/Urbano, 2=Rural)
    "DPTO",  # Departamento (código 2 dígitos)
    "P2057",  # ¿Se considera campesino?
    "P2059",  # ¿Alguna vez fue campesino?
    # Discapacidad — Escala Washington (8 dimensiones)
    "P1906S1",
    "P1906S2",
    "P1906S3",
    "P1906S4",
    "P1906S5",
    "P1906S6",
    "P1906S7",
    "P1906S8",
    # ── Fuerza de trabajo (H) ─────────────────────────────────────
    "FT",
    "PET",
    "OCI",
    "DSI",
    "FFT",
    "P6240",  # Actividad semana pasada
    # ── Ocupados (I) — ingresos y tiempo ──────────────────────────
    "INGLABO",  # Ingreso laboral mensual
    "P6500",  # Salario bruto declarado
    "P6800",  # Horas normales semana
    "P6850",  # Horas reales semana pasada
    "P7130",  # Desea cambiar trabajo
    "AREA",  # Municipio 5 dígitos (32 ciudades)
    # ── Posición ocupacional ───────────────────────────────────────
    "P6430",  # Posición ocupacional (CISE-93 1-9)
    # ── Forma de trabajo (independientes) ─────────────────────────
    "P6765",  # 1-8. P6765=7 → "tiene negocio"
    # ── Informalidad 17ª CIET (sector + ocupación) ────────────────
    # Sector — ASALARIADOS
    "P3045S1",  # ¿Empresa registrada CC? (asalariados)
    "P3046",  # ¿Empresa tiene contabilidad? (asalariados)
    # Sector — INDEPENDIENTES SIN NEGOCIO
    "P3051",  # ¿Tiene negocio, empresa, finca?
    "P3065",  # ¿Registrada CC? (sin negocio)
    "P3066",  # ¿Tiene contabilidad? (sin negocio) — CRÍTICA
    # Sector — INDEPENDIENTES CON NEGOCIO
    "P3067",  # ¿Registró negocio CC? (con negocio)
    "P3067S1",  # ¿Renovó registro? (1=Sí, 2=No)
    "P3067S2",  # Año de última renovación                        ← NUEVA
    "P6775",  # ¿Lleva contabilidad? (negocio)                  ← NUEVA
    "P3068",  # ¿Separa gastos negocio/hogar?
    # ── Tamaño y oficio ───────────────────────────────────────────
    "P3069",  # Tamaño empresa (1=solo, 4=6-10, ...)
    "OFICIO_C8",  # Oficio CIUO-08 (4 caracteres) — CRÍTICA
    # ── Rama de actividad ─────────────────────────────────────────
    "RAMA2D_R4",  # CIIU 2 dígitos (excluir ramas 84 y 99)
    "RAMA4D_R4",  # CIIU 4 dígitos
    # ── Salud ─────────────────────────────────────────────────────
    # P6090 ya capturado en Características generales (informativa)
    "P6100",  # Régimen (1=Contrib, 2=Esp, 3=Subs, 9=NS)       ← NUEVA
    "P6110",  # ¿Quién paga salud? (1, 2, 4 = empleador)        ← NUEVA
    # ── Pensión ───────────────────────────────────────────────────
    "P6920",  # ¿Cotiza pensión? (1=Sí, 3=Pensionado)
    "P6930",  # Fondo de pensiones (1, 2, 3 = válidos)
    "P6940",  # ¿Quién paga pensión? (1, 3 = empleador)         ← NUEVA
    # ── Contrato ──────────────────────────────────────────────────
    "P6440",  # ¿Tiene contrato?
    "P6450",  # ¿Verbal o escrito? (2=Escrito)
    "P6460",  # ¿Contrato indefinido?
    # ── Autonomía laboral ─────────────────────────────────────────
    "P3047",  # ¿Quién decide horario?
    "P3048",  # ¿Quién decide qué producir?
    "P3049",  # ¿Quién decide precio?
    # ── Tenencia de tierra y actividad agropecuaria (v5.1) ────────
    "P3056",  # Tipo actividad negocio (1=mercancías, 2=agropecuario)
    "P3064",  # ¿Propietario de la tierra? (1=Sí, 2=No)
    "P3064S1",  # Valor estimado arriendo terreno (COP/mes)
    # ── Compensación ──────────────────────────────────────────────
    "P6510S1",  # Horas extras
    "P6580S1",  # Bonificaciones
    "P6585S1A1",  # Auxilio alimentación
    "P6585S2A1",  # Auxilio transporte
    # ── Variables de alto valor analítico ─────────────────────────
    "P1802",  # Alcance mercado (1-6, 6=Exportación)
    "P3363",  # ¿Cómo consiguió empleo?
    "P3364",  # ¿Retención en la fuente?
    "P6400",  # ¿Trabaja donde lo contrataron?
    "P6410",  # Tipo intermediación (EST, CTA)
    # ── No ocupados (J) ───────────────────────────────────────────
    "P7250",  # Semanas buscando trabajo
    "P6300",  # ¿Desea trabajar? (FFT con deseo)
    "P6310",  # ¿Disponible para trabajar?
    "P7140S2",  # Razón: mejorar ingresos
    # ── Otras formas de trabajo (K) ───────────────────────────────
    "P3054",  # Autoconsumo bienes
    "P3054S1",  # Horas autoconsumo bienes
    "P3055",  # Autoconsumo servicios
    "P3055S1",  # Horas autoconsumo servicios
    "P3057",  # Formación no remunerada
    # ── Migración (L) ─────────────────────────────────────────────
    "P3370",  # ¿Dónde vivía hace 12 meses?
    "P3370S1",  # Departamento hace 12 meses
    "P3376",  # País de nacimiento
    "P3378S1",  # Año de llegada a Colombia
    # ── Otros ingresos (M) ────────────────────────────────────────
    "P7422",  # Arriendos recibidos
    "P7500S1",  # Pensiones
    "P7500S1A1",  # Monto pensiones
    "P7500S2",  # Ayudas hogares nacionales
    "P7500S2A1",  # Monto ayudas
    "P7500S3",  # Ayudas institucionales
    "P7510S2",  # Remesas del exterior
    "P7510S2A1",  # Monto remesas
]
"""Columnas extraídas por defecto en preparar_base().

Para agregar variables adicionales desde el notebook sin modificar
este archivo, use el parámetro `columnas_extra`:

    prep = PreparadorGEIH(config=config)
    df = prep.preparar_base(geih, columnas_extra=["P3069", "P6880"])

Las columnas extra se fusionan con esta lista. Si una columna no
existe en la base, se ignora silenciosamente (sin error).
"""

# v6.0 — Alias semántico: COLUMNAS_DEFAULT ya contiene todas las
# variables necesarias para replicar el Boletín DANE. Se expone como
# COLUMNAS_BOLETIN para que el código del usuario sea explícito sobre
# su intención cuando esté replicando indicadores oficiales.
COLUMNAS_BOLETIN: list[str] = list(COLUMNAS_DEFAULT)
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
        df = prep.preparar_base(geih, columnas_extra=["P3069", "P3376S1"])
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()
        self._conversor = ConversorTipos()

    # ── Método principal ───────────────────────────────────────

    def preparar_base(
        self,
        df_raw: pd.DataFrame,
        columnas: Optional[list[str]] = None,
        columnas_extra: Optional[list[str]] = None,
        meses_filtro: Optional[Union[int, list[int]]] = None,
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
            df = prep.preparar_base(geih, columnas_extra=["P3069", "P6880"])

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
                print(f"⚠️  Columnas extra no encontradas en la base: {sorted(extra_faltantes)}")

        # ── Resolver filtro de meses ───────────────────────────
        # Prioridad: meses_filtro explícito > config.meses_rango > None
        filtro_final: Optional[Union[int, list[int]]] = meses_filtro
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
                    f"meses_filtro debe ser int o list[int], recibido: {type(filtro_final)}"
                )
            df = df_raw.loc[mask, cols_ok].copy()
        else:
            df = df_raw[cols_ok].copy()

        gc.collect()

        # ── Convertir tipos numéricos ──────────────────────────
        cols_str = {"DPTO", "RAMA2D_R4", "RAMA4D_R4", "AREA", "CLASE"}
        self._conversor.convertir_columnas_numericas(df, cols_ok, excluir=list(cols_str))

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
            df["RAMA_INT"] = (
                pd.to_numeric(df["RAMA2D_R4"], errors="coerce").round(0).astype("Int64")
            )
            df["RAMA"] = self.mapear_rama_ciiu(df["RAMA2D_R4"])

        # ── Ciudad (por DPTO y AREA) ──────────────────────────
        if "DPTO_STR" in df.columns:
            df["CIUDAD"] = df["DPTO_STR"].map(DPTO_A_CIUDAD)

        if "AREA" in df.columns:
            # AREA en GEIH es código de dominio de 2 dígitos, no DIVIPOLA 5
            area_2d = df["AREA"].astype(str).str.strip().str.zfill(2)
            ciudad_area = area_2d.map(AREA_GEIH_A_CIUDAD)
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
            df["POSICION_OCU"] = pd.to_numeric(df["P6430"], errors="coerce").map(
                POSICION_OCUPACIONAL
            )

        # ── Rango de edad (rangos del boletín DANE) ──────────
        if "P6040" in df.columns:
            edad = pd.to_numeric(df["P6040"], errors="coerce")
            rango = pd.Series(pd.NA, index=df.index, dtype="object")
            rango[(edad >= 15) & (edad <= 24)] = "15-24"
            rango[(edad >= 25) & (edad <= 54)] = "25-54"
            rango[edad >= 55] = "55+"
            df["EDAD_RANGO"] = rango

        # ── Informalidad 17ª CIET (v7.0 — definición DANE completa) ──
        # Fuente: Nota metodológica DANE "Nueva medición de informalidad
        # laboral" (julio 2022), basada en 17ª CIET (OIT 2003) y Manual
        # de Informalidad INE Chile.
        #
        # La informalidad laboral tiene DOS dimensiones:
        #   1. SECTOR: ¿la unidad económica (empresa) es formal o informal?
        #      Criterios: registro mercantil (Cámara de Comercio) y/o
        #      contabilidad completa. Proxy: tamaño de empresa (P3069).
        #   2. OCUPACIÓN: ¿el puesto de trabajo es formal o informal?
        #      Criterios: afiliación a salud contributiva Y cotización a
        #      pensión, ambas pagadas (total o parcialmente) por el empleador.
        #
        # Informal = sector_informal OR (sector_formal AND ocupación_informal)
        #
        # Variables requeridas:
        #   P6430    — posición ocupacional CISE-93
        #   P6920    — cotiza pensión (1=Sí, 2=No, 3=Ya pensionado)
        #   P6090    — régimen de salud (1=Contributivo, 2=Especial, 3=Subsidiado)
        #   P3069    — tamaño empresa (1-10)
        #   P3045S1  — ¿empresa registrada Cámara de Comercio? (asalariados)
        #   P3046    — ¿empresa tiene contabilidad? (asalariados)
        #   P3051    — ¿tiene negocio? (independientes)
        #   P3065    — ¿registrada Cámara Comercio? (indep. sin negocio)
        #   P3067    — ¿registró negocio Cámara Comercio? (indep. con negocio)
        #   P3067S1  — ¿renovó registro?
        #   P3068    — ¿contabilidad separa gastos negocio/hogar?
        #
        # Si faltan las variables de sector (P3045S1, P3067, etc.), se cae
        # a la aproximación simplificada (solo P6430+P6920+P3069).
        df = self._clasificar_informalidad(df)

        # ── Nivel educativo ──────────────────────────────────
        if "P3042" in df.columns:
            df["NIVEL_GRUPO"] = df["P3042"].map(NIVELES_AGRUPADOS)
            df["ANOS_EDUC"] = df["P3042"].map(P3042_A_ANOS)

        # ── Ingreso en SMMLV ─────────────────────────────────
        if "INGLABO" in df.columns:
            df["INGLABO_SML"] = df["INGLABO"] / self.config.smmlv

        return df

    # ── Informalidad 17ª CIET ──────────────────────────────────
    # _clasificar_informalidad (delegación al módulo oficial)
    def _clasificar_informalidad(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clasifica informalidad laboral según SINTAXIS OFICIAL DANE.

        Delega a `geih.informalidad.clasificar_informalidad_dane`, que es
        una traducción literal del código SAS publicado por el DANE en el
        anexo "anex-GEIHEISS-dic2025-feb2026.xlsx".

        El año de referencia para la regla del registro mercantil
        (P3067S2 >= ANIO−1) se toma de:
        1. self.config.anio si está disponible.
        2. Una columna PER del DataFrame.
        3. El año actual del sistema.

        Args:
            df: DataFrame con las variables GEIH preparadas.

        Returns:
            El mismo DataFrame con la columna `INFORMAL` añadida
            (Int8: 1=informal, 0=formal, NA=sin información).
        """
        # Determinar año de referencia
        anio_ref = None
        if hasattr(self, "config") and hasattr(self.config, "anio"):
            anio_ref = self.config.anio

        print("\n📊 Calculando informalidad según sintaxis OFICIAL DANE...")
        df["INFORMAL"] = clasificar_informalidad_dane(df, anio_referencia=anio_ref, verbose=True)

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
            ruta_ciiu,
            sheet_name=sheet_name,
            converters={"RAMA4D_R4": str},
        )

        df["RAMA4D_STD"] = self._conversor.estandarizar_ciiu4(df["RAMA4D_R4"])
        df_ciiu["RAMA4D_STD"] = self._conversor.estandarizar_ciiu4(df_ciiu["RAMA4D_R4"])

        rama_df = set(df["RAMA4D_STD"].dropna().unique())
        rama_ciiu = set(df_ciiu["RAMA4D_STD"].dropna().unique())
        match = rama_df & rama_ciiu
        sin_match = rama_df - rama_ciiu
        print(f"   Códigos en base   : {len(rama_df)}")
        print(f"   Códigos en CIIU   : {len(rama_ciiu)}")
        print(
            f"   Con match         : {len(match)} ({len(match) / max(len(rama_df), 1) * 100:.0f}%)"
        )
        if sin_match:
            print(f"   Sin match (top 10): {sorted(sin_match)[:10]}")

        ciiu_slim = df_ciiu[["RAMA4D_STD", "DESCRIPCION_CIIU"]].drop_duplicates("RAMA4D_STD")
        df = df.merge(ciiu_slim, on="RAMA4D_STD", how="left")

        n_con = df["DESCRIPCION_CIIU"].notna().sum()
        n_sin = df["DESCRIPCION_CIIU"].isna().sum()
        print(f"   Con descripción   : {n_con:,} ({n_con / len(df) * 100:.1f}%)")
        print(f"   Sin descripción   : {n_sin:,} ({n_sin / len(df) * 100:.1f}%)")

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
            ruta_divipola,
            sheet_name=sheet_name,
            skiprows=skiprows,
            converters={"Código": str},
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
        print(f"   Departamentos mapeados: {n_ok:,} ({n_ok / len(df) * 100:.1f}%)")

        return df

    def _aplicar_fallback_ciiu(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica descripción CIIU de fallback usando el código de 2 dígitos."""
        sin_desc = df["DESCRIPCION_CIIU"].isna()
        rama2d = pd.to_numeric(df.loc[sin_desc, "RAMA2D_R4"], errors="coerce")

        for rango, desc in CIIU_DESCRIPCION_FALLBACK:
            # mask_rango = rama2d.apply(lambda x: x in rango if pd.notna(x) else False)
            mask_rango = rama2d.apply(lambda x, r=rango: x in r if pd.notna(x) else False)
            if mask_rango.any():
                df.loc[
                    sin_desc & mask_rango.reindex(df.index, fill_value=False), "DESCRIPCION_CIIU"
                ] = desc

        n_recuperados = sin_desc.sum() - df["DESCRIPCION_CIIU"].isna().sum()
        if n_recuperados > 0:
            print(f"   Fallback CIIU 2D  : {n_recuperados:,} registros recuperados")

        return df


# ════════════════════════════════════════════════════════════════════════════
# 📄 geih/profiler.py
#    Categoría: codigo
