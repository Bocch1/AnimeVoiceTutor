"""Verify an installed source tree or an export ZIP.

Installed directories can contain local environments, caches and models. A ZIP
intended for publication must not contain them; use --archive for that audit.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT_NAMES = {
    '.env', '.avt-local.ps1', '.avt-local.ps1.tmp', 'data', 'models',
    'external', 'datasets', 'backups', '.venv', 'runtime', '.installer',
    '.git', '.pytest_cache', '.mypy_cache', '.ruff_cache', '__pycache__',
    'local', 'private', 'weights', 'checkpoints', 'outputs', 'reports',
    'logs', 'build', 'dist', '.venv_old_backup', 'packages',
}
PRIVATE_SUFFIXES = {
    '.wav', '.mp3', '.flac', '.ogg', '.mkv', '.mp4', '.pth', '.pt',
    '.ckpt', '.safetensors', '.onnx', '.png', '.jpg', '.jpeg', '.webp',
    '.gif', '.db', '.sqlite3', '.exe', '.dll', '.pyd', '.pem', '.key',
    '.zip', '.7z', '.rar', '.pyc',
}
REQUIRED = {
    'README.md', 'README.zh-CN.md', 'README.ja.md', 'LICENSE',
    'SECURITY.md', 'First Run Setup.cmd', 'Start AnimeVoiceTutor.cmd',
    'Stop AnimeVoiceTutor.cmd', 'web/index.html', 'voice_tutor/app.py',
}



def is_private_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts or '\\' in relative:
        return True
    if relative == '.env.example':
        return False
    if path.parts[0] in PRIVATE_ROOT_NAMES or path.parts[0].startswith('.env.'):
        return True
    if any(part in {'__pycache__', '.pytest_cache', '.venv', 'node_modules'} or part.startswith('.venv') or part.endswith('.egg-info') for part in path.parts):
        return True
    if relative.startswith('configs/') and path.suffix == '.json':
        if not path.name.endswith(('.example.json', '.sample.json')):
            return True
    if path.suffix.lower() in PRIVATE_SUFFIXES:
        return True
    return False


def verify_source(root: Path = ROOT) -> None:
    for name in REQUIRED:
        if not (root / name).is_file():
            raise AssertionError(f'Missing public source file: {name}')
    html = (root / 'web/index.html').read_text(encoding='utf-8-sig')
    assert 'CHARACTER_LINE_POINTS_BASE64' in html
    assert 'let SECRET_GREETINGS=[]' in html
    assert 'id="characterSelect"' in html
    assert not (root / 'web/assets/azusa_subject.png').exists()
    assert (root / 'voice_tutor/characters.py').is_file()
    assert (root / 'tools/build_character_pack.py').is_file()
    assert 'secret_yui_1' not in html  # Character-only lines must be in optional packs.

    # Local, gitignored installation files must not invalidate a source test.
    # The strict package scan below still prohibits these files in an export.
    for directory, subdirectories, filenames in os.walk(root):
        base = Path(directory)
        # Do not recurse into installed environments or downloaded model trees.
        subdirectories[:] = [
            child for child in subdirectories
            if not is_private_path((base / child).relative_to(root).as_posix())
        ]
        for filename in filenames:
            path = base / filename
            relative = path.relative_to(root).as_posix()
            if is_private_path(relative):
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                raise AssertionError(f'Unexpected large source file: {relative}')
    print('PUBLIC_SOURCE_STRUCTURE_PASS')


def verify_archive(archive: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        names = set()
        for item in zf.infolist():
            name = item.filename
            if name.endswith('/'):
                continue
            if name in names:
                raise AssertionError(f'Duplicate archive file: {name}')
            names.add(name)
            if is_private_path(name):
                raise AssertionError(f'Private or disallowed file in archive: {name}')
            if item.file_size > 2 * 1024 * 1024:
                raise AssertionError(f'Unexpected large archive file: {name}')
        missing = REQUIRED - names
        if missing:
            raise AssertionError(f'Missing required archive files: {sorted(missing)}')
        if 'web/assets/azusa_subject.png' in names:
            raise AssertionError('Character artwork belongs in a separate Release asset')
        invalid = zf.testzip()
        if invalid:
            raise AssertionError(f'Archive CRC error: {invalid}')
    print(f'PUBLIC_ARCHIVE_PASS: {len(names)} files')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Strictly audit ZIP contents before public distribution')
    args = parser.parse_args()
    if args.archive:
        verify_archive(args.archive)
    else:
        verify_source()


if __name__ == '__main__':
    main()
