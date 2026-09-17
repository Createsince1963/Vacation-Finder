@echo off
setlocal

rem ---------------------------------------------------------------------
rem Build-APK.bat - double-click wrapper for the pyside6-android-deploy
rem cloud-build toolchain (Tools_Central\pyside6-android-deploy\).
rem
rem Just calls Build-Apk-Cloud.ps1 with this project's path, so you don't
rem have to open PowerShell and type the full command by hand every time.
rem
rem Requires (one-time setup, see the toolchain's README.md):
rem   - GitHub CLI installed and authenticated (winget install GitHub.cli,
rem     then gh auth login)
rem   - This project already pushed to GitHub at least once
rem     (git push -u origin main)
rem
rem Optional: pass a commit message as the first argument, e.g.
rem   Build-APK.bat "Fixed half-day vacation bug"
rem If you don't pass one, an uncommitted-changes check still runs - if
rem there's nothing to commit, that's fine and the build starts anyway.
rem ---------------------------------------------------------------------

set "PROJECT_PATH=%~dp0"
if "%PROJECT_PATH:~-1%"=="\" set "PROJECT_PATH=%PROJECT_PATH:~0,-1%"

set "TOOLCHAIN_SCRIPT=C:\Users\mail\AI_Coworker_Claude\Tools_Central\pyside6-android-deploy\Build-Apk-Cloud.ps1"

set "COMMIT_MSG=%~1"
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=Update %date% %time%"

echo ========================================
echo  APK Vacation Finder - Cloud APK Build
echo ========================================
echo Project:   %PROJECT_PATH%
echo Toolchain: %TOOLCHAIN_SCRIPT%
echo Commit msg: %COMMIT_MSG%
echo.

if not exist "%TOOLCHAIN_SCRIPT%" (
    echo FEHLER: Toolchain-Skript nicht gefunden unter:
    echo   %TOOLCHAIN_SCRIPT%
    echo Pruefe, ob Tools_Central am erwarteten Pfad liegt.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TOOLCHAIN_SCRIPT%" -ProjectPath "%PROJECT_PATH%" -CommitMessage "%COMMIT_MSG%"

echo.
echo ========================================
echo  Fertig (oder Fehler siehe oben).
echo ========================================
pause
