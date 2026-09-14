# -*- coding: utf-8 -*-
"""Pruebas de la seudonimizacion (apartado 3.6.2 del documento de tesis).

Lo que tienen que sostener: que el nombre del participante no quede guardado
en ningun lado, y que aun asi se le pueda reconocer cuando vuelve.
"""
from seudonimo import (normalizar, hash_nombre, siguiente_codigo,
                       es_seudonimo, SALT)


def test_el_mismo_nombre_escrito_distinto_es_la_misma_persona():
    """Acentos, mayusculas y espacios de mas no crean participantes nuevos."""
    formas = ["Jose Perez", "José Pérez", "  jose   perez ", "JOSE PEREZ"]
    huellas = {hash_nombre(f) for f in formas}
    assert len(huellas) == 1


def test_personas_distintas_tienen_huellas_distintas():
    assert hash_nombre("Jose Perez") != hash_nombre("Jose Peres")
    assert hash_nombre("Ana Lopez") != hash_nombre("Ana Lopez Ruiz")


def test_la_huella_no_contiene_el_nombre():
    """Ni en claro ni por partes: es lo que se guarda en la base."""
    huella = hash_nombre("Antonio Pacheco")
    for trozo in ["antonio", "pacheco", "Antonio", "Pacheco"]:
        assert trozo not in huella
    assert len(huella) == 64
    assert all(c in "0123456789abcdef" for c in huella)


def test_la_huella_lleva_sal():
    """Sin sal, un diccionario de nombres comunes la revierte."""
    import hashlib
    desnuda = hashlib.sha256("jose perez".encode("utf-8")).hexdigest()
    assert hash_nombre("Jose Perez") != desnuda
    assert SALT


def test_los_codigos_son_correlativos_y_no_se_repiten():
    assert siguiente_codigo([]) == "E01"
    assert siguiente_codigo(["E01"]) == "E02"
    assert siguiente_codigo(["E01", "E02", "E03"]) == "E04"


def test_reutiliza_un_codigo_liberado():
    assert siguiente_codigo(["E01", "E03"]) == "E02"


def test_reconoce_lo_que_ya_es_seudonimo():
    assert es_seudonimo("E01")
    assert es_seudonimo("E12")
    assert not es_seudonimo("Antonio Pacheco")
    assert not es_seudonimo("")


def test_normalizar_no_se_rompe_con_entradas_raras():
    assert normalizar(None) == ""
    assert normalizar("") == ""
    assert normalizar("   ") == ""


# ------------------------------------------------- de punta a punta, en la BD

def test_la_base_de_datos_no_guarda_el_nombre():
    """La prueba que sostiene la afirmacion del apartado 3.6.2."""
    from database import SessionLocal, Student

    nombre = "Antonio Pacheco"
    db = SessionLocal()
    db.add(Student(name=siguiente_codigo(c for (c,) in db.query(Student.name).all()),
                   name_hash=hash_nombre(nombre),
                   level="intermedio"))
    db.commit()

    # ningun registro contiene el nombre, ni entero ni por apellido
    for alumno in db.query(Student).all():
        assert nombre not in (alumno.name or "")
        assert "Pacheco" not in (alumno.name or "")
        assert es_seudonimo(alumno.name)

    # y aun asi se le encuentra cuando vuelve a escribir su nombre
    vuelve = db.query(Student).filter_by(name_hash=hash_nombre("  antonio   PACHECO ")).first()
    assert vuelve is not None
    assert vuelve.level == "intermedio"
    db.close()
