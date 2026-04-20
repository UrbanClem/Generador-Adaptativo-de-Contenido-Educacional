from rag_engine import retrieve_context, generate_with_llm

def generate_explanation(topic, student_level):
    context = retrieve_context(topic)
    
    prompt = f"""
Eres un tutor adaptativo de matemáticas (ecuaciones de primer grado).

Nivel del estudiante: {student_level}

Contexto educativo:
{context}

Tarea:
Genera una explicación personalizada sobre "{topic}" adecuada para el nivel {student_level}.

- Si es básico: usa ejemplos simples, paso a paso.
- Si es intermedio: incluye variaciones y conexiones.
- Si es avanzado: profundiza en conceptos y aplicaciones.
"""
    return generate_with_llm(prompt)

def generate_exercises(topic, student_level, quantity=3):
    prompt = f"""
Genera {quantity} ejercicios de práctica sobre "{topic}" para un estudiante de nivel {student_level}.

Formato:
Ejercicio 1: ...
Ejercicio 2: ...
Ejercicio 3: ...

Incluye las respuestas al final.
"""
    return generate_with_llm(prompt)

def give_feedback(student_answer, correct_answer, student_level):
    prompt = f"""
Estudiante de nivel {student_level} respondió: "{student_answer}"
Respuesta correcta: "{correct_answer}"

Genera retroalimentación personalizada:
- Si es correcto: refuerza el aprendizaje.
- Si es incorrecto: explica el error sin frustrar.
- Da una sugerencia concreta.
"""
    return generate_with_llm(prompt)