# Cursor globalStorage/state.vscdb の肥大化を整理する（要: Cursor 完全終了）
# チャット UI の履歴キャッシュを削除し VACUUM。設定は基本的に維持。
# 使い方: Cursor を終了 → PowerShell で:
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   .\scripts\cursor_cleanup_state_db.ps1

$ErrorActionPreference = "Stop"
$dbDir = Join-Path $env:APPDATA "Cursor\User\globalStorage"
$dbPath = Join-Path $dbDir "state.vscdb"

if (-not (Test-Path $dbPath)) {
    Write-Error "見つかりません: $dbPath"
}

$cursor = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursor) {
    Write-Host "Cursor が起動中です（$($cursor.Count) プロセス）。完全終了してから再実行してください。" -ForegroundColor Red
    exit 1
}

$sqlite = Get-Command sqlite3 -ErrorAction SilentlyContinue
if (-not $sqlite) {
    Write-Host "sqlite3 がありません。次を実行してから再試行:" -ForegroundColor Yellow
    Write-Host "  winget install SQLite.SQLite"
    exit 1
}

$mbBefore = [math]::Round((Get-Item $dbPath).Length / 1MB, 1)
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $dbDir "state.vscdb.backup-$stamp"
Write-Host "バックアップ: $backup ($mbBefore MB) ..."
Copy-Item $dbPath $backup

$sql = @"
PRAGMA journal_mode=DELETE;
BEGIN IMMEDIATE;
DELETE FROM cursorDiskKV WHERE key LIKE 'agentKv:%';
DELETE FROM cursorDiskKV WHERE key LIKE 'bubbleId:%';
DELETE FROM cursorDiskKV WHERE key LIKE 'checkpointId:%';
DELETE FROM cursorDiskKV WHERE key LIKE 'composerData:%';
COMMIT;
VACUUM;
"@

Write-Host "キャッシュキーを削除して VACUUM 中..."
$sql | & sqlite3 $dbPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "失敗しました。バックアップから復元:" -ForegroundColor Red
    Write-Host "  Copy-Item '$backup' '$dbPath' -Force"
    exit $LASTEXITCODE
}

$mbAfter = [math]::Round((Get-Item $dbPath).Length / 1MB, 1)
Write-Host "完了: ${mbBefore} MB -> ${mbAfter} MB" -ForegroundColor Green
Write-Host "Cursor を起動してください。チャット一覧は空になる場合があります（エージェントログは ~/.cursor/projects/ に残ることがあります）。"
