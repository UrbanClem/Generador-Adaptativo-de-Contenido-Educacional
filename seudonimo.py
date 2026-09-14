# -*- coding: utf-8 -*-
"""Seudonimizacion de los participantes.

El apartado 3.6.2 del documento de tesis compromete que los datos se almacenen
de forma seudonimizada. Hasta la primera iteracion la base guardaba el nombre
completo tal como lo escribia el estudiante; este modulo lo sustituye:

- El estudiante sigue escribiendo su nombre para entrar, porque es lo que
  recuerda, pero **el nombre nunca se guarda**.
- La base guarda un codigo correlativo ("E01", "E02", ...) y un hash del
  nombre, que sirve unicamente para reconocer a quien vuelve.
- El hash lleva sal, de modo que no se pueda revertir por diccionario de
  nombres comunes. La sal se lee de la variable de entorno SEUDONIMO_SALT.

Quien abra la base de datos ve "E01" y una cadena hexadecimal: puede seguir el
avance de un participante a lo largo de la sesion, que es lo que la
investigacion necesita, sin saber de quien se trata.
"""
import hashlib
import os
import re
import unicodedata

SALT = os.getenv("SEUDONIMO_SALT", "tesis-generador-adaptativo")

PREFIJO = "E"


def normalizar(nombre):
    """Deja el nombre comparable: sin acentos, sin dobles espacios, en minusculas.

    Asi "José  Pérez", "jose perez" y "JOSE PEREZ" son la misma persona y no
    se crean tres participantes distintos.
    """
    texto = unicodedata.normalize("NFKD", str(nombre or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto).strip().lower()
    return texto


def hash_nombre(nombre):
    """Huella del nombre, con sal. Es lo unico que se guarda para reconocerlo."""
    base = (SALT + "|" + normalizar(nombre)).encode("utf-8")
    return hashlib.sha256(base).hexdigest()


def siguiente_codigo(codigos_existentes):
    """Devuelve el siguiente codigo libre a partir de los ya asignados."""
    usados = set()
    for c in codigos_existentes:
        m = re.fullmatch(PREFIJO + r"(\d+)", str(c or ""))
        if m:
            usados.add(int(m.group(1)))
    n = 1
    while n in usados:
        n += 1
    return "%s%02d" % (PREFIJO, n)


def es_seudonimo(valor):
    """True si la cadena ya es un codigo y no un nombre."""
    return bool(re.fullmatch(PREFIJO + r"\d+", str(valor or "")))
