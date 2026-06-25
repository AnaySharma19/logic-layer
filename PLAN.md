# Logic Layer — Build Plan (Ollama + Qwen3.5 4B)

**Pipeline:** user prompt → target AI agent (via API) → raw text response → **Qwen3.5 4B, served locally through Ollama** → checks the local DB first, trusted sources only if nothing found locally → reply to user with a verdict (`verified` / `unverified` / `wrong`).

Every checklist item below ends with the file it belongs in, so there's no ambiguity about where code goes.

---

## 0. Project structure (reference this for every step below)

```
logic-layer/
├── README.md
├── plan.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── logiclayer/
│   ├── __init__.py
│   ├── cli/
│   │   ├── main.py                  # Typer app, entry point for the `logiclayer` command
│   │   └── commands/
│   │       ├── query.py             # `logiclayer query`
│   │       ├── verify.py            # `logiclayer verify`
│   │       ├── kb.py                # `logiclayer kb add-fact` / `kb refresh`
│   │       └── scheduler.py         # `logiclayer scheduler start`
│   ├── connectors/
│   │   ├── base.py                  # AgentConnector interface
│   │   └── openai_connector.py      # (or whichever chatbot/agent you're verifying)
│   ├── verifier/
│   │   ├── ollama_client.py         # thin HTTP wrapper around Ollama's /api/chat
│   │   ├── tools.py                 # actual Python functions behind each tool
│   │   ├── system_prompt.py         # the system prompt template fed to Qwen
│   │   └── orchestrator.py          # the agentic loop — calls ollama_client, runs tools, enforces gating
│   ├── knowledge_base/
│   │   ├── schema.py                # Pydantic models: Fact, Source
│   │   ├── loader.py                # loads JSON facts/sources into SQLite
│   │   ├── local_check.py           # check_local_db logic (exact + embeddings match)
│   │   └── embeddings.py            # builds/queries the ChromaDB or FAISS index
│   ├── trusted_sources/
│   │   ├── search.py                # search_trusted_sources logic, whitelist-only
│   │   └── scraper.py               # requests + BeautifulSoup
│   ├── scheduler/
│   │   └── jobs.py                  # APScheduler job: refresh_knowledge_base()
│   ├── reporting/
│   │   └── formatter.py             # turns verdicts into the final user-facing reply
│   ├── logging/
│   │   └── logger.py                # SQLite/JSON logging of queries + tool calls
│   └── config/
│       ├── settings.py              # loads .env, model name, Ollama host/port
│       └── whitelisted_domains.json
├── local-knowledge-base/
│   ├── facts/                       # one JSON file per fact
│   ├── sources/                     # one JSON file per source
│   └── embeddings/                  # gitignored, regenerable
├── tests/
│   ├── test_local_check.py
│   ├── test_trusted_sources.py
│   ├── test_orchestrator.py
│   └── test_cli.py
└── docs/
```

---

## 1. First, build the local database - manish (comunicate the trusted source list with ranveer)

- [ ] Define the `Fact` and `Source` Pydantic models (`logiclayer/knowledge_base/schema.py`)
- [ ] Create the empty folders `local-knowledge-base/facts/` and `local-knowledge-base/sources/` and seed facts 
- [ ] Write the loader that reads all fact/source JSON files into SQLite (`logiclayer/knowledge_base/loader.py`)
- [ ] Write the orphan-fact checker — every fact must cite a `source_id` that exists (`logiclayer/knowledge_base/loader.py`, run as a standalone check)
- [ ] Build the embeddings index over fact text using "BAAI/bge-small-en-v1.5" (Hugging face & sentence-transformer) and manage them using FAISS (py library), stored under `local-knowledge-base/embeddings/` (`logiclayer/knowledge_base/embeddings.py`)
- [ ] Write `check_local_db(claim)` — exact match first, then embeddings fallback (`logiclayer/knowledge_base/local_check.py`)

## 2. Then build the trusted-source search tool — locked to the whitelist - ranveer (communicate the trusted source list with manish)

- [ ] Create `logiclayer/config/whitelisted_domains.json` with the approved domains
- [ ] Write the scraper (requests + BeautifulSoup) (`logiclayer/trusted_sources/scraper.py`)
- [ ] Write `search_trusted_sources(query)` — no domain parameter in the signature, searches only the whitelist + `.gov` fallback, filters out anything not on the list before returning (`logiclayer/trusted_sources/search.py`)
- [ ] Normalize results into the same JSON evidence shape as `check_local_db`'s output 
- [ ] Cache hits back into `local-knowledge-base/facts/` as new fact entries (same file, calls into `logiclayer/knowledge_base/loader.py`)(automaticaley creating the database)

## 3. Then set up Ollama and Qwen3.5 4B - aaditya

This is the part that needs its own attention — Ollama doesn't give you tool-calling for free, you write the loop yourself.

- [ ] Install Ollama and pull the model: `ollama pull qwen3.5:4b` (check the exact tag in the Ollama library — it may differ slightly)
- [ ] Confirm it runs and responds: `ollama run qwen3.5:4b "hello"` from the terminal, no project code involved yet
- [ ] Write `ollama_client.py` — a thin wrapper that POSTs to `http://localhost:11434/api/chat` with the messages array and the `tools` schema, and returns the parsed response (`logiclayer/verifier/ollama_client.py`)
- [ ] Define the three tool schemas Ollama expects (OpenAI-style function JSON): `check_local_db`, `search_trusted_sources`, `report_verdict` — schema definitions live next to the client (`logiclayer/verifier/ollama_client.py`), the actual Python functions they map to live in `logiclayer/verifier/tools.py`
- [ ] Write the system prompt template — read the response, identify claims, call `check_local_db` first, only call `report_verdict` once every claim has a verdict (`logiclayer/verifier/system_prompt.py`)
- [ ] Test `ollama_client.py` standalone with a throwaway script and 10-15 hand-written claims before wiring it into anything else — confirm Qwen actually calls the tools instead of answering from its own knowledge

## 4. Then build the agent connector - kunal

This is the "user prompt → API → generate text" half of the pipeline — the chatbot being checked, not the checker.

- [ ] Write the `AgentConnector` base interface: `send(prompt) -> raw_response` (`logiclayer/connectors/base.py`)
- [ ] Implement the connector for whichever chatbot/agent you're actually verifying (`logiclayer/connectors/openai_connector.py` or similarly named file per agent)
- [ ] Add the API key to `.env`, document it in `.env.example`, load it via `logiclayer/config/settings.py`

P.S. - use nvdia nim api keys for testing they are free!!

## 5. Then build the orchestration loop - anay

This is the file that actually ties everything above together — it's the most important file in the project.

- [ ] Send the user's prompt through the connector from step 4 → get the raw response (`logiclayer/verifier/orchestrator.py`)
- [ ] Call `ollama_client.py` with the raw response, the system prompt, and only the `check_local_db` + `report_verdict` tools enabled at first
- [ ] When a `check_local_db` tool call comes back empty for a claim, **only then** add `search_trusted_sources` to the tools list for the next turn — this gating logic lives in `orchestrator.py`, not in the prompt, so Qwen can't skip the local check even if it wanted to
- [ ] Execute whichever tool Qwen calls by dispatching to the real function in `logiclayer/verifier/tools.py`, feed the result back into the message history, and call Ollama again — loop until `report_verdict` has been called for every claim
- [ ] Collect all `report_verdict` calls into one structured report object (still in `orchestrator.py`)

## 6. Then build the three-verdict reply - soumya

- [x] `verified` → state the claim is correct, cite the source
- [x] `unverified` → say plainly nothing in the local DB or trusted sources could confirm or deny it
- [x] `wrong` → show the original statement and Qwen's corrected version side by side, cite the source
- [ ] All three cases formatted in `logiclayer/reporting/formatter.py`, called from `orchestrator.py` right after step 5 finishes

## 7. Then build the CLI

- [ ] Set up the Typer app (`logiclayer/cli/main.py`)
- [ ] `logiclayer query "<prompt>" --agent <name>` → calls connector (step 4) → orchestrator (step 5) → formatter (step 6) (`logiclayer/cli/commands/query.py`)
- [ ] `logiclayer verify <file.json>` → skips the connector, feeds a saved transcript straight into the orchestrator (`logiclayer/cli/commands/verify.py`)
- [ ] `logiclayer kb add-fact --file <fact.json>` / `logiclayer kb refresh` (`logiclayer/cli/commands/kb.py`)
- [ ] `logiclayer scheduler start` (`logiclayer/cli/commands/scheduler.py`)

## 8. Then add the APScheduler refresh job

- [ ] Write `refresh_knowledge_base()` — re-validates facts/sources, re-runs `search_trusted_sources` on anything stale (`logiclayer/scheduler/jobs.py`)
- [ ] Wire it into APScheduler with a cron trigger (same file)
- [ ] Hook it up to `logiclayer scheduler start` from step 7

## 9. Then add logging & metadata storage

- [ ] Set up SQLite (or JSON log files) for: prompt, agent used, every tool call Qwen made, final verdicts (`logiclayer/logging/logger.py`)
- [ ] Call the logger from `orchestrator.py` after every tool call and at the end of every run — this is what lets you confirm the "only search if needed" gate is actually holding in practice

## 10. Then write tests

- [ ] `tests/test_local_check.py` — exact + embeddings matching against seeded facts
- [ ] `tests/test_trusted_sources.py` — confirm only whitelisted/`.gov` domains ever come back, even if you try to force something else
- [ ] `tests/test_orchestrator.py` — confirm `search_trusted_sources` is never called when `check_local_db` already succeeded; run all three verdict paths end to end
- [ ] `tests/test_cli.py` — smoke test `logiclayer query` against a mocked connector

## 11. Then package & clean up the repo

- [ ] `pyproject.toml` with a CLI entry point so `pip install -e .` gives you the `logiclayer` command
- [ ] `.gitignore` — env files, `__pycache__`, `local-knowledge-base/embeddings/*`, logs, `*.db`
- [ ] `README.md`, `CONTRIBUTING.md`, `CODEOWNERS`
- [ ] `.github/workflows/ci.yml` — lint + test on every push

## 12. Finally, deploy (optional) 

- [ ] `Dockerfile` that installs the package, runs Ollama (or points at an existing Ollama instance), and runs the CLI/scheduler
- [ ] Decide if this stays a local dev tool or runs unattended on a server — if it's a server, Ollama needs to be running there too, not just on your laptop