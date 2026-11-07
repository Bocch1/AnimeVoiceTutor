param([switch]$Strict, [switch]$Json)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$spec=Join-Path $root 'release\install_specs\voice_baseline.json'
if(-not (Test-Path -LiteralPath $spec -PathType Leaf)){throw 'BASELINE_MANIFEST_MISSING'}
$manifest=Get-Content -LiteralPath $spec -Raw -Encoding UTF8 | ConvertFrom-Json
$checks=@()
function Add-Check([string]$name,[bool]$ok,[string]$message,[bool]$required){
    $script:checks+= [PSCustomObject]@{name=$name;ok=$ok;required=$required;detail=$message}
    if(-not $Json){$tag=if($ok){'PASS'}else{if($required){'BLOCK'}else{'WARN'}};Write-Host ('[{0}] {1}: {2}' -f $tag,$name,$message)}
}
Add-Check 'Windows x64' ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT -and [Environment]::Is64BitOperatingSystem) 'Windows x64 installer target' $true
$gpu=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
$gpuText='No accessible NVIDIA driver'
$gpuOK=$false
if($gpu){try{$result=(& $gpu.Source -L 2>$null | Out-String).Trim(); if($LASTEXITCODE -eq 0 -and $result -match 'GPU\s*0'){ $gpuOK=$true;$gpuText=$result }}catch{}}
Add-Check 'NVIDIA GPU and driver' $gpuOK $gpuText $true
$ff=(Get-Command ffmpeg.exe -ErrorAction SilentlyContinue)
$probe=(Get-Command ffprobe.exe -ErrorAction SilentlyContinue)
Add-Check 'FFmpeg + FFprobe' ($null -ne $ff -and $null -ne $probe) 'Available on PATH or install before voice test' $false
$git=(Get-Command git.exe -ErrorAction SilentlyContinue)
Add-Check 'Git' ($null -ne $git) 'Required to download the pinned GPT-SoVITS checkout' $false
$drive=[IO.Path]::GetPathRoot($root)
try{$free=[math]::Round(([System.IO.DriveInfo]::new($drive)).AvailableFreeSpace/1GB,1)}catch{$free=-1}
Add-Check 'Disk space >= 25 GiB' ($free -ge 25) "Free ${free} GiB (estimated, not exact requirement)" $true
foreach($role in @('web','asr','tts')){
    $lock=Join-Path $root ('release\install_specs\'+$role+'_requirements.lock')
    $ok=$false
    if(Test-Path -LiteralPath $lock -PathType Leaf){$expected=[string]$manifest.runtime_lock_sha256.$role;$actual=(Get-FileHash -LiteralPath $lock -Algorithm SHA256).Hash.ToLowerInvariant();$ok=($expected -eq $actual)}
    Add-Check "Dependency lock $role" $ok 'Matches the bundled baseline SHA-256' $true
}
$blocked=@($checks|Where-Object {$_.required -and -not $_.ok})
if($Json){[PSCustomObject]@{checks=$checks;blockers=@($blocked|ForEach-Object {$_.name})}|ConvertTo-Json -Depth 6}
if($Strict -and $blocked.Count){throw ('PREFLIGHT_BLOCKED: '+(($blocked|ForEach-Object {$_.name})-join ', '))}
