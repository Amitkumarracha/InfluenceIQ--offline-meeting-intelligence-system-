"""Figures derived only from saved observations; PNG for Word, SVG/PDF for publication."""
import json,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'professor_guidelines';EV=OUT/'evaluation';FIG=OUT/'figures'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
def save(fig,name):
 fig.tight_layout()
 for ext in ('png','svg','pdf'):fig.savefig(FIG/f'{name}.{ext}',dpi=300,bbox_inches='tight')
 plt.close(fig)
def generate():
 a=json.loads((EV/'audio_summary.json').read_text())
 fig,axes=plt.subplots(1,2,figsize=(10,3.8))
 for ax,metric in zip(axes,['wer','cer']):
  for i,model in enumerate(['small','medium']):
   j=json.loads((EV/('indic_summary.json' if model=='small' else 'medium/indic_summary.json')).read_text())
   values=[j['summary'][lang][metric]*100 for lang in ['hindi','hinglish']]
   bars=ax.bar([n+(i-.5)*.36 for n in range(2)],values,.36,label=model)
   ax.bar_label(bars,fmt='%.1f',padding=3)
  ax.set_xticks([0,1],['Hindi (n=8)','Hinglish (n=8)']);ax.set_ylabel(metric.upper()+' (%)');ax.set_ylim(0,85);ax.legend()
 save(fig,'indic_errors')
 fig,ax=plt.subplots(figsize=(7,3.5));pairs=sorted((float(k),v*100) for k,v in a['development_pooled_der'].items());ax.plot(*zip(*pairs),'o-',color='#176b87');ax.axvline(.9,color='#ad4933',linestyle='--',label='Selected on development only');ax.set(xlabel='Clustering threshold',ylabel='Pooled development DER (%)',xticks=[.5,.7,.9,1.1]);ax.legend();save(fig,'calibration')
 fig,ax=plt.subplots(figsize=(8,3.5));labels=[];bottom=[0]*len(a['test'])
 for key,label,color in [('missed_speech_rate','Missed speech','#477da7'),('false_alarm_rate','False alarm','#e3ae57'),('speaker_error_rate','Speaker confusion','#af5763')]:
  values=[r['der'][key]*100 for r in a['test']];ax.bar(range(len(values)),values,bottom=bottom,label=label,color=color);bottom=[x+y for x,y in zip(bottom,values)]
 ax.set_xticks(range(len(bottom)),[r['meeting']+'\nthreshold '+str(r['threshold']) for r in a['test']]);ax.set_ylabel('DER components (%)');ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1.2));save(fig,'der_components')
 fig,ax=plt.subplots(figsize=(10,6));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
 boxes=[(0.2,4.7,'Browser / Android clients\nCapture, import, review'),(3.6,4.7,'Local API + single worker\nAuth, ownership, job state'),(7,4.7,'Local persistence\nSQLite, recordings, reports'),(.2,2.7,'Saved audio → FFmpeg\nMono PCM + ASR word cache'),(3.6,2.7,'Offline speech analysis\nWhisper + global diarization'),(7,2.7,'PPTX extraction\nText, tables, optional OCR'),(.2,.7,'Live preview branch\n15s windows; busy → disclose'),(3.6,.7,'NLP + presentation alignment\nEvents, evidence, decision chains'),(7,.7,'Human review + export\nNames, roles, influence evidence')]
 for x,y,label in boxes:
  ax.add_patch(FancyBboxPatch((x,y),2.8,.9,boxstyle='round,pad=.06',facecolor='#e6f1f5',edgecolor='#356779'));ax.text(x+1.4,y+.45,label,ha='center',va='center',fontsize=9)
 for start,end in [((3,5.15),(3.5,5.15)),((6.4,5.15),(6.9,5.15)),((1.6,4.7),(1.6,3.65)),((3,3.15),(3.5,3.15)),((5,4.7),(5,3.65)),((5,2.7),(5,1.65)),((8.4,2.7),(6.4,1.3)),((6.4,1.15),(6.9,1.15)),((1.6,2.7),(1.6,1.65))]:ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#356779'})
 ax.text(5,.1,'All inference local after provisioning. Android has a separate native pipeline; no live speaker tracking.',ha='center',fontsize=9)
 save(fig,'system_architecture')
 fig,ax=plt.subplots(figsize=(9,3.5));ax.axis('off')
 entries=[('Freeze protocol','Select data, split groups,\nfix thresholds and metrics'),('Development','Choose threshold using\nmanual-reference DER'),('Held-out tests','Measure DER / WER;\nretain errors and hypotheses'),('Report limits','Separate functional tests\nfrom human validation')]
 for i,(title,body) in enumerate(entries):
  x=.02+i*.25;ax.text(x+.105,.6,title+'\n\n'+body,transform=ax.transAxes,ha='center',va='center',fontsize=9,bbox={'boxstyle':'round,pad=.7','facecolor':'#eef3e4','edgecolor':'#69854d'})
  if i<3:ax.annotate('',xy=(x+.25,.6),xytext=(x+.22,.6),xycoords='axes fraction',arrowprops={'arrowstyle':'->'})
 save(fig,'evaluation_protocol')
 with (EV/'figure_data.csv').open('w') as f:
  writer=csv.writer(f);writer.writerow(['meeting','threshold','groups','reference_speakers','der','miss','false_alarm','confusion'])
  for r in a['test']:writer.writerow([r['meeting'],r['threshold'],r['clusters'],r['reference_speakers'],*[r['der'][k] for k in ['der','missed_speech_rate','false_alarm_rate','speaker_error_rate']]])
 assert all((FIG/(name+'.png')).stat().st_size>1000 for name in ['system_architecture','indic_errors','der_components','calibration','evaluation_protocol'])
if __name__=='__main__':generate()
