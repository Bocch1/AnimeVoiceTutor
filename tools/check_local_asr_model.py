"""Minimum file-integrity check for an already downloaded Qwen3-ASR model."""

import argparse
import json
from pathlib import Path


def complete(directory: Path) -> bool:
    if not (directory / 'config.json').is_file():
        return False
    index_files = list(directory.glob('*.safetensors.index.json')) + list(directory.glob('*.bin.index.json'))
    if index_files:
        for index in index_files:
            try:
                manifest = json.loads(index.read_text(encoding='utf-8'))
                shards = set(manifest['weight_map'].values())
            except (OSError, ValueError, TypeError, KeyError):
                return False
            if not shards or any(not (directory / name).is_file() or (directory / name).stat().st_size == 0 for name in shards):
                return False
        return True
    return any(p.is_file() and p.stat().st_size > 0
               for pattern in ('*.safetensors', 'pytorch_model*.bin') for p in directory.glob(pattern))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model_dir', type=Path)
    args = parser.parse_args()
    ok = complete(args.model_dir)
    print('ASR_MODEL_FILES_PRESENT' if ok else 'ASR_MODEL_FILES_MISSING_OR_INCOMPLETE')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
