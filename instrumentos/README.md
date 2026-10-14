# Instrumentos de investigación

Instrumentos del apartado 3.6 del documento de tesis, reunidos aquí para que
puedan aplicarse y validarse. Corresponden a la Tabla 12 (*Instrumentos de la
investigación*).

| Archivo | Instrumento | Se aplica a | Naturaleza |
|---|---|---|---|
| `guion_entrevista_docentes.md` | Guion de entrevista semiestructurada | Docentes | Cualitativo |
| `encuesta_carga_planeacion.md` | Encuesta de carga de planeación | Docentes | Cuantitativo |
| `rubrica_calidad_pedagogica.md` | Rúbrica de calidad pedagógica | Docentes | Cuantitativo |
| `escala_usabilidad_sus.md` | Escala de usabilidad del sistema (SUS) | Docentes y estudiantes | Cuantitativo |
| `cuestionario_aceptacion_tecnologica.md` | Cuestionario de aceptación tecnológica (TAM) | Docentes | Cuantitativo |

## Cómo se relacionan con el sistema

- La **rúbrica** valora el material que el docente genera y revisa en la
  pantalla *Revisar material* del panel docente.
- La **escala SUS** y el **cuestionario de aceptación** se responden después de
  que el docente usa el prototipo completo.
- Las dos **medidas objetivas** que pide el apartado 3.6.1 —proporción de
  material aceptado sin edición y tiempo de edición por material— no se
  recogen con un cuestionario: las calcula el propio sistema. El panel del
  docente las muestra en la sección *Métricas* (`GET /teacher/metrics`) a
  partir de las decisiones registradas (`GET /teacher/materials`).

## Pendientes de validación

Tal como señala el apartado 3.6.1, la rúbrica se somete a validación de
contenido por juicio de expertos y su confiabilidad entre evaluadores se estima
con el coeficiente kappa de Cohen sobre una submuestra evaluada por pares. Los
instrumentos aquí reunidos son la versión de trabajo, lista para esa validación.
