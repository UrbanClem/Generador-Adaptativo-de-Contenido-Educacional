print("Iniciando el servidor... (cargar el modelo de embeddings tarda"
      " entre 20 y 60 segundos la primera vez)", flush=True)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from seudonimo import hash_nombre, siguiente_codigo
from database import SessionLocal, Student, PrePostTest, Assignment, MaterialReview
from rag_engine import load_knowledge_base, recargar_knowledge_base, info_corpus, retrieve_pertinentes
from content_generator import generate_explanation, generate_exercises, give_feedback
from cognitive_diagnostic import CognitiveDiagnosticProfile, generate_adaptive_questions, evaluate_answer_semantic
from config import KNOWLEDGE_DOCENTE
from docente_utils import nombre_corpus_seguro, calcular_metricas
from datetime import datetime
import time
import os
import json

app = Flask(__name__, static_folder='frontend', static_url_path='/frontend')
CORS(app)

# Cargar base de conocimiento al iniciar
load_knowledge_base()

print("Todo listo. Abre http://localhost:5000 en el navegador "
      "(Ctrl+C aqui para detenerlo).", flush=True)

# ========== PREGUNTAS DEL DIAGNÓSTICO (FALLBACK) ==========
DIAGNOSTIC_QUESTIONS = [
    {"pregunta": "x + 3 = 7, ¿cuánto vale x?", "respuesta": "4", "nivel": "basico", "puntos": 10},
    {"pregunta": "2x - 5 = 9, ¿cuánto vale x?", "respuesta": "7", "nivel": "intermedio", "puntos": 20},
    {"pregunta": "3(x - 4) = 2x + 1, ¿cuánto vale x?", "respuesta": "13", "nivel": "avanzado", "puntos": 30},
    {"pregunta": "Resuelve: 5x + 2 = 3x + 10", "respuesta": "4", "nivel": "intermedio", "puntos": 20},
    {"pregunta": "¿Cuál es la solución de 2(3x - 1) = 4x + 6?", "respuesta": "4", "nivel": "avanzado", "puntos": 30}
]

# ========== SIRVE EL FRONTEND ==========
@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/frontend/<path:path>')
def serve_frontend(path):
    return send_from_directory('frontend', path)

@app.route('/style.css')
def serve_css():
    return send_from_directory('frontend', 'style.css')

@app.route('/frontend/app.js')
def serve_js():
    return send_from_directory('frontend', 'app.js')

# ========== ENDPOINTS DE ESTUDIANTES ==========

@app.route('/students/<name>', methods=['GET'])
def get_student(name):
    """Busca al participante por la huella de su nombre.

    El nombre llega para poder reconocerlo, pero no se guarda ni se devuelve:
    lo que sale es el seudonimo.
    """
    db = SessionLocal()
    student = db.query(Student).filter_by(name_hash=hash_nombre(name)).first()
    db.close()
    
    if student:
        return jsonify({
            "id": student.id,
            "name": student.name,
            "level": student.level,
            "level_score": student.level_score
        })
    else:
        return jsonify({"error": "Estudiante no encontrado"}), 404

@app.route('/students', methods=['POST'])
def create_student():
    data = request.json
    db = SessionLocal()
    
    # El nombre que llega solo sirve para calcular la huella; no se almacena.
    huella = hash_nombre(data['name'])
    existente = db.query(Student).filter_by(name_hash=huella).first()
    if existente is not None:
        datos = {"success": True, "id": existente.id, "name": existente.name,
                 "level": existente.level, "level_score": existente.level_score}
        db.close()
        return jsonify(datos)

    codigo = siguiente_codigo(c for (c,) in db.query(Student.name).all())

    student = Student(
        name=codigo,
        name_hash=huella,
        level=data.get('level', 'basico'),
        level_score=data.get('level_score', 50),
        diagnostic_results=data.get('diagnostic_results', {}),
        interaction_history=[]
    )
    db.add(student)
    db.commit()
    
    # ✅ Guardar los valores ANTES de cerrar la sesión
    student_id = student.id
    student_name = student.name
    student_level = student.level
    student_level_score = student.level_score
    
    db.close()
    
    return jsonify({
        "success": True, 
        "id": student_id, 
        "name": student_name, 
        "level": student_level,
        "level_score": student_level_score
    })

# ========== ENDPOINTS DE DIAGNÓSTICO TRADICIONAL ==========

@app.route('/diagnostic/questions', methods=['GET'])
def get_diagnostic_questions():
    return jsonify(DIAGNOSTIC_QUESTIONS)

@app.route('/diagnostic/evaluate', methods=['POST'])
def evaluate_diagnostic():
    data = request.json
    answers = data.get('answers', [])
    
    score = 0
    total_points = 0
    level_count = {"basico": 0, "intermedio": 0, "avanzado": 0}
    
    for i, q in enumerate(DIAGNOSTIC_QUESTIONS):
        total_points += q["puntos"]
        if i < len(answers) and answers[i].strip() == q["respuesta"]:
            score += q["puntos"]
            level_count[q["nivel"]] += 1
    
    level_score = (score / total_points) * 100 if total_points > 0 else 0
    
    if level_score >= 70:
        level = "avanzado"
    elif level_score >= 40:
        level = "intermedio"
    else:
        level = "basico"
    
    return jsonify({
        "score": score,
        "total": total_points,
        "level_score": level_score,
        "level": level,
        "level_counts": level_count
    })

# ========== ENDPOINTS DE DIAGNÓSTICO ADAPTATIVO ==========

active_sessions = {}

@app.route('/student/progress', methods=['POST'])
def update_progress():
    data = request.json
    student_id = data.get('student_id')
    question = data.get('question')
    is_correct = data.get('is_correct')
    topic = data.get('topic')
    
    # Actualizar historial de interacciones del estudiante
    db = SessionLocal()
    student = db.query(Student).filter_by(id=student_id).first()
    if student:
        if not student.interaction_history:
            student.interaction_history = []
        student.interaction_history.append({
            "topic": topic,
            "question": question,
            "is_correct": is_correct,
            "timestamp": datetime.utcnow().isoformat()
        })
        db.commit()
    db.close()
    
    return jsonify({"success": True})

@app.route('/diagnostic/test', methods=['POST'])
def test_diagnostic():
    """Prueba si la IA puede generar preguntas - SIN FALLBACK"""
    try:
        from cognitive_diagnostic import generate_test_questions_only
        generate_test_questions_only()
        return jsonify({"success": True, "message": "IA disponible"})
    except Exception as e:
        print(f"Error en test de IA: {str(e)}")
        return jsonify({"error": f"IA no disponible: {str(e)}"}), 503

@app.route('/diagnostic/start', methods=['POST'])
def start_adaptive_diagnostic():
    data = request.json
    student_id = data.get('student_id')
    student_name = data.get('student_name')
    
    if not student_id or not student_name:
        return jsonify({"error": "Se requiere student_id y student_name"}), 400
    
    try:
        from cognitive_diagnostic import CognitiveDiagnosticProfile, generate_adaptive_questions
        
        profile = CognitiveDiagnosticProfile(student_id, student_name)
        questions = generate_adaptive_questions(profile, num_questions=3)
        
        session_id = f"{student_id}_{int(time.time())}"
        total_rounds = 4
        
        active_sessions[session_id] = {
            "profile": profile,
            "current_round": 1,
            "total_rounds": total_rounds,
            "questions_remaining": questions,
            "answers_history": []
        }
        
        return jsonify({
            "session_id": session_id,
            "current_level": profile.current_level,
            "zpd_attributes": profile.zpd_attributes,
            "questions": questions,
            "round": 1,
            "total_rounds": total_rounds
        })
        
    except Exception as e:
        print(f"Error iniciando diagnóstico: {str(e)}")
        return jsonify({"error": f"Error con IA: {str(e)}"}), 503

@app.route('/diagnostic/answer', methods=['POST'])
def process_diagnostic_answer():
    data = request.json
    session_id = data.get('session_id')
    question_text = data.get('question')
    student_answer = data.get('student_answer')
    expected_answer = data.get('expected_answer')
    response_time = data.get('response_time')
    
    session = active_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Sesión no encontrada"}), 404
    
    profile = session["profile"]
    
    # Evaluar respuesta
    from cognitive_diagnostic import evaluate_answer_semantic
    is_correct = evaluate_answer_semantic(question_text, student_answer, expected_answer)
    
    # Crear objeto pregunta para el perfil
    question_obj = {
        "pregunta": question_text,
        "tipo": "abierta",
        "nivel": profile.current_level
    }
    
    # Actualizar perfil cognitivo
    profile.update_from_response(question_obj, is_correct, response_time)
    
    # Registrar respuesta
    session["answers_history"].append({
        "question": question_text,
        "student_answer": student_answer,
        "is_correct": is_correct,
        "response_time": response_time
    })
    
    # Remover la pregunta respondida
    if session["questions_remaining"] and len(session["questions_remaining"]) > 0:
        session["questions_remaining"].pop(0)
    
    new_questions = []
    next_round = session["current_round"]
    is_complete = False
    
    # Si no hay más preguntas en esta ronda
    if not session["questions_remaining"] or len(session["questions_remaining"]) == 0:
        next_round = session["current_round"] + 1
        session["current_round"] = next_round
        
        if next_round <= session["total_rounds"]:
            # Generar nuevas preguntas para la siguiente ronda
            new_questions = generate_adaptive_questions(profile, num_questions=3)
            session["questions_remaining"] = new_questions
            print(f"🔄 Nueva ronda {next_round}: {len(new_questions)} preguntas generadas")
        else:
            # Diagnóstico completado
            is_complete = True
            print(f"✅ Diagnóstico completado para {profile.student_name}")
            del active_sessions[session_id]
    
    # Preparar respuesta
    response_data = {
        "is_correct": is_correct,
        "feedback": {
            "reasoning": "Evaluación completada",
            "level_adjustment": 10 if is_correct else -5
        },
        "current_level": profile.current_level,
        "profile_feedback": profile.get_feedback(),
        "is_complete": is_complete
    }
    
    # Si hay nuevas preguntas, enviarlas
    if new_questions and len(new_questions) > 0:
        response_data["next_questions"] = new_questions
        response_data["next_round"] = next_round
    
    # Si aún hay preguntas en la ronda actual, enviar la siguiente
    elif session.get("questions_remaining") and len(session["questions_remaining"]) > 0:
        response_data["next_questions"] = session["questions_remaining"]
        response_data["next_round"] = session["current_round"]
    
    return jsonify(response_data)

@app.route('/diagnostic/status/<session_id>', methods=['GET'])
def get_diagnostic_status(session_id):
    session = active_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Sesión no encontrada"}), 404
    
    profile = session["profile"]
    return jsonify({
        "current_level": profile.current_level,
        "profile_feedback": profile.get_feedback(),
        "current_round": session["current_round"],
        "total_rounds": session["total_rounds"],
        "questions_remaining": session["questions_remaining"]
    })

# ========== ENDPOINTS DE CONTENIDO ==========

@app.route('/explain', methods=['POST'])
def explain():
    data = request.json
    topic = data.get('topic')
    student_level = data.get('student_level', 'basico')
    explanation, fragmentos = generate_explanation(topic, student_level,
                                                   con_fragmentos=True)
    fuentes = []
    for f in fragmentos:
        if f["fuente"] and f["fuente"] not in fuentes:
            fuentes.append(f["fuente"])
    return jsonify({"content": explanation, "topic": topic, "level": student_level,
                    "fuentes": fuentes, "fragmentos": fragmentos})

@app.route('/exercises', methods=['POST'])
def exercises():
    """Genera ejercicios de práctica - formato estructurado para respuestas

    Los ejercicios se anclan al corpus con los fragmentos recuperados para el
    tema, igual que las explicaciones (extensión del anclaje documental).
    """
    data = request.json
    topic = data.get('topic', 'matemáticas')
    student_level = data.get('student_level', 'basico')
    quantity = data.get('quantity', 3)
    
    from content_generator import generate_exercises_with_answers
    pasajes = retrieve_pertinentes(topic, n_results=3)
    material = '\n\n---\n\n'.join(p["texto"] for p in pasajes) or None
    exercises = generate_exercises_with_answers(topic, student_level, quantity,
                                                material=material)
    fragmentos = [{"fuente": p["fuente"], "texto": p["texto"]} for p in pasajes]

    return jsonify({
        "exercises": exercises,
        "topic": topic,
        "level": student_level,
        "fragmentos": fragmentos
    })


@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    student_answer = data.get('student_answer')
    correct_answer = data.get('correct_answer')
    student_level = data.get('student_level', 'basico')
    topic = data.get('topic')
    material = None
    if topic:
        pasajes = retrieve_pertinentes(topic, n_results=3)
        material = '\n\n---\n\n'.join(p["texto"] for p in pasajes) or None
    feedback_text = give_feedback(student_answer, correct_answer, student_level,
                                  material=material)
    return jsonify({"content": feedback_text, "is_correct": student_answer.strip() == correct_answer.strip()})

# ========== ENDPOINTS DE MÉTRICAS ==========

@app.route('/test/save', methods=['POST'])
def save_test_result():
    data = request.json
    student_id = data.get('student_id')
    topic = data.get('topic')
    test_type = data.get('test_type')
    score = data.get('score')
    answers = data.get('answers', {})
    
    db = SessionLocal()
    test_record = PrePostTest(
        student_id=student_id,
        topic=topic,
        test_type=test_type,
        score=score,
        answers=answers
    )
    db.add(test_record)
    db.commit()
    db.close()
    
    return jsonify({"success": True})

@app.route('/learning/gain', methods=['GET'])
def get_learning_gain():
    student_id = request.args.get('student_id', type=int)
    topic = request.args.get('topic')
    
    db = SessionLocal()
    pre_test = db.query(PrePostTest).filter_by(student_id=student_id, topic=topic, test_type='pre').first()
    post_test = db.query(PrePostTest).filter_by(student_id=student_id, topic=topic, test_type='post').first()
    db.close()
    
    if not pre_test or not post_test:
        return jsonify({"error": "No hay suficientes datos"}), 404
    
    gain = post_test.score - pre_test.score
    normalized_gain = gain / (100 - pre_test.score) if pre_test.score < 100 else 0
    
    return jsonify({
        "pre_score": pre_test.score,
        "post_score": post_test.score,
        "gain": gain,
        "normalized_gain": normalized_gain
    })

# ========== ENDPOINTS DE DOCENTES (TAREAS Y ACTIVIDADES) ==========

def _assignment_dict(a):
    """Convierte una fila Assignment en JSON (se llama antes de cerrar la sesión)."""
    return {
        "id": a.id,
        "tipo": a.tipo,
        "titulo": a.titulo,
        "descripcion": a.descripcion or "",
        "tema": a.tema or "",
        "level": a.level,
        "due_date": a.due_date,
        "content": a.content or {},
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }

@app.route('/teacher/assignments', methods=['GET'])
def list_assignments():
    """Lista las tareas y actividades. Con ?tipo=tarea o ?tipo=actividad filtra."""
    tipo = request.args.get('tipo')
    db = SessionLocal()
    query = db.query(Assignment)
    if tipo in ('tarea', 'actividad'):
        query = query.filter_by(tipo=tipo)
    items = query.order_by(Assignment.created_at.desc()).all()
    resultado = [_assignment_dict(a) for a in items]
    db.close()
    return jsonify(resultado)

@app.route('/teacher/assignments', methods=['POST'])
def create_assignment():
    """Crea una tarea o actividad con lo que haya armado el docente."""
    data = request.json or {}
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({"error": "El título es obligatorio"}), 400

    tipo = data.get('tipo', 'tarea')
    if tipo not in ('tarea', 'actividad'):
        tipo = 'tarea'

    db = SessionLocal()
    assignment = Assignment(
        tipo=tipo,
        titulo=titulo,
        descripcion=data.get('descripcion', ''),
        tema=data.get('tema', ''),
        level=data.get('level', 'basico'),
        due_date=data.get('due_date') or None,
        content=data.get('content', {}) or {}
    )
    db.add(assignment)
    db.commit()
    result = _assignment_dict(assignment)
    db.close()
    return jsonify({"success": True, "assignment": result}), 201

@app.route('/teacher/assignments/<int:assignment_id>', methods=['DELETE'])
def delete_assignment(assignment_id):
    db = SessionLocal()
    assignment = db.query(Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        db.close()
        return jsonify({"error": "Tarea o actividad no encontrada"}), 404
    db.delete(assignment)
    db.commit()
    db.close()
    return jsonify({"success": True})

@app.route('/teacher/assignments/generate', methods=['POST'])
def generate_assignment_content():
    """Genera con IA el contenido de una tarea/actividad antes de guardarla.

    No guarda nada: devuelve los ejercicios (y opcionalmente la explicación)
    para que el docente los revise y los confirme al guardar.
    """
    data = request.json or {}
    topic = (data.get('topic') or '').strip()
    level = data.get('student_level', 'basico')
    if not topic:
        return jsonify({"error": "Indica un tema para generar el contenido"}), 400

    try:
        quantity = int(data.get('quantity', 3))
    except (TypeError, ValueError):
        quantity = 3
    quantity = max(1, min(quantity, 10))

    from content_generator import generate_exercises_with_answers, generate_explanation

    exercises = generate_exercises_with_answers(topic, level, quantity)

    explicacion = ""
    fuentes = []
    if data.get('incluir_explicacion'):
        explicacion, fuentes = generate_explanation(topic, level, con_fuentes=True)

    return jsonify({
        "exercises": exercises,
        "explicacion": explicacion,
        "fuentes": fuentes,
        "topic": topic,
        "level": level
    })

# ========== ENDPOINTS DE REVISIÓN DE MATERIAL (RF10, RF12, RF13) ==========

def _material_review_dict(m):
    return {
        "id": m.id,
        "docente": m.docente or "",
        "tipo": m.tipo,
        "tema": m.tema or "",
        "level": m.level,
        "contenido_original": m.contenido_original or "",
        "contenido_final": m.contenido_final or "",
        "decision": m.decision,
        "segundos": m.segundos or 0.0,
        "fragmentos": m.fragmentos or [],
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }

@app.route('/teacher/material/generate', methods=['POST'])
def generate_material_for_review():
    """Genera material para que el docente lo revise (no lo guarda).

    Devuelve el contenido generado y los fragmentos del corpus que lo
    sustentan, para mostrarlos junto al material (RF12).
    """
    data = request.json or {}
    tema = (data.get('tema') or '').strip()
    tipo = data.get('tipo', 'explicacion')
    level = data.get('level', 'basico')
    if not tema:
        return jsonify({"error": "Indica un tema"}), 400
    if tipo not in ('explicacion', 'ejercicios'):
        tipo = 'explicacion'

    if tipo == 'explicacion':
        texto, fragmentos = generate_explanation(tema, level, con_fragmentos=True)
        contenido = {"texto": texto, "ejercicios": []}
    else:
        try:
            quantity = int(data.get('quantity', 3))
        except (TypeError, ValueError):
            quantity = 3
        quantity = max(1, min(quantity, 10))
        from content_generator import generate_exercises_with_answers
        pasajes = retrieve_pertinentes(tema, n_results=3)
        material = '\n\n---\n\n'.join(p["texto"] for p in pasajes) or None
        ejercicios = generate_exercises_with_answers(tema, level, quantity,
                                                     material=material)
        fragmentos = [{"fuente": p["fuente"], "texto": p["texto"]} for p in pasajes]
        contenido = {"texto": "", "ejercicios": ejercicios}

    return jsonify({
        "tipo": tipo,
        "tema": tema,
        "level": level,
        "contenido": contenido,
        "fragmentos": fragmentos
    })

@app.route('/teacher/material/decision', methods=['POST'])
def save_material_decision():
    """Registra la decisión del docente y el tiempo empleado (RF13)."""
    data = request.json or {}
    decision = data.get('decision', 'aceptado')
    if decision not in ('aceptado', 'editado', 'rechazado'):
        return jsonify({"error": "Decisión inválida"}), 400

    try:
        segundos = float(data.get('segundos', 0))
    except (TypeError, ValueError):
        segundos = 0.0
    segundos = max(0.0, segundos)

    contenido_original = data.get('contenido_original', '') or ''
    contenido_final = data.get('contenido_final')
    if contenido_final is None:
        contenido_final = contenido_original

    db = SessionLocal()
    review = MaterialReview(
        docente=(data.get('docente') or '')[:120],
        tipo=data.get('tipo', 'explicacion'),
        tema=data.get('tema', ''),
        level=data.get('level', 'basico'),
        contenido_original=contenido_original,
        contenido_final=contenido_final,
        decision=decision,
        segundos=segundos,
        fragmentos=data.get('fragmentos', []) or []
    )
    db.add(review)
    db.commit()
    result = _material_review_dict(review)
    db.close()
    return jsonify({"success": True, "review": result}), 201

@app.route('/teacher/materials', methods=['GET'])
def list_material_reviews():
    limite = request.args.get('limit', default=100, type=int)
    db = SessionLocal()
    items = (db.query(MaterialReview)
               .order_by(MaterialReview.created_at.desc())
               .limit(limite).all())
    resultado = [_material_review_dict(m) for m in items]
    db.close()
    return jsonify(resultado)

def _calcular_metricas(reviews):
    """Envuelve la lógica de docente_utils para no repetirla."""
    return calcular_metricas(reviews)

@app.route('/teacher/metrics', methods=['GET'])
def teacher_metrics():
    db = SessionLocal()
    reviews = db.query(MaterialReview).all()
    metricas = _calcular_metricas(reviews)
    db.close()
    return jsonify(metricas)

# ========== ENDPOINTS DE CORPUS PROPIO DEL DOCENTE (RF11) ==========

def _nombre_corpus_seguro(nombre):
    """Compatibilidad: delega en docente_utils."""
    return nombre_corpus_seguro(nombre)

@app.route('/teacher/corpus', methods=['GET'])
def get_corpus():
    return jsonify(info_corpus())

@app.route('/teacher/corpus', methods=['POST'])
def upload_corpus():
    """Guarda un documento de texto del docente y reindexa (RF11)."""
    data = request.json or {}
    nombre = _nombre_corpus_seguro(data.get('nombre'))
    contenido = data.get('contenido') or ''
    if not nombre:
        return jsonify({"error": "Nombre de archivo inválido"}), 400
    if not contenido.strip():
        return jsonify({"error": "El documento está vacío"}), 400

    os.makedirs(KNOWLEDGE_DOCENTE, exist_ok=True)
    ruta = os.path.join(KNOWLEDGE_DOCENTE, nombre)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)

    fragmentos = recargar_knowledge_base()
    return jsonify({"success": True, "nombre": nombre,
                    "fragmentos_indexados": fragmentos}), 201

@app.route('/teacher/corpus/<nombre>', methods=['DELETE'])
def delete_corpus(nombre):
    """Borra un documento del docente (solo de su carpeta) y reindexa."""
    nombre = _nombre_corpus_seguro(nombre)
    if not nombre:
        return jsonify({"error": "Nombre de archivo inválido"}), 400
    ruta = os.path.join(KNOWLEDGE_DOCENTE, nombre)
    if not os.path.exists(ruta):
        return jsonify({"error": "Documento no encontrado"}), 404
    os.remove(ruta)
    recargar_knowledge_base()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)