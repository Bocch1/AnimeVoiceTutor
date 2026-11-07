# Produce a machine-local reproducibility report without changing models.
param([string]$EngineFolder='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
if(-not $EngineFolder){$EngineFolder=if($env:AVT_TTS_ROOT){$env:AVT_TTS_ROOT}else{Join-Path $root 'external\GPT-SoVITS-v5'}}
if(-not (Test-Path -LiteralPath (Join-Path $EngineFolder 'api_v2.py') -PathType Leaf)){throw 'ENGINE_NOT_FOUND: Select the folder containing api_v2.py'}
$engine=(Resolve-Path -LiteralPath $EngineFolder).Path
$commit='unknown'
if(Test-Path -LiteralPath (Join-Path $engine '.git')){
    $commit=((& git.exe -C $engine rev-parse HEAD 2>$null)|Select-Object -Last 1)
    if($LASTEXITCODE -ne 0){$commit='unknown'}
}
$engineGitStatus=@()
$engineGitDirty=$false
if(Test-Path -LiteralPath (Join-Path $engine '.git')){
    try{
        $engineGitStatus=@(& git.exe -C $engine status --porcelain=v1 --untracked-files=normal 2>$null | ForEach-Object {[string]$_})
        if($LASTEXITCODE -eq 0){$engineGitDirty=($engineGitStatus.Count -gt 0)}
    }catch{}
}
$files=@{}
# Include the inference code, config, and local Japanese dictionary in the hash inventory.
foreach($rel in @('api_v2.py','GPT_SoVITS/inference_webui.py',
                  'GPT_SoVITS/TTS_infer_pack/TTS.py',
                  'GPT_SoVITS/configs/tts_infer.yaml',
                  'GPT_SoVITS/Accel/PyTorch/__init__.py',
                  'GPT_SoVITS/text/ja_userdic/user.dict',
                  'GPT_SoVITS/text/ja_userdic/userdict.md5')){
    $path=Join-Path $engine $rel
    if(Test-Path -LiteralPath $path -PathType Leaf){$files[$rel]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$ttsPython=''
$ttsVersion='unknown'
$torchVersion='unknown'
$freezeHash='unknown'
try{
    $ttsPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role tts | Select-Object -Last 1)
    if($ttsPython -and (Test-Path -LiteralPath $ttsPython -PathType Leaf)){
        $ttsVersion=((& $ttsPython --version 2>&1)|Out-String).Trim()
        $pipShow=(& $ttsPython -m pip show torch 2>$null | Select-String '^Version:')
        if($pipShow){$torchVersion=([string]$pipShow[-1]).Replace('Version:','').Trim()}
        $freeze=(& $ttsPython -m pip freeze 2>$null | Sort-Object)
        if($LASTEXITCODE -eq 0){
            $sha=[System.Security.Cryptography.SHA256]::Create()
            try{
                $bytes=[Text.Encoding]::UTF8.GetBytes(($freeze -join "`n"))
                $freezeHash=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
            }finally{$sha.Dispose()}
        }
    }
}catch{Write-Warning 'Could not read all TTS runtime package versions.'}
$driver='unknown'
try{
    if(Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue){
        $driver=((& nvidia-smi.exe --query-gpu=driver_version --format=csv,noheader 2>$null | Select-Object -First 1)|Out-String).Trim()
    }
}catch{}
$ffmpeg='unknown'
try{
    if(Get-Command ffmpeg.exe -ErrorAction SilentlyContinue){
        $ffmpeg=((& ffmpeg.exe -version 2>$null | Select-Object -First 1)|Out-String).Trim()
    }
}catch{}
$character='default';$selected=Join-Path $root 'data\app\selected_character.json'
if(Test-Path -LiteralPath $selected -PathType Leaf){
    try{$character=[string](Get-Content -LiteralPath $selected -Raw -Encoding UTF8|ConvertFrom-Json).id}catch{}
}
$characterHashes=@{}
if($character -ne 'default' -and $character -match '^[a-zA-Z0-9_-]+$'){
    $pack=Join-Path $root ('data\character_packs\'+$character)
    foreach($name in @('character.json','configs/tts_preset.json','models/gpt.ckpt','models/sovits.pth')){
        $file=Join-Path $pack $name
        if(Test-Path -LiteralPath $file -PathType Leaf){$characterHashes[$name]=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
}
$report=[ordered]@{
    schema_version=1
    captured_utc=[DateTime]::UtcNow.ToString('o')
    engine_path=$engine
    engine_commit=$commit
    engine_worktree_dirty=$engineGitDirty
    engine_git_status=$engineGitStatus
    engine_file_sha256=$files
    tts_python=$ttsPython
    tts_python_version=$ttsVersion
    torch_version=$torchVersion
    tts_pip_freeze_sha256=$freezeHash
    nvidia_driver=$driver
    ffmpeg_version=$ffmpeg
    selected_character=$character
    character_file_sha256=$characterHashes
    warning='Machine-local diagnostic; NOT an official validated cross-machine baseline.'
}
$dest=Join-Path $root 'data\app\voice_baseline_local.json'
New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force|Out-Null
[IO.File]::WriteAllText($dest,($report|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Write-Host 'LOCAL_ENGINE_BASELINE_CAPTURED:' $dest
Write-Host 'ENGINE_COMMIT:' $commit
Write-Host 'ENGINE_WORKTREE_DIRTY:' $engineGitDirty
Write-Host 'ENGINE_LOCAL_CHANGES:' $engineGitStatus.Count
Write-Host 'TORCH_VERSION:' $torchVersion
Write-Host 'SELECTED_CHARACTER:' $character
