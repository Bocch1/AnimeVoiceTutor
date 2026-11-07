param([ValidateSet('0.6B','1.7B')][string]$Model='0.6B')
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$folder=if ($Model -eq '0.6B') { 'qwen3_asr_0_6b' } else { 'qwen3_asr_1_7b' }
$repo=if ($Model -eq '0.6B') { 'Qwen/Qwen3-ASR-0.6B' } else { 'Qwen/Qwen3-ASR-1.7B' }
$destination=Join-Path $root "models\$folder"
$python=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role asr | Select-Object -Last 1)
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Install the ASR runtime first: advanced\Setup AnimeVoiceTutor.cmd all'
}
$checker=Join-Path $root 'tools\check_local_asr_model.py'
if (Test-Path -LiteralPath (Join-Path $destination 'config.json') -PathType Leaf) {
    & $python $checker $destination
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Model files already present: $destination. Skipped download."
        return
    }
    Write-Warning 'Model directory contains incomplete weights; resuming download.'
}
Write-Host "Downloading public model $repo to $destination. Existing files are reused."
& $python (Join-Path $root 'tools\download_hf_model.py') --repo $repo --destination $destination
if ($LASTEXITCODE -ne 0) {
    throw 'Download failed. Check your network and retry; cached files are preserved.'
}
& $python $checker $destination
if ($LASTEXITCODE -ne 0) {
    throw 'Download incomplete. Check your network and retry; cached files are preserved.'
}
Write-Host 'ASR model available. Third-party license terms apply.'
