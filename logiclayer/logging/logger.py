#Log Infrastructure and seperate code with Log management

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Any, Dict

# Setup the logger 
logger = logging.getLogger(__name__)

# Define paths relative to this project setup
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "local-knowledge-base"))
DB_PATH = os.path.join(DB_DIR, "audit_logs.db")
JSON_LOG_PATH = os.path.join(DB_DIR, "pipeline_logs.jsonl")

def is_connected(conn) :
    """Check if SQLite3 is connected, it is active and valid returns False otherwise"""
    try:
        conn.execute("SELECT 1;")
        return True
    except (sqlite3.ProgrammingError, sqlite3.OperationalError, sqlite3.Error):
        return False
    except AttributeError:
        return False

def init_logger():
    """
    Ensures directory paths exist and creates the SQLite database tables if they haven't been initialized yet.
    """
    # Create local storage directory if missing
    os.makedirs(DB_DIR, exist_ok=True)
    
    try:
        connector = sqlite3.connect(DB_PATH)
        if is_connected(connector):
            logger.info("SQLite3 database connection established successfully")
        else:
            logger.error("SQLite3 connection failed after opening")
    except sqlite3.Error as e:
        logger.critical(f"failed to open database file : {e}")
        return

    cursor = connector.cursor()
    
    # Table for tracking user sessions and queries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            query_text TEXT NOT NULL
        )
    """)
    
    # Table for capturing nested AI tool choices and execution payloads
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            result TEXT NOT NULL
        )
    """)
    
    connector.commit()
    connector.close()

# Automatically run initialization when this file is imported by the orchestrator
init_logger()


def log_query(query_text: str):
    """Logs the entry point raw text query into both SQLite and JSONL formats."""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 1. SQLite Write
    try:
        connector = sqlite3.connect(DB_PATH)
        cursor = connector.cursor()
        cursor.execute(
            "INSERT INTO queries (timestamp, query_text) VALUES (?, ?)",
            (timestamp, query_text)
        )
        connector.commit()
        connector.close()
    except Exception as e:
        print(f"[Logger Error] SQLite query logging failed: {e}")

    # 2. JSONL Write (Appends structured logs cleanly line-by-line)
    try:
        log_entry = {
            "type": "user_query",
            "timestamp": timestamp,
            "query": query_text
        }
        with open(JSON_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[Logger Error] JSON query logging failed: {e}")


def log_tool_call(tool_name: str, arguments: Dict[str, Any], result: str):
    """Logs the inner step model tool selections into both SQLite and JSONL formats."""
    # CHANGED: Swapped deprecated datetime.utcnow() for timezone-aware utc implementation
    timestamp = datetime.now(timezone.utc).isoformat()
    args_json = json.dumps(arguments)
    
    # 1. SQLite Write
    try:
        connector = sqlite3.connect(DB_PATH)
        cursor = connector.cursor()
        cursor.execute(
            "INSERT INTO tool_calls (timestamp, tool_name, arguments, result) VALUES (?, ?, ?, ?)",
            (timestamp, tool_name, args_json, result)
        )
        connector.commit()
        connector.close()
    except Exception as e:
        print(f"[Logger Error] SQLite tool logging failed: {e}")

    # 2. JSONL Write
    try:
        log_entry = {
            "type": "tool_execution",
            "timestamp": timestamp,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result
        }
        with open(JSON_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[Logger Error] JSON tool logging failed: {e}")