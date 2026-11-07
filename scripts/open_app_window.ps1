param([string]$Url = '')
$ErrorActionPreference = 'Stop'
if (-not $Url) { $webPort = [int](& (Join-Path $PSScriptRoot 'web_port.ps1')); $Url = "http://127.0.0.1:$webPort" }
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$candidates = @()
foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)) {
    if ($base) { $candidates += (Join-Path $base 'Microsoft\Edge\Application\msedge.exe') }
}
if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe') }
$browser = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if ($browser) {
    # App mode uses a dedicated window; the browser binary itself is not bundled.
    $profile = Join-Path $root 'data\browser_profile'
    New-Item -Path $profile -ItemType Directory -Force | Out-Null
    $args = "--app=$Url --user-data-dir=`"$profile`" --no-first-run"
    Start-Process -FilePath $browser -ArgumentList $args | Out-Null
} else {
    Start-Process $Url | Out-Null
}
