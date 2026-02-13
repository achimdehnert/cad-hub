#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# deploy-remote.sh — Production deploy script for CAD Hub (Hetzner VM)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Called via SSH from GitHub Actions or manually on the VM.
# Handles: image pull, DB migrations, rolling restart, healthcheck, rollback.
#
# Usage:
#   deploy-remote.sh --tag <IMAGE_TAG> --app <APP_NAME> [OPTIONS]
#
# Options:
#   --tag           Docker image tag to deploy (required)
#   --app           Application name (required)
#   --compose-file  Compose file (default: docker-compose.prod.yml)
#   --env-file      Env file (default: .env.prod)
#   --deploy-dir    Deploy directory (default: /opt/<app>)
#   --web-service   Web service name in compose (default: web)
#   --skip-migrate  Skip database migrations
#   --skip-backup   Skip pre-deploy DB backup
#   --dry-run       Print actions without executing
#   --rollback-to   Rollback to a specific tag
#   --health-endpoint  Health endpoint (default: /livez/)
#
# Exit codes:
#   0 = success
#   1 = general error
#   2 = healthcheck failed (rollback attempted)
#   3 = rollback failed (manual intervention required)
#   4 = migration failed (containers NOT restarted)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ─── Defaults ────────────────────────────────────────────────────────────────
IMAGE_TAG=""
APP_NAME=""
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
DEPLOY_DIR=""
WEB_SERVICE="web"
SKIP_MIGRATE=false
SKIP_BACKUP=false
DRY_RUN=false
ROLLBACK_TO=""
HEALTH_RETRIES=12
HEALTH_INTERVAL=5
HEALTH_ENDPOINT="/livez/"

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

ts()    { date '+%Y-%m-%dT%H:%M:%S%z'; }
log()   { echo -e "${GREEN}[$(ts)]${NC} $*"; }
warn()  { echo -e "${YELLOW}[$(ts)] WARN:${NC} $*" >&2; }
err()   { echo -e "${RED}[$(ts)] ERROR:${NC} $*" >&2; }
info()  { echo -e "${BLUE}[$(ts)]${NC} $*"; }

audit() {
    local action="$1" status="$2" detail="${3:-}"
    local entry
    entry=$(printf \
        '{"ts":"%s","app":"%s","tag":"%s","action":"%s","status":"%s","detail":"%s"}' \
        "$(ts)" "$APP_NAME" "$IMAGE_TAG" "$action" "$status" "$detail")
    echo "$entry" >> "${DEPLOY_DIR}/deployments.jsonl"
}

die() { err "$1"; audit "deploy" "failed" "$1"; exit "${2:-1}"; }

# ─── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)              IMAGE_TAG="$2";         shift 2 ;;
        --app)              APP_NAME="$2";          shift 2 ;;
        --compose-file)     COMPOSE_FILE="$2";      shift 2 ;;
        --env-file)         ENV_FILE="$2";          shift 2 ;;
        --deploy-dir)       DEPLOY_DIR="$2";        shift 2 ;;
        --web-service)      WEB_SERVICE="$2";       shift 2 ;;
        --skip-migrate)     SKIP_MIGRATE=true;      shift   ;;
        --skip-backup)      SKIP_BACKUP=true;       shift   ;;
        --dry-run)          DRY_RUN=true;           shift   ;;
        --rollback-to)      ROLLBACK_TO="$2";       shift 2 ;;
        --health-retries)   HEALTH_RETRIES="$2";    shift 2 ;;
        --health-interval)  HEALTH_INTERVAL="$2";   shift 2 ;;
        --health-endpoint)  HEALTH_ENDPOINT="$2";   shift 2 ;;
        *) die "Unknown option: $1" 1 ;;
    esac
done

[[ -z "$IMAGE_TAG" ]] && die "--tag is required" 1
[[ -z "$APP_NAME" ]]  && die "--app is required" 1

DEPLOY_DIR="${DEPLOY_DIR:-/opt/${APP_NAME}}"
TAG_VAR="IMAGE_TAG"

# ─── Validate environment ───────────────────────────────────────────────────
[[ -d "$DEPLOY_DIR" ]]                     || die "Deploy dir not found: $DEPLOY_DIR" 1
[[ -f "${DEPLOY_DIR}/${COMPOSE_FILE}" ]]   || die "Compose file not found" 1
[[ -f "${DEPLOY_DIR}/${ENV_FILE}" ]]       || die "Env file not found" 1
command -v docker >/dev/null               || die "docker not found" 1
docker info >/dev/null 2>&1               || die "docker daemon not running" 1

cd "$DEPLOY_DIR"

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

log "═══════════════════════════════════════════════════════════"
log "  Deploy: ${APP_NAME}  Tag: ${IMAGE_TAG}"
log "  Dir: ${DEPLOY_DIR}  Compose: ${COMPOSE_FILE}"
log "═══════════════════════════════════════════════════════════"

# ─── 1. Save current state for rollback ──────────────────────────────────────
PREV_TAG=$(grep -oP "${TAG_VAR}=\K.*" "$ENV_FILE" 2>/dev/null || echo "unknown")
ROLLBACK_FILE="${DEPLOY_DIR}/.rollback_state"
echo "${TAG_VAR}=${PREV_TAG}" > "$ROLLBACK_FILE"
info "Previous tag: ${PREV_TAG}"

if [[ -n "$ROLLBACK_TO" ]]; then
    log "Rolling back to ${ROLLBACK_TO}..."
    IMAGE_TAG="$ROLLBACK_TO"
fi

if $DRY_RUN; then
    info "[DRY-RUN] Would set ${TAG_VAR}=${IMAGE_TAG}"
    info "[DRY-RUN] Would pull + restart ${WEB_SERVICE}"
    exit 0
fi

# ─── 2. Pre-deploy DB backup ────────────────────────────────────────────────
if ! $SKIP_BACKUP; then
    DB_CONTAINER=$(compose ps --format '{{.Names}}' 2>/dev/null \
        | grep -E '(postgres|_db)' | head -1 || true)
    if [[ -n "$DB_CONTAINER" ]]; then
        BACKUP_DIR="${DEPLOY_DIR}/backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="${BACKUP_DIR}/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
        log "Creating DB backup..."
        if docker exec "$DB_CONTAINER" \
            pg_dumpall -U "${POSTGRES_USER:-postgres}" 2>/dev/null \
            | gzip > "$BACKUP_FILE"; then
            info "Backup: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"
            audit "backup" "ok" "$BACKUP_FILE"
        else
            warn "DB backup failed — continuing (non-blocking)"
        fi
        ls -1t "${BACKUP_DIR}"/pre_deploy_*.sql.gz 2>/dev/null \
            | tail -n +11 | xargs rm -f 2>/dev/null || true
    else
        info "No postgres container found — skipping backup"
    fi
fi

# ─── 3. Update image tag in env file ────────────────────────────────────────
log "Setting ${TAG_VAR}=${IMAGE_TAG}"
if grep -q "^${TAG_VAR}=" "$ENV_FILE"; then
    sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${IMAGE_TAG}|" "$ENV_FILE"
else
    echo "${TAG_VAR}=${IMAGE_TAG}" >> "$ENV_FILE"
fi

# ─── 4. Pull new images ─────────────────────────────────────────────────────
log "Pulling images..."
compose pull "$WEB_SERVICE" || die "Image pull failed for tag ${IMAGE_TAG}" 1

# ─── 5. Run DB migrations BEFORE container switch ───────────────────────────
if ! $SKIP_MIGRATE && [[ -z "$ROLLBACK_TO" ]]; then
    log "Running migrations..."
    MIGRATE_EXIT=0
    compose run --rm --no-deps "$WEB_SERVICE" \
        python manage.py migrate --noinput 2>&1 \
        | tee /tmp/migrate.log || MIGRATE_EXIT=$?

    if [[ $MIGRATE_EXIT -ne 0 ]]; then
        err "Migration FAILED (exit code: ${MIGRATE_EXIT})"
        err "Containers NOT restarted. Investigate before retry."
        sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${PREV_TAG}|" "$ENV_FILE"
        audit "migrate" "failed" "exit=${MIGRATE_EXIT}"
        exit 4
    fi
    log "Migrations applied successfully"
    audit "migrate" "ok" ""
fi

# ─── 6. Rolling restart ─────────────────────────────────────────────────────
log "Restarting ${WEB_SERVICE}..."
compose up -d --no-deps --force-recreate "$WEB_SERVICE"

# Also restart worker if it exists
if compose ps --services 2>/dev/null | grep -q "^worker$"; then
    log "Restarting worker..."
    compose up -d --no-deps --force-recreate worker
fi

# Collect static files
WEB_CONTAINER=$(compose ps --format '{{.Names}}' "$WEB_SERVICE" 2>/dev/null \
    | head -1)
if [[ -n "$WEB_CONTAINER" ]]; then
    docker exec "$WEB_CONTAINER" \
        python manage.py collectstatic --noinput 2>/dev/null || true
fi

# ─── 7. Healthcheck loop ────────────────────────────────────────────────────
log "Waiting for healthcheck (${HEALTH_RETRIES}x${HEALTH_INTERVAL}s)..."

HEALTH_PORT=$(docker port "$WEB_CONTAINER" 8000 2>/dev/null \
    | head -1 | cut -d: -f2 || echo "")
if [[ -n "$HEALTH_PORT" ]]; then
    HEALTH_URL="http://127.0.0.1:${HEALTH_PORT}${HEALTH_ENDPOINT}"
else
    HEALTH_URL="http://127.0.0.1:8000${HEALTH_ENDPOINT}"
fi

HEALTHY=false
for i in $(seq 1 "$HEALTH_RETRIES"); do
    sleep "$HEALTH_INTERVAL"
    HTTP_CODE=$(curl -sf -o /dev/null -w '%{http_code}' \
        "$HEALTH_URL" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        log "Healthcheck PASSED (attempt ${i}/${HEALTH_RETRIES})"
        HEALTHY=true
        break
    fi
    warn "Healthcheck: HTTP ${HTTP_CODE} (attempt ${i}/${HEALTH_RETRIES})"
done

# ─── 8. Rollback on failure ─────────────────────────────────────────────────
if ! $HEALTHY; then
    err "Healthcheck FAILED after ${HEALTH_RETRIES} attempts"
    audit "healthcheck" "failed" "last_http=${HTTP_CODE}"

    if [[ "$PREV_TAG" != "unknown" && "$PREV_TAG" != "$IMAGE_TAG" ]]; then
        warn "Rolling back to ${PREV_TAG}..."
        sed -i "s|^${TAG_VAR}=.*|${TAG_VAR}=${PREV_TAG}|" "$ENV_FILE"
        compose pull "$WEB_SERVICE" || true
        compose up -d --no-deps --force-recreate "$WEB_SERVICE"

        sleep 10
        RB_CODE=$(curl -sf -o /dev/null -w '%{http_code}' \
            "$HEALTH_URL" 2>/dev/null || echo "000")
        if [[ "$RB_CODE" == "200" ]]; then
            warn "Rollback SUCCEEDED (HTTP ${RB_CODE})"
            audit "rollback" "ok" "to=${PREV_TAG}"
            exit 2
        else
            err "Rollback FAILED — MANUAL INTERVENTION REQUIRED"
            audit "rollback" "failed" "to=${PREV_TAG},http=${RB_CODE}"
            exit 3
        fi
    else
        err "No previous tag to rollback to — MANUAL INTERVENTION"
        exit 3
    fi
fi

# ─── 9. Cleanup ─────────────────────────────────────────────────────────────
docker image prune -f >/dev/null 2>&1 || true
rm -f "$ROLLBACK_FILE"

# ─── 10. Success ─────────────────────────────────────────────────────────────
audit "deploy" "ok" "from=${PREV_TAG}"
log "═══════════════════════════════════════════════════════════"
log "  DEPLOY OK: ${APP_NAME} → ${IMAGE_TAG}"
log "  Previous:  ${PREV_TAG}"
log "═══════════════════════════════════════════════════════════"
exit 0
