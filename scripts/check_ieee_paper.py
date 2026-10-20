"""Check IEEE document structure, measurement fidelity and typeset output."""
import json
import re
import subprocess
import zipfile
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

from build_ieee_paper import blocks, FOLDER, W


def check():
    source=(FOLDER/'RESEARCH_PAPER.md').read_text();items=blocks(source)
    identities=['Anushka Chatterjee','Amitkumar Racha','Sahil Awatramani','Shriyans Sahoo',
                'Symbiosis Institute of Technology, Pune','Dr. Nivedita Mishra',
                '23070126015','24070126501','23070126112','23070126125',
                'anushkac2311@gmail.com','rachaamitkumar@gmail.com','sahilawatramani@gmail.com',
                'shriyanssahoo2005@gmail.com','nivedita.mishra@sitpune.edu.in']
    assert all(value in source for value in identities)
    assert 'Author names pending confirmation' not in source
    abstract=next(items[i+1][1] for i,(k,v) in enumerate(items) if k=='section' and v=='Abstract')
    assert 150 <= len(abstract.split()) <= 250
    assert not re.search(r'\[\d+\]',abstract)
    refs=[v for k,v in items if k=='reference']
    assert [int(re.match(r'\[(\d+)\]',r)[1]) for r in refs] == list(range(1,16))
    body=source.split('## References')[0]
    assert list(dict.fromkeys(map(int,re.findall(r'\[(\d+)\]',body))))==list(range(1,16))
    assert len(source.split('Index Terms—')[1].split('\n')[0].split(';'))==5
    assert re.findall(r'^## ([IVX]+)\.',source,re.M)==['I','II','III','IV','V','VI','VII']
    tables=[v for k,v in items if k=='table'];assert len(tables)==4
    expected=[['Training','29','20,339','5,862'],['Development','6','3,739','1,117'],['Historical','12','11,136','2,481']]
    assert tables[0][1:]==expected
    ev=FOLDER/'evaluation';load=lambda name:json.loads((ev/name).read_text())
    comparisons=load('classifier_comparison/summary.json')['models']
    pipeline=load('pipeline_improvement/summary.json')['test']
    families=['logistic_regression','complement_nb','linear_svm','random_forest']
    selected=[next(row['test'] for row in comparisons if row['method']==family+'__'+feature)
              for feature in ['local','context_40'] for family in families]+[pipeline]
    for row,truth in zip(tables[1][1:],selected):
        assert row[1:]==[f'{100*truth[key]:.2f}' for key in ['precision','recall','f1','average_precision']],row
    asr=load('quality_scorecard/summary.json')['asr']
    cohorts={'E-dev':'English development (2 clips)','E-hist':'English historical (2 clips)',
             'H':'Hindi (8 samples)','H-E':'Hinglish (8 samples)'}
    for row in tables[2][1:]:
        match=next(r for r in asr if r['cohort']==cohorts[row[0]] and r['model']==('large-v3-turbo' if row[1]=='turbo' else row[1]))
        assert row[2:]==[f"{100*match[key]['rate']:.2f}" for key in ['wer','cer']],row
    audio=load('comparative_evaluation.json')['pooled_audio_comparison']
    for row,key in zip(tables[3][1:],['pooled_der','pooled_jer','speech_precision','speech_recall','speech_f1','speaker_count_mae']):
        assert row[1:]==[f"{r[key]*(1 if key=='speaker_count_mae' else 100):.2f}" for r in audio],row
    tex=(FOLDER/'RESEARCH_PAPER.tex').read_text()
    with zipfile.ZipFile(FOLDER/'RESEARCH_PAPER_LATEX.zip') as archive:
        assert archive.read('RESEARCH_PAPER.tex').decode()==tex
        for name in ['IEEEtran.cls','figures/ieee_architecture.pdf','figures/ieee_classifier_results.pdf']:
            assert archive.read(name)==(FOLDER/name).read_bytes()
    assert r'\documentclass[conference,a4paper]{IEEEtran}' in tex
    assert tex.count(r'\begin{equation}')==2 and tex.count(r'\begin{table}')==4
    assert tex.count(r'\begin{figure}')==2
    log=(FOLDER/'RESEARCH_PAPER.log').read_text(errors='replace')
    assert not re.search(r'Missing character|Overfull|undefined references|undefined citations',log), 'Fix LaTeX layout/font/reference warnings'
    with zipfile.ZipFile(FOLDER/'RESEARCH_PAPER.docx') as archive:
        xml=ET.fromstring(archive.read('word/document.xml'))
        assert len([name for name in archive.namelist() if name.startswith('word/media/')])==2
        assert [node.get('{'+W+'}num') for node in xml.findall('.//{'+W+'}cols')]==['1','2']
        text=' '.join(xml.itertext())
        assert all(value in text for value in identities)
        assert 'Abstract—' in text and 'I. INTRODUCTION' in text
        assert all(value in text for value in ['53.54','28.85','57.26','63.91'])
    assert (FOLDER/'RESEARCH_PAPER.doc').read_bytes()[:8]==bytes.fromhex('d0cf11e0a1b11ae1')
    page=(FOLDER/'RESEARCH_PAPER.html').read_text()
    assert 'column-count:2' in page and page.count('src="data:image/png;base64,')==2
    info=subprocess.check_output(['pdfinfo',str(FOLDER/'RESEARCH_PAPER.pdf')],text=True)
    pages=int(re.search(r'Pages:\s+(\d+)',info)[1]);assert pages>1
    assert '(A4)' in info
    pdftext=subprocess.check_output(['pdftotext',str(FOLDER/'RESEARCH_PAPER.pdf'),'-'],text=True)
    normalised=' '.join(unicodedata.normalize('NFKC',pdftext).split())
    assert all(value in normalised for value in identities)
    assert all(value in pdftext for value in ['53.54','28.85','57.26','63.91'])
    assert 'REFERENCES' in re.sub(r'\s+','',pdftext.upper())
    assert '\ufffd' not in pdftext
    fonts=subprocess.check_output(['pdffonts',str(FOLDER/'RESEARCH_PAPER.pdf')],text=True)
    for line in fonts.splitlines()[2:]:
        assert 'Type 3' not in line,line
        assert re.search(r'\byes\s+(?:yes|no)\s+(?:yes|no)\s+\d+\s+\d+\s*$',line),line
    result={'status':'passed','format':'IEEEtran conference A4','pages':pages,'abstract_words':len(abstract.split()),
            'tables_verified_against_artifacts':4,'figures':2,'references':15,'equations':2,
            'word_columns':[1,2],'pdf_fonts_embedded':True,'latex_bundle_complete':True,
            'author_details':'Four students, affiliation, faculty guide and all five emails verified across source, Word and PDF',
            'limits':['Venue requirements and IEEE PDF eXpress certification remain unchecked.']}
    (ev/'ieee_paper/validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':check()
