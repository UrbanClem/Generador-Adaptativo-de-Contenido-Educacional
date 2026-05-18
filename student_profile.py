from database import SessionLocal, Student, ExerciseResult
import json

def diagnostic_assessment():
    print("\n=== EVALUACIÓN DIAGNÓSTICA ===")
    print("Responde 5 preguntas para determinar tu nivel:")
    
    questions = [
        {"pregunta": "x + 3 = 7, ¿cuánto vale x?", "respuesta": "4", "nivel": "basico", "puntos": 10},
        {"pregunta": "2x - 5 = 9, ¿cuánto vale x?", "respuesta": "7", "nivel": "intermedio", "puntos": 20},
        {"pregunta": "3(x - 4) = 2x + 1, ¿cuánto vale x?", "respuesta": "13", "nivel": "avanzado", "puntos": 30},
        {"pregunta": "Resuelve: 5x + 2 = 3x + 10", "respuesta": "4", "nivel": "intermedio", "puntos": 20},
        {"pregunta": "¿Cuál es la solución de 2(3x - 1) = 4x + 6?", "respuesta": "4", "nivel": "avanzado", "puntos": 30}
    ]
    
    score = 0
    total_points = 0
    level_count = {"basico": 0, "intermedio": 0, "avanzado": 0}
    
    for q in questions:
        print(f"\n{q['pregunta']}")
        user_answer = input("Tu respuesta: ").strip()
        total_points += q["puntos"]
        if user_answer == q["respuesta"]:
            score += q["puntos"]
            level_count[q["nivel"]] += 1
    
    # Calcular nivel_score (0-100)
    level_score = (score / total_points) * 100
    
    # Determinar nivel basado en puntaje continuo
    if level_score >= 70:
        level = "avanzado"
    elif level_score >= 40:
        level = "intermedio"
    else:
        level = "basico"
    
    print(f"\nPuntaje: {score}/{total_points} ({level_score:.1f}%)")
    print(f"Nivel asignado: {level}")
    
    return level, level_score, {"score": score, "total": total_points, "level_score": level_score, "details": level_count}

def create_or_get_student(session, name):
    student = session.query(Student).filter_by(name=name).first()
    if not student:
        print(f"\n📝 Estudiante nuevo. Realizando evaluación diagnóstica...")
        level, level_score, results = diagnostic_assessment()
        student = Student(
            name=name, 
            level=level, 
            level_score=level_score,
            diagnostic_results=results,
            interaction_history=[]
        )
        session.add(student)
        session.commit()
        print(f"✅ Estudiante {name} registrado con nivel {level} (puntaje: {level_score:.1f}%)")
    else:
        print(f"\n✅ Bienvenido de vuelta {student.name} (nivel: {student.level}, puntaje: {student.level_score:.1f}%)")
    
    session.refresh(student)
    return student

def update_student_profile(session, student, exercise_result, topic):
    """Actualiza el perfil del estudiante dinámicamente basado en su desempeño"""
    
    # Registrar el ejercicio en el historial
    if student.interaction_history is None:
        student.interaction_history = []
    
    student.interaction_history.append({
        "topic": topic,
        "is_correct": exercise_result.get("is_correct", False),
        "attempts": exercise_result.get("attempts", 1),
        "timestamp": str(datetime.utcnow())
    })
    
    # Mantener solo las últimas 20 interacciones
    if len(student.interaction_history) > 20:
        student.interaction_history = student.interaction_history[-20:]
    
    # Calcular tasa de aciertos reciente (últimas 10 interacciones)
    recent = student.interaction_history[-10:]
    if recent:
        correct_count = sum(1 for i in recent if i.get("is_correct", False))
        success_rate = (correct_count / len(recent)) * 100
    else:
        success_rate = student.level_score
    
    # Actualizar level_score (70% peso histórico + 30% peso reciente)
    student.level_score = (student.level_score * 0.7) + (success_rate * 0.3)
    
    # Actualizar nivel basado en nuevo puntaje
    if student.level_score >= 70:
        new_level = "avanzado"
    elif student.level_score >= 40:
        new_level = "intermedio"
    else:
        new_level = "basico"
    
    # Registrar cambio de nivel
    if new_level != student.level:
        print(f"\n🎉 ¡Felicidades! Has subido de nivel: {student.level} → {new_level}")
        student.level = new_level
    
    # Registrar errores comunes
    if not exercise_result.get("is_correct", True):
        error_type = exercise_result.get("error_type", "general")
        if student.common_errors is None:
            student.common_errors = []
        student.common_errors.append({
            "topic": topic,
            "error_type": error_type,
            "timestamp": str(datetime.utcnow())
        })
        # Mantener solo últimos 10 errores
        if len(student.common_errors) > 10:
            student.common_errors = student.common_errors[-10:]
    
    session.commit()
    return student