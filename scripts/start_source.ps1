param(
    [switch]$SkipASR,
    [switch]$SkipTTS,
    [switch]$TextOnly,
    [switch]$NoBrowser
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'load_local_runtime.ps1')
if ($TextOnly) { $SkipASR=$true; $SkipTTS=$true }
if (-not $SkipASR) {
    $override = [Environment]::GetEnvironmentVariable('JVT_ASR_MODEL_PATH')
    $haveExternal = (-not [string]::IsNullOrWhiteSpace($override)) -and (Test-Path -LiteralPath (Join-Path $override 'config.json') -PathType Leaf)
    $haveLocal = (Test-Path -LiteralPath (Join-Path $root 'models\qwen3_asr_0_6b\config.json') -PathType Leaf) -or (Test-Path -LiteralPath (Join-Path $root 'models\qwen3_asr_1_7b\config.json') -PathType Leaf)
    if (-not ($haveExternal -or $haveLocal)) {
        Write-Host 'ASR model not configured; starting without microphone service.'
        $SkipASR=$true
    }
}
if (-not $SkipTTS) {
    $selection=Join-Path $root 'data\app\selected_character.json'
    $characterId='default'
    if (Test-Path -LiteralPath $selection -PathType Leaf) {
        try { $characterId=(Get-Content -LiteralPath $selection -Raw -Encoding UTF8 | ConvertFrom-Json).id } catch { }
    }
    $pack=Join-Path $root ("data\character_packs\"+$characterId)
    $ttsRoot=if ($env:AVT_TTS_ROOT) { $env:AVT_TTS_ROOT } else { Join-Path $root 'external\GPT-SoVITS-v5' }
    # A pack may use its own relative asset names; read the manifest instead
    # of assuming models/gpt.ckpt etc. Missing or invalid packs just disable TTS.
    $hasPackModel=$false
    $manifestPath=Join-Path $pack 'character.json'
    if ($characterId -ne 'default' -and (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        try {
            $manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($manifest.id -eq $characterId -and $null -ne $manifest.voice -and $null -ne $manifest.model) {
                $assets=@($manifest.model.gpt_weights,$manifest.model.sovits_weights,$manifest.model.preset,$manifest.voice.reference_audio_path)
                $hasPackModel=($assets.Count -eq 4)
                $packAbsolute=[IO.Path]::GetFullPath($pack).TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar
                foreach ($asset in $assets) {
                    if ($asset -isnot [string] -or [string]::IsNullOrWhiteSpace($asset) -or $asset.Contains('..') -or $asset.Contains(':') -or $asset.StartsWith('/') -or $asset.StartsWith('\')) { $hasPackModel=$false; break }
                    $resolved=[IO.Path]::GetFullPath((Join-Path $pack ($asset.Replace('/','\'))))
                    if (-not $resolved.StartsWith($packAbsolute,[StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $resolved -PathType Leaf)) { $hasPackModel=$false; break }
                }
            }
        } catch { $hasPackModel=$false }
    }
    if (-not $hasPackModel -or -not (Test-Path -LiteralPath (Join-Path $ttsRoot 'api_v2.py') -PathType Leaf)) {
        Write-Host 'No active character TTS pack; continuing in text or ASR-only mode.'
        $SkipTTS=$true
    }
}
$launchArgs=@{}
if ($SkipASR) { $launchArgs.SkipASR=$true }
if ($SkipTTS) { $launchArgs.SkipTTS=$true }
if ($NoBrowser) { $launchArgs.NoBrowser=$true }
& (Join-Path $PSScriptRoot 'launch_app.ps1') @launchArgs
if ($LASTEXITCODE -is [int]) { exit $LASTEXITCODE }
