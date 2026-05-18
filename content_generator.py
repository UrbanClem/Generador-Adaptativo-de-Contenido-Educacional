import ollama
import json
import re
from cognitive_diagnostic import solve_equation

# ========== CONFIGURACIÓN ==========
MODEL_NAME = "mistral:latest"  # Usar Mistral para mejor calidad


def generate_explanation(topic, student_level):
    """Genera una explicación personalizada del tema"""
    prompt = f"""
Eres un tutor de matemáticas. Explica {topic} a un estudiante de nivel {student_level}.

REGLAS:
- Usa lenguaje claro y sencillo
- Incluye un ejemplo práctico
- No uses fórmulas demasiado complejas
- Extensión: 3-5 párrafos
"""
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        print(f"Error generando explicación: {e}")
        return f"Lo siento, no pude generar una explicación en este momento. Error: {str(e)}"


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


def generate_exercises_with_answers(topic, student_level, quantity=3):
    """
    Genera ejercicios con IA en formato estructurado para que el usuario pueda responder.
    Retorna una lista de ejercicios con pregunta, respuesta esperada y pista.
    """
    
    prompt = f"""
Eres un profesor de matemáticas. Genera {quantity} ejercicios de {topic} para nivel {student_level}.

REGLAS:
- Cada ejercicio debe ser una ECUACIÓN de primer grado
- Formato: "2x + 3 = 11"
- La respuesta debe ser un número entero
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
        
        # Validar cada ejercicio con el solucionador matemático
        for ex in exercises:
            equation = ex.get("pregunta", "")
            real_answer = solve_equation(equation)
            if real_answer:
                ex["respuesta_esperada"] = real_answer
                print(f"✅ Ecuación válida: {equation} → respuesta: {real_answer}")
            else:
                print(f"⚠️ No se pudo resolver: {equation}")
                ex["respuesta_esperada"] = "0"
        
        return exercises
        
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


def give_feedback(student_answer, correct_answer, student_level):
    """Genera retroalimentación personalizada para una respuesta"""
    prompt = f"""
Estudiante de nivel {student_level} respondió: "{student_answer}"
Respuesta correcta: "{correct_answer}"

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