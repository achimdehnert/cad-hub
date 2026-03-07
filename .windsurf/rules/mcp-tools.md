---
trigger: always_on
---

# MCP Tools — Verfügbare Server & Fähigkeiten

## Aktive MCP-Server (Windsurf)

| Server | Prefix | Zweck |
|--------|--------|-------|
| **deployment-mcp** | `mcp5_*` | SSH, Docker, Git, DB, DNS, SSL, Firewall, Env, CI/CD, Cloudflare |
| **github** | `mcp8_*` | GitHub API: Issues, PRs, Repos, Branches, Files, Reviews |
| **platform-context** | `mcp12_*` | Architektur-Regeln, ADR-Compliance, banned patterns |
| **orchestrator** | `mcp11_*` | Task-Analyse, Agent-Team, Quality Gates, Audit, Deploy-Check |
| **llm-mcp** | (intern) | LLM-Calls via Groq/OpenAI/Anthropic |

> **KEIN separater `cloudflare-api` Server!**
> Cloudflare läuft komplett über **deployment-mcp**: `cloudflare_manage` (DNS/Zone/Tunnel) + `cf_access_*` (Zero Trust Access).

---

## deployment-mcp — 13 Tools, 133 Actions

Start-Script: `/home/dehnert/.local/bin/start-deployment-mcp.sh`

| Tool | Wichtigste Actions |
|------|--------------------|
| `server_manage` | create, delete, list, status, power, rebuild |
| `firewall_manage` | create, delete, list, set_rules, apply |
| `docker_manage` | compose_up/down/ps/logs/restart, container_list/exec/logs |
| `database_manage` | create, drop, backup, restore, query, migrate |
| `network_manage` | dns_record_*, dns_zone_*, ssl_*, dns_set_a, dns_set_cname |
| `cloudflare_manage` | cf_dns_*, cf_zone_*, cf_tunnel_*, cf_verify_token, cf_security_* |
| `ionos_manage` | ionos_zone_*, ionos_record_*, ionos_domain_status |
| `env_manage` | get, set, delete, secret_get/set/delete/list, validate |
| `ssh_manage` | exec, file_read, file_write, file_exists, dir_list, http_check, run_script |
| `git_manage` | status, diff, log, add, commit, push, pull, clone, checkout, branch_list |
| `system_manage` | health_check, health_dashboard, nginx_*, service_*, log_search, cron_list |
| `cicd_manage` | workflow_runs, dispatch, cancel, bfagent_deploy, canary_deploy |
| `pip_manage` | list, install, uninstall, freeze, show |

### Cloudflare Access Tools (ADR-106 FIX-A) — AKTIV ✅

| Tool | Funktion |
|------|----------|
| `cf_access_app_list` | Zero Trust Applications auflisten |
| `cf_access_app_add_hostname` | Hostname zu bestehender App hinzufügen |
| `cf_access_policy_create` | Allow-Policy per email_domain anlegen |
| `cf_access_service_token_list` | Service Tokens auflisten |
| `cf_access_service_token_create` | Neuen Service Token erstellen |

**Bekannte Access Application:**
- ID: `7ffe5703-6732-4f46-8842-883339bba22c` — "Staging Environments"
- Domains: `staging.coach-hub.iil.pet`, `staging.wedding-hub.iil.pet`
- Policy: "iil.gmbh Team" (Allow @iil.gmbh)

---

## orchestrator MCP — Tools (mcp11_*)

| Tool | Funktion |
|------|----------|
| `mcp11_analyze_task` | Task analysieren → Modell/Team/Gate empfehlen |
| `mcp11_agent_plan_task` | Task → Branches + Sub-Tasks (Planner v1/v2) |
| `mcp11_agent_team_status` | Agenten-Status, 15 Tools, Deploy-Targets |
| `mcp11_check_gate` | Prüfen ob Aktion bei aktuellem Gate erlaubt |
| `mcp11_deploy_check` | Health/Status für 9 Repos (action: targets/health/status) |
| `mcp11_get_audit_log` | Audit-Einträge abrufen |
| `mcp11_log_action` | Aktion ins Audit-Log schreiben |
| `mcp11_get_cost_estimate` | Token-Kosten schätzen |
| `mcp11_request_approval` | Gate-Approval anfordern |
| `mcp11_run_tests` | pytest für deployment_mcp/orchestrator_mcp/llm_mcp/all |
| `mcp11_run_lint` | ruff für MCP-Module |
| `mcp11_run_git` | Git auf bekannten Repos (status/diff/log/add_commit_push) |
| `mcp11_check_repos` | ADR-022 Konsistenz-Check über alle Repos |
| `mcp11_mcp_health` | Health aller MCP-Server prüfen |

**Deploy-Targets:** coach-hub, billing-hub, travel-beat, weltenhub, trading-hub, cad-hub, pptx-hub, risk-hub, ausschreibungs-hub

**Agent-Team:** Developer(Gate 1) + Tester(Gate 0) + Guardian aktiv; autonomous_developer=true

---

## platform-context MCP — Tools (mcp12_*)

| Tool | Wann |
|------|------|
| `mcp12_get_context_for_task` | **VOR jeder Code-Änderung** — Architektur-Kontext holen |
| `mcp12_check_violations` | Code-Snippet auf ADR-Verstöße prüfen |
| `mcp12_get_banned_patterns` | Verbotene Patterns für Context abrufen |
| `mcp12_get_project_facts` | Repo-Facts (settings, container, port) |

---

## Secrets & Tokens (lokal: `/home/dehnert/.secrets/`)

| Datei | Env-Variable | Verwendung |
|-------|-------------|------------|
| `hetzner_cloud_token` | `DEPLOYMENT_MCP_HETZNER_API_TOKEN` | Hetzner Cloud |
| `github_token` | `GITHUB_TOKEN` | GitHub API |
| `cloudflare_write_token` | `CLOUDFLARE_API_TOKEN` | CF DNS/Zone/Tunnel |
| `cloudflare_access_token` | `DEPLOYMENT_MCP_CLOUDFLARE_API_TOKEN` | CF Zero Trust Access |
| `ionos_api_key` | `IONOS_API_KEY` | IONOS DNS |

**CF Account ID:** `733e9e07504b6f1d63659052db27161a`

---

## Bekannte Infrastruktur

| Host | IP | Zweck |
|------|----|-------|
| Prod-Server | `88.198.191.108` | Alle Platform-Apps (Docker) |
| Odoo-Server | `46.225.127.211` | odoo.iil.pet (CPX32, Docker 27.5.1 gepinnt!) |

---

## Regeln

- PROD-Server (88.198.191.108) nur **read-only** via MCP
- Deploys über `scripts/ship.sh` oder CI/CD — nie direkt
- `mcp11_deploy_check health` nach jedem Deploy
- `mcp12_get_context_for_task` VOR Code-Änderungen
- Bei Gate 2+ Tasks: `mcp11_agent_plan_task` zur Planung

## Häufige Fallstricke

| Symptom | Ursache | Fix |
|---------|---------|-----|
| `cf_access_*` → 403 | Falscher Token | `cloudflare_access_token` nutzen, nicht `cloudflare_api_token` |
| `DEPLOYMENT_MCP_X not set` | Token-File fehlt | `/home/dehnert/.secrets/` prüfen |
| `run_command` hängt | Multi-line Python | Einzeiler oder Script-Datei nutzen |
| Tool nicht gefunden | Code-Änderung ohne Neustart | Windsurf neu starten |
