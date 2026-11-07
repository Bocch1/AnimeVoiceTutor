"""Download only a user-requested Hugging Face model into a local directory."""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=args.repo, local_dir=args.destination)
    print("MODEL_DOWNLOAD_COMPLETE")


if __name__ == "__main__":
    main()
