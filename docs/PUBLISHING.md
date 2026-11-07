# Publishing Core and update ZIPs

AnimeVoiceTutor uses **one Core source ZIP** and optional separate **character ZIPs**. A small incremental **Update ZIP** applies only to the source version named in its patch manifest; it is not a complete install.

## Before publishing

1. Update the project version consistently in `pyproject.toml`, Web status and launch checks. Review `release/install_specs/voice_baseline.json` and `release/project_links.json`; the latter must contain the **actual** public GitHub Releases URL before enabling automatic character downloads. Do not guess the repository owner.
2. In the maintained project, run `advanced/Verify Source.cmd`. Fix all failures.
3. Double-click `advanced/Build Public Source.cmd`. Its default result is `packages/updates/AnimeVoiceTutor_Core_vX.Y.Z.zip`. The builder exports only `release/public_source_files.txt` and performs tests in a fresh isolated staging directory. The private `packages/` folder is **not** bundled.
4. Test this **exact ZIP** in a new folder on Windows: install or diagnose the voice base, import an authorized test character ZIP, run ASR and generate real TTS, exit and restart using only the GUI. See [Testing](TESTING.md).
5. Commit/push the verified public source files to the intended GitHub repository. Create a release/tag on that **same commit**, and upload the matching Core ZIP. GitHub's automatic “Source code (zip)” is separate from the tested Core ZIP.
6. Publish `AnimeVoiceTutor_Update_vX.Y.Z.zip` only if you have tested it against the stated predecessor version. Include the expected previous-file hashes, backups and rollback in the patch. Keep update archives in `packages/updates/` locally.

## Simple filenames

- `AnimeVoiceTutor_Core_v0.13.1.zip`: complete public Core.
- `AnimeVoiceTutor_Update_v0.13.1.zip`: incremental change from a documented compatible predecessor.
- `AnimeVoiceTutor_Character_azusa_v1.zip`: character ZIP (if redistribution is permitted).

Keep each new release under its own version; do not repeatedly publish different contents under the same filename. For changes after publishing a version, bump the version rather than silently replacing ZIP contents.

## Keep private content private

Do **not** commit or attach entire `packages/`, `data/`, `runtime/`, `external/`, `models/`, `.venv/`, `.env`, local logs, trained weights or personal media. The local `packages/characters` folder can contain protected media and is never a public Release by default. MIT covers the app code, not third-party character assets or GPT-SoVITS upstream models; a takedown notice does not grant redistribution rights.

## Reproducibility limitations

`release/install_specs/voice_baseline.json` pins a GPT-SoVITS upstream commit, but the developer's working inference engine has separate uncommitted modifications. Until those differences are reviewed and offered as an authorized, SHA-256-pinned overlay, a clean install cannot be advertised as fully identical to the developer's voice environment. The Python lock files and upstream asset receipts are not a guarantee of identical hardware inference on every PC.

For a final check from the project root:

```powershell
python scripts\verify_public_source.py --archive ".\packages\updates\AnimeVoiceTutor_Core_v0.13.1.zip"
```

Expected: `PUBLIC_ARCHIVE_PASS`. Successful code tests are necessary but not a substitute for real Windows installation tests.
