# Install AnimeVoiceTutor — AI character voice chat

For ordinary use, open the project folder in **Windows File Explorer** and double-click the files described here. A terminal is not required.

## Requirements

The primary accelerated target is **Windows 10/11 x64** with a compatible NVIDIA GPU and driver supporting CUDA 12.8. Internet access and sufficient disk space are required to download dependencies, Qwen3-ASR, GPT-SoVITS and pretrained resources. FFmpeg/ffprobe are also required. AI chat needs a separately configured OpenAI/DeepSeek API key. Compatibility may vary with hardware, drivers, and system configuration; other operating systems and GPU types have not been established as supported profiles.

## First use: voice environment, then a character pack

1. Download `AnimeVoiceTutor_Core_v0.13.1.zip` from the **[official GitHub Releases](https://github.com/Bocch1/AnimeVoiceTutor/releases)** page. Extract the **whole** ZIP into a writable local folder, for example `C:\Apps\AnimeVoiceTutor`. Do not launch scripts from a patch ZIP's `payload` directory.
2. Double-click `First Run Setup.cmd`. Choose your language from **Language** (this label is always English).
3. **Step 1 — Voice environment:** click **Install voice base** to install or repair the Web, ASR and TTS runtimes, the Qwen3-ASR 1.7B model and the GPT-SoVITS inference prerequisites. **Diagnostics** checks the installed components; green success means the base checks passed. **Advanced options** permits existing engine and ASR model paths, a smaller ASR model, and a separately reviewed engine overlay. Installation may download multiple gigabytes.
4. **Step 2 — Character:** download an **AnimeVoiceTutor_Character_*.zip** file from the same Release Assets when one is published. Use **Refresh releases** and **Download and install selected character**, or choose that previously downloaded ZIP from your computer. These are AnimeVoiceTutor-specific character packages, not arbitrary standalone `.pth` weights. Do not import untrusted or unauthorized packs.
5. Double-click `Start AnimeVoiceTutor.cmd`. The app opens in a browser-style window without a persistent console. Enter your own AI provider key under Settings. Confirm recording, transcription and newly generated character speech in the Web interface.
6. Click **Exit application** in the Web sidebar. `Stop AnimeVoiceTutor.cmd` is a fallback if the Web exit is unavailable.

When using an existing compatible installation, **Diagnostics** may pass without running Install again. If it fails, inspect the named missing component; **Install** attempts to repair it. A successful environment diagnosis is **not a claim that a selected character's weights have already loaded**. A pre-recorded greeting can play without live GPT-SoVITS inference. If live TTS is unavailable, open Web **Service status** and choose **Retry character voice**.

## Local package organization

`First Run Setup.cmd` creates `packages/updates` and `packages/characters`. Imported character ZIPs are archived in the latter and extracted model files remain in `data/character_packs`. Building a Core release places the ZIP in `packages/updates`. See [Local packages](LOCAL_PACKAGES.md) for naming and version rules.

## Existing models and reproducibility

Advanced installation can use an existing GPT-SoVITS folder containing `api_v2.py` and an existing Qwen3-ASR model folder. It checks important paths but cannot guarantee that every unseen model is compatible. The published `release/install_specs/voice_baseline.json` pins the upstream GPT-SoVITS source commit (`04a44eb977586645f33594b72af13a035a2056c6`) and Python dependency lock digests; the original developer's engine **also has local uncommitted changes** that are not yet part of a distributable overlay. Upstream pretrained and ASR downloads are not all locked to developer-verified hashes. Do not claim that this preview perfectly reproduces every audio sample on every GPU.

If a trusted compatibility overlay is published, it can be selected under **Advanced options**. Overlays require explicit opt-in and validate file SHA-256 before applying, with backups. A plain upstream source ZIP is not a compatibility overlay.

## If something fails

- **Installation fails:** check its component-specific error and `data/logs/first_run/`; retry Install after resolving driver, disk, download or file-permission issues.
- **Cannot download character:** verify the project's real GitHub Releases URL and whether an authorized character ZIP has actually been published. The default `release/project_links.json` contains no invented repository owner.
- **Character installed but no live speech:** open **Service status** and select **Retry character voice**. Check `data/logs/tts_refresh.log` if the error persists. An unrelated listener on port 9880 is not automatically killed.
- **App does not open:** see `data/logs/desktop_start.log`. The launcher may use an alternative Web port if the preferred port is occupied.
- **App does not exit:** double-click `Stop AnimeVoiceTutor.cmd` to end services owned by this installation; do not terminate unknown Python processes.

Developer diagnostics and manual source tests remain in `advanced/`. See [Testing](TESTING.md). CMD filenames with spaces are intentional; scripts use quoted paths.

## Advanced: manual development environment

Maintainers may install the Web package into an intentionally selected development Python environment with `python -m pip install -e .`, then use tools under `advanced/` to configure ASR and TTS independently. This is **not** the standard user installation flow and does not automatically install all model weights or GPU prerequisites. Do not run it inside a custom shared environment unless you understand the dependency changes.

For the isolated install workflow, `scripts/quick_setup.ps1` uses `uv pip sync` against the role-specific lock files. Paths such as `AVT_TTS_PYTHON` and `AVT_ASR_PYTHON` select previously installed compatible interpreter environments; users do not need to set them manually for the standard installer.
