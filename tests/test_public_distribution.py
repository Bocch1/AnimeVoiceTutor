from pathlib import Path
import json
import zipfile

import pytest

from scripts.verify_public_source import is_private_path, verify_archive
ROOT=Path(__file__).resolve().parents[1]

def test_local_launchers_and_docs_exist():
    assert all((ROOT/p).is_file() for p in ['README.md','README.zh-CN.md','README.ja.md','Start AnimeVoiceTutor.cmd','Stop AnimeVoiceTutor.cmd','advanced/Setup AnimeVoiceTutor.cmd','scripts/setup_source.ps1'])

def test_original_hidden_greetings_and_replay_logic_preserved():
    text=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert "let SECRET_GREETINGS=[]" in text
    assert "SECRET_GREETINGS=data.hidden_greetings" in text
    assert "if(welcomeTapCount%3===0 && SECRET_GREETINGS.length>0)" in text
    assert 'greetingPlaySequence' in text and '/api/secret-greetings/speak' in text

def test_example_configs_do_not_distribute_voices():
    # Runtime-only configuration is expected after linking a local installation.
    # Only the PUBLIC archive, not the user's working directory, must exclude it.
    assert json.loads((ROOT/'configs/voice_profiles_v08.example.json').read_text(encoding='utf-8'))['voices']==[]
    assert is_private_path('configs/frozen_tts_preset.json')
    assert is_private_path('configs/voice_profiles_v08.json')
    assert not is_private_path('configs/frozen_tts_preset.example.json')
    assert not is_private_path('configs/voice_profiles_v08.example.json')
    assert 'configs/*.json' in (ROOT/'.gitignore').read_text(encoding='utf-8')
    assert not is_private_path('.env.example')
    assert is_private_path('.env.production')


def test_public_archive_rejects_local_voice_config(tmp_path):
    archive = tmp_path / 'public_with_private_config.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('configs/frozen_tts_preset.json', '{"private": true}')
    with pytest.raises(AssertionError, match='Private or disallowed file'):
        verify_archive(archive)


def test_character_artwork_is_excluded_from_core():
    assert is_private_path('web/assets/azusa_subject.png')
    assert is_private_path('web/assets/unknown.png')
    assert is_private_path('data/private_portrait.png')
    ignore=(ROOT/'.gitignore').read_text(encoding='utf-8')
    assert '!web/assets/azusa_subject.png' not in ignore
