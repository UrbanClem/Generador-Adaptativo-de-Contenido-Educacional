# educacion_backend

Prototipo del proyecto de tesis **Generador Adaptativo de Contenidos
Educativos con IA**: diagnóstico adaptativo por atributos cognitivos y
generación de explicaciones y ejercicios de ecuaciones de primer grado con un
modelo de lenguaje local y recuperación sobre un corpus propio.

## Cómo correrlo

Desde cero, recién clonado:

```bash
git clone git@github.com:UrbanClem/Generador-Adaptativo-de-Contenido-Educacional.git
cd Generador-Adaptativo-de-Contenido-Educacional

pip install -r requirements.txt     # Python 3.12
ollama pull mistral                 # ~4 GB, una sola vez
ollama serve                        # en otra terminal, se queda corriendo

python main_api.py                  # http://localhost:5000
```

Para comprobar que quedó bien instalado:

```bash
pytest tests/ -v                    # 49 pruebas, entre 1 y 2 minutos
```

No hace falta instalar nada de base de datos: por defecto usa **SQLite**, en
`education.db`, que se crea sola la primera vez. Tampoco hay que indexar el
corpus a mano: la base vectorial se construye en el primer arranque a partir
de los documentos de `knowledge/`, y eso tarda un poco más que los siguientes.

`education.db` **no está en el repositorio** y no debe subirse: guarda los
datos de las sesiones. Cada quien tiene la suya.

## Configuración

Todo lo que cambia entre máquinas está en `config.py` y se puede sobrescribir
con variables de entorno o con un archivo `.env` en esta carpeta:

| Variable | Por defecto | Para qué |
|---|---|---|
| `DATABASE_URL` | `sqlite:///education.db` | Base de datos |
| `OLLAMA_MODEL` | `mistral:latest` | Modelo de generación |

Para volver a PostgreSQL (así estuvo hasta septiembre de 2026), basta con:

```
DATABASE_URL=postgresql://postgres:admin@localhost:5432/rag_education
```

Para probar con un modelo más ligero, `OLLAMA_MODEL=llama3.2:1b`: responde
mucho más rápido, pero inventa más ecuaciones mal planteadas.

## Estructura

| Archivo | Qué hace |
|---|---|
| `main_api.py` | API en Flask y servidor del frontend |
| `config.py` | Base de datos y modelo configurables |
| `database.py` | Modelos de SQLAlchemy; crea las tablas y agrega columnas faltantes |
| `cognitive_diagnostic.py` | Perfil cognitivo, matriz Q, generación de reactivos y solucionador con sympy |
| `content_generator.py` | Explicaciones, ejercicios y retroalimentación |
| `rag_engine.py` | Índice vectorial (ChromaDB) sobre `knowledge/` y el corpus del docente |
| `docente_utils.py` | Medidas objetivas del panel del docente y saneo de nombres del corpus |
| `student_profile.py`, `dynamic_profile.py`, `learning_metrics.py` | Perfil del estudiante y métricas |
| `frontend/` | Interfaz del estudiante y panel del docente (HTML, CSS y JavaScript) |
| `knowledge/` | Corpus de referencia en texto plano (`knowledge/docente/` guarda lo que sube el docente) |
| `instrumentos/` | Rúbrica de calidad, SUS, cuestionario de aceptación, encuesta de carga y guion de entrevista |
| `main.py` | Versión de línea de comandos, anterior a la web |

## Notas

- **Las respuestas no las calcula el modelo, las calcula sympy.** El modelo
  propone la ecuación y `ajustar_a_entero()` la corrige: mistral falla en
  cerca del 80% de los casos (de `8x + 17 = 23` sale x = 0.75), así que se
  recorre el término independiente lo mínimo para que la solución sea entera
  (`8x + 17 = 25`, x = 1), respetando estructura y paréntesis.
- El diagnóstico tarda entre 15 y 30 segundos en arrancar y la explicación
  cerca de un minuto: es mistral 7B corriendo local, no es que se haya
  trabado.
- La base de conocimiento se indexa sola la primera vez que arranca el
  servidor y queda guardada en `chroma_db/`. Los documentos se guardan
  **troceados** en fragmentos de ~700 caracteres, cortados en los renglones en
  blanco para no partir un ejemplo a la mitad; los 13 archivos de `knowledge/`
  dan 22 fragmentos. El docente puede subir sus propios `.txt` desde la sección
  *Corpus* del panel: se guardan en `knowledge/docente/` y el índice se
  reconstruye solo (RF11).
- **Las explicaciones salen del material del curso.** `generate_explanation()`
  recupera tres fragmentos, descarta los que no tratan el tema y solo con los
  que quedan arma el prompt. `/explain` devuelve los archivos usados y los
  **fragmentos completos** que sustentan la respuesta (RF12), que el frontend
  muestra al pie de la explicación. Los ejercicios (`/exercises`) y la
  retroalimentación (`/feedback`) también se anclan al material recuperado, no
  solo las explicaciones.
- **Si el tema no está en el corpus, no se explica nada.** Se responde que el
  material no lo cubre y se listan los temas que sí, sin llamar al modelo. La
  regla en el prompt no bastaba: con "derivadas" mistral se inventó una
  explicación, y equivocada (`d/dx(-2) = -1`), aunque tenía prohibido salirse
  del material.
- **El filtro de pertinencia lo hace el propio modelo, no la distancia del
  vector.** `all-MiniLM-L6-v2` está entrenado en inglés y en español los
  valores se enciman: "despejar la incógnita" (sí está en el material) queda a
  0.693 y "números complejos" (no está) a 0.459, así que ningún umbral los
  separa. En cambio, preguntarle a mistral "¿este material sirve para explicar
  X?" con `num_predict=3` acierta 14 de 16 temas de prueba y cuesta menos de
  un segundo por fragmento.

## Pruebas

Hay **49 pruebas automatizadas** en `tests/`: 16 unitarias, 9 de seudonimización, 15 del panel del docente y los 9 casos
funcionales CP01–CP09 de la tabla 13 del documento de tesis. Se corren desde
esta carpeta:

```bash
C:/Python312/python.exe -m pytest tests/ -v
```

Cubren lo que sostiene que el contenido sea correcto: el solucionador
algebraico, la corrección a solución entera (conservando paréntesis), la
verificación de respuestas por sustitución, el troceado del corpus, el anclaje
documental y el respaldo ante caída del servicio. CP06 y CP07 llaman al modelo
de verdad, así que necesitan `ollama serve`; si no está levantado se saltan
solos y el resto sigue corriendo. Detalle completo en `tests/README.md`.

## Datos de los participantes

El nombre que escribe el estudiante **no se guarda**. `seudonimo.py` calcula
una huella con sal (SHA-256) y la base almacena un código correlativo —`E01`,
`E02`— junto con esa huella. Quien abra `education.db` ve el código y una
cadena hexadecimal: puede seguir el avance de un participante a lo largo de la
sesión, que es lo que la investigación necesita, sin saber de quién se trata.

El nombre escrito se queda únicamente en el navegador, para el saludo de la
pantalla principal, y se borra al cerrar sesión.

La sal se lee de `SEUDONIMO_SALT`. **Para las sesiones de evaluación conviene
poner una propia** en el `.env`: con la de por defecto, alguien que conozca el
código podría probar nombres hasta dar con la huella.

Esto cumple lo que compromete el apartado 3.6.2 del documento de tesis, y las
pruebas de `tests/test_seudonimo.py` lo verifican.

## Pendientes

Las cuatro líneas declaradas en el borrador de tesis ya están cubiertas:

1. ~~Interfaz de docente (no existe todavía).~~ Hecha: panel del docente para
   crear tareas y actividades (`/teacher/assignments`) y para **revisar, editar,
   aceptar o rechazar** material generado (`/teacher/material/generate`,
   `/teacher/material/decision`).
2. ~~Carga de corpus propio por parte del docente.~~ Hecha: sección *Corpus* del
   panel y endpoints `GET/POST /teacher/corpus`, `DELETE /teacher/corpus/<nombre>`;
   al subir o borrar un documento el índice se reconstruye solo.
3. ~~Mostrar el fragmento de origen junto a cada material generado.~~ Hecho:
   `/explain`, `/exercises` y el generador del panel devuelven los fragmentos
   completos (texto y archivo), no solo el nombre del archivo.
4. ~~Registrar la decisión de aceptación o edición del docente.~~ Hecho: cada
   decisión se guarda con la decisión, el tiempo empleado y los fragmentos
   (`material_reviews`); `GET /teacher/metrics` calcula la proporción de
   material aceptado sin edición y el tiempo de edición por material.

Además, los ejercicios y la retroalimentación ya usan la recuperación: se anclan
a los fragmentos del corpus igual que las explicaciones.

Los instrumentos de evaluación del apartado 3.6 (rúbrica de calidad, SUS,
cuestionario de aceptación, encuesta de carga y guion de entrevista) están en
`instrumentos/`, listos para su validación por juicio de expertos.
