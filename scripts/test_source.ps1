param([switch]$Voice, [switch]$TtsOnly, [switch]$AsrOnly)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
$python=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web | Select-Object -Last 1)
if (-not $python -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Web Python environment is missing. Run advanced\Setup AnimeVoiceTutor.cmd first.'
}
$script=Join-Path $root 'tools\smoke_voice_services.py'
Set-Location -LiteralPath $root
$argsList=@($script)
if ($Voice) { $argsList += '--voice' }
if ($TtsOnly) { $argsList += '--tts-only' }
if ($AsrOnly) { $argsList += '--asr-only' }
& $python @argsList
if ($LASTEXITCODE -ne 0) { throw 'AnimeVoiceTutor live smoke test failed.' }
