"""Install a trusted, data-only character ZIP under data/character_packs/.

Usage: python tools/install_character_pack.py path/to/character.zip
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voice_tutor.characters import import_pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    result = import_pack(args.archive.resolve())
    print('CHARACTER_PACK_INSTALLED:', result['id'], result['label'])

if __name__ == '__main__':
    main()
