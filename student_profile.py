from database import SessionLocal, Student

def diagnostic_assessment():
    print("\n=== EVALUACIÓN DIAGNÓSTICA ===")
    print("Responde 5 preguntas para determinar tu nivel:")
    
    questions = [
        {"pregunta": "x + 3 = 7, ¿cuánto vale x?", "respuesta": "4", "nivel": "basico"},
        {"pregunta": "2x - 5 = 9, ¿cuánto vale x?", "respuesta": "7", "nivel": "intermedio"},
        {"pregunta": "3(x - 4) = 2x + 1, ¿cuánto vale x?", "respuesta": "13", "nivel": "avanzado"},
        {"pregunta": "Resuelve: 5x + 2 = 3x + 10", "respuesta": "4", "nivel": "intermedio"},
        {"pregunta": "¿Cuál es la solución de 2(3x - 1) = 4x + 6?", "respuesta": "4", "nivel": "avanzado"}
    ]
    
    score = 0
    level_count = {"basico": 0, "intermedio": 0, "avanzado": 0}
    
    for q in questions:
        print(f"\n{q['pregunta']}")
        user_answer = input("Tu respuesta: ").strip()
        if user_answer == q["respuesta"]:
            score += 1
            level_count[q["nivel"]] += 1
    
    # Determinar nivel
    if level_count["avanzado"] >= 3:
        level = "avanzado"
    elif level_count["intermedio"] >= 3:
        level = "intermedio"
    else:
        level = "basico"
    
    print(f"\nPuntaje: {score}/5")
    print(f"Nivel asignado: {level}")
    
    return level, {"score": score, "level": level, "details": level_count}

def create_or_get_student(name):
    session = SessionLocal()
    student = session.query(Student).filter_by(name=name).first()
    if not student:
        level, results = diagnostic_assessment()
        student = Student(name=name, level=level, diagnostic_results=results)
        session.add(student)
        session.commit()
    else:
        print(f"\nBienvenido de vuelta {student.name} (nivel: {student.level})")
    session.close()
    return student