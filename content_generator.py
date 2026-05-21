import ollama
import json
import re
from cognitive_diagnostic import solve_equation

# ========== CONFIGURACIÓN ==========
MODEL_NAME = "mistral:latest"

# ========== TEMAS MATEMÁTICOS VÁLIDOS (MÁS DE 200 PALABRAS CLAVE) ==========
MATH_TOPICS = [
    # Álgebra básica
    "ecuacion", "ecuación", "ecuaciones", "algebra", "álgebra", "expresion", "expresión",
    "polinomio", "polinomios", "factorizacion", "factorización", "binomio", "binomios",
    "trinomio", "trinomios", "monomio", "monomios", "termino", "término", "terminos",
    "coeficiente", "coeficientes", "variable", "variables", "incognita", "incógnita",
    
    # Ecuaciones
    "lineal", "lineales", "cuadratica", "cuadrática", "cuadraticas", "cuadráticas",
    "exponencial", "exponenciales", "logaritmica", "logarítmica", "logaritmicas",
    "racional", "racionales", "irracional", "irracionales", "sistema", "sistemas",
    
    # Aritmética
    "suma", "resta", "multiplicacion", "multiplicación", "division", "división",
    "fraccion", "fracción", "fracciones", "decimal", "decimales", "porcentaje", "porcentajes",
    "proporcion", "proporción", "proporciones", "razon", "razón", "razones",
    "potencia", "potencias", "exponente", "exponentes", "raiz", "raíz", "raices", "raíces",
    "radical", "radicales", "logaritmo", "logaritmos", "valor absoluto",
    
    # Geometría
    "geometria", "geometría", "punto", "linea", "línea", "recta", "plano", "planos",
    "angulo", "ángulo", "angulos", "ángulos", "triangulo", "triángulo", "triangulos",
    "cuadrado", "cuadrados", "rectangulo", "rectángulo", "rectangulos", "circulo", "círculo",
    "circunferencia", "perimetro", "perímetro", "area", "área", "volumen", "volumenes",
    "superficie", "poligono", "polígono", "poligonos", "pentagono", "pentágono",
    "hexagono", "hexágono", "octagono", "octágono", "rombo", "rombos", "trapecio",
    "elipse", "elipses", "parabola", "parábola", "hiperbola", "hipérbola",
    
    # Trigonometría
    "trigonometria", "trigonometría", "seno", "coseno", "tangente", "cotangente",
    "secante", "cosecante", "sen", "cos", "tan", "cot", "sec", "csc",
    "identidad", "identidades", "angulo doble", "angulo medio", "radian", "radianes",
    
    # Cálculo
    "calculo", "cálculo", "derivada", "derivadas", "diferenciacion", "diferenciación",
    "integral", "integrales", "integracion", "integración", "limite", "límite", "limites",
    "continuidad", "funcion", "función", "funciones", "grafica", "gráfica", "graficas",
    "optimizacion", "optimización", "maximo", "máximo", "minimo", "mínimo",
    "serie", "series", "sucesion", "sucesión",
    
    # Estadística y Probabilidad
    "estadistica", "estadística", "probabilidad", "media", "mediana", "moda",
    "desviacion", "desviación", "varianza", "correlacion", "correlación",
    "regresion", "regresión", "distribucion", "distribución", "normal", "binomial",
    "poisson", "permutacion", "permutación", "combinacion", "combinación",
    
    # Matrices y Vectores
    "matriz", "matrices", "determinante", "determinantes", "vector", "vectores",
    "producto punto", "producto cruz", "producto escalar", "producto vectorial",
    "espacio vectorial", "transformacion lineal", "transformación lineal",
    
    # Teoremas y conceptos específicos
    "pitagoras", "pitágoras", "teorema", "teoremas", "demostracion", "demostración",
    "demostrar", "propiedad", "propiedades", "axioma", "axiomas", "postulado",
    
    # Números y conjuntos
    "numero", "número", "numeros", "números", "entero", "enteros", "natural", "naturales",
    "racional", "racionales", "irracional", "irracionales", "real", "reales",
    "complejo", "complejos", "imaginario", "imaginarios", "primo", "primos",
    "compuesto", "compuestos", "par", "impar", "multiplo", "múltiplo", "divisor",
    
    # Palabras de operación comunes
    "calcular", "resuelve", "resolver", "halla", "encuentra", "determina",
    "simplifica", "simplificar", "despeja", "despejar", "evalua", "evaluar",
    "grafica", "graficar", "representa", "representar",
    
    # Matemáticas generales
    "matematicas", "matemáticas", "math", "mate", "mates", "matematico", "matemático",
    "aritmetica", "aritmética", "geometrica", "geométrica", "analisis", "análisis",
    "topologia", "topología", "teoria de numeros", "teoría de números"
]


def is_math_topic(topic: str) -> bool:
    """Verifica si el tema solicitado es de matemáticas con detección avanzada."""
    topic_lower = topic.lower().strip()
    
    # 1. Verificar palabras clave exactas
    for valid_topic in MATH_TOPICS:
        if valid_topic in topic_lower:
            print(f"✅ Tema matemático detectado: '{topic}' (coincidencia: '{valid_topic}')")
            return True
    
    # 2. Verificar si contiene términos matemáticos comunes
    math_indicators = ["=", "+", "-", "*", "/", "x", "y", "z", "√", "π", "pi", "sen", "cos", "tan"]
    for indicator in math_indicators:
        if indicator in topic_lower:
            print(f"✅ Tema matemático detectado por símbolo: '{topic}' (contiene '{indicator}')")
            return True
    
    # 3. Verificar si parece una ecuación
    if re.search(r'\d+\s*[x]\s*[=]\s*\d+', topic_lower):
        print(f"✅ Tema matemático detectado como ecuación: '{topic}'")
        return True
    
    print(f"❌ Tema NO matemático: '{topic}'")
    return False


def get_non_math_message(topic: str) -> str:
    """Mensaje de error para temas no matemáticos."""
    return f"""⚠️ Lo siento, este sistema solo puede ayudarte con temas de MATEMÁTICAS.

El tema '{topic}' no está dentro de mis capacidades.

📚 Temas matemáticos que puedes consultar:
• Álgebra: ecuaciones, polinomios, factorización, sistemas de ecuaciones
• Geometría: áreas, perímetros, volúmenes, triángulos, círculos, Pitágoras
• Trigonometría: seno, coseno, tangente, identidades trigonométricas
• Cálculo: derivadas, integrales, límites, funciones
• Estadística: media, mediana, moda, probabilidad
• Aritmética: fracciones, decimales, porcentajes, potencias, raíces
• Matrices: determinantes, suma y multiplicación de matrices

Por favor, intenta con un tema matemático válido.
"""


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


def generate_explanation(topic, student_level, student_preferences=None):
    """Genera una explicación personalizada del tema - SOLO MATEMÁTICAS"""
    
    if not is_math_topic(topic):
        return get_non_math_message(topic)
    
    # Construir contexto de preferencias si existe
    preference_context = ""
    if student_preferences and 'explicaciones' in student_preferences:
        last_feedbacks = student_preferences['explicaciones'][-3:]
        if last_feedbacks:
            preference_context = "\n\nBasado en retroalimentación anterior:\n"
            for fb in last_feedbacks:
                if "no entendi" in fb['feedback'].lower():
                    preference_context += "- El estudiante no entendió explicaciones previas. Sé más claro y usa ejemplos más simples.\n"
                elif "mas ejemplos" in fb['feedback'].lower():
                    preference_context += "- Al estudiante le gustan los ejemplos. Incluye varios ejemplos prácticos.\n"
                elif "muy largo" in fb['feedback'].lower():
                    preference_context += "- El estudiante prefiere explicaciones más cortas y directas.\n"
                elif "me gusta" in fb['feedback'].lower():
                    preference_context += "- Al estudiante le gustó tu estilo. Mantén un tono positivo y claro.\n"
    
    prompt = f"""
Eres un tutor experto en matemáticas. Explica "{topic}" a un estudiante de nivel {student_level}.

REGLAS:
- Usa lenguaje claro y sencillo, adaptado al nivel {student_level}
- Define los conceptos clave antes de usarlos
- Incluye al menos 2 ejemplos prácticos y variados
- Si el tema tiene fórmulas, escríbelas de forma clara (ej: a² + b² = c²)
- Extensión: 3-5 párrafos
- NO uses asteriscos (*) ni guiones bajos (_)
- Sé paciente y motivador
- Si el tema es complejo, divídelo en pasos simples
{preference_context}

Tu explicación debe ser educativa, precisa y fácil de entender.
"""
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        content = content.replace('*', '').replace('_', '')
        return content
    except Exception as e:
        raise Exception(f"Error generando explicación: {str(e)}")


def generate_exercises_with_answers(topic, student_level, quantity=3):
    """
    Genera ejercicios con IA en formato estructurado.
    Detecta automáticamente el tipo de tema matemático.
    """
    print(f"🔍 generate_exercises_with_answers: topic={topic}, level={student_level}")

    # Validar tema matemático
    if not is_math_topic(topic):
        raise Exception(get_non_math_message(topic))

    # Detectar tipo de tema
    topic_lower = topic.lower().strip()
    
    # Detectar categorías
    is_geometry = any(word in topic_lower for word in ["geometria", "geometría", "triangulo", "triángulo", "circulo", "círculo", "area", "área", "perimetro", "perímetro", "volumen", "rectangulo", "cuadrado"])
    is_trigonometry = any(word in topic_lower for word in ["trigonometria", "trigonometría", "seno", "coseno", "tangente", "sen", "cos", "tan", "radian"])
    is_calculus = any(word in topic_lower for word in ["derivada", "integral", "limite", "límite", "calculo", "cálculo", "diferenciacion"])
    is_statistics = any(word in topic_lower for word in ["estadistica", "estadística", "probabilidad", "media", "mediana", "moda", "desviacion"])
    is_algebra = any(word in topic_lower for word in ["algebra", "álgebra", "ecuacion", "ecuación", "polinomio", "factorizacion"])
    is_pythagoras = any(word in topic_lower for word in ["pitagoras", "pitágoras", "teorema"])
    is_arithmetic = any(word in topic_lower for word in ["fraccion", "fracción", "porcentaje", "decimal", "potencia", "raiz"])
    is_matrices = any(word in topic_lower for word in ["matriz", "matrices", "determinante", "vector"])
    
    # Construir instrucciones específicas según la categoría
    if is_pythagoras:
        format_instruction = """
REGLAS PARA TEOREMA DE PITÁGORAS:
- Cada ejercicio debe ser un problema DESCRIPTIVO de un triángulo rectángulo
- Ejemplo: "Un triángulo rectángulo tiene catetos de 3 cm y 4 cm. ¿Cuánto mide la hipotenusa?"
- Usa números enteros para que la respuesta sea exacta
- La respuesta debe ser un número (entero o decimal)
"""
    elif is_geometry:
        format_instruction = f"""
REGLAS PARA GEOMETRÍA:
- Cada ejercicio debe ser un problema sobre {topic}
- Ejemplos: 
  * "Calcula el área de un rectángulo de 5 cm de base y 3 cm de altura" (respuesta: 15)
  * "Calcula el perímetro de un cuadrado de lado 4 cm" (respuesta: 16)
  * "Calcula el volumen de un cubo de arista 3 cm" (respuesta: 27)
- Incluye las fórmulas necesarias en la pista
- La respuesta debe ser un número
"""
    elif is_trigonometry:
        format_instruction = f"""
REGLAS PARA TRIGONOMETRÍA:
- Cada ejercicio debe ser un problema sobre {topic} para nivel {student_level}
- Ejemplo: "Si sen(θ) = 0.5, ¿cuánto vale θ en grados?" (respuesta: 30)
- Usa ángulos comunes: 0°, 30°, 45°, 60°, 90°
- La respuesta debe ser un número
"""
    elif is_calculus:
        format_instruction = f"""
REGLAS PARA CÁLCULO:
- Cada ejercicio debe ser un problema sobre {topic} para nivel {student_level}
- Ejemplo para derivadas: "Derivada de f(x) = x²" (respuesta: 2x)
- Ejemplo para integrales: "∫ 2x dx" (respuesta: x²)
- Ejemplo para límites: "límite cuando x→2 de (x²-4)/(x-2)" (respuesta: 4)
- La respuesta debe ser clara y concisa (puede incluir expresiones algebraicas)
"""
    elif is_statistics:
        format_instruction = f"""
REGLAS PARA ESTADÍSTICA:
- Cada ejercicio debe ser un problema sobre {topic}
- Ejemplos:
  * "Calcula la media de: 2, 4, 6, 8, 10" (respuesta: 6)
  * "Calcula la mediana de: 3, 5, 7, 9, 11" (respuesta: 7)
  * "¿Cuál es la probabilidad de obtener un 6 al lanzar un dado?" (respuesta: 0.1667)
- La respuesta debe ser un número (entero o decimal)
"""
    elif is_matrices:
        format_instruction = f"""
REGLAS PARA MATRICES:
- Cada ejercicio debe ser un problema sobre {topic}
- Ejemplo: "Calcula el determinante de la matriz [[2, 3], [1, 4]]" (respuesta: 5)
- La respuesta debe ser un número
"""
    elif is_arithmetic:
        format_instruction = f"""
REGLAS PARA ARITMÉTICA:
- Cada ejercicio debe ser un problema sobre {topic}
- Ejemplos:
  * "Convierte 3/4 a decimal" (respuesta: 0.75)
  * "Calcula el 20% de 150" (respuesta: 30)
  * "Calcula 2³" (respuesta: 8)
- La respuesta debe ser un número
"""
    else:
        format_instruction = f"""
REGLAS GENERALES:
- Cada ejercicio debe ser un problema claro sobre {topic}
- Adapta la dificultad al nivel {student_level}
- La respuesta debe ser un número (entero o decimal) o expresión algebraica simple
- NO uses asteriscos (*) en la pregunta
"""
    
    prompt = f"""
Eres un profesor de matemáticas especializado en {topic}. Genera {quantity} ejercicios sobre "{topic}" para nivel {student_level}.

{format_instruction}

REGLAS ADICIONALES:
- Las preguntas deben ser CLARAS y DIRECTAS
- Las pistas deben ser ÚTILES pero NO deben revelar la respuesta
- Si es posible, que las respuestas sean números enteros
- Varía los ejercicios (no uses siempre el mismo patrón)

RESPONDE SOLO CON UN JSON. FORMATO EXACTO:
[
    {{
        "pregunta": "texto del ejercicio",
        "respuesta_esperada": "número o expresión",
        "pista": "pista breve sin dar la respuesta (máximo 10 palabras)"
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
            if 'respuesta_esperada' not in ex:
                raise Exception(f"Ejercicio sin respuesta_esperada: {ex.get('pregunta', '?')}")
            
            ex['is_math'] = True
            
            if 'pista' in ex:
                ex['pista'] = ex['pista'].replace('*', '').replace('_', '')
                # Limitar pista a 12 palabras
                words = ex['pista'].split()
                if len(words) > 12:
                    ex['pista'] = ' '.join(words[:12]) + '...'
            if 'pregunta' in ex:
                ex['pregunta'] = ex['pregunta'].replace('*', '').replace('_', '')
            
            # Intentar normalizar respuesta numérica si es posible
            try:
                # Si la respuesta es un número (entero o decimal)
                test_num = float(ex['respuesta_esperada'].replace('x', '0').replace('θ', '0').split()[0] if ' ' in ex['respuesta_esperada'] else ex['respuesta_esperada'])
                ex['respuesta_esperada'] = normalize_numeric_answer(ex['respuesta_esperada'])
            except:
                # Si no es numérico (como "2x" o "x²"), mantener como está
                pass

        print(f"✅ Generados {len(exercises)} ejercicios sobre '{topic}'")
        return exercises

    except json.JSONDecodeError as e:
        raise Exception(f"La IA no devolvió JSON válido: {str(e)}")
    except Exception as e:
        raise Exception(f"Error generando ejercicios: {str(e)}")


def give_feedback(student_answer, correct_answer, student_level, is_math=False):
    """Genera retroalimentación personalizada para una respuesta"""
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

Genera retroalimentación educativa (máximo 2 oraciones):
- Si es correcto: felicita y refuerza el aprendizaje
- Si es incorrecto: explica amablemente y da una pista
- NO uses asteriscos (*) ni guiones bajos (_)
- Sé breve y directo
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


def generate_exercises(topic, student_level, quantity=3):
    """Versión simple para compatibilidad - devuelve texto plano"""
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