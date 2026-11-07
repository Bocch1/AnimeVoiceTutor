# Verify the complete offline voice base; no web server or character pack is required.
# This is a read-only diagnostic. It never downloads or modifies files.
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
$failures=New-Object 'System.Collections.Generic.List[string]'
function Check([string]$name,[bool]$ok,[string]$detail){
    $tag=if($ok){'PASS'}else{'FAIL'}
    Write-Host ('[{0}] {1}: {2}' -f $tag,$name,$detail)
    if(-not $ok){$script:failures.Add($name)}
}
$manifestPath=Join-Path $root 'release\install_specs\voice_baseline.json'
$manifest=Get-Content -LiteralPath $manifestPath -Encoding UTF8 -Raw|ConvertFrom-Json
Check 'Windows x64' ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT -and [Environment]::Is64BitOperatingSystem) 'Windows 64-bit is required'
$probe=Join-Path $PSScriptRoot 'runtime_import_probe.py'
$py=@{}
foreach($role in @('web','asr','tts')){
    $runtime=''
    try{$runtime=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role $role | Select-Object -Last 1)}catch{}
    $exists=($runtime -and (Test-Path -LiteralPath $runtime -PathType Leaf))
    Check ("$role Python") ([bool]$exists) ([string]$runtime)
    if($exists){
        $py[$role]=$runtime
        try {
            # Native stderr is diagnostic output, not a fatal PowerShell ErrorRecord.
            $previousPreference=$ErrorActionPreference
            $ErrorActionPreference='Continue'
            try{ & $runtime $probe --role $role 2>&1 | Out-Host; $resultCode=$LASTEXITCODE }
            finally{ $ErrorActionPreference=$previousPreference }
            Check ("$role runtime imports and CUDA") ($resultCode -eq 0) 'Required packages and GPU checks'
        } catch { Check ("$role runtime imports and CUDA") $false ([string]$_) }
    }
    $lock=Join-Path $root ('release\install_specs\'+$role+'_requirements.lock')
    $expected=[string]$manifest.runtime_lock_sha256.$role
    $valid=(Test-Path -LiteralPath $lock -PathType Leaf) -and ((Get-FileHash -LiteralPath $lock -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected)
    Check ("$role dependency lock integrity") $valid 'Bundled SHA-256 baseline'
}
$asrFolder=if($env:JVT_ASR_MODEL_PATH){$env:JVT_ASR_MODEL_PATH}else{
    $preferred=Join-Path $root 'models\qwen3_asr_1_7b'
    if(Test-Path -LiteralPath (Join-Path $preferred 'config.json') -PathType Leaf){$preferred}else{Join-Path $root 'models\qwen3_asr_0_6b'}
}
if($py.ContainsKey('web')){
    try {
        $previousPreference=$ErrorActionPreference
        $ErrorActionPreference='Continue'
        try{ & $py['web'] (Join-Path $root 'tools\check_local_asr_model.py') $asrFolder 2>&1 | Out-Host; $modelResult=$LASTEXITCODE }
        finally{ $ErrorActionPreference=$previousPreference }
        Check 'Qwen3-ASR model files' ($modelResult -eq 0) $asrFolder
    } catch { Check 'Qwen3-ASR model files' $false ([string]$_) }
}else{Check 'Qwen3-ASR model files' $false 'Web Python required for model integrity check'}
$engine=if($env:AVT_TTS_ROOT){$env:AVT_TTS_ROOT}else{Join-Path $root 'external\GPT-SoVITS-v5'}
Check 'GPT-SoVITS v5 source' (Test-Path -LiteralPath (Join-Path $engine 'api_v2.py') -PathType Leaf) $engine
$pretrained=Join-Path $engine 'GPT_SoVITS\pretrained_models'
$hasPretrained=(Test-Path -LiteralPath $pretrained -PathType Container) -and
    (@(Get-ChildItem -LiteralPath $pretrained -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.Length -gt 0}).Count -gt 0)
Check 'GPT-SoVITS pretrained resources' $hasPretrained $pretrained
Check 'FFmpeg' ($null -ne (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue)) 'ffmpeg.exe must be available'
Check 'FFprobe' ($null -ne (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)) 'ffprobe.exe must be available'
if($failures.Count -gt 0){
    Write-Host ('VOICE_BASE_DIAGNOSTICS_FAILED: '+($failures -join ', '))
    throw 'VOICE_BASE_DIAGNOSTICS_FAILED'
}
Write-Host 'VOICE_BASE_DIAGNOSTICS_PASS'
