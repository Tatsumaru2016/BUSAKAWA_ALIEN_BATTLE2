@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem BUSAKAWA ALIEN BATTLE2 v1.0 - Windows EXE build
rem Usage: build.bat | build.bat slim | build.bat video | build.bat clean

set "EXE_NAME=BusakawaAlienBattle2"
set "SPEC_FILE=main.spec"
set "DIST_EXE=dist\%EXE_NAME%.exe"
set "SLIM_DIR=dist\%EXE_NAME%"
set "SLIM_EXE=%SLIM_DIR%\%EXE_NAME%.exe"
set "BUILD_MODE=full"
set "CLEAN=0"
set "PYCORE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"

if /I "%~1"=="clean" set "CLEAN=1"
if /I "%~1"=="slim" set "BUILD_MODE=slim"
if /I "%~1"=="video" set "BUILD_MODE=video"
if /I "%~2"=="clean" set "CLEAN=1"
if "%BUILD_MODE%"=="slim" set "SPEC_FILE=main_slim.spec"
if "%BUILD_MODE%"=="video" set "SPEC_FILE=main_video.spec"

echo ========================================
echo  BUSAKAWA ALIEN BATTLE2 v1.0 - EXE Build
echo ========================================
echo  Project: %CD%
echo  Mode:    %BUILD_MODE%
echo  Clean:   %CLEAN%
echo.

set "PY=python"
if exist "%PYCORE%" (
    "%PYCORE%" -c "import sys" 2>nul
    if not errorlevel 1 set "PY=%PYCORE%"
)
"%PY%" -c "import sys" 2>nul
if errorlevel 1 (
    set "PY=py -3.14"
    "%PY%" -c "import sys" 2>nul
    if errorlevel 1 (
        set "PY=py -3"
        "%PY%" -c "import sys" 2>nul
        if errorlevel 1 (
            echo [ERROR] Python 3.10+ not found.
            echo   Try: python --version
            echo   Or:  %PYCORE%
            pause
            exit /b 1
        )
    )
)
for /f "delims=" %%V in ('"%PY%" --version 2^>^&1') do echo Python: %%V
echo  Using: %PY%
echo.

echo Checking build dependencies...
set "NEED_PIP=0"
"%PY%" -c "import pygame" 2>nul
if errorlevel 1 set "NEED_PIP=1"
"%PY%" -c "import PyInstaller" 2>nul
if errorlevel 1 set "NEED_PIP=1"
if "%BUILD_MODE%"=="video" (
    "%PY%" -c "import cv2" 2>nul
    if errorlevel 1 set "NEED_PIP=1"
)
if "%NEED_PIP%"=="1" (
    echo Installing from requirements-build.txt ...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements-build.txt
    if errorlevel 1 goto pip_failed
)
if "%BUILD_MODE%"=="video" (
    if not exist "assets\splash_intro.mp4" (
        echo [ERROR] Missing assets\splash_intro.mp4 - required for video build
        pause
        exit /b 1
    )
)

echo Generating asset manifest...
"%PY%" tools\generate_build_assets.py
if errorlevel 1 (
    echo [ERROR] generate_build_assets.py failed
    pause
    exit /b 1
)
if not exist "%SPEC_FILE%" (
    echo [ERROR] Missing %SPEC_FILE%
    pause
    exit /b 1
)
if not exist "main.py" (
    echo [ERROR] Missing main.py
    pause
    exit /b 1
)
if not exist "assets\" (
    echo [ERROR] Missing assets folder
    pause
    exit /b 1
)
echo Dependencies OK.
echo.

if "%CLEAN%"=="1" (
    echo Cleaning build cache...
    if exist "build\" rmdir /s /q "build"
    if exist "%DIST_EXE%" del /f /q "%DIST_EXE%"
    if exist "%SLIM_DIR%" rmdir /s /q "%SLIM_DIR%"
    echo.
)

if "%BUILD_MODE%"=="slim" (
    echo Building slim onedir - assets copied beside EXE...
    echo   spec: %SPEC_FILE%
    echo   out:  %SLIM_EXE%
) else if "%BUILD_MODE%"=="video" (
    echo Building one-file EXE - assets + MP4 + OpenCV bundled...
    echo   spec: %SPEC_FILE%
    echo   out:  %DIST_EXE%
) else (
    echo Building one-file EXE - referenced assets only, logo splash...
    echo   spec: %SPEC_FILE%
    echo   out:  %DIST_EXE%
)
echo.
"%PY%" -m PyInstaller "%SPEC_FILE%" --noconfirm
if errorlevel 1 goto build_failed

if "%BUILD_MODE%"=="slim" (
    if not exist "%SLIM_EXE%" (
        echo [ERROR] EXE not created: %SLIM_EXE%
        pause
        exit /b 1
    )
    echo Copying assets from manifest...
    if not exist "%SLIM_DIR%\assets" mkdir "%SLIM_DIR%\assets"
    for /f "usebackq delims=" %%F in ("build_assets_manifest.txt") do (
        if exist "assets\%%F" copy /Y "assets\%%F" "%SLIM_DIR%\assets\" >nul
    )
    if exist "README.txt" copy /Y "README.txt" "%SLIM_DIR%\" >nul
    if exist "DISTRIBUTE.txt" copy /Y "DISTRIBUTE.txt" "%SLIM_DIR%\" >nul
    echo.
    echo ========================================
    echo  Slim build OK
    echo ========================================
    for %%A in ("%SLIM_EXE%") do echo  EXE: %%~fA  Size: %%~zA bytes
    echo  Ship folder: %SLIM_DIR%\
    echo.
    pause
    exit /b 0
)

if not exist "%DIST_EXE%" (
    echo [ERROR] EXE not created: %DIST_EXE%
    pause
    exit /b 1
)

if exist "README.txt" copy /Y "README.txt" "dist\" >nul
if exist "DISTRIBUTE.txt" copy /Y "DISTRIBUTE.txt" "dist\" >nul

echo.
echo ========================================
echo  Build OK
echo ========================================
for %%A in ("%DIST_EXE%") do echo  File: %%~fA  Size: %%~zA bytes
echo.
echo  Output: dist\%EXE_NAME%.exe
if not "%BUILD_MODE%"=="video" (
    echo  MP4 EXE:  build_mp4.bat
    echo  Slim:     build.bat slim
)
echo  Clean: build_mp4.bat clean
echo.
pause
exit /b 0

:pip_failed
echo [ERROR] pip install failed.
pause
exit /b 1

:build_failed
echo [ERROR] PyInstaller build failed.
if exist "build\main\warn-main.txt" echo  See: build\main\warn-main.txt
pause
exit /b 1
