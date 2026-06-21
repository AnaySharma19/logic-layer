# Logic Layer

**A local, CLI-based fact-checking layer that catches hallucinations before they reach the user.**

Maintained by **Team ReBinders**

---

## 1. The Problem

AI agents hallucinate. They generate confident, fluent, well-structured answers that are sometimes simply false. The industry-standard fix today — Retrieval Augmented Generation / "feeding the AI factual data" — helps, but it doesn't solve the problem. The facts still pass *through* the model, and the model can still distort, misattribute, or fabricate on top of them. The hallucination rate goes down. It never goes to zero.

## 2. Our Solution

Logic Layer is a CLI tool that sits *outside* the AI agent, between the agent and the user.

Every response the agent generates is intercepted before the user sees it, checked against facts, and only released once it passes verification — or clearly labeled if it can't be verified.

**The key design choice:** the checking is done by a separate, small local model — **Qwen3.5 4B, served through Ollama** — not by the agent itself, and not by feeding factual data into the agent as context. The checker reads the agent's output, looks things up, and decides. It never sees the reference data paraphrased or "creatively interpreted" by the agent being checked — that's what separates Logic Layer from the standard RAG approach.

## 3. How It Works

### 3.1 The Big Picture

```
User
  |
  | (1) prompt, via CLI
  v
Agent Connector ----> Target AI Agent (any agent with an API)
  |
  | (2) raw response
  v
Qwen3.5 4B (via Ollama) ---- tool calls ---- Local JSON/SQLite DB
  |                                                |
  | (3) if nothing found locally...                |
  v                                                v
  ------------------------> Trusted Source Search (whitelist + .gov only)
  |
  | (4) verdict per claim: verified / unverified / wrong
  v
CLI ----> reply shown to the user
```

The checker is **agent-agnostic** — it doesn't matter which AI model produced the response being checked. It works as a layer on top of any agent that exposes an API.

### 3.2 One Model Does the Whole Job

Earlier designs split this into separate stages — a claim extractor, a local lookup, a trusted-source lookup, and a dedicated contradiction-detection model. That's gone. Qwen3.5 4B does all of it in one agentic loop:

1. Reads the raw response.
2. Identifies the claims worth checking.
3. Calls a `check_local_db` tool for each one.
4. If nothing comes back, calls a `search_trusted_sources` tool.
5. Calls a `report_verdict` tool with its conclusion for each claim.

No spaCy, no separate NLI classifier — one small model, given the right tools, does the extraction *and* the judgment.

### 3.3 Local First, Trusted Sources Only If Needed

The model is never allowed to search the open web. Two things enforce this, not just a prompt instruction:

- The search tool itself has no parameter for picking a site — it only ever searches a fixed whitelist of domains, falling back to `.gov` if nothing else matches. Anything outside that list is filtered out before the model ever sees it.
- The orchestrator (the code coordinating the model, not the model itself) only makes the trusted-source tool *available* to Qwen after the local check has already come back empty for that claim. The model can't reach for the web tool early even if it wanted to — it isn't offered the option until the local DB has had its turn.

### 3.4 Three Verdicts

- **Verified** — the claim matches local or trusted-source evidence; source is cited.
- **Wrong** — the claim contradicts the evidence; the original statement and the correct one are shown side by side, with the source.
- **Unverified** — no evidence found anywhere, locally or in trusted sources; flagged plainly so the user knows to be careful, instead of being silently passed through as true.

### 3.5 The Local Knowledge Base

The local knowledge base is a flat, JSON-based fact store, loaded into SQLite for fast lookup:

- Each fact is its own JSON file: a claim, a value, and a `source_id`.
- Every fact must cite a source that actually exists — there are no orphan facts.
- A FAISS index sits over the fact text so lookups aren't limited to exact keyword matches.
- New facts get added automatically whenever a trusted-source search finds something the local DB didn't have — the next identical claim hits the cheap local check instead of the web.
- The whole thing is refreshed on a schedule (via APScheduler), not built once and left to go stale.

### 3.6 Why the Local Check Comes First

It's the fastest and cheapest layer — no model call, no web request — so it absorbs as much of the verification load as possible before falling back to the trusted-source search, which is slower and rate-limited.

## 4. Differentiation Summary

1. The checking model never sees the agent's output paraphrased through a RAG-style context window — it independently looks things up after the fact.
2. One small local model (Qwen3.5 4B) handles claim identification, lookup, and judgment — no separate extraction or contradiction-detection models to maintain.
3. Trusted-source access is locked down architecturally (tool signature + orchestrator gating), not just by asking the model nicely.
4. Three honest verdicts, including an explicit "we don't know" state, instead of a binary true/false.
5. `Wrong` verdicts always show the incorrect statement and the correct one side by side — not just a flag.
6. Runs entirely as a CLI, fully local — no browser extension, no dashboard, no GUI dependency.
7. Works as a layer on top of *any* AI agent — not tied to one model or vendor.

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Language / runtime | **Python 3.12.11**, pinned via `pyenv local 3.12.11`, isolated in a project `venv` |
| Verifier model | Qwen3.5 4B, served locally via **Ollama** |
| CLI | Python, **Typer** |
| Agent connectors | REST/HTTP adapters per target AI agent's API |
| Local facts database | JSON fact files, loaded into **SQLite** |
| Semantic lookup | **FAISS** |
| Trusted source verification | Whitelisted-domain search + scraping (`requests`, `BeautifulSoup`), `.gov` fallback |
| Metadata / logs | SQLite (or JSON log files) |
| Source/DB refresh scheduler | **APScheduler** (cron-style, in-process) |
| Containerization / deployment | Docker (optional) |

## 6. Project Structure

```
logic-layer/
├── README.md
├── plan.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── logiclayer/
│   ├── cli/                     # Typer app + commands (query, verify, kb, scheduler)
│   ├── connectors/               # per-agent API adapters
│   ├── verifier/                  # Ollama client, tool definitions, system prompt, orchestrator
│   ├── knowledge_base/            # schema, loader, local check, FAISS embeddings
│   ├── trusted_sources/           # whitelist search + scraper
│   ├── scheduler/                 # APScheduler refresh job
│   ├── reporting/                  # verdict → reply formatting
│   ├── logging/                    # query + tool-call logs
│   └── config/                     # settings, whitelisted domains
├── local-knowledge-base/
│   ├── facts/                      # one JSON file per fact
│   ├── sources/                    # one JSON file per source
│   └── embeddings/                  # FAISS index, gitignored
├── tests/
└── docs/
```

See [`build-plan.md`](./logic-layer-build-plan.md) for the file-by-file build order.

## 7. Getting Started

### 7.1 Environment Setup

This project targets **Python 3.12.11**. Pin and isolate it before installing anything:

```bash
# 1. Pin the project's Python version with pyenv
pyenv install 3.12.11   # skip if already installed
pyenv local 3.12.11     # writes .python-version in the repo root

# 2. Create and activate a virtual environment using that pinned version
python -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate
```

All commands below assume this venv is active.

### 7.2 Install and Run

```bash
# 1. Install and run Ollama, then pull the verifier model
ollama pull qwen3.5:4b

# 2. Install the project
pip install -e .

# 3. Try it
logiclayer query "Python was created by Guido van Rossum and released in 1991" --agent <name>
```

**For development/testing:** NVIDIA NIM offers free API keys, which work well for standing up an agent connector to test the pipeline end to end without paying for a target-agent API while you're still building.

## 8. Roadmap

See [`plan.md`](./plan.md) and [`logic-layer-build-plan.md`](./logic-layer-build-plan.md) for phases, task breakdown, and open risks.

## 9. Team

**Team ReBinders**