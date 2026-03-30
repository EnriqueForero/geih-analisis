# FOR Néstor — Publicar un paquete Python desde Colab a GitHub y PyPI

**Tarea:** Diseñar el notebook de publicación, recomendar el nombre del
paquete y explicar todo el proceso de distribución open source.

---

## Paso 1: La decisión del nombre — por qué importa más de lo que parece

### El problema de `geih_2025`

El nombre del paquete tiene dos partes que hay que separar:
- **Nombre de distribución** (lo que pones en `pip install`)
- **Nombre de importación** (lo que pones en `from ... import`)

En Python, estos dos pueden ser distintos. Pandas lo hace: se llama
`scikit-learn` en pip pero `sklearn` en el código. Esta separación
es una solución estándar cuando el nombre ideal ya está tomado
o cuando el nombre de importación tiene restricciones (años, guiones, etc.)

`geih_2025` como nombre de importación tiene estos problemas:
1. El año implica que el paquete "vence" — un usuario en 2028 dudará
   antes de instalar algo llamado 2025.
2. Ya soporta 2022-2026+. El nombre dice una cosa, el código hace otra.
3. Si algún día lo renombras a `geih`, *rompes* todo el código de todos
   los usuarios (`from geih_2025 import` deja de funcionar).

### La solución: cambiar solo el nombre de distribución

```
pip install geih-analisis        ← nombre nuevo, PyPI
from geih_2025 import ConfigGEIH ← nombre existente, sin cambios
```

Así el cambio es completamente invisible para todo el código existente.
Los usuarios nuevos lo instalan con `geih-analisis`, pero el código
que ya escribiste (y todo lo que documentes) sigue usando `geih_2025`.

### Cuándo y cómo migrar el nombre de importación (futuro)

Si en 2027 decides que `geih_2025` ya no tiene sentido y quieres
llamarlo simplemente `geih`:
1. Creas el nuevo paquete `geih` que importa todo de `geih_2025`
2. En `geih_2025` pones un warning de deprecación: `DeprecationWarning: use 'geih' instead`
3. Das 6 meses de período de transición donde ambos funcionan
4. Publicas `geih_2025` como "deprecated" en PyPI
Este proceso se llama *deprecation path* y es como lo hacen todos los
paquetes profesionales cuando cambian nombres.

---

## Paso 2: Por qué publicar desde Colab es diferente a publicar desde local

### El problema central

En tu máquina local, git tiene acceso al sistema de archivos y guarda
las credenciales de GitHub en el keychain. En Colab, el entorno se
destruye con cada sesión — no hay keychain, no hay credenciales
persistentes, y el sistema de archivos de /content desaparece.

La solución son los **Colab Secrets**: un almacén cifrado de valores
sensibles que persiste entre sesiones y se puede leer con `userdata.get()`.
Es lo equivalente a las variables de entorno en sistemas locales.

### Por qué copiar a /content antes de hacer git

Google Drive tiene un overhead de I/O muy alto para operaciones git
porque cada acceso a un archivo implica una solicitud de red. Un
`git add -A` sobre una carpeta en Drive con 50 archivos puede tomar
30 segundos. El mismo comando sobre /content (SSD local de Colab)
toma 0.3 segundos. La solución: copiar de Drive a /content, operar
localmente, y el resultado queda en GitHub/PyPI (que son externos,
no en Drive).

---

## Paso 3: El flujo de publicación en detalle

```
Google Drive (fuente de verdad del código)
    ↓ shutil.copytree() — excluye *.parquet, *.csv, resultados/
/content/geih_build (directorio de trabajo temporal)
    ├── geih_2025/          ← código Python
    ├── pyproject.toml      ← metadatos generados por el notebook
    ├── README.md
    ├── LICENSE
    └── .gitignore

[Paso GitHub]
    git init + git add + git commit
    git push → github.com/usuario/geih-analisis
    git tag v4.3.1 → github.com/usuario/geih-analisis/releases

[Paso build]
    python -m build → dist/
        geih_analisis-4.3.1-py3-none-any.whl  (rueda, instalación rápida)
        geih_analisis-4.3.1.tar.gz             (fuente, para auditoría)

[Paso twine check]
    Verifica que los archivos cumplen estándares PyPI
    antes de intentar subir (fail fast)

[Paso twine upload]
    Si subir_a_pypi_real=False → TestPyPI (seguro, para probar)
    Si subir_a_pypi_real=True  → PyPI real (visible para el mundo)
```

---

## Paso 4: Semver — cómo numerar las versiones

El estándar es `MAJOR.MINOR.PATCH` (ej: `4.3.1`):

| Tipo | Cuándo | Ejemplo |
|---|---|---|
| PATCH | Bug fix, sin nueva funcionalidad | 4.3.0 → 4.3.1 |
| MINOR | Nueva funcionalidad, compatible | 4.3.0 → 4.4.0 |
| MAJOR | Cambio que rompe compatibilidad | 4.3.0 → 5.0.0 |

Romper compatibilidad significa que el código existente de los usuarios
deja de funcionar sin modificaciones. Ejemplos: renombrar una clase,
cambiar la firma de una función, eliminar un parámetro.

La regla práctica: mientras el paquete esté en desarrollo activo y
los usuarios sean principalmente internos de ProColombia, puedes usar
MINOR libremente. Cuando haya usuarios externos que dependen de la API,
sé más conservador con los cambios MINOR y cuidadoso con los MAJOR.

---

## Paso 5: TestPyPI vs PyPI real — nunca saltar el paso de prueba

TestPyPI es un servidor de prueba idéntico al real pero aislado.
Publicar allí tiene cero consecuencias: si algo sale mal, simplemente
publicas de nuevo. Las ventajas:

1. **Verifica el proceso completo**: el build, el upload, la instalación
2. **Verifica los metadatos**: que la descripción, el README y los links
   aparecen correctamente en la página del paquete
3. **Detecta errores de nombre**: si el nombre ya está tomado en PyPI real,
   lo descubres en TestPyPI sin problemas

El flujo recomendado:
```
TestPyPI (siempre) → revisar página web → PyPI real (solo si todo OK)
```

Para probar la instalación desde TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            geih-analisis
```
El `--extra-index-url` es necesario porque las dependencias
(pandas, numpy, etc.) no están en TestPyPI — las busca en el PyPI real.

---

## Paso 6: Los tokens — gestión de secretos en Colab

### Por qué nunca escribir tokens en el código

Un token de GitHub con permisos de repositorio permite hacer push,
crear issues, acceder a código privado. Si queda en un notebook
que se comparte o en el historial de git, es una vulnerabilidad real.

Los Colab Secrets resuelven esto: están cifrados, no aparecen en
el historial de celdas, y se pueden revocar desde GitHub/PyPI sin
tocar el código.

### Tipos de tokens que necesitas

**GitHub Personal Access Token (Classic)**:
- Permisos mínimos necesarios: `repo` (acceso completo al repositorio)
- Dónde crearlo: GitHub → Settings → Developer settings → Personal access tokens
- Duración recomendada: 90 días (renovar cuando expire)

**PyPI API Token**:
- Scope recomendado: "Specific project" en vez de "Entire account"
  (más seguro — si el token se compromete, solo afecta ese paquete)
- Dónde crearlo: pypi.org → Account settings → API tokens
- Empieza siempre con `pypi-`

---

## Paso 7: Qué falta para tener un paquete verdaderamente profesional

El notebook hace GitHub + PyPI. Para el siguiente nivel:

**1. GitHub Actions** (automatización):
Cuando crees un Release en GitHub, el build y el upload a PyPI
suceden automáticamente sin correr el notebook. Solo tienes que
crear el Release con el tag correcto.

**2. Tests en CI**:
Cada push a GitHub corre los 71 tests automáticamente.
Si alguno falla, GitHub te avisa antes de publicar.

**3. Documentación automática** (Read the Docs):
Los docstrings del paquete se convierten en una página web
de documentación automáticamente. La URL sería
`geih-analisis.readthedocs.io`.

**4. CHANGELOG.md**:
Un archivo que documenta qué cambió en cada versión.
Es lo primero que leen los usuarios antes de actualizar.

---

## Paso 8: Lo que un experto vería

### `py.typed` — un marcador de 0 bytes que cambia todo

El archivo `py.typed` que crea el notebook le dice a mypy, pyright
y los IDEs que el paquete soporta type hints. Sin él, el IDE no
muestra autocompletado de tipos cuando importas el paquete.
Es un archivo vacío que tarda 0 segundos en crear y mejora la
experiencia de usuario de forma significativa.

### El `pyproject.toml` moderno vs el `setup.py` viejo

El notebook genera `pyproject.toml`, no `setup.py`. Desde 2021,
`pyproject.toml` es el estándar oficial de Python (PEP 517/518).
`setup.py` sigue funcionando pero está en proceso de deprecación.
La diferencia técnica: `pyproject.toml` es declarativo (datos puros),
`setup.py` es código ejecutable (necesitas correr Python para leerlo,
lo que crea problemas de seguridad y reproducibilidad).

### `py3-none-any.whl` — qué significa el nombre del wheel

```
geih_analisis-4.3.1-py3-none-any.whl
                     ↑    ↑    ↑
                     │    │    └─ any CPU architecture (no compilado)
                     │    └────── none (no extensiones C)
                     └─────────── Python 3.x compatible
```
Un paquete "none-any" es el ideal: funciona en cualquier SO,
cualquier arquitectura, cualquier Python 3.x. Esto es posible porque
el paquete es Python puro (sin extensiones C como numpy tiene).

---

## Paso 9: Lecciones que aplican a cualquier proyecto

### Lección 1: Nombre de distribución ≠ nombre de importación

Esta separación existe en muchos paquetes famosos y es una herramienta
poderosa para evolucionar el nombre de un paquete sin romper el código
existente. Aprenderla temprano evita el problema doloroso de tener
que hacer una migración forzada más tarde.

### Lección 2: TestPyPI antes de PyPI siempre

En ingeniería de software hay un principio: nunca haces el deploy
a producción directamente. Siempre hay un ambiente de staging.
TestPyPI es tu staging. No hay razón para saltárselo.

### Lección 3: Los secretos no van en el código, nunca

Tokens, contraseñas, claves API: ninguno en el código, ninguno en
comentarios, ninguno en archivos de configuración que se suban a git.
El historial de git es permanente — incluso si borras el token del código
actual, sigue estando en el historial a menos que hagas un rebase completo.
La solución son las variables de entorno o los sistemas de secretos
(Colab Secrets, AWS Secrets Manager, GitHub Secrets, etc.).

### Lección 4: Semver es un contrato con tus usuarios

Cuando publicas con semver, les estás diciendo: "si solo cambia
el PATCH, puedes actualizar con ojos cerrados". Si rompes ese contrato
(un PATCH que rompe código), pierdes la confianza de los usuarios.
Es mejor sobre-versionar (un MINOR cuando era PATCH) que bajo-versionar.

---

*Generado automáticamente como parte del flujo de aprendizaje continuo.*
*Pipeline: `geih_2025 v4.3.0` | ProColombia · GIC*
