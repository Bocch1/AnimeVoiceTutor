param([string]$RunId = '')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$statePath = Join-Path $root 'data\app\local_services.json'
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
$webPort = [int](& (Join-Path $PSScriptRoot 'web_port.ps1'))
$allowedPorts = @($webPort, 8766, 9880)
if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
    Write-Host 'No managed AnimeVoiceTutor services are recorded.'
    exit 0
}
try {
    $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw "Cannot parse service state: $statePath"
}
# Browser monitors and older exit requests must not stop a newer launch.
if ($RunId -and [string]$state.run_id -ne $RunId) {
    Write-Host 'A newer AnimeVoiceTutor session is active; shutdown skipped.'
    exit 0
}
function Trusted-Listener([string]$serviceName, [string]$commandLine) {
    if (-not $commandLine) { return $false }
    switch ($serviceName) {
        'web' { return ($commandLine -match '(-m\s+voice_tutor\s+serve|uvicorn\s+voice_tutor\.app:app)') }
        'asr' { return ($commandLine -match '(services\.asr_service:app)') }
        'tts' { return ($commandLine -match '(^|[\\/])api_v2\.py(\s|$)') }
        default { return $false }
    }
}
function Stop-OwnedProcess([int]$ProcessId, [string]$Label) {
    # Stop-Process is idempotent and does not produce taskkill /T stale-child errors.
    try {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
    } catch {
        if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
            Write-Warning "Could not stop $Label (PID $ProcessId): $($_.Exception.Message)"
            return $false
        }
    }
    for ($wait = 0; $wait -lt 15; $wait++) {
        if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 180
    }
    Write-Warning "$Label still appears active (PID $ProcessId)."
    return $false
}
function Stop-OwnedTree([int]$ProcessId, [string]$Label) {
    # Kill descendants of a verified Python listener without surfacing benign
    # taskkill diagnostics about children that have already exited.
    try {
        $start = New-Object System.Diagnostics.ProcessStartInfo
        $start.FileName = 'taskkill.exe'
        $start.Arguments = "/PID $ProcessId /T /F"
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $killer = [System.Diagnostics.Process]::Start($start)
        $null = $killer.StandardOutput.ReadToEnd()
        $null = $killer.StandardError.ReadToEnd()
        $killer.WaitForExit()
        $killer.Dispose()
    } catch {
        Write-Host "Tree stop unavailable for $Label, trying a direct process stop."
    }
    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return $true }
    return Stop-OwnedProcess $ProcessId $Label
}
$failures = @()
$entries = @($state.processes | Where-Object { $null -ne $_ -and $null -ne $_.pid })
# Stop the actual managed Python listeners before stopping their launcher shells.
foreach ($entry in @($entries | Where-Object { $_.kind -eq 'listener' } | Sort-Object { if ($_.name -eq 'web') { 1 } else { 0 } })) {
    ${avtProcessId} = [int]$entry.pid
    $port = [int]$entry.port
    if (${avtProcessId} -lt 4 -or $port -notin $allowedPorts -or
        ($entry.name -eq 'web' -and $port -ne $webPort) -or
        ($entry.name -ne 'web' -and $port -eq $webPort)) { continue }
    $listener = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -eq ${avtProcessId} })
    if ($listener.Count -eq 0) { continue }
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=${avtProcessId}" -ErrorAction SilentlyContinue
    if (-not $procInfo -or $procInfo.Name -notmatch '^python(w)?\.exe$' -or
        -not (Trusted-Listener ([string]$entry.name) ([string]$procInfo.CommandLine))) {
        Write-Warning "Skipped listener PID ${avtProcessId}: process identity did not match."
        $failures += "listener ${avtProcessId} (identity mismatch)"
        continue
    }
    Write-Host "Stopping $($entry.name) Python listener on $port (PID ${avtProcessId})"
    # Never kill the Web process tree: the exit helper is a child of Web.
    # Stop Web last and directly so the helper survives to finish cleanup.
    if ($entry.name -eq 'web') {
        if (-not (Stop-OwnedProcess ${avtProcessId} $entry.name)) { $failures += "listener ${avtProcessId}" }
    } elseif (-not (Stop-OwnedTree ${avtProcessId} $entry.name)) {
        $failures += "listener ${avtProcessId}"
    }
}
foreach ($entry in @($entries | Where-Object { $_.kind -ne 'listener' })) {
    ${avtProcessId} = [int]$entry.pid
    if (${avtProcessId} -lt 4) { continue }
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId=${avtProcessId}" -ErrorAction SilentlyContinue
    if (-not $procInfo) { continue }
    if ($procInfo.Name -notmatch '^powershell\.exe$') { continue }
    $leaf = [System.IO.Path]::GetFileName([string]$entry.script)
    if (-not $leaf -or -not $procInfo.CommandLine -or
        $procInfo.CommandLine.IndexOf($leaf, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        Write-Host "Skipped stale launcher PID ${avtProcessId}: identity did not match."
        continue
    }
    Write-Host "Stopping $($entry.name) launcher (PID ${avtProcessId})"
    if (-not (Stop-OwnedProcess ${avtProcessId} $entry.name)) { $failures += "launcher ${avtProcessId}" }
}
# Before clearing the state, verify that none of the previously recorded Python
# listeners still owns its port. Unknown port occupants are never terminated.
foreach ($entry in @($entries | Where-Object { $_.kind -eq 'listener' })) {
    ${avtProcessId} = [int]$entry.pid
    $port = [int]$entry.port
    if (${avtProcessId} -lt 4 -or $port -notin $allowedPorts -or
        ($entry.name -eq 'web' -and $port -ne $webPort) -or
        ($entry.name -ne 'web' -and $port -eq $webPort)) { continue }
    $remaining = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -eq ${avtProcessId} })
    if ($remaining.Count -gt 0) { $failures += "port $port PID ${avtProcessId}" }
}
if ($failures.Count -gt 0) {
    Write-Warning ('Incomplete shutdown: ' + (($failures | Select-Object -Unique) -join ', '))
    throw 'Some managed processes remain. Service state was retained for a retry.'
}
# Do not delete a new run's state during concurrent restart.
try {
    $current = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$current.run_id -eq [string]$state.run_id) {
        Remove-Item -LiteralPath $statePath -Force -ErrorAction Stop
    }
} catch {
    Write-Warning 'Services stopped, but their state file could not be cleaned up.'
}
Write-Host 'AnimeVoiceTutor managed services stopped.' -ForegroundColor Green
