param([Parameter(Mandatory=$true)][string]$RunId, [int]$WebPort = 0)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$statePath = Join-Path $root 'data\app\local_services.json'
$stopScript = Join-Path $PSScriptRoot 'stop_app.ps1'
if ($WebPort -ge 1024 -and $WebPort -le 65535 -and $WebPort -notin @(8766,9880)) {
    $webPort = $WebPort
} else {
    $webPort = [int](& (Join-Path $PSScriptRoot 'web_port.ps1'))
}
$webBase = "http://127.0.0.1:$webPort"
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$startedAt = Get-Date
$connectedOnce = $false
$lastWebResponse = Get-Date
Write-Output "Browser monitor started for instance $RunId"
while ($true) {
    if (-not (Test-Path -LiteralPath $statePath)) { break }
    try {
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]$state.run_id -ne $RunId) { break }
    } catch { break }
    $presence = $null
    try {
        $presence = Invoke-RestMethod "$webBase/api/browser/presence" -TimeoutSec 3 -ErrorAction Stop
        $lastWebResponse = Get-Date
    } catch {
        # If the browser window never loaded, do not leave a GPU-heavy server forever.
        # If Web vanished, clean up the other managed services too.
        if (((Get-Date) - $startedAt).TotalSeconds -gt 180 -and -not $connectedOnce) {
            Write-Output 'No browser ever connected; stopping managed services.'
            & $stopScript -RunId $RunId
            break
        }
        if ($connectedOnce -and ((Get-Date) - $lastWebResponse).TotalSeconds -gt 30) {
            Write-Output 'Web service unavailable; stopping managed services.'
            & $stopScript -RunId $RunId
            break
        }
        Start-Sleep -Seconds 5
        continue
    }
    if ($presence.ever_connected) { $connectedOnce = $true }
    if ($connectedOnce -and ([int]$presence.active_clients -eq 0) -and
        ($null -ne $presence.inactive_seconds) -and
        ([double]$presence.inactive_seconds -ge 20)) {
        Write-Output 'Last AnimeVoiceTutor browser tab closed; stopping managed services.'
        & $stopScript -RunId $RunId
        break
    }
    if (-not $connectedOnce -and ((Get-Date) - $startedAt).TotalSeconds -gt 180) {
        Write-Output 'No browser connected during startup; stopping managed services.'
        & $stopScript -RunId $RunId
        break
    }
    Start-Sleep -Seconds 5
}
Write-Output 'Browser monitor finished.'
