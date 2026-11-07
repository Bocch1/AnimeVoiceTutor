# Security and privacy

AnimeVoiceTutor is intended for local use. Web, ASR, and TTS services should bind to `127.0.0.1`; do not expose them directly to the public Internet without an independent security review.

- Keep `.env`, `.avt-local.ps1`, provider API keys, private JSON configuration, recordings, user conversations, logs, downloaded models and virtual environments out of public commits and source archives.
- Provider credentials are configured by the user; the Windows application uses DPAPI for stored provider credentials where supported.
- Install character ZIPs and model weights only from trusted, authorized sources. Model-weight deserialization can be unsafe even when an archive's file paths and extensions have been validated.
- The release builder audits allowlisted source files, but contributors must still review their commits and any distribution assets.
- CI source tests use synthetic fixtures and do not require GitHub Actions secrets or private model files.

For a security issue, use the repository's private vulnerability reporting or contact the maintainer privately. Do not post API keys, private user text, raw model recordings, or sensitive logs in public issues.
