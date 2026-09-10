from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
import os
from config import OLLAMA_MODEL, KNOWLEDGE_DIR, CHROMA_DIR

# Cargar modelo de embeddings open-source
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Tamano aproximado de cada fragmento, en caracteres. Los documentos completos
# (4 KB cada uno) no caben en el prompt sin desplazar al resto de la consigna.
TAM_FRAGMENTO = 700

# Inicializar ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)


def _crear_coleccion():
    return chroma_client.get_or_create_collection(
        name="knowledge_base",
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
    )


collection = _crear_coleccion()


def trocear(texto, titulo):
    """Parte un documento en fragmentos de ~TAM_FRAGMENTO caracteres.

    Se corta en los renglones en blanco para no partir un ejemplo a la mitad,
    y cada fragmento lleva el titulo del documento al inicio para que la
    busqueda por similitud tenga de que agarrarse.
    """
    bloques = [b.strip() for b in texto.split("\n\n") if b.strip()]
    fragmentos = []
    actual = ""
    for bloque in bloques:
        if actual and len(actual) + len(bloque) > TAM_FRAGMENTO:
            fragmentos.append(actual)
            actual = bloque
        else:
            actual = f"{actual}\n\n{bloque}" if actual else bloque
    if actual:
        fragmentos.append(actual)
    return [f"{titulo}\n\n{f}" if not f.startswith(titulo) else f for f in fragmentos]


def _troceada():
    """True si lo que ya esta en ChromaDB se cargo troceado (ids con '#')."""
    datos = collection.get(limit=1)
    ids = datos.get("ids") or []
    return bool(ids) and "#" in ids[0]


def load_knowledge_base(folder_path=KNOWLEDGE_DIR, recargar=False):
    """Carga documentos .txt como base de conocimiento, troceados"""
    global collection

    if collection.count() > 0 and _troceada() and not recargar:
        print(f"Base de conocimiento ya cargada ({collection.count()} fragmentos)")
        return

    # La coleccion vieja guardaba un documento entero por id: se rehace
    chroma_client.delete_collection(name="knowledge_base")
    collection = _crear_coleccion()

    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                content = f.read()
            titulo = content.strip().split("\n")[0].strip()
            fragmentos = trocear(content, titulo)
            collection.add(
                documents=fragmentos,
                metadatas=[{"source": filename, "fragmento": i} for i in range(len(fragmentos))],
                ids=[f"{filename}#{i}" for i in range(len(fragmentos))]
            )
    print(f"Cargados {collection.count()} fragmentos")


def retrieve_passages(query, n_results=3):
    """Recupera los fragmentos mas parecidos a la consulta.

    Devuelve una lista de diccionarios con el texto y el archivo del que sale,
    para poder citar el material que se uso.
    """
    available = collection.count()
    if available == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(n_results, available))
    documentos = results.get("documents") or []
    if not documentos or not documentos[0]:
        return []
    metadatos = (results.get("metadatas") or [[]])[0]
    pasajes = []
    for i, texto in enumerate(documentos[0]):
        meta = metadatos[i] if i < len(metadatos) else {}
        pasajes.append({"texto": texto, "fuente": meta.get("source", "")})
    return pasajes


def retrieve_context(query, n_results=3):
    """Igual que retrieve_passages pero devuelve el texto ya unido"""
    return "\n\n".join(p["texto"] for p in retrieve_passages(query, n_results))


PLANTILLA_JUEZ = """Responde unicamente con SI o NO.

MATERIAL:
{material}

Pregunta: el MATERIAL de arriba sirve para explicarle a un estudiante el tema "{tema}"?
Responde SI solo si el MATERIAL trata ese mismo tema. Responde NO si trata un tema distinto.
Respuesta (SI o NO):"""


def pertinente(tema, material):
    """True si el fragmento recuperado trata el tema que se pregunto.

    La distancia del vector no alcanza para decidirlo: el modelo de embeddings
    esta entrenado en ingles y en espanol devuelve valores que se enciman
    ("despejar la incognita", que si esta en el material, queda mas lejos que
    "numeros complejos", que no esta). Se le pregunta al propio modelo, que
    solo tiene que contestar SI o NO y tarda menos de un segundo.
    """
    import ollama
    try:
        respuesta = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": PLANTILLA_JUEZ.format(material=material, tema=tema)}],
            options={"temperature": 0, "num_predict": 3},
        )
    except Exception as e:
        print(f"No se pudo juzgar la pertinencia del material: {e}")
        return True  # ante la duda se conserva el fragmento
    return respuesta["message"]["content"].strip().upper().startswith("SI")


def retrieve_pertinentes(tema, n_results=3):
    """Recupera fragmentos y descarta los que no tratan el tema.

    Devuelve solo el material que el juez aprueba, para que una consulta de un
    tema que no esta en el corpus llegue vacia en vez de arrastrar el fragmento
    mas cercano.
    """
    return [p for p in retrieve_passages(tema, n_results) if pertinente(tema, p["texto"])]


def temas_disponibles():
    """Titulos de los documentos del corpus, para decir que si esta cubierto."""
    titulos = []
    if not os.path.isdir(KNOWLEDGE_DIR):
        return titulos
    for filename in sorted(os.listdir(KNOWLEDGE_DIR)):
        if not filename.endswith(".txt"):
            continue
        with open(os.path.join(KNOWLEDGE_DIR, filename), "r", encoding="utf-8") as f:
            titulo = f.readline().strip()
        # Los documentos viejos no traen titulo, arrancan con el texto corrido
        if not titulo or titulo != titulo.upper():
            continue
        # El formulario y los errores comunes son material de apoyo del tutor,
        # no temas que el estudiante pida
        if titulo.rstrip().endswith("IA"):
            continue
        if titulo not in titulos:
            titulos.append(titulo)
    return titulos


def generate_with_llm(prompt, use_openai=False):
    if use_openai:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    else:
        import ollama
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
