$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = & (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web
if (-not $python -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Web Python runtime could not be resolved.'
}
Set-Location -LiteralPath $root
& $python -m voice_tutor serve
if ($LASTEXITCODE -ne 0) { throw "Web service exited with code $LASTEXITCODE" }
