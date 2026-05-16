from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
import os

# Cargar modelo de embeddings open-source
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Inicializar ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
)

def load_knowledge_base(folder_path="./knowledge"):
    """Carga documentos .txt como base de conocimiento"""
    if collection.count() > 0:
        print("Base de conocimiento ya cargada")
        return
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                content = f.read()
                collection.add(
                    documents=[content],
                    metadatas=[{"source": filename}],
                    ids=[filename]
                )
    print(f"Cargados {collection.count()} documentos")

def retrieve_context(query, n_results=3):
    available = collection.count()
    if available == 0:
        return ""
    results = collection.query(query_texts=[query], n_results=min(n_results, available))
    if results['documents']:
        return "\n".join(results['documents'][0])
    return ""

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
        response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']