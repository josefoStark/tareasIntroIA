from app.embed import get_client

GENERATION_MODEL = "gemini-3.8-flash"

ABSTENTION_MESSAGE = (
    "No hay información suficiente en los documentos para responder "
    "esta pregunta."
)


def _is_abstention(answer: str) -> bool:
    """
    Detecta si el modelo se abstuvo, sin exigir coincidencia exacta
    de mayúsculas o de texto adicional alrededor.
    """
    normalized = answer.strip().lower()

    return (
        not normalized
        or ABSTENTION_MESSAGE.lower() in normalized
        or normalized.startswith("no hay información suficiente")
    )


def generate_answer(question: str, documents, metadatas):
    context_parts = []

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1
    ):
        source = metadata.get("source", "desconocido")

        context_parts.append(
            f"[{i}]\n"
            f"Fuente: {source}\n"
            f"{document}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
Eres un asistente de preguntas y respuestas basado en recuperación
de información.

Responde la pregunta utilizando ÚNICAMENTE la información del contexto.
Responde siempre en español.

REGLAS:

1. No utilices conocimientos externos al contexto.
2. Cada afirmación importante debe estar respaldada por una cita
   [n] correspondiente a la fuente utilizada.
3. Las citas deben tener el formato [1], [2], [3], etc.
4. Si el contexto no contiene información suficiente para responder,
   responde exactamente:
   "{ABSTENTION_MESSAGE}"
5. No inventes fuentes, citas ni información.

Pregunta:
{question}

Contexto:
{context}
"""

    response = get_client().models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    answer = (response.text or "").strip()
    abstained = _is_abstention(answer)

    if abstained:
        # Mensaje limpio y consistente, sin texto de relleno del modelo.
        answer = ABSTENTION_MESSAGE

    return answer, abstained
