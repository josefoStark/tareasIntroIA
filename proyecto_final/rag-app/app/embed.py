import math
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError


load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"


class MissingAPIKeyError(RuntimeError):
    """GOOGLE_API_KEY no está configurada."""


_client = None


def api_key_configured() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


def get_client() -> genai.Client:
    """
    Crea el cliente de Google AI la primera vez que se necesita.
    Así la API arranca aunque falte la clave y puede responder
    con un error claro en lugar de fallar al importar el módulo.
    """
    global _client

    if _client is None:
        key = os.getenv("GOOGLE_API_KEY", "").strip()

        if not key:
            raise MissingAPIKeyError(
                "Falta GOOGLE_API_KEY. Defínela en el archivo .env "
                "y reinicia la API."
            )

        _client = genai.Client(api_key=key)

    return _client


def _embed_with_retry(contents, max_retries=None, label=""):
    """
    Llama a la API de embeddings.

    - Rate limit (HTTP 429): espera con backoff progresivo y reintenta.
      Si max_retries es None, reintenta indefinidamente (ingesta);
      si es un número, se rinde tras esos reintentos (consultas).
    - Cualquier otro error se propaga sin reintentar.
    """
    attempts = 0

    while True:
        try:
            response = get_client().models.embed_content(
                model=EMBEDDING_MODEL,
                contents=contents
            )

            return [embedding.values for embedding in response.embeddings]

        except APIError as e:
            if getattr(e, "code", None) != 429:
                print(f"❌ Error de API ({label}): {e}")
                raise

            attempts += 1

            if max_retries is not None and attempts > max_retries:
                raise

            # Backoff: 10, 20, 30, 40, 50, 60, 60, 60...
            wait_time = min(attempts * 10, 60)

            print(
                f"⚠️ Rate Limit ({label}). "
                f"Esperando {wait_time}s... (Reintento {attempts})"
            )

            time.sleep(wait_time)


def embed_text(text: str) -> list[float]:
    """Embedding de un solo texto (p. ej. la pregunta del usuario)."""
    return _embed_with_retry(text, max_retries=2, label="consulta")[0]


def embed_texts(
    texts: list[str],
    batch_size: int = 16
) -> list[list[float]]:
    """
    Genera embeddings en lotes pequeños.

    Los Rate Limits (429) se esperan y se reintentan sin límite, de modo
    que la ingesta continúa sola cuando la API vuelve a aceptar
    solicitudes. Otros errores de la API detienen el proceso.
    """
    embeddings = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        embeddings.extend(
            _embed_with_retry(batch, label=f"lote {start}")
        )

        # Pausa pequeña entre lotes para reducir la presión sobre la API.
        time.sleep(0.5)

    return embeddings


def cosine_similarity(
    a: list[float],
    b: list[float]
) -> float:
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)
