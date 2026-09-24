---
title: "ADR-036: Klickdummy Bauantrag-Vorprüfung für Einreicher"
status: Accepted
date: 2026-09-23
deciders: Achim Dehnert
scope: cad-hub
conforms_to: platform:ADR-211
tags: [klickdummy]
class: mock
sunset_after: "2027-09-23"
extension_review_required: true
related: []
---

# ADR-036: Klickdummy Bauantrag-Vorprüfung für Einreicher

## Kontext

cad-hub#72 (K4) verankert ein gemeinsames Vorgangsmodell „Vorgang → Dokumente
→ Befunde" für die Sachbearbeitung. Ein Owner-Kommentar auf #72 sowie Issue
#77 erweitern den Scope: eine Behörde hat gegenüber IIL eine **zweite
Reihenfolge** vorgetragen — die Prüfung soll **vor** der verbindlichen
Einreichung stattfinden, ausgelöst vom Entwurfsverfasser/Einreicher selbst,
nicht erst nach Eingang durch die Sachbearbeitung. #77 selbst bleibt bis zum
Kill-Gate KONZ-meiki-010 (30.11.2026) und einem Herstellergespräch gesperrt
— zulässig vorher ist ausdrücklich nur, das Vorgangsmodell so zu schneiden,
dass eine Einreicher-Rolle und eine Löschfrist später ohne Umbau passen
(bereits umgesetzt in #72 K4), sowie eine **Klick-Validierung** der
Einreicher-Journey ohne echten Bau.

Fachliche Grundlage ist die Bayerische Bauvorlagenverordnung (BauVorlV)
§§ 3, 7, 8, 9: der Pflichtkatalog an Unterlagen ist **bedingt** (Verfahrensart,
Bebauungsplan-Gebiet, Erschließung, Abstandsflächenübernahme), keine feste
Liste je Verfahrensart. Diese Bedingtheit ist der Kern der Journey und lässt
sich vor jedem Code nur an einem klickbaren Stand validieren.

Dieses Repo ist **öffentlich** — der Klickdummy trägt keine Haus-, Personen-
oder Herstellernamen; die konkrete Behörde und ihre Anforderungen im Detail
bleiben in einem privaten Repo dokumentiert (Verweis nur über #77, nicht als
Pfad).

## Entscheidung

Klasse **`mock`**: kein Backend, kein `?demo=`-Parameter, alle drei
Systemgrenzen (Landes-Antragsassistent, Fachverfahren-Adapter, Prüfkern)
sind als Mocks sichtbar, nichts davon ist real verdrahtet. Kein I2-Guard
nötig (`no_backend: true` ersetzt die Prod-Guard-Frage, die nur bei
`stub-demo`/`story`/`spec-demo` entsteht).

5 Screens (v0.1; seit Revision 2 sieben — siehe unten), aus der Einreicher-Journey
abgeleitet, in Ablaufreihenfolge:

- `upload` — PDF-Satz hochladen (nur Einzel-PDF), Verfahrensart wählen,
  Bedingungen ankreuzen, Löschfrist-Hinweis, ausdrücklicher Hinweis „keine
  Einreichung"
- `sortierung` — erkannte Vorlagenart je Datei mit Konfidenz, Korrektur,
  Sammeldatei-Aufteilung
- `fehlliste` — bedingter Soll-Katalog (BauVorlV §3) gegen Ist, Status je
  Zeile (vorhanden/fehlt/unklar), Aggregatzahl per CSS-Zähler aus den Zeilen
  berechnet (kein Literal)
- `formpruefung` — Merkmale je Vorlagenart mit Vorhandensein/Konfidenz/Fundort,
  Maßstabsleiste ausdrücklich als **Anforderung der Behörde** (nicht
  BauVorlV) gekennzeichnet, Konsistenzabgleich über Dokumente, explizit
  **keine Zulässigkeitsprüfung**
- `bericht` — Hinweisliste mit Konfidenz, PDF-Download (Mock), Button
  „Weiter zum Antragsassistenten des Landes" als reine Link-Attrappe,
  Löschfrist-Erinnerung, optionale Weitergabe an die Sachbearbeitung

Zwei Personas: `entwurfsverfasser` (Einreicher, sieht alle 5 Screens) und
`sachbearbeitung` (sekundär, sieht nur `bericht`).

**Technische Umsetzung ohne Custom-JS** (Auftragsvorgabe, abweichend vom
bisherigen `projekt-ifc-upload`-Klickdummy, der Navigation per Inline-JS
löst): Screen-Wechsel über CSS `:target` (Nav-Links sind Anker `#<id>`),
die Aggregatzahl auf `fehlliste` über CSS-Zähler (`counter-increment` auf
`data-status="fehlt"`). Die einzigen `<script>`-Tags sind die
Feedback-Widget-Konfiguration und der Widget-Include selbst.

Erst-Einbindung des Feedback-Widgets in diesem Repo: `platform-snippets/klickdummy/feedback-widget/widget.js`
existierte noch nicht (der bestehende Klickdummy hat es nie eingebunden) —
per `klickdummy-install-snippets` nachgezogen, bewusst nur die
`feedback-widget/`-Datei behalten, nicht die übrigen Snippets (genesor-sync,
issue-templates u.a.), um den Diff auf das für AK7 Nötige zu beschränken.

## Konsequenzen

- Klick-Validierung der Einreicher-Journey ist möglich, bevor an #77 gebaut
  wird — Owner-Entscheidung zur Reihenfolge (Einreicher zuerst vs.
  Sachbearbeitung zuerst, #72) kann am Klickdummy geprüft werden.
- Kein Code-Risiko: `class: mock` bedeutet keine reale Route, kein reales
  Datenmodell ist von diesem PR betroffen — unabhängig von #72/PR #78.
- Die Screens sind bewusst als **eine mögliche** Umsetzung der bedingten
  BauVorlV-Logik modelliert (9 Katalogpunkte, ein Sonderbau-Szenario als
  Demo-Zustand); ein realer Bau (hinter dem Kill-Gate) kann davon abweichen,
  ohne dass dieser Klickdummy dafür Bestandsschutz beansprucht.
- `platform-snippets/klickdummy/` ist damit erstmals im Repo — künftige
  Klickdummies können den Include direkt übernehmen, ohne erneut
  `klickdummy-install-snippets` laufen zu lassen.
- Auto-Deploy-on-Merge (`deploy.yml`, kein `paths-ignore`) triggert bei einem
  Merge dieses PRs einen echten Production-Deploy von cad-hub, obwohl nur
  statische Dateien unter `klickdummy/`/`docs/`/`platform-snippets/`
  geändert werden — unkritisch (kein App-Code betroffen), aber zu wissen vor
  dem Merge.

## Revision 2 (2026-09-24) — Antragsteller-Einstieg: Vorhaben, Vorhabensnummer, Formular-Download

**Anlass (Owner, Kapitäns-Kanal 2026-09-24):** „Antragsteller geht auf LRA-Seite → eröffnet
neues Bauvorhaben (Auswahl aus Liste der Möglichkeiten), erhält Vorhabensnummer → gelangt auf
seine Vorhabensseite → Infos zum Vorhaben plus Herunterladen (im Bulk?) der Anträge →
Hochladen der Anträge → Prüfung auf Vollständigkeit … Rest ist bereits bekannt."

**Erweiterung** (`extension_review_required: true` → hier dokumentiert), Spec v0.1 → v0.2,
7 statt 5 Screens:

- `vorhaben_anlegen` (neu, Screen 1) — Seite der Bauaufsichtsbehörde: Vorhabensart aus
  **fester Liste** (kein Freitext), Verfahrensart **vorgeschlagen und änderbar** mit dem
  Hinweis „keine Rechtsauskunft", Gemeinde/Flurstück (erfunden), die drei Bedingungen
  (wandern von `upload` hierher), Button „Vorhaben anlegen". Die Vorhabensnummer
  (`BV-<Jahr>-<6 Ziffern>`) erscheint erst **nach** dem Anlegen — im Mock über den
  Anker-Sprung zur Vorhabensseite, ohne JS.
- `vorhabensseite` (neu, Screen 2, Route `/vorhaben/{vorhabensnummer}`) — Nummer, Grunddaten,
  Status (`angelegt → Unterlagen hochgeladen → vorgeprüft`; „eingereicht" wird hier **nie**
  gesetzt), der aus Vorhabensart und Bedingungen abgeleitete Katalog der Anträge/Vorlagen
  mit **Download je Formular und als ZIP-Paket** (Owner-Frage „im Bulk?" → beides; das Paket
  enthält genau den angezeigten Katalog), Wiederaufruf per Nummer mit Löschfrist, Einstieg in
  den Upload.
- `upload` — an das Vorhaben gebunden: Nummer, Verfahrensart und Bedingungen sind übernommen
  und hier **nur angezeigt** (`disabled`), Änderung auf der Vorhabensseite.
- `fehlliste` — heißt jetzt sichtbar „Vollständigkeit", trägt die Vorhabensnummer und den
  Rückweg zur Vorhabensseite (fehlende Formulare dort laden).
- `bericht` — trägt die Vorhabensnummer.
- Persona `antragsteller` (Bauherr/Bevollmächtigte) neu; sieht Vorhaben, Vorhabensseite, Upload,
  Vollständigkeit, Bericht. `entwurfsverfasser` sieht zusätzlich Sortierung und Formprüfung.

**Bewusst offen gelassen:** Wiederaufruf ohne Login nur per Nummer (kein BayernID-Bezug), weil
der Vorab-Dienst nichts Verbindliches trägt und nach Löschfrist verfällt — ob die Behörde
einen zweiten Faktor will, ist eine Frage an den Pilot; ebenso, ob die ZIP-Attrappe im echten
Bau ein serverseitig gebautes Paket oder ein Verweis auf den Formularserver des Landes wird.

**Nicht geändert:** Klasse `mock`, kein Backend, kein Custom-JS, Systemgrenzen, Löschfrist,
alle bestehenden Parity-Checks (ein Text-Update bei `upload.bedingungen_erfassbar`).

## Bezug

- `platform:ADR-211` — Klickdummy-Konvention (Rev 13)
- `cad-hub:ADR-035` — Schwester-Klickdummy `projekt-ifc-upload` (`sister_of`)
- cad-hub#72 (K4 Vorgangsmodell), cad-hub#77 (Scope-Erweiterung Einreicher-Vorprüfung)
- Bayerische Bauvorlagenverordnung (BauVorlV) §§ 3, 7, 8, 9
