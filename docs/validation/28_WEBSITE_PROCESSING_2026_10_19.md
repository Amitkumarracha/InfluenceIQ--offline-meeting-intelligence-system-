# Website processing and participant review — 19 October 2026

The website is the current development target. These changes do not modify the Android app or require new models, cloud processing, or package installation.

## Findings from the completed upload

The 2,560.569-second recording took 1,420.631 seconds of worker time (23:40.6). Speaker separation consumed 788.341 seconds and transcription 615.151 seconds. Audio preparation, slides, alignment and structured NLP accounted for the remainder. Earlier transcript-only runs are not comparable to this run with speaker separation enabled.

Automatic clustering produced **139 groups**, of which eight had nonzero influence estimates. This does not establish 139 participants. Speaker fragmentation and sparse decision-linked evidence make these scores unsuitable for interpreting actual people. No ground-truth speaker count or checked transcript was supplied, so no count was guessed and the original meeting was not rerun or rewritten.

## Delivered changes

- Upload-byte progress, measured per-stage audio progress, continuously updating elapsed time, and explicitly estimated overall progress/remaining time. Total ETA uses comparable previous local stage timings and current measured pace; insufficient data shows a calculating state instead of an invented finish time. Completed worker time remains fixed when reopening a meeting.
- Serial, cancellable polling prevents overlapping responses from replacing a completed report. All report sections, names, roles, vocabulary, audio links and revisions update together without a page reload. Interrupted polling reconnects automatically.
- Transcription runs before global speaker separation, providing draft checkpoints earlier. Speaker attribution then reuses independently cached raw words and timestamps. Changing diarization does not require new neural speech decoding when these observations exist. Existing older attributed caches remain compatible; an older cache without raw words may need one fresh decode when the speaker configuration changes.
- Native Sherpa progress callbacks report speaker-feature work. The feature counter is capped below completion until whole-recording clustering returns. State writes are throttled during feature extraction.
- Speaker labels start at **Speaker 1** in the UI; stable internal IDs are retained. Names and custom contribution roles propagate to transcript, evidence, actions and influence. Explicit English/Hindi/Hinglish self-introductions can provide reviewable names; absent or conflicting introductions abstain. This is text evidence, not biometric identification or job-title inference.
- An optional known speaker count is visible before upload. Completed reports can rerun separation with a corrected count and a revision check. Audio, title and source-bound action reviews survive; names/roles must be reviewed again because groups can change. Unusually high automatic counts are flagged. Unknown counts remain automatic.
- Transcript search highlights literal matches, reports matching passages, filters by speaker and provides clear/reset and timestamp playback controls. It searches the selected meeting; no generative or cross-meeting semantic search was added.
- Vocabulary suggestions prioritize observed acronyms, technical terms, repeated name/product spellings and terms also present in slides. Frequent conversational fillers alone do not become hints. Suggestions are cached and versioned. Editing hints affects future recordings, not the saved transcript.
- Language observations and original Hindi/English/Hinglish text are retained. Editable vocabulary, language selection and speaker settings are available in the upload workflow.
- PPTX upload displays the filename once, with replace/remove actions. Archive size, XML and package relationships are checked before scheduling expensive audio inference. Legacy binary `.ppt` is not supported; save it as `.pptx` first.
- WAV, MP3, M4A, MP4 with audio, FLAC, OGG, WebM, AAC, OPUS, WMA, AIFF/AIF, AMR and 3GP are accepted when FFmpeg can decode the contents. Multipart chronological recordings are retained. Corrupt/empty/non-audio inputs are rejected.
- Login/register have submission state, duplicate-submit prevention, password visibility, confirmation and useful validation errors. Local development CORS includes port 5174.
- Desktop navigation, responsive surfaces, upload controls, processing cards, evidence views and auth screens share the updated visual design. There are no generative notes, question-answering or summary routes in this workflow. Observed question events remain part of the NLP taxonomy.

## Validation

- Full Python suite: **555 passed**, seven upstream deprecation warnings. The final PPT package-hardening change also passed all 19 focused website tests.
- Frontend lint and production build pass.
- Browser workflow passes at widths **360, 390, 960 and 1440** without page errors or horizontal overflow. Checks include microphone pause/resume, recording recovery, auth confirmation, PPT selection, progress, completion without reload, imported speaker names, edits/history, role labels, search highlights, print, influence evidence, slide alignment and export. Browser API responses are intercepted fixtures; microphone input is synthetic.
- Real FFmpeg encode/decode checks pass for 13 format families, including AAC-in-3GP and AMR narrowband.
- Real offline API worker: a public 20-second English AMI excerpt plus a PPTX completed in **12.392 seconds**, producing four transcript passages, two speaker clusters, one slide and two influence records. Draft text appeared before completion; measured diarization progress was observed at 6.7%, 40% and 86.7%. Socket connections were denied and **none were attempted**. This is an integration check, not recognition/speaker accuracy evidence.
- Re-attributing that excerpt with changed test speaker IDs reused exact original passage text/times with **zero neural decodes**, taking about **0.049 seconds**. This measures attribution only, not speaker-model inference or a full-meeting speedup.
- Artifacts are under `.runtime/validation/web-20261019/`; browser screenshots are under `.runtime/validation/minimal-ui/`. Validation accounts/databases are isolated from the user's database.
- The real backend was gracefully restarted only after it had zero queued/processing jobs. Existing accounts, completed uploads and original recordings were retained. Backend `8001` and frontend proxy `5174` both pass health checks. Backend logs are at `.runtime/backend-web.log`.

## Remaining work and limits

1. **Automatic speaker quality is unresolved on the long recording.** Calibrate clustering and evaluate held-out recordings with checked speaker intervals, including overlapping/distant speech. A known count is optional, not a substitute for automatic evaluation. The upstream [Sherpa example](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/offline-speaker-diarization.py) exposes automatic clustering thresholds and exact counts; neither establishes accuracy for this recording. No threshold was changed without evidence.
2. **Hindi/Hinglish speech accuracy is unmeasured.** Unicode/script detection, mixed-language NLP rules and source preservation are tested; natural code-switched audio needs human-checked transcripts and speaker annotations. No new training or fine-tuning is required to run the system; an annotated evaluation set is required before deciding whether either would help.
3. **Draft progress is incremental file processing, not microphone-streaming recognition.** Browser recording remains recoverable locally, then is analysed after upload/stop. ASR checkpoints normally cover 120-second chunks; the first uncached chunk must finish before its draft text appears. True low-latency recognition during capture needs a separate bounded capture/inference flow and end-to-end timing/accuracy tests.
4. **Influence remains an unvalidated analytical estimate.** A zero means no weighted contribution was detected, not that the person had no influence. The formula and source evidence remain inspectable; scores were not inflated or replaced with speaking-time rankings.
5. No new full-length before/after speed or RAM benchmark was run. Reordering work improves time to the first draft; word-cache reuse avoids repeated speech decoding for eligible reruns. It does not remove the cost of fresh speaker inference.
