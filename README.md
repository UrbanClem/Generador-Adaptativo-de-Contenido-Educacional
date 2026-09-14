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
pytest tests/ -v                    # 34 pruebas, entre 1 y 2 minutos
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
| `rag_engine.py` | Índice vectorial (ChromaDB) sobre `knowledge/` |
| `student_profile.py`, `dynamic_profile.py`, `learning_metrics.py` | Perfil del estudiante y métricas |
| `frontend/` | Interfaz del estudiante (HTML, CSS y JavaScript) |
| `knowledge/` | Corpus de referencia en texto plano |
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
  dan 22 fragmentos.
- **Las explicaciones salen del material del curso.** `generate_explanation()`
  recupera tres fragmentos, descarta los que no tratan el tema y solo con los
  que quedan arma el prompt; `/explain` devuelve además la lista de archivos
  usados, que el frontend muestra al pie de la explicación.
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

Hay **34 pruebas automatizadas** en `tests/`: 16 unitarias, 9 de seudonimización y los 9 casos
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

Las cuatro líneas declaradas en el borrador de tesis:

1. Interfaz de docente (no existe todavía).
2. Carga de corpus propio por parte del docente.
3. Mostrar el fragmento de origen junto a cada material generado (hecho a
   medias: se muestra el archivo, falta el fragmento).
4. Registrar la decisión de aceptación o edición del docente.

Además, los ejercicios y la retroalimentación todavía no usan la recuperación:
solo las explicaciones están ancladas al material.
