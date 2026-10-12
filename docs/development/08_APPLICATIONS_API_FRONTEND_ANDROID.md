# API, browser, local AI, and Android implementation

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Local API and state

[`backend/api.py`](../../backend/api.py) uses FastAPI, SQLite/SQLAlchemy, bcrypt passwords, JWT access tokens, private job manifests, and one shared inference executor. `users` stores IDs/email/password hashes and a legacy nullable reset field. `meetings` stores ID, owner, title, status, report JSON string, and creation time. The default active database is `data/state/nexus_v2.db`; `nexus.db` is retained historical data.

The runtime directory is restricted to owner access, and a generated JWT secret file is private. Authorization filters meetings by owner. Playback tokens carry purpose, user, meeting, and expiry and are checked separately from access tokens. Public `/media` serving and public reset-token disclosure from the older version were replaced; terminal recovery uses `scripts/reset_password.py`.

| Route | Operation |
| --- | --- |
| `POST /api/auth/register`, `/login` | Local account creation/login; access tokens last 24 hours |
| `POST /api/auth/forgot-password`, `/reset-password` | Disabled; instruct terminal recovery |
| `GET /api/health` | Local model readiness, available speech models, optional notes models, upload limit |
| `POST /api/analyze` | Multipart audio parts, optional one PPTX, title, diarization/model/language/vocabulary/speaker count; returns 202 |
| `GET /api/meetings` | Owned meeting list |
| `GET /api/search?q=...` | Lexical search across owned completed transcripts |
| `GET /api/meetings/{id}` | Status/stage/errors/progress/preview/report and scoped playback URL |
| `GET /api/meetings/{id}/audio?token=...` | Authorized PCM playback |
| `POST /api/meetings/{id}/retry` | Queue a failed meeting if source manifest remains |
| `POST /api/meetings/{id}/summarize` | Queue optional notes using an installed local model |
| `POST /api/meetings/{id}/ask` | Passage retrieval or local model-backed draft answer |
| `POST /api/meetings/{id}/edit` | Title and known-speaker aliases |
| `GET /api/meetings/{id}/export?format=...` | JSON, MD, TXT, SRT, VTT, or transcript CSV |

The API validates supported extensions and decodable audio, reads uploads in 1 MiB blocks, limits total payload to 1 GiB by default, and accepts up to 32 ordered audio parts and one presentation. It is a local single-process prototype, not a horizontally scaled queue service.

## Browser implementation

[`App.jsx`](../../frontend/src/App.jsx) provides accounts, library/search, microphone/device selection, optional shared-tab audio, audio upload ordering, model/language/vocabulary/speaker settings, processing previews, report review, transcript pagination/search, playback, aliases, and exports. `MeetingNotes.jsx` (historical; removed in chapter 18) adds optional notes and questions.

Recording uses MediaRecorder and Web Audio. A real amplitude measure is displayed. Microphone capture requests no automatic echo/noise/gain processing; hardware/browser behavior can still differ. Shared-tab audio, when available, is mixed with the microphone; this is recording-source mixing, not the research slide-fusion method.

[`recordingStore.js`](../../frontend/src/recordingStore.js) saves produced recording blobs immediately in IndexedDB and reconstructs a file after a tab reload. It does not guarantee uninterrupted background recording or unlimited storage. Stop/save before submitting; keep the recording tab open. Microphone permissions require localhost or HTTPS.

Laptop transcript pages show 100 passages; print/export paths retain all passages. A lower model score can expose an audio-review shortcut, but it is not an accuracy probability.

The launcher builds `frontend/dist` and serves it from FastAPI at port 8000. Vite development scripts remain available, but historical dual-server launcher instructions are superseded. Saved early browser scripts have selectors tied to old UI text; use the latest fixture script as the source of current browser checks and inspect selectors before rerunning historical scripts.

## Optional local notes and questions

`local_notes.py` (historical; removed in chapter 18) accesses fixed loopback Ollama `127.0.0.1:11434`, disables proxy-environment use/redirect following, and accepts installed local GGUF completion models. It rejects advertised cloud/remote aliases. The application does not automatically start Ollama or download its model.

Notes groups are overview, decisions, action_items, and open_questions. Input is split into bounded UTF-8 prompt parts (target 5,000 bytes, long texts subdivided into 500-character pieces). Each part is processed with structured JSON output. An item is retained only with valid source segment IDs and a nonempty exact quote present in a cited source. Owner/deadline strings must appear literally in cited text; otherwise they become null.

Completed parts are cached using transcript/model digest identity. Per-part notes are deduplicated by quote plus source IDs without a later global synthesis that might drop late content. This preserves processed-part coverage but can leave repetition/incomplete cross-part reasoning.

[`search.py`](../../src/meeting/search.py) implements Unicode lexical retrieval with term frequency, document frequency, phrase boost, and neighboring-turn context. It is not an embedding/vector search engine. Q&A selects up to eight hits, collects their context, and sends only the first bounded context chunk to the local model. It does **not** guarantee inclusion of every retrieved hit or understanding of the entire meeting. No local model means useful search passages are still returned.

Checked quotes establish provenance, not entailment: a correct quote can be attached to an incorrect paraphrase. Human review and factuality evaluation are still required. Optional LLM notes are separate from the deterministic event/decision/influence pipeline, so a paper should evaluate them separately.

## Android architecture

The latest manifest identifies `org.meetiq.offline`, version **0.4.0-prototype**, label InfluenceIQ, minimum API 26. The direct build targets API 35 and compiles ARM64/x86_64 using pinned whisper.cpp v1.7.6. Source roles:

| File | Responsibility |
| --- | --- |
| `MainActivity.java` | Native Home/Recording/meeting detail/settings navigation and state restoration |
| `MeetingService.java` | Foreground microphone/analysis service, progress, resumable chunk processing |
| `NativeWhisper.java`, `whisper_jni.cpp` | Native model loading/transcription bridge |
| `WavAudio.java` | WAV validation, normalization, header recovery and PCM handling |
| `EventRules.java` | Compiled bilingual candidate/blocker banks |
| `MeetingRepository.java` | Local meeting summaries/cache, metadata-preserving rename, Markdown export |
| `AudioPlaybackController.java` | Local playback lifecycle and seeking |
| `LocalTransfers.java` | Background document-picker imports/exports |
| `MeetingProgress.java` | Actual recording amplitude and structured chunk progress |
| `Ui.java`, `res/` | Native widgets, local vector icons, system themes |
| `json/Json.java` | Local JSON support used by JVM-side checks |

Private meeting folders retain `audio.wav`, `report.json`, and `checkpoint.json` plus metadata. Model import copies a selected local GGML model into private storage. App backup is disabled; exports use a user-selected destination. No INTERNET permission is present.

## Feature parity

| Feature | Laptop | Android 0.4.0 |
| --- | --- | --- |
| Offline inference after provisioning | Yes | Yes, after model import |
| Microphone recording | Browser; recoverable blobs | Native foreground service/WAV |
| ASR engine | faster-whisper/CTranslate2; small default | whisper.cpp; local base model provisioned |
| Chunk overlap/checkpoints | Word midpoint handling; content/settings key | Segment midpoint handling; audio/model-byte key |
| Hindi/English settings and phrase candidates | Yes; quality unvalidated | Yes; quality unvalidated |
| Real speaker separation | Optional model/backend; currently unprovisioned | Absent, UNKNOWN |
| Slide alignment | Optional embedding/TF-IDF | Absent |
| Decision lineage/interactions/influence | Heuristic modules | Absent |
| Local LLM notes/questions | Optional Ollama | Absent |
| Playback/search/title/export | Yes | Yes |
| Analysis pause | Interrupted-job recovery | Explicit pause between native chunks |
| Account/server requirement | Local account and API | None |

## Verification boundary

October 5/6 records describe Python/frontend checks and emulator native inference. The later [Android design record](../android/DESIGN.md) documents real emulator microphone capture, model/WAV import, English native inference, pause/restart/resume, search/pagination, candidate filters, playback, rename, exports, and layouts. Its UI screenshots partly use generated reports; they are UI evidence, not recognition accuracy evidence.

No physical ARM64 phone evaluation is recorded. Android Gradle files still declare 0.3.1 while the manifest/direct build declare 0.4.0; use `android/build.sh` and report the built manifest version. The historical root `efficiency-results.json` also records the earlier 0.3.1 stage, not the latest UI release.
