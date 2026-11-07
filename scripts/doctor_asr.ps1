$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
Write-Host 'AnimeVoiceTutor Qwen3-ASR diagnostics'
Write-Host ('Project: ' + $root)
Get-ChildItem (Join-Path $root 'models') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'qwen3_asr_*' } | ForEach-Object {
    Write-Host ("Model folder: {0}, config.json: {1}" -f $_.Name, (Test-Path -LiteralPath (Join-Path $_.FullName 'config.json')))
}
try {
    & (Join-Path $root 'scripts\start_asr_local.ps1') -Mode auto -DiagnoseOnly
} catch {
    Write-Warning $_.Exception.Message
}
$log=(Join-Path $root 'data\logs\asr_stderr.log')
if (Test-Path -LiteralPath $log) {
    Write-Host "`nLast 60 ASR error log lines ($log):"
    Get-Content -LiteralPath $log -Tail 60
}
