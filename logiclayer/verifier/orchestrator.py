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

MAX_TRY = 3 #number of tries to import any file
for attempt in range(1, MAX_TRY+1):
    try:
        # 2. Importing real ollama client.py
        #Aaditya focus that I have mentioned call_ollama we will discuss it according to your setup
        from logiclayer.verifier.ollama_client import call_ollama 
        logger.info("Successfully imported call_ollama.")
        break
        
    except ImportError as e:
        logger.error(f"Attempt {attempt}/{MAX_TRY} : ollama_client.py could not be found!")
        if attempt == MAX_TRY:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)
        
for attempt in range(1, MAX_TRY+1):
    try:
        # 4. Importing functions from logiclayer/verifier/tools.py
        #Announcement folks here I have named  check_local_db, search_trusted_sources, report_verdict from the tools.py
        from logiclayer.verifier.tools import check_local_db, search_trusted_sources, report_verdict
        logger.info("Successfully imported tools -> check_local_db, search_trusted_sources, report_verdict.")
        break

    except ImportError as e:
        logger.error(f"Attempt {attempt}/{MAX_TRY} : tools.py module file missing! Initializing fallback.")
        if attempt == MAX_TRY:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)

for attempt in range(1, MAX_TRY+1):
    try:
        # Integration with the logger module created
        from logiclayer.logging.logger import log_query, log_tool_call
        logger.info("Successfully imported logger -> log_query, log_tool_call")
        break

    except ImportError as e:
        logger.warning("logging/logger.py missing.")
        if attempt == MAX_TRY:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)

for attempt in range(1, MAX_TRY+1):
    try:
        #importing connector as per Kunal's code
        from logiclayer.connectors.nvidia_connector import NvidiaConnector
        logger.info("Successfully imported nvidia_connector -> NvidiaConnector")
        break

    except ImportError as e:
        logger.error(f"Attempt {attempt}/{MAX_TRY} : nvidia_connector file missing! Initializing fallback.")
        if attempt == MAX_TRY:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)

for attempt in range(1, MAX_TRY+1):
    try:
        #importing system_prompt as per plan.md
        from logiclayer.verifier.system_prompt import sys_prompt
        logger.info("Successfully imported system_prompt -> sys_prompt")
        break

    except ImportError as e:
        logger.error(f"Attempt {attempt}/{MAX_TRY} : system_prompt file missing! Initializing fallback.")
        if attempt == MAX_TRY:
            logger.critical("Maximum attempts reached. Crashing application safely!!")
            raise e

        importlib.invalid_caches()
        await asyncio.sleep(0.05)


# ==============================================================================
#ORCHESTRATION ENGINE
# ==============================================================================

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
            "claim": str|None,
            "execution_latency_seconds": 0.0,
            "verdicts": [],
            "evidence" : str|None,
            "source_url" : str|None,
            "correection" : str|None,
            "tier_used" : str|None
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
            #we will go for parallel execution of claim verification
            
            BATCH_SIZE = 30
            MAX_CONCURRENT_PER_BATCH = 10
            IO_TIMEOUT_SECONDS = 1.0
            async def process_single claim(claim_args : Dict[str, Any], gate : asyncio.Semaphore) -> Dict[str, Any] :
                claim_text = claim_args.get("claim", "")
                claim_record = {
                    "claim": claim_text,
                    "verdicts": "unverified",
                    "evidence" : None,
                    "source_url" : None,
                    "correection" : None,
                    "tier_used" : None
                }

    
                async with gate:
                    try:
                        # Step 1: Check Local DB Gate
                        async with asyncio.timeout(IO_TIMEOUT_SECONDS):
                            db_results = await check_local_db(claim_text)
            
                        if db_results:
                            #Local DB returns a dict containing evaluating elements
                            claim_record["verdict"] = db_results.get("verdict", "verified") # e.g., verified / wrong / unverified
                            claim_record["evidence"] = db_results.get("evidence", "Match found in local database logs.")
                            claim_record["source_url"] = db_results.get("source_url", "local_db://cache")
                            claim_record["correction"] = db_results.get("correction", None)
                            claim_record["tier_used"] = "local_db"
                
                        else:
                            # Step 2: Fallback to External Trusted Source Gate
                            async with asyncio.timeout(IO_TIMEOUT_SECONDS):
                                web_results = await search_trusted_sources(claim_text)
                
                            if web_results:
                                claim_record["verdict"] = web_results.get("verdict", "verified")
                                claim_record["evidence"] = web_results.get("evidence", None)
                                claim_record["source_url"] = web_results.get("source_url", None)
                                claim_record["correction"] = web_results.get("correction", None)
                                claim_record["tier_used"] = "trusted_source_search"

                    
                        # Step 3: Call reporting framework tool tool to sync status live
                        await report_verdict(claim_record)
                        return claim_record

                    except TimeoutError:
                        logger.error(f"Timeout hit during verification for: {claim_text[:40]}...")
                        claim_record["verdict"] = "unverified"
                        claim_record["evidence"] = "Verification pipeline timed out."
                        claim_record["tier_used"] = "timeout_failure"
                        await report_verdict(claim_record)
                        return claim_record
            
                    except Exception as worker_err:
                        logger.error(f"Unexpected worker failure: {str(worker_err)}", exc_info=True)
                        claim_record["verdict"] = "unverified"
                        claim_record["evidence"] = f"Runtime Crash: {type(worker_err).__name__}"
                        claim_record["tier_used"] = "system_error"
                        await report_verdict(claim_record)
                        return claim_record

            try:
                # 1. Extract Claims from System response
                claims_list = []

                if isinstance(system_prompt_response, str) :
                    #if its a raw block of text seperated by newlines or list tags
                    claims_list = [
                        line.strip("- *123456780. ").strip()
                        for line in system_prompt_response.split("\n")
                        if line.strip() and len(line.strip()) > 5
                    ]
            elif isinstance(system_prompt_response, dict) :
                #if its structured json containing a direct key
                claims_list = system_prompt_response.get("claims", [])
            
            elif isinstance(system_prompt_response, list):
                #if its already an array of string objects
                claims_list = system_prompt_response

            total_claims_count = len(claims_list)

            if total_c;aims_count == 0:
                logger.warning("No evaluable claim targets parased inside response payload string.")
                report_payload["tier_used"] = "no_claims_extracted"

            else:
                logger.info(f"Preparing batch grid processing loop for {total_claims_count} extracted claims...")
                concurrency_gate = asyncio.Semaphore(MAX_CONCURRENT_PER_BATCH)

                #Execute batches of 30 until empty
                for i in range(0, total_claims_count, BATCH_SIZE) :
                    current_batch_chunk = claims_list[i : i + BATCH_SIZE]
                    batch_num = (i//BATCH_SIZE) + 1

                    logger.info(f"Processing Batch Sequence #{batch_num} ({len(current_batch_chunk)} claims)...")

                    batch_tasks = [
                        process_single_claim(claim_text, concurrency_gate)
                        for claim_text in current_batch_chunk
                    ]

                    #Blocks here until all 30 elements in the active batch
                    batch_results = await asyncio.gather(*batch_tasks)
                    report_payload["verdicts"].extend(batch_results)

                logger.info("All parallel allocation batches processed successfully.")

        except Exception as tool_pipeline_err:
            logger.error(f"Error handling orchestration verification pipeline : {str(tool_pipeline_err)}", exc_info = True)
            report_payload["evidence"] = f"Pipeline execution break : {str(tool_pipeline_err)}"

        finally:
            # Closes out the time calculation
            report_payload["execution_latency_seconds"] = round(time.perf_counter() - start_time, 4)
            print(f"Orchestration Loop Execution latency : {report_payload["execution_latency_seconds"]} seconds")
            return report_payload

