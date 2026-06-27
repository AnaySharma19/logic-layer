"""
Throwaway script for testing `ollama_client.py` in isolation.

Per Section 3 of the build plan: before wiring the orchestrator, confirm
that Qwen3.5 4B (a) is reachable via Ollama, and (b) actually emits tool
calls against the three schemas defined in `ollama_client.py` instead of
answering from its own knowledge.

Run with:  python -m logiclayer.verifier._standalone_test

This file is intentionally not a pytest module — it is a manual smoke test.
"""

from __future__ import annotations

import json

from logiclayer.verifier.ollama_client import (
    ALL_TOOLS,
    chat,
    extract_content,
    extract_tool_calls,
)


HANDWRITTEN_CLAIMS = [
    # 1. well-known, easy to hallucinate correctly without tools
    "Python was created by Guido van Rossum and first released in 1991.",
    # 2. true, obscure enough to need lookup
    "The Eiffel Tower can be 15 cm taller during hot days due to thermal expansion.",
    # 3. false on its face
    "The moon is made of green cheese.",
    # 4. borderline / vague
    "Chocolate is good for you.",
    # 5. historical
    "World War II ended in 1945.",
]


def _try_call(messages: list[dict], tools: list[dict]) -> dict | None:
    try:
        return chat(messages, tools=tools)
    except ConnectionError as exc:
        print(f"❌ Ollama unreachable: {exc}")
        return None


def run() -> None:
    print("=" * 70)
    print(" Standalone smoke test for ollama_client.py + Qwen3.5 4B tool calls")
    print("=" * 70)
    print(f"Tools offered: {[t['function']['name'] for t in ALL_TOOLS]}\n")

    for i, claim in enumerate(HANDWRITTEN_CLAIMS, start=1):
        print(f"\n--- Claim {i}: {claim!r}")
        response = _try_call(
            messages=[{"role": "user", "content": claim}],
            tools=ALL_TOOLS,
        )
        if response is None:
            print("   (skipping remaining claims — Ollama is not reachable)")
            return

        tool_calls = extract_tool_calls(response)
        content = extract_content(response)

        print(f"   plain content: {content[:120]!r}{'...' if len(content) > 120 else ''}")
        if tool_calls:
            print(f"   tool calls: {len(tool_calls)}")
            for call in tool_calls:
                print(f"     - {call['name']}({json.dumps(call['arguments'])})")
        else:
            print("   ⚠️  no tool calls — model answered from its own knowledge")

    print("\n" + "=" * 70)
    print(" Done.")
    print(" Expectation: every claim should have produced at least one")
    print(" `check_local_db` tool call. If not, the system prompt or tool")
    print(" schema needs adjusting before wiring the orchestrator.")
    print("=" * 70)


if __name__ == "__main__":
    run()