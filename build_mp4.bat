@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem BUSAKAWA ALIEN BATTLE2 v1.0 - MP4 splash EXE (OpenCV + splash_intro.mp4)
rem Usage:
rem   build_mp4.bat         build dist\BusakawaAlienBattle2.exe (~160MB)
rem   build_mp4.bat clean   delete cache then rebuild

echo ========================================
echo  MP4 build (video splash + OpenCV)
echo ========================================
echo.

if /I "%~1"=="clean" (
    call "%~dp0build.bat" video clean
) else (
    call "%~dp0build.bat" video %*
)

exit /b %ERRORLEVEL%
