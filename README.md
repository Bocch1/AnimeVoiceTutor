# AnimeVoiceTutor

**A self-hosted Japanese conversation tutor with optional local character voices.**

English | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

AnimeVoiceTutor provides Japanese conversation, speech recognition (Qwen3-ASR), and character speech synthesis (GPT-SoVITS). Chat with an AI provider requires your own OpenAI/DeepSeek API key. No models, API keys or copyrighted character media are included in the small Core ZIP.

## Get started (Windows)

1. Download **`AnimeVoiceTutor_Core_v0.13.1.zip`** from the project's GitHub Releases page. Extract the **entire** ZIP to a writable folder. Do not run setup from an incremental update ZIP's `payload` directory.
2. Double-click **`First Run Setup.cmd`**. The language selector is always called **Language** (English / 简体中文 / 日本語). In Step 1, click **Install voice base**. **Diagnostics** checks the installed base and reports what is missing; **Advanced options** lets you use your existing ASR model or GPT-SoVITS engine.
3. In Step 2, select a **character ZIP** from the project's published GitHub Releases list, then click **Download and install selected character**. Alternatively, choose a trusted character ZIP already on your computer. You can also import a ZIP later in the Web app.
4. Double-click **`Start AnimeVoiceTutor.cmd`**. Use the app's Settings page to enter your own AI provider credentials. Speak, chat, listen to generated audio, and use **Exit application** in the sidebar when finished. `Stop AnimeVoiceTutor.cmd` is an emergency fallback.

You do **not** need to run a terminal for normal use. The setup window distinguishes environment installation/diagnosis from live speech: a successful environment check does not claim that a specific character's TTS weights are loaded. If TTS is initializing, allow it to load; check **Service status** if it fails.

**Platform target:** Windows 10/11 x64 and a compatible NVIDIA GPU/driver for CUDA 12.8. Fully automated installation is not guaranteed on all PCs, and an internet connection is needed for dependency/model downloads. The TTS source reference is pinned, but equivalence with the developer's locally modified GPT-SoVITS inference files has **not** been established. See [Installation](docs/INSTALLATION.md).

## Where are my downloaded packages?

The first-run wizard creates these local folders beside your Core source:

```text
packages/
  updates/       AnimeVoiceTutor_Core_v0.13.1.zip, AnimeVoiceTutor_Update_v0.13.1.zip
  characters/    AnimeVoiceTutor_Character_<id>_v<version>.zip
```

Imported character ZIPs are archived automatically. The installed/extracted character data continues to live in `data/character_packs/` and is not moved. When building a new Core locally, the output goes to `packages/updates/`. These folders are **private and Git-ignored**; neither the original character ZIP nor the installed weights are included in the public Core source package. See [Local package folders](docs/LOCAL_PACKAGES.md).

## Three everyday files

| Double-click | Purpose |
| --- | --- |
| `First Run Setup.cmd` | Install/check the base and import character ZIPs |
| `Start AnimeVoiceTutor.cmd` | Open the application without a persistent console |
| `Stop AnimeVoiceTutor.cmd` | Stop managed services if the in-app Exit control is unavailable |

Spaces in CMD filenames are supported by Windows. Keep the names unchanged; the provided scripts quote their paths. Diagnostic, test and export commands live in [`advanced/`](advanced/).

## Documentation

- [Installation and environment checks](docs/INSTALLATION.md)
- [Local ZIP archive and naming rules](docs/LOCAL_PACKAGES.md)
- [Character ZIP format](docs/CHARACTER_PACKS.md)
- [Real-user testing](docs/TESTING.md)
- [Publishing Core and updates](docs/PUBLISHING.md)

**Licenses:** The Core application source is MIT-licensed; GPT-SoVITS, FFmpeg, pretrained models, and character artwork/audio/weights have independent rights. Do not distribute third-party character media without permission. A takedown notice is not permission. See [Security](SECURITY.md) and [Third-party notices](THIRD_PARTY_NOTICES.md).
