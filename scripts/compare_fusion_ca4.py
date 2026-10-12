"""Compare temporal, semantic and deployed hybrid alignment without training or fabricated labels."""
import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import statistics
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT, get


def fixtures():
    """Author-designed diagnostic cases, not natural meeting ground truth."""
    slide_texts = [
        'Budget and costs: total project budget 250000 rupees. Hardware cost 150000 rupees. Software cost 100000 rupees.',
        'Performance target: response time below 100 milliseconds. Transcription accuracy and speaker diarization are evaluated separately.',
        'Project schedule: prototype delivery on 15 October. User testing on 20 October. Final submission on 30 October.',
        'Offline deployment: meeting audio stays on the local laptop. Cloud processing is optional. Internet is not required after model installation.',
        'Risks and mitigation: overlapping speech, noisy microphones, ambiguous speaker identities. Manual review and a known speaker count reduce errors.',
        'Meeting responsibilities: project manager coordinates work. Industrial designer selects hardware. Marketing expert studies customers. UI designer creates the interface.',
    ]
    ids = [f'slide_{i+1:02d}' for i in range(len(slide_texts))]
    cases=[]
    def add(group, text, gold, shown=None, timed=True):
        cases.append({'id': f'case_{len(cases)+1:02d}', 'group':group, 'text':text,
                      'gold':ids[gold] if gold is not None else 'NO_CONFIDENT_SLIDE',
                      'shown':ids[shown if shown is not None else gold] if (shown is not None or gold is not None) else ids[0],
                      'timed':timed, 'start':5., 'end':10.})
    for i in range(4): add('exact_content',slide_texts[i],i)
    for text,i in [('We have allocated two hundred and fifty thousand rupees for this project.',0),
                   ('Our system should reply in under a tenth of a second.',1),
                   ('The first working version is due in mid October, with tests five days later.',2),
                   ('Once the weights are installed, we can analyse recordings without a network connection.',3)]:
        add('paraphrase',text,i)
    for i in range(4): add('offscreen_reference',slide_texts[i],i,shown=(i+1)%6)
    for i in range(4): add('missing_slide_times',slide_texts[i],i,timed=False)
    for i in range(4): add('context_dependent','That is the agreed target for this part.',i)
    for text in ['I enjoyed the beach on my holiday.', 'The football match was exciting yesterday.',
                 'My favourite meal is pasta with tomato sauce.', '']:
        add('unrelated_or_blank',text,None,shown=0)
    assert len(cases)==24 and len({c['id'] for c in cases})==24
    return ids,slide_texts,cases


def predict(segments, ids, times, embeddings, score_rows, strategy):
    import numpy as np
    from src.fusion.multimodal_representation import align_segment
    from src.fusion.temporal_alignment import SlideTimingInfo
    results=[]
    for index,segment in enumerate(segments):
        used_times=times[index] if strategy!='semantic_only' else [SlideTimingInfo(sid) for sid in ids]
        scores=dict(zip(ids,map(float,score_rows[index]))) if strategy!='temporal_only' else dict.fromkeys(ids,0.)
        result=align_segment(segment,ids,used_times,embeddings,None,3,
            1. if strategy=='temporal_only' else .5,
            0. if strategy=='temporal_only' else (1. if strategy=='semantic_only' else .5),
            float(get('alignment.threshold',.3)),precomputed_scores=scores)
        results.append(result)
    return results


def metrics(gold,pred):
    labels=sorted(set(gold)|set(pred))
    macro=[]
    tp=fp=fn=0
    for label in labels:
        hit=sum(g==p==label for g,p in zip(gold,pred))
        extra=sum(p==label and g!=label for g,p in zip(gold,pred))
        missing=sum(g==label and p!=label for g,p in zip(gold,pred))
        macro.append(2*hit/max(1,2*hit+extra+missing))
        if label!='NO_CONFIDENT_SLIDE':tp+=hit;fp+=extra;fn+=missing
    return {'correct':sum(g==p for g,p in zip(gold,pred)),'total':len(gold),
        'top1_accuracy':sum(g==p for g,p in zip(gold,pred))/len(gold),
        'macro_f1_including_no_slide':statistics.mean(macro),
        'grounded_precision':tp/max(1,tp+fp),'grounded_recall':tp/max(1,tp+fn),
        'grounded_f1':2*tp/max(1,2*tp+fp+fn),
        'coverage':sum(p!='NO_CONFIDENT_SLIDE' for p in pred)/len(pred)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=PROJECT_ROOT/'outputs/evaluation/final_ca4')
    parser.add_argument('--meeting-id',default='meeting_8e464f9471b34c46ad9f4ab3a547c923')
    args=parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',args.meeting_id):parser.error('Invalid meeting ID')
    import numpy as np
    import torch
    from src.audio.asr import TranscriptSegment, _deserialise_result
    from src.fusion.semantic_alignment import load_embedding_model, iter_semantic_scores
    from src.fusion.temporal_alignment import SlideTimingInfo, timings_from_presentation_dict
    torch.set_num_threads(4)
    args.output.mkdir(parents=True,exist_ok=True)
    ids,texts,cases=fixtures()
    (args.output/'controlled_cases.json').write_text(json.dumps({'slides':dict(zip(ids,texts)), 'cases':cases},indent=2))
    started=time.perf_counter();model=load_embedding_model(get('ppt.embeddings.model'))
    model_seconds=time.perf_counter()-started
    started=time.perf_counter();keys=np.asarray(model.encode(texts,show_progress_bar=False),dtype=np.float32)
    rows=list(iter_semantic_scores([c['text'] for c in cases],keys,model));encode_seconds=time.perf_counter()-started
    segments=[TranscriptSegment(i+1,c['start'],c['end'],'SPEAKER_TEST',c['text']) for i,c in enumerate(cases)]
    times=[[SlideTimingInfo(sid,0.,30.) if c['timed'] and sid==c['shown'] else SlideTimingInfo(sid,40.,70.) if c['timed'] else SlideTimingInfo(sid) for sid in ids] for c in cases]
    output={'experiment':'CA4 controlled alignment diagnostic','scope':'24 author-designed cases, six constructed slides; frozen pretrained encoder; no training/test split, no real-meeting accuracy claim',
        'model':get('ppt.embeddings.model'),'threshold':get('alignment.threshold',.3),'threads':4,
        'model_load_seconds':model_seconds,'shared_encoding_seconds':encode_seconds,'methods':{},'cases':cases,
        'fixture_sha256':hashlib.sha256((args.output/'controlled_cases.json').read_bytes()).hexdigest()}
    for strategy in ['temporal_only','semantic_only','temporal_semantic_hybrid']:
        started=time.perf_counter();results=predict(segments,ids,times,keys,rows,strategy)
        duration=time.perf_counter()-started
        predicted=[r.selected_slide for r in results]
        output['methods'][strategy]={'metrics':metrics([c['gold'] for c in cases],predicted),
            'selection_seconds':duration,'predictions':predicted,
            'by_group':{group:metrics([c['gold'] for c in cases if c['group']==group],[p for c,p in zip(cases,predicted) if c['group']==group]) for group in sorted({c['group'] for c in cases})}}
        (args.output/f'controlled_{strategy}_alignment.json').write_text(json.dumps([asdict(r) for r in results],indent=2))
    assert output['methods']['temporal_only']['by_group']['missing_slide_times']['coverage']==0
    assert all(np.asarray(rows)[-1]==0), 'Blank passage must have zero semantic scores'
    (args.output/'controlled_comparison.json').write_text(json.dumps(output,indent=2))
    # Existing real transcript/deck: compare coverage only unless independent labels exist.
    root=PROJECT_ROOT/'data/processed'
    paths=[root/'audio'/f'{args.meeting_id}_transcript.json',root/'slides'/f'{args.meeting_id}_slides.json',root/'slides'/f'{args.meeting_id}_embeddings.npy']
    transcript=_deserialise_result(json.loads(paths[0].read_text()));pdata=json.loads(paths[1].read_text());keys=np.load(paths[2])
    ids=[s['slide_id'] for s in pdata['slides']];timings=timings_from_presentation_dict(pdata)
    started=time.perf_counter();rows=list(iter_semantic_scores([s.text for s in transcript.segments],keys,model));encode_seconds=time.perf_counter()-started
    real={'meeting_id':args.meeting_id,'passages':len(transcript.segments),'slides':len(ids),
        'slides_with_valid_times':sum(t.has_timing for t in timings),'encoding_seconds':encode_seconds,
        'ground_truth_status':'independent slide-relevance labels unavailable; coverage is not accuracy',
        'input_sha256':{str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'methods':{}}
    selected={}
    for strategy in output['methods']:
        started=time.perf_counter();results=predict(transcript.segments,ids,[timings]*len(transcript.segments),keys,rows,strategy)
        selected[strategy]=[r.selected_slide for r in results]
        counts=Counter(selected[strategy]);linked=len(results)-counts.get('NO_CONFIDENT_SLIDE',0)
        real['methods'][strategy]={'linked_passages':linked,'coverage':linked/max(1,len(results)),
            'selection_seconds':time.perf_counter()-started,'top1_accuracy':None,'f1':None,
            'predicted_slide_counts':dict(counts)}
    real['semantic_hybrid_agreement']=sum(a==b for a,b in zip(selected['semantic_only'],selected['temporal_semantic_hybrid']))/max(1,len(transcript.segments))
    if not real['slides_with_valid_times']:
        assert real['semantic_hybrid_agreement']==1 and real['methods']['temporal_only']['linked_passages']==0
    (args.output/'real_unlabelled_comparison.json').write_text(json.dumps(real,indent=2))
    print(json.dumps({'controlled':{k:v['metrics'] for k,v in output['methods'].items()},'real':{k:v for k,v in real.items() if k not in ['input_sha256','methods']},'real_results':real['methods']},indent=2))

if __name__=='__main__':main()
