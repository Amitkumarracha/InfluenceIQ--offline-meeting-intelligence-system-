#!/usr/bin/env python3
"""Validate the revised paper and recompute metrics from saved outer predictions."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import itertools
import json
import re
import subprocess
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

import numpy as np

FOLDER=Path(__file__).resolve().parent
CHECKS=[]


def check(name,condition):
    CHECKS.append({"check":name,"passed":bool(condition)})


def load(name):return json.loads((FOLDER/name).read_text())


def pct(name,value,expected):check(name,abs(float(value.replace('−','-').replace('**',''))-100*expected)<=.005000001)


def output(args):return subprocess.check_output(args,text=True)


def main():
    spec=importlib.util.spec_from_file_location("builder",FOLDER/"build_paper.py")
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    source=(FOLDER/"manuscript.md").read_text();resolved,order=builder.resolve_citations(source)
    items=builder.renderer.blocks(resolved);tables=[v for k,v in items if k=="table"]
    paragraphs='\n'.join(v for k,v in items if k=="paragraph")
    images=[v for k,v in items if k=="image"]
    check("approved title",items[0][1]=="InfluenceIQ: A Multimodal Framework for Assessing Participant Contributions to Meeting Decisions")
    check("ten main tables and seven figures",len(tables)==10 and len(images)==7)
    check("four equations",re.findall(r'^Equation \((\d+)\)',source,re.M)==['1','2','3','4'])
    check("generated source current",(FOLDER/"paper.md").read_text()==resolved and (FOLDER/"paper.tex").read_text()==builder.latex(items))
    check("23 references",len(order)==23)
    numbers=list(dict.fromkeys(re.findall(r'\[(\d+)\]',resolved.split('## References')[0])))
    check("first citations numbered 1 through 23",numbers==[str(n) for n in range(1,24)])
    for section in ['Abstract','Conclusion']:
        text=next(items[i+1][1] for i,pair in enumerate(items) if pair==('section',section))
        check("no citations in "+section,not re.search(r'\[\d+\]|\[@',text))
        if section=='Abstract':check("abstract 150 to 250 words",150<=len(text.split())<=250)
    for number in range(1,8):check("Fig. "+str(number)+" referenced",f'Fig. {number}' in paragraphs)
    for roman in ['I','II','III','IV','V','VI','VII','VIII','IX','X']:check('Table '+roman+' referenced',f'Table {roman}' in paragraphs)
    results=load('analysis/results.json');protocol=load('analysis/protocol.json');features=load('analysis/features.json')
    check("frozen protocol script hash",hashlib.sha256((FOLDER/'run_revision_analysis.py').read_bytes()).hexdigest()==protocol['script_sha256'])
    check("frozen derived feature hash",hashlib.sha256((FOLDER/'analysis/features.json').read_bytes()).hexdigest()==protocol['derived_features_sha256'])
    check("not represented as fresh evaluation",protocol['fresh_test'] is False and 'exploratory' in source.lower())
    check("84 people and 28 meetings",len(features)==84 and len({r['meeting_id'] for r in features})==28)
    covered=[]
    for fold in protocol['outer_folds']:
        fit=set(fold['train_groups']);test=set(fold['evaluation_groups']);covered.extend(test)
        check(f"outer fold {fold['fold']} complete separation",len(fit)==24 and len(test)==4 and not fit&test)
        inner_covered=[]
        for i,inner in enumerate(fold['inner_folds']):
            train=set(inner['fit_groups']);dev=set(inner['development_groups']);inner_covered.extend(dev)
            check(f"inner groups {fold['fold']}/{i}",not train&dev and train|dev==fit and not (train|dev)&test)
        check(f"inner coverage {fold['fold']}",sorted(inner_covered)==sorted(fit))
    check("each group evaluated once",len(covered)==28 and len(set(covered))==28)
    with (FOLDER/'analysis/predictions.csv').open() as stream:predictions=list(csv.DictReader(stream))
    check("84 unique outer predictions",len(predictions)==84 and len({(r['meeting_id'],r['participant']) for r in predictions})==84)
    for f,p in zip(features,predictions):check('prediction identity '+f['participant'],(f['participant'],f['meeting_id'])==(p['participant'],p['meeting_id']))
    # Independent metric implementation: no calls to the analysis scorer.
    metrics={}
    for method,record in results['scores'].items():
        observations=[]
        for group in sorted(set(covered),key=int):
            rows=[r for r in predictions if r['meeting_id']==group]
            y=[float(r['target']) for r in rows];p=[float(r[method]) for r in rows]
            pairs=[(i,j) for i,j in itertools.combinations(range(len(rows)),2) if y[i]!=y[j]]
            total=sum(.5 if p[i]==p[j] else int((p[i]-p[j])*(y[i]-y[j])>0) for i,j in pairs)
            observations.append({'meeting_id':group,'pairwise_accuracy':total/len(pairs),
                'top_set_correct':set(i for i,v in enumerate(p) if v==max(p))==set(i for i,v in enumerate(y) if v==max(y)),
                'constant_prediction':max(p)==min(p),'comparable_pairs':len(pairs)})
        m={'pairwise_accuracy':np.mean([r['pairwise_accuracy'] for r in observations]),
           'top_set_accuracy':np.mean([r['top_set_correct'] for r in observations]),
           'constant_meetings':sum(r['constant_prediction'] for r in observations),'per_meeting':observations}
        metrics[method]=m
        check('recomputed accuracy '+method,abs(m['pairwise_accuracy']-record['pairwise_accuracy'])<1e-12)
        check('recomputed top set '+method,abs(m['top_set_accuracy']-record['top_set_accuracy'])<1e-12)
        check('recomputed constants '+method,m['constant_meetings']==record['constant_meetings'])
    methods=['combined','speaking_duration','word_count','participation','prototype_fixed_weights','contribution','constant_ties']
    for row,key in zip(tables[3][1:],methods):
        pct('main Table IV pairwise '+key,row[2],metrics[key]['pairwise_accuracy'])
        top=re.fullmatch(r'(\d+)/28 \(([\d.]+)%\)',row[4])
        check('main Table IV top count '+key,int(top[1])==round(28*metrics[key]['top_set_accuracy']))
        pct('main Table IV top percent '+key,top[2],metrics[key]['top_set_accuracy'])
        check('main Table IV nonconstant '+key,int(row[5].split('/')[0])==28-metrics[key]['constant_meetings'])
        shown=[float(n) for n in re.findall(r'\d+\.\d+',row[3])]
        check('main Table IV interval '+key,np.allclose(shown,np.array(results['scores'][key]['descriptive_bootstrap_95_ci'])*100,atol=.005000001))
    check('latest 68.93 prominent in Table IV',tables[3][1][2]=='**68.93**' and 'Latest combined ridge' in tables[3][1][0])
    presentation=load('figures/presentation_manifest.json')
    for filename,digest in presentation['inputs'].items():
        check('presentation input hash '+filename,hashlib.sha256((FOLDER/filename).read_bytes()).hexdigest()==digest)
    check('presentation generator hash',hashlib.sha256((FOLDER/'build_presentation_figures.py').read_bytes()).hexdigest()==presentation['generator_sha256'])
    x=np.array([[r['features'][k] for k in protocol['feature_families']['contribution']] for r in features])
    for j,row in enumerate(tables[2][1:]):
        active=x[:,j]>0
        check('coverage people '+row[0],int(row[1].split('/')[0])==int(active.sum()))
        check('coverage meetings '+row[0],int(row[2].split('/')[0])==len({r['meeting_id'] for r,a in zip(features,active) if a}))
    check('zero-vector diagnosis',int((~np.any(x>0,axis=1)).sum())==results['participants_without_contribution_features']==70)
    indices=np.random.default_rng(protocol['seed']).integers(0,28,size=(10000,28))
    for row,(name,left,right) in zip(tables[4][1:],[('combined_minus_participation','combined','participation'),('combined_minus_word_count','combined','word_count'),('contribution_minus_participation','contribution','participation')]):
        a=np.array([r['pairwise_accuracy'] for r in metrics[left]['per_meeting']]);b=np.array([r['pairwise_accuracy'] for r in metrics[right]['per_meeting']])
        delta=a-b;ci=np.percentile(delta[indices].mean(axis=1),[2.5,97.5])
        pct('paired mean '+name,row[1],delta.mean())
        displayed=[float(n.replace('−','-')) for n in re.findall(r'[−-]?\d+\.\d+',row[2])]
        check('paired interval '+name,len(displayed)==2 and np.allclose(displayed,ci*100,atol=.005000001))
        counts=[int(n) for n in re.findall(r'\d+',row[3])]
        check('paired better/same/worse '+name,counts==[int((delta>0).sum()),int((delta==0).sum()),int((delta<0).sum())])
    initial=load('historical_records/initial_results.json')
    development=load('historical_records/initial_development.json')
    check('all fourteen original finalists',len(tables[5][1:])==len(initial['results'])==14)
    for row,key in zip(tables[5][1:],initial['results']):
        pct('historical pairwise '+key,row[2],initial['results'][key]['meeting_macro_pairwise_accuracy'])
        best=max(d['development']['meeting_macro_pairwise_accuracy'] for d in development if d['name']==key)
        pct('original development '+key,row[1],best)
    semantic=load('historical_records/semantic_results.json');semdev=load('historical_records/semantic_development.json')
    keys=[k for k in semantic['results'] if '__' in k]
    check('all twenty semantic/role finalists and four corrected variants',len(keys)==20 and len(tables[6][1:])==24)
    for row,key in zip(tables[6][1:21],keys):
        pct('later historical '+key,row[2],semantic['results'][key]['meeting_macro_pairwise_accuracy'])
        pct('later development '+key,row[1],max(d['development']['meeting_macro_pairwise_accuracy'] for d in semdev if d['name']==key))
    corrected=load('historical_records/corrected_fixed_results.json')['cohorts']
    balanced=load('historical_records/balanced_fixed_results.json')['cohorts']
    tail=[(corrected['development']['corrected_keyword'],corrected['test']['corrected_keyword']),
          (corrected['development']['corrected_keyword_topic'],corrected['test']['corrected_keyword_topic']),
          (balanced['dev']['contextual_roles_fixed_influence'],balanced['test']['contextual_roles_fixed_influence']),
          (load('historical_records/corrected_ranker_selection.json')['development'],load('historical_records/corrected_ranker_results.json')['candidate'])]
    for row,(dev,test) in zip(tables[6][21:],tail):
        pct('corrected development '+row[0],row[1],dev['meeting_macro_pairwise_accuracy'])
        pct('corrected historical '+row[0],row[2],test['meeting_macro_pairwise_accuracy'])
    # The two ablation blocks have different reference systems/interventions.
    check('eleven ablation rows',len(tables[7][1:])==11)
    full=metrics['combined']['pairwise_accuracy'];fixed=metrics['prototype_fixed_weights']['pairwise_accuracy']
    records=[(metrics[k],full) for k in ['combined','participation','contribution']]
    records.append((metrics['prototype_fixed_weights'],fixed))
    records.extend((r,fixed) for r in results['fixed_weight_deletions'])
    for row,(record,reference) in zip(tables[7][1:],records):
        pct('ablation PA '+row[0],row[1],record['pairwise_accuracy'])
        pct('ablation change '+row[0],row[2],record['pairwise_accuracy']-reference)
        check('ablation constants '+row[0],int(row[3])==record['constant_meetings'])
    classifiers=load('historical_records/discussion_classifier_comparison.json')['models']
    check('twelve supporting models',len(tables[8][1:])==12)
    for row,record in zip(tables[8][1:9],classifiers):
        pct('classifier development '+record['method'],row[3],record['dev']['f1'])
        pct('classifier historical '+record['method'],row[4],record['test']['f1'])
    discussion=load('historical_records/discussion_results.json')['metrics']
    pct('installed blend historical F1',tables[8][9][4],discussion['frozen_blend']['f1'])
    pct('neural discussion historical F1',tables[8][10][4],discussion['macro_f1'])
    for row,filename in zip(tables[8][11:],['unweighted_roles_results.json','balanced_roles_results.json']):
        pct('role historical '+filename,row[4],load('historical_records/'+filename)['metrics']['macro_f1'])
    for filename,record in load('historical_records/source_manifest.json').items():
        check('historical source hash '+filename,hashlib.sha256((FOLDER/'historical_records'/filename).read_bytes()).hexdigest()==record['sha256'])
    with (FOLDER/'analysis/model_pipeline_inventory.csv').open() as stream:inventory=list(csv.DictReader(stream))
    check('complete final-method inventory',len(inventory)==61)
    with (FOLDER/'analysis/development_search_inventory.csv').open() as stream:trials=list(csv.DictReader(stream))
    check('all 121 ranking development records',len(trials)==121)
    for experiment,filename in [('Original GAP','initial_development.json'),('Semantic/role GAP','semantic_development.json'),('Corrected XGBoost','corrected_ranker_development.json')]:
        rows=[r for r in trials if r['experiment']==experiment]
        records=load('historical_records/'+filename)
        check('development search complete '+experiment,len(rows)==len(records))
        for row,record in zip(rows,records):
            pct('development search '+experiment+'/'+row['trial'],row['development_PA_percent'],record['development']['meeting_macro_pairwise_accuracy'])
    cases=load('analysis/cases.json')
    check('three role cases',len(cases['cases'])==3)
    check('case disclosure',all('role' in r['scope'].lower() for r in cases['cases']))
    check('source-checked role outcomes',[r['emitted_event'] for r in cases['cases']]==['agreement',None,'question'])
    check('proposal diagnostic recorded',results['role_diagnostic']['rows'][0]['reference_positive']==537 and results['role_diagnostic']['rows'][0]['predicted_positive']==0)
    role=results['role_diagnostic']['rows'][1]
    check('agreement confusion arithmetic',role['true_positive']+role['false_negative']==role['reference_positive']==684 and role['true_positive']+role['false_positive']==role['predicted_positive']==80)
    supplement=(FOLDER/'SUPPLEMENT.md').read_text();supp_items=builder.renderer.blocks(supplement)
    supp_tables=[v for k,v in supp_items if k=='table']
    check('seven supplement tables',len(supp_tables)==7)
    initial_keys=['speaking_time','word_count','utterance_count','decision_count','prototype_influence','structure__ridge','structure__pairwise_logistic','structure__extra_trees','text__ridge','text__pairwise_logistic','text__extra_trees','combined__ridge','combined__pairwise_logistic','combined__extra_trees']
    for row,key in zip(supp_tables[2][1:],initial_keys):
        pct('supplement original pairwise '+key,row[1],initial['results'][key]['meeting_macro_pairwise_accuracy'])
        pct('supplement original top '+key,row[2],initial['results'][key]['top_set_accuracy'])
    ai=load('historical_records/ai_pilot_results.json')
    for row,key in zip(supp_tables[5][1:],['majority','source_only','outcome_only','paired']):
        pct('supplement AI agreement '+key,row[1],ai['methods'][key]['ai_label_agreement'])
        pct('supplement AI F1 '+key,row[2],ai['methods'][key]['macro_f1_four_classes'])
    check('AI labels remain independent-human=false',ai['independent_human_accuracy_measured'] is False)
    manifest=load('build_manifest.json')
    check('source manifest current',hashlib.sha256((FOLDER/'manuscript.md').read_bytes()).hexdigest()==manifest['source_sha256'])
    pages={}
    for stem in ['paper','supplement']:
        log=(FOLDER/(stem+'.log')).read_text(errors='replace')
        check(stem+' no overflow/missing glyph/citation error',not re.search(r'Overfull \\[hv]box|Missing character:|(?:Citation|Reference).+undefined|! LaTeX Error',log))
        info=output(['pdfinfo',str(FOLDER/(stem+'.pdf'))]);pages[stem]=int(re.search(r'Pages:\s+(\d+)',info)[1])
        fonts=output(['pdffonts',str(FOLDER/(stem+'.pdf'))])
        check(stem+' embedded fonts',all(row.split()[-5]=='yes' for row in fonts.splitlines()[2:] if row.strip()))
    pdf_text=output(['pdftotext',str(FOLDER/'paper.pdf'),'-'])
    check('PDF approved title','InfluenceIQ: A Multimodal Framework' in ' '.join(unicodedata.normalize('NFKC',pdf_text).split()))
    with zipfile.ZipFile(FOLDER/'paper.docx') as z:
        root=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        check('Word ten editable tables',len(root.findall('.//w:tbl',ns))==10)
        media=[name for name in z.namelist() if name.startswith('word/media/')]
        check('Word seven figures',len(media)==7)
        check('Word current images',{hashlib.sha256(z.read(name)).hexdigest() for name in media}=={hashlib.sha256((FOLDER/v[1]).read_bytes()).hexdigest() for v in images})
        word_text=' '.join(n.text or '' for n in root.findall('.//w:t',ns))
        check('Word inline bold rendered','**' not in word_text and bool(root.findall('.//w:b',ns)))
        for person in load('authors.json')['authors']:
            check('Word author '+person['name'],person['name'] in word_text and person['email'] in word_text)
    normalized=' '.join(unicodedata.normalize('NFKC',pdf_text).split())
    compact=re.sub(r'\s|-\s*','',normalized)
    for person in load('authors.json')['authors']:
        check('PDF author '+person['name'],person['name'] in normalized and person['email'] in compact)
    for key in ['institution','university','address']:
        check('PDF affiliation '+key,load('authors.json')[key] in normalized)
    check('PDF guide contact',load('authors.json')['faculty_guide']['email'] in compact)
    check('PDF main result present','68.93' in normalized)
    check('fresh named PDF matches canonical',(FOLDER/'InfluenceIQ_comparative_revision.pdf').read_bytes()==(FOLDER/'paper.pdf').read_bytes())
    pages_text=pdf_text.split('\f')
    reference_page=next(i for i,page in enumerate(pages_text) if re.search(r'R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S',page))
    check('tables precede bibliography',not any(re.search(r'TABLE\s+[IVX]+',page) for page in pages_text[reference_page:]))
    with zipfile.ZipFile(FOLDER/'paper_latex.zip') as z:
        check('LaTeX package current',z.read('paper.tex')==(FOLDER/'paper.tex').read_bytes())
    with zipfile.ZipFile(FOLDER/'research_package.zip') as z:
        recorded=json.loads(z.read('research_manifest.json'))
        check('research package attribution','DATA_ATTRIBUTION.txt' in z.namelist())
        for name,digest in recorded.items():
            check('research archive '+name,hashlib.sha256(z.read(name)).hexdigest()==digest and hashlib.sha256((FOLDER/name).read_bytes()).hexdigest()==digest)
    result={'status':'passed' if all(r['passed'] for r in CHECKS) else 'failed','passed':sum(r['passed'] for r in CHECKS),
        'total':len(CHECKS),'pdf_pages':pages['paper'],'supplement_pages':pages['supplement'],
        'scope':'Document, provenance and numerical consistency; not a certification of contribution validity or acceptance.',
        'notes':['Word XML checked; rendered pagination not certified.','Bootstrap intervals are descriptive; corpus reuse is exploratory.'], 'checks':CHECKS}
    (FOLDER/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','passed','total','pdf_pages','supplement_pages']},indent=2))
    for r in CHECKS:
        if not r['passed']:print('FAILED:',r['check'])
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
