# Main/nested project reconciliation — 19 October 2026

The active project is **`/home/amitkumar/Music/MAI Project`**. Open that directory in VS Code and run the commands from [RUN_CURRENT.md](../guides/RUN_CURRENT.md). The separate historical checkout is now retained at `waste/InfluenceIQ--offline-meeting-intelligence-system-/`. The [complete inventory and cleanup follow-up](26_LEGACY_CLEANUP_2026_10_19.md) records the reversible move and additional missing records preserved afterward.

## What was compared

The nested repository is at `701ad8e2645ba35f560021f8d26611064668f4f9` (initial commit), while the main repository is at `c3d93bb35d1af27facaa54343b384c9b2d7aeb08` plus the current readiness/account-sync work. The nested `my.txt` (preserved verbatim as [work notes](../history/NESTED_WORK_NOTES_2026_10_18.txt)) records the recent conversation and links to files in the **main** project; it is not a newer implementation stored in that checkout.

A path-aware source/configuration inventory compared **96 files**: **35 equivalent** after line-ending normalization, **44 different**, and **17 present only at their nested paths**. The latter count includes old hand-in documents, notes, Flutter/Kotlin UI files and Docker tooling; it does not mean 17 missing production features. Moved entry points/settings/dependencies were mapped using [PATH_MIGRATION.md](../development/PATH_MIGRATION.md).

The manifest `outputs/evaluation/nested_comparison_20261019.json` contains file paths, sizes, hashes, mappings and classifications. Private databases, credentials, recordings, generated outputs and vendor/build caches were excluded from the source comparison.

## Integration decisions

| Nested material | Main-project action |
| --- | --- |
| Added FastAPI, Uvicorn, multipart, bcrypt and PyJWT requirements | Already present in the active `environment/requirements.txt`; retain the main pinned/constrained environment and lockfile |
| Changes to five tracked requirement/launcher files | Reviewed; old `venv/`, root `api.py`/`.env`, CUDA/Ollama paths and removed offline flags are unsuitable for this prepared CPU/offline environment; retain current launchers and plain commands |
| Older audio, meeting, PPT and evaluation code | Retain the main implementation with ONNX diarization, resumable chunks, corrected decisions/fusion/evaluation and optional local OCR; no newer algorithm implementation was found in the nested tracked changes |
| Kotlin/Compose/Retrofit login, history and upload client | Carry its useful shared-account requirement through the main native Account & sync implementation. Preserve local Whisper/JNI, recording, playback, checkpoints and direct SDK build; do not switch to server-only processing |
| Flutter client, Gradle distribution/cache and tunnel/Docker tooling | Retain as references in the nested checkout; they are not dependencies of the active native/local app |
| `my.txt` and older submitted reports/notes | The conversation note was copied verbatim to `docs/history/NESTED_WORK_NOTES_2026_10_18.txt` for provenance; older reports remain intact and current research reports are not overwritten |
| Separate legacy database/history | Imported the separate account and four meetings after explicit user authorization, using additive inserts and private pre-import backups. Password hashes and ownership are retained; no credential file, signing key or existing database is replaced |

The main `.gitignore` now excludes this independent reference checkout, and pytest configuration excludes it from recursion. This prevents accidental vendoring or running its older test suite as part of the active project. The nested repository's own files and Git status were preserved.

## Current delivery

The earlier readiness changes are already in the main project; the interrupted account feature is completed there and described in [shared-account validation](24_ACCOUNT_SYNC_2026_10_18.md). The [account guide](../guides/ACCOUNT_SYNC.md) explains how website and Android point to the same backend, including USB forwarding on this laptop.

Current verification is recorded in `logs/account_sync_*`, `outputs/account-sync-ui/` and `outputs/evaluation/account_sync_delivery_20261019.json`. These distinguish code/build/emulator results from physical-phone and language-accuracy requirements. No new speech model, fine-tuning or cloud deployment was performed for this reconciliation.

Before import, the main database had 9 accounts/13 meetings and the nested database had 1 separate account/4 meetings. After the user's explicit authorization, `scripts/import_legacy_history.py` imported that history: the main database now has **10 accounts/17 meetings**. All original main rows remain unchanged, the source database is unchanged, and all four recordings were verified byte-for-byte. The existing bcrypt password hash is retained; sign in afresh using the legacy account's email/password. Old reset tokens, server secrets and signing keys were not copied. The human password was not known or tested.

Private SQLite snapshots and a manifest are retained at `.runtime/legacy-imports/245c02f4638845fd81419518e8e8b8e5/`. Keep this backup private. The importer defaults to dry-run, rejects conflicting account/meeting/audio identifiers, rolls back new files on database failure, and was rerun successfully with zero additions. Five regression tests cover these protections.

Two imported meetings retain their historical **failed** status and saved recordings; use the website's Retry action to run analysis. Two completed historical reports have no saved full transcript in either checkout or backup. They retain their estimates and carry `processing.legacy_transcript_missing`, an explicit warning and an empty transcript list. Android displays **Historical report**, distinct from a no-speech result. Download a completed report to Android and run Update analysis to recover a transcript from its recording; publication is a separate explicit action. No transcript or success was fabricated and no legacy ML job was automatically started during import.

Authenticated API verification recovered all four owned history entries, downloaded all four protected recordings and rendered all six exports for each of the two completed reports (12 exports). See `outputs/evaluation/legacy_import_api_20261019.json`. Import results are in `logs/legacy_import_result.json`; the earlier read-only inventory in `outputs/evaluation/nested_state_inventory_20261019.json` intentionally records the counts before import.

Physical 6 GB Samsung acceptance testing, independently checked natural Hindi/Hinglish data and release qualification remain outstanding. Account synchronization does not change the previously measured recognition error rates or validate influence scores.
