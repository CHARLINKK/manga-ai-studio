@echo off
Title Assistente de Instalacao
echo Preparando dependencias da Interface do Instalador...
py -3.12 -m pip install -r requirements.txt --quiet
echo.
echo Iniciando Assistente de Instalacao...
py -3.12 setup_wizard.py
pause
