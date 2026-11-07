# Windows Forms setup. Save as UTF-8 with BOM for Windows PowerShell 5.1.
$ErrorActionPreference='Stop'
if([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitOperatingSystem){throw 'Windows x64 is required'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$required=@('scripts\quick_setup.ps1','scripts\first_run_tasks.ps1','scripts\first_run_preflight.ps1','release\install_specs\voice_baseline.json','tools\install_and_select_character.py','release\public_source_files.txt')
foreach($rel in $required){
    if(-not(Test-Path -LiteralPath (Join-Path $root $rel) -PathType Leaf)){
        [System.Windows.Forms.MessageBox]::Show(('Incomplete Core directory. Extract full Core ZIP, not patch payload: '+$rel),'Incomplete Core')|Out-Null
        exit 2
    }
}
$script:taskProcess=$null
$script:taskLog=''
$script:lastOutput=''
$logDir=Join-Path $root 'data\logs\first_run'
[IO.Directory]::CreateDirectory($logDir)|Out-Null
$script:lang=if([System.Globalization.CultureInfo]::CurrentUICulture.Name -match '^zh'){'zh-CN'}elseif([System.Globalization.CultureInfo]::CurrentUICulture.Name -match '^ja'){'ja'}else{'en'}
$script:translations=@{}

$script:translations['en'] = @{
    'window' = 'AnimeVoiceTutor | First Run Setup'
    'lang' = 'Language'
    'title' = 'AnimeVoiceTutor · Voice setup'
    'subtitle' = 'One base installation, then download a character ZIP from GitHub Releases.'
    'step1' = 'STEP 1 · Install voice environment'
    'desc1' = 'Sets up Web, ASR and TTS environments, Qwen3-ASR, GPT-SoVITS and optional pretrained resources.'
    'model' = 'Qwen3-ASR model'
    'download' = 'Auto-download pinned GPT-SoVITS v5 source'
    'existing' = 'Use existing compatible GPT-SoVITS engine'
    'browse' = 'Browse...'
    'upstream' = 'Download upstream pretrained models (large; requires network)'
    'constraints' = 'Windows x64 + NVIDIA CUDA 12.8 is the validated target. Installation and models require disk space.'
    'install' = 'Install voice base'
    'doctor' = 'Diagnostics'
    'capture' = 'Capture engine baseline'
    'step2' = 'STEP 2 · Download and install character ZIP'
    'desc2' = 'Visit this project''s GitHub Releases, download a trusted character ZIP, and import it below.'
    'releases' = 'Releases URL'
    'open' = 'Open Releases'
    'zip' = 'Character ZIP file'
    'choose' = 'Choose ZIP'
    'import' = 'Import and activate'
    'start' = 'Start AnimeVoiceTutor'
    'test' = 'Test live voice'
    'close' = 'Close'
    'closeerror' = 'The setup window could not close normally. See the local log for details.'
    'ready' = 'Ready for installation or environment diagnostics.'
    'running' = 'Running. View the log below.'
    'ok' = 'Completed successfully.'
    'fail' = 'Step failed. Read the log for the cause.'
    'wrongdir' = 'Incomplete Core directory. Extract the entire Core ZIP, not the patch payload. Missing: '
    'badurl' = 'Enter the GitHub repository Releases URL first.'
    'badpath' = 'Choose an engine folder containing api_v2.py.'
    'badzip' = 'Select an existing ZIP from Releases.'
    'confirmbase' = 'The base installer downloads Python dependencies and models. Continue?'
    'confirmpack' = 'Install this trusted character ZIP? Model weight files may execute unsafe code.'
    'busy' = 'Installation is still running; closing is disabled.'
    'nosmoke' = 'Start the application and select a character before testing live speech.'
    'pretrainNote' = 'The official pretrained asset is not yet pinned by a verified SHA-256; a receipt will be saved.'
    'advanced' = 'Advanced options'
    'available' = 'Available characters'
    'refresh' = 'Refresh releases'
    'downloadInstall' = 'Download and install selected character'
    'asrLocal' = 'Existing ASR model directory (optional)'
    'patchApply' = 'Apply a trusted compatibility overlay to selected GPT-SoVITS'
    'patchUrl' = 'Overlay ZIP download URL (GitHub Releases)'
    'patchLocal' = 'Or local compatibility ZIP (choose one)'
    'okay' = 'Save options'
    'missingRelease' = 'No published character ZIP found. Check the Releases URL.'
    'badAsset' = 'Refresh the list and select a character.'
    'askDownload' = 'Download and install this selected character from the trusted Release?'
    'baseWarning' = 'Base setup can download several gigabytes. A clean upstream engine does not yet include the developer local inference modifications.'
    'log' = 'Detailed third-party logs may be in English.'
}

$script:translations['zh-CN'] = @{
    'window' = 'AnimeVoiceTutor | 首次安装'
    'lang' = 'Language'
    'title' = 'AnimeVoiceTutor · 语音环境安装'
    'subtitle' = '先安装一次基础环境，再从 GitHub Releases 下载人物角色 ZIP。'
    'step1' = '步骤 1 · 安装基础语音环境'
    'desc1' = '配置 Web、ASR、TTS 环境、Qwen3-ASR、GPT-SoVITS，以及可选的预训练资源。'
    'model' = 'Qwen3-ASR 模型'
    'download' = '自动下载已固定版本的 GPT-SoVITS v5'
    'existing' = '使用电脑上已有的兼容 GPT-SoVITS 引擎'
    'browse' = '浏览…'
    'upstream' = '下载上游预训练模型（文件较大，需要联网）'
    'constraints' = '目前验证目标：Windows x64 + NVIDIA CUDA 12.8。请预留充足硬盘空间。'
    'install' = '安装基础语音环境'
    'doctor' = '环境诊断'
    'capture' = '记录引擎版本基准'
    'step2' = '步骤 2 · 下载并安装人物角色 ZIP'
    'desc2' = '打开项目的 GitHub Releases，下载可信任的人物 ZIP，然后在这里导入。'
    'releases' = 'Releases 网页地址'
    'open' = '打开 Releases'
    'zip' = '人物角色 ZIP 文件'
    'choose' = '选择 ZIP'
    'import' = '导入并激活人物'
    'start' = '启动 AnimeVoiceTutor'
    'test' = '测试实时语音'
    'close' = '关闭'
    'closeerror' = '安装窗口未能正常关闭。请查看本地日志。'
    'ready' = '可以安装环境或运行环境诊断。'
    'running' = '任务执行中，请查看下方日志。'
    'ok' = '操作成功。'
    'fail' = '任务失败，请查看日志。'
    'wrongdir' = '不完整的 Core 目录。请解压完整源码 ZIP，不能从补丁 payload 目录运行。缺少：'
    'badurl' = '请填写 GitHub 仓库的 Releases 网页地址。'
    'badpath' = '请选择包含 api_v2.py 的引擎目录。'
    'badzip' = '请先选择已下载的角色 ZIP。'
    'confirmbase' = '将下载 Python 依赖与模型文件，可能需要大量磁盘空间，继续吗？'
    'confirmpack' = '确认导入此可信角色包？模型权重可能存在反序列化代码执行风险。'
    'busy' = '安装仍在进行，暂时不能关闭。'
    'nosmoke' = '请先启动程序并选择人物角色，再测试实时语音。'
    'pretrainNote' = '上游模型缺少已验证的固定 SHA-256；安装时会记录下载摘要。'
    'advanced' = '高级选项'
    'available' = '可用人物角色'
    'refresh' = '刷新 Releases'
    'downloadInstall' = '下载并安装选中的角色'
    'asrLocal' = '已有 ASR 模型目录（可选）'
    'patchApply' = '为选中的 GPT-SoVITS 应用可信兼容补丁'
    'patchUrl' = '兼容补丁 ZIP 链接（GitHub Releases）'
    'patchLocal' = '或者选择本地兼容补丁 ZIP（二选一）'
    'okay' = '保存选项'
    'missingRelease' = '没有找到已公开的人物 ZIP，请检查 Releases 地址。'
    'badAsset' = '请先刷新列表并选择人物。'
    'askDownload' = '确认从可信任的 Release 下载并安装此人物？'
    'baseWarning' = '环境安装可能下载数 GB 文件。纯净上游引擎尚不包含开发者的本地推理修改。'
    'log' = '第三方组件的详细日志可能为英语。'
}

$script:translations['ja'] = @{
    'window' = 'AnimeVoiceTutor | 初回セットアップ'
    'lang' = 'Language'
    'title' = 'AnimeVoiceTutor · 音声環境のセットアップ'
    'subtitle' = '基本環境を一度導入し、GitHub Releases からキャラクター ZIP を取得します。'
    'step1' = 'ステップ 1 · 音声環境のインストール'
    'desc1' = 'Web、ASR、TTS、Qwen3-ASR、GPT-SoVITS、および必要な学習済みリソースを設定します。'
    'model' = 'Qwen3-ASR モデル'
    'download' = '固定版 GPT-SoVITS v5 を自動取得'
    'existing' = 'この PC にある互換 GPT-SoVITS エンジンを使用'
    'browse' = '参照…'
    'upstream' = '学習済みモデルをダウンロード（大容量・通信が必要）'
    'constraints' = '検証対象：Windows x64 + NVIDIA CUDA 12.8。十分な空き容量が必要です。'
    'install' = '音声環境をインストール'
    'doctor' = '環境診断'
    'capture' = 'エンジンの版を記録'
    'step2' = 'ステップ 2 · キャラクター ZIP のダウンロードと導入'
    'desc2' = 'GitHub Releases から信頼できるキャラクター ZIP を取得し、ここで取り込みます。'
    'releases' = 'Releases URL'
    'open' = 'Releases を開く'
    'zip' = 'キャラクター ZIP ファイル'
    'choose' = 'ZIP を選択'
    'import' = '取り込んで有効化'
    'start' = 'AnimeVoiceTutor を起動'
    'test' = '音声テスト'
    'close' = '閉じる'
    'closeerror' = 'セットアップ画面を閉じられませんでした。ローカルログを確認してください。'
    'ready' = '環境のインストールまたは診断を実行できます。'
    'running' = '処理中です。下のログを確認してください。'
    'ok' = '正常に完了しました。'
    'fail' = '処理に失敗しました。ログを確認してください。'
    'wrongdir' = 'Core ディレクトリが不完全です。パッチではなく Core ZIP 全体を展開してください。不足：'
    'badurl' = 'GitHub リポジトリの Releases URL を入力してください。'
    'badpath' = 'api_v2.py を含むエンジンフォルダーを選択してください。'
    'badzip' = 'ダウンロード済みのキャラクター ZIP を選んでください。'
    'confirmbase' = 'Python とモデルをダウンロードします。大容量のため時間と空き容量が必要です。続けますか？'
    'confirmpack' = '信頼できるキャラクター ZIP をインストールしますか？モデルの読み込みにはリスクがあります。'
    'busy' = 'インストール中は閉じられません。'
    'nosmoke' = 'アプリ起動・キャラクター選択後に音声をテストしてください。'
    'pretrainNote' = '上流モデルの検証済み SHA-256 は未確定です。ダウンロード時に記録します。'
    'advanced' = '詳細設定'
    'available' = '公開中のキャラクター'
    'refresh' = 'Releases を更新'
    'downloadInstall' = '選択したキャラクターをダウンロードして導入'
    'asrLocal' = '既存 ASR モデルフォルダー（任意）'
    'patchApply' = '信頼できる GPT-SoVITS 互換パッチを適用'
    'patchUrl' = 'パッチ ZIP の URL（GitHub Releases）'
    'patchLocal' = 'またはローカルの互換 ZIP を選択'
    'okay' = '設定を保存'
    'missingRelease' = '公開キャラクター ZIP が見つかりません。URL を確認してください。'
    'badAsset' = '更新してキャラクターを選んでください。'
    'askDownload' = '信頼できる Release からこのキャラクターを導入しますか？'
    'baseWarning' = '大容量のファイルを取得する場合があります。上流のエンジンには開発者による推論修正が含まれていません。'
    'log' = '外部コンポーネントのログは英語の場合があります。'
}


function T([string]$key){return [string]$script:translations[$script:lang][$key]}
$form=New-Object System.Windows.Forms.Form
$form.Width=880;$form.Height=880
$form.MinimumSize=New-Object System.Drawing.Size(860,810)
$form.StartPosition='CenterScreen'
$form.Font=New-Object System.Drawing.Font('Segoe UI',9)
$form.BackColor=[System.Drawing.Color]::White
$script:labelled=New-Object System.Collections.ArrayList
function Add-Label([string]$key,[int]$x,[int]$y,[int]$w,[int]$h,[bool]$strong=$false){
    $control=New-Object System.Windows.Forms.Label
    $control.Tag=$key
    $control.Location=New-Object System.Drawing.Point($x,$y)
    $control.Size=New-Object System.Drawing.Size($w,$h)
    $control.AutoEllipsis=$true
    if($strong){$control.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)}
    $form.Controls.Add($control);[void]$script:labelled.Add($control);return $control
}
function Add-Button([string]$key,[int]$x,[int]$y,[int]$w,[int]$h){
    $control=New-Object System.Windows.Forms.Button
    $control.Tag=$key
    $control.Location=New-Object System.Drawing.Point($x,$y)
    $control.Size=New-Object System.Drawing.Size($w,$h)
    $form.Controls.Add($control);[void]$script:labelled.Add($control);return $control
}
function Add-Text([int]$x,[int]$y,[int]$w){
    $control=New-Object System.Windows.Forms.TextBox
    $control.Location=New-Object System.Drawing.Point($x,$y)
    $control.Size=New-Object System.Drawing.Size($w,27)
    $form.Controls.Add($control);return $control
}
function Quote-PS([string]$s){return "'"+$s.Replace("'","''")+"'"}
function Apply-Language{
    $form.Text=T 'window'
    foreach($control in $script:labelled){$control.Text=T ([string]$control.Tag)}
    $languageLabel.Text='Language'
    if($null -eq $script:taskProcess){$status.Text=T 'ready'}
}
$languageLabel=New-Object System.Windows.Forms.Label
$languageLabel.Location=New-Object System.Drawing.Point(555,20);$languageLabel.Size=New-Object System.Drawing.Size(95,24)
$form.Controls.Add($languageLabel)
$language=New-Object System.Windows.Forms.ComboBox
$language.Location=New-Object System.Drawing.Point(652,16);$language.Size=New-Object System.Drawing.Size(194,27)
$language.DropDownStyle='DropDownList'
[void]$language.Items.Add('简体中文');[void]$language.Items.Add('English');[void]$language.Items.Add('日本語')
$form.Controls.Add($language)
$null=Add-Label 'title' 26 14 510 32 $true
$null=Add-Label 'subtitle' 26 55 814 35
$null=Add-Label 'step1' 26 105 810 28 $true
$null=Add-Label 'desc1' 33 138 800 44
$null=Add-Label 'model' 33 190 142 23
$model=New-Object System.Windows.Forms.ComboBox
$model.Location=New-Object System.Drawing.Point(180,185);$model.Size=New-Object System.Drawing.Size(220,27)
$model.DropDownStyle='DropDownList'
[void]$model.Items.Add('1.7B');[void]$model.Items.Add('0.6B')
$model.SelectedIndex=0;$form.Controls.Add($model)
$engineDownload=New-Object System.Windows.Forms.RadioButton
$engineDownload.Tag='download';$engineDownload.Location=New-Object System.Drawing.Point(33,227)
$engineDownload.Size=New-Object System.Drawing.Size(796,26);$engineDownload.Checked=$true
$form.Controls.Add($engineDownload);[void]$script:labelled.Add($engineDownload)
$engineExisting=New-Object System.Windows.Forms.RadioButton
$engineExisting.Tag='existing';$engineExisting.Location=New-Object System.Drawing.Point(33,259)
$engineExisting.Size=New-Object System.Drawing.Size(796,26)
$form.Controls.Add($engineExisting);[void]$script:labelled.Add($engineExisting)
$enginePath=Add-Text 48 298 628
$browseEngine=Add-Button 'browse' 689 297 156 30
$enginePath.Enabled=$false;$browseEngine.Enabled=$false
$engineExisting.Add_CheckedChanged({$enginePath.Enabled=$engineExisting.Checked;$browseEngine.Enabled=$engineExisting.Checked})
$browseEngine.Add_Click({
    $dialog=New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description='GPT-SoVITS / api_v2.py'
    if($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){$enginePath.Text=$dialog.SelectedPath}
    $dialog.Dispose()
})
$pretrained=New-Object System.Windows.Forms.CheckBox
$pretrained.Tag='upstream';$pretrained.Location=New-Object System.Drawing.Point(33,339)
$pretrained.Size=New-Object System.Drawing.Size(796,26);$pretrained.Checked=$true
$form.Controls.Add($pretrained);[void]$script:labelled.Add($pretrained)
$null=Add-Label 'constraints' 33 377 810 37
$install=Add-Button 'install' 33 190 240 38
$doctor=Add-Button 'doctor' 283 190 163 38
$capture=Add-Button 'capture' 455 570 185 35
$null=Add-Label 'step2' 26 263 810 28 $true
$null=Add-Label 'desc2' 33 294 805 40
$null=Add-Label 'releases' 33 338 180 24
$release=Add-Text 215 335 459
$linksPath=Join-Path $root 'release\project_links.json'
if(Test-Path -LiteralPath $linksPath -PathType Leaf){
    try{$links=Get-Content -LiteralPath $linksPath -Raw -Encoding UTF8|ConvertFrom-Json
        if([string]$links.releases_url -match '^https://github\.com/[^/\s]+/[^/\s]+/releases$'){$release.Text=[string]$links.releases_url}
    }catch{}
}
if(-not $release.Text -and (Test-Path -LiteralPath (Join-Path $root '.git'))){
    try{$remote=((& git -C $root remote get-url origin 2>$null)|Select-Object -Last 1)
        if($remote -match '^https://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?$'){$release.Text=('https://github.com/'+$Matches[1]+'/'+$Matches[2]+'/releases')}
    }catch{}
}
$releaseSaved=Join-Path $root 'data\app\character_release_source.json'
if(Test-Path -LiteralPath $releaseSaved){
    try{$saved=Get-Content -LiteralPath $releaseSaved -Raw -Encoding UTF8|ConvertFrom-Json
        if([string]$saved.releases_url -match '^https://github\.com/[^/\s]+/[^/\s]+/releases$'){$release.Text=[string]$saved.releases_url}
    }catch{}
}
$open=Add-Button 'open' 688 334 155 30
$null=Add-Label 'zip' 33 490 180 24
$character=Add-Text 215 487 459
$choose=Add-Button 'choose' 688 486 155 30
$import=Add-Button 'import' 33 529 214 38
$start=Add-Button 'start' 33 588 225 38
$test=Add-Button 'test' 455 615 185 35
$close=Add-Button 'close' 672 588 173 38
# Visible normal workflow: two operations. All path choices live in an Advanced dialog.
$advancedButton=Add-Button 'advanced' 456 190 202 38
$advancedForm=New-Object System.Windows.Forms.Form
$advancedForm.Width=860;$advancedForm.Height=750
$advancedForm.StartPosition='CenterParent'
$advancedForm.Font=$form.Font
$advancedForm.FormBorderStyle='FixedDialog'
$advancedForm.MaximizeBox=$false;$advancedForm.MinimizeBox=$false
# Move existing engine/model controls into the Advanced dialog without changing bindings.
foreach($control in @($model,$engineDownload,$engineExisting,$enginePath,$browseEngine,$pretrained)){
    $form.Controls.Remove($control)
    $advancedForm.Controls.Add($control)
}
foreach($c in @($script:labelled|Where-Object{$_.Tag -in @('model','constraints')})){
    $form.Controls.Remove($c);$advancedForm.Controls.Add($c)
}
$labelModel=@($script:labelled|Where-Object{$_.Tag -eq 'model'})[0]
$labelConstraints=@($script:labelled|Where-Object{$_.Tag -eq 'constraints'})[0]
$labelModel.Location=New-Object System.Drawing.Point(25,27)
$model.Location=New-Object System.Drawing.Point(200,24)
$engineDownload.Location=New-Object System.Drawing.Point(25,73)
$engineExisting.Location=New-Object System.Drawing.Point(25,109)
$enginePath.Location=New-Object System.Drawing.Point(48,149)
$browseEngine.Location=New-Object System.Drawing.Point(685,148)
$pretrained.Location=New-Object System.Drawing.Point(25,193)
$labelConstraints.Location=New-Object System.Drawing.Point(25,228)
function Advanced-Label([string]$key,[int]$y){
    $c=New-Object System.Windows.Forms.Label;$c.Tag=$key
    $c.Location=New-Object System.Drawing.Point(25,$y)
    $c.Size=New-Object System.Drawing.Size(805,27)
    $advancedForm.Controls.Add($c);[void]$script:labelled.Add($c);return $c
}
function Advanced-Text([int]$y){
    $c=New-Object System.Windows.Forms.TextBox;$c.Location=New-Object System.Drawing.Point(25,$y)
    $c.Size=New-Object System.Drawing.Size(650,26);$advancedForm.Controls.Add($c);return $c
}
function Advanced-Browse([System.Windows.Forms.TextBox]$targetBox,[string]$kind){
    $c=New-Object System.Windows.Forms.Button;$c.Text='...'
    $c.Location=New-Object System.Drawing.Point(687,($targetBox.Top-2));$c.Size=New-Object System.Drawing.Size(140,31)
    $advancedForm.Controls.Add($c)
    $handler={
        if($kind -eq 'folder'){
            $d=New-Object System.Windows.Forms.FolderBrowserDialog
            if($d.ShowDialog($advancedForm) -eq 'OK'){$targetBox.Text=$d.SelectedPath}
        }else{
            $d=New-Object System.Windows.Forms.OpenFileDialog;$d.Filter='ZIP (*.zip)|*.zip'
            if($d.ShowDialog($advancedForm) -eq 'OK'){$targetBox.Text=$d.FileName}
        }
        $d.Dispose()
    }
    $c.Add_Click($handler.GetNewClosure())
    return $c
}
$null=Advanced-Label 'asrLocal' 277
$asrPath=Advanced-Text 307
$null=Advanced-Browse $asrPath 'folder'
$patchCheck=New-Object System.Windows.Forms.CheckBox
$patchCheck.Tag='patchApply';$patchCheck.Location=New-Object System.Drawing.Point(25,350)
$patchCheck.Size=New-Object System.Drawing.Size(805,28)
$advancedForm.Controls.Add($patchCheck);[void]$script:labelled.Add($patchCheck)
$null=Advanced-Label 'patchUrl' 382
$patchUrl=Advanced-Text 410
$null=Advanced-Label 'patchLocal' 444
$patchZip=Advanced-Text 472
$null=Advanced-Browse $patchZip 'file'
$advancedOkay=New-Object System.Windows.Forms.Button
$advancedOkay.Tag='okay';$advancedOkay.Location=New-Object System.Drawing.Point(665,600)
$advancedOkay.Size=New-Object System.Drawing.Size(160,40)
$advancedForm.Controls.Add($advancedOkay);[void]$script:labelled.Add($advancedOkay)
# Keep expert-only live smoke test and baseline capture out of the main installation step.
foreach($control in @($capture,$test)){
    $form.Controls.Remove($control)
    $advancedForm.Controls.Add($control)
}
$advancedOkay.Add_Click({$advancedForm.Hide()})
$advancedButton.Add_Click({[void]$advancedForm.ShowDialog($form)})
# Character downloads are selected from published GitHub Releases, never guessed filenames.
$null=Add-Label 'available' 33 381 170 27
$available=New-Object System.Windows.Forms.ComboBox
$available.Location=New-Object System.Drawing.Point(215,377);$available.Size=New-Object System.Drawing.Size(459,29)
$available.DropDownStyle='DropDownList';$form.Controls.Add($available)
$refresh=Add-Button 'refresh' 688 376 155 31
$downloadInstall=Add-Button 'downloadInstall' 33 429 500 40
$script:releaseAssets=@()
$script:taskStage=''
$progress=New-Object System.Windows.Forms.ProgressBar
$progress.Location=New-Object System.Drawing.Point(33,655);$progress.Size=New-Object System.Drawing.Size(810,16)
$form.Controls.Add($progress)
$status=New-Object System.Windows.Forms.Label
$status.Location=New-Object System.Drawing.Point(33,683);$status.Size=New-Object System.Drawing.Size(810,24)
$form.Controls.Add($status)
$logBox=New-Object System.Windows.Forms.TextBox
$logBox.Multiline=$true;$logBox.ReadOnly=$true;$logBox.ScrollBars='Vertical'
$logBox.Location=New-Object System.Drawing.Point(33,712);$logBox.Size=New-Object System.Drawing.Size(810,105)
$logBox.Anchor='Top,Bottom,Left,Right';$form.Controls.Add($logBox)
$langIndex=@{'zh-CN'=0;en=1;ja=2}
$language.SelectedIndex=$langIndex[$script:lang]
$language.Add_SelectedIndexChanged({$script:lang=@('zh-CN','en','ja')[$language.SelectedIndex];Apply-Language})
Apply-Language

$open.Add_Click({
    $url=$release.Text.Trim()
    if($url -notmatch '^https://github\.com/[^/\s]+/[^/\s]+/releases(?:/[^\s]*)?$'){
        [System.Windows.Forms.MessageBox]::Show((T 'badurl'),(T 'releases'))|Out-Null;return
    }
    Start-Process $url
})
$choose.Add_Click({
    $dialog=New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter='Character ZIP (*.zip)|*.zip';$dialog.CheckFileExists=$true
    if($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){$character.Text=$dialog.FileName}
    $dialog.Dispose()
})
$timer=New-Object System.Windows.Forms.Timer
$timer.Interval=700
$timer.Add_Tick({
    if($null -eq $script:taskProcess){$timer.Stop();return}
    $output=''
    if(Test-Path -LiteralPath $script:taskLog){try{$output=[IO.File]::ReadAllText($script:taskLog)}catch{}}
    if($output.Length -gt 36000){$output=$output.Substring($output.Length-36000)}
    if($script:lastOutput -ne $output){
        $script:lastOutput=$output;$logBox.Text=$output
        $logBox.SelectionStart=$logBox.Text.Length;$logBox.ScrollToCaret()
    }
    if($script:taskProcess.HasExited){
        $timer.Stop();$code=$script:taskProcess.ExitCode
        $script:taskProcess.Dispose();$script:taskProcess=$null
        $progress.Style='Continuous';$progress.Value=if($code -eq 0){100}else{0}
        $status.Text=if($code -eq 0){T 'ok'}else{T 'fail'}
        foreach($control in @($install,$import,$doctor,$capture,$test,$start,$close,$refresh,$downloadInstall,$advancedButton)){$control.Enabled=$true}
        if($code -eq 0 -and $script:taskStage -eq 'list_characters'){
            $assetFile=Join-Path $root 'data\app\available_character_releases.json'
            try{
                $script:releaseAssets=@(Get-Content -LiteralPath $assetFile -Raw -Encoding UTF8|ConvertFrom-Json)
                $available.Items.Clear()
                foreach($a in $script:releaseAssets){[void]$available.Items.Add(('{0} | {1} | {2:N1} MiB' -f $a.name,$a.release,($a.size/1MB)))}
                if($available.Items.Count -gt 0){$available.SelectedIndex=0}
                else{$status.Text=T 'missingRelease'}
            }catch{$status.Text=T 'fail'}
        }
        $script:taskStage=''
    }
})
function Launch-Job([string]$arguments,[string]$label,[string]$stage=''){
    if($null -ne $script:taskProcess){return}
    $script:taskStage=$stage
    $script:taskLog=Join-Path $logDir (([DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff'))+'.log')
    $script:lastOutput='';$logBox.Text='';$progress.Style='Marquee';$status.Text=T 'running'
    foreach($control in @($install,$import,$doctor,$capture,$test,$start,$close,$refresh,$downloadInstall,$advancedButton)){$control.Enabled=$false}
    $taskPath=Join-Path $PSScriptRoot 'first_run_tasks.ps1'
    $template=@'
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$InformationPreference='Continue'
$exitCode=0
try{
    Start-Transcript -LiteralPath __LOG__ -Force|Out-Null
    & __TASK__ __ARGS__
    if(-not $?){throw 'Installer task failed'}
    Write-Host 'FIRST_RUN_TASK_COMPLETE'
}catch{
    Write-Host ('FIRST_RUN_TASK_FAILED: '+$_)
    $exitCode=1
}finally{try{Stop-Transcript|Out-Null}catch{}}
exit $exitCode
'@
    $command=$template.Replace('__LOG__',(Quote-PS $script:taskLog)).Replace('__TASK__',(Quote-PS $taskPath)).Replace('__ARGS__',$arguments)
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $script:taskProcess=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -WorkingDirectory $root -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -WindowStyle Hidden -PassThru
    $timer.Start()
}
function Make-Stage([string]$stage,[string]$extra=''){
    return ('-Stage '+(Quote-PS $stage)+' -Language '+(Quote-PS $script:lang)+' '+$extra)
}
$install.Add_Click({
    $mode=if($engineExisting.Checked){'existing'}else{'download'}
    if($mode -eq 'existing' -and -not (Test-Path -LiteralPath (Join-Path $enginePath.Text 'api_v2.py') -PathType Leaf)){
        [System.Windows.Forms.MessageBox]::Show((T 'badpath'),(T 'existing'))|Out-Null;return
    }
    if([System.Windows.Forms.MessageBox]::Show((T 'confirmbase'),(T 'install'),'YesNo','Question') -ne 'Yes'){return}
    $extras='-AsrModel '+(Quote-PS ([string]$model.SelectedItem))+' -EngineAction '+(Quote-PS $mode)
    if($mode -eq 'existing'){$extras+=' -EngineFolder '+(Quote-PS $enginePath.Text.Trim())}
    if($pretrained.Checked){$extras+=' -DownloadPretrained'}
    if($asrPath.Text.Trim()){$extras+=' -ExistingAsrFolder '+(Quote-PS $asrPath.Text.Trim())}
    if($patchCheck.Checked){
        $extras+=' -ApplyOverlay'
        if($patchUrl.Text.Trim()){$extras+=' -EnginePatchUrl '+(Quote-PS $patchUrl.Text.Trim())}
        if($patchZip.Text.Trim()){$extras+=' -EnginePatchZip '+(Quote-PS $patchZip.Text.Trim())}
    }
    $extras+=' -InstallFFmpeg'
    Launch-Job (Make-Stage 'base' $extras) (T 'install')
})
$refresh.Add_Click({
    $url=$release.Text.Trim()
    if($url -notmatch '^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/releases/?$'){
        [System.Windows.Forms.MessageBox]::Show((T 'badurl'))|Out-Null;return
    }
    $folder=Join-Path $root 'data\app';[IO.Directory]::CreateDirectory($folder)|Out-Null
    [IO.File]::WriteAllText($releaseSaved,('{"releases_url":'+(ConvertTo-Json $url -Compress)+'}'),[Text.UTF8Encoding]::new($false))
    $available.Items.Clear();$script:releaseAssets=@()
    Launch-Job (Make-Stage 'list_characters' ('-ReleasesUrl '+(Quote-PS $url))) (T 'refresh') 'list_characters'
})
$downloadInstall.Add_Click({
    $ix=$available.SelectedIndex
    if($ix -lt 0 -or $ix -ge $script:releaseAssets.Count){
        [System.Windows.Forms.MessageBox]::Show((T 'badAsset'))|Out-Null;return
    }
    if([System.Windows.Forms.MessageBox]::Show((T 'askDownload'),(T 'downloadInstall'),'YesNo','Question') -ne 'Yes'){return}
    $id=[string]$script:releaseAssets[$ix].id
    $args='-ReleasesUrl '+(Quote-PS $release.Text.Trim())+' -AssetId '+$id
    Launch-Job (Make-Stage 'character_release' $args) (T 'downloadInstall') 'character_release'
})
$import.Add_Click({
    if(-not (Test-Path -LiteralPath $character.Text.Trim() -PathType Leaf)){
        [System.Windows.Forms.MessageBox]::Show((T 'badzip'),(T 'zip'))|Out-Null;return
    }
    if([System.Windows.Forms.MessageBox]::Show((T 'confirmpack'),(T 'import'),'YesNo','Question') -ne 'Yes'){return}
    Launch-Job (Make-Stage 'character' ('-CharacterZip '+(Quote-PS $character.Text.Trim()))) (T 'import')
})
$doctor.Add_Click({Launch-Job (Make-Stage 'diagnostics') (T 'doctor')})
$capture.Add_Click({
    $extra=if($engineExisting.Checked -and $enginePath.Text.Trim()){'-EngineFolder '+(Quote-PS $enginePath.Text.Trim())}else{''}
    Launch-Job (Make-Stage 'capture' $extra) (T 'capture')
})
$test.Add_Click({Launch-Job (Make-Stage 'voice_test') (T 'test')})
$start.Add_Click({
    $launcher=Join-Path $root 'scripts\desktop_start.vbs'
    Start-Process -FilePath (Join-Path $env:WINDIR 'System32\wscript.exe') -ArgumentList ('"'+$launcher+'"') -WorkingDirectory $root
})
# Resolve the owner from the button, rather than a script-scoped GUI variable in an event callback.
# A completed background job is not a reason to block closing the setup window.
$close.Add_Click({
    param($sender,$clickArgs)
    try{
        if($null -ne $script:taskProcess -and -not $script:taskProcess.HasExited){
            $status.Text=T 'busy'
            return
        }
        $window=$sender.FindForm()
        if($null -eq $window){throw 'SETUP_OWNER_FORM_MISSING'}
        $window.DialogResult=[System.Windows.Forms.DialogResult]::Cancel
        $window.Close()
    }catch{
        try{
            $detail=([DateTime]::UtcNow.ToString('o')+' GUI_CLOSE_FAILED: '+$_.Exception.ToString()+[Environment]::NewLine)
            [IO.File]::AppendAllText((Join-Path $logDir 'gui_errors.log'),$detail,[Text.UTF8Encoding]::new($false))
        }catch{}
        [System.Windows.Forms.MessageBox]::Show((T 'closeerror'),(T 'window'))|Out-Null
    }
})
$form.Add_FormClosing({
    param($sender,$eventArgs)
    if($null -ne $script:taskProcess){
        try{
            if(-not $script:taskProcess.HasExited){
                $eventArgs.Cancel=$true
                [System.Windows.Forms.MessageBox]::Show((T 'busy'),(T 'window'))|Out-Null
                return
            }
            $script:taskProcess.Dispose()
            $script:taskProcess=$null
        }catch{
            $eventArgs.Cancel=$true
            [System.Windows.Forms.MessageBox]::Show((T 'busy'),(T 'window'))|Out-Null
        }
    }
})
try{
    [void]$form.ShowDialog()
}finally{
    $timer.Stop()
    $timer.Dispose()
    $form.Dispose()
}
exit 0
