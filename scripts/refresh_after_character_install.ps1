# First Run imports with a separate Python process. Refresh a running managed
# Web instance's voice state and model; otherwise the next Start loads the pack.
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$statePath=Join-Path $root 'data\app\local_services.json'
$selectedPath=Join-Path $root 'data\app\selected_character.json'
if(-not (Test-Path -LiteralPath $selectedPath -PathType Leaf)){throw 'CHARACTER_SELECTION_MISSING'}
$character=[string]((Get-Content -LiteralPath $selectedPath -Raw -Encoding UTF8|ConvertFrom-Json).id)
if(-not (Test-Path -LiteralPath $statePath -PathType Leaf)){
    Write-Host 'CHARACTER_SELECTED: Voice model loads when the application starts.'
    return
}
try{$state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json}catch{
    Write-Warning 'Existing Web service record could not be parsed; start the application to load the model.'
    return
}
$web=@($state.processes|Where-Object{$_.name -eq 'web' -and $_.kind -eq 'listener'})
if($web.Count -ne 1 -or -not (Get-Process -Id ([int]$web[0].pid) -ErrorAction SilentlyContinue)){
    Write-Host 'CHARACTER_SELECTED: No running managed Web instance; Start will load the model.'
    return
}
try{
    & (Join-Path $PSScriptRoot 'refresh_character_tts.ps1') -RunId ([string]$state.run_id) -CharacterId $character
    if(-not $?){throw 'TTS_RELOAD_FAILED'}
}catch{
    # The role was installed, but report the voice loading failure separately.
    Write-Warning ('CHARACTER_INSTALLED_BUT_TTS_NOT_READY: '+$_.Exception.Message)
    Write-Host 'Use the in-app service status and data\logs\tts_stderr.log to diagnose.'
}
