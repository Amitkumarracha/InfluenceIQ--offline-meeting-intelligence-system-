# Shared web/Android accounts — 18–19 October 2026

This follows the [0.6.1 readiness work](23_READINESS_2026_10_18.md). Android **0.7.0-prototype**, version code **8**, uses the website's existing account database when connected to the same backend. This is shared account identity with explicit meeting transfers; local recording and analysis remain independent of sign-in.

**Follow-up delivery:** [0.7.1 / version code 9](27_READ_AI_COMPARISON_AND_FOLLOWUPS_2026_10_19.md) adds source-bound human task reviews and local calendar exports. This document's 0.7.0 APK hash is the earlier snapshot; use the newer delivery manifest for the current APK.

## Implemented

- `backend/api.py` returns a stable `user_id` on login/registration and exposes authenticated `/api/auth/me`. Existing accounts/password hashes are retained. No second authentication database or cloud identity service was added.
- Android Account & sync supports registration, sign-in, profile refresh/save, account history, sign-out, publication of completed device meetings and downloads for offline review/playback/export.
- Access tokens are encrypted with AES-GCM using Android Keystore; the app does not persist passwords. Android's optional password-manager UI is controlled separately by the user. Logout clears the account session/history cache and retains device files.
- HTTPS is required except exact local-development hosts. Redirects, URL credentials and non-origin URLs are rejected. USB `adb reverse` permits phone-to-laptop testing with the backend still bound to loopback.
- A confirmed Publish action transfers the completed report, participant labels, extracted slide text and canonical recording. It does not run server inference. Login/profile refresh never uploads recordings. Downloads normalize website audio to native WAV format and translate report schema aliases.
- User-scoped sync keys prevent duplicate records on retries/concurrent publication. Content revisions reject stale updates after website edits. Existing audio is compared by PCM content, allowing different RIFF metadata headers while rejecting different recordings. A newer account revision becomes a separate offline snapshot instead of overwriting local corrections.
- Uploads/downloads use bounded streaming buffers. Publication's database/audio checks run in a worker thread with cleanup retained if the request disconnects. The API event loop does not hash an entire long recording synchronously.
- `meeting_sync_links` is an additive table; existing user/meeting tables are not replaced. Speaker/ASR model defaults, raw checkpoints and local analysis behavior are retained.

Main sources: `AccountClient.java`, `AccountSession.java`, `AccountSync.java`, `AccountView.java`, `PortableReport.java`, `SyncAddress.java`, `MainActivity.java`, the manifest/network-security resource, `backend/api.py`, `src/report/portable.py` and `frontend/src/App.jsx`.

## Verification evidence

Regression and runtime logs are under `logs/account_sync_*`. Native screen captures and integration results are under `outputs/account-sync-ui/`. The final delivery manifest records exact checks and APK hash at `outputs/evaluation/account_sync_delivery_20261019.json`.

The Python account tests exercise shared web/app identity, profile/history, report translation and all six website exports, ownership of private audio, expired tokens, duplicate and concurrent retry handling, stale revision conflicts, malformed/oversized uploads and WAV metadata differences. JVM checks cover the server-origin policy. The real Android JSON/runtime probe covers website-to-native schema conversion and preserved source data alongside the existing analysis/export contracts.

The live account test uses an isolated validation database/runtime on port 8766 and clearly labelled fixtures. It does not register validation accounts or insert meetings in the real user database. The Android target is the Pixel_6 x86_64 emulator, API 37 with 16 KB pages; ARM64 is built, not physically verified. See the delivery manifest for final pass/fail results rather than interpreting interrupted automation attempts as successful runs.

### Final measured checks

| Check | Result / evidence |
| --- | --- |
| Python regression suite | **531 passed**, 7 dependency warnings; `logs/account_sync_python_tests.log` |
| Frontend lint, production build and intercepted browser checks | Passed; 360/390/960 px, no browser errors; `logs/account_sync_frontend_*` and `logs/account_sync_browser.log` |
| Real backend and production/development browser | Passed shared user ID, Android-updated profile, all eight report tabs and Vite proxy origin; `outputs/account-sync-ui/browser-result.json` and `dev-browser-result.json` |
| Native account UI on API 37 / 16 KB emulator | Passed existing-account login, Keystore session restoration, bidirectional profile updates, publish/download, shared registration, account switching and sign-out preserving local files; `outputs/account-sync-ui/result.json` |
| Native runtime, JVM and final review screens | Passed portable reports, historical-report warning, analysis/export contracts, server policy and UI smoke; `logs/account_sync_android_runtime.log`, `logs/account_sync_android_jvm.log`, `logs/legacy_android_ui.log`, `logs/account_sync_android_review_ui.log` |
| APK | Built/signed, ARM64 + x86_64, version 0.7.0-prototype / code 8, signature verified and 16 KB zip alignment verified |
| Authorized historical import | 1 account, 4 meetings and 4 exact recording copies; original rows/source preserved. Five importer tests passed. Four authenticated audio downloads and 12 report exports passed |

The Android account UI flow completed across resumed automation runs: the earlier attempt stopped at an uppercase confirmation button and then the operating system's password-manager prompt. These were automation obstacles, not passing runs; the final combined state is recorded by `logs/account_sync_android_ui_finish.log`. The newly built APK also passed the historical-report warning and review-screen smoke checks. The development APK SHA-256 is `a8585c9194768b52fbe044680df8a459744e21b524661848afaa0a6687941c1d`.

## Boundaries

This is not automatic background mirroring, browser-to-app single sign-on, collaborative conflict merging or an encrypted per-account device vault. Device files remain visible in the local library after logout. A linked copy cannot be published under another server/account. A server connection is needed for account operations; cloud inference is not required.

Original PPTX binaries, model weights, ASR checkpoints and device analysis preferences are not synchronized. Extracted slide content and matching results do transfer. Reports must be completed; original website upload/analysis remains available for unprocessed audio. Physical Samsung network/lifecycle/large-transfer testing and production signing remain pending. Hindi/Hinglish accuracy and scientific influence validation are unchanged by account sync.

Use the [account setup guide](../guides/ACCOUNT_SYNC.md) and [current terminal commands](../guides/RUN_CURRENT.md). The [nested-checkout reconciliation](25_NESTED_PROJECT_RECONCILIATION_2026_10_19.md) explains why the older Kotlin/network-only client was not copied over the native offline app.
