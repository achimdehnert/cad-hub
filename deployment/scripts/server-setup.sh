#!/bin/bash
# ===========================================================================
# server-setup.sh — CAD Hub Server Setup (88.198.191.108)
# Run once as root or sudo-capable user on the Hetzner server
# Usage: sudo bash server-setup.sh [--github-pat <PAT>]
# ===========================================================================
set -euo pipefail

REPO="cad-hub"
GITHUB_ORG="achimdehnert"
DEPLOY_DIR="/opt/cad-hub"
RUNNER_DIR="/home/github-runner/runner-achimdehnert-cad-hub"
RUNNER_TARBALL="/home/github-runner/actions-runner/actions-runner-linux-x64-2.331.0.tar.gz"
NGINX_CONF_SRC="deployment/nginx/nl2cad.de.conf"
NGINX_CONF_DEST="/etc/nginx/sites-available/nl2cad.de"
GITHUB_PAT="${GITHUB_PAT:-}"

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --github-pat) GITHUB_PAT="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

log()  { echo -e "\033[1;32m[SETUP]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
err()  { echo -e "\033[1;31m[ERR]\033[0m $*" >&2; }

# ---------------------------------------------------------------------------
# 1. Create /opt/cad-hub deploy directory
# ---------------------------------------------------------------------------
log "Creating deploy directory: ${DEPLOY_DIR}"
mkdir -p "${DEPLOY_DIR}/staticfiles"
mkdir -p "${DEPLOY_DIR}/media"
mkdir -p "${DEPLOY_DIR}/backups"

# Copy docker-compose and nginx config from repo (if running from repo root)
if [[ -f "docker-compose.prod.yml" ]]; then
    cp docker-compose.prod.yml "${DEPLOY_DIR}/"
    log "Copied docker-compose.prod.yml"
fi
if [[ -f "${NGINX_CONF_SRC}" ]]; then
    cp "${NGINX_CONF_SRC}" "${NGINX_CONF_DEST}"
    log "Copied Nginx config to ${NGINX_CONF_DEST}"
fi

# Set permissions
chown -R deploy:deploy "${DEPLOY_DIR}"
chmod 755 "${DEPLOY_DIR}"

log "Deploy directory ready: ${DEPLOY_DIR}"

# ---------------------------------------------------------------------------
# 2. .env.prod — create from example if not exists
# ---------------------------------------------------------------------------
if [[ ! -f "${DEPLOY_DIR}/.env.prod" ]]; then
    if [[ -f ".env.prod.example" ]]; then
        cp .env.prod.example "${DEPLOY_DIR}/.env.prod"
        chown deploy:deploy "${DEPLOY_DIR}/.env.prod"
        chmod 640 "${DEPLOY_DIR}/.env.prod"
        warn ".env.prod created from example — EDIT IT NOW: ${DEPLOY_DIR}/.env.prod"
    else
        warn ".env.prod.example not found — create ${DEPLOY_DIR}/.env.prod manually"
    fi
else
    log ".env.prod already exists — skipping"
fi

# ---------------------------------------------------------------------------
# 3. Nginx setup
# ---------------------------------------------------------------------------
if [[ -f "${NGINX_CONF_DEST}" ]]; then
    NGINX_ENABLED="/etc/nginx/sites-enabled/nl2cad.de"
    if [[ ! -L "${NGINX_ENABLED}" ]]; then
        ln -s "${NGINX_CONF_DEST}" "${NGINX_ENABLED}"
        log "Nginx site enabled: nl2cad.de"
    fi
    nginx -t && systemctl reload nginx && log "Nginx reloaded"
else
    warn "Nginx config not found at ${NGINX_CONF_DEST} — copy manually"
fi

# ---------------------------------------------------------------------------
# 4. SSL — Certbot (Let's Encrypt)
# ---------------------------------------------------------------------------
if command -v certbot >/dev/null 2>&1; then
    if [[ ! -d "/etc/letsencrypt/live/nl2cad.de" ]]; then
        log "Requesting SSL certificate for nl2cad.de..."
        certbot --nginx -d nl2cad.de -d www.nl2cad.de --non-interactive --agree-tos \
            --email admin@nl2cad.de --redirect || warn "Certbot failed — run manually"
    else
        log "SSL certificate already exists"
    fi
else
    warn "certbot not installed — install with: apt install certbot python3-certbot-nginx"
fi

# ---------------------------------------------------------------------------
# 5. GitHub Actions Runner
# ---------------------------------------------------------------------------
if [[ -z "${GITHUB_PAT}" ]]; then
    warn "No --github-pat provided — skipping runner registration"
    warn "Run manually:"
    warn "  sudo bash server-setup.sh --github-pat <YOUR_PAT>"
else
    log "Registering GitHub Actions Runner for ${REPO}..."

    # Get registration token
    TOKEN=$(curl -s -X POST \
        -H "Authorization: Bearer ${GITHUB_PAT}" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${GITHUB_ORG}/${REPO}/actions/runners/registration-token" \
        | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))")

    if [[ -z "${TOKEN}" ]]; then
        err "Failed to get runner token — check PAT permissions (repo + admin:org)"
        exit 1
    fi

    # Create runner directory
    mkdir -p "${RUNNER_DIR}"
    if [[ -f "${RUNNER_TARBALL}" ]]; then
        tar xzf "${RUNNER_TARBALL}" -C "${RUNNER_DIR}"
    else
        err "Runner tarball not found: ${RUNNER_TARBALL}"
        err "Download from: https://github.com/actions/runner/releases"
        exit 1
    fi
    chown -R github-runner:github-runner "${RUNNER_DIR}"

    # Configure runner
    sudo -u github-runner bash -c "cd '${RUNNER_DIR}' && ./config.sh \
        --url https://github.com/${GITHUB_ORG}/${REPO} \
        --token '${TOKEN}' \
        --name dev-hetzner \
        --labels 'self-hosted,hetzner,dev' \
        --work '_work' \
        --unattended \
        --replace"

    # Install and start as service
    bash -c "cd '${RUNNER_DIR}' && ./svc.sh install github-runner"
    bash -c "cd '${RUNNER_DIR}' && ./svc.sh start"

    log "Runner registered and started: ${RUNNER_DIR}"
fi

# ---------------------------------------------------------------------------
# 6. Ensure github-runner is in deploy group
# ---------------------------------------------------------------------------
if id github-runner &>/dev/null; then
    usermod -aG deploy github-runner
    log "github-runner added to deploy group"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
log "═══════════════════════════════════════════════════════════"
log "  CAD Hub Server Setup Complete"
log "  Deploy dir:  ${DEPLOY_DIR}"
log "  Nginx conf:  ${NGINX_CONF_DEST}"
log "  Runner dir:  ${RUNNER_DIR}"
log "═══════════════════════════════════════════════════════════"
echo ""
warn "NEXT STEPS:"
echo "  1. Edit ${DEPLOY_DIR}/.env.prod with real values"
echo "  2. Set GitHub Secrets in repo settings:"
echo "       HETZNER_HOST=88.198.191.108  # noqa: hardcode"
echo "       HETZNER_USER=deploy"
echo "       HETZNER_SSH_KEY=<private key content>"
echo "  3. Push to main or trigger workflow_dispatch to deploy"
echo "  4. Check: https://nl2cad.de/livez/"
