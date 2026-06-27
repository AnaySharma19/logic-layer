import sqlite3
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

DB_PATH = Path("local-knowledge-base/knowledge_base.db")
INDEX_PATH = Path("local-knowledge-base/embeddings/faiss_index.bin")
MAP_PATH = Path("local-knowledge-base/embeddings/fact_mapping.txt")

MIN_SIMILARITY_THRESHOLD = 0.75

MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("🧠 Loading BGE model for query analysis...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def check_local_db(claim: str):
    """Checks SQLite for exact match first, then falls back to BGE+FAISS
    semantic search with safety bounds. Returns either None or a 3-tuple:
    (fact_id, statement, source_name)."""
    print(f"\n🧐 Running verification pipeline for claim: '{claim}'")

    if not DB_PATH.exists():
        print("❌ Error: Database file missing.")
        return None

    # STRATEGY 1: EXACT MATCH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.fact_id, f.statement, s.name 
        FROM facts f
        JOIN sources s ON f.source_id = s.source_id
        WHERE LOWER(f.statement) = LOWER(?)
    """, (claim.strip(),))
    exact_match = cursor.fetchone()
    conn.close()

    if exact_match:
        print("🎯 Found an EXACT match in SQLite!")
        return exact_match

    # STRATEGY 2: SEMANTIC FALLBACK WITH SAFETY GUARDS
    if not INDEX_PATH.exists() or not MAP_PATH.exists():
        print("⚠️ Semantic lookup skipped: Vector index files missing.")
        return None

    index = faiss.read_index(str(INDEX_PATH))
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        fact_id_mapping = [line.strip() for line in f.readlines()]

    if index.ntotal != len(fact_id_mapping):
        raise RuntimeError("❌ Critical Error: FAISS index and mapping file are out of sync.")

    model = get_model()
    query_vector = model.encode([claim], normalize_embeddings=True).astype('float32')
    similarities, indices = index.search(query_vector, 1)

    match_index = indices[0][0]
    similarity_score = float(similarities[0][0])

    if match_index == -1 or match_index < 0 or match_index >= len(fact_id_mapping):
        print("⚠️ Semantic search: No valid vector matches found in the index.")
        return None

    if similarity_score < MIN_SIMILARITY_THRESHOLD:
        print(f"🛑 Match found ({similarity_score:.4f}), but fell short of the minimum safety threshold ({MIN_SIMILARITY_THRESHOLD}). Treating as unverified.")
        return None

    matched_fact_id = fact_id_mapping[match_index]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.fact_id, f.statement, s.name 
        FROM facts f
        JOIN sources s ON f.source_id = s.source_id
        WHERE f.fact_id = ?
    """, (matched_fact_id,))
    semantic_match = cursor.fetchone()
    conn.close()

    if semantic_match:
        print("🤖 Found a safe SEMANTIC match via guardrailed vector lookups!")
        print(f"📊 SCORE: {similarity_score:.4f}")
        return semantic_match
    return None


if __name__ == "__main__":
    test_claims = [
        "Python was created by Guido van Rossum: Guido van Rossum, first released in 1991",
        "Who designed the python programming language",
        "The moon is made of cheese",
    ]
    for claim in test_claims:
        result = check_local_db(claim)
        print(f"  -> Result: {result}")
