# Testing a Core source release

A source ZIP should be validated in a new directory, not inside an existing working installation. This avoids accidentally passing tests because of locally installed models, cached dependencies, or untracked files.

## 1. Extract a public ZIP

In PowerShell, provide the downloaded ZIP path when prompted:

```powershell
$zip=(Read-Host 'Full path to Core ZIP').Trim('"'); if(!(Test-Path -LiteralPath $zip -PathType Leaf)){throw 'Core ZIP not found'}; $testRoot=Join-Path $env:TEMP ('AnimeVoiceTutor_ReleaseTest_'+[guid]::NewGuid().ToString('N')); Expand-Archive -LiteralPath $zip -DestinationPath $testRoot; Set-Location $testRoot
```

Do not extract over the maintained source checkout. Only the public source ZIP should be published; a running test directory may contain private settings, models, runtime packages, and generated recordings.

## 2. Install Web and run regression tests

```powershell
& '.\Setup AnimeVoiceTutor.cmd'
& '.\Verify Source.cmd'
```

`Setup` may download Python and packages but should not install character voices. `Verify Source` runs the public structural check and the included synthetic regression suite. It cannot establish GPU inference health.

## 3. Start Web without speech

```powershell
$env:AVT_WEB_PORT='8777'
& '.\Start AnimeVoiceTutor.cmd' -TextOnly -NoBrowser
& '.\Test AnimeVoiceTutor.cmd'
```

Open `http://127.0.0.1:8777`. Confirm the default welcome screen is character-neutral. The Web UI should load without model files or an API key. To test AI chat, configure a provider separately; a Web smoke test does not call the provider.

If using an already installed ASR/TTS service on the machine, choose a separate Web port but remember that shared voice ports are **not** isolated. Do not stop services belonging to unrelated applications.

## 4. Optional live character and speech test

For an installation with legitimate local speech assets:

1. Install or link compatible ASR/TTS Python environments and the ASR model. `Use Existing Models.cmd` can reference an existing installation; an explicit `-TtsRoot` may be needed when GPT-SoVITS is not in the default location.
2. Install an authorized character ZIP using **Settings → Character → Install ZIP** and select the character.
3. Ensure the GPT-SoVITS engine contains `api_v2.py` and is not already running an unrelated model on port `9880`.
4. Stop the test instance and restart **without** `-TextOnly` / `-SkipTTS`. Avoid reusing a stale Web process after changing model paths.
5. Verify `/api/status` reports `tts_engine_available: true` and `tts_ready: true`, then run:

```powershell
& '.\Test AnimeVoiceTutor.cmd' -Voice
```

Expected checks include a responding WebUI, an audible local WAV, and nonempty ASR transcription. The WAV is written to `data/smoke_tests/` and is **not** a release asset. Listen to it to assess qualitative voice output; the smoke test does not measure character-voice similarity, emotion, or online AI conversation quality.

If the TTS service is unavailable, run `Doctor AnimeVoiceTutor.cmd`, inspect `data/logs/tts_stdout.log` and `tts_stderr.log`, and verify that the current role's configured engine and weights are actually loaded. A port-listening message alone does not prove this.

## 5. Audit the archive, not the installed directory

From the extracted source directory:

```powershell
& '.\runtime\web\Scripts\python.exe' '.\scripts\verify_public_source.py' --archive $zip
```

The archive should report `PUBLIC_ARCHIVE_PASS`. It must not include `.env`, `.avt-local.ps1`, populated private config, `data/`, `runtime/`, character weights, reference recordings, downloaded engines, or user conversations.

The public source archive contains only files allowed by `release/public_source_files.txt`. The maintained development checkout can legitimately have additional local files. Compare **published files**, not the entire directory tree.

## 6. Stop the test copy

```powershell
& '.\Stop AnimeVoiceTutor.cmd'
```

Check that the service instance you stop belongs to the test copy. Do not force-terminate unrecognized processes.
