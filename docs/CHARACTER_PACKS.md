# Character packs

AnimeVoiceTutor Core is character-neutral: it includes no fictional-character portrait, character-specific hidden greetings, voice weights, or reference recordings. Character resources are installed separately as local ZIP packages. The Core remains usable for text chat without a character pack.

## Install or switch a character

1. Obtain a character ZIP from a source authorized to distribute all its contents.
2. Open **Settings → Character → Install ZIP** and select the file.
3. After successful installation the app activates the character and updates its welcome screen, portrait, and greetings. Switch between installed characters and **Standard Japanese** in the same settings section.
4. For a pack with live voice weights, ensure a compatible GPT-SoVITS-v5 engine is configured and restart the managed TTS service when changing voice models.

Alternatively, install through Python:

```powershell
python tools/install_character_pack.py "C:\path\to\character.zip"
```

Pack data is stored under `data/character_packs/<id>/`; the selected ID is stored separately under `data/app/`. Both are local runtime state and are excluded from the public Core ZIP. An installed pack is not automatically updated by a new Core release.

A **UI-only** package can contain artwork, point-line animation, greetings, and optional prerecorded WAVs without a synthetic voice model. A **full voice** package also contains the GPT and SoVITS weights, reference WAV, and inference preset. Installing a full pack **does not install** the GPT-SoVITS engine or Python environment.

The importer rejects executable/script entries and unsafe paths. It does not make third-party model weights intrinsically safe; load only trusted packs. Duplicate character IDs are not overwritten automatically. Back up or remove the installed character directory deliberately before replacing a pack; do not change the Core source directory.

## ZIP layout (schema version 1)

```text
character.json
assets/portrait.png                 # Optional
assets/greeting_*.wav               # Optional prerecorded greetings
effects/portrait_points.json       # Optional, declarative animation
models/gpt.ckpt                    # Full voice pack
models/sovits.pth                  # Full voice pack
audio/reference.wav                # Full voice pack
configs/tts_preset.json            # Full voice pack
```

Example `character.json` (the `model` and `voice` sections are omitted in a UI-only pack):

```json
{
  "schema_version": 1,
  "id": "example_character",
  "display_name": "Example Character",
  "avatar": "日",
  "portrait": "assets/portrait.png",
  "effect_data": "effects/portrait_points.json",
  "greetings": {
    "morning": [{"id": "morning_1", "text": "おはようございます。"}],
    "afternoon": [{"id": "afternoon_1", "text": "こんにちは。"}],
    "evening": [{"id": "evening_1", "text": "こんばんは。"}],
    "night": [{"id": "night_1", "text": "こんばんは。"}]
  },
  "hidden_greetings": [],
  "voice": {
    "id": "example_voice",
    "label": "Example Voice",
    "reference_audio_path": "audio/reference.wav",
    "prompt_text": "Reference recording transcript"
  },
  "model": {
    "engine": "GPT-SoVITS-v5",
    "gpt_weights": "models/gpt.ckpt",
    "sovits_weights": "models/sovits.pth",
    "preset": "configs/tts_preset.json"
  }
}
```

Each greeting may also have an optional `audio` path to a WAV stored within the ZIP. Available prerecorded WAVs can play without live synthesis. If no recording is present, on-demand synthesis requires a working TTS service and a voice pack. The character ZIP contains declarative animation data, not executable custom frontend code.

## Create a pack from authorized local files

For a new character, inspect the CLI options:

```powershell
python tools/build_character_pack.py --help
```

For an existing installation with legacy voice files and a separately prepared UI ZIP, use:

```powershell
python tools/migrate_local_character.py --ui-zip "C:\path\to\character_ui.zip" --project "C:\path\to\existing_project" --output "C:\path\to\character_full.zip"
```

The migration helper copies the configured weights, reference WAV, frozen voice preset, and any existing greeting recordings. It does not retrain or modify the model. To require all greeting recordings in a pack, start the correct local TTS engine first and use `--render-missing --require-recordings`; inspect the manifest and synthesized audio before distribution. The program does not infer permission to redistribute the source materials.

## Runtime checks

- `voice_ready: true` in character listing means the pack contains expected voice resources. It does **not** mean a GPU inference engine is running.
- `tts_engine_available: true` means the configured GPT-SoVITS engine source can be found.
- `tts_ready: true` in `/api/status` means the active voice has a validated binding to the running TTS service.
- `Test AnimeVoiceTutor.cmd -Voice` performs actual TTS synthesis and ASR transcription when both services are configured.

A process listening on `9880` is not sufficient to claim that the selected character has loaded: the model-binding check must pass. Stop known conflicting TTS services before switching voice weights; do not terminate unrelated processes by PID alone.

## Distribution rights

The application MIT license covers its code, **not** optional character images, names, recordings, fine-tuned voice weights, or derivative media. Distribute a character ZIP only after confirming permission for **each** resource it contains. Core source releases should remain character-neutral.
