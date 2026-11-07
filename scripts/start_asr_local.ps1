param(
    [ValidateSet('quality', 'realtime', 'auto')][string]$Mode = 'auto',
    [switch]$DiagnoseOnly
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')

function Get-ModelDirectory {
    $override = [Environment]::GetEnvironmentVariable('JVT_ASR_MODEL_PATH')
    if ($override) {
        $file = Join-Path $override 'config.json'
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "JVT_ASR_MODEL_PATH does not contain config.json: $override"
        }
        return (Resolve-Path -LiteralPath $override).Path
    }
    $priority = if ($Mode -eq 'quality') { @('qwen3_asr_1_7b') } elseif ($Mode -eq 'realtime') {
        @('qwen3_asr_0_6b')
    } else { @('qwen3_asr_0_6b','qwen3_asr_1_7b') }
    foreach ($folder in $priority) {
        $path = Join-Path $root "models\$folder"
        if (Test-Path -LiteralPath (Join-Path $path 'config.json') -PathType Leaf) {
            return (Resolve-Path -LiteralPath $path).Path
        }
    }
    $candidates = $priority -join ', '
    throw "No complete offline Qwen3-ASR model directory found in models\ ($candidates). A folder alone is not enough; config.json is required. Set JVT_ASR_MODEL_PATH for a different model location."
}

function Test-ASRPython([string]$exe) {
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { return $false }
    $probe = Join-Path $root 'scripts\asr_env_probe.py'
    if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) {
        throw "ASR environment probe missing: $probe. Install the v0.8.2 patch completely."
    }
    # Start the native process without piping stderr through Windows PowerShell 5.1.
    # The old `& python ... 2>&1` could throw NativeCommandError when EAP=Stop,
    # hiding the actual package check and rejecting every candidate.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $exe
    $psi.Arguments = '-B "' + $probe + '"'
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    try {
        if (-not $proc.Start()) {
            Write-Host "ASR candidate could not start: $exe"
            return $false
        }
        $outTask = $proc.StandardOutput.ReadToEndAsync()
        $errTask = $proc.StandardError.ReadToEndAsync()
        if (-not $proc.WaitForExit(20000)) {
            try { $proc.Kill() } catch {}
            Write-Host "ASR candidate timed out (20 seconds): $exe"
            return $false
        }
        $out = $outTask.GetAwaiter().GetResult().Trim()
        $err = $errTask.GetAwaiter().GetResult().Trim()
        if ($out) { Write-Host "ASR candidate $exe : $out" }
        if ($err) { Write-Host "ASR candidate stderr ($exe): $err" }
        if ($proc.ExitCode -eq 0) { return $true }
        Write-Host "ASR candidate failed with exit code $($proc.ExitCode): $exe"
        return $false
    } catch {
        Write-Host "ASR candidate launch error ($exe): $($_.Exception.Message)"
        return $false
    } finally {
        $proc.Dispose()
    }
}

function Find-ASRPython {
    $resolved = & (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role asr
    if ($resolved -and (Test-ASRPython $resolved)) { return $resolved }
    throw 'No validated ASR Python runtime. Run scripts\setup_source.ps1 -Role asr or configure AVT_ASR_PYTHON.'
}

$model = Get-ModelDirectory
$python = Find-ASRPython
Write-Host "ASR model: $model"
Write-Host "ASR Python: $python"
if ($DiagnoseOnly) {
    Write-Host 'ASR preflight succeeded. No service was started.'
    return
}
$env:QWEN_ASR_MODEL = $model
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$env:PYTHONUNBUFFERED = '1'
Write-Host 'Starting Qwen3-ASR at http://127.0.0.1:8766 (loading the model may take a while).'
& $python -u -m uvicorn services.asr_service:app --host 127.0.0.1 --port 8766 --log-level info
if ($LASTEXITCODE -ne 0) { throw "ASR Python exited with code $LASTEXITCODE. Examine the traceback above." }
