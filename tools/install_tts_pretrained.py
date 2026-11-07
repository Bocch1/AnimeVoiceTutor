"""Fetch and safely install upstream GPT-SoVITS Japanese inference prerequisites.

Third-party download is NOT version locked until upstream asset SHA-256 is
verified against a release-published digest. The local receipt records what
was downloaded so the maintainer can later lock an exact asset.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
from urllib.request import Request, urlopen
import zipfile

URL = "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main/pretrained_models.zip"
CHUNK = 1024 * 1024
MAX_DOWNLOAD_BYTES = 12 * 1024**3
MAX_UNCOMPRESSED_BYTES = 22 * 1024**3


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    result = []
    total = 0
    for member in archive.infolist():
        # On Windows, zipfile normalizes backslashes in .filename before we
        # see the member. .orig_filename retains the raw name from the ZIP.
        raw = member.orig_filename
        if (raw != member.filename or not raw or "\\" in raw or raw.startswith("/") or ":" in raw
                or any(p in ("", ".", "..") for p in raw.split("/"))
                or (member.external_attr >> 16) & 0o170000 == stat.S_IFLNK):
            raise ValueError(f"Unsafe archive path: {raw!r}")
        if not member.is_dir() and not (raw.startswith("pretrained_models/") or raw.startswith("GPT_SoVITS/pretrained_models/")):
            raise ValueError(f"Unexpected pretrained path: {raw!r}")
        total += member.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Pretrained archive exceeds extraction limit")
        result.append(member)
    if not any(not x.is_dir() for x in result):
        raise ValueError("Empty pretrained archive")
    return result


def install(archive_path: Path, engine: Path, expected_sha: str | None = None) -> str:
    digest = hashlib.sha256()
    with archive_path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if expected_sha and actual.lower() != expected_sha.lower():
        raise ValueError("Pretrained archive SHA-256 mismatch")
    dest_root = engine / "GPT_SoVITS"
    if not (engine / "api_v2.py").is_file():
        raise ValueError("No GPT-SoVITS engine found at the target directory")
    with zipfile.ZipFile(archive_path) as source:
        members = safe_members(source)
        # All names resolve into GPT_SoVITS/pretrained_models/.
        with tempfile.TemporaryDirectory(prefix="avt_pretrained_", dir=str(engine.parent)) as td:
            stage = Path(td)
            for member in members:
                if member.is_dir():
                    continue
                name = member.filename
                relative = name.removeprefix("GPT_SoVITS/")
                target = stage.joinpath(*PurePosixPath(relative).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as inp, target.open("wb") as out:
                    shutil.copyfileobj(inp, out, CHUNK)
            source_root = stage / "pretrained_models"
            if not source_root.is_dir():
                raise ValueError("Archive did not contain pretrained_models")
            destination = dest_root / "pretrained_models"
            # Do not overwrite preexisting model weights. Refuse incomplete/conflicting installs.
            if destination.exists() and any(destination.rglob("*")):
                raise FileExistsError("Pretrained directory already populated. Check it manually; existing files will not be overwritten.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_root), str(destination))
    receipt = engine / ".avt_pretrained_receipt.json"
    receipt.write_text(json.dumps({"url": URL, "sha256": actual, "verified_expected_sha256": bool(expected_sha)}, indent=2) + "\n", encoding="utf-8")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--expected-sha256", default="")
    opts = parser.parse_args()
    opts.engine.parent.mkdir(parents=True, exist_ok=True)
    if opts.archive:
        print("LOCAL_ARCHIVE:", opts.archive)
        print("PRETRAINED_SHA256:", install(opts.archive, opts.engine, opts.expected_sha256 or None))
        return
    with tempfile.TemporaryDirectory(prefix="avt_download_", dir=str(opts.engine.parent)) as td:
        archive = Path(td) / "pretrained_models.zip"
        print("DOWNLOADING_UPSTREAM_PRETRAINED:", URL, flush=True)
        request = Request(URL, headers={"User-Agent": "AnimeVoiceTutor-Installer/0.13.1"})
        size = 0
        with urlopen(request, timeout=90) as response, archive.open("wb") as out:
            while block := response.read(CHUNK):
                size += len(block)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Download exceeds maximum allowed size")
                out.write(block)
        print("PRETRAINED_SHA256:", install(archive, opts.engine, opts.expected_sha256 or None), flush=True)
        if not opts.expected_sha256:
            print("NOTE: Upstream asset had no fixed expected hash; receipt saved. This is not a bit-for-bit reproducible baseline.", flush=True)


if __name__ == "__main__":
    main()
