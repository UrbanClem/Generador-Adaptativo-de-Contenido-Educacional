from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from database import SessionLocal, Student
from rag_engine import load_knowledge_base
from content_generator import generate_explanation, generate_exercises, give_feedback


# --- Startup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_knowledge_base()
    yield


app = FastAPI(title="Sistema Educativo Adaptativo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Dependencia de base de datos ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Modelos de request ---

class StudentCreate(BaseModel):
    name: str
    level: str
    diagnostic_results: dict


class DiagnosticAnswers(BaseModel):
    answers: List[str]


class ExplainRequest(BaseModel):
    topic: str
    student_level: str


class ExerciseRequest(BaseModel):
    topic: str
    student_level: str
    quantity: int = 3


class FeedbackRequest(BaseModel):
    student_answer: str
    correct_answer: str
    student_level: str


# --- Preguntas diagnósticas ---

DIAGNOSTIC_QUESTIONS = [
    {"id": 1, "pregunta": "x + 3 = 7, ¿cuánto vale x?",               "respuesta": "4",  "nivel": "basico"},
    {"id": 2, "pregunta": "2x - 5 = 9, ¿cuánto vale x?",              "respuesta": "7",  "nivel": "intermedio"},
    {"id": 3, "pregunta": "3(x - 4) = 2x + 1, ¿cuánto vale x?",       "respuesta": "13", "nivel": "avanzado"},
    {"id": 4, "pregunta": "Resuelve: 5x + 2 = 3x + 10",               "respuesta": "4",  "nivel": "intermedio"},
    {"id": 5, "pregunta": "¿Cuál es la solución de 2(3x - 1) = 4x + 6?", "respuesta": "4", "nivel": "avanzado"},
]


# --- Endpoints de estudiantes ---

@app.get("/students/{name}")
def get_student(name: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.name == name).first()
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return {
        "name": student.name,
        "level": student.level,
        "diagnostic_results": student.diagnostic_results,
    }


@app.post("/students", status_code=201)
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="El estudiante ya existe")
    student = Student(
        name=data.name,
        level=data.level,
        diagnostic_results=data.diagnostic_results,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"name": student.name, "level": student.level}


# --- Endpoints de diagnóstico ---

@app.get("/diagnostic/questions")
def get_diagnostic_questions():
    return [{"id": q["id"], "pregunta": q["pregunta"]} for q in DIAGNOSTIC_QUESTIONS]


@app.post("/diagnostic/evaluate")
def evaluate_diagnostic(data: DiagnosticAnswers):
    score = 0
    level_count = {"basico": 0, "intermedio": 0, "avanzado": 0}

    for i, answer in enumerate(data.answers):
        if i < len(DIAGNOSTIC_QUESTIONS):
            q = DIAGNOSTIC_QUESTIONS[i]
            if answer.strip() == q["respuesta"]:
                score += 1
                level_count[q["nivel"]] += 1

    if level_count["avanzado"] >= 2:
        level = "avanzado"
    elif level_count["intermedio"] >= 1:
        level = "intermedio"
    else:
        level = "basico"

    return {"level": level, "score": score, "details": level_count}


# --- Endpoints de contenido ---

@app.post("/explain")
def explain(request: ExplainRequest):
    result = generate_explanation(request.topic, request.student_level)
    return {"content": result}


@app.post("/exercises")
def exercises(request: ExerciseRequest):
    result = generate_exercises(request.topic, request.student_level, request.quantity)
    return {"content": result}


@app.post("/feedback")
def feedback(request: FeedbackRequest):
    result = give_feedback(request.student_answer, request.correct_answer, request.student_level)
    return {"content": result}


# --- Servir frontend (debe ir al final) ---

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
