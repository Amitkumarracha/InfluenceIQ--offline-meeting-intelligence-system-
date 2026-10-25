# Website fixes and validation — 25 October 2026

The updated application is served at **http://127.0.0.1:8001**. The production frontend was rebuilt and the idle project backend restarted. Existing account/history counts and the signing secret were checked before and after restart and preserved. The development frontend on port 5174 continues to use that backend.

Machine-readable evidence: [website_regression_20261025.json](../../outputs/evaluation/website_regression_20261025.json). Detailed logs, screenshots, generated input decks, speech parts, and downloads are retained under `.runtime/validation/web-regression-20261025/`. Existing user reports and historical research metrics were not overwritten.

## Reported issues and corrections

| Issue | Finding and correction |
| --- | --- |
| Login/register | Registration left the view set to registration after logout. Logout now returns to sign-in and clears credentials and meeting state. Added auth timeout/retry messaging and autofill attributes. Tested password confirmation, invalid credentials, duplicate/normalized email, connection failure, registration, logout, and sign-in. |
| Extra PPT chooser line | Replaced the styled file-label control with a keyboard-accessible button and an explicitly hidden native input. Each selected deck appears once in its ordered list; Add more PPTs remains available. |
| Multiple audio files | Asynchronous draft recovery could overwrite newly selected audio. Recovery now replaces only its previous recovered File object and preserves independently uploaded files. File additions use functional state updates. A recovered recording is cleared after successful upload even when reordered away from the first position. |
| Multiple presentations | Verified adding through the native chooser, ordered multipart submission, two-deck extraction, unique slide IDs, and source references. Existing API tests also cover rejecting a broken second deck and cleaning up an invalid upload. |
| Preparing audio / invisible progress | Decoding now supplies measured audio/part counters. ASR supplies recognition progress within a chunk. The processing panel retains stage, elapsed-time, and reconnect indicators. |
| Transcript tail only | Processing retains the complete available draft while speaker attribution runs over earlier chunks. Recording previews also retain earlier passages beyond the previous 100-passage cap. Browser checks cover 105 live-preview passages and 75 saved-draft passages, including the first passage. |
| Manual refresh to see results | A failed initial report fetch previously left polling disabled. Loading now retries; completed status without report data does not stop polling. API responses are private/no-store and the frontend entry point is revalidated. |
| Vocabulary filler | Version 3 excludes sentence-initial capitals from ordinary proper-name detection, filters more conversational/calendar words, and restricts digit/letter technical candidates to recognized measurement units. Acronyms, observed names, domain terms, and slide-grounded terms remain candidates. |
| Default speaker numbers | Website and readable transcript exports number anonymous speakers consecutively by transcript appearance while preserving stored speaker IDs and explicit names. Sparse IDs such as SPEAKER_42 and SPEAKER_03 display as Speaker 1 and Speaker 2. |
| Mostly zero influence | Saved scores matched their recorded weighted features, but single English proposal/evidence cues could fall below the default cutoff because their pattern banks were longer. Winning-role confidence now includes observed cue count, without changing the density-based role selection or prototype influence weights. New reports record scoring version 2 and contribution coverage; warnings explain missing scored contributions. The top-speaker log now follows actual rank. |
| Unexpected model/runtime | Account preferences now fall back to the configured model rather than inheriting another account's selected model. A real run and cached rerun verified that unchanged word recognition and speaker results are reused. No decoder-quality setting was reduced. |

## Verification

- **656 Python tests passed**, with seven dependency deprecation warnings, in the recorded 17.06-second full-suite run.
- Frontend lint and production build passed.
- Browser fixtures passed at 360, 390, 960, and 1440 pixels, including auth errors, reconnect, incomplete completion response, automatic full results, file reordering/removal, recording recovery, speaker edits, history, all result tabs, search, pagination, print, and exports.
- The actual backend/browser flow passed registration → two audio parts + two PPTX decks → processing/draft → complete results → speaker/vocabulary edits → six downloaded formats → history → sign-out → sign-in.
- A separate actual-backend recording check preserved two browser audio chunks and recovered them after reload. Its microphone source was Chromium's synthetic input.
- Tests check an explicit proposal/evidence/decision chain, all identified speakers including zero-feature speakers, source IDs, and exact weighted score arithmetic. Negation, export safety, ownership, action-review revisions/calendar behavior, invalid media, and cache invalidation are covered in the full suite.

The live test uses an isolated account database/runtime on port 18001. It creates test accounts and meetings; the user's main account database is not used for those operations. The generated artifacts use a public English excerpt and simple test decks. The live browser script uses keyboard activation for Analyse after the native chooser; intercepted browser tests also exercise pointer activation. Interrupted audio-element requests during navigation were observed; there were no JavaScript page errors in the passing run.

## Measured processing time and interpretation

The passing real run used an existing **90-second English AMI excerpt**, split into two 45-second WAV files, two generated one-slide PPTX decks, CPU/int8 Whisper small, and a four-speaker constraint. Models were already loaded; meeting-level inference inputs were uncached.

| Stage | Seconds |
| --- | ---: |
| Transcription | 17.360149 |
| Speaker diarization | 23.829777 |
| Word attribution | 0.067808 |
| Recorded processing total | 41.840682 |
| Unchanged cached reanalysis total | 0.602751 |

The result contained 25 transcript passages, four participants, five events, one unresolved decision candidate, and four influence records. Both decks were present. All eight result tabs opened automatically and six formats downloaded. Stage sampling can miss short stages; exact durations are in the report metadata.

The total above excludes upload, queueing, audio decode, and final persistence. It is not a repeated controlled speed benchmark, cold-start timing, or a demonstrated 3× improvement. Speaker processing accounted for about 24 seconds; comparing a speaker-enabled run against a transcript-only run can therefore be misleading. The saved 42.7-minute example also spent about 733 seconds on speakers and 545 seconds on transcription and produced 31 clusters, requiring speaker review.

## Influence diagnostic and limits

Replaying current rule analysis on two saved transcripts recovered 17 and 16 proposal events respectively, plus two evidence events in each. Zero-score counts changed from 28 to 21 among 31 groups and from 131 to 109 among 139 groups. These compare saved outputs with the current pipeline, not independently adjudicated labels or an isolated accuracy experiment. The original reports remain intact.

The correction fixes deterministic suppression of recognized cues. It does not establish that every additional event is correct or make influence a causal measure. Speaker fragmentation, implicit language, incomplete event/relation coverage, and unvalidated weights remain limits. Existing meetings require explicit reanalysis to use the new analysis rules; their historical metrics remain attached to their original versions.

No physical-microphone validation, new WER/DER/F1 benchmark, long Hindi/Hinglish meeting study, Android-device run, or public deployment was performed for this website correction.

## Software checks

```bash
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/test_browser_offline.cjs
```

`scripts/test_browser.cjs` and `scripts/test_browser_recording.cjs` now target the current interface and default to an isolated local API on port 18001. The live upload script expects the prepared `first.wav`, `second.wav`, `first.pptx`, and `second.pptx` under `.runtime/validation/web-regression-20261025/`. Provision permitted input fixtures before using it in another checkout.
