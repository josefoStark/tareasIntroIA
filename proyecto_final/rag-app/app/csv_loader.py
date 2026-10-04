import csv
import re


REQUIRED_COLUMNS = ["Title", "Plot"]

# Marcadores de referencia de Wikipedia como [1], [23]. Se eliminan porque
# se confunden con las citas [n] que debe generar el modelo.
REFERENCE_MARKER = re.compile(r"\[\d+\]")


def clean_text(text):
    text = REFERENCE_MARKER.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def load_movies_csv(path, limit=None):
    documents = []

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        missing = [
            column for column in REQUIRED_COLUMNS
            if column not in (reader.fieldnames or [])
        ]

        if missing:
            raise ValueError(
                "El CSV no tiene las columnas requeridas: "
                f"{', '.join(missing)}. Columnas encontradas: "
                f"{reader.fieldnames}. Verifica que el separador sea coma."
            )

        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                break

            title = row.get("Title", "").strip()
            release_year = row.get("Release Year", "").strip()
            origin = row.get("Origin/Ethnicity", "").strip()
            director = row.get("Director", "").strip()
            cast = row.get("Cast", "").strip()
            genre = row.get("Genre", "").strip()
            plot = clean_text(row.get("Plot", ""))

            document = f"""
Title: {title}
Release Year: {release_year}
Origin/Ethnicity: {origin}
Director: {director}
Cast: {cast}
Genre: {genre}
Plot: {plot}
""".strip()

            metadata = {
                "source": path,
                "title": title,
                "release_year": release_year,
                "row": i
            }

            documents.append({
                "text": document,
                "metadata": metadata
            })

    return documents
