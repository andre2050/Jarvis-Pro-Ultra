@echo off
title JARVIS Pro Ultra - Build do .EXE
echo ============================================
echo   J.A.R.V.I.S PRO ULTRA - GERADOR DO .EXE
echo ============================================
echo.
where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado! Instale em https://python.org e marque "Add to PATH".
    pause
    exit /b 1
)
echo [1/3] Instalando dependencias...
pip install requests psutil numpy sounddevice pyttsx3 SpeechRecognition pyaudio comtypes pywin32 openwakeword pyinstaller
if errorlevel 1 ( echo Falha ao instalar dependencias & pause & exit /b 1 )
echo.
echo [2/3] Compilando o JARVIS-Pro-Ultra.exe ...
pyinstaller --noconfirm --clean --onefile --windowed --name "JARVIS-Pro-Ultra" --icon assets\icon.ico --add-data "actions;actions" --add-data "config;config" --collect-all sounddevice --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 --hidden-import comtypes --hidden-import comtypes.stream --hidden-import win32com --hidden-import win32com.client main.py
if errorlevel 1 ( echo Falha no build & pause & exit /b 1 )
echo.
echo [3/3] PRONTO!
echo O arquivo JARVIS-Pro-Ultra.exe esta na pasta dist\
dist\JARVIS-Pro-Ultra.exe
pause
