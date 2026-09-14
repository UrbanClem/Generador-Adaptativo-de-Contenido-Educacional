# -*- coding: utf-8 -*-
"""Configuracion comun de las pruebas.

Lo importante: la base de datos se apunta a un archivo temporal ANTES de
importar cualquier modulo del proyecto, porque `database.py` crea el engine
en tiempo de importacion leyendo `config.DATABASE_URL`. Asi las pruebas no
tocan `education.db`, que trae los datos de las sesiones reales.
"""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_BD = os.path.join(tempfile.gettempdir(), "test_education.db")
if os.path.exists(_BD):
    os.remove(_BD)
os.environ["DATABASE_URL"] = "sqlite:///" + _BD.replace(os.sep, "/")

import pytest  # noqa: E402
from database import Base, engine, SessionLocal, Student  # noqa: E402

Base.metadata.create_all(engine)


def hay_ollama():
    """True si el servicio de generacion responde."""
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


necesita_llm = pytest.mark.skipif(
    not hay_ollama(),
    reason="requiere `ollama serve` levantado con el modelo configurado",
)


@pytest.fixture
def alumno():
    """Crea un alumno de prueba y devuelve su id."""
    db = SessionLocal()
    a = Student(name="Alumno de prueba", level="basico")
    db.add(a)
    db.commit()
    sid = a.id
    db.close()
    return sid


@pytest.fixture
def perfil(alumno):
    from cognitive_diagnostic import CognitiveDiagnosticProfile
    return CognitiveDiagnosticProfile(alumno, "Alumno de prueba")
