@echo off
cd /d "%~dp0"
echo Wendezeit wird gestartet ...
rem Eigene Python-Umgebung im Ordner .venv, damit die Pakete nicht systemweit installiert werden
if not exist ".venv\Scripts\python.exe" (
    echo Beim ersten Start wird die Python-Umgebung eingerichtet, das dauert etwas ...
    python -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --disable-pip-version-check
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"
".venv\Scripts\python.exe" app.py
pause
