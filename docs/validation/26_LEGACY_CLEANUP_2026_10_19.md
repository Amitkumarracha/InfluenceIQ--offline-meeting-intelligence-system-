# Complete legacy-folder inventory and cleanup — 19 October 2026

The active project is **`/home/amitkumar/Music/MAI Project`**. The inactive checkout was moved from `InfluenceIQ--offline-meeting-intelligence-system-/` to **`waste/InfluenceIQ--offline-meeting-intelligence-system-/`** after its useful missing records were preserved. This is a reversible move. No files were deleted and no disk space was reclaimed.

## Full inventory

The earlier [source reconciliation](25_NESTED_PROJECT_RECONCILIATION_2026_10_19.md) compared 96 selected source/configuration files. This follow-up inspected **every regular file and symbolic link**, including hidden files, untracked Android source, dependency caches, databases and `laptop_backup/`. All 21,554 entries were checked before and after the move: regular files by SHA-256 and size, symbolic links by their stored target. Approximately 2.25 GB of regular-file content was preserved.

| Category | Entries | Decision |
| --- | ---: | --- |
| Source, documents and assets | 116 | Compare mapped main paths and existing document hashes; preserve missing useful documents; retain superseded clients/launchers in the retired checkout |
| Dependencies and generated/build caches | 17,998 | Retire with the old checkout; the active environment and native build dependencies remain in their existing main-project directories |
| Historical data/results | 3,218 | 3,177 already match their mapped main files byte-for-byte; preserve the other 41 variants in a private recovery archive |
| Private configuration, databases and diagnostics | 7 | Preserve separately in the private recovery archive; never load them over the active database or expose their contents |
| Git metadata | 37 | Preserve the independent repository intact |
| Symbolic links | 178 | Preserve the exact link targets without following them into other folders |
| **Total** | **21,554** | **No deletions** |

The complete per-entry paths, sizes, hashes, comparisons and dispositions are in `outputs/evaluation/legacy_cleanup_inventory_20261019.json`. Source-to-destination preservation mappings and final checks are in `outputs/evaluation/legacy_cleanup_result_20261019.json`. These files are local validation artifacts excluded from Git.

## Missing material preserved in the main project

Three historical documents are now in [docs/history/legacy_reference_20261019](../history/legacy_reference_20261019/README.md):

- `Group12_Multimodal_AI_Report_2_README_submitted.md`
- `Offline_Multimodal_Meeting_Intelligence_Report_1_README_submitte.md`
- `myfile.txt`

They were copied verbatim, with their origin explained in a new README. They describe earlier work and contain outdated claims; they are not current implementation instructions or proof of recognition accuracy or research novelty. `my.txt` was already preserved as [the earlier work note](../history/NESTED_WORK_NOTES_2026_10_18.txt). Both historical submission PDFs already match the main `docs/submitted/` copies byte-for-byte, so no duplicate PDFs were added.

The private **`archive/legacy_recovery_20261019/`** contains the 41 absent/different historical data/result variants and seven state/diagnostic files. These include old processed audio, VAD output, resume-state files, report exports, two additional backup databases, the original legacy database/configuration and diagnostic logs. File paths are retained, all copies were hash-verified, the archive root has mode 0700 and files 0600. Existing main results, inputs and checkpoints were not overwritten. These artifacts are retained as history, not reclassified as new validated results or automatically resumed jobs.

The older Kotlin network client uses a fixed tunnel endpoint and request-body logging; its account/history/upload behavior is already covered by the main native shared-account implementation. The Flutter scaffold references missing screen files and old route shapes. Neither client adds a working offline audio engine. Their source, old Docker/tunnel tooling, unused assets, empty notebook note and workstation-specific settings remain in the retired checkout; they are not dependencies of the active Java/JNI application.

## What remains active

The canonical backend, website, native Android app, model weights, Python environment, recordings, SQLite account state, APK and original recovery backups stay in their existing main-project locations. No running process referenced the retired checkout when it was moved. The active account database SHA-256 was unchanged by this cleanup; it still contains the previously authorized **10 accounts and 17 meetings**. Four imported recordings and the private pre-import SQLite backups remain available.

`waste/` is ignored by Git and excluded from pytest recursion. Its private README explains the move and restoration. This folder is inactive recovery material, not a launcher directory. It can contain private original state; do not publish it. To restore the old checkout if needed, first ensure the original root path does not exist, then move the entire child directory back. Do not merge it over active application files.

## Verification and remaining stages

After the move, the local setup validator passed with offline model lookup. The Python regression suite passed **531 tests**, with seven dependency warnings; see `logs/legacy_cleanup_setup.log` and `logs/legacy_cleanup_python_tests.log`. Documentation links, Git exclusions and source whitespace were checked. Application code was unchanged during this cleanup, so the previously verified **0.7.0-prototype** APK and frontend build remain the delivered artifacts; see [account-sync validation](24_ACCOUNT_SYNC_2026_10_18.md).

The implemented local processing, shared-account transfer, history import, preservation and cleanup stages are complete. Physical Samsung acceptance, long-meeting/large-transfer checks, independently transcribed natural Hindi/Hinglish recordings and production release qualification remain outstanding. Two historically failed analyses and two historical reports missing full transcripts retain their recordings for user-initiated reanalysis. Organizing files does not resolve those accuracy and acceptance requirements.

Use [RUN_CURRENT.md](../guides/RUN_CURRENT.md) for separate backend, website and Android commands, and [ACCOUNT_SYNC.md](../guides/ACCOUNT_SYNC.md) for the same user account across both clients. No new model download, package installation, fine-tuning or cloud processing was required for this cleanup.
