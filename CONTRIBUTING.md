# Contributing to Logic Layer

Thanks for your interest in contributing to **Logic Layer** — a universal AI masking layer that catches hallucinations before they reach the user.

This guide is written so that **even if you've never used GitHub before — and never used `pyenv` or a Python virtual environment before — you can make your first contribution today.** It covers the basic Git/GitHub workflow step by step, the Python environment setup step by step, plus the specific rules this project follows.

If you're an experienced contributor, feel free to skip Sections 1 and 1.5 and jump straight to [Section 2](#2-getting-started).

also remember to update `plan.md` and `documentation.md` and add any new requiremnets into `requiremnets.txt` before commiting any changes

---

## 1. New to GitHub? Start Here

If you already know what "fork," "branch," and "pull request" mean, skip ahead. Otherwise, here's the 5-minute version.

### 1.1 The key concepts

| Term | What it means |
|---|---|
| **Repository (repo)** | The project's folder of code, hosted on GitHub. |
| **Fork** | Your own personal copy of someone else's repo, under your GitHub account. You make changes here first. |
| **Clone** | Downloading a copy of a repo (your fork) onto your own computer so you can edit files. |
| **Branch** | A separate "lane" of work, off to the side of the main code, so your changes don't affect anything until they're reviewed and merged. |
| **Commit** | A saved snapshot of your changes, with a message describing what you did. |
| **Push** | Uploading your local commits back up to GitHub. |
| **Pull Request (PR)** | A request asking the project maintainers to review and merge your branch into the real project. |

### 1.2 The basic flow, visually

```
Fork the repo  →  Clone it locally  →  Create a branch  →  Make changes
      →  Commit changes  →  Push branch to GitHub  →  Open a Pull Request
      →  Maintainers review  →  Merged! 🎉
```

### 1.3 Step-by-step for your first contribution

**Step 1 — Fork the repo.**
On the GitHub page for this project, click the **Fork** button (top-right). This creates a copy under your own GitHub username.

**Step 2 — Clone your fork to your computer.**
```bash
git clone https://github.com/<your-username>/logic-layer.git
cd logic-layer
```

**Step 3 — Add the original project as a remote (so you can stay up to date).**
```bash
git remote add upstream https://github.com/<org>/logic-layer.git
```

**Step 4 — Create a new branch.**
Never make changes directly on `main` or `develop`. Always create a branch first:
```bash
git checkout -b feat/your-feature-name
```
(See [Section 3](#3-branch-naming-convention) below for naming rules.)

**Step 5 — Set up your Python environment.**
Before editing any Python code, set up `pyenv` and a virtual environment — see [Section 1.5](#15-new-to-pyenv-and-virtual-environments-start-here) if you've never done this, or [Section 2.3](#23-local-environment-setup) for the short version.

**Step 6 — Make your changes.**
Edit files in your code editor as needed.

**Step 7 — Check what changed.**
```bash
git status
git diff
```

**Step 8 — Stage and commit your changes.**
```bash
git add .
git commit -m "feat(verification): add contradiction-detector verdict mapping"
```
(See [Section 4](#4-commit-messages) for the message format we use.)

**Step 9 — Push your branch to your fork on GitHub.**
```bash
git push origin feat/your-feature-name
```

**Step 10 — Open a Pull Request.**
Go to your fork on GitHub. You'll see a banner suggesting you open a PR for the branch you just pushed — click it, fill out the template, and submit.

**Step 11 — Respond to review feedback.**
A maintainer will review your PR (see [Section 5.1](#51-review-expectations)). If they ask for changes, just make more commits on the same branch and push again — the PR updates automatically.

### 1.4 Useful things to know as a beginner

- **You can't break anything by branching.** `main` and `develop` stay untouched until your PR is reviewed and merged.
- **It's fine to push multiple times.** Each `git push` just updates your existing PR.
- **Pulling in updates from the original repo**, if your fork falls behind:
  ```bash
  git fetch upstream
  git checkout develop
  git merge upstream/develop
  ```
- **Stuck or made a mess?** It's okay — open an issue or ask in your PR. Everyone's first PR is a little messy.

### 1.5 New to `pyenv` and virtual environments? Start here

If you've only ever had "one Python" installed on your computer and run scripts directly, this section is for you. Two ideas, explained from scratch:

**What is `pyenv`, and why do we use it?**

Different projects often need different Python *versions*. Your computer might come with Python 3.9, but this project needs **Python 3.12.10** specifically. `pyenv` lets you install multiple Python versions side by side and pick exactly which one a given project uses, without touching or breaking the system Python your OS relies on.

**What is a virtual environment (`venv`), and why do we use it?**

A virtual environment is an isolated, project-specific folder of installed Python *packages*. Without one, every Python project on your machine shares the same global pile of installed packages — install version 2 of a library for one project and you might silently break a different project that needed version 1. A `venv` gives this project its own private package folder so nothing leaks in or out.

Put together: **`pyenv` picks the Python version, `venv` isolates the packages.** You use both, every time, for this project.

**Step-by-step, from a totally clean machine:**

1. **Install `pyenv` itself** (one-time, per computer):
   ```bash
   # macOS (Homebrew)
   brew install pyenv

   # Linux
   curl https://pyenv.run | bash
   ```
   After installing, follow the printed instructions to add `pyenv` to your shell startup file (`.bashrc`, `.zshrc`, etc.), then restart your terminal. Confirm it worked:
   ```bash
   pyenv --version
   ```

2. **Install Python 3.12.10 via `pyenv`** (one-time, per computer):
   ```bash
   pyenv install 3.12.10
   ```
   This downloads and builds that exact Python version — it does **not** replace your system Python.

3. **Pin this project to that version** (run from inside the `logic-layer` folder):
   ```bash
   cd logic-layer
   pyenv local 3.12.10
   ```
   This creates a `.python-version` file in the repo. From now on, any time your terminal is inside this folder, `python` automatically means Python 3.12.10 — no need to remember to switch it manually.

4. **Create the project's virtual environment** (one-time, per clone of the repo):
   ```bash
   python -m venv venv
   ```
   This creates a `venv/` folder containing an isolated copy of Python 3.12.10 and its own empty package list. It's already listed in `.gitignore`, so it never gets committed.

5. **Activate the virtual environment** (every time you open a new terminal to work on this project):
   ```bash
   source venv/bin/activate        # macOS/Linux
   venv\Scripts\activate           # Windows
   ```
   You'll know it worked because your terminal prompt will show `(venv)` at the start of the line. From here on, `pip install` and `python` only affect this isolated environment.

6. **Install the project's dependencies** (after activating):
   ```bash
   pip install -r middleware/requirements.txt
   ```

7. **When you're done working, deactivate** (optional, just exits the isolated environment):
   ```bash
   deactivate
   ```

**Common beginner mistakes to avoid:**

- Forgetting to `activate` the `venv` before running `pip install` — you'll end up installing packages globally instead, which is exactly what `venv` exists to prevent.
- Running `pyenv local 3.12.10` somewhere outside the `logic-layer` folder — it only pins the version for the folder (and subfolders) you ran it in.
- Committing the `venv/` folder to Git — don't; it's already gitignored, and it shouldn't ever be tracked.

---

## 2. Getting Started

### 2.1 Prerequisites

- **Python 3.12.10**, managed via `pyenv` (see [Section 1.5](#15-new-to-pyenv-and-virtual-environments-start-here) if this is new to you) — used for the FastAPI middleware, claim extraction, verification layers
- **Node.js** ≥ 18 LTS (for the UI client — browser extension + web dashboard)
- **PostgreSQL** ≥ 14 (for verdict history, metadata, logs)
- **Docker** + Docker Compose (for the local dev environment)
- **Git** ≥ 2.30
- **Make** (optional but recommended — we ship a `Makefile` with common commands)

### 2.2 Clone the repo

```bash
git clone https://github.com/<org>/logic-layer.git
cd logic-layer
```

### 2.3 Local environment setup

```bash
# Copy the env template and fill in real values
cp .env.example .env

# Pin the Python version with pyenv (writes .python-version)
pyenv install 3.12.10   # skip if you already have it installed
pyenv local 3.12.10

# Create and activate a virtual environment for the middleware
python -m venv venv
source venv/bin/activate     # (Windows: venv\Scripts\activate)
pip install -r middleware/requirements.txt

# UI client
cd ui-client
npm install
cd ..
```

If any of the `pyenv`/`venv` steps above are unfamiliar, walk through [Section 1.5](#15-new-to-pyenv-and-virtual-environments-start-here) first — it explains each command before you run it.

#### What is `.env.example` for?

`.env.example` is a **template** that lists every environment variable the project needs to run — things like database connection strings, API keys, ports, and feature flags — but with placeholder or blank values instead of real secrets.

- It exists so new contributors know exactly which variables they need to set, without anyone having to share real credentials in the repo.
- The actual file you'll use is `.env`, which you create yourself by copying the template (`cp .env.example .env`) and filling in real values for your local setup.
- `.env` is listed in `.gitignore` and should **never** be committed — it can contain real secrets (API keys, passwords, tokens). `.env.example` is safe to commit because it contains no real values.
- If you add a new environment variable while developing, add a matching placeholder entry to `.env.example` in the same PR, so other contributors know it exists.

### 2.4 Running the stack locally

```bash
docker compose up --build       # postgres + middleware + ui-client
```

For running pieces individually during development:

```bash
# Middleware (FastAPI with hot reload) — make sure venv is activated first
cd middleware
uvicorn api.main:app --reload --port 8000

# UI client
cd ui-client
npm run dev
```

---

## 3. Branch Naming Convention

Use the following prefixes so the intent of every branch is obvious at a glance:

| Prefix | Use for |
|---|---|
| `feat/` | A new feature (e.g. `feat/trusted-source-check`) |
| `fix/` | A bug fix (e.g. `fix/claim-extraction-empty-string`) |
| `chore/` | Tooling, deps, refactors with no behavior change |
| `docs/` | Documentation-only changes |
| `test/` | Adding or fixing tests only |
| `hotfix/` | Urgent production fix (branch from `main`, not `develop`) |

Branch names are kebab-case after the prefix. Keep them short and specific.

---

## 4. Commit Messages

We follow **Conventional Commits** so the changelog and release notes can be generated automatically later.

Format:

```
<type>(<scope>): <short summary>

<body — wrap at ~72 chars, explain the *why*, not the *what*>

<footer — reference issues, breaking changes>
```

Examples:

```
feat(verification): add contradiction-detector verdict mapping
fix(claim-extraction): don't drop trailing punctuation on last claim
docs(readme): clarify four-verdict output contract
```

Allowed types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `ci`.

---

## 5. Pull Request Process

1. **Branch off `develop`** for normal work, off `main` only for hotfixes.
2. **Keep PRs focused** — one logical change per PR. If a fix and a refactor are entangled, split them.
3. **Write or update tests** for any behavior change. PRs without tests will be asked to add them.
4. **Run the full local check before pushing** (with your `venv` activated):
   ```bash
   make lint
   make test
   ```
5. **Fill out the PR template** completely — context, what changed, how to test, screenshots for UI.
6. **Request the right reviewer(s)** — `CODEOWNERS` will auto-request, but check the diff actually went to the folder owner.
7. **Squash-merge** once approved and CI is green. Don't merge your own PR until at least one approval is recorded.

### 5.1 Review expectations

- First review within **2 working days**.
- Reviews focus on: correctness, edge cases, readability, test coverage, and whether the change matches the design in `README.md` / `PLAN.md`.
- We do **not** block on style nits — the linter handles that.

---

## 6. Coding Standards

### 6.1 Python (middleware, verification, scripts)

- **PEP 8** + `ruff` for formatting and import order.
- **Type hints** on all public functions. `mypy --strict` is the bar.
- **Docstrings** (Google style) on every module and public function.
- No print statements in production code — use the `logging` module.
- Tests with `pytest`. Aim for ≥ 80% line coverage on touched modules.
- All of the above assumes you're working inside the project's `venv` on Python 3.12.10 (pinned via `pyenv`) — see [Section 1.5](#15-new-to-pyenv-and-virtual-environments-start-here).

### 6.2 JavaScript / TypeScript (UI client)

- **TypeScript strict mode**, no `any` unless justified in a comment.
- **ESLint + Prettier** with the repo config.
- **React functional components + hooks.** No class components in new code.
- Component files in `PascalCase.tsx`; utilities in `camelCase.ts`.

### 6.3 Markdown (local knowledge base, docs)

- One fact per file, frontmatter at the top.
- Every fact file must have a `source:` field linking to a record in `local-knowledge-base/sources/`.
- Link related facts with relative wiki-style links: `[[python-created-by-guido]]`.

---

## 7. Local Knowledge Base Contribution Rules

The local knowledge base is **curated, not auto-generated**. Follow these rules when adding facts:

1. Every fact must be **verifiable** from a whitelisted source in `local-knowledge-base/sources/`.
2. Facts are atomic — one claim per file. Don't bundle multiple claims together.
3. Cross-link generously with `[[wiki-style]]` links.
4. Never paste facts as context into the AI agent — that's the whole point of this project. The agent never sees the KB.
5. When a fact becomes outdated, mark it `status: stale` rather than deleting it, so the audit trail stays intact.

---

## 8. Issue Reporting

- **Bug reports** → use the `.github/ISSUE_TEMPLATE/bug_report.md` template.
- **Feature requests** → use the `.github/ISSUE_TEMPLATE/feature_request.md` template.
- **Security issues** → do **not** open a public issue. Email the team lead directly (see `CODEOWNERS`).

---

## 9. Releasing

Releases follow [Semantic Versioning](https://semver.org/). Tag format: `vMAJOR.MINOR.PATCH`. The `.github/workflows/release.yml` pipeline handles version bumps, changelog generation, and Docker image publishing. Manual releases are discouraged.

---

## 10. Code of Conduct

By participating in this project you agree to keep discussions respectful, constructive, and on-topic. We're a small team building something hard — assume good intent, give feedback on the work not the person, and help each other ship.

---

## 11. Questions?

If something in this guide is unclear, open a PR against this file — documentation is part of the project. If you're brand new and just stuck on a Git command, or stuck on a `pyenv`/`venv` step, that's a great thing to ask about in your PR or in an issue — no question is too basic.
