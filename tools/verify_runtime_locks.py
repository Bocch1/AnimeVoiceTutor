#!/usr/bin/env python3
"""Read-only verification of Windows online-installer hashed dependency locks.

A valid lock is NOT proof of functional install, model licensing, or native
Conda dependency completeness. This module intentionally uses stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

NAME = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
VERSION = r"[A-Za-z0-9][A-Za-z0-9_.!+\-]*"
PIN = re.compile(rf"^({NAME})==({VERSION})(?=\s|;|$)")
HASH = re.compile(r"--hash=sha256:([a-fA-F0-9]{64})(?![a-fA-F0-9])")
# This URL is pinned to the upstream CPU TorchCodec 0.11.1 Windows cp310 wheel.
# No generic direct URL requirements are permitted in release locks.
CPU_CODEC_URL = (
    "https://download.pytorch.org/whl/cpu/"
    "torchcodec-0.11.1%2Bcpu-cp310-cp310-win_amd64.whl"
)
CPU_CODEC_DIRECT = re.compile(
    r"^torchcodec\s+@\s+(" + re.escape(CPU_CODEC_URL).replace("%2B", r"(?:%2B|\+)")
    + r")(?:#sha256=([a-fA-F0-9]{64}))?(?=\s|$)", re.IGNORECASE
)
ALLOWED_INDEX = re.compile(r"^https://(?:pypi\.org/simple|download\.pytorch\.org/whl/(?:cpu|cu\d{3,4}))/?$")
ROLES = ("web", "asr", "tts")


def canon(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def normalized_lines(body: str) -> list[str]:
    """Assemble uv's backslash-continued requirements, ignoring comments."""
    logical: list[str] = []
    partial = ""
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        if continued:
            line = line[:-1].strip()
        partial = (partial + " " + line).strip()
        if not continued:
            logical.append(partial)
            partial = ""
    if partial:
        raise ValueError("Unterminated multiline requirement")
    return logical


def parse_pins(body: str, *, require_hash: bool) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in normalized_lines(body):
        if line.startswith("--"):
            if require_hash:
                option = re.match(r"^--(?:extra-index-url|index-url)\s+(\S+)$", line)
                if not option or not ALLOWED_INDEX.fullmatch(option.group(1)):
                    raise ValueError("Unapproved dependency index or option in lock")
            else:
                raise ValueError("Unexpected option in frozen dependency snapshot")
            continue
        direct_codec = CPU_CODEC_DIRECT.match(line) if require_hash else None
        if direct_codec:
            name, version = "torchcodec", "0.11.1+cpu"
            tail = line[direct_codec.end():].strip()
            hashes = HASH.findall(tail)
            # Require the final lock to carry an explicit archive digest; uv
            # must not be allowed to fetch unverified direct URLs at install.
            if not hashes or HASH.sub("", tail).strip():
                raise ValueError("CPU TorchCodec direct wheel must have only SHA256 hashes")
            if direct_codec.group(2) and direct_codec.group(2).lower() not in [h.lower() for h in hashes]:
                raise ValueError("CPU TorchCodec URL fragment conflicts with lock hashes")
            if name in pins:
                raise ValueError("Duplicate package entry: " + name)
            pins[name] = version
            continue
        match = PIN.match(line)
        if match is None:
            raise ValueError("Unpinned, editable, or unsupported requirement")
        name, version = canon(match.group(1)), match.group(2)
        if name in pins:
            raise ValueError("Duplicate package entry: " + name)
        if require_hash:
            hashes = HASH.findall(line)
            if not hashes:
                raise ValueError("A locked package is missing its SHA256: " + name)
            tail = line[match.end():]
            tail = HASH.sub("", tail).strip()
            if "--" in tail or (tail and not tail.startswith(";")):
                raise ValueError("Unexpected non-hash content in lock for " + name)
        pins[name] = version
    if not pins:
        raise ValueError("Requirements file is empty")
    return pins


def check_role(snapshot: dict, role: str, frozen: str, lock: str) -> dict:
    if role not in ROLES:
        raise ValueError("Unknown installer role")
    if snapshot.get("schema") != 1 or snapshot.get("application") != "AnimeVoiceTutor":
        raise ValueError("Unsupported dependency snapshot")
    entry = snapshot.get("roles", {}).get(role)
    if not isinstance(entry, dict):
        raise ValueError("Snapshot does not contain selected role")
    expected_digest = entry.get("requirements_sha256")
    if hashlib.sha256(frozen.encode("utf-8")).hexdigest() != expected_digest:
        raise ValueError("Frozen requirements do not match their recorded SHA256")
    original = parse_pins(frozen, require_hash=False)
    resolved = parse_pins(lock, require_hash=True)
    direct_codec_rows = [line for line in normalized_lines(lock)
                         if CPU_CODEC_DIRECT.match(line)]
    if direct_codec_rows:
        # Restrict the exceptional CPU wheel to the precisely audited TTS
        # snapshot; other roles/versions or future variants need fresh review.
        if (role != "tts" or entry.get("python") != "3.10.22"
                or original.get("torchcodec") != "0.11.1+cpu"
                or entry.get("torch_extra_index") != "https://download.pytorch.org/whl/cu128"):
            raise ValueError("CPU TorchCodec wheel source is not approved for this role/runtime")
    # Always compare non-Torch packages exactly. For a Web CPU build only,
    # pip freeze may report the distribution's public metadata version while
    # torch.__version__ includes the CPU build suffix. Accept that one
    # discrepancy only when the runtime version independently recorded in
    # the snapshot agrees exactly with the resolved CPU wheel. This does not
    # establish binary identity; an isolated runtime smoke test is required.
    missing = {name: version for name, version in original.items()
               if name != "torch" and resolved.get(name) != version}
    torch_variant_reconciled = False
    if "torch" in original:
        expected_torch, locked_torch = original["torch"], resolved.get("torch")
        if expected_torch != locked_torch:
            runtime_torch = str(entry.get("torch", ""))
            from_index = entry.get("torch_extra_index")
            known_cpu_index = from_index in (
                "https://download.pytorch.org/whl/cpu",
                "https://download.pytorch.org/whl/cpu/",
            )
            if (role == "web" and known_cpu_index
                    and isinstance(locked_torch, str)
                    and expected_torch == runtime_torch.partition("+")[0]
                    and runtime_torch == locked_torch
                    and locked_torch.endswith("+cpu")
                    and "+" not in expected_torch
                    and entry.get("torch_cuda") is None):
                torch_variant_reconciled = True
            else:
                missing["torch"] = expected_torch
    if missing:
        issues = []
        for name, old in sorted(missing.items()):
            new = resolved.get(name)
            if name == "torch":
                issues.append(f"torch (freeze={old!r}, runtime={entry.get('torch')!r}, resolved={new!r})")
            else:
                issues.append(f"{name} (freeze={old!r}, resolved={new!r})")
        raise ValueError("Resolved lock drifted from installed package versions: " + "; ".join(issues))
    # Compilation uses `uv pip compile --torch-backend <cpu|cu128>`; uv's
    # default first-index policy keeps all non-PyTorch packages on PyPI.
    # This backend choice is in the snapshot and MUST be applied again when
    # installing the lock with `uv pip sync`. Do not emit an extra-index-url:
    # it would make generic packages vulnerable to the PyTorch mirror's pins.
    options = [line for line in normalized_lines(lock) if line.startswith("--")]
    if '--index-url https://pypi.org/simple' not in options:
        raise ValueError("The PyPI primary index is missing from the lock")
    if any(option.startswith('--extra-index-url ') for option in options):
        raise ValueError("Unscoped extra-index-url is not allowed; use --torch-backend")
    index = entry.get("torch_extra_index")
    backend = None
    if index:
        if not isinstance(index, str) or not ALLOWED_INDEX.fullmatch(index):
            raise ValueError("Unapproved PyTorch index in snapshot")
        if not index.startswith('https://download.pytorch.org/whl/'):
            raise ValueError("Unsupported PyTorch backend index")
        backend = index.rstrip('/').rsplit('/', 1)[-1]
        if 'torch' not in original:
            raise ValueError("Snapshot declares a PyTorch backend but has no torch pin")
        # Guard against accidentally compiling the CUDA snapshot against
        # CPU wheels or vice versa. Other package names remain unaltered.
        # For a Web public-version alias, compare the locked build to the
        # independently recorded import version; all other cases retain the
        # original strict snapshot check.
        inspected_torch = resolved['torch'] if torch_variant_reconciled else original['torch']
        if '+' + backend not in inspected_torch.lower():
            raise ValueError("Installed torch version does not match its backend")
    return {"role": role, "frozen_packages": len(original), "resolved_packages": len(resolved),
            "lock_sha256": hashlib.sha256(lock.encode("utf-8")).hexdigest(),
            "snapshot_matches": True, "all_packages_hashed": True,
            "torch_backend": backend, "install_requires_torch_backend": backend is not None,
            "web_cpu_torch_distribution_alias": torch_variant_reconciled,
            "tts_cpu_torchcodec_direct_wheel": bool(direct_codec_rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--role", required=True, choices=ROLES)
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--lock", required=True)
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig"))
        frozen = Path(args.requirements).read_text(encoding="utf-8-sig")
        lock = Path(args.lock).read_text(encoding="utf-8-sig")
        result = check_role(snapshot, args.role, frozen, lock)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("LOCK CHECK FAILED: " + str(exc), file=sys.stderr)
        return 1
    print("LOCK CHECK OK: " + json.dumps(result, sort_keys=True))
    if result["web_cpu_torch_distribution_alias"]:
        print("NOTE: Web CPU PyTorch import version matches; installed wheel identity is NOT proven. Run a clean-install smoke test.")
    print("PENDING: native/Conda dependencies, GPU drivers, model authorization, clean install, real ASR/TTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
