@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Plateforme Datatym - Barometres
echo.
echo   Plateforme Datatym - automatisation des barometres
echo   Installation des dependances (premiere fois uniquement)...
python -m pip install -q -r requirements.txt
echo   Ouverture de http://127.0.0.1:8765
echo   Pour arreter la plateforme : fermer cette fenetre.
echo.
:demarrer
python app.py
rem Le serveur s'est arrete (erreur ou mise a jour en cours) : il redemarre tout seul.
echo.
echo   Redemarrage de la plateforme dans 3 secondes...
timeout /t 3 /nobreak >nul
set SANS_NAVIGATEUR=1
goto demarrer
