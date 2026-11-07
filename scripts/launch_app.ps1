param([switch]$SkipASR, [switch]$SkipTTS, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$logDir = Join-Path $root 'data\logs'
$stateDir = Join-Path $root 'data\app'
New-Item -ItemType Directory -Force -Path $logDir, $stateDir | Out-Null
$statePath = Join-Path $stateDir 'local_services.json'
$webPort = [int](& (Join-Path $PSScriptRoot 'web_port.ps1'))
$webBase = "http://127.0.0.1:$webPort"
$script:startedServices = @()
$script:owned = @()
$script:runId = [guid]::NewGuid().ToString("N")

function Has-Listener([int]$port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        try {
            $async = $tcp.BeginConnect('127.0.0.1', $port, $null, $null)
            if (-not $async.AsyncWaitHandle.WaitOne(350, $false)) { return $false }
            $tcp.EndConnect($async)
            return $true
        } finally { $tcp.Dispose() }
    } catch { return $false }
}
function Get-Json([string]$url) {
    try { return Invoke-RestMethod -Uri $url -TimeoutSec 2 -ErrorAction Stop }
    catch { return $null }
}
function Get-Service-Listener([string]$name, [int]$port) {
    $sockets = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    foreach ($socket in $sockets) {
        ${avtProcessId} = [int]$socket.OwningProcess
        $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=${avtProcessId}" -ErrorAction SilentlyContinue
        if (-not $procInfo -or $procInfo.Name -notmatch '^python(w)?\.exe$') { continue }
        $line = [string]$procInfo.CommandLine
        $trusted = switch ($name) {
            'web' { $line -match '(-m\s+voice_tutor\s+serve|uvicorn\s+voice_tutor\.app:app)' }
            'asr' { $line -match '(services\.asr_service:app)' }
            'tts' { $line -match '(^|[\\/])api_v2\.py(\s|$)' }
            default { $false }
        }
        if ($trusted) { return [pscustomobject]@{ name=$name; pid=${avtProcessId}; kind='listener'; port=$port; script='' } }
    }
    return $null
}
function Is-Previous-ManagedListener([string]$name, [int]$port, [int]$listenerPid) {
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { return $false }
    try {
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($entry in @($state.processes)) {
            if ($entry.kind -eq 'listener' -and $entry.name -eq $name -and
                [int]$entry.port -eq $port -and [int]$entry.pid -eq $listenerPid) {
                return $true
            }
        }
    } catch { return $false }
    return $false
}
function Record-Listener([string]$name, [int]$port) {
    $listener = Get-Service-Listener $name $port
    if ($null -eq $listener) { return }
    if ($name -notin $script:startedServices -and
        -not (Is-Previous-ManagedListener $name $port ([int]$listener.pid))) { return }
    if (@($script:owned | Where-Object { $_.kind -eq 'listener' -and $_.pid -eq $listener.pid }).Count -eq 0) {
        $script:owned += $listener
        Write-Host "[$name] Tracking actual listener PID $($listener.pid) on $port."
    }
}
function Launch-Service([string]$name, [int]$port, [string]$scriptFile) {
    if (Has-Listener $port) {
        $listener = Get-Service-Listener $name $port
        if ($name -eq 'web') {
            if ($listener -and (Is-Previous-ManagedListener 'web' $port ([int]$listener.pid))) {
                $status = Get-Json "$webBase/api/status"
                if ($status -and $status.version -eq '0.12.0') {
                    Write-Host "[web] Reusing a recorded Tutor listener on $port (PID $($listener.pid))."
                    Record-Listener 'web' $port
                    return
                }
            }
            throw "Web port $port is occupied by another service. It will not be stopped or adopted."
        }
        if ($null -ne $listener) {
            Write-Host "[$name] Reusing an existing compatible service on port $port (not owned; will not be stopped)."
            return
        }
        throw "[$name] Port $port is occupied by an unexpected process. Nothing was stopped."
    }
    $file = Join-Path $root $scriptFile
    if (-not (Test-Path -LiteralPath $file)) { throw "Launcher missing: $file" }
    $out = Join-Path $logDir "${name}_stdout.log"
    $err = Join-Path $logDir "${name}_stderr.log"
    $launchArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$file`""
    $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    $script:owned += [pscustomobject]@{ name=$name; pid=$proc.Id; script=$scriptFile }
    $script:startedServices += $name
    Write-Host "[$name] Started process $($proc.Id). Logs: data\logs\${name}_*.log"
}
function Save-Processes {
    [pscustomobject]@{ run_id=$script:runId; created_at=(Get-Date).ToString('o'); processes=$script:owned } |
        ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

Write-Host 'AnimeVoiceTutor | One-click local launcher'
Write-Host "Project: $root"
$webPython = (& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web)
if (-not (Test-Path -LiteralPath $webPython)) {
    Write-Host 'ERROR: The web app Python environment is not installed.'
    Write-Host 'Run Setup AnimeVoiceTutor.cmd once during installation.'
    exit 1
}
if (-not (Test-Path -LiteralPath (Join-Path $root '.env'))) {
    Write-Host 'WARNING: No .env found. DeepSeek text chat needs configuration.'
}

# Preserve prior owned processes so the Stop shortcut can still shut them down.
if (Test-Path -LiteralPath $statePath) {
    try {
        $old = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($entry in @($old.processes)) {
            if ($null -ne $entry -and $null -ne $entry.pid) {
                $running = Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue
                if ($running -and $entry.kind -ne 'listener') { $script:owned += $entry }
            }
        }
    } catch { Write-Host 'Ignoring an unreadable old process state file.' }
}

# Capture intended character before service startup to avoid a selection race.
$ttsCharacterAtStart='default'
$ttsSelection=Join-Path $stateDir 'selected_character.json'
if (Test-Path -LiteralPath $ttsSelection -PathType Leaf) {
    try { $ttsCharacterAtStart=(Get-Content -LiteralPath $ttsSelection -Raw -Encoding UTF8 | ConvertFrom-Json).id } catch { }
}
if (-not $SkipASR) { Launch-Service 'asr' 8766 'scripts\start_asr_auto.ps1' }
if (-not $SkipTTS) { Launch-Service 'tts' 9880 'scripts\start_tts_api_frozen.ps1' }
Launch-Service 'web' $webPort 'scripts\start_web.ps1'
# Capture the real Web PID, not only its hidden PowerShell parent process.
Record-Listener 'web' $webPort
Save-Processes

Write-Host 'Checking Web service...'
$webOk = $false
for ($i = 0; $i -lt 30; $i++) {
    $webOk = (Get-Json "$webBase/api/status") -ne $null
    if ($webOk) { break }
    Start-Sleep -Seconds 1
}
if (-not $webOk) {
    Write-Host 'ERROR: Web service did not become available.'
    Write-Host "Check $logDir\web_stderr.log"
    exit 1
}

if (-not $NoBrowser) { & (Join-Path $PSScriptRoot 'open_app_window.ps1') -Url $webBase }
Write-Host "Web app ready: $webBase"
Write-Host 'Checking voice services (ASR may need to load a model)...'
$asrReady = $SkipASR
$ttsReady = $SkipTTS
$asrError = ''
for ($i = 0; $i -lt 70; $i++) {
    if (-not $SkipASR) {
        $health = Get-Json 'http://127.0.0.1:8766/health'
        if ($health -and $health.ready) { $asrReady = $true }
        if ($health -and $health.error) { $asrError = [string]$health.error; break }
    }
    if (-not $SkipTTS -and (Has-Listener 9880)) { $ttsReady = $true }
    if ($asrReady -and $ttsReady) { break }
    # Detect failure early rather than waiting through a long timeout.
    $asrProcess = @($script:owned | Where-Object { $_.name -eq 'asr' } | Select-Object -Last 1)
    $ttsProcess = @($script:owned | Where-Object { $_.name -eq 'tts' } | Select-Object -Last 1)
    $asrStopped = (-not $SkipASR) -and (-not $asrReady) -and ($asrProcess.Count -gt 0) -and (-not (Get-Process -Id $asrProcess[0].pid -ErrorAction SilentlyContinue))
    $ttsStopped = (-not $SkipTTS) -and (-not $ttsReady) -and ($ttsProcess.Count -gt 0) -and (-not (Get-Process -Id $ttsProcess[0].pid -ErrorAction SilentlyContinue))
    if ($asrError -or ($asrStopped -and ($ttsReady -or $ttsStopped)) -or ($ttsStopped -and ($asrReady -or $asrStopped))) { break }
    Start-Sleep -Seconds 2
}
Write-Host ''
if ($SkipASR) { Write-Host 'ASR: skipped by request' }
elseif ($asrReady) { Write-Host 'ASR: ready for Japanese microphone transcription' }
else {
    Write-Host 'ASR: unavailable (text chat and TTS can still work)'
    if ($asrError) { Write-Host "ASR reported: $asrError" }
    Write-Host "ASR log: $logDir\asr_stderr.log"
    Write-Host 'Diagnostic: powershell -ExecutionPolicy Bypass -File scripts\doctor_asr.ps1'
}
if ($SkipTTS) { Write-Host 'TTS: skipped by request' }
elseif ($ttsReady) { Write-Host 'TTS: port 9880 is listening' }
else { Write-Host "TTS: unavailable; check $logDir\tts_stderr.log" }
Write-Host ''
# Capture actual Python listeners; PowerShell wrapper processes may exit separately.
Record-Listener 'web' $webPort
if (-not $SkipASR) { Record-Listener 'asr' 8766 }
if (-not $SkipTTS) { Record-Listener 'tts' 9880 }
# Record which installed model the managed TTS listener actually started with.
# A reused listener is never assigned to a new character automatically.
if (-not $SkipTTS -and $ttsReady -and $script:startedServices -contains 'tts') {
    $listener=@($script:owned | Where-Object { $_.name -eq 'tts' -and $_.kind -eq 'listener' } | Select-Object -Last 1)
    $selection=Join-Path $stateDir 'selected_character.json'
    if ($listener.Count -gt 0 -and (Test-Path -LiteralPath $selection -PathType Leaf)) {
        # Windows PowerShell 5.1's Set-Content -Encoding UTF8 adds a BOM, which
        # the JSON reader must not have to depend on. Write portable UTF-8.
        $bindingJson = [pscustomobject]@{
            character_id = $ttsCharacterAtStart
            listener_pid = [int]$listener[0].pid
        } | ConvertTo-Json -Compress
        $bindingPath = Join-Path $stateDir 'tts_model_binding.json'
        [System.IO.File]::WriteAllText($bindingPath, $bindingJson, ([System.Text.UTF8Encoding]::new($false)))
    }
}

Save-Processes
if (-not $NoBrowser) {
    $monitor = Join-Path $root 'scripts\monitor_browser.ps1'
    if (-not (Test-Path -LiteralPath $monitor)) { throw 'Browser monitor script is missing.' }
    $monArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$monitor`" -RunId $script:runId"
    Start-Process -FilePath 'powershell.exe' -ArgumentList $monArgs -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir ("browser_monitor_$($script:runId)_stdout.log")) `
        -RedirectStandardError (Join-Path $logDir ("browser_monitor_$($script:runId)_stderr.log")) | Out-Null
    Write-Host 'The last browser tab closing will automatically stop the managed services.'
} else {
    Write-Host 'NoBrowser mode: services stay active until Stop AnimeVoiceTutor.cmd is run.'
}
Write-Host 'You can also use Stop AnimeVoiceTutor.cmd at any time.'
if ((-not $SkipASR -and -not $asrReady) -or (-not $SkipTTS -and -not $ttsReady)) {
    Write-Host 'A voice service needs attention. The text app is still available.'
    exit 2
}
