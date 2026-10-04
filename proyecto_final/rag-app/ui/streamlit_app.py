import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

# La API devuelve en "score" la similitud coseno (mayor = más parecido).
SCORE_LABEL = "Similitud"

st.set_page_config(
    page_title="RAG Movie Explorer",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 RAG Movie Explorer")
st.caption(
    "Consulta información de películas con un sistema RAG "
    "(Streamlit → FastAPI → ChromaDB + Google AI)"
)


# ---------- Utilidades ----------

def error_detail(response: requests.Response) -> str:
    """Extrae el mensaje de error que devolvió la API (detail / error)."""
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("error")
            if detail:
                return str(detail)
    except ValueError:
        pass
    return response.text[:500]


def get_health():
    """Devuelve (datos_health, mensaje_error). Uno de los dos es None."""
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if res.status_code == 200:
            return res.json(), None
        return None, f"La API respondió {res.status_code}: {error_detail(res)}"
    except requests.exceptions.ConnectionError:
        return None, (
            f"No se pudo conectar con la API en {API_BASE_URL}. "
            "¿Está corriendo uvicorn?"
        )
    except requests.exceptions.RequestException as e:
        return None, f"Error al consultar /health: {e}"


# ---------- Barra lateral: estado e ingesta ----------

health, health_error = get_health()

with st.sidebar:
    st.header("⚙️ Estado de la API")

    if health_error:
        st.error(health_error)
    else:
        st.success(f"API online · chunks indexados: {health.get('chunks', 0)}")

        if not health.get("google_api_key", True):
            st.error(
                "La API no tiene GOOGLE_API_KEY configurada. "
                "Defínela en el archivo .env y reinicia la API."
            )

    st.button("Actualizar estado")

    st.divider()

    st.subheader("📁 Ingesta de datos (CSV)")
    uploaded_file = st.file_uploader(
        "Cargar dataset de películas (.csv)", type=["csv"]
    )

    if uploaded_file is not None and st.button("Procesar e ingerir dataset"):
        with st.spinner(
            "Enviando CSV a la API, generando embeddings e indexando en ChromaDB "
            "(puede tardar varios minutos)..."
        ):
            try:
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "text/csv",
                    )
                }
                # (timeout de conexión, timeout de lectura): la ingesta es larga
                response = requests.post(
                    f"{API_BASE_URL}/ingest", files=files, timeout=(10, 3600)
                )

                if response.status_code != 200:
                    st.error(
                        f"Error en la ingesta ({response.status_code}): "
                        f"{error_detail(response)}"
                    )
                else:
                    data = response.json()
                    # Por seguridad, por si alguna respuesta 200 trae {"error": ...}
                    if "error" in data:
                        st.error(data["error"])
                    else:
                        movies = data.get("movies", data.get("documents", "N/A"))
                        # Se guarda el mensaje y se recarga la página para que
                        # el estado de la API (chunks) y el formulario de
                        # preguntas se actualicen sin pulsar nada más.
                        st.session_state["ingest_result"] = (
                            f"¡Ingesta exitosa! Películas: {movies} · "
                            f"Chunks de este archivo: {data.get('chunks', 'N/A')} · "
                            f"Total en el índice: {data.get('total_chunks', 'N/A')}"
                        )
                        st.rerun()
            except requests.exceptions.ConnectionError:
                st.error("Se perdió la conexión con la API durante la ingesta.")
            except requests.exceptions.RequestException as e:
                st.error(f"Error durante la ingesta: {e}")

    ingest_result = st.session_state.pop("ingest_result", None)
    if ingest_result:
        st.success(ingest_result)


# ---------- Estados vacíos / error del panel principal ----------

if health_error:
    st.error("La API no está disponible, no se pueden hacer consultas.")
    st.stop()

if health.get("chunks", 0) == 0:
    st.info(
        "El índice está vacío. Carga un CSV desde la barra lateral "
        "e ingiérelo antes de preguntar."
    )
    st.stop()


# ---------- Consulta ----------

st.subheader("🔍 Realizar una consulta")

with st.form("query_form"):
    col1, col2 = st.columns([4, 1])
    with col1:
        question = st.text_input(
            "Escribe tu pregunta sobre las películas:",
            placeholder="Ej. ¿En qué película de 1901 aparece Carrie Nation?",
        )
    with col2:
        top_k = st.number_input("Top K chunks", min_value=1, max_value=10, value=3)

    submitted = st.form_submit_button("Consultar RAG")

if submitted:
    if not question.strip():
        st.warning("Por favor escribe una pregunta.")
    else:
        with st.spinner("Buscando evidencia y generando respuesta con Gemini..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/query",
                    json={"question": question.strip(), "top_k": int(top_k)},
                    timeout=90,
                )
            except requests.exceptions.ConnectionError:
                st.error("No se pudo conectar con la API.")
                st.stop()
            except requests.exceptions.Timeout:
                st.error("La API tardó demasiado en responder. Intenta de nuevo.")
                st.stop()
            except requests.exceptions.RequestException as e:
                st.error(f"Error al consultar la API: {e}")
                st.stop()

        if response.status_code != 200:
            # Incluye casos como clave de Google ausente (el detalle viene de la API)
            st.error(
                f"Error en la API ({response.status_code}): "
                f"{error_detail(response)}"
            )
            st.stop()

        data = response.json()
        answer = data.get("answer", "")
        citations = data.get("citations", [])
        abstained = data.get("abstained", False)

        if abstained:
            st.warning(
                "⚠️ El sistema se abstuvo de responder: no hay evidencia "
                "suficiente en los documentos."
            )

        st.markdown("### 🤖 Respuesta")
        st.write(answer)

        st.divider()
        st.markdown(
            "### 📚 Evidencia recuperada"
            + (" (insuficiente para responder)" if abstained else "")
        )

        if not citations:
            st.info("La API no devolvió chunks de evidencia.")
        else:
            for c in citations:
                score = c.get("score")
                score_str = (
                    f"{score:.4f}" if isinstance(score, (int, float)) else "N/A"
                )
                title = c.get("title") or "Título no disponible"
                year = c.get("release_year") or "N/A"

                with st.expander(
                    f"[{c.get('id', '?')}] {title} ({year}) · "
                    f"{SCORE_LABEL}: {score_str}"
                ):
                    st.markdown(
                        f"**Origen:** `{c.get('source', 'desconocido')}` · "
                        f"fila {c.get('row', 'N/A')} · chunk {c.get('chunk', 'N/A')}"
                    )
                    st.write(c.get("text", ""))
