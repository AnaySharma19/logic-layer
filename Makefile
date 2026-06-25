# Makefile — common development tasks for Logic Layer.
#
# Targets:
#   make install        — install all deps (Python + Node)
#   make lint           — ruff + eslint + markdownlint
#   make test           — pytest + vitest
#   make run            — docker compose up
#   make refresh-kb     — run scripts/db_updater.py
#   make clean          — remove caches and local artifacts
#
# Kept simple on purpose — see CONTRIBUTING.md.