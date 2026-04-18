"""
geih.analisis_dpto_rama — Ocupados promedio anual por Departamento × Rama CIIU.

Replica la metodología oficial del DANE para estimar población ocupada
desagregada por departamento (DIVIPOLA) y rama de actividad económica
(CIIU Rev. 4 adaptada para Colombia), a 2 dígitos (88 divisiones) o
4 dígitos (~500 clases).

Metodología:
  1. Para cada mes m y cada celda (DPTO, rama):
       T_m = Σ FEX_C18   (total expandido del mes en la celda)
       n_m = conteo muestral del mes en la celda
  2. Promedio anual = media de los 12 totales mensuales, reponderada
     por meses con dato (los meses faltantes se interpretan como ceros).
  3. Evaluación de precisión estadística:
     El CV se calcula con evaluar_total() del módulo muestreo, que aplica
     la fórmula de varianza bajo diseño complejo (Cochran 1977, Kish 1965):

         Var(p̂) ≈ DEFF × p(1−p) / n_base

     donde:
       p      = proporción de la celda respecto al total del departamento
       n_base = tamaño muestral del DEPARTAMENTO (no de la celda)
       DEFF   = efecto de diseño (default 2.5 para GEIH)

     La n correcta es la del dominio de estimación (departamento), porque
     todos los registros del dominio —los que caen en la rama y los que
     no— contribuyen a estimar la proporción p. Usar n_celda subestimaría
     la información disponible e inflaría el CV artificialmente.

Filtro de ocupados:
  Esta clase asume que el DataFrame de entrada contiene SOLO ocupados.
  En el pipeline estándar, la base se construye desde "Ocupados.CSV"
  (módulo DANE que solo contiene OCI==1 por diseño). Como protección
  defensiva, si la columna OCI existe en el DataFrame, se filtra
  automáticamente por OCI==1.

Uso típico:
    from geih import OcupadosDptoRama, ConfigGEIH

    analisis = OcupadosDptoRama(config=ConfigGEIH())
    tabla_2d = analisis.calcular(df_consolidado, nivel_ciiu="2d")
    tabla_4d = analisis.calcular(df_consolidado, nivel_ciiu="4d")

    analisis.exportar_excel(
        {"2d": tabla_2d, "4d": tabla_4d},
        ruta="resultados/Ocupados_DPTO_CIIU_2025.xlsx",
    )
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

try:
    from .config import ConfigGEIH
except ImportError:  # permite uso fuera del paquete
    ConfigGEIH = None  # type: ignore

try:
    from .muestreo import ConfigMuestreo, evaluar_total
except ImportError:  # permite uso fuera del paquete
    evaluar_total = None  # type: ignore
    ConfigMuestreo = None  # type: ignore


# ═════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═════════════════════════════════════════════════════════════════════

_NIVELES_VALIDOS = {
    "2d": {"col_origen": "RAMA2D_R4", "col_final": "ciiu_2d", "padding": 2},
    "4d": {"col_origen": "RAMA4D_R4", "col_final": "ciiu_4d", "padding": 4},
}

_UMBRAL_CONFIABLE = 0.07
_UMBRAL_ACEPTABLE = 0.15

_ETIQUETAS_PUBLICABLES = ("Confiable", "Aceptable con reserva")

# Mapeo: etiquetas del módulo muestreo → etiquetas locales
_MAPEO_CLASIFICACION = {
    "✅ Precisión alta": "Confiable",
    "⚠️  Precisión aceptable": "Aceptable con reserva",
    "⚠️⚠️ Precisión baja": "No publicable",
    "❌ No confiable": "No publicable",
}


# ═════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═════════════════════════════════════════════════════════════════════


class OcupadosDptoRama:
    """Ocupados promedio anual por departamento × rama CIIU.

    Attributes:
        config: Instancia opcional de ConfigGEIH (no es obligatoria para
            este cálculo; se incluye por consistencia con el resto del
            paquete y para permitir extensiones futuras).
        config_muestreo: Instancia opcional de ConfigMuestreo. Si no se
            provee, se crea una con los defaults DANE (DEFF=2.5).
    """

    def __init__(
        self,
        config: ConfigGEIH | None = None,
        config_muestreo: ConfigMuestreo | None = None,
    ) -> None:
        self.config = config
        self.config_muestreo = config_muestreo

    # ─────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL
    # ─────────────────────────────────────────────────────────────

    def calcular(
        self,
        df: pd.DataFrame,
        nivel_ciiu: str = "2d",
        verbose: bool = True,
    ) -> pd.DataFrame:
        """Calcula ocupados promedio anual por DPTO × rama CIIU.

        Args:
            df: DataFrame consolidado con al menos las columnas
                DPTO, FEX_C18, MES_NUM y la columna de rama correspondiente
                al nivel solicitado (RAMA2D_R4 o RAMA4D_R4).
                Si contiene la columna OCI, se filtra automáticamente
                por OCI==1 como protección defensiva.
            nivel_ciiu: "2d" (88 divisiones) o "4d" (~500 clases).
            verbose: Si True, imprime mensajes de diagnóstico.

        Returns:
            DataFrame con columnas: DPTO, ciiu_{nivel}, ocupados_promedio,
            desv_mensual, meses_con_dato, n_anual, ee_aprox, cv_aprox,
            calidad.
        """
        if nivel_ciiu not in _NIVELES_VALIDOS:
            raise ValueError(f"nivel_ciiu debe ser '2d' o '4d', recibido: {nivel_ciiu!r}")

        meta = _NIVELES_VALIDOS[nivel_ciiu]
        col_rama = meta["col_origen"]
        col_final = meta["col_final"]

        self._validar_columnas(df, col_rama)

        # Higiene: filas válidas
        mask = (
            df["DPTO"].notna() & df["FEX_C18"].notna() & (df["FEX_C18"] > 0) & df[col_rama].notna()
        )

        # Filtro defensivo: si OCI existe, usar solo ocupados.
        # En el pipeline estándar la base ya viene de "Ocupados.CSV"
        # (solo OCI==1), pero si el usuario pasa una base más amplia,
        # este filtro previene la inclusión de desocupados/inactivos.
        # Nota: OCI puede ser string ("1") o numérico (1) según cómo
        # se haya leído la base; se maneja ambos casos.
        if "OCI" in df.columns:
            oci = pd.to_numeric(df["OCI"], errors="coerce")
            mask = mask & (oci == 1)
            if verbose:
                n_no_oci = ((oci != 1) & oci.notna()).sum()
                if n_no_oci:
                    print(f"   ⓘ Filtro OCI: excluidos {n_no_oci:,} registros no ocupados")

        df_lim = df.loc[mask].copy()
        descartadas = (~mask).sum()
        if verbose and descartadas:
            print(
                f"   ⓘ {col_rama}: descartados {descartadas:,} registros "
                f"(sin DPTO, FEX, rama codificada, o no ocupados)"
            )

        # ── Paso 1: totales mensuales por celda ──
        mensual = df_lim.groupby(["DPTO", col_rama, "MES_NUM"], as_index=False).agg(
            total_expandido=("FEX_C18", "sum"), n_muestra=("FEX_C18", "size")
        )

        # ── Paso 2: agregación anual ──
        anual = mensual.groupby(["DPTO", col_rama], as_index=False).agg(
            ocupados_promedio=("total_expandido", "mean"),
            desv_mensual=("total_expandido", "std"),
            meses_con_dato=("total_expandido", "size"),
            n_anual=("n_muestra", "sum"),
        )

        # Reponderación: meses faltantes son ceros reales
        anual["ocupados_promedio"] = anual["ocupados_promedio"] * anual["meses_con_dato"] / 12

        # ── CV temporal (informativo, se conserva por compatibilidad) ──
        anual["ee_aprox"] = anual["desv_mensual"] / np.sqrt(anual["meses_con_dato"])
        anual["cv_aprox"] = np.where(
            anual["ocupados_promedio"] > 0,
            anual["ee_aprox"] / anual["ocupados_promedio"],
            np.nan,
        )

        # ── Universo departamental: n_base y total expandido ──
        # n_base_dpto = total de registros muestrales del departamento
        # (es el n correcto para Var(p) = DEFF * p(1-p) / n_base)
        dpto_stats = df_lim.groupby("DPTO").agg(
            n_base_dpto=("FEX_C18", "size"), fex_total_dpto=("FEX_C18", "sum")
        )

        # ── CV muestral (riguroso, determina la calidad) ──
        anual["calidad"], anual["cv_muestral"] = self._calcular_calidad_muestral(anual, dpto_stats)

        # Renombrar columna final y ordenar
        anual = anual.rename(columns={col_rama: col_final})
        anual = anual.sort_values(
            ["DPTO", "ocupados_promedio"], ascending=[True, False]
        ).reset_index(drop=True)

        if verbose:
            total = anual["ocupados_promedio"].sum()
            pub = anual[anual["calidad"].isin(_ETIQUETAS_PUBLICABLES)]
            cob = pub["ocupados_promedio"].sum() / total if total else 0
            print(
                f"   ✅ Nivel {nivel_ciiu}: {len(anual):,} celdas, "
                f"total nacional {total:,.0f}, "
                f"cobertura publicable {cob:.1%}"
            )

        return anual

    # ─────────────────────────────────────────────────────────────
    # EVALUACIÓN DE CALIDAD MUESTRAL
    # ─────────────────────────────────────────────────────────────

    def _calcular_calidad_muestral(
        self,
        anual: pd.DataFrame,
        dpto_stats: pd.DataFrame,
    ) -> tuple:
        """Calcula la etiqueta de calidad y el CV muestral numérico.

        Aplica la fórmula de varianza binomial bajo diseño complejo:

            Var(p̂) ≈ DEFF × p(1−p) / n_base

        donde:
          p      = proporción de la celda respecto al departamento
          n_base = registros muestrales del departamento completo
                   (Cochran 1977: el n es el del dominio de estimación,
                   no el del subgrupo, porque todos los registros del
                   dominio contribuyen a estimar p)
          DEFF   = efecto de diseño del muestreo complejo

        Muestra mínima: si n_celda < muestra_minima_registros (100),
        la celda se marca como "No publicable". NO se aplica el umbral
        de n_expandido (50,000) porque fue diseñado para dominios
        completos, no para celdas cruzadas DPTO×rama.

        Si el módulo muestreo no está disponible, usa CV temporal.

        Returns:
            Tupla (calidades: pd.Series, cv_muestral: pd.Series).
            cv_muestral contiene el CV como fracción (0.05 = 5%).
        """
        if evaluar_total is None:
            return (
                anual["cv_aprox"].apply(self._etiquetar_calidad_temporal),
                anual["cv_aprox"].copy(),
            )

        cfg = self.config_muestreo or ConfigMuestreo()

        # Total expandido y n_base por departamento
        totales_dpto = anual.groupby("DPTO")["ocupados_promedio"].transform("sum")
        celdas_por_dpto = anual.groupby("DPTO")["ocupados_promedio"].transform("count")
        total_nacional = anual["ocupados_promedio"].sum()
        n_nacional = int(dpto_stats["n_base_dpto"].sum())

        if total_nacional <= 0:
            return (
                pd.Series("Sin dato", index=anual.index),
                pd.Series(np.nan, index=anual.index),
            )

        calidades = []
        cvs_muestrales = []
        for i in range(len(anual)):
            row = anual.iloc[i]
            dpto = row["DPTO"]
            n_celda = int(row["n_anual"])
            ocu = float(row["ocupados_promedio"])
            n_exp_dpto = float(totales_dpto.iloc[i])
            n_celdas = int(celdas_por_dpto.iloc[i])

            if ocu <= 0 or n_celda <= 0:
                calidades.append("Sin dato")
                cvs_muestrales.append(np.nan)
                continue

            # Muestra mínima: solo n_registros de la celda
            if n_celda < cfg.muestra_minima_registros:
                calidades.append("No publicable")
                cvs_muestrales.append(np.nan)
                continue

            # n_base y proporción: respecto al departamento
            # (fallback a nacional si celda única en su dpto)
            if n_celdas > 1 and n_exp_dpto > 0 and dpto in dpto_stats.index:
                prop = ocu / n_exp_dpto
                n_base = int(dpto_stats.loc[dpto, "n_base_dpto"])
                universo = n_exp_dpto
            else:
                prop = ocu / total_nacional
                n_base = n_nacional
                universo = total_nacional

            prec = evaluar_total(
                total_expandido=ocu,
                n_registros=n_base,
                n_expandido=universo,
                proporcion_universo=max(0.001, min(prop, 0.999)),
                config=cfg,
            )
            etiqueta = _MAPEO_CLASIFICACION.get(prec.clasificacion, "No publicable")
            calidades.append(etiqueta)
            cvs_muestrales.append(prec.cv_pct / 100 if pd.notna(prec.cv_pct) else np.nan)

        return (
            pd.Series(calidades, index=anual.index),
            pd.Series(cvs_muestrales, index=anual.index),
        )

    # ─────────────────────────────────────────────────────────────
    # ENRIQUECIMIENTO CON CORRELATIVAS
    # ─────────────────────────────────────────────────────────────

    def enriquecer(
        self,
        tabla: pd.DataFrame,
        dep: pd.DataFrame,
        ciiu: pd.DataFrame,
        nivel_ciiu: str = "2d",
    ) -> pd.DataFrame:
        """Agrega nombres legibles de departamento y rama CIIU.

        Args:
            tabla: Salida de `calcular()`.
            dep: Correlativa DIVIPOLA con columnas dpto_codigo, dpto_nombre.
            ciiu: Correlativa CIIU con columnas del nivel correspondiente:
                  ciiu_2d + ciiu_2d_desc + seccion_letra + seccion_desc, o
                  ciiu_4d + ciiu_4d_desc + ciiu_2d + ciiu_2d_desc + sección.
            nivel_ciiu: "2d" o "4d", debe coincidir con el de la tabla.

        Returns:
            DataFrame enriquecido con columnas descriptivas.
        """
        meta = _NIVELES_VALIDOS[nivel_ciiu]
        meta["col_final"]

        out = tabla.merge(
            dep[["dpto_codigo", "dpto_nombre"]],
            left_on="DPTO",
            right_on="dpto_codigo",
            how="left",
        )

        if nivel_ciiu == "2d":
            out = out.merge(
                ciiu[["ciiu_2d", "ciiu_2d_desc", "seccion_letra", "seccion_desc"]],
                on="ciiu_2d",
                how="left",
            )
            cols = [
                "dpto_codigo",
                "dpto_nombre",
                "seccion_letra",
                "seccion_desc",
                "ciiu_2d",
                "ciiu_2d_desc",
                "ocupados_promedio",
                "n_anual",
                "cv_muestral",
                "calidad",
                "meses_con_dato",
            ]
        else:
            out = out.merge(ciiu, on="ciiu_4d", how="left")
            cols = [
                "dpto_codigo",
                "dpto_nombre",
                "seccion_letra",
                "seccion_desc",
                "ciiu_2d",
                "ciiu_2d_desc",
                "ciiu_4d",
                "ciiu_4d_desc",
                "ocupados_promedio",
                "n_anual",
                "cv_muestral",
                "calidad",
                "meses_con_dato",
            ]

        return (
            out[cols]
            .sort_values(["dpto_nombre", "ocupados_promedio"], ascending=[True, False])
            .reset_index(drop=True)
        )

    # ─────────────────────────────────────────────────────────────
    # EXPORTACIÓN A EXCEL
    # ─────────────────────────────────────────────────────────────

    def exportar_excel(
        self,
        resultados: dict[str, pd.DataFrame],
        ruta: Union[str, Path],
        incluir_matriz: bool = True,
        incluir_top: bool = True,
    ) -> Path:
        """Genera Excel multi-hoja con los resultados.

        Args:
            resultados: Dict con claves '2d' y/o '4d' y DataFrames
                enriquecidos (salida de `enriquecer()`).
            ruta: Ruta del archivo .xlsx a crear.
            incluir_matriz: Agrega hoja pivote DPTO × rama (solo 2d).
            incluir_top: Agrega hoja top-10 ramas por dpto (solo 4d).

        Returns:
            Path del archivo generado.
        """
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)

        pub = _ETIQUETAS_PUBLICABLES
        metadatos_filas = [
            ("Fuente", "DANE — GEIH, marco 2018"),
            ("Unidad", "Persona ocupada en la semana de referencia"),
            ("Variable de peso", "FEX_C18 (factor de expansión calibrado)"),
            ("Cálculo", "Promedio de los 12 totales mensuales expandidos"),
            ("Clasificación sectorial", "CIIU Rev. 4 A.C."),
            ("División geográfica", "DIVIPOLA DANE"),
            (
                "Evaluación de calidad",
                "CV muestral con DEFF (diseño complejo DANE/OIT). "
                "n_base = muestra del departamento (Cochran 1977).",
            ),
            ("Calidad — Confiable", f"CV ≤ {_UMBRAL_CONFIABLE:.0%}"),
            ("Calidad — Aceptable", f"{_UMBRAL_CONFIABLE:.0%} < CV ≤ {_UMBRAL_ACEPTABLE:.0%}"),
            ("Calidad — No publicable", f"CV > {_UMBRAL_ACEPTABLE:.0%}"),
            (
                "Limitación geográfica",
                "Representativa por departamento y 13 AM. No a nivel municipal.",
            ),
            ("Fecha de generación", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]

        with pd.ExcelWriter(ruta, engine="openpyxl") as xw:
            pd.DataFrame(metadatos_filas, columns=["Campo", "Valor"]).to_excel(
                xw, sheet_name="metadatos", index=False
            )

            if "2d" in resultados:
                t2 = resultados["2d"]
                t2.to_excel(xw, sheet_name="2d_largo_completo", index=False)
                t2[t2["calidad"].isin(pub)].to_excel(
                    xw, sheet_name="2d_largo_publicable", index=False
                )
                if incluir_matriz and "ciiu_2d_desc" in t2.columns:
                    self._construir_matriz(t2).to_excel(xw, sheet_name="2d_matriz_dpto_x_rama")

            if "4d" in resultados:
                t4 = resultados["4d"]
                t4.to_excel(xw, sheet_name="4d_largo_completo", index=False)
                if incluir_top:
                    top = (
                        t4[t4["calidad"].isin(pub)]
                        .sort_values(["dpto_nombre", "ocupados_promedio"], ascending=[True, False])
                        .groupby("dpto_nombre", group_keys=False)
                        .head(10)
                        .reset_index(drop=True)
                    )
                    top.to_excel(xw, sheet_name="4d_top_por_dpto", index=False)

        self._ajustar_anchos(ruta)
        return ruta

    # ─────────────────────────────────────────────────────────────
    # HELPERS PRIVADOS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _validar_columnas(df: pd.DataFrame, col_rama: str) -> None:
        requeridas = {"DPTO", "FEX_C18", "MES_NUM", col_rama}
        faltantes = requeridas - set(df.columns)
        if faltantes:
            raise KeyError(
                f"Faltan columnas requeridas: {sorted(faltantes)}. Presentes: {sorted(df.columns)}"
            )

    @staticmethod
    def _etiquetar_calidad_temporal(cv: float) -> str:
        """Fallback: etiqueta basada en CV temporal (sin módulo muestreo)."""
        if pd.isna(cv):
            return "Sin dato"
        if cv <= _UMBRAL_CONFIABLE:
            return "Confiable"
        if cv <= _UMBRAL_ACEPTABLE:
            return "Aceptable con reserva"
        return "No publicable"

    @staticmethod
    def _construir_matriz(tabla_2d_enriquecida: pd.DataFrame) -> pd.DataFrame:
        df = tabla_2d_enriquecida.assign(rama=lambda d: d["ciiu_2d"] + " - " + d["ciiu_2d_desc"])
        matriz = df.pivot_table(
            index="dpto_nombre",
            columns="rama",
            values="ocupados_promedio",
            aggfunc="sum",
            fill_value=0,
        ).round(0)
        matriz["TOTAL"] = matriz.sum(axis=1)
        matriz.loc["TOTAL NACIONAL"] = matriz.sum(axis=0)
        return matriz

    @staticmethod
    def _ajustar_anchos(ruta: Path) -> None:
        try:
            from openpyxl import load_workbook

            wb = load_workbook(ruta)
            for ws in wb.worksheets:
                for col in ws.columns:
                    longitudes = (len(str(c.value)) for c in col if c.value is not None)
                    max_len = max(longitudes, default=10)
                    ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
            wb.save(ruta)
        except ImportError:
            pass
