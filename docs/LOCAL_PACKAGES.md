# Local update and character ZIPs

AnimeVoiceTutor keeps a **private local archive** in the project folder. The first-run launcher creates it automatically. It does not contain the running Python environment or installed model directories.

```text
AnimeVoiceTutor/
  packages/
    updates/
      AnimeVoiceTutor_Core_v0.13.1.zip
      AnimeVoiceTutor_Update_v0.13.1.zip
    characters/
      AnimeVoiceTutor_Character_azusa_v1.zip
```

## Naming

- **Core:** `AnimeVoiceTutor_Core_vX.Y.Z.zip` — complete public Core source package.
- **Update:** `AnimeVoiceTutor_Update_vX.Y.Z.zip` — incremental patch for a compatible earlier version. Apply only to the exact baseline required by that patch; it is not a standalone installer.
- **Character:** `AnimeVoiceTutor_Character_<id>_vN.zip` (or `vN.N.N`). The ID comes from `character.json`, not from an arbitrary downloaded ZIP filename.

New character packs may define `"pack_version": "1"` in `character.json`. Existing packs without this field are archived as `v1` **only as a local packaging label**, not as a claim about the trained model revision. An archive with the same identity/version but different content is not overwritten; use a new pack version for legitimate updates.

## What is saved automatically?

1. A successful character import through **First Run** or the **Web UI** keeps its original ZIP in `packages/characters`, using the standard name. Its extracted, usable files remain in `data/character_packs`.
2. Downloading and importing a published character stores a local character ZIP. Failed or partial downloads are not considered installed packs.
3. `advanced/Build Public Source.cmd` creates the current complete Core ZIP under `packages/updates` by default.
4. The official incremental patch application script may place a copy of its patch ZIP in `packages/updates` when applied, so you can refer to previous updates.

Do not extract update ZIPs into this folder or run `First Run Setup.cmd` from a patch's `payload` directory. A ZIP copy is a backup/download artifact, not an installed environment. Old, unused ZIPs may be deleted manually to free space; this does not uninstall already imported characters.

## Privacy and release safety

The **entire `packages/` directory is ignored by Git and excluded from the Core export allowlist**. Never copy it wholesale into a GitHub Release or a public commit. Publish an individual character pack only after confirming distribution rights for every image, recording, voice weight and other included asset. A takedown notice is not permission.
