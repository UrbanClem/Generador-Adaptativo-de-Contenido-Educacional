"""Configuración central del prototipo.

Todo lo que cambia entre máquinas (base de datos, modelo de lenguaje) se lee
de aquí, y se puede sobrescribir con variables de entorno o con un archivo
`.env` en esta misma carpeta.

Variables:
    DATABASE_URL   cadena de conexión de SQLAlchemy.
                   Por defecto SQLite en `education.db`, junto a este archivo.
                   Para volver a PostgreSQL:
                   postgresql://postgres:admin@localhost:5432/rag_education
    OLLAMA_MODEL   modelo de Ollama para generación (por defecto mistral:latest).
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_SQLITE_PATH = os.path.join(BASE_DIR, "education.db").replace(os.sep, "/")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + _SQLITE_PATH)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")

KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
# Material que sube el docente (RF11). Vive aparte del corpus de referencia
# para poder distinguir el uno del otro y borrar solo lo que el docente cargó.
KNOWLEDGE_DOCENTE = os.path.join(KNOWLEDGE_DIR, "docente")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
