# Logic Layer — Build Plan (Ollama + Qwen3.5 4B)

**Pipeline:** user prompt → target AI agent (via API) → raw text response → **spaCy splits it into claims** → **Qwen3.5 4B, served locally through Ollama**, verifies claims **in parallel** → checks the local DB first, trusted sources only if nothing found locally → reply to user with a verdict (`verified` / `unverified` / `wrong`).

Every checklist item below ends with the file it belongs in, so there's no ambiguity about where code goes.

---

## Decisions from sync-up (2026-06-29)

Read these before starting any step — they apply globally.

- **Scope (no history for now).** The verifier processes a single user prompt → agent response → verdict cycle only. No conversation memory, no multi-turn threads. The `ollama_client.py` messages array stays single-shot. Don't build history until this is explicitly re-scoped.
- **Parallel claim checking.** All claims extracted from a response are verified in parallel inside `orchestrator.py`, not one-by-one. Dispatch `check_local_db` for every claim concurrently, then aggregate before feeding back to Qwen. Sequential claim checking doesn't scale — this is what unlocks latency.
- **Claim extraction = spaCy.** Raw agent responses are split into claims using a spaCy pipeline (sentence segmentation + noun-chunk heuristics). Output shape: `list[{claim_id: int, text: str}]`, ordered, deduplicated, dropping pure questions/interjections. Owner: **Aaditya** (lives under step 3).
- **Contribution doc per owner (one page max).** Every contributor writes `docs/contributions/<name>.md` covering: file(s) owned, one-line description per file, what each file actually does end-to-end, and how it plugs into the pipeline. One page each — keep it tight.
- **Tomorrow (2026-06-30) deadline: understand + coordinate, not code.** By tomorrow, every owner must be able to (a) explain their task in their own words, (b) name the people they depend on and what they need from them, (c) name the people who depend on them and what they'll deliver. Code timing is unconstrained — understanding and coordination are not.
- **Coordinate actively during integration.** See the matrix below. If you change a function signature or the shape of any payload, ping everyone downstream the same day — don't wait for integration to break.

## Coordination matrix

| Owner | Owns (steps) | Depends on | Consumed by |
|---|---|---|---|
| **Manish** | 1 (local DB) | Ranveer (whitelist) | Aaditya, Anay |
| **Ranveer** | 2 (trusted sources) | Manish (seed schema) | Aaditya, Anay |
| **Aaditya** | 3 (Ollama + spaCy claim extraction), 13 (Dockerfile) | Manish, Ranveer | Anay |
| **Kunal** | 4 (connector), 7 (CLI) | — | Anay |
| **Anay** | 5 (orchestrator), 9 (logging) | Aaditya, Kunal, Manish, Ranveer | Soumya |
| **Soumya** | 6 (formatter), 8 (scheduler) | Anay | end user |

Specific integration contracts — lock these early:

- **Manish ↔ Ranveer** — the trusted-source whitelist (`whitelisted_domains.json`) must align with the local-DB seed facts so `search_trusted_sources`' cache-back writes into the same schema.
- **Aaditya → Anay** — spaCy claim-extraction output is exactly `list[{claim_id, text}]`, ordered. Anay's orchestrator consumes this shape and nothing else.
- **Kunal → Anay** — orchestrator calls the connector only through `AgentConnector.send(prompt) -> raw_response`. No SDK imports in `orchestrator.py`.
- **Anay → Soumya** — the structured verdict report object emitted by step 5 must match what `reporting/formatter.py` consumes in step 6.

---

## 0. Project structure (reference this for every step below)

```
logiclayer/
├── README.md
├── plan.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── docs/
│   └── contributions/                # one-page doc per owner
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
│   │   ├── claim_extractor.py       # spaCy pipeline → list[{claim_id, text}]   (NEW — Aaditya)
│   │   ├── tools.py                 # actual Python functions behind each tool
│   │   ├── system_prompt.py         # the system prompt template fed to Qwen
│   │   └── orchestrator.py          # the agentic loop — parallel claim checking, dispatches tools, enforces gating
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
└── Dockerfile                       # required (step 13)
```

---

## 1. First, build the local database — manish

🤝 Coordinate with **Ranveer** — whitelist ↔ seed facts alignment.

- [ ] Define the `Fact` and `Source` Pydantic models (`logiclayer/knowledge_base/schema.py`)
- [ ] Create the empty folders `local-knowledge-base/facts/` and `local-knowledge-base/sources/` and seed facts
- [ ] Write the loader that reads all fact/source JSON files into SQLite (`logiclayer/knowledge_base/loader.py`)
- [ ] Write the orphan-fact checker — every fact must cite a `source_id` that exists (`logiclayer/knowledge_base/loader.py`, run as a standalone check)
- [ ] Build the embeddings index over fact text using "BAAI/bge-small-en-v1.5" (Hugging face & sentence-transformer) and manage them using FAISS (py library), stored under `local-knowledge-base/embeddings/` (`logiclayer/knowledge_base/embeddings.py`)
- [ ] Write `check_local_db(claim)` — exact match first, then embeddings fallback (`logiclayer/knowledge_base/local_check.py`)

📄 Contribution doc required: `docs/contributions/manish.md` (one page, file list + what each does).

---

## 2. Then build the trusted-source search tool — locked to the whitelist — ranveer

🤝 Coordinate with **Manish** — whitelist ↔ seed schema alignment.

- [ ] Create `logiclayer/config/whitelisted_domains.json` with the approved domains
- [ ] Write the scraper (requests + BeautifulSoup) (`logiclayer/trusted_sources/scraper.py`)
- [ ] Write `search_trusted_sources(query)` — no domain parameter in the signature, searches only the whitelist + `.gov` fallback, filters out anything not on the list before returning (`logiclayer/trusted_sources/search.py`)
- [ ] Normalize results into the same JSON evidence shape as `check_local_db`'s output
- [ ] Cache hits back into `local-knowledge-base/facts/` as new fact entries (same file, calls into `logiclayer/knowledge_base/loader.py`)(automaticaley creating the database)

📄 Contribution doc required: `docs/contributions/ranveer.md`.

---

## 3. Then set up Ollama, Qwen3.5 4B, and spaCy claim extraction — aaditya

This part needs its own attention — Ollama doesn't give you tool-calling for free, you write the loop yourself. And **spaCy is what produces the claims Qwen verifies** — the orchestrator (step 5) consumes its output directly, so the shape must be locked early.

- [ ] Install Ollama and pull the model: `ollama pull qwen3.5:4b` (check the exact tag in the Ollama library — it may differ slightly)
- [ ] Confirm it runs and responds: `ollama run qwen3.5:4b "hello"` from the terminal, no project code involved yet
- [ ] Add spaCy to dependencies: `spacy` + the `en_core_web_sm` model in `pyproject.toml` / `requirements.txt` (also pinned into the Dockerfile in step 13)
- [ ] Write `claim_extractor.py` — spaCy pipeline that takes a raw response and returns `list[{claim_id: int, text: str}]`, ordered, deduplicated, dropping pure questions / interjections (`logiclayer/verifier/claim_extractor.py`)
- [ ] Test `claim_extractor.py` standalone with 10–15 hand-written responses before wiring it into anything else — confirm the output shape is stable
- [ ] Write `ollama_client.py` — a thin wrapper that POSTs to `http://localhost:11434/api/chat` with the messages array and the `tools` schema, and returns the parsed response (`logiclayer/verifier/ollama_client.py`)
- [ ] Define the three tool schemas Ollama expects (OpenAI-style function JSON): `check_local_db`, `search_trusted_sources`, `report_verdict` — schema definitions live next to the client (`logiclayer/verifier/ollama_client.py`), the actual Python functions they map to live in `logiclayer/verifier/tools.py`
- [ ] Write the system prompt template — read the list of claims (already extracted by spaCy), call `check_local_db` for each, only call `report_verdict` once every claim has a verdict (`logiclayer/verifier/system_prompt.py`)
- [ ] Test `ollama_client.py` standalone with a throwaway script and 10–15 hand-written claims before wiring it into anything else — confirm Qwen actually calls the tools instead of answering from its own knowledge

🤝 Coordinate with **Anay** — the claim list `list[{claim_id, text}]` is the contract. Lock it before step 5's parallel loop is built against it.

📄 Contribution doc required: `docs/contributions/aaditya.md`.

---

## 4. Then build the agent connector — kunal

This is the "user prompt → API → generate text" half of the pipeline — the chatbot being checked, not the checker.

- [ ] Write the `AgentConnector` base interface: `send(prompt) -> raw_response` (`logiclayer/connectors/base.py`)
- [ ] Implement the connector for whichever chatbot/agent you're actually verifying (`logiclayer/connectors/openai_connector.py` or similarly named file per agent)
- [ ] Add the API key to `.env`, document it in `.env.example`, load it via `logiclayer/config/settings.py`

P.S. - use nvdia nim api keys for testing they are free!!

🤝 Coordinate with **Anay** — orchestrator only calls through `AgentConnector.send(...)`. No SDK imports in `orchestrator.py`.

📄 Contribution doc required: `docs/contributions/kunal.md` (covers steps 4 + 7).

---

## 5. Then build the orchestration loop — anay

This is the file that ties everything above together — the most important file in the project. **Claims are verified in parallel** — never sequentially. Per the sync-up decision, this is non-negotiable.

- [ ] Send the user's prompt through the connector from step 4 → get the raw response (`logiclayer/verifier/orchestrator.py`)
- [ ] Hand the raw response to Aaditya's `claim_extractor.py` → get `list[{claim_id, text}]`. If the list is empty, short-circuit straight to a single `report_verdict("unverified")` and stop
- [ ] Call `ollama_client.py` with the claim list, the system prompt, and only the `check_local_db` + `report_verdict` tools enabled at first
- [ ] **Verify claims in parallel** — when Qwen signals `check_local_db` calls, dispatch every claim's lookup concurrently (`asyncio.gather` or `ThreadPoolExecutor` — pick one and stick to it). Aggregate per-claim results before the next message
- [ ] When a claim's `check_local_db` comes back empty, **only that claim** gets `search_trusted_sources` added to its tool list on the next turn — this gating logic lives in `orchestrator.py`, not in the prompt, so Qwen can't skip the local check even if it wanted to. Per-claim gating is enforced in parallel.
- [ ] Execute whichever tool Qwen calls by dispatching to the real function in `logiclayer/verifier/tools.py`, feed the result back into the message history, and call Ollama again — loop until `report_verdict` has been called for every claim. **Per-claim state is held in a dict keyed by `claim_id`**, not in a single sequential history. Remember: no conversation memory across user prompts (sync-up scope decision).
- [ ] Collect all `report_verdict` calls into one structured report object (still in `orchestrator.py`)

🤝 Coordinate with **Aaditya** (claim shape), **Kunal** (`AgentConnector` interface), **Soumya** (verdict report shape).

📄 Contribution doc required: `docs/contributions/anay.md` (covers steps 5 + 9).

---

## 6. Then build the three-verdict reply — soumya

- [x] `verified` → state the claim is correct, cite the source
- [x] `unverified` → say plainly nothing in the local DB or trusted sources could confirm or deny it
- [x] `wrong` → show the original statement and Qwen's corrected version side by side, cite the source
- [ ] All three cases formatted in `logiclayer/reporting/formatter.py`, called from `orchestrator.py` right after step 5 finishes

🤝 Coordinate with **Anay** — the structured verdict report object produced in step 5 must match what `formatter.py` consumes here. Lock the shape early.

📄 Contribution doc required: `docs/contributions/soumya.md` (covers steps 6 + 8).

---

## 7. Then build the CLI — kunal

- [ ] Set up the Typer app (`logiclayer/cli/main.py`)
- [ ] `logiclayer query "<prompt>" --agent <name>` → calls connector (step 4) → orchestrator (step 5) → formatter (step 6) (`logiclayer/cli/commands/query.py`)
- [ ] `logiclayer verify <file.json>` → skips the connector, feeds a saved transcript straight into the orchestrator (`logiclayer/cli/commands/verify.py`)
- [ ] `logiclayer kb add-fact --file <fact.json>` / `logiclayer kb refresh` (`logiclayer/cli/commands/kb.py`)
- [ ] `logiclayer scheduler start` (`logiclayer/cli/commands/scheduler.py`)

📄 Contribution doc: covered by `docs/contributions/kunal.md`.

---

## 8. Then add the APScheduler refresh job — soumya

- [ ] Write `refresh_knowledge_base()` — re-validates facts/sources, re-runs `search_trusted_sources` on anything stale (`logiclayer/scheduler/jobs.py`)
- [ ] Wire it into APScheduler with a cron trigger (same file)
- [ ] Hook it up to `logiclayer scheduler start` from step 7

📄 Contribution doc: covered by `docs/contributions/soumya.md`.

---

## 9. Then add logging & metadata storage — anay

- [ ] Set up SQLite (or JSON log files) for: prompt, agent used, every tool call Qwen made, final verdicts (`logiclayer/logging/logger.py`)
- [ ] Call the logger from `orchestrator.py` after every tool call and at the end of every run — this is what lets you confirm the "only search if needed" gate is actually holding in practice

📄 Contribution doc: covered by `docs/contributions/anay.md`.

---

## 10. Then write tests — done

- [ ] `tests/test_local_check.py` — exact + embeddings matching against seeded facts
- [ ] `tests/test_trusted_sources.py` — confirm only whitelisted/`.gov` domains ever come back, even if you try to force something else
- [ ] `tests/test_orchestrator.py` — confirm `search_trusted_sources` is never called when `check_local_db` already succeeded; **confirm claims are dispatched in parallel** (not sequential); run all three verdict paths end to end
- [ ] `tests/test_cli.py` — smoke test `logiclayer query` against a mocked connector

---

## 11. Then package & clean up the repo

- [ ] `pyproject.toml` with a CLI entry point so `pip install -e .` gives you the `logiclayer` command. Must include `spacy` + a `python -m spacy download en_core_web_sm` hook (or a post-install step) so claim extraction works out of the box.
- [ ] `.gitignore` — env files, `__pycache__`, `local-knowledge-base/embeddings/*`, logs, `*.db`
- [ ] `README.md`, `CONTRIBUTING.md`, `CODEOWNERS`
- [ ] `.github/workflows/ci.yml` — lint + test on every push

---

## 13. Finally, deploy — aaditya

**Required, not optional** (per sync-up 2026-06-29). Verify it builds end-to-end before considering this step done.

- [ ] `Dockerfile` that installs the package, pulls Qwen3.5 4B through Ollama (or points at an existing Ollama instance via `OLLAMA_HOST` env var), installs spaCy + downloads the `en_core_web_sm` model, and runs the CLI/scheduler
- [ ] Decide if this stays a local dev tool or runs unattended on a server — if it's a server, Ollama needs to be running there too, not just on your laptop