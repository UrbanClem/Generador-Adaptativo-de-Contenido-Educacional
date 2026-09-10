from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from sqlalchemy import text
from datetime import datetime
from config import DATABASE_URL

# SQLite necesita check_same_thread=False porque Flask atiende cada peticion
# en un hilo distinto; con PostgreSQL el parametro no aplica.
_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_args)
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

MODELOS = [
    ("students", Student),
    ("exercise_results", ExerciseResult),
    ("pre_post_tests", PrePostTest),
    ("cognitive_profiles", CognitiveProfile),
]


def _agregar_columnas_faltantes(inspector, table_name, model):
    """Agrega a una tabla ya existente las columnas nuevas del modelo.

    Hace falta porque la base de SQLite viene de una version anterior del
    prototipo, cuando la tabla students todavia no tenia level_score ni
    interaction_history.
    """
    existentes = {c["name"] for c in inspector.get_columns(table_name)}
    for columna in model.__table__.columns:
        if columna.name in existentes:
            continue
        tipo = columna.type.compile(engine.dialect)
        with engine.begin() as conn:
            conn.execute(text(
                'ALTER TABLE %s ADD COLUMN %s %s' % (table_name, columna.name, tipo)))
            # las filas viejas quedan en NULL; se rellenan con el valor por defecto
            defecto = getattr(columna.default, "arg", None)
            if defecto is not None and not callable(defecto):
                conn.execute(
                    text('UPDATE %s SET %s = :v WHERE %s IS NULL'
                         % (table_name, columna.name, columna.name)),
                    {"v": defecto})
        print("Columna '%s.%s' agregada" % (table_name, columna.name))


def init_db():
    inspector = inspect(engine)
    for table_name, model in MODELOS:
        if not inspector.has_table(table_name):
            model.__table__.create(engine)
            print("Tabla '%s' creada" % table_name)
        else:
            _agregar_columnas_faltantes(inspector, table_name, model)

init_db()