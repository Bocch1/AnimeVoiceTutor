"""Import a user-selected character archive and optionally activate it."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voice_tutor.characters import import_pack, select_character, archive_matches_installed, PackError


def install_once(archive: Path) -> dict:
    """Safely reuse an identical installed pack without overwriting local assets."""
    try:
        return import_pack(archive.resolve())
    except PackError as exc:
        if 'already installed' not in str(exc):
            raise
        with zipfile.ZipFile(archive) as source:
            entry = json.loads(source.read('character.json').decode('utf-8-sig'))
        identity = entry.get('id', '')
        if not isinstance(identity, str) or not archive_matches_installed(archive, identity):
            raise PackError('Character ID already exists with different files') from exc
        # Keep the ZIP in the local character archive even when its installed
        # directory already exists and contains identical files.
        from voice_tutor import characters as _characters
        if _characters.PACK_ROOT == _characters.ROOT / 'data' / 'character_packs':
            from tools.local_package_store import archive_character
            archive_character(archive)
        print('CHARACTER_PACK_ALREADY_INSTALLED_IDENTICAL:', identity)
        return {'id': identity}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--select', action='store_true')
    options = parser.parse_args()
    result = install_once(options.archive.resolve())
    if options.select:
        select_character(result['id'])
    print('CHARACTER_PACK_INSTALLED:', result['id'])
    if options.select:
        print('CHARACTER_SELECTED:', result['id'])


if __name__ == '__main__':
    main()
