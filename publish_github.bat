@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "GH=C:\Program Files\GitHub CLI\gh.exe"
if not exist "%GH%" set "GH=gh"

"%GH%" auth status >nul 2>&1
if errorlevel 1 (
    echo GitHub login required. Complete the browser sign-in when prompted.
    "%GH%" auth login -p https -h github.com -w
    if errorlevel 1 exit /b 1
)

for /f "delims=" %%R in ('"%GH%" repo view --json nameWithOwner -q .nameWithOwner 2^>nul') do set "REPO=%%R"
if not defined REPO (
    echo Creating public GitHub repository ...
    "%GH%" repo create BUSAKAWA_ALIEN_BATTLE2 --public --source=. --remote=origin --push
    if errorlevel 1 exit /b 1
) else (
    echo Remote repository: %REPO%
    git push -u origin main
    if errorlevel 1 exit /b 1
)

echo.
echo Enabling GitHub Pages (GitHub Actions source) ...
"%GH%" api repos/%REPO%/pages -X POST -f build_type=workflow 2>nul
if errorlevel 1 (
    "%GH%" api repos/%REPO%/pages -X PUT -f build_type=workflow 2>nul
)

echo.
echo ========================================
echo  Publish complete
echo ========================================
for /f "delims=" %%U in ('"%GH%" repo view --json url -q .url 2^>nul') do echo  Repo:   %%U
for /f "delims=" %%P in ('"%GH%" api repos/%REPO%/pages -q .html_url 2^>nul') do echo  Play:   %%P
echo.
echo  First deploy may take 3-5 minutes after push.
echo  Check: GitHub repo - Actions tab
echo.
pause
