import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from logiclayer.verifier.orchestrator import OrchestrationEngine

@pytest.fixture
def mock_connector():
    """Provides an isolated mock for the external agent connector stream."""
    connector = MagicMock()
    connector.send = AsyncMock(return_value="Isolated Mock Trace Stream Output")
    return connector

@pytest.fixture
def engine(mock_connector):
    """Provides a cleanly generated OrchestrationEngine instance."""
    return OrchestrationEngine(agent_connector=mock_connector)


# ==============================================================================
# FAULT-TOLERANT TEST EXECUTION SUITE
# ==============================================================================

@pytest.mark.asyncio
@patch('logiclayer.verifier.orchestrator.sys_prompt')
@patch('logiclayer.verifier.orchestrator.check_local_db')
@patch('logiclayer.verifier.orchestrator.search_trusted_sources')
@patch('logiclayer.verifier.orchestrator.report_verdict')
async def test_local_db_hit_prevents_web_search(
    mock_report, mock_search, mock_db, mock_sys_prompt, engine
):
    mock_sys_prompt.return_value = ["The moon orbits the earth."]
    mock_db.return_value = {
        "verdict": "verified", 
        "evidence": "DB Cache Match", 
        "source_url": "local_db"
    }
    mock_search.return_value = {} 
    
    result = await engine.process_response_stream("Execute Test")
    
    assert len(result["verdicts"]) == 1
    verdict_record = result["verdicts"][0]
    assert verdict_record["tier_used"] == "local_db"
    assert verdict_record["verdict"] == "verified"
    
    mock_db.assert_called_once()
    mock_search.assert_not_called() 

@pytest.mark.asyncio
@patch('logiclayer.verifier.orchestrator.sys_prompt')
@patch('logiclayer.verifier.orchestrator.check_local_db')
@patch('logiclayer.verifier.orchestrator.search_trusted_sources')
@patch('logiclayer.verifier.orchestrator.report_verdict')
async def test_fallback_to_trusted_sources(
    mock_report, mock_search, mock_db, mock_sys_prompt, engine
):
    mock_sys_prompt.return_value = ["Deep learning relies on backpropagation."]
    mock_db.return_value = {} 
    mock_search.return_value = {
        "verdict": "verified", 
        "evidence": "Found in external papers index.",
        "source_url": "https://trusted-source.example.com"
    }
    
    result = await engine.process_response_stream("Execute Test")
    
    assert len(result["verdicts"]) == 1
    verdict_record = result["verdicts"][0]
    assert verdict_record["tier_used"] == "trusted_source_search"
    mock_db.assert_called_once()
    mock_search.assert_called_once()

@pytest.mark.asyncio
@patch('logiclayer.verifier.orchestrator.sys_prompt')
@patch('logiclayer.verifier.orchestrator.report_verdict')
async def test_no_claims_extracted(mock_report, mock_sys_prompt, engine):
    mock_sys_prompt.return_value = [] 
    
    result = await engine.process_response_stream("Execute Test")
    
    assert len(result["verdicts"]) == 0
    assert result["tier_used"] == "no_claims_extracted"

@pytest.mark.asyncio
@patch('logiclayer.verifier.orchestrator.sys_prompt')
@patch('logiclayer.verifier.orchestrator.check_local_db')
@patch('logiclayer.verifier.orchestrator.report_verdict')
async def test_io_timeout_handling(mock_report, mock_db, mock_sys_prompt, engine):
    mock_sys_prompt.return_value = ["Hanging query block simulation."]
    
    # Simulate a tool call that takes longer than the internal 1.0s timeout limit
    async def lagging_db_call(*args, **kwargs):
        await asyncio.sleep(1.5) 
        return {}
        
    mock_db.side_effect = lagging_db_call
    
    result = await engine.process_response_stream("Execute Test")
    
    assert len(result["verdicts"]) == 1
    verdict_record = result["verdicts"][0]
    assert verdict_record["verdict"] == "unverified"
    assert verdict_record["tier_used"] == "timeout_failure"