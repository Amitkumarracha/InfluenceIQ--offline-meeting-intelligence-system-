"""
Entry point for the meeting intelligence pipeline.

Audio pipeline (Phases 1–5):
    python scripts/run_pipeline.py --audio <path> [--meeting-id <id>]
        [--skip-diarization] [--skip-asr] [--diarization-json <path>]

PPT pipeline (Phase 6 — standalone):
    python scripts/run_pipeline.py --ppt <path> [--meeting-id <id>]
        [--skip-embeddings]

Alignment pipeline (Phase 7 — standalone):
    python scripts/run_pipeline.py --transcript <path> --slides <path>
        [--embeddings <path>] [--meeting-id <id>]

Event/Evidence pipeline (Phase 8 — standalone):
    python scripts/run_pipeline.py --multimodal <multimodal.json>
        [--meeting-id <id>]

Decision reconstruction pipeline (Phase 9 — standalone):
    python scripts/run_pipeline.py --events <events.json>
        --evidence <evidence.json> [--meeting-id <id>]

Interaction analysis pipeline (Phase 10 — standalone):
    python scripts/run_pipeline.py --decisions <decisions.json>
        --events <events.json> --evidence <evidence.json> [--meeting-id <id>]

Influence analysis pipeline (Phase 11 — standalone):
    python scripts/run_pipeline.py --interactions <interactions.json>
        --decisions <decisions.json> --events <events.json>
        --evidence <evidence.json> [--meeting-id <id>]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import get_logger

logger = get_logger("pipeline")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multimodal Meeting Intelligence Pipeline")

    # Mutually exclusive input modes
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--audio", help="Path to the input audio file")
    input_group.add_argument("--ppt", help="Path to the input PPT/PPTX file")
    input_group.add_argument(
        "--transcript",
        help="Path to transcript JSON (alignment mode — requires --slides)",
    )
    input_group.add_argument(
        "--multimodal",
        help="Path to multimodal JSON (event/evidence extraction mode)",
    )
    input_group.add_argument(
        "--events",
        help="Path to events JSON (decision reconstruction mode — requires --evidence)",
    )
    input_group.add_argument(
        "--decisions",
        help="Path to decisions JSON (interaction analysis mode — requires --events and --evidence)",
    )
    input_group.add_argument(
        "--interactions",
        help="Path to interactions JSON (influence analysis mode — requires --decisions, --events, --evidence)",
    )
    parser.add_argument("--meeting-id", default=None, help="Meeting identifier")

    # Audio-pipeline flags
    parser.add_argument(
        "--skip-diarization",
        action="store_true",
        help="Skip diarization (useful if HF_TOKEN is not set)",
    )
    parser.add_argument(
        "--skip-asr",
        action="store_true",
        help="Skip ASR / transcription stage",
    )
    parser.add_argument(
        "--diarization-json",
        default=None,
        help="Path to an existing diarization JSON (skips running diarization again)",
    )

    # PPT-pipeline flags
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip slide embedding generation (PPT mode only)",
    )

    # Alignment-pipeline flags
    parser.add_argument(
        "--slides",
        default=None,
        help="Path to slides JSON (alignment mode)",
    )
    parser.add_argument(
        "--embeddings",
        default=None,
        help="Path to slide embeddings .npy (alignment mode; auto-detected if omitted)",
    )

    # Decision-pipeline flags
    parser.add_argument(
        "--evidence",
        default=None,
        help="Path to evidence JSON (decision reconstruction / interaction / influence analysis mode)",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# PPT pipeline (Phase 6)
# ---------------------------------------------------------------------------

def run_ppt_pipeline(args: argparse.Namespace) -> None:
    """Standalone PPT processing — no audio-PPT alignment in this phase."""
    from src.ppt.extract import PPTXExtractor
    from src.ppt.embeddings import generate_embeddings, save_embeddings
    from src.ppt.io import save_presentation_json
    from src.utils.config import get

    ppt_path = Path(args.ppt)
    if not ppt_path.exists():
        logger.error("PPT file not found: %s", ppt_path)
        sys.exit(1)

    meeting_id = args.meeting_id or None  # extractor will derive from filename if None

    # --- Step 1: validate & extract ---
    cfg = get("ppt") or {}
    extractor = PPTXExtractor(
        ppt_path,
        meeting_id=meeting_id,
        extract_text=cfg.get("extract_text", True),
        extract_tables=cfg.get("extract_tables", True),
        extract_notes=cfg.get("extract_notes", True),
    )

    logger.info("=== PPT Stage 1: Slide Extraction ===")
    try:
        pdata = extractor.extract()
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Extraction failed: %s", exc)
        sys.exit(1)

    # --- Step 2: save JSON ---
    out_dir = Path("data/processed/slides")
    json_path = out_dir / f"{pdata.meeting_id}_slides.json"
    save_presentation_json(pdata, json_path)

    # --- Step 3: optional embeddings ---
    emb_path = None
    if not args.skip_embeddings:
        logger.info("=== PPT Stage 2: Slide Embeddings ===")
        embeddings = generate_embeddings(pdata)
        if embeddings is not None:
            emb_path = out_dir / f"{pdata.meeting_id}_embeddings.npy"
            save_embeddings(embeddings, emb_path)
        else:
            logger.warning("Embedding generation skipped (model unavailable or error).")
    else:
        logger.info("Embeddings skipped (--skip-embeddings).")

    # --- Step 4: summary ---
    slides_with_text = sum(1 for s in pdata.slides if s.text or s.title)
    total_tables = sum(len(s.tables) for s in pdata.slides)
    total_images = sum(s.metadata.get("image_count", 0) for s in pdata.slides)

    print("\n[PPT Summary]")
    print(f"  Meeting ID      : {pdata.meeting_id}")
    print(f"  Source file     : {pdata.source_file}")
    print(f"  Total slides    : {pdata.num_slides}")
    print(f"  Slides with text: {slides_with_text}")
    print(f"  Total tables    : {total_tables}")
    print(f"  Total images    : {total_images}")
    print(f"  Slide JSON      : {json_path}")
    if emb_path:
        print(f"  Embeddings      : {emb_path}")
    print("\nDone.")


# ---------------------------------------------------------------------------
# Influence analysis pipeline (Phase 11)
# ---------------------------------------------------------------------------

def run_influence_pipeline(args: argparse.Namespace) -> None:
    """Standalone participant influence analysis — Phase 11."""
    from src.meeting.influence import run_influence_analysis

    interactions_path = Path(args.interactions)
    for flag, name in [
        (args.decisions, "--decisions"),
        (args.events,    "--events"),
        (args.evidence,  "--evidence"),
    ]:
        if not flag:
            logger.error("%s is required with --interactions", name)
            sys.exit(1)

    decisions_path = Path(args.decisions)
    events_path    = Path(args.events)
    evidence_path  = Path(args.evidence)

    logger.info("=== Phase 11: Participant Influence Analysis ===")
    try:
        result, influence_path, baselines_path = run_influence_analysis(
            events_path=events_path,
            evidence_path=evidence_path,
            decisions_path=decisions_path,
            interactions_path=interactions_path,
            meeting_id=args.meeting_id or None,
        )
    except FileNotFoundError as exc:
        logger.error("Influence analysis failed — missing input: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Influence analysis failed: %s", exc)
        sys.exit(1)

    print("\n[Influence Analysis Summary]")
    print(f"  Meeting ID        : {result.meeting_id}")
    print(f"  Participants      : {len(result.participants)}")
    print(f"  Scoring method    : {result.method.get('type', 'N/A')}")
    print(f"  Normalisation     : {result.method.get('normalization', 'N/A')}")
    for p in result.by_rank():
        print(f"    Rank {p.rank:<3} {p.participant:<20} score={p.influence_score:.4f}")
    print(f"  Influence JSON    : {influence_path}")
    print(f"  Baselines JSON    : {baselines_path}")
    print("\nNOTE: Scores are analytical estimates. Human evaluation required to validate.")
    print("\nDone.")


# ---------------------------------------------------------------------------
# Interaction analysis pipeline (Phase 10)
# ---------------------------------------------------------------------------

def run_interaction_pipeline(args: argparse.Namespace) -> None:
    """Standalone participant interaction analysis — Phase 10."""
    from src.meeting.interaction import run_interaction_analysis

    decisions_path = Path(args.decisions)
    if not args.events:
        logger.error("--events <path> is required with --decisions")
        sys.exit(1)
    if not args.evidence:
        logger.error("--evidence <path> is required with --decisions")
        sys.exit(1)
    events_path = Path(args.events)
    evidence_path = Path(args.evidence)

    logger.info("=== Phase 10: Participant Interaction Analysis ===")
    try:
        result, interactions_path, graph_path = run_interaction_analysis(
            events_path=events_path,
            evidence_path=evidence_path,
            decisions_path=decisions_path,
            meeting_id=args.meeting_id or None,
        )
    except FileNotFoundError as exc:
        logger.error("Interaction analysis failed — missing input: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Interaction analysis failed: %s", exc)
        sys.exit(1)

    type_counts = result.count_by_type()
    decision_linked = len(result.decision_linked())
    unresolved = sum(1 for i in result.interactions if i.target_speaker is None)

    print("\n[Interaction Analysis Summary]")
    print(f"  Meeting ID              : {result.meeting_id}")
    print(f"  Participants            : {', '.join(result.participants)}")
    print(f"  Total interactions      : {len(result.interactions)}")
    for itype, n in sorted(type_counts.items()):
        print(f"    {itype:<20}: {n}")
    print(f"  Decision-linked         : {decision_linked}")
    print(f"  Unresolved target       : {unresolved}")
    print(f"  Interactions JSON       : {interactions_path}")
    print(f"  Interaction graph JSON  : {graph_path}")
    print("\nDone.")


# ---------------------------------------------------------------------------
# Decision reconstruction pipeline (Phase 9)
# ---------------------------------------------------------------------------

def run_decision_pipeline(args: argparse.Namespace) -> None:
    """Standalone decision reconstruction — Phase 9."""
    from src.meeting.decisions import run_decision_reconstruction

    events_path = Path(args.events)
    if not args.evidence:
        logger.error("--evidence <path> is required with --events")
        sys.exit(1)
    evidence_path = Path(args.evidence)

    logger.info("=== Phase 9: Decision Reconstruction ===")
    try:
        result, decisions_path, graph_path = run_decision_reconstruction(
            events_path=events_path,
            evidence_path=evidence_path,
            meeting_id=args.meeting_id or None,
        )
    except FileNotFoundError as exc:
        logger.error("Decision reconstruction failed — missing input: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Decision reconstruction failed: %s", exc)
        sys.exit(1)

    status_counts = result.count_by_status()
    lineage_total = sum(len(d.lineage) for d in result.decisions)

    print("\n[Decision Reconstruction Summary]")
    print(f"  Meeting ID        : {result.meeting_id}")
    print(f"  Total decisions   : {len(result.decisions)}")
    for status, n in sorted(status_counts.items()):
        print(f"    {status:<20}: {n}")
    print(f"  Lineage edges     : {lineage_total}")
    print(f"  Decisions JSON    : {decisions_path}")
    print(f"  Graph JSON        : {graph_path}")
    print("\nDone.")


# ---------------------------------------------------------------------------
# Event/Evidence pipeline (Phase 8)
# ---------------------------------------------------------------------------

def run_event_pipeline(args: argparse.Namespace) -> None:
    """Standalone event and evidence extraction — Phase 8."""
    from src.meeting.events import run_event_extraction
    from src.meeting.evidence import run_evidence_extraction
    from src.utils.config import get

    multimodal_path = Path(args.multimodal)
    if not multimodal_path.exists():
        logger.error("Multimodal JSON not found: %s", multimodal_path)
        sys.exit(1)

    meeting_id = args.meeting_id or None

    logger.info("=== Phase 8: Event Extraction ===")
    try:
        event_result, events_path = run_event_extraction(
            multimodal_path=multimodal_path,
            meeting_id=meeting_id,
        )
    except Exception as exc:
        logger.error("Event extraction failed: %s", exc)
        sys.exit(1)

    logger.info("=== Phase 8: Evidence Extraction ===")
    window_s = float(get("meeting_analysis.evidence_window_s", 60.0))
    try:
        evidence_result, evidence_path = run_evidence_extraction(
            events_path=events_path,
            meeting_id=event_result.meeting_id,
            window_s=window_s,
        )
    except Exception as exc:
        logger.error("Evidence extraction failed: %s", exc)
        sys.exit(1)

    counts = event_result.count_by_type()
    print("\n[Event/Evidence Summary]")
    print(f"  Meeting ID         : {event_result.meeting_id}")
    print(f"  Total events       : {len(event_result.events)}")
    for etype, n in sorted(counts.items()):
        print(f"    {etype:<20}: {n}")
    print(f"  Evidence relations : {len(evidence_result.relations)}")
    print(f"  Events JSON        : {events_path}")
    print(f"  Evidence JSON      : {evidence_path}")
    print("\nDone.")


# ---------------------------------------------------------------------------
# Alignment pipeline (Phase 7)
# ---------------------------------------------------------------------------

def run_alignment_pipeline(args: argparse.Namespace) -> None:
    """Standalone Audio–PPT alignment — Phase 7."""
    from src.fusion.multimodal_representation import run_alignment, NO_SLIDE

    transcript_path = Path(args.transcript)
    if not args.slides:
        logger.error("--slides <path> is required with --transcript")
        sys.exit(1)
    slides_path = Path(args.slides)
    embeddings_path = Path(args.embeddings) if args.embeddings else None

    logger.info("=== Phase 7: Audio–PPT Alignment ===")
    try:
        alignment_results, multimodal_segments, aln_path, mm_path = run_alignment(
            transcript_path=transcript_path,
            slides_path=slides_path,
            embeddings_path=embeddings_path,
            meeting_id=args.meeting_id or None,
        )
    except FileNotFoundError as exc:
        logger.error("Alignment failed — missing input: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Alignment failed: %s", exc)
        sys.exit(1)

    aligned = sum(1 for a in alignment_results if a.selected_slide != NO_SLIDE)
    no_slide = len(alignment_results) - aligned

    print("\n[Alignment Summary]")
    print(f"  Total segments   : {len(alignment_results)}")
    print(f"  Aligned to slide : {aligned}")
    print(f"  No confident slide: {no_slide}")
    print(f"  Alignment JSON   : {aln_path}")
    print(f"  Multimodal JSON  : {mm_path}")
    print("\nDone.")


# ---------------------------------------------------------------------------
# Audio pipeline (Phases 1–5)
# ---------------------------------------------------------------------------

def run_audio_pipeline(args: argparse.Namespace) -> None:
    from src.audio.asr import run_asr
    from src.audio.diarization import run_diarization
    from src.audio.preprocess import preprocess_audio
    from src.audio.vad import run_vad

    audio_path = Path(args.audio)
    if not audio_path.exists():
        logger.error("Input file not found: %s", audio_path)
        sys.exit(1)

    meeting_id = args.meeting_id or audio_path.stem

    # --- Stage 1: Preprocessing ---
    logger.info("=== Stage 1: Audio Preprocessing ===")
    processed_path, metadata = preprocess_audio(audio_path)

    print("\n[Preprocessing Summary]")
    print(f"  Input file      : {metadata.file_name}")
    print(f"  Original SR     : {metadata.original_sample_rate} Hz")
    print(f"  Processed SR    : {metadata.processed_sample_rate} Hz")
    print(f"  Original ch     : {metadata.original_channels}")
    print(f"  Original dur    : {metadata.original_duration:.2f}s")
    print(f"  Processed dur   : {metadata.processed_duration:.2f}s")
    print(f"  Output          : {processed_path}")

    # --- Stage 2: VAD ---
    logger.info("=== Stage 2: Voice Activity Detection ===")
    vad_segments, vad_json_path = run_vad(processed_path, meeting_id=meeting_id)
    total_speech = sum(s.end - s.start for s in vad_segments)

    print("\n[VAD Summary]")
    print(f"  Speech segments : {len(vad_segments)}")
    print(f"  Total speech    : {total_speech:.2f}s")
    print(f"  VAD JSON        : {vad_json_path}")

    # --- Stage 3: Diarization ---
    diar_json_path = None
    if args.diarization_json:
        diar_json_path = Path(args.diarization_json)
        logger.info("Using provided diarization JSON: %s", diar_json_path)
    elif args.skip_diarization:
        logger.info("Diarization skipped (--skip-diarization flag set).")
    else:
        logger.info("=== Stage 3: Speaker Diarization ===")
        try:
            diar_result, diar_json_path = run_diarization(processed_path, meeting_id=meeting_id)
            print("\n[Diarization Summary]")
            print(f"  Speakers found  : {diar_result.num_speakers}")
            print(f"  Speaker IDs     : {', '.join(diar_result.speakers)}")
            print(f"  Segments        : {len(diar_result.segments)}")
            print(f"  Diarization JSON: {diar_json_path}")
        except EnvironmentError as e:
            logger.error("Diarization skipped: %s", e)
            print(f"\n[Diarization] Skipped — {e}")

    # --- Stage 4: ASR + Speaker Attribution ---
    if args.skip_asr:
        logger.info("ASR skipped (--skip-asr flag set).")
    elif diar_json_path is None:
        logger.warning("ASR skipped — no diarization JSON available (run diarization first).")
        print("\n[ASR] Skipped — no diarization results available.")
    else:
        logger.info("=== Stage 4: ASR + Speaker Attribution ===")
        try:
            asr_result, asr_json_path, asr_txt_path = run_asr(
                processed_path,
                diarization_path=diar_json_path,
                meeting_id=meeting_id,
            )
            print("\n[ASR Summary]")
            print(f"  Language        : {asr_result.language or 'auto'}")
            print(f"  Duration        : {asr_result.duration:.2f}s")
            print(f"  Speakers        : {', '.join(asr_result.speakers) or 'none'}")
            print(f"  Segments        : {len(asr_result.segments)}")
            print(f"  Transcript JSON : {asr_json_path}")
            print(f"  Transcript TXT  : {asr_txt_path}")
        except FileNotFoundError as e:
            logger.error("ASR failed: %s", e)
            print(f"\n[ASR] Failed — {e}")

    print("\nDone.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    if args.ppt:
        run_ppt_pipeline(args)
    elif args.transcript:
        run_alignment_pipeline(args)
    elif args.multimodal:
        run_event_pipeline(args)
    elif args.interactions:
        run_influence_pipeline(args)
    elif args.decisions:
        run_interaction_pipeline(args)
    elif args.events:
        run_decision_pipeline(args)
    else:
        run_audio_pipeline(args)


if __name__ == "__main__":
    main()
