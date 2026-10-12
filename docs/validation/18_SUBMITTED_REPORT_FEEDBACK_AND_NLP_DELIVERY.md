# Submitted report, teammate feedback and NLP delivery — 7 October 2026

This chapter supersedes the application scope described in chapters 08 and 17. Chapters 01–16 remain a historical audit snapshot; chapter 17 records the earlier minimalist UI. The [submitted report](../submitted/GRPUP_NO_12_MAI_REPORT_1_LLM.md) was read, including its six objectives, architecture, influence signals, final outputs, baselines and evaluation plan. It has not been edited.

Both pasted discussions were reviewed. They are interpretations of feedback, not implementation or measured results. Their example influence/accuracy percentages, role names, task owners and deadlines are illustrative; they are not evidence that this project produces those outputs correctly.

## What your friend means

The website transcribes, but the project's central speaker/role/influence analysis was not becoming usable. He wants speaker identities linked throughout the transcript and analytical outputs, editable names and role labels, Hindi/English language handling and real Hinglish checks, optional vocabulary, and removal of notes/chat based on generative AI. Transcript-word search across meetings distracts from this purpose.

This is consistent with the report's main purpose: **speaker attribution → audio/PPT alignment → events/evidence → decision reconstruction → participant contribution → explainable influence**. A simpler Home must still lead to those core outputs. The report's “meeting summary” can be a structured statistical/extractive overview; it does not require an LLM-written summary.

The pasted assistant's proposed strict WAV-only upload policy would undo the earlier explicitly requested conversion fix. The website keeps its existing supported uploads; imported files are normalized internally. No new restriction to pre-converted 16 kHz mono PCM16 files was introduced.

## What existed before this change

- Recoverable multilingual transcription, an optional diarization adapter, PPT text/table/metadata extraction, semantic/optional temporal alignment, event/evidence rules, decision reconstruction, interaction graphs and weighted decision-linked influence were already implemented.
- The last UI change made capture simpler and added editable name/role metadata, but did not solve absent speaker weights. The default pyannote models were not locally available, so automatic mode returned UNKNOWN and no identified participants.
- Local generative notes and questions were added earlier, although they were not needed for the submitted research objectives.
- The website exposed little of the structured research output. Further inspection found a serialization boundary mismatch: influence JSON uses `participant`/`influence_score`, and action timestamps were formatted strings. A view expecting dataclass `speaker_id`/`score` and numeric timestamps would fail to expose valid output.
- Earlier current-only contributions and inherited research methods are distinguished in chapters 01, 06 and 07. Enabling an existing implementation does not make its algorithm newly invented.

## Changes delivered now

| Requirement | Implemented change | Practical limit |
| --- | --- | --- |
| Participants missing | Provisioned public local ONNX segmentation/embedding weights and installed pinned sherpa-onnx 1.13.8; selected the existing adapter as laptop default; Settings/health show setup status | Clusters can split/merge speakers; no physical identity recognition; global clustering reads the complete recording |
| Older UNKNOWN meetings | Owned **Analyse speakers from saved audio** operation queues required diarization and rebuilds downstream NLP, preserving title and edited vocabulary | Only UNKNOWN-only meetings; source audio must still exist; does not silently reassign already named clusters |
| Editable names and roles | Existing owned edits retained; names and user/estimated roles shown in transcript, Participants, actions, decisions, influence and slide/event evidence | Contribution roles are heuristic; human labels do not change scoring weights or prove a job title |
| Explainable influence | Dedicated view shows real score, seven normalized features, raw counts, weights and decision-linked source events | Prototype weights and ranking validity remain unmeasured; causal influence is not established |
| Full participant coverage | Scoring includes attributed speakers with no extracted events, using genuinely zero observed feature counts | Zero means no tracked decision-linked contribution, not that a person was unimportant |
| Correct explanation | Objection explanation now distinguishes base credit from the additional later-revision bonus | A later revision remains temporal association, not proof that the objection caused it |
| NLP meeting analysis | Separate event timeline and interaction relationships; decisions expose proposal/discussion/evidence/revision/final-event source records | Phrase rules and time-window grouping miss intent/coreference; source links do not establish semantic truth |
| Presentation output | Serialized native slides, tables and aligned discussion exposed in Presentation | Image metadata does not understand charts; OCR disabled; English MiniLM cross-language matching is unvalidated |
| Audio/PPT consistency | Review-required same-unit quantity mismatch flags on aligned statements sharing lexical context | A narrow numerical diagnostic, not general semantic/visual contradiction detection; empty flags do not prove consistency |
| Language | Automatic ASR retained; all observed chunk languages serialized; script/romanized-Hindi cues displayed as possible code mixing | Dominant chunk language is not complete within-sentence language recognition; cues are not language percentages or WER |
| Hinglish NLP | Added a bounded imperative task pattern and a negation guard; checked proposals/evidence/disagreement/decision/action in a mixed fixture | Audio/diarization are mocked in that fixture; real mixed-audio accuracy still needs checked recordings |
| Vocabulary | Optional spelling hints and observed Unicode word suggestions retained and editable | Suggestions are not NER, corrections or accuracy guarantees |
| No generative AI | Removed frontend notes component, local LLM module, health enumeration, resume worker and summarize/ask endpoints; old generated content is not published/exported | Historical saved content is retained in storage; speech recognition and neural encoders remain, as required by the project |
| No cross-transcript search | Removed library transcript-search UI and API route | History title filtering and finding text within the open meeting remain ordinary navigation aids |
| Export/history | JSON preserves structured NLP output; text/subtitle/CSV exports include saved speaker roles; CSV formula protection extended to roles | Old reports do not acquire new analytical fields until processed; edits are saved through the explicit Save controls |

## Comparison against the six formal objectives

| Report objective | Current evidence | What remains incomplete or unevaluated |
| --- | --- | --- |
| 1. Long audio with speaker-attributed transcription | Chunked ASR, word-level overlap attribution, global ONNX diarization and participant views run locally | Speaker accuracy/overlap recovery and two-hour diarization memory/runtime; no DER measurement in this delivery |
| 2. Textual and visual PPT representation | Native text, titles, tables, notes and visual metadata retained; slide content exposed | OCR/image/chart interpretation and a validated visual representation |
| 3. Cross-modal alignment | Existing semantic cosine matching with optional temporal scores, plus optional TF-IDF baseline | No live slide timing is created from PPT upload; Hindi/English cross-language alignment and ground-truth F1 remain unmeasured |
| 4. Suggestions, objections, evidence, corrections, decisions and tasks | Existing English/Hindi/Hinglish rules, new imperative guard, source events and reconstructed decisions exposed | Classification precision/recall/F1, coreference and robust implicit intent |
| 5. Inconsistencies with evidence | New narrow numeric mismatch diagnostic retains statement, slide text, unit and timestamp | General semantic contradiction, entity disambiguation, visual inconsistencies and evaluated precision/recall |
| 6. Explainable participant influence | Existing proposal/evidence/challenge/revision/decision/interaction/slide features, normalized weighted scores and source events surfaced | Human rank correlation, weight validation, true component ablations and causal interpretation |

Speaking duration and transcript-passage counts are displayed separately from influence. The implemented influence model deliberately gives speaking time no direct weight; the report's participation signal is represented through decision-linked contributions/interactions and separate baselines, not a new speech-duration component. This choice should be stated in the methods rather than claiming the exact illustrative six-term formula from the pasted chat.

## Verified results

| Check | Result | Boundary |
| --- | --- | --- |
| Python suite | **494 passed, 7 dependency warnings** after removing obsolete generative tests and adding NLP/ownership/export checks | Model boundaries are mocked in applicable unit tests; count is not an accuracy metric |
| Dependency/setup | 127 packages compatible; ASR, slide and ONNX speaker readiness true | Setup checks inspect local files/packages, not recognition quality |
| Website | Production build/lint pass; browser workflow passes at 360/390/960 px without page overflow or JS errors | Synthetic microphone and intercepted fixture responses |
| Browser features | Recording recovery, settings/profile, PPT/hints upload, name/role save/history, role labels in transcript, actual JSON influence keys, source evidence, slide links, printing/export and removed generative/search UI checked | Not a human usability study |
| Automatic real diarization | 90-second English AMI audio produced **8 clusters / 18 turns** in about 28 seconds | Demonstrates operation but also over-clustering; threshold is not calibrated; not a validated speaker count |
| Constrained real pipeline | Same real 90-second audio with an explicit **4-speaker constraint**: **4 participants, 23 transcript passages, 3 NLP events, 4 influence records, 2 generated validation slides and 3 confident slide links**, with **zero socket connections** | Not a WER/DER/alignment benchmark. No decisions in this short excerpt; zero contribution scores are legitimate. Slides are validation fixtures |
| Cached full pipeline rerun | 2.873 seconds | ASR/diarization checkpoints reused; do not present as cold processing speed |
| Mixed-text downstream integration | Five source-preserving mixed Hindi/English/Hinglish events, two participants, one decision, action candidate and contribution estimates | Audio/diarization mocked; actual NLP/decision/interaction/scoring modules run; no bilingual ASR accuracy claim |
| Real Hindi/English language smoke | Public Hindi and English speech examples detected as `hi` / `en`; a constructed 7.213-second Hindi-then-English clip retained 17 Devanagari words and 3 Latin words and was labelled possible mixing; zero socket connections | Concatenated language-ID examples, not a natural Hinglish meeting; no independent checked transcript/WER; observed recognition spelling errors are not corrected by script detection |
| Shared Android rule checks | JVM WAV/progress/Unicode/PPT and bilingual/negation checks pass after rule-bank export | This delivery does not add native Android diarization or PPT fusion |

No checked natural Hindi–English meeting recording/reference was supplied or found for a new WER test. It would be false to conclude that actual Hinglish transcription is accurate from text fixtures or English audio. The public speech examples came from the [maintainer language-identification sample archive](https://k2-fsa.github.io/sherpa/onnx/spoken-language-identification/pretrained_models.html). Recognition of both scripts shows operation, not correctness; the Hindi hypothesis contains spellings that warrant human review.

Use the existing [recording evaluator](../../scripts/evaluate_recordings.py) with consented real audio and independently corrected references. Keep Hindi/English script normalization consistent. The evaluator records WER; it does not validate decisions or influence.

Local evidence: `logs/report_scope_tests.log`, `report_scope_browser.log`, `report_scope_real_diarization.log`, `report_scope_real_pipeline.log`, `report_scope_setup.json`, `report_scope_public_languages.log`, and `report_scope_shared_android_rules.log`. Real/fixed transcript artifacts are under `data/processed/` and `outputs/reports/report_scope_*`. These generated artifacts are ignored by Git. Prior submitted documents and user audio were not deleted.

## Developer file map and reproduction

- [config.yaml](../../config/config.yaml), [requirements.txt](../../environment/requirements.txt), [requirements-lock.txt](../../environment/requirements-lock.txt): default local speaker backend and pinned runtime packages.
- [download_speaker_models.py](../../scripts/download_speaker_models.py): explicit public downloads, SHA-256 verification, bounded archive member extraction and provenance. Downloads are not performed during inference.
- [diarization.py](../../src/audio/diarization.py), [onnx_diarization.py](../../src/audio/onnx_diarization.py): local readiness, global voice clustering and CPU thread settings.
- [asr.py](../../src/audio/asr.py): observed chunk-language metadata and cache-version update; multilingual speech model unchanged.
- [language.py](../../src/meeting/language.py), [consistency.py](../../src/meeting/consistency.py): heuristic language cues and narrow slide-quantity review flags.
- [events.py](../../src/meeting/events.py), [language_rules.py](../../src/meeting/language_rules.py): Hinglish imperative task rule and its negation blocker.
- [influence.py](../../src/meeting/influence.py): complete attributed participant coverage and corrected explanation; original weights/features retained.
- [generator.py](../../src/report/generator.py), [exporter.py](../../src/report/exporter.py), [transcript_export.py](../../src/report/transcript_export.py): observed contribution roles, serialized research artifacts, numeric timestamp field and role-aware non-generative exports.
- [orchestrator.py](../../src/pipeline/orchestrator.py), [api.py](../../backend/api.py): real attribution status, explicit non-generative processing, owned queued speaker recovery and removed LLM/search operations.
- [App.jsx](../../frontend/src/App.jsx), [index.css](../../frontend/src/index.css): evidence-oriented tabs, role propagation, presentation/consistency views and minimal capture retained.
- [test_report_scope.py](../../tests/test_report_scope.py): ownership, obsolete-content suppression, mixed-event provenance/negation, zero observed contributions, serialized slide checks and safe role export.
- [test_browser_offline.cjs](../../scripts/test_browser_offline.cjs), [smoke_report_scope.py](../../scripts/smoke_report_scope.py): fixture UI and real offline integration checks.

Removed active sources: `frontend/src/MeetingNotes.jsx`, `src/meeting/local_notes.py`, `tests/test_local_notes.py`. API notes/chat routes are absent. Historical chapter descriptions remain labelled as snapshots; dead links to removed files are marked accordingly.

```bash
# Already installed/provisioned on this laptop; fresh installations use these explicit steps.
bash scripts/setup.sh
.venv/bin/python scripts/download_models.py --slides
.venv/bin/python scripts/download_speaker_models.py
.venv/bin/python scripts/validate_setup.py
bash scripts/start_app.sh

# Repeat meaningful checks.
OMP_NUM_THREADS=4 bash scripts/check.sh -q
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/test_browser_offline.cjs
OMP_NUM_THREADS=4 .venv/bin/python scripts/smoke_report_scope.py \
  --audio /path/to/real.wav --ppt /path/to/slides.pptx --speakers 4 --id new_validation
```

The speaker provisioning procedure follows the [official sherpa-onnx documentation](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html) and [maintainer's Python example](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/offline-speaker-diarization.py). Model/code licensing is separate from this application's code; consult the original model terms before redistribution. The supplied public segmentation archive and embedding file are pinned by SHA-256 in the provisioning script.

## What a journal paper can claim

The project now exposes a working integration of locally attributed transcripts, inherited multimodal alignment, deterministic event/decision/interaction analysis and explainable contribution scoring through editable participant views. It removes an unrelated generative assistant and makes implementation boundaries explicit.

This does not establish a new trained diarization model, a novel fusion equation, high bilingual accuracy, validated role recognition, correct semantic contradictions or superior influence rankings. Use the report's WER/DER/alignment/event/decision/lineage/rank-correlation metrics, controlled B1–B4 comparisons and human evaluation. Chapter 11 documents defects in the legacy evaluation runner; fixing the website does not fix those experiments or make earlier ablation labels valid. Research novelty must be framed and evaluated separately.
