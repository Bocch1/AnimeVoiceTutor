param([ValidateSet('web','asr','tts')][string]$Role = 'web')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
$candidates = New-Object 'System.Collections.Generic.List[string]'
function Add-Candidate([string]$path) {
    if (-not [string]::IsNullOrWhiteSpace($path)) { $script:candidates.Add($path) }
}
if ($Role -eq 'tts') {
    Add-Candidate $env:AVT_TTS_PYTHON
    Add-Candidate (Join-Path $root 'runtime\tts\python.exe')
    Add-Candidate (Join-Path $root 'runtime\tts\Scripts\python.exe')
    Add-Candidate (Join-Path $root 'runtime\tts\env\python.exe')
    Add-Candidate (Join-Path $root '.venv_tts\Scripts\python.exe')
    if ($env:CONDA_PREFIX -and (Split-Path -Leaf $env:CONDA_PREFIX) -eq 'jvt-gpt-sovits-v5') {
        Add-Candidate (Join-Path $env:CONDA_PREFIX 'python.exe')
    }
    foreach ($base in @('miniconda3', 'anaconda3', 'Miniconda3', 'Anaconda3')) {
        Add-Candidate (Join-Path $HOME "$base\envs\jvt-gpt-sovits-v5\python.exe")
    }
    # Developer fallback: conda may not live below the user's home directory.
    $conda = Get-Command 'conda.exe' -ErrorAction SilentlyContinue
    if ($conda) {
        try {
            $base = ((& $conda.Source info --base 2>$null) | Select-Object -Last 1).Trim()
            if ($base) { Add-Candidate (Join-Path $base 'envs\jvt-gpt-sovits-v5\python.exe') }
        } catch { }
    }
} else {
    if ($Role -eq 'asr') {
        Add-Candidate $env:AVT_ASR_PYTHON
        Add-Candidate $env:JVT_ASR_PYTHON
        Add-Candidate (Join-Path $root 'runtime\asr\python.exe')
        Add-Candidate (Join-Path $root 'runtime\asr\Scripts\python.exe')
        # Preserve existing local Conda ASR environments before installing new ones.
        if ($env:CONDA_PREFIX -and (Split-Path -Leaf $env:CONDA_PREFIX) -in @('jvt-asr','jvt-qwen-asr')) {
            Add-Candidate (Join-Path $env:CONDA_PREFIX 'python.exe')
        }
        foreach ($base in @('miniconda3','anaconda3','Miniconda3','Anaconda3')) {
            foreach ($name in @('jvt-asr','jvt-qwen-asr')) {
                Add-Candidate (Join-Path $HOME "$base\envs\$name\python.exe")
            }
        }
        $conda = Get-Command 'conda.exe' -ErrorAction SilentlyContinue
        if ($conda) {
            try {
                $base = ((& $conda.Source info --base 2>$null) | Select-Object -Last 1).Trim()
                if ($base) {
                    foreach ($name in @('jvt-asr','jvt-qwen-asr')) {
                        Add-Candidate (Join-Path $base "envs\$name\python.exe")
                    }
                }
            } catch { }
        }
    }
    if ($Role -eq 'web') {
        Add-Candidate $env:AVT_WEB_PYTHON
        Add-Candidate (Join-Path $root 'runtime\web\python.exe')
        Add-Candidate (Join-Path $root 'runtime\web\Scripts\python.exe')
        Add-Candidate (Join-Path $root '.venv\Scripts\python.exe')
    }
}
foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        (Resolve-Path -LiteralPath $candidate).Path
        exit 0
    }
}
throw "No Python runtime for $Role. Provide the appropriate runtime\web or runtime\tts relocatable Python distribution, or install the developer virtual/Conda environment."
