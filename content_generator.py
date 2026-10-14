import ollama
import json
import re
from cognitive_diagnostic import ajustar_a_entero
from rag_engine import retrieve_pertinentes, temas_disponibles
from config import OLLAMA_MODEL

# ========== CONFIGURACIÓN ==========
MODEL_NAME = OLLAMA_MODEL  # se configura con la variable OLLAMA_MODEL


def generate_explanation(topic, student_level, con_fuentes=False, con_fragmentos=False):
    """Genera una explicación personalizada del tema, apoyada en el material

    Recupera de la base de conocimiento los fragmentos más parecidos al tema,
    descarta los que no tratan ese tema y pasa el resto en el prompt, para que
    la explicación salga del material del curso y no del conocimiento propio
    del modelo. Si no queda material, no se explica nada: pedirle al prompt que
    avise no funciona (con "derivadas" el modelo inventó una explicación, y
    equivocada, aunque la regla se lo prohibía).

    Con `con_fuentes=True` devuelve además la lista de archivos usados; con
    `con_fragmentos=True` devuelve los fragmentos completos (texto y fuente),
    que es lo que exige la trazabilidad por fragmento (RF12).
    """
    pasajes = retrieve_pertinentes(topic, n_results=3)
    material = '\n\n---\n\n'.join(p["texto"] for p in pasajes)
    fuentes = []
    for p in pasajes:
        if p["fuente"] and p["fuente"] not in fuentes:
            fuentes.append(p["fuente"])
    fragmentos = [{"fuente": p["fuente"], "texto": p["texto"]} for p in pasajes]

    if not material:
        print(f"Sin material para '{topic}': no se genera explicación")
        temas = temas_disponibles()
        texto = (f"El material del curso no cubre \"{topic}\", así que no puedo explicarlo. "
                 "Los temas que sí están cubiertos son:\n\n"
                 + "\n".join(f"- {t.capitalize()}" for t in temas))
        if con_fragmentos:
            return texto, []
        return (texto, []) if con_fuentes else texto

    prompt = f"""
Eres un tutor de matemáticas. Explica {topic} a un estudiante de nivel {student_level}.

MATERIAL DEL CURSO:
{material}

REGLAS:
- Explica únicamente con lo que aparece en el material de arriba
- No inventes reglas, fórmulas ni definiciones que no estén ahí
- Usa lenguaje claro y sencillo
- Incluye un ejemplo práctico tomado del material
- Extensión: 3-5 párrafos
"""

    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        texto = response['message']['content']
    except Exception as e:
        print(f"Error generando explicación: {e}")
        texto = f"Lo siento, no pude generar una explicación en este momento. Error: {str(e)}"
        fuentes = []
        fragmentos = []

    if con_fragmentos:
        return texto, fragmentos
    return (texto, fuentes) if con_fuentes else texto


def generate_exercises(topic, student_level, quantity=3):
    """Genera ejercicios de práctica (formato texto simple) - VERSIÓN ANTIGUA"""
    prompt = f"""
Genera {quantity} ejercicios de {topic} para nivel {student_level}.
Incluye las respuestas al final.

Formato:
Ejercicio 1: ...
Ejercicio 2: ...
...
Respuestas: ...
"""
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        print(f"Error generando ejercicios: {e}")
        return f"Error: {str(e)}"


def generate_exercises_with_answers(topic, student_level, quantity=3, material=None):
    """
    Genera ejercicios con IA en formato estructurado para que el usuario pueda responder.
    Retorna una lista de ejercicios con pregunta, respuesta esperada y pista.

    Cuando se entrega `material` (fragmentos recuperados del corpus), los
    ejercicios se anclan a ese material igual que las explicaciones, en vez de
    generarse solo a partir del conocimiento del modelo (RF11/evolutivo).
    """
    
    bloque_material = ""
    if material:
        bloque_material = f"""
MATERIAL DEL CURSO (basa los ejercicios en él, no inventes métodos que no aparezcan):
{material}
"""

    prompt = f"""
Eres un profesor de matemáticas. Genera {quantity + 3} ejercicios de {topic} para nivel {student_level}.
{bloque_material}
REGLAS:
- Cada ejercicio debe ser una ECUACIÓN de primer grado
- Formato: "2x + 3 = 11"
- La respuesta debe ser un número entero (la división debe ser exacta)
- Incluye una pista corta sin revelar la respuesta

RESPONDE SOLO CON UN JSON. FORMATO EXACTO:
[
    {{
        "pregunta": "2x + 3 = 11",
        "respuesta_esperada": "4",
        "pista": "Resta 3, luego divide entre 2"
    }}
]
"""
    
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content'].strip()
        
        # Limpiar markdown
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        exercises = json.loads(content)
        
        # Validar cada ejercicio con el solucionador matemático, no con la IA
        validos = []
        for ex in exercises:
            equation = ex.get("pregunta", "")
            ajuste = ajustar_a_entero(equation)
            if ajuste is None:
                print(f"Descartado (no se pudo interpretar): {equation}")
                continue
            if ajuste[0] != equation:
                print(f"Ajustado: {equation} -> {ajuste[0]}")
            ex["pregunta"], ex["respuesta_esperada"] = ajuste
            ex["tipo"] = "abierta"
            validos.append(ex)

        # Si la IA no dejó suficientes ejercicios usables, se completa con el banco
        if len(validos) < quantity:
            respaldo = fallback_exercises(topic, student_level, quantity)
            usadas = {e["pregunta"] for e in validos}
            for ex in respaldo:
                if len(validos) >= quantity:
                    break
                if ex["pregunta"] not in usadas:
                    validos.append(ex)

        return validos[:quantity]
        
    except json.JSONDecodeError as e:
        print(f"Error JSON en generate_exercises_with_answers: {e}")
        print(f"Contenido recibido: {content[:200] if 'content' in dir() else 'N/A'}")
        return fallback_exercises(topic, student_level, quantity)
    except Exception as e:
        print(f"Error generando ejercicios con IA: {e}")
        return fallback_exercises(topic, student_level, quantity)


def fallback_exercises(topic, student_level, quantity=3):
    """Ejercicios de respaldo verificados"""
    bank = {
        "basico": [
            {"pregunta": "x + 3 = 7", "respuesta_esperada": "4", "pista": "Resta 3 en ambos lados"},
            {"pregunta": "x - 2 = 5", "respuesta_esperada": "7", "pista": "Suma 2 en ambos lados"},
            {"pregunta": "x + 8 = 15", "respuesta_esperada": "7", "pista": "Resta 8 en ambos lados"},
            {"pregunta": "x - 4 = 9", "respuesta_esperada": "13", "pista": "Suma 4 en ambos lados"},
            {"pregunta": "x + 5 = 12", "respuesta_esperada": "7", "pista": "Resta 5 en ambos lados"}
        ],
        "intermedio": [
            {"pregunta": "2x + 3 = 11", "respuesta_esperada": "4", "pista": "Resta 3, luego divide entre 2"},
            {"pregunta": "3x - 5 = 10", "respuesta_esperada": "5", "pista": "Suma 5, luego divide entre 3"},
            {"pregunta": "4x + 2 = 18", "respuesta_esperada": "4", "pista": "Resta 2, luego divide entre 4"},
            {"pregunta": "5x - 3 = 22", "respuesta_esperada": "5", "pista": "Suma 3, luego divide entre 5"},
            {"pregunta": "2x + 7 = 21", "respuesta_esperada": "7", "pista": "Resta 7, luego divide entre 2"}
        ],
        "avanzado": [
            {"pregunta": "2(x - 3) = 8", "respuesta_esperada": "7", "pista": "Divide entre 2, luego suma 3"},
            {"pregunta": "3x + 4 = 2x + 9", "respuesta_esperada": "5", "pista": "Resta 2x, luego resta 4"},
            {"pregunta": "4(x + 1) = 2(x + 5)", "respuesta_esperada": "3", "pista": "Aplica distributiva, luego agrupa"},
            {"pregunta": "2(x + 4) = 3(x - 1)", "respuesta_esperada": "11", "pista": "Aplica distributiva, luego agrupa"},
            {"pregunta": "5x + 2 = 3x + 12", "respuesta_esperada": "5", "pista": "Resta 3x, luego resta 2, luego divide"}
        ]
    }
    
    selected = bank.get(student_level, bank["basico"])[:quantity]
    for ex in selected:
        ex["tipo"] = "abierta"
    return selected


def give_feedback(student_answer, correct_answer, student_level, material=None):
    """Genera retroalimentación personalizada para una respuesta

    Si se entrega `material` (fragmentos del corpus recuperados para el tema),
    la retroalimentación se apoya en ese material en lugar de generarse sola
    (extensión del anclaje documental a la retroalimentación).
    """
    bloque_material = ""
    if material:
        bloque_material = f"""
Apóyate en este material del curso al explicar:
{material}
"""
    prompt = f"""
Estudiante de nivel {student_level} respondió: "{student_answer}"
Respuesta correcta: "{correct_answer}"
{bloque_material}
Genera retroalimentación educativa (máximo 2 oraciones):
- Si es correcto: felicita y refuerza el aprendizaje
- Si es incorrecto: explica amablemente y da una pista
"""
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        print(f"Error generando feedback: {e}")
        if str(student_answer).strip() == str(correct_answer).strip():
            return "¡Correcto! Bien hecho."
        else:
            return f"Incorrecto. La respuesta correcta es {correct_answer}. Sigue practicando."