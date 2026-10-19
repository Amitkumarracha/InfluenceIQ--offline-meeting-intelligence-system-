# Same account on Android and the website

Android **0.7.1-prototype** can use the website's existing accounts. There is one backend user database: registration from either client creates an account usable by both. The same email/password on different independent servers does **not** identify the same account. Use the same server installation, not a second backend/database. Browser and Android sessions are separate; this is shared identity, not automatic browser-to-app sign-in.

Recording, local inference, playback, the device library and exports still work without signing in or connecting. **No cloud inference is required.** Account operations need a connection to your configured server, which can run on this laptop.

## Run with the laptop and USB-connected Samsung

Start the backend/frontend using [RUN_CURRENT.md](RUN_CURRENT.md). The backend can remain bound to `127.0.0.1`. In a separate terminal:

```sh
cd "/home/amitkumar/Music/MAI Project"
export PATH="/home/amitkumar/Android/Sdk/platform-tools:$PATH"
adb devices
adb -s PHONE_SERIAL install -r --no-incremental android/build/meet-iq-debug.apk
adb -s PHONE_SERIAL reverse tcp:8001 tcp:8001
adb -s PHONE_SERIAL shell am start -n org.meetiq.offline/.MainActivity
```

Replace `PHONE_SERIAL` with your actual phone serial. In Android, open **Account & sync**, enter `http://127.0.0.1:8001`, then use your website email/password. Create a shared account there only if you do not already have one. USB forwarding must be established again after reconnecting/rebooting. For the emulator, use its serial and the same forwarding command, or `http://10.0.2.2:8001`.

For separate computers or normal mobile connectivity, configure an HTTPS server and enter its origin, for example `https://meetings.example.org`. The website Settings page shows the API server origin to use. The API must be served under `/api` at that origin. A development Vite address such as port 5173 is not the Android API address. Public HTTP/LAN HTTP, URL credentials, query strings, fragments and subpaths are rejected; do not disable certificate verification. No public deployment was performed in this delivery.

## What synchronizes

| Data | Behavior |
| --- | --- |
| Identity | Same backend user ID/email, existing password validation and 24-hour access tokens |
| Profile | Account name, role and organization are fetched on sign-in/Refresh account; Save account profile updates the website profile. The website has Refresh account profile |
| Account history | Android fetches that user's server meetings on sign-in/Refresh account; website history refreshes periodically and on opening History |
| Device meeting → account | Open a completed local meeting → Meeting options → Publish to account → confirm. Sends report, transcript, labels, extracted slide text and recording, without rerunning server inference |
| Account meeting → device | Tap a completed account meeting to save an offline copy, including its recording. It opens in the normal native review/player/export screens |
| Reviewed follow-ups | Confirmed owner, exact due date, open/done/dismissed state and source-bound review metadata transfer with the report. See [follow-ups](FOLLOW_UPS.md) |
| Later edits | Publish again to update the linked account copy. A stale revision is rejected if the website has changed; download the latest version and review before editing/publishing it |

Only explicitly selected meetings are published. Sign-in/profile refresh never uploads device recordings. Repeating a successful publication, including a retry after a lost response, does not create another meeting. Updates use the original audio; changing the recording requires a separate meeting. Downloads of a newer server revision create a separate local snapshot, preserving all existing local edits. Downloading a revision already present reopens that device copy.

Reports are translated between native and website schemas at transfer boundaries. The raw ASR checkpoint and model defaults are unchanged. Candidate decisions and influence remain estimates, with their original method metadata; transfer does not improve or validate accuracy. Normalizing website audio into the native canonical WAV format occurs during download.

## Imported historical meetings

The authorized legacy account and four meetings are now in the main server database; use the original account email/password on both clients. Two historical analyses had failed and can be retried from website history. Two completed reports lack saved full transcripts; their recordings and existing estimates are retained with an explicit historical-report warning. Download one to Android and use Update analysis to produce a new transcript, reviewing the result before publishing. Import did not silently rerun models or invent missing content. The [reconciliation record](../validation/25_NESTED_PROJECT_RECONCILIATION_2026_10_19.md) lists the private backup and verification evidence.

## Privacy and boundaries

The APK now includes **INTERNET permission** for this explicitly requested account feature, superseding the older 0.6.1 no-network packaging. MeetingService/JNI inference does not use an account or network client. Network operations happen only through Account & sync or a confirmed Publish action; there is no background scheduler, analytics, telemetry SDK or automatic recording upload.

The app does not persist passwords. Android may offer your chosen password manager; saving there is a separate user choice. Access tokens are encrypted with AES-GCM using Android Keystore, app backup remains disabled, and logout clears the account session/cache. Requests require HTTPS apart from exact local-development hosts; redirects are refused so credentials are not forwarded elsewhere. See Android's official [Keystore](https://developer.android.com/privacy-and-security/keystore) and [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config) documentation.

The offline library is **device-scoped**, not an encrypted per-account vault. Signing out does not delete device recordings or downloaded snapshots; people sharing an unlocked phone can still access its local library. A linked device copy cannot be published under a different account/server. Server requests enforce ownership independently of the UI, including audio download.

This is explicit synchronization, not automatic background mirroring or collaborative conflict merging. Original PPTX binaries, model files, ASR checkpoints and device analysis preferences are not transferred. Extracted slide text/matches do transfer. Transfers should be kept in the foreground; interrupted publication can be retried safely. Android downloads are limited to 700 MiB; report requests/responses to 20 MiB; server uploads follow `MAI_MAX_UPLOAD_BYTES` (default 1 GiB). The endpoint accepts completed reports, not raw/unanalysed recordings. Existing website audio analysis/upload remains available separately.

Current phone/device and accuracy acceptance limits remain in the [readiness record](../validation/23_READINESS_2026_10_18.md). See the [account sync validation record](../validation/24_ACCOUNT_SYNC_2026_10_18.md) for this change's checks.
