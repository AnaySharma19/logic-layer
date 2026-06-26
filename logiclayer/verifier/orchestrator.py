#The ORCHESTRATOR 
"""
The string of the pearls.
This is the file that actually ties everything above together — it's the most important file in the project.

- [ ] Send the user's prompt through the connector from step 4 → get the raw response (`logiclayer/verifier/orchestrator.py`)
- [ ] Call `ollama_client.py` with the raw response, the system prompt, and only the `check_local_db` + `report_verdict` tools enabled at first
- [ ] When a `check_local_db` tool call comes back empty for a claim, **only then** add `search_trusted_sources` to the tools list for the next turn — this gating logic lives in `orchestrator.py`, not in the prompt, so Qwen can't skip the local check even if it wanted to
- [ ] Execute whichever tool Qwen calls by dispatching to the real function in `logiclayer/verifier/tools.py`, feed the result back into the message history, and call Ollama again — loop until `report_verdict` has been called for every claim
- [ ] Collect all `report_verdict` calls into one structured report object (still in `orchestrator.py`)
"""


import asyncio
import logging
import time
from typing import Any, Dict, List

# Setup the logger 
logger = logging.getLogger(__name__)

try:
    # 2. Importing real ollama client.py
    from logiclayer.verifier.ollama_client import call_ollama 
    
    #Aaditya focus that I have mentioned call_ollama change it according to your setup

except ImportError:
    logger.critical("ollama_client.py could not be found! Registering safety mock fallback.")
    async def call_ollama(messages: list, tools: list) -> dict:
        await asyncio.sleep(0.05)
        return {"tool_calls": [{"name": "check_local_db", "arguments": {"claim": "Automated pipeline validation."}}]}

try:
    # 4. Importing functions from logiclayer/verifier/tools.py
    from logiclayer.verifier.tools import check_local_db, search_trusted_sources, report_verdict
    
    #Announcement folks here I have named  check_local_db, search_trusted_sources, report_verdict from the tools.py

except ImportError:
    logger.critical("tools.py module file missing! Initializing fallback.")
    async def check_local_db(claim: str) -> list: return []
    async def search_trusted_sources(claim: str) -> str: return "Web proof baseline."
    async def report_verdict(verdict_data: dict) -> str: return "Logged."

try:
    # Integration with the logger module created
    from logiclayer.logging.logger import log_query, log_tool_call

except ImportError:
    logger.warning("logging/logger.py missing. Internal trace wrappers will catch write requests.")
    def log_query(sid, q): pass
    def log_tool_call(sid, t, a, r): pass


# ==============================================================================
#ORCHESTRATION ENGINE
# ==============================================================================

class OrchestrationEngine:
    def __init__(self, agent_connector: Any):
        self.agent_connector = agent_connector

    async def process_response_stream(self, session_id: str) -> Dict[str, Any]:
        """
        Executes an audited verification event loop over claims with active failure prevention.
        """
        # Start benchmark timing counter
        start_time = time.perf_counter()
        
        # 5. Master container report payload with structured report object
        report_payload = {
            "status": "failed",
            "session_id": session_id,
            "execution_latency_seconds": 0.0,
            "verdicts": [],
            "error_log": None
        }

        try:
            # 1. Send user's prompt through connector 
            try:
                raw_response = await self.agent_connector.get_latest_response(session_id)

            except Exception as conn_err:
                raise RuntimeError(f"Step 4 Connector interface network breakdown: {conn_err}")

            # Audit the starting raw user request string
            log_query(session_id, raw_response)

            system_prompt = (
                "You are an orchestration checker. Extract statements and call verification tools. "
                "You must check local db tables before utilizing external web engines."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Verify: {raw_response}"}
            ]
            
            # 2. Only the 'check_local_db' + 'report_verdict' tools enabled at first
            enabled_tools = ["check_local_db", "report_verdict"]
            
            loop_active = True
            max_turns = 4 # Safety brake preventing infinite loops 
            turn = 0

            # 4. Loop until 'report_verdict' has been called for every claim
            while loop_active and turn < max_turns:
                turn += 1
                
                try:
                    model_output = await call_ollama(messages, tools=enabled_tools)

                except Exception as llm_err:
                    logger.error(f"Ollama remote network transaction failed on turn {turn}: {llm_err}")
                    report_payload["error_log"] = f"LLM client interface failure: {llm_err}"
                    break

                tool_calls = model_output.get("tool_calls", [])
                
                if not tool_calls:
                    messages.append({"role": "assistant", "content": model_output.get("content", "")})
                    break 

                # 4. Handle tool execution choices 
                for tool in tool_calls:
                    tool_name = tool.get("name")
                    tool_args = tool.get("arguments", {})
                    tool_result_str = ""
                    
                    try:
                        if tool_name == "check_local_db":
                            db_results = await check_local_db(tool_args.get("claim"))
                            tool_result_str = str(db_results)
                            
                            # 3. Gating Logic: When check_local_db comes back empty, **"only then"** add search_trusted_sources
                            if not db_results and "search_trusted_sources" not in enabled_tools:
                                enabled_tools.append("search_trusted_sources")
                                logger.info("Gating criterion achieved: search_trusted_sources exposed to agent.")

                        elif tool_name == "search_trusted_sources":
                            web_results = await search_trusted_sources(tool_args.get("claim"))
                            tool_result_str = str(web_results)

                        elif tool_name == "report_verdict":
                            await report_verdict(tool_args)
                            tool_result_str = "Logged."
                            
                            # 5. Collect all 'report_verdict' calls into one structured report object
                            report_payload["verdicts"].append(tool_args)
                            
                            # Switch loop indicator off as validation completed
                            loop_active = False

                        # 4. Feed the valid result back into the message history
                        messages.append({"role": "tool", "name": tool_name, "content": tool_result_str})
                        log_tool_call(session_id, tool_name, tool_args, tool_result_str)

                    except Exception as tool_runtime_err:
                        
                        #Failure Containment: If a tool crashes, log it but let the orchestration loop continue
                        
                        error_msg = f"Runtime Crash Exception inside tool '{tool_name}': {tool_runtime_err}"
                        logger.error(error_msg)
                        messages.append({"role": "tool", "name": tool_name, "content": error_msg})
                        log_tool_call(session_id, tool_name, tool_args, error_msg)

            # Define processing completion indicators
            report_payload["status"] = "success" if not report_payload["error_log"] else "partial_success"

        except Exception as critical_pipeline_crash:
            logger.critical(f"Fatal Orchestration Framework Core System Failure: {critical_pipeline_crash}")
            report_payload["status"] = "fatal_crash"
            report_payload["error_log"] = str(critical_pipeline_crash)

        finally:
            # Time difference calculation 
            report_payload["execution_latency_seconds"] = round(time.perf_counter() - start_time, 4)
            print(f"Orchestration Loop Execution Latency: {report_payload['execution_latency_seconds']} seconds")
            return report_payload

