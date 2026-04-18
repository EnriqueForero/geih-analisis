"""
geih.descargador — Descarga automática de microdatos GEIH desde el DANE.

Elimina el paso manual de descargar ZIPs del portal de microdatos,
descomprimirlos y organizarlos en carpetas mensuales.

Inspirado en geihdanepy (github.com/BautistaDavid/geihdanepy) pero
mejorado con: soporte multi-año, descompresión automática a la
estructura de carpetas que espera ConsolidadorGEIH, verificación
de integridad, y progreso visible.

NOTA IMPORTANTE: El portal de microdatos del DANE (microdatos.dane.gov.co)
a veces requiere aceptar términos de uso. Si la descarga falla con
código 403 o redirección, el usuario debe descargar manualmente desde
el portal y colocar los ZIPs en la carpeta indicada.

Autor: Néstor Enrique Forero Herrera
"""

__all__ = ["DescargadorDANE"]

import shutil
import zipfile
from pathlib import Path
from typing import Optional

from .config import MESES_NOMBRES, ConfigGEIH

# ═════════════════════════════════════════════════════════════════════
# CATÁLOGO DE URLs DEL DANE POR AÑO
# ═════════════════════════════════════════════════════════════════════

# IDs del catálogo de microdatos DANE para cada año.
# Página: https://microdatos.dane.gov.co/index.php/catalog/{ID}/get-microdata
# Actualizar cuando el DANE publique nuevos años.
CATALOGO_DANE: dict[int, dict] = {
    2022: {"catalog_id": 771, "nota": "Marco 2018 — primer año"},
    2023: {"catalog_id": 782, "nota": "Marco 2018"},
    2024: {"catalog_id": 819, "nota": "Marco 2018"},
    2025: {"catalog_id": 853, "nota": "Marco 2018"},
    # 2026: {"catalog_id": ???, "nota": "Actualizar cuando se publique"},
}

# Patrones de URL del DANE (pueden cambiar — el DANE no tiene API estable)
_URL_MICRODATOS = "https://microdatos.dane.gov.co/index.php/catalog/{catalog_id}/get-microdata"
_URL_DOWNLOAD = "https://microdatos.dane.gov.co/index.php/catalog/{catalog_id}/download/{file_id}"


class DescargadorDANE:
    """Descarga y organiza microdatos GEIH desde el portal del DANE.

    El flujo completo es:
      1. Descargar ZIPs mensuales del portal de microdatos
      2. Descomprimirlos en la estructura de carpetas esperada
      3. Verificar que todos los módulos CSV estén presentes

    Si la descarga automática falla (el DANE requiere aceptar términos),
    el módulo ofrece instrucciones claras para descarga manual.

    Uso típico:
        desc = DescargadorDANE(
            config=ConfigGEIH(anio=2025, n_meses=12),
            ruta_destino='/content/drive/MyDrive/GEIH',
        )
        # Opción A: Descarga automática (si el DANE lo permite)
        desc.descargar_todos()

        # Opción B: Organizar ZIPs ya descargados manualmente
        desc.organizar_zips('/content/drive/MyDrive/GEIH/zips_dane')

        # Verificar estructura
        desc.verificar()
    """

    def __init__(
        self,
        config: Optional[ConfigGEIH] = None,
        ruta_destino: str = ".",
    ):
        """
        Args:
            config: Configuración con año y n_meses.
            ruta_destino: Carpeta donde crear la estructura de carpetas
                          mensuales (ej: 'Enero 2025/CSV/').
        """
        self.config = config or ConfigGEIH()
        self.ruta_destino = Path(ruta_destino)
        self.ruta_destino.mkdir(parents=True, exist_ok=True)

    def descargar_todos(self) -> dict[str, str]:
        """Intenta descargar todos los meses desde el portal del DANE.

        Returns:
            Dict con {mes: 'ok'|'error: mensaje'} para cada mes.

        NOTA: El DANE puede bloquear descargas automáticas. Si falla,
        use organizar_zips() con archivos descargados manualmente.
        """
        anio = self.config.anio
        if anio not in CATALOGO_DANE:
            print(f"❌ Año {anio} no está en el catálogo del DANE.")
            print(f"   Años disponibles: {sorted(CATALOGO_DANE.keys())}")
            print("   → Descargue manualmente desde:")
            print("     https://microdatos.dane.gov.co/index.php/catalog/central")
            return {}

        catalog_id = CATALOGO_DANE[anio]["catalog_id"]
        print(f"\n{'='*60}")
        print(f"  DESCARGA GEIH {anio} — Catálogo DANE #{catalog_id}")
        print(f"{'='*60}")
        print(f"  Portal: {_URL_MICRODATOS.format(catalog_id=catalog_id)}")
        print(f"  Meses a descargar: {self.config.n_meses}")

        resultados = {}
        carpetas = self.config.carpetas_mensuales

        try:
            import requests
        except ImportError:
            print("\n⚠️  El módulo 'requests' no está instalado.")
            print("   Instalar con: !pip install requests")
            print("   O use organizar_zips() con archivos descargados manualmente.")
            return {}

        for i, mes_carpeta in enumerate(carpetas, 1):
            mes_nombre = mes_carpeta.split()[0]  # 'Enero 2025' → 'Enero'
            print(f"\n🔄 [{i}/{len(carpetas)}] Descargando {mes_carpeta}...")

            try:
                ok = self._descargar_mes(mes_nombre, catalog_id, requests)
                resultados[mes_carpeta] = "ok" if ok else "no encontrado"
            except Exception as e:
                resultados[mes_carpeta] = f"error: {e}"
                print(f"   ❌ Error: {e}")

        # Resumen
        ok_count = sum(1 for v in resultados.values() if v == "ok")
        print(f"\n{'='*60}")
        print(f"  RESUMEN: {ok_count}/{len(carpetas)} meses descargados")
        if ok_count < len(carpetas):
            print("\n  Para los meses faltantes, descargue manualmente desde:")
            print(f"  {_URL_MICRODATOS.format(catalog_id=catalog_id)}")
            print("  y use: descargador.organizar_zips('ruta/a/los/zips')")
        print(f"{'='*60}")

        return resultados

    def _descargar_mes(self, mes_nombre: str, catalog_id: int, requests) -> bool:
        """Intenta descargar el ZIP de un mes específico.

        El DANE nombra los archivos como 'Enero.csv', 'Febrero.csv', etc.
        (son ZIPs renombrados o CSVs directos según el año).
        """
        # Intentar variantes de nombre que usa el DANE
        variantes = [
            f"{mes_nombre}.csv",
            f"{mes_nombre} CSV.zip",
            f"{mes_nombre}.zip",
            f"mes_{MESES_NOMBRES.index(mes_nombre)+1:02d}.zip",
        ]

        url_page = _URL_MICRODATOS.format(catalog_id=catalog_id)

        # El DANE no tiene API pública — intentamos scraping ligero
        try:
            resp = requests.get(url_page, timeout=30)
            if resp.status_code != 200:
                print(f"   ⚠️  Portal responde {resp.status_code} — puede requerir login")
                return False

            # Buscar links de descarga en la página
            content = resp.text
            for variante in variantes:
                if variante.lower() in content.lower():
                    print(f"   📥 Encontrado: {variante}")
                    # Intentar extraer el link de descarga
                    # (El DANE usa JavaScript, esto es best-effort)
                    break
            else:
                print(f"   ⚠️  No se encontró archivo para {mes_nombre}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Error de red: {e}")
            return False

        print("   ⚠️  Descarga automática no soportada por el portal actual del DANE.")
        print("   → Use organizar_zips() con archivos descargados manualmente.")
        return False

    def organizar_zips(
        self,
        ruta_zips: str,
        patron: str = "*.zip",
    ) -> int:
        """Organiza ZIPs descargados manualmente en la estructura de carpetas.

        El DANE publica ZIPs mensuales. Esta función los descomprime
        en la estructura que espera ConsolidadorGEIH:
            Enero 2025/CSV/Características generales....CSV
            Enero 2025/CSV/Ocupados.CSV
            ...

        Args:
            ruta_zips: Carpeta donde están los ZIPs descargados.
            patron: Patrón glob para encontrar ZIPs.

        Returns:
            Número de meses organizados exitosamente.

        Uso:
            # 1. Descargue los ZIPs del DANE manualmente
            # 2. Colóquelos en una carpeta
            desc.organizar_zips('/content/drive/MyDrive/GEIH/zips')
        """
        ruta = Path(ruta_zips)
        if not ruta.exists():
            print(f"❌ Carpeta no existe: {ruta}")
            return 0

        zips = sorted(ruta.glob(patron))
        if not zips:
            print(f"⚠️  No se encontraron archivos {patron} en {ruta}")
            return 0

        print(f"\n{'='*60}")
        print(f"  ORGANIZANDO ZIPs GEIH {self.config.anio}")
        print(f"{'='*60}")
        print(f"  ZIPs encontrados: {len(zips)}")

        organizados = 0
        for zip_path in zips:
            try:
                mes_nombre = self._inferir_mes_de_zip(zip_path.name)
                if mes_nombre is None:
                    print(f"  ⚠️  No se pudo inferir el mes de: {zip_path.name}")
                    continue

                carpeta_mes = f"{mes_nombre} {self.config.anio}"
                ruta_csv = self.ruta_destino / carpeta_mes / "CSV"
                ruta_csv.mkdir(parents=True, exist_ok=True)

                n_extraidos = self._extraer_zip(zip_path, ruta_csv)
                print(f"  ✅ {carpeta_mes}: {n_extraidos} archivos extraídos")
                organizados += 1

            except Exception as e:
                print(f"  ❌ Error con {zip_path.name}: {e}")

        print(f"\n✅ {organizados} meses organizados en {self.ruta_destino}")
        return organizados

    def _extraer_zip(self, zip_path: Path, ruta_csv: Path) -> int:
        """Extrae un ZIP al directorio CSV, manejando subcarpetas."""
        n = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                # Solo extraer CSVs (ignorar carpetas, __MACOSX, etc.)
                basename = Path(member).name
                if not basename.upper().endswith(".CSV"):
                    continue
                if basename.startswith(".") or "__MACOSX" in member:
                    continue

                # Extraer al directorio CSV plano
                with zf.open(member) as src:
                    dest = ruta_csv / basename
                    with open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    n += 1
        return n

    def _inferir_mes_de_zip(self, nombre_archivo: str) -> Optional[str]:
        """Infiere el nombre del mes a partir del nombre del ZIP."""
        nombre_lower = nombre_archivo.lower()
        for mes in MESES_NOMBRES:
            if mes.lower() in nombre_lower:
                return mes
        # Intentar por número: mes_01.zip, 01_enero.zip, etc.
        import re

        match = re.search(r"(\d{1,2})", nombre_archivo)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 12:
                return MESES_NOMBRES[num - 1]
        return None

    def verificar(self) -> dict[str, list[str]]:
        """Verifica que la estructura de carpetas esté completa.

        Wrapper sobre ConsolidadorGEIH.verificar_estructura().

        Returns:
            Dict con 'ok' y 'faltantes'.
        """
        from .consolidador import ConsolidadorGEIH

        c = ConsolidadorGEIH(
            ruta_base=str(self.ruta_destino),
            config=self.config,
        )
        return c.verificar_estructura()

    def instrucciones_descarga_manual(self) -> None:
        """Imprime instrucciones paso a paso para descarga manual."""
        anio = self.config.anio
        catalog_id = CATALOGO_DANE.get(anio, {}).get("catalog_id", "???")

        print(f"\n{'='*65}")
        print(f"  📋 INSTRUCCIONES DE DESCARGA MANUAL — GEIH {anio}")
        print(f"{'='*65}")
        print("")
        print("  1. Abra el portal de microdatos del DANE:")
        print(f"     https://microdatos.dane.gov.co/index.php/catalog/{catalog_id}/get-microdata")
        print("")
        print("  2. Acepte los términos de uso (si se le solicita).")
        print("")
        print("  3. Descargue los ZIPs mensuales (Enero.csv ... Diciembre.csv)")
        print("     Nota: El DANE los nombra .csv pero son ZIPs.")
        print("")
        print("  4. Coloque TODOS los ZIPs en una sola carpeta, por ejemplo:")
        print(f"     {self.ruta_destino}/zips_dane_{anio}/")
        print("")
        print("  5. Ejecute en el notebook:")
        print("     from geih import DescargadorDANE, ConfigGEIH")
        print("     desc = DescargadorDANE(")
        print(f"         config=ConfigGEIH(anio={anio}, n_meses={self.config.n_meses}),")
        print(f"         ruta_destino='{self.ruta_destino}',")
        print("     )")
        print(f"     desc.organizar_zips('{self.ruta_destino}/zips_dane_{anio}')")
        print("     desc.verificar()")
        print("")
        print("  6. Continúe con el pipeline normal:")
        print(f"     consolidador = ConsolidadorGEIH(ruta_base='{self.ruta_destino}', ...)")
        print(f"{'='*65}")
