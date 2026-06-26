#Orchestrator tester

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from logiclayer.verifier.orchestrator import OrchestrationEngine


class MockAgentConnector:
    
    async def get_latest_response(self, session_id: str) -> str:
        return "The local database is empty and water boils at 100 degrees."

@pytest.mark.asyncio
async def test_orchestration_loop_success():
    """
    Tests that the orchestration engine executes successfully, triggers 
    the gating logic when local DB is empty, and records verdicts.
    """
    # Initialize the connector dependency
    mock_connector = MockAgentConnector()
    engine = OrchestrationEngine(agent_connector=mock_connector)
    
    session_id = "test-session-123"

    # Define a sequence of mock responses representing Qwen's tool calls turn-by-turn
    mock_llm_turns = [
        # Turn 1: Model decides to check the local database first
        {
            "tool_calls": [{"name": "check_local_db", "arguments": {"claim": "water boils at 100 degrees"}}]
        },
        # Turn 2: Model calls search_trusted_sources (unlocked because turn 1 returned empty)
        {
            "tool_calls": [{"name": "search_trusted_sources", "arguments": {"claim": "water boils at 100 degrees"}}]
        },
        # Turn 3: Model logs the final verdict and finishes
        {
            "tool_calls": [{"name": "report_verdict", "arguments": {"claim": "water boils at 100 degrees", "status": "verified"}}]
        }
    ]
    
    # Iterator to hand out the LLM turns one by one during the while loop execution
    turn_iterator = iter(mock_llm_turns)
    
    async def mock_call_ollama(messages, tools):
        try:
            return next(turn_iterator)
        except StopIteration:
            return {"content": "All claims processed."}

    # Patch all external module dependencies to isolate the orchestrator logic
    with patch("logiclayer.verifier.orchestrator.call_ollama", side_effect=mock_call_ollama), \
         patch("logiclayer.verifier.orchestrator.check_local_db", new_callable=AsyncMock) as mock_db, \
         patch("logiclayer.verifier.orchestrator.search_trusted_sources", new_callable=AsyncMock) as mock_search, \
         patch("logiclayer.verifier.orchestrator.report_verdict", new_callable=AsyncMock) as mock_verdict, \
         patch("logiclayer.verifier.orchestrator.log_query") as mock_log_query, \
         patch("logiclayer.verifier.orchestrator.log_tool_call") as mock_log_tool:

        # Configure check_local_db to return an empty array (satisfying condition 3 to unlock web search)
        mock_db.return_value = []
        mock_search.return_value = "Verified online via scientific consensus index."
        mock_verdict.return_value = "Logged."

        # Execute the timed pipeline execution stream
        result = await engine.process_response_stream(session_id)

        
        # 1. Assert core pipeline execution completed successfully
        assert result["status"] == "success"
        assert result["session_id"] == session_id
        assert isinstance(result["execution_latency_seconds"], float)
        
        # 2. Assert check_local_db was invoked on the initial loop step
        mock_db.assert_called_once_with("water boils at 100 degrees")
        
        # 3. Assert search_trusted_sources was reached (gating logic handshake worked)
        mock_search.assert_called_once_with("water boils at 100 degrees")
        
        # 4. Assert report_verdict caught the final metrics structure
        assert len(result["verdicts"]) == 1
        assert result["verdicts"][0]["status"] == "verified"
        
        # 5. Assert the audit logger system received tracking events
        mock_log_query.assert_called_once()
        assert mock_log_tool.call_count >= 1
        
        print("\n All 5 orchestration loop criteria verified successfully!")
