# cad-hub — Developer Makefile

.PHONY: install test test-v lint clean help dev

PYTHON := python3
PIP    := pip

help:
	@echo "Available targets:"
	@echo "  install   — pip install dependencies"
	@echo "  test      — pytest (quiet)"
	@echo "  test-v    — pytest (verbose)"
	@echo "  lint      — ruff check"
	@echo "  clean     — remove __pycache__ + .pytest_cache"
	@echo "  dev       — lokaler Dev-Server starten (platform/scripts/dev.sh)"

install:
	$(PIP) install -r requirements.txt -r requirements-test.txt

# --- injected by gen_make_test_pg.py: self-contained `make test` (PG + env) ---
# config/settings/test.py needs live Postgres + POSTGRES_* env + SECRET_KEY guard.
# Reconstructing that by hand is error-prone — use `make test`, never raw pytest.
TEST_PG_NAME := $(notdir $(CURDIR))-make-test-pg
TEST_PG_PORT := 5432
# Self-sufficient pytest lookup: prefer repo venv, fall back to module run.
# Avoids depending on a $(VENV_BIN)/$(PYTHON) convention that differs per repo.
TEST_PYTEST := $(shell [ -x .venv/bin/pytest ] && echo .venv/bin/pytest || echo "python3 -m pytest")
test: test-pg
test-pg:
	@docker rm -f $(TEST_PG_NAME) >/dev/null 2>&1 || true
	@docker run -d --rm --name $(TEST_PG_NAME) \
		-e POSTGRES_USER=test_user -e POSTGRES_PASSWORD=test_pass -e POSTGRES_DB=test_db \
		-p $(TEST_PG_PORT):5432 postgres:16-alpine >/dev/null
	@for i in $$(seq 1 30); do \
		docker exec $(TEST_PG_NAME) pg_isready -U test_user >/dev/null 2>&1 && break; sleep 1; \
	done
	@set -e; trap 'docker stop $(TEST_PG_NAME) >/dev/null 2>&1 || true' EXIT; \
		DJANGO_SETTINGS_MODULE=config.settings.test \
		SECRET_KEY="make-test-key-not-insecure-0123456789abcdef" \
		POSTGRES_USER=test_user POSTGRES_PASSWORD=test_pass POSTGRES_DB=test_db \
		POSTGRES_HOST=localhost POSTGRES_PORT=$(TEST_PG_PORT) \
		TEST_DB_USER=test_user TEST_DB_PASSWORD=test_pass TEST_DB_NAME=test_db \
		TEST_DB_HOST=localhost TEST_DB_PORT=$(TEST_PG_PORT) \
		$(TEST_PYTEST) $(if $(K),-k "$(K)",) $(if $(ARGS),$(ARGS),-q)
# --- end injected block ---
test-v:
	DJANGO_SETTINGS_MODULE=config.settings.test $(PYTHON) -m pytest --tb=short -v

lint:
	ruff check .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	@echo "Cleaned."

dev:
	bash $(HOME)/github/platform/scripts/dev.sh $(notdir $(CURDIR))

