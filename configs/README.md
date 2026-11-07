# Local configuration

AnimeVoiceTutor Core does not ship provider secrets, speaker recordings, trained weights, or a default character voice.

- **AI provider:** configure the provider and API key in the Web application settings. Do not commit credentials or a populated `.env` file.
- **ASR and GPT-SoVITS runtime paths:** use `Use Existing Models.cmd` or `scripts/reuse_existing_installation.ps1` to link existing Python environments, ASR weights and the GPT-SoVITS engine in machine-local `.avt-local.ps1`.
- **Character voice:** install a compatible character ZIP using **Settings → Character**. A voice pack contains its own model weights, reference audio and TTS preset; legacy private files do not automatically activate a character.

Files such as `frozen_tts_preset.example.json`, `voice_profiles_v08.example.json`, and `voice_profiles_v08.sample.json` document legacy configuration formats or aid migration from older installations. They contain no distributable trained voice. Do not edit them to include personal paths or credentials; use private, Git-ignored files for local configuration instead.

See [Installation](../docs/INSTALLATION.md) and [Character packs](../docs/CHARACTER_PACKS.md).
