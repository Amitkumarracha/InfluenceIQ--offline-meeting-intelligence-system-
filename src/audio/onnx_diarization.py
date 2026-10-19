"""Local sherpa-onnx adapter. Explicit provisioning precedes offline inference."""
from pathlib import Path
import soundfile as sf
from src.utils.config import PROJECT_ROOT, get


def model_paths():
    paths = []
    for key in ('segmentation_model', 'embedding_model'):
        value = get('diarization.onnx.' + key, '')
        if not value:
            raise RuntimeError('Configure diarization.onnx segmentation_model and embedding_model paths first.')
        path = Path(value)
        path = path if path.is_absolute() else PROJECT_ROOT / path
        if not path.is_file():
            raise RuntimeError('Local ONNX diarization model missing: ' + str(path))
        paths.append(path)
    return paths


def diarize(audio_path, num_speakers=None, progress=None):
    if num_speakers is None and (get('diarization.min_speakers') is not None or get('diarization.max_speakers') is not None):
        raise ValueError('ONNX supports an exact speaker count, not min/max bounds; unset those bounds first.')
    segmentation, embedding = model_paths()
    try:
        import sherpa_onnx
    except ImportError as exc:
        raise RuntimeError('Install optional sherpa-onnx manually; see RUN_MANUALLY.md.') from exc
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(segmentation)),
            num_threads=int(get("asr.cpu_threads", 4))),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding), num_threads=int(get("asr.cpu_threads", 4))),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=num_speakers or -1,
            threshold=float(get('diarization.onnx.cluster_threshold', .9))),
        min_duration_on=.3, min_duration_off=.5)
    if not config.validate():
        raise RuntimeError('Invalid local ONNX diarization configuration')
    engine = sherpa_onnx.OfflineSpeakerDiarization(config)
    with sf.SoundFile(audio_path) as audio:
        if audio.channels != 1 or audio.samplerate != engine.sample_rate:
            raise ValueError('ONNX diarization requires normalized mono audio at the model sample rate')
        # The upstream API clusters the whole meeting. Chunking independently
        # would silently reset speaker identities. This is not streaming DER.
        samples = audio.read(dtype='float32')
    def checkpoint(processed_chunks, num_chunks):
        if progress:
            # Feature extraction ends before whole-meeting clustering finishes.
            progress({'completed_seconds': min(.98, processed_chunks / max(1, num_chunks)) * len(samples) / engine.sample_rate,
                      'total_seconds': len(samples) / engine.sample_rate, 'cached': False,
                      'phase': 'speaker_features' if processed_chunks < num_chunks else 'clustering'})
        return 0

    result = (engine.process(samples, callback=checkpoint) if progress else engine.process(samples)).sort_by_start_time()
    if progress:
        progress({'completed_seconds': len(samples) / engine.sample_rate,
                  'total_seconds': len(samples) / engine.sample_rate, 'cached': False, 'phase': 'complete'})
    return [(float(turn.start), float(turn.end), str(turn.speaker)) for turn in result]
