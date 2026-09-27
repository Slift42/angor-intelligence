@echo off
REM Double-cliquez sur ce fichier : collecte les sources puis ouvre la carte.
cd /d "%~dp0"
python collecte.py
start "" "docs\index.html"
pause
