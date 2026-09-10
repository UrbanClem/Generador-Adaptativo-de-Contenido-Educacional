"""
Sistema de Diagnóstico Cognitivo basado en CDA (Cognitive Diagnostic Assessment)
SOLO USA IA - SIN PREGUNTAS PREDETERMINADAS
"""

import ollama
import json
import re
import sympy
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations,
                                        implicit_multiplication_application)
from typing import List, Dict, Any
from database import SessionLocal, CognitiveProfile
from config import OLLAMA_MODEL

# ========== CONFIGURACIÓN ==========
MODEL_NAME = OLLAMA_MODEL  # se configura con la variable OLLAMA_MODEL

# ========== MATRIZ Q ==========
ATTRIBUTES = {
    "A1": "Identificar variable desconocida",
    "A2": "Realizar operaciones aritméticas básicas",
    "A3": "Aislar términos con variable",
    "A4": "Aplicar propiedad distributiva",
    "A5": "Resolver ecuaciones con variables en ambos lados",
    "A6": "Interpretar problemas contextualizados"
}

Q_MATRIX = {
    "basico": {"simple_equation": {"A1": 1, "A2": 1, "A3": 0, "A4": 0, "A5": 0, "A6": 0}},
    "intermedio": {"two_step_eq": {"A1": 1, "A2": 1, "A3": 1, "A4": 1, "A5": 0, "A6": 1}},
    "avanzado": {"both_sides_eq": {"A1": 1, "A2": 1, "A3": 1, "A4": 1, "A5": 1, "A6": 1}}
}


class CognitiveDiagnosticProfile:
    def __init__(self, student_id: int, student_name: str):
        self.student_id = student_id
        self.student_name = student_name
        self.attribute_mastery = {attr: 0.0 for attr in ATTRIBUTES.keys()}
        self.response_history: List[Dict] = []
        self.current_level = "basico"
        self.zpd_attributes: List[str] = []
        self._load_from_db()
    
    def _load_from_db(self):
        db = SessionLocal()
        profile = db.query(CognitiveProfile).filter_by(student_id=self.student_id).first()
        if profile:
            self.attribute_mastery = profile.attribute_mastery or {attr: 0.0 for attr in ATTRIBUTES.keys()}
            self.current_level = profile.current_level or "basico"
            self.zpd_attributes = profile.zpd_attributes or []
            self.response_history = profile.response_history or []
        db.close()
    
    def save_to_db(self):
        db = SessionLocal()
        profile = db.query(CognitiveProfile).filter_by(student_id=self.student_id).first()
        if profile:
            profile.attribute_mastery = self.attribute_mastery
            profile.current_level = self.current_level
            profile.zpd_attributes = self.zpd_attributes
            profile.response_history = self.response_history[-50:]
        else:
            profile = CognitiveProfile(
                student_id=self.student_id,
                attribute_mastery=self.attribute_mastery,
                current_level=self.current_level,
                zpd_attributes=self.zpd_attributes,
                response_history=self.response_history[-50:]
            )
            db.add(profile)
        db.commit()
        db.close()
    
    def update_from_response(self, question: Dict, is_correct: bool, response_time: float = None):
        question_text = question.get("pregunta", "")
        
        self.response_history.append({
            "question": question_text,
            "is_correct": is_correct,
            "response_time": response_time
        })
        
        # Actualizar nivel basado en respuestas recientes
        if len(self.response_history) >= 5:
            recent_correct = sum(1 for r in self.response_history[-8:] if r.get("is_correct", False))
            if recent_correct >= 6:
                self.current_level = "avanzado"
            elif recent_correct >= 3:
                self.current_level = "intermedio"
            else:
                self.current_level = "basico"
        
        self.save_to_db()
    
    def get_next_difficulty(self) -> str:
        return self.current_level
    
    def get_feedback(self) -> Dict:
        return {
            "level": self.current_level,
            "strengths": [ATTRIBUTES[a] for a, v in self.attribute_mastery.items() if v >= 0.7],
            "developing": [ATTRIBUTES[a] for a in self.zpd_attributes],
            "weaknesses": [ATTRIBUTES[a] for a, v in self.attribute_mastery.items() if v < 0.3]
        }


# ========== VALIDADOR MATEMÁTICO ==========

def solve_equation(equation: str):
    """Resuelve una ecuacion de primer grado con sympy (NO con la IA).

    Devuelve la solucion como cadena, o None si la ecuacion no se puede
    interpretar o no tiene solucion unica. Acepta las formas que suele
    devolver el modelo: "5x - 17 = 8", "5*x - 17 = 8", "2(x - 3) = 8".
    """
    try:
        eq = str(equation).strip().lower().replace(" ", "")
        if eq.count("=") != 1:
            return None

        izq, der = eq.split("=")
        x = sympy.Symbol("x")
        # implicit_multiplication_application entiende "5x" y "2(x-3)"
        transf = standard_transformations + (implicit_multiplication_application,)
        izq = parse_expr(izq, transformations=transf, local_dict={"x": x})
        der = parse_expr(der, transformations=transf, local_dict={"x": x})

        soluciones = sympy.solve(sympy.Eq(izq, der), x)
        if len(soluciones) != 1:
            return None

        valor = sympy.nsimplify(soluciones[0])
        if not valor.is_real:
            return None
        if valor == int(valor):
            return str(int(valor))
        return str(round(float(valor), 2))

    except Exception as e:
        print("Error resolviendo ecuacion '%s': %s" % (equation, e))
        return None


def solucion_entera(equation: str):
    """Como solve_equation, pero descarta lo que no da un entero.

    El modelo a veces devuelve ecuaciones como "3x - 7 = 6" (x = 4.33) pese a
    que el prompt le pide soluciones enteras; esas se desechan en vez de
    presentarselas al estudiante.
    """
    resultado = solve_equation(equation)
    if resultado is None:
        return None
    try:
        numero = float(resultado)
    except ValueError:
        return None
    if numero != int(numero):
        return None
    return str(int(numero))


def _formatear(expr):
    """Escribe la expresión como la vería un alumno: 5x - 17, no 5*x - 17."""
    return sympy.sstr(expr).replace("*x", "x").replace("  ", " ")


def _partes(equation):
    """Devuelve (izquierda, derecha) como expresiones de sympy, o None."""
    eq = str(equation).strip().lower().replace(" ", "")
    if eq.count("=") != 1:
        return None
    izq, der = eq.split("=")
    x = sympy.Symbol("x")
    transf = standard_transformations + (implicit_multiplication_application,)
    try:
        return (parse_expr(izq, transformations=transf, local_dict={"x": x}),
                parse_expr(der, transformations=transf, local_dict={"x": x}))
    except Exception:
        return None


def ajustar_a_entero(equation: str):
    """Corrige una ecuación del modelo para que su solución sea entera.

    El modelo propone la estructura y el nivel de dificultad, pero se equivoca
    seguido en la aritmética: de "8x + 17 = 23" sale x = 0.75. En vez de
    desechar la ecuación, se recorre el término independiente lo mínimo
    necesario para que la solución sea el entero más cercano (aquí, "8x + 17
    = 25", x = 1). La estructura y los coeficientes se respetan.

    Devuelve (ecuacion, respuesta) o None si no hay nada que hacer.
    """
    partes = _partes(equation)
    if partes is None:
        return None
    izq, der = partes
    # el lado izquierdo se conserva tal como lo escribió el modelo, para no
    # perder los paréntesis (sympy los distribuye al interpretar la cadena)
    izq_txt = str(equation).split("=")[0].strip()

    x = sympy.Symbol("x")
    dif = sympy.expand(izq - der)
    a = dif.coeff(x, 1)          # coeficiente de x
    b = dif.coeff(x, 0)          # término independiente
    if a == 0 or not (a.is_number and b.is_number):
        return None

    solucion = sympy.Rational(-b, a)
    if solucion == int(solucion) and solucion != 0:
        return str(equation).strip(), str(int(solucion))

    # entero más cercano, evitando la solución trivial x = 0
    objetivo = int(sympy.floor(solucion + sympy.Rational(1, 2)))
    if objetivo == 0:
        objetivo = 1

    # se recorre el lado derecho para que la solución sea justo el objetivo
    nueva_der = sympy.expand(der + (a * objetivo + b))
    if nueva_der == izq:
        return None

    ajustada = izq_txt + " = " + _formatear(nueva_der)
    comprobacion = solve_equation(ajustada)
    if comprobacion != str(objetivo):
        return None
    return ajustada, comprobacion


# ========== GENERADOR DE PREGUNTAS SOLO CON IA ==========

def _pedir_ecuaciones(target_level, cantidad, prohibidas):
    """Una llamada al modelo: devuelve la lista de ecuaciones que propuso."""
    forbidden = ""
    if prohibidas:
        forbidden = "\n\nPREGUNTAS PROHIBIDAS (NO LAS REPITAS):\n"
        for q in list(prohibidas)[-15:]:
            forbidden += "- %s\n" % q

    prompt = f"""
Eres un profesor de matemáticas. Genera {cantidad} ecuaciones de PRIMER GRADO.

Nivel: {target_level}

{forbidden}

REGLAS ESTRICTAS:
- Usa el formato: "5x - 17 = 8" (SOLO la ecuación, sin texto extra)
- Variables solo 'x', números enteros entre 1 y 50
- La solución TIENE que ser un número entero: antes de escribir cada
  ecuación, resuélvela y comprueba que la división es exacta
- NO uses problemas de palabras
- NO incluyas texto adicional fuera del JSON

RESPONDE SOLO CON UN JSON. FORMATO EXACTO:
[
    {{"pregunta": "2x + 3 = 11", "respuesta_esperada": "4"}}
]
"""

    response = ollama.chat(model=MODEL_NAME,
                           messages=[{'role': 'user', 'content': prompt}])
    content = response['message']['content'].strip()
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)

    try:
        questions = json.loads(content)
    except json.JSONDecodeError as e:
        raise Exception(
            f"La IA no devolvió JSON válido: {str(e)}. Respuesta: {content[:200]}")

    if not isinstance(questions, list) or not questions:
        raise Exception("La IA no generó preguntas")

    return questions


def generate_adaptive_questions(profile: CognitiveDiagnosticProfile, num_questions: int = 3):
    """Genera preguntas usando SOLO IA.

    La respuesta de cada ecuación se calcula con sympy, no con el modelo, y se
    descarta lo que no tenga solución entera. Como el modelo falla seguido en
    esa condición, se piden de más y se reintenta hasta tres veces; si aun así
    no se juntan las preguntas necesarias, se lanza excepción.
    """
    target_level = profile.get_next_difficulty()
    used_questions = [r.get("question", "") for r in profile.response_history
                      if r.get("question")]

    valid_questions = []
    ultimo_error = None

    for intento in range(1, 4):
        faltan = num_questions - len(valid_questions)
        prohibidas = used_questions + [v["pregunta"] for v in valid_questions]

        try:
            propuestas = _pedir_ecuaciones(target_level, faltan + 3, prohibidas)
        except Exception as e:
            ultimo_error = e
            print(f"Intento {intento}: {e}")
            continue

        for q in propuestas:
            equation = q.get("pregunta", "")
            if not equation:
                continue

            # La respuesta real se calcula con Python, no con la IA, y si la
            # ecuación no da entero se corrige antes de mostrarla
            ajuste = ajustar_a_entero(equation)
            if ajuste is None:
                print(f"Descartada (no se pudo interpretar): {equation}")
                continue
            if ajuste[0] != equation:
                print(f"Ajustada: {equation} -> {ajuste[0]}")
            equation, real_answer = ajuste
            q["pregunta"] = equation

            if equation in prohibidas:
                print(f"Descartada (repetida): {equation}")
                continue

            q["respuesta_esperada"] = real_answer
            q["tipo"] = "abierta"
            q["nivel"] = target_level
            q["scaffolding_hint"] = get_hint_by_equation_type(equation)
            valid_questions.append(q)
            prohibidas.append(equation)

        if len(valid_questions) >= num_questions:
            break

        print(f"Intento {intento}: van {len(valid_questions)} de {num_questions}, "
              f"se vuelve a pedir")

    if len(valid_questions) < num_questions:
        detalle = f" Último error: {ultimo_error}" if ultimo_error else ""
        raise Exception(
            f"Solo se generaron {len(valid_questions)} preguntas válidas de "
            f"{num_questions} en 3 intentos.{detalle}")

    print(f"Generadas {len(valid_questions)} preguntas con IA para nivel {target_level}")
    return valid_questions[:num_questions]


def get_hint_by_equation_type(equation: str) -> str:
    """Genera hints sin revelar la respuesta"""
    if "(" in equation and ")" in equation:
        return "Aplica la propiedad distributiva, luego resuelve paso a paso"
    elif equation.count("x") > 1:
        return "Agrupa los términos con x en un lado y las constantes en el otro"
    elif "*" in equation or equation.count("x") == 1 and any(c.isdigit() for c in equation):
        return "Aísla la variable dividiendo por el coeficiente"
    else:
        return "Realiza la operación inversa para despejar x"


def generate_test_questions_only():
    """Prueba que la IA puede generar preguntas - SIN FALLBACK"""
    test_prompt = "Responde SOLO con el número 4"
    
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': test_prompt}])
        content = response['message']['content'].strip()
        
        # Verificar que la respuesta contiene un 4
        if '4' in content:
            return True
        else:
            raise Exception(f"La IA no respondió correctamente: {content}")
            
    except Exception as e:
        raise Exception(f"IA no disponible: {str(e)}")


def evaluate_answer_semantic(question: str, student_answer, expected_answer) -> bool:
    """Evaluación semántica - maneja strings y números"""
    student_clean = str(student_answer).strip().lower()
    expected_clean = str(expected_answer).strip().lower()
    
    # Quitar "x=" si existe
    student_clean = re.sub(r'^x\s*=\s*', '', student_clean)
    expected_clean = re.sub(r'^x\s*=\s*', '', expected_clean)
    
    # Quitar espacios
    student_clean = student_clean.replace(" ", "")
    expected_clean = expected_clean.replace(" ", "")
    
    # Intentar convertir a número
    try:
        student_num = int(float(student_clean))
        expected_num = int(float(expected_clean))
        return student_num == expected_num
    except:
        return student_clean == expected_clean