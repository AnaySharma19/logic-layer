"""
Thin HTTP wrapper around Ollama's /api/chat endpoint.

This module is the only place in the codebase that talks to Ollama directly.
It exposes a single `chat()` function that takes a messages list and an
optional tools schema, POSTs to http://localhost:11434/api/chat, and returns
a parsed response dict.

It also defines the three OpenAI-style tool schemas the orchestrator hands to
Qwen3.5 4B. The actual Python functions those tools call into live in
`tools.py` — schemas and execution are kept separate so the orchestrator can
gate which tools are offered without touching the prompt.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

OLLAMA_HOST = "http://localhost:11434"
CHAT_ENDPOINT = f"{OLLAMA_HOST}/api/chat"
DEFAULT_MODEL = "qwen3.5:4b"
REQUEST_TIMEOUT = 120  # seconds


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI-style function-calling JSON)
# ---------------------------------------------------------------------------
# These three schemas are what Qwen sees. They are intentionally minimal —
# the model only needs to know what each tool is called, what arguments it
# takes, and what it returns conceptually. The real work is done by the
# Python functions in tools.py; the orchestrator dispatches there.

TOOL_CHECK_LOCAL_DB = {
    "type": "function",
    "function": {
        "name": "check_local_db",
        "description": (
            "Check the local knowledge base for an exact or semantically "
            "similar fact matching the given claim. ALWAYS call this first "
            "before considering any other verification step."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The claim to look up in the local database.",
                },
            },
            "required": ["claim"],
        },
    },
}

TOOL_SEARCH_TRUSTED_SOURCES = {
    "type": "function",
    "function": {
        "name": "search_trusted_sources",
        "description": (
            "Search a fixed whitelist of trusted domains (with a .gov fallback) "
            "for evidence about a claim. Only call this AFTER check_local_db "
            "has returned empty for the same claim."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The claim to look up on trusted external sources.",
                },
            },
            "required": ["claim"],
        },
    },
}

TOOL_REPORT_VERDICT = {
    "type": "function",
    "function": {
        "name": "report_verdict",
        "description": (
            "Report the final verdict for a claim. Call this exactly once per "
            "claim after you have gathered all the evidence you intend to gather."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The original claim being judged.",
                },
                "verdict": {
                    "type": "string",
                    "enum": ["verified", "unverified", "wrong"],
                    "description": (
                        "verified = evidence supports the claim; "
                        "wrong = evidence contradicts the claim; "
                        "unverified = no evidence found anywhere."
                    ),
                },
                "evidence": {
                    "type": "string",
                    "description": (
                        "Short summary of the evidence found (or 'no evidence "
                        "found' for unverified). Include the source name."
                    ),
                },
                "correction": {
                    "type": "string",
                    "description": (
                        "Only set when verdict is 'wrong': the corrected "
                        "statement, shown side-by-side with the original."
                    ),
                },
            },
            "required": ["claim", "verdict", "evidence"],
        },
    },
}

ALL_TOOLS: list[dict[str, Any]] = [
    TOOL_CHECK_LOCAL_DB,
    TOOL_SEARCH_TRUSTED_SOURCES,
    TOOL_REPORT_VERDICT,
]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to Ollama and return the parsed response."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ConnectionError(
            f"Could not reach Ollama at {url}. Is `ollama serve` running? "
            f"Underlying error: {exc}"
        ) from exc


def chat(
    messages: list[dict[str, Any]],
    *,
    model: str = DEFAULT_MODEL,
    tools: list[dict[str, Any]] | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """
    Send a chat completion request to Ollama and return the parsed response.

    Args:
        messages: List of {"role": ..., "content": ...} messages. Tool
            messages use role "tool" with a "name" field.
        model: Name of the Ollama model to use (default: qwen3.5:4b).
        tools: Optional list of OpenAI-style tool schemas to expose. Pass
            `None` or `[]` to make no tools available for this turn.
        stream: Whether to stream the response. Kept off by default so the
            orchestrator gets a single, complete reply to reason over.

    Returns:
        The parsed JSON response from Ollama. The shape mirrors OpenAI's
        chat completion response: {"message": {"role", "content",
        "tool_calls": [...]}, "done": true, ...}.

    Raises:
        ConnectionError: If Ollama is unreachable.
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools

    return _post(CHAT_ENDPOINT, payload)


def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Pull the tool_calls list out of an Ollama chat response, or [] if none.

    Ollama returns tool calls under message.tool_calls, each shaped like:
        {"function": {"name": ..., "arguments": {...}}}
    `arguments` may arrive as a JSON string on some versions, so we normalize.
    """
    message = response.get("message") or {}
    raw_calls = message.get("tool_calls") or []
    normalized: list[dict[str, Any]] = []
    for call in raw_calls:
        func = call.get("function") or {}
        name = func.get("name")
        arguments = func.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                arguments = {}
        if name:
            normalized.append({"name": name, "arguments": arguments})
    return normalized


def extract_content(response: dict[str, Any]) -> str:
    """Pull the plain text content out of an Ollama chat response."""
    message = response.get("message") or {}
    return message.get("content") or ""


if __name__ == "__main__":
    # Minimal sanity check — runs only if invoked directly.
    print(f"Pinging Ollama at {CHAT_ENDPOINT} with model={DEFAULT_MODEL}...")
    try:
        resp = chat([{"role": "user", "content": "hello"}])
    except ConnectionError as e:
        print(f"❌ {e}")
        raise SystemExit(1)
    print("✅ Response received:")
    print(json.dumps(resp, indent=2)[:500])