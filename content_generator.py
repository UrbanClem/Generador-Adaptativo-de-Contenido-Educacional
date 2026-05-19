import ollama
import json
import re
from cognitive_diagnostic import solve_equation

# ========== CONFIGURACIÓN ==========
MODEL_NAME = "mistral:latest"

# ========== TEMAS MATEMÁTICOS VÁLIDOS ==========
MATH_TOPICS = [
    "ecuacion", "ecuación", "ecuaciones", "ecucacion", "ecucaciones", 
    "algebra", "álgebra", "lineal", "lineales", "cuadratica", "cuadrática",
    "pitagoras", "pitágoras", "teorema", "geometria", "geometría", 
    "triangulo", "triángulo", "fraccion", "fracción", "fracciones", 
    "porcentaje", "porcentajes", "derivada", "derivadas", "integral", "integrales",
    "matriz", "matrices", "vector", "vectores", "funcion", "función", "funciones",
    "area", "área", "perimetro", "perímetro", "volumen", "trigonometria", "trigonometría",
    "matematicas", "matemáticas", "math"
]


def is_math_topic(topic: str) -> bool:
    """Verifica si el tema solicitado es de matemáticas."""
    topic_lower = topic.lower().strip()
    for valid_topic in MATH_TOPICS:
        if valid_topic in topic_lower:
            print(f"✅ Tema matemático detectado: '{topic}'")
            return True
    return False


def get_non_math_message(topic: str) -> str:
    """Mensaje de error para temas no matemáticos."""
    return f"⚠️ Lo siento, este sistema solo puede ayudarte con temas de MATEMÁTICAS. El tema '{topic}' no está dentro de mis capacidades."


def normalize_numeric_answer(answer_str: str) -> str:
    """Normaliza una respuesta para que sea estrictamente numérica."""
    cleaned = str(answer_str).strip()
    cleaned = re.sub(r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s:=]+', '', cleaned)
    cleaned = cleaned.strip()

    frac_match = re.match(r'^(-?\d+)\s*/\s*(\d+)$', cleaned)
    if frac_match:
        num = float(frac_match.group(1))
        den = float(frac_match.group(2))
        if den != 0:
            result = num / den
            if result == int(result):
                return str(int(result))
            return str(round(result, 4))

    try:
        num_val = float(cleaned)
        if num_val == int(num_val):
            return str(int(num_val))
        return str(round(num_val, 4))
    except ValueError:
        pass

    num_match = re.search(r'-?\d+\.?\d*', cleaned)
    if num_match:
        num_val = float(num_match.group())
        if num_val == int(num_val):
            return str(int(num_val))
        return str(round(num_val, 4))

    return "0"


def is_simple_linear_equation(equation: str) -> bool:
    """Verifica si la ecuación es lineal simple (sin ^, sin sqrt, etc.)"""
    if '^' in equation or 'sqrt' in equation or 'sin' in equation or 'cos' in equation:
        return False
    x_count = equation.lower().count('x')
    return x_count >= 1 and 'x^' not in equation.lower()


def extract_equation_from_text(text: str) -> str:
    """Extrae solo la ecuación de un texto."""
    if '=' not in text:
        return text
    
    patterns = [
        r'(\d*\s*[xX]\s*[+\-*/]?\s*\d+\s*[=]\s*\d+)',
        r'(\d+\s*[+\-*/]?\s*[xX]\s*[+\-*/]?\s*\d+\s*[=]\s*\d+)',
        r'([xX]\s*[+\-*/]?\s*\d+\s*[=]\s*\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            equation = match.group(1).strip()
            equation = re.sub(r'\s+', ' ', equation)
            return equation
    
    return text


def generate_explanation(topic, student_level):
    """Genera una explicación personalizada del tema"""
    
    if not is_math_topic(topic):
        return get_non_math_message(topic)
    
    prompt = f"""
Eres un tutor de matemáticas. Explica {topic} a un estudiante de nivel {student_level}.

REGLAS:
- Usa lenguaje claro y sencillo
- Incluye un ejemplo práctico
- Extensión: 3-5 párrafos
- NO uses asteriscos (*) ni guiones bajos (_)
"""
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        content = content.replace('*', '').replace('_', '')
        return content
    except Exception as e:
        raise Exception(f"Error generando explicación: {str(e)}")


def generate_exercises(topic, student_level, quantity=3):
    """Genera ejercicios de práctica en formato texto simple (para compatibilidad)"""
    try:
        exercises = generate_exercises_with_answers(topic, student_level, quantity)
        result = ""
        for i, ex in enumerate(exercises, 1):
            result += f"Ejercicio {i}: {ex.get('pregunta', '')}\n"
            result += f"Pista: {ex.get('pista', '')}\n\n"
        result += "Respuestas:\n"
        for i, ex in enumerate(exercises, 1):
            result += f"{i}. {ex.get('respuesta_esperada', '')}\n"
        return result
    except Exception as e:
        return f"Error generando ejercicios: {str(e)}"


def generate_exercises_with_answers(topic, student_level, quantity=3):
    """Genera ejercicios con IA en formato estructurado."""
    print(f"🔍 generate_exercises_with_answers: topic={topic}, level={student_level}")

    if not is_math_topic(topic):
        raise Exception(get_non_math_message(topic))

    topic_lower = topic.lower().strip()
    is_pythagoras = any(word in topic_lower for word in ["pitagoras", "pitágoras", "teorema", "triangulo", "triángulo", "hipotenusa", "cateto"])
    is_equation = any(word in topic_lower for word in ["ecuacion", "ecuación", "ecucacion", "lineal", "algebra", "álgebra"])

    print(f"📊 Detección: Pitágoras={is_pythagoras}, Ecuación={is_equation}")

    if is_pythagoras:
        prompt = f"""
Eres un profesor de matemáticas. Genera {quantity} ejercicios del TEOREMA DE PITÁGORAS para nivel {student_level}.

REGLAS:
- Cada ejercicio debe ser un problema DESCRIPTIVO de un triángulo rectángulo
- Ejemplo: "Un triángulo rectángulo tiene catetos de 3 cm y 4 cm. ¿Cuánto mide la hipotenusa?"
- Incluye SIEMPRE la respuesta correcta en el campo "respuesta_esperada"
- La respuesta debe ser un número

RESPONDE SOLO CON UN JSON. FORMATO EXACTO:
[
    {{
        "pregunta": "Un triángulo rectángulo tiene catetos de 3 y 4. ¿Hipotenusa?",
        "respuesta_esperada": "5",
        "pista": "Usa a² + b² = c²"
    }}
]
"""
    else:
        prompt = f"""
Eres un profesor de matemáticas. Genera {quantity} ejercicios de ECUACIONES LINEALES de primer grado para nivel {student_level}.

REGLAS ESTRICTAS:
- Usa SOLO ecuaciones lineales SIMPLES. Ejemplos: "2x + 3 = 11", "4x - 7 = 19"
- NO uses ecuaciones cuadráticas (x²) ni cúbicas (x³)
- NO uses texto adicional como "resuelve" o signos de interrogación
- NO uses asteriscos (*)

RESPONDE SOLO CON UN JSON. FORMATO EXACTO:
[
    {{
        "pregunta": "2x + 3 = 11",
        "respuesta_esperada": "4",
        "pista": "Resta 3, divide entre 2"
    }}
]
"""
    
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content'].strip()
        
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        exercises = json.loads(content)

        if not exercises or len(exercises) == 0:
            raise Exception("La IA no generó ejercicios")

        for ex in exercises:
            question_text = ex.get('pregunta', '')
            if not question_text:
                raise Exception("Ejercicio sin pregunta")
            
            if 'respuesta_esperada' not in ex:
                raise Exception(f"Ejercicio sin respuesta_esperada: {question_text}")
            
            if is_equation and not is_pythagoras:
                clean_equation = extract_equation_from_text(question_text)
                
                if not is_simple_linear_equation(clean_equation):
                    print(f"⚠️ Ecuación no lineal simple: {clean_equation}, omitiendo...")
                    continue
                
                real_answer = solve_equation(clean_equation)
                if real_answer is not None:
                    ex['respuesta_esperada'] = real_answer
                    ex['pregunta'] = clean_equation
                    print(f"✅ Ecuación: {clean_equation} → Respuesta: {real_answer}")
                else:
                    print(f"⚠️ No se pudo resolver: {clean_equation}")
            else:
                ex['respuesta_esperada'] = normalize_numeric_answer(ex['respuesta_esperada'])
                print(f"✅ {question_text[:50]}... → Respuesta: {ex['respuesta_esperada']}")
            
            ex['is_math'] = True
            
            if 'pista' in ex:
                ex['pista'] = ex['pista'].replace('*', '').replace('_', '')
            ex['pregunta'] = ex['pregunta'].replace('*', '').replace('_', '')

        valid_exercises = [ex for ex in exercises if 'respuesta_esperada' in ex]
        
        if len(valid_exercises) < quantity:
            print(f"⚠️ Solo {len(valid_exercises)} ejercicios válidos de {quantity}")
        
        return valid_exercises[:quantity]

    except json.JSONDecodeError as e:
        raise Exception(f"La IA no devolvió JSON válido: {str(e)}")
    except Exception as e:
        raise Exception(f"Error generando ejercicios: {str(e)}")


def give_feedback(student_answer, correct_answer, student_level, is_math=False):
    """Genera retroalimentación personalizada"""
    if is_math:
        try:
            student_num = float(str(student_answer).strip())
            correct_num = float(str(correct_answer).strip())
            is_correct = abs(student_num - correct_num) < 0.01
        except (ValueError, TypeError):
            is_correct = str(student_answer).strip() == str(correct_answer).strip()
    else:
        is_correct = str(student_answer).strip() == str(correct_answer).strip()

    prompt = f"""
Estudiante de nivel {student_level} respondió: "{student_answer}"
Respuesta correcta: "{correct_answer}"

Genera retroalimentación breve (2 oraciones max):
- Si es correcto: felicita
- Si es incorrecto: da una pista
- NO uses asteriscos
"""
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        content = content.replace('*', '').replace('_', '')
        return content
    except Exception as e:
        print(f"Error generando feedback: {e}")
        if is_correct:
            return "¡Correcto! Bien hecho."
        else:
            return f"Incorrecto. La respuesta correcta es {correct_answer}. Sigue practicando."