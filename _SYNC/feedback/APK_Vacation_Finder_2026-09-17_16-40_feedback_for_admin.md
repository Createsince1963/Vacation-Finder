# Feedback: APK_Vacation_Finder -- 2026-09-17 16:40

## Status
v0.1-dev PySide6/Qt6 desktop scaffold complete and smoke-tested (headless Qt run,
offscreen platform, no crashes across Year/Month/List views; Excel + iCal export
verified against sample data).

## Was umgesetzt wurde
- constants.py, models.py: 1:1 Datenbasis aus dem Original (98 Laender, Jahre 2020-2030)
- api_client.py: Nager.Date + OpenHolidays API Clients, kein API-Key, mit Timeout und
  Fehlerbehandlung (gibt bei Netzwerkfehler leere Liste statt Absturz zurueck)
- calendar_logic.py: Wochennummer, Bridge-Day-Erkennung (bis 2 Tage), Arbeitstage-
  Berechnung -- reine, testbare Funktionen ohne Qt-Abhaengigkeit
- storage.py: Urlaube als JSON im App-Datenverzeichnis (ersetzt localStorage), mit
  Fehlerbehandlung fuer korrupte/fehlende Dateien (Bug aus dem Original behoben)
- export.py: Excel- (openpyxl) und iCal-Export (stdlib-only ICS-Writer, keine
  Zusatzabhaengigkeit) -- Bugfix ggue. Original: Vacation/School-Holiday-Tage werden
  jetzt korrekt kategorisiert statt faelschlich als "Weekend" exportiert
- workers.py: Netzwerk-Fetch in QThread, damit die UI beim Laden nicht einfriert
- vacation_dialog.py, main_window.py, main.py: vollstaendige QtWidgets-Oberflaeche
  (Jahr-/Monats-/Listenansicht, Filter, Laendervergleich, Urlaubsverwaltung)

## Bewusst nicht uebernommen
- Gemini-KI-Chat-Assistent (kein API-Key im Client -- siehe Sicherheitsreview des
  Originals)

## Getestet
- `python -m py_compile` auf allen Modulen: OK
- Headless-Start (QT_QPA_PLATFORM=offscreen) inkl. Event-Loop: MainWindow baut sich
  fehlerfrei auf, alle drei Ansichten rendern ohne Absturz
- Netzwerk-Calls schlagen in der Cloud-Sandbox erwartungsgemaess fehl (Egress-Proxy
  blockiert date.nager.at/openholidaysapi.org) -- auf dem echten Rechner mit normalem
  Internetzugang sollte das funktionieren, wurde dort aber noch NICHT verifiziert
- Excel- und iCal-Export gegen Beispieldaten verifiziert (gueltige Dateien, korrekte
  Kategorisierung)

## Offene Punkte / naechste Schritte
1. Live-Test auf dem echten Rechner (Netzwerk, echte Feiertagsdaten, UI-Optik) noch
   nicht durchgefuehrt -- bitte `run.bat` im PyModul-Ordner ausfuehren
2. Suchfeld (search_edit) ist verdrahtet, filtert aber die Ansichten noch nicht --
   im Original nur als separates "Search Results"-Panel unterhalb der Kalenderansicht
   umgesetzt; hier als v1-Lueke dokumentiert statt verschwiegen
3. Android-APK-Build (pyside6-android-deploy) noch nicht begonnen -- WSL2-Verfuegbarkeit
   auf diesem Rechner noch zu pruefen
4. requirements-build.txt liegt bei, alle Abhaengigkeiten sind bereits zentral vorhanden
