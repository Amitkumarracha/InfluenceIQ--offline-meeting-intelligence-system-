"""Complete local audio-to-report workflow shared by API and CLI."""
import json
import re
import time
from pathlib import Path
from src.utils.cache import atomic_json
from src.utils.config import PROJECT_ROOT, get
from src.utils.checkpointing import save_resume_state, mark_stage_complete


def run_meeting(audio_path, meeting_id, ppt_path=None, diarization='auto', progress=None, options=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', meeting_id):
        raise ValueError('Invalid meeting identifier')
    if diarization not in {'auto', 'required', 'off'}:
        raise ValueError('Invalid diarization mode')
    from src.audio.preprocess import preprocess_audio
    from src.audio.asr import run_asr
    from dataclasses import asdict
    from src.meeting.events import KeywordEventExtractor
    from src.audio.diarization import run_diarization
    from src.meeting.events import run_event_extraction
    from src.meeting.evidence import run_evidence_extraction
    from src.meeting.decisions import run_decision_reconstruction
    from src.meeting.interaction import run_interaction_analysis
    from src.meeting.influence import run_influence_analysis
    from src.report.generator import generate_report
    from src.report.exporter import export_all

    root = PROJECT_ROOT / 'data' / 'processed'
    warnings = []
    options = options or {}
    stage = None
    started = stage_started = time.perf_counter()
    stage_timings = {}
    asr_progress = {}
    preview_path = root / 'audio' / f'{meeting_id}_preview.json'

    def update(name):
        nonlocal stage, stage_started
        now = time.perf_counter()
        if stage is not None:
            stage_timings[stage] = round(now - stage_started, 6)
        stage_started = now
        stage = name
        save_resume_state(meeting_id, name)
        if progress:
            progress(name)

    def transcription_progress(details):
        asr_progress.update(details)
        if progress:
            progress('transcription', details)

    def preview(segments, details):
        recent = [asdict(segment) for segment in segments[-50:]]
        events = KeywordEventExtractor().extract(recent, meeting_id)
        atomic_json(preview_path, {**details, 'transcript_segments': recent,
            'events': [asdict(event) for event in events.events], 'requires_review': True})

    try:
        atomic_json(preview_path, {'transcript_segments': [], 'events': [], 'requires_review': True})
        update('preprocessing')
        processed, metadata = preprocess_audio(audio_path, root / 'audio' / f'{meeting_id}_processed.wav', reuse_normalized=True)
        mark_stage_complete(meeting_id, stage, processed)
        update('diarization')
        diar_path = root / 'audio' / f'{meeting_id}_diarization.json'
        speaker_identified = False
        if diarization != 'off':
            try:
                diar_result, diar_path = run_diarization(processed, meeting_id=meeting_id, num_speakers=options.get('num_speakers'))
                speaker_identified = bool(diar_result.segments)
            except Exception as exc:
                if diarization == 'required':
                    raise
                warnings.append('Speaker separation unavailable. All speech is labelled UNKNOWN; participant influence is unavailable.')
        if not speaker_identified:
            if diarization == 'off':
                warnings.append('Speaker separation disabled. All speech is labelled UNKNOWN.')
            # No invented speaker identity; ASR works independently of diarization.
            diar_path = root / 'audio' / f'{meeting_id}_unknown_diarization.json'
            atomic_json(diar_path, {'meeting_id': meeting_id, 'segments': []})
        mark_stage_complete(meeting_id, stage, diar_path)
        update('transcription')
        transcript, transcript_path, _ = run_asr(processed, diar_path, meeting_id, options=options,
            progress=transcription_progress, on_chunk=preview)
        mark_stage_complete(meeting_id, stage, transcript_path)
        source = transcript_path
        if ppt_path:
            update('slides')
            from src.ppt.extract import PPTXExtractor
            from src.ppt.io import save_presentation_json
            from src.ppt.embeddings import generate_embeddings, save_embeddings
            from src.fusion.multimodal_representation import run_alignment
            slides = PPTXExtractor(Path(ppt_path), meeting_id=meeting_id).extract()
            slides_path = root / 'slides' / f'{meeting_id}_slides.json'
            save_presentation_json(slides, slides_path)
            emb_path = None
            if get('alignment.method', 'embeddings') == 'embeddings':
                embeddings = generate_embeddings(slides)
                if embeddings is None:
                    raise RuntimeError('Slide embedding model missing. Provision it manually or select alignment.method: tfidf.')
                emb_path = root / 'slides' / f'{meeting_id}_embeddings.npy'
                save_embeddings(embeddings, emb_path)
            update('alignment')
            _, _, _, source = run_alignment(transcript_path, slides_path, emb_path,
                                             meeting_id, root / 'alignment')
        update('events')
        _, events = run_event_extraction(source, meeting_id, root / 'events')
        _, evidence = run_evidence_extraction(events, meeting_id, root / 'events',
                                              window_s=float(get('meeting_analysis.evidence_window_s', 60)))
        update('decisions')
        _, decisions, _ = run_decision_reconstruction(events, evidence, meeting_id, root / 'decisions')
        update('interactions')
        _, interactions, _ = run_interaction_analysis(events, evidence, decisions, meeting_id, root / 'interactions')
        update('influence')
        _, influence, _ = run_influence_analysis(events, evidence, decisions, interactions, meeting_id, root / 'influence')
        payload = json.loads(influence.read_text())
        payload['participants'] = [p for p in payload.get('participants', []) if p.get('participant') != 'UNKNOWN']
        if not speaker_identified:
            payload['status'] = 'unavailable_without_diarization'
        atomic_json(influence, payload)
        update('report')
        report = generate_report(meeting_id, root, include_slides=bool(ppt_path))
        if not transcript.segments:
            warnings.append('No speech was transcribed. Check the recording and microphone placement.')
        if transcript.recording_quality.get('clipped_sample_ratio', 0) > .01:
            warnings.append('More than 1% of audio samples are near full scale. Check microphone gain and review potentially clipped speech.')
        report.processing = {
            'warnings': warnings, 'speaker_separation': speaker_identified,
            'speaker_backend': get('diarization.backend'), 'generative_ai': False,
            'language': transcript.language, 'recording_quality': transcript.recording_quality, 'asr_model': options.get('model_size') or get('asr.model_size'),
            'options': options, 'alignment_method': get('alignment.method', 'embeddings') if ppt_path else None,
            'analysis_method': 'English/Hindi/Hinglish keyword heuristics; review against source audio',
            'accuracy_measured': False,
            'stage_timings_seconds': stage_timings,
            'asr_requested_device': get('asr.device', 'cpu'),
            'asr_requested_compute_type': get('asr.compute_type', 'int8'),
            'cpu_threads': int(get('asr.cpu_threads', 4)),
            'asr_last_chunk_cached': asr_progress.get('cached'),
        }
        export_all(report, PROJECT_ROOT / 'outputs' / 'reports', formats=['json', 'markdown', 'html', 'csv'])
        report_path = PROJECT_ROOT / 'outputs' / 'reports' / f'{meeting_id}_report.json'
        payload = json.loads(report_path.read_text())
        payload['transcript_segments'] = [vars(s) for s in transcript.segments]
        from src.meeting.vocabulary import suggest_vocabulary
        payload['vocabulary_suggestions'] = suggest_vocabulary(payload['transcript_segments'])
        payload['vocabulary'] = options.get('vocabulary', '')
        stage_timings['report'] = round(time.perf_counter() - stage_started, 6)
        payload['processing']['stage_timings_seconds'] = stage_timings
        payload['processing']['elapsed_seconds'] = round(time.perf_counter() - started, 6)
        payload['processing']['timing_scope'] = 'Processing stages through report preparation; excludes module imports, upload/decode, queue wait and final JSON/checkpoint writes'
        atomic_json(report_path, payload)
        mark_stage_complete(meeting_id, 'report', report_path, extra={'status': 'completed'})
        return report_path
    except Exception:
        save_resume_state(meeting_id, stage, status='failed')
        raise
