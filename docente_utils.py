# -*- coding: utf-8 -*-
"""Utilidades del panel docente, sin dependencias de Flask ni de la base.

Se separan aquí para que las pruebas puedan verificar la lógica sin importar
`main_api` (que al importarse carga la base de conocimiento y el modelo de
embeddings). Es la misma separación por responsabilidad que pide RNF07.
"""
import os


def _valor(registro, nombre, defecto=None):
    """Lee un campo de un objeto (fila de SQLAlchemy) o de un diccionario."""
    if isinstance(registro, dict):
        return registro.get(nombre, defecto)
    return getattr(registro, nombre, defecto)


def nombre_corpus_seguro(nombre):
    """Deja solo el nombre base, sin rutas, y garantiza la extensión .txt.

    Evita que un nombre con separadores o con `..` escriba fuera de la carpeta
    del corpus del docente.
    """
    nombre = os.path.basename((nombre or '').strip())
    nombre = nombre.replace('\\', '').replace('/', '')
    # Tras quitar separadores, un nombre que era ".." o "." queda inutilizable
    if not nombre or nombre in ('.', '..'):
        return None
    if not nombre.lower().endswith('.txt'):
        nombre += '.txt'
    return nombre


def calcular_metricas(reviews):
    """Dos medidas objetivas del apartado 3.6.1 a partir de las decisiones.

    Devuelve la proporción de material aceptado sin edición y los tiempos
    (global medio y medio de los materiales que se editaron).
    """
    total = len(reviews)
    aceptados = sum(1 for r in reviews if _valor(r, 'decision') == 'aceptado')
    editados = sum(1 for r in reviews if _valor(r, 'decision') == 'editado')
    rechazados = sum(1 for r in reviews if _valor(r, 'decision') == 'rechazado')

    tiempos = [(_valor(r, 'segundos') or 0) for r in reviews]
    tiempos = [t for t in tiempos if t]
    tiempos_edicion = [(_valor(r, 'segundos') or 0) for r in reviews
                       if _valor(r, 'decision') == 'editado']
    tiempos_edicion = [t for t in tiempos_edicion if t]

    return {
        "total": total,
        "aceptados": aceptados,
        "editados": editados,
        "rechazados": rechazados,
        "aceptacion_sin_edicion": (aceptados / total) if total else 0.0,
        "tiempo_medio": (sum(tiempos) / len(tiempos)) if tiempos else 0.0,
        "tiempo_medio_edicion": (sum(tiempos_edicion) / len(tiempos_edicion)) if tiempos_edicion else 0.0,
    }
