"""
Python functions behind each tool the verifier exposes to Qwen.

The orchestrator imports from here. Schema definitions live in
`ollama_client.py`; execution lives here. Keeping them separate lets the
orchestrator gate which tools are *offered* to the model without touching
the prompt.

These functions are intentionally thin — they delegate to the modules that
already do the real work (`knowledge_base.local_check` and
`trusted_sources.search`). Section 5 of the build plan wires the dispatch
loop on top of this.
"""

from __future__ import annotations

from typing import Any

from logiclayer.knowledge_base.local_check import check_local_db
from logiclayer.trusted_sources.search import search_trusted_sources


def run_check_local_db(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatch a `check_local_db` tool call from Qwen.

    Expected arguments: {"claim": str}
    Returns a JSON-serializable dict so it can be fed back as a tool message.
    """
    claim = (arguments or {}).get("claim", "").strip()
    if not claim:
        return {"found": False, "error": "missing 'claim' argument"}

    result = check_local_db(claim)
    if result is None:
        return {"found": False, "claim": claim}

    # check_local_db returns (fact_id, statement, source_name)
    fact_id, statement, source_name = result
    return {
        "found": True,
        "claim": claim,
        "matched_fact_id": fact_id,
        "statement": statement,
        "source": source_name,
    }


def run_search_trusted_sources(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatch a `search_trusted_sources` tool call from Qwen.

    Expected arguments: {"claim": str}
    Returns a JSON-serializable dict. Only callable when the orchestrator has
    decided to expose the tool (i.e. local check came back empty).
    """
    claim = (arguments or {}).get("claim", "").strip()
    if not claim:
        return {"found": False, "error": "missing 'claim' argument"}

    result = search_trusted_sources(claim)
    if result is None:
        return {"found": False, "claim": claim}

    # search_trusted_sources returns (query, value, source_name)
    _, value, source_name = result
    return {
        "found": True,
        "claim": claim,
        "evidence": value,
        "source": source_name,
    }


def run_report_verdict(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and normalize a `report_verdict` call from Qwen.

    This does not "do" anything externally — it just makes sure the verdict
    payload is well-formed before the orchestrator records it. Heavy
    validation here keeps the orchestrator loop simple.
    """
    args = arguments or {}
    claim = (args.get("claim") or "").strip()
    verdict = (args.get("verdict") or "").strip().lower()
    evidence = (args.get("evidence") or "").strip()
    correction = (args.get("correction") or "").strip()

    if verdict not in {"verified", "unverified", "wrong"}:
        return {"accepted": False, "error": f"invalid verdict '{verdict}'"}
    if not claim:
        return {"accepted": False, "error": "missing 'claim'"}
    if verdict == "wrong" and not correction:
        return {
            "accepted": False,
            "error": "verdict 'wrong' requires a non-empty 'correction' field",
        }

    return {
        "accepted": True,
        "claim": claim,
        "verdict": verdict,
        "evidence": evidence or ("no evidence found" if verdict == "unverified" else ""),
        "correction": correction,
    }


TOOL_DISPATCH = {
    "check_local_db": run_check_local_db,
    "search_trusted_sources": run_search_trusted_sources,
    "report_verdict": run_report_verdict,
}