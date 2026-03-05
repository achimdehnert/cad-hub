---
description: Pflicht-Ritual vor jeder Coding-Agent-Session
---

# Agent Session Start

## Step 1: Kontext laden
```
1. docs/CORE_CONTEXT.md
2. docs/AGENT_HANDOVER.md
3. docs/adr/README.md
```

## Step 2: Aufgabe klären
- [ ] GitHub Issue vorhanden?
- [ ] ADR nötig?
- [ ] Governance-Check bei complexity >= moderate?

## Step 3: Repo syncen
// turbo
```bash
bash ~/github/platform/scripts/sync-repo.sh
```

## Step 4: Branch-Status
// turbo
```bash
git status && git log --oneline -5
```

## Step 5: Tests baseline
// turbo
```bash
pytest tests/ -q --tb=no 2>&1 | tail -5
```

## Step 6: Plan aufstellen
```
Komplexität: trivial|simple|moderate|complex
Risk: low|medium|high
```
Bei moderate+ → `/agentic-coding`

## Step 7: Session-Ende
- [ ] AGENT_HANDOVER.md aktualisiert
- [ ] Tests grün
- [ ] `bash ~/github/platform/scripts/sync-repo.sh`
