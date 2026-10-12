"""Build the final CA4 report, figures and cumulative PDF record from local evidence."""
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.utils.config import PROJECT_ROOT

SUBMITTED=PROJECT_ROOT/'docs/submitted'
SOURCE=SUBMITTED/'Multimodal AI Mini Project Continuous Assessment 4.md'
ASSETS=SUBMITTED/'final_report_assets'


def read(path):return json.loads((PROJECT_ROOT/path).read_text())


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    ASSETS.mkdir(parents=True,exist_ok=True)
    def save(fig,name):
        fig.savefig(ASSETS/f'{name}.png',bbox_inches='tight',facecolor='white')
        fig.savefig(ASSETS/f'{name}.pdf',bbox_inches='tight',facecolor='white')
        plt.close(fig)
    counts=read('outputs/evaluation/final_ca4/eda_inventory.json')['dialogue_act_counts']
    labels=list(counts)[:7]+['Remaining eight categories'];values=list(counts.values())[:7]+[sum(list(counts.values())[7:])]
    fig,ax=plt.subplots(figsize=(8,3.3));bars=ax.barh(labels[::-1],values[::-1],color='#326481')
    for bar,val in zip(bars,values[::-1]):ax.text(val+250,bar.get_y()+bar.get_height()/2,f'{val:,}',va='center',fontsize=9)
    ax.set_xlim(0,max(values)*1.22);ax.set_xlabel('Dialogue-act count (manual XML enumeration)');save(fig,'eda_distribution')
    result=read('outputs/evaluation/final_ca4/controlled_comparison.json')
    methods=list(result['methods']);metrics=[result['methods'][m]['metrics'] for m in methods]
    fig,ax=plt.subplots(figsize=(8,3.6));x=np.arange(3)
    for shift,key,label,col in [(-.24,'top1_accuracy','Top-1 correctness','#326481'),(0,'grounded_f1','Grounded F1','#46785d'),(.24,'coverage','Coverage','#bb8545')]:
        values=[m[key]*100 for m in metrics];bars=ax.bar(x+shift,values,width=.22,label=label,color=col)
        ax.bar_label(bars,labels=[f'{v:.1f}' for v in values],padding=3,fontsize=8)
    ax.set_xticks(x,['Temporal only','Semantic only','Temporal + semantic']);ax.set_ylim(0,118);ax.set_ylabel('Percentage / F1 × 100');ax.legend(loc='upper left',ncol=3,fontsize=9)
    ax.set_title('Controlled diagnostic: 24 authored cases, six constructed slides',fontsize=11);save(fig,'fusion_comparison')
    report=read('outputs/reports/meeting_288ab746_report.json');rows=sorted(report['influence_vs_speaking'],key=lambda r:r['speaking_rank'])
    fig,ax=plt.subplots(figsize=(8,3.5));x=np.arange(len(rows));duration=[r['speaking_duration_s'] for r in rows];score=[r['influence_score'] for r in rows]
    ax.bar(x-.18,np.array(duration)/max(duration),width=.36,color='#326481',label='Historical duration proxy / maximum')
    ax.bar(x+.18,np.array(score)/max(score),width=.36,color='#bb8545',label='Heuristic influence / maximum')
    ax.set_xticks(x,[r['participant'].replace('SPEAKER_','S') for r in rows]);ax.set_ylabel('Separately normalized fields');ax.set_ylim(0,1.2);ax.legend(fontsize=9,ncol=2)
    ax.set_title('Historical CA3 example: different rank definitions, not human validation',fontsize=11);save(fig,'historical_influence')
    runs=read('outputs/evaluation/maintenance_pipeline_timing.json');stages=['diarization','transcription','slides','alignment'];fig,axes=plt.subplots(1,2,figsize=(8,3.6))
    for ax,run in zip(axes,runs):
        timings=run['processing']['stage_timings_seconds'];ax.bar(['Speakers','ASR','Slides','Align'],[timings[k] for k in stages],color='#326481');ax.tick_params(axis='x',rotation=20);ax.set_ylabel('Seconds');ax.set_title('Fresh inference artifacts' if run['run']=='fresh_input' else 'Same-ID cached repeat',fontsize=10)
    fig.tight_layout();save(fig,'processing_times')
    fig,ax=plt.subplots(figsize=(8,5.2));ax.set_axis_off()
    boxes=[(.04,.76,.42,.19,'AUDIO / SPEECH','Local decode → 16 kHz mono\nSpeaker clusters + pretrained ASR\nTimestamped, attributed passages'),
           (.54,.76,.42,.19,'PRESENTATION / DOCUMENT','Native title, body, tables, notes\nFrozen text embeddings or TF-IDF\nReal display times only when supplied'),
           (.16,.47,.68,.2,'ALIGNMENT / LATE SCORE FUSION','Temporal-only | Semantic-only | Combined\nThreshold / no-slide sentinel / source IDs'),
           (.16,.2,.68,.2,'DETERMINISTIC NLP / REVIEW','Events → evidence → candidate decisions → interactions\nWeighted contribution estimates, timestamps and history'),
           (.16,.015,.68,.115,'APPLICATION OUTPUT','Python: web/API/history/exports · Android: native offline analysis')]
    from matplotlib.patches import FancyBboxPatch
    for x,y,w,h,title,body in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.01',facecolor='#f0f5f7',edgecolor='#326481',linewidth=1.2))
        ax.text(x+w/2,y+h-.035,title,ha='center',va='top',fontsize=10,fontweight='bold',color='#203e53')
        ax.text(x+w/2,y+.045,body,ha='center',va='bottom',fontsize=9,linespacing=1.5)
    for start,end in [((.25,.75),(.37,.68)),((.75,.75),(.63,.68)),((.5,.46),(.5,.41)),((.5,.19),(.5,.14))]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#326481','lw':1.5})
    save(fig,'architecture')
    fig,axes=plt.subplots(1,3,figsize=(8,5.1))
    for ax,name,label in zip(axes,['participants','analysis','presentation'],['Editable participants','Influence / source evidence','Native presentation links']):
        ax.imshow(plt.imread(PROJECT_ROOT/f'android/design/analysis/{name}.png'));ax.set_axis_off();ax.set_title(label,fontsize=9)
    fig.tight_layout();save(fig,'android_analysis')


STYLE='''
@page { size:A4; }
* { box-sizing:border-box; }
body { margin:0; color:#1d2730; font:11pt/1.33 "Liberation Serif", "Times New Roman", serif; }
h1,h2,h3 { font-family:"DejaVu Sans",Arial,sans-serif; color:#203e53; }
h1 { font-size:24pt; line-height:1.25; margin:22mm 0 10mm; }
h2 { font-size:17pt; line-height:1.25; margin:0 0 7mm; break-before:page; }
h3 { font-size:12pt; margin:5mm 0 3mm; break-after:avoid; }
p { margin:0 0 3mm; orphans:3; widows:3; }
a { color:#245c80; text-decoration:none; overflow-wrap:anywhere; }
.cover { break-after:page; text-align:center; padding:3mm 0; }
.cover h1 { border-bottom:2px solid #326481; padding-bottom:8mm; }
.cover table { font:11pt/1.4 "Liberation Serif",serif; margin:8mm auto; width:90%; }
.cover p:last-child { margin-top:9mm; font-size:10pt; }
nav { break-after:page; }
nav h2 { break-before:auto; }
nav ol { list-style:none; padding:0; }
nav li { display:flex; justify-content:space-between; gap:5mm; margin:2.2mm 0; font:10.5pt/1.3 "DejaVu Sans",Arial,sans-serif; }
nav li a { color:#203e53; }
nav small { font-family:"Liberation Serif",serif; }
table { border-collapse:collapse; width:100%; table-layout:fixed; font-size:9.2pt; line-height:1.28; margin:4mm 0 5mm; }
th,td { border:1px solid #b6c7d0; padding:1.8mm; vertical-align:top; overflow-wrap:anywhere; }
th { background:#edf3f6; font-weight:bold; color:#203e53; }
thead { display:table-header-group; }
tr { break-inside:avoid; }
table:has(th:nth-child(6)) { font-size:8.8pt; }
table:has(th:nth-child(6)) th:first-child { width:24%; }
table:has(th:nth-child(7)) th:first-child { width:24%; }
img { display:block; max-width:100%; max-height:180mm; height:auto; margin:5mm auto 2mm; }
p:has(>img) { break-inside:avoid; }
p:has(>em:only-child) { font-size:9pt; color:#465560; }
pre { white-space:pre-wrap; overflow-wrap:anywhere; font-size:8.3pt; line-height:1.38; background:#f4f6f7; padding:3mm; border-left:2px solid #326481; break-inside:avoid; }
code { font-family:"DejaVu Sans Mono",monospace; font-size:.83em; overflow-wrap:anywhere; }
ol,ul { padding-left:6mm; margin:2mm 0 4mm; }
li { margin-bottom:2mm; }
'''


def render_html():
    from markdown_it import MarkdownIt
    source=SOURCE.read_text()
    assert source.strip() and all(x in source for x in ['Group 12','23070126015','24070126501','23070126112','23070126125'])
    parser=MarkdownIt('commonmark',{'html':False}).enable('table')
    tokens=parser.parse(source);headings=[]
    for i,token in enumerate(tokens):
        if token.type=='heading_open' and token.tag=='h2':
            anchor=f'section-{len(headings)+1}';token.attrSet('id',anchor)
            headings.append({'id':anchor,'title':tokens[i+1].content})
    rendered=parser.renderer.render(tokens,parser.options,{}).replace('src="final_report_assets/', 'src="')
    cut=rendered.index('<h2');cover=rendered[:cut];body=rendered[cut:]
    toc='<nav><h2>Contents</h2><ol>'+''.join(f'<li><a href="#{h["id"]}">{html.escape(h["title"])}</a><span data-page="{h["id"]}"></span></li>' for h in headings)+'</ol><small>One cumulative group report. The supporting record PDF appends earlier submissions unchanged.</small></nav>'
    result='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Group 12 — Final Multimodal AI Report</title><style>'+STYLE+'</style></head><body><section class="cover">'+cover+'</section>'+toc+body+'</body></html>'
    target=SUBMITTED/'final_report_assets/Group12_Final_Report.html';target.write_text(result)
    (ASSETS/'headings.json').write_text(json.dumps(headings,indent=2))
    for image in re.findall(r'!\[[^]]*\]\(([^)]+)\)',source):assert (SUBMITTED/image).is_file(),image
    return target


def pdf_pages(path):
    info=subprocess.run(['pdfinfo',str(path)],check=True,capture_output=True,text=True).stdout
    return int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])


def main():
    figures();evidence=ASSETS/'evidence';evidence.mkdir(exist_ok=True)
    for p in sorted((PROJECT_ROOT/'outputs/evaluation/final_ca4').glob('*.json')):shutil.copy2(p,evidence/p.name)
    for relative in ['outputs/evaluation/maintenance_alignment_batch.json','outputs/evaluation/maintenance_pipeline_timing.json','logs/maintenance_speaker_threads.json']:
        shutil.copy2(PROJECT_ROOT/relative,evidence/Path(relative).name)
    target=render_html();pdf=SUBMITTED/'Group12_Multimodal_AI_Final_Report_CA4.pdf'
    subprocess.run(['node',str(PROJECT_ROOT/'scripts/render_report_pdf.cjs'),str(target),str(pdf)],check=True,cwd=PROJECT_ROOT)
    # Page-numbered table of contents is derived from the first print, then printed again.
    text=subprocess.run(['pdftotext','-layout',str(pdf),'-'],check=True,capture_output=True,text=True).stdout
    pages=text.split('\f');headings=json.loads((ASSETS/'headings.json').read_text());doc=target.read_text()
    for heading in headings:
        title=heading['title'];page=None
        for i,content in enumerate(pages[2:],start=3):
            normalized=' '.join(content.split())
            if title in normalized or (len(title)>55 and title[:50] in normalized):page=i;break
        assert page is not None,f'Heading missing from PDF: {title}'
        doc=doc.replace(f'<span data-page="{heading["id"]}"></span>',f'<span data-page="{heading["id"]}">{page}</span>')
        heading['page']=page
    target.write_text(doc);(ASSETS/'headings.json').write_text(json.dumps(headings,indent=2))
    subprocess.run(['node',str(PROJECT_ROOT/'scripts/render_report_pdf.cjs'),str(target),str(pdf)],check=True,cwd=PROJECT_ROOT)
    originals=[SUBMITTED/name for name in ['GRPUP_NO_12_MAI_REPORT_1.pdf','Group12_Multimodal_AI_Report_2.pdf','Group12_Multimodal_AI_Report_CA3.pdf','24070126501_Literature_Review_Individual.pdf']]
    combined=SUBMITTED/'Group12_Complete_CA1_to_CA4_Record.pdf'
    subprocess.run(['pdfunite',str(pdf),*[str(p) for p in originals],str(combined)],check=True)
    assert pdf_pages(combined)==pdf_pages(pdf)+sum(pdf_pages(p) for p in originals)
    final_text=subprocess.run(['pdftotext','-layout',str(pdf),'-'],check=True,capture_output=True,text=True).stdout
    for phrase in ['23070126015','24070126501','23070126112','23070126125','83.33%','66.67%','117,887','507 tests passed']:
        assert phrase in final_text,f'Required cover/result text missing: {phrase}'
    assert '\ufffd' not in final_text,'Unicode replacement character in report'
    manifest={'date':'2026-10-10','main_submission_pdf':pdf.name,'main_pages':pdf_pages(pdf),'supporting_record_pdf':combined.name,
        'supporting_pages':pdf_pages(combined),'source_markdown':SOURCE.name,'original_sources':{p.name:{'pages':pdf_pages(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in originals},
        'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,pdf,combined]},
        'status':'Primary PDF is the one cumulative group report; combined record is optional supporting history.'}
    (ASSETS/'report_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
