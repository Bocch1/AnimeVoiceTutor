"""Avoid port collisions with a simultaneously running local audio extractor."""
from pathlib import Path
import os

import pytest
from voice_tutor.ports import web_port

ROOT = Path(__file__).resolve().parents[1]


def test_web_port_defaults_to_8767(monkeypatch):
    monkeypatch.delenv("AVT_WEB_PORT", raising=False)
    assert web_port() == 8767
    monkeypatch.setenv("AVT_WEB_PORT", "8775")
    assert web_port() == 8775
    for invalid in ("", "localhost", "8765bad", "0", "1023", "65536", "8766", "9880", "８７６７"):
        if not invalid:
            continue  # blank means unset via the PowerShell startup helper
        monkeypatch.setenv("AVT_WEB_PORT", invalid)
        with pytest.raises(ValueError):
            web_port()


def test_entire_web_lifecycle_uses_configurable_port():
    main = (ROOT / "voice_tutor/__main__.py").read_text(encoding="utf-8")
    app = (ROOT / "voice_tutor/app.py").read_text(encoding="utf-8")
    launch = (ROOT / "scripts/launch_app.ps1").read_text(encoding="utf-8")
    stop = (ROOT / "scripts/stop_app.ps1").read_text(encoding="utf-8")
    monitor = (ROOT / "scripts/monitor_browser.ps1").read_text(encoding="utf-8")
    smoke = (ROOT / "tools/smoke_voice_services.py").read_text(encoding="utf-8")
    assert "port=web_port()" in main
    assert '== web_port()' in app
    assert "Launch-Service 'web' $webPort" in launch
    assert "Record-Listener 'web' $webPort" in launch
    assert 'http://127.0.0.1:8765' not in launch
    assert "$port -notin $allowedPorts" in stop
    assert '$webBase/api/browser/presence' in monitor
    assert 'web_port()' in smoke


def test_web_port_script_exists_and_bounds_port():
    script = (ROOT / "scripts/web_port.ps1").read_text(encoding="utf-8")
    assert 'AVT_WEB_PORT' in script
    assert "'8767'" in script
    assert '65535' in script


def test_live_smoke_script_imports_package_without_pythonpath(tmp_path):
    """Direct script launch must work from any cwd, including clean-user shells."""
    import subprocess
    import sys

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/smoke_voice_services.py"), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--voice" in result.stdout
