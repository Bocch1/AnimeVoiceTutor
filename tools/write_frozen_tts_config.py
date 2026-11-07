"""Create a separate GPT-SoVITS API configuration without altering upstream files."""

from pathlib import Path
import json
import argparse
import yaml
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def generate(tts_root: Path) -> Path:
    source = tts_root / "GPT_SoVITS" / "configs" / "tts_infer.yaml"
    from voice_tutor.characters import active_preset
    active = active_preset()
    if not active:
        raise RuntimeError('No active character with a complete TTS model pack')
    preset = active['preset']
    gpt = active['gpt']
    sovits = active['sovits']
    for f in (source, gpt, sovits):
        if not f.is_file():
            raise FileNotFoundError(f"Required upstream GPT-SoVITS file missing: {f}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["custom"].update({
        "device": "cuda",
        "is_half": preset["precision"] == "fp16",
        "version": preset["model_version"],
        "t2s_weights_path": str(gpt.resolve()),
        "vits_weights_path": str(sovits.resolve()),
    })
    target = tts_root / "TEMP" / "jvt_frozen_tts_api.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("GPT weights:", gpt)
    print("SoVITS weights:", sovits)
    print("Precision:", preset["precision"])
    print("TTS API config:", target)
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tts-root", type=Path, required=True)
    args = p.parse_args()
    print(generate(args.tts_root.resolve()))


if __name__ == "__main__":
    main()
