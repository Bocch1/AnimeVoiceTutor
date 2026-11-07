# Verify that a port 9880 Python listener was launched by this checkout's
# frozen GPT-SoVITS launcher, even if its state record was lost.
# This does NOT stop processes. Parent provenance is mandatory for recovery.
function Test-LocalFrozenTtsProvenance {
    param(
        [Parameter(Mandatory=$true)][int]$ListenerPid,
        [Parameter(Mandatory=$true)][string]$ExpectedPython,
        [Parameter(Mandatory=$true)][string]$ProjectRoot
    )
    if ($ListenerPid -lt 4 -or -not (Test-Path -LiteralPath $ExpectedPython -PathType Leaf)) { return $false }
    $portOwners = @(Get-NetTCPConnection -State Listen -LocalPort 9880 -ErrorAction SilentlyContinue |
        Where-Object { [int]$_.OwningProcess -eq $ListenerPid })
    if ($portOwners.Count -eq 0) { return $false }
    $child = Get-CimInstance Win32_Process -Filter "ProcessId=$ListenerPid" -ErrorAction SilentlyContinue
    if (-not $child -or $child.Name -notmatch '^python(w)?\.exe$' -or -not $child.ExecutablePath) { return $false }
    if (-not [string]::Equals([IO.Path]::GetFullPath([string]$child.ExecutablePath),
                             [IO.Path]::GetFullPath($ExpectedPython),
                             [StringComparison]::OrdinalIgnoreCase)) { return $false }
    $argsLine = [string]$child.CommandLine
    # Require this app's exact API invocation, not a generic Python service.
    if ($argsLine -notmatch '(?i)(?:^|\s)-s\s+\.?[\\/]api_v2\.py(?:\s|$)' -or
        $argsLine -notmatch '(?i)(?:^|\s)-a\s+127\.0\.0\.1(?:\s|$)' -or
        $argsLine -notmatch '(?i)(?:^|\s)-p\s+9880(?:\s|$)' -or
        $argsLine -notmatch '(?i)(?:^|\s)-c\s+\.?[\\/]TEMP[\\/]jvt_frozen_tts_api\.yaml(?:\s|$)') { return $false }
    $parentId = [int]$child.ParentProcessId
    if ($parentId -lt 4 -or $parentId -eq $ListenerPid) { return $false }
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$parentId" -ErrorAction SilentlyContinue
    if (-not $parent -or $parent.Name -notmatch '^(powershell|pwsh)\.exe$') { return $false }
    $expectedLauncher = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'scripts\start_tts_api_frozen.ps1'))
    $pattern = '(?i)(?:^|\s)-File\s+"?' + [regex]::Escape($expectedLauncher) + '(?:"|\s|$)'
    if ([string]$parent.CommandLine -notmatch $pattern) { return $false }
    # Reject a recycled parent PID when creation timestamps are available.
    if ($null -ne $child.CreationDate -and $null -ne $parent.CreationDate -and
        $parent.CreationDate -gt $child.CreationDate) { return $false }
    return $true
}
