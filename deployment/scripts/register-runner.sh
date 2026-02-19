#!/bin/bash
# ===========================================================================
# register-runner.sh — GitHub Actions Runner für cad-hub registrieren
# Ausführen als: sudo bash register-runner.sh <GITHUB_PAT>
# PAT braucht: repo + admin:org Scopes (oder fine-grained: Actions: write)
# ===========================================================================
set -euo pipefail

GITHUB_PAT="${1:?Usage: sudo bash register-runner.sh <GITHUB_PAT>}"
REPO="cad-hub"
GITHUB_ORG="achimdehnert"
RUNNER_DIR="/home/github-runner/runner-achimdehnert-cad-hub"
TARBALL="/home/github-runner/actions-runner/actions-runner-linux-x64-2.331.0.tar.gz"

log()  { echo -e "\033[1;32m[RUNNER]\033[0m $*"; }
err()  { echo -e "\033[1;31m[ERR]\033[0m $*" >&2; exit 1; }

# 1. Registration token holen
log "Hole Runner-Token von GitHub..."
TOKEN=$(curl -s -X POST \
    -H "Authorization: Bearer ${GITHUB_PAT}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${GITHUB_ORG}/${REPO}/actions/runners/registration-token" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('token',''))")

[[ -z "$TOKEN" ]] && err "Token leer — PAT-Berechtigungen prüfen (repo + admin:org)"
log "Token erhalten ✓"

# 2. Runner-Verzeichnis anlegen
log "Erstelle Runner-Verzeichnis: ${RUNNER_DIR}"
mkdir -p "${RUNNER_DIR}"
[[ -f "$TARBALL" ]] || err "Tarball nicht gefunden: $TARBALL"
tar xzf "$TARBALL" -C "${RUNNER_DIR}"
chown -R github-runner:github-runner "${RUNNER_DIR}"

# 3. Runner konfigurieren
log "Konfiguriere Runner..."
sudo -u github-runner bash -c "cd '${RUNNER_DIR}' && ./config.sh \
    --url https://github.com/${GITHUB_ORG}/${REPO} \
    --token '${TOKEN}' \
    --name dev-hetzner \
    --labels 'self-hosted,hetzner,dev' \
    --work '_work' \
    --unattended \
    --replace"

# 4. Als systemd-Service installieren und starten
log "Installiere und starte Service..."
bash -c "cd '${RUNNER_DIR}' && ./svc.sh install github-runner"
bash -c "cd '${RUNNER_DIR}' && ./svc.sh start"

# 5. github-runner zur deploy-Gruppe hinzufügen (für /opt/cad-hub Zugriff)
usermod -aG deploy github-runner
log "github-runner zur deploy-Gruppe hinzugefügt"

# 6. Status prüfen
sleep 2
SERVICE=$(systemctl list-units "actions.runner.achimdehnert-cad-hub*" --no-legend | awk '{print $1}' | head -1)
if [[ -n "$SERVICE" ]]; then
    systemctl status "$SERVICE" --no-pager | tail -5
    log "Runner-Service läuft: $SERVICE"
else
    log "Service-Name prüfen: sudo systemctl list-units 'actions.runner.*'"
fi

log "═══════════════════════════════════════════════════════"
log "  Runner registriert: ${RUNNER_DIR}"
log "  Repo: https://github.com/${GITHUB_ORG}/${REPO}"
log "  Labels: self-hosted, hetzner, dev"
log "═══════════════════════════════════════════════════════"
