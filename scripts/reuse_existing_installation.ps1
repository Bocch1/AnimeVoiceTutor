param(
    [Parameter(Mandatory=$true)][string]$ExistingProjectRoot,
    [string]$WebPython = '',
    [string]$AsrPython = '',
    [string]$TtsPython = '',
    [string]$AsrModelPath = '',
    [string]$TtsRoot = ''
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$existing = (Resolve-Path -LiteralPath $ExistingProjectRoot -ErrorAction Stop).Path
if ($existing -eq $root) { throw 'Use a separate extracted source directory, not the existing working project.' }

function First-File([string[]]$Candidates) {
    foreach ($path in $Candidates) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $path).Path
        }
    }
    return ''
}
function Protect-String([string]$value) { return $value.Replace("'", "''") }
function Set-LocalValue([System.Collections.Generic.List[string]]$lines, [string]$name, [string]$value) {
    if ($value) { $lines.Add('  $env:' + $name + " = '" + (Protect-String $value) + "'") }
}
if (-not $TtsRoot) { $TtsRoot = Join-Path $existing 'external\GPT-SoVITS-v5' }
if (-not (Test-Path -LiteralPath (Join-Path $TtsRoot 'api_v2.py') -PathType Leaf)) {
    Write-Warning 'GPT-SoVITS source not found; provide -TtsRoot if installed elsewhere.'
    $TtsRoot = ''
} else { $TtsRoot = (Resolve-Path -LiteralPath $TtsRoot).Path }

if (-not $AsrModelPath) {
    foreach ($folder in @('qwen3_asr_0_6b','qwen3_asr_1_7b')) {
        $candidate = Join-Path $existing "models\$folder"
        if (Test-Path -LiteralPath (Join-Path $candidate 'config.json') -PathType Leaf) {
            $AsrModelPath = $candidate; break
        }
    }
}
if ($AsrModelPath) {
    if (-not (Test-Path -LiteralPath (Join-Path $AsrModelPath 'config.json') -PathType Leaf)) {
        throw "ASR model missing config.json: $AsrModelPath"
    }
    $AsrModelPath = (Resolve-Path -LiteralPath $AsrModelPath).Path
}

if (-not $WebPython) {
    $WebPython = First-File @((Join-Path $root 'runtime\web\Scripts\python.exe'), (Join-Path $existing '.venv\Scripts\python.exe'), (Join-Path $existing 'runtime\web\Scripts\python.exe'))
}
if (-not $AsrPython) {
    $AsrPython = First-File @((Join-Path $existing 'runtime\asr\Scripts\python.exe'), (Join-Path $HOME 'miniconda3\envs\jvt-asr\python.exe'), (Join-Path $HOME 'miniconda3\envs\jvt-qwen-asr\python.exe'), (Join-Path $HOME 'anaconda3\envs\jvt-asr\python.exe'))
}
if (-not $TtsPython) {
    $TtsPython = First-File @((Join-Path $existing 'runtime\tts\Scripts\python.exe'), (Join-Path $HOME 'miniconda3\envs\jvt-gpt-sovits-v5\python.exe'), (Join-Path $HOME 'anaconda3\envs\jvt-gpt-sovits-v5\python.exe'))
}
foreach ($entry in @(@('WebPython',$WebPython),@('AsrPython',$AsrPython),@('TtsPython',$TtsPython))) {
    if ($entry[1] -and -not (Test-Path -LiteralPath $entry[1] -PathType Leaf)) {
        throw "$($entry[0]) file not found: $($entry[1])"
    }
}

# Copy only small, private configuration. Never copy or modify model weights or media.
$configDir = Join-Path $root 'configs'
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
$oldPreset = Join-Path $existing 'configs\frozen_tts_preset.json'
$newPreset = Join-Path $configDir 'frozen_tts_preset.json'
if ((Test-Path -LiteralPath $oldPreset -PathType Leaf) -and -not (Test-Path -LiteralPath $newPreset)) {
    Copy-Item -LiteralPath $oldPreset -Destination $newPreset
    Write-Host 'Copied private TTS preset to extracted directory.'
}
$oldProfiles = First-File @((Join-Path $existing 'configs\voice_profiles_v08.json'), (Join-Path $existing 'configs\voices.json'))
$newProfiles = Join-Path $configDir 'voice_profiles_v08.json'
if ($oldProfiles -and -not (Test-Path -LiteralPath $newProfiles)) {
    $profiles = Get-Content -LiteralPath $oldProfiles -Encoding UTF8 -Raw | ConvertFrom-Json
    if ($null -eq $profiles.voices) { throw "Invalid voice profiles: $oldProfiles" }
    foreach ($voice in @($profiles.voices)) {
        $ref = [string]$voice.reference_audio_path
        if ($ref -and -not [System.IO.Path]::IsPathRooted($ref)) {
            $voice.reference_audio_path = [System.IO.Path]::GetFullPath((Join-Path $existing $ref))
        }
    }
    $jsonText = $profiles | ConvertTo-Json -Depth 16
    [System.IO.File]::WriteAllText($newProfiles, $jsonText, ([System.Text.UTF8Encoding]::new($false)))
    Write-Host 'Copied voice configuration with references to original local audio paths.'
}

$lines = New-Object 'System.Collections.Generic.List[string]'
$lines.Add('# Machine-local runtime paths. Not tracked by Git. Do not distribute.')
Set-LocalValue $lines 'AVT_WEB_PYTHON' $WebPython
Set-LocalValue $lines 'AVT_ASR_PYTHON' $AsrPython
Set-LocalValue $lines 'AVT_TTS_PYTHON' $TtsPython
Set-LocalValue $lines 'JVT_ASR_MODEL_PATH' $AsrModelPath
Set-LocalValue $lines 'AVT_TTS_ROOT' $TtsRoot
$target = Join-Path $root '.avt-local.ps1'
# Atomic output: update the extracted source only, never the working installation.
$temp = $target + '.tmp'
[System.IO.File]::WriteAllLines($temp, $lines, ([System.Text.UTF8Encoding]::new($false)))
Move-Item -LiteralPath $temp -Destination $target -Force
Write-Host 'Local model/runtime references configured. No model download, weight copy or dependency installation occurred.'
Write-Host 'Read-only preflight: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor_source.ps1'
Write-Host 'Voice smoke test (after starting): Test AnimeVoiceTutor.cmd -Voice'
