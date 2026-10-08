@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Plateforme Datatym - Barometres
echo.
echo   Plateforme Datatym - automatisation des barometres
echo   Installation des dependances (premiere fois uniquement)...
python -m pip install -q -r requirements.txt
echo   Ouverture de http://127.0.0.1:8765
python app.py
pause
