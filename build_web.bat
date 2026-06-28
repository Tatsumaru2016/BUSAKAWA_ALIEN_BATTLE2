@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem BUSAKAWA ALIEN BATTLE2 - Web build (pygbag)
rem Usage: build_web.bat | build_web.bat clean | build_web.bat serve

set "BUILD_MODE=build"
set "CLEAN=0"
if /I "%~1"=="clean" set "CLEAN=1"
if /I "%~1"=="serve" set "BUILD_MODE=serve"

set "PY=python"
"%PY%" -c "import sys" 2>nul
if errorlevel 1 (
    set "PY=py -3"
    "%PY%" -c "import sys" 2>nul
    if errorlevel 1 (
        echo [ERROR] Python 3.10+ not found.
        pause
        exit /b 1
    )
)
for /f "delims=" %%V in ('"%PY%" --version 2^>^&1') do echo Python: %%V
echo.

echo Installing web build dependencies...
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements-web.txt
if errorlevel 1 goto pip_failed
echo.

if "%CLEAN%"=="1" (
    echo Cleaning build/web ...
    if exist "build\web" rmdir /s /q "build\web"
    echo.
)

echo Converting SFX WAV to OGG for browser ...
"%PY%" tools\convert_sfx_to_ogg.py
if errorlevel 1 goto sfx_failed
echo.

if not exist "favicon.png" (
    if exist "assets\icon.png" (
        echo Creating favicon.png from assets\icon.png ...
        copy /Y "assets\icon.png" "favicon.png" >nul
    )
)

if "%BUILD_MODE%"=="serve" (
    echo Starting pygbag test server ...
    echo   Open http://localhost:8000 in Chrome/Edge
    echo   Debug: http://localhost:8000#debug
    echo.
    "%PY%" -m pygbag --title "Busakawa Alien Battle 2" .
    exit /b 0
)

echo Building web package ...
echo   Output: build\web\
echo.
"%PY%" -m pygbag --build --title "Busakawa Alien Battle 2" --archive .
if errorlevel 1 goto build_failed

echo.
echo ========================================
echo  Web build OK
echo ========================================
echo  Folder:  build\web\
echo  Archive: build\web.zip  (itch.io HTML upload)
echo.
echo  Local test: build_web.bat serve
echo.
pause
exit /b 0

:pip_failed
echo [ERROR] pip install failed.
pause
exit /b 1

:sfx_failed
echo [ERROR] SFX OGG conversion failed.
echo   Install ffmpeg, or: pip install imageio-ffmpeg
pause
exit /b 1

:build_failed
echo [ERROR] pygbag build failed.
pause
exit /b 1
