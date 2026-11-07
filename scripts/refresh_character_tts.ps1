# Restart only this managed AnimeVoiceTutor TTS listener after character changes.
# Never terminate an unrecorded / foreign listener on TCP 9880.
param(
    [Parameter(Mandatory=$true)][string]$RunId,
    [Parameter(Mandatory=$true)][string]$CharacterId
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
. (Join-Path $PSScriptRoot 'verify_local_tts_provenance.ps1')
$statePath=Join-Path $root 'data\app\local_services.json'
$selectionPath=Join-Path $root 'data\app\selected_character.json'
$bindingPath=Join-Path $root 'data\app\tts_model_binding.json'
$refreshStatePath=Join-Path $root 'data\app\tts_refresh_state.json'
$logDir=Join-Path $root 'data\logs'
New-Item -ItemType Directory -Path $logDir -Force|Out-Null
if($RunId -notmatch '^[a-fA-F0-9]{32}$'){throw 'TTS_RELOAD_INVALID_RUN_ID'}
if($CharacterId -notmatch '^[a-z][a-z0-9_]{1,47}$' -or $CharacterId -eq 'default'){throw 'TTS_RELOAD_INVALID_CHARACTER'}
$sha=[System.Security.Cryptography.SHA256]::Create()
try{$hash=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($root.ToLowerInvariant()))).Replace('-','').Substring(0,24)}
finally{$sha.Dispose()}
$mutex=New-Object System.Threading.Mutex($false,('Local\AVT_START_'+$hash))
$acquired=$false
function Save-RefreshState([string]$status,[string]$detail){
    $payload=[pscustomobject]@{run_id=$RunId;character_id=$CharacterId;status=$status;detail=$detail;updated_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Compress
    $temp=$refreshStatePath+'.tmp'
    [IO.File]::WriteAllText($temp,$payload,[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $refreshStatePath -Force
}
try{
    try{$acquired=$mutex.WaitOne(180000)}catch [System.Threading.AbandonedMutexException]{$acquired=$true}
    if(-not $acquired){throw 'TTS_RELOAD_START_MUTEX_TIMEOUT'}
    function Read-ManagedState {
        if(-not (Test-Path -LiteralPath $statePath -PathType Leaf)){throw 'TTS_RELOAD_UNMANAGED_WEB'}
        $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json
        if([string]$state.run_id -ne $RunId){throw 'TTS_RELOAD_RUN_CHANGED'}
        return $state
    }
    function Confirm-Selection {
        if(-not (Test-Path -LiteralPath $selectionPath -PathType Leaf)){throw 'TTS_RELOAD_NO_SELECTION'}
        $id=[string]((Get-Content -LiteralPath $selectionPath -Raw -Encoding UTF8|ConvertFrom-Json).id)
        if($id -ne $CharacterId){throw 'TTS_RELOAD_SELECTION_CHANGED'}
    }
    function Listener-Pid {
        $found=@(Get-NetTCPConnection -State Listen -LocalPort 9880 -ErrorAction SilentlyContinue)
        if($found.Count -eq 0){return 0}
        return [int]$found[0].OwningProcess
    }
    function Trusted-Tts([int]$id,[int]$parentId,[string]$expectedPython){
        if($id -lt 4){return $false}
        $info=Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
        if(-not $info){return $false}
        if($info.Name -notmatch '^python(w)?\.exe$'){return $false}
        if([string]$info.CommandLine -notmatch '(^|[\\/])api_v2\.py(\s|$)'){return $false}
        if(-not $info.ExecutablePath){return $false}
        $samePython=[string]::Equals([IO.Path]::GetFullPath([string]$info.ExecutablePath),
                                      [IO.Path]::GetFullPath($expectedPython),
                                      [StringComparison]::OrdinalIgnoreCase)
        if(-not $samePython){return $false}
        if($parentId -gt 0 -and [int]$info.ParentProcessId -ne $parentId){return $false}
        return $true
    }
    $state=Read-ManagedState
    Confirm-Selection
    Save-RefreshState 'loading' 'Starting the selected GPT-SoVITS model'
    $webEntries=@($state.processes | Where-Object{$_.name -eq 'web' -and $_.kind -eq 'listener'})
    if($webEntries.Count -ne 1){throw 'TTS_RELOAD_UNMANAGED_WEB'}
    $webPid=[int]$webEntries[0].pid
    if(-not (Get-Process -Id $webPid -ErrorAction SilentlyContinue)){throw 'TTS_RELOAD_WEB_NOT_RUNNING'}
    $ttsPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role tts|Select-Object -Last 1)
    if(-not $ttsPython -or -not (Test-Path -LiteralPath $ttsPython -PathType Leaf)){throw 'TTS_RELOAD_PYTHON_MISSING'}
    $ttsRoot=if($env:AVT_TTS_ROOT){$env:AVT_TTS_ROOT}else{Join-Path $root 'external\GPT-SoVITS-v5'}
    if(-not (Test-Path -LiteralPath (Join-Path $ttsRoot 'api_v2.py') -PathType Leaf)){throw 'TTS_RELOAD_ENGINE_MISSING'}
    # Fail before stopping the existing voice if character config or weights are incomplete.
    & $ttsPython (Join-Path $root 'tools\write_frozen_tts_config.py') --tts-root $ttsRoot
    if($LASTEXITCODE -ne 0){throw 'TTS_RELOAD_CONFIG_INVALID'}
    $oldPid=Listener-Pid
    if($oldPid -gt 0){
        $previous=@($state.processes | Where-Object{$_.name -eq 'tts' -and $_.kind -eq 'listener' -and [int]$_.port -eq 9880 -and [int]$_.pid -eq $oldPid})
        # A previous AnimeVoiceTutor session can leave behind its frozen API
        # without a current state record. Only recover it if its real parent
        # is this checkout's verified start_tts_api_frozen.ps1 launcher.
        $recordedOwned=($previous.Count -eq 1 -and (Trusted-Tts $oldPid 0 $ttsPython))
        $localOrphan=(Test-LocalFrozenTtsProvenance -ListenerPid $oldPid -ExpectedPython $ttsPython -ProjectRoot $root)
        if(-not $recordedOwned -and -not $localOrphan){
            throw 'TTS_FOREIGN_LISTENER_ON_9880: Port 9880 process is not verified as this project; close its own app or inspect the parent process.'
        }
        if($localOrphan -and -not $recordedOwned){Write-Host "TTS_RELOAD_RECOVER_LOCAL_ORPHAN_PID: $oldPid"}
        Write-Host "TTS_RELOAD_STOP_MANAGED_PID: $oldPid"
        Stop-Process -Id $oldPid -Force -ErrorAction Stop
        for($i=0;$i -lt 40 -and (Listener-Pid) -gt 0;$i++){Start-Sleep -Milliseconds 250}
        if((Listener-Pid) -ne 0){throw 'TTS_RELOAD_OLD_LISTENER_STILL_RUNNING'}
    }
    Confirm-Selection
    # Remove the previous binding immediately; stale weights must never appear ready.
    if(Test-Path -LiteralPath $bindingPath){Remove-Item -LiteralPath $bindingPath -Force}
    $scriptFile=Join-Path $root 'scripts\start_tts_api_frozen.ps1'
    $args="-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$scriptFile`""
    $logTag=Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $out=Join-Path $logDir ("tts_model_${logTag}_stdout.log")
    $err=Join-Path $logDir ("tts_model_${logTag}_stderr.log")
    Write-Host "TTS_RELOAD_WORKER_LOGS: $out | $err"
    $launcher=Start-Process -FilePath 'powershell.exe' -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    Write-Host "TTS_RELOAD_START_LAUNCHER_PID: $($launcher.Id)"
    $newPid=0
    for($i=0;$i -lt 105;$i++){
        Start-Sleep -Seconds 1
        $candidate=Listener-Pid
        if($candidate -gt 0){
            if(-not (Trusted-Tts $candidate ([int]$launcher.Id) $ttsPython)){
                throw 'TTS_RELOAD_LISTENER_IDENTITY_UNVERIFIED'
            }
            $newPid=$candidate
            break
        }
        if($launcher.HasExited){throw ('TTS_RELOAD_WORKER_EXITED: inspect '+$err)}
    }
    if($newPid -le 0){throw ('TTS_RELOAD_TIMEOUT: inspect '+$err)}
    Confirm-Selection
    $state=Read-ManagedState
    if(-not (Get-Process -Id $webPid -ErrorAction SilentlyContinue)){throw 'TTS_RELOAD_WEB_EXITED'}
    $entries=@($state.processes | Where-Object{$_.name -ne 'tts'})
    $entries+=@([pscustomobject]@{name='tts';pid=[int]$launcher.Id;script='scripts\start_tts_api_frozen.ps1'},
                [pscustomobject]@{name='tts';pid=[int]$newPid;kind='listener';port=9880;script=''})
    $state.processes=$entries
    $tempState=$statePath+'.tts_reload.tmp'
    [IO.File]::WriteAllText($tempState,($state|ConvertTo-Json -Depth 7),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tempState -Destination $statePath -Force
    $binding=@{character_id=$CharacterId;listener_pid=[int]$newPid}|ConvertTo-Json -Compress
    $tempBinding=$bindingPath+'.tmp'
    [IO.File]::WriteAllText($tempBinding,$binding,[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tempBinding -Destination $bindingPath -Force
    Save-RefreshState 'ready' 'Selected character model is loaded'
    Write-Host "TTS_MODEL_REFRESH_READY: $CharacterId PID $newPid"
}catch{
    $reason=$_.Exception.Message
    Write-Host ('TTS_MODEL_REFRESH_FAILED: '+$reason)
    try{Save-RefreshState 'failed' $reason}catch{}
    throw
}finally{
    if($acquired){try{$mutex.ReleaseMutex()}catch{}}
    $mutex.Dispose()
}
