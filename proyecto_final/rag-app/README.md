# RAG Movie Explorer

Sistema RAG (generación aumentada por recuperación) sobre un corpus de
películas. Responde en español, con citas `[n]`, **solo** con la evidencia
recuperada y se abstiene cuando no la hay.

| Capa | Tecnología | Rol |
|---|---|---|
| UI | Streamlit | Cargar el CSV, preguntar y ver respuesta, citas y scores |
| API | FastAPI | Ingestar, consultar e informar el estado del índice |
| Índice | ChromaDB (persistente en `chroma/`) | Guardar chunks + vectores y devolver los más similares |
| Embeddings y generación | Google AI (`gemini-embedding-001` y `gemini-3.8-flash`) | Vectorizar chunks y preguntas; redactar la respuesta |

```
Usuario → Streamlit (8501) → HTTP JSON → FastAPI (8000)
                                          ├── Google AI: embeddings
                                          ├── ChromaDB: persistencia y k-NN
                                          └── Google AI (Gemini): respuesta anclada
```

Streamlit **nunca** habla directo con Chroma ni con Google AI: todo pasa por
la API.

## Estructura

```
rag-app/
  README.md
  REPORTE.md             # reporte con evidencias
  images/                # capturas de pantalla del reporte
  requirements.txt
  .env.example
  .gitignore
  data/                  # corpus de ejemplo (CSV de películas)
  chroma/                # índice persistente (ignorado por git)
  app/
    __init__.py
    main.py              # FastAPI: /health, /ingest, /query
    chunk.py             # partición en chunks con overlap
    csv_loader.py        # lectura y limpieza del CSV de películas
    embed.py             # cliente de embeddings de Google AI
    store.py             # ChromaDB: alta (upsert) y consulta top-k
    generate.py          # Gemini: respuesta anclada + abstención
  ui/
    streamlit_app.py     # carga, consulta, citas y scores
```

## Requisitos

- Python 3.10 o superior
- Una clave de Google AI Studio

## Instalación

Todos los comandos se ejecutan desde la carpeta `rag-app/`.

1. Crear y activar el entorno virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   venv\Scripts\activate           # Windows
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Obtener la clave en [Google AI Studio](https://aistudio.google.com/apikey)
   y guardarla en un archivo `.env` (copia `.env.example`):

   ```bash
   cp .env.example .env
   # edita .env y completa:
   # GOOGLE_API_KEY=tu_clave
   ```

   El archivo `.env` no se sube al repositorio.

## Ejecución

Se necesitan dos terminales, ambas con el entorno virtual activo y dentro de
`rag-app/`.

**Terminal 1: API**

```bash
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva: <http://localhost:8000/docs>

**Terminal 2: UI**

```bash
streamlit run ui/streamlit_app.py
```

Interfaz: <http://localhost:8501>

## Uso

1. **Ingerir el corpus.** En la barra lateral de Streamlit, carga el CSV
   (por ejemplo `data/movies_test.csv`) y pulsa *Procesar e ingerir dataset*.
   La ingesta llama a `POST /ingest` y puede tardar según el tamaño del CSV y
   la cuota de la API de Google. Al terminar, el formulario de preguntas se
   habilita solo.
2. **Preguntar.** Escribe una pregunta, por ejemplo
   *¿De qué año es Alice in Wonderland?*, y pulsa *Consultar RAG*.
3. **Revisar la evidencia.** La UI muestra la respuesta con citas `[n]` y, en
   *Evidencia recuperada*, cada chunk con su origen, fila y score de similitud.

### Formato del CSV

Codificación UTF-8, separado por comas, con encabezado. Columnas esperadas:
`Release Year`, `Title`, `Origin/Ethnicity`, `Director`, `Cast`, `Genre`,
`Plot`. `Title` y `Plot` son obligatorias; si faltan, `/ingest` responde 400
con el detalle. Cada fila se trata como un documento y, antes de indexarse, se
eliminan del plot los marcadores de referencia tipo `[1]` para que no se
confundan con las citas del modelo.

### Probar la API sin la UI

```bash
# Estado
curl http://localhost:8000/health

# Ingesta
curl -X POST -F "file=@data/movies_test.csv" http://localhost:8000/ingest

# Pregunta
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿De qué año es Alice in Wonderland?", "top_k": 3}'
```

(En Windows PowerShell, usa `curl.exe` o prueba los endpoints desde `/docs`.)

### Probar la API desde `/docs`

Abre <http://localhost:8000/docs> (Swagger UI), que lista `/health`,
`/ingest` y `/query`. En cada endpoint pulsa *Try it out*:

- `/health`: *Execute* devuelve el estado y los chunks indexados.
- `/ingest`: en el campo `file` elige el CSV y pulsa *Execute*.
- `/query`: edita el cuerpo JSON, por ejemplo
  `{"question": "¿De qué año es Alice in Wonderland?", "top_k": 3}`,
  y pulsa *Execute*.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado de la API, número de chunks indexados y si hay `GOOGLE_API_KEY` |
| POST | `/ingest` | Recibe un CSV, lo parte en chunks, calcula embeddings y los guarda en Chroma. Devuelve `filename`, `movies`/`documents`, `chunks` y `total_chunks` |
| POST | `/query` | Cuerpo `{"question": str, "top_k": 1-10}`. Devuelve `answer`, `citations` (`id`, `source`, `text`, `score`, `title`, `release_year`, `row`, `chunk`) y `abstained` |

Errores comunes: 400 (CSV inválido o pregunta vacía), 409 (índice vacío),
429 (cuota de Google), 502 (error de Google AI), 503 (falta `GOOGLE_API_KEY`).

## Decisiones de diseño

### Chunking

Ventanas de **300 palabras con 50 de solape** (configurables en `chunk.py` y
`main.py`). Cada película se representa como un texto con todos sus campos
(título, año, origen, director, reparto, género, trama). Las tramas son largas,
así que cada película suele dividirse en varios chunks (84 películas generaron
248 chunks, unos 3 por película); el solape evita cortar información en el
borde entre dos chunks.

### Embeddings

`gemini-embedding-001` para chunks y preguntas (siempre el mismo modelo).
Chroma **no** usa su embedder por defecto: recibe los vectores ya calculados.
La colección usa distancia coseno y la API expone `score = 1 - distancia`, es
decir, la **similitud coseno** (mayor = más parecido).

### Regla de abstención

Hay dos capas:

1. **Umbral de similitud (`MIN_SCORE`, 0.60 por defecto).** Si el mejor chunk
   recuperado tiene similitud menor que el umbral, el sistema se abstiene
   directamente: `abstained: true`, mensaje *"No hay información suficiente
   en los documentos para responder esta pregunta."* y **no se llama a
   Gemini**. Se puede cambiar con la variable de entorno `MIN_SCORE`.
2. **Prompt de Gemini.** Si el umbral se supera, el modelo recibe los chunks
   numerados con la instrucción de responder solo con ese contexto, en español
   y con citas; si el contexto no alcanza, debe responder con el mensaje de
   abstención, y la API lo marca como `abstained: true`.

En ningún caso se rellena con conocimiento propio del modelo.

### Reparto de responsabilidades

- **Google AI:** embeddings de chunks y preguntas (`gemini-embedding-001`) y
  generación de la respuesta (`gemini-3.8-flash`).
- **ChromaDB:** persistencia en disco y búsqueda de los `top_k` vecinos por
  vector.
- **FastAPI:** orquestación (chunking, llamadas a Google AI y Chroma,
  umbral de abstención, errores HTTP).
- **Streamlit:** cliente HTTP de la API.

## Persistencia y reinicio del índice

El índice vive en `chroma/` y sobrevive a reinicios de la API. Para empezar de
cero, detén la API y borra la carpeta `chroma/`. Si cambias la métrica de
distancia de la colección, también hay que borrarla y volver a ingerir.
Re-ingerir el mismo archivo actualiza los chunks (no los duplica).

## Problemas frecuentes

- **La UI dice que no puede conectar con la API:** verifica que uvicorn corre
  en el puerto 8000 y que lo lanzaste desde `rag-app/`.
- **"Falta GOOGLE_API_KEY":** revisa `.env` y reinicia la API.
- **Error de cuota (429) o ingesta lenta:** la ingesta espera y reintenta sola
  cuando Google limita las peticiones; para un CSV grande puede tardar.
- **Error sobre la métrica de la colección al arrancar:** borra `chroma/` y
  vuelve a ingerir.
