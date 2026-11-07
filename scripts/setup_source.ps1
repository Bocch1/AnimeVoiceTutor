param(
    [ValidateSet('web','asr','tts','all')][string]$Role = 'web',
    [switch]$DryRun,
    [string]$UvPath = ''
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$roles = if ($Role -eq 'all') { @('web','asr','tts') } else { @($Role) }
$pyVersions = @{web='3.11.18';asr='3.12.16';tts='3.10.22'}
$torchBackends = @{web='cpu';asr='cu128';tts='cu128'}
if (-not [Environment]::Is64BitOperatingSystem -or [Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This installer is intended for Windows x64.'
}
foreach ($roleName in $roles) {
    $lock = Join-Path $root "release\install_specs\${roleName}_requirements.lock"
    if (-not (Test-Path -LiteralPath $lock -PathType Leaf)) { throw "Missing lock file: $lock" }
    $body = Get-Content -LiteralPath $lock -Raw -Encoding UTF8
    if ($body -notmatch '--hash=sha256:[a-f0-9]{64}') { throw "Unhashed lock: $roleName" }
    if ($body -match '(?m)^--extra-index-url\s') { throw "Unsafe unscoped index in $roleName lock" }
}
if ([string]::IsNullOrWhiteSpace($UvPath)) {
    $found = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($found) { $UvPath = $found.Source }
}
if ([string]::IsNullOrWhiteSpace($UvPath) -or -not (Test-Path -LiteralPath $UvPath -PathType Leaf)) {
    if ($DryRun) { throw 'uv.exe is missing; dry-run never installs tools.' }
    $UvPath = (& (Join-Path $PSScriptRoot 'bootstrap_uv.ps1') | Select-Object -Last 1).Trim()
    if (-not (Test-Path -LiteralPath $UvPath -PathType Leaf)) { throw 'uv bootstrap failed.' }
}
Write-Host "AnimeVoiceTutor source runtime setup: $($roles -join ', ')"
Write-Host "Source: $root"
Write-Host "uv executable: $UvPath"
if ($DryRun) { Write-Host 'DRY RUN: Python environments unchanged'; exit 0 }
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root '.installer\managed_python'
$env:UV_CACHE_DIR = Join-Path $env:LOCALAPPDATA 'AnimeVoiceTutor\uv_cache'
$env:UV_PYTHON_PREFERENCE = 'only-managed'
foreach ($roleName in $roles) {
    $pythonVersion = $pyVersions[$roleName]
    $target = Join-Path $root "runtime\$roleName"
    $pythonExe = Join-Path $target 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        & $UvPath python install $pythonVersion
        if ($LASTEXITCODE -ne 0) { throw "uv Python install failed for $roleName" }
        & $UvPath venv --python $pythonVersion --python-preference only-managed $target
        if ($LASTEXITCODE -ne 0) { throw "uv venv failed for $roleName" }
    }
    $lock = Join-Path $root "release\install_specs\${roleName}_requirements.lock"
    & $UvPath pip sync --python $pythonExe --require-hashes --index-strategy first-index --torch-backend $torchBackends[$roleName] $lock
    if ($LASTEXITCODE -ne 0) { throw "Dependency sync failed for $roleName" }
    # Use a Python script rather than -c: Windows PowerShell 5.1 can strip
    # literal double quotes from native-command arguments.
    $probe = Join-Path $PSScriptRoot 'runtime_import_probe.py'
    & $pythonExe $probe --role $roleName
    if ($LASTEXITCODE -ne 0) { throw "Import or CUDA smoke test failed for $roleName" }
    Write-Host "$roleName role installed and smoke tested."
}
Write-Host 'Python environments installed. ASR/TTS models, licensed reference audio, FFmpeg, and provider API keys are NOT included.'
