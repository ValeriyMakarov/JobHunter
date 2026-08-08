@echo off

cd /d "%~dp0src"

"%~dp0.venv\Scripts\python.exe" -m jobhunter --debug

pause