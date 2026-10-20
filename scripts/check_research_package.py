"""Check reproducible figure data, citations, manuscript structure and embedded exports."""
import json,re,subprocess,zipfile,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'professor_guidelines'
paper=(root/'RESEARCH_SUPPLEMENT.md').read_text()
abstract=paper.split('## Abstract')[1].split('Keywords:')[0]
assert 150 <= len(abstract.split()) <= 250
for heading,next_heading in [('## Abstract','Keywords:'),('## 5 Results','## 6 Discussion'),('## 7 Conclusion','## Statements')]:
 section=paper.split(heading)[1].split(next_heading)[0]
 assert not re.search(r'\[\d+\]',section),heading
assert re.findall(r'^Fig\. (\d+)\.',paper,re.M)==list('12345678')
images=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',paper);assert len(images)==8
for name in images:
 p=root/name;assert p.is_file() and p.stat().st_size>1000
 for suffix in ['.svg','.pdf']:assert p.with_suffix(suffix).exists()
refs=paper.split('## References')[1];assert re.findall(r'^\[(\d+)\]',refs,re.M)==[str(i) for i in range(1,16)]
html=(root/'RESEARCH_SUPPLEMENT.html').read_text();assert html.count('src="data:image/png;base64,')==8
with zipfile.ZipFile(root/'RESEARCH_SUPPLEMENT.docx') as z:
 assert len([p for p in z.namelist() if p.startswith('word/media/')])>=8
assert (root/'RESEARCH_SUPPLEMENT.doc').read_bytes()[:8]==bytes.fromhex('d0cf11e0a1b11ae1')
output=subprocess.check_output(['pdfimages','-list',str(root/'RESEARCH_SUPPLEMENT.pdf')],text=True)
assert len([line for line in output.splitlines() if len(line.split()) > 2 and line.split()[2] == 'image'])==8
ext=json.loads((root/'evaluation/public_extension/summary.json').read_text())
assert ext['n']==4 and ext['reference_words']==sum(r['wer']['reference_length'] for r in ext['rows'])
assert abs(ext['wer']-ext['errors']/ext['reference_words'])<1e-12
comparison=json.loads((root/'evaluation/comparative_evaluation.json').read_text())
assert len(comparison['ablations'])==8 and len(comparison['baselines'])==7
assert comparison['ablations'][0]['mean_absolute_score_change']==0
assert all(row['human_accuracy_status']=='ground_truth_unavailable' for row in comparison['baselines'])
assert all(row['spearman_vs_human'] is None for row in comparison['baselines'])
assert all(0 <= row['speech_f1'] <= 1 for row in comparison['pooled_audio_comparison'])
subprocess.run([sys.executable,str(root.parent/'scripts/check_ieee_paper.py')],check=True)
print(json.dumps({'status':'passed','supplement_embedded_figures':8,'supplement_references':15,'supplement_abstract_words':len(abstract.split()),'additional_public_samples':4,'formats':['md','html','docx','doc','pdf']}))
