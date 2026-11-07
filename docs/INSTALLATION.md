# Installation guide

AnimeVoiceTutor is distributed as source code and Windows launch scripts. The Web app, speech recognition, speech synthesis, and character data are separate components. Install only what you intend to use.

## Requirements

- Windows x64 and PowerShell 5.1 or later for the provided `.cmd`/`.ps1` launchers.
- Internet access to download required Python packages. Online AI chat also requires a user-configured API provider and API key.
- For accelerated speech: a compatible NVIDIA GPU/driver, CUDA-compatible PyTorch, and FFmpeg/ffprobe on `PATH`. Hardware compatibility is not established by installing Python packages alone.

## Choose an installation method

| Method | Installs | When to use |
| --- | --- | --- |
| `Setup AnimeVoiceTutor.cmd` | Web Python and packages | Text-only Core |
| `Quick Setup.cmd` → `web` | Web Python and packages | Same as Web-only setup |
| `Quick Setup.cmd` → `full` | Separate Web, ASR and TTS Python environments | Local speech planned |
| Manual `venv`, uv, or Conda | Selected dependencies | Custom and development environments |

The quick installer calls `scripts/setup_source.ps1` through `scripts/quick_setup.ps1`. It synchronizes the selected `runtime/<role>` environment to the supplied lock file. Do not run it against a custom environment containing packages you want to preserve. Quick Setup can bootstrap `uv`, including managed Python versions, but does not install GPU drivers or FFmpeg.

Provided lock recipes target Web Python 3.11.18, ASR 3.12.16, TTS 3.10.22, with CUDA 12.8 PyTorch for speech. They are tested recommendations, not a guarantee of compatibility for every GPU.

Run the graphical selector by double-clicking **`Quick Setup.cmd`**, or select a role:

```powershell
& '.\Quick Setup.cmd' web
& '.\Quick Setup.cmd' full
```

To preview the plan without installing:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\quick_setup.ps1 -Mode full -DryRun
```

**The setup scripts do not download** Qwen3-ASR weights, a GPT-SoVITS engine, character ZIPs, reference recordings, or an LLM provider key.

## Manual Web installation

From the source root, with Python 3.11 available:

```powershell
py -3.11 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -e '.[test]'
& '.\.venv\Scripts\python.exe' -m pytest -q tests
```

The standard pip editable install installs Web/test requirements only. If using a nonstandard Web Python location, configure `AVT_WEB_PYTHON`. ASR and TTS need their own compatible environments; do not merge incompatible package sets.

To create locked speech environments manually, install `uv` and use the project's lock files:

```powershell
uv python install 3.12.16 3.10.22
uv venv --python 3.12.16 runtime/asr
uv pip sync --python runtime/asr/Scripts/python.exe --require-hashes --index-strategy first-index --torch-backend cu128 release/install_specs/asr_requirements.lock
uv venv --python 3.10.22 runtime/tts
uv pip sync --python runtime/tts/Scripts/python.exe --require-hashes --index-strategy first-index --torch-backend cu128 release/install_specs/tts_requirements.lock
```

Custom ASR/TTS interpreters can be referenced through `AVT_ASR_PYTHON` and `AVT_TTS_PYTHON`; or use `scripts/reuse_existing_installation.ps1` to create machine-local settings.

## Configure AI chat

Start the Web interface and configure an OpenAI or DeepSeek provider and API key in **Settings**. No API key is supplied with the repository. Web startup alone does not demonstrate a successful provider connection.

## Optional ASR

After installing an ASR Python environment, run:

```powershell
& '.\Download ASR Model.cmd'         # Qwen3-ASR-0.6B
& '.\Download ASR Model.cmd' 1.7B    # larger option
```

An existing ASR model may be referenced using `JVT_ASR_MODEL_PATH` or the local reuse script, rather than downloaded again.

## Optional GPT-SoVITS voice

1. Install or link a compatible GPT-SoVITS-v5 engine; `api_v2.py` must exist in the engine directory. Use `AVT_TTS_ROOT` or `scripts/reuse_existing_installation.ps1 -TtsRoot` if it lives outside the project.
2. Supply a compatible Python environment (`AVT_TTS_PYTHON`, or `-TtsPython` in the reuse script) with the engine's requirements.
3. In **Settings → Character**, install an authorized voice-pack ZIP containing the model weights, reference WAV, transcript and inference preset. The pack is not the engine.
4. Select the character and start AnimeVoiceTutor normally, without `-TextOnly`/`-SkipTTS`.
5. Confirm `tts_ready: true` through the status panel or `/api/status`, then test real synthesis.

The TTS service normally listens on localhost port `9880`. Another process listening there is **not** proof that the selected voice is loaded; the app validates its character-to-model binding. Stop an old, known service before starting a different character's voice, and do not terminate unidentified processes.

For existing installations, **`Use Existing Models.cmd`** can link ASR model and engine/Python paths without copying large weights. It does not automatically convert legacy private voice settings into a new character pack; install a character ZIP separately. Read [Character packs](CHARACTER_PACKS.md) for details.

## Run and verify

```powershell
& '.\Doctor AnimeVoiceTutor.cmd'
& '.\Verify Source.cmd'
& '.\Start AnimeVoiceTutor.cmd' -NoBrowser
& '.\Test AnimeVoiceTutor.cmd'
& '.\Test AnimeVoiceTutor.cmd' -Voice
```

Use `Stop AnimeVoiceTutor.cmd` to end managed services. The Web app defaults to `http://127.0.0.1:8767`; choose a different available Web port by setting `AVT_WEB_PORT`. Local ASR and TTS generally use ports `8766` and `9880`.

`Doctor` checks paths and dependencies; it does not load a neural model. `Test ... -Voice` performs an actual TTS WAV generation and ASR transcription test. See [Testing](TESTING.md).
