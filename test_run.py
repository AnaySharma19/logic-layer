#Mock Test Run for Orchestration Engine
"""This script is designed to test the orchestration engine in a controlled environment. 
    It simulates the interactions between the various components of the system, including the agent connector, search tool, and contradiction detector. 
    The goal is to validate the orchestration logic and ensure that the system behaves as expected under different scenarios."""

import sys
import os
import asyncio


# Creating mock internal directory structure dynamically so script runs safely
os.makedirs("logiclayer/reporting", exist_ok=True)
with open("logiclayer/reporting/__init__.py", "w") as f: pass


with open("logiclayer/reporting/formatter.py", "w") as f:
    f.write
    ('''def format_report(verdicts_list: list) -> str:
    lines = ["===================================", "   LOGIC-LAYER AUDIT REPORT OUT", "==================================="]
    for v in verdicts_list:
        lines.append(f"-> Claim: {v.get('claim')}")
        lines.append(f"   Verdict: {v.get('verdict').upper()}")
        lines.append(f"   Tier Used: {v.get('tier_used')}")
        if v.get('correction'):
            lines.append(f"   Correction Suggestion: {v.get('correction')}")
        lines.append("-----------------------------------")
    
    if verdicts_list and "pipeline_latency" in verdicts_list[0]:
        lines.append(f" Total Engine Latency: {verdicts_list[0]['pipeline_latency']}")
        lines.append(f" Loop Iteration Count: {verdicts_list[0]['loop_attempts_made']}/2")
    return "\\n".join(lines)
    ''')


# Reload system tracking registers
from Orchestrator import OrchestrationEngine

class MockAgentConnector:
    async def get_latest_response(self, session_id: str) -> str:
        return "The sky is green. Water is wet."
    async def request_corrected_response(self, session_id: str, feedback: str) -> str:
        print(f"Kunal's Agent received feedback: [{feedback}]")
        return "The sky is blue. Water is wet."
    async def extract_claims(self, text: str) -> list:
        if "green" in text:
            return ["The sky is green", "Water is wet"]
        return ["The sky is blue", "Water is wet"]

class MockSearchTool:
    async def query_whitelist(self, claim: str) -> str:
        return "Database contents matching context instructions."

class MockContradictionDetector:
    async def analyze(self, claim: str, context: str) -> dict:
        if "green" in claim:
            return 
            {
                "claim": claim,
                "verdict": "wrong",
                "evidence": "Observed context mismatch error.",
                "source_url": "https://python.org",
                "correction": "The sky is blue",
                "tier_used": "none"
            }
        return 
        {
            "claim": claim,
            "verdict": "verified",
            "evidence": "Matches database logs perfectly.",
            "source_url": "https://python.org",
            "correction": None,
            "tier_used": "local"
        }

async def main():
    
    engine = OrchestrationEngine(
        agent_connector=MockAgentConnector(),
        search_tool=MockSearchTool(),
        contradiction_detector=MockContradictionDetector()
    )
    result = await engine.process_response_stream(session_id="session_789")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
