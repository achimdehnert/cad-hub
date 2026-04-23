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

test:
	DJANGO_SETTINGS_MODULE=config.settings.test $(PYTHON) -m pytest --tb=short -q

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

