# Briefing: APK_Vacation_Finder

**Projekt-ID**: `APK_Vacation_Finder`
**Pfad**: `C:\Users\mail\AI_Coworker_Claude\APK Vacation-Finder\`
**Stand**: 2026-09-17

## Was das Projekt ist

Nachbau von "Thomas Vacation Finder" (Feiertags-/Bridge-Day-/Urlaubsplanungs-Tool) als
PySide6/Qt6-Desktop-App mit Android-APK als Zielformat. Die Original-Version ist eine
React/Vite-Web-App aus Google AI Studio und liegt unveraendert als Referenz unter
`AI Google code/`.

## Zentrale Pfade

- Zentrales Python (WinPython 3.13): `Tools_Central\Python\python\python.exe`
- Geteilte PySide6-Android-Build-Toolchain: `Tools_Central\pyside6-android-deploy\`
- Native Android-SDK/Gradle-Umgebung (fuer spaetere Referenz/Wiederverwendung von SDK-Komponenten):
  aktuell noch unter `Padel Buchung\.android-build\`, geplanter Zielort `Tools_Central\Android-Build\`
- Dein Code: `BIN\versions\v0.1\PyModul\`
- Dein Feedback an Admin: `_SYNC\feedback\`
- Toolchains-Registry: `Tools_Central\_SYNC\toolchains.json`
- Projekt-Manifest: `Tools_Central\_SYNC\projects_manifest.json`

## Tech-Stack-Entscheidungen (Stand 2026-09-17)

- GUI: PySide6/Qt6 mit QtWidgets (nicht QML) -- pyside6-android-deploy unterstuetzt beides
- PySide6 wurde bewusst einmalig in die zentrale `requirements.txt` (WinPython) aufgenommen;
  PyQt5 bleibt parallel bestehen -- Qt-Binding wird pro Projekt in der PyInstaller-Spec festgelegt
- Android-Build laeuft NICHT nativ unter Windows, sondern ueber WSL2/Linux
  (Qt-eigene Empfehlung fuer `pyside6-android-deploy`)
- Feiertagsdaten: Nager.Date API + OpenHolidays API -- beide frei zugaenglich, **kein API-Key noetig**
- Gemini-KI-Chat-Feature aus dem Original wird NICHT uebernommen (kein API-Key im Client, siehe
  Sicherheitsreview des Originals)

## Naming-Schema (wie im Rest von Tools_Central)

```
APK_Vacation_Finder_YYYY-MM-DD_HH-MM_action.log
APK_Vacation_Finder_YYYY-MM-DD_HH-MM_feedback_for_admin.md
```

## Offene Punkte (Stand 2026-09-17)

1. Android NDK ist weder unter `Padel Buchung\.android-build\` noch zentral vorhanden --
   muss ueber das `pyside-setup`-Helper-Skript von `pyside6-android-deploy` geholt werden
   (nicht manuell installieren, um Versions-Mismatches zu vermeiden).
2. WSL2-Verfuegbarkeit auf diesem Rechner noch nicht bestaetigt.
3. `Tools_Central\templates\` (PROJECT_BRIEFING.md etc.) fehlt weiterhin -- diese Datei wurde
   daher freihaendig nach dem in `ADMIN.md`/`HOW_TO_START_NEW_PROJECT.md` beschriebenen Schema
   erstellt, nicht aus einer Vorlage kopiert.
