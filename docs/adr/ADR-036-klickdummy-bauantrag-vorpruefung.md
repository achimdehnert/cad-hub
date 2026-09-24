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

5 Screens (v0.1; seit Revision 2 sieben, seit Revision 3 zehn, seit Revision 4 elf, seit Revision 5 zwölf, seit Revision 6 dreizehn — siehe
unten), aus der Einreicher-Journey abgeleitet, in Ablaufreihenfolge:

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

## Revision 3 (2026-09-24) — Feedback-Schleife: Unterlagen-Feedback, Freigabe, Bauamt, Rückmeldung, Nachbesserung

**Anlass (Owner, Kapitäns-Kanal 2026-09-24, zweiter Zuruf):** „Antragsteller lädt Unterlagen
hoch. Nach Hochladen erfolgt eine Prüfung auf Unterlagen-Ebene und ein Feedback für die
einzelne Unterlage, ob sie komplett ist oder notwendige Informationen fehlen; dann gibt der
Antragsteller Unterlagen zur Prüfung frei (Button ‚Unterlagen einreichen') → Das Bauamt prüft
und gibt ebenfalls auf Ebene der Einzelanlage Feedback; nach Abschluss erhält der Antragsteller
Nachricht und kann auf seiner Vorhabensseite das Feedback je Antragselement einsehen, die
Anträge komplettieren und erneut einreichen."

**Erweiterung**, Spec v0.2 → v0.3, 10 Screens (7 Prozess + 3 Detail):

- `unterlagen_feedback` (neu, Screen 4) — je Unterlage genau ein Status (komplett /
  unvollständig mit konkret benannten fehlenden Angaben / nicht zugeordnet), Katalogpunkte ohne
  Unterlage, Links in die Detail-Screens; Button **„Unterlagen einreichen"** = Freigabe an den
  Vorab-Dienst der Behörde (Runde 1), mit Warnung bei Lücken, aber ohne Sperre.
- `pruefung_bauamt` (neu, Screen 5, Persona `sachbearbeitung`, Login angedeutet) — automatisches
  Feedback und Bauamt-Urteil **je Einzelanlage** nebeneinander (in Ordnung / Nachbesserung /
  nicht erforderlich) mit Hinweistext; „Prüfung abschließen" beendet die Runde und
  benachrichtigt; ausdrücklich **kein Bescheid**, keine Zulässigkeit, kein Fachverfahren.
- `rueckmeldung` (neu, Screen 6) — Nachricht (E-Mail-Attrappe **ohne Prüfinhalte**), Rückmeldung
  je Antragselement, Aktionen „Ersetzen" (→ Upload) und „Ergänzen" (→ Formular auf der
  Vorhabensseite), „Erneut einreichen" = Runde 2.
- `vorhabensseite` — Statuskette erweitert (`zur_pruefung_freigegeben`, `rueckmeldung_liegt_vor`,
  `erneut_freigegeben`), Rundenzähler, Nachrichten-Verlauf mit Sprung zur Rückmeldung.
- `sortierung`, `fehlliste`, `formpruefung` werden **Detail-Screens** (Nav-Gruppe „Details"),
  aus dem Unterlagen-Feedback verlinkt; `sachbearbeitung` sieht jetzt `pruefung_bauamt` und
  `bericht`.

**Begriffsentscheidung:** Der Owner-Button heißt „Unterlagen einreichen". Weil ADR-036 §Kontext
und #77 die verbindliche Einreichung ausschließlich dem Landes-Assistenten zuweisen, trägt der
Button den Zusatz „zur Prüfung an das Bauamt freigeben", der Status heißt
`zur_pruefung_freigegeben`, und jeder betroffene Screen sagt, dass die Landes-Einreichung ein
eigener Schritt bleibt. Der Rückkanal Bauamt → Antragsteller ist damit erstmals Teil des
Klickdummys — als Vorab-Dienst, nicht als Fachverfahren (K3/K4 aus #77 bleiben getrennt).

**Offen für den Pilot:** ob das Bauamt eine Runde auch ohne Freigabe sehen darf (Einblick vor
„einreichen"), ob Nachrichten per E-Mail oder nur auf der Vorhabensseite laufen, und wie viele
Runden zulässig sind, bevor auf die verbindliche Einreichung verwiesen wird.

## Revision 4 (2026-09-24) — Abschluss K3/K4: bei Vollständigkeit Übergabe an den Landes-Assistenten

**Anlass (Owner, Kapitäns-Kanal 2026-09-24, dritter Zuruf):** „K1 mit Feedbackschleife
Einreicher–Bauamt; K3/K4 wenn vollständig → hochladen Landes-Assistent." Damit ist die
Zuordnung zu #77 festgelegt: Screens 1–6 sind **K1** (Vorprüfung mit Rückkanal), Screen 7 ist
**K3/K4** (Übergabe).

**Erweiterung**, Spec v0.3 → v0.4, 11 Screens (8 Prozess + 3 Detail):

- `uebergabe_landesassistent` (neu, Screen 7) — erreichbar erst, wenn das Bauamt jedes
  Antragselement als „in Ordnung" oder „nicht erforderlich" beurteilt hat (aus den Zeilen
  abgeleitet, kein gesetztes Flag; sonst Rückverweis in die Nachbesserung). Zeigt das Paket
  der geprüften **PDF-Einzeldateien** mit Rundenstand, den Button „Im Antragsassistenten des
  Landes einreichen" (Attrappe, BayernID dort — K3) und getrennt davon die **strukturierte
  Befund-Übergabe** an das Fachverfahren (Regel-ID, Konfidenz, Fundort, Status; Attrappe am
  Fachverfahren-Adapter — K4). Statuskette um `vollstaendig` und
  `an_landesassistent_uebergeben` ergänzt, Löschfrist nach Übergabe genannt.
- `rueckmeldung` — nennt das Ende der Schleife: vollständig → Übergabe statt weiterer Runde.

**Grenze bleibt:** Der Vorab-Dienst reicht nicht selbst ein; er übergibt in den
Landes-Assistenten, wo Anmeldung und verbindliche Einreichung liegen. Welcher Adapter die
Befunde ins Fachverfahren trägt, entscheidet das Herstellergespräch (#77 K3/K4, Rahmen).

## Revision 5 (2026-09-24) — Übersicht mehrerer Vorhaben, Reihenfolge der Vorhabensseite

**Anlass (Owner, Kapitäns-Kanal 2026-09-24, nach Sichtung des veröffentlichten KD):** „Reihenfolge
der Screens: 1. Übersicht der Vorhaben (können mehrere sein) → Vorhaben: → Grunddaten → Benötigte
Anträge und Vorlagen → Nächster Schritt → Rückmeldung des Bauamts → Nachrichten zum Vorhaben →
verbessern → Rückmeldung des Bauamts → Prüfung abschließen → Antragsteller benachrichtigen."

**Änderung**, Spec v0.4 → v0.5, 12 Screens:

- `vorhaben_uebersicht` (neu, Screen 1, Default beim Aufruf) — mehrere Vorhaben mit Status und
  nächstem Schritt, „Neues Vorhaben anlegen". Benennt als Pilotfrage: eine Übersicht braucht eine
  **Anmeldung**; Wiederaufruf per Nummer allein genügt dafür nicht.
- `vorhabensseite` — Blöcke in Owner-Reihenfolge: Grunddaten → Benötigte Anträge → Nächster
  Schritt → **Rückmeldung des Bauamts** (Kurzfassung je Element mit „Verbessern") → Nachrichten.
- `rueckmeldung` — Aktionsspalte heißt „Verbessern"; Schleife bleibt Verbessern → erneut
  einreichen → Prüfung Bauamt → „Prüfung abschließen → Antragsteller benachrichtigen" →
  Rückmeldung (nächste Runde).
- Navigation 1–8 neu nummeriert.

## Revision 6 (2026-09-24) — Eigene Prüfung in Ausbaustufen bis „Pläne auslesen", finales Hochladen an das Land

**Anlass (Owner, Kapitäns-Kanal 2026-09-24):** „Nach ‚Anträge und PDF-Satz hochladen' → eigene
Prüfung (mehrere Ausbaustufen … bis hin zu ‚Pläne auslesen') → fehlt: final an Land hochladen."

**Änderung**, Spec v0.5 → v0.6, 13 Screens:

- `unterlagen_feedback` — neuer Block „Eigene Prüfung — Ausbaustufen": **S1** Sortieren, **S2**
  Vollständigkeit + Form, **S3** Pläne auslesen, je Stufe Kurzergebnis und Link; Hinweis, dass
  spätere Stufen im Pilot abgeschaltet sein können. Stufen entsprechen cad-hub#72 (Stufe 1–3).
- `plaene_auslesen` (neu, Stufe 3) — gelesene Werte aus Lageplan/Bauzeichnungen (Flurstück,
  Maßstab, Fläche, Grenzabstände, GRZ, Geschosse) mit Konfidenz, Fundort und Abgleich gegen
  Grunddaten/Antrag; „unsicher" ist nie ein Befund; keine Zulässigkeitsprüfung.
- `upload` — zeigt die ganze Prozesskette bis „final an das Land hochladen".
- `uebergabe_landesassistent` heißt jetzt sichtbar **„Final an das Land hochladen"** (Nav 8);
  `rueckmeldung` führt mit einem eigenen Button dorthin, aktiv erst bei Vollständigkeit.
- Navigation: Detail-Gruppe heißt „Eigene Prüfung — Stufen" (S1, S2, S3).

## Bezug

- `platform:ADR-211` — Klickdummy-Konvention (Rev 13)
- `cad-hub:ADR-035` — Schwester-Klickdummy `projekt-ifc-upload` (`sister_of`)
- cad-hub#72 (K4 Vorgangsmodell), cad-hub#77 (Scope-Erweiterung Einreicher-Vorprüfung)
- Bayerische Bauvorlagenverordnung (BauVorlV) §§ 3, 7, 8, 9
