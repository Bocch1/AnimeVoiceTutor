# Install uv from an established package manager if it is not already available.
$ErrorActionPreference = 'Stop'
function Find-Uv {
    $cmd = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($cmd -and (Test-Path -LiteralPath $cmd.Source -PathType Leaf)) { return $cmd.Source }
    foreach ($path in @(
        (Join-Path $HOME '.local\bin\uv.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\uv.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\uv\uv.exe')
    )) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) { return $path }
    }
    return ''
}
function First-FoundUv { param([string]$BasePath)
    if ($BasePath) {
        foreach ($p in @((Join-Path $BasePath 'Scripts\uv.exe'), (Join-Path $BasePath 'bin\uv.exe'))) {
            if (Test-Path -LiteralPath $p -PathType Leaf) { return $p }
        }
    }
    return ''
}

$located = Find-Uv
if ($located) { Write-Output $located; return }
$winget = Get-Command winget.exe -ErrorAction SilentlyContinue
if ($winget) {
    Write-Host 'Installing uv through the official WinGet package...' -ForegroundColor Cyan
    & $winget.Source install --id astral-sh.uv --exact --source winget --accept-package-agreements --accept-source-agreements | Out-Host
    $located = Find-Uv
    if ($located) { Write-Output $located; return }
    Write-Warning 'WinGet completed but uv.exe is not visible in this session.'
}
$py = Get-Command py.exe -ErrorAction SilentlyContinue
$python = Get-Command python.exe -ErrorAction SilentlyContinue
$launcher = if ($py) { $py.Source } elseif ($python) { $python.Source } else { '' }
if ($launcher) {
    Write-Host 'Installing uv using pip in the existing Python installation...' -ForegroundColor Cyan
    & $launcher -m pip install --user uv | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'pip install uv failed' }
    $userBase = (& $launcher -c 'import site; print(site.USER_BASE)') | Select-Object -Last 1
    $located = First-FoundUv -BasePath $userBase
    if ($located) { Write-Output $located; return }
    $located = Find-Uv
    if ($located) { Write-Output $located; return }
}
throw 'Could not find uv.exe. Install uv from https://docs.astral.sh/uv/getting-started/installation/ and run Setup again.'

