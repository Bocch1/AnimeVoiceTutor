$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $root 'scripts\start_asr_local.ps1') -Mode auto
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "ASR launcher failed with exit code $LASTEXITCODE" }
