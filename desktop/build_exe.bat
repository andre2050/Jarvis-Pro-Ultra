@echo off
setlocal
title J.A.R.V.I.S PRO ULTRA - Gerador do .EXE
cd /d "%~dp0"

echo ============================================
echo    J.A.R.V.I.S PRO ULTRA - GERADOR DO .EXE
echo ============================================
echo.

REM ---- [1/5] Python existe? ----
where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python nao encontrado!
    echo     Baixe em https://python.org/py e marque "Add Python to PATH".
    echo     Depois rode este arquivo de novo.
    pause & exit /b 1
)
for /f "delims=" %%v in ('python -c "import sys;print(sys.version.split()[0])"') do set PYV=%%v
echo [OK] Python %PYV% encontrado.

REM ---- [2/5] pip funciona? ----
python -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [X] pip com problema. Tentando consertar...
    python -m ensurepip --default-pip
    if errorlevel 1 ( echo Falhou. Reinstale o Python marcando "pip". & pause & exit /b 1 )
)
echo [OK] pip funcionando.

REM ---- [3/5] Dependencias ----
echo.
echo [3/5] Instalando dependencias (pode demorar na primeira vez)...
python -m pip install --quiet requests psutil numpy sounddevice pyttsx3 SpeechRecognition pyaudio comtypes pywin32 openwakeword pyinstaller
if errorlevel 1 (
    echo     Permissao negada? tentando de novo pro usuario local...
    python -m pip install --quiet --user requests psutil numpy sounddevice pyttsx3 SpeechRecognition pyaudio comtypes pywin32 openwakeword pyinstaller
    if errorlevel 1 (
        echo [X] Nao consegui instalar as dependencias.
        echo     Dica: feche o antivirus ou rode como administrador.
        pause & exit /b 1
    )
)
echo [OK] Dependencias prontas.

REM ---- [4/5] Compilar ----
echo.
echo [4/5] Compilando o JARVIS-Pro-Ultra.exe (fica pronto em ~2 min)...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "JARVIS-Pro-Ultra" --icon assets\icon.ico --add-data "actions;actions" --add-data "config;config" --collect-all sounddevice --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 --hidden-import comtypes --hidden-import comtypes.stream --hidden-import win32com --hidden-import win32com.client main.py
if errorlevel 1 (
    echo [X] O build falhou. Mande a mensagem acima pro Kaelo que ele resolve.
    pause & exit /b 1
)

REM ---- [5/5] Confirmacao ----
if not exist "dist\JARVIS-Pro-Ultra.exe" (
    echo [X] O exe nao apareceu na pasta dist. Mande o print do erro pro Kaelo.
    pause & exit /b 1
)
for /f "delims=" %%s in ('powershell -NoProfile -Command "[math]::Round((Get-Item 'dist\JARVIS-Pro-Ultra.exe').Length / 1MB)"') do set TAM=%%s
echo.
echo ============================================
echo    PRONTO, SENHOR! O JARVIS FOI COMPILADO
echo ============================================
echo    Arquivo: %cd%\dist\JARVIS-Pro-Ultra.exe
echo    Tamanho: %TAM% MB
echo.
echo    Ele e independente - nao precisa de Python
echo    instalado pra rodar. Copie pra onde quiser.
echo ============================================
echo.
choice /c SN /m "Abrir o JARVIS agora? [S/N]"
if errorlevel 2 ( start "" explorer "%cd%\dist" ) else ( start "" "%cd%\dist\JARVIS-Pro-Ultra.exe" )
pause
