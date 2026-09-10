"""
Diagnóstico adaptativo con Cognitive Diagnostic Assessment (CDA)
Basado en: 
- Computerized Adaptive Assessment and Learning System (MDPI, 2025) [citation:1]
- Zona de Desarrollo Próximo (Vygotsky) [citation:4]
- Instructional Scaffolding (TPM, 2025) [citation:9]
"""

import ollama
from config import OLLAMA_MODEL
import json
import re
from cognitive_diagnostic import CognitiveDiagnosticProfile

# Almacenamiento temporal de perfiles (en producción, guardar en BD)
active_profiles = {}

def generate_adaptive_questions(profile: CognitiveDiagnosticProfile, num_questions: int = 3):
    """
    Genera preguntas adaptativas basadas en el perfil cognitivo
    Implementa Computerized Adaptive Testing (CAT) adaptativo [citation:1][citation:8]
    """
    
    target_level = profile.get_next_difficulty()
    zpd_attrs = profile.zpd_attributes
    
    # Construir prompt enfocado en ZPD
    zpd_focus = ""
    if zpd_attrs:
        zpd_focus = f"\nEnfócate especialmente en los atributos en Zona de Desarrollo Próximo: {', '.join(zpd_attrs)}"
    
    prompt = f"""
Eres un tutor experto en matemáticas que aplica principios de Cognitive Diagnostic Assessment (CDA).

Perfil del estudiante:
- Nivel actual: {profile.current_level}
- Atributos dominados: {[a for a, v in profile.attribute_mastery.items() if v >= 0.7]}
- Atributos en Zona de Desarrollo Próximo (ZPD): {zpd_attrs}
- Atributos no dominados: {[a for a, v in profile.attribute_mastery.items() if v < 0.3]}

Zona de Desarrollo Próximo (Vygotsky): {zpd_focus}

Genera {num_questions} preguntas de matemáticas (ecuaciones de primer grado o teorema de Pitágoras).

REGLAS:
1. Las preguntas deben estar en el nivel {target_level}
2. Prioriza trabajar los atributos en ZPD (ayuda con andamiaje)
3. Si hay atributos no dominados, incluye preguntas básicas sobre ellos
4. Alterna entre diferentes tipos de problemas (interleaving)
5. Incluye tanto respuestas abiertas como opción múltiple

Formato JSON:
[
    {{
        "pregunta": "...",
        "tipo": "abierta" o "opcion_multiple",
        "opciones": ["..."] (solo si tipo es opcion_multiple),
        "respuesta_esperada": "...",
        "nivel": "{target_level}",
        "atributos_evaluados": ["A1", "A2", ...],
        "scaffolding_hint": "pista opcional para ayudar"
    }}
]
"""
    
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        questions = json.loads(content)
        return questions
    except Exception as e:
        print(f"Error generando preguntas adaptativas: {e}")
        return generate_fallback_questions(target_level, num_questions)

def generate_fallback_questions(level: str, num_questions: int = 3):
    """Preguntas de respaldo estructuradas por atributos cognitivos"""
    bank = {
        "basico": [
            {"pregunta": "x + 3 = 7, ¿cuánto vale x?", "tipo": "abierta", "respuesta_esperada": "4", 
             "nivel": "basico", "atributos_evaluados": ["A1", "A2"]},
            {"pregunta": "y - 5 = 2, ¿cuánto vale y?", "tipo": "abierta", "respuesta_esperada": "7",
             "nivel": "basico", "atributos_evaluados": ["A1", "A2"]},
            {"pregunta": "¿Qué número satisface a + 4 = 9?", "tipo": "abierta", "respuesta_esperada": "5",
             "nivel": "basico", "atributos_evaluados": ["A1", "A2", "A6"]}
        ],
        "intermedio": [
            {"pregunta": "3x = 24, ¿cuánto vale x?", "tipo": "abierta", "respuesta_esperada": "8",
             "nivel": "intermedio", "atributos_evaluados": ["A1", "A2", "A3"]},
            {"pregunta": "2x + 5 = 15, ¿cuánto vale x?", "tipo": "abierta", "respuesta_esperada": "5",
             "nivel": "intermedio", "atributos_evaluados": ["A1", "A2", "A3", "A6"]}
        ],
        "avanzado": [
            {"pregunta": "3(x - 2) = 15, ¿cuánto vale x?", "tipo": "abierta", "respuesta_esperada": "7",
             "nivel": "avanzado", "atributos_evaluados": ["A1", "A2", "A3", "A4", "A5"]},
            {"pregunta": "2x + 5 = x + 12, ¿cuánto vale x?", "tipo": "abierta", "respuesta_esperada": "7",
             "nivel": "avanzado", "atributos_evaluados": ["A1", "A2", "A3", "A4", "A5", "A6"]}
        ]
    }
    return bank.get(level, bank["basico"])[:num_questions]

def adaptive_diagnostic_session(student_name: str, num_rounds: int = 4, questions_per_round: int = 3):
    """
    Sesión de diagnóstico adaptativo completa
    Implementa Cognitive Diagnostic Assessment (CDA) [citation:1]
    """
    
    # Inicializar perfil cognitivo
    profile = CognitiveDiagnosticProfile(student_name)
    
    print(f"\n{'='*60}")
    print(f"🎯 DIAGNÓSTICO ADAPTATIVO COGNITIVO para {student_name}")
    print(f"{'='*60}")
    print(f"Basado en Cognitive Diagnostic Assessment (CDA)")
    print(f"Se evaluarán {num_rounds} rondas de {questions_per_round} preguntas cada una.")
    print(f"Las preguntas se adaptan a tu Zona de Desarrollo Próximo (Vygotsky).\n")
    
    for round_num in range(1, num_rounds + 1):
        print(f"\n--- Ronda {round_num} de {num_rounds} ---")
        print(f"Nivel actual: {profile.current_level.upper()}")
        
        if profile.zpd_attributes:
            print(f"🌱 Trabajando en: {', '.join(profile.zpd_attributes)}")
        
        questions = generate_adaptive_questions(profile, questions_per_round)
        
        for q in questions:
            print(f"\n📝 {q['pregunta']}")
            
            if q.get('scaffolding_hint'):
                print(f"💡 Pista: {q['scaffolding_hint']} [citation:9]")
            
            answer = input("Tu respuesta: ").strip()
            is_correct = answer == q['respuesta_esperada']
            
            # Actualizar perfil cognitivo
            profile.update_from_response(q, is_correct)
            
            if is_correct:
                print("   ✅ Correcto")
            else:
                print(f"   ❌ Incorrecto. Respuesta esperada: {q['respuesta_esperada']}")
        
        # Mostrar progreso
        print(profile.generate_feedback())
    
    print(f"\n{'='*60}")
    print(f"📊 DIAGNÓSTICO COMPLETADO")
    print(f"🎓 Nivel final: {profile.current_level.upper()}")
    print(profile.generate_feedback())
    print(f"{'='*60}")
    
    # Guardar perfil para uso futuro
    active_profiles[student_name] = profile
    
    return profile.current_level, profile.attribute_mastery, profile.to_dict()