"""
geih.informalidad — Implementación oficial DANE de la informalidad laboral.

Esta es una TRADUCCIÓN LITERAL Y EXACTA del código SAS oficial publicado
por el DANE en el anexo "anex-GEIHEISS-dic2025-feb2026.xlsx", hojas
"Código_SAS" y "Código_STATA". Fuente:

    https://www.dane.gov.co/index.php/estadisticas-por-tema/
    mercado-laboral/empleo-informal-y-seguridad-social

Convención del DANE (importante):
    EI = 1  →  ocupado FORMAL
    EI = 0  →  ocupado INFORMAL
    EI = .  →  no aplica (e.g. P6430=3 que se ignora)

Convención de la librería interna `geih`:
    INFORMAL = 1  →  ocupado informal
    INFORMAL = 0  →  ocupado formal
    INFORMAL = NA →  sin información suficiente

La función `clasificar_informalidad_dane` calcula EI literalmente como en
SAS y luego invierte la convención al final para producir INFORMAL.

Variables requeridas:

    CRÍTICAS (sin estas el cálculo es aproximado):
      P6430    — Posición ocupacional (CISE-93 1-9)
      P6765    — Forma de trabajo (1-8). 7 = "tiene negocio"
      P3045S1  — ¿Empresa registrada CC? (asalariados)
      P3046    — ¿Empresa tiene contabilidad? (asalariados)
      P3065    — ¿Registrada CC? (indep. sin negocio)
      P3066    — ¿Tiene contabilidad? (indep. sin negocio)
      P3067    — ¿Registró negocio CC? (indep. con negocio)
      P3067S1  — ¿Renovó? (1=Sí, 2=No)
      P3067S2  — Año de última renovación
      P6775    — ¿Lleva contabilidad? (negocio)
      P3068    — ¿Separa gastos negocio/hogar?
      P3069    — Tamaño empresa (1=solo, 4=6-10, ...)
      P6100    — Régimen salud (1=Contrib, 2=Esp, 3=Subs, 9=NS)
      P6110    — ¿Quién paga salud? (1, 2, 4 = empleador participa)
      P6450    — ¿Contrato escrito? (2=Escrito)
      P6920    — ¿Cotiza pensión? (1=Sí, 3=Pensionado)
      P6930    — Fondo de pensiones (1, 2, 3 = válidos)
      P6940    — ¿Quién paga pensión? (1, 3 = empleador participa)
      RAMA2D_R4 — CIIU 2 dígitos (84, 99 → formal por definición)
      OFICIO_C8 — Oficio CIUO 08 (4 caracteres). Solo discriminan los
                  primeros 2 dígitos: 00-20 = directivos/profesionales,
                  21+ = técnicos/operarios.

    AÑO de referencia (para P3067S2):
      Se calcula como (año_de_la_encuesta − 1).
      Por defecto, el módulo usa el año de PER si está disponible
      (variable de período de la GEIH), o el año en curso del sistema.

Notas de adaptación:
    1. SAS usa cadenas vs Python usa numérico para OFICIO_C8_2D. Aquí
       se trabaja siempre numérico.
    2. SAS usa `IF ... ELSE IF ...` con cortocircuito. En pandas se
       implementa con máscaras booleanas y asignaciones secuenciales.
       Cada regla SOLO afecta a las filas donde EI sigue NA al momento
       de evaluarse.
    3. La sintaxis oficial reemplaza P3068 == 9 por P3068 == 3 desde
       2023; aquí se aceptan ambos.
    4. Si una variable crítica no está en el DataFrame, se imprime un
       mensaje de advertencia y la función degrada elegantemente.

Autor: Néstor Enrique Forero Herrera (ProColombia)
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

__all__ = [
    "VARIABLES_CRITICAS",
    "VARIABLES_REQUERIDAS",
    "clasificar_informalidad_dane",
]


# ═════════════════════════════════════════════════════════════════════
# Variables que la sintaxis SAS oficial del DANE consume
# ═════════════════════════════════════════════════════════════════════

VARIABLES_REQUERIDAS: set[str] = {
    # Posición ocupacional
    "P6430",
    # Forma de trabajo (independientes)
    "P6765",
    # Sector — asalariados
    "P3045S1",
    "P3046",
    # Sector — independientes sin negocio
    "P3065",
    "P3066",
    # Sector — independientes con negocio
    "P3067",
    "P3067S1",
    "P3067S2",
    "P6775",
    "P3068",
    # Tamaño y oficio
    "P3069",
    "OFICIO_C8",
    # Salud
    "P6100",
    "P6110",
    # Pensión
    "P6920",
    "P6930",
    "P6940",
    # Contrato (para SALUD vía P6450 cuando régimen es 9)
    "P6450",
    # Rama (para excluir 84 y 99)
    "RAMA2D_R4",
}
"""Variables que la sintaxis SAS oficial del DANE requiere para
clasificar correctamente."""

VARIABLES_CRITICAS: set[str] = {
    "P6430",
    "P6765",
    "P3045S1",
    "P3046",
    "P3065",
    "P3067",
    "P6775",
    "P3069",
    "P6100",
    "P6110",
    "P6920",
    "P6940",
    "RAMA2D_R4",
}
"""Subconjunto sin el cual el cálculo será visiblemente diferente
del Excel oficial."""


# ═════════════════════════════════════════════════════════════════════
# Función pública
# ═════════════════════════════════════════════════════════════════════


def clasificar_informalidad_dane(
    df: pd.DataFrame,
    *,
    anio_referencia: int | None = None,
    verbose: bool = True,
) -> pd.Series:
    """Clasifica informalidad laboral según sintaxis OFICIAL DANE.

    Traducción LITERAL del código SAS publicado por el DANE en el
    Excel anex-GEIHEISS-dic2025-feb2026.xlsx.

    Args:
        df: DataFrame con las columnas listadas en `VARIABLES_REQUERIDAS`.
            Las columnas que falten se tratan como totalmente NA.
        anio_referencia: Año de la encuesta (e.g., 2025). El umbral de
            renovación del registro mercantil se calcula como
            `anio_referencia − 1`. Si None, se intenta deducir desde
            `df["PER"]` o desde el sistema.
        verbose: Imprimir mensajes de cobertura y advertencias.

    Returns:
        pd.Series Int8 con valores:
            0 = ocupado formal
            1 = ocupado informal
            <NA> = no aplica (P6430=3) o sin información suficiente

        Esta convención (1=informal) es la INVERSA del SAS (donde
        EI=1=formal); la inversión se hace para mantener compatibilidad
        con la columna INFORMAL preexistente del proyecto.
    """
    # ──────────────────────────────────────────────────────────────
    # 1. Determinar año de referencia
    # ──────────────────────────────────────────────────────────────
    if anio_referencia is None:
        if "PER" in df.columns:
            per_vals = pd.to_numeric(df["PER"], errors="coerce").dropna()
            if len(per_vals) > 0:
                anio_referencia = int(per_vals.iloc[0])
        if anio_referencia is None:
            anio_referencia = datetime.now().year

    anios_umbral = anio_referencia - 1  # ANIOS = PER - 1 en SAS

    if verbose:
        print(
            f"ℹ️  Informalidad DANE: año referencia={anio_referencia}, "
            f"umbral renovación P3067S2 >= {anios_umbral}"
        )

    # ──────────────────────────────────────────────────────────────
    # 2. Reportar variables faltantes
    # ──────────────────────────────────────────────────────────────
    cols_presentes = set(df.columns)
    faltantes_criticas = VARIABLES_CRITICAS - cols_presentes
    if faltantes_criticas and verbose:
        print(f"⚠️  Variables CRÍTICAS faltantes: {sorted(faltantes_criticas)}")
        print("    El cálculo será aproximado.")

    faltantes_total = VARIABLES_REQUERIDAS - cols_presentes
    if faltantes_total and verbose:
        print(f"ℹ️  Variables faltantes (se tratan como NA): {sorted(faltantes_total)}")

    # ──────────────────────────────────────────────────────────────
    # 3. Helper: cargar columna como Series numérica, NA si no existe
    # ──────────────────────────────────────────────────────────────
    def _num(col: str) -> pd.Series:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
        return pd.Series(np.nan, index=df.index, dtype="float64")

    # ──────────────────────────────────────────────────────────────
    # 4. Cargar todas las variables
    # ──────────────────────────────────────────────────────────────
    P6430 = _num("P6430")
    P6765 = _num("P6765")
    P3045S1 = _num("P3045S1")
    P3046 = _num("P3046")
    P3065 = _num("P3065")
    P3066 = _num("P3066")
    P3067 = _num("P3067")
    P3067S1 = _num("P3067S1")
    P3067S2 = _num("P3067S2")
    P6775 = _num("P6775")
    P3068 = _num("P3068")
    P3069 = _num("P3069")
    P6100 = _num("P6100")
    P6110 = _num("P6110")
    P6450 = _num("P6450")
    P6920 = _num("P6920")
    P6930 = _num("P6930")
    P6940 = _num("P6940")

    # ──────────────────────────────────────────────────────────────
    # 5. Rama 2 dígitos como NUMÉRICO (en SAS: numérico)
    # ──────────────────────────────────────────────────────────────
    if "RAMA2D_R4" in df.columns:
        # Puede venir como string ("84") o numérico (84). Convertir.
        RAMA2D = pd.to_numeric(df["RAMA2D_R4"], errors="coerce")
    else:
        RAMA2D = pd.Series(np.nan, index=df.index, dtype="float64")

    # ──────────────────────────────────────────────────────────────
    # 6. Oficio CIUO_C8 — extraer 2 primeros dígitos como numérico
    # ──────────────────────────────────────────────────────────────
    if "OFICIO_C8" in df.columns:
        # OFICIO_C8 puede ser string de 4 chars o numérico.
        # SAS hace SUBSTR(OFICIO_C8, 1, 2) → primeros 2 chars.
        oficio_str = df["OFICIO_C8"].astype(str).str.zfill(4).str[:2]
        OFICIO2D = pd.to_numeric(oficio_str, errors="coerce")
    else:
        # Sin OFICIO_C8, los nodos que dependen de él se vuelven NA;
        # los conserva como NA (informal por defecto al final).
        OFICIO2D = pd.Series(np.nan, index=df.index, dtype="float64")

    # ──────────────────────────────────────────────────────────────
    # 7. PRIMERO calcular FORMAL (variable de SECTOR)
    #    Convención SAS: FORMAL=1 → sector formal; FORMAL=0 → informal
    # ──────────────────────────────────────────────────────────────
    FORMAL = pd.Series(np.nan, index=df.index, dtype="float64")

    def _set(mask: pd.Series, value: float, only_unset: bool = True):
        """Asignar `value` a FORMAL en filas donde `mask` es True y FORMAL
        sigue NA (replica el cortocircuito IF/ELSE IF de SAS)."""
        if only_unset:
            mask = mask.fillna(False) & FORMAL.isna()
        else:
            mask = mask.fillna(False)
        FORMAL.loc[mask] = value

    # ── SECTOR INFORMAL — reglas iniciales (orden SAS) ────────────
    # IF P6430=3 THEN FORMAL=. ELSE          (empleado doméstico → no aplica aquí)
    _set(P6430 == 3, np.nan, only_unset=False)
    # En SAS no se asigna nada (queda missing); en pandas dejamos NA.
    # Pero es importante NO sobreescribir esto después → marcar como
    # "ya procesada" simulando con un sentinel. Para ello, usamos la
    # variable auxiliar `bloqueada` que recordará "fila ya tratada".
    bloqueada = P6430 == 3

    # IF P6430=6 THEN FORMAL=0 ELSE          (TFSR → informal por def)
    _set((P6430 == 6) & ~bloqueada, 0)
    # IF Rama2d_R4 IN (84,99) THEN FORMAL=1 ELSE
    _set(RAMA2D.isin([84, 99]) & ~bloqueada, 1)
    # IF P6430=8 THEN FORMAL=0 ELSE          (Otro → informal)
    _set((P6430 == 8) & ~bloqueada, 0)

    # ── ASALARIADOS ────────────────────────────────────────────────
    # IF P6430 = 2 THEN FORMAL=1 ELSE        (gobierno → sector formal)
    _set(P6430 == 2, 1)

    # IF P6430 IN (1,7) & (P3045S1=1) THEN FORMAL=1 ELSE
    es_asal_17 = P6430.isin([1, 7])
    _set(es_asal_17 & (P3045S1 == 1), 1)
    # IF P6430 IN (1,7) & ((P3045S1 IN (2,9)) AND P3046 = 1) THEN FORMAL=1
    _set(es_asal_17 & P3045S1.isin([2, 9]) & (P3046 == 1), 1)
    # IF ... P3046 = 2 THEN FORMAL=0
    _set(es_asal_17 & P3045S1.isin([2, 9]) & (P3046 == 2), 0)
    # IF ... P3046 = 9 & P3069 >= 4 THEN FORMAL=1
    _set(es_asal_17 & P3045S1.isin([2, 9]) & (P3046 == 9) & (P3069 >= 4), 1)
    # IF ... P3046 = 9 & P3069 <= 3 THEN FORMAL=0
    _set(es_asal_17 & P3045S1.isin([2, 9]) & (P3046 == 9) & (P3069 <= 3), 0)

    # ── INDEPENDIENTES SIN NEGOCIO (P6765 ≠ 7) ────────────────────
    es_indep_45 = P6430.isin([4, 5])
    es_patron = P6430 == 5
    es_cta_propia = P6430 == 4
    sin_negocio = es_indep_45 & (P6765 != 7)
    con_negocio = es_indep_45 & (P6765 == 7)

    # IF P6430 IN (4,5) & P6765 NOT IN (7) & P3065=1 THEN FORMAL=1
    _set(sin_negocio & (P3065 == 1), 1)
    # IF ... P3065 IN (2,9) & P3066=1 THEN FORMAL=1
    _set(sin_negocio & P3065.isin([2, 9]) & (P3066 == 1), 1)
    # IF ... P3065 IN (2,9) & P3066=2 THEN FORMAL=0
    _set(sin_negocio & P3065.isin([2, 9]) & (P3066 == 2), 0)
    # IF P6430=5 & ... P3066=9 & P3069 >= 4 THEN FORMAL=1
    _set(sin_negocio & es_patron & P3065.isin([2, 9]) & (P3066 == 9) & (P3069 >= 4), 1)
    # IF P6430=5 & ... P3066=9 & P3069 <= 3 THEN FORMAL=0
    _set(sin_negocio & es_patron & P3065.isin([2, 9]) & (P3066 == 9) & (P3069 <= 3), 0)
    # IF P6430=4 & ... P3066=9 & OFICIO 00-20 THEN FORMAL=1
    _set(sin_negocio & es_cta_propia & P3065.isin([2, 9]) & (P3066 == 9) & (OFICIO2D <= 20), 1)
    # IF P6430=4 & ... P3066=9 & OFICIO >=21 THEN FORMAL=0
    _set(sin_negocio & es_cta_propia & P3065.isin([2, 9]) & (P3066 == 9) & (OFICIO2D >= 21), 0)

    # ── INDEPENDIENTES CON NEGOCIO Y CON REGISTRO MERCANTIL ───────
    # IF ... P3067=1 & P3067S1=1 & P3067S2 >= ANIOS THEN FORMAL=1
    _set(con_negocio & (P3067 == 1) & (P3067S1 == 1) & (anios_umbral <= P3067S2), 1)
    # IF ... P3067=1 & P3067S1=1 & P3067S2 < ANIOS THEN FORMAL=0
    _set(con_negocio & (P3067 == 1) & (P3067S1 == 1) & (anios_umbral > P3067S2), 0)
    # IF ... P3067=1 & P3067S1=2 & P6775=1 THEN FORMAL=1
    _set(con_negocio & (P3067 == 1) & (P3067S1 == 2) & (P6775 == 1), 1)
    # IF ... P3067=1 & P3067S1=2 & P6775=3 & OFICIO 00-20 THEN FORMAL=1
    _set(con_negocio & (P3067 == 1) & (P3067S1 == 2) & (P6775 == 3) & (OFICIO2D <= 20), 1)
    # IF ... P6775=3 & OFICIO >=21 THEN FORMAL=0
    _set(con_negocio & (P3067 == 1) & (P3067S1 == 2) & (P6775 == 3) & (OFICIO2D >= 21), 0)
    # IF ... P6775=2 THEN FORMAL=0
    _set(con_negocio & (P3067 == 1) & (P3067S1 == 2) & (P6775 == 2), 0)
    # IF P6430=4 & ... P6775=9 & OFICIO 00-20 THEN FORMAL=1
    _set(
        con_negocio
        & es_cta_propia
        & (P3067 == 1)
        & (P3067S1 == 2)
        & (P6775 == 9)
        & (OFICIO2D <= 20),
        1,
    )
    # IF P6430=4 & ... P6775=9 & OFICIO >=21 THEN FORMAL=0
    _set(
        con_negocio
        & es_cta_propia
        & (P3067 == 1)
        & (P3067S1 == 2)
        & (P6775 == 9)
        & (OFICIO2D >= 21),
        0,
    )
    # IF P6430=5 & ... P6775=9 & P3069 >=4 THEN FORMAL=1
    _set(con_negocio & es_patron & (P3067 == 1) & (P3067S1 == 2) & (P6775 == 9) & (P3069 >= 4), 1)
    # IF P6430=5 & ... P6775=9 & P3069 <=3 THEN FORMAL=0
    _set(con_negocio & es_patron & (P3067 == 1) & (P3067S1 == 2) & (P6775 == 9) & (P3069 <= 3), 0)

    # ── INDEPENDIENTES CON NEGOCIO Y SIN REGISTRO MERCANTIL ───────
    # IF ... P3067=2 & P6775=1 & P3068=1 THEN FORMAL=1
    _set(con_negocio & (P3067 == 2) & (P6775 == 1) & (P3068 == 1), 1)
    # IF ... P3067=2 & P6775=1 & P3068=2 THEN FORMAL=0
    _set(con_negocio & (P3067 == 2) & (P6775 == 1) & (P3068 == 2), 0)
    # IF ... P3067=2 & P6775=3 & OFICIO 00-20 THEN FORMAL=1
    _set(con_negocio & (P3067 == 2) & (P6775 == 3) & (OFICIO2D <= 20), 1)
    # IF ... P3067=2 & P6775=3 & OFICIO >=21 THEN FORMAL=0
    _set(con_negocio & (P3067 == 2) & (P6775 == 3) & (OFICIO2D >= 21), 0)
    # IF ... P3067=2 & P6775=1 & P3068 IN (3,9) THEN FORMAL=0
    _set(con_negocio & (P3067 == 2) & (P6775 == 1) & P3068.isin([3, 9]), 0)
    # IF ... P3067=2 & P6775=2 THEN FORMAL=0
    _set(con_negocio & (P3067 == 2) & (P6775 == 2), 0)
    # IF P6430=5 & ... P3067=2 & P6775=9 & P3069 >=4 THEN FORMAL=1
    _set(con_negocio & es_patron & (P3067 == 2) & (P6775 == 9) & (P3069 >= 4), 1)
    # IF P6430=5 & ... P3067=2 & P6775=9 & P3069 <=3 THEN FORMAL=0
    _set(con_negocio & es_patron & (P3067 == 2) & (P6775 == 9) & (P3069 <= 3), 0)
    # IF P6430=4 & ... P3067=2 & P6775=9 & OFICIO 00-20 THEN FORMAL=1
    _set(con_negocio & es_cta_propia & (P3067 == 2) & (P6775 == 9) & (OFICIO2D <= 20), 1)
    # IF P6430=4 & ... P3067=2 & P6775=9 & OFICIO >=21 THEN FORMAL=0
    _set(con_negocio & es_cta_propia & (P3067 == 2) & (P6775 == 9) & (OFICIO2D >= 21), 0)

    # ──────────────────────────────────────────────────────────────
    # 8. SALUD (asalariados 1, 3, 7)
    # ──────────────────────────────────────────────────────────────
    es_asal_137 = P6430.isin([1, 3, 7])
    SALUD = pd.Series(np.nan, index=df.index, dtype="float64")

    # IF (P6430 IN (1,3,7) & P6100 IN (1,2) & P6110 IN (1,2,4)) THEN SALUD=1
    cond1 = es_asal_137 & P6100.isin([1, 2]) & P6110.isin([1, 2, 4])
    # IF (P6430 IN (1,3,7) & P6100=9 & P6450=2) THEN SALUD=1
    cond2 = es_asal_137 & (P6100 == 9) & (P6450 == 2)
    # IF (P6430 IN (1,3,7) & P6110=9 & P6450=2) THEN SALUD=1
    cond3 = es_asal_137 & (P6110 == 9) & (P6450 == 2)

    SALUD.loc[es_asal_137] = 0  # Default 0 para asalariados
    SALUD.loc[cond1.fillna(False)] = 1
    SALUD.loc[cond2.fillna(False)] = 1
    SALUD.loc[cond3.fillna(False)] = 1

    # ──────────────────────────────────────────────────────────────
    # 9. PENSIÓN (asalariados 1, 3, 7)
    # ──────────────────────────────────────────────────────────────
    PENSION = pd.Series(np.nan, index=df.index, dtype="float64")
    PENSION.loc[es_asal_137] = 0

    # IF (... P6920=3) THEN PENSION=1   (pensionado activo)
    PENSION.loc[(es_asal_137 & (P6920 == 3)).fillna(False)] = 1
    # IF (... P6920=1 & P6930 IN (1,2,3) & P6940 IN (1,3)) THEN PENSION=1
    cond_p = es_asal_137 & (P6920 == 1) & P6930.isin([1, 2, 3]) & P6940.isin([1, 3])
    PENSION.loc[cond_p.fillna(False)] = 1

    # ──────────────────────────────────────────────────────────────
    # 10. EI (variable final, convención SAS)
    # ──────────────────────────────────────────────────────────────
    EI = pd.Series(np.nan, index=df.index, dtype="float64")

    # IF P6430 IN (2) THEN EI=1
    EI.loc[(P6430 == 2).fillna(False)] = 1
    # IF P6430 IN (6,8) THEN EI=0
    EI.loc[P6430.isin([6, 8]).fillna(False)] = 0
    # IF P6430 IN (4,5) THEN EI=FORMAL
    mask_indep = P6430.isin([4, 5]).fillna(False)
    EI.loc[mask_indep] = FORMAL.loc[mask_indep]
    # IF P6430 IN (1,3,7) & SALUD=1 & PENSION=1 THEN EI=1
    cond_asal_formal = P6430.isin([1, 3, 7]) & (SALUD == 1) & (PENSION == 1)
    EI.loc[cond_asal_formal.fillna(False)] = 1
    # IF P6430 IN (1,3,7) THEN EI=0  (resto de asalariados)
    cond_asal_resto = P6430.isin([1, 3, 7]) & EI.isna()
    EI.loc[cond_asal_resto.fillna(False)] = 0

    # IF Rama2d_R4 IN ('84','99') & P6430 NOT IN (6,8) THEN EI=1
    # (rama administración pública / orgs extraterritoriales son
    #  formales por definición incluso en asalariados que pudieran
    #  haber quedado en 0 por SALUD/PENSION incompletas)
    cond_rama = RAMA2D.isin([84, 99]) & ~P6430.isin([6, 8])
    EI.loc[cond_rama.fillna(False)] = 1

    # ──────────────────────────────────────────────────────────────
    # 11. Inversión de convención (DANE EI=1 formal → libreria INFORMAL=1 informal)
    # ──────────────────────────────────────────────────────────────
    INFORMAL = pd.Series(pd.NA, index=df.index, dtype="Int8")
    INFORMAL.loc[EI == 1] = 0  # DANE formal → INFORMAL=0
    INFORMAL.loc[EI == 0] = 1  # DANE informal → INFORMAL=1

    # ──────────────────────────────────────────────────────────────
    # 12. Reporte final de cobertura
    # ──────────────────────────────────────────────────────────────
    if verbose:
        n_total = len(df)
        n_clas = INFORMAL.notna().sum()
        n_inf = (INFORMAL == 1).sum()
        n_form = (INFORMAL == 0).sum()
        n_na = INFORMAL.isna().sum()
        cob = 100 * n_clas / n_total if n_total > 0 else 0
        print(
            f"   Cobertura: {cob:.2f}% "
            f"({n_clas:,}/{n_total:,} clasificados | "
            f"{n_inf:,} informales | {n_form:,} formales | "
            f"{n_na:,} NA)"
        )

    return INFORMAL


# ════════════════════════════════════════════════════════════════════════════
# 📄 geih/logger.py
#    Categoría: codigo
