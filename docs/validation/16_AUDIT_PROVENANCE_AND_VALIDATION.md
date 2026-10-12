# Audit provenance, validation, and limits

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Snapshot identity

Audit date: **7 October 2026**, user timezone **Asia/Kolkata**.

Current root: `/home/amitkumar/Music/MAI Project`.

Compared older snapshot: `/home/amitkumar/Music/MAI Project/mai folder older`.

Git HEAD at inspection: `3e90a24317c294f1ae40700658651cc8cb0e9026`. The working tree already contains modified/untracked Android 0.4.0 files, changed project-status documentation, and the untracked old folder. HEAD alone does not identify the complete current implementation. The [source manifest](14_FILE_BY_FILE_COMPARISON.md) captures actual file bytes, including working-tree changes.

No applicable AGENTS.md file was found in the project or ancestor paths during inspection. The Ponytail skill was used to keep the review and deliverable focused; explanatory documentation is explicitly requested here. No agents were delegated, source algorithm was changed, commit was made, or app was deployed.

## Evidence examined

| Evidence class | Inspected material | What it supports |
| --- | --- | --- |
| Source/config | Current and older source modules, APIs, defaults, setup/launchers, manifests, AST definitions and hashes | Implemented methods and structural differences |
| Environment | venv metadata, installed package metadata, uv compatibility check, local model snapshots, CPU/RAM/Node/FFmpeg inspection | Current local installation profile |
| History | Four local commits, old workstation execution log/guides, current status/efficiency/design records | Documented migration chronology and recorded changes |
| Outputs | All shared report/evaluation file bytes, report schema counts, all saved benchmark metric JSONs | Preserved outputs, preliminary WER/resource observations |
| Validation logs | Python efficiency suite log, Android final JVM/signature/export records, linked browser/integration evidence | Prior software/device-fixture checks, with explicit scope |
| Dataset artifacts | Directory counts, staged-data script, AMI annotation locations and local annotation templates | Available data versus missing custom human labels |
| Primary literature | ACL Anthology, original research/corpus pages, upstream model/runtime documentation | Preliminary related-work context; not exhaustive novelty |

Private account records, credential values, and user transcript text are not reproduced. Model loading was not needed for diagnostics. The whole AMI corpus was inventoried, not decoded or re-evaluated.

## Checks run for this documentation task

1. Compared raw bytes/SHA-256 for all 147 scoped first-party source/config/documentation files: 49 identical, 32 modified, 66 current-only, zero older-only. Confirmed old orchestrator/cache/setup-validator empty placeholders.
2. Compared 561 shared report-directory artifacts and two shared evaluation JSON artifacts: all byte-identical. Counted added report files and full report schema differences without copying transcript content.
3. Parsed current Python source to produce the source symbol index and line references.
4. Ran four no-model assertions confirming required-final proposal fallback, duplicate A4/A5 flags, event-speaker omission, and permissive decision-time matching. See [11](../research/11_EVALUATION_BASELINES_AND_ABLATIONS.md).
5. Ran `.venv/bin/python scripts/validate_setup.py`: **passed**, Python 3.11.17, FFmpeg/ffprobe present, ASR/slides ready, diarization not ready, frontend build and Android APK present.
6. Ran `.bootstrap/bin/uv pip check --python .venv/bin/python`: **125 packages checked; all installed packages compatible**. The venv has no `pip` module, so handbook commands use uv.
7. Checked this handbook's relative links, Markdown fence pairing, complete source-manifest membership/checksums, source preservation, and exact recorded WER/RTF/RSS values.

No speech benchmark, training job, model download, package installation, frontend build, Android build, emulator session, or server was started for this documentation audit. Tests/reporting performed in earlier work are explicitly called **recorded** results throughout the handbook.

## Current binary identifiers

| Local artifact | SHA-256 observed |
| --- | --- |
| `models/ggml-base.bin` | `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe` |
| `android/build/meet-iq-debug.apk` | `14b3b15ad988c8722791a0125386a38f75c68821b0188a7f473c244b4a7c447f` |

The current APK digest differs from the earlier 0.3.1 APK recorded in `efficiency-results.json`; that is expected after the later 0.4.0 UI changes. The current manifest and design record are the sources for its version. The APK is development-signed.

Laptop model snapshot revisions are in [03](../development/03_ENVIRONMENT_AND_SETUP.md). A release/experiment supplement should also hash exact model binaries and record inference package versions; model folder names alone are insufficient.

## What was created or changed

Created `research_developer_docs/` containing the index and numbered Markdown chapters 01–16. Added one navigation paragraph to the root `README.md`. The manifest's root README hash includes that paragraph. Existing executable source, datasets, recordings, databases, weights, and the older snapshot were preserved.

The handbook has documentation-time counts; they will change as new artifacts are created. Its source references are line numbers from the current snapshot, not permanent future anchors.

## What cannot be concluded

Exact fidelity to the live GPU workstation cannot be certified: no remote filesystem, installed environment, current GPU/CUDA inspection, full old data/model manifest, or paired GPU results were available. Historical GPU runtime estimates are not measurements.

No current-old full-task accuracy improvement is established by preserved reports. Existing English WER runs do not validate bilingual decisions or influence. Current algorithm options and documentation flags can be reserved, stubbed, or imperfect; chapters 06–11 distinguish executable behavior from names/comments.

No statistical contribution/causality, complete prior-art novelty, whole-meeting offline performance envelope, or physical-phone qualification is established. These are specific missing evidence categories for the requested journal preparation, not reasons to stop implementation work.

## Keeping the handbook useful

After code changes, refresh the file manifest/symbol lines and record new experiments with effective settings, hashes, independent labels, cache policy, hardware, timing units, and failure history. Update current/recorded/proposed labels together. Keep the old snapshot read-only as a comparison reference unless intentionally replacing it with another dated, identified baseline.
