<div align="center">

# 📊 geih-analisis

**El paquete Python definitivo para analizar la Gran Encuesta Integrada de Hogares (GEIH) del DANE — Colombia.**

[![PyPI version](https://badge.fury.io/py/geih-analisis.svg)](https://pypi.org/project/geih-analisis/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI downloads](https://img.shields.io/pypi/dm/geih-analisis.svg)](https://pypi.org/project/geih-analisis/)
[![Tested on](https://img.shields.io/badge/tested%20on-Colab%20%7C%20Linux%20%7C%20macOS%20%7C%20Windows-informational)]()
[![AI Assisted](https://img.shields.io/badge/AI%20Assisted-Claude%20%7C%20Gemini-blue)]()

*Convierte microdatos crudos del DANE en indicadores laborales listos para reportar: desempleo, salarios, brechas de género, informalidad, retornos a la educación, Gini y más — con pocas líneas de código y rigor muestral.*

</div>

---

> **🇬🇧 English summary:** Python package for analyzing microdata from Colombia's official household survey (GEIH, DANE). Reads raw monthly ZIP files directly into memory, builds a ~5M-row Data Lake, and computes labor-market indicators (unemployment, wages, gender gap, informality, regional CIIU × department) with proper complex-survey sampling error. `pip install geih-analisis`.

---

## ⚠️ Antes de empezar — tres advertencias que debes leer

> **1. Este paquete NO es una fuente oficial.** Es una herramienta de cálculo desarrollada de manera independiente. No tiene afiliación, respaldo, endoso ni vínculo institucional alguno con el Departamento Administrativo Nacional de Estadística (DANE). Los datos de la GEIH son propiedad del DANE y su uso se rige por los términos del portal oficial de microdatos.
>
> **2. Siempre valide contra el Boletín DANE.** Cualquier indicador producido con esta librería **debe contrastarse** con el Boletín GEIH oficial más reciente antes de publicarse, citarse o enviarse a tomadores de decisión. Si su cifra difiere de la publicada por el DANE en más de la tolerancia del indicador (típicamente **±0.05 p.p.** para tasas, **±1 mil personas** para poblaciones), el problema está en su consolidado o código — no en el boletín. El [Boletín mensual de empleo](https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo) es la fuente-de-verdad. Use la [§ Verificación contra el Boletín DANE](#-13-verificación-contra-el-boletín-dane) como protocolo obligatorio.
>
> **3. La responsabilidad final es del usuario.** Los autores proveen esta herramienta de buena fe bajo licencia MIT sin garantía alguna. El usuario es responsable de verificar la correspondencia de los resultados con fuentes oficiales, de interpretarlos dentro del marco metodológico correcto, y de cumplir los términos de uso de los datos originales del DANE.

---

## 📑 Tabla de contenidos

1. [¿Qué es esta librería?](#-1-qué-es-esta-librería)
2. [¿Para quién está diseñada?](#-2-para-quién-está-diseñada)
3. [Instalación](#-3-instalación)
4. [Paso 0 — Descargar los datos del DANE](#-4-paso-0--descargar-los-datos-del-dane)
5. [Inicio rápido — *Hola Mundo Laboral*](#-5-inicio-rápido--hola-mundo-laboral)
6. [Conceptos clave que debes entender](#-6-conceptos-clave-que-debes-entender)
7. [Arquitectura y flujo de trabajo](#-7-arquitectura-y-flujo-de-trabajo)
8. [Catálogo completo de análisis](#-8-catálogo-completo-de-análisis)
9. [Ejemplos por perfil de usuario](#-9-ejemplos-por-perfil-de-usuario)
10. [Análisis departamental × rama CIIU](#-10-análisis-departamental--rama-ciiu)
11. [Análisis por 32 ciudades y áreas metropolitanas](#-11-análisis-por-32-ciudades-y-áreas-metropolitanas)
12. [Análisis de tierras agropecuarias](#-12-análisis-de-tierras-agropecuarias)
13. [Verificación contra el Boletín DANE](#-13-verificación-contra-el-boletín-dane)
14. [Replicación oficial — Informalidad (17ª CIET)](#-14-replicación-oficial--informalidad-17ª-ciet)
15. [Precisión muestral — cómo saber si puedes publicar](#-15-precisión-muestral--cómo-saber-si-puedes-publicar)
16. [Desestacionalización de series](#-16-desestacionalización-de-series)
17. [Dashboard interactivo (Streamlit)](#-17-dashboard-interactivo-streamlit)
18. [Configuración avanzada](#-18-configuración-avanzada)
19. [Herramientas auxiliares](#-19-herramientas-auxiliares)
20. [Notebooks de ejemplo](#-20-notebooks-de-ejemplo)
21. [Años soportados y SMMLV](#-21-años-soportados-y-smmlv)
22. [Mapa del código (para contribuidores)](#-22-mapa-del-código-para-contribuidores)
23. [Preguntas frecuentes](#-23-preguntas-frecuentes)
24. [Cómo citar](#-24-cómo-citar)
25. [Agradecimientos](#-25-agradecimientos)
26. [Licencia, metodología y disclaimer legal](#-26-licencia-metodología-y-disclaimer-legal)

---

## 🎯 1. ¿Qué es esta librería?

### En una frase
`geih-analisis` automatiza todo el proceso que va desde los archivos `.zip` crudos que publica el DANE cada mes hasta tener indicadores laborales de publicación calidad-boletín — con factores de expansión, coeficientes de variación, intervalos de confianza y clasificación de precisión incluidos.

### Una analogía para estudiantes
Piensa en los microdatos de la GEIH como si fueran los **ingredientes crudos** de un restaurante: 8 CSV mensuales (personas, hogares, ocupados, entre otros), cada uno con cientos de columnas, nombres crípticos (`P6430`, `P3042`, `FEX_C18`), códigos que hay que descifrar con un manual de 500 páginas, y reglas de ponderación complejas.

`geih-analisis` es el **chef de cocina** que:

1. **Recibe los ingredientes crudos** (los ZIP mensuales, sin descomprimir).
2. **Los limpia y los combina** (hace los JOINs correctos, aplica factores de expansión, mapea códigos a etiquetas).
3. **Te entrega el plato servido** (una tabla de indicadores que puedes pegar directamente en tu tesis, informe o presentación).

Y lo hace siguiendo **la receta oficial del DANE** — no una aproximación. Cuando haya que elegir entre "lo fácil" y "lo oficial", elige "lo oficial" y te avisa si tu configuración podría estar produciendo cifras que no cuadran con el boletín.

### Lo que esta librería te ahorra
Sin `geih-analisis`, un estudiante típico de economía se enfrenta a:

- 🔴 **2–3 semanas** descifrando el manual DDI-853 y el diccionario de variables
- 🔴 **1 semana** montando el merge correcto de los 8 módulos CSV
- 🔴 **Varios días** descubriendo por qué sus cifras no cuadran con el boletín (y casi siempre es el factor de expansión o el dominio geográfico)
- 🔴 **Incertidumbre permanente** sobre si puede publicar una cifra de Vaupés o si la muestra es muy pequeña

Con `geih-analisis`, esas mismas tareas toman:

- 🟢 **5 minutos** para instalar y descargar los ZIP
- 🟢 **5 minutos más** para la primera consolidación (se hace una vez al año)
- 🟢 **Segundos** para cada indicador nuevo (la librería cachea en Parquet)
- 🟢 **Una línea** para saber si la cifra es publicable (`clasificar_precision(cv_pct)`)

---

## 👥 2. ¿Para quién está diseñada?

Esta librería es para ti si eres alguno de los siguientes perfiles:

### 🎓 Estudiante de pregrado o posgrado
**Economía, Sociología, Ciencia Política, Ingeniería Industrial, Estadística.** Necesitas datos reales del mercado laboral colombiano para tu trabajo de grado, tesis o paper — y no quieres perder un semestre pelando los microdatos. Con unas 10 líneas de código produces una tabla de brecha salarial, una ecuación de Mincer o un Gini nacional, todos con intervalos de confianza.

### 🔬 Investigador académico
**Universidades, think tanks, centros de estudios.** Necesitas reproducibilidad total, replicabilidad multi-año, y rigor estadístico (CV, DEFF, IC 95 % bajo diseño complejo). Esta librería te da eso más un CHANGELOG auditable, tests canario contra el boletín DANE y un protocolo de verificación documentado.

### 🏛️ Gobierno, consultor o analista sectorial
**Ministerios, gobernaciones, alcaldías, Centros de Pensamiento, firmas consultoras, empresas privadas.** Necesitas reportes departamentales o sectoriales con evaluación de confiabilidad en cada celda — no quieres publicar una TD de Amazonas sin saber que el CV es del 38 %. La librería integra la clasificación oficial DANE (`✅ Precisión alta / ⚠️ aceptable / ❌ No publicable`) en cada tabla.

### 📰 Periodista de datos o analista independiente
**Medios especializados, portales de datos, investigación ciudadana.** Necesitas ir más rápido que las redacciones tradicionales, pero con cifras defendibles. El dashboard Streamlit incluido te permite hacer exploración visual sin programar, y los Excel exportados traen formato institucional listo para infografía.

### 💼 Empresa privada
**Departamentos de inteligencia de mercado, RR. HH., planificación estratégica.** Necesitas entender tamaño de bolsa laboral por región, niveles salariales por sector, disponibilidad de talento bilingüe, costos laborales reales (incluyendo el 54 % de carga prestacional colombiana). Los índices ICE, ICI, ITAT, IVI, ICF están diseñados exactamente para eso.

**No necesitas** experiencia avanzada en programación, conocer la estructura interna de la GEIH, ni saber qué es un factor de expansión. El paquete maneja todo eso por ti. Si sabes llamar una función de Python y leer una tabla, puedes usarlo.

---

## 🚀 3. Instalación

### Opción A — `pip` desde PyPI (recomendado)

```bash
# Instalación básica — suficiente para 90 % de los casos
pip install geih-analisis

# Con gráficos (matplotlib + plotly)
pip install "geih-analisis[viz]"

# Con dashboard web interactivo (Streamlit)
pip install "geih-analisis[dashboard]"

# Todo — gráficos + dashboard + utilidades Colab
pip install "geih-analisis[all]"
```

### Opción B — Google Colab (flujo típico del autor)

```python
# Celda 1: montar Google Drive e instalar
from google.colab import drive
drive.mount('/content/drive')

!pip install geih-analisis --upgrade --quiet

# Celda 2: verificar versión instalada
from geih import __version__
print(f"✅ geih-analisis v{__version__} listo")
```

### Opción C — desarrollo desde el repositorio

```bash
git clone https://github.com/enriqueforero/geih-analisis.git
cd geih-analisis
pip install -e ".[dev]"
pytest tests/ -v
```

### Requisitos del sistema

| Componente | Mínimo | Recomendado | Por qué importa |
|---|---|---|---|
| **Python** | 3.9 | 3.11+ | Soporte de tipos y `dataclass(kw_only=True)` |
| **pandas** | 1.5 | 2.0+ | Agrupaciones grandes con `pyarrow` backend |
| **numpy** | 1.21 | 1.24+ | Operaciones vectorizadas sobre FEX |
| **pyarrow** | 10.0 | 14.0+ | Lectura/escritura Parquet del Data Lake |
| **scipy** | 1.7 | 1.11+ | Distribuciones para IC bajo diseño complejo |
| **openpyxl** | 3.0 | 3.1+ | Exportación Excel multi-hoja con formato |
| **RAM** | 8 GB | 16 GB+ | El Data Lake anual ocupa ~2–3 GB en RAM |
| **Disco** | 5 GB | 10 GB+ | ZIP mensuales + Parquet consolidado |

> 💡 **Tip Colab:** la opción *Colab Pro* con RAM alta (25 GB) maneja un año completo sin problemas. El plan gratuito (12 GB) necesita que proceses trimestre por trimestre o uses el checkpoint (§7).

---

## 📥 4. Paso 0 — Descargar los datos del DANE

> ⚠️ **Este paquete no incluye los datos.** Los microdatos son públicos y gratuitos. Tú los descargas del portal oficial del DANE.

### 4.1 ¿Dónde descargar los microdatos?

**Portal oficial del DANE:** 🔗 [https://microdatos.dane.gov.co](https://microdatos.dane.gov.co/index.php/catalog/central/about)

**Pasos:**

1. Abrir el portal y buscar **"Gran Encuesta Integrada de Hogares"** (desde 2022 se publica con el Marco Muestral 2018).
2. Seleccionar el año (ej. *GEIH 2025* o *GEIH 2026*, según sea el caso) → click en **"Obtener microdatos"**.
3. Descargar el **ZIP mensual** de cada mes que quieras analizar.

Cada ZIP contiene los **8 módulos CSV** que define el DANE:

| # | Módulo | Granularidad | Qué contiene |
|---|---|---|---|
| 1 | Características generales | Persona | Sexo, edad, parentesco, etnia, educación |
| 2 | Datos del hogar y vivienda | Hogar | Tenencia, servicios, pobreza multidimensional |
| 3 | Fuerza de trabajo | Persona 15+ | Condición de actividad (OCI/DSI/INA) |
| 4 | Ocupados | Persona ocupada | Rama, posición, contrato, salario, seg. social |
| 5 | No ocupados | Persona no ocupada | Tiempo de desempleo, búsqueda |
| 6 | Otras formas de trabajo | Persona 10+ | Trabajo no remunerado, cuidado |
| 7 | Migración | Persona | Lugar de nacimiento, razón de cambio |
| 8 | Otros ingresos | Persona | Pensiones, arriendos, remesas |

> 📘 **Los archivos `.DAT` y `.SAV` son para software estadístico especializado (SPSS, SAS)** y no se usan aquí. Solo necesitas el ZIP que contiene los CSV.

### 4.2 Documentación oficial que DEBES leer al menos una vez

Leer estos documentos evita errores graves. No es opcional para uso serio.

| Recurso | Para qué sirve | Enlace |
|---|---|---|
| **Manual DDI-853** | Diccionario completo de variables (`P3271`=sexo, `P6430`=posición ocupacional, `P6870`=tamaño empresa, etc.) | [Catálogo DANE 853](https://microdatos.dane.gov.co/index.php/catalog/853) |
| **Boletín mensual GEIH** | Cifras oficiales publicadas — **fuente-de-verdad para validación cruzada** | [Mercado laboral DANE](https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo) |
| **Anexo Excel del boletín** | Cifras con 4 decimales — crítico para validación estricta (el PDF redondea a 1 decimal) | Dentro del boletín, pestaña "Anexos" |
| **DIVIPOLA** | División Político-Administrativa (códigos de departamento y municipio) | [Geoportal DANE](https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/) |
| **CIIU Rev. 4 A.C.** | Clasificación Industrial para Colombia — define qué significa cada `RAMA2D_R4` y `RAMA4D_R4` | [Clasificaciones DANE](https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/clasificaciones) |
| **Tablas correlativas** | Conversiones entre clasificaciones (CIIU↔CPC, CIIU↔CIUO) | [Tablas correlativas DANE](https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/tablas-correlativas) |
| **Nota metodológica de Informalidad** | Definición operativa de la 17ª CIET aplicada por el DANE | [Nueva medición de informalidad](https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/Nueva_medicion_informalidad.pdf) |

> 🛑 **Regla de oro:** cualquier indicador que produzca con esta librería **debe** validarse contra el boletín DANE más reciente antes de publicarse. La librería es una herramienta de cálculo, no una fuente oficial. Si una cifra suya difiere del boletín, **asuma que el problema está en su código o su consolidado** — no en el boletín.

### 4.3 Organización de archivos — carpeta `data/`

La estructura es **deliberadamente simple**. Crea una carpeta `data/` y coloca los ZIP tal como los descargaste, con el patrón `<Mes> <Año>.zip`:

```
mi_proyecto/
│
├── data/                          ← tu variable RUTA
│   ├── Enero 2025.zip             ← ZIP del DANE, SIN descomprimir
│   ├── Febrero 2025.zip
│   ├── Marzo 2025.zip
│   ├── Abril 2025.zip
│   ├── Mayo 2025.zip
│   ├── Junio 2025.zip
│   ├── Julio 2025.zip
│   ├── Agosto 2025.zip
│   ├── Septiembre 2025.zip
│   ├── Octubre 2025.zip
│   ├── Noviembre 2025.zip
│   └── Diciembre 2025.zip
│
└── mi_analisis.ipynb              ← tu notebook
```

> 📝 **Nombres exactos:** `Enero 2025.zip`, `Febrero 2025.zip`, … `Diciembre 2025.zip`. Mayúscula inicial, espacio, año, extensión `.zip`. Esta es la nomenclatura que el paquete busca, la cual es la misma que utiliza el DANE al momento de crear esta librería.
>

### 4.4 Verificar que todo está en orden

```python
from geih import ConsolidadorGEIH, ConfigGEIH

config = ConfigGEIH(anio=2025, n_meses=12)
cons   = ConsolidadorGEIH(ruta_base='data', config=config)
cons.verificar_estructura()
# ✅ Enero 2025.zip: 8 módulos — OK
# ✅ Febrero 2025.zip: 8 módulos — OK
# ...
# ❌ Abril 2025.zip: falta el módulo "Ocupados" — descarga incompleta
```

Si un ZIP falta, está corrupto, o le falta un módulo interno, el verificador lo indica exactamente. Úsalo siempre antes de consolidar — te ahorra horas de debugging.

---

## ⚡ 5. Inicio rápido — *Hola Mundo Laboral*

### 5.1 La versión ultra-corta — 3 líneas útiles (cuando ya consolidaste)

```python
from geih import ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH, IndicadoresLaborales

config = ConfigGEIH(anio=2025, n_meses=12)
geih   = ConsolidadorGEIH.cargar('data/GEIH_2025_Consolidado.parquet')
df     = PreparadorGEIH(config=config).preparar_base(geih)
r      = IndicadoresLaborales(config=config).calcular(df)
print(f"TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
# → TD=9.8%  TGP=63.4%  TO=57.2%
```

### 5.2 La versión completa — de los ZIP a los resultados

```python
from geih import (
    ConfigGEIH, ConsolidadorGEIH, PreparadorGEIH,
    IndicadoresLaborales, AnalisisSalarios, BrechaGenero, Exportador,
)
import os

# 1) Configurar el análisis
RUTA   = 'data'                                 # carpeta con los ZIP mensuales
config = ConfigGEIH(anio=2025, n_meses=12)
config.resumen()                                 # imprime SMMLV, período y ZIP esperados

# 2) Consolidar los ZIP del DANE (primera vez: ~5 min; luego instantáneo)
PARQUET = f'{RUTA}/GEIH_{config.anio}_Consolidado.parquet'
if os.path.exists(PARQUET):
    geih = ConsolidadorGEIH.cargar(PARQUET)      # recarga desde cache
else:
    cons = ConsolidadorGEIH(ruta_base=RUTA, config=config, incluir_area=True)
    cons.verificar_estructura()
    geih = cons.consolidar(checkpoint=True)      # retoma si Colab se desconecta
    cons.exportar(geih, PARQUET)                 # guarda para próximas corridas

# 3) Preparar el Data Mart analítico
prep = PreparadorGEIH(config=config)
df   = prep.preparar_base(geih)                  # ya deriva DOMINIO, RAMA, INFORMAL automáticamente

# 4) Calcular indicadores y validar contra DANE
ind = IndicadoresLaborales(config=config)
r   = ind.calcular(df)
ind.sanity_check(r, f"Anual {config.anio}")      # alerta si difiere del boletín

# 5) Exportar resultados con formato institucional
exp = Exportador(ruta_base=RUTA, config=config)
exp.guardar_tabla(ind.por_departamento(df), f'desempleo_dptos_{config.anio}')
print(f"✅ TD={r['TD_%']:.1f}%  TGP={r['TGP_%']:.1f}%  TO={r['TO_%']:.1f}%")
```

**Lo que acabas de hacer en 20 líneas:**

- Leíste 12 ZIP del DANE (~95 archivos CSV internos)
- Uniste 8 módulos con LEFT JOIN correcto sobre el ancla "Características generales"
- Aplicaste el factor de expansión ajustado (`FEX_ADJ = FEX_C18 / 12` para vista anual)
- Derivaste ~15 variables analíticas (dominio geográfico, rama CIIU legible, informalidad oficial)
- Calculaste 3 tasas con tolerancia de validación contra el boletín oficial
- Exportaste a Excel con formato institucional

Lo que en STATA o SAS tomaría semanas y cientos de líneas de código — aquí son minutos.

---

## 🧠 6. Conceptos clave que debes entender

Si es tu primera vez trabajando con la GEIH, estos 10 conceptos te ahorrarán muchos dolores de cabeza.

### 6.1 Factor de expansión (FEX)

**La idea fundamental de cualquier encuesta muestral.** Una fila del CSV **NO es una persona**; es **una persona que representa a muchas** en la población real.

**Analogía:** imagina que quieres saber cuántas personas en tu ciudad comen arroz. En lugar de preguntarle a 2 millones de personas (imposible), encuestas a 200. Pero si en tu muestra una mujer de 34 años representa el perfil de 10 000 mujeres de 34 años de la ciudad, su respuesta cuenta como **10 000 "votos"**, no uno.

El DANE entrega dos factores clave:

- `FEX_C18`: factor de expansión del DANE, calibrado contra proyecciones CNPV-2018.
- `FEX_ADJ`: versión **ajustada por la librería** según el período analizado (si son 12 meses, divide entre 12; si es trimestre, entre 3).

**Regla práctica:** siempre que sumes, promedies o cuentes, **multiplica por `FEX_ADJ`**. La librería lo hace automáticamente en todas sus clases.

### 6.2 PET, PEA, OCI, DSI, INA — el vocabulario del mercado laboral

| Sigla | Qué es | Condición técnica en la GEIH |
|---|---|---|
| **PET** | Población en Edad de Trabajar | 15 años o más |
| **PEA** | Población Económicamente Activa | PET que trabaja (OCI) o busca trabajo (DSI) |
| **OCI** | Ocupados | Trabajó ≥ 1 hora la semana pasada O tenía trabajo temporalmente ausente |
| **DSI** | Desocupados | No trabajó, buscó activamente, estaba disponible |
| **INA** | Inactivos | PET que ni trabaja ni busca (estudiantes, amas de casa, pensionados) |

**Las tres tasas fundamentales:**

```
TGP (Tasa Global de Participación) = PEA / PET          × 100   → "qué % de los en edad de trabajar participan"
TO  (Tasa de Ocupación)            = OCI / PET          × 100   → "qué % de los en edad de trabajar están empleados"
TD  (Tasa de Desempleo)            = DSI / PEA          × 100   → "qué % de los que quieren trabajar no lo encuentran"
```

### 6.3 SMMLV — Salario Mínimo Mensual Legal Vigente

Fijado por decreto cada diciembre, es la unidad natural para expresar ingresos laborales en Colombia. La librería lo lleva automáticamente por año:

| Año | SMMLV (COP) | Fuente legal |
|---|---|---|
| 2022 | $1.000.000 | Decreto 1724/2021 |
| 2023 | $1.160.000 | Decreto 2613/2022 |
| 2024 | $1.300.000 | Decreto 2292/2023 |
| 2025 | $1.423.500 | Decreto 1572/2024 |
| 2026 | $1.750.905 | Decreto 2426/2025 |

> 📌 **Actualizable sin release:** si el DANE publica un ajuste retroactivo o sale un nuevo año, puedes actualizar `geih_config.json` sin esperar una nueva versión en PyPI (§18).

### 6.4 CIIU — Clasificación Industrial Internacional Uniforme Rev. 4 A.C.

La CIIU responde la pregunta **"¿en qué sector trabaja esta persona?"**. La librería usa la adaptación colombiana (Rev. 4 A.C.) en dos niveles:

- **2 dígitos** → 88 divisiones (ej. `10` = Elaboración de productos alimenticios)
- **4 dígitos** → ~500 clases (ej. `1040` = Elaboración de productos lácteos)

También agrupa las 88 divisiones en las **13 ramas DANE** oficiales (Agricultura, Industrias manufactureras, Comercio, etc.) que ves en los boletines.

### 6.5 DIVIPOLA — códigos geográficos

| Nivel | Dígitos | Ejemplo |
|---|---|---|
| Departamento | 2 | `11` = Bogotá, `76` = Valle del Cauca |
| Municipio | 5 | `11001` = Bogotá D.C., `76001` = Cali |
| AREA | 5 | Variable del módulo Ocupados, para 32 ciudades y AM |

### 6.6 Dominio geográfico

La GEIH publica cifras en 4 dominios mutuamente excluyentes:

- `13_AM` — 13 áreas metropolitanas principales (Bogotá, Medellín, Cali, Barranquilla AM, Bucaramanga AM, …)
- `10_ciudades` — 10 ciudades intermedias adicionales
- `otras_cab` — resto de cabeceras municipales del país
- `rural` — centros poblados y rural disperso

La librería construye esta clasificación automáticamente en la columna `DOMINIO`.

### 6.7 CISE-93 — posición ocupacional

La GEIH clasifica a los ocupados según la **Clasificación Internacional de la Situación en el Empleo (CISE-93)**:

| Código | Categoría |
|---|---|
| 1 | Empleado particular |
| 2 | Empleado del gobierno |
| 3 | Empleado doméstico |
| 4 | Cuenta propia |
| 5 | Patrón o empleador |
| 6 | Trabajador familiar sin remuneración |
| **7** | **Jornalero o peón** ← crítico |
| 8 | Trabajador sin remuneración en otras empresas |
| 9 | Otro |

### 6.8 17ª CIET — definición oficial de informalidad

El DANE adoptó en 2023 la definición de la **17ª Conferencia Internacional de Estadísticos del Trabajo**, que combina dos dimensiones:

- **Sector formal/informal** (naturaleza de la unidad productiva): tamaño, registro, contabilidad.
- **Empleo formal/informal** (naturaleza del puesto): contrato, seguridad social.

Es **más restrictiva** que la definición anterior (PILA + tamaño empresa). La librería implementa la versión oficial usando `P6430` (posición), `P6870` (tamaño), `P6920` (cotización pensional) y otras variables, con una **traducción literal del código SAS oficial del DANE** (§14).

### 6.9 Coeficiente de Variación (CV) y DEFF

El **CV** es la medida estándar para decir "¿qué tan confiable es esta cifra?". En una encuesta muestral:

```
CV (%) = [Error Estándar / Estimación] × 100
```

Menor CV = mayor precisión. La clasificación oficial DANE:

| CV | Semáforo | Uso recomendado |
|---|---|---|
| < 7 % | ✅ **Precisión alta** | Publicable sin reservas |
| 7–15 % | ⚠️ **Aceptable** | Publicable con nota metodológica |
| 15–20 % | ⚠️⚠️ **Baja** | Solo con caveat explícito |
| > 20 % | ❌ **No confiable** | No publicar |

El **DEFF (Design Effect)** es el multiplicador que corrige la varianza por el hecho de que la GEIH usa muestreo estratificado por conglomerados — no MAS simple. Para la GEIH, DEFF típico ≈ 2.5.

### 6.10 Data Lake vs. Data Mart

La librería separa explícitamente dos conceptos:

- **Data Lake** (`ConsolidadorGEIH`): universo completo de ~515 columnas × ~5M filas. Se guarda una vez al año como Parquet. Útil para análisis no previstos.
- **Data Mart** (`PreparadorGEIH`): subconjunto analítico de ~70 columnas derivadas y tipadas. Es lo que consumen todas las clases de análisis.

**Analogía:** el Data Lake es tu **bodega completa**; el Data Mart es tu **mostrador**. Mismo origen, dos propósitos.

---

## 🏗️ 7. Arquitectura y flujo de trabajo

### 7.1 El pipeline de cinco etapas

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FLUJO END-TO-END                            │
└─────────────────────────────────────────────────────────────────────┘

   1. data/Enero 2025.zip, Febrero 2025.zip, ..., Diciembre 2025.zip
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ConsolidadorGEIH                                                   │
│  • Lee los ZIP directamente a RAM (sin descomprimir)                │
│  • Para cada mes: LEFT JOIN de los 8 módulos sobre ancla            │
│                    "Características generales"                      │
│  • Concatena los 12 meses                                           │
│  • Guarda el Data Lake (~515 col × ~815.000 filas x año) en Parquet │
│  • Soporta checkpoint: retoma si Colab se desconecta                │
│  • Soporta append_mes(): agrega mes nuevo sin reconsolidar          │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
   2. data/GEIH_2025_Consolidado.parquet   (Data Lake — universo completo)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PreparadorGEIH                                                     │
│  • Filtra a columnas analíticas (Data Mart, ~70 col)                │
│  • Calcula FEX_ADJ según el período configurado                     │
│  • Deriva variables (DOMINIO, RAMA, SEXO, INFORMAL, NIVEL_EDU, ...) │
│  • Mapea códigos a etiquetas legibles                               │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
   3. df  (DataFrame analítico listo para usar)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Clases de análisis  (~80 disponibles, ver §8)                      │
│  • IndicadoresLaborales  (TD, TGP, TO)                              │
│  • AnalisisSalarios, BrechaGenero, IndicesCompuestos (Gini)         │
│  • EcuacionMincer, CalidadEmpleo (ICE), Competitividad (ICI)        │
│  • AnalisisDepartamental, OcupadosDptoRama, AnalisisOcupadosCiudad  │
│  • AnalisisTierraAgropecuario, AnalisisMigracion, ...               │
│  • ReplicadorInformalidad, ReplicadorSeguridadSocial (boletín DANE) │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
   4. Tablas y gráficos en memoria (pandas DataFrames, matplotlib/plotly figs)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Exportador                                                         │
│  • CSV + XLSX con formato institucional (colores, bordes, anchos)   │
│  • Gráficos PNG de alta resolución                                  │
│  • Excel multi-hoja para reportes departamentales o sectoriales     │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
   5. resultados_geih_2025/
        ├── tablas/    (CSV para Power BI / Tableau)
        ├── graficas/  (PNG para PPT / PDF)
        └── excel/     (XLSX institucional para Comité)
```

### 7.2 El parámetro que controla todo: `ConfigGEIH`

`ConfigGEIH` es un `dataclass` que concentra toda la configuración del análisis. Cambia solo esto y el resto del pipeline se ajusta automáticamente:

```python
# Año completo — 12 meses
ConfigGEIH(anio=2025, n_meses=12)

# Primer trimestre
ConfigGEIH(anio=2026, n_meses=3)

# Solo enero
ConfigGEIH(anio=2026, n_meses=1)

# Primer semestre (los 6 primeros meses)
ConfigGEIH(anio=2025, n_meses=12, meses_rango=[1, 2, 3, 4, 5, 6])

# Solo diciembre (vista del mes específico)
ConfigGEIH(anio=2025, n_meses=12, meses_rango=[12])

# Trimestre no contiguo (ej. Octubre + Diciembre — análisis ad hoc)
ConfigGEIH(anio=2025, n_meses=12, meses_rango=[10, 12])
```

`ConfigGEIH` automáticamente:

- Selecciona el SMMLV correcto del año.
- Genera la lista de ZIP esperados.
- Calcula el divisor del factor de expansión (`FEX_ADJ = FEX_C18 / len(meses_rango)` para vista promedio anual).
- Carga referencias DANE si están en `geih_config.json`.

---

## 📊 8. Catálogo completo de análisis

La librería expone ~80 clases de análisis organizadas por familia temática. Esta es la tabla completa de lo que puedes calcular.

### 8.1 Indicadores fundamentales del mercado laboral

| Clase | Qué produce | Unidad |
|---|---|---|
| `IndicadoresLaborales` | TD, TGP, TO — nacional y por departamento, con campos `_raw` sin redondear para validación estricta | % |
| `AnalisisSalarios` | Mediana, media, percentiles p10/p25/p75/p90 por rama, edad, nivel educativo | COP y SMMLV |
| `BrechaGenero` | Diferencia salarial H/M por nivel educativo | % |
| `DistribucionIngresos` | Distribución de ocupados por rangos de SMMLV (0–1, 1–2, 2–4, 4+) | % |
| `IndicesCompuestos` | Coeficiente de Gini del ingreso laboral, curva de Lorenz | [0, 1] |
| `AnalisisRamaSexo` | Composición del empleo por rama CIIU × sexo | miles y % |
| `AnalisisArea` | Indicadores por 13 áreas metropolitanas principales (dominio `13_AM`) | varias |
| `AnalisisCruzado` | Cruce libre entre cualquier par de dimensiones (edad × rama, sexo × nivel, etc.) | varias |

### 8.2 Índices compuestos y análisis avanzado

| Clase | Índice | Lo que mide |
|---|---|---|
| `CalidadEmpleo` | **ICE** | Agregado de pensión + salud + horas + salario sobre ocupados |
| `CompetitividadLaboral` | **ICI** | Ranking departamental de competitividad del mercado laboral |
| `VulnerabilidadLaboral` | **IVI** | Vulnerabilidad por rama (informalidad + bajo salario + sin prestaciones) |
| `MapaTalento` | **ITAT** | Oferta, costo y calidad del talento por departamento |
| `FormalidadSectorial` | **ICF** | Índice de formalidad por sector económico CIIU |
| `EcuacionMincer` | β Mincer | Retorno salarial por año de educación (OLS ponderado) |
| `Estacionalidad` | Series | Variación mensual de TD, TGP, TO |
| `FuerzaLaboralJoven` | Juvenil | Indicadores para personas de 15–28 años |
| `CostoLaboral` | Costo total | Salario + 54 % de carga prestacional (pensión + salud + cesantías + prima + vacaciones + parafiscales) |
| `ProductividadTamano` | PIB/ocupado | Productividad aproximada por tamaño de empresa |
| `ContribucionSectorial` | Aporte | Contribución de cada sector al empleo total |
| `AnalisisHoras` | Horas | Distribución de horas trabajadas, sobreempleo horario |
| `AnalisisSubempleo` | Subempleo | Subempleo subjetivo y objetivo |
| `AnalisisFFT` | FFT | Fuerza de trabajo potencial (extendida) |
| `AnalisisUrbanoRural` | Brecha | Brecha cabecera vs. resto |
| `BonoDemografico` | Bono | Ventana de oportunidad demográfica |
| `EtnicoRacial` | Composición | Empleo por autorreconocimiento étnico |
| `ProxyBilinguismo` | Bilingüismo | Proxy vía variable P3041 (idiomas) |
| `AnalisisFFT` | Fuerza de trabajo | Trabajadores potenciales fuera de la PEA |

### 8.3 Poblaciones especiales y análisis complementarios

| Clase | Foco |
|---|---|
| `AnalisisCampesino` | Autorreconocimiento campesino (variable oficial desde 2023) |
| `AnalisisDiscapacidad` | Grupo de Washington de Naciones Unidas |
| `AnalisisMigracion` | Migración interna y externa |
| `AnalisisSobrecalificacion` | Trabajadores con educación por encima del puesto |
| `AnalisisContractual` | Tipo de contrato (indefinido, fijo, OPS, sin contrato) |
| `AnalisisAutonomia` | Trabajadores por cuenta propia y autoempleo |
| `DuracionDesempleo` | Tiempo en desempleo, desempleados de larga duración |
| `DashboardSectoresProColombia` | Reporte integral por sectores de interés de ProColombia |
| `AnatomaSalario` | Descomposición del salario (básico + extras + primas) |
| `FormaPago` | Forma de pago (efectivo, transferencia, especie) |
| `CanalEmpleo` | Cómo consiguió el empleo el ocupado (familia, internet, agencia, etc.) |

### 8.4 Análisis geográficos

| Clase | Granularidad |
|---|---|
| `AnalisisDepartamental` | 33 entidades territoriales (32 dptos + Bogotá D.C.), con precisión muestral |
| `AnalisisOcupadosCiudad` | 32 ciudades y áreas metropolitanas — 6 tablas + 3 gráficos + Excel multi-hoja |
| `OcupadosDptoRama` | Departamento × Rama CIIU (2 o 4 dígitos) — con CV y clasificación DANE |

### 8.5 Análisis sectoriales especializados

| Clase | Sector |
|---|---|
| `AnalisisTierraAgropecuario` | Tenencia de tierra (P3064), renta agraria (P3064S1), tipo de actividad (P3056), CIIU agrícola a 4 dígitos |
| `Top20Sectores` | Ranking de las 20 ramas CIIU con mayor ocupación |

### 8.6 Multi-año

| Clase | Uso |
|---|---|
| `ComparadorMultiAnio` | Comparación de indicadores a través de varios años (evolución interanual, variación absoluta y relativa) |

### 8.7 Replicación oficial DANE

Clases que implementan **traducción literal** de metodologías oficiales para validación cruzada:

| Clase | Replica |
|---|---|
| `ReplicadorInformalidad` | 6 hojas del anexo Excel de informalidad del boletín (pág. 42) — 17ª CIET |
| `ReplicadorSeguridadSocial` | Hojas de seguridad social del anexo Excel |
| `clasificar_informalidad_dane()` | Función pura que implementa el algoritmo SAS oficial |

### 8.8 Herramientas auxiliares

| Clase / función | Uso |
|---|---|
| `DiagnosticoCalidad` | Valores faltantes, ceros sospechosos, tipos incorrectos, columnas duplicadas |
| `MergeCorrelativas` | Agrega `DESCRIPCION_CIIU` y nombres de departamento/municipio desde Excel externos |
| `EstadisticasPonderadas` | Media, mediana, cuantiles ponderados por FEX (evita reinventar la rueda) |
| `GestorMemoria` | Reporta uso de RAM durante el pipeline (útil en Colab) |
| `ConversorTipos` | Conversión robusta de tipos (int, float, category) respetando nulos del DANE |
| `DescargadorDANE` | Helper para organizar ZIP recién descargados |
| `PerfilMemoria`, `medir_tiempo` | Profiling de pipelines largos |

---

## 👤 9. Ejemplos por perfil de usuario

### 9.1 🎓 Para estudiantes — Brecha salarial de género por educación

*¿Ganan lo mismo hombres y mujeres con el mismo nivel educativo? Respuesta en 4 líneas.*

```python
from geih import BrechaGenero

brecha = BrechaGenero(config=config).calcular(df)
print(brecha)
```

**Salida esperada** (cifras ilustrativas - No reales):

| Nivel educativo | Hombres (mediana COP) | Mujeres (mediana COP) | Brecha (%) |
|---|---:|---:|---:|
| 4. Media | $1.400.000 | $1.100.000 | −21.4 % |
| 6. Universitaria | $3.200.000 | $2.750.000 | −14.0 % |
| 7. Posgrado | $6.500.000 | $5.800.000 | −10.7 % |

### 9.2 🔬 Para investigadores — Ecuación de Mincer + Gini nacional

*Retorno salarial por cada año extra de educación y desigualdad del ingreso laboral.*

```python
from geih import EcuacionMincer, IndicesCompuestos

# ln(W) = β0 + β1·Educ + β2·Exp + β3·Exp² — OLS ponderado por FEX
mincer = EcuacionMincer(config=config).estimar_todos(df)
print(mincer[['Grupo', 'beta_educacion', 'se_educacion', 'R2', 'n']])
# → β1 ≈ 0.08-0.12 en Colombia: cada año extra de educación aumenta el salario ~8-12 %

# Coeficiente de Gini nacional del ingreso laboral
gini = IndicesCompuestos(config=config).gini(df)
print(f"Gini laboral nacional: {gini:.3f}")
# → ~0.48 típicamente — uno de los más altos de la OCDE
```

### 9.3 🏛️ Para gobierno — Reporte departamental con rigor muestral

*Reporte integral listo para publicar, con evaluación de confiabilidad en cada celda.*

```python
from geih import AnalisisDepartamental, Exportador

reporte = AnalisisDepartamental(config=config).calcular(df)

# Filtrar solo cifras publicables
publicables = reporte[reporte['Clasificacion'].isin(['✅ Precisión alta', '⚠️ Aceptable'])]

print(f"De 33 entidades, {len(publicables)} tienen cifras publicables.")
print(f"Dptos no publicables (muestra insuficiente): {set(reporte['Departamento']) - set(publicables['Departamento'])}")

# Exportar a Excel institucional
Exportador(ruta_base='salida', config=config).guardar_excel(
    {'Departamentos': reporte},
    f'Reporte_Departamental_{config.anio}'
)
```

> ⚠️ **Dptos típicamente con CV > 20 % en vista mensual:** Amazonas, Vichada, Vaupés, Guainía, San Andrés. Requieren agregación anual o trimestral para ser publicables.

### 9.4 🌱 Para sector agropecuario — Ingresos por tenencia de tierra

*¿Cuánto gana un campesino propietario vs. uno arrendatario vs. un jornalero?*

```python
from geih import AnalisisTierraAgropecuario

tierra   = AnalisisTierraAgropecuario(config=config)
reporte  = tierra.reporte_completo(df)

# El reporte incluye:
# - Brecha de ingresos propietario vs no propietario
# - Costo de oportunidad (ingreso laboral vs renta estimada del predio)
# - Distribución por género en actividades agropecuarias
# - Formalidad agropecuaria por tipo de actividad
# - CIIU a 4 dígitos (Agricultura, Silvicultura, Pesca)
# - Desagregación departamental con evaluación de confiabilidad

tierra.exportar_excel(reporte, f"tierras_{config.anio}.xlsx")
```

### 9.5 💼 Para empresas — Mapa de talento y costos laborales por región

*¿Dónde abrir una nueva planta considerando disponibilidad de talento, salarios y formalidad?*

```python
from geih import MapaTalento, CostoLaboral, CompetitividadLaboral

mapa = MapaTalento(config=config).calcular(df)
# → ranking departamental por: oferta de talento, costo promedio, formalidad, bilingüismo

costo = CostoLaboral(config=config).calcular(df)
# → salario bruto + carga prestacional (~54 %) — costo real para el empleador

ici = CompetitividadLaboral(config=config).calcular(df)
# → índice compuesto de competitividad laboral por departamento
```

### 9.6 📰 Para periodistas — 5 cifras rápidas para una nota de día

```python
from geih import IndicadoresLaborales, DuracionDesempleo, FuerzaLaboralJoven

ind = IndicadoresLaborales(config=config).calcular(df)
juv = FuerzaLaboralJoven(config=config).calcular(df)
dur = DuracionDesempleo(config=config).calcular(df)

print(f"📌 TD nacional: {ind['TD_%']:.1f} %")
print(f"📌 TD juvenil (15-28): {juv['TD_juvenil_%']:.1f} %")
print(f"📌 TD mujeres: {ind['TD_Mujeres_%']:.1f} %")
print(f"📌 Duración promedio del desempleo: {dur['mediana_semanas']:.0f} semanas")
print(f"📌 % de desempleados de larga duración (>1 año): {dur['pct_larga_duracion']:.1f} %")
```

---

## 🗺️ 10. Análisis departamental × rama CIIU

Replica la metodología oficial del DANE para estimar ocupados por Departamento (DIVIPOLA) × Rama CIIU Rev. 4 adaptada:

- **2 dígitos** → 88 divisiones
- **4 dígitos** → ~500 clases

```python
from geih import OcupadosDptoRama

odr = OcupadosDptoRama(config=config)

tabla_2d = odr.calcular(df, nivel="2d")   # 88 divisiones
tabla_4d = odr.calcular(df, nivel="4d")   # ~500 clases

odr.exportar_excel(tabla_2d, f"ocupados_dpto_rama_2d_{config.anio}.xlsx")
```

### Metodología implementada

Para cada mes y celda `(DPTO, rama)`:

1. Total expandido: `T_m = Σ FEX_C18`
2. Conteo muestral: `n_m`
3. Promedio anual = media de los 12 totales mensuales reponderada por meses con dato

La varianza bajo diseño complejo se estima con:

```
Var(p̂) ≈ DEFF × p(1 − p) / n_base
```

donde `n_base` es el tamaño muestral del **departamento** (no de la celda), porque todos los registros del dominio contribuyen a estimar la proporción. Referencias: Cochran (1977), Kish (1965).

Cada celda del output lleva su clasificación DANE (`✅ Alta / ⚠️ Aceptable / ⚠️⚠️ Baja / ❌ No confiable`) y el IC al 95 %.

---

## 🏙️ 11. Análisis por 32 ciudades y áreas metropolitanas

```python
from geih import AnalisisOcupadosCiudad

area   = AnalisisOcupadosCiudad(config=config)
tablas = area.calcular(df)              # dict de 6 tablas
area.imprimir(tablas)
area.exportar_excel(tablas, f"CIIU_Area_{config.anio}.xlsx")
```

**6 tablas producidas:**

1. Total nacional (baseline para comparación)
2. Agrupación DANE (las 13 ramas oficiales)
3. Dominio geográfico (13_AM, 10_ciudades, otras_cab, rural)
4. Ciudad / Área metropolitana (32 unidades)
5. Granular CIIU × ciudad
6. CIIU nacional (para contrastar mezcla sectorial)

**3 gráficos** producidos: barras por agrupación, barras por ciudades, heatmap rama × ciudad.

Usa la variable `AREA` (DIVIPOLA de 5 dígitos del módulo Ocupados) para identificar:

- 13 ciudades principales del boletín
- 10 áreas intermedias adicionales
- 9 ciudades complementarias (total 32)

---

## 🌾 12. Análisis de tierras agropecuarias

```python
from geih import AnalisisTierraAgropecuario

tierra  = AnalisisTierraAgropecuario(config=config)
reporte = tierra.reporte_completo(df)
tierra.exportar_excel(reporte, f"tierras_{config.anio}.xlsx")
```

Explota las variables:

- `P3064` → tenencia de la tierra (propia, arrendada, prestada, jornal)
- `P3064S1` → renta agraria estimada
- `P3056` → tipo de actividad agropecuaria

**Produce:**

- Brecha de ingresos propietario vs. no propietario
- Costo de oportunidad: ingreso laboral vs. renta de la tierra
- Distribución por género en actividades agropecuarias
- Formalidad agropecuaria (usualmente la más baja del país, ~85 %)
- CIIU a 4 dígitos: Agricultura (`01XX`), Silvicultura (`02XX`), Pesca (`03XX`)
- Desagregación departamental con evaluación de confiabilidad en cada celda

---

## ✅ 13. Verificación contra el Boletín DANE

> Esta sección documenta el **flujo obligatorio** para validar que sus cálculos reproducen el Boletín DANE oficial dentro de tolerancia estricta. **No omitir.**

### 13.1 Por qué es obligatorio validar

La librería implementa cientos de operaciones sobre microdatos complejos. Aunque la suite de tests garantiza que los cálculos son **matemáticamente correctos contra cifras hardcoded del boletín**, su consolidado puede tener problemas que la librería no puede detectar:

- Meses faltantes en el ZIP
- Factores de expansión corruptos
- Columnas renombradas por el DANE en una actualización menor
- Joins mal hechos en el consolidado
- Errores de descarga silenciosa (archivos truncados)

**La única defensa real es validar el resultado final contra el boletín publicado por el DANE para el mismo período.**

### 13.2 El flujo de 5 pasos

1. **Descargue el boletín mensual del DANE** para el período analizado (PDF + anexo Excel). El anexo Excel es la fuente-de-verdad: el PDF redondea a 1 decimal.
2. **Identifique 5–10 cifras de control** — típicamente: TD nacional, TGP nacional, ocupados totales, ocupados por dominio (13_AM, rural), tasas por sexo. Estas son sus **canarios**.
3. **Calcule las mismas cifras** usando `IndicadoresLaborales.calcular()` con los campos `_raw` (sin redondear).
4. **Compare con tolerancia estricta** — ±0.05 p.p. para tasas, ±1 mil para poblaciones.
5. **Si todo cuadra**, su consolidado es confiable. Si no cuadra, **no avance** hasta entender por qué.

### 13.3 Plantilla de verificación

```python
from geih import ConfigGEIH, PreparadorGEIH, IndicadoresLaborales

# Vista de diciembre
cfg = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[12])
df_dic = PreparadorGEIH(cfg).preparar_base(geih_raw)

r = IndicadoresLaborales().calcular(df_dic)

# Cifras del Boletín DANE (del anexo Excel, NO del PDF redondeado)
# ⚠️ Actualice estas cifras contrastando con el boletín del período que analiza
TOLERANCIA_PP = 0.05
referencias = {
    'TD_raw':  8.0,
    'TGP_raw': 64.3,
    'TO_raw':  59.2,
}
for clave, ref in referencias.items():
    diff = abs(r[clave] - ref)
    estado = '✅' if diff <= TOLERANCIA_PP else '❌'
    print(f'{estado} {clave}: {r[clave]:.4f}  (DANE: {ref}  Δ={diff:.4f})')

# Sanity check ácido: PET expandido debe estar ~40.9 M en CUALQUIER vista
# Es el canario más sensible: detecta divisores FEX mal aplicados
pet_M = df_dic.loc[df_dic['PET'] == 1, 'FEX_ADJ'].sum() / 1e6
assert 40.5 < pet_M < 41.3, f'PET = {pet_M:.2f}M fuera de rango — divisor FEX mal'
```

### 13.4 Tests canario automatizados

El paquete incluye `tests/test_canarios_boletin.py` — una batería de tests organizados por familia de indicador que validan **end-to-end** la replicación del boletín:

- Divisor FEX en 3 vistas temporales (anual, trimestral, mensual)
- Tasas TD / TGP / TO
- Brecha por sexo
- Dominio geográfico (incluye regresión específica: "`'13_AM' → 0 filas`")
- Ramas CIIU — las 13 agrupaciones DANE
- Posición ocupacional (incluye regresión: "jornalero = código 7, no 8")
- Informalidad 17ª CIET
- Exposición de valores `_raw` vs. `_%`

```bash
# Correr los canarios contra su consolidado local
GEIH_TEST_DATA=/ruta/a/su/consolidado/ pytest tests/test_canarios_boletin.py -v
```

Si la variable de entorno no está definida, los tests se **skipean limpiamente** — no falla la suite por falta de datos. Esto permite incluirlos en CI sin subir microdatos al repositorio.

### 13.5 Tolerancias recomendadas

| Tipo de indicador | Tolerancia | Justificación |
|---|---|---|
| Tasas (TD, TGP, TO, informalidad) | **±0.05 p.p.** | Mitad del último decimal publicado por DANE |
| Poblaciones (miles) | **±1 mil** | Precisión declarada del anexo Excel |
| Ingresos (pesos / mes) | **±500 COP** | ~0.05 % del SMMLV |
| Informalidad rural | **±0.5 p.p.** | La definición oficial usa registro mercantil que la librería no replica sin metadato externo |
| Cifras desestacionalizadas (STL) | **±0.3 p.p.** | DANE usa X-13-ARIMA con calendario laboral colombiano no reproducible exactamente |

---

## 🛡️ 14. Replicación oficial — Informalidad (17ª CIET)

Calcular la informalidad **no** es solo ver si alguien paga salud y pensión. La metodología oficial del DANE cruza:

- **Sector** (naturaleza de la unidad productiva): tamaño de la empresa, registro mercantil, contabilidad
- **Ocupación** (naturaleza del puesto): tipo de contrato, pagos de seguridad social

La librería `geih-analisis` contiene una **traducción literal del código SAS oficial del DANE** que implementa el algoritmo 17ª CIET:

```python
from geih import clasificar_informalidad_dane

# Aplica la función sobre el DataFrame preparado
df['INFORMAL'] = clasificar_informalidad_dane(df)
# 0 = Formal, 1 = Informal

# Tasa nacional expandida
ocupados_mask = df['OCI'] == 1
tasa = df.loc[ocupados_mask & (df['INFORMAL'] == 1), 'FEX_ADJ'].sum() / \
       df.loc[ocupados_mask, 'FEX_ADJ'].sum()
print(f"Tasa de informalidad nacional: {tasa * 100:.1f} %")
```

Para replicar hoja por hoja el **anexo Excel de informalidad** del boletín DANE:

```python
from geih import ReplicadorInformalidad, HOJAS_INFORMALIDAD

rep = ReplicadorInformalidad(df, config=config)
resultado = rep.replicar_todas_las_hojas()

# Cada hoja viene con comparación celda-a-celda contra el Excel oficial
for hoja, resumen in resultado.items():
    print(f"{hoja}: {resumen.celdas_correctas}/{resumen.celdas_totales} ✅")
```

---

## 📏 15. Precisión muestral — cómo saber si puedes publicar

Esta es una de las contribuciones más valiosas de la librería: **integra la evaluación de confiabilidad en cada cifra que produce**.

### 15.1 Evaluar una proporción arbitraria

```python
from geih import evaluar_proporcion

p = evaluar_proporcion(
    proporcion=0.089,           # la cifra que calculaste (ej. TD = 8.9%)
    n_registros=50_000,          # tamaño muestral del dominio
    n_expandido=26_000_000,      # PET o PEA expandida del dominio
    dominio="Nacional",
)
print(p.resumen())
# Nacional  Est=8.90  EE=0.20  CV=2.3%  IC=[8.51, 9.29]  ✅ Precisión alta
```

### 15.2 Evaluar una media (ej. ingreso laboral mediano)

```python
from geih import evaluar_media

evaluar_media(
    media=2_100_000,             # la media calculada
    desv_est=1_450_000,
    n_registros=38_000,
    n_expandido=22_000_000,
    dominio="Ocupados",
).resumen()
# Ocupados  Est=2100000  EE=7400  CV=0.4%  IC=[$2.086M, $2.115M]  ✅ Precisión alta
```

### 15.3 Evaluar un total expandido

```python
from geih import evaluar_total

evaluar_total(
    total=24_500_000,            # ocupados totales
    n_registros=50_000,
    n_expandido=26_000_000,
    dominio="Ocupados",
).resumen()
```

### 15.4 Clasificación directa a partir de un CV

```python
from geih import clasificar_precision

print(clasificar_precision(cv_pct=8.3))   # → "⚠️ Precisión aceptable"
print(clasificar_precision(cv_pct=3.2))   # → "✅ Precisión alta"
print(clasificar_precision(cv_pct=22.1))  # → "❌ No confiable"
```

### 15.5 Tabla de referencia rápida

| CV | Semáforo DANE | ¿Puedo publicar? |
|---|---|---|
| < 7 % | ✅ Precisión alta | Sí, sin reservas |
| 7–15 % | ⚠️ Aceptable | Sí, con nota metodológica |
| 15–20 % | ⚠️⚠️ Baja | Solo como referencia / con caveat explícito |
| > 20 % | ❌ No confiable | **No publicar** — agregue el período o zoom out geográfico |

Las clases `AnalisisDepartamental`, `OcupadosDptoRama`, `AnalisisOcupadosCiudad` y `AnalisisTierraAgropecuario` **integran esta evaluación en cada fila del output** — no tienes que llamarla manualmente.

---

## 📉 16. Desestacionalización de series

El módulo `geih.estacional` permite reproducir la sección **"TD desestacionalizada"** del Boletín DANE (página 25 típica), que separa la tendencia de los efectos estacionales en la serie mensual.

### 16.1 ¿Por qué desestacionalizar?

La TD cruda mensual tiene patrones estacionales fuertes: pico en enero (fin de contratos navideños), valle en noviembre (alta contratación pre-navideña). Comparar `TD(noviembre)` con `TD(enero)` directamente lleva a conclusiones erróneas. La serie desestacionalizada permite ver **la tendencia subyacente**.

### 16.2 Uso básico

```python
from geih.estacional import desestacionalizar_td_mensual
import pandas as pd

# STL requiere ≥ 24 meses → usar histórico del año anterior
td_anio_previo = pd.Series(
    [12.1, 11.5, 11.3, 10.6, 10.3, 10.3, 10.0, 9.8, 9.1, 8.4, 8.2, 9.1],
    index=pd.period_range('2024-01', '2024-12', freq='M').to_timestamp(),
)

resultado = desestacionalizar_td_mensual(
    df_anual,
    anio=2025,
    incluir_historico=td_anio_previo,
)
print(resultado.tail(3))
#             td_cruda  td_desest
# 2025-10-01      7.20       7.51
# 2025-11-01      7.00       7.43
# 2025-12-01      8.00       7.62
```

### 16.3 Limitación importante

El método por defecto es **STL (Seasonal-Trend LOESS)**, disponible vía `statsmodels`. El DANE internamente usa **X-13-ARIMA-SEATS** con calendario laboral colombiano (días hábiles, Semana Santa, festivos), parámetros que la librería no expone. **Esperar diferencias de ±0.1 a ±0.3 p.p.** entre la curva de la librería y la del DANE. La forma general (tendencia, picos, valles) sí es reproducible.

---

## 🖥️ 17. Dashboard interactivo (Streamlit)

Si tienes los Parquet consolidados pero quieres que alguien de tu equipo explore los datos sin programar, la librería incluye una aplicación web.

```bash
pip install "geih-analisis[dashboard]"
python -m geih.dashboard ruta/a/tu/carpeta/data
```

O desde Python:

```python
from geih import ejecutar_dashboard
ejecutar_dashboard(ruta_base="data", puerto=8501)
# 🌐 Dashboard disponible en http://localhost:8501
```

Se abre una pestaña en el navegador con:

- Filtros por año, mes, departamento, sexo, rama
- Histogramas de ingresos
- Mapa de desempleo por departamento
- Tablas descargables a Excel
- Gráficos de brecha de género y Gini

---

## ⚙️ 18. Configuración avanzada

### 18.1 `geih_config.json` — actualizar sin esperar un release

Crea un archivo `geih_config.json` en tu directorio de trabajo:

```json
{
  "smmlv_por_anio": {
    "2027": 1900000
  },
  "ref_dane": {
    "2026": { "td_anual_pct": 9.2, "tgp_anual_pct": 64.0, "to_anual_pct": 58.0 }
  },
  "muestreo": {
    "deff_default": 2.5,
    "cv_preciso_pct": 7.0,
    "cv_aceptable_pct": 15.0,
    "cv_bajo_pct": 20.0
  },
  "carga_prestacional": 0.54
}
```

**Orden de búsqueda:**

1. Ruta explícita pasada en código
2. Variable de entorno `GEIH_CONFIG_PATH`
3. `./geih_config.json` (cwd)
4. `~/.geih/geih_config.json` (home del usuario)

### 18.2 Agregar columnas personalizadas

Por defecto, la librería extrae unas 70 columnas clave. Si necesitas una variable específica (ej. `P7140S2` — razón para querer cambiar de trabajo) sin modificar el código fuente:

```python
df = PreparadorGEIH(config=config).preparar_base(
    geih_raw,
    columnas_extra=["P7140S2", "P6500S2"]   # Principio Abierto / Cerrado
)
```

### 18.3 Analizar un subconjunto de meses

```python
# Solo primer semestre
config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[1, 2, 3, 4, 5, 6])

# Solo diciembre (para replicar boletín mensual)
config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[12])

# Trimestre octubre-diciembre
config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[10, 11, 12])

# Meses no contiguos (análisis ad hoc)
config = ConfigGEIH(anio=2025, n_meses=12, meses_rango=[3, 6, 9, 12])
```

El divisor del factor de expansión se ajusta automáticamente al número de meses del `meses_rango`.

### 18.4 Agregar un mes nuevo sin reconsolidar

Cuando el DANE publica un nuevo mes:

```python
from geih import ConsolidadorGEIH

# Si ya tienes GEIH_2025_Consolidado.parquet y descargaste Enero 2026.zip
ConsolidadorGEIH.append_mes(
    parquet_existente='data/GEIH_2025_Consolidado.parquet',
    zip_nuevo='data/Enero 2026.zip',
    parquet_salida='data/GEIH_2025_2026M01_Consolidado.parquet',
)
```

---

## 🧰 19. Herramientas auxiliares

### 19.1 Diagnóstico de calidad de la base

```python
from geih import DiagnosticoCalidad

diag  = DiagnosticoCalidad()
tabla = diag.valores_faltantes(geih, titulo="Base 2025", umbral_pct=1.0)
diag.verificar_tipos(geih)
diag.columnas_duplicadas(geih)
```

### 19.2 Merge con correlativas (etiquetas legibles)

```python
from geih import MergeCorrelativas

merger = MergeCorrelativas()
df = merger.merge_ciiu(df, ruta_ciiu="correlativas/CIIU_Rev4_Col.xlsx",
                      sheet_name="CIIU 2022")
df = merger.merge_divipola(df, ruta_divipola="correlativas/DIVIPOLA.xlsx")
```

Agrega `DESCRIPCION_CIIU` y nombres legibles de departamento/municipio a partir de archivos Excel externos.

### 19.3 Estadísticas ponderadas manuales

```python
from geih.utils import EstadisticasPonderadas as EP

# Todas estas funciones respetan el factor de expansión
mediana  = EP.mediana(df['INGLABO'], df['FEX_ADJ'])
media    = EP.media(df['INGLABO'], df['FEX_ADJ'])
p90      = EP.cuantil(df['INGLABO'], df['FEX_ADJ'], q=0.90)
desv_est = EP.desv_est(df['INGLABO'], df['FEX_ADJ'])
```

### 19.4 Logging estructurado

```python
from geih.logger import configurar_logging, get_logger

configurar_logging(nivel="INFO", archivo="logs/geih_2025.log")
log = get_logger("mi_analisis")
log.info("Inicio del pipeline")
```

### 19.5 Exportador unificado

```python
from geih import Exportador

exp = Exportador(ruta_base="data", config=config)
exp.guardar_tabla(td_dpto, "desempleo_dptos_2025")       # CSV + XLSX
exp.guardar_grafico(fig, "td_por_rama")                   # PNG alta res
exp.guardar_excel({'Dptos': df1, 'Ramas': df2}, 'reporte')  # multi-hoja
```

Crea automáticamente `resultados_geih_<anio>/{tablas,graficas,excel}/`.

### 19.6 Comparación multi-año

```python
from geih import ComparadorMultiAnio

comp = ComparadorMultiAnio()
comp.agregar_anio(2024, 'data/GEIH_2024_Consolidado.parquet', ConfigGEIH(anio=2024))
comp.agregar_anio(2025, 'data/GEIH_2025_Consolidado.parquet', ConfigGEIH(anio=2025))
comp.agregar_anio(2026, 'data/GEIH_2026_M01.parquet', ConfigGEIH(anio=2026, n_meses=1))

comp.comparar_indicadores()      # TD / TGP / TO con variación anual
comp.comparar_departamentos()    # TD por departamento × año
comp.comparar_brecha_genero()    # brecha H/M por año
```

---

## 📓 20. Notebooks de ejemplo

El repositorio incluye notebooks de referencia ejecutables. Todos funcionan en Google Colab con `!pip install geih-analisis` en la primera celda.

| Notebook | Para qué sirve |
|---|---|
| `Verificacion_GEIH_vs_Boletin_DANE.ipynb` | **Replicación verbatim del Boletín DANE.** Plantilla reutilizable con comparaciones individuales contra el anexo Excel oficial. Úsela para validar cualquier período |

### Recomendación de flujo para usuarios nuevos

1. **Descargar microdatos GEIH** del año más reciente del portal DANE.
2. **Ejecutar `Verificacion_GEIH_vs_Boletin_DANE.ipynb`** y verificar que `cons.verificar_estructura()` reporta los 12 meses OK.
3. **Ejecutar el notebook de verificación vs. boletín.** Si llega al final con ≥95 % ✅, su consolidado es confiable.
4. **Solo entonces** empezar a calcular indicadores nuevos. Validar siempre el resultado contra alguna cifra publicada por el DANE.

---

## 📅 21. Años soportados y SMMLV

La librería soporta la GEIH desde **2022 (Marco Muestral 2018)** hasta el año más reciente publicado por el DANE. Los SMMLV están hardcoded pero pueden actualizarse vía `geih_config.json` sin esperar un release.

| Año | SMMLV (COP) | Decreto | Notas |
|---|---:|---|---|
| 2022 | $1.000.000 | 1724 de 2021 | Marco Muestral 2018 — nueva serie |
| 2023 | $1.160.000 | 2613 de 2022 | +16 % interanual |
| 2024 | $1.300.000 | 2292 de 2023 | +12 % interanual |
| 2025 | $1.423.500 | 1572 de 2024 | +9.5 % interanual |
| 2026 | $1.750.905 | 2426 de 2025 | +23 % interanual (ajuste extraordinario) |
| 2027+ | — | — | Actualizable vía `geih_config.json` |

> 📘 **Años anteriores a 2022** (Marco Muestral 2005): no están soportados oficialmente porque las clasificaciones CIIU y DIVIPOLA difieren. Si su análisis requiere series largas, considere usar solo los agregados publicados en el boletín.

---

## 🗂️ 22. Mapa del código (para contribuidores)

Estructura del paquete — útil si quieres contribuir o entender dónde vive cada funcionalidad:

```
geih/
├── __init__.py                          # API pública — ~80 clases re-exportadas
├── config.py                            # ConfigGEIH, constantes, SMMLV, DIVIPOLA, CIIU
├── consolidador.py                      # ConsolidadorGEIH — ZIP → Parquet
├── preparador.py                        # PreparadorGEIH — Data Lake → Data Mart
├── descargador.py                       # DescargadorDANE — helper de organización
│
├── indicadores.py                       # IndicadoresLaborales, BrechaGenero, Gini
├── analisis_area.py                     # AnalisisOcupadosCiudad (32 ciudades)
├── analisis_departamental.py            # AnalisisDepartamental (33 entidades)
├── analisis_dpto_rama.py                # OcupadosDptoRama (CIIU × Dpto)
├── analisis_poblacional.py              # Campesino, Discapacidad, Migración, ...
├── analisis_tierra.py                   # AnalisisTierraAgropecuario
├── analisis_complementario.py           # DuracionDesempleo, CanalEmpleo, ...
├── analisis_avanzado.py                 # Mincer, ICE, ICI, IVI, MapaTalento, ...
│
├── informalidad.py                      # clasificar_informalidad_dane() — 17ª CIET
├── replicacion_dane_common.py           # Base para replicación oficial
├── replicacion_dane_informalidad.py     # Replica hojas informalidad del boletín
├── replicacion_dane_seguridad_social.py # Replica hojas seg. social del boletín
│
├── muestreo.py                          # evaluar_proporcion, _media, _total; CV, DEFF
├── estacional.py                        # desestacionalizar() — STL / X-13
├── comparativo.py                       # ComparadorMultiAnio
│
├── diagnostico.py                       # DiagnosticoCalidad, Top20Sectores
├── exportador.py                        # Exportador unificado CSV/XLSX/PNG
├── visualizacion.py                     # Gráficos matplotlib (estáticos)
├── visualizacion_interactiva.py         # Gráficos plotly (interactivos)
├── dashboard.py                         # App Streamlit
├── profiler.py                          # PerfilMemoria, medir_tiempo
├── logger.py                            # Logging estructurado
└── utils.py                             # EstadisticasPonderadas, GestorMemoria

tests/
├── test_canarios_boletin.py             # Tests end-to-end contra boletín DANE
├── test_paridad_golden.py               # Tests de paridad binaria contra golden set
├── test_indicadores.py                  # Tests unitarios de TD/TGP/TO
├── test_informalidad.py                 # Tests 17ª CIET
├── test_replicacion_*.py                # Tests de replicación hoja por hoja
├── test_preparador.py                   # Tests de preparación del Data Mart
├── test_consolidador.py                 # Tests de lectura ZIP → RAM
├── test_estadisticas_ponderadas.py      # Tests de FEX weighting
├── test_config.py                       # Tests de ConfigGEIH
├── test_layout_excel_dane.py            # Tests de formato Excel boletín
├── test_resolver_trimestre.py           # Tests de resolución de períodos móviles
├── smoke_test.py                        # Smoke test rápido
└── golden_expected.json                 # Cifras congeladas para paridad binaria
```

### Filosofía de desarrollo

- **Fail Fast:** errores internos del paquete propagan con su traceback real. `try/except` solo se usa con **discriminación por `ImportError.name`** cuando la causa raíz es una dependencia opcional (matplotlib, streamlit).
- **Single Source of Truth:** `__version__` se lee de `importlib.metadata` sobre `pyproject.toml` — no hay hardcodes duplicados.
- **Principio Abierto / Cerrado:** `PreparadorGEIH.preparar_base(columnas_extra=[...])` para extender sin modificar.
- **Semantic Versioning:** cambios breaking solo en mayores; deprecations anunciadas con warning antes de remover.
- **Tests canario:** cada bug corregido queda con un test específico que se activa si el bug vuelve.

### Contribuir

```bash
git clone https://github.com/enriqueforero/geih-analisis.git
cd geih-analisis
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
ruff check . && ruff format .
```

El CI ejecuta `ruff` + `pytest` con matriz Python 3.9–3.12. La cobertura actual tiene un gate de **25 %** con roadmap a 55 % en 2027. Branch protection exige que los 5 jobs estén en verde antes de permitir merge a `main`.

---

## ❓ 23. Preguntas frecuentes

**¿Qué es la GEIH?**
La Gran Encuesta Integrada de Hogares del DANE. Encuesta mensual con más de 250 000 hogares al año. Es la fuente oficial de las tasas de desempleo y empleo de Colombia.

**¿Tengo que descomprimir los ZIP del DANE?**
No. El paquete lee directamente desde `.zip` a RAM. Coloca los ZIP en `data/` con el nombre `Enero 2025.zip`, etc.

**¿Por qué la primera consolidación tarda ~5 minutos?**
Está leyendo y uniendo ~95 archivos CSV (8 módulos × 12 meses) con ~5 M filas × ~515 columnas desde dentro de los ZIP. El resultado se guarda en Parquet: las siguientes veces carga en segundos.

**¿Y si Colab se desconecta?**
`consolidar(checkpoint=True)` guarda el avance mes a mes y retoma automáticamente.

**¿Puedo analizar un solo mes?**
Sí: `ConfigGEIH(anio=2026, n_meses=1)`. Solo necesitas `data/Enero 2026.zip`.

**¿Puedo agregar un mes nuevo sin reconsolidar?**
Sí: `ConsolidadorGEIH.append_mes()` añade un mes al Parquet existente.

**¿Los datos tienen costo?**
No. Son públicos y gratuitos en [microdatos.dane.gov.co](https://microdatos.dane.gov.co) sin registro.

**¿Funciona con años anteriores a 2022?**
No oficialmente. Antes de 2022 la GEIH usaba el Marco Muestral 2005 con clasificaciones CIIU y DIVIPOLA diferentes. Para series largas, use los agregados del boletín.

**¿Los 33 departamentos están incluidos?**
Sí, los 32 + Bogotá D.C. Para departamentos pequeños (Amazonía, Orinoquía, San Andrés) el paquete advierte automáticamente cuando la muestra es insuficiente.

**¿Hay un dashboard visual?**
Sí. `ejecutar_dashboard(ruta_base="data")` lanza una interfaz Streamlit. Requiere `pip install "geih-analisis[dashboard]"`.

**¿Puedo agregar variables personalizadas sin modificar el paquete?**
Sí: `prep.preparar_base(geih, columnas_extra=["P6870", "P7310", ...])`.

**¿Cómo actualizo el SMMLV de un año nuevo sin esperar un release?**
Crea `geih_config.json` con `{"smmlv_por_anio": {"2027": 1900000}}` y el paquete lo detecta automáticamente (§18.1).

**¿Mis cifras no cuadran con el boletín — qué hago?**
Antes que nada: **no publique**. Revise en orden: (1) ¿consolidó los 12 meses o hay alguno faltante? (2) ¿el divisor FEX coincide con el período analizado? (3) ¿la columna `P6870` está en su Parquet (necesaria para informalidad 17ª CIET)? (4) ¿actualizó a la última versión de la librería? Si nada funciona, abra un issue en GitHub con su consolidado mínimo reproducible.

**¿Puedo usar este paquete para producir cifras oficiales?**
**No.** Esta es una herramienta independiente. Cualquier cifra oficial debe venir del DANE directamente. La librería sirve para análisis exploratorio, investigación académica, consultoría o periodismo, pero el boletín DANE siempre es la fuente-de-verdad.

**¿La librería recolecta datos o telemetría?**
No. No hay telemetría, ni conexiones de red no solicitadas, ni recolección de datos. Todo corre localmente. El único recurso externo es el portal del DANE, y eres tú quien descarga los ZIP manualmente.

---

## ✒️ 24. Cómo citar

Si usas esta librería para tu tesis, artículo, informe o consultoría, se agradece la citación:

```bibtex
@software{forero2026geih,
  author  = {Forero Herrera, N{\'e}stor Enrique},
  title   = {geih-analisis: Paquete Python para an{\'a}lisis de microdatos GEIH},
  year    = {2026},
  url     = {https://github.com/enriqueforero/geih-analisis},
  note    = {Datos fuente: Gran Encuesta Integrada de Hogares --- DANE, Colombia}
}
```

**Citación APA (formato corto):**

> Forero Herrera, N. E. (2026). *geih-analisis* [Software]. https://github.com/enriqueforero/geih-analisis

**Citación Chicago (footnote):**

> Néstor Enrique Forero Herrera, *geih-analisis: Paquete Python para análisis de microdatos GEIH*, 2026, https://github.com/enriqueforero/geih-analisis.

Para cifras específicas, **cite siempre también la fuente original del DANE**:

> Fuente: Elaboración propia con base en microdatos GEIH — DANE, procesados con `geih-analisis`.

---

## 🙏 25. Agradecimientos

El diseño de esta librería se inspiró en notebooks previos compartidos por colegas, cuyo aporte se reconoce explícitamente:

- **[Lina María Castro](https://co.linkedin.com/in/lina-maria-castro)** compartió notebooks propios sobre **consolidación multi-módulo de la GEIH** y sobre **análisis por municipios**, que sirvieron como referencia metodológica inicial para el `ConsolidadorGEIH` y para `AnalisisOcupadosCiudad`. Aunque la implementación final reescribió ambos módulos desde cero, el enfoque original de Lina fue el punto de partida conceptual.
- **[Nicolás Rivera](https://co.linkedin.com/in/nicol%C3%A1s-rivera-garz%C3%B3n-7a8b23201)** extendió el trabajo anterior al incorporar mejoras de programación en los notebooks y **validó los cálculos de ocupados por municipio × rama de actividad económica**, contrastando cifras contra los boletines oficiales del DANE.

Ambos aportes son anteriores al paquete y se reconocen como contribuciones intelectuales al proyecto.

Se agradecen también los reportes de bugs, sugerencias de mejora y validaciones cruzadas de la comunidad de usuarios académicos, gubernamentales y del sector privado que han usado la librería desde su primera publicación.

---

## 📄 26. Licencia, metodología y disclaimer legal

### Licencia MIT

```
Copyright (c) 2026 Néstor Enrique Forero Herrera

Se concede permiso, libre de cargos, a cualquier persona que obtenga una copia
de este software y de los archivos de documentación asociados (el "Software"),
a utilizar el Software sin restricción, incluyendo sin limitación los derechos
a usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar, y/o
vender copias del Software, sujeto a las condiciones del archivo LICENSE.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA
O IMPLÍCITA, INCLUYENDO PERO NO LIMITADA A GARANTÍAS DE COMERCIABILIDAD,
IDONEIDAD PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN.
```

### Metodología de desarrollo

La arquitectura, la lógica de negocio y los requerimientos son de **autoría humana**; el autor asume responsabilidad total del código publicado. Se utilizaron modelos de IA generativa (Claude y Gemini) como asistencia técnica para código boilerplate, optimización y refactorización. **Ningún bloque asistido por IA se integró sin revisión crítica y validación funcional.**

Las replicaciones oficiales (`ReplicadorInformalidad`, `ReplicadorSeguridadSocial`, `clasificar_informalidad_dane`) son **traducciones literales del código SAS/STATA oficial del DANE** publicado en la documentación técnica del boletín. Cualquier discrepancia que se detecte entre la librería y el boletín debe reportarse como bug.

### Disclaimer legal completo

1. **Datos y afiliación.** Los microdatos de la GEIH son propiedad del **Departamento Administrativo Nacional de Estadística (DANE)** de Colombia. Este paquete es una herramienta de cálculo **independiente, sin afiliación oficial, respaldo institucional, endoso o vínculo de ningún tipo con el DANE**. El uso de los datos se rige por los términos y condiciones del portal oficial de microdatos del DANE ([microdatos.dane.gov.co](https://microdatos.dane.gov.co)), que el usuario debe leer y aceptar independientemente.

2. **No es fuente oficial.** Las cifras producidas por esta librería **no constituyen información estadística oficial** y no deben presentarse como tal. La fuente oficial de los indicadores del mercado laboral colombiano es el Boletín GEIH publicado mensualmente por el DANE.

3. **Validación obligatoria.** El usuario es responsable de validar las cifras producidas contra el boletín DANE correspondiente antes de publicarlas, citarlas o usarlas como insumo para decisiones. Cualquier discrepancia superior a las tolerancias declaradas (§13.5) debe investigarse antes de publicar.

4. **Sin garantía.** El software se distribuye **"tal cual"** bajo licencia MIT, sin garantía de correctitud, completitud, adecuación a propósito particular o no infracción. Los autores no son responsables por decisiones tomadas con base en cifras producidas por la librería.

5. **Uso académico, investigativo y comercial permitido** bajo los términos de la licencia MIT, siempre respetando los términos de uso originales de los datos del DANE.

6. **Privacidad y anonimización.** Los microdatos GEIH publicados por el DANE están anonimizados según sus políticas de confidencialidad. Esta librería no revierte la anonimización ni intenta re-identificar personas. El usuario no debe intentar re-identificar registros individuales; hacerlo puede violar leyes colombianas de protección de datos (Ley 1581 de 2012).

7. **Marcas y nombres.** "DANE", "GEIH", "DIVIPOLA", "CIIU" y demás nomenclaturas son marcas, nombres oficiales o estándares de sus respectivos titulares (DANE, ONU, entre otros). Se usan aquí con propósito descriptivo de referencia técnica, sin reclamar derecho alguno sobre ellos.

### Reporte de problemas

Para reportar bugs, discrepancias con el boletín DANE o sugerencias de mejora:

- 🐛 [GitHub Issues](https://github.com/enriqueforero/geih-analisis/issues)
- 💬 [GitHub Discussions](https://github.com/enriqueforero/geih-analisis/discussions)

**Al reportar una discrepancia con el boletín DANE, incluye:**

1. Período analizado (año, meses)
2. Indicador específico (ej. "TD_raw nacional")
3. Valor obtenido vs. valor del boletín (con referencia a la hoja y celda del anexo Excel)
4. Versión de `geih-analisis` (`python -c "import geih; print(geih.__version__)"`)
5. Código mínimo reproducible

---

<div align="center">

**Hecho con pasión en Bogotá, Colombia.**
*Porque los datos laborales deben estar al alcance de todos — estudiantes, investigadores, periodistas, gobierno y sector privado — con el mismo rigor que el DANE aplica en sus boletines.*

[⬆ Volver al inicio](#-geih-analisis)

</div>
