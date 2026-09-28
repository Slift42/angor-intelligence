@echo off
REM Envoie vos modifications sur GitHub (la carte en ligne se met a jour toute seule ensuite).
cd /d "%~dp0"
REM 1. Recuperer d abord ce que le robot a enregistre en ligne (base historique)
git pull --rebase --autostash
REM 2. Envoyer vos modifications
git add -A
git commit -m "Mise a jour %date% %time%"
git push
pause
