"""Validate fail-closed recovery of the existing frozen TTS process."""
from pathlib import Path
import os
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_recovery_requires_exact_local_parent_and_frozen_config():
    helper = (ROOT/'scripts/verify_local_tts_provenance.ps1').read_text()
    for token in ['Get-NetTCPConnection', 'ExpectedPython', 'CreationDate',
                  'start_tts_api_frozen.ps1', 'jvt_frozen_tts_api', '-File',
                  'ParentProcessId', 'Get-CimInstance', '9880']:
        assert token in helper
    assert 'Stop-Process' not in helper and 'taskkill' not in helper.lower()


def test_launch_and_reload_use_same_provenance_guard():
    launch = (ROOT/'scripts/launch_app.ps1').read_text(encoding='utf-8-sig')
    refresh = (ROOT/'scripts/refresh_character_tts.ps1').read_text(encoding='utf-8-sig')
    assert launch.count('Test-LocalFrozenTtsProvenance') == 1
    assert refresh.count('Test-LocalFrozenTtsProvenance') == 1
    assert 'TTS_RELOAD_RECOVER_LOCAL_ORPHAN_PID' in refresh
    assert 'TTS_FOREIGN_LISTENER_ON_9880' in refresh
    assert '[tts] Recovered this checkout' in launch
    assert '[tts] Scheduled voice reload' in launch
    assert 'local_services.json' in refresh


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows PowerShell 5.1 only')
def test_windows_ps_parses_frozen_recovery_scripts():
    command = (
        '$path=$env:AVT_PS_PARSE_TARGET;'
        'if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { exit 2 };'
        '$t=$null;$e=$null;'
        '[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$t,[ref]$e)|Out-Null;'
        'if ($e.Count -gt 0) { $e | ForEach-Object { Write-Output $_.Message }; exit 1 }'
    )
    for relative in ['scripts/verify_local_tts_provenance.ps1',
                     'scripts/launch_app.ps1', 'scripts/refresh_character_tts.ps1']:
        script = ROOT / relative
        # Use an environment variable instead of PowerShell -Command $args[0].
        env = os.environ.copy()
        env['AVT_PS_PARSE_TARGET'] = str(script.resolve())
        outcome = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            env=env, capture_output=True, text=True,
        )
        assert outcome.returncode == 0, (relative, outcome.stdout, outcome.stderr)
