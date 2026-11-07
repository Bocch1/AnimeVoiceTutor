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
# A previous launch may have chosen an alternate port. Prefer its recorded
# port when present; verify process identity before ever reusing it.
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    try {
        $savedState = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        [int]$savedPort = 0
        if ($null -ne $savedState.web_port -and
            [int]::TryParse([string]$savedState.web_port, [ref]$savedPort) -and
            $savedPort -ge 1024 -and $savedPort -le 65535 -and
            $savedPort -notin @(8766,9880)) { $webPort = $savedPort }
    } catch { Write-Host 'Previous Web port state is unreadable; using the configured port.' }
}
$webBase = "http://127.0.0.1:$webPort"
$script:startedServices = @()
$script:owned = @()
$script:runId = [guid]::NewGuid().ToString("N")
. (Join-Path $PSScriptRoot 'verify_local_tts_provenance.ps1')
$script:recoveredTts = $false

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
# The launched Web process inherits this random run ID. A foreign listener
# cannot produce the matching signed-by-launch response, even if its Python
# executable path happens to look the same as our virtual environment.
function Get-ManagedWebListener([int]$port, [string]$runId) {
    if ($runId -notmatch '^[0-9a-fA-F]{32}$') { return $null }
    $uri = "http://127.0.0.1:$port/api/system/managed-identity"
    try {
        $claim = Invoke-RestMethod -Uri $uri -Headers @{'X-AVT-Run-Id'=$runId} -TimeoutSec 2 -ErrorAction Stop
        if (-not $claim.managed -or [int]$claim.web_port -ne $port) { return $null }
        ${avtProcessId} = [int]$claim.pid
        if (${avtProcessId} -lt 4) { return $null }
        $socket = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Where-Object { [int]$_.OwningProcess -eq ${avtProcessId} })
        if ($socket.Count -lt 1) { return $null }
        $process = Get-Process -Id ${avtProcessId} -ErrorAction SilentlyContinue
        if (-not $process -or $process.ProcessName -notmatch '^python(w)?$') { return $null }
        return [pscustomobject]@{name='web';pid=${avtProcessId};kind='listener';port=$port;script=''}
    } catch { return $null }
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
        # A generic command line is not enough to adopt a Web process from
        # another checkout. Require the exact configured Web Python executable.
        if ($trusted -and $name -eq 'web') {
            $expectedWebPython = (& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web)
            if (-not $expectedWebPython -or -not $procInfo.ExecutablePath -or
                -not [string]::Equals(
                    [IO.Path]::GetFullPath([string]$procInfo.ExecutablePath),
                    [IO.Path]::GetFullPath([string]$expectedWebPython),
                    [StringComparison]::OrdinalIgnoreCase)) { $trusted = $false }
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
# Save only processes we have positively identified. The Web port must be
# recorded because a foreign listener may force an alternate port.
function Save-Processes {
    [pscustomobject]@{ run_id=$script:runId; web_port=$webPort; created_at=(Get-Date).ToString('o'); processes=$script:owned } |
        ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding UTF8
}
function Start-BrowserMonitor {
    if ($NoBrowser) { return }
    $monitor = Join-Path $root 'scripts\monitor_browser.ps1'
    if (-not (Test-Path -LiteralPath $monitor)) { throw 'Browser monitor script is missing.' }
    $monArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$monitor`" -RunId $script:runId -WebPort $webPort"
    Start-Process -FilePath 'powershell.exe' -ArgumentList $monArgs -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir ("browser_monitor_$($script:runId)_stdout.log")) `
        -RedirectStandardError (Join-Path $logDir ("browser_monitor_$($script:runId)_stderr.log")) | Out-Null
    Write-Host 'Browser lifecycle monitor started for this app instance.'
}
# A second click opens only a listener that proves the same managed run ID.
# A legacy or foreign Web listener is not adopted or killed; choose another port.
function Try-Open-ExistingInstance {
    if (-not (Has-Listener $webPort)) { return $false }
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { return $false }
    try {
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $previousRun = [string]$state.run_id
        if ($previousRun -notmatch '^[0-9a-fA-F]{32}$') { return $false }
        $web = Get-ManagedWebListener $webPort $previousRun
        if ($null -eq $web) { return $false }
        $script:runId = $previousRun
        $script:owned = @($state.processes)
        if (@($script:owned | Where-Object {
            $_.name -eq 'web' -and $_.kind -eq 'listener' -and [int]$_.pid -eq [int]$web.pid
        }).Count -eq 0) {
            $script:owned += $web
            Save-Processes
        }
        Write-Host "Reusing verified managed AnimeVoiceTutor Web PID $($web.pid) on $webPort."
        if (-not $NoBrowser) { & (Join-Path $PSScriptRoot 'open_app_window.ps1') -Url $webBase }
        return $true
    } catch { return $false }
}
if (Try-Open-ExistingInstance) { return }

# A port owned by another application must never be killed or adopted. Choose
# a free project-local Web port and keep its value in the managed state.
if (Has-Listener $webPort) {
    $occupiedPort = $webPort
    $alternatePorts = @(8777,8778,8779,8780,8781,8782,8783,8784,8785)
    $alternative = $null
    foreach ($candidate in $alternatePorts) {
        if ($candidate -eq $occupiedPort -or $candidate -in @(8766,9880)) { continue }
        if (-not (Has-Listener $candidate)) { $alternative = $candidate; break }
    }
    if ($null -eq $alternative) {
        throw "Web port $occupiedPort is occupied and no safe alternate Web port was found. Nothing was stopped."
    }
    $webPort = [int]$alternative
    $webBase = "http://127.0.0.1:$webPort"
    Write-Host "Web port $occupiedPort belongs to an unverified listener; using alternate Web port $webPort instead."
}
# The Web subprocess, API and browser-side exit helper must all agree on the
# effective port and the random managed run ID. They are inherited only by
# children of this launcher, not by a manually launched Web server.
$env:AVT_WEB_PORT = [string]$webPort
$env:AVT_MANAGED_RUN_ID = $script:runId

function Record-Listener([string]$name, [int]$port) {
    $listener = if ($name -eq 'web') {
        Get-ManagedWebListener $port $script:runId
    } else { Get-Service-Listener $name $port }
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
                if ($status -and $status.version -eq '0.13.1') {
                    Write-Host "[web] Reusing a recorded Tutor listener on $port (PID $($listener.pid))."
                    Record-Listener 'web' $port
                    return
                }
            }
            throw "Web port $port is occupied by another service. It will not be stopped or adopted."
        }
        if ($null -ne $listener) {
            if ($name -eq 'tts') {
                $expectedTtsPython = (& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role tts | Select-Object -Last 1)
                if ($expectedTtsPython -and (Test-LocalFrozenTtsProvenance -ListenerPid ([int]$listener.pid) -ExpectedPython $expectedTtsPython -ProjectRoot $root)) {
                    # A genuine stale local TTS may have lost its state file.
                    # Recover only the verified Python listener, not an untrusted wrapper.
                    $script:owned += [pscustomobject]@{ name='tts'; pid=[int]$listener.pid; kind='listener'; port=9880; script='' }
                    $script:recoveredTts = $true
                    Write-Host "[tts] Recovered this checkout's frozen TTS listener PID $($listener.pid)."
                    return
                }
            }
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

Write-Host 'AnimeVoiceTutor | One-click local launcher'
Write-Host "Project: $root"
$webPython = (& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web)
if (-not (Test-Path -LiteralPath $webPython)) {
    Write-Host 'ERROR: The web app Python environment is not installed.'
    Write-Host 'Run advanced\Setup AnimeVoiceTutor.cmd once during installation.'
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
# Register the exact Web listener before showing the window. This is essential
# for browser Exit and post-import character TTS activation. Never mistake an
# unverified running Web server for a managed desktop instance.
Record-Listener 'web' $webPort
$registeredWeb=@($script:owned | Where-Object {
    $_.name -eq 'web' -and $_.kind -eq 'listener' -and [int]$_.port -eq $webPort
})
if ($registeredWeb.Count -ne 1) {
    Write-Host 'ERROR: Web launched but managed ownership handshake failed.'
    Write-Host "Web log: $logDir\web_stderr.log"
    Save-Processes
    throw 'WEB_MANAGED_IDENTITY_MISSING'
}
Save-Processes

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
# Do not advertise stale voice weights as ready just because a local frozen
# listener was recovered. If the selected character does not match the
# recorded binding, refresh it using the same verified managed run.
if ($script:recoveredTts -and -not $SkipTTS -and $ttsCharacterAtStart -ne 'default') {
    $recordedTts = @($script:owned | Where-Object { $_.name -eq 'tts' -and $_.kind -eq 'listener' -and [int]$_.port -eq 9880 } | Select-Object -Last 1)
    $bindingPath = Join-Path $stateDir 'tts_model_binding.json'
    $bound = $false
    if ($recordedTts.Count -gt 0 -and (Test-Path -LiteralPath $bindingPath -PathType Leaf)) {
        try {
            $binding = Get-Content -LiteralPath $bindingPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $bound = ([string]$binding.character_id -eq [string]$ttsCharacterAtStart -and [int]$binding.listener_pid -eq [int]$recordedTts[0].pid)
        } catch { $bound = $false }
    }
    if (-not $bound) {
        $refreshScript = Join-Path $root 'scripts\refresh_character_tts.ps1'
        $refreshArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$refreshScript`" -RunId $script:runId -CharacterId $ttsCharacterAtStart"
        Start-Process -FilePath 'powershell.exe' -ArgumentList $refreshArgs -WorkingDirectory $root -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $logDir 'tts_start_recovery_stdout.log') `
            -RedirectStandardError (Join-Path $logDir 'tts_start_recovery_stderr.log') | Out-Null
        Write-Host '[tts] Scheduled voice reload for recovered local frozen API.'
    }
}
if (-not $NoBrowser) {
    Start-BrowserMonitor
} else {
    Write-Host 'NoBrowser mode: services stay active until Stop AnimeVoiceTutor.cmd is run.'
}
Write-Host 'You can also use Stop AnimeVoiceTutor.cmd at any time.'
if ((-not $SkipASR -and -not $asrReady) -or (-not $SkipTTS -and -not $ttsReady)) {
    Write-Host 'A voice service needs attention. The text app is still available.'
    exit 2
}
