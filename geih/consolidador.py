# -*- coding: utf-8 -*-
"""
geih.consolidador — Consolidación de microdatos GEIH mensuales.

Lee los módulos CSV de cada mes, los une por las llaves DIRECTORIO +
SECUENCIA_P + ORDEN y concatena los 12 meses en una base única.

Decisiones críticas:
  - El módulo ancla siempre es "Características generales" (universo completo).
  - El join es LEFT para no multiplicar filas.
  - Las columnas duplicadas entre módulos se eliminan antes del merge.
  - MES_NUM se agrega como variable creada (no existe en DANE).

CAMBIO v4.0 — Escalabilidad multi-año:
  - consolidar() ahora usa config.carpetas_mensuales en vez de MESES_CARPETAS.
  - agregar_mes() permite añadir un mes nuevo a un Parquet existente
    sin re-consolidar todo (procesamiento incremental mes a mes).

Autor: Néstor Enrique Forero Herrera
"""

__all__ = [
    "ConsolidadorGEIH",
]


import gc
import os
import unicodedata
from pathlib import Path
from typing import List, Optional, Dict

import pandas as pd

from .config import (
    ConfigGEIH,
    MESES_CARPETAS,
    MESES_NOMBRES,
    MODULOS_CSV,
    CONVERTERS_BASE,
    CONVERTERS_CON_AREA,
    LLAVES_PERSONA,
    LLAVES_HOGAR,
)


class ConsolidadorGEIH:
    """Consolida los microdatos GEIH mensuales en una base única.

    El proceso es:
      1. Para cada mes, leer los módulos CSV necesarios
      2. Unir módulos usando LEFT JOIN (ancla: Características generales)
      3. Agregar MES_NUM para identificar el mes
      4. Concatenar todos los meses
      5. Exportar a Parquet (eficiente en espacio y velocidad)

    CAMBIO v4.0: Las carpetas mensuales se toman de config.carpetas_mensuales,
    que se genera dinámicamente según config.anio y config.n_meses.

    Uso típico desde el notebook:
        # Año 2025 completo
        config = ConfigGEIH(anio=2025, n_meses=12)
        consolidador = ConsolidadorGEIH(
            ruta_base='/content/drive/MyDrive/GEIH',
            config=config,
        )
        geih = consolidador.consolidar()
        consolidador.exportar(geih, f'GEIH_{config.anio}_Consolidado.parquet')

        # Agregar enero 2026 sin re-consolidar
        config_2026 = ConfigGEIH(anio=2026, n_meses=1)
        consolidador_2026 = ConsolidadorGEIH(
            ruta_base='/content/drive/MyDrive/GEIH',
            config=config_2026,
        )
        consolidador_2026.agregar_mes(
            mes_carpeta='Enero 2026',
            parquet_existente='GEIH_2026_Consolidado.parquet',
        )
    """

    def __init__(
        self,
        ruta_base: str,
        config: Optional[ConfigGEIH] = None,
        incluir_area: bool = False,
        modulos_extra: Optional[List[str]] = None,
    ):
        """
        Args:
            ruta_base: Ruta a la carpeta que contiene las subcarpetas mensuales.
            config: Configuración del análisis. Usa defaults si no se provee.
            incluir_area: Si True, incluye 'AREA' en los converters para
                          habilitar análisis por 32 ciudades.
            modulos_extra: Módulos adicionales a incluir (ej: 'otras_formas',
                          'micronegocios'). Por defecto solo se consolidan
                          los 5 módulos principales.
        """
        self.ruta_base = Path(ruta_base)
        self.config = config or ConfigGEIH()
        self.converters = CONVERTERS_CON_AREA if incluir_area else CONVERTERS_BASE
        self._modulos_a_incluir = [
            "caracteristicas", "hogar", "fuerza_trabajo",
            "ocupados", "no_ocupados",
            "otras_formas", "migracion", "otros_ingresos",
        ]
        if modulos_extra:
            self._modulos_a_incluir.extend(modulos_extra)

    # ── Búsqueda de archivos resiliente a tildes ────────────────

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Elimina tildes y convierte a minúsculas para comparación.

        'Migración.CSV' → 'migracion.csv'
        'Características generales...' → 'caracteristicas generales...'

        Usa descomposición Unicode NFD: separa la letra base del acento,
        luego elimina los acentos (categoría Mn = Mark, Nonspacing).
        """
        nfkd = unicodedata.normalize("NFD", texto)
        sin_tildes = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
        return sin_tildes.lower()

    @classmethod
    def _buscar_archivo(cls, carpeta: Path, nombre_esperado: str) -> Optional[Path]:
        """Busca un archivo en disco comparando sin tildes ni mayúsculas.

        El DANE a veces publica 'Migración.CSV' y a veces 'Migracion.CSV'.
        Esta función encuentra el archivo sin importar las tildes.

        Args:
            carpeta: Directorio donde buscar.
            nombre_esperado: Nombre de archivo que esperamos (puede tener tildes o no).

        Returns:
            Path al archivo real encontrado, o None si no existe.
        """
        # Intento directo primero (rápido si el nombre es exacto)
        ruta_directa = carpeta / nombre_esperado
        if ruta_directa.exists():
            return ruta_directa

        # Búsqueda normalizada: comparar sin tildes
        nombre_norm = cls._normalizar(nombre_esperado)
        try:
            for archivo in carpeta.iterdir():
                if cls._normalizar(archivo.name) == nombre_norm:
                    return archivo
        except (PermissionError, OSError):
            pass

        return None

    # ── Métodos públicos ───────────────────────────────────────────

    def verificar_estructura(
        self,
        carpetas: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        """Verifica que existan las carpetas y archivos esperados.

        Pre-flight check: detecta problemas ANTES de iniciar la lectura.
        Busca archivos de forma resiliente a tildes (Migración = Migracion).

        CAMBIO v4.0: Si no se pasan carpetas, usa config.carpetas_mensuales
        (dinámicas según año y n_meses).

        Returns:
            Dict con 'ok' (meses completos) y 'faltantes' (archivos no encontrados).
        """
        carpetas = carpetas or self.config.carpetas_mensuales
        resultado = {"ok": [], "faltantes": []}

        for mes in carpetas:
            ruta_mes = self.ruta_base / mes / "CSV"
            if not ruta_mes.exists():
                resultado["faltantes"].append(f"{mes}/CSV/ (carpeta no existe)")
                continue

            archivos_faltantes = []
            for mod_key in self._modulos_a_incluir:
                nombre_csv = MODULOS_CSV.get(mod_key, "")
                encontrado = self._buscar_archivo(ruta_mes, nombre_csv)
                if encontrado is None:
                    archivos_faltantes.append(nombre_csv)

            if archivos_faltantes:
                for arch in archivos_faltantes:
                    resultado["faltantes"].append(f"{mes}/CSV/{arch}")
            else:
                resultado["ok"].append(mes)

        # Reporte
        print(f"\n{'='*60}")
        print(f"  PRE-FLIGHT CHECK — Estructura de archivos GEIH {self.config.anio}")
        print(f"{'='*60}")
        print(f"  ✅ Meses completos : {len(resultado['ok'])}")
        if resultado["faltantes"]:
            print(f"  ❌ Archivos faltantes: {len(resultado['faltantes'])}")
            for f in resultado["faltantes"][:10]:
                print(f"     • {f}")
        else:
            print(f"  ✅ Todos los archivos presentes")

        return resultado

    def consolidar(
        self,
        carpetas: Optional[List[str]] = None,
        checkpoint: bool = True,
        ruta_checkpoints: Optional[str] = None,
    ) -> pd.DataFrame:
        """Consolida todos los meses en una base única.

        Este es el método principal. Lee los CSV, une los módulos
        y concatena. Reporta progreso visible al usuario.

        CAMBIO v4.2 — Checkpointing:
          Si checkpoint=True, guarda un Parquet después de cada mes.
          Si el proceso falla a mitad de camino (timeout, OOM, crash),
          al re-ejecutar detecta qué meses ya fueron procesados y
          los omite, reanudando desde donde quedó.

        Args:
            carpetas: Lista de carpetas mensuales a procesar.
                      Usa config.carpetas_mensuales por defecto.
            checkpoint: Si True, guarda progreso mes a mes.
            ruta_checkpoints: Carpeta para checkpoints. Si None, usa
                             ruta_base/_checkpoints_{anio}/

        Returns:
            DataFrame consolidado con ~5M filas y columna MES_NUM.

        Raises:
            FileNotFoundError: Si no se encuentra ningún archivo.
        """
        carpetas = carpetas or self.config.carpetas_mensuales
        bases_mensuales: List[pd.DataFrame] = []

        # ── Configurar checkpoints ─────────────────────────────────
        if checkpoint:
            ckpt_dir = Path(ruta_checkpoints) if ruta_checkpoints else (
                self.ruta_base / f"_checkpoints_{self.config.anio}"
            )
            ckpt_dir.mkdir(parents=True, exist_ok=True)
        else:
            ckpt_dir = None

        print(f"\n{'='*60}")
        print(f"  CONSOLIDACIÓN GEIH {self.config.anio} — {len(carpetas)} meses")
        if checkpoint:
            print(f"  Checkpointing: ON → {ckpt_dir}")
        print(f"{'='*60}")

        for i, mes in enumerate(carpetas, 1):
            # ── Verificar si ya existe checkpoint ──────────────────
            if ckpt_dir:
                ckpt_file = ckpt_dir / f"mes_{i:02d}.parquet"
                if ckpt_file.exists():
                    print(f"\n♻️  [{i}/{len(carpetas)}] {mes} — "
                          f"recuperado de checkpoint")
                    df_mes = pd.read_parquet(ckpt_file)
                    bases_mensuales.append(df_mes)
                    print(f"   ✅ {mes}: {df_mes.shape[0]:,} filas (checkpoint)")
                    continue

            print(f"\n🔄 [{i}/{len(carpetas)}] Procesando {mes}...")

            try:
                df_mes = self._procesar_mes(mes, numero_mes=i)
                bases_mensuales.append(df_mes)
                print(f"   ✅ {mes}: {df_mes.shape[0]:,} filas × {df_mes.shape[1]} cols")

                # ── Guardar checkpoint ─────────────────────────────
                if ckpt_dir:
                    df_mes.to_parquet(ckpt_file, index=False, compression="snappy")
                    print(f"   💾 Checkpoint guardado: {ckpt_file.name}")

            except FileNotFoundError as e:
                print(f"   ⚠️ Archivos faltantes en {mes}: {e}")
            except Exception as e:
                print(f"   ❌ Error en {mes}: {e}")
                if ckpt_dir and bases_mensuales:
                    print(f"   💾 {len(bases_mensuales)} meses en checkpoint — "
                          f"re-ejecute para continuar.")

        if not bases_mensuales:
            raise FileNotFoundError(
                "❌ No se procesó ningún mes. Verifica las carpetas con "
                "verificar_estructura()."
            )

        print(f"\n🔗 Concatenando {len(bases_mensuales)} meses...")
        geih = pd.concat(bases_mensuales, ignore_index=True)

        # Limpieza de intermedios
        del bases_mensuales
        gc.collect()

        # ── Limpiar checkpoints si todo salió bien ─────────────────
        if ckpt_dir and len(carpetas) == geih["MES_NUM"].nunique():
            self._limpiar_checkpoints(ckpt_dir)

        print(f"\n{'='*60}")
        print(f"  ✅ CONSOLIDACIÓN COMPLETA — {self.config.anio}")
        print(f"  {geih.shape[0]:,} filas × {geih.shape[1]} columnas")
        print(f"  Meses: {geih['MES_NUM'].nunique()} (de {geih['MES_NUM'].min()} a {geih['MES_NUM'].max()})")
        print(f"{'='*60}")

        return geih

    @staticmethod
    def _limpiar_checkpoints(ckpt_dir: Path) -> None:
        """Elimina la carpeta de checkpoints después de consolidación exitosa."""
        try:
            import shutil
            shutil.rmtree(ckpt_dir)
            print(f"   🗑️  Checkpoints eliminados (consolidación exitosa)")
        except Exception:
            pass  # No crítico si falla la limpieza

    def agregar_mes(
        self,
        mes_carpeta: str,
        parquet_existente: str,
        numero_mes: Optional[int] = None,
    ) -> pd.DataFrame:
        """Agrega un mes nuevo a un Parquet existente SIN re-consolidar todo.

        Caso de uso: cada mes, el DANE publica datos nuevos. En vez de
        re-consolidar los 12 meses (~10 min), solo lee el mes nuevo y
        lo concatena al Parquet existente (~1 min).

        Args:
            mes_carpeta: Nombre de la carpeta del mes nuevo (ej: 'Abril 2026').
            parquet_existente: Nombre del archivo Parquet al que agregar.
                              Se busca en self.ruta_base.
            numero_mes: Número del mes (1-12). Si None, se infiere del
                        nombre de la carpeta.

        Returns:
            DataFrame con la base actualizada (existente + mes nuevo).

        Ejemplo desde el notebook:
            consolidador = ConsolidadorGEIH(
                ruta_base=RUTA,
                config=ConfigGEIH(anio=2026, n_meses=4),
                incluir_area=True,
            )
            geih = consolidador.agregar_mes(
                mes_carpeta='Abril 2026',
                parquet_existente='GEIH_2026_Consolidado.parquet',
            )
            consolidador.exportar(geih, 'GEIH_2026_Consolidado.parquet')
        """
        ruta_parquet = self.ruta_base / parquet_existente

        # ── Cargar base existente ──────────────────────────────────
        if ruta_parquet.exists():
            print(f"📂 Cargando base existente: {parquet_existente}")
            df_existente = pd.read_parquet(ruta_parquet)
            meses_existentes = sorted(df_existente["MES_NUM"].unique().tolist())
            print(f"   Meses existentes: {meses_existentes} "
                  f"({df_existente.shape[0]:,} filas)")
        else:
            print(f"📂 No existe {parquet_existente} — se creará desde cero.")
            df_existente = None
            meses_existentes = []

        # ── Inferir número de mes ──────────────────────────────────
        if numero_mes is None:
            numero_mes = self._inferir_numero_mes(mes_carpeta)

        if numero_mes in meses_existentes:
            print(f"⚠️  El mes {numero_mes} ({mes_carpeta}) ya existe en la base.")
            print(f"   Para reemplazarlo, elimine ese mes primero o "
                  f"re-consolide desde cero.")
            return df_existente

        # ── Procesar mes nuevo ─────────────────────────────────────
        print(f"\n🔄 Procesando {mes_carpeta} (MES_NUM={numero_mes})...")
        df_nuevo = self._procesar_mes(mes_carpeta, numero_mes=numero_mes)
        print(f"   ✅ {mes_carpeta}: {df_nuevo.shape[0]:,} filas × "
              f"{df_nuevo.shape[1]} cols")

        # ── Concatenar ─────────────────────────────────────────────
        if df_existente is not None:
            geih = pd.concat([df_existente, df_nuevo], ignore_index=True)
            del df_existente, df_nuevo
        else:
            geih = df_nuevo
            del df_nuevo
        gc.collect()

        meses_final = sorted(geih["MES_NUM"].unique().tolist())
        print(f"\n{'='*60}")
        print(f"  ✅ MES AGREGADO — {mes_carpeta}")
        print(f"  {geih.shape[0]:,} filas × {geih.shape[1]} columnas")
        print(f"  Meses: {meses_final}")
        print(f"  ⚠️  Recuerde actualizar config.n_meses={len(meses_final)} "
              f"para que FEX_ADJ se divida correctamente.")
        print(f"{'='*60}")

        return geih

    def exportar(
        self,
        df: pd.DataFrame,
        nombre: Optional[str] = None,
        formato: str = "parquet",
    ) -> None:
        """Exporta la base consolidada a disco.

        CAMBIO v4.0: Si no se pasa nombre, se genera automáticamente
        como 'GEIH_{anio}_Consolidado.parquet'.

        Args:
            df: DataFrame consolidado.
            nombre: Nombre del archivo de salida. Si None, se auto-genera.
            formato: 'parquet' (recomendado) o 'csv'.
        """
        if nombre is None:
            ext = "parquet" if formato == "parquet" else "csv"
            nombre = f"GEIH_{self.config.anio}_Consolidado.{ext}"

        ruta = self.ruta_base / nombre

        if formato == "parquet":
            df.to_parquet(ruta, index=False, compression="snappy")
        elif formato == "csv":
            df.to_csv(
                ruta, index=False,
                encoding=self.config.encoding_csv,
            )
        else:
            raise ValueError(f"Formato no soportado: {formato}")

        size_mb = ruta.stat().st_size / 1e6
        print(f"✅ Base guardada: {ruta.name} ({size_mb:.0f} MB)")

    @staticmethod
    def cargar(ruta: str) -> pd.DataFrame:
        """Carga una base previamente consolidada.

        Args:
            ruta: Ruta al archivo .parquet o .csv.

        Returns:
            DataFrame con la base GEIH consolidada.
        """
        ruta_p = Path(ruta)
        if ruta_p.suffix == ".parquet":
            df = pd.read_parquet(ruta_p)
        elif ruta_p.suffix in (".csv", ".zip"):
            df = pd.read_csv(ruta_p, low_memory=False)
        else:
            raise ValueError(f"Formato no reconocido: {ruta_p.suffix}")

        print(f"✅ Base cargada: {df.shape[0]:,} filas × {df.shape[1]} cols")
        return df

    # ── Métodos privados ───────────────────────────────────────────

    @staticmethod
    def _inferir_numero_mes(nombre_carpeta: str) -> int:
        """Infiere el número de mes a partir del nombre de carpeta DANE.

        'Enero 2025' → 1, 'Diciembre 2026' → 12.

        Args:
            nombre_carpeta: Nombre como 'Marzo 2026'.

        Returns:
            Número del mes (1-12).

        Raises:
            ValueError: Si no se puede inferir el mes.
        """
        nombre_lower = nombre_carpeta.lower().strip()
        for i, mes in enumerate(MESES_NOMBRES, 1):
            if nombre_lower.startswith(mes.lower()):
                return i
        raise ValueError(
            f"No se pudo inferir el número de mes de '{nombre_carpeta}'. "
            f"Pase numero_mes= explícitamente."
        )

    def _procesar_mes(self, mes: str, numero_mes: int) -> pd.DataFrame:
        """Lee y une los módulos de un mes específico.

        El módulo ancla es siempre 'Características generales' porque
        contiene TODOS los individuos del universo. Los demás módulos
        son subconjuntos (solo ocupados, solo desocupados, etc.).

        Usa _buscar_archivo() para encontrar CSVs sin importar
        si tienen tildes o no (Migración.CSV = Migracion.CSV).
        """
        ruta_csv = self.ruta_base / mes / "CSV"

        # Leer módulo ancla (universo completo)
        ruta_ancla = self._buscar_archivo(ruta_csv, MODULOS_CSV["caracteristicas"])
        if ruta_ancla is None:
            raise FileNotFoundError(
                f"Módulo ancla no encontrado en {ruta_csv}: "
                f"{MODULOS_CSV['caracteristicas']}"
            )
        df_mes = self._leer_csv(ruta_ancla)

        # Unir módulos secundarios
        modulos_secundarios = {
            "hogar":          LLAVES_HOGAR,
            "fuerza_trabajo": LLAVES_PERSONA,
            "ocupados":       LLAVES_PERSONA,
            "no_ocupados":    LLAVES_PERSONA,
        }
        # Módulos opcionales
        for mod in self._modulos_a_incluir:
            if mod in ("caracteristicas",):
                continue
            if mod not in modulos_secundarios:
                modulos_secundarios[mod] = LLAVES_PERSONA

        for mod_key, llaves in modulos_secundarios.items():
            if mod_key not in self._modulos_a_incluir:
                continue
            nombre_csv = MODULOS_CSV.get(mod_key)
            if not nombre_csv:
                continue
            ruta_mod = self._buscar_archivo(ruta_csv, nombre_csv)
            if ruta_mod is not None:
                df_mod = self._leer_csv(ruta_mod)
                df_mes = self._unir_sin_duplicados(df_mes, df_mod, llaves)
                del df_mod
                gc.collect()

        # Agregar número de mes
        df_mes["MES_NUM"] = numero_mes

        return df_mes

    def _leer_csv(self, ruta: Path) -> pd.DataFrame:
        """Lee un CSV del DANE con la configuración correcta."""
        return pd.read_csv(
            ruta,
            sep=self.config.separador_csv,
            encoding=self.config.encoding_csv,
            converters=self.converters,
            low_memory=False,
        )

    @staticmethod
    def _unir_sin_duplicados(
        df_izq: pd.DataFrame,
        df_der: pd.DataFrame,
        llaves: List[str],
    ) -> pd.DataFrame:
        """Une dos DataFrames evitando columnas duplicadas.

        Solo trae del df_der las columnas que NO existen en df_izq.
        Usa how='left' para preservar el universo del módulo ancla.

        ⚠️ NUNCA usar how='outer' aquí: multiplicaría filas y
        produciría el error clásico de PEA inflada.

        Args:
            df_izq: DataFrame base (módulo ancla o acumulado).
            df_der: DataFrame a unir (módulo secundario).
            llaves: Columnas de join.

        Returns:
            DataFrame unido sin columnas _x / _y.
        """
        columnas_nuevas = df_der.columns.difference(df_izq.columns).tolist()
        columnas_a_usar = columnas_nuevas + llaves
        return pd.merge(
            df_izq,
            df_der[columnas_a_usar],
            on=llaves,
            how="left",
        )
