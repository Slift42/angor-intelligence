@echo off
REM Envoie vos modifications sur GitHub (la carte en ligne se met a jour toute seule ensuite).
cd /d "%~dp0"
git add -A
git commit -m "Mise a jour %date% %time%"
git push
pause
