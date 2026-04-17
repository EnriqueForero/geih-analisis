# -*- coding: utf-8 -*-
"""Barrido empírico de informalidad v7.3.

Este helper explora combinaciones razonables de parámetros para el bloque
"independientes" y selecciona la configuración que minimiza el error máximo
contra el Excel oficial del DANE para diciembre de 2025.
"""

from itertools import product
import pandas as pd


def clasificar_param_v73(
    df: pd.DataFrame,
    *,
    asal_estrictez_pago: str = "fila_x_fila",
    indep_proxy_tam: bool = True,
    indep_umbral_tam: int = 4,
    indep_tam_solo_patron: bool = False,
    indep_cuasi_estricta: bool = False,
) -> pd.Series:
    """Clasificar informalidad con parámetros explícitos.

    Args:
        df: DataFrame GEIH preparado.
        asal_estrictez_pago: Tratamiento de P6110/P6940.
        indep_proxy_tam: Si se usa tamaño como apoyo empírico.
        indep_umbral_tam: Umbral sobre P3069 para considerar empresa grande.
        indep_tam_solo_patron: Si True, el tamaño solo aplica a patrones.
        indep_cuasi_estricta: Si True, cuasi-sociedad exige P6775=1 y P3068=1.

    Returns:
        Serie Int8 con 1=informal, 0=formal.
    """
    def _num(col: str):
        return pd.to_numeric(df[col], errors="coerce") if col in df.columns else None

    def _false():
        return pd.Series(False, index=df.index)

    pos = pd.to_numeric(df["P6430"], errors="coerce")
    salud_reg = _num("P6100")
    salud_pago = _num("P6110")
    pension = _num("P6920")
    pension_pag = _num("P6940")
    cont_escr = _num("P6450")
    reg_con = _num("P3067")
    renov = _num("P3067S1")
    anio_renov = _num("P3067S2")
    contab_neg = _num("P6775")
    sep_gastos = _num("P3068")
    reg_sin = _num("P3065")
    tam = _num("P3069")

    informal = pd.Series(pd.NA, index=df.index, dtype="Int8")
    informal[pos.isin([6, 8, 9])] = 1

    es_asal = pos.isin([1, 2, 3, 7])
    if salud_reg is not None:
        salud_pos = salud_reg.isin([1, 2])
    elif "P6090" in df.columns:
        salud_pos = pd.to_numeric(df["P6090"], errors="coerce") == 1
    else:
        salud_pos = _false()

    pension_pos = (pension == 1) if pension is not None else _false()

    if asal_estrictez_pago == "estricto":
        salud_ok = salud_pago.isin([1, 2, 4]) if salud_pago is not None else pd.Series(True, index=df.index)
        pension_ok = pension_pag.isin([1, 3]) if pension_pag is not None else pd.Series(True, index=df.index)
        ocup_formal_activo = salud_pos & salud_ok & pension_pos & pension_ok
    elif asal_estrictez_pago == "fila_x_fila":
        salud_invalid = salud_pago.isin([3, 5]) if salud_pago is not None else _false()
        pension_invalid = pension_pag.isin([2, 4]) if pension_pag is not None else _false()
        ocup_formal_activo = salud_pos & ~salud_invalid & pension_pos & ~pension_invalid
    elif asal_estrictez_pago == "indulgente":
        ocup_formal_activo = salud_pos & pension_pos
    else:
        raise ValueError(f"asal_estrictez_pago inválido: {asal_estrictez_pago}")

    pensionado_formal = ((pension == 3) & (cont_escr == 2)) if pension is not None and cont_escr is not None else _false()
    ocup_formal = ocup_formal_activo | pensionado_formal
    informal[es_asal & ocup_formal] = 0
    informal[es_asal & ~ocup_formal] = 1

    es_indep = pos.isin([4, 5])
    es_patron = (pos == 5)
    if tam is not None and indep_proxy_tam:
        tam_grande = (tam >= indep_umbral_tam) & tam.notna()
        tam_grande_aplica = tam_grande & es_patron if indep_tam_solo_patron else tam_grande
    else:
        tam_grande_aplica = _false()

    if reg_con is not None:
        tiene_p3067 = reg_con.notna()
        reg_vigente = (reg_con == 1)
        if anio_renov is not None and anio_renov.notna().any():
            anio_max = int(anio_renov.dropna().max())
            tiene_anio = anio_renov.notna()
            renov_anio_ok = anio_renov.between(anio_max - 1, anio_max)
            if renov is not None:
                reg_vigente = reg_vigente & ((tiene_anio & renov_anio_ok) | (~tiene_anio & (renov != 2)))
            else:
                reg_vigente = reg_vigente & tiene_anio & renov_anio_ok
        elif renov is not None:
            reg_vigente = reg_vigente & (renov != 2)
    else:
        tiene_p3067 = _false()
        reg_vigente = _false()

    if indep_cuasi_estricta:
        if contab_neg is not None and sep_gastos is not None:
            cuasi_soc = (contab_neg == 1) & (sep_gastos == 1)
        else:
            cuasi_soc = _false()
    else:
        if contab_neg is not None and sep_gastos is not None:
            cuasi_soc = (contab_neg == 1) & (sep_gastos != 2)
        elif contab_neg is not None:
            cuasi_soc = (contab_neg == 1)
        elif sep_gastos is not None:
            cuasi_soc = (sep_gastos == 1)
        else:
            cuasi_soc = _false()

    if reg_con is not None:
        ruta_a = es_indep & tiene_p3067
        sub_a1 = ruta_a & (reg_con == 1)
        if contab_neg is not None:
            sf_a1 = sub_a1 & reg_vigente & ((contab_neg == 1) | tam_grande_aplica)
        else:
            sf_a1 = sub_a1 & reg_vigente
        informal[sub_a1 & sf_a1] = 0
        informal[sub_a1 & ~sf_a1] = 1
        sub_a2 = ruta_a & (reg_con == 2)
        sf_a2 = sub_a2 & (cuasi_soc | tam_grande_aplica)
        informal[sub_a2 & sf_a2] = 0
        informal[sub_a2 & ~sf_a2] = 1
    else:
        ruta_a = _false()

    if reg_sin is not None:
        ruta_b = es_indep & ~tiene_p3067 & reg_sin.notna()
        sf_b = ruta_b & ((reg_sin == 1) | cuasi_soc | tam_grande_aplica)
        informal[ruta_b & sf_b] = 0
        informal[ruta_b & ~sf_b] = 1
    else:
        ruta_b = _false()

    ruta_c = es_indep & ~tiene_p3067 & ~ruta_b
    informal[ruta_c & tam_grande_aplica] = 0
    informal[ruta_c & ~tam_grande_aplica] = 1

    es_gob = (pos == 2)
    informal[es_gob & ocup_formal] = 0
    informal[es_gob & ~ocup_formal] = 1
    return informal


def ejecutar_barrido(df_dic: pd.DataFrame, ref_dane=None, verbose: bool = True) -> pd.DataFrame:
    """Ejecutar barrido de 24 combinaciones y ordenar por error máximo."""
    if ref_dane is None:
        ref_dane = {"nacional": 55.5, "13_AM": 41.3, "rural": 83.2}

    combinaciones = list(product(
        ["estricto", "fila_x_fila"],
        [True, False],
        [True, False],
        [3, 4, 5],
    ))

    def _tasa(df_sub: pd.DataFrame, info: pd.Series) -> float:
        oci = df_sub[df_sub["OCI"] == 1].copy()
        oci["INF_temp"] = info.loc[oci.index]
        total = oci["FEX_ADJ"].sum()
        inf = oci.loc[oci["INF_temp"] == 1, "FEX_ADJ"].sum()
        return 100 * inf / total if total > 0 else float("nan")

    resultados = []
    for asal_pago, tam_solo_pat, cuasi_estr, umbral in combinaciones:
        info = clasificar_param_v73(
            df_dic,
            asal_estrictez_pago=asal_pago,
            indep_proxy_tam=True,
            indep_umbral_tam=umbral,
            indep_tam_solo_patron=tam_solo_pat,
            indep_cuasi_estricta=cuasi_estr,
        )
        t_nac = _tasa(df_dic, info)
        t_13 = _tasa(df_dic[df_dic["DOMINIO"] == "13_AM"], info)
        t_rur = _tasa(df_dic[df_dic["DOMINIO"] == "rural"], info)
        d_nac = t_nac - ref_dane["nacional"]
        d_13 = t_13 - ref_dane["13_AM"]
        d_rur = t_rur - ref_dane["rural"]
        resultados.append({
            "asal_pago": asal_pago,
            "tam_solo_pat": tam_solo_pat,
            "cuasi_estr": cuasi_estr,
            "umbral": umbral,
            "Nac %": round(t_nac, 2),
            "Δ Nac": round(d_nac, 2),
            "13AM %": round(t_13, 2),
            "Δ 13AM": round(d_13, 2),
            "Rural %": round(t_rur, 2),
            "Δ Rural": round(d_rur, 2),
            "|Δ| total": round(abs(d_nac) + abs(d_13) + abs(d_rur), 3),
            "max |Δ|": round(max(abs(d_nac), abs(d_13), abs(d_rur)), 3),
        })

    df_res = pd.DataFrame(resultados).sort_values(["max |Δ|", "|Δ| total"], ascending=True).reset_index(drop=True)
    if verbose:
        print(df_res.to_string(index=False))
        mejor = df_res.iloc[0]
        print(f"\n🏆 Mejor configuración: max|Δ|={mejor['max |Δ|']:.3f}, |Δ| total={mejor['|Δ| total']:.3f}")
    return df_res


def aplicar_recomendacion(df_dic: pd.DataFrame, params: dict, verbose: bool = True) -> pd.DataFrame:
    """Aplicar al DataFrame una configuración concreta del barrido."""
    info = clasificar_param_v73(df_dic, **params)
    df_dic = df_dic.copy()
    df_dic["INFORMAL"] = info.astype("Int8")
    if verbose:
        oci = df_dic[df_dic["OCI"] == 1]
        for nombre, sub in [("Nacional", oci), ("13 AM", oci[oci["DOMINIO"] == "13_AM"]), ("Rural", oci[oci["DOMINIO"] == "rural"] )]:
            total = sub["FEX_ADJ"].sum()
            inf = sub.loc[sub["INFORMAL"] == 1, "FEX_ADJ"].sum()
            tasa = 100 * inf / total if total > 0 else 0.0
            print(f"  {nombre:10s}: {tasa:.2f}%")
    return df_dic
