# -*- coding: utf-8 -*-
"""
geih.muestreo — Precisión muestral y significancia estadística.

Módulo transversal que provee cálculo de errores de muestreo para
cualquier estimación derivada de la GEIH. Sin este módulo, las
desagregaciones finas (departamentales, sectoriales, por tenencia)
producen cifras sin contexto de confiabilidad.

La GEIH usa un diseño muestral complejo (probabilístico, multietápico,
estratificado, por conglomerados). Cuando las variables de diseño
(estrato, UPM) no están disponibles, se usa el efecto de diseño (DEFF)
como aproximación — estándar del DANE para publicaciones externas.

Clasificación de precisión según estándares DANE:
  - CV <  7%  → Precisión alta (✅ Publicable)
  - CV  7–15% → Precisión aceptable (⚠️ Usar con precaución)
  - CV 15–20% → Precisión baja (⚠️⚠️ Solo referencia)
  - CV > 20%  → No confiable (❌ No publicar)

PRINCIPIO DE DISEÑO:
  Este módulo NO modifica DataFrames ni calcula indicadores. Solo recibe
  valores numéricos (estimaciones, tamaños, proporciones) y devuelve
  métricas de precisión. Responsabilidad única (SRP).

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "ConfigMuestreo",
    "PrecisionEstimacion",
    "evaluar_proporcion",
    "evaluar_media",
    "evaluar_total",
    "clasificar_precision",
    "advertencia_muestral",
    "PRECISION_ALTA",
    "PRECISION_ACEPTABLE",
    "PRECISION_BAJA",
    "NO_CONFIABLE",
]


from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import numpy as np


# ═════════════════════════════════════════════════════════════════════
# CONSTANTES DE CLASIFICACIÓN
# ═════════════════════════════════════════════════════════════════════

PRECISION_ALTA: str = "✅ Precisión alta"
PRECISION_ACEPTABLE: str = "⚠️  Precisión aceptable"
PRECISION_BAJA: str = "⚠️⚠️ Precisión baja"
NO_CONFIABLE: str = "❌ No confiable"


# ═════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE MUESTREO
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ConfigMuestreo:
    """Parámetros de precisión muestral para la GEIH.

    Los valores por defecto reflejan los estándares del DANE para la
    GEIH Marco 2018. El DEFF de 2.5 es conservador para estimaciones
    nacionales; para dominios geográficos pequeños, el DEFF efectivo
    puede ser menor (menos conglomerados → menor correlación intra).

    Estos parámetros se pueden sobrecargar desde geih_config.json
    para ajustar a necesidades específicas sin modificar código fuente.

    Atributos:
        deff: Efecto de diseño aproximado. DEFF > 1 indica que el diseño
              complejo es menos eficiente que un MAS. Para la GEIH, el
              DANE reporta DEFFs entre 1.5 y 4.0 según el indicador.
        cv_preciso_pct: Umbral superior de CV para precisión alta.
        cv_aceptable_pct: Umbral superior para precisión aceptable.
        cv_poco_preciso_pct: Umbral superior para precisión baja.
        muestra_minima_registros: Registros mínimos en la base (sin expandir).
        muestra_minima_expandida: Personas expandidas mínimas (FEX_ADJ).
        nivel_confianza: Nivel de confianza para intervalos (0.90, 0.95, 0.99).
    """
    deff: float = 2.5
    cv_preciso_pct: float = 7.0
    cv_aceptable_pct: float = 15.0
    cv_poco_preciso_pct: float = 20.0
    muestra_minima_registros: int = 100
    muestra_minima_expandida: float = 50_000
    nivel_confianza: float = 0.95

    def __post_init__(self):
        if self.deff < 1.0:
            raise ValueError(
                f"deff={self.deff} no puede ser menor a 1.0. "
                f"Un diseño muestral complejo siempre tiene DEFF ≥ 1."
            )
        if not 0.80 <= self.nivel_confianza <= 0.999:
            raise ValueError(
                f"nivel_confianza={self.nivel_confianza} fuera de rango [0.80, 0.999]"
            )

    @property
    def z_alpha(self) -> float:
        """Valor Z para el nivel de confianza configurado.

        Usa la aproximación inversa de la distribución normal.
        Para niveles estándar:
          0.90 → 1.645
          0.95 → 1.960
          0.99 → 2.576
        """
        from scipy.stats import norm
        return float(norm.ppf((1 + self.nivel_confianza) / 2))


# ═════════════════════════════════════════════════════════════════════
# RESULTADO DE EVALUACIÓN DE PRECISIÓN
# ═════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PrecisionEstimacion:
    """Resultado inmutable de la evaluación de precisión de una estimación.

    Este objeto encapsula toda la información de confiabilidad de una
    cifra. Cualquier clase de análisis puede retornar esto junto con
    la estimación puntual.

    Atributos:
        estimacion: Valor puntual de la estimación.
        error_estandar: Error estándar de la estimación.
        cv_pct: Coeficiente de variación en porcentaje.
        ic_inferior: Límite inferior del intervalo de confianza.
        ic_superior: Límite superior del intervalo de confianza.
        nivel_confianza: Nivel de confianza usado (ej: 0.95).
        n_registros: Tamaño muestral en registros (sin expandir).
        n_expandido: Tamaño poblacional estimado (con FEX).
        clasificacion: Etiqueta de precisión DANE.
        es_confiable: True si CV ≤ umbral de precisión aceptable.
        dominio: Nombre del dominio de estimación (ej: "Antioquia").
    """
    estimacion: float
    error_estandar: float
    cv_pct: float
    ic_inferior: float
    ic_superior: float
    nivel_confianza: float
    n_registros: int
    n_expandido: float
    clasificacion: str
    es_confiable: bool
    dominio: str = "Nacional"

    def resumen(self) -> str:
        """Resumen legible de la precisión para impresión."""
        return (
            f"  {self.dominio:<25s} "
            f"Est={self.estimacion:>10.1f}  "
            f"EE={self.error_estandar:>8.2f}  "
            f"CV={self.cv_pct:>5.1f}%  "
            f"IC=[{self.ic_inferior:.1f}, {self.ic_superior:.1f}]  "
            f"n={self.n_registros:>6,}  "
            f"N̂={self.n_expandido/1e6:.3f}M  "
            f"{self.clasificacion}"
        )


# ═════════════════════════════════════════════════════════════════════
# FUNCIONES DE EVALUACIÓN DE PRECISIÓN
# ═════════════════════════════════════════════════════════════════════

def clasificar_precision(cv_pct: float, config: Optional[ConfigMuestreo] = None) -> str:
    """Clasifica la precisión de una estimación según su CV.

    Implementa la clasificación estándar del DANE para publicaciones
    de la GEIH.

    Args:
        cv_pct: Coeficiente de variación en porcentaje.
        config: Parámetros de muestreo. Si None, usa defaults DANE.

    Returns:
        Etiqueta de clasificación con emoji indicador.
    """
    cfg = config or ConfigMuestreo()
    if np.isnan(cv_pct) or cv_pct < 0:
        return NO_CONFIABLE
    if cv_pct <= cfg.cv_preciso_pct:
        return PRECISION_ALTA
    if cv_pct <= cfg.cv_aceptable_pct:
        return PRECISION_ACEPTABLE
    if cv_pct <= cfg.cv_poco_preciso_pct:
        return PRECISION_BAJA
    return NO_CONFIABLE


def evaluar_proporcion(
    proporcion: float,
    n_registros: int,
    n_expandido: float,
    dominio: str = "Nacional",
    config: Optional[ConfigMuestreo] = None,
) -> PrecisionEstimacion:
    """Evalúa la precisión de una estimación de proporción (ej: TD, TGP).

    Usa la fórmula de varianza de una proporción bajo MAS ajustada
    por el efecto de diseño (DEFF):

        Var(p̂) ≈ DEFF × p(1-p) / n

    Donde:
      - p = proporción estimada (ej: 0.089 para TD=8.9%)
      - n = tamaño muestral efectivo (registros, no expandido)
      - DEFF = efecto de diseño del muestreo complejo

    Args:
        proporcion: Proporción estimada entre 0 y 1.
        n_registros: Registros en la base (sin expandir).
        n_expandido: Personas expandidas con FEX_ADJ.
        dominio: Nombre del dominio para el reporte.
        config: Parámetros de muestreo.

    Returns:
        PrecisionEstimacion con toda la información de confiabilidad.

    Ejemplo:
        >>> evaluar_proporcion(0.089, n_registros=50000, n_expandido=26e6)
        PrecisionEstimacion(estimacion=8.9, cv_pct=1.2, ...)
    """
    cfg = config or ConfigMuestreo()

    # Protección contra inputs degenerados
    p = max(0.001, min(proporcion, 0.999))
    n = max(1, n_registros)

    # Varianza bajo diseño complejo
    var_p = cfg.deff * p * (1 - p) / n
    se = np.sqrt(var_p)

    # CV en porcentaje
    cv_pct = (se / p * 100) if p > 0 else np.nan

    # Intervalo de confianza
    z = cfg.z_alpha
    ic_inf = max(0, p - z * se)
    ic_sup = min(1, p + z * se)

    clasificacion = clasificar_precision(cv_pct, cfg)
    es_confiable = cv_pct <= cfg.cv_aceptable_pct if not np.isnan(cv_pct) else False

    return PrecisionEstimacion(
        estimacion=round(p * 100, 2),
        error_estandar=round(se * 100, 4),
        cv_pct=round(cv_pct, 1) if not np.isnan(cv_pct) else np.nan,
        ic_inferior=round(ic_inf * 100, 2),
        ic_superior=round(ic_sup * 100, 2),
        nivel_confianza=cfg.nivel_confianza,
        n_registros=n,
        n_expandido=n_expandido,
        clasificacion=clasificacion,
        es_confiable=es_confiable,
        dominio=dominio,
    )


def evaluar_media(
    media: float,
    varianza_muestral: float,
    n_registros: int,
    n_expandido: float,
    dominio: str = "Nacional",
    config: Optional[ConfigMuestreo] = None,
) -> PrecisionEstimacion:
    """Evalúa la precisión de una estimación de media (ej: ingreso mediano).

    Usa la fórmula:
        Var(x̄) ≈ DEFF × S² / n

    Args:
        media: Media (o mediana) estimada.
        varianza_muestral: Varianza muestral de la variable.
        n_registros: Registros en la base.
        n_expandido: Personas expandidas con FEX_ADJ.
        dominio: Nombre del dominio.
        config: Parámetros de muestreo.

    Returns:
        PrecisionEstimacion con información de confiabilidad.
    """
    cfg = config or ConfigMuestreo()

    n = max(1, n_registros)
    var_media = cfg.deff * varianza_muestral / n
    se = np.sqrt(max(0, var_media))

    cv_pct = (se / abs(media) * 100) if abs(media) > 0 else np.nan

    z = cfg.z_alpha
    ic_inf = media - z * se
    ic_sup = media + z * se

    clasificacion = clasificar_precision(cv_pct, cfg)
    es_confiable = cv_pct <= cfg.cv_aceptable_pct if not np.isnan(cv_pct) else False

    return PrecisionEstimacion(
        estimacion=round(media, 2),
        error_estandar=round(se, 2),
        cv_pct=round(cv_pct, 1) if not np.isnan(cv_pct) else np.nan,
        ic_inferior=round(ic_inf, 2),
        ic_superior=round(ic_sup, 2),
        nivel_confianza=cfg.nivel_confianza,
        n_registros=n,
        n_expandido=n_expandido,
        clasificacion=clasificacion,
        es_confiable=es_confiable,
        dominio=dominio,
    )


def evaluar_total(
    total_expandido: float,
    n_registros: int,
    n_expandido: float,
    proporcion_universo: float = 1.0,
    dominio: str = "Nacional",
    config: Optional[ConfigMuestreo] = None,
) -> PrecisionEstimacion:
    """Evalúa la precisión de una estimación de total (ej: Total Ocupados).

    Aproximación para totales poblacionales:
        CV(T̂) ≈ CV(p̂) cuando T̂ = N × p̂

    Args:
        total_expandido: Total estimado (expandido con FEX_ADJ).
        n_registros: Registros en la muestra.
        n_expandido: Universo expandido total.
        proporcion_universo: Proporción que el total representa del universo.
        dominio: Nombre del dominio.
        config: Parámetros de muestreo.

    Returns:
        PrecisionEstimacion con información de confiabilidad.
    """
    cfg = config or ConfigMuestreo()

    p = max(0.001, min(proporcion_universo, 0.999))
    precision_prop = evaluar_proporcion(
        p, n_registros, n_expandido, dominio, cfg
    )

    # Transferir el CV de la proporción al total
    cv_pct = precision_prop.cv_pct
    se_total = abs(total_expandido) * cv_pct / 100 if not np.isnan(cv_pct) else np.nan

    z = cfg.z_alpha
    ic_inf = total_expandido - z * se_total if not np.isnan(se_total) else np.nan
    ic_sup = total_expandido + z * se_total if not np.isnan(se_total) else np.nan

    clasificacion = clasificar_precision(cv_pct, cfg)
    es_confiable = cv_pct <= cfg.cv_aceptable_pct if not np.isnan(cv_pct) else False

    return PrecisionEstimacion(
        estimacion=round(total_expandido, 0),
        error_estandar=round(se_total, 0) if not np.isnan(se_total) else np.nan,
        cv_pct=round(cv_pct, 1) if not np.isnan(cv_pct) else np.nan,
        ic_inferior=round(ic_inf, 0) if not np.isnan(ic_inf) else np.nan,
        ic_superior=round(ic_sup, 0) if not np.isnan(ic_sup) else np.nan,
        nivel_confianza=cfg.nivel_confianza,
        n_registros=n_registros,
        n_expandido=n_expandido,
        clasificacion=clasificacion,
        es_confiable=es_confiable,
        dominio=dominio,
    )


def advertencia_muestral(
    n_registros: int,
    n_expandido: float,
    dominio: str = "Dominio",
    config: Optional[ConfigMuestreo] = None,
) -> Optional[str]:
    """Genera advertencia si el tamaño muestral es insuficiente.

    Evalúa tanto los registros en la base (sin expandir) como las
    personas expandidas. Ambos deben superar los umbrales mínimos.

    Args:
        n_registros: Registros en la muestra.
        n_expandido: Personas expandidas.
        dominio: Nombre del dominio para el mensaje.
        config: Parámetros de muestreo.

    Returns:
        Mensaje de advertencia si la muestra es insuficiente, None si es OK.
    """
    cfg = config or ConfigMuestreo()
    mensajes = []

    if n_registros < cfg.muestra_minima_registros:
        mensajes.append(
            f"n={n_registros:,} registros < mínimo {cfg.muestra_minima_registros:,}"
        )
    if n_expandido < cfg.muestra_minima_expandida:
        mensajes.append(
            f"N̂={n_expandido:,.0f} expandidos < mínimo {cfg.muestra_minima_expandida:,.0f}"
        )

    if mensajes:
        return (
            f"⚠️  MUESTRA INSUFICIENTE en {dominio}: "
            + "; ".join(mensajes)
            + ". Las estimaciones pueden no ser confiables."
        )
    return None
