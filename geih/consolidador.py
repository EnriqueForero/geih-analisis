# -*- coding: utf-8 -*-
"""
geih.consolidador — Consolidación de microdatos GEIH mensuales (v5.1).

Construye el Data Lake (universo completo, ~515 columnas, ~5M filas) a partir
de los .zip mensuales del DANE. El filtrado a columnas analíticas es
responsabilidad de `preparador.py` (Data Mart), no de este módulo.

Decisiones críticas:
  - Módulo ancla: "Características generales" (universo completo).
  - Join: LEFT (nunca OUTER → inflaría la PEA).
  - MES_NUM se agrega como variable creada.

v5.0  Lectura directa de .zip a RAM (sin descomprimir a disco).
v5.1  DRY en verificar_estructura: el lector universal acepta
      `solo_verificar=True` y reusa el índice construido una sola vez.

Autor: Néstor Enrique Forero Herrera
"""

from __future__ import annotations

__all__ = ["ConsolidadorGEIH"]

import gc
import shutil
import unicodedata
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

import pandas as pd

from .config import (
    ConfigGEIH,
    MESES_NOMBRES,
    MODULOS_CSV,
    CONVERTERS_BASE,
    CONVERTERS_CON_AREA,
    LLAVES_PERSONA,
    LLAVES_HOGAR,
)

# Lector universal de un mes. Contrato:
#   lector(mod_key)                       -> pd.DataFrame | None
#   lector(mod_key, solo_verificar=True)  -> bool
_LectorModulo = Callable[..., Union[pd.DataFrame, bool, None]]


class ConsolidadorGEIH:
    """Consolida los microdatos GEIH mensuales en una base única (Data Lake)."""

    def __init__(
        self,
        ruta_base: str,
        config: Optional[ConfigGEIH] = None,
        incluir_area: bool = False,
        modulos_extra: Optional[List[str]] = None,
    ):
        self.ruta_base = Path(ruta_base)
        self.config = config or ConfigGEIH()
        self.converters = CONVERTERS_CON_AREA if incluir_area else CONVERTERS_BASE
        self._modulos_a_incluir: List[str] = [
            "caracteristicas", "hogar", "fuerza_trabajo",
            "ocupados", "no_ocupados",
            "otras_formas", "migracion", "otros_ingresos",
        ]
        if modulos_extra:
            self._modulos_a_incluir.extend(modulos_extra)

    # ── Normalización y fuzzy matching ────────────────────────────────

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Quita tildes, baja a minúsculas y colapsa espacios múltiples."""
        nfkd = unicodedata.normalize("NFD", texto)
        sin_tildes = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
        return " ".join(sin_tildes.lower().split())

    @staticmethod
    def _es_basura(nombre_ruta: str) -> bool:
        """Filtra __MACOSX, .DS_Store y subcarpetas DAT/ SAV/ (por segmento)."""
        n = nombre_ruta.replace("\\", "/")
        if "__MACOSX" in n or n.endswith(".DS_Store"):
            return True
        partes = {p.lower() for p in n.split("/") if p}
        return "dat" in partes or "sav" in partes

    # ── Lector universal (ZIP o carpeta) ──────────────────────────────

    @contextmanager
    def _abrir_fuente_mes(self, mes: str) -> Iterator[_LectorModulo]:
        """Abre la fuente de un mes y cede un lector unificado.

        Prioridad: `<mes>.zip` → `<mes>/` (fallback).

        Contrato del lector cedido:
            lector(mod_key)                      -> DataFrame | None
            lector(mod_key, solo_verificar=True) -> bool  (sin parsear CSV)
        """
        ruta_zip = self.ruta_base / f"{mes}.zip"
        ruta_dir = self.ruta_base / mes

        if ruta_zip.exists():
            with zipfile.ZipFile(ruta_zip, "r") as zf:
                indice_zip: Dict[str, str] = {}
                for info in zf.infolist():
                    if info.is_dir() or self._es_basura(info.filename):
                        continue
                    if not info.filename.lower().endswith(".csv"):
                        continue
                    clave = self._normalizar(Path(info.filename).stem)
                    indice_zip.setdefault(clave, info.filename)

                def lector_zip(
                    mod_key: str, solo_verificar: bool = False,
                ) -> Union[pd.DataFrame, bool, None]:
                    nombre_esperado = MODULOS_CSV.get(mod_key, "")
                    if not nombre_esperado:
                        return False if solo_verificar else None
                    clave = self._normalizar(Path(nombre_esperado).stem)
                    ruta_interna = indice_zip.get(clave)
                    if ruta_interna is None:
                        return False if solo_verificar else None
                    if solo_verificar:
                        return True
                    with zf.open(ruta_interna) as stream:
                        return self._leer_csv(stream)

                yield lector_zip
            return

        if ruta_dir.exists():
            indice_dir: Dict[str, Path] = {}
            for archivo in ruta_dir.rglob("*"):
                if not archivo.is_file() or archivo.suffix.lower() != ".csv":
                    continue
                if self._es_basura(str(archivo.relative_to(ruta_dir))):
                    continue
                clave = self._normalizar(archivo.stem)
                indice_dir.setdefault(clave, archivo)

            def lector_dir(
                mod_key: str, solo_verificar: bool = False,
            ) -> Union[pd.DataFrame, bool, None]:
                nombre_esperado = MODULOS_CSV.get(mod_key, "")
                if not nombre_esperado:
                    return False if solo_verificar else None
                clave = self._normalizar(Path(nombre_esperado).stem)
                ruta = indice_dir.get(clave)
                if ruta is None:
                    return False if solo_verificar else None
                if solo_verificar:
                    return True
                return self._leer_csv(ruta)

            yield lector_dir
            return

        raise FileNotFoundError(
            f"No se encontró '{mes}.zip' ni la carpeta '{mes}/' en {self.ruta_base}"
        )

    # ── API pública ───────────────────────────────────────────────────

    def verificar_estructura(
        self, carpetas: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        """Pre-flight check en milisegundos (solo consulta índices)."""
        carpetas = carpetas or self.config.carpetas_mensuales
        resultado: Dict[str, List[str]] = {"ok": [], "faltantes": []}

        print(f"\n{'='*60}")
        print(f"  PRE-FLIGHT CHECK — GEIH {self.config.anio}")
        print(f"{'='*60}")

        for mes in carpetas:
            try:
                with self._abrir_fuente_mes(mes) as lector:
                    faltantes_mes: List[str] = []
                    for mod_key in self._modulos_a_incluir:
                        if not lector(mod_key, solo_verificar=True):
                            nombre_csv = MODULOS_CSV.get(mod_key, mod_key)
                            faltantes_mes.append(f"[{mes}] falta: {nombre_csv}")
                    if faltantes_mes:
                        resultado["faltantes"].extend(faltantes_mes)
                    else:
                        resultado["ok"].append(mes)
            except FileNotFoundError:
                resultado["faltantes"].append(f"[{mes}] no existe .zip ni carpeta")
            except zipfile.BadZipFile:
                resultado["faltantes"].append(f"[{mes}] .zip corrupto")

        print(f"  ✅ Meses completos : {len(resultado['ok'])}")
        if resultado["faltantes"]:
            print(f"  ❌ Archivos faltantes: {len(resultado['faltantes'])}")
            for f in resultado["faltantes"][:10]:
                print(f"     • {f}")
        else:
            print(f"  ✅ Todos los archivos presentes (ZIP o carpeta)")
        return resultado

    def consolidar(
        self,
        carpetas: Optional[List[str]] = None,
        checkpoint: bool = True,
        ruta_checkpoints: Optional[str] = None,
    ) -> pd.DataFrame:
        """Consolida todos los meses. Soporta .zip y carpetas transparentemente."""
        carpetas = carpetas or self.config.carpetas_mensuales
        bases_mensuales: List[pd.DataFrame] = []

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
            if ckpt_dir:
                ckpt_file = ckpt_dir / f"mes_{i:02d}.parquet"
                if ckpt_file.exists():
                    print(f"\n♻️  [{i}/{len(carpetas)}] {mes} — checkpoint recuperado")
                    bases_mensuales.append(pd.read_parquet(ckpt_file))
                    continue

            print(f"\n🔄 [{i}/{len(carpetas)}] Procesando {mes}...")
            try:
                df_mes = self._procesar_mes(mes, numero_mes=i)
                bases_mensuales.append(df_mes)
                print(f"   ✅ {mes}: {df_mes.shape[0]:,} filas × {df_mes.shape[1]} cols")
                if ckpt_dir:
                    df_mes.to_parquet(ckpt_file, index=False, compression="snappy")
                    print(f"   💾 Checkpoint: {ckpt_file.name}")
            except FileNotFoundError as e:
                print(f"   ⚠️  {e}")
            except Exception as e:
                print(f"   ❌ Error en {mes}: {e}")
                if ckpt_dir and bases_mensuales:
                    print(f"   💾 {len(bases_mensuales)} meses en checkpoint — "
                          f"re-ejecute para continuar.")

        if not bases_mensuales:
            raise FileNotFoundError(
                "❌ No se procesó ningún mes. Use verificar_estructura() para diagnosticar."
            )

        print(f"\n🔗 Concatenando {len(bases_mensuales)} meses...")
        geih = pd.concat(bases_mensuales, ignore_index=True)
        del bases_mensuales
        gc.collect()

        if ckpt_dir and len(carpetas) == geih["MES_NUM"].nunique():
            self._limpiar_checkpoints(ckpt_dir)

        print(f"\n{'='*60}")
        print(f"  ✅ CONSOLIDACIÓN COMPLETA — {self.config.anio}")
        print(f"  {geih.shape[0]:,} filas × {geih.shape[1]} columnas")
        print(f"  Meses: {geih['MES_NUM'].nunique()} "
              f"(de {geih['MES_NUM'].min()} a {geih['MES_NUM'].max()})")
        print(f"{'='*60}")
        return geih

    def agregar_mes(
        self,
        mes_carpeta: str,
        parquet_existente: str,
        numero_mes: Optional[int] = None,
    ) -> pd.DataFrame:
        """Agrega un mes a un Parquet existente sin re-consolidar todo."""
        ruta_parquet = self.ruta_base / parquet_existente

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

        if numero_mes is None:
            numero_mes = self._inferir_numero_mes(mes_carpeta)

        if numero_mes in meses_existentes:
            print(f"⚠️  El mes {numero_mes} ({mes_carpeta}) ya existe en la base.")
            return df_existente

        print(f"\n🔄 Procesando {mes_carpeta} (MES_NUM={numero_mes})...")
        df_nuevo = self._procesar_mes(mes_carpeta, numero_mes=numero_mes)
        print(f"   ✅ {mes_carpeta}: {df_nuevo.shape[0]:,} filas × "
              f"{df_nuevo.shape[1]} cols")

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
        self, df: pd.DataFrame,
        nombre: Optional[str] = None, formato: str = "parquet",
    ) -> None:
        """Exporta a Parquet (recomendado) o CSV."""
        if formato not in ("parquet", "csv"):
            raise ValueError(f"Formato no soportado: {formato!r}")
        if nombre is None:
            nombre = f"GEIH_{self.config.anio}_Consolidado.{formato}"
        ruta = self.ruta_base / nombre
        if formato == "parquet":
            df.to_parquet(ruta, index=False, compression="snappy")
        else:
            df.to_csv(ruta, index=False, encoding=self.config.encoding_csv)
        print(f"✅ Base guardada: {ruta.name} ({ruta.stat().st_size / 1e6:.0f} MB)")

    @staticmethod
    def cargar(ruta: str) -> pd.DataFrame:
        """Carga una base previamente consolidada (Parquet o CSV)."""
        ruta_p = Path(ruta)
        if ruta_p.suffix == ".parquet":
            df = pd.read_parquet(ruta_p)
        elif ruta_p.suffix in (".csv", ".zip"):
            df = pd.read_csv(ruta_p, low_memory=False)
        else:
            raise ValueError(f"Formato no reconocido: {ruta_p.suffix}")
        print(f"✅ Base cargada: {df.shape[0]:,} filas × {df.shape[1]} cols")
        return df

    # ── Métodos privados ──────────────────────────────────────────────

    @staticmethod
    def _inferir_numero_mes(nombre_carpeta: str) -> int:
        """'Enero 2025' → 1 ; 'Diciembre 2026' → 12."""
        nombre_lower = nombre_carpeta.lower().strip()
        for i, mes in enumerate(MESES_NOMBRES, 1):
            if nombre_lower.startswith(mes.lower()):
                return i
        raise ValueError(
            f"No se pudo inferir el número de mes de '{nombre_carpeta}'. "
            f"Pase numero_mes= explícitamente."
        )

    def _procesar_mes(self, mes: str, numero_mes: int) -> pd.DataFrame:
        """Ancla + LEFT JOINs + MES_NUM (agnóstico de ZIP vs. carpeta)."""
        with self._abrir_fuente_mes(mes) as lector:
            df_mes = lector("caracteristicas")
            if df_mes is None:
                raise FileNotFoundError(
                    f"Módulo ancla no encontrado en {mes}: "
                    f"{MODULOS_CSV['caracteristicas']}"
                )

            modulos_secundarios: Dict[str, List[str]] = {
                "hogar":          LLAVES_HOGAR,
                "fuerza_trabajo": LLAVES_PERSONA,
                "ocupados":       LLAVES_PERSONA,
                "no_ocupados":    LLAVES_PERSONA,
            }
            for mod in self._modulos_a_incluir:
                if mod != "caracteristicas":
                    modulos_secundarios.setdefault(mod, LLAVES_PERSONA)

            for mod_key, llaves in modulos_secundarios.items():
                if mod_key not in self._modulos_a_incluir:
                    continue
                df_mod = lector(mod_key)
                if df_mod is not None:
                    df_mes = self._unir_sin_duplicados(df_mes, df_mod, llaves)
                    del df_mod
                    gc.collect()

        df_mes["MES_NUM"] = numero_mes
        return df_mes

    def _leer_csv(self, origen: Union[Path, Any]) -> pd.DataFrame:
        """Parsea un CSV del DANE. Acepta Path o file-like (stream de ZIP)."""
        return pd.read_csv(
            origen,
            sep=self.config.separador_csv,
            encoding=self.config.encoding_csv,
            converters=self.converters,
            low_memory=False,
        )

    @staticmethod
    def _unir_sin_duplicados(
        df_izq: pd.DataFrame, df_der: pd.DataFrame, llaves: List[str],
    ) -> pd.DataFrame:
        """LEFT JOIN sin columnas duplicadas. NUNCA usar how='outer' aquí."""
        columnas_nuevas = df_der.columns.difference(df_izq.columns).tolist()
        columnas_a_usar = columnas_nuevas + llaves
        return pd.merge(df_izq, df_der[columnas_a_usar], on=llaves, how="left")

    @staticmethod
    def _limpiar_checkpoints(ckpt_dir: Path) -> None:
        """Elimina la carpeta de checkpoints tras consolidación exitosa."""
        try:
            shutil.rmtree(ckpt_dir)
            print(f"   🗑️  Checkpoints eliminados (consolidación exitosa)")
        except Exception:
            pass  # No crítico: el proceso ya terminó bien.
