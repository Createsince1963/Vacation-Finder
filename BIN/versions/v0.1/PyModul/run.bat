@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=C:\Users\mail\AI_Coworker_Claude\Tools_Central\Python\python\python.exe"
"%PYTHON_EXE%" main.py
if errorlevel 1 pause
