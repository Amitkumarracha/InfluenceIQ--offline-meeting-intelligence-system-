"""Compare scalar and batched cosine scores on saved meeting text, offline."""
import argparse
import json
import re
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT, get


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--meeting-id', required=True)
    parser.add_argument('--max-segments', type=int, default=256)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', args.meeting_id) or args.max_segments < 1:
        parser.error('Supply a valid meeting ID and positive segment count')
    import numpy as np
    import torch
    from src.fusion.semantic_alignment import compute_semantic_scores, iter_semantic_scores, load_embedding_model
    torch.set_num_threads(int(get('asr.cpu_threads', 4)))
    root = PROJECT_ROOT / 'data/processed'
    transcript = json.loads((root / 'audio' / f'{args.meeting_id}_transcript.json').read_text())
    slides = json.loads((root / 'slides' / f'{args.meeting_id}_slides.json').read_text())
    keys = np.load(root / 'slides' / f'{args.meeting_id}_embeddings.npy')
    ids = [slide['slide_id'] for slide in slides['slides']]
    texts = [s['text'] for s in transcript['segments'][:args.max_segments]]
    if not texts or not ids:
        parser.error('Saved transcript and slides must be nonempty')
    start = time.perf_counter()
    model = load_embedding_model(get('ppt.embeddings.model'))
    load_seconds = time.perf_counter() - start
    model.encode(['warm up'], show_progress_bar=False)
    start = time.perf_counter()
    scalar = np.asarray([[s.score for s in compute_semantic_scores(text, ids, keys, model)] for text in texts])
    scalar_seconds = time.perf_counter() - start
    start = time.perf_counter()
    batch = np.asarray(list(iter_semantic_scores(texts, keys, model)))
    batch_seconds = time.perf_counter() - start
    threshold = float(get('alignment.threshold', .3))
    def selected(rows):
        return [ids[int(np.argmax(row))] if np.max(row) >= threshold else 'NO_CONFIDENT_SLIDE' for row in rows]
    result = {'meeting_id': args.meeting_id, 'passages': len(texts), 'slides': len(ids),
        'threads': torch.get_num_threads(), 'model': get('ppt.embeddings.model'),
        'model_load_seconds': load_seconds, 'scalar_seconds': scalar_seconds,
        'batched_seconds': batch_seconds, 'speedup': scalar_seconds / batch_seconds,
        'max_absolute_score_difference': float(np.max(np.abs(scalar - batch))),
        'semantic_only_selection_agreement': sum(a == b for a,b in zip(selected(scalar), selected(batch))) / len(texts),
        'scope': 'Warm-model semantic scoring only; scalar first then batch, one local run. Not end-to-end speed or alignment accuracy.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
