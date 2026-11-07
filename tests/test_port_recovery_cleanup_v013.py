"""Regression contracts for the local, click-first Windows launcher."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ps(name: str) -> str:
    return (ROOT / 'scripts' / name).read_text(encoding='utf-8')


def test_existing_web_reuse_requires_authenticated_same_run_identity():
    code = _ps('launch_app.ps1')
    assert 'function Try-Open-ExistingInstance' in code
    assert 'Get-ManagedWebListener $webPort $previousRun' in code
    assert 'api/system/managed-identity' in code
    assert "'X-AVT-Run-Id'=$runId" in code
    assert 'Get-NetTCPConnection' in code
    assert '$script:runId = $previousRun' in code
    assert 'Get-Json "$webBase/api/status"' not in code.split('function Try-Open-ExistingInstance')[1].split('if (Try-Open-ExistingInstance)')[0]
    assert code.index('if (Try-Open-ExistingInstance) { return }') < code.index("Launch-Service 'asr'")
    assert 'Recovering a verified local AnimeVoiceTutor Web PID' not in code


def test_foreign_port_falls_back_without_killing_other_service():
    code = _ps('launch_app.ps1')
    assert 'if (Has-Listener $webPort)' in code
    assert '$alternatePorts = @(8777,8778,8779,8780,8781,8782,8783,8784,8785)' in code
    assert 'if (-not (Has-Listener $candidate))' in code
    assert "using alternate Web port $webPort instead" in code
    assert '$env:AVT_WEB_PORT = [string]$webPort' in code
    assert 'web_port=$webPort' in code
    assert "Stop-Process" not in code


def test_service_stop_and_browser_monitor_use_active_port():
    stop = _ps('stop_app.ps1')
    mon = _ps('monitor_browser.ps1')
    launch = _ps('launch_app.ps1')
    assert 'TryParse([string]$state.web_port' in stop
    assert '$allowedPorts = @($webPort, 8766, 9880)' in stop
    assert 'param([Parameter(Mandatory=$true)][string]$RunId, [int]$WebPort = 0)' in mon
    assert '$webPort = $WebPort' in mon
    assert '-RunId $script:runId -WebPort $webPort' in launch
    assert 'Start-BrowserMonitor' in launch


def test_only_three_public_root_commands_are_released():
    allowlist = (ROOT / 'release/public_source_files.txt').read_text()
    paths = {p.strip() for p in allowlist.splitlines() if p.strip() and not p.startswith('#')}
    assert {p for p in paths if '/' not in p and p.lower().endswith(('.exe','.cmd','.bat'))} == {
        'First Run Setup.cmd', 'Start AnimeVoiceTutor.cmd', 'Stop AnimeVoiceTutor.cmd'
    }
