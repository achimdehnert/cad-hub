#!/bin/bash
# =============================================================================
# cad-hub ship.sh — commit + build + push + deploy in einem Schritt
# =============================================================================
# Usage:
#   ./scripts/ship.sh "feat: deine commit message"
#   ./scripts/ship.sh          # auto-generierte commit message
# =============================================================================
set -euo pipefail

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
APP_NAME="cad-hub"
IMAGE="ghcr.io/achimdehnert/cad-hub:latest"
DOCKERFILE="docker/app/Dockerfile"
WEB_SERVICE="web"
SERVER="root@88.198.191.108"
COMPOSE_PATH="/opt/cad-hub"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_URL="https://nl2cad.de/livez/"
MIGRATE_CMD="python manage.py migrate --no-input"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "   ${GREEN}✓${NC} $1"; }
warn() { echo -e "   ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "   ${RED}✗${NC} $1"; exit 1; }

# -----------------------------------------------------------------------------
# Auto-commit message
# -----------------------------------------------------------------------------
if [ -z "${1:-}" ]; then
  CHANGED=$(git -C "$REPO_DIR" diff --cached --name-only 2>/dev/null; \
            git -C "$REPO_DIR" diff --name-only; \
            git -C "$REPO_DIR" ls-files --others --exclude-standard)
  PARTS=""
  for dir in templates apps static config scripts; do
    COUNT=$(echo "$CHANGED" | grep -c "^$dir/" || true)
    [ "$COUNT" -gt 0 ] && PARTS="$PARTS $dir($COUNT)"
  done
  [ -z "$PARTS" ] && PARTS=" update"
  COMMIT_MSG="chore:$PARTS"
else
  COMMIT_MSG="$1"
fi

echo ""
echo "🚀 $APP_NAME ship — $(date '+%H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# =============================================================================
# 1. Git
# =============================================================================
echo ""
echo "📦 [1/4] Git commit + push..."
cd "$REPO_DIR"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "$COMMIT_MSG"
  ok "Committed: $COMMIT_MSG"
else
  ok "Nichts zu committen — working tree clean"
fi
git push origin main
ok "GitHub: up to date"

# =============================================================================
# 2. Docker build
# =============================================================================
echo ""
echo "🔨 [2/4] Docker build..."
docker build -f "$REPO_DIR/$DOCKERFILE" -t "$IMAGE" "$REPO_DIR"
ok "Image gebaut"

# =============================================================================
# 3. Docker push
# =============================================================================
echo ""
echo "📤 [3/4] Docker push → GHCR..."
docker push "$IMAGE"
ok "Image gepusht"

# =============================================================================
# 4. Server deploy
# =============================================================================
echo ""
echo "🖥️  [4/4] Server deploy..."
ssh "$SERVER" "
  cd $COMPOSE_PATH &&
  docker compose -f $COMPOSE_FILE pull $WEB_SERVICE &&
  docker compose -f $COMPOSE_FILE up -d --force-recreate $WEB_SERVICE
"
ok "Container neugestartet"

sleep 6
ssh "$SERVER" "
  docker compose -f $COMPOSE_PATH/$COMPOSE_FILE exec -T $WEB_SERVICE $MIGRATE_CMD 2>&1 | tail -5
" && ok "Migrationen ausgeführt" || warn "Migration check: bitte logs prüfen"

# =============================================================================
# 5. Health check (retry)
# =============================================================================
echo ""
echo "🏥 Health Check..."
MAX_RETRIES=12
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    ok "$HEALTH_URL → 200 OK"
    break
  fi
  RETRY=$((RETRY + 1))
  [ $RETRY -eq $MAX_RETRIES ] && fail "Health check fehlgeschlagen nach $MAX_RETRIES Versuchen (letzter Status: $STATUS)"
  sleep 5
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "✅ ${GREEN}Ship erfolgreich — $(date '+%H:%M:%S')${NC}"
echo ""
