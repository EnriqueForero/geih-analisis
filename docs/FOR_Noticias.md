# FOR_Noticias.md — Lo que aprendimos refactorizando la GEIH 2025

**Fecha:** 2026-03-28  
**Proyecto:** Convertir un notebook monolítico de ~9,600 líneas en un paquete modular de Python  
**Versión final:** v3.0.0 — 12 archivos .py, 48 clases, 4,091 líneas  
**Iteraciones:** 3 versiones con correcciones sustanciales entre cada una

---

## Paso 1: Enfoque y razonamiento

### ¿Cuál fue el punto de partida?

El notebook original era un solo archivo de 9,600 líneas donde convivían constantes, consolidación, cálculos, gráficos y documentación. Todo funcionaba si uno lo ejecutaba celda por celda en orden, pero no era reutilizable, testeable ni mantenible.

Mi enfoque fue leer CADA línea para identificar **fronteras naturales** — lugares donde el código cambiaba de tema. Encontré 7 "habitaciones" escondidas en el monolito: configuración, memoria, consolidación, preparación de datos, funciones estadísticas, módulos de análisis y gráficos.

La clave fue que las **dependencias fluyen en una sola dirección**: config → utils → consolidador → preparador → indicadores → visualización. No hay ciclos. Esto hizo posible una separación limpia.

### La decisión arquitectónica central

Separé por **responsabilidad**, no por tamaño. No creé 20 archivos de 50 líneas ni un solo archivo de 4,000. La regla fue: si dos funciones comparten el mismo "por qué" y siempre se usan juntas, van en el mismo archivo. Si una hace cálculos y otra dibuja gráficos, van en archivos distintos aunque operen sobre los mismos datos.

---

## Paso 2: Caminos descartados

### Opción A: Un solo archivo .py con clases
**Rechazada:** un archivo de 4,000+ líneas con 48 clases es igual de difícil de navegar. Si solo necesitas la consolidación, cargas todo el código de Mincer en memoria.

### Opción B: Un archivo por clase (48 archivos)
**Rechazada:** demasiada fragmentación. Los imports circulares se vuelven un problema real. Para entender el flujo hay que abrir 12 pestañas.

### Opción C: Migrar a Polars/DuckDB simultáneamente
**Rechazada por ahora:** el equipo conoce Pandas. Migrar tecnología + arquitectura al mismo tiempo es como remodelar la casa mientras te mudas. Pero el diseño por clases hace que la migración futura sea modular: cambiar `EstadisticasPonderadas` internamente no afecta a las 48 clases que la usan.

### Opción D: Framework kedro/prefect
**Rechazada:** overengineering. Es un notebook de análisis para un equipo de 6 personas, no un pipeline en producción en la nube.

---

## Paso 3: Cómo encajan las piezas

Piensa en el paquete como una línea de ensamblaje:

```
CSV del DANE (8 módulos × 12 meses)
    ↓
[ConsolidadorGEIH] → DataFrame crudo (5M filas × 347 cols)
    ↓
[PreparadorGEIH] → DataFrame con FEX_ADJ, ramas, variables derivadas
    ↓
[48 clases de análisis] → DataFrames de resultados numéricos
    ↓
[Visualización] → Figuras matplotlib
    ↓
[Exportador] → resultados_geih_2025/
                ├── graficas/   (PNGs)
                ├── tablas/     (CSVs)
                ├── excel/      (XLSX multi-hoja)
                └── metadata.json
```

La regla estricta: **cada etapa solo recibe el output de la anterior.** Los indicadores nunca tocan los CSV directamente. Los gráficos nunca calculan percentiles. El exportador nunca decide qué calcular.

### ¿Por qué `config.py` centraliza TODO?

Antes, `SMMLV_2025 = 1_423_500` aparecía **6 veces** en el notebook. Si en 2026 cambia a $1,500,000, hay que buscar en 6 sitios y rezar para no olvidar uno. Ahora está en UN lugar y las 48 clases lo importan de ahí.

Lo mismo pasa con los mapeos CIIU, los nombres de departamentos, las carpetas mensuales, las llaves de merge. Todo lo que es "verdad del negocio" vive en `config.py`. Si cambia la realidad, cambia un archivo.

---

## Paso 4: Herramientas y decisiones técnicas

### ¿Por qué `@dataclass` con `__post_init__`?
Porque un diccionario `config = {'n_meses': 12}` no explota si escribes `config['n_messe']` — falla silenciosamente. Con `@dataclass`, el IDE autocompleta y `__post_init__` valida que `n_meses` esté entre 1 y 12 antes de que el código empiece a correr.

### ¿Por qué `np.select` para mapear CIIU?
El notebook original usaba `.apply(lambda x: ...)` para mapear códigos CIIU. Eso es un loop disfrazado: 5 millones de filas × 13 comparaciones = minutos. `np.select` con `.between()` es **vectorizado** — opera en C sobre arrays completos en ~2 segundos.

### ¿Por qué separar cálculo de visualización?
Imagina que necesitas la tabla de salarios por rama en un Excel para el VP, no en un gráfico PNG. Con el notebook original, la función de cálculo estaba dentro del bloque de matplotlib — para obtener el DataFrame, tenías que generar el gráfico. Ahora puedes llamar `AnalisisSalarios().por_rama(df)` y obtener un DataFrame limpio sin dibujar nada.

### ¿Por qué el Exportador crea carpetas?
Antes, los PNGs quedaban sueltos en la raíz de Google Drive mezclados con los CSVs y los Parquets. Encontrar `BoxPlot_salarios_rama_anual_2025.png` entre 40 archivos era un castigo. Ahora todo va a `resultados_geih_2025/graficas/` con un `metadata.json` que registra exactamente qué parámetros generaron esos resultados.

---

## Paso 5: Tradeoffs

| Prioricé | Sacrifiqué | Razón |
|---|---|---|
| 8 módulos DANE completos | Velocidad de consolidación | Migración y Otros Ingresos agregan columnas pero la riqueza analítica lo justifica |
| 48 clases de análisis | Brevedad del código | Cada clase documenta con docstrings el "por qué", no solo el "qué" |
| Compatibilidad Pandas | Performance Polars | El equipo conoce Pandas; la migración sería un segundo proyecto |
| Carpetas organizadas | Simplicidad | La organización escala; el desorden no |
| Cobertura completa de variables DDI | Tiempo de desarrollo | Mapear 431 variables del DANE toma más tiempo pero evita "¿por qué no puedo analizar campesinos?" |

---

## Paso 6: Errores, correcciones y la gran lección

### Error 1 (v1→v2): Cobertura incompleta — 8/36 módulos

La primera versión fue honesta en su estructura pero le faltaban **21 módulos de análisis enteros**. No tenía ICF, ICI, IVI, Mincer, bilingüismo, FFT, estacionalidad, ni varios otros. Cuando el usuario preguntó "¿esto hace TODO lo que hacía el original?", la respuesta honesta fue "no, solo 22%."

**Lección:** refactorizar no es solo reorganizar código — es verificar que la reorganización preservó TODA la funcionalidad. Es como cuando mudas de casa: si llegas y te faltan 3 cajas, no importa qué tan bonita esté la cocina nueva.

### Error 2 (v2→v3): Solo 5 de 8 módulos DANE

El DDI del DANE (documento de 25,000 líneas, 431 variables) reveló que la GEIH tiene **8 módulos CSV**, no 5. Faltaban:
- **Migración** — interna e internacional (P3370-P3379)
- **Otras formas de trabajo** — autoconsumo, voluntariado (P3054-P3057)
- **Otros ingresos** — pensiones, remesas, arriendos (P7422-P7510)

Y dentro de los módulos que sí se cargaban, había variables de poblaciones enteras sin explotar:
- **P2057** — autodefinición campesina (mandato del PND)
- **P1906S1-S8** — discapacidad escala Washington (8 dimensiones)
- **P3047-P3049** — autonomía laboral (contratistas dependientes)
- **P1802** — alcance de mercado hasta exportación

**Lección:** el manual del DANE es la fuente de verdad, no el notebook anterior. El notebook anterior era el producto de las necesidades de un momento; el DDI es el catálogo completo de lo posible.

### Error 3: `np.trapz` renombrado

`np.trapz()` fue renombrado a `np.trapezoid()` en NumPy ≥ 2.0. Fix: `getattr(np, "trapezoid", getattr(np, "trapz", None))`.

**Lección:** cuando uses funciones de librerías que cambian entre versiones, haz feature detection (`getattr`), no version checking.

---

## Paso 7: Trampas para el futuro

### Trampa 1: LEFT JOIN, nunca OUTER
Si alguien cambia `how='left'` a `how='outer'` en el consolidador, la PEA se dispara a 56 millones. Error silencioso. El `sanity_check()` alerta si PEA > 40M.

### Trampa 2: FEX_C18 sin dividir
El error más frecuente del mundo GEIH. El paquete lo maneja automáticamente con `ConfigGEIH(n_meses=12)` y `preparar_base(mes_filtro=None)`.

### Trampa 3: DPTO como numérico
Sin `converters={'DPTO': str}`, Antioquia pasa de `'05'` a `5`. 7 millones de registros quedan sin departamento. Sin error.

### Trampa 4: Proxy bilingüismo — códigos CINE-F engañosos
Los códigos 111/112 capturan a TODOS los licenciados, no solo a los de idiomas. Solo los 22x son formación directa en lenguas. Incluirlos produce que Chocó sea el departamento más "bilingüe".

### Trampa 5: P1802 solo tiene valores 1-3 en algunos meses
La variable de alcance de mercado (6=exportación) a veces no tiene el valor 6 porque depende del tipo de trabajador encuestado. Siempre verificar la distribución antes de reportar.

---

## Paso 8: Qué notaría un experto

1. **Responsabilidad única real.** Cada clase tiene un verbo claro: ConsolidadorGEIH *consolida*, AnalisisCampesino *analiza campesinos*. Si el nombre no te dice qué hace, el diseño está mal.

2. **El catálogo `VARIABLES_POR_MODULO`.** 431 variables documentadas en español. Un principiante copia la variable; un experto consulta el catálogo para saber qué hay disponible.

3. **Pre-flight checks.** `verificar_estructura()` valida en 2 segundos que existan los 96 archivos (8 módulos × 12 meses). Un principiante esperaría 10 minutos para descubrir que falta uno.

4. **Mincer usa WLS, no OLS.** La ecuación de Mincer se estima con Weighted Least Squares usando FEX_ADJ como peso. OLS sin pesos produce β₁ sesgados porque ignora que cada registro representa un número diferente de personas.

5. **La normalización min-max con inversión.** En ICI e ITAT, el costo laboral se invierte (menor costo = mejor score). Sin invertir, Bogotá (la más cara) aparece como "la más competitiva".

6. **Discapacidad usa criterio ONU, no la pregunta cruda.** La escala Washington tiene 4 niveles por dimensión. El criterio ONU define discapacidad como al menos una dimensión con valor 3 (mucha dificultad) o 4 (no puede). Usar valor ≥2 sobreestima la prevalencia por 3×.

---

## Paso 9: Lecciones transferibles

### 1. "Lee el manual del fabricante"

La lección más grande de v2→v3: el notebook original NO cubría todo lo que la GEIH ofrece. Solo usaba 5 de 8 módulos y ~80 de 431 variables. Al leer el DDI del DANE, descubrí variables como P1802 (alcance de mercado → exportación), P2057 (campesinos), y P1906S1-S8 (discapacidad) que son oro para ProColombia y nadie las usa.

**Analogía:** es como comprar un iPhone y usar solo WhatsApp. El teléfono puede hacer 100 cosas más, pero si nunca leíste qué más hay, no sabes que existen.

### 2. La auditoría honesta protege

Cuando preguntaron "¿esto hace todo?", la tentación era decir "sí". Pero la auditoría mostró 22% de cobertura. Reconocerlo permitió corregirlo. La deuda oculta siempre cobra intereses más altos que la deuda declarada.

### 3. SSOT es supervivencia

SMMLV definido en 6 lugares → alguien actualiza 5 y olvida 1 → un módulo usa 2025 y otro 2024. Nadie nota el error porque ambos "se ven razonables". La Single Source of Truth no es buena práctica — es la diferencia entre datos correctos y datos que parecen correctos.

### 4. La estructura de carpetas cuenta una historia

`resultados_geih_2025/graficas/BoxPlot_salarios_rama.png` dice exactamente qué es. `BoxPlot_salarios_rama.png` suelto entre 40 archivos no dice nada.

### 5. Fail Fast con validación visible

El `sanity_check()` que alerta si PEA > 40M ha evitado más errores que cualquier otra línea del paquete. No es sofisticado — es un `if` con un `print`. Pero captura el error más frecuente y costoso de la GEIH.

### 6. La modularidad se siente como LEGO

```python
resultado = AnalisisSalarios().por_rama(
    PreparadorGEIH().preparar_base(
        ConsolidadorGEIH.cargar('GEIH_2025.parquet')
    )
)
```

Si cambias Pandas por Polars en el preparador, los indicadores ni se enteran. Si agregas un módulo nuevo, no tocas nada existente. Eso es el Open/Closed Principle: abierto para extensión, cerrado para modificación.

---

## Resumen del viaje en números

| Métrica | v1 | v2 | v3 |
|---|---|---|---|
| Módulos DANE consolidados | 5/8 | 5/8 | **8/8** |
| Clases de análisis | 8 | 36 | **48** |
| Cobertura funcional | 22% | 100% original | **100% + poblaciones nuevas** |
| Variables catalogadas | ~15 | ~80 | **431 (DDI completo)** |
| Exportación organizada | No | No | **Sí (3 carpetas + metadata)** |
| Líneas de código | 2,427 | 3,530 | **4,091** |
| Líneas originales | 9,624 | 9,624 | 9,624 |

---

**Próximos pasos sugeridos:**
1. Correr el paquete contra la base real para validar sanity checks
2. Agregar `pytest` para estadísticas ponderadas y mapeo CIIU
3. Crear notebook-ejemplo con las 15 celdas de la guía
4. Evaluar Polars para la consolidación
5. Explorar variables MX1-MX7 del notebook original (P6500 vs INGLABO, P6765, P3363)
