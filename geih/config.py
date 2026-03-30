# -*- coding: utf-8 -*-
"""
geih.config — Configuración centralizada para el análisis GEIH.

Toda constante, mapeo, paleta de colores y parámetro configurable vive aquí.
Nunca hay "números mágicos" sueltos en la lógica de negocio.

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
]


from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


# ═════════════════════════════════════════════════════════════════════
# PARÁMETROS ECONÓMICOS — MULTI-AÑO
# ═════════════════════════════════════════════════════════════════════

SMMLV_POR_ANIO: Dict[int, int] = {
    2022: 1_000_000,
    2023: 1_160_000,
    2024: 1_300_000,
    2025: 1_423_500,
    2026: 1_750_905,   # Decreto 2426 de 2025 — actualizar si cambia
    # Agregar años futuros aquí. Solo se modifica esta línea.
}
"""SMMLV por año en COP. Fuente: Decretos anuales del Gobierno Nacional.
Para agregar un año nuevo, solo agregar una entrada al diccionario."""

# Retrocompatibilidad: módulos que importaban SMMLV_2025 directamente
SMMLV_2025: int = SMMLV_POR_ANIO[2025]

CARGA_PRESTACIONAL: float = 0.54
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
        n_meses: Cuántos meses generar (1-12). Permite procesamiento
                 parcial del año en curso.

    Returns:
        Lista de strings como ['Enero 2025', 'Febrero 2025', ...].

    Ejemplo:
        >>> generar_carpetas_mensuales(2026, n_meses=3)
        ['Enero 2026', 'Febrero 2026', 'Marzo 2026']
    """
    n = max(1, min(n_meses, 12))
    return [f"{mes} {anio}" for mes in MESES_NOMBRES[:n]]


def generar_etiqueta_periodo(anio: int, n_meses: int = 12) -> str:
    """Genera la etiqueta legible del período para títulos y reportes.

    Ejemplos:
        (2025, 12) → 'Enero – Diciembre 2025'
        (2026, 3)  → 'Enero – Marzo 2026'
        (2026, 1)  → 'Enero 2026'
    """
    n = max(1, min(n_meses, 12))
    if n == 1:
        return f"{MESES_NOMBRES[0]} {anio}"
    return f"{MESES_NOMBRES[0]} – {MESES_NOMBRES[n - 1]} {anio}"


# Retrocompatibilidad: código que importaba MESES_CARPETAS como constante
MESES_CARPETAS: List[str] = generar_carpetas_mensuales(2025, 12)


# ═════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL ANÁLISIS — MULTI-AÑO
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ConfigGEIH:
    """Parámetros configurables para el pipeline GEIH.

    Centraliza todo lo que un usuario necesita ajustar.
    Valida en __post_init__ para fallar rápido si algo está mal.

    CAMBIO v4.0: ahora recibe `anio` y auto-deriva SMMLV, carpetas
    mensuales y etiqueta de período. El usuario solo necesita cambiar
    `anio` y `n_meses` para procesar cualquier año.

    Uso típico:
        # Año 2025 completo (12 meses)
        config = ConfigGEIH(anio=2025, n_meses=12)

        # Primeros 3 meses de 2026
        config = ConfigGEIH(anio=2026, n_meses=3)

        # Mes puntual: marzo 2026
        config = ConfigGEIH(anio=2026, n_meses=1)
    """
    anio: int = 2025
    """Año de los datos a procesar."""

    n_meses: int = 12
    """Número de meses consolidados. Controla la división del FEX_C18."""

    smmlv: int = 0
    """SMMLV del año de análisis en COP. Si 0 (default), se auto-selecciona
    de SMMLV_POR_ANIO según el año. Solo asignar manualmente si el año
    aún no está en el diccionario."""

    periodo_etiqueta: str = ""
    """Etiqueta legible para títulos y reportes. Si vacía, se genera
    automáticamente como 'Enero – Diciembre 2025'."""

    random_seed: int = 42
    """Semilla para reproducibilidad (muestreo, ML)."""

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
        # ── Validación básica ──────────────────────────────────────
        if self.n_meses < 1 or self.n_meses > 12:
            raise ValueError(f"n_meses={self.n_meses} fuera de rango [1, 12]")
        if self.anio < 2018 or self.anio > 2050:
            raise ValueError(
                f"anio={self.anio} fuera de rango [2018, 2050]. "
                f"La GEIH Marco 2018 inicia en 2022."
            )

        # ── Auto-seleccionar SMMLV según el año ────────────────────
        if self.smmlv == 0:
            if self.anio in SMMLV_POR_ANIO:
                self.smmlv = SMMLV_POR_ANIO[self.anio]
            else:
                # Año no registrado → usar el último conocido + advertencia
                ultimo_anio = max(SMMLV_POR_ANIO.keys())
                self.smmlv = SMMLV_POR_ANIO[ultimo_anio]
                print(
                    f"⚠️  SMMLV para {self.anio} no está registrado en "
                    f"SMMLV_POR_ANIO. Usando el de {ultimo_anio}: "
                    f"${self.smmlv:,}. Actualice config.py cuando se "
                    f"publique el decreto."
                )

        if self.smmlv < 100_000:
            raise ValueError(f"smmlv={self.smmlv} parece demasiado bajo")

        # ── Auto-generar etiqueta de período ───────────────────────
        if not self.periodo_etiqueta:
            self.periodo_etiqueta = generar_etiqueta_periodo(
                self.anio, self.n_meses
            )

    # ── Propiedades calculadas ──────────────────────────────────
    @property
    def carpetas_mensuales(self) -> List[str]:
        """Lista de carpetas mensuales DANE para este año y n_meses.

        Reemplaza la constante MESES_CARPETAS. Las clases que antes
        usaban MESES_CARPETAS ahora usan config.carpetas_mensuales.
        """
        return generar_carpetas_mensuales(self.anio, self.n_meses)

    @property
    def referencia_dane(self) -> Optional["ReferenciaDane"]:
        """Referencia DANE para validación, o None si no está disponible.

        Devuelve None para años sin referencia publicada (ej: 2026 parcial).
        El sanity_check() maneja None gracefully: advierte en vez de fallar.
        """
        return REF_DANE.get(self.anio)

    def resumen(self) -> None:
        """Imprime un resumen legible de la configuración activa."""
        ref = self.referencia_dane
        ref_status = "✅ Disponible" if ref else "⚠️  No disponible"
        print(f"\n{'='*55}")
        print(f"  CONFIGURACIÓN GEIH — {self.periodo_etiqueta}")
        print(f"{'='*55}")
        print(f"  Año           : {self.anio}")
        print(f"  Meses         : {self.n_meses}")
        print(f"  SMMLV         : ${self.smmlv:,} COP")
        print(f"  FEX divisor   : ÷ {self.n_meses}")
        print(f"  Ref. DANE     : {ref_status}")
        print(f"  Carpetas      : {self.carpetas_mensuales[0]} → "
              f"{self.carpetas_mensuales[-1]}")
        print(f"{'='*55}")


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
# COLUMNAS QUE DEBEN LEERSE COMO STRING (NO NUMÉRICAS)
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

# Catálogo de variables clave por módulo (para referencia y selección)
VARIABLES_POR_MODULO: Dict[str, List[str]] = {
    "caracteristicas": [
        "P3271",      # Sexo (1=H, 2=M)
        "P6040",      # Edad
        "P6080",      # Autorreconocimiento étnico (1=Indígena, 5=Afro, 6=Ninguno)
        "P3042",      # Nivel educativo (1-13)
        "P3043S1",    # Campo de formación (CINE-F)
        "P6090",      # Afiliado salud (1=Sí)
        "P2057",      # ¿Se considera campesino? (1=Sí)
        "P2059",      # ¿Alguna vez fue campesino?
        "P1906S1",    # Discapacidad: Oír
        "P1906S2",    # Discapacidad: Hablar
        "P1906S3",    # Discapacidad: Ver
        "P1906S4",    # Discapacidad: Moverse
        "P1906S5",    # Discapacidad: Agarrar
        "P1906S6",    # Discapacidad: Entender
        "P1906S7",    # Discapacidad: Autocuidado
        "P1906S8",    # Discapacidad: Relacionarse
        "CLASE",      # Zona (1=Urbano/Cabecera, 2=Rural)
        "FEX_C18",    # Factor de expansión
    ],
    "ocupados": [
        "OCI",        # Ocupado (=1)
        "INGLABO",    # Ingreso laboral mensual COP
        "P6500",      # Salario bruto declarado
        "P6430",      # Posición ocupacional (1-9)
        "P6800",      # Horas normales semana
        "P6850",      # Horas reales semana pasada
        "P6920",      # Cotiza pensión (1=Sí, 2=No, 3=Pensionado)
        "P3069",      # Tamaño empresa (1-10 categorías)
        "P7130",      # Desea cambiar trabajo (1=Sí)
        "P6440",      # ¿Tiene contrato?
        "P6450",      # ¿Contrato escrito?
        "P6460",      # ¿Contrato indefinido?
        "P1802",      # Alcance mercado (1-6, 6=Exportación)
        "P3047",      # ¿Quién decide horario?
        "P3048",      # ¿Quién decide qué producir?
        "P3049",      # ¿Quién decide precio?
        "P3363",      # ¿Cómo consiguió empleo?
        "P3364",      # ¿Le descontaron retención en la fuente?
        "P6765",      # Forma de trabajo (destajo, honorarios, etc.)
        "P6400",      # ¿Trabaja donde lo contrataron?
        "P6410",      # Tipo intermediación (EST, CTA)
        "P6510S1",    # Horas extras
        "P6580S1",    # Bonificaciones
        "P6585S1A1",  # Auxilio alimentación
        "P6585S2A1",  # Auxilio transporte
        "RAMA2D_R4",  # CIIU 2 dígitos
        "RAMA4D_R4",  # CIIU 4 dígitos
        "AREA",       # Municipio (5 dígitos)
    ],
    "no_ocupados": [
        "DSI",        # Desocupado (=1)
        "P7250",      # Semanas buscando trabajo
        "P6300",      # ¿Desearía trabajar? (FFT con deseo)
        "P6310",      # ¿Disponible para trabajar?
        "FFT",        # Fuera de la fuerza de trabajo (=1)
    ],
    "fuerza_trabajo": [
        "FT",         # En la fuerza de trabajo (=1)
        "PET",        # Población en edad de trabajar (=1)
        "P6240",      # Actividad semana pasada
        "P6280",      # ¿Disponible para trabajar?
    ],
    "otras_formas": [
        "P3054",      # Producción bienes autoconsumo
        "P3054S1",    # Horas autoconsumo
        "P3055",      # Producción servicios autoconsumo
        "P3055S1",    # Horas servicios autoconsumo
        "P3056",      # Trabajo voluntario
        "P3057",      # Trabajo en formación
    ],
    "migracion": [
        "P3370",      # ¿Dónde vivía hace 12 meses?
        "P3370S1",    # Departamento hace 12 meses
        "P3371",      # ¿Dónde vivía hace 5 años?
        "P3376",      # País de nacimiento
        "P3378S1",    # Año de llegada a Colombia
    ],
    "otros_ingresos": [
        "P7422",      # Arriendos recibidos
        "P7500S1",    # Pensión jubilación
        "P7500S2",    # Ayudas de otros hogares
        "P7500S3",    # Ayudas institucionales
        "P7510S1",    # Intereses/dividendos
        "P7510S2",    # Remesas del exterior
        "P7510S3",    # Cesantías
    ],
}


# ═════════════════════════════════════════════════════════════════════
# MAPEO CIIU Rev.4 → 13 RAMAS DANE (AGRUPACIÓN ESTÁNDAR)
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

# Tabla de rangos: (CIIU_min, CIIU_max, clave_rama)
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
# AGRUPACIÓN DANE DE 8 GRUPOS (PARA TABLAS POR ÁREA)
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

# Mapeo directo: código CIIU 2 dígitos (string) → nombre de agrupación DANE
# Usado por AnalisisOcupadosCiudad para tablas y Excel
_AGRUP_DANE_POR_DIVISION: Dict[str, str] = {}
for _nombre, _rangos in AGRUPACION_DANE_8.items():
    for _lo, _hi in _rangos:
        for _i in range(_lo, _hi + 1):
            _AGRUP_DANE_POR_DIVISION[str(_i).zfill(2)] = _nombre


# ═════════════════════════════════════════════════════════════════════
# DEPARTAMENTOS DE COLOMBIA (CÓDIGO DIVIPOLA → NOMBRE)
# ═════════════════════════════════════════════════════════════════════

DEPARTAMENTOS: Dict[str, str] = {
    "05": "Antioquia",       "08": "Atlántico",
    "11": "Bogotá D.C.",     "13": "Bolívar",
    "15": "Boyacá",          "17": "Caldas",
    "18": "Caquetá",         "19": "Cauca",
    "20": "Cesar",           "23": "Córdoba",
    "25": "Cundinamarca",    "27": "Chocó",
    "41": "Huila",           "44": "La Guajira",
    "47": "Magdalena",       "50": "Meta",
    "52": "Nariño",          "54": "Norte de Santander",
    "63": "Quindío",         "66": "Risaralda",
    "68": "Santander",       "70": "Sucre",
    "73": "Tolima",          "76": "Valle del Cauca",
}


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
}

AREA_A_CIUDAD: Dict[str, str] = {
    # ── 13 ciudades principales y sus áreas metropolitanas ──────
    "11001": "Bogotá D.C.",
    # Medellín AM (8 municipios)
    "05001": "Medellín A.M.",     "05088": "Medellín A.M.",
    "05308": "Medellín A.M.",     "05318": "Medellín A.M.",
    "05360": "Medellín A.M.",     "05380": "Medellín A.M.",
    "05400": "Medellín A.M.",     "05501": "Medellín A.M.",
    # Cali AM (6 municipios)
    "76001": "Cali A.M.",         "76111": "Cali A.M.",
    "76113": "Cali A.M.",         "76364": "Cali A.M.",
    "76520": "Cali A.M.",         "76563": "Cali A.M.",
    # Barranquilla AM (4 municipios)
    "08001": "Barranquilla A.M.", "08433": "Barranquilla A.M.",
    "08549": "Barranquilla A.M.", "08758": "Barranquilla A.M.",
    # Bucaramanga AM (6 municipios)
    "68001": "Bucaramanga A.M.",  "68081": "Bucaramanga A.M.",
    "68276": "Bucaramanga A.M.",  "68307": "Bucaramanga A.M.",
    "68615": "Bucaramanga A.M.",  "68705": "Bucaramanga A.M.",
    # Manizales AM (3 municipios)
    "17001": "Manizales A.M.",    "17042": "Manizales A.M.",
    "17616": "Manizales A.M.",
    # Pereira AM (3 municipios)
    "66001": "Pereira A.M.",      "66045": "Pereira A.M.",
    "66170": "Pereira A.M.",
    # Cúcuta AM (5 municipios)
    "54001": "Cúcuta A.M.",       "54128": "Cúcuta A.M.",
    "54172": "Cúcuta A.M.",       "54206": "Cúcuta A.M.",
    "54520": "Cúcuta A.M.",
    # Ciudades sin AM
    "52001": "Pasto",             "41001": "Ibagué",
    "23001": "Montería",          "13001": "Cartagena",
    "50001": "Villavicencio",
    # ── 10 ciudades intermedias ─────────────────────────────────
    "15001": "Tunja",             "18001": "Florencia",
    "19001": "Popayán",           "20001": "Valledupar",
    "27001": "Quibdó",            "41551": "Neiva",
    "44001": "Riohacha",          "47001": "Santa Marta",
    "63001": "Armenia",           "70001": "Sincelejo",
}

# Clasificación DANE: dominios geográficos para reportes
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
# NIVELES EDUCATIVOS (P3042 → ETIQUETA)
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

# Conversión P3042 → Años de educación acumulados (para Mincer)
P3042_A_ANOS: Dict[int, int] = {
    1: 0, 2: 0, 3: 5, 4: 9, 5: 11, 6: 11, 7: 11,
    8: 14, 9: 15, 10: 16, 11: 17, 12: 18, 13: 21,
}


# ═════════════════════════════════════════════════════════════════════
# RANGOS DE INGRESO EN MÚLTIPLOS DE SMMLV
# ═════════════════════════════════════════════════════════════════════

RANGOS_SMMLV_LIMITES: List[float] = [0, 0.5, 1, 1.5, 2, 3, 4, 6, 10, float("inf")]

RANGOS_SMMLV_ETIQUETAS: List[str] = [
    "< 0.5 SMMLV",    "0.5 – 1 SMMLV",  "1 – 1.5 SMMLV",
    "1.5 – 2 SMMLV",  "2 – 3 SMMLV",    "3 – 4 SMMLV",
    "4 – 6 SMMLV",    "6 – 10 SMMLV",   "> 10 SMMLV",
]


# ═════════════════════════════════════════════════════════════════════
# ETIQUETAS DE TAMAÑO DE EMPRESA (P3069)
# ═════════════════════════════════════════════════════════════════════

TAMANO_EMPRESA: Dict[int, str] = {
    1: "Solo (1)",       2: "2–3 pers.",     3: "4–5 pers.",
    4: "6–10 pers.",     5: "11–19 pers.",   6: "20–30 pers.",
    7: "31–50 pers.",    8: "51–100 pers.",  9: "101–200 pers.",
    10: "201+ pers.",
}


# ═════════════════════════════════════════════════════════════════════
# MAPEO CIIU INTERNO (FALLBACK PARA MERGE INCOMPLETO)
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
# REFERENCIA DANE — MULTI-AÑO (PARA VALIDACIÓN SANITY CHECK)
# ═════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReferenciaDane:
    """Valores de referencia del boletín DANE para validación cruzada.

    Cada año tiene sus propios valores publicados por el DANE.
    Para años sin datos publicados, no se crea una entrada en REF_DANE
    y el sanity_check advierte 'sin referencia disponible'.
    """
    pea_anual_m: float = 0.0        # Millones
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


REF_DANE: Dict[int, ReferenciaDane] = {
    2025: ReferenciaDane(
        pea_anual_m=26.3,  ocupados_anual_m=23.8, desocupados_anual_m=2.1,
        td_anual_pct=8.9,  tgp_anual_pct=64.3,   to_anual_pct=58.6,
        pea_dic_m=26.3,    ocupados_dic_m=24.2,   desocupados_dic_m=2.1,
        td_dic_pct=8.0,    tgp_dic_pct=64.3,      to_dic_pct=59.2,
    ),
    # Agregar 2026 cuando el DANE publique el boletín anual:
    # 2026: ReferenciaDane(
    #     pea_anual_m=..., ocupados_anual_m=..., desocupados_anual_m=...,
    #     td_anual_pct=..., tgp_anual_pct=..., to_anual_pct=...,
    # ),
}

# Retrocompatibilidad: código que importaba REF_DANE_2025 directamente
REF_DANE_2025 = REF_DANE[2025]
