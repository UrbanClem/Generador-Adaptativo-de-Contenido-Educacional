# -*- coding: utf-8 -*-
"""Pruebas unitarias: funciones que no dependen del modelo de lenguaje.

Cubren la parte del sistema de la que depende la correccion del contenido: el
solucionador algebraico, la correccion de los reactivos que propone el modelo,
la verificacion de la respuesta del estudiante y el troceado del corpus.
"""
import sympy

from cognitive_diagnostic import (solve_equation, solucion_entera,
                                  ajustar_a_entero, evaluate_answer_semantic,
                                  get_hint_by_equation_type)
from rag_engine import trocear
from content_generator import fallback_exercises


# ---------------------------------------------------------- solve_equation

def test_resuelve_las_formas_que_devuelve_el_modelo():
    """Acepta "5x", "5*x" y parentesis, que son las tres formas que salen."""
    assert solve_equation("5x - 17 = 8") == "5"
    assert solve_equation("5*x - 17 = 8") == "5"
    assert solve_equation("2(x - 3) = 8") == "7"


def test_devuelve_none_si_no_se_puede_interpretar():
    assert solve_equation("esto no es una ecuacion") is None
    assert solve_equation("3x + 1") is None          # sin signo igual
    assert solve_equation("x = x") is None           # infinitas soluciones


def test_solucion_entera_descarta_las_fraccionarias():
    assert solve_equation("3x - 7 = 6") is not None  # existe, pero no es entera
    assert solucion_entera("3x - 7 = 6") is None
    assert solucion_entera("2x + 3 = 11") == "4"


# --------------------------------------------------------- ajustar_a_entero

def test_no_toca_la_ecuacion_si_ya_da_entero():
    assert ajustar_a_entero("2x + 3 = 11") == ("2x + 3 = 11", "4")


def test_corrige_la_ecuacion_hasta_que_la_solucion_sea_entera():
    """El caso documentado: de 8x + 17 = 23 sale x = 0.75."""
    assert solve_equation("8x + 17 = 23") == "0.75"
    ecuacion, respuesta = ajustar_a_entero("8x + 17 = 23")
    assert float(respuesta) == int(float(respuesta))
    assert solve_equation(ecuacion) == respuesta


def test_conserva_los_parentesis_al_corregir():
    """Si se distribuye, el reactivo deja de ejercitar la propiedad
    distributiva: es el atributo A4 de la matriz Q."""
    ecuacion, _ = ajustar_a_entero("4(x + 5) = 7")
    assert "(" in ecuacion and ")" in ecuacion


def test_nunca_entrega_la_solucion_trivial_cero():
    for eq in ["5x + 2 = 2", "3x - 1 = -1", "7x + 10 = 10"]:
        resultado = ajustar_a_entero(eq)
        if resultado is not None:
            assert int(resultado[1]) != 0


def test_la_respuesta_que_devuelve_siempre_resuelve_la_ecuacion():
    """Lo que sostiene el apartado 3.7: la respuesta la calcula sympy."""
    for eq in ["8x + 17 = 23", "3x - 7 = 6", "5x + 4 = 18", "2(x - 3) = 9",
               "7x - 2 = 20", "4x + 11 = 30", "6(x + 1) = 15", "9x - 5 = 13"]:
        resultado = ajustar_a_entero(eq)
        assert resultado is not None, eq
        ecuacion, respuesta = resultado
        x = sympy.Symbol("x")
        izq, der = ecuacion.split("=")
        transf = (sympy.parsing.sympy_parser.standard_transformations +
                  (sympy.parsing.sympy_parser.implicit_multiplication_application,))
        izq = sympy.parsing.sympy_parser.parse_expr(izq.strip(), transformations=transf)
        der = sympy.parsing.sympy_parser.parse_expr(der.strip(), transformations=transf)
        assert izq.subs(x, int(respuesta)) == der.subs(x, int(respuesta)), ecuacion


# -------------------------------------------------- evaluate_answer_semantic

def test_acepta_la_respuesta_escrita_de_varias_formas():
    assert evaluate_answer_semantic("2x + 3 = 11", "4", "4")
    assert evaluate_answer_semantic("2x + 3 = 11", "x = 4", "4")
    assert evaluate_answer_semantic("2x + 3 = 11", " 4 ", "4")
    assert evaluate_answer_semantic("2x + 3 = 11", "4.0", "4")


def test_rechaza_la_respuesta_incorrecta():
    assert not evaluate_answer_semantic("2x + 3 = 11", "5", "4")
    assert not evaluate_answer_semantic("2x + 3 = 11", "", "4")
    assert not evaluate_answer_semantic("2x + 3 = 11", "no se", "4")


# ------------------------------------------------------------------ trocear

def test_cada_fragmento_lleva_el_titulo_del_documento():
    texto = "parrafo uno\n\nparrafo dos\n\nparrafo tres"
    for f in trocear(texto, "ECUACIONES BASICAS"):
        assert f.startswith("ECUACIONES BASICAS")


def test_el_troceado_no_parte_los_bloques_ni_pierde_texto():
    texto = "\n\n".join("bloque numero %d" % i for i in range(1, 12))
    fragmentos = trocear(texto, "TITULO")
    assert len(fragmentos) >= 1
    unido = " ".join(fragmentos)
    for i in range(1, 12):
        assert "bloque numero %d" % i in unido


# --------------------------------------------------------------- andamiaje

def test_la_pista_corresponde_al_tipo_de_ecuacion():
    assert "distributiva" in get_hint_by_equation_type("2(x - 3) = 8").lower()
    assert "x" in get_hint_by_equation_type("5x - 2 = 3x + 8").lower()


def test_la_pista_nunca_revela_la_respuesta():
    for eq in ["2(x - 3) = 8", "5x - 2 = 3x + 8", "4x = 20"]:
        pista = get_hint_by_equation_type(eq)
        solucion = solve_equation(eq)
        if solucion is not None:
            assert solucion not in pista


# ------------------------------------------------------------ banco de respaldo

def test_el_banco_de_respaldo_entrega_la_cantidad_pedida():
    for nivel in ["basico", "intermedio", "avanzado"]:
        assert len(fallback_exercises("ecuaciones", nivel, 3)) == 3


def test_las_respuestas_del_banco_de_respaldo_son_correctas():
    """Si el banco trae un error, el estudiante lo ve cuando el modelo falla."""
    for nivel in ["basico", "intermedio", "avanzado"]:
        for ex in fallback_exercises("ecuaciones", nivel, 5):
            esperada = ex["respuesta_esperada"]
            assert solve_equation(ex["pregunta"]) == str(esperada), ex["pregunta"]
            assert ex["pista"]
