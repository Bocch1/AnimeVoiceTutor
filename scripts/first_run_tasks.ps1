<# Two-stage, voice-first setup for Windows x64 (NVIDIA CUDA target).
   All character assets come from separately downloaded, trusted ZIP files.
   Do not run from an incomplete patch payload directory.
#>
param(
    [ValidateSet('base','character','character_release','list_characters','diagnostics','voice_test','capture')][string]$Stage = 'base',
    [ValidateSet('zh-CN','en','ja')][string]$Language = 'en',
    [ValidateSet('0.6B','1.7B')][string]$AsrModel = '1.7B',
    [ValidateSet('existing','download')][string]$EngineAction = 'download',
    [string]$EngineFolder = '',
    [string]$CharacterZip = '',
    [string]$ReleasesUrl = '',
    [int]$AssetId = 0,
    [string]$ExistingAsrFolder = '',
    [switch]$ApplyOverlay,
    [string]$EnginePatchZip = '',
    [string]$EnginePatchUrl = '',
    [switch]$DownloadPretrained,
    [switch]$InstallFFmpeg,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$setup=Join-Path $PSScriptRoot 'quick_setup.ps1'
$asr=Join-Path $PSScriptRoot 'download_asr_model.ps1'
$preflight=Join-Path $PSScriptRoot 'first_run_preflight.ps1'
$baselinePath=Join-Path $root 'release\install_specs\voice_baseline.json'
$installer=Join-Path $root 'tools\install_and_select_character.py'
$pretrained=Join-Path $root 'tools\install_tts_pretrained.py'
$github=Join-Path $root 'tools\github_character_release.py'
$fetchEngine=Join-Path $root 'tools\fetch_pinned_engine.py'
$overlayTool=Join-Path $root 'tools\apply_engine_overlay.py'
# Reuse the same Web Python interpreter as Doctor and the normal launcher.
# Existing developer installs commonly use .venv instead of runtime/web.
$webPython=$null
foreach($needed in @($setup,$asr,$preflight,$baselinePath,$installer,$pretrained,$github,$fetchEngine,$overlayTool,(Join-Path $root 'release\public_source_files.txt'))){
    if(-not (Test-Path -LiteralPath $needed -PathType Leaf)){
        throw ('INCOMPLETE_SOURCE_DIRECTORY: '+$needed+'. Extract the complete Core ZIP; never launch the patch payload directly.')
    }
}
$base=Get-Content -LiteralPath $baselinePath -Encoding UTF8 -Raw|ConvertFrom-Json
$messages=@{
 'base_start'=@{'zh-CN'='正在安装基础语音环境';en='Installing voice base';ja='音声環境をインストールしています'}
 'base_done'=@{'zh-CN'='基础环境检查通过，安装完成';en='Voice base verification passed; installation complete';ja='音声環境の診断に合格しました。インストール完了'}
 'character_start'=@{'zh-CN'='正在导入角色包';en='Importing character ZIP';ja='キャラクター ZIP を導入しています'}
 'character_done'=@{'zh-CN'='角色已导入并选中。启动应用后测试语音';en='Character installed and selected. Start the app, then test voice';ja='キャラクターを選択しました。アプリ起動後、音声をテストしてください'}
 'external'=@{'zh-CN'='第三方安装器的详细日志可能使用英语';en='Third-party installer output may be in English';ja='外部インストーラーの詳細ログは英語の場合があります'}
}
function Say([string]$key){Write-Host ('[{0}] {1}' -f $Language,$messages[$key][$Language])}
function Exec-PS([string]$scriptPath,[hashtable]$arguments){
    & $scriptPath @arguments
    if(-not $?){throw ('STEP_FAILED: '+[IO.Path]::GetFileName($scriptPath))}
}
function Set-Engine([string]$path){
    if(-not (Test-Path -LiteralPath (Join-Path $path 'api_v2.py') -PathType Leaf)){throw 'ENGINE_INVALID: api_v2.py not found'}
    $resolved=(Resolve-Path -LiteralPath $path).Path
    $target=Join-Path $root '.avt-local.ps1'
    $lines=@()
    if(Test-Path -LiteralPath $target -PathType Leaf){$lines=@(Get-Content -LiteralPath $target -Encoding UTF8|Where-Object{$_ -notmatch '^\s*\$env:AVT_TTS_ROOT\s*='})}
    $lines+=('$env:AVT_TTS_ROOT = '''+$resolved.Replace("'","''")+'''')
    $tmp=$target+'.tmp'
    [IO.File]::WriteAllLines($tmp,[string[]]$lines,[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $target -Force
    Write-Host ('ENGINE_SOURCE_CONFIGURED: '+$resolved)
}
if($Stage -eq 'diagnostics'){
    & (Join-Path $PSScriptRoot 'diagnose_voice_base.ps1')
    if(-not $?){throw 'VOICE_BASE_DIAGNOSTICS_FAILED'}
    return
}
if($Stage -eq 'capture'){
    $params=@{}
    if($EngineFolder){$params.EngineFolder=$EngineFolder}
    & (Join-Path $PSScriptRoot 'capture_voice_baseline.ps1') @params
    return
}
if($Stage -eq 'voice_test'){
    & (Join-Path $PSScriptRoot 'test_source.ps1') -Voice
    if(-not $?){throw 'VOICE_SMOKE_TEST_FAILED'}
    return
}
if($Stage -eq 'character'){
    if(-not $CharacterZip -or -not (Test-Path -LiteralPath $CharacterZip -PathType Leaf)){throw 'CHARACTER_ZIP_REQUIRED'}
    if($DryRun){Write-Host 'DRY_RUN_OK: character ZIP is present';return}
    $webPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web | Select-Object -Last 1)
    if(-not $webPython -or -not (Test-Path -LiteralPath $webPython -PathType Leaf)){throw 'WEB_RUNTIME_MISSING: Install Base first'}
    Say 'character_start'
    & $webPython $installer $CharacterZip --select
    if($LASTEXITCODE -ne 0){throw 'CHARACTER_IMPORT_FAILED'}
    & (Join-Path $PSScriptRoot 'refresh_after_character_install.ps1')
    Write-Host 'STEP_2_CHARACTER_IMPORT_COMPLETE'
    Say 'character_done'
    return
}
# Character Release download is deliberately separate from environment installation.
if($Stage -in @('list_characters','character_release')){
    if($ReleasesUrl -notmatch '^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/releases/?$'){
        throw 'INVALID_GITHUB_RELEASES_URL'
    }
    $webPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web | Select-Object -Last 1)
    if(-not $webPython -or -not (Test-Path -LiteralPath $webPython -PathType Leaf)){throw 'WEB_RUNTIME_MISSING: Install Base first'}
    if($Stage -eq 'list_characters'){
        $listing=@(& $webPython $github --releases-url $ReleasesUrl --list)
        if($LASTEXITCODE -ne 0){throw 'GITHUB_CHARACTER_LIST_FAILED'}
        $jsonText=($listing -join [Environment]::NewLine)
        $assets=$jsonText|ConvertFrom-Json
        $folder=Join-Path $root 'data\app'
        New-Item -ItemType Directory -Path $folder -Force|Out-Null
        [IO.File]::WriteAllText((Join-Path $folder 'available_character_releases.json'),$jsonText,[Text.UTF8Encoding]::new($false))
        Write-Host ('CHARACTERS_DISCOVERED: '+@($assets).Count)
        return
    }
    if($AssetId -le 0){throw 'CHARACTER_RELEASE_ASSET_NOT_SELECTED'}
    if($DryRun){Write-Host 'CHARACTER_RELEASE_DRY_RUN';return}
    $downloadDir=Join-Path $root 'data\downloads\characters'
    & $webPython $github --releases-url $ReleasesUrl --asset-id $AssetId --download-dir $downloadDir --install-and-select
    if($LASTEXITCODE -ne 0){throw 'CHARACTER_RELEASE_INSTALL_FAILED'}
    & (Join-Path $PSScriptRoot 'refresh_after_character_install.ps1')
    Write-Host 'STEP_2_CHARACTER_IMPORT_COMPLETE'
    Say 'character_done'
    return
}
if($EngineAction -eq 'existing'){
    if(-not $EngineFolder -or -not (Test-Path -LiteralPath (Join-Path $EngineFolder 'api_v2.py') -PathType Leaf)){throw 'ENGINE_PATH_INVALID'}
}else{
    if($EngineFolder){throw 'ENGINE_MANAGED_LOCATION_REQUIRED'}
    $EngineFolder=Join-Path $root 'external\GPT-SoVITS-v5'
}
if($DryRun){Write-Host "DRY_RUN_OK: model=$AsrModel engine=$EngineAction pretrained=$DownloadPretrained ffmpeg=$InstallFFmpeg";return}
# This supported accelerated profile requires NVIDIA. Stop BEFORE downloading gigabytes.
& $preflight -Strict
if(-not $?){throw 'PREFLIGHT_FAILED'}
Say 'base_start';Say 'external'
& $setup -Mode full
if(-not $?){throw 'RUNTIME_INSTALL_FAILED'}
# Resolve the Web runtime only AFTER the installer has created it.
$webPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web | Select-Object -Last 1)
if(-not $webPython -or -not (Test-Path -LiteralPath $webPython -PathType Leaf)){throw 'WEB_RUNTIME_MISSING_AFTER_INSTALL'}
if($ExistingAsrFolder){
    if(-not (Test-Path -LiteralPath (Join-Path $ExistingAsrFolder 'config.json') -PathType Leaf)){
        throw 'LOCAL_ASR_MODEL_INVALID'
    }
    $asrPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role asr | Select-Object -Last 1)
    & $asrPython (Join-Path $root 'tools\check_local_asr_model.py') $ExistingAsrFolder
    if($LASTEXITCODE -ne 0){throw 'LOCAL_ASR_MODEL_INCOMPLETE'}
    Write-Host ('USING_EXISTING_ASR_MODEL: '+$ExistingAsrFolder)
}else{
    & $asr -Model $AsrModel
    if(-not $?){throw 'ASR_DOWNLOAD_FAILED'}
}
if($EngineAction -eq 'download'){
    $revision=[string]$base.tts_engine.reference
    if($revision -notmatch '^[a-f0-9]{7,40}$'){throw 'INVALID_PINNED_ENGINE_REFERENCE'}
    if(-not (Test-Path -LiteralPath (Join-Path $EngineFolder 'api_v2.py') -PathType Leaf)){
        if(Test-Path -LiteralPath $EngineFolder){throw 'ENGINE_DESTINATION_NOT_EMPTY: cannot overwrite existing folder'}
        New-Item -ItemType Directory -Path (Split-Path -Parent $EngineFolder) -Force|Out-Null
        Write-Host ('FETCH_PINNED_GPT_SOVITS: '+$revision)
        & $webPython $fetchEngine --destination $EngineFolder --commit $revision
        if($LASTEXITCODE -ne 0){throw 'PINNED_ENGINE_DOWNLOAD_FAILED'}
    }
    $marker=Join-Path $EngineFolder '.avt_engine_source.json'
    if(Test-Path -LiteralPath $marker){
        $actual=[string](Get-Content -LiteralPath $marker -Raw -Encoding UTF8|ConvertFrom-Json).commit
    }elseif(Test-Path -LiteralPath (Join-Path $EngineFolder '.git')){
        $actual=((& git.exe -C $EngineFolder rev-parse HEAD)|Select-Object -Last 1).Trim()
    }else{throw 'MANAGED_ENGINE_VERSION_UNVERIFIED'}
    if(-not $actual.StartsWith($revision,[StringComparison]::OrdinalIgnoreCase)){
        throw ('ENGINE_REVISION_MISMATCH: got '+$actual+', expected '+$revision)
    }
    Write-Host ('PINNED_ENGINE_REVISION_OK: '+$actual)
}
Set-Engine $EngineFolder
if($ExistingAsrFolder){
    $target=Join-Path $root '.avt-local.ps1'
    $lines=@(Get-Content -LiteralPath $target -Encoding UTF8|Where-Object{$_ -notmatch '^\s*\$env:JVT_ASR_MODEL_PATH\s*='})
    $lines+=('$env:JVT_ASR_MODEL_PATH = '''+([IO.Path]::GetFullPath($ExistingAsrFolder)).Replace("'","''")+'''')
    [IO.File]::WriteAllLines($target,[string[]]$lines,[Text.UTF8Encoding]::new($false))
}
if($ApplyOverlay){
    if(-not $EnginePatchZip -and -not $EnginePatchUrl){throw 'ENGINE_OVERLAY_SOURCE_REQUIRED'}
    if($EnginePatchZip -and $EnginePatchUrl){throw 'SELECT_ONLY_ONE_OVERLAY_SOURCE'}
    $archive=$EnginePatchZip
    if($EnginePatchUrl){
        if($EnginePatchUrl -notmatch '^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/releases/download/[^/\s]+/[A-Za-z0-9_.-]+\.zip$'){
            throw 'ENGINE_OVERLAY_URL_MUST_BE_GITHUB_RELEASE_ASSET'
        }
        $folder=Join-Path $root 'data\downloads\engine_overlays'
        New-Item -ItemType Directory -Path $folder -Force|Out-Null
        $archive=Join-Path $folder ('overlay_'+[guid]::NewGuid().ToString('N')+'.zip')
        Invoke-WebRequest -Uri $EnginePatchUrl -OutFile $archive -UseBasicParsing
    }
    & $webPython $overlayTool --archive $archive --engine $EngineFolder --dry-run
    if($LASTEXITCODE -ne 0){throw 'ENGINE_OVERLAY_PREVIEW_FAILED'}
    & $webPython $overlayTool --archive $archive --engine $EngineFolder
    if($LASTEXITCODE -ne 0){throw 'ENGINE_OVERLAY_APPLY_FAILED'}
    Write-Host 'ENGINE_OVERLAY_APPLIED_WITH_BACKUP'
}
if($DownloadPretrained){
    if($EngineAction -eq 'existing'){
        Write-Warning 'EXISTING_ENGINE_UNCHANGED: Skipping pretrained download into a shared external engine. Configure it separately if resources are missing.'
    }elseif((Test-Path -LiteralPath (Join-Path $EngineFolder 'GPT_SoVITS\pretrained_models') -PathType Container) -and
           @((Get-ChildItem -LiteralPath (Join-Path $EngineFolder 'GPT_SoVITS\pretrained_models') -Recurse -File -ErrorAction SilentlyContinue)).Count -gt 0){
        Write-Warning 'PRETRAINED_PRESENT_UNVERIFIED: Existing files were not overwritten; verify them before using TTS.'
    }else{
        $ttsPython=(& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role tts|Select-Object -Last 1)
        & $ttsPython $pretrained --engine $EngineFolder
        if($LASTEXITCODE -ne 0){throw 'PRETRAINED_DOWNLOAD_FAILED'}
    }
}
if(-not (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)){
    if($InstallFFmpeg){
        if(-not (Get-Command winget.exe -ErrorAction SilentlyContinue)){
            Write-Warning 'WINGET_MISSING: Install App Installer or FFmpeg manually.'
        }else{
            $ffmpegVersion=[string]$base.ffmpeg.winget_version
            Write-Host ('INSTALL_FFMPEG_FROM_WINGET: Gyan.FFmpeg '+$ffmpegVersion)
            & winget.exe install --exact --id Gyan.FFmpeg --version $ffmpegVersion --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
            if($LASTEXITCODE -ne 0){Write-Warning 'FFMPEG_WINGET_FAILED: Use the official FFmpeg distribution and restart your terminal.'}
            else {
                # winget may update the user/machine PATH after this process started.
                # Refresh it before the strict post-install diagnosis runs.
                $machinePath=[Environment]::GetEnvironmentVariable('Path','Machine')
                $userPath=[Environment]::GetEnvironmentVariable('Path','User')
                if($machinePath -or $userPath){$env:Path=($machinePath+';'+$userPath+';'+$env:Path)}
            }
        }
    }
    if(-not (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)){
        Write-Warning 'FFMPEG_NOT_ON_PATH: Reopen the application after installing FFmpeg/FFprobe. Voice readiness is not confirmed.'
    }
}
& (Join-Path $PSScriptRoot 'diagnose_voice_base.ps1')
if(-not $?){throw 'VOICE_BASE_INCOMPLETE: Run Install again or review the failed component'}
Write-Host 'STEP_1_BASE_SETUP_COMPLETE'
Say 'base_done'
Write-Host 'REPRODUCIBILITY_NOTE: Installed ASR and upstream pretrained assets are receipted but NOT pinned to verified developer hashes. Run Capture baseline on the original machine.'
