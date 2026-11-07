"""Download an explicitly requested Hugging Face model and record its exact revision."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--revision', default='main')
    args = parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download
    # Resolve the moving branch name BEFORE downloading files, then fetch one
    # immutable commit. The receipt is machine-local, not a release baseline.
    info = HfApi().model_info(args.repo, revision=args.revision)
    sha = str(info.sha)
    if not (len(sha) == 40 and all(x in '0123456789abcdef' for x in sha.lower())):
        raise RuntimeError('Unable to resolve immutable Hugging Face revision')
    snapshot_download(repo_id=args.repo, revision=sha, local_dir=str(args.destination))
    args.destination.mkdir(parents=True, exist_ok=True)
    (args.destination / '.avt_model_receipt.json').write_text(
        json.dumps({'repository': args.repo, 'revision': sha}, indent=2) + '\n', encoding='utf-8')
    print('MODEL_DOWNLOAD_COMPLETE:', args.repo, sha)


if __name__ == '__main__':
    main()
