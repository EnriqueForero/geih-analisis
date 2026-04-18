"""
geih.analisis_departamental — Análisis departamental consolidado con precisión muestral.

Clase central para análisis regional: consolida indicadores que antes estaban
dispersos en 6+ clases (IndicadoresLaborales, CalidadEmpleo, AnalisisSalarios,
etc.) en un solo punto de acceso para reportes departamentales.

INNOVACIÓN CLAVE: Cada estimación lleva su evaluación de precisión muestral
(CV, IC, clasificación DANE). Esto es crítico para departamentos con muestra
pequeña (Amazonía, Orinoquía) donde publicar cifras sin contexto de
confiabilidad es irresponsable.

Frecuencias soportadas:
  - Anual (12 meses)
  - Semestral (6 meses: ene-jun o jul-dic)
  - Trimestral (3 meses)
  - Mensual (1 mes, solo ciudades principales)

Diseño:
  - Principio Abierto/Cerrado: se pueden agregar indicadores nuevos
    extendiendo el método `_calcular_indicadores_dpto()` sin modificar
    los existentes.
  - SRP: esta clase solo calcula y reporta. No genera gráficos.
  - Vectorización: cero bucles sobre filas de DataFrame.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "AnalisisDepartamental",
]


from typing import Any, Optional

import numpy as np
import pandas as pd

from .config import (
    DEPARTAMENTOS,
    ConfigGEIH,
)
from .muestreo import (
    NO_CONFIABLE,
    advertencia_muestral,
    evaluar_media,
    evaluar_proporcion,
)
from .utils import ConversorTipos
from .utils import EstadisticasPonderadas as EP


class AnalisisDepartamental:
    """Análisis consolidado del mercado laboral por departamento.

    Produce un reporte integral por departamento con indicadores
    fundamentales, salariales y de calidad del empleo — cada uno
    acompañado de su métrica de precisión muestral.

    NOTA MUESTRAL:
    La GEIH tiene ~315.000 hogares/año a nivel nacional. Al desagregar
    por departamento, los más pequeños (Vaupés, Guainía, Vichada) pueden
    tener < 200 registros. Para análisis semestral, la muestra se reduce
    a la mitad. Esta clase advierte automáticamente cuando la muestra es
    insuficiente.

    Uso típico:
        # Análisis anual por departamento
        ad = AnalisisDepartamental(config=config)
        reporte = ad.calcular(df)
        ad.imprimir(reporte)

        # Exportar con indicador de confiabilidad
        ad.exportar_excel(reporte, "departamentos_2025.xlsx")

        # Solo departamentos con muestra confiable
        reporte_ok = ad.calcular(df, solo_confiables=True)
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()
        self._config_muestreo = self.config.config_muestreo

    def calcular(
        self,
        df: pd.DataFrame,
        solo_confiables: bool = False,
        incluir_precision: bool = True,
    ) -> pd.DataFrame:
        """Calcula indicadores por departamento con evaluación de precisión.

        Args:
            df: DataFrame preparado con variables derivadas (DPTO_STR, etc.).
            solo_confiables: Si True, excluye departamentos con CV > 20%.
            incluir_precision: Si True, incluye columnas de CV e IC.

        Returns:
            DataFrame con indicadores y métricas de precisión por departamento.
        """
        if "DPTO_STR" not in df.columns:
            df["DPTO_STR"] = ConversorTipos.estandarizar_dpto(df["DPTO"])

        filas: list[dict[str, Any]] = []

        for dpto, nombre in DEPARTAMENTOS.items():
            mask_dpto = df["DPTO_STR"] == dpto
            n_registros = int(mask_dpto.sum())

            # Verificación de muestra mínima
            if n_registros < self._config_muestreo.muestra_minima_registros:
                continue

            df_dpto = df[mask_dpto]
            fex_total = df_dpto["FEX_ADJ"].sum()

            # Advertencia muestral
            adv = advertencia_muestral(n_registros, fex_total, nombre, self._config_muestreo)

            fila = self._calcular_indicadores_dpto(df_dpto, nombre, dpto, n_registros, fex_total)

            if incluir_precision:
                fila["n_registros"] = n_registros
                fila["N_expandido_M"] = round(fex_total / 1e6, 3)
                fila["Advertencia"] = adv if adv else ""

            filas.append(fila)

        if not filas:
            print("⚠️  No se encontraron departamentos con muestra suficiente.")
            return pd.DataFrame()

        resultado = pd.DataFrame(filas)

        if solo_confiables:
            resultado = resultado[resultado["CV_TD_%"] <= self._config_muestreo.cv_poco_preciso_pct]

        resultado = resultado.sort_values("TD_%", ascending=False)

        self._imprimir_resumen(resultado)
        return resultado

    def _calcular_indicadores_dpto(
        self,
        df_dpto: pd.DataFrame,
        nombre: str,
        codigo: str,
        n_registros: int,
        fex_total: float,
    ) -> dict[str, Any]:
        """Calcula todos los indicadores para un departamento.

        Método extensible: agregar indicadores aquí sin modificar
        la estructura del método calcular() (Principio Abierto/Cerrado).
        """
        fex = "FEX_ADJ"

        # ── Indicadores fundamentales ──────────────────────────
        pet = df_dpto.loc[df_dpto["PET"] == 1, fex].sum() if "PET" in df_dpto.columns else 0
        pea = df_dpto.loc[df_dpto["FT"] == 1, fex].sum() if "FT" in df_dpto.columns else 0
        ocu = df_dpto.loc[df_dpto["OCI"] == 1, fex].sum() if "OCI" in df_dpto.columns else 0
        des = df_dpto.loc[df_dpto["DSI"] == 1, fex].sum() if "DSI" in df_dpto.columns else 0

        td = (des / pea * 100) if pea > 0 else np.nan
        tgp = (pea / pet * 100) if pet > 0 else np.nan
        to = (ocu / pet * 100) if pet > 0 else np.nan

        # ── Precisión de TD ────────────────────────────────────
        n_pea_reg = int((df_dpto["FT"] == 1).sum()) if "FT" in df_dpto.columns else 0
        p_td = des / pea if pea > 0 else 0
        prec_td = evaluar_proporcion(p_td, n_pea_reg, pea, nombre, self._config_muestreo)

        # ── Salario mediano ────────────────────────────────────
        mediana_sal = np.nan
        cv_mediana = np.nan
        if "INGLABO" in df_dpto.columns:
            mask_ing = (df_dpto["OCI"] == 1) & (df_dpto["INGLABO"] > 0)
            if mask_ing.sum() > 30:
                mediana_sal = EP.mediana(
                    df_dpto.loc[mask_ing, "INGLABO"],
                    df_dpto.loc[mask_ing, fex],
                )
                var_sal = df_dpto.loc[mask_ing, "INGLABO"].var()
                n_ing = int(mask_ing.sum())
                prec_sal = evaluar_media(
                    mediana_sal,
                    var_sal,
                    n_ing,
                    df_dpto.loc[mask_ing, fex].sum(),
                    nombre,
                    self._config_muestreo,
                )
                cv_mediana = prec_sal.cv_pct

        # ── Formalidad (cotiza pensión) ────────────────────────
        pct_pension = np.nan
        if "P6920" in df_dpto.columns and ocu > 0:
            mask_ocu = df_dpto["OCI"] == 1
            n_pension = df_dpto.loc[mask_ocu & (df_dpto["P6920"] == 1), fex].sum()
            pct_pension = round(n_pension / ocu * 100, 1) if ocu > 0 else np.nan

        # ── Informalidad (no cotiza pensión) ───────────────────
        pct_informal = round(100 - pct_pension, 1) if not np.isnan(pct_pension) else np.nan

        # ── Ingreso en SMMLV ───────────────────────────────────
        mediana_sml = np.nan
        if not np.isnan(mediana_sal):
            mediana_sml = round(mediana_sal / self.config.smmlv, 2)

        # ── Subempleo (deseo de cambiar trabajo) ───────────────
        pct_desea_cambiar = np.nan
        if "P7130" in df_dpto.columns and ocu > 0:
            mask_ocu = df_dpto["OCI"] == 1
            n_cambiar = df_dpto.loc[mask_ocu & (df_dpto["P7130"] == 1), fex].sum()
            pct_desea_cambiar = round(n_cambiar / ocu * 100, 1)

        # ── Composición urbano/rural ───────────────────────────
        pct_urbano = np.nan
        if "CLASE" in df_dpto.columns:
            n_urbano = df_dpto.loc[df_dpto["CLASE"].astype(str) == "1", fex].sum()
            pct_urbano = round(n_urbano / fex_total * 100, 1) if fex_total > 0 else np.nan

        return {
            "Departamento": nombre,
            "DPTO": codigo,
            "PET_M": round(pet / 1e6, 3),
            "PEA_M": round(pea / 1e6, 3),
            "Ocupados_M": round(ocu / 1e6, 3),
            "Desocupados_M": round(des / 1e6, 3),
            "TD_%": round(td, 1) if not np.isnan(td) else np.nan,
            "TGP_%": round(tgp, 1) if not np.isnan(tgp) else np.nan,
            "TO_%": round(to, 1) if not np.isnan(to) else np.nan,
            "CV_TD_%": prec_td.cv_pct,
            "IC_TD_inf": prec_td.ic_inferior,
            "IC_TD_sup": prec_td.ic_superior,
            "Precision_TD": prec_td.clasificacion,
            "Mediana_COP": round(mediana_sal) if not np.isnan(mediana_sal) else np.nan,
            "Mediana_SMMLV": mediana_sml,
            "CV_Mediana_%": cv_mediana,
            "Cotiza_pension_%": pct_pension,
            "Informalidad_%": pct_informal,
            "Desea_cambiar_%": pct_desea_cambiar,
            "Pct_urbano_%": pct_urbano,
        }

    def _imprimir_resumen(self, resultado: pd.DataFrame) -> None:
        """Imprime resumen tabular del reporte departamental."""
        n_total = len(resultado)
        n_confiable = (resultado["Precision_TD"] != NO_CONFIABLE).sum()

        print(f"\n{'='*80}")
        print(f"  REPORTE DEPARTAMENTAL — {self.config.periodo_etiqueta}")
        print(f"{'='*80}")
        print(f"  Departamentos analizados : {n_total}")
        print(f"  Con precisión confiable  : {n_confiable}")
        print(f"  Sin precisión confiable  : {n_total - n_confiable}")
        print(f"{'─'*80}")
        print(
            f"  {'Departamento':<25s} {'TD_%':>6s} {'CV%':>5s} {'IC 95%':>14s} "
            f"{'Med.COP':>12s} {'Prec.':>12s}"
        )
        print(f"{'─'*80}")

        for _, r in resultado.head(33).iterrows():
            td = r.get("TD_%", np.nan)
            cv = r.get("CV_TD_%", np.nan)
            ic_i = r.get("IC_TD_inf", np.nan)
            ic_s = r.get("IC_TD_sup", np.nan)
            med = r.get("Mediana_COP", np.nan)
            prec = r.get("Precision_TD", "")

            td_str = f"{td:.1f}" if not np.isnan(td) else "—"
            cv_str = f"{cv:.1f}" if not np.isnan(cv) else "—"
            ic_str = f"[{ic_i:.1f}, {ic_s:.1f}]" if not np.isnan(ic_i) else "—"
            med_str = f"${med:,.0f}" if not np.isnan(med) else "—"

            print(
                f"  {r['Departamento']:<25s} {td_str:>6s} {cv_str:>5s} "
                f"{ic_str:>14s} {med_str:>12s} {prec}"
            )

        print(f"{'='*80}")

    def exportar_excel(
        self,
        resultado: pd.DataFrame,
        nombre: str = "Reporte_Departamental_GEIH.xlsx",
    ) -> None:
        """Exporta el reporte departamental a Excel con metadatos."""
        with pd.ExcelWriter(nombre, engine="openpyxl") as writer:
            resultado.to_excel(writer, sheet_name="Indicadores", index=False)

            # Hoja de metadatos
            meta = pd.DataFrame(
                [
                    {"Campo": "Período", "Valor": self.config.periodo_etiqueta},
                    {"Campo": "SMMLV", "Valor": f"${self.config.smmlv:,}"},
                    {"Campo": "n_meses", "Valor": str(self.config.n_meses)},
                    {"Campo": "DEFF usado", "Valor": str(self._config_muestreo.deff)},
                    {
                        "Campo": "Nivel confianza",
                        "Valor": f"{self._config_muestreo.nivel_confianza:.0%}",
                    },
                    {"Campo": "CV preciso ≤", "Valor": f"{self._config_muestreo.cv_preciso_pct}%"},
                    {
                        "Campo": "CV aceptable ≤",
                        "Valor": f"{self._config_muestreo.cv_aceptable_pct}%",
                    },
                ]
            )
            meta.to_excel(writer, sheet_name="Metadatos", index=False)

        print(f"✅ Excel departamental exportado: {nombre}")
