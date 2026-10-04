import chromadb


CHROMA_PATH = "./chroma"
COLLECTION_NAME = "rag_documents"


client = chromadb.PersistentClient(path=CHROMA_PATH)

# Métrica coseno: Chroma devuelve distancia = 1 - similitud coseno.
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

# Si la colección ya existía con la métrica por defecto (L2), los scores
# no serían similitudes. Se avisa en lugar de dar resultados engañosos.
if (collection.metadata or {}).get("hnsw:space") != "cosine":
    raise RuntimeError(
        "La colección de Chroma existente no usa distancia coseno. "
        "Detén la API, borra la carpeta ./chroma y vuelve a ingerir."
    )


def add_chunks(
    ids,
    texts,
    embeddings,
    metadatas
):
    # upsert: re-ingerir el mismo archivo actualiza en lugar de duplicar
    # o ignorar los chunks con IDs ya existentes.
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )


def query(
    embedding,
    top_k=3
):
    total = collection.count()

    if total == 0:
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    return collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, total),
        include=["documents", "metadatas", "distances"]
    )


def count_chunks():
    return collection.count()
