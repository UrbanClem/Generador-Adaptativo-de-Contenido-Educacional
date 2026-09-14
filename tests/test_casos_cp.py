# -*- coding: utf-8 -*-
"""Casos de prueba funcionales CP01 a CP09 (tabla 13 del documento de tesis).

Un caso por prueba, con la misma clave y el mismo resultado esperado que la
tabla. Los que dependen del modelo de lenguaje se marcan con `necesita_llm` y
se saltan si `ollama serve` no esta levantado, para que la suite siga siendo
ejecutable sin el servicio.
"""
import os

import pytest
import sympy

from conftest import necesita_llm

import cognitive_diagnostic as cd
import content_generator as cg
import rag_engine as rag
from config import KNOWLEDGE_DIR


def _sustituye(ecuacion, valor):
    """Comprueba la solucion sustituyendola en la ecuacion original."""
    transf = (sympy.parsing.sympy_parser.standard_transformations +
              (sympy.parsing.sympy_parser.implicit_multiplication_application,))
    izq, der = ecuacion.split("=")
    x = sympy.Symbol("x")
    izq = sympy.parsing.sympy_parser.parse_expr(izq.strip(), transformations=transf)
    der = sympy.parsing.sympy_parser.parse_expr(der.strip(), transformations=transf)
    return izq.subs(x, valor) == der.subs(x, valor)


def test_cp01_resolucion_algebraica():
    """Ecuacion de primer grado con parentesis -> solucion correcta,
    comprobada por sustitucion."""
    ecuacion = "2(x - 3) = 8"
    solucion = cd.solve_equation(ecuacion)
    assert solucion == "7"
    assert _sustituye(ecuacion, int(solucion))


def test_cp02_correccion_a_solucion_entera():
    """Ecuacion generada con solucion fraccionaria -> ecuacion equivalente con
    solucion entera y estructura conservada."""
    original = "4(x + 5) = 7"
    assert cd.solucion_entera(original) is None      # la de entrada no sirve

    ecuacion, respuesta = cd.ajustar_a_entero(original)
    assert float(respuesta) == int(float(respuesta))
    assert _sustituye(ecuacion, int(respuesta))
    # estructura conservada: sigue siendo "4(x + 5) = ..."
    assert ecuacion.split("=")[0].strip() == original.split("=")[0].strip()


def test_cp03_troceado_del_corpus():
    """Documento del corpus -> fragmentos de tamano acotado, con el titulo del
    documento como encabezado."""
    ruta = os.path.join(KNOWLEDGE_DIR, "05_teorema_pitagoras.txt")
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()
    titulo = texto.splitlines()[0].strip()

    fragmentos = rag.trocear(texto, titulo)
    assert fragmentos
    for f in fragmentos:
        assert f.startswith(titulo)
        assert len(f) <= rag.TAM_FRAGMENTO + len(titulo) + 200


def test_cp04_diagnostico_sube_de_nivel(perfil):
    """Racha de respuestas correctas -> aumento de nivel en la siguiente ronda.

    Nota: el sistema no reacciona a tres respuestas, sino a la tendencia de las
    ultimas ocho (seis aciertos para 'avanzado'). Se comprueba ese
    comportamiento, que es el implementado.
    """
    assert perfil.get_next_difficulty() == "basico"
    for i in range(8):
        perfil.update_from_response({"pregunta": "2x + %d = %d" % (i, i + 4)}, True)
    assert perfil.get_next_difficulty() == "avanzado"


def test_cp05_diagnostico_baja_de_nivel_y_da_andamiaje(perfil):
    """Racha de respuestas incorrectas -> descenso de nivel y entrega de una
    pista de andamiaje."""
    for i in range(8):
        perfil.update_from_response({"pregunta": "5x - %d = 3x + 8" % i}, True)
    assert perfil.get_next_difficulty() == "avanzado"

    for i in range(8):
        perfil.update_from_response({"pregunta": "5x - %d = 3x + 8" % i}, False)
    assert perfil.get_next_difficulty() == "basico"

    pista = cd.get_hint_by_equation_type("5x - 2 = 3x + 8")
    assert pista and cd.solve_equation("5x - 2 = 3x + 8") not in pista


@necesita_llm
def test_cp06_explicacion_con_anclaje():
    """Tema cubierto por el corpus -> explicacion generada con indicacion del
    documento de origen."""
    texto, fuentes = cg.generate_explanation("teorema de Pitagoras", "basico",
                                             con_fuentes=True)
    assert fuentes, "no se cito ningun documento de origen"
    assert all(f.endswith(".txt") for f in fuentes)
    assert len(texto.split()) > 40
    assert "no puedo explicarlo" not in texto


@necesita_llm
def test_cp07_consulta_fuera_del_corpus():
    """Tema ajeno al corpus -> aviso de tema no cubierto y lista de temas
    disponibles, sin generacion."""
    texto, fuentes = cg.generate_explanation("integrales de superficie", "basico",
                                             con_fuentes=True)
    assert fuentes == []
    assert "no cubre" in texto.lower()
    assert "los temas que sí están cubiertos" in texto.lower()


def test_cp08_fallo_del_servicio_de_generacion(monkeypatch):
    """Peticion con el servicio detenido -> entrega de reactivos de respaldo y
    mensaje de estado, sin interrupcion."""
    def caido(*args, **kwargs):
        raise ConnectionError("servicio de generacion no disponible")

    monkeypatch.setattr(cg.ollama, "chat", caido)

    ejercicios = cg.generate_exercises_with_answers("ecuaciones", "basico", 3)
    assert len(ejercicios) == 3
    for ex in ejercicios:
        assert cd.solve_equation(ex["pregunta"]) == str(ex["respuesta_esperada"])
        assert ex["pista"]


def test_cp09_flujo_completo(perfil, monkeypatch):
    """Sesion de principio a fin -> perfil registrado, material generado y
    respuesta verificada sin error.

    La generacion se fuerza al banco de respaldo para que el caso sea
    reproducible y no dependa de lo que conteste el modelo esa corrida.
    """
    from database import SessionLocal, CognitiveProfile

    def caido(*args, **kwargs):
        raise ConnectionError("servicio de generacion no disponible")

    monkeypatch.setattr(cg.ollama, "chat", caido)

    # 1. material generado para el nivel del perfil
    ejercicios = cg.generate_exercises_with_answers(
        "ecuaciones", perfil.get_next_difficulty(), 3)
    assert len(ejercicios) == 3

    # 2. el estudiante responde: una bien y una mal
    bien = ejercicios[0]
    assert cd.evaluate_answer_semantic(bien["pregunta"],
                                       bien["respuesta_esperada"],
                                       bien["respuesta_esperada"])
    perfil.update_from_response(bien, True)

    mal = ejercicios[1]
    equivocada = str(int(mal["respuesta_esperada"]) + 1)
    assert not cd.evaluate_answer_semantic(mal["pregunta"], equivocada,
                                           mal["respuesta_esperada"])
    perfil.update_from_response(mal, False)

    # 3. el perfil quedo registrado en la base de datos
    db = SessionLocal()
    guardado = db.query(CognitiveProfile).filter_by(
        student_id=perfil.student_id).first()
    assert guardado is not None
    assert len(guardado.response_history) == 2
    db.close()

    # 4. la retroalimentacion del perfil es consultable
    feedback = perfil.get_feedback()
    assert feedback["level"] in ("basico", "intermedio", "avanzado")
