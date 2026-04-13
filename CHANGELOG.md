# Changelog

Todos los cambios notables de `geih-analisis` se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [0.1.6] — 2026-04-13

Versión orientada a **rigor de validación contra el Boletín DANE**. Se identifican
y corrigen seis bugs latentes detectados durante la replicación verbatim del
Boletín GEIH Diciembre 2025, se añade derivación automática de variables
analíticas, un módulo de desestacionalización y una batería de tests "canario"
que protege contra regresiones futuras.

### Fixed
- **`ConfigGEIH.__post_init__` — validación de `meses_rango` corregida.**
  Antes era imposible construir Configs como `meses_rango=[12]` o
  `[10,11,12]` porque la validación comparaba `max(meses_rango)` contra
  un `n_meses` que ya había sido sobrescrito en la misma función. La
  validación ahora ocurre antes de la sincronización, contra el calendario
  absoluto `[1..12]` y contra el `n_meses` original del consolidado fuente.
  Además se valida lista vacía y duplicados.
- **`ConfigGEIH.carpetas_mensuales` — usa `_meses_consolidado_fuente`.**
  Antes leía el `n_meses` ya sobrescrito por `meses_rango`, generando
  carpetas incompletas al filtrar análisis. Ahora siempre devuelve las
  carpetas del consolidado fuente, independientemente del rango analítico.
- **`PreparadorGEIH.preparar_base` — divisor FEX unificado.**
  La rama vieja `if int → divisor=1 else config.n_meses` fallaba cuando
  `meses_filtro=list` se combinaba con `config.meses_rango`. La nueva
  lógica de tres ramas es estable bajo cualquier combinación.
- **`PreparadorGEIH.agregar_variables_derivadas` — `DOMINIO` reescrito.**
  Antes usaba `AREA_A_CIUDAD.keys()` como set de las 13 A.M., pero ese
  diccionario contiene DIVIPOLA de 5 dígitos (no AREA de 2 dígitos del
  microdato GEIH) y además incluye más de 13 ciudades. Resultado del bug:
  `DOMINIO=='13_AM'` devolvía 0 filas. Ahora usa `DPTOS_13_CIUDADES` y
  `DPTOS_10_CIUDADES` (sets oficiales de 2 dígitos) sobre la columna
  `AREA` cruda, generando cuatro categorías mutuamente excluyentes:
  `13_AM`, `10_ciudades`, `otras_cab`, `rural`.
- **`PreparadorGEIH.agregar_variables_derivadas` — `POSICION_OCU` corregido.**
  El mapeo inline previo tenía cruzados los códigos 7 y 8: ponía
  "Trabajador sin remuneración en otras empresas" como código 7 y
  "Jornalero o peón" como código 8, **invirtiendo el orden CISE-93**
  publicado por el DANE. Confirmado contra la hoja `Ocupados TN_posición`
  del anexo Excel: jornalero ≈ 849 mil personas en Dic-2025 corresponde
  a P6430=7. Ahora usa `POSICION_OCUPACIONAL` de `config.py` como única
  fuente de verdad.
- **`PreparadorGEIH.agregar_variables_derivadas` — `INFORMAL` mejorado.**
  Dos correcciones en una: (a) el código del jornalero en la regla de
  asalariados estaba como `pos == 8` (incorrecto, ver fix anterior); ahora
  es `pos == 7`. (b) Los patrones (P6430=5) ahora se clasifican como
  formales solo si cumplen **ambas** condiciones de la 17ª CIET: empresa
  de más de 5 empleados (P6870 ≥ 6) **y** cotización pensional. Antes se
  evaluaban solo por cotización, sesgando la informalidad +1 a +3 p.p. en
  zonas rurales donde abundan los patrones pequeños.

### Added
- **`PreparadorGEIH.preparar_base(derivar=True)`** — nuevo parámetro que
  llama automáticamente a `agregar_variables_derivadas` antes del return.
  Antes el usuario debía recordar invocarla manualmente, lo cual era fuente
  frecuente de `KeyError` en código que referenciaba `RAMA`, `SEXO`,
  `DOMINIO`, etc. El comportamiento por defecto cambió a `True`; usuarios
  avanzados que quieran el DataFrame mínimo (solo tipos + FEX_ADJ) pueden
  pasar `derivar=False`.
- **`P6870` añadida a `COLUMNAS_DEFAULT`.** Tamaño de establecimiento del
  módulo de Ocupados, requisito para la definición oficial 17ª CIET de
  informalidad. Es barata en memoria y crítica para la corrección.
- **`COLUMNAS_BOLETIN`** — nuevo alias semántico de `COLUMNAS_DEFAULT`,
  exportado desde `preparador.py`. Documenta la intención del código:
  ```python
  df = prep.preparar_base(geih, columnas=COLUMNAS_BOLETIN)
  ```
- **`IndicadoresLaborales.calcular()` — campos `_raw` añadidos.**
  El método ahora devuelve también `TD_raw`, `TGP_raw`, `TO_raw` con los
  valores sin redondear, en paralelo a los `TD_%`, `TGP_%`, `TO_%` que
  redondean a 1 decimal para display. Los campos `_raw` son necesarios
  para validar contra el anexo Excel del DANE con tolerancia ±0.05 p.p.,
  porque el anexo trae 4 decimales y el round destruía esa resolución.
- **`IndicadoresLaborales.sanity_check(tolerancia_pp=0.5)`** — la tolerancia
  ahora es parámetro en vez de constante hardcoded. Permite validación
  estricta (±0.05 p.p.) cuando se trabaja con datos exactos.
- **Nuevo módulo `geih.estacional`** — desestacionalización de series
  mensuales mediante STL (Seasonal-Trend LOESS, default) o X-13-ARIMA-SEATS
  (opcional, requiere binario externo). Tres funciones públicas:
  `validar_serie_mensual`, `desestacionalizar`, `desestacionalizar_td_mensual`.
  Permite replicar la pág. 25 del Boletín DANE (TD desestacionalizada
  mensual). El método X-13 oficial del DANE no es reproducible exactamente
  porque usa calendario laboral colombiano que no exponemos; se documenta
  un sesgo esperado de ±0.1 a ±0.3 p.p. frente a la serie publicada.
- **`tests/test_canarios_boletin.py`** — batería de 26 tests "canario"
  organizados en 8 clases que validan end-to-end la replicación del
  Boletín DANE: divisor FEX en 3 vistas temporales, tasas TD/TGP/TO,
  brecha por sexo, dominio geográfico (con regresión específica del bug
  `'13_AM' → 0 filas`), ramas CIIU, posición ocupacional (con regresión
  del bug jornalero=7), informalidad, y exposición de valores `_raw`.
  Los tests se skipean limpiamente si la variable de entorno
  `GEIH_TEST_DATA` no apunta a un consolidado válido, permitiendo correr
  el resto del test suite sin acceso a microdatos.
- **Notebook `Verificacion_GEIH_2025_vs_Boletin_DANE_v3.ipynb`** —
  replicación verbatim del Boletín GEIH Dic-2025 contra el anexo Excel
  oficial del DANE, con tolerancia estricta ±0.05 p.p. Cubre 9 secciones
  (A: Diciembre mensual, B: Trimestre Oct-Dic, C: Anual Ene-Dic,
  D: Informalidad, E: Juventud, F: Étnico, G: Ingresos IML, H: Errores
  muestrales, I: Replicación de gráficas) y produce un CSV maestro con
  73+ comparaciones individuales contra el boletín.

### Changed
- **`README.md`** documenta dos nuevas secciones: "Verificación contra el
  Boletín DANE" (sección 13) y "Replicación de gráficas y desestacionalización"
  (sección 14). La sección 4 ("Descargar los datos del DANE") se enriqueció
  con enlaces directos a DIVIPOLA, CIIU Rev. 4 A.C., manual DDI-853 y
  boletines mensuales para validación cruzada.
- **`PreparadorGEIH.agregar_variables_derivadas`** ya no es responsabilidad
  del usuario llamarla: queda integrada en el flujo estándar de
  `preparar_base`. Esto reduce significativamente la curva de aprendizaje.

### Deprecated
- **Acceso a `IndicadoresLaborales.calcular()['TD_%']` para validación.**
  Sigue funcionando para display (mantiene retrocompatibilidad), pero para
  comparación con cifras DANE de precisión completa use `TD_raw`.

### Notas de migración (0.1.5 → 0.1.6)
1. **Reinstale** la librería en su entorno y **reinicie el kernel** de
   Colab/Jupyter. Python cachea módulos: sin reinicio no verá los cambios.
2. **Si su código llama `agregar_variables_derivadas` manualmente después
   de `preparar_base`, ya no es necesario** — la llamada es automática.
   El método es idempotente, así que mantenerla no rompe nada, pero es
   trabajo redundante.
3. **Si dependía del comportamiento `DOMINIO=='13_AM'` con la lógica vieja
   (que reportaba 0 filas o cifras incorrectas)**, su código estaba
   produciendo basura silenciosamente. La cifra correcta de ocupados en
   13 A.M. para Dic-2025 es ~11.525 mil. Verifique todos los reportes que
   dependían de esa columna.
4. **Si reconsolidó la base con 0.1.4 o anterior**, considere reconsolidar
   con 0.1.6 para que `P6870` (tamaño establecimiento) entre en el Parquet.
   Sin esa columna, `INFORMAL` cae a la versión aproximada y avisa con
   un warning legible — no falla.
5. **Si tiene tests propios que validan TD/TGP/TO**, considere migrarlos
   a usar `TD_raw` para tolerancias estrictas. Los `TD_%` siguen sirviendo
   para display.
6. **Para correr los tests canario nuevos:**
   ```bash
   GEIH_TEST_DATA=/ruta/a/su/consolidado/2025 \
       pytest tests/test_canarios_boletin.py -v
   ```

---

## [0.1.5] — 2026-04-13

### Added
- **`ConsolidadorGEIH`  — lectura directa desde `.zip` a RAM.** El consolidador ahora
  abre los ZIP mensuales del DANE con `zipfile` y lee los CSV internos sin escribir
  a disco. Nueva estructura recomendada: `data/Enero 2025.zip`, `data/Febrero 2025.zip`, etc.
- **`OcupadosDptoRama`** (`geih.analisis_dpto_rama`) — nueva clase que estima ocupados
  promedio anual por Departamento (DIVIPOLA) × Rama CIIU Rev. 4 adaptada, a 2 dígitos
  (88 divisiones) o 4 dígitos (~500 clases). Incluye CV bajo diseño complejo
  (Cochran 1977, Kish 1965), IC al 95 % y clasificación de precisión DANE por celda.
- **`ConsolidadorGEIH.append_mes()`** — permite agregar un mes nuevo a un Parquet
  existente sin reconsolidar todo el año.
- **`verificar_estructura()` DRY** — el lector universal acepta `solo_verificar=True`
  y reutiliza el índice del ZIP construido una sola vez (v5.1).
- **Separación explícita Data Lake / Data Mart** — `ConsolidadorGEIH` construye el
  universo completo (~515 columnas, ~5 M filas); el filtrado a columnas analíticas
  es responsabilidad exclusiva de `PreparadorGEIH`.

### Documentation
- El README ahora documenta **herramientas auxiliares** que ya existían en el paquete
  pero no estaban expuestas: `DiagnosticoCalidad`, `MergeCorrelativas`, `Top20Sectores`,
  `ejecutar_dashboard()` (Streamlit), `evaluar_media()`, `evaluar_total()`,
  `clasificar_precision()`, `LoggerGEIH` y el `Exportador` unificado.
- Se listan explícitamente clases analíticas previamente no documentadas:
  `AnalisisHoras`, `AnalisisSubempleo`, `AnalisisFFT`, `AnalisisUrbanoRural`,
  `ProductividadTamano`, `ContribucionSectorial`, `AnatomaSalario`, `FormaPago`,
  `CanalEmpleo`, `EtnicoRacial`, `BonoDemografico`, `ProxyBilinguismo`,
  `AnalisisOtrasFormas`, `AnalisisOtrosIngresos`, `AnalisisAlcanceMercado`,
  `AnalisisDesanimados`.
- **Agradecimientos actualizados:** se reconoce explícitamente el aporte de
  Lina María Castro en los notebooks originales de **consolidación** y **análisis por
  municipios**, y de Nicolás Rivera en la **validación de los cálculos de ocupados
  por municipio × rama de actividad económica**.

### Changed
- **`AnalisisOcupadosCiudad`** (`geih.analisis_area`) refactorizado: produce 6 tablas
  (total nacional, agrupación DANE, dominio geográfico, ciudad/AM, granular CIIU×ciudad,
  CIIU nacional) + 3 gráficos + exportación Excel multi-hoja. Usa la variable `AREA`
  (DIVIPOLA de 5 dígitos) para identificar 32 ciudades y áreas metropolitanas.
- **Join de módulos:** se documenta explícitamente el uso de **LEFT JOIN** sobre el
  módulo ancla "Características generales". Usar OUTER inflaría la PEA.
- **README completamente reescrito** con la nueva estructura `data/*.zip`, ejemplos
  actualizados y sección dedicada a `OcupadosDptoRama`.

### Deprecated
- **Estructura antigua `Mes Año/CSV/*.CSV`** — sigue funcionando como fallback, pero
  se desaconseja para nuevas instalaciones. Usa ZIP directamente.
- **Descompresión manual de los ZIP del DANE** — ya no es necesaria.

### Removed
- Referencias a "96 archivos CSV sueltos" en la documentación: ahora son 12 ZIP.
- Sección del README que describía `DescargadorDANE.organizar_zips()` como paso
  obligatorio de organización (el flujo recomendado es colocar los ZIP directamente).

### Fixed
- Cálculo de `MES_NUM` documentado como variable creada (no extraída) durante la
  consolidación.

### Notas de migración (0.1.4 → 0.1.5)
1. **Recomendado:** mover los ZIP del DANE a `data/` renombrándolos `Enero 2025.zip`,
   `Febrero 2025.zip`, etc. Eliminar las carpetas `Mes Año/CSV/` si ya no las usas.
2. **Opcional:** si tu Parquet consolidado fue generado con 0.1.4, sigue siendo
   compatible con 0.1.5 — no hace falta reconsolidar.
3. **Nuevo import:** `from geih import OcupadosDptoRama`.

---

## [0.1.4] — 2026-04-02

### Added
- `AnalisisDepartamental` — reporte integral departamental con precisión muestral.
- `AnalisisTierraAgropecuario` — explotación de P3064 / P3064S1 / P3056.
- Soporte para `geih_config.json` externo (SMMLV, ref DANE, parámetros muestrales).
- Módulo `geih.muestreo` con `evaluar_proporcion()` y `evaluar_total()`.
- Cobertura completa de los 33 departamentos (incluyendo Amazonía, Orinoquía,
  San Andrés).

### Changed
- `ConfigGEIH` soporta `meses_rango` para análisis semestrales o trimestrales.
- `PreparadorGEIH.preparar_base()` acepta `columnas_extra` sin modificar el código
  fuente (Principio Abierto/Cerrado).

---

## [0.1.0] — 2026-04-01

- Primera publicación en PyPI. Soporte GEIH 2022–2025. 70+ clases analíticas.
  Optimizado para Google Colab.
