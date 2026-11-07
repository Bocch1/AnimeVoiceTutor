"""Complete a character UI package with authorized local TTS files.

The core source does not bundle voice weights, reference WAVs or pre-recorded
character speech. Users may package material they are authorized to distribute.

Example:
  python tools/build_character_pack.py --base-zip Azusa_UI.zip \
    --gpt-weights my_gpt.ckpt --sovits-weights my_sovits.pth \
    --reference-audio reference.wav --preset preset.json \
    --prompt-text 'Japanese reference transcript' --output Azusa_Full.zip
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voice_tutor.characters import validate_manifest, PackError


def build(args):
    with tempfile.TemporaryDirectory(prefix='avt_pack_build_') as work:
        stage = Path(work)
        with zipfile.ZipFile(args.base_zip) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                # Only the trusted base is accepted; use the same strict verifier.
                from voice_tutor.characters import ALLOWED_EXT, MAX_FILES
                p = Path(item.filename)
                if (p.is_absolute() or '..' in p.parts or '\\' in item.filename
                        or item.filename.startswith('.') or p.suffix.lower() not in ALLOWED_EXT):
                    raise PackError('Unsafe base package path')
                target = stage / p
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as src, target.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
        manifest_file = stage / 'character.json'
        manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
        copy_map = {
            'models/gpt.ckpt': args.gpt_weights,
            'models/sovits.pth': args.sovits_weights,
            'audio/reference.wav': args.reference_audio,
            'configs/tts_preset.json': args.preset,
        }
        for rel, source in copy_map.items():
            src = Path(source).resolve()
            if not src.is_file():
                raise FileNotFoundError(src)
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        manifest['pack_version'] = getattr(args, 'pack_version', '1')
        manifest['voice'] = {
            'id': args.voice_id,
            'label': manifest['display_name'],
            'reference_audio_path': 'audio/reference.wav',
            'prompt_text': args.prompt_text,
        }
        manifest['model'] = {
            'engine': 'GPT-SoVITS-v5',
            'gpt_weights': 'models/gpt.ckpt',
            'sovits_weights': 'models/sovits.pth',
            'preset': 'configs/tts_preset.json',
        }
        color_avatar = getattr(args, 'avatar_color', None)
        if color_avatar is not None:
            avatar_source = Path(color_avatar).resolve()
            if not avatar_source.is_file() or avatar_source.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
                raise ValueError('Color avatar must be a readable image')
            avatar_rel = 'assets/avatar_color' + avatar_source.suffix.lower()
            avatar_dest = stage / avatar_rel
            avatar_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(avatar_source, avatar_dest)
            manifest['avatar_color'] = avatar_rel
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        validate_manifest(stage)
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.is_file():
            raise FileExistsError(f'Output already exists: {output}')
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            for file in sorted(stage.rglob('*')):
                if file.is_file():
                    archive.write(file, file.relative_to(stage).as_posix())
        print('CHARACTER_PACK_CREATED:', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-zip', required=True, type=Path)
    parser.add_argument('--gpt-weights', required=True, type=Path)
    parser.add_argument('--sovits-weights', required=True, type=Path)
    parser.add_argument('--reference-audio', required=True, type=Path)
    parser.add_argument('--avatar-color', type=Path, help='Optional original-color avatar image, separate from monochrome portrait')
    parser.add_argument('--preset', required=True, type=Path)
    parser.add_argument('--prompt-text', required=True)
    parser.add_argument('--pack-version', default='1', help='Character archive version, e.g. 1 or 1.1.0')
    parser.add_argument('--voice-id', default='azusa_e36')
    parser.add_argument('--output', required=True, type=Path)
    build(parser.parse_args())

if __name__ == '__main__':
    main()
