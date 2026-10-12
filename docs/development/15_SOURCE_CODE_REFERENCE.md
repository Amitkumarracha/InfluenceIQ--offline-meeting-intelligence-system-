# Source reference and entry points

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

This index was generated from the inspected current Python AST. Names and line numbers locate implementation; they do not establish that docstrings or historical advertised capabilities are correct. Chapters 04–11 explain actual behavior and limitations. Full first-party non-Python filenames and hashes are in [14](../validation/14_FILE_BY_FILE_COMPARISON.md).

## Entry points to read first

`api.run_pipeline_background` → `src.audio.parts.decode_parts` → `src.pipeline.orchestrator.run_meeting` → `src.audio.asr.run_asr` → meeting analysis runners → report generator/exporter. Complete CLI: `scripts/process_meeting.py`. Independent-stage CLI: `scripts/run_pipeline.py`. Benchmark CLI: `scripts/benchmark_ami.py`.

## api.py

[Open source](../../backend/api.py) — Local accounts, owner-scoped meetings/media, durable queue, optional notes/Q&A and exports.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `redact_media_token` | 51 | function |
| `User` | 65 | class; data/container class |
| `Meeting` | 73 | class; data/container class |
| `job_path` | 86 | function |
| `job_state` | 90 | function |
| `run_pipeline_background` | 97 | function |
| `run_summary_background` | 135 | function |
| `lifespan` | 168 | async function |
| `get_db` | 200 | function |
| `get_current_user` | 205 | function |
| `access_response` | 218 | function |
| `UserLogin` | 224 | class; `normalize_email`, `password_bytes` |
| `UserCreate` | 244 | class; data/container class |
| `register` | 249 | function |
| `login` | 263 | function |
| `reset_disabled` | 272 | function |
| `health` | 277 | function |
| `analyze_meeting` | 301 | async function |
| `owned_meeting` | 374 | function |
| `get_meetings` | 382 | function |
| `search_meetings` | 388 | function |
| `get_meeting` | 398 | function |
| `meeting_audio` | 423 | function |
| `retry` | 440 | function |
| `NotesRequest` | 453 | class; data/container class |
| `generate_notes` | 458 | function |
| `QuestionRequest` | 477 | class; data/container class |
| `ask_meeting` | 483 | async function |
| `MeetingEdit` | 498 | class; data/container class |
| `edit_meeting` | 504 | function |
| `export_meeting` | 525 | function |

## create_test_samples.py

[Open source](../../scripts/create_test_samples.py) — Small synthetic test input generator; fixtures are not human speech ground truth.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## run_small_chunk.py

[Open source](../../archive/legacy_tools/run_small_chunk.py) — Retained historical stage-oriented batch audio runner.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `ensure_env` | 18 | function |
| `list_meeting_ids` | 36 | function |
| `run_meeting` | 48 | function |
| `main` | 64 | function |

## scripts/benchmark_ami.py

[Open source](../../scripts/benchmark_ami.py) — Reproducible AMI excerpt benchmark, using manual annotations as reference.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `normalize` | 19 | function |
| `main` | 24 | function |

## scripts/check_android_design.py

[Open source](../../scripts/check_android_design.py) — Read-only UI smoke check on an explicitly selected Android emulator.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `main` | 15 | function |

## scripts/download_models.py

[Open source](../../scripts/download_models.py) — One-time online provisioning. Meeting inference never downloads models.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `main` | 13 | function |

## scripts/evaluate_recordings.py

[Open source](../../scripts/evaluate_recordings.py) — Evaluate manually transcribed phone excerpts, grouped as Hindi/English/Hinglish.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `normalized` | 21 | function |
| `main` | 26 | function |

## scripts/export_event_rules.py

[Open source](../../scripts/export_event_rules.py) — Export our shared phrase rules for Android; no models/downloads needed.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `main` | 10 | function |

## scripts/generate_dummy_ppt.py

[Open source](../../scripts/generate_dummy_ppt.py) — Retained utility/generator; inspect source before running.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `generate_ppt` | 4 | function |

## scripts/generate_report.py

[Open source](../../scripts/generate_report.py) — Report generation script — Phase 13.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `parse_args` | 27 | function |
| `main` | 47 | function |

## scripts/generate_test_audio.py

[Open source](../../scripts/generate_test_audio.py) — Generate a short synthetic test audio file for pipeline validation.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `main` | 18 | function |

## scripts/generate_test_meeting.py

[Open source](../../scripts/generate_test_meeting.py) — Retained utility/generator; inspect source before running.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `generate_ppt` | 7 | function |
| `generate_audio` | 41 | function |

## scripts/prepare_batch_data.py

[Open source](../../scripts/prepare_batch_data.py) — Retained utility/generator; inspect source before running.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `prepare_audio` | 7 | function |
| `prepare_ppts` | 22 | function |

## scripts/process_meeting.py

[Open source](../../scripts/process_meeting.py) — Run every stage with resumable ASR; no server is needed.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## scripts/reset_password.py

[Open source](../../scripts/reset_password.py) — Local recovery only: requires access to the laptop's project and database.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## scripts/run_evaluation.py

[Open source](../../scripts/run_evaluation.py) — Evaluation script — Phase 12.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `parse_args` | 54 | function |
| `_resolve_paths` | 90 | function |
| `_load_annotations` | 104 | function |
| `main` | 119 | function |

## scripts/run_pipeline.py

[Open source](../../scripts/run_pipeline.py) — Entry point for the meeting intelligence pipeline.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `parse_args` | 46 | function |
| `run_ppt_pipeline` | 126 | function |
| `run_influence_pipeline` | 197 | function |
| `run_interaction_pipeline` | 248 | function |
| `run_decision_pipeline` | 298 | function |
| `run_event_pipeline` | 340 | function |
| `run_alignment_pipeline` | 391 | function |
| `run_audio_pipeline` | 433 | function |
| `main` | 536 | function |

## scripts/smoke_long_offline.py

[Open source](../../scripts/smoke_long_offline.py) — Long-duration regression: two hours of silence followed by real speech.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `main` | 18 | function |

## scripts/validate_setup.py

[Open source](../../scripts/validate_setup.py) — Inspect local readiness without downloading models or exposing credentials.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `main` | 12 | function |

## src/__init__.py

[Open source](../../src/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/audio/__init__.py

[Open source](../../src/audio/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/audio/asr.py

[Open source](../../src/audio/asr.py) — Chunked local Whisper ASR, word-based speaker assignment, quality diagnostics and content-key recovery.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `TranscriptSegment` | 34 | class; data/container class |
| `TranscriptResult` | 46 | class; data/container class |
| `_preload_cuda_libraries` | 63 | function |
| `_load_whisper_model` | 85 | function |
| `compute_overlap` | 139 | function |
| `attribute_speaker` | 149 | function |
| `_load_diarization_json` | 189 | function |
| `run_asr` | 196 | function |
| `_save_json` | 413 | function |
| `_save_txt` | 428 | function |
| `_fmt_ts` | 450 | function |
| `_deserialise_result` | 457 | function |

## src/audio/diarization.py

[Open source](../../src/audio/diarization.py) — Optional pyannote/ONNX selection, cached speaker intervals and cluster normalization.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `DiarizationSegment` | 17 | class; data/container class |
| `DiarizationResult` | 25 | class; data/container class |
| `_load_pipeline` | 32 | function |
| `merge_adjacent_segments` | 61 | function |
| `normalize_speaker_labels` | 96 | function |
| `run_diarization` | 122 | function |

## src/audio/onnx_diarization.py

[Open source](../../src/audio/onnx_diarization.py) — Optional manually provisioned sherpa-onnx full-recording adapter; not evaluated on real local models.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `model_paths` | 7 | function |
| `diarize` | 21 | function |

## src/audio/parts.py

[Open source](../../src/audio/parts.py) — Chronological upload decoding to one durable PCM recording with input/output hash validation.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `decode_parts` | 10 | function |

## src/audio/preprocess.py

[Open source](../../src/audio/preprocess.py) — Audio probing and atomic FFmpeg conversion/reuse of normalized PCM.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `AudioMetadata` | 12 | class; data/container class |
| `probe_audio` | 21 | function |
| `preprocess_audio` | 37 | function |

## src/audio/vad.py

[Open source](../../src/audio/vad.py) — Packaged Silero detection in bounded overlapping blocks; used by the staged audio runner.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `SpeechSegment` | 12 | class; data/container class |
| `_load_silero_vad` | 18 | function |
| `run_vad` | 23 | function |

## src/evaluation/__init__.py

[Open source](../../src/evaluation/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/evaluation/ablation.py

[Open source](../../src/evaluation/ablation.py) — Inherited influence-feature weight removal, not genuine upstream fusion ablation.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `run_ablation` | 102 | function |
| `run_all_ablations` | 185 | function |
| `ablation_results_to_dict` | 220 | function |

## src/evaluation/baselines.py

[Open source](../../src/evaluation/baselines.py) — Inherited event-subset baselines; publication limitations documented in chapter 11.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_max_norm` | 42 | function |
| `_decision_event_ids` | 54 | function |
| `baseline_speaking_time` | 73 | function |
| `baseline_speaking_time_turns` | 106 | function |
| `baseline_decision_event_count` | 140 | function |
| `baseline_decision_evidence_count` | 172 | function |
| `baseline_transcript_only` | 214 | function |
| `baseline_audio_ppt_no_decision` | 251 | function |
| `build_comparison_table` | 294 | function |

## src/evaluation/metrics.py

[Open source](../../src/evaluation/metrics.py) — WER, corrected permutation-aware DER, heuristic event/decision/alignment matching and rank/resource metrics.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_no_gt` | 55 | function |
| `_levenshtein` | 64 | function |
| `calculate_wer` | 90 | function |
| `calculate_der` | 142 | function |
| `_prf` | 211 | function |
| `evaluate_alignment` | 228 | function |
| `evaluate_events` | 293 | function |
| `evaluate_decisions` | 371 | function |
| `evaluate_decision_lineage` | 441 | function |
| `_spearman` | 503 | function |
| `_kendall_tau` | 529 | function |
| `evaluate_influence_ranking` | 555 | function |
| `calculate_efficiency` | 626 | function |
| `build_eval_metadata` | 678 | function |

## src/fusion/__init__.py

[Open source](../../src/fusion/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/fusion/lexical_alignment.py

[Open source](../../src/fusion/lexical_alignment.py) — Sparse Unicode TF-IDF content scorer; alternative to the neural content score.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `TfidfIndex` | 7 | class; `__init__`, `vector`, `scores` |

## src/fusion/multimodal_representation.py

[Open source](../../src/fusion/multimodal_representation.py) — Candidate filtering, weighted scoring, abstention, joined records and alignment/multimodal JSON.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `SlideCandidate` | 53 | class; data/container class |
| `AlignmentResult` | 63 | class; data/container class |
| `MultimodalSegment` | 75 | class; data/container class |
| `label_confidence` | 96 | function |
| `combine_scores` | 109 | function |
| `align_segment` | 145 | function |
| `run_alignment` | 243 | function |
| `_candidate_to_dict` | 409 | function |
| `_alignment_to_dict` | 419 | function |
| `_multimodal_to_dict` | 431 | function |
| `_save_alignment_json` | 447 | function |
| `_save_multimodal_json` | 464 | function |

## src/fusion/semantic_alignment.py

[Open source](../../src/fusion/semantic_alignment.py) — Transcript sentence embedding and normalized cosine matching to slide embeddings; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `SemanticScore` | 27 | class; data/container class |
| `_l2_normalise` | 37 | function |
| `cosine_similarity_matrix` | 44 | function |
| `embed_text` | 64 | function |
| `compute_semantic_scores` | 100 | function |
| `load_embedding_model` | 143 | function |

## src/fusion/temporal_alignment.py

[Open source](../../src/fusion/temporal_alignment.py) — Optional slide-time overlap; None for unavailable timing; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `SlideTimingInfo` | 28 | class; `has_timing` |
| `TemporalScore` | 48 | class; data/container class |
| `compute_overlap_seconds` | 63 | function |
| `temporal_score_for_slide` | 73 | function |
| `compute_temporal_scores` | 122 | function |
| `has_any_timing` | 139 | function |
| `timing_from_slide_dict` | 148 | function |
| `timings_from_presentation_dict` | 162 | function |

## src/meeting/__init__.py

[Open source](../../src/meeting/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/meeting/decisions.py

[Open source](../../src/meeting/decisions.py) — Temporal anchors/clusters, status/roles, source IDs, lineage and graph serialization.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `LineageEdge` | 118 | class; data/container class |
| `ParticipantRole` | 126 | class; data/container class |
| `EventImpact` | 133 | class; data/container class |
| `Decision` | 140 | class; data/container class |
| `DecisionResult` | 166 | class; `by_status`, `count_by_status` |
| `_build_networkx_graph` | 185 | function |
| `_graph_to_dict` | 222 | function |
| `_topic_from_text` | 240 | function |
| `_event_index` | 248 | function |
| `_evidence_for_event` | 252 | function |
| `_events_in_window` | 260 | function |
| `_classify_impact` | 274 | function |
| `_infer_status` | 292 | function |
| `_build_lineage` | 321 | function |
| `reconstruct_decisions` | 389 | function |
| `_decision_to_dict` | 625 | function |
| `save_decisions_json` | 655 | function |
| `save_decision_graph_json` | 668 | function |
| `load_decisions_json` | 689 | function |
| `run_decision_reconstruction` | 737 | function |

## src/meeting/events.py

[Open source](../../src/meeting/events.py) — Single highest-scoring English/Hindi/Hinglish candidate type per transcript segment.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `get_active_event_types` | 71 | function |
| `MeetingEvent` | 84 | class; data/container class |
| `EventExtractionResult` | 98 | class; `by_type`, `count_by_type` |
| `BaseEventExtractor` | 117 | class; `extract` |
| `_match_event_type` | 263 | function |
| `KeywordEventExtractor` | 305 | class; `__init__`, `extract` |
| `load_multimodal_segments` | 379 | function |
| `save_events_json` | 394 | function |
| `load_events_json` | 410 | function |
| `_event_to_dict` | 433 | function |
| `run_event_extraction` | 451 | function |

## src/meeting/evidence.py

[Open source](../../src/meeting/evidence.py) — Nearest suitable preceding event and slide-grounding relation heuristics; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `EvidenceRelation` | 95 | class; data/container class |
| `EvidenceExtractionResult` | 106 | class; `by_relationship` |
| `_find_preceding_event` | 138 | function |
| `extract_evidence` | 159 | function |
| `save_evidence_json` | 251 | function |
| `load_evidence_json` | 267 | function |
| `_relation_to_dict` | 290 | function |
| `run_evidence_extraction` | 305 | function |

## src/meeting/influence.py

[Open source](../../src/meeting/influence.py) — Seven-feature normalized weighted score; UNKNOWN exclusion and main-runner transcript baselines.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `FeatureVector` | 117 | class; `to_dict` |
| `DecisionContribution` | 155 | class; data/container class |
| `ParticipantInfluence` | 164 | class; data/container class |
| `BaselineScores` | 182 | class; data/container class |
| `InfluenceResult` | 195 | class; `by_rank`, `for_participant` |
| `_load_weights` | 213 | function |
| `_max_normalise` | 245 | function |
| `_normalise_feature_across_participants` | 257 | function |
| `_event_index` | 270 | function |
| `_decision_event_ids` | 274 | function |
| `_revision_event_ids` | 290 | function |
| `_objection_triggers_revision` | 294 | function |
| `_evidence_contributes_to_revision` | 317 | function |
| `extract_features` | 334 | function |
| `extract_baselines` | 471 | function |
| `compute_decision_contributions` | 553 | function |
| `_generate_explanation` | 624 | function |
| `compute_influence` | 704 | function |
| `_method_meta` | 854 | function |
| `_pi_to_dict` | 871 | function |
| `_baseline_to_dict` | 893 | function |
| `save_influence_json` | 906 | function |
| `save_baselines_json` | 920 | function |
| `load_influence_json` | 937 | function |
| `run_influence_analysis` | 979 | function |

## src/meeting/interaction.py

[Open source](../../src/meeting/interaction.py) — Evidence/lineage/reactive-event interaction passes and participant statistics.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `Interaction` | 107 | class; data/container class |
| `ParticipantStats` | 123 | class; data/container class |
| `InteractionResult` | 138 | class; `by_type`, `count_by_type`, `decision_linked` |
| `_make_event_index` | 162 | function |
| `_find_preceding_targetable` | 166 | function |
| `_decision_for_event` | 191 | function |
| `extract_interactions` | 215 | function |
| `build_participant_graph` | 385 | function |
| `_participant_graph_to_dict` | 424 | function |
| `_interaction_to_dict` | 451 | function |
| `_stats_to_dict` | 467 | function |
| `save_interactions_json` | 479 | function |
| `save_interaction_graph_json` | 495 | function |
| `load_interactions_json` | 512 | function |
| `run_interaction_analysis` | 561 | function |

## src/meeting/language_rules.py

[Open source](../../src/meeting/language_rules.py) — Question/negation blocker phrase definitions shared with exported Android assets.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/meeting/local_notes.py

Open source (historical; removed in chapter 18) — Loopback local Ollama, structured draft notes, literal source validation, model/transcript digest checkpoints.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_request` | 38 | function |
| `local_models` | 48 | function |
| `require_local_model` | 55 | function |
| `_chat` | 67 | function |
| `transcript_chunks` | 89 | function |
| `checked_items` | 105 | function |
| `summarize` | 133 | function |
| `ask` | 168 | function |

## src/meeting/search.py

[Open source](../../src/meeting/search.py) — Unicode lexical ranking, phrase boost and neighboring transcript context.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `tokens` | 9 | function |
| `search_segments` | 13 | function |

## src/pipeline/__init__.py

[Open source](../../src/pipeline/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/pipeline/orchestrator.py

[Open source](../../src/pipeline/orchestrator.py) — Complete shared audio-to-report workflow, optional slides/speakers, progress and preview callbacks.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `run_meeting` | 10 | function |

## src/ppt/__init__.py

[Open source](../../src/ppt/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/ppt/embeddings.py

[Open source](../../src/ppt/embeddings.py) — Slide-text construction, local sentence embedding generation and NPY persistence; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `build_slide_text` | 36 | function |
| `generate_embeddings` | 65 | function |
| `save_embeddings` | 130 | function |
| `load_embeddings` | 137 | function |
| `get_slide_embedding` | 142 | function |

## src/ppt/extract.py

[Open source](../../src/ppt/extract.py) — Native PPTX text/tables/notes/image/shape metadata and slide/presentation data classes; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `TableData` | 30 | class; data/container class |
| `SlideData` | 36 | class; data/container class |
| `PresentationData` | 48 | class; data/container class |
| `BaseSlideExtractor` | 60 | class; `validate`, `extract` |
| `PPTXExtractor` | 82 | class; `__init__`, `validate`, `extract`, `_get_title`, `_get_text_blocks`, `_get_tables`, `_get_notes`, `_get_metadata` |
| `_safe_id` | 316 | function |
| `derive_meeting_id` | 322 | function |

## src/ppt/features.py

[Open source](../../src/ppt/features.py) — Structural metadata feature summaries, not computer vision; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `SlideFeatures` | 28 | class; data/container class |
| `extract_slide_features` | 50 | function |
| `extract_presentation_features` | 75 | function |
| `presentation_feature_summary` | 80 | function |

## src/ppt/io.py

[Open source](../../src/ppt/io.py) — Slide/presentation JSON serialization; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_table_to_dict` | 22 | function |
| `_slide_to_dict` | 26 | function |
| `presentation_to_dict` | 38 | function |
| `save_presentation_json` | 47 | function |
| `load_presentation_json` | 60 | function |

## src/ppt/ocr.py

[Open source](../../src/ppt/ocr.py) — OCR interface stub; availability always false; no OCR engine implemented.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `OCRResult` | 37 | class; data/container class |
| `extract_ocr_text` | 50 | function |
| `is_ocr_enabled` | 97 | function |
| `_ocr_available` | 106 | function |
| `_ocr_image_bytes` | 117 | function |

## src/report/__init__.py

[Open source](../../src/report/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/report/exporter.py

[Open source](../../src/report/exporter.py) — Pipeline JSON/Markdown/HTML/section CSV outputs.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_overview_to_dict` | 38 | function |
| `_participant_to_dict` | 52 | function |
| `_decision_to_dict` | 67 | function |
| `_action_to_dict` | 89 | function |
| `_influence_to_dict` | 100 | function |
| `export_json` | 114 | function |
| `_md_table` | 143 | function |
| `export_markdown` | 152 | function |
| `_h` | 464 | function |
| `_html_table` | 469 | function |
| `export_html` | 494 | function |
| `export_csv_participants` | 693 | function |
| `export_csv_decisions` | 716 | function |
| `export_csv_influence` | 739 | function |
| `export_csv_action_items` | 762 | function |
| `export_all` | 785 | function |

## src/report/generator.py

[Open source](../../src/report/generator.py) — Report sections, source traceability and full-transcript participant/duration statistics.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `MeetingOverview` | 48 | class; data/container class |
| `ParticipantSummary` | 60 | class; data/container class |
| `DecisionReport` | 74 | class; data/container class |
| `ActionItem` | 95 | class; data/container class |
| `InfluenceReport` | 105 | class; data/container class |
| `MeetingReport` | 118 | class; data/container class |
| `_fmt_ts` | 142 | function |
| `_build_lineage_text` | 155 | function |
| `_load_json` | 187 | function |
| `_resolve_input_paths` | 198 | function |
| `_build_overview` | 224 | function |
| `_build_participants` | 259 | function |
| `_build_executive_summary` | 339 | function |
| `_build_slide_discussions` | 384 | function |
| `_build_proposals` | 417 | function |
| `_build_evidence_items` | 449 | function |
| `_build_decisions` | 480 | function |
| `_build_action_items` | 513 | function |
| `_build_interactions` | 547 | function |
| `_build_influence` | 580 | function |
| `_build_influence_vs_speaking` | 599 | function |
| `_build_traceability` | 629 | function |
| `_build_evaluation` | 666 | function |
| `_build_ablation` | 689 | function |
| `generate_report` | 712 | function |

## src/report/transcript_export.py

[Open source](../../src/report/transcript_export.py) — Saved-report full transcript/notes exports to MD/TXT/SRT/VTT/transcript CSV.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `stamp` | 6 | function |
| `render_export` | 11 | function |

## src/utils/__init__.py

[Open source](../../src/utils/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## src/utils/cache.py

[Open source](../../src/utils/cache.py) — SHA-256 fingerprint, cache-key reads, atomic fsync/replace JSON.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `fingerprint` | 9 | function |
| `atomic_json` | 18 | function |
| `read_cache` | 32 | function |

## src/utils/checkpointing.py

[Open source](../../src/utils/checkpointing.py) — Per-meeting resume state and stage-completion markers.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `ensure_meeting_checkpoint_dir` | 14 | function |
| `load_resume_state` | 22 | function |
| `save_resume_state` | 50 | function |
| `mark_stage_complete` | 79 | function |

## src/utils/config.py

[Open source](../../src/utils/config.py) — Project config/env loader, cached YAML, selected overrides and offline model defaults.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `load_env` | 15 | function |
| `load_config` | 43 | function |
| `get` | 53 | function |

## src/utils/logging.py

[Open source](../../src/utils/logging.py) — Configured pipeline logger; inherited.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `get_logger` | 7 | function |

## src/utils/paths.py

[Open source](../../src/utils/paths.py) — Project-relative raw/processed audio path helpers.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `get_processed_audio_dir` | 11 | function |
| `get_raw_audio_dir` | 18 | function |

## src/utils/text.py

[Open source](../../src/utils/text.py) — Unicode NFKC/casefold and letter/number/combining-mark tokenization.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `normalize_text` | 5 | function |
| `words` | 9 | function |

## tests/__init__.py

[Open source](../../tests/__init__.py) — Package initialization.

No top-level function/class definitions; inspect module body/constants/CLI wiring.

## tests/test_alignment.py

[Open source](../../tests/test_alignment.py) — Regression suite: test_alignment.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_make_slide_ids` | 21 | function |
| `_make_random_embeddings` | 25 | function |
| `_make_transcript_segment` | 30 | function |
| `TestTemporalOverlap` | 51 | class; `test_full_overlap`, `test_partial_overlap`, `test_no_overlap`, `test_segment_contained_in_slide`, `test_slide_contained_in_segment`, `test_adjacent_no_overlap` |
| `TestTemporalScore` | 81 | class; `test_score_full_overlap`, `test_score_half_overlap`, `test_score_no_timing`, `test_score_clipped_at_one` |
| `TestNoTiming` | 114 | class; `test_has_any_timing_false`, `test_has_any_timing_true`, `test_compute_temporal_scores_all_none` |
| `TestCosineSimilarity` | 140 | class; `test_identical_vectors`, `test_orthogonal_vectors`, `test_zero_query_vector`, `test_batch_scores` |
| `TestCombineScores` | 178 | class; `test_equal_weights`, `test_temporal_only_weight`, `test_semantic_only_weight`, `test_no_temporal_falls_back_to_semantic`, `test_no_temporal_zero_semantic` |
| `TestConfidenceLabel` | 210 | class; `test_high`, `test_medium`, `test_low`, `test_boundary_is_medium` |
| `TestTopK` | 232 | class; `_run_align`, `test_top_k_respected`, `test_top_k_one`, `test_candidates_sorted_descending` |
| `TestNoConfidentSlide` | 288 | class; `test_below_threshold_gives_no_slide`, `test_above_threshold_gives_slide` |
| `TestMultimodalRepresentation` | 353 | class; `test_structure`, `test_no_slide_multimodal` |
| `TestInvalidInputs` | 410 | class; `test_missing_transcript`, `test_missing_slides`, `test_missing_embeddings`, `test_semantic_scores_dim_mismatch` |
| `TestEdgeCases` | 467 | class; `_stub_align`, `test_empty_segment_text`, `test_single_slide`, `test_many_slides`, `test_timing_info_from_dict`, `test_timing_info_missing_keys`, `test_empty_slide_text_embed` |
| `TestAlignmentSerialisation` | 535 | class; `test_alignment_to_dict`, `test_multimodal_to_dict` |

## tests/test_api.py

[Open source](../../tests/test_api.py) — Regression suite: test_api.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `api_client` | 15 | function |
| `register` | 29 | function |
| `test_private_audio_and_cross_account_access` | 35 | function |
| `test_rejects_invalid_and_oversized_uploads` | 61 | function |
| `test_password_reset_never_returns_takeover_token` | 71 | function |
| `test_processing_preview_is_private` | 80 | function |

## tests/test_audio.py

[Open source](../../tests/test_audio.py) — Regression suite: test_audio.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_make_synthetic_wav` | 45 | function |
| `_make_mock_diarization` | 57 | function |
| `TestPreprocessAudio` | 71 | class; `test_invalid_path_raises`, `test_returns_correct_types`, `test_output_file_exists`, `test_output_is_16khz`, `test_output_is_mono`, `test_metadata_duration`, `test_original_file_untouched` |
| `TestRunVAD` | 119 | class; `test_invalid_path_raises`, `test_returns_segments_and_path`, `test_json_output_exists`, `test_json_structure`, `test_segment_structure`, `test_segment_ids_sequential`, `test_speech_segment_type` |
| `TestDiarizationHelpers` | 177 | class; `test_merge_adjacent_segments_same_speaker`, `test_merge_adjacent_segments_large_gap_not_merged`, `test_merge_adjacent_segments_different_speakers_not_merged`, `test_merge_adjacent_segments_empty`, `test_normalize_speaker_labels` |
| `TestRunDiarization` | 217 | class; `test_invalid_path_raises`, `test_missing_hf_token_raises`, `test_returns_result_and_path`, `test_speaker_labels_canonical`, `test_segments_ordered_by_start`, `test_segment_ids_sequential`, `test_json_output_structure`, `test_segment_end_gt_start`, `test_diarization_segment_type`, `test_empty_diarization_handles_gracefully` |
| `TestASRHelpers` | 343 | class; `test_compute_overlap_full`, `test_compute_overlap_partial`, `test_compute_overlap_none`, `test_compute_overlap_touching`, `test_attribute_speaker_best_match`, `test_attribute_speaker_unknown_below_threshold`, `test_attribute_speaker_empty_diarization`, `test_attribute_speaker_exact_threshold` |
| `_make_mock_asr_segment` | 388 | function |
| `_make_mock_transcription_info` | 398 | function |
| `_write_diarization_json` | 405 | function |
| `TestRunASR` | 421 | class; `test_missing_audio_raises`, `test_missing_diarization_raises`, `test_returns_result_and_paths`, `test_speaker_attribution_correct`, `test_unknown_speaker_when_no_overlap`, `test_segment_ids_sequential`, `test_confidence_attached`, `test_json_output_structure`, `test_caching_skips_model_reload`, `test_txt_output_contains_speaker_and_text`, `test_load_whisper_model_falls_back_to_cpu_on_missing_cuda_library` |

## tests/test_efficiency.py

[Open source](../../tests/test_efficiency.py) — Regression suite: test_efficiency.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `test_decode_parts_is_ordered_atomic_and_reuses_verified_recording` | 18 | function |
| `test_hindi_combining_marks_remain_whole_words_and_retrieval_does_not_translate` | 45 | function |
| `test_negation_and_questions_do_not_become_confirmations` | 66 | function |
| `test_more_hinglish_forms_keep_original_source` | 81 | function |
| `test_silence_does_not_load_whisper_and_previews_have_stable_ids` | 86 | function |
| `test_tfidf_alignment_works_without_embedding_weights` | 108 | function |
| `test_onnx_adapter_keeps_global_speaker_labels_and_cache` | 123 | function |
| `test_graph_exports_preserve_all_edges_without_networkx` | 153 | function |
| `test_phone_evaluation_groups_human_references_without_changing_scripts` | 172 | function |

## tests/test_evaluation.py

[Open source](../../tests/test_evaluation.py) — Regression suite: test_evaluation.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_ev` | 65 | function |
| `_pipeline_data` | 88 | function |
| `TestWER` | 109 | class; `test_perfect_match`, `test_full_substitution`, `test_deletion`, `test_insertion`, `test_no_ground_truth_returns_unavailable`, `test_empty_ground_truth_returns_unavailable`, `test_empty_hypothesis`, `test_case_insensitive`, `test_wer_never_fabricated` |
| `TestDER` | 158 | class; `_seg`, `test_perfect_match`, `test_no_ground_truth_returns_unavailable`, `test_empty_ground_truth_returns_unavailable`, `test_speaker_error_detected`, `test_missed_speech_detected`, `test_result_structure` |
| `TestPRF` | 204 | class; `test_perfect`, `test_all_wrong`, `test_zero_tp_fp`, `test_values_in_range` |
| `TestAlignmentEvaluation` | 233 | class; `test_perfect_alignment`, `test_no_ground_truth`, `test_wrong_slide_reduces_f1`, `test_missing_prediction`, `test_empty_predictions` |
| `TestEventEvaluation` | 270 | class; `test_perfect_event_match`, `test_no_ground_truth`, `test_timestamp_tolerance_matching`, `test_timestamp_outside_tolerance_misses`, `test_wrong_type_no_match`, `test_per_type_breakdown` |
| `TestDecisionEvaluation` | 318 | class; `test_perfect_decision_match`, `test_no_ground_truth`, `test_topic_jaccard_matching`, `test_no_match_returns_zero_f1` |
| `TestLineageEvaluation` | 348 | class; `test_perfect_lineage_match`, `test_no_ground_truth`, `test_missing_edge_reduces_recall`, `test_extra_edge_reduces_precision` |
| `TestInfluenceRankingEvaluation` | 383 | class; `test_perfect_agreement`, `test_reversed_ranking`, `test_no_human_ranking_returns_unavailable`, `test_empty_human_ranking_returns_unavailable`, `test_result_structure`, `test_note_warns_against_fabrication` |
| `TestRankCorrelations` | 422 | class; `test_spearman_perfect`, `test_spearman_reversed`, `test_spearman_single_pair_nan`, `test_kendall_perfect`, `test_kendall_reversed` |
| `TestEfficiency` | 444 | class; `test_basic_timing`, `test_no_audio_duration_rtf_none`, `test_empty_timings_returns_error`, `test_rtf_less_than_one_faster_than_realtime`, `test_stage_timings_preserved` |
| `TestBaselines` | 475 | class; `test_max_norm_safety`, `test_max_norm_correct`, `test_b1_speaking_time`, `test_b2_speaking_time_turns`, `test_b3_decision_event_count`, `test_b4_decision_evidence_count`, `test_b5_transcript_only`, `test_b6_audio_ppt_no_decision`, `test_speaking_time_not_same_as_decision_linked` |
| `TestComparisonTable` | 541 | class; `test_table_structure`, `test_no_fabricated_values_without_human_ranking`, `test_proposed_method_present_when_scores_provided` |
| `TestAblation` | 575 | class; `test_ablation_configs_complete`, `test_run_all_ablations_produces_one_result_per_config`, `test_ablation_result_structure`, `test_a1_full_system_has_nonzero_scores`, `test_metrics_none_without_human_ranking`, `test_ablation_dict_serialisable`, `test_ablation_uses_same_data` |
| `TestMissingGroundTruth` | 630 | class; `test_wer_no_gt`, `test_der_no_gt`, `test_alignment_no_gt`, `test_events_no_gt`, `test_decisions_no_gt`, `test_lineage_no_gt`, `test_influence_no_gt`, `test_no_gt_response_has_metric_field` |
| `TestReproducibilityMetadata` | 679 | class; `test_metadata_structure`, `test_no_secrets_in_metadata` |
| `TestEvaluationIO` | 698 | class; `test_save_and_load_metrics_json`, `test_comparison_csv_structure` |

## tests/test_laptop_workflow.py

[Open source](../../tests/test_laptop_workflow.py) — Regression suite: test_laptop_workflow.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `test_word_level_turns_and_changed_input_invalidates_cache` | 15 | function |
| `test_interrupted_chunk_resume` | 38 | function |
| `test_attribution_sums_split_turns_and_abstains_on_overlap` | 62 | function |
| `test_bilingual_event_sources_preserved` | 76 | function |
| `test_report_counts_full_transcript_not_only_keyword_events` | 85 | function |
| `test_der_is_invariant_to_cluster_names_and_supports_overlap` | 97 | function |
| `test_influence_baselines_include_speech_without_events` | 103 | function |
| `test_language_detection_respects_configured_meeting_languages` | 115 | function |

## tests/test_local_notes.py

Open source (historical; removed in chapter 18) — Regression suite: test_local_notes.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `segment` | 17 | function |
| `item` | 21 | function |
| `test_invalid_citations_and_invented_owners_are_rejected` | 25 | function |
| `test_unicode_long_turns_fit_context_and_preserve_every_character` | 36 | function |
| `test_notes_resume_all_parts_and_invalidate_changed_model` | 45 | function |
| `test_cloud_aliases_never_receive_transcript` | 72 | function |
| `test_search_keeps_neighbours_and_no_model_fallback` | 89 | function |
| `test_exports_keep_late_meeting_times_names_and_csv_safety` | 99 | function |
| `test_asr_per_meeting_hints_cache_and_progress` | 111 | function |
| `test_api_notes_search_edits_and_exports_are_owned` | 130 | function |
| `test_api_validates_persisted_meeting_options` | 160 | function |

## tests/test_meeting.py

[Open source](../../tests/test_meeting.py) — Regression suite: test_meeting.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_seg` | 40 | function |
| `_event` | 59 | function |
| `TestEventObject` | 87 | class; `test_fields_preserved`, `test_null_slide_allowed`, `test_null_confidence_allowed` |
| `TestEventTypes` | 111 | class; `test_all_taxonomy_types_present`, `test_get_active_types_returns_list` |
| `TestKeywordExtractor` | 132 | class; `_extract`, `test_proposal_detected`, `test_question_detected`, `test_agreement_detected`, `test_disagreement_detected`, `test_evidence_detected`, `test_action_item_detected`, `test_empty_text_skipped`, `test_no_match_skipped`, `test_meeting_id_preserved` |
| `TestTraceability` | 190 | class; `test_speaker_preserved`, `test_timestamps_preserved`, `test_source_segment_id_preserved`, `test_slide_id_preserved`, `test_no_slide_sentinel_becomes_none` |
| `TestExtractionResult` | 235 | class; `test_by_type`, `test_count_by_type` |
| `TestEvidenceStructure` | 263 | class; `test_relation_fields`, `test_null_confidence_allowed`, `test_by_relationship` |
| `TestEvidenceExtraction` | 295 | class; `_events`, `test_slide_grounding_creates_supports`, `test_objection_creates_contradicts`, `test_agreement_creates_supports`, `test_revision_creates_modifies`, `test_clarification_creates_clarifies`, `test_window_prevents_distant_link`, `test_no_events_no_relations` |
| `TestSerialisationEvents` | 384 | class; `test_event_to_dict_round_trip`, `test_save_and_load_events`, `test_events_json_structure` |
| `TestSerialisationEvidence` | 416 | class; `test_relation_to_dict_round_trip`, `test_save_and_load_evidence`, `test_evidence_json_structure` |
| `TestInvalidInputs` | 452 | class; `test_missing_events_file`, `test_missing_multimodal_file`, `test_extractor_handles_missing_text_key`, `test_invalid_event_type_not_fabricated` |
| `TestRunners` | 482 | class; `_write_multimodal`, `test_run_event_extraction_creates_file`, `test_run_evidence_extraction_creates_file`, `test_full_traceability_chain` |
| `_make_event` | 585 | function |
| `_full_chain` | 608 | function |
| `TestDecisionObject` | 630 | class; `test_decision_fields`, `test_decision_statuses_complete`, `test_lineage_edge_fields`, `test_event_impact_fields`, `test_participant_role_fields` |
| `TestStatusInference` | 679 | class; `_events_of_types`, `test_confirmed_with_decision`, `test_probable_with_agreement_only`, `test_unresolved_proposal_only`, `test_conflicting_multiple_proposals_with_objection` |
| `TestImpactClassification` | 707 | class; `test_proposal_directly_relevant`, `test_final_decision_directly_relevant`, `test_revision_directly_relevant`, `test_objection_indirectly_relevant`, `test_question_contextual`, `test_action_item_unresolved` |
| `TestFullChainReconstruction` | 737 | class; `test_decision_detected`, `test_confirmed_status`, `test_proposal_preserved`, `test_final_decision_preserved`, `test_revisions_collected`, `test_agreements_collected`, `test_participants_extracted`, `test_slide_grounding_preserved`, `test_supporting_segments_preserved`, `test_lineage_edges_present` |
| `TestUncertaintyHandling` | 810 | class; `test_unresolved_proposal_no_agreement`, `test_require_final_decision_skips_agreement_only`, `test_no_events_no_decisions`, `test_event_id_traceability` |
| `TestParticipantRoles` | 850 | class; `test_proposer_role`, `test_final_decision_maker_role`, `test_no_organisational_roles` |
| `TestDecisionSerialisation` | 878 | class; `test_save_and_load_decisions`, `test_decisions_json_structure`, `test_graph_json_structure`, `test_json_round_trip_lineage` |
| `TestDecisionRunner` | 935 | class; `_write_json`, `test_runner_creates_output_files`, `test_runner_missing_events_raises`, `test_runner_missing_evidence_raises` |
| `_make_interaction` | 1008 | function |
| `_interaction_chain` | 1035 | function |
| `TestInteractionObject` | 1069 | class; `test_fields_preserved`, `test_null_target_allowed`, `test_null_related_decision_allowed`, `test_null_slide_allowed` |
| `TestInteractionTypes` | 1096 | class; `test_all_types_present`, `test_interaction_type_valid_in_make_interaction` |
| `TestSourceTargetAssignment` | 1114 | class; `test_objection_source_is_objector`, `test_agreement_source_is_agreer`, `test_no_self_interaction`, `test_unknown_target_is_none_not_fabricated` |
| `TestTemporalWindowFiltering` | 1156 | class; `test_events_within_window_linked`, `test_events_outside_window_not_linked_pass3` |
| `TestInteractionTypeDetection` | 1189 | class; `test_objection_relationship_detected`, `test_support_relationship_detected`, `test_agreement_relationship_detected`, `test_response_or_reference_detected` |
| `TestDecisionLinkedInteractions` | 1219 | class; `test_some_interactions_linked_to_decision`, `test_decision_id_preserved`, `test_count_by_type_returns_dict` |
| `TestSlideLinkedInteractions` | 1248 | class; `test_slide_id_preserved_when_available`, `test_no_forced_slide_when_absent` |
| `TestParticipantGraph` | 1269 | class; `test_graph_nodes_are_speakers`, `test_graph_edges_represent_interactions`, `test_graph_node_stats_are_interaction_counts_not_influence` |
| `TestParticipantStats` | 1304 | class; `test_stats_produced_for_all_speakers`, `test_initiated_plus_received_consistent`, `test_type_counts_sum_to_initiated`, `test_stats_not_labelled_influence` |
| `TestInteractionSerialisation` | 1336 | class; `test_save_and_load_interactions`, `test_interactions_json_structure`, `test_interaction_fields_in_json`, `test_confidence_is_null_in_json`, `test_graph_json_structure`, `test_graph_json_nodes_are_speakers` |
| `TestInteractionRunner` | 1411 | class; `test_runner_creates_output_files`, `test_runner_missing_events_raises`, `test_runner_missing_evidence_raises` |
| `_influence_chain` | 1491 | function |
| `TestFeatureVector` | 1541 | class; `test_default_values_are_zero`, `test_to_dict_keys`, `test_ablation_flags_default_true` |
| `TestMaxNormalise` | 1578 | class; `test_max_becomes_one`, `test_all_zero_stays_zero`, `test_no_nan`, `test_single_nonzero` |
| `TestWeightLoading` | 1604 | class; `test_default_weights_cover_all_features`, `test_load_weights_returns_dict`, `test_weights_sum_to_one`, `test_zero_weight_ablation` |
| `TestFeatureExtraction` | 1633 | class; `test_returns_vector_per_speaker`, `test_decision_linked_proposal_gets_credit`, `test_evidence_gets_credit`, `test_objection_gets_credit`, `test_slide_grounded_contribution` |
| `TestWeightedScoring` | 1669 | class; `test_scores_in_unit_interval`, `test_all_scores_non_negative`, `test_scores_are_not_nan`, `test_speaking_time_is_not_dominant` |
| `TestRanking` | 1708 | class; `test_rank_1_has_highest_score`, `test_ranks_are_positive_integers`, `test_by_rank_sorted`, `test_ties_share_same_rank` |
| `TestDecisionLevelContribution` | 1752 | class; `test_decision_contributions_produced`, `test_contribution_score_in_range`, `test_roles_are_valid_strings`, `test_supporting_events_are_known_event_ids` |
| `TestBaselineScores` | 1794 | class; `test_baselines_produced_per_speaker`, `test_speaking_time_positive`, `test_speaking_time_norm_in_unit_interval`, `test_b2_in_unit_interval`, `test_b3_b4_non_negative`, `test_baselines_stored_separately_from_influence` |
| `TestExplanationAndTraceability` | 1841 | class; `test_explanation_is_non_empty_list`, `test_explanation_strings_not_generic`, `test_supporting_events_are_real_event_ids`, `test_supporting_decisions_are_real_decision_ids`, `test_score_not_labelled_causal` |
| `TestAblation` | 1889 | class; `test_zeroing_all_features_gives_zero_scores`, `test_disabling_one_feature_changes_scores` |
| `TestEdgeCases` | 1911 | class; `test_empty_events_produces_empty_result`, `test_single_participant_no_crash`, `test_no_decisions_still_produces_result` |
| `TestInfluenceSerialisation` | 1949 | class; `test_save_and_load_influence`, `test_influence_json_structure`, `test_baselines_json_structure`, `test_method_metadata_in_json` |
| `TestInfluenceRunner` | 2010 | class; `test_runner_creates_output_files`, `test_runner_missing_file_raises` |

## tests/test_ppt.py

[Open source](../../tests/test_ppt.py) — Regression suite: test_ppt.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_make_pptx` | 31 | function |
| `pptx_path` | 89 | function |
| `presentation_data` | 95 | function |
| `test_invalid_path_raises` | 105 | function |
| `test_invalid_extension_raises` | 112 | function |
| `test_slide_count` | 125 | function |
| `test_slide_numbers` | 134 | function |
| `test_slide_ids` | 139 | function |
| `test_title_slide1` | 148 | function |
| `test_title_slide2` | 152 | function |
| `test_no_title_slide3` | 156 | function |
| `test_text_slide1` | 165 | function |
| `test_text_does_not_duplicate_title` | 173 | function |
| `test_text_slide3_textbox` | 179 | function |
| `test_no_tables_slide1` | 188 | function |
| `test_table_slide2` | 192 | function |
| `test_notes_slide2` | 204 | function |
| `test_notes_slide1_none` | 210 | function |
| `test_metadata_keys` | 219 | function |
| `test_metadata_table_count_slide2` | 226 | function |
| `test_metadata_dimensions` | 230 | function |
| `test_meeting_id_from_filename` | 240 | function |
| `test_meeting_id_custom` | 245 | function |
| `test_meeting_id_derived` | 252 | function |
| `test_json_serialisation` | 263 | function |
| `test_json_slide_structure` | 285 | function |
| `test_build_slide_text_includes_title` | 306 | function |
| `test_build_slide_text_includes_body` | 312 | function |
| `test_build_slide_text_includes_table_cells` | 318 | function |
| `test_build_slide_text_includes_notes` | 325 | function |
| `test_slide_features_extraction` | 335 | function |
| `test_presentation_feature_summary` | 343 | function |
| `test_ocr_disabled_returns_empty` | 356 | function |

## tests/test_report.py

[Open source](../../tests/test_report.py) — Regression suite: test_report.py. Neural/model boundaries may be mocked; not empirical accuracy.

| Symbol | Line | Kind / direct methods |
| --- | ---: | --- |
| `_make_minimal_report` | 176 | function |
| `TestTimestampFormatter` | 219 | class; `test_zero`, `test_one_hour`, `test_none`, `test_hms` |
| `TestOverviewBuilding` | 237 | class; `test_meeting_id`, `test_num_participants`, `test_num_decisions`, `test_num_action_items`, `test_duration_positive`, `test_missing_events_graceful` |
| `TestParticipantBuilding` | 268 | class; `test_all_speakers_present`, `test_influence_scores_attached`, `test_speaking_duration_positive`, `test_roles_populated` |
| `TestExecutiveSummary` | 294 | class; `test_no_fabricated_content`, `test_num_proposals_correct`, `test_confirmed_decisions_listed`, `test_missing_data_graceful` |
| `TestDecisionRendering` | 317 | class; `test_decision_count`, `test_decision_fields`, `test_lineage_text_not_empty`, `test_unresolved_decision_says_unresolved`, `test_missing_decisions_graceful` |
| `TestActionItems` | 354 | class; `test_action_item_count`, `test_action_item_speaker`, `test_action_item_timestamp`, `test_unassigned_when_no_speaker` |
| `TestInfluenceRendering` | 378 | class; `test_influence_list_populated`, `test_ranked_correctly`, `test_explanations_non_empty`, `test_missing_influence_returns_empty`, `test_no_fabricated_scores` |
| `TestInfluenceVsSpeaking` | 410 | class; `test_produces_rows_per_participant`, `test_both_ranks_present` |
| `TestTraceability` | 428 | class; `test_chains_produced`, `test_chain_fields`, `test_event_ids_real` |
| `TestMissingInputHandling` | 451 | class; `test_missing_influence_json`, `test_missing_influence_section_marked`, `test_missing_evaluation_marked_unavailable`, `test_interactions_status_when_missing` |
| `TestJSONExport` | 476 | class; `test_json_created`, `test_json_structure`, `test_json_serialisable`, `test_json_meeting_id` |
| `TestMarkdownExport` | 511 | class; `test_markdown_created`, `test_markdown_has_headings`, `test_markdown_no_fabricated_scores`, `test_markdown_influence_disclaimer`, `test_markdown_speaking_vs_influence` |
| `TestHTMLExport` | 554 | class; `test_html_created`, `test_html_valid_structure`, `test_html_no_external_deps`, `test_html_contains_meeting_id` |
| `TestCSVExport` | 590 | class; `test_participants_csv`, `test_decisions_csv`, `test_influence_csv`, `test_action_items_csv` |
| `TestExportAll` | 638 | class; `test_all_formats_created`, `test_selective_format`, `test_returns_path_dict` |
| `TestSlideDiscussions` | 667 | class; `test_slides_grouped`, `test_no_slide_events_excluded`, `test_missing_events_graceful` |
| `TestInteractionsSection` | 690 | class; `test_interaction_count`, `test_interaction_type_counts`, `test_note_about_influence`, `test_missing_interactions_returns_unavailable` |

## Non-Python source landmarks

| Area | Files / responsibility |
| --- | --- |
| Browser | `frontend/src/App.jsx`: recorder/upload/review; `MeetingNotes.jsx`: notes/questions; `recordingStore.js`: IndexedDB |
| Browser checks | `scripts/test_browser_offline.cjs`: current fixtures; earlier browser `.cjs` scripts have historical selectors |
| Native Android UI | `MainActivity.java`, `Ui.java`, resources: navigation/theme/icons and state |
| Android service/storage | `MeetingService.java`, `MeetingProgress.java`, `MeetingRepository.java`, `LocalTransfers.java` |
| Android audio/rules | `WavAudio.java`, `AudioPlaybackController.java`, `EventRules.java` |
| Native inference | `NativeWhisper.java`, `app/src/main/cpp/whisper_jni.cpp`, `CMakeLists.txt` |
| Android checks | `android/test/{WavAudioTest,MeetingProgressTest,EventRulesTest}.java`; direct `test.sh`/`build.sh` |
| Provisioning/launcher | `scripts/setup.sh`, `android/setup.sh`, `scripts/start_app.sh` |

`android/vendor/whisper.cpp` is third-party upstream source and intentionally excluded from this first-party index. No old .env values, private account records, model binaries, or user transcript contents are reproduced here.
