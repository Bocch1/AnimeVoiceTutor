# Testing AnimeVoiceTutor

## Acceptance test: operate it like a real user

1. In **Windows File Explorer**, open the extracted full Core folder. Double-click **First Run Setup.cmd**. Select English, 简体中文 or 日本語 under the always-English **Language** label.
2. In **Step 1**, click **Diagnostics**. If the base check fails, click **Install voice base**, resolve any stated driver/network errors, then run Diagnostics again. Confirm its result is accurate; it is not a live character inference test.
3. In **Step 2**, import an authorized character ZIP or download one that is actually published on GitHub Releases. The selected ZIP is archived under `packages/characters/` and installed under `data/character_packs/`.
4. Double-click **Start AnimeVoiceTutor.cmd**. Check the app opens without leaving a persistent console. Click Start a second time to confirm the same instance is reused.
5. In the app, record a short Japanese sentence and verify the ASR transcription. Send a message (requires a configured AI provider) and hear **newly synthesized speech**. A cached/prerecorded welcome WAV is not proof of TTS success.
6. Switch or install another permitted character and confirm the status panel reports real model loading, rather than only showing an installed pack. Use **Retry character voice** if needed.
7. Use the sidebar **Exit application**. Launch once more to check there is no stale Web/TTS service. `Stop AnimeVoiceTutor.cmd` is a fallback.

## Developer tests (optional)

In a PowerShell prompt **from the project root**:

```powershell
& '.\advanced\Verify Source.cmd'
& '.\advanced\Doctor AnimeVoiceTutor.cmd'
& '.\advanced\Test AnimeVoiceTutor.cmd' -Voice
```

`Verify Source` tests project code and structure. `Doctor` checks installed prerequisites and configured paths. `Test -Voice` performs live synthesis/ASR checks **after the application has started**. None of these tests alone establishes that every PC or GPU can run the app, or that a character voice matches subjective quality targets.

## Testing a public ZIP

Use a **fresh extraction folder**, separate from the developer's local models. Test the exact Core ZIP whose filename and Git tag will be published. The ZIP must not contain `data/`, `.env`, `external/`, `runtime/`, `models/`, or `packages/`.

For a strict ZIP structure check from a Python-enabled project shell:

```powershell
python scripts\verify_public_source.py --archive "C:\path\to\AnimeVoiceTutor_Core_v0.13.1.zip"
```

This should print `PUBLIC_ARCHIVE_PASS`. Tests on the build machine cannot substitute for an actual Windows first-run install. Private character packs and third-party models are not part of the public Core distribution.

## Diagnostic logs

| File | Purpose |
| --- | --- |
| `data/logs/desktop_start.log` | Click-start failures |
| `data/logs/first_run/` | Installation and environment checks |
| `data/logs/tts_refresh.log` | Character model reload attempts |
| `data/logs/tts_model_*_stderr.log` | GPT-SoVITS errors |

Do not share logs containing API keys or personal file paths without redacting them.
