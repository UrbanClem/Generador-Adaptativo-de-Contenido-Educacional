from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/rag_education")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    level = Column(String, nullable=False)
    level_score = Column(Float, default=0.0)
    common_errors = Column(JSON, default=list)
    diagnostic_results = Column(JSON, default=dict)
    interaction_history = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExerciseResult(Base):
    __tablename__ = "exercise_results"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    student_answer = Column(String)
    correct_answer = Column(String)
    is_correct = Column(Boolean, default=False)
    attempts = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)

class PrePostTest(Base):
    __tablename__ = "pre_post_tests"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    test_type = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    answers = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)

class CognitiveProfile(Base):
    __tablename__ = "cognitive_profiles"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False, unique=True)
    attribute_mastery = Column(JSON, default=dict)
    current_level = Column(String, default="basico")
    zpd_attributes = Column(JSON, default=list)
    response_history = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    inspector = inspect(engine)
    tables_to_create = [
        ("students", Student),
        ("exercise_results", ExerciseResult),
        ("pre_post_tests", PrePostTest),
        ("cognitive_profiles", CognitiveProfile)
    ]
    for table_name, model in tables_to_create:
        if not inspector.has_table(table_name):
            model.__table__.create(engine)
            print(f"✅ Tabla '{table_name}' creada")
        else:
            print(f"ℹ️ Tabla '{table_name}' ya existe")

init_db()