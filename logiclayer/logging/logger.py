#Log Infrastructure and seperate code with Log management

import os
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict

# Define paths relative to this project 
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "local-knowledge-base"))
DB_PATH = os.path.join(DB_DIR, "audit_logs.db")
JSON_LOG_PATH = os.path.join(DB_DIR, "pipeline_logs.jsonl")

def init_logger():
    """
    Ensures directory paths exist and creates the SQLite database tables if they haven't been initialized yet.
    """

    os.makedirs(DB_DIR, exist_ok=True)
    

    connector = sqlite3.connect(DB_PATH)
    cursor = connector.cursor()
    
    # Table for tracking user sessions and queries
    cursor.execute
    (
        """
        CREATE TABLE IF NOT EXISTS queries 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            query_text TEXT NOT NULL
        )
        """
    )
    
    # Table for capturing nested AI tool choices and execution payloads
    cursor.execute
    (
        """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            result TEXT NOT NULL
        )
        """
    )
    
    connector.commit()
    connector.close()

# Run initialization when this file is imported by the orchestrator
init_logger()


def log_query(session_id: str, query_text: str):
    """Logs the entry point raw text query into both SQLite and JSONL formats (since it was an option so i chose both)."""
    timestamp = datetime.utcnow().isoformat()
    

    # 1. SQLite Write
    try:
        connector = sqlite3.connect(DB_PATH)
        cursor = connector.cursor()
        cursor.execute("INSERT INTO queries (session_id, timestamp, query_text) VALUES (?, ?, ?)",(session_id, timestamp, query_text))
        connector.commit()
        connector.close()

    except Exception as e:
        print(f"[Logger Error] SQLite query logging failed: {e}")


    # 2. JSONL Write (Appends structured logs cleanly line-by-line)
    try:
        log_entry = {
            "type": "user_query",
            "session_id": session_id,
            "timestamp": timestamp,
            "query": query_text
        }

        with open(JSON_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        print(f"[Logger Error] JSON query logging failed: {e}")


def log_tool_call(session_id: str, tool_name: str, arguments: Dict[str, Any], result: str):

    timestamp = datetime.utcnow().isoformat()
    args_json = json.dumps(arguments)
    

    # 1. SQLite Write
    try:
        connector = sqlite3.connect(DB_PATH)
        cursor = connector.cursor()
        cursor.execute("INSERT INTO tool_calls (session_id, timestamp, tool_name, arguments, result) VALUES (?, ?, ?, ?, ?)",(session_id, timestamp, tool_name, args_json, result))
        connector.commit()
        connector.close()

    except Exception as e:
        print(f"[Logger Error] SQLite tool logging failed: {e}")


    # 2. JSONL Write
    try:
        log_entry = {
            "type": "tool_execution",
            "session_id": session_id,
            "timestamp": timestamp,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result
        }
        with open(JSON_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    except Exception as e:
        print(f"[Logger Error] JSON tool logging failed: {e}")
