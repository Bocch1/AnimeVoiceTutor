# Non-interactive, hidden Windows launcher for normal desktop usage.
# Keep detailed diagnostics in a local transcript rather than a console window.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$logDir = Join-Path $root 'data\logs'
New-Item -Path $logDir -ItemType Directory -Force | Out-Null
$logPath = Join-Path $logDir 'desktop_start.log'
$transcribing = $false
$mutex = $null
$mutexOwned = $false
$failure = 0
try {
    Start-Transcript -Path $logPath -Append -ErrorAction Stop | Out-Null
    $transcribing = $true
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($root.ToLowerInvariant())
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').Substring(0, 24) }
    finally { $sha.Dispose() }
    $mutex = New-Object System.Threading.Mutex($false, ('Local\AVT_START_' + $hash))
    try {
        $mutexOwned = $mutex.WaitOne(180000)
    } catch [System.Threading.AbandonedMutexException] {
        $mutexOwned = $true
    }
    if (-not $mutexOwned) { throw 'Another AnimeVoiceTutor launch is taking too long. Check desktop_start.log.' }
    Write-Host ('Desktop launch: ' + [DateTime]::UtcNow.ToString('o'))
    $global:LASTEXITCODE = 0
    & (Join-Path $PSScriptRoot 'start_source.ps1')
    if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
        if ($LASTEXITCODE -eq 2) {
            Write-Host 'Web opened but a voice service needs attention.'
            $failure = 2
        } else {
            throw "Startup returned exit code $LASTEXITCODE. Check data\logs for service details."
        }
    }
} catch {
    $failure = 1
    try { Write-Host ('DESKTOP_START_FAILED: ' + $_.Exception.ToString()) } catch { }
    try {
        [IO.File]::AppendAllText($logPath, ('DESKTOP_START_FAILED: ' + $_.Exception.ToString() + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    } catch { }
} finally {
    if ($mutexOwned -and $null -ne $mutex) { try { $mutex.ReleaseMutex() } catch {} }
    if ($null -ne $mutex) { $mutex.Dispose() }
    if ($transcribing) { try { Stop-Transcript | Out-Null } catch {} }
}
exit $failure
