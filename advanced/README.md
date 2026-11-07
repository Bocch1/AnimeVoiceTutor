# Advanced commands

These Windows command launchers are optional developer and troubleshooting tools. Ordinary users should start with `../First Run Setup.cmd` and use `../Start AnimeVoiceTutor.cmd` / `../Stop AnimeVoiceTutor.cmd`.

- `Quick Setup.cmd` and `Setup AnimeVoiceTutor.cmd`: manual or legacy environment installation.
- `Download ASR Model.cmd`: manually fetch an ASR model.
- `Use Existing Models.cmd`: link a compatible existing local installation.
- `Doctor AnimeVoiceTutor.cmd`: check paths and prerequisites.
- `Test AnimeVoiceTutor.cmd`: run a live service smoke test after starting.
- `Verify Source.cmd`: run automated source regression tests.
- `Build Public Source.cmd`: export a full public-source ZIP to `packages/updates/` (private local archive).

Run these scripts from this directory by double-clicking, or from a PowerShell prompt in the project root using `& '.\advanced\<file>.cmd'`. The wrappers always change into the Core project root before invoking their scripts.
