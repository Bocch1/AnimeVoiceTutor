"""Current-source contracts; historical patch snapshots are not release criteria."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_application_endpoints_are_present():
    source = (ROOT / 'voice_tutor/app.py').read_text(encoding='utf-8-sig')
    required = (
        '@app.get("/api/status")',
        '@app.post("/api/secret-greetings/speak")',
        '@app.post("/api/system/exit")',
        '@app.get("/api/browser/presence")',
    )
    for endpoint in required:
        assert endpoint in source, endpoint
    assert 'secrets.compare_digest' in source
    assert re.search(r'"version":\s*"\d+\.\d+\.\d+"', source)


def test_current_welcome_ui_and_cache_contract():
    html = (ROOT / 'web/index.html').read_text(encoding='utf-8-sig')
    assert html.count('id="roleAvatar"') == 1
    assert html.count('id="roleTrigger"') == 1
    assert 'SECRET_GREETINGS' in html
    assert 'ttsText' in html
    assert "'/api/secret-greetings/speak'" in html
    assert 'const welcomeAudioCache=new Map()' in html
    assert 'nextWelcomeGreeting()' in html
    assert 'requestAnimationFrame(draw)' in html
    assert 'prefers-reduced-motion: reduce' in html


def test_web_runtime_uses_resolver_not_developer_absolute_path():
    script = (ROOT / 'scripts/start_web.ps1').read_text(encoding='utf-8-sig')
    assert "resolve_runtime_python.ps1" in script
    assert '-Role web' in script
    assert '& $python -m voice_tutor serve' in script
    assert r'& .\.venv\Scripts\python.exe' not in script


def test_service_runtime_resolution_and_identity_guard():
    resolver = (ROOT / 'scripts/resolve_runtime_python.ps1').read_text(encoding='utf-8-sig')
    stop = (ROOT / 'scripts/stop_app.ps1').read_text(encoding='utf-8-sig')
    asr = resolver.index('Add-Candidate $env:AVT_ASR_PYTHON')
    web = resolver.index('Add-Candidate $env:AVT_WEB_PYTHON')
    assert asr < web
    assert r'runtime\asr\python.exe' in resolver
    assert r'runtime\web\python.exe' in resolver
    assert r'runtime\tts\python.exe' in resolver
    assert 'Trusted-Listener' in stop
    assert 'if ($RunId -and [string]$state.run_id -ne $RunId)' in stop
    assert 'Service state was retained for a retry' in stop
    assert '$procId:' not in stop


def test_referenced_asset_and_fixed_voice_configuration():
    assert "@app.get('/api/characters/{identity}/{kind}')" in (ROOT / 'voice_tutor/app.py').read_text(encoding='utf-8')
    tts = (ROOT / 'scripts/start_tts_api_frozen.ps1').read_text(encoding='utf-8-sig')
    assert 'write_frozen_tts_config.py' in tts
    assert "'False'" in tts
    assert 'api_v2.py' in tts
