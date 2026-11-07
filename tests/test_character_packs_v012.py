"""Character packs are optional, declarative, isolated from neutral Core."""
import json
from pathlib import Path
import zipfile

import pytest
from fastapi.testclient import TestClient
from voice_tutor import app as module
from voice_tutor import characters
from voice_tutor.greetings import GREETING_GROUPS


def package(tmp_path, *, with_audio=False):
    folder = tmp_path/'contents'
    folder.mkdir(exist_ok=True)
    info = {
        'schema_version': 1, 'id': 'example_character',
        'display_name': 'Example Character', 'avatar': '日',
        'greetings': {'morning': [{'id': 'morning_1', 'text': 'おはようございます。'}]},
        'hidden_greetings': [],
    }
    if with_audio:
        (folder/'audio').mkdir(exist_ok=True)
        (folder/'audio'/'morning_1.wav').write_bytes(b'RIFF'+b'\0'*80)
        info['greetings']['morning'][0]['audio'] = 'audio/morning_1.wav'
    (folder/'character.json').write_text(json.dumps(info), encoding='utf-8')
    output = tmp_path/'example.zip'
    with zipfile.ZipFile(output, 'w') as archive:
        for f in folder.rglob('*'):
            if f.is_file(): archive.write(f, f.relative_to(folder).as_posix())
    return output


def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(characters, 'PACK_ROOT', tmp_path/'installed')
    monkeypatch.setattr(characters, 'SELECTION', tmp_path/'app'/'selected_character.json')
    monkeypatch.setattr(characters, 'BINDING', tmp_path/'app'/'tts_model_binding.json')


def test_default_core_only_uses_formal_time_greetings(tmp_path, monkeypatch):
    isolated(tmp_path, monkeypatch)
    assert characters.active_id() == 'default'
    assert not characters.list_installed()
    assert not characters.current_voice_profiles()
    assert all('唯先輩' not in phrase for rows in GREETING_GROUPS.values() for _, phrase in rows)
    assert any('こんにちは。' in phrase for _, phrase in GREETING_GROUPS['afternoon'])
    assert characters.greetings_for_active()['hidden_greetings'] == []
    with TestClient(module.app) as client:
        response = client.get('/api/characters')
        assert response.status_code == 200
        assert response.json()['active'] == 'default'


def test_install_select_and_recorded_greeting(tmp_path, monkeypatch):
    isolated(tmp_path, monkeypatch)
    archive = package(tmp_path, with_audio=True)
    assert characters.import_pack(archive)['id'] == 'example_character'
    assert characters.active_id() == 'default'
    with TestClient(module.app) as client:
        response = client.post('/api/characters/active', json={'id':'example_character'},
                               headers={'Origin':'http://testserver'})
        assert response.status_code == 200
        assert response.json()['tts_restart_required'] is False
        assert characters.active_id() == 'example_character'
        text = client.get('/api/characters/active/content').json()
        assert text['greetings']['morning'][0]['text'] == 'おはようございます。'
        wav = client.get('/api/characters/example_character/greeting-audio/morning_1')
        assert wav.status_code == 200 and wav.content.startswith(b'RIFF')
        assert client.get('/api/characters/another/greeting-audio/morning_1').status_code == 404
        assert client.post('/api/characters/active', json={'id':'default'},
                           headers={'Origin':'http://testserver'}).status_code == 200
    assert characters.active_id() == 'default'


@pytest.mark.parametrize('filename', (
    '../outside.json',
    'bad.py',
    r'assets\escape.png',
))
def test_pack_path_traversal_and_binaries_are_rejected(tmp_path, monkeypatch, filename):
    isolated(tmp_path, monkeypatch)
    archive = tmp_path / 'malicious.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('character.json', json.dumps({
            'schema_version': 1, 'id': 'bad', 'display_name': 'Bad'
        }))
        # ZipInfo.__init__ converts backslashes to slashes on Windows.
        # Override filename AFTER construction to write the exact unsafe bytes.
        info = zipfile.ZipInfo(filename)
        info.filename = filename
        z.writestr(info, b'x')
    with zipfile.ZipFile(archive) as z:
        assert z.infolist()[1].orig_filename == filename
    with pytest.raises(characters.PackError):
        characters.import_pack(archive)
    assert not characters.list_installed()


@pytest.mark.parametrize('encoding', ('utf-8', 'utf-8-sig'))
def test_character_model_binding_accepts_windows_powershell_json(tmp_path, monkeypatch, encoding):
    # Windows PowerShell 5.1 historically writes BOM when using -Encoding UTF8.
    isolated(tmp_path, monkeypatch)
    characters.BINDING.parent.mkdir(parents=True)
    monkeypatch.setattr(characters, 'active_id', lambda: 'example_character')
    monkeypatch.setattr(characters, 'current_voice_profiles', lambda: [{'id': 'example_voice'}])
    monkeypatch.setattr(characters, '_process_running', lambda pid: pid == 12345)
    characters.BINDING.write_text(json.dumps({'character_id': 'example_character',
                                             'listener_pid': 12345}), encoding=encoding)
    assert characters.tts_binding_matches() is True
    characters.BINDING.write_text(json.dumps({'character_id': 'unrelated',
                                             'listener_pid': 12345}), encoding=encoding)
    assert characters.tts_binding_matches() is False


def test_launcher_persists_tts_binding_without_utf8_bom():
    launcher = (Path(__file__).resolve().parents[1]/'scripts/launch_app.ps1').read_text(encoding='utf-8')
    assert "[System.IO.File]::WriteAllText($bindingPath" in launcher
    assert "[System.Text.UTF8Encoding]::new($false)" in launcher


def test_character_model_binding_fails_closed(tmp_path, monkeypatch):
    isolated(tmp_path, monkeypatch)
    assert characters.tts_binding_matches() is False
    with TestClient(module.app) as client:
        result = client.post('/api/speak', json={'voice_id':'unknown','text':'こんにちは。'})
        assert result.status_code == 503


def test_no_role_specific_artwork_or_hidden_lines_in_core():
    root = Path(__file__).resolve().parents[1]
    html = (root/'web/index.html').read_text(encoding='utf-8-sig')
    assert 'id="characterSelect"' in html
    assert 'function loadCharacterContent()' in html
    assert 'secret_yui_1' not in html
    assert not (root/'web/assets/azusa_subject.png').exists()
    assert (root/'tools/build_character_pack.py').is_file()


def test_settings_upload_character_zip_accepts_multipart(tmp_path, monkeypatch):
    isolated(tmp_path, monkeypatch)
    archive = package(tmp_path)
    with TestClient(module.app) as client:
        with archive.open('rb') as stream:
            uploaded = client.post('/api/characters/install',
                headers={'Origin':'http://testserver'},
                files={'archive': ('example.zip', stream, 'application/zip')})
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()['installed']['id'] == 'example_character'
        assert uploaded.json()['active'] == 'example_character'
        assert client.get('/api/characters').json()['active'] == 'example_character'
        entry = client.get('/api/characters').json()['characters'][1]
        assert entry['recordings_present'] == 0
        assert entry['recordings_total'] == 1
        with archive.open('rb') as stream:
            no_origin = client.post('/api/characters/install',
                files={'archive': ('example.zip', stream, 'application/zip')})
        assert no_origin.status_code == 403
        assert client.get('/api/characters').json()['characters'][1]['id'] == 'example_character'


def test_neutral_frontend_is_portrait_free_at_first_paint():
    html = (Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    neutral = html.split('id="thread"', 1)[1].split('</section>',1)[0]
    assert 'particle-stage' not in neutral
    assert 'greeting-play hidden' in neutral
    assert 'ttsOptional' in html


def test_build_full_character_pack_from_local_files(tmp_path):
    from types import SimpleNamespace
    from tools.build_character_pack import build
    from voice_tutor.characters import validate_manifest
    base = package(tmp_path)
    materials = tmp_path / 'materials'
    materials.mkdir()
    for filename in ('model.ckpt','model.pth'):
        (materials/filename).write_bytes(b'example only')
    (materials/'reference.wav').write_bytes(b'RIFF'+b'\x00'*100)
    (materials/'preset.json').write_text('{}', encoding='utf-8')
    result = tmp_path/'full.zip'
    build(SimpleNamespace(base_zip=base, gpt_weights=materials/'model.ckpt',
         sovits_weights=materials/'model.pth', reference_audio=materials/'reference.wav',
         preset=materials/'preset.json', voice_id='example_voice',
         prompt_text='これは例です。', output=result))
    stage=tmp_path/'full_extracted'
    with zipfile.ZipFile(result) as z: z.extractall(stage)
    info=validate_manifest(stage)
    assert info['voice']['prompt_text']=='これは例です。'
    assert info['model']['gpt_weights']=='models/gpt.ckpt'


def test_import_uploaded_pack_rejects_sibling_character_source(tmp_path, monkeypatch):
    isolated(tmp_path, monkeypatch)
    with zipfile.ZipFile(tmp_path/'malicious.zip','w') as z:
        z.writestr('character.json',json.dumps({'schema_version':1,'id':'evil','display_name':'Evil'}))
        z.writestr('something.pickle',b'not allowed')
    with pytest.raises(characters.PackError):
        characters.import_pack(tmp_path/'malicious.zip')


def test_character_pack_status_separates_resources_from_running_model(tmp_path, monkeypatch):
    isolated(tmp_path, monkeypatch)
    archive = package(tmp_path, with_audio=True)
    characters.import_pack(archive)
    characters.select_character('example_character')
    with TestClient(module.app) as client:
        status = client.get('/api/status').json()
        assert status['character_id'] == 'example_character'
        assert status['tts_pack_installed'] is False
        assert status['tts_ready'] is False
        assert 'tts_detail' in status
        assert client.get('/api/characters').json()['characters'][1]['recordings_present'] == 1


def test_character_installation_ui_has_progress_activation_and_tab_icons():
    html = (Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    assert 'id="characterInstallProgress"' in html
    assert 'id="characterActivation"' in html
    assert 'function uploadCharacterPack(' in html
    assert "closeSettings();await newChat();" in html
    for icon in ('message', 'cpu', 'user', 'wave', 'archive', 'info'):
        assert f'data-settings-icon="{icon}"' in html
        assert f'  {icon}:' in html


def test_full_voice_upload_activates_profile_but_not_unbound_tts(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from tools.build_character_pack import build

    isolated(tmp_path, monkeypatch)
    monkeypatch.setattr(module, 'voices', {})
    source = package(tmp_path)
    material = tmp_path / 'voice'
    material.mkdir()
    (material/'gpt.ckpt').write_bytes(b'example')
    (material/'sovits.pth').write_bytes(b'example')
    (material/'reference.wav').write_bytes(b'RIFF'+b'\x00'*80)
    (material/'preset.json').write_text('{}', encoding='utf-8')
    full = tmp_path/'full_pack.zip'
    build(SimpleNamespace(base_zip=source, gpt_weights=material/'gpt.ckpt',
         sovits_weights=material/'sovits.pth', reference_audio=material/'reference.wav',
         preset=material/'preset.json', voice_id='example_voice',
         prompt_text='こんにちは。', output=full))
    with TestClient(module.app) as client, full.open('rb') as stream:
        res = client.post('/api/characters/install',
            headers={'Origin': 'http://testserver'},
            files={'archive': ('full_pack.zip', stream, 'application/zip')})
        assert res.status_code == 200, res.text
        assert res.json()['active'] == 'example_character'
        assert res.json()['tts_restart_required'] is True
        assert 'example_voice' in module.voices
        status = client.get('/api/status').json()
        assert status['tts_pack_installed'] is True
        # The installer never marks the GPU service ready merely for finding weights.
        assert status['tts_ready'] is False
        assert isinstance(status['tts_detail'], str) and status['tts_detail']
