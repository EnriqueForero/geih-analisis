"""
geih.logger — Sistema centralizado de logging con trazabilidad.

Reemplaza los print() dispersos por logging estructurado que:
  - Escribe a consola (para visibilidad inmediata en Colab)
  - Escribe a archivo (para trazabilidad post-ejecución)
  - Registra timestamp, módulo, nivel y mensaje
  - Permite filtrar por nivel (DEBUG, INFO, WARNING, ERROR)

Migración gradual: los módulos existentes pueden seguir usando print()
y migrar a logging progresivamente. Este módulo provee get_logger()
para obtener un logger del paquete ya configurado.

Uso desde cualquier módulo del paquete:
    from .logger import get_logger
    log = get_logger(__name__)
    log.info("Procesando mes %d...", i)
    log.warning("Columna %s no encontrada", col)
    log.error("Error en consolidación: %s", e)

Configuración desde el notebook:
    from geih.logger import configurar_logging
    configurar_logging(nivel='DEBUG', archivo='geih_pipeline.log')

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "LoggerGEIH",
    "configurar_logging",
    "get_logger",
]

import logging
import sys
from pathlib import Path
from typing import Optional

# Nombre raíz del logger del paquete
_LOGGER_NAME = "geih"

# Formato para consola (compacto, con emojis para niveles)
_FORMATO_CONSOLA = "%(message)s"

# Formato para archivo (completo, con timestamp y módulo)
_FORMATO_ARCHIVO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Formato de fecha
_FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

# Flag para evitar configuración múltiple
_configurado = False


def get_logger(nombre: str = _LOGGER_NAME) -> logging.Logger:
    """Obtiene un logger del paquete ya configurado.

    Si el logging no ha sido configurado explícitamente, se configura
    con defaults (INFO a consola, sin archivo).

    Args:
        nombre: Nombre del logger. Usar __name__ desde cada módulo
                para trazabilidad (ej: 'geih.consolidador').

    Returns:
        Logger configurado listo para usar.

    Uso:
        log = get_logger(__name__)
        log.info("Mensaje informativo")
        log.warning("⚠️  Advertencia")
        log.error("❌ Error")
        log.debug("Detalle para depuración")
    """
    global _configurado
    if not _configurado:
        configurar_logging()  # defaults
    return logging.getLogger(nombre)


def configurar_logging(
    nivel: str = "INFO",
    archivo: Optional[str] = None,
    nivel_archivo: str = "DEBUG",
    formato_consola: Optional[str] = None,
    formato_archivo: Optional[str] = None,
) -> logging.Logger:
    """Configura el sistema de logging del paquete.

    Llamar UNA VEZ al inicio del notebook o script.
    Las llamadas posteriores se ignoran (idempotente).

    Args:
        nivel: Nivel mínimo para consola ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        archivo: Ruta del archivo de log. Si None, solo consola.
        nivel_archivo: Nivel mínimo para el archivo (default: DEBUG = todo).
        formato_consola: Formato custom para consola.
        formato_archivo: Formato custom para archivo.

    Returns:
        Logger raíz del paquete.

    Ejemplo en notebook:
        from geih.logger import configurar_logging
        configurar_logging(
            nivel='INFO',                    # consola: solo INFO+
            archivo='geih_pipeline.log',     # archivo: todo desde DEBUG
        )
    """
    global _configurado

    logger = logging.getLogger(_LOGGER_NAME)

    # Evitar handlers duplicados si se llama más de una vez
    if _configurado:
        return logger

    logger.setLevel(logging.DEBUG)  # capturar todo; los handlers filtran

    # ── Handler de consola ─────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, nivel.upper(), logging.INFO))
    console_handler.setFormatter(
        logging.Formatter(
            formato_consola or _FORMATO_CONSOLA,
            datefmt=_FORMATO_FECHA,
        )
    )
    logger.addHandler(console_handler)

    # ── Handler de archivo (opcional) ──────────────────────────
    if archivo:
        ruta = Path(archivo)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            ruta,
            mode="a",
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, nivel_archivo.upper(), logging.DEBUG))
        file_handler.setFormatter(
            logging.Formatter(
                formato_archivo or _FORMATO_ARCHIVO,
                datefmt=_FORMATO_FECHA,
            )
        )
        logger.addHandler(file_handler)
        logger.info(f"📝 Log → {ruta.resolve()}")

    # No propagar al logger root de Python
    logger.propagate = False
    _configurado = True

    return logger


class LoggerGEIH:
    """Wrapper de conveniencia para módulos que quieran migrar de print() a log.

    Provee métodos que imitan la interfaz de print() pero usan logging.
    Permite migración gradual: reemplazar `print(msg)` por `self.log.info(msg)`.

    Uso como mixin en clases existentes:
        class MiClase(LoggerGEIH):
            def __init__(self):
                super().__init__()   # configura self.log

            def procesar(self):
                self.log.info("Procesando...")
                self.log.warning("⚠️  Algo raro")

    O como atributo:
        class MiClase:
            def __init__(self):
                self._logger = LoggerGEIH(nombre='geih.mi_clase')

            def procesar(self):
                self._logger.info("Procesando...")
    """

    def __init__(self, nombre: Optional[str] = None):
        self.log = get_logger(nombre or self.__class__.__qualname__)

    def info(self, msg: str, *args) -> None:
        self.log.info(msg, *args)

    def warning(self, msg: str, *args) -> None:
        self.log.warning(msg, *args)

    def error(self, msg: str, *args) -> None:
        self.log.error(msg, *args)

    def debug(self, msg: str, *args) -> None:
        self.log.debug(msg, *args)


def resetear_logging() -> None:
    """Resetea la configuración de logging (útil para tests).

    Elimina todos los handlers del logger del paquete y permite
    reconfigurar desde cero.
    """
    global _configurado
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    _configurado = False


# ════════════════════════════════════════════════════════════════════════════
# 📄 geih/muestreo.py
#    Categoría: codigo
