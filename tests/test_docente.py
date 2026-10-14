# -*- coding: utf-8 -*-
"""Pruebas de las funciones nuevas del panel docente (RF10 a RF13 y RF11).

Cubren la lógica que no depende del modelo de lenguaje: el cálculo de las
medidas objetivas, el saneo de nombres del corpus, el guardado de las
decisiones y el anclaje de ejercicios y retroalimentación al material
recuperado (que se comprueba interceptando el prompt enviado al modelo).
"""
import json

import pytest

import docente_utils
import content_generator as cg
import rag_engine as rag


# ---------- Medidas objetivas (apartado 3.6.1) ----------

def test_metricas_sin_revisiones():
    m = docente_utils.calcular_metricas([])
    assert m["total"] == 0
    assert m["aceptacion_sin_edicion"] == 0.0
    assert m["tiempo_medio"] == 0.0


def test_metricas_calculan_proporcion_y_tiempos():
    reviews = [
        {"decision": "aceptado", "segundos": 10},
        {"decision": "aceptado", "segundos": 20},
        {"decision": "editado", "segundos": 40},
        {"decision": "rechazado", "segundos": 30},
    ]
    m = docente_utils.calcular_metricas(reviews)
    assert m["total"] == 4
    assert m["aceptados"] == 2
    assert m["aceptacion_sin_edicion"] == 0.5
    assert m["tiempo_medio"] == 25.0
    assert m["tiempo_medio_edicion"] == 40.0


def test_metricas_aceptan_objetos_no_solo_diccionarios():
    class Fila:
        def __init__(self, decision, segundos):
            self.decision = decision
            self.segundos = segundos

    m = docente_utils.calcular_metricas([Fila("aceptado", 5), Fila("rechazado", 0)])
    assert m["aceptados"] == 1
    assert m["tiempo_medio"] == 5.0


# ---------- Saneo de nombres del corpus (RF11) ----------

@pytest.mark.parametrize("entrada,esperado", [
    ("tema", "tema.txt"),
    ("tema.TXT", "tema.TXT"),
    ("carpeta/tema.txt", "tema.txt"),
    ("..\\..\\windows\\system32.txt", "system32.txt"),
])
def test_nombre_corpus_seguro(entrada, esperado):
    assert docente_utils.nombre_corpus_seguro(entrada) == esperado


def test_nombre_corpus_rechaza_vacios_y_escape():
    assert docente_utils.nombre_corpus_seguro("") is None
    assert docente_utils.nombre_corpus_seguro("   ") is None
    assert docente_utils.nombre_corpus_seguro("..") is None


def test_clave_indice_distingue_el_origen():
    assert rag._clave_indice("a.txt", False) == "a.txt"
    assert rag._clave_indice("a.txt", True) == "docente/a.txt"


# ---------- Registro de la decisión (RF13) ----------

def test_material_review_se_persiste_con_fragmentos():
    from database import SessionLocal, MaterialReview

    db = SessionLocal()
    m = MaterialReview(
        tipo="explicacion", tema="teorema de Pitagoras", level="basico",
        contenido_original="original", contenido_final="editado",
        decision="editado", segundos=12.5,
        fragmentos=[{"fuente": "05_teorema_pitagoras.txt", "texto": "a2 + b2 = c2"}],
    )
    db.add(m)
    db.commit()
    mid = m.id
    assert mid

    guardado = db.query(MaterialReview).filter_by(id=mid).first()
    assert guardado.decision == "editado"
    assert guardado.segundos == 12.5
    assert guardado.fragmentos[0]["fuente"] == "05_teorema_pitagoras.txt"

    db.delete(guardado)
    db.commit()
    db.close()


def test_assignment_se_persiste():
    from database import SessionLocal, Assignment

    db = SessionLocal()
    a = Assignment(tipo="actividad", titulo="Practica", tema="ecuaciones",
                   level="intermedio",
                   content={"ejercicios": [{"pregunta": "x+1=2",
                                            "respuesta_esperada": "1"}]})
    db.add(a)
    db.commit()
    aid = a.id
    assert aid

    guardado = db.query(Assignment).filter_by(id=aid).first()
    assert guardado.tipo == "actividad"
    assert guardado.content["ejercicios"][0]["respuesta_esperada"] == "1"

    db.delete(guardado)
    db.commit()
    db.close()


# ---------- Anclaje documental en explicaciones, ejercicios y feedback ----------

def test_explicacion_devuelve_fragmentos(monkeypatch):
    """RF12: la explicación devuelve los fragmentos, no solo el archivo."""
    pasajes = [{"fuente": "05_teorema_pitagoras.txt", "texto": "El teorema dice a^2 + b^2 = c^2"}]
    monkeypatch.setattr(cg, "retrieve_pertinentes", lambda tema, n_results=3: pasajes)
    monkeypatch.setattr(cg.ollama, "chat",
                        lambda **kw: {"message": {"content": "explicacion de prueba"}})

    texto, fragmentos = cg.generate_explanation("teorema de Pitagoras", "basico",
                                                con_fragmentos=True)
    assert texto == "explicacion de prueba"
    assert fragmentos == pasajes


def test_explicacion_sin_material_no_devuelve_fragmentos(monkeypatch):
    monkeypatch.setattr(cg, "retrieve_pertinentes", lambda tema, n_results=3: [])
    monkeypatch.setattr(cg, "temas_disponibles", lambda: ["Ecuaciones basicas"])

    texto, fragmentos = cg.generate_explanation("integrales", "basico",
                                                con_fragmentos=True)
    assert fragmentos == []
    assert "no cubre" in texto.lower()


def test_ejercicios_incluyen_material_en_el_prompt(monkeypatch):
    capturado = {}

    def chat_falso(model=None, messages=None, **kw):
        capturado["prompt"] = messages[0]["content"]
        return {"message": {"content": json.dumps([
            {"pregunta": "2x + 3 = 11", "respuesta_esperada": "4",
             "pista": "Resta 3 y divide"}
        ])}}

    monkeypatch.setattr(cg.ollama, "chat", chat_falso)

    ejercicios = cg.generate_exercises_with_answers(
        "ecuaciones", "basico", 1,
        material="MATERIAL-UNICO-DEL-CURSO: despeja la incognita")

    assert len(ejercicios) == 1
    assert "MATERIAL-UNICO-DEL-CURSO" in capturado["prompt"]


def test_feedback_incluye_material_en_el_prompt(monkeypatch):
    capturado = {}

    def chat_falso(model=None, messages=None, **kw):
        capturado["prompt"] = messages[0]["content"]
        return {"message": {"content": "bien"}}

    monkeypatch.setattr(cg.ollama, "chat", chat_falso)

    cg.give_feedback("4", "4", "basico",
                     material="MATERIAL-UNICO-DEL-CURSO: suma en ambos lados")

    assert "MATERIAL-UNICO-DEL-CURSO" in capturado["prompt"]
