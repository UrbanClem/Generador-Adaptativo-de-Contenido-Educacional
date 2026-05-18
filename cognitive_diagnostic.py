"""
Sistema de Diagnóstico Cognitivo basado en CDA (Cognitive Diagnostic Assessment)
SOLO USA IA - SIN PREGUNTAS PREDETERMINADAS
"""

import ollama
import json
import re
from typing import List, Dict, Any
from database import SessionLocal, CognitiveProfile

# ========== CONFIGURACIÓN ==========
MODEL_NAME = "mistral:latest"  # Usar Mistral (mejor calidad)

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
    """
    Resuelve ecuaciones de primer grado usando Python (NO IA)
    """
    try:
        eq = equation.replace(" ", "").lower()
        
        if "=" not in eq:
            return None
        
        left, right = eq.split("=")
        
        x_match = re.search(r'([+-]?\d*)(x)', left)
        if not x_match:
            return None
        
        coef_str = x_match.group(1)
        if coef_str == "" or coef_str == "+":
            x_term = 1
        elif coef_str == "-":
            x_term = -1
        else:
            x_term = int(coef_str)
        
        rest = left.replace(x_match.group(0), "")
        if rest == "" or rest == "+":
            constant = 0
        elif rest.startswith("+"):
            constant = int(rest[1:]) if rest[1:] else 0
        else:
            constant = int(rest) if rest else 0
        
        right_val = int(right)
        result = (right_val - constant) / x_term
        
        if result == int(result):
            return str(int(result))
        else:
            return str(round(result, 2))
            
    except Exception as e:
        print(f"Error resolviendo ecuación '{equation}': {e}")
        return None


# ========== GENERADOR DE PREGUNTAS SOLO CON IA ==========

def generate_adaptive_questions(profile: CognitiveDiagnosticProfile, num_questions: int = 3):
    """
    Genera preguntas usando SOLO IA.
    Si la IA falla o da respuestas inválidas, LANZA EXCEPCIÓN.
    """
    
    target_level = profile.get_next_difficulty()
    
    # Obtener preguntas ya usadas
    used_questions = [r.get("question", "") for r in profile.response_history if r.get("question")]
    
    forbidden = ""
    if used_questions:
        forbidden = f"\n\n⚠️ PREGUNTAS PROHIBIDAS (NO LAS REPITAS):\n"
        for q in used_questions[-15:]:
            forbidden += f"- {q}\n"
    
    prompt = f"""
Eres un profesor de matemáticas. Genera {num_questions} ecuaciones de PRIMER GRADO.

Nivel: {target_level}

{forbidden}

REGLAS ESTRICTAS:
- Usa el formato: "5x - 17 = 8" (SOLO la ecuación, sin texto extra)
- Variables solo 'x', números enteros entre 1 y 50
- La respuesta debe ser un número entero
- NO uses problemas de palabras
- NO incluyas texto adicional fuera del JSON

RESPONDE SOLO CON UN JSON. FORMATO EXACTO:
[
    {{"pregunta": "2x + 3 = 11", "respuesta_esperada": "4"}}
]
"""
    
    response = ollama.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}])
    content = response['message']['content'].strip()
    
    # Limpiar markdown
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    
    try:
        questions = json.loads(content)
    except json.JSONDecodeError as e:
        raise Exception(f"La IA no devolvió JSON válido: {str(e)}. Respuesta: {content[:200]}")
    
    if not questions or len(questions) == 0:
        raise Exception("La IA no generó preguntas")
    
    valid_questions = []
    for i, q in enumerate(questions):
        equation = q.get("pregunta", "")
        if not equation:
            raise Exception(f"Pregunta {i+1} sin campo 'pregunta'")
        
        # Calcular respuesta REAL con Python
        real_answer = solve_equation(equation)
        
        if real_answer is None:
            raise Exception(f"No se pudo resolver la ecuación: {equation}")
        
        # Verificar que la ecuación no esté repetida
        if equation in used_questions:
            raise Exception(f"Pregunta repetida: {equation}")
        
        q["respuesta_esperada"] = real_answer
        q["tipo"] = "abierta"
        q["nivel"] = target_level
        q["scaffolding_hint"] = get_hint_by_equation_type(equation)
        
        valid_questions.append(q)
    
    if len(valid_questions) < num_questions:
        raise Exception(f"Solo se generaron {len(valid_questions)} preguntas válidas de {num_questions}")
    
    print(f"✅ Generadas {len(valid_questions)} preguntas con IA para nivel {target_level}")
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