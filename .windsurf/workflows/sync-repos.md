---
description: Neue Repos in mcp_config.json eintragen — filesystem MCP automatisch synchronisieren
version: "1.0"
last_reviewed: 2026-03-04
review_interval_days: 90
scope: cross-repo
---

## Was dieser Workflow tut

Ermittelt alle Verzeichnisse unter `/home/dehnert/github/`, vergleicht mit den
in `mcp_config.json` eingetragenen Pfaden und trägt fehlende Repos automatisch ein.

**Wann ausführen:**
- Nach `git clone` eines neuen Repos
- Nach Anlegen eines neuen GitHub-Repos
- Wenn Agent "Access denied" für ein Repo meldet

---

## Schritt 1 — mcp_config.json synchronisieren

// turbo
```bash
python3 /home/dehnert/github/bfagent/scripts/sync_mcp_repos.py
```

---

## Schritt 2 — Windsurf neu starten

**Pflicht** — ohne Neustart bleibt der alte MCP-Server aktiv:

> `Cmd+Shift+P` → **Reload Window**

---

## Verifikation

```bash
python3 -c "
import json
c = json.load(open('/home/dehnert/.codeium/windsurf/mcp_config.json'))
repos = [a for a in c['mcpServers']['filesystem']['args'] if '/github/' in a]
print(f'{len(repos)} Repos konfiguriert')
for r in repos: print(f'  + {r}')
"
```
