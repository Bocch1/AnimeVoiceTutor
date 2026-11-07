<#
Optional environment bootstrap. Uses the existing pinned and hashed locks.
Speech engines, trained voice weights and user media are separate assets.
The source tree, Conda installations and user credentials are not modified.
#>
param(
    [Parameter(Position=0)]
    [ValidateSet('menu', 'full', 'web', 'asr', 'tts', 'help')]
    [string]$Mode = 'menu',
    [switch]$DryRun,
    [string]$UvPath = ''
)
$ErrorActionPreference = 'Stop'

function Show-Help {
    Write-Host 'AnimeVoiceTutor | Optional quick environment setup'
    Write-Host ''
    Write-Host 'Usage:'
    Write-Host '  Quick Setup.cmd             Interactive role selection'
    Write-Host '  Quick Setup.cmd full        Web + ASR + TTS environments'
    Write-Host '  Quick Setup.cmd web         Web only (CPU, no GPU required)'
    Write-Host '  Quick Setup.cmd asr         ASR runtime only'
    Write-Host '  Quick Setup.cmd tts         TTS runtime only'
    Write-Host '  powershell -File scripts\quick_setup.ps1 -Mode full -DryRun'
    Write-Host ''
    Write-Host 'Manual installation: docs\INSTALLATION.md'
}

if ($Mode -eq 'help') { Show-Help; return }
if ($Mode -eq 'menu') {
    Show-Help
    Write-Host ''
    Write-Host 'Select what to install:'
    Write-Host '  [1] Recommended full Python environments (Web + ASR + TTS)'
    Write-Host '  [2] Web only (lightweight, CPU)'
    Write-Host '  [3] ASR only (NVIDIA CUDA 12.8)'
    Write-Host '  [4] TTS only (NVIDIA CUDA 12.8)'
    Write-Host '  [5] Cancel'
    $selection = (Read-Host 'Choice [1]').Trim()
    if ($selection -eq '') { $selection = '1' }
    switch ($selection) {
        '1' { $Mode = 'full'; break }
        '2' { $Mode = 'web'; break }
        '3' { $Mode = 'asr'; break }
        '4' { $Mode = 'tts'; break }
        '5' { Write-Host 'Cancelled. No changes made.'; return }
        default { throw 'Invalid selection. Run Quick Setup.cmd again.' }
    }
}

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$role = if ($Mode -eq 'full') { 'all' } else { $Mode }
$spec = Join-Path $root 'release\install_specs'
$needed = if ($role -eq 'all') { @('web', 'asr', 'tts') } else { @($role) }
foreach ($name in $needed) {
    if (-not (Test-Path -LiteralPath (Join-Path $spec "${name}_requirements.lock") -PathType Leaf)) {
        throw "Missing dependency lock for $name. Download the complete source archive."
    }
}
Write-Host ''
Write-Host "Selected environment roles: $($needed -join ', ')"
Write-Host 'Python: Web 3.11.18 / ASR 3.12.16 / TTS 3.10.22'
Write-Host 'Backend: Web CPU / ASR and TTS CUDA 12.8'
Write-Host 'Installation directory: runtime\<role> (inside this checkout)'
Write-Host 'Dependencies may require substantial network traffic and disk space.'
Write-Host 'The installer does NOT download models, TTS engine source, reference audio or FFmpeg.'
if ($role -ne 'web') {
    Write-Host 'The ASR/TTS roles require a compatible NVIDIA GPU and driver.'
}
if ($DryRun) { Write-Host 'DRY_RUN_OK: No tools, environments or packages were installed.'; return }
$installer = Join-Path $PSScriptRoot 'setup_source.ps1'
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Missing setup_source.ps1' }
$params = @{ Role = $role }
if (-not [string]::IsNullOrWhiteSpace($UvPath)) { $params.UvPath = $UvPath }
& $installer @params
if (-not $?) { throw 'Environment setup did not complete.' }
Write-Host ''
Write-Host 'QUICK_SETUP_COMPLETE: Python environments are ready.'
Write-Host 'Optional ASR model: Download ASR Model.cmd (0.6B by default).'
Write-Host 'Manual voice setup: docs\INSTALLATION.md and configs\README.md.'
Write-Host 'Run Doctor AnimeVoiceTutor.cmd to inspect your local configuration.'
