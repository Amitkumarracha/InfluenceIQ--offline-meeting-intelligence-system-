"""Frozen four-row MUCS extension; public download then local inference, no training."""
import sys,json,hashlib,time,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from src.audio.asr import run_asr
from src.evaluation.metrics import calculate_wer
from src.utils.text import words
from src.utils.cache import atomic_json
root=Path(__file__).resolve().parents[1];out=root/'professor_guidelines/evaluation/public_extension';out.mkdir(parents=True,exist_ok=True)
work=root/'.runtime/research-evaluation/public_extension';work.mkdir(parents=True,exist_ok=True)
protocol={'dataset':'dianavdavidson/MUCS-Hinglish','indices':[100,400,800,1200],'split':'test','model':'small','selection':'Fixed spaced row indices before inference; not random or full-corpus evaluation','original_license':'CC-BY-SA-4.0','mirror_declared_license':'CC-BY-4.0','source':'https://www.openslr.org/104/','note':'Original source license governs; do not rely on conflicting mirror metadata.'}
atomic_json(out/'protocol.json',protocol)
empty=work/'unknown.json';atomic_json(empty,{'segments':[]});rows=[]
for index in protocol['indices']:
 saved=out/f'{index}.json'
 if saved.exists():rows.append(json.loads(saved.read_text()));continue
 response=requests.get('https://datasets-server.huggingface.co/rows',params={'dataset':protocol['dataset'],'config':'default','split':'test','offset':index,'length':1},timeout=60);response.raise_for_status();row=response.json()['rows'][0]['row']
 response=requests.get(row['audio'][0]['src'],timeout=60);response.raise_for_status();source=work/f'{index}.audio';source.write_bytes(response.content)
 audio=work/f'{index}.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','16000','-ac','1',str(audio)],check=True)
 t=time.perf_counter();result,_,_=run_asr(audio,empty,f'extension_{index}',work,options={'model_size':'small','language':None});elapsed=time.perf_counter()-t
 ref=' '.join(words(row['transcript']));hyp=' '.join(words(' '.join(s.text for s in result.segments)))
 value={'index':index,'segment_id':row['segment_id'],'speaker_id':row['speaker_id'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'reference':ref,'hypothesis':hyp,'wer':calculate_wer(ref,hyp),'seconds':result.duration,'processing_seconds':elapsed}
 atomic_json(saved,value);rows.append(value);print(index,value['wer'],flush=True)
errors=sum(sum(r['wer'][k] for k in ['substitutions','deletions','insertions']) for r in rows);n=sum(r['wer']['reference_length'] for r in rows)
atomic_json(out/'summary.json',{'n':len(rows),'wer':errors/n,'errors':errors,'reference_words':n,'rows':rows,'scope':'Additional exploratory diagnostic, not independent validation of influence or whole meetings'})
