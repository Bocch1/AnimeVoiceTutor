$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$items = @(
  @{name='Web Python';path='runtime\web\Scripts\python.exe'},
  @{name='ASR Python';path='runtime\asr\Scripts\python.exe'},
  @{name='TTS Python';path='runtime\tts\Scripts\python.exe'},
  @{name='ASR model';path='models\qwen3_asr_0_6b\config.json'},
  @{name='ASR 1.7B model';path='models\qwen3_asr_1_7b\config.json'},
  @{name='GPT-SoVITS source';path='external\GPT-SoVITS-v5\api_v2.py'},
  @{name='TTS private preset';path='configs\frozen_tts_preset.json'},
  @{name='Voice references';path='configs\voice_profiles_v08.json'}
)
foreach ($item in $items) {
  [pscustomobject]@{Item=$item.name;Present=(Test-Path -LiteralPath (Join-Path $root $item.path) -PathType Leaf)}
}
[pscustomobject]@{Item='ffmpeg.exe on PATH';Present=($null -ne (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue))}
[pscustomobject]@{Item='ffprobe.exe on PATH';Present=($null -ne (Get-Command ffprobe.exe -ErrorAction SilentlyContinue))}
Write-Host 'This preflight never downloads files or prints secrets.'
