# -*- coding: utf-8 -*-
"""
geih.analisis_tierra — Distribución salarial por tenencia de tierra agropecuaria.

Cruza el ingreso laboral de trabajadores del sector primario (CIIU 01-03)
con la tenencia de tierra (P3064: propietario vs no propietario), abriendo
un mundo de análisis de política pública agraria y desarrollo regional.

VARIABLES CLAVE DE LA GEIH:
  P3064   → ¿Propietario de la tierra? (1=Sí, 2=No, 9=NS/NI)
  P3064S1 → Valor estimado de arriendo mensual del terreno (COP)
  P3056   → Tipo de actividad (1=Mercancías/servicios, 2=Agropecuario)
  RAMA2D_R4 → CIIU 2 dígitos (01=Agricultura, 02=Silvicultura, 03=Pesca)
  RAMA4D_R4 → CIIU 4 dígitos (detalle: 0111=cereales, 0141=bovinos, etc.)

LIMITACIÓN MUESTRAL: P3064 solo aplica a trabajadores independientes del
sector agropecuario. Es un subuniverso pequeño. A nivel nacional hay
suficiente muestra (~3-4M de ocupados agropecuarios), pero al cruzar con
departamento + subcategoría + tenencia, las celdas pueden quedarse con
pocas observaciones. CADA cruce lleva su evaluación de precisión.

ANÁLISIS DISPONIBLES:
  1. Brecha de ingresos propietario vs. no propietario
  2. Costo de oportunidad: ingreso vs. renta estimada de la tierra
  3. Distribución de la tierra por género
  4. Formalidad agropecuaria por tenencia
  5. Análisis por subcategoría CIIU (qué se cultiva/cría)
  6. Desagregación departamental con evaluación de confiabilidad
  7. Brecha urbano-rural dentro del sector agropecuario
  8. Análisis del ingreso agropecuario vs. SMMLV por tenencia

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "AnalisisTierraAgropecuario",
]


from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd

from .config import (
    ConfigGEIH,
    DEPARTAMENTOS,
    CIIU_SECTOR_PRIMARIO,
    CIIU_AGRICULTURA_DETALLE,
    NIVELES_AGRUPADOS,
    RANGOS_SMMLV_LIMITES,
    RANGOS_SMMLV_ETIQUETAS,
)
from .utils import EstadisticasPonderadas as EP, ConversorTipos
from .muestreo import (
    ConfigMuestreo,
    PrecisionEstimacion,
    evaluar_proporcion,
    evaluar_media,
    advertencia_muestral,
    clasificar_precision,
)


# ═════════════════════════════════════════════════════════════════════
# CONSTANTES DEL MÓDULO
# ═════════════════════════════════════════════════════════════════════

_TENENCIA_MAP: Dict[int, str] = {
    1: "Propietario",
    2: "No propietario",
}

_TIPO_ACTIVIDAD_MAP: Dict[int, str] = {
    1: "Mercancías/servicios",
    2: "Producción agropecuaria",
}


class AnalisisTierraAgropecuario:
    """Análisis de distribución salarial por tenencia de tierra agropecuaria.

    Explota las variables P3064 (tenencia), P3064S1 (renta estimada) y
    P3056 (tipo de actividad) para revelar las dinámicas del mercado
    laboral agropecuario colombiano.

    Cada estimación lleva su evaluación de precisión muestral. Cuando
    la muestra es insuficiente, la tabla lo indica explícitamente.

    Uso típico:
        tierra = AnalisisTierraAgropecuario(config=config)

        # Brecha de ingresos por tenencia
        brecha = tierra.brecha_ingresos(df)

        # Por departamento (con precisión)
        dept = tierra.por_departamento(df)

        # Costo de oportunidad
        costo_op = tierra.costo_oportunidad(df)

        # Por género
        genero = tierra.por_genero(df)

        # Reporte completo
        reporte = tierra.reporte_completo(df)
    """

    def __init__(self, config: Optional[ConfigGEIH] = None):
        self.config = config or ConfigGEIH()
        self._config_muestreo = self.config.config_muestreo

    # ── Filtro base: sector agropecuario ───────────────────────

    def _filtrar_agropecuario(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra ocupados del sector primario (CIIU 01-03).

        Estrategia dual: usa RAMA2D_R4 (CIIU 2 dígitos) cuando está
        disponible, o P3056==2 como fallback.

        Returns:
            DataFrame filtrado con variables derivadas de tenencia.
        """
        mask_ocu = df["OCI"] == 1

        # CIIU 01-03 (sector primario)
        if "RAMA2D_R4" in df.columns:
            rama2d = pd.to_numeric(df["RAMA2D_R4"], errors="coerce")
            mask_agro = mask_ocu & rama2d.between(1, 3)
        elif "P3056" in df.columns:
            # Fallback: tipo de actividad agropecuaria
            mask_agro = mask_ocu & (df["P3056"] == 2)
        else:
            print("⚠️  No se encontraron variables para identificar sector agropecuario.")
            return pd.DataFrame()

        df_agro = df[mask_agro].copy()

        if df_agro.empty:
            print("⚠️  No hay registros del sector agropecuario en la base.")
            return df_agro

        # Variables derivadas de tenencia
        if "P3064" in df_agro.columns:
            df_agro["TENENCIA"] = df_agro["P3064"].map(_TENENCIA_MAP)
        else:
            print("⚠️  Variable P3064 (tenencia de tierra) no encontrada en la base.")
            print("   Verifique que el módulo de Ocupados esté consolidado.")

        # Subcategoría CIIU
        if "RAMA2D_R4" in df_agro.columns:
            rama2d_str = pd.to_numeric(
                df_agro["RAMA2D_R4"], errors="coerce"
            ).round(0).astype("Int64").astype(str).str.zfill(2)
            df_agro["SUBCATEGORIA_CIIU"] = rama2d_str.map(CIIU_SECTOR_PRIMARIO)

        # Detalle CIIU 4 dígitos si disponible
        if "RAMA4D_R4" in df_agro.columns:
            rama4d_str = df_agro["RAMA4D_R4"].astype(str).str.zfill(4)
            df_agro["DETALLE_CIIU"] = rama4d_str.map(CIIU_AGRICULTURA_DETALLE)

        n_total = len(df_agro)
        n_expandido = df_agro["FEX_ADJ"].sum()
        n_con_tenencia = df_agro["TENENCIA"].notna().sum() if "TENENCIA" in df_agro.columns else 0

        print(f"\n{'='*60}")
        print(f"  SECTOR AGROPECUARIO — {self.config.periodo_etiqueta}")
        print(f"{'='*60}")
        print(f"  Registros en muestra     : {n_total:,}")
        print(f"  Personas expandidas      : {n_expandido/1e6:.3f} M")
        print(f"  Con dato de tenencia     : {n_con_tenencia:,} ({n_con_tenencia/max(n_total,1)*100:.1f}%)")
        print(f"{'='*60}")

        return df_agro

    # ══════════════════════════════════════════════════════════════
    # 1. BRECHA DE INGRESOS POR TENENCIA
    # ══════════════════════════════════════════════════════════════

    def brecha_ingresos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Brecha salarial entre propietarios y no propietarios de tierra.

        Responde: ¿Ser dueño de la parcela realmente saca al trabajador
        agropecuario de la pobreza, o el ingreso mediano sigue por debajo
        de 1 SMMLV a pesar de tener el activo?

        Returns:
            DataFrame con mediana, media, percentiles y SMMLV por tenencia.
        """
        df_agro = self._filtrar_agropecuario(df)
        if df_agro.empty or "TENENCIA" not in df_agro.columns:
            return pd.DataFrame()

        df_ing = df_agro[(df_agro["INGLABO"] > 0) & df_agro["TENENCIA"].notna()]

        if df_ing.empty:
            print("⚠️  No hay registros con ingreso y tenencia válidos.")
            return pd.DataFrame()

        filas: List[Dict[str, Any]] = []
        for tenencia in ["Propietario", "No propietario"]:
            mask = df_ing["TENENCIA"] == tenencia
            n_reg = int(mask.sum())
            n_exp = df_ing.loc[mask, "FEX_ADJ"].sum()

            adv = advertencia_muestral(n_reg, n_exp, tenencia, self._config_muestreo)

            if n_reg < 30:
                filas.append({
                    "Tenencia": tenencia, "n_registros": n_reg,
                    "Advertencia": adv or "Muestra muy pequeña",
                })
                continue

            mediana = EP.mediana(df_ing.loc[mask, "INGLABO"], df_ing.loc[mask, "FEX_ADJ"])
            media = EP.media(df_ing.loc[mask, "INGLABO"], df_ing.loc[mask, "FEX_ADJ"])
            var_sal = df_ing.loc[mask, "INGLABO"].var()

            prec = evaluar_media(mediana, var_sal, n_reg, n_exp, tenencia, self._config_muestreo)

            # Distribución por rangos SMMLV (vectorizado)
            inglabo_sml = df_ing.loc[mask, "INGLABO"] / self.config.smmlv
            pct_bajo_1sml = (
                df_ing.loc[mask & (df_ing["INGLABO"] < self.config.smmlv), "FEX_ADJ"].sum()
                / n_exp * 100
            ) if n_exp > 0 else np.nan

            filas.append({
                "Tenencia": tenencia,
                "n_registros": n_reg,
                "N_expandido_M": round(n_exp / 1e6, 3),
                "Mediana_COP": round(mediana),
                "Media_COP": round(media),
                "Mediana_SMMLV": round(mediana / self.config.smmlv, 2),
                "Pct_bajo_1SMMLV_%": round(pct_bajo_1sml, 1) if not np.isnan(pct_bajo_1sml) else np.nan,
                "CV_%": prec.cv_pct,
                "Precision": prec.clasificacion,
                "Advertencia": adv or "",
            })

        resultado = pd.DataFrame(filas)
        self._imprimir_brecha(resultado)
        return resultado

    # ══════════════════════════════════════════════════════════════
    # 2. COSTO DE OPORTUNIDAD (RENTA DE LA TIERRA)
    # ══════════════════════════════════════════════════════════════

    def costo_oportunidad(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compara ingreso laboral vs. renta estimada de la tierra.

        Responde: ¿El campesino propietario gana más trabajando la tierra
        que si simplemente la arrendara?

        Usa P3064S1 (valor estimado de arriendo mensual) como proxy del
        costo de oportunidad del activo tierra.

        Returns:
            DataFrame con ingreso vs renta por departamento.
        """
        df_agro = self._filtrar_agropecuario(df)
        if df_agro.empty:
            return pd.DataFrame()

        # Solo propietarios con renta estimada válida
        mask = (
            (df_agro.get("P3064", pd.Series(dtype=float)) == 1)
            & df_agro.get("P3064S1", pd.Series(dtype=float)).notna()
            & (df_agro.get("P3064S1", pd.Series(dtype=float)) > 0)
            & (df_agro["INGLABO"] > 0)
        )
        df_prop = df_agro[mask]

        if len(df_prop) < 30:
            print(f"⚠️  Solo {len(df_prop)} propietarios con renta y salario válidos.")
            return pd.DataFrame()

        renta_col = pd.to_numeric(df_prop["P3064S1"], errors="coerce")

        filas: List[Dict[str, Any]] = []

        # Nacional
        n_reg = len(df_prop)
        n_exp = df_prop["FEX_ADJ"].sum()
        med_ingreso = EP.mediana(df_prop["INGLABO"], df_prop["FEX_ADJ"])
        med_renta = EP.mediana(renta_col, df_prop["FEX_ADJ"])

        ratio = med_ingreso / med_renta if med_renta > 0 else np.nan
        excedente = med_ingreso - med_renta

        filas.append({
            "Dominio": "Nacional",
            "n_registros": n_reg,
            "Mediana_ingreso_COP": round(med_ingreso),
            "Mediana_renta_COP": round(med_renta),
            "Ratio_ingreso_renta": round(ratio, 2) if not np.isnan(ratio) else np.nan,
            "Excedente_COP": round(excedente),
            "Interpretacion": (
                "Ingreso > Renta → Trabaja la tierra es más rentable"
                if excedente > 0 else
                "Ingreso < Renta → Arrendar sería más rentable"
            ),
        })

        # Por departamento (si hay muestra)
        if "NOMBRE_DPTO" in df_prop.columns:
            for dpto in df_prop["NOMBRE_DPTO"].dropna().unique():
                m = df_prop["NOMBRE_DPTO"] == dpto
                n = int(m.sum())
                if n < 30:
                    continue
                med_i = EP.mediana(df_prop.loc[m, "INGLABO"], df_prop.loc[m, "FEX_ADJ"])
                med_r = EP.mediana(renta_col[m], df_prop.loc[m, "FEX_ADJ"])
                r = med_i / med_r if med_r > 0 else np.nan
                exc = med_i - med_r

                adv = advertencia_muestral(n, df_prop.loc[m, "FEX_ADJ"].sum(), dpto, self._config_muestreo)

                filas.append({
                    "Dominio": dpto,
                    "n_registros": n,
                    "Mediana_ingreso_COP": round(med_i),
                    "Mediana_renta_COP": round(med_r),
                    "Ratio_ingreso_renta": round(r, 2) if not np.isnan(r) else np.nan,
                    "Excedente_COP": round(exc),
                    "Interpretacion": (
                        "Ingreso > Renta" if exc > 0 else "Ingreso < Renta"
                    ),
                    "Advertencia": adv or "",
                })

        return pd.DataFrame(filas)

    # ══════════════════════════════════════════════════════════════
    # 3. DISTRIBUCIÓN DE LA TIERRA POR GÉNERO
    # ══════════════════════════════════════════════════════════════

    def por_genero(self, df: pd.DataFrame) -> pd.DataFrame:
        """Inequidad en titularidad de tierras productivas por sexo.

        Cruza P3064 (tenencia) × P3271 (sexo) para demostrar la brecha
        de género en la propiedad de la tierra agropecuaria.

        Returns:
            DataFrame con tasas de propiedad, ingreso mediano y brecha por sexo.
        """
        df_agro = self._filtrar_agropecuario(df)
        if df_agro.empty or "TENENCIA" not in df_agro.columns:
            return pd.DataFrame()

        if "P3271" not in df_agro.columns:
            print("⚠️  Variable P3271 (sexo) no encontrada.")
            return pd.DataFrame()

        df_val = df_agro[df_agro["TENENCIA"].notna() & (df_agro["INGLABO"] > 0)]
        df_val["SEXO"] = df_val["P3271"].map({1: "Hombres", 2: "Mujeres"})

        filas: List[Dict[str, Any]] = []
        for sexo in ["Hombres", "Mujeres"]:
            mask_sexo = df_val["SEXO"] == sexo
            n_reg = int(mask_sexo.sum())
            if n_reg < 30:
                continue

            n_exp = df_val.loc[mask_sexo, "FEX_ADJ"].sum()
            n_propietario = df_val.loc[mask_sexo & (df_val["TENENCIA"] == "Propietario"), "FEX_ADJ"].sum()
            pct_propietario = round(n_propietario / n_exp * 100, 1) if n_exp > 0 else np.nan

            mediana = EP.mediana(
                df_val.loc[mask_sexo, "INGLABO"],
                df_val.loc[mask_sexo, "FEX_ADJ"],
            )

            # Mediana de propietarios vs no propietarios
            med_prop = np.nan
            med_no_prop = np.nan
            mask_prop = mask_sexo & (df_val["TENENCIA"] == "Propietario")
            mask_no_prop = mask_sexo & (df_val["TENENCIA"] == "No propietario")

            if mask_prop.sum() > 20:
                med_prop = EP.mediana(df_val.loc[mask_prop, "INGLABO"], df_val.loc[mask_prop, "FEX_ADJ"])
            if mask_no_prop.sum() > 20:
                med_no_prop = EP.mediana(df_val.loc[mask_no_prop, "INGLABO"], df_val.loc[mask_no_prop, "FEX_ADJ"])

            adv = advertencia_muestral(n_reg, n_exp, sexo, self._config_muestreo)

            filas.append({
                "Sexo": sexo,
                "n_registros": n_reg,
                "N_expandido_M": round(n_exp / 1e6, 3),
                "Pct_propietario_%": pct_propietario,
                "Mediana_general_COP": round(mediana),
                "Mediana_propietario_COP": round(med_prop) if not np.isnan(med_prop) else np.nan,
                "Mediana_no_propietario_COP": round(med_no_prop) if not np.isnan(med_no_prop) else np.nan,
                "Mediana_SMMLV": round(mediana / self.config.smmlv, 2),
                "Advertencia": adv or "",
            })

        resultado = pd.DataFrame(filas)

        # Calcular brecha si hay ambos sexos
        if len(resultado) == 2:
            pct_h = resultado.loc[resultado["Sexo"] == "Hombres", "Pct_propietario_%"].iloc[0]
            pct_m = resultado.loc[resultado["Sexo"] == "Mujeres", "Pct_propietario_%"].iloc[0]
            if not np.isnan(pct_h) and not np.isnan(pct_m):
                print(f"\n   📊 Brecha de propiedad de tierra:")
                print(f"      Hombres propietarios: {pct_h:.1f}%")
                print(f"      Mujeres propietarias: {pct_m:.1f}%")
                print(f"      Brecha: {pct_h - pct_m:+.1f} p.p.")

        return resultado

    # ══════════════════════════════════════════════════════════════
    # 4. POR DEPARTAMENTO
    # ══════════════════════════════════════════════════════════════

    def por_departamento(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución salarial agropecuaria por departamento y tenencia.

        Para cada departamento con muestra suficiente, calcula mediana
        salarial de propietarios vs no propietarios con evaluación
        de precisión muestral.

        Returns:
            DataFrame con indicadores por departamento y precisión.
        """
        df_agro = self._filtrar_agropecuario(df)
        if df_agro.empty or "TENENCIA" not in df_agro.columns:
            return pd.DataFrame()

        if "DPTO_STR" not in df_agro.columns and "DPTO" in df_agro.columns:
            df_agro["DPTO_STR"] = ConversorTipos.estandarizar_dpto(df_agro["DPTO"])

        df_val = df_agro[df_agro["TENENCIA"].notna() & (df_agro["INGLABO"] > 0)]

        filas: List[Dict[str, Any]] = []
        for dpto, nombre in DEPARTAMENTOS.items():
            mask = df_val["DPTO_STR"] == dpto
            n_reg = int(mask.sum())
            n_exp = df_val.loc[mask, "FEX_ADJ"].sum()

            adv = advertencia_muestral(n_reg, n_exp, nombre, self._config_muestreo)
            if n_reg < self._config_muestreo.muestra_minima_registros:
                continue

            mediana = EP.mediana(df_val.loc[mask, "INGLABO"], df_val.loc[mask, "FEX_ADJ"])

            # Por tenencia
            med_prop = np.nan
            med_no_prop = np.nan
            mask_prop = mask & (df_val["TENENCIA"] == "Propietario")
            mask_no_prop = mask & (df_val["TENENCIA"] == "No propietario")

            n_prop = int(mask_prop.sum())
            n_no_prop = int(mask_no_prop.sum())

            if n_prop > 20:
                med_prop = EP.mediana(df_val.loc[mask_prop, "INGLABO"], df_val.loc[mask_prop, "FEX_ADJ"])
            if n_no_prop > 20:
                med_no_prop = EP.mediana(df_val.loc[mask_no_prop, "INGLABO"], df_val.loc[mask_no_prop, "FEX_ADJ"])

            brecha = round(med_prop - med_no_prop) if not (np.isnan(med_prop) or np.isnan(med_no_prop)) else np.nan

            # Precisión
            var_sal = df_val.loc[mask, "INGLABO"].var()
            prec = evaluar_media(mediana, var_sal, n_reg, n_exp, nombre, self._config_muestreo)

            # % propiedad
            n_exp_prop = df_val.loc[mask_prop, "FEX_ADJ"].sum()
            pct_prop = round(n_exp_prop / n_exp * 100, 1) if n_exp > 0 else np.nan

            filas.append({
                "Departamento": nombre,
                "DPTO": dpto,
                "n_registros": n_reg,
                "N_expandido_M": round(n_exp / 1e6, 3),
                "Mediana_general_COP": round(mediana),
                "Mediana_propietario_COP": round(med_prop) if not np.isnan(med_prop) else np.nan,
                "Mediana_no_propietario_COP": round(med_no_prop) if not np.isnan(med_no_prop) else np.nan,
                "Brecha_COP": brecha,
                "Pct_propietario_%": pct_prop,
                "Mediana_SMMLV": round(mediana / self.config.smmlv, 2),
                "CV_%": prec.cv_pct,
                "Precision": prec.clasificacion,
                "Advertencia": adv or "",
            })

        return pd.DataFrame(filas).sort_values("Mediana_general_COP", ascending=False)

    # ══════════════════════════════════════════════════════════════
    # 5. POR SUBCATEGORÍA CIIU (QUÉ SE CULTIVA/CRÍA)
    # ══════════════════════════════════════════════════════════════

    def por_subcategoria(self, df: pd.DataFrame) -> pd.DataFrame:
        """Distribución salarial por tipo de actividad agropecuaria.

        Usa CIIU a 2 dígitos para separar: agricultura (01), silvicultura (02),
        pesca (03), y si hay suficiente muestra, CIIU 4 dígitos para detalle.

        Returns:
            DataFrame con ingreso mediano por subcategoría agropecuaria.
        """
        df_agro = self._filtrar_agropecuario(df)
        if df_agro.empty:
            return pd.DataFrame()

        df_val = df_agro[df_agro["INGLABO"] > 0]

        filas: List[Dict[str, Any]] = []

        # Por CIIU 2 dígitos
        if "SUBCATEGORIA_CIIU" in df_val.columns:
            for subcat in df_val["SUBCATEGORIA_CIIU"].dropna().unique():
                mask = df_val["SUBCATEGORIA_CIIU"] == subcat
                n_reg = int(mask.sum())
                if n_reg < 30:
                    continue
                n_exp = df_val.loc[mask, "FEX_ADJ"].sum()
                mediana = EP.mediana(df_val.loc[mask, "INGLABO"], df_val.loc[mask, "FEX_ADJ"])

                pct_prop = np.nan
                if "TENENCIA" in df_val.columns:
                    n_prop = df_val.loc[mask & (df_val["TENENCIA"] == "Propietario"), "FEX_ADJ"].sum()
                    pct_prop = round(n_prop / n_exp * 100, 1) if n_exp > 0 else np.nan

                var_sal = df_val.loc[mask, "INGLABO"].var()
                prec = evaluar_media(mediana, var_sal, n_reg, n_exp, subcat, self._config_muestreo)

                filas.append({
                    "Subcategoria": subcat,
                    "n_registros": n_reg,
                    "N_expandido_M": round(n_exp / 1e6, 3),
                    "Mediana_COP": round(mediana),
                    "Mediana_SMMLV": round(mediana / self.config.smmlv, 2),
                    "Pct_propietario_%": pct_prop,
                    "CV_%": prec.cv_pct,
                    "Precision": prec.clasificacion,
                })

        return pd.DataFrame(filas).sort_values("Mediana_COP", ascending=False)

    # ══════════════════════════════════════════════════════════════
    # 6. FORMALIDAD AGROPECUARIA POR TENENCIA
    # ══════════════════════════════════════════════════════════════

    def formalidad_por_tenencia(self, df: pd.DataFrame) -> pd.DataFrame:
        """Formalidad laboral del sector agropecuario por tenencia de tierra.

        Cruza cotización a pensión (P6920) con P3064 para revelar si la
        propiedad de la tierra correlaciona con mayor formalización.

        Returns:
            DataFrame con tasas de formalidad por tenencia.
        """
        df_agro = self._filtrar_agropecuario(df)
        if df_agro.empty or "TENENCIA" not in df_agro.columns:
            return pd.DataFrame()
        if "P6920" not in df_agro.columns:
            print("⚠️  Variable P6920 (cotización pensión) no disponible.")
            return pd.DataFrame()

        df_val = df_agro[df_agro["TENENCIA"].notna()]

        filas: List[Dict[str, Any]] = []
        for tenencia in ["Propietario", "No propietario"]:
            mask = df_val["TENENCIA"] == tenencia
            n_reg = int(mask.sum())
            n_exp = df_val.loc[mask, "FEX_ADJ"].sum()

            if n_reg < 30:
                continue

            n_pension = df_val.loc[mask & (df_val["P6920"] == 1), "FEX_ADJ"].sum()
            pct_pension = round(n_pension / n_exp * 100, 1) if n_exp > 0 else np.nan

            # Contrato escrito
            pct_contrato = np.nan
            if "P6450" in df_val.columns:
                n_contrato = df_val.loc[mask & (df_val["P6450"] == 1), "FEX_ADJ"].sum()
                pct_contrato = round(n_contrato / n_exp * 100, 1) if n_exp > 0 else np.nan

            adv = advertencia_muestral(n_reg, n_exp, tenencia, self._config_muestreo)

            filas.append({
                "Tenencia": tenencia,
                "n_registros": n_reg,
                "N_expandido_M": round(n_exp / 1e6, 3),
                "Cotiza_pension_%": pct_pension,
                "Contrato_escrito_%": pct_contrato,
                "Advertencia": adv or "",
            })

        return pd.DataFrame(filas)

    # ══════════════════════════════════════════════════════════════
    # 7. REPORTE COMPLETO
    # ══════════════════════════════════════════════════════════════

    def reporte_completo(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Genera el reporte completo de análisis agropecuario por tierra.

        Ejecuta todos los análisis disponibles y retorna un diccionario
        con los resultados.

        Returns:
            Dict con claves:
              - 'brecha': brecha de ingresos por tenencia
              - 'genero': distribución por sexo
              - 'departamento': por departamento
              - 'subcategoria': por tipo de actividad
              - 'formalidad': formalidad por tenencia
              - 'costo_oportunidad': ingreso vs renta (si P3064S1 disponible)
        """
        resultados: Dict[str, pd.DataFrame] = {}

        print("\n" + "═" * 60)
        print("  REPORTE COMPLETO: TIERRA Y MERCADO LABORAL AGROPECUARIO")
        print("═" * 60)

        print("\n── 1. Brecha de ingresos por tenencia ──────────────────")
        resultados["brecha"] = self.brecha_ingresos(df)

        print("\n── 2. Distribución por género ──────────────────────────")
        resultados["genero"] = self.por_genero(df)

        print("\n── 3. Por departamento ─────────────────────────────────")
        resultados["departamento"] = self.por_departamento(df)

        print("\n── 4. Por subcategoría agropecuaria ────────────────────")
        resultados["subcategoria"] = self.por_subcategoria(df)

        print("\n── 5. Formalidad por tenencia ──────────────────────────")
        resultados["formalidad"] = self.formalidad_por_tenencia(df)

        print("\n── 6. Costo de oportunidad ─────────────────────────────")
        resultados["costo_oportunidad"] = self.costo_oportunidad(df)

        return resultados

    def exportar_excel(
        self,
        resultados: Dict[str, pd.DataFrame],
        nombre: str = "Analisis_Tierra_GEIH.xlsx",
    ) -> None:
        """Exporta todos los resultados a Excel con múltiples hojas."""
        nombres_hojas = {
            "brecha": "Brecha Ingresos",
            "genero": "Género y Tierra",
            "departamento": "Por Departamento",
            "subcategoria": "Subcategoría CIIU",
            "formalidad": "Formalidad",
            "costo_oportunidad": "Costo Oportunidad",
        }

        with pd.ExcelWriter(nombre, engine="openpyxl") as writer:
            for clave, hoja in nombres_hojas.items():
                if clave in resultados and not resultados[clave].empty:
                    resultados[clave].to_excel(writer, sheet_name=hoja, index=False)

        print(f"✅ Excel de análisis de tierras exportado: {nombre}")

    # ── Impresión ──────────────────────────────────────────────

    def _imprimir_brecha(self, resultado: pd.DataFrame) -> None:
        """Imprime resumen de brecha de ingresos por tenencia."""
        print(f"\n{'─'*60}")
        print(f"  BRECHA DE INGRESOS POR TENENCIA DE TIERRA")
        print(f"{'─'*60}")
        for _, r in resultado.iterrows():
            tenencia = r.get("Tenencia", "")
            mediana = r.get("Mediana_COP", np.nan)
            sml = r.get("Mediana_SMMLV", np.nan)
            pct_bajo = r.get("Pct_bajo_1SMMLV_%", np.nan)
            prec = r.get("Precision", "")

            if not np.isnan(mediana):
                print(f"  {tenencia:<20s} ${mediana:>12,.0f} ({sml:.2f}× SMMLV)  "
                      f"<1SML: {pct_bajo:.1f}%  {prec}")
            else:
                adv = r.get("Advertencia", "")
                print(f"  {tenencia:<20s} — {adv}")
        print(f"{'─'*60}")
