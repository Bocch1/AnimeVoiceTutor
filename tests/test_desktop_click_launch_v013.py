"""Desktop-click flow: no persistent terminal for normal usage; CLI remains available."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_normal_start_uses_hidden_wscript_and_preserves_cli_switches():
    script = (ROOT / 'Start AnimeVoiceTutor.cmd').read_text(encoding='utf-8')
    assert 'if not "%~1"=="" goto console' in script
    assert 'start "" wscript.exe "%~dp0scripts\\desktop_start.vbs"' in script
    assert 'scripts\\start_source.ps1" %*' in script
    assert 'start_source.ps1' not in script.split(':console', 1)[0]


def test_desktop_launcher_uses_no_console_and_reports_startup_errors():
    vbs = (ROOT / 'scripts/desktop_start.vbs').read_text(encoding='ascii')
    ps = (ROOT / 'scripts/desktop_start.ps1').read_text(encoding='utf-8')
    assert 'shell.Run(command, 0, True)' in vbs
    assert 'MsgBox' in vbs and 'desktop_start.log' in vbs
    assert 'code = 2' in vbs
    assert 'Start-Transcript' in ps and 'Stop-Transcript' in ps
    assert "'Local\\AVT_START_'" in ps
    assert '$mutex.WaitOne(' in ps
    assert 'start_source.ps1' in ps
    assert 'DESKTOP_START_FAILED:' in ps


def test_second_click_reuses_recorded_web_without_restarting_services():
    launch = (ROOT / 'scripts/launch_app.ps1').read_text(encoding='utf-8')
    assert 'function Try-Open-ExistingInstance' in launch
    assert 'Get-Service-Listener' in launch
    assert 'Get-ManagedWebListener $webPort $previousRun' in launch
    assert '$_ .pid' not in launch
    assert '$script:runId = $previousRun' in launch
    assert 'if (Try-Open-ExistingInstance) { return }' in launch
    assert launch.index('if (Try-Open-ExistingInstance) { return }') < launch.index("Launch-Service 'asr'")
    assert 'RunId' in (ROOT / 'scripts/stop_app.ps1').read_text(encoding='utf-8')


def test_setup_start_button_uses_desktop_path():
    gui = (ROOT / 'scripts/first_run_gui.ps1').read_text(encoding='utf-8-sig')
    assert "Join-Path $root 'scripts\\desktop_start.vbs'" in gui
    assert "'System32\\wscript.exe'" in gui


def test_public_release_includes_click_launcher_without_models():
    public = (ROOT / 'release/public_source_files.txt').read_text(encoding='utf-8')
    assert 'scripts/desktop_start.ps1' in public.splitlines()
    assert 'scripts/desktop_start.vbs' in public.splitlines()
    assert 'data/browser_profile' not in public
