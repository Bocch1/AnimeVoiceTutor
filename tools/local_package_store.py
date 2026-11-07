"""Keep local release ZIPs organized without distributing private model files.

The `packages` directory is a user-local archive, never part of a public Core ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){0,2}$")
UPDATE_NAME = re.compile(r"^AnimeVoiceTutor_(?:Core|Update)_v[0-9]+(?:\.[0-9]+){0,2}\.zip$")


def ensure_folders(root: Path = ROOT) -> tuple[Path, Path]:
    """Create private local folders only; do not move installed weights."""
    base = root / 'packages'
    updates, characters = base / 'updates', base / 'characters'
    updates.mkdir(parents=True, exist_ok=True)
    characters.mkdir(parents=True, exist_ok=True)
    return updates, characters


def _copy_verified(source: Path, destination: Path) -> Path:
    source = source.resolve(strict=True)
    if not source.is_file() or source.suffix.lower() != '.zip':
        raise ValueError('Expected an existing ZIP file')
    if source == destination.resolve():
        return destination
    if destination.exists():
        if _digest(source) == _digest(destination):
            return destination
        raise FileExistsError('A different archive already has this name: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL prevents two installers overwriting the same archive concurrently.
    tmp = destination.with_name(destination.name + '.part')
    try:
        with source.open('rb') as inp, tmp.open('xb') as out:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if _digest(source) != _digest(tmp):
            raise IOError('Archive copy failed integrity check')
        os.replace(tmp, destination)
    finally:
        tmp.unlink(missing_ok=True)
    return destination


def _digest(file: Path) -> str:
    h = hashlib.sha256()
    with file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def character_archive_name(archive: Path) -> str:
    """Read the character identity, not the original untrusted ZIP filename.

    Older packs without pack_version are stored as v1. This is a package label,
    not a claim about the underlying TTS training weights.
    """
    with zipfile.ZipFile(archive) as zf:
        with zf.open('character.json') as source:
            manifest = json.loads(source.read(1024 * 1024).decode('utf-8-sig'))
    identity = manifest.get('id')
    if not isinstance(identity, str) or not NAME.fullmatch(identity):
        raise ValueError('Character ID invalid')
    version = manifest.get('pack_version', '1')
    if isinstance(version, int) and version >= 1:
        version = str(version)
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError('Invalid character pack version')
    return f'AnimeVoiceTutor_Character_{identity}_v{version}.zip'


def archive_character(archive: Path, root: Path = ROOT) -> Path:
    _, folder = ensure_folders(root)
    return _copy_verified(archive, folder / character_archive_name(archive))


def archive_update(archive: Path, root: Path = ROOT) -> Path:
    updates, _ = ensure_folders(root)
    if not UPDATE_NAME.fullmatch(archive.name):
        raise ValueError('Expected AnimeVoiceTutor_Core_vX.Y.Z.zip or AnimeVoiceTutor_Update_vX.Y.Z.zip')
    return _copy_verified(archive, updates / archive.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init', action='store_true', help='Create packages/updates and packages/characters')
    parser.add_argument('--character', type=Path, help='Store a validated character ZIP')
    parser.add_argument('--update', type=Path, help='Store an official update or Core ZIP')
    parser.add_argument('--project', type=Path, default=ROOT)
    args = parser.parse_args()
    if sum([args.init, bool(args.character), bool(args.update)]) != 1:
        parser.error('Specify exactly one of --init, --character or --update')
    if args.init:
        updates, characters = ensure_folders(args.project)
        print('LOCAL_PACKAGES_READY:', updates, characters)
    elif args.character:
        print('CHARACTER_ZIP_ARCHIVED:', archive_character(args.character, args.project))
    else:
        print('UPDATE_ZIP_ARCHIVED:', archive_update(args.update, args.project))


if __name__ == '__main__':
    main()
