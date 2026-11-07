$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
$ttsRoot = if ($env:AVT_TTS_ROOT) { $env:AVT_TTS_ROOT } else { Join-Path $root 'external\GPT-SoVITS-v5' }
$ttsPython = & (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role tts
if (-not (Test-Path -LiteralPath $ttsPython)) { throw "TTS Python missing: $ttsPython" }
if (-not (Test-Path -LiteralPath (Join-Path $ttsRoot 'api_v2.py'))) { throw "GPT-SoVITS api_v2.py missing: $ttsRoot" }
$port = Get-NetTCPConnection -State Listen -LocalPort 9880 -ErrorAction SilentlyContinue
if ($port) { throw 'Port 9880 already in use. Stop the old TTS API before starting another one.' }
& $ttsPython (Join-Path $root 'tools\write_frozen_tts_config.py') --tts-root $ttsRoot
if ($LASTEXITCODE -ne 0) { throw 'Failed to create frozen TTS API config.' }
$env:CUDAGraph = '0'
$env:is_half = 'False'
$env:NO_PROXY = 'localhost,127.0.0.1,0.0.0.0,::1'
$env:GRADIO_SERVER_NAME = '127.0.0.1'
Set-Location -LiteralPath $ttsRoot
Write-Host 'Starting frozen FP32 TTS API on http://127.0.0.1:9880'
& $ttsPython -s .\api_v2.py -a 127.0.0.1 -p 9880 -c .\TEMP\jvt_frozen_tts_api.yaml
