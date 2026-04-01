# -*- coding: utf-8 -*-
"""
geih.config — Configuración centralizada para el análisis GEIH.

Toda constante, mapeo, paleta de colores y parámetro configurable vive aquí.
Nunca hay "números mágicos" sueltos en la lógica de negocio.

CAMBIO v5.1 — Configuración externa + departamentos completos:
  - Soporte para geih_config.json externo: actualizar SMMLV y referencias
    DANE sin necesidad de lanzar un nuevo release a PyPI.
  - 33 departamentos (32 + Bogotá D.C.) — antes faltaban 9 de Amazonía,
    Orinoquía y San Andrés.
  - ConfigMuestreo integrada para precisión estadística.
  - ConfigGEIH ahora tiene `config_muestreo` embebida.

CAMBIO v4.0 — Escalabilidad multi-año:
  - ConfigGEIH ahora recibe `anio` y auto-selecciona SMMLV y carpetas.
  - MESES_CARPETAS es ahora una función, no una lista hardcoded.
  - ReferenciaDane es un diccionario por año.
  - Para años sin referencia DANE publicada, el sanity_check advierte
    en vez de fallar.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "SMMLV_POR_ANIO",
    "SMMLV_2025",
    "CARGA_PRESTACIONAL",
    "MESES_NOMBRES",
    "generar_carpetas_mensuales",
    "generar_etiqueta_periodo",
    "MESES_CARPETAS",
    "ConfigGEIH",
    "COLORES",
    "LLAVES_PERSONA",
    "LLAVES_HOGAR",
    "CONVERTERS_BASE",
    "CONVERTERS_CON_AREA",
    "MODULOS_CSV",
    "VARIABLES_POR_MODULO",
    "RAMAS_DANE",
    "TABLA_CIIU_RAMAS",
    "AGRUPACION_DANE_8",
    "_AGRUP_DANE_POR_DIVISION",
    "DEPARTAMENTOS",
    "DPTO_A_CIUDAD",
    "AREA_A_CIUDAD",
    "CIUDADES_13_PRINCIPALES",
    "CIUDADES_10_INTERMEDIAS",
    "NIVELES_EDUCATIVOS",
    "NIVELES_AGRUPADOS",
    "P3042_A_ANOS",
    "RANGOS_SMMLV_LIMITES",
    "RANGOS_SMMLV_ETIQUETAS",
    "TAMANO_EMPRESA",
    "CIIU_DESCRIPCION_FALLBACK",
    "ReferenciaDane",
    "REF_DANE",
    "REF_DANE_2025",
    "cargar_config_externa",
]


import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


# ═════════════════════════════════════════════════════════════════════
# CARGA DE CONFIGURACIÓN EXTERNA (geih_config.json)
# ═════════════════════════════════════════════════════════════════════

_CONFIG_EXTERNA_CACHE: Optional[Dict[str, Any]] = None


def cargar_config_externa(
    ruta: Optional[str] = None,
    silencioso: bool = True,
) -> Dict[str, Any]:
    """Carga configuración desde un archivo JSON externo.

    Busca geih_config.json en este orden de prioridad:
      1. Ruta explícita proporcionada como argumento.
      2. Variable de entorno GEIH_CONFIG_PATH.
      3. Directorio de trabajo actual: ./geih_config.json
      4. Home del usuario: ~/.geih/geih_config.json

    Si no encuentra ningún archivo, retorna un dict vacío y usa
    los valores por defecto hardcodeados en este módulo.

    Este diseño permite actualizar el SMMLV de un año nuevo o agregar
    referencias DANE sin necesidad de lanzar un nuevo release a PyPI.

    Args:
        ruta: Ruta explícita al archivo JSON. Si None, busca automáticamente.
        silencioso: Si True, no imprime mensaje cuando no encuentra archivo.

    Returns:
        Diccionario con la configuración externa, o {} si no existe.

    Ejemplo:
        >>> cfg = cargar_config_externa("/mi/ruta/geih_config.json")
        >>> cfg.get("smmlv_por_anio", {}).get("2027", None)
        1_900_000
    """
    global _CONFIG_EXTERNA_CACHE

    # Cache: solo leer el archivo una vez por sesión
    if _CONFIG_EXTERNA_CACHE is not None and ruta is None:
        return _CONFIG_EXTERNA_CACHE

    import os

    # Orden de búsqueda
    candidatos: List[Path] = []
    if ruta:
        candidatos.append(Path(ruta))
    env_path = os.environ.get("GEIH_CONFIG_PATH")
    if env_path:
        candidatos.append(Path(env_path))
    candidatos.append(Path.cwd() / "geih_config.json")
    candidatos.append(Path.home() / ".geih" / "geih_config.json")

    for archivo in candidatos:
        if archivo.exists() and archivo.is_file():
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not silencioso:
                    print(f"📋 Configuración externa cargada: {archivo}")
                _CONFIG_EXTERNA_CACHE = data
                return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️  Error leyendo {archivo}: {e}. Usando defaults.")
                _CONFIG_EXTERNA_CACHE = {}
                return {}

    if not silencioso:
        print("ℹ️  No se encontró geih_config.json. Usando configuración interna.")
    _CONFIG_EXTERNA_CACHE = {}
    return {}


def _merge_smmlv(hardcoded: Dict[int, int]) -> Dict[int, int]:
    """Combina SMMLV hardcodeado con valores del JSON externo.

    El JSON externo tiene prioridad: si define un año que ya existe
    en el hardcoded, lo sobreescribe. Esto permite corregir errores
    sin un nuevo release.
    """
    ext = cargar_config_externa()
    ext_smmlv = ext.get("smmlv_por_anio", {})
    merged = dict(hardcoded)
    for anio_str, valor in ext_smmlv.items():
        try:
            merged[int(anio_str)] = int(valor)
        except (ValueError, TypeError):
            continue
    return merged


# ═════════════════════════════════════════════════════════════════════
# PARÁMETROS ECONÓMICOS — MULTI-AÑO
# ═════════════════════════════════════════════════════════════════════

_SMMLV_HARDCODED: Dict[int, int] = {
    2022: 1_000_000,
    2023: 1_160_000,
    2024: 1_300_000,
    2025: 1_423_500,
    2026: 1_750_905,   # Decreto 2426 de 2025
}

# Merge con configuración externa (si existe)
SMMLV_POR_ANIO: Dict[int, int] = _merge_smmlv(_SMMLV_HARDCODED)
"""SMMLV por año en COP. Se actualiza automáticamente desde geih_config.json
si existe, sin necesidad de un nuevo release a PyPI."""

# Retrocompatibilidad
SMMLV_2025: int = SMMLV_POR_ANIO.get(2025, 1_423_500)

CARGA_PRESTACIONAL: float = cargar_config_externa().get(
    "carga_prestacional", 0.54
)
"""Factor de carga prestacional sobre salario base en Colombia (~54%).
Incluye pensión 12%, salud 8.5%, parafiscales 9%, cesantías 8.33%,
intereses 1%, prima 8.33%, vacaciones 4.17%, riesgos variable."""


# ═════════════════════════════════════════════════════════════════════
# NOMBRES DE LOS MESES (GENERACIÓN DINÁMICA DE CARPETAS)
# ═════════════════════════════════════════════════════════════════════

MESES_NOMBRES: List[str] = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
"""Nombres de meses en español, tal como los usa el DANE en sus carpetas."""


def generar_carpetas_mensuales(anio: int, n_meses: int = 12) -> List[str]:
    """Genera la lista de carpetas mensuales para un año y cantidad de meses.

    El DANE nombra las carpetas como 'Enero 2025', 'Febrero 2025', etc.
    Esta función genera esa lista dinámicamente.

    Args:
        anio: Año de los datos (ej: 2025, 2026).
        n_meses: Cuántos meses generar (1-12).

    Returns:
        Lista de strings como ['Enero 2025', 'Febrero 2025', ...].
    """
    n = max(1, min(n_meses, 12))
    return [f"{mes} {anio}" for mes in MESES_NOMBRES[:n]]


def generar_etiqueta_periodo(
    anio: int,
    n_meses: int = 12,
    meses_rango: Optional[List[int]] = None,
) -> str:
    """Genera la etiqueta legible del período para títulos y reportes.

    CAMBIO v5.1: Soporta rangos de meses arbitrarios para análisis
    semestral u otros períodos no contiguos desde el inicio.

    Ejemplos:
        (2025, 12)               → 'Enero – Diciembre 2025'
        (2026, 3)                → 'Enero – Marzo 2026'
        (2026, 1)                → 'Enero 2026'
        (2025, 6, [7,8,9,10,11,12]) → 'Julio – Diciembre 2025'
    """
    if meses_rango:
        # Rango explícito: usar primer y último mes del rango
        meses_ord = sorted(meses_rango)
        inicio = MESES_NOMBRES[meses_ord[0] - 1]
        fin = MESES_NOMBRES[meses_ord[-1] - 1]
        if len(meses_ord) == 1:
            return f"{inicio} {anio}"
        return f"{inicio} – {fin} {anio}"

    n = max(1, min(n_meses, 12))
    if n == 1:
        return f"{MESES_NOMBRES[0]} {anio}"
    return f"{MESES_NOMBRES[0]} – {MESES_NOMBRES[n - 1]} {anio}"


# Retrocompatibilidad
MESES_CARPETAS: List[str] = generar_carpetas_mensuales(2025, 12)


# ═════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ANÁLISIS — MULTI-AÑO
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ConfigGEIH:
    """Parámetros configurables para el pipeline GEIH.

    Centraliza todo lo que un usuario necesita ajustar.
    Valida en __post_init__ para fallar rápido si algo está mal.

    CAMBIO v5.1:
      - Soporte para `meses_rango`: filtrar meses arbitrarios (semestral).
      - `config_muestreo` embebida para cálculos de precisión estadística.
      - SMMLV se carga automáticamente desde geih_config.json si existe.

    CAMBIO v4.0:
      - Recibe `anio` y auto-deriva SMMLV, carpetas y etiqueta de período.

    Uso típico:
        # Año 2025 completo
        config = ConfigGEIH(anio=2025, n_meses=12)

        # Primer semestre 2025
        config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[1,2,3,4,5,6])

        # Segundo semestre 2025
        config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[7,8,9,10,11,12])

    NOTA sobre meses_rango y n_meses:
        - `n_meses` controla cómo se divide el FEX_C18 (divisor del factor
          de expansión). Si el Parquet tiene 12 meses, n_meses=12.
        - `meses_rango` controla QUÉ meses se incluyen en el análisis.
        - Son independientes: un Parquet de 12 meses (n_meses=12) puede
          analizarse en subconjuntos semestrales (meses_rango=[1..6]).
        - Para un semestre donde el FEX ya fue dividido entre 12, el
          divisor correcto sigue siendo 12, no 6. La reducción del universo
          se refleja en que se suman menos registros, no en el divisor.
    """
    anio: int = 2025
    """Año de los datos a procesar."""

    n_meses: int = 12
    """Número de meses consolidados. Controla la división del FEX_C18."""

    meses_rango: Optional[List[int]] = None
    """Rango de meses a incluir en el análisis (1-12). Si None, incluye todos.
    Permite análisis semestral: [1,2,3,4,5,6] o [7,8,9,10,11,12].
    No afecta el divisor del FEX_C18 — eso lo controla n_meses."""

    smmlv: int = 0
    """SMMLV del año de análisis en COP. Si 0, se auto-selecciona."""

    periodo_etiqueta: str = ""
    """Etiqueta legible para títulos y reportes. Si vacía, se genera."""

    random_seed: int = 42
    """Semilla para reproducibilidad."""

    encoding_csv: str = "latin-1"
    """Encoding de los CSV del DANE."""

    separador_csv: str = ";"
    """Separador de columnas en los CSV del DANE."""

    edad_minima_oit: int = 15
    """Edad mínima para análisis de mercado laboral (estándar OIT)."""

    edad_minima_dane: int = 10
    """Edad mínima usada por el DANE para PET."""

    def __post_init__(self):
        """Valida parámetros y auto-deriva valores calculados."""
        
        # ── 1. Sincronización automática de divisor poblacional ──
        # Si el usuario pasa un filtro de meses específico, el divisor
        # del factor de expansión (n_meses) DEBE ser exactamente la 
        # cantidad de meses filtrados para no inflar/reducir la población.
        if self.meses_rango is not None:
            if not isinstance(self.meses_rango, list):
                raise TypeError("meses_rango debe ser una lista de enteros")
            
            # ¡AQUÍ ESTÁ LA MAGIA! Sincronización forzada:
            self.n_meses = len(self.meses_rango)
            
        # ── Validación básica ──────────────────────────────────────
        if self.n_meses < 1 or self.n_meses > 12:
            raise ValueError(f"n_meses={self.n_meses} fuera de rango [1, 12]")
        if self.anio < 2018 or self.anio > 2050:
            raise ValueError(
                f"anio={self.anio} fuera de rango [2018, 2050]. "
                f"La GEIH Marco 2018 inicia en 2022."
            )

        # ── Validar meses_rango ────────────────────────────────────
        if self.meses_rango is not None:
            if not isinstance(self.meses_rango, list):
                raise TypeError(
                    f"meses_rango debe ser una lista de enteros, "
                    f"recibido: {type(self.meses_rango)}"
                )
            for m in self.meses_rango:
                if not isinstance(m, int) or m < 1 or m > 12:
                    raise ValueError(
                        f"Mes {m} en meses_rango fuera de rango [1, 12]"
                    )
            # Verificar que los meses del rango estén dentro de n_meses
            max_mes = max(self.meses_rango)
            if max_mes > self.n_meses:
                raise ValueError(
                    f"meses_rango incluye mes {max_mes} pero n_meses={self.n_meses}. "
                    f"Los meses del rango deben existir en el consolidado."
                )

        # ── Auto-seleccionar SMMLV según el año ────────────────────
        if self.smmlv == 0:
            if self.anio in SMMLV_POR_ANIO:
                self.smmlv = SMMLV_POR_ANIO[self.anio]
            else:
                ultimo_anio = max(SMMLV_POR_ANIO.keys())
                self.smmlv = SMMLV_POR_ANIO[ultimo_anio]
                print(
                    f"⚠️  SMMLV para {self.anio} no está registrado en "
                    f"SMMLV_POR_ANIO. Usando el de {ultimo_anio}: "
                    f"${self.smmlv:,}. Actualice config.py o geih_config.json "
                    f"cuando se publique el decreto."
                )

        if self.smmlv < 100_000:
            raise ValueError(f"smmlv={self.smmlv} parece demasiado bajo")

        # ── Auto-generar etiqueta de período ───────────────────────
        if not self.periodo_etiqueta:
            self.periodo_etiqueta = generar_etiqueta_periodo(
                self.anio, self.n_meses, self.meses_rango
            )

    # ── Propiedades calculadas ──────────────────────────────────
    @property
    def carpetas_mensuales(self) -> List[str]:
        """Lista de carpetas mensuales DANE para este año y n_meses."""
        return generar_carpetas_mensuales(self.anio, self.n_meses)

    @property
    def referencia_dane(self) -> Optional["ReferenciaDane"]:
        """Referencia DANE para validación, o None si no está disponible."""
        return REF_DANE.get(self.anio)

    @property
    def config_muestreo(self) -> "ConfigMuestreo":
        """Configuración de precisión muestral. Carga desde JSON si existe."""
        from .muestreo import ConfigMuestreo
        ext = cargar_config_externa()
        muestreo_cfg = ext.get("muestreo", {})
        return ConfigMuestreo(**{
            k: v for k, v in muestreo_cfg.items()
            if k in ConfigMuestreo.__dataclass_fields__
        }) if muestreo_cfg else ConfigMuestreo()

    def resumen(self) -> None:
        """Imprime un resumen legible de la configuración activa."""
        ref = self.referencia_dane
        ref_status = "✅ Disponible" if ref else "⚠️  No disponible"
        ext = cargar_config_externa()
        ext_status = "✅ Cargado" if ext else "—  No encontrado (usando defaults)"

        print(f"\n{'='*60}")
        print(f"  CONFIGURACIÓN GEIH — {self.periodo_etiqueta}")
        print(f"{'='*60}")
        print(f"  Año              : {self.anio}")
        print(f"  Meses (divisor)  : {self.n_meses}")
        if self.meses_rango:
            print(f"  Meses (filtro)   : {self.meses_rango}")
        print(f"  SMMLV            : ${self.smmlv:,} COP")
        print(f"  FEX divisor      : ÷ {self.n_meses}")
        print(f"  Ref. DANE        : {ref_status}")
        print(f"  Config externa   : {ext_status}")
        print(f"  Carpetas         : {self.carpetas_mensuales[0]} → "
              f"{self.carpetas_mensuales[-1]}")
        print(f"{'='*60}")


# ═════════════════════════════════════════════════════════════════════
# PALETA DE COLORES INSTITUCIONAL
# ═════════════════════════════════════════════════════════════════════

COLORES: Dict[str, str] = {
    "azul":     "#2E6DA4",
    "rojo":     "#C0392B",
    "verde":    "#1E8449",
    "morado":   "#7D3C98",
    "naranja":  "#E67E22",
    "gris":     "#7F8C8D",
    "cyan":     "#1ABC9C",
    "amarillo": "#F39C12",
    "negro":    "#1A252F",
    "linea":    "#BDC3C7",
    "fondo":    "#F7F9FC",
}


# ═════════════════════════════════════════════════════════════════════
# LLAVES DE ENLACE ENTRE MÓDULOS GEIH
# ═════════════════════════════════════════════════════════════════════

LLAVES_PERSONA: List[str] = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
"""Llave única a nivel de persona (individuo)."""

LLAVES_HOGAR: List[str] = ["DIRECTORIO", "SECUENCIA_P"]
"""Llave única a nivel de hogar."""


# ═════════════════════════════════════════════════════════════════════
# COLUMNAS QUE DEBEN LEERSE COMO STRING
# ═════════════════════════════════════════════════════════════════════

CONVERTERS_BASE: Dict[str, type] = {
    "DIRECTORIO":  str,
    "SECUENCIA_P": str,
    "ORDEN":       str,
    "DPTO":        str,
    "RAMA2D_R4":   str,
    "RAMA4D_R4":   str,
}

CONVERTERS_CON_AREA: Dict[str, type] = {
    **CONVERTERS_BASE,
    "AREA": str,
}


# ═════════════════════════════════════════════════════════════════════
# NOMBRES DE ARCHIVOS CSV POR MÓDULO GEIH
# ═════════════════════════════════════════════════════════════════════

MODULOS_CSV: Dict[str, str] = {
    "caracteristicas": "Características generales, seguridad social en salud y educación.CSV",
    "hogar":           "Datos del hogar y la vivienda.CSV",
    "fuerza_trabajo":  "Fuerza de trabajo.CSV",
    "ocupados":        "Ocupados.CSV",
    "no_ocupados":     "No ocupados.CSV",
    "otras_formas":    "Otras formas de trabajo.CSV",
    "migracion":       "Migración.CSV",
    "otros_ingresos":  "Otros ingresos e impuestos.CSV",
}

VARIABLES_POR_MODULO: Dict[str, List[str]] = {
    "caracteristicas": [
        "P3271",      # Sexo (1=H, 2=M)
        "P6040",      # Edad
        "P6080",      # Autorreconocimiento étnico
        "P3042",      # Nivel educativo (1-13)
        "P3043S1",    # Campo de formación (CINE-F)
        "P6090",      # Afiliado salud (1=Sí)
        "P2057",      # ¿Se considera campesino? (1=Sí)
        "P2059",      # ¿Alguna vez fue campesino?
        "P1906S1", "P1906S2", "P1906S3", "P1906S4",
        "P1906S5", "P1906S6", "P1906S7", "P1906S8",
        "CLASE",      # Zona (1=Urbano, 2=Rural)
        "FEX_C18",    # Factor de expansión
    ],
    "ocupados": [
        "OCI", "INGLABO", "P6500", "P6430", "P6800", "P6850",
        "P6920", "P3069", "P7130", "P6440", "P6450", "P6460",
        "P1802", "P3047", "P3048", "P3049", "P3363", "P3364",
        "P6765", "P6400", "P6410",
        "P6510S1", "P6580S1", "P6585S1A1", "P6585S2A1",
        "RAMA2D_R4", "RAMA4D_R4", "AREA",
        # Tenencia de tierra y tipo de actividad (v5.1)
        "P3056",      # Tipo de actividad del negocio (1=mercancías, 2=agro)
        "P3064",      # ¿Propietario de la tierra? (1=Sí, 2=No)
        "P3064S1",    # Valor estimado arriendo terreno (COP/mes)
    ],
    "no_ocupados": [
        "DSI", "P7250", "P6300", "P6310", "FFT",
    ],
    "fuerza_trabajo": [
        "FT", "PET", "P6240", "P6280",
    ],
    "otras_formas": [
        "P3054", "P3054S1", "P3055", "P3055S1", "P3056", "P3057",
    ],
    "migracion": [
        "P3370", "P3370S1", "P3371", "P3376", "P3378S1",
    ],
    "otros_ingresos": [
        "P7422", "P7500S1", "P7500S1A1", "P7500S2", "P7500S2A1",
        "P7500S3", "P7510S1", "P7510S2", "P7510S2A1", "P7510S3",
    ],
}


# ═════════════════════════════════════════════════════════════════════
# MAPEO CIIU Rev.4 → 13 RAMAS DANE
# ═════════════════════════════════════════════════════════════════════

RAMAS_DANE: Dict[str, str] = {
    "AGRI": "Agricultura, ganadería, caza, silvicultura y pesca",
    "SUMI": "Suministro de electricidad, gas, agua y gestión de desechos^",
    "MANU": "Industrias manufactureras",
    "CONS": "Construcción",
    "COME": "Comercio y reparación de vehículos",
    "TRAN": "Transporte y almacenamiento",
    "ALOJ": "Alojamiento y servicios de comida",
    "INFO": "Información y comunicaciones",
    "FINA": "Actividades financieras y de seguros",
    "INMO": "Actividades inmobiliarias",
    "PROF": "Actividades profesionales, científicas, técnicas y de servicios administrativos",
    "ADMP": "Administración pública y defensa, educación y atención de la salud humana",
    "ARTE": "Actividades artísticas, entretenimiento, recreación y otras actividades de servicio",
}

TABLA_CIIU_RAMAS: List[Tuple[int, int, str]] = [
    (1,  3,  "AGRI"), (5,  9,  "SUMI"), (10, 33, "MANU"),
    (35, 35, "SUMI"), (36, 39, "SUMI"), (41, 43, "CONS"),
    (45, 47, "COME"), (49, 53, "TRAN"), (55, 56, "ALOJ"),
    (58, 63, "INFO"), (64, 66, "FINA"), (68, 68, "INMO"),
    (69, 75, "PROF"), (77, 82, "PROF"), (84, 84, "ADMP"),
    (85, 85, "ADMP"), (86, 88, "ADMP"), (90, 93, "ARTE"),
    (94, 96, "ARTE"), (97, 98, "ARTE"), (99, 99, "ARTE"),
]


# ═════════════════════════════════════════════════════════════════════
# AGRUPACIÓN DANE DE 8 GRUPOS
# ═════════════════════════════════════════════════════════════════════

AGRUPACION_DANE_8: Dict[str, List[Tuple[int, int]]] = {
    "Agricultura, ganadería, pesca y silvicultura":              [(1, 3)],
    "Explotación de minas y canteras":                           [(5, 9)],
    "Industrias manufactureras":                                 [(10, 33)],
    "Electricidad, agua, gas y desechos":                        [(35, 39)],
    "Construcción":                                              [(41, 43)],
    "Comercio, transporte, alojamiento y comida":                [(45, 56)],
    "Actividades financieras, profesionales y administrativas":  [(58, 83)],
    "Administración pública, educación, salud y otros":          [(84, 99)],
}

_AGRUP_DANE_POR_DIVISION: Dict[str, str] = {}
for _nombre, _rangos in AGRUPACION_DANE_8.items():
    for _lo, _hi in _rangos:
        for _i in range(_lo, _hi + 1):
            _AGRUP_DANE_POR_DIVISION[str(_i).zfill(2)] = _nombre


# ═════════════════════════════════════════════════════════════════════
# DEPARTAMENTOS DE COLOMBIA — COMPLETO (33 ENTIDADES)
# ═════════════════════════════════════════════════════════════════════
# CAMBIO v5.1: Antes tenía 24 departamentos. Ahora incluye los 32
# departamentos + Bogotá D.C. La documentación DDI de la GEIH 2025
# confirma cobertura en cabeceras de capitales de Amazonía y Orinoquía.
# San Andrés se cubre en cabecera (excluyendo Providencia y rural).

DEPARTAMENTOS: Dict[str, str] = {
    "05": "Antioquia",               "08": "Atlántico",
    "11": "Bogotá D.C.",             "13": "Bolívar",
    "15": "Boyacá",                  "17": "Caldas",
    "18": "Caquetá",                 "19": "Cauca",
    "20": "Cesar",                   "23": "Córdoba",
    "25": "Cundinamarca",            "27": "Chocó",
    "41": "Huila",                   "44": "La Guajira",
    "47": "Magdalena",               "50": "Meta",
    "52": "Nariño",                  "54": "Norte de Santander",
    "63": "Quindío",                 "66": "Risaralda",
    "68": "Santander",               "70": "Sucre",
    "73": "Tolima",                  "76": "Valle del Cauca",
    # ── Amazonía y Orinoquía (v5.1) ────────────────────────────
    "81": "Arauca",                  "85": "Casanare",
    "86": "Putumayo",                "88": "San Andrés y Providencia",
    "91": "Amazonas",                "94": "Guainía",
    "95": "Guaviare",                "97": "Vaupés",
    "99": "Vichada",
}
"""33 entidades territoriales de Colombia (32 departamentos + Bogotá D.C.).

NOTA MUESTRAL: Los departamentos de Amazonía/Orinoquía tienen muestra
limitada en la GEIH (solo cabeceras de capitales). Las estimaciones para
estos departamentos deben evaluarse con la infraestructura de muestreo
(geih.muestreo) antes de publicarse. El DANE no publica cifras mensuales
para estos departamentos por esta razón."""


# ═════════════════════════════════════════════════════════════════════
# CIUDADES Y ÁREAS METROPOLITANAS
# ═════════════════════════════════════════════════════════════════════

DPTO_A_CIUDAD: Dict[str, str] = {
    "11": "Bogotá D.C.",          "05": "Medellín A.M.",
    "76": "Cali A.M.",            "08": "Barranquilla A.M.",
    "68": "Bucaramanga A.M.",     "17": "Manizales A.M.",
    "66": "Pereira A.M.",         "54": "Cúcuta A.M.",
    "52": "Pasto",                "41": "Ibagué",
    "23": "Montería",             "13": "Cartagena",
    "50": "Villavicencio",        "15": "Boyacá/Tunja",
    "18": "Caquetá/Florencia",    "19": "Cauca/Popayán",
    "20": "Cesar/Valledupar",     "27": "Chocó/Quibdó",
    "44": "La Guajira/Riohacha",  "47": "Magdalena/Sta.Marta",
    "63": "Quindío/Armenia",      "70": "Sucre/Sincelejo",
    "25": "Cundinamarca",         "73": "Tolima",
    # ── Amazonía y Orinoquía (v5.1) ────────────────────────────
    "81": "Arauca",               "85": "Casanare/Yopal",
    "86": "Putumayo/Mocoa",       "88": "San Andrés",
    "91": "Amazonas/Leticia",     "94": "Guainía/Inírida",
    "95": "Guaviare/S.J.Guaviare", "97": "Vaupés/Mitú",
    "99": "Vichada/Pto.Carreño",
}

AREA_A_CIUDAD: Dict[str, str] = {
    # ── 13 ciudades principales y sus áreas metropolitanas ──────
    "11001": "Bogotá D.C.",
    "05001": "Medellín A.M.",     "05088": "Medellín A.M.",
    "05308": "Medellín A.M.",     "05318": "Medellín A.M.",
    "05360": "Medellín A.M.",     "05380": "Medellín A.M.",
    "05400": "Medellín A.M.",     "05501": "Medellín A.M.",
    "76001": "Cali A.M.",         "76111": "Cali A.M.",
    "76113": "Cali A.M.",         "76364": "Cali A.M.",
    "76520": "Cali A.M.",         "76563": "Cali A.M.",
    "08001": "Barranquilla A.M.", "08433": "Barranquilla A.M.",
    "08549": "Barranquilla A.M.", "08758": "Barranquilla A.M.",
    "68001": "Bucaramanga A.M.",  "68081": "Bucaramanga A.M.",
    "68276": "Bucaramanga A.M.",  "68307": "Bucaramanga A.M.",
    "68615": "Bucaramanga A.M.",  "68705": "Bucaramanga A.M.",
    "17001": "Manizales A.M.",    "17042": "Manizales A.M.",
    "17616": "Manizales A.M.",
    "66001": "Pereira A.M.",      "66045": "Pereira A.M.",
    "66170": "Pereira A.M.",
    "54001": "Cúcuta A.M.",       "54128": "Cúcuta A.M.",
    "54172": "Cúcuta A.M.",       "54206": "Cúcuta A.M.",
    "54520": "Cúcuta A.M.",
    "52001": "Pasto",             "41001": "Ibagué",
    "23001": "Montería",          "13001": "Cartagena",
    "50001": "Villavicencio",
    # ── 10 ciudades intermedias ─────────────────────────────────
    "15001": "Tunja",             "18001": "Florencia",
    "19001": "Popayán",           "20001": "Valledupar",
    "27001": "Quibdó",            "41551": "Neiva",
    "44001": "Riohacha",          "47001": "Santa Marta",
    "63001": "Armenia",           "70001": "Sincelejo",
    # ── Capitales Amazonía/Orinoquía (v5.1) ────────────────────
    "81001": "Arauca",            "85001": "Yopal",
    "86001": "Mocoa",             "88001": "San Andrés",
    "91001": "Leticia",           "94001": "Inírida",
    "95001": "San José del Guaviare", "97001": "Mitú",
    "99001": "Puerto Carreño",
}

CIUDADES_13_PRINCIPALES: set = {
    "Bogotá D.C.", "Medellín A.M.", "Cali A.M.", "Barranquilla A.M.",
    "Bucaramanga A.M.", "Manizales A.M.", "Pereira A.M.", "Cúcuta A.M.",
    "Pasto", "Ibagué", "Montería", "Cartagena", "Villavicencio",
}
CIUDADES_10_INTERMEDIAS: set = {
    "Tunja", "Florencia", "Popayán", "Valledupar", "Quibdó",
    "Neiva", "Riohacha", "Santa Marta", "Armenia", "Sincelejo",
}


# ═════════════════════════════════════════════════════════════════════
# NIVELES EDUCATIVOS
# ═════════════════════════════════════════════════════════════════════

NIVELES_EDUCATIVOS: Dict[int, str] = {
    1: "Ninguno",             2: "Preescolar",
    3: "Básica primaria",     4: "Básica secundaria",
    5: "Media académica",     6: "Media técnica",
    7: "Normalista",          8: "Técnica profesional",
    9: "Tecnológica",        10: "Universitaria",
    11: "Especialización",   12: "Maestría",
    13: "Doctorado",
}

NIVELES_AGRUPADOS: Dict[int, str] = {
    1: "1. Sin educación",     2: "1. Sin educación",
    3: "2. Primaria",          4: "3. Secundaria",
    5: "4. Media",             6: "4. Media",
    7: "4. Media",             8: "5. Técnica/Tecno.",
    9: "5. Técnica/Tecno.",   10: "6. Universitaria",
    11: "7. Posgrado",        12: "7. Posgrado",
    13: "7. Posgrado",
}

P3042_A_ANOS: Dict[int, int] = {
    1: 0, 2: 0, 3: 5, 4: 9, 5: 11, 6: 11, 7: 11,
    8: 14, 9: 15, 10: 16, 11: 17, 12: 18, 13: 21,
}


# ═════════════════════════════════════════════════════════════════════
# RANGOS DE INGRESO
# ═════════════════════════════════════════════════════════════════════

RANGOS_SMMLV_LIMITES: List[float] = [0, 0.5, 1, 1.5, 2, 3, 4, 6, 10, float("inf")]

RANGOS_SMMLV_ETIQUETAS: List[str] = [
    "< 0.5 SMMLV",    "0.5 – 1 SMMLV",  "1 – 1.5 SMMLV",
    "1.5 – 2 SMMLV",  "2 – 3 SMMLV",    "3 – 4 SMMLV",
    "4 – 6 SMMLV",    "6 – 10 SMMLV",   "> 10 SMMLV",
]


# ═════════════════════════════════════════════════════════════════════
# TAMAÑO DE EMPRESA
# ═════════════════════════════════════════════════════════════════════

TAMANO_EMPRESA: Dict[int, str] = {
    1: "Solo (1)",       2: "2–3 pers.",     3: "4–5 pers.",
    4: "6–10 pers.",     5: "11–19 pers.",   6: "20–30 pers.",
    7: "31–50 pers.",    8: "51–100 pers.",  9: "101–200 pers.",
    10: "201+ pers.",
}


# ═════════════════════════════════════════════════════════════════════
# MAPEO CIIU FALLBACK
# ═════════════════════════════════════════════════════════════════════

CIIU_DESCRIPCION_FALLBACK: List[Tuple[range, str]] = [
    (range(1, 4),   "Agricultura, ganadería, caza, silvicultura y pesca"),
    (range(5, 10),  "Explotación de minas y canteras"),
    (range(10, 34), "Industrias manufactureras"),
    (range(35, 36), "Suministro de electricidad, gas, vapor y aire acondicionado"),
    (range(36, 40), "Distribución de agua; gestión de desechos"),
    (range(41, 44), "Construcción"),
    (range(45, 48), "Comercio al por mayor y al por menor; reparación de vehículos"),
    (range(49, 54), "Transporte y almacenamiento"),
    (range(55, 57), "Alojamiento y servicios de comida"),
    (range(58, 64), "Información y comunicaciones"),
    (range(64, 67), "Actividades financieras y de seguros"),
    (range(68, 69), "Actividades inmobiliarias"),
    (range(69, 76), "Actividades profesionales, científicas y técnicas"),
    (range(77, 83), "Actividades de servicios administrativos y de apoyo"),
    (range(84, 85), "Administración pública y defensa"),
    (range(85, 86), "Educación"),
    (range(86, 89), "Salud y asistencia social"),
    (range(90, 100), "Actividades artísticas, entretenimiento y otras"),
]


# ═════════════════════════════════════════════════════════════════════
# SUBCATEGORÍAS CIIU SECTOR PRIMARIO (v5.1 — Análisis de tierras)
# ═════════════════════════════════════════════════════════════════════

CIIU_SECTOR_PRIMARIO: Dict[str, str] = {
    "01": "Agricultura, ganadería, caza y servicios conexos",
    "02": "Silvicultura y extracción de madera",
    "03": "Pesca y acuicultura",
}
"""Divisiones CIIU Rev.4 del sector primario (CIIU 01-03).
Usado por AnalisisTierraAgropecuario para desagregar por tipo de actividad."""

CIIU_AGRICULTURA_DETALLE: Dict[str, str] = {
    "0111": "Cultivo de cereales y leguminosas",
    "0112": "Cultivo de arroz",
    "0113": "Cultivo de hortalizas, raíces y tubérculos",
    "0114": "Cultivo de tabaco",
    "0115": "Cultivo de plantas textiles",
    "0119": "Otros cultivos transitorios",
    "0121": "Cultivo de frutas tropicales y subtropicales",
    "0122": "Cultivo de plátano y banano",
    "0123": "Cultivo de café",
    "0124": "Cultivo de caña de azúcar",
    "0125": "Cultivo de flor de corte",
    "0126": "Cultivo de palma para aceite",
    "0127": "Cultivo de plantas con las que se preparan bebidas",
    "0128": "Cultivo de especias y aromáticas",
    "0129": "Otros cultivos permanentes",
    "0130": "Propagación de plantas",
    "0141": "Cría de ganado bovino y bufalino",
    "0142": "Cría de caballos y otros equinos",
    "0143": "Cría de ovejas y cabras",
    "0144": "Cría de ganado porcino",
    "0145": "Cría de aves de corral",
    "0149": "Cría de otros animales",
    "0150": "Explotación mixta",
    "0161": "Actividades de apoyo a la agricultura",
    "0162": "Actividades de apoyo a la ganadería",
    "0163": "Actividades posteriores a la cosecha",
    "0170": "Caza ordinaria y con trampas",
}
"""Detalle CIIU Rev.4 a 4 dígitos para agricultura (grupo 01).
Permite análisis granular de 'especificidad de tierras'."""


# ═════════════════════════════════════════════════════════════════════
# REFERENCIA DANE — MULTI-AÑO
# ═════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReferenciaDane:
    """Valores de referencia del boletín DANE para validación cruzada."""
    pea_anual_m: float = 0.0
    ocupados_anual_m: float = 0.0
    desocupados_anual_m: float = 0.0
    td_anual_pct: float = 0.0
    tgp_anual_pct: float = 0.0
    to_anual_pct: float = 0.0
    pea_dic_m: float = 0.0
    ocupados_dic_m: float = 0.0
    desocupados_dic_m: float = 0.0
    td_dic_pct: float = 0.0
    tgp_dic_pct: float = 0.0
    to_dic_pct: float = 0.0


def _construir_ref_dane() -> Dict[int, ReferenciaDane]:
    """Construye el diccionario de referencias, fusionando hardcoded + JSON."""
    # Hardcoded (siempre presente como fallback)
    refs: Dict[int, ReferenciaDane] = {
        2025: ReferenciaDane(
            pea_anual_m=26.3,  ocupados_anual_m=23.8, desocupados_anual_m=2.1,
            td_anual_pct=8.9,  tgp_anual_pct=64.3,   to_anual_pct=58.6,
            pea_dic_m=26.3,    ocupados_dic_m=24.2,   desocupados_dic_m=2.1,
            td_dic_pct=8.0,    tgp_dic_pct=64.3,      to_dic_pct=59.2,
        ),
    }

    # Fusionar con JSON externo
    ext = cargar_config_externa()
    ext_refs = ext.get("ref_dane", {})
    for anio_str, valores in ext_refs.items():
        try:
            anio = int(anio_str)
            refs[anio] = ReferenciaDane(**{
                k: float(v) for k, v in valores.items()
                if k in ReferenciaDane.__dataclass_fields__
            })
        except (ValueError, TypeError):
            continue

    return refs


REF_DANE: Dict[int, ReferenciaDane] = _construir_ref_dane()

# Retrocompatibilidad
REF_DANE_2025 = REF_DANE.get(2025, ReferenciaDane())
