"""The neutral core never distributes a specific character or its model."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from voice_tutor import app as m
from voice_tutor import characters
ROOT = Path(__file__).resolve().parents[1]


def test_public_templates_are_empty():
    assert '"greetings": []' in (ROOT/'configs/private_greetings.example.json').read_text(encoding='utf-8')
    assert '"voices": []' in (ROOT/'configs/voice_profiles_v08.example.json').read_text(encoding='utf-8')


def test_neutral_core_has_no_character_artwork(tmp_path, monkeypatch):
    # Neutral-source checks must not depend on a user's installed character packs.
    # Importantly, do not delete or mutate any real data/character_packs directory.
    monkeypatch.setattr(characters, 'PACK_ROOT', tmp_path / 'empty_character_packs')
    monkeypatch.setattr(characters, 'SELECTION', tmp_path / 'selected_character.json')
    assert not (ROOT/'web/assets/azusa_subject.png').exists()
    with TestClient(m.app) as client:
        response = client.get('/api/characters')
        assert response.status_code == 200
        assert response.json()['active'] == 'default'
        assert client.get('/api/characters/azusa/portrait').status_code == 404
        assert client.get('/api/secret-greetings').json() == {'greetings': []}


def test_installed_character_portrait_does_not_make_core_non_neutral(tmp_path, monkeypatch):
    # An installed pack is intentionally accessible through the media endpoint.
    # That must not be mistaken for a bundled, copyrighted Core asset.
    folder = tmp_path / 'installed' / 'azusa'
    (folder / 'assets').mkdir(parents=True)
    (folder / 'assets' / 'portrait.png').write_bytes(b'example portrait')
    (folder / 'character.json').write_text(json.dumps({
        'schema_version': 1, 'id': 'azusa', 'display_name': 'Azusa',
        'portrait': 'assets/portrait.png'
    }), encoding='utf-8')
    monkeypatch.setattr(characters, 'PACK_ROOT', tmp_path / 'installed')
    monkeypatch.setattr(characters, 'SELECTION', tmp_path / 'selected_character.json')
    with TestClient(m.app) as client:
        assert client.get('/api/characters/azusa/portrait').status_code == 200
        assert any(item['id'] == 'azusa'
                   for item in client.get('/api/characters').json()['characters'])
    assert not (ROOT / 'web/assets/azusa_subject.png').exists()


def test_pack_animation_is_loaded_from_data_not_embedded():
    html = (ROOT/'web/index.html').read_text(encoding='utf-8')
    assert 'let CHARACTER_LINE_POINTS_BASE64' in html
    assert 'function startCharacterPortrait()' in html
    assert "'/api/characters/'+encodeURIComponent(activeCharacter)+'/effects'" in html
    assert 'secret_yui_1' not in html


def test_character_select_settings_are_present():
    html = (ROOT/'web/index.html').read_text(encoding='utf-8')
    assert 'id="characterSelect"' in html
    assert 'id="characterInstall"' in html
    assert 'welcomeTapCount%3===0 && SECRET_GREETINGS.length>0' in html


def test_audio_stop_control_survives_character_welcome_rebuild():
    # The welcome balloon temporarily owns #stopAudio. Rebuilds must return it
    # to its persistent parent before removing/replacing the balloon.
    html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
    assert 'function restoreStopAudioControl()' in html
    assert 'hideWelcome();renderWelcome();' in html
    assert "restoreStopAudioControl();\n  $('welcome')?.remove();" in html
    assert "restoreStopAudioControl();\n  thread.classList.add('is-welcome');" in html
    assert "$('stopAudio')?.classList.remove('hidden');" in html
    assert "$('stopAudio')?.classList.add('hidden');" in html
