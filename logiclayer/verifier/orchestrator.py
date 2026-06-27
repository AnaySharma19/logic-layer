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
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

# Setup the logger 
logger = logging.getLogger(__name__)

Max_try = 3 #number of tries to import any file
for attempt in range(1, Max_try+1):
    try:
        # 2. Importing real ollama client.py
        #Aaditya focus that I have mentioned call_ollama we will discuss it according to your setup
        from logiclayer.verifier.ollama_client import call_ollama 
        logger.info("Successfully imported call_ollama.")
        break
        
    except ImportError as e:
        logger.error(f"Attempt {attempt}/{Max_try} : ollama_client.py could not be found!")
        if attempt == Max_try:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)
        
for attempt in range(1, Max_try+1):
    try:
        # 4. Importing functions from logiclayer/verifier/tools.py
        #Announcement folks here I have named  check_local_db, search_trusted_sources, report_verdict from the tools.py
        from logiclayer.verifier.tools import check_local_db, search_trusted_sources, report_verdict
        logger.info("Successfully imported tools -> check_local_db, search_trusted_sources, report_verdict.")
        break

    except ImportError as e:
        logger.error(f"Attempt {attempt}/{Max_try} : tools.py module file missing! Initializing fallback.")
        if attempt == Max_try:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)

for attempt in range(1, Max_try+1):
    try:
        # Integration with the logger module created
        from logiclayer.logging.logger import log_query, log_tool_call
        logger.info("Successfully imported logger -> log_query, log_tool_call")
        break

    except ImportError as e:
        logger.warning("logging/logger.py missing.")
        if attempt == Max_try:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)

for attempt in range(1, Max_try+1):
    try:
        #importing connector as per Kunal's code
        from logiclayer.connectors.nvidia_connector import NvidiaConnector
        logger.info("Successfully imported nvidia_connector -> NvidiaConnector")
        break

    except ImportError as e:
        logger.error(f"Attempt {attempt}/{Max_try} : nvidia_connector file missing! Initializing fallback.")
        if attempt == Max_try:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)

for attempt in range(1, Max_try+1):
    try:
        #importing system_prompt as per plan.md
        from logiclayer.verifier.system_prompt import sys_prompt
        logger.info("Successfully imported system_prompt -> sys_prompt")
        break

    except ImportError as e:
        logger.error(f"Attempt {attempt}/{Max_try} : system_prompt file missing! Initializing fallback.")
        if attempt == Max_try:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)


# ==============================================================================
#ORCHESTRATION ENGINE
# ==============================================================================

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
        self.agent_connector = NvidiaConnector

    async def process_response_stream(self, Any):
        """
        Executes an audited verification event loop over claims with active failure prevention.
        """
        # Start benchmark timing counter
        start_time = time.perf_counter()
        
        # 5. Master container report payload with structured report object
        report_payload = {
            "status": "failed",
            "execution_latency_seconds": 0.0,
            "verdicts": [],
            "error_log": None
        }

        try:
            # 1. Send user's prompt through connector 
            try:
                raw_response = await self.agent_connector.send(self, prompt: str)
                logger.info("Recieved raw response from the AI agent")

            except Exception as conn_err:
                raise RuntimeError(f"Failed to connect to the Target AI Agent: {conn_err}")
                logger.error("Agent Connetor failed to connect to the Orchestrator")

            # Audit the starting raw user request string
            log_query(raw_response)

            try:
                #Here we will try to acquire the response from Qwen3.5
                system_prompt_response = sys_prompt(raw_response)
                logger.info("Transferred the system prompt to Qwen3.5 4B")
            
            except Exception as e:
                raise RuntimeError(f"Failed to send system_prompt : {e}")
                logger.error("Failed to send system_promptr")

            #Since we have received the modified response from ollama sonow we will go for the tools implementation






































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

