# Feedback: APK_Vacation_Finder -- 2026-09-17 17:05

## Anlass
User-Frage: Ist die Feiertags-Sichtbarkeits-Logik vollstaendig? Kann der User
eigene Urlaubstage verwalten (nicht nur setzen)? Bruecktentage-Logik erzeugt
zu viele falsch-positive "Gleittage".

## Befund: Bruecktentage-Bug bestaetigt und behoben
Die 1:1 aus dem Original uebernommene isBridgeDay()-Heuristik prueft pro Tag
nur den direkten Nachbartag -- dadurch wurden Tage faelschlich als Bruecktentag
markiert, die gar nicht an ein Wochenende/einen weiteren Feiertag anschliessen
(Beispiel: Feiertag Donnerstag -> Mittwoch wurde faelschlich mitmarkiert, obwohl
Dienstag ein normaler Arbeitstag ist und keine Wochenend-Verbindung entsteht).

Neu implementiert (calendar_logic.py, compute_bridge_days()): Luecken-basierte
Erkennung ueber das ganze Jahr -- nur 1..N zusammenhaengende Arbeitstage, die auf
BEIDEN Seiten an einen arbeitsfreien Block (Wochenende/Feiertag) angrenzen,
zaehlen als Bruecktentag. Mit synthetischen Testfaellen verifiziert (Wed-neben-
Donnerstag-Feiertag wird jetzt korrekt NICHT mehr markiert).

Zusaetzlich: "Max bridge gap"-Spinbox (1-3 Tage) im Toolbar ergaenzt, wie vom
User gewuenscht ("oder User-Abfrage") -- User kann die Sensitivitaet selbst
einstellen statt eine feste Regel zu bekommen.

## Befund: Urlaubsverwaltung war unvollstaendig
"Verwalten" war nur teilweise umgesetzt: Hinzufuegen (Add Vacation) funktionierte,
aber es gab keine sichtbare Liste bestehender Urlaube und keine Edit-/Remove-UI
im MainWindow (VacationDialog unterstuetzte Edit-Modus zwar strukturell, wurde
aber nie damit aufgerufen).

Ergaenzt: "Planned Vacations"-Panel (sichtbar sobald >=1 Urlaub existiert) mit
Tabelle (Name, Zeitraum, Arbeitstage, Edit-/Remove-Button pro Zeile) und
Gesamt-Arbeitstage-Anzeige inkl. Warnung bei >30 Tagen -- analog zum Original.

## Nebenbefund waehrend Tests: QThread-Absturzrisiko
Beim Headless-Testen (QT_QPA_PLATFORM=offscreen) ist aufgefallen: Schliesst
das Fenster waehrend ein Netzwerk-Fetch noch laeuft (oder kurz danach), konnte
closeEvent() auf ein bereits zerstoertes QThread-C++-Objekt zugreifen
(RuntimeError von shiboken). Behoben: Python-Referenz wird beim Thread-Ende
sauber genullt, closeEvent() zusaetzlich mit try/except abgesichert. Sauberer
Exit jetzt verifiziert (Fenster oeffnen -> Fetch laeuft -> schliessen -> kein
Crash, kein Qt-Warning mehr).

## Weiterhin offen
- Noch kein Live-Test auf dem echten Rechner mit echtem Internetzugang
  (Netzwerk in der Cloud-Sandbox geblockt, siehe vorheriges Feedback-Log)
- Suchfeld filtert Ansichten weiterhin nicht (bekannte v1-Luecke)
