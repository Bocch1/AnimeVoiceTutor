$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
$ttsRoot = if ($env:AVT_TTS_ROOT) { $env:AVT_TTS_ROOT } else { Join-Path $root 'external\GPT-SoVITS-v5' }
$asrRoot = if ($env:JVT_ASR_MODEL_PATH) { $env:JVT_ASR_MODEL_PATH } elseif (Test-Path (Join-Path $root 'models\qwen3_asr_0_6b\config.json')) { Join-Path $root 'models\qwen3_asr_0_6b' } else { Join-Path $root 'models\qwen3_asr_1_7b' }
function Check([string]$name,[bool]$present,[string]$details) {
    $status = if ($present) { 'PASS' } else { 'MISSING' }
    Write-Host ('[{0}] {1} - {2}' -f $status,$name,$details)
}
Write-Host "AnimeVoiceTutor source preflight (read-only): $root"
foreach ($role in @('web','asr','tts')) {
    try {
        $python = (& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role $role | Select-Object -Last 1)
        Check "$role Python" ($python -and (Test-Path -LiteralPath $python -PathType Leaf)) $python
    } catch { Check "$role Python" $false 'not resolved' }
}
Check 'ASR model config' (Test-Path -LiteralPath (Join-Path $asrRoot 'config.json') -PathType Leaf) $asrRoot
Check 'TTS engine source' (Test-Path -LiteralPath (Join-Path $ttsRoot 'api_v2.py') -PathType Leaf) $ttsRoot
$selected='default'
$selection=Join-Path $root 'data\app\selected_character.json'
if (Test-Path -LiteralPath $selection -PathType Leaf) {
    try { $selected=(Get-Content -LiteralPath $selection -Raw -Encoding UTF8 | ConvertFrom-Json).id } catch { }
}
$pack=Join-Path $root ("data\character_packs\"+$selected)
Check 'Selected character' ($selected -eq 'default' -or (Test-Path -LiteralPath (Join-Path $pack 'character.json') -PathType Leaf)) $selected
if ($selected -ne 'default') {
    Check 'Character TTS preset' (Test-Path -LiteralPath (Join-Path $pack 'configs\tts_preset.json') -PathType Leaf) (Join-Path $pack 'configs\tts_preset.json')
    Check 'Character GPT weights' (Test-Path -LiteralPath (Join-Path $pack 'models\gpt.ckpt') -PathType Leaf) (Join-Path $pack 'models\gpt.ckpt')
    Check 'Character SoVITS weights' (Test-Path -LiteralPath (Join-Path $pack 'models\sovits.pth') -PathType Leaf) (Join-Path $pack 'models\sovits.pth')
}
Check 'FFmpeg' ($null -ne (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue)) 'ffmpeg.exe on PATH'
Check 'FFprobe' ($null -ne (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)) 'ffprobe.exe on PATH'
Write-Host 'This preflight checks file paths, not actual model inference. Use advanced\Test AnimeVoiceTutor.cmd -Voice after starting the application.'
