"""Optional local character packages, kept separate from the neutral core.

Packs are data, never executable Python/JS. Only explicitly permitted file types
and relative paths can be extracted from a user-supplied ZIP.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import zipfile

from .config import ROOT

PACK_ROOT = ROOT / 'data' / 'character_packs'
SELECTION = ROOT / 'data' / 'app' / 'selected_character.json'
IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]{1,47}$')
ALLOWED_EXT = {'.json', '.png', '.jpg', '.jpeg', '.webp', '.wav', '.ckpt', '.pth', '.safetensors'}
MAX_FILES = 300
MAX_TOTAL_BYTES = 8 * 1024**3
MAX_ZIP_BYTES = 8 * 1024**3
MAX_JSON_BYTES = 4 * 1024**2


class PackError(ValueError):
    pass


def _local_file(base: Path, rel: str, *, must_exist: bool = True) -> Path:
    if not isinstance(rel, str) or len(rel) > 256 or '\\' in rel:
        raise PackError('Unsafe pack asset path')
    parts = PurePosixPath(rel)
    if parts.is_absolute() or not parts.parts or any(x in ('.', '..') for x in parts.parts):
        raise PackError('Unsafe pack asset path')
    result = base.joinpath(*parts.parts).resolve()
    if not result.is_relative_to(base.resolve()):
        raise PackError('Unsafe pack asset path')
    if must_exist and (not result.is_file() or result.is_symlink()):
        raise PackError(f'Character asset missing: {rel}')
    return result


def _greetings(value, *, hidden=False):
    if not isinstance(value, list) or len(value) > 60:
        raise PackError('Invalid greeting list')
    seen = set()
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise PackError('Invalid greeting entry')
        identity, text = item.get('id'), item.get('text')
        if not isinstance(identity, str) or not IDENTIFIER.fullmatch(identity) or identity in seen:
            raise PackError('Invalid greeting ID')
        if not isinstance(text, str) or not 1 <= len(text) <= 600:
            raise PackError('Invalid greeting text')
        seen.add(identity)
        record = {'id': identity, 'text': text}
        for field in ('ttsText', 'audio'):
            if field in item:
                if not isinstance(item[field], str) or len(item[field]) > 600:
                    raise PackError('Invalid greeting field')
                record[field] = item[field]
        result.append(record)
    return result


def validate_manifest(folder: Path) -> dict:
    file = folder / 'character.json'
    if not file.is_file() or file.stat().st_size > MAX_JSON_BYTES:
        raise PackError('character.json missing or too large')
    try:
        raw = json.loads(file.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise PackError('Invalid character.json') from exc
    if not isinstance(raw, dict) or raw.get('schema_version') != 1:
        raise PackError('Unsupported character pack schema')
    identity = raw.get('id')
    if not isinstance(identity, str) or not IDENTIFIER.fullmatch(identity) or identity == 'default':
        raise PackError('Invalid character ID')
    title = raw.get('display_name')
    if not isinstance(title, str) or not 1 <= len(title) <= 100:
        raise PackError('Invalid character display name')
    for field in ('portrait', 'avatar_color', 'effect_data'):
        if raw.get(field):
            file_path = _local_file(folder, raw[field])
            if field in ('portrait', 'avatar_color') and file_path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
                raise PackError('Portrait must be an image')
            if field == 'effect_data':
                if file_path.suffix.lower() != '.json' or file_path.stat().st_size > 2_000_000:
                    raise PackError('Invalid effect data')
                try:
                    effects = json.loads(file_path.read_text(encoding='utf-8'))
                    if effects.get('type') != 'point_line_v1' or len(effects.get('points_base64', '')) > 150_000 or len(effects.get('outline_base64', '')) > 20_000:
                        raise ValueError('Invalid effect type or size')
                except (OSError, ValueError, AttributeError) as exc:
                    raise PackError('Invalid effect data') from exc
    group = raw.get('greetings', {})
    if not isinstance(group, dict) or set(group) - {'morning', 'afternoon', 'evening', 'night'}:
        raise PackError('Invalid greeting periods')
    for items in group.values():
        for record in _greetings(items):
            if record.get('audio'):
                if _local_file(folder, record['audio']).suffix.lower() != '.wav':
                    raise PackError('Greeting audio must be WAV')
    for record in _greetings(raw.get('hidden_greetings', []), hidden=True):
        if record.get('audio'):
            if _local_file(folder, record['audio']).suffix.lower() != '.wav':
                raise PackError('Hidden greeting audio must be WAV')
    voice = raw.get('voice')
    model = raw.get('model')
    if voice is not None:
        if not isinstance(voice, dict) or not isinstance(voice.get('id'), str) or not IDENTIFIER.fullmatch(voice['id']):
            raise PackError('Invalid voice profile')
        if not isinstance(voice.get('prompt_text'), str) or len(voice['prompt_text']) > 800:
            raise PackError('Invalid reference prompt')
        if _local_file(folder, voice.get('reference_audio_path', '')).suffix.lower() != '.wav':
            raise PackError('Voice requires a WAV reference')
        if not isinstance(model, dict):
            raise PackError('Voice profile requires model files')
        for key, extensions in [('gpt_weights', {'.ckpt'}), ('sovits_weights', {'.pth', '.safetensors'}), ('preset', {'.json'})]:
            if _local_file(folder, model.get(key, '')).suffix.lower() not in extensions:
                raise PackError(f'Invalid model asset: {key}')
    elif model is not None:
        raise PackError('Model specified without voice')
    return raw


def list_installed() -> list[dict]:
    result = []
    if PACK_ROOT.is_dir():
        for folder in sorted(PACK_ROOT.iterdir()):
            if not folder.is_dir() or folder.is_symlink():
                continue
            try:
                raw = validate_manifest(folder)
            except PackError:
                continue
            records = [entry for group in raw.get('greetings', {}).values() for entry in group]
            records += raw.get('hidden_greetings', [])
            result.append({'id': raw['id'], 'label': raw['display_name'],
                           'has_portrait': bool(raw.get('portrait')),
                           'has_color_avatar': bool(raw.get('avatar_color') or (folder / 'assets' / 'avatar_color.png').is_file()),
                           'voice_ready': bool(raw.get('voice')),
                           'recordings_present': sum(bool(entry.get('audio')) for entry in records),
                           'recordings_total': len(records),
                           'avatar': str(raw.get('avatar', '日'))[:2]})
    return result


def active_id() -> str:
    try:
        content = json.loads(SELECTION.read_text(encoding='utf-8'))
        candidate = content.get('id')
        if candidate in {item['id'] for item in list_installed()}:
            return candidate
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return 'default'


def active_manifest() -> tuple[Path | None, dict | None]:
    identity = active_id()
    if identity == 'default':
        return None, None
    folder = PACK_ROOT / identity
    try:
        return folder, validate_manifest(folder)
    except PackError:
        return None, None


def select_character(identity: str) -> None:
    if identity != 'default' and identity not in {item['id'] for item in list_installed()}:
        raise PackError('Character pack is not installed')
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    temp = SELECTION.with_suffix('.tmp')
    temp.write_text(json.dumps({'id': identity}), encoding='utf-8')
    os.replace(temp, SELECTION)


def current_voice_profiles() -> dict:
    folder, raw = active_manifest()
    if not raw or not isinstance(raw.get('voice'), dict):
        return {}
    voice = raw['voice']
    return {voice['id']: {
        'id': voice['id'], 'label': voice.get('label', raw['display_name']),
        'reference_audio_path': str(_local_file(folder, voice['reference_audio_path'])),
        'prompt_text': voice['prompt_text']
    }}


def active_preset() -> dict | None:
    folder, raw = active_manifest()
    if not raw or not raw.get('model'):
        return None
    model = raw['model']
    preset = json.loads(_local_file(folder, model['preset']).read_text(encoding='utf-8'))
    return {'preset': preset,
            'gpt': _local_file(folder, model['gpt_weights']),
            'sovits': _local_file(folder, model['sovits_weights'])}


def greetings_for_active() -> dict:
    folder, raw = active_manifest()
    if not raw:
        return {'greetings': {}, 'hidden_greetings': [], 'character_id': 'default'}
    return {'greetings': raw.get('greetings', {}),
            'hidden_greetings': raw.get('hidden_greetings', []),
            'character_id': raw['id']}


def public_pack_asset(identity: str, kind: str) -> Path:
    folder = PACK_ROOT / identity
    if identity not in {item['id'] for item in list_installed()}:
        raise PackError('Character pack not found')
    raw = validate_manifest(folder)
    if kind == 'avatar':
        # Dedicated original-color avatar is optional and independent of the
        # monochrome line-art source used by the welcome animation.
        if raw.get('avatar_color'):
            return _local_file(folder, raw['avatar_color'])
        local_color = folder / 'assets' / 'avatar_color.png'
        if local_color.is_file() and not local_color.is_symlink():
            return _local_file(folder, 'assets/avatar_color.png')
        if raw.get('portrait'):
            return _local_file(folder, raw['portrait'])
        raise PackError('No avatar image available')
    key = {'portrait': 'portrait', 'effects': 'effect_data'}.get(kind)
    if not key or not raw.get(key):
        raise PackError('Asset not available')
    return _local_file(folder, raw[key])


def import_pack(archive: Path) -> dict:
    if archive.stat().st_size > MAX_ZIP_BYTES:
        raise PackError('Character archive too large')
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='avt_character_', dir=PACK_ROOT) as temp_dir:
        stage = Path(temp_dir)
        try:
            with zipfile.ZipFile(archive) as z:
                entries = z.infolist()
                if not 1 <= len(entries) <= MAX_FILES:
                    raise PackError('Invalid archive file count')
                if sum(item.file_size for item in entries) > MAX_TOTAL_BYTES:
                    raise PackError('Uncompressed pack exceeds size limit')
                seen = set()
                for item in entries:
                    # On Windows, zipfile normalizes backslashes in item.filename.
                    # Keep the original central-directory spelling authoritative:
                    # a malicious ZIP entry must not become safe by normalization.
                    raw_name = item.orig_filename
                    name = item.filename
                    if raw_name != name or '\\' in raw_name:
                        raise PackError('Invalid raw ZIP path')
                    if '\\' in name or name.startswith('/') or ':' in name:
                        raise PackError('Invalid ZIP path')
                    parts = PurePosixPath(name.rstrip('/'))
                    if '..' in parts.parts or any(p.startswith('.') for p in parts.parts):
                        raise PackError('Invalid ZIP entry')
                    if name.lower() in seen:
                        raise PackError('Duplicate archive entry')
                    seen.add(name.lower())
                    file_type = (item.external_attr >> 16) & 0o170000
                    if file_type == 0o120000:
                        raise PackError('Symlinks are not allowed')
                    if item.is_dir():
                        continue
                    if len(parts.parts) > 7 or parts.suffix.lower() not in ALLOWED_EXT:
                        raise PackError('Unexpected character asset type')
                    target = stage.joinpath(*parts.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(item) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst, length=1024*1024)
        except (zipfile.BadZipFile, RuntimeError) as exc:
            raise PackError('Invalid character ZIP') from exc
        manifest = validate_manifest(stage)
        identity = manifest['id']
        target = PACK_ROOT / identity
        if target.exists():
            raise PackError('Character already installed; remove existing pack manually before replacing')
        # Keep a local copy of each imported ZIP for reinstall / transfer.
        # Isolated tests may override PACK_ROOT with a temp folder; archive only
        # when using the canonical data/character_packs location.
        if PACK_ROOT == ROOT / 'data' / 'character_packs':
            from tools.local_package_store import archive_character
            archive_character(archive, ROOT)
        os.replace(stage, target)
        return {'id': identity, 'label': manifest['display_name']}

BINDING = ROOT / 'data' / 'app' / 'tts_model_binding.json'


def _process_running(pid: int) -> bool:
    if sys.platform == 'win32':
        # Never use os.kill(pid, 0) on Windows: unlike POSIX, it may terminate
        # the target process. Query only the process handle and exit status.
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x1000, 0, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            status = ctypes.c_uint()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(status))) and status.value == 259
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def tts_binding_matches() -> bool:
    """Only use the model when our launcher bound this actual TTS listener.

    This intentionally fails closed for services reused from unrelated projects.
    """
    identity = active_id()
    if identity == 'default' or not current_voice_profiles():
        return False
    try:
        binding = json.loads(BINDING.read_text(encoding='utf-8-sig'))
        if binding.get('character_id') != identity:
            return False
        pid = int(binding.get('listener_pid', 0))
        if pid <= 0:
            return False
        return _process_running(pid)
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def archive_matches_installed(archive: Path, identity: str) -> bool:
    """Accept a repeated import only when every archived file equals the installed pack.

    No extraction occurs on this path. A different archive with the same ID must
    not silently select or overwrite existing voice weights.
    """
    folder = PACK_ROOT / identity
    try:
        if archive.stat().st_size > MAX_ZIP_BYTES:
            return False
        if validate_manifest(folder)['id'] != identity:
            return False
        actual = {p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if p.is_file()}
        if any(p.is_symlink() for p in folder.rglob('*')):
            return False
        with zipfile.ZipFile(archive) as source:
            members = [m for m in source.infolist() if not m.is_dir()]
            if len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_TOTAL_BYTES:
                return False
            seen = set()
            for member in members:
                rel = member.orig_filename
                parts = PurePosixPath(rel)
                file_type = (member.external_attr >> 16) & 0o170000
                if ('\\' in rel or parts.is_absolute() or any(x in ('.', '..') for x in parts.parts)
                    or len(parts.parts) > 7 or parts.suffix.lower() not in ALLOWED_EXT
                    or file_type == 0o120000 or rel in seen or rel not in actual):
                    return False
                seen.add(rel)
                digest = hashlib.sha256()
                with source.open(member) as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                        digest.update(chunk)
                installed_hash = hashlib.sha256()
                with actual[rel].open('rb') as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                        installed_hash.update(chunk)
                if digest.digest() != installed_hash.digest():
                    return False
            return seen == set(actual)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, PackError):
        return False
