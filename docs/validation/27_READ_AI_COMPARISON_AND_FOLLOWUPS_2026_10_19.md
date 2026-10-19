# Read.ai comparison, repository research and follow-up delivery — 19 October 2026

This review used Read.ai's current product documentation, upstream GitHub repositories and model cards. It is a targeted review, not a claim to have inspected the whole Internet or independently benchmarked a competitor. All comparisons describe capabilities, not demonstrated quality equivalence. InfluenceIQ remains a local prototype requiring physical-phone and Hindi/Hinglish validation.

## What the competitor documents

Read.ai advertises transcripts, summaries, key discussion points, actions, playback/highlights and participant/coaching metrics in its [meeting reports](https://www.read.ai/meeting-reports). Its [mobile documentation](https://www.read.ai/mobile) describes in-person capture, shared accounts, automatic cross-device synchronization and recordings up to four hours. Its [integrations directory](https://www.read.ai/integrations) lists calendar, messaging, CRM and task-management connections. Its [homepage](https://www.read.ai/) also describes Ask Read with citations and context from other connected work sources. These are vendor feature descriptions; they do not establish recognition accuracy for our microphones, meetings or mixed-language input.

| Capability | InfluenceIQ's actual current state |
| --- | --- |
| Local microphone capture/import | Implemented on Android and website; real phone capture/lifecycle acceptance pending |
| Offline speech/speaker processing | Laptop faster-whisper + Sherpa-ONNX, Android Whisper.cpp + ONNX; no account needed locally |
| Hindi/English/Hinglish | Multilingual ASR and bilingual rules available; natural target-domain accuracy not established |
| Transcript, evidence playback and review | Implemented; human names require correction, unclear speech can remain UNKNOWN |
| Summaries | Structured extractive recap in report data; no fluent generative summary or chatbot |
| Action ownership/deadlines/completion | New explicit user-reviewed fields on web/Android, separate from source evidence |
| Calendar connection | New local ICS export for reviewed open deadlines; no OAuth calendar connection or automatic invitations |
| Shared web/mobile account | Implemented on the same backend; explicit publish/download, no automatic background mirroring |
| Search/Ask Read equivalent | Title search and within-meeting transcript search; no cross-meeting semantic Q&A |
| Video highlights, sentiment, charisma/coaching | Not implemented; influence estimates do not substitute for these measurements |
| Calendar bots, Slack/CRM/email connections | Not implemented; any live connection needs network access, credentials and explicit user-selected sharing |
| Reliable long meetings | Chunked/resumable ASR exists; global diarization remains memory-limited and real long-meeting phone validation is pending |

## Upstream projects checked and integration decisions

The runtime licenses below do not automatically license every associated model or dataset. Existing APK runtime/model notices are already packaged under `android/app/src/main/assets/licenses/`.

| Primary source | Suitability / decision |
| --- | --- |
| [Whisper.cpp](https://github.com/ggml-org/whisper.cpp), [MIT license](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE) | Retain the tested native Android engine, pinned v1.7.6. Quantization/VAD/accelerators are evaluation options; a latest-master replacement is not an accuracy result |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [MIT license](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE) | Already integrated on the laptop with CPU/int8, chunk recovery and vocabulary hotwords. Batching is not enabled by default: memory and code-switching/timestamp behavior need comparison on the target data |
| [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx), [Apache-2.0 license](https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE) | Already integrated/pinned v1.13.8 for speakers. Upstream has Android, streaming, VAD and enhancement examples, but our current diarizer is global rather than streaming. A streaming implementation must validate stable identities across windows |
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT; already used in the laptop ASR path. Retain its current behavior rather than introducing another unmeasured detector |
| [WhisperX](https://github.com/m-bain/whisperX), [BSD-2-Clause license](https://github.com/m-bain/whisperX/blob/main/LICENSE) | Possible laptop forced-alignment experiment. Its own documentation discloses language-specific alignment requirements, overlapping-speech limits and imperfect diarization. Extra models/runtime make it an unsuitable automatic mobile replacement |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | MIT runtime candidate for optional local summaries/Q&A. Not added: a suitable separately licensed model, multilingual factuality tests, bounded retrieval and phone RAM/latency measurements are required |
| [Meetily](https://github.com/Zackriya-Solutions/meetily), [MIT license](https://github.com/Zackriya-Solutions/meetily/blob/main/LICENSE.md) | Useful local desktop workflow reference. It is a desktop application, not a drop-in Android component; no source was copied or extra desktop stack installed |
| [Vosk](https://github.com/alphacep/vosk-api) | Apache-2.0 runtime and Android/offline support make it another benchmark candidate. Do not assume separate Hindi/English models improve code-switching; selected model licenses and results need checking |
| [TEN VAD](https://github.com/TEN-framework/ten-vad/blob/main/LICENSE) | Its published license adds competition/deployment conditions to Apache-2.0. Not integrated or treated as an ordinary permissive replacement |
| [AI4Bharat IndicConformer-600M](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) | MIT model card, gated access/contact-sharing conditions, Hindi among supported Indian languages. Candidate for a separate laptop benchmark; no assumed English/Hinglish superiority. The card now points to Indic-Transcribe |
| [Indic-Transcribe-core](https://huggingface.co/bodhan-ai/indic-transcribe-core) | Its card explicitly targets code mixing/Indian-accented English, but lists 1.2B parameters, a 4.6 GB checkpoint, gated access and a custom license. Consider only after access terms and hardware feasibility are resolved; not downloaded or added to the 6 GB phone |

No new upstream code, dependency, model, external account connection or public service was installed for this delivery. Existing pinned libraries remain in use. Model-card benchmark numbers were not substituted for our own results, and a Hindi benchmark is not a Hinglish meeting benchmark.

## Implemented improvement

**Android 0.7.1-prototype / version code 9** and the website now support reviewed follow-ups:

- Set an optional task owner, an explicit calendar date, and open/done/dismissed status.
- Keep corrections separate from original event/transcript text. The speaker is never assumed to be the owner, and ambiguous relative dates are not silently guessed.
- Bind reviews to the source event ID, exact text and available source timestamp. Retain old annotations across reanalysis while withholding them from changed evidence.
- Require authenticated ownership and a matching current report revision for web saves. Reject stale edits and malformed dates/control characters. Native metadata is written atomically and preserves other fields.
- Carry reviews through existing explicit native/web report synchronization and Markdown/JSON exports.
- Export reviewed open deadlines as local all-day calendar reminders, using [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545) text escaping, CRLF, UTF-8 line folding, stable UIDs and exclusive end dates. No invitations, external API or automatic scheduling is performed.

This improves follow-through and prevents some incorrect metadata associations. It does not improve speech recognition or establish task-extraction accuracy. See [the user guide](../guides/FOLLOW_UPS.md).

Main sources are `src/meeting/followups.py`, `backend/api.py`, `src/report/{portable,transcript_export}.py`, `frontend/src/{App,TaskReview}.jsx`, and native `ActionReviews.java`, `MeetingRepository.java`, `MainActivity.java`. No inference model/decoder default changed.

## Verification

Final measurements, APK hash and result paths are recorded in `outputs/evaluation/followups_delivery_20261019.json`. Logs use `logs/followups_*`; screenshots and live-client results use `outputs/followups-ui/`.

The final regression suite passed **536 tests** with seven dependency warnings. Frontend lint/build and the existing browser workflow passed. A real isolated backend/browser run at 360/390/960 px saved a Hindi owner, persisted it across reload and downloaded the calendar. Native UI testing downloaded that review, edited the owner/date, published it back, then downloaded a website completion update while preserving the older local snapshot. Empty-calendar guidance and validation-account sign-out passed. JVM and real Android-runtime probes passed; the APK signature and 16 KB zip alignment were verified. This is an emulator result, not a physical Samsung or external calendar-client import result.

The dedicated Python tests cover private ownership, stale revisions, real native-report publication/republishing, review preservation across reanalysis, source changes, invalid labels/dates, calendar escaping/folding/year boundaries, and exclusions for undated/unreviewed/done/dismissed tasks. The actual Android JSON/runtime probe covers local persistence, unchanged source files, metadata preservation, source changes and calendar/report exports. Browser and native account tests use an isolated validation account/database, not the real 10-account/17-meeting history. Browser audio used in fixture checks is synthetic; the new task UI does not constitute an ASR evaluation.

## What must happen next to compete on quality

1. Collect consented Hindi, English and Hinglish meeting excerpts with independently checked transcripts and speaker timelines, including near/far voices, background noise and overlap. Separate train/tuning/test speakers and meetings. Do not use inferred labels as references.
2. Run the same audio through current models and candidate configurations. Record model revision/license, language mode, vocabulary hints, device/thread/quantization settings, WER/CER, DER, processing time, peak memory and thermal/battery behavior. Treat native-script and Romanized alternatives with a documented scoring policy; do not compare incompatible WER/OIWER metrics as if identical.
3. Use the existing `scripts/evaluate_recordings.py --manifest ... --model small --output ...` workflow for laptop WER once recordings exist. It does not evaluate diarization or non-Whisper candidates; those need separate adapters and the same references. No new benchmark was fabricated here.
4. Validate a real long meeting on the Samsung, then test interruption/restart, limited storage, screen locking and long transfer recovery. A two-hour silence fixture is not a real meeting benchmark. Bounded-memory speaker tracking remains a separate implementation/validation stage.
5. Build additional recap/search/integration features in measured stages. Cross-meeting evidence retrieval and optional source-grounded local generation are future work. Calendar/CRM bots, automatic mirroring and public sharing are separate online workflows; keep them explicit so the offline core stays usable without any service.

Physical-phone acceptance, target-language quality, production signing and a fair same-input Read.ai comparison remain incomplete. There is no claim of full Read.ai parity, superior accuracy, universal real-time performance or production readiness.
