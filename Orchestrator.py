#Orchestration Loop
"""ROLE ---->  this code will work as the central guidrail for the project 
1. it will take the agent connections from Kunal 
2. the prompts will be processed by the AI agent
3. it will recieve the respopnse and divert them to search tool build by Manish & Ranveer
4. their code (i guess) will seperate individual claims and give in return some file with claim and source
5. the file is then given to contradiction detector made by Aaditya
6. the filtered response is then sent to formatter made by Soumya to build the three verdict statement"""

import asyncio
try:
    from logiclayer.reporting.formatter import format_report
except ImportError :
    def format_report(verdicts: list) -> str:
        return f"=== fallback report ===\n Processed {len(verdicts)} verdicts.\n=== end fallback report ==="
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(level = logging.INFO)

class OrchestrationEngine :

    def __init__(
        self,
        agent_connector : Any,
        search_tool : Any,
        contradiction_detector : Any,
        #formatter : Any
    ) -> None:
        """for plug and play feature added for future updates

        Args :
            agent_connector : by Kunal
            search_tool : by Ranveer and Manish
            contradiction_detector : by Aaditya
        """
        self.agent = agent_connector
        self.search = search_tool
        self.detector = contradiction_detector
        self.max_attempts = 2

    async def _verify_single_claim(self, claim: str)  -> Dict[str,Any]:
        # Runs Validation process
        try :
            search_results = await self.search.query_whitelist(claim)

            verdict_data : Dict[str, Any] = await self.detector.analyze(claim, search_results)

            return verdict_data

        except Exception as exc:
            logger.error("Step failure validating claim '%s' : %s", claim, exc)
            return 
            { 
                "claim" : claim,
                "verdict" : "unverified",
                "correction" : None,
                "tier_used" : "none"
            }
    async def process_response_stream(self, session_id : str) -> str:
        """Main security loop
        Args :
            session_id : Track user ID 
        Returns :
            A single formatted report string for formatter
        """

        start_time : float = time.perf_counter()

        attempt : int = 1
        current_feedback : str = ""
        raw_ai_text : str = ""
        final_verdicts : List[Dict[str,Any]] = []

        while attempt <= self.max_attempts :
            logger.info("starting verification loop cycle. try %d / %d", attempt, self.max_attempts)
            

            #Step 1 :: Get response from agent connector
            if attempt == 1 :
                raw_ai_text = await self.agent.get_latest_response(session_id)
            else :
                logger.warning("Routing correction logs")

                raw_ai_text = await self.sgent.request_corrcted_response(session_id, current_feedback)
            

            #Step 2 :: pull individual claims
            claims : List[str] = await self.agent.extract_claims(raw_ai_text)

            if not claims:
                break


            #Step 3 :: parallel evaluation
            tasks = [self._verify_single_claim(claim) for claim in claims]
            final_verdicts = await asyncio.gather(*tasks)


            #Step 4 :: analyse if claim returned as "wrong"
            #contradictions = [v for v in final_verdicts if v["verdict"] == "wrong"]
            contradictions = [v for v in final_verdicts
                              if v is not None and isinstance(v, dict) and v.get("verdict") == "wrong" and v.get("correction")]                            
                            
            if not contradictions :
                logger.info("All facts checked ")
                break


            #Step 5 :: if attempts left and contradiction exists go back to loop again
            logger.warning("Hallucinations identified. constructing feedback parameter loop.")
            feecback_messages = [f"fix target '{c['claim']}' : Use '{c['corrction']}' instead." for c in contradictions]
            current_feedback = " | ".join(feedback_messages)

            attempt += 1


        #calculate exact time taken to run the system loop
        end_time : float = time.perf_counter()
        execution_latency : float = end_time - start_time
        logger.info("orchestration loop executed in %f seconds", execution_latency)


        #get loop tracking details to logs metadata
        logger.info("Total loop iterations : %d", attempt - 1)


        #route the structured outputs
        final_report_cli : str = format_report(final_verdicts)
        return final_report_cli