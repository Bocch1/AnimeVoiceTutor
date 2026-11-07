"""Local release ZIP layout and public-source privacy contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from tools.local_package_store import (
    ensure_folders, archive_character, archive_update, character_archive_name,
)
from scripts.verify_public_source import is_private_path
from tools.build_public_source import public_paths

ROOT = Path(__file__).resolve().parents[1]


def _char_zip(folder: Path, identity='azusa', version=None, suffix='') -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / f'temporary{suffix}.zip'
    record = {'schema_version': 1, 'id': identity, 'display_name': 'Azusa',
              'greetings': {}, 'hidden_greetings': []}
    if version is not None:
        record['pack_version'] = version
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('character.json', json.dumps(record))
    return archive


def test_local_folders_are_private_not_part_of_public_zip(tmp_path):
    updates, characters = ensure_folders(tmp_path)
    assert updates == tmp_path/'packages'/'updates'
    assert characters == tmp_path/'packages'/'characters'
    assert is_private_path('packages/updates/AnimeVoiceTutor_Core_v0.13.1.zip')
    assert is_private_path('packages/characters/AnimeVoiceTutor_Character_azusa_v1.zip')
    assert 'packages/' in (ROOT/'.gitignore').read_text(encoding='utf-8')
    assert not any(n.startswith('packages/') for n in public_paths(ROOT))


def test_character_archive_standard_name_and_duplicate_reuse(tmp_path):
    source = _char_zip(tmp_path/'download', version='2.1')
    target = archive_character(source, tmp_path/'project')
    assert target.name == 'AnimeVoiceTutor_Character_azusa_v2.1.zip'
    assert archive_character(source, tmp_path/'project') == target
    assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()


def test_legacy_character_archive_uses_package_v1_label(tmp_path):
    source = _char_zip(tmp_path/'download')
    assert character_archive_name(source) == 'AnimeVoiceTutor_Character_azusa_v1.zip'


def test_existing_character_version_never_overwritten(tmp_path):
    first = _char_zip(tmp_path/'src_a')
    target = archive_character(first, tmp_path/'project')
    second = _char_zip(tmp_path/'src_b', suffix='_different', version='1')
    with zipfile.ZipFile(second, 'a') as zf:
        zf.writestr('audio/extra.wav', b'a different pack')
    with pytest.raises(FileExistsError):
        archive_character(second, tmp_path/'project')
    assert target.read_bytes() == first.read_bytes()


def test_update_archiver_only_accepts_canonical_versions(tmp_path):
    source = tmp_path/'AnimeVoiceTutor_Core_v0.13.1.zip'
    source.write_bytes(b'zip placeholder')
    stored = archive_update(source, tmp_path/'project')
    assert stored == tmp_path/'project/packages/updates/AnimeVoiceTutor_Core_v0.13.1.zip'
    assert stored.read_bytes() == source.read_bytes()
    malicious = tmp_path/'random.zip'
    malicious.write_bytes(b'any')
    with pytest.raises(ValueError):
        archive_update(malicious, tmp_path/'project')


def test_current_version_and_entrypoints_are_consistent():
    import tomllib
    version = tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    assert version == '0.13.1'
    assert '"version": "0.13.1"' in (ROOT/'voice_tutor/app.py').read_text(encoding='utf-8')
    for rel in ['README.md', 'README.zh-CN.md', 'README.ja.md']:
        doc = (ROOT/rel).read_text(encoding='utf-8')
        assert f'AnimeVoiceTutor_Core_v{version}.zip' in doc
        assert 'Language' in doc
    assert (ROOT/'First Run Setup.cmd').read_text(encoding='utf-8').count('"%~dp0packages\\') == 4
    assert '3b95794' not in (ROOT/'docs/INSTALLATION.md').read_text(encoding='utf-8')


def test_start_cmds_quote_full_paths():
    for name in ['First Run Setup.cmd', 'Start AnimeVoiceTutor.cmd', 'Stop AnimeVoiceTutor.cmd']:
        content = (ROOT/name).read_text(encoding='utf-8')
        assert '"%~dp0' in content
        assert 'cd /d "%~dp0"' in content


def test_character_import_saves_zip_in_project_archive(tmp_path, monkeypatch):
    from voice_tutor import characters
    local_project = tmp_path / 'avt'
    source = _char_zip(tmp_path / 'download', identity='azusa')
    monkeypatch.setattr(characters, 'ROOT', local_project)
    monkeypatch.setattr(characters, 'PACK_ROOT', local_project / 'data' / 'character_packs')
    installed = characters.import_pack(source)
    assert installed['id'] == 'azusa'
    saved = local_project / 'packages' / 'characters' / 'AnimeVoiceTutor_Character_azusa_v1.zip'
    assert saved.is_file()
    assert saved.read_bytes() == source.read_bytes()
    assert (local_project / 'data' / 'character_packs' / 'azusa' / 'character.json').is_file()


def test_readme_document_links_exist_and_public_version_matches():
    import re
    for rel in ['README.md', 'README.zh-CN.md', 'README.ja.md']:
        content = (ROOT / rel).read_text(encoding='utf-8')
        for target in re.findall(r'\[[^\]]+\]\((docs/[^)#]+)\)', content):
            assert (ROOT / target).is_file(), (rel, target)
    spec = json.loads((ROOT / 'release/install_specs/voice_baseline.json').read_text(encoding='utf-8'))
    assert spec['release'] == '0.13.1'
