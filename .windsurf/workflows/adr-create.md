---
description: Neuen ADR anlegen mit automatischer Nummerierung und Standardstruktur
version: "1.0"
last_reviewed: 2026-03-06
review_interval_days: 90
scope: cross-repo
---

Inputs: Titel (kurz), Kontext-Beschreibung.

1. Nächste ADR-Nummer ermitteln:
   // turbo
   ```bash
   ls docs/adr/ADR-0*.md | sort -t- -k2 -n | tail -1
   ```
   Höchste Nummer + 1 nehmen.

2. Dateiname generieren: `ADR-{NNN}-{titel-kebab-case}.md`

3. ADR-Datei mit diesem Template anlegen:

   ```markdown
   # ADR-{NNN}: {Titel}

   | Metadata | Value |
   |----------|-------|
   | **Status** | Proposed |
   | **Date** | {heute YYYY-MM-DD} |
   | **Author** | Achim Dehnert |
   | **Reviewers** | — |
   | **Supersedes** | — |
   | **Related** | {verwandte ADRs aus Kontext erkennen} |

   ---

   ## 1. Kontext und Problemstellung
   {Nutzer-Kontext}

   ## 2. Entscheidung
   {Auszufüllen}

   ## 3. Implementierung
   {Auszufüllen}

   ## 4. Konsequenzen
   ### 4.1 Positiv
   ### 4.2 Negativ
   ### 4.3 Mitigation

   ## 5. Changelog
   | Date | Author | Change |
   |------|--------|--------|
   | {heute} | Achim Dehnert | Initial draft |
   ```

4. Datei zur Bearbeitung öffnen.

5. Ausgabe: "ADR-{NNN} erstellt: docs/adr/{filename}"
