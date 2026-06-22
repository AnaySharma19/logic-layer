import json
import sqlite3
from pathlib import Path

from logiclayer.knowledge_base.schema import Source, Fact

DB_PATH = Path("local-knowledge-base/knowledge_base.db")
FACTS_DIR = Path("local-knowledge-base/facts")
SOURCES_DIR = Path("local-knowledge-base/sources")


def init_db():
    """Initializes the schema structures inside SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            domain TEXT NOT NULL,
            category TEXT NOT NULL,
            retrieved_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            fact_id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            value TEXT NOT NULL,
            source_id TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES sources (source_id)
        )
    """)
    conn.commit()
    conn.close()


def load_sources(conn: sqlite3.Connection) -> set[str]:
    """Reads every JSON file in SOURCES_DIR, validates it, writes it to the
    sources table. Returns the set of source_ids that loaded successfully --
    load_facts() uses this set to catch orphan facts before they're written."""
    cursor = conn.cursor()
    loaded_ids: set[str] = set()

    for path in sorted(SOURCES_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            source = Source(**raw)
        except Exception as e:
            print(f"  ❌ Skipping invalid source file {path.name}: {e}")
            continue

        cursor.execute(
            "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?, ?, ?)",
            (source.source_id, source.name, source.url,
             source.domain, source.category, source.retrieved_at),
        )
        loaded_ids.add(source.source_id)

    conn.commit()
    return loaded_ids


def load_facts(conn: sqlite3.Connection, known_source_ids: set[str]) -> list[tuple[str, str]]:
    """Reads every JSON file in FACTS_DIR, validates it, writes valid ones to
    the facts table. Facts citing a source_id not in known_source_ids are
    orphans -- they are NOT written, and are returned so the caller can
    report them loudly instead of silently dropping them."""
    cursor = conn.cursor()
    orphans: list[tuple[str, str]] = []

    for path in sorted(FACTS_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            fact = Fact(**raw)
        except Exception as e:
            print(f"  ❌ Skipping invalid fact file {path.name}: {e}")
            continue

        if fact.source_id not in known_source_ids:
            orphans.append((fact.fact_id, fact.source_id))
            continue

        cursor.execute(
            "INSERT OR REPLACE INTO facts VALUES (?, ?, ?, ?)",
            (fact.fact_id, fact.claim, fact.value, fact.source_id),
        )

    conn.commit()
    return orphans


def load_data():
    """Full pipeline: init tables, load sources, load facts, report orphans.
    This is the function that was missing -- call this to actually populate
    the database from your local-knowledge-base/ JSON files."""
    init_db()
    conn = sqlite3.connect(DB_PATH)

    print("📥 Loading sources...")
    source_ids = load_sources(conn)
    print(f"  ✅ Loaded {len(source_ids)} sources.")

    print("📥 Loading facts...")
    orphans = load_facts(conn, source_ids)

    fact_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    print(f"  ✅ Loaded {fact_count} facts.")

    if orphans:
        print(f"\n  ⚠️  {len(orphans)} ORPHAN FACT(S) -- NOT loaded into the database:")
        for fact_id, source_id in orphans:
            print(f"     - {fact_id} cites missing source_id '{source_id}'")
    else:
        print("  ✅ No orphan facts. Database is clean.")

    conn.close()
    return orphans


def check_orphans_standalone():
    """Run this on its own (without reloading anything) to audit the JSON
    files on disk for orphan facts, without touching the database at all.
    Useful as a pre-commit / CI check before load_data() ever runs."""
    source_ids = set()
    for path in SOURCES_DIR.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            source_ids.add(raw["source_id"])
        except Exception as e:
            print(f"  ❌ Skipping unreadable source file {path.name}: {e}")

    orphans = []
    for path in FACTS_DIR.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ❌ Skipping unreadable fact file {path.name}: {e}")
            continue
        if raw.get("source_id") not in source_ids:
            orphans.append((raw.get("fact_id"), raw.get("source_id")))

    if orphans:
        print(f"⚠️  {len(orphans)} orphan fact(s) found on disk:")
        for fact_id, source_id in orphans:
            print(f"   - {fact_id} -> missing source_id '{source_id}'")
    else:
        print("✅ No orphans found on disk.")
    return orphans


if __name__ == "__main__":
    load_data()
