#!/bin/bash
# Thin-wrapper — delegiert an platform/scripts/ship.sh
# Config: .ship.conf im Repo-Root
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM_SHIP="$(cd "$REPO_DIR/../platform/scripts" && pwd)/ship.sh"
if [ ! -f "$PLATFORM_SHIP" ]; then
  echo "ERROR: $PLATFORM_SHIP nicht gefunden." >&2
  exit 1
fi
exec bash "$PLATFORM_SHIP" --repo "$REPO_DIR" "${@}"
