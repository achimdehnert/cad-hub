---
description: Fully Agentic Coding — Task definieren, planen, ausführen
---

# Agentic Coding Workflow

## Step 0: Governance Check
Bei complexity >= moderate: `/governance-check`

## Step 1: Task
- type: feature|bugfix|refactor|test|adr|infra
- complexity: trivial|simple|moderate|complex|architectural
- risk_level: low|medium|high|critical

## Step 2: Ausführung
1. Service Layer: views → services → models
2. Minimale Änderungen, `test_should_*`

## Step 3: Guardian
```bash
ruff check . --fix && pytest tests/ -q
```

## Step 4: PR
```bash
git checkout -b feat/ISSUE-beschreibung
git commit -m "feat(scope): desc\n\nCloses #ISSUE"
```
