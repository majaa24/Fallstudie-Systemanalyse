@echo off
cd /d "%~dp0"
echo Wendezeit wird gestartet ...
python -m pip install -r requirements.txt --quiet
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"
python app.py
pause
