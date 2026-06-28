# PowerShell から: .\build.ps1  または  .\build.ps1 clean
param(
    [switch]$Clean
)
$bat = Join-Path $PSScriptRoot "build.bat"
if ($Clean) {
    & cmd.exe /c "`"$bat`" clean"
} else {
    & cmd.exe /c "`"$bat`""
}
exit $LASTEXITCODE
