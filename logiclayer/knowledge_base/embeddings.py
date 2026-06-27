import sqlite3
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

DB_PATH = Path("local-knowledge-base/knowledge_base.db")
INDEX_PATH = Path("local-knowledge-base/embeddings/faiss_index.bin")
MAP_PATH = Path("local-knowledge-base/embeddings/fact_mapping.txt")

MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("🧠 Loading BAAI/bge-small-en-v1.5 neural network model...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_embeddings_index():
    """Reads facts from SQLite and saves a guarded FAISS index over statements."""
    print("🤖 Initializing semantic embedding pipeline...")

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        print(f"❌ Error: Database file not found at {DB_PATH}. Run loader.py first!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT fact_id, statement FROM facts")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("⚠️ No facts found in the database to index.")
        return

    print(f"📖 Found {len(rows)} facts to process. Generating neural embeddings...")

    fact_ids = [row[0] for row in rows]
    statements = [row[1] for row in rows]

    model = get_model()
    vectors_matrix = model.encode(statements, normalize_embeddings=True).astype('float32')
    dimensions = vectors_matrix.shape[1]

    index = faiss.IndexFlatIP(dimensions)
    index.add(vectors_matrix)

    if index.ntotal != len(fact_ids):
        raise ValueError(f"❌ Matrix mismatch: Index row count ({index.ntotal}) doesn't match ID mapping count ({len(fact_ids)}).")

    faiss.write_index(index, str(INDEX_PATH))

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        for f_id in fact_ids:
            f.write(f"{f_id}\n")

    print(f"✅ Success! FAISS index saved at: {INDEX_PATH}")
    print(f"🗺️ Fact ID mappings saved at: {MAP_PATH} (Rows: {index.ntotal})")


if __name__ == "__main__":
    try:
        build_embeddings_index()
    except Exception as e:
        print(f"💥 Embedding generation failed: {e}")
