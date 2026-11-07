# AnimeVoiceTutor

**Local-first Japanese conversation practice** with AI chat, optional speech recognition, and installable character voices.

**English** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

AnimeVoiceTutor is a self-hosted, browser-based application for practicing Japanese. Use the character-neutral Core for text conversations and corrections, then add optional ASR and speech synthesis when the required models and runtime are configured. The application does not provide a hosted AI service or an included commercial API key.

## What it does

- Practice conversations in Japanese using a configured OpenAI or DeepSeek API provider.
- Review corrections, edit messages, and continue a conversation with its context.
- Keep conversation history with automatic titles and pinned sessions.
- Dictate Japanese with optional local Qwen3-ASR.
- Listen to responses using optional local GPT-SoVITS and an installed compatible character voice pack.
- Switch between English, Simplified Chinese, and Japanese interface languages.
- Start with a neutral, time-aware welcome screen; install character portraits, animations, greetings, and voices separately.

## Downloads and editions

| Component | Included in Core source ZIP? | Notes |
| --- | --- | --- |
| Web application and Windows launch scripts | Yes | Runs without speech models |
| Dependency definitions, setup scripts and tests | Yes | Setup requires downloads of Python/packages |
| Qwen3-ASR model | No | Optional separate model download |
| GPT-SoVITS inference engine | No | Install or link a compatible engine separately |
| Character voice weights, portrait and recordings | No | Optional authorized character ZIP |
| AI provider access or API key | No | Configure your own provider |

The Core archive is **source code plus launch/setup scripts**, not a packaged `.exe` or an offline voice installer. Character packs are optional, and the standard Core does not speak in a character voice by itself.

## Quick start on Windows

1. Download the Core source ZIP from [GitHub Releases](../../releases), or clone the repository. Extract the ZIP to a new folder.
2. Double-click **`Setup AnimeVoiceTutor.cmd`** to install the Web runtime. Alternatively, choose Web, ASR, and/or TTS environments through **`Quick Setup.cmd`**.
3. Double-click **`Start AnimeVoiceTutor.cmd`**. The default address is `http://127.0.0.1:8767`.
4. In **Settings**, configure an AI provider and an API key for online conversations.
5. Exit in the application or run **`Stop AnimeVoiceTutor.cmd`**.

The Web UI can launch without an ASR model or character pack. Actual AI responses require a configured provider and network connectivity. Quick Setup installs Python dependencies only; it does **not** download ASR weights, the GPT-SoVITS engine, character media, or FFmpeg.

**System support:** Windows x64 with PowerShell 5.1 or later. Speech acceleration requires compatible NVIDIA drivers, CUDA/PyTorch and FFmpeg/ffprobe. The locked environment recipes use Python 3.11 (Web), 3.12 (ASR), and 3.10 (TTS). See [Installation](docs/INSTALLATION.md) for supported setup methods and limitations.

## Optional speech and character packs

For Japanese microphone transcription, install the ASR runtime and then run **`Download ASR Model.cmd`**. A larger Qwen3-ASR option is also available.

For character TTS, provide a compatible GPT-SoVITS-v5 engine and its Python runtime, then install an authorized character ZIP through **Settings → Character → Install ZIP**. A complete voice pack contains its own voice weights, reference audio and configuration; the engine itself remains a separate dependency. Switch characters in Settings and restart the managed TTS service when changing voice weights.

An installed pack does not grant permissions to share its artwork, source recordings, or weights. Do not install untrusted model files. See [Character packs](docs/CHARACTER_PACKS.md).

## Diagnostics and development

From the project folder in PowerShell:

```powershell
& '.\Doctor AnimeVoiceTutor.cmd'    # Check installed paths and dependencies
& '.\Verify Source.cmd'             # Public source structure and regression tests
& '.\Test AnimeVoiceTutor.cmd'      # Check a running Web service
& '.\Test AnimeVoiceTutor.cmd' -Voice  # Real TTS + ASR smoke test when configured
```

The voice smoke test verifies an audible WAV and ASR transcription, not speaker similarity or an online AI-provider response. Configure the provider separately in Settings.

For development with your own Python environment:

```powershell
python -m pip install -e ".[test]"
python -m pytest -q tests
```

This pip path installs the Web/test dependencies, not the optional GPU engines or weights. Refer to [Installation](docs/INSTALLATION.md) and [Testing](docs/TESTING.md) for further checks.

## Repository layout

- `voice_tutor/` — application backend and character-pack integration
- `web/` — browser interface
- `services/` — ASR service
- `scripts/` — setup, startup, diagnostics, and source export
- `tools/` — pack building, installation, and other local utilities
- `release/` — public-file allowlist and dependency specifications
- `tests/` — automated regression tests
- `docs/` — installation, character-pack, testing, and publishing guides

To make a public source ZIP from a development checkout, run **`Build Public Source.cmd`**. The exporter includes only files in `release/public_source_files.txt`, tests the clean source stage and excludes local configurations, models, histories, and environments. Instructions for updating GitHub through its website or GitHub Desktop are in [Publishing](docs/PUBLISHING.md).

## License and attribution

Application source is licensed under [MIT](LICENSE). Third-party dependencies, pretrained models, audio, artwork, and derivative character assets have **separate** licenses or permissions. No character art, fine-tuned voice weights, reference recordings, or third-party engine source is bundled in Core. See [Third-party notices](THIRD_PARTY_NOTICES.md) and [Security](SECURITY.md).
