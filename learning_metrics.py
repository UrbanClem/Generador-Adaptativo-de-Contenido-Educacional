from database import SessionLocal, PrePostTest
import ollama
from config import OLLAMA_MODEL
import json
import re

def generate_test_questions(topic, difficulty, num_questions=3):
    """Genera preguntas de evaluación pre/post usando IA"""
    
    prompt = f"""
Genera {num_questions} preguntas de opción múltiple sobre "{topic}" con dificultad {difficulty}.

Formato JSON (sin texto adicional):
[
    {{
        "question": "texto de la pregunta",
        "options": ["opción A", "opción B", "opción C", "opción D"],
        "correct": 0
    }}
]
"""
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        return json.loads(content)
    except Exception as e:
        print(f"Error generando preguntas: {e}")
        return [
            {"question": f"¿Qué es el teorema de Pitágoras?", 
             "options": ["a² + b² = c²", "a + b = c", "a × b = c", "a / b = c"], 
             "correct": 0},
            {"question": "Resuelve: x + 5 = 10",
             "options": ["5", "10", "15", "2"],
             "correct": 0},
            {"question": "En un triángulo rectángulo, la hipotenusa es...",
             "options": ["El lado más largo", "El lado más corto", "El lado opuesto al ángulo recto", "Todas son correctas"],
             "correct": 3}
        ][:num_questions]

def calculate_learning_gain_with_ai(student_id, topic):
    """Calcula la ganancia de aprendizaje y genera un análisis cualitativo"""
    
    session = SessionLocal()
    pre_test = session.query(PrePostTest).filter_by(
        student_id=student_id, topic=topic, test_type='pre'
    ).first()
    post_test = session.query(PrePostTest).filter_by(
        student_id=student_id, topic=topic, test_type='post'
    ).first()
    session.close()
    
    if not pre_test or not post_test:
        return {"error": "No hay suficientes datos. Completa ambas evaluaciones (pre y post)."}
    
    gain = post_test.score - pre_test.score
    normalized_gain = gain / (100 - pre_test.score) if pre_test.score < 100 else 0
    
    # Usar IA para generar análisis cualitativo
    analysis_prompt = f"""
Analiza el progreso de un estudiante en el tema "{topic}":
- Pre-test: {pre_test.score:.1f}%
- Post-test: {post_test.score:.1f}%
- Ganancia absoluta: {gain:.1f} puntos
- Ganancia normalizada (Hake gain): {normalized_gain:.3f}

Genera un breve análisis cualitativo (máximo 100 palabras) sobre su aprendizaje.
"""
    
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': analysis_prompt}])
        qualitative_analysis = response['message']['content']
    except:
        qualitative_analysis = "El estudiante mostró mejora en su desempeño después de la intervención."
    
    return {
        "pre_score": pre_test.score,
        "post_score": post_test.score,
        "gain": gain,
        "normalized_gain": normalized_gain,
        "qualitative_analysis": qualitative_analysis
    }