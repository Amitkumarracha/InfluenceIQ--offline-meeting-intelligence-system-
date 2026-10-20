"""Local turbo comparison on fixed English development and existing Indic pilots."""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.compare_asr_quality import pooled
from scripts.evaluate_research_audio import reference, clip
from scripts.improve_decision_discussions import sha256
from src.audio.asr import run_asr
from src.utils.cache import atomic_json
from src.utils.config import PROJECT_ROOT, get
from src.utils.text import words
from src.evaluation.metrics import calculate_wer

OUT=PROJECT_ROOT/'professor_guidelines/evaluation/turbo_quality'
WORK=PROJECT_ROOT/'.runtime/turbo-quality'


def evaluate(audio, truth, name, corpus, source_hash):
    output=OUT/(name+'.json')
    if output.exists():
        row=json.loads(output.read_text());assert row['source_sha256']==source_hash
        return row
    started=time.perf_counter()
    result,_,_=run_asr(audio,WORK/'unknown.json',name,WORK,
                      options={'model_size':'large-v3-turbo','language':None})
    truth=' '.join(words(truth));hypothesis=' '.join(words(' '.join(s.text for s in result.segments)))
    row={'model':'large-v3-turbo','corpus':corpus,'sample':name,'source_sha256':source_hash,
        'reference':truth,'hypothesis':hypothesis,'wer':calculate_wer(truth,hypothesis),
        'cer':calculate_wer(' '.join(truth.replace(' ','')),' '.join(hypothesis.replace(' ',''))),
        'elapsed_seconds':time.perf_counter()-started,'detected_languages':result.detected_languages}
    atomic_json(output,row);print(name,'WER',row['wer']['wer'],'CER',row['cer']['wer'],flush=True)
    return row


def main():
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    cache=PROJECT_ROOT/'models/hf/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
    revision=(cache/'refs/main').read_text().strip()
    with (cache/'snapshots'/revision/'model.bin').open('rb') as stream:
        weight_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    atomic_json(OUT/'protocol.json',{'model':'large-v3-turbo','model_revision':revision,
        'weights_sha256':weight_hash,'language':'auto','cpu_compute_type':'int8','beam_size':get('asr.beam_size'),
        'english_dev':['ES2002a','ES2003a'],'english_historical':['IS1001b','TS3007d'],
        'indic':'Exactly the existing eight Hindi and eight Hinglish manifest samples',
        'selection':'English default eligible only if dev WER and CER do not regress vs small; report all corpora',
        'sources':['https://huggingface.co/openai/whisper-large-v3-turbo',
                   'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo'],
        'script_sha256':sha256(Path(__file__)),
        'limits':['Exploratory reused cohorts; no fresh final test.',
            'Timing may include concurrent model training and initialization; no speed superiority claim.',
            'Indic samples are tiny/correlated; reference script/boundaries remain unchanged.',
            'TS3007d incomplete reference prefix remains included; no post-hoc trimming.']})
    atomic_json(WORK/'unknown.json',{'segments':[]})
    rows=[]
    for corpus,names in [('english_dev',['ES2002a','ES2003a']),('english_historical',['IS1001b','TS3007d'])]:
        for meeting in names:
            text,_=reference(meeting);audio=clip(meeting)
            rows.append(evaluate(audio,text,'turbo_'+meeting,corpus,sha256(audio)))
    for corpus in ['hindi','hinglish']:
        manifest=json.loads((PROJECT_ROOT/f'professor_guidelines/evaluation/{corpus}_manifest.json').read_text())
        for index,sample in enumerate(manifest['samples']):
            assert sha256(PROJECT_ROOT/sample['path'])==sample['sha256']
            audio=PROJECT_ROOT/f'.runtime/research-evaluation/indic/{corpus}_{index}.wav'
            rows.append(evaluate(audio,sample['reference'],f'turbo_{corpus}_{index}',corpus,sample['sha256']))
    summary={corpus:{'n':len(chosen),'wer':pooled(chosen,'wer'),'cer':pooled(chosen,'cer')}
             for corpus in ['english_dev','english_historical','hindi','hinglish']
             for chosen in [[r for r in rows if r['corpus']==corpus]]}
    baseline=json.loads((PROJECT_ROOT/'professor_guidelines/evaluation/asr_quality/summary.json').read_text())
    small=next(r for r in baseline['models'] if r['model']=='small')
    eligible=all(summary['english_dev'][metric]['rate']<=small[metric]['rate'] for metric in ['wer','cer'])
    atomic_json(OUT/'summary.json',{'model':'large-v3-turbo','summary':summary,'passes_english_dev_gate':eligible,
        'baseline_english_dev':small,'status':'Exploratory frozen-cohort recognition comparison; no new speech-model training'})
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
