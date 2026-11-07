"""Create a portable character ZIP from already-authorized local GPT-SoVITS files.

This does not modify the original project and does not upload any files.
The output may contain copyrighted voices and must not be distributed without
permission. The UI base ZIP supplies the character artwork and greeting catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
from urllib.parse import urlparse
import secrets
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voice_tutor.characters import validate_manifest, PackError, ALLOWED_EXT


def migrate(args):
    origin = args.project.resolve()
    preset = origin / 'configs' / 'frozen_tts_preset.json'
    profiles = origin / 'configs' / 'voice_profiles_v08.json'
    if not profiles.is_file():
        profiles = origin / 'configs' / 'voices.json'
    tts_root = (args.tts_root or (origin / 'external' / 'GPT-SoVITS-v5')).resolve()
    config = json.loads(preset.read_text(encoding='utf-8'))
    sources = json.loads(profiles.read_text(encoding='utf-8'))['voices']
    target = next((v for v in sources if v.get('id') == args.voice_id), None)
    if target is None:
        raise PackError(f'Voice profile not found: {args.voice_id}')
    audio = Path(target['reference_audio_path'])
    if not audio.is_absolute():
        audio = origin / audio
    weights = [(tts_root / config['gpt_weights']).resolve(),
               (tts_root / config['sovits_weights']).resolve()]
    for src in (audio, preset, *weights):
        if not src.is_file():
            raise FileNotFoundError(src)
    with tempfile.TemporaryDirectory(prefix='avt_migrate_') as work:
        stage = Path(work)
        with zipfile.ZipFile(args.ui_zip) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                rel = Path(name)
                if (name.startswith('/') or '\\' in name or '..' in rel.parts
                        or rel.suffix.lower() not in ALLOWED_EXT):
                    raise PackError('Unsafe UI base archive')
                destination = stage / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, destination.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
        raw = json.loads((stage / 'character.json').read_text(encoding='utf-8'))
        asset_map = {'models/gpt.ckpt': weights[0],
                     'models/sovits.pth': weights[1],
                     'audio/reference.wav': audio,
                     'configs/tts_preset.json': preset}
        for rel, source in asset_map.items():
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        raw['voice'] = {'id': args.voice_id, 'label': target.get('label', raw['display_name']),
                        'reference_audio_path': 'audio/reference.wav',
                        'prompt_text': target['prompt_text']}
        raw['model'] = {'engine': 'GPT-SoVITS-v5', 'gpt_weights': 'models/gpt.ckpt',
                        'sovits_weights': 'models/sovits.pth', 'preset': 'configs/tts_preset.json'}
        # Add cached greeting WAVs if present. Never synthesize or guess a file.
        cache = origin / 'data' / 'app' / 'greeting_audio_cache'
        all_records = [g for group in raw.get('greetings', {}).values() for g in group]
        all_records += raw.get('hidden_greetings', [])
        for record in all_records:
            identity = record['id']
            speech = record.get('ttsText') or record['text']
            digest = hashlib.sha256((identity + '\x00' + args.voice_id + '\x00' + speech).encode()).hexdigest()
            candidate = cache / f'secret_{digest}.wav'
            if not candidate.is_file():
                phrase = hashlib.sha256(speech.encode()).hexdigest()[:12]
                for legacy in [cache / f'{identity}_{phrase}_{args.voice_id}.wav',
                               cache / f'{identity}_{phrase}.wav']:
                    if legacy.is_file():
                        candidate = legacy
                        break
            if candidate.is_file() and candidate.stat().st_size > 44:
                with candidate.open('rb') as f:
                    if f.read(4) != b'RIFF':
                        continue
                dest = stage / 'audio' / 'greetings' / f'{identity}.wav'
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, dest)
                record['audio'] = dest.relative_to(stage).as_posix()
        missing = [record for record in all_records if not record.get('audio')]
        if missing and args.render_missing:
            uri = urlparse(args.tts_url)
            if uri.scheme != 'http' or uri.hostname not in {'127.0.0.1', 'localhost', '::1'}:
                raise PackError('Only localhost HTTP TTS is accepted')
            # The caller must start the intended voice's model in their own
            # existing TTS server. This script never loads arbitrary weights.
            with httpx.Client(timeout=180.0, trust_env=False) as client:
                for record in missing:
                    request = dict(config['inference'])
                    request.update({'text': record.get('ttsText') or record['text'],
                                    'ref_audio_path': str(audio),
                                    'prompt_text': target['prompt_text'],
                                    'seed': secrets.randbelow(2**32 - 1)})
                    response = client.post(args.tts_url, json=request)
                    response.raise_for_status()
                    payload = response.content
                    if len(payload) <= 44 or payload[:4] != b'RIFF' or payload[8:12] != b'WAVE':
                        raise PackError(f'TTS returned invalid WAV for {record["id"]}')
                    destination = stage / 'audio' / 'greetings' / f'{record["id"]}.wav'
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(payload)
                    record['audio'] = destination.relative_to(stage).as_posix()
            missing = []
        if args.require_recordings and missing:
            raise PackError(f'Missing {len(missing)} cached greeting WAVs. '
                            'Use --render-missing with the correct running local TTS model.')
        (stage / 'character.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
        validate_manifest(stage)
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(output)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    z.write(path, path.relative_to(stage).as_posix())
    print('COMPLETE_CHARACTER_PACK_CREATED:', output)
    print('Contains real voice weights/reference media; check redistribution rights before publishing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui-zip', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--voice-id', default='azusa_e36')
    parser.add_argument('--tts-root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render-missing', action='store_true', help='Generate missing greeting WAVs using your running local TTS model')
    parser.add_argument('--require-recordings', action='store_true', help='Fail if any hidden or timed greeting WAV is missing')
    parser.add_argument('--tts-url', default='http://127.0.0.1:9880/tts')
    migrate(parser.parse_args())

if __name__ == '__main__':
    main()
