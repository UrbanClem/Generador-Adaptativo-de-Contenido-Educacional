# Pruebas del prototipo

Conjunto de pruebas automatizadas del apartado 3.6 del documento de tesis.
Son **25**: 16 unitarias y los 9 casos funcionales CP01–CP09 de la tabla 13.

## Cómo se corren

Desde `educacion_backend/`:

```bash
PYTHONIOENCODING=utf-8 C:/Python312/python.exe -m pytest tests/ -v
```

Para ver sólo los casos funcionales:

```bash
C:/Python312/python.exe -m pytest tests/test_casos_cp.py -v
```

Requisitos: `pytest` (en el Python 3.12 del usuario, no en el `.venv` de la
carpeta) y, para CP06 y CP07, `ollama serve` levantado con el modelo de
`config.py`. Si Ollama no está corriendo esos dos casos se marcan como
*skipped* y el resto sigue corriendo.

La suite completa tarda entre uno y dos minutos y medio: CP06 y CP07 llaman al
modelo de verdad, no lo simulan.

## Qué cubre cada archivo

- **`conftest.py`** — apunta la base de datos a un archivo temporal **antes**
  de importar cualquier módulo del proyecto, porque `database.py` crea el
  engine al importarse leyendo `config.DATABASE_URL`. Así las pruebas no tocan
  `education.db`, que trae los datos de las sesiones reales. También define el
  marcador `necesita_llm`.

- **`test_unitarias.py`** — las funciones de las que depende que el contenido
  sea correcto, aisladas del modelo:
  - `solve_equation` con las tres formas que devuelve el modelo (`5x`, `5*x`,
    `2(x - 3)`), y que devuelve `None` en vez de adivinar cuando no puede.
  - `solucion_entera` descarta las fraccionarias.
  - `ajustar_a_entero`: corrige el caso documentado (`8x + 17 = 23`, x = 0.75),
    **conserva los paréntesis** (si se distribuyen, el reactivo deja de
    ejercitar el atributo A4), nunca entrega x = 0, y la respuesta que devuelve
    siempre resuelve la ecuación —comprobado por sustitución simbólica sobre
    ocho ecuaciones.
  - `evaluate_answer_semantic` acepta `4`, `x = 4`, `4.0` y espacios, y rechaza
    la respuesta vacía y la incorrecta.
  - `trocear` pone el título en cada fragmento y no pierde texto.
  - Las pistas corresponden al tipo de ecuación y **nunca contienen la
    respuesta**.
  - El banco de respaldo entrega la cantidad pedida y **sus respuestas son
    correctas**: si el banco trae un error, el estudiante lo ve justo cuando el
    modelo falló.

- **`test_casos_cp.py`** — un caso por clave, con el resultado esperado de la
  tabla 13:

  | Caso | Qué comprueba |
  |---|---|
  | CP01 | Resuelve `2(x - 3) = 8` y comprueba la solución por sustitución |
  | CP02 | Corrige una ecuación fraccionaria conservando el lado izquierdo |
  | CP03 | Trocea un documento real del corpus con el título como encabezado |
  | CP04 | Una racha de aciertos sube el nivel del perfil |
  | CP05 | Una racha de errores lo baja y entrega pista de andamiaje |
  | CP06 | Explica un tema del corpus **citando el archivo de origen** (usa el modelo) |
  | CP07 | Ante un tema ajeno avisa y lista los temas cubiertos, sin generar (usa el modelo) |
  | CP08 | Con el servicio caído entrega reactivos de respaldo y sigue operando |
  | CP09 | Flujo completo: perfil registrado, material generado, respuesta verificada |

## Notas

- **CP04 y CP05 no reaccionan a tres respuestas consecutivas**, como decía la
  primera versión de la tabla 13: `update_from_response` decide por la
  tendencia de las últimas ocho (seis aciertos para `avanzado`). Las pruebas
  comprueban el comportamiento implementado y la tabla del documento se
  corrigió para que coincida.
- CP08 y CP09 simulan la caída del servicio sustituyendo `ollama.chat` por una
  función que lanza excepción. Es la forma de provocar el fallo sin tener que
  apagar Ollama a media corrida.
- `attribute_mastery` (los seis atributos de la matriz Q) **se inicializa,
  se guarda y se lee, pero ninguna línea la actualiza a partir de las
  respuestas**: se queda en 0.0. Por eso no hay prueba que lo cubra. Es un
  pendiente real del prototipo, no un descuido de la suite.
