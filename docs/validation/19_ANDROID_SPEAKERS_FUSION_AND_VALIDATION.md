# Android speaker, influence and PPT fusion delivery

Delivered 7 October 2026. This chapter supersedes earlier statements in chapters 08, 13, 17 and 18 that the native Android prototype lacks speaker/influence/PPT analysis. The submitted report and `mai folder older` snapshot were not edited.

## What changed from 0.5 to 0.6

| Component | Previous native Android | Current 0.6 implementation |
| --- | --- | --- |
| Speakers | All passages were `UNKNOWN` | Packaged pretrained ONNX segmentation and speaker embeddings; meeting-global clustering; conservative timestamp attribution |
| Participant names / roles | Unavailable | Observed contribution roles, editable names/roles, saved metadata/history and transcript/export labels |
| Influence | Unavailable | Seven weighted candidate decision-linked feature categories, raw counts, source events, tied ranks and honest zero-evidence scores |
| PPT | Native text for reference | TF-IDF passage-to-slide matching; minimum score/margin; matched speech, speakers, timestamps and playable evidence |
| Re-analysis | Chunked ASR checkpoint | ASR plus audio/model/count-addressed speaker cache; Overview → Update analysis refreshes derived analysis |
| Language | Requested setting only | Dominant Hindi/English language observed per ASR chunk is retained in passages and report metadata |
| Cloud | No option | Optional configured HTTPS website opened in a browser; local processing still requires no network permission |
| Research measurements | Earlier native smoke tests only | New source-verified English Android WER/DER pilot and current website WER rerun; limitations below |

APK: [`android/build/meet-iq-debug.apk`](../../android/build/meet-iq-debug.apk), **0.6.0-prototype**, approximately 70 MiB, ARM64 and x86_64, Android API 26+. Size increased because the speaker weights and native runtime are bundled. This is a signed development APK; it is not a store release. The GGML speech model still needs importing once. Speaker setup requires no phone-side download.

## Native pipeline and exact implementation

1. Existing `AudioImport`/`WavAudio` normalize recordings to canonical 16 kHz mono PCM16 WAV in private app storage. Recording still streams recoverable WAV data, with a six-hour capture ceiling.
2. `MeetingService` runs whisper.cpp in 120-second chunks with two seconds of boundary context. Checkpoint identity **v4** includes the speech-model/audio SHA-256, language and vocabulary. It retains the raw transcript. The one-time v3→v4 transition reprocesses old checkpoints because token timestamps were added.
3. `whisper_jni.cpp` enables token timestamps, joins BPE pieces into complete word text before UTF-8/JSON serialization, and returns the dominant selected Hindi/English language. This prevents serializing individual partial Hindi UTF-8 token pieces as words.
4. The service frees the Whisper model before speaker inference. `speakers_jni.cpp` calls Sherpa ONNX's C API using the same segmentation/ERes2Net weights provisioned for the website. Both networks use two CPU threads. Clustering covers the complete supported recording; speaker labels are normalized by first appearance.
5. `speaker-turns.json` is cached using audio hash, both model hashes, runtime version, requested participant count and threshold. Changing only the presentation reuses speaker/ASR work. The default clustering threshold is **0.5**, still unvalidated; a known participant count can be supplied in Settings.
6. `SpeakerReports` builds derived attributed passages, leaving the raw ASR checkpoint unchanged. Valid word timestamps split passages at speaker changes. When word timing/text reconstruction is invalid, attribution falls back conservatively to the whole ASR segment. `SpeakerAttribution` requires at least 50% overlap coverage and a 15% duration margin over a second speaker; unclear/overlapping passages stay `UNKNOWN`. Cluster IDs identify voices within one meeting, not people across meetings.
7. The existing exported English/Hindi/Hinglish event rules produce extractive candidates with source segment IDs, timestamps and speaker IDs. These are reviewed candidates, not generated meeting notes.
8. `SlideIndex` tokenizes Unicode letters/marks/numbers, removes a small stop-word/action-word list, builds sparse slide TF-IDF vectors, and computes cosine similarity to passage text. A slide is selected only at score **≥0.15** and top-two margin **≥0.05**. Top candidates remain in JSON. Scores are lexical similarity, not confidence or semantic entailment.
9. `MeetingAnalysis` links each explicit decision candidate to preceding proposal/evidence/objection/revision candidates within **120 seconds** only when lexical topic terms overlap. A decision includes its own source event. Generic verbs such as “reduce” do not link unrelated latency/budget topics. This is a limited lexical candidate lineage, not the full Python decision/evidence graph.
10. Influence counts decision-linked proposal, evidence, objection, revision, decision, interaction and slide-grounded contributions. Adjacent different-speaker linked events can add interaction credit when they share a decision and topic. Multiple rule labels on one source passage do not duplicate a category's contribution. Unknown speakers never become fabricated participant records.

Weights follow the existing prototype categories:

| Feature | Weight |
| --- | ---: |
| proposal | 0.15 |
| evidence | 0.20 |
| objection | 0.15 |
| revision | 0.20 |
| decision | 0.15 |
| interaction | 0.05 |
| slide_grounding | 0.10 |

Each raw feature is divided by the maximum across observed participants; absent evidence gives zero. Influence is the weighted sum, bounded to [0,1]. Attributed speaking time is displayed separately and is not added to the influence formula. Scores are estimates from candidate evidence, not causal influence or accuracy percentages. No decision-linked evidence gives a zero score with an explanation; it does not establish that a participant had no real influence.

Native method IDs are `android_candidate_lineage_v1` and `tfidf_native_slide_text_v1`. The website's graph/evidence logic is different. Do not claim Android and Python rankings are equivalent because they share weight names.

## Screens and persistence

Home stays minimal: recording, audio import, optional PPT and vocabulary, recent history and Settings. Reports now have Participants and Presentation tabs alongside Transcript, Actions, Decisions and Analysis. The existing horizontal tabs scroll on phones.

Participant edits are stored in `metadata.json` under `speaker_names` / `speaker_roles`. They retain unrelated metadata and apply to transcript/event/influence/presentation labels. JSON exports retain stable speaker IDs and add display names/roles; Markdown includes events, influence, presentation matches and the complete transcript. The export is labelled **Meeting report**; there is no generative notes or chat feature.

After replacing a PPT, use **Overview → Update analysis**. Names refer to meeting-local cluster IDs: verify them again if changing the participant count or speaker model changes clustering. Roles are observed contribution descriptions, with user-entered overrides, not automatically verified professional titles. Actual role/name text spoken in audio may itself contain ASR errors.

Example current screenshots: [Participants](../../android/design/analysis/participants.png), [Transcript](../../android/design/analysis/transcript.png), [Influence](../../android/design/analysis/analysis.png), [Presentation](../../android/design/analysis/presentation.png). “Asha / Project lead” is an intentionally entered test alias, not AMI ground truth.

## Build / model provisioning

```bash
# Existing 0.5 development checkout:
.venv/bin/python scripts/setup_android_speakers.py
bash android/build.sh
bash android/test.sh
# Connected emulator/device; after the build:
bash android/test-device-analysis.sh
adb install -r android/build/meet-iq-debug.apk
```

Fresh setup also invokes speaker provisioning from `android/setup.sh`. The provisioning script verifies checksums, extracts only the two required native libraries per ABI and copies verified speaker weights into generated assets. Native dependencies/assets are ignored build products, not committed model files. Gradle configuration is updated for the same ABI/version/dependencies; the tested build here uses the direct SDK build script.

| Artifact | SHA-256 |
| --- | --- |
| Sherpa Android 1.13.8 archive | `2ff63469a71cb6009aa2e3ed5f4a670f8abdcbe4bb9ffd23776afc792a6b4f44` |
| Pinned C API header | `2a1b95084be8fd1deb3228fcad2fd3f7f0258b64582f7402281ec174c7b7f4ce` |
| Segmentation ONNX | `220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079` |
| Speaker embedding ONNX | `1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b` |

Runtime/model sources: [Sherpa Android diarization](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/apk.html), [pinned native release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/v1.13.8), [segmentation model card](https://huggingface.co/pyannote/segmentation-3.0), [3D-Speaker toolkit/model documentation](https://github.com/modelscope/3D-Speaker). These pretrained models were not trained by this project.

The packaged ONNX Runtime binary reports version 1.28.2. The APK includes upstream license/third-party notices under `assets/licenses/`, with [component provenance](../../android/app/src/main/assets/licenses/NOTICE.md). The direct SDK build is verified; Gradle packaging also selects the pinned C API library once when it is supplied by both CMake and the runtime directory.

## Source map for a new developer

| File | Responsibility |
| --- | --- |
| [`scripts/setup_android_speakers.py`](../../scripts/setup_android_speakers.py) | Explicit checksummed build-time runtime/model provisioning |
| [`CMakeLists.txt`](../../android/app/src/main/cpp/CMakeLists.txt) | JNI build and pinned imported C API library |
| [`speakers_jni.cpp`](../../android/app/src/main/cpp/speakers_jni.cpp) | PCM float buffer, ONNX networks, global clustering, progress and result ownership |
| [`whisper_jni.cpp`](../../android/app/src/main/cpp/whisper_jni.cpp) | Speech decoding, language selection and joined token timestamps |
| [`NativeSpeakers.java`](../../android/app/src/main/java/org/meetiq/offline/NativeSpeakers.java) | Private verified model extraction and JNI wrapper |
| [`SpeakerAttribution.java`](../../android/app/src/main/java/org/meetiq/offline/SpeakerAttribution.java) | Conservative overlap/margin attribution |
| [`SpeakerReports.java`](../../android/app/src/main/java/org/meetiq/offline/SpeakerReports.java) | Derived word-attributed passages and checkpoint preservation |
| [`SlideIndex.java`](../../android/app/src/main/java/org/meetiq/offline/SlideIndex.java) | Unicode sparse TF-IDF text index and lexical topic check |
| [`MeetingAnalysis.java`](../../android/app/src/main/java/org/meetiq/offline/MeetingAnalysis.java) | Slide matches, candidate lineage, roles, contribution features and influence |
| [`MeetingService.java`](../../android/app/src/main/java/org/meetiq/offline/MeetingService.java) | Foreground processing, stage order, caches, partial/final reports |
| [`MeetingRepository.java`](../../android/app/src/main/java/org/meetiq/offline/MeetingRepository.java) | History, participant metadata and complete exports |
| [`MainActivity.java`](../../android/app/src/main/java/org/meetiq/offline/MainActivity.java) | Native minimal UI, edits, source playback, update and browser shortcut |
| [`MeetingAnalysisProbe.java`](../../android/test/MeetingAnalysisProbe.java) | Actual Android-runtime fusion/scoring/export contract checks |
| [`scripts/evaluate_android_ami.py`](../../scripts/evaluate_android_ami.py) | Verify excerpt PCM against AMI source and score manual WER/DER references |

## Measured evidence from this update

### Android annotated English pilot

Real AMI `ES2002a.Array1-01`, **source seconds 60–150**, 90 seconds, normalized PCM samples independently verified against the original source. Native multilingual **GGML base** model, explicit **four-speaker** constraint, Pixel_6 x86_64 emulator/API 37 with 16 KB pages. An artificial three-slide presentation was imported through the Android document picker; it is an integration fixture, not manually labelled AMI slide ground truth.

| Measurement | Result |
| --- | ---: |
| WER | **37.7358%** |
| Reference words | 265 |
| Substitutions / deletions / insertions | 56 / 37 / 7 |
| Native speaker-turn DER | **13.4815%** |
| Delivered attributed-passage DER | **13.9809%** |
| Identified participants | 4 |
| Native speaker turns | 12 |
| Delivered transcript passages | 33 |
| Event candidates | 6 |
| Decision candidates | 0 |
| Influence records | 4, all zero due to no decision-linked evidence |
| Slides / selected text matches | 3 / 8 |

DER uses AMI manual segment transcriber boundaries, optimal label permutation, a 0.25-second collar and overlap included. Native-turn DER and delivered-passage DER measure different outputs. The initial 20-second smoke excerpt fell in unannotated pre-meeting speech and was rejected by the evaluator rather than assigned fabricated accuracy; the annotated window above was then used.

Metrics: [`outputs/evaluation/android06_ami90_annotated.json`](../../outputs/evaluation/android06_ami90_annotated.json), log [`logs/android_06_ami_metrics.log`](../../logs/android_06_ami_metrics.log). Exact current report and input/model hashes are recorded by the evaluator/report. This is one short English pilot, not a reliable estimate for all meetings or natural Hinglish. No fusion F1 or human influence correlation was measured.

### Website ASR rerun

Existing ten-minute `ES2002a.Array1-01`, source seconds **30–630**, default multilingual **small / CPU int8 / 120-second chunks**, diarization disabled for the ASR benchmark. Current recorded WER is **42.2992%** (175 substitutions, 369 deletions, 30 insertions / 1,357 reference words). The earlier saved 120-second-profile run was **41.4886%**; this rerun is **0.8106 percentage points worse**, so this delivery does not demonstrate an accuracy improvement. The historical 300-second-profile result was 45.8364%; changing profiles is a separate comparison, not evidence that adding speaker/fusion features improved ASR.

The timed fresh-ID run recorded 105.945 seconds, RTF 0.1766 and process peak RSS 1,057.2 MiB. These figures came from this laptop run, with other workloads present; they are not a controlled phone/GPU comparison. The historical window includes pre-meeting audio not fully covered by AMI's manual word reference, and overlapping reference words are ordered by timestamp. Report the window/reference policy explicitly rather than converting WER into a general “accuracy” promise.

Metrics: [`outputs/evaluation/benchmark_ES2002a_30_600_small_android06_scope_benchmark.json`](../../outputs/evaluation/benchmark_ES2002a_30_600_small_android06_scope_benchmark.json), log [`logs/current_scope_wer.log`](../../logs/current_scope_wer.log). Android and website figures use different models/windows and should not be treated as a direct head-to-head comparison.

### Functional checks

- **502 Python tests passed**, including training leakage/input validation, closed registration with existing login and explicit GPU profile overrides: [`logs/android_06_python_tests.log`](../../logs/android_06_python_tests.log).
- Native ARM64/x86_64 build, APK signing/installation and 16 KB emulator library loading passed: [`logs/android_06_build.log`](../../logs/android_06_build.log).
- JVM WAV/import/PPT/rule checks plus Hindi lexical matching, ambiguous/unknown text and overlap abstention passed: [`logs/android_06_jvm.log`](../../logs/android_06_jvm.log).
- Android-runtime probe verifies lexical fusion, unrelated-topic rejection, candidate lineage, nonzero/zero influence, unknown exclusion, word-level speaker splitting, raw-checkpoint preservation, metadata edits and complete name/role exports: [`logs/android_06_analysis_probe.log`](../../logs/android_06_analysis_probe.log). Its positive influence examples are synthetic contract fixtures, not research measurements.
- Actual app UI verified real ASR/speakers, PPT document-picker import, derived cache reuse, name/role edits retained after process restart, and edited labels in the transcript. Current screenshots above show that result.

Passing these checks establishes functioning implementation, not validated research novelty, general recognition quality or production readiness.

## Remaining limitations and next work

- On-device global speaker processing supports **up to one hour**. It uses a native full-recording float buffer (up to ~230 MB) plus model/intermediate memory. Longer audio keeps its full chunked transcript and explicitly reports unavailable speaker analysis. Physical-phone memory/battery/thermal/background testing is still required; no physical phone was connected.
- Pause waits for the current native stage. The pinned upstream speaker API reports progress but does not support cancelling mid-stage. Its completed speaker cache is retained for resume.
- Automatic clustering can over/under-count speakers. Known count helped the measured pilot; tune threshold/count handling on validation DER before deployment claims.
- Rules and lexical candidate linkage can miss paraphrases, negation scope, implicit decisions and topic relationships. Android contribution roles/lineage are a baseline rather than full Python parity.
- Slide image-only content has no text match. No visual encoder, OCR or phone-side temporal slide windows are implemented. Cross-language lexical matching is weak unless terms overlap; it does not translate Hindi speech into English slide text.
- Native dominant language is scoped to Hindi/English. Natural within-sentence Hinglish, event/role quality, influence agreement and general phone accuracy still need independently annotated data.
- Training infrastructure is prepared, but no newly trained model or real human-labelled training set is claimed: [chapter 20](../research/20_TRAINING_DATA_AND_MULTIMODAL_RESEARCH.md).
- Cloud hosting is prepared, not deployed. Phone cloud use currently opens the website in a browser and does not synchronize local history: [chapter 21](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md).
