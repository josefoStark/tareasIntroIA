import os
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from google.genai.errors import APIError
from pydantic import BaseModel, Field

from app.chunk import chunk_text
from app.csv_loader import load_movies_csv
from app.embed import (
    MissingAPIKeyError,
    api_key_configured,
    embed_text,
    embed_texts,
)
from app.generate import ABSTENTION_MESSAGE, generate_answer
from app.store import add_chunks, count_chunks, query


# Similitud coseno mínima del mejor chunk para intentar responder.
# Si ningún chunk la alcanza, el sistema se abstiene sin llamar a Gemini.
# Calíbralo con tus preguntas de prueba (ver el score en la UI).
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.60"))

BATCH_SIZE = 250


app = FastAPI(
    title="RAG API",
    description="API para el sistema RAG de Películas",
    version="1.0.0"
)


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=10)


def google_error(e: Exception) -> HTTPException:
    """Traduce errores de Google AI a respuestas HTTP claras."""
    if isinstance(e, MissingAPIKeyError):
        return HTTPException(status_code=503, detail=str(e))

    if getattr(e, "code", None) == 429:
        return HTTPException(
            status_code=429,
            detail=(
                "Se alcanzó el límite de cuota de Google AI. "
                "Espera un momento e inténtalo de nuevo."
            )
        )

    return HTTPException(
        status_code=502,
        detail=f"Error al comunicarse con Google AI: {e}"
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "chunks": count_chunks(),
        "google_api_key": api_key_configured()
    }


def index_batch(ids, texts, metadatas):
    embeddings = embed_texts(texts, batch_size=16)

    add_chunks(
        ids=ids,
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(texts)


@app.post("/ingest")
def ingest(file: UploadFile = File(...)):
    filename = os.path.basename(file.filename or "")

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un CSV."
        )

    if not api_key_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Falta GOOGLE_API_KEY. Defínela en el archivo .env "
                "y reinicia la API."
            )
        )

    os.makedirs("data", exist_ok=True)
    temp_path = f"data/{filename}"

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        movies = load_movies_csv(temp_path)
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="El CSV debe estar codificado en UTF-8."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not movies:
        raise HTTPException(
            status_code=400,
            detail="El CSV no contiene registros."
        )

    current_ids = []
    current_texts = []
    current_metadatas = []
    total_processed_chunks = 0

    print(f"🚀 Iniciando ingesta de {len(movies)} películas...")

    try:
        for movie_idx, movie in enumerate(movies):
            chunks = chunk_text(
                movie["text"],
                chunk_size=300,
                overlap=50
            )

            for chunk_index, chunk in enumerate(chunks):
                current_texts.append(chunk)

                metadata = movie["metadata"].copy()
                metadata["chunk"] = chunk_index
                current_metadatas.append(metadata)

                current_ids.append(
                    f"{filename}_{movie['metadata']['row']}_{chunk_index}"
                )

            if len(current_texts) >= BATCH_SIZE:
                total_processed_chunks += index_batch(
                    current_ids, current_texts, current_metadatas
                )

                print(
                    f"✅ Ingeridos {total_processed_chunks} chunks... "
                    f"({movie_idx + 1}/{len(movies)} películas)"
                )

                current_ids.clear()
                current_texts.clear()
                current_metadatas.clear()

        if current_texts:
            total_processed_chunks += index_batch(
                current_ids, current_texts, current_metadatas
            )

    except (MissingAPIKeyError, APIError) as e:
        error = google_error(e)
        error.detail = (
            f"{error.detail} (chunks indexados antes del fallo: "
            f"{total_processed_chunks})"
        )
        raise error

    print(
        f"🎉 Ingesta finalizada. "
        f"Total chunks en este archivo: {total_processed_chunks}"
    )

    return {
        "filename": filename,
        "movies": len(movies),
        "documents": len(movies),
        "chunks": total_processed_chunks,
        "total_chunks": count_chunks()
    }


@app.post("/query")
def query_documents(request: QueryRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía."
        )

    if count_chunks() == 0:
        raise HTTPException(
            status_code=409,
            detail="El índice está vacío. Ingiere un CSV antes de preguntar."
        )

    try:
        embedding = embed_text(question)
    except (MissingAPIKeyError, APIError) as e:
        raise google_error(e)

    results = query(
        embedding=embedding,
        top_k=request.top_k
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    citations = []

    for index, (document, metadata, distance) in enumerate(
        zip(documents, metadatas, distances),
        start=1
    ):
        citation = {
            "id": index,
            "source": metadata.get("source", "desconocido"),
            "text": document,
            # Colección coseno: distancia = 1 - similitud.
            "score": round(1 - distance, 4)
        }

        for key in ("title", "release_year", "row", "chunk"):
            if key in metadata:
                citation[key] = metadata[key]

        citations.append(citation)

    best_score = max((c["score"] for c in citations), default=0.0)

    # Primera capa de abstención: ningún chunk se parece lo suficiente
    # a la pregunta. No se llama a Gemini.
    if not citations or best_score < MIN_SCORE:
        return {
            "question": question,
            "answer": ABSTENTION_MESSAGE,
            "citations": citations,
            "abstained": True
        }

    # Segunda capa: Gemini también puede abstenerse si el contexto
    # no cubre la pregunta.
    try:
        answer, abstained = generate_answer(
            question=question,
            documents=documents,
            metadatas=metadatas
        )
    except (MissingAPIKeyError, APIError) as e:
        raise google_error(e)

    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "abstained": abstained
    }
