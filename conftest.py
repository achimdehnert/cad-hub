# conftest.py — root-level pytest configuration
import os

# Exclude e2e tests (require playwright) from default collection
collect_ignore_glob = ["tests/e2e/*"]
