from database import SessionLocal
from student_profile import create_or_get_student
from rag_engine import load_knowledge_base
from content_generator import generate_explanation, generate_exercises, give_feedback

def main():
    print("=== GENERADOR ADAPTATIVO DE CONTENIDOS EDUCATIVOS CON IA ===\n")
    
    # 1. Cargar documentos
    load_knowledge_base()
    
    # 2. Identificar estudiante
    name = input("Nombre del estudiante: ")
    student = create_or_get_student(name)
    
    while True:
        print(f"\n--- Menú para {student.name} (nivel: {student.level}) ---")
        print("1. Generar explicación personalizada")
        print("2. Generar ejercicios de práctica")
        print("3. Simular retroalimentación")
        print("4. Salir")
        
        option = input("Opción: ")
        
        if option == "1":
            topic = input("¿Qué tema quieres aprender? ")
            explanation = generate_explanation(topic, student.level)
            print(f"\n🔹 EXPLICACIÓN:\n{explanation}\n")
        
        elif option == "2":
            topic = input("¿Sobre qué tema quieres ejercicios? ")
            exercises = generate_exercises(topic, student.level)
            print(f"\n📝 EJERCICIOS:\n{exercises}\n")
        
        elif option == "3":
            user_answer = input("Tu respuesta: ")
            correct = input("Respuesta correcta: ")
            feedback = give_feedback(user_answer, correct, student.level)
            print(f"\n💬 RETROALIMENTACIÓN:\n{feedback}\n")
        
        elif option == "4":
            print("¡Hasta luego!")
            break

if __name__ == "__main__":
    main()