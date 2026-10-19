"""Small preregistered AMI development/held-out audit; no annotations enter inference."""
import sys,json,time,subprocess,resource,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT,get
from src.utils.cache import atomic_json
from src.audio.onnx_diarization import diarize
from src.audio.asr import run_asr
from src.evaluation.metrics import calculate_der,calculate_wer
from src.utils.text import words
ROOT=PROJECT_ROOT
OUT=ROOT/'professor_guidelines/evaluation'
WORK=ROOT/'.runtime/research-evaluation';WORK.mkdir(parents=True,exist_ok=True)
# Frozen before inference. Speaker groups differ across development/test meetings.
SPLITS={'development':['ES2002a','ES2003a'], 'test':['IS1001b','TS3007d']}
THRESHOLDS=[.5,.7,.9,1.1]
START=60;DURATION=120

def reference(meeting):
    base=ROOT/'AMI_dataset/annotations/ami_public_manual_1.6.2'
    transcript=[]; turns=[]
    for file in sorted((base/'words').glob(f'{meeting}.*.words.xml')):
        speaker=file.name.split('.')[1]
        for word in ET.parse(file).getroot():
            if word.tag.rsplit('}',1)[-1]=='w' and word.get('punc')!='true' and word.text:
                start=float(word.get('starttime',-1))
                if START<=start<START+DURATION:transcript.append((start,word.text))
        segfile=base/'segments'/f'{meeting}.{speaker}.segments.xml'
        for item in ET.parse(segfile).getroot():
            start=float(item.get('transcriber_start',-1));end=float(item.get('transcriber_end',-1))
            if end>START and start<START+DURATION:
                turns.append({'start':max(0,start-START),'end':min(DURATION,end-START),'speaker':speaker})
    return ' '.join(words(' '.join(text for _,text in sorted(transcript)))),turns

def clip(meeting):
    output=WORK/(meeting+'.wav')
    if not output.exists():
        source=ROOT/f'AMI_dataset/audio/Array1-01/{meeting}/audio/{meeting}.Array1-01.wav'
        subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-ss',str(START),'-t',str(DURATION),'-i',str(source),'-ar','16000','-ac','1',str(output)],check=True)
    return output

def evaluate(meeting,threshold,split):
    saved=OUT/f'ami_{meeting}_threshold_{threshold}.json'
    if saved.exists():return json.loads(saved.read_text())
    truth,turns=reference(meeting); audio=clip(meeting)
    def settings(key,default=None):return threshold if key=='diarization.onnx.cluster_threshold' else get(key,default)
    started=time.perf_counter()
    with patch('src.audio.onnx_diarization.get',side_effect=settings):
        result=diarize(audio)
    seconds=time.perf_counter()-started
    hypothesis=[dict(start=a,end=b,speaker=s) for a,b,s in result]
    value={'meeting':meeting,'split':split,'start':START,'duration':DURATION,'channel':'Array1-01','threshold':threshold,
           'clusters':len({s for _,_,s in result}),'reference_speakers':len({s['speaker'] for s in turns}),
           'der':calculate_der(turns,hypothesis,duration=DURATION),'diarization_seconds':seconds,'rtf':seconds/DURATION,
           'peak_process_rss_mb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
           'reference_protocol':'AMI manual speech segments, 0.25s collar, overlap included, optimal speaker mapping, excerpt UEM',
           'hypothesis':hypothesis}
    atomic_json(saved,value); print(json.dumps({k:v for k,v in value.items() if k!='hypothesis'}),flush=True)
    return value

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    atomic_json(OUT/'audio_protocol.json',{'splits':SPLITS,'threshold_grid':THRESHOLDS,'start':START,'seconds':DURATION,
      'selection':'Minimum development pooled DER; ties choose lower threshold; tests not used for selection',
      'scope':'Small English AMI pilot; segments can include internal silence; not an official full-corpus benchmark'})
    development=[evaluate(m,t,'development') for t in THRESHOLDS for m in SPLITS['development']]
    def pooled(t):
        rows=[r for r in development if r['threshold']==t]
        return sum(r['der']['der']*r['der']['total_reference_duration'] for r in rows)/sum(r['der']['total_reference_duration'] for r in rows)
    selected=min(THRESHOLDS,key=lambda t:(pooled(t),t))
    heldout=[evaluate(m,t,'test') for t in sorted({.5,selected}) for m in SPLITS['test']]
    asr=[]
    for meeting in SPLITS['test']:
        reference_text,_=reference(meeting);audio=clip(meeting);empty=WORK/'unknown.json';atomic_json(empty,{'segments':[]})
        started=time.perf_counter()
        result,_,_=run_asr(audio,empty,'research_'+meeting,WORK,options={'model_size':'small','language':None})
        seconds=time.perf_counter()-started
        hypothesis=' '.join(words(' '.join(s.text for s in result.segments)))
        asr.append({'meeting':meeting,'wer':calculate_wer(reference_text,hypothesis),'elapsed_seconds':seconds,'rtf':seconds/DURATION,'model':'small','device':'cpu','compute_type':'int8','reference':reference_text,'hypothesis':hypothesis})
    atomic_json(OUT/'audio_summary.json',{'selected_threshold':selected,'development_pooled_der':{str(t):pooled(t) for t in THRESHOLDS},'test':heldout,'asr':asr,'limits':['Two development and two different held-out meeting groups, 120s each; not a full-corpus claim.','Long uploaded recording has no verified reference.','ASR ordered overlapping reference words; not speaker-attributed WER.','Native model initialization included in timing; RSS is cumulative process peak.']})
if __name__=='__main__':main()
