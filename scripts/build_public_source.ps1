param(
    [string]$OutputPath = '',
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = $null
foreach ($rel in @('runtime\web\Scripts\python.exe', '.venv\Scripts\python.exe')) {
    $candidate = Join-Path $root $rel
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $python = $candidate; break }
}
if (-not $python) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $python = $found.Source }
}
if (-not $python) { throw 'Python not found. Run advanced\Setup AnimeVoiceTutor.cmd or install Python 3.11+.' }
$argsList = @(Join-Path $root 'tools\build_public_source.py')
if ($OutputPath) { $argsList += @('--output', $OutputPath) }
if ($SkipTests) { $argsList += '--skip-tests' }
& $python @argsList
if ($LASTEXITCODE -ne 0) { throw 'Public source export failed.' }
