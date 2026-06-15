.DEFAULT_GOAL := help

VENV := venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help venv install seed reset-db run setup clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(VENV):  ## Create the virtual environment
	python3 -m venv $(VENV)

venv: $(VENV)  ## Alias for creating the venv

install: $(VENV)  ## Install dependencies into the venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

seed:  ## Seed the database with the event schedule
	$(PY) -m db.seed

reset-db:  ## Delete the SQLite database (drops all data) and reseed
	rm -f wellness.db wellness.db-shm wellness.db-wal
	$(PY) -m db.seed

run:  ## Start the bot
	$(PY) bot.py

setup: install seed  ## One-shot bootstrap: venv + deps + seed
	@echo ""
	@echo "Setup complete. Add your BOT_TOKEN to .env, then run: make run"

clean:  ## Remove venv, database, and caches
	rm -rf $(VENV)
	rm -f wellness.db wellness.db-shm wellness.db-wal
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
