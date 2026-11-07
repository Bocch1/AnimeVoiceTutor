"""Export a portable, reviewed-source allowlist from the canonical developer tree.

All source files come from this project, not from old release archives. Tests
run in an isolated temporary copy, so local backups and external engines are
never part of pytest discovery. Does not install or touch local model runtimes.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = 'release/public_source_files.txt'

# Avoid capturing real provider credentials or accidentally leaking OS user paths.
SECRET_PATTERNS = (
    re.compile(r'(?im)^[ \t]*(?:DEEPSEEK_API_KEY|OPENAI_API_KEY|HF_TOKEN|GITHUB_TOKEN|AWS_SECRET_ACCESS_KEY)[ \t]*=[ \t]*(?![ \t]*(?:#|$))[^\s#]+'),
    re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b'),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{25,}\b'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'\bAIza[0-9A-Za-z_-]{30,}\b'),
    re.compile(r'(?i)[A-Z]:[/\\]Users[/\\][^/\\\s<>{}]+[/\\]'),
    re.compile(r'(?i)[A-Z]:[/\\]codes[/\\]github[/\\]'),
)

def public_paths(root: Path = PROJECT_ROOT) -> list[str]:
    sys.path.insert(0, str(root))
    from scripts.verify_public_source import is_private_path
    manifest = root / MANIFEST
    if not manifest.is_file():
        raise RuntimeError(f'Public source manifest missing: {manifest}')
    entries = [line.strip() for line in manifest.read_text(encoding='utf-8').splitlines()
               if line.strip() and not line.lstrip().startswith('#')]
    if len(entries) != len(set(entries)) or entries != sorted(entries):
        raise RuntimeError('Public source manifest has duplicate or unsorted entries')
    if MANIFEST not in entries:
        raise RuntimeError('Manifest must include itself')
    for name in entries:
        path = PurePosixPath(name)
        if name != path.as_posix() or '\\' in name or is_private_path(name) or path.is_absolute() or '..' in path.parts:
            raise RuntimeError(f'Disallowed public source path: {name}')
        target = root.joinpath(*path.parts)
        if not target.is_file() or target.is_symlink():
            raise RuntimeError(f'Public file is missing or a symlink: {name}')
        if target.stat().st_size > 2_000_000:
            raise RuntimeError(f'Public file unexpectedly large: {name}')
    return entries

def check_text_privacy(root: Path, names: list[str]) -> None:
    for name in names:
        file = root.joinpath(*PurePosixPath(name).parts)
        if file.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
            continue
        raw = file.read_bytes()
        if b'\x00' in raw:
            raise RuntimeError(f'Binary file not permitted in public source: {name}')
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise RuntimeError(f'Non-UTF8 text file: {name}') from exc
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            raise RuntimeError(f'Credential or developer-specific path detected: {name}')

def build(output: Path, *, root: Path = PROJECT_ROOT, skip_tests: bool = False) -> Path:
    names = public_paths(root)
    check_text_privacy(root, names)
    with tempfile.TemporaryDirectory(prefix='avt_source_export_') as work:
        stage = Path(work) / 'source'
        for name in names:
            source = root.joinpath(*PurePosixPath(name).parts)
            target = stage.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        env = os.environ.copy()
        env['PYTHONPATH'] = str(stage)  # do not import developer-only tools/external sources
        check = subprocess.run([sys.executable, 'scripts/verify_public_source.py'], cwd=stage, env=env, check=False)
        if check.returncode:
            raise RuntimeError('Clean source structure check failed')
        if not skip_tests:
            check = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests'], cwd=stage, env=env, check=False)
            if check.returncode:
                raise RuntimeError('Clean source regression tests failed')
        output = output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output == root.resolve() or output.is_relative_to(root.resolve()):
            raise RuntimeError('Output ZIP must be outside the developer project')
        tmp = output.with_name(output.name + '.incomplete')
        try:
            with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for name in names:
                    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    zf.writestr(info, stage.joinpath(*PurePosixPath(name).parts).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            sys.path.insert(0, str(stage))
            # Direct import of verifier from tested staging tree; no extracted model data.
            import importlib.util
            spec = importlib.util.spec_from_file_location('avt_archive_verifier', stage/'scripts/verify_public_source.py')
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            module.verify_archive(tmp)
            os.replace(tmp, output)
        finally:
            if tmp.exists():
                tmp.unlink()
    print(f'PUBLIC_SOURCE_ARCHIVE_CREATED: {output}')
    print(f'PUBLIC_SOURCE_FILE_COUNT: {len(names)}')
    return output

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Destination ZIP path (default: Downloads)')
    parser.add_argument('--skip-tests', action='store_true', help='For development only; public releases must run tests')
    args = parser.parse_args()
    import tomllib
    release_version = tomllib.loads((PROJECT_ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    output = args.output or (Path.home()/'Downloads'/f'AnimeVoiceTutor_Source_v{release_version}_from_project.zip')
    try:
        build(output, skip_tests=args.skip_tests)
    except Exception as exc:
        print(f'PUBLIC_SOURCE_EXPORT_FAILED: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc

if __name__ == '__main__':
    main()
