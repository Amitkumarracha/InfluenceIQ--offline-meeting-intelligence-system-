"""Small new fusion prototypes on constructed derived-text/timing cases, not app accuracy."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
import torch
from torch import nn

from scripts.compare_fusion_ca4 import metrics
from src.fusion.semantic_alignment import load_embedding_model
from src.utils.config import get


class EarlyFusion(nn.Module):
    def __init__(self,dimension):
        super().__init__()
        self.predictor=nn.Sequential(nn.Linear(2*dimension+2,32),nn.ReLU(),nn.Linear(32,1))

    def forward(self,query,slide,cues):
        return self.predictor(torch.cat([query,slide,cues],dim=1)).squeeze(1)


class IntermediateFusion(nn.Module):
    def __init__(self,dimension):
        super().__init__()
        self.query_encoder=nn.Sequential(nn.Linear(dimension,16),nn.Tanh())
        self.slide_encoder=nn.Sequential(nn.Linear(dimension,16),nn.Tanh())
        self.predictor=nn.Sequential(nn.Linear(66,16),nn.ReLU(),nn.Linear(16,1))

    def forward(self,query,slide,cues):
        a,b=self.query_encoder(query),self.slide_encoder(slide)
        return self.predictor(torch.cat([a,b,torch.abs(a-b),a*b,cues],dim=1)).squeeze(1)


def grouped_case_folds(cases):
    groups=np.array([' '.join(c['text'].lower().split()) for c in cases])
    for train,test in GroupKFold(n_splits=4).split(np.arange(len(cases)),groups=groups):
        assert set(groups[train]).isdisjoint(groups[test])
        yield train,test


def main():
    started=time.perf_counter();torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    source=ROOT/'outputs/evaluation/final_ca4/controlled_cases.json'
    data=json.loads(source.read_text());cases=data['cases'];ids=list(data['slides']);count=len(ids)
    out=ROOT/'results/fusion_architecture_experiment';out.mkdir(parents=True,exist_ok=True)
    encoder=load_embedding_model(get('ppt.embeddings.model'))
    encoded=np.asarray(encoder.encode([c['text'] for c in cases]+list(data['slides'].values()),
        show_progress_bar=False,normalize_embeddings=True),dtype=np.float32)
    queries=encoded[:len(cases)];slides=encoded[len(cases):]
    for i,c in enumerate(cases):
        if not c['text'].strip():queries[i]=0
    query=np.repeat(queries,count,axis=0);slide=np.tile(slides,(len(cases),1))
    cues=np.array([[float(c['timed'] and sid==c['shown']),float(c['timed'])] for c in cases for sid in ids],dtype=np.float32)
    target=np.array([float(c['gold']==sid) for c in cases for sid in ids],dtype=np.float32)
    cosine=np.sum(query*slide,axis=1).reshape(-1,1)
    inputs=[torch.from_numpy(x) for x in [query,slide,cues]]
    predictions={k:[None]*len(cases) for k in ['early','intermediate','late']}
    scores={k:np.zeros((len(cases),count)) for k in predictions}
    durations={k:0. for k in predictions};protocol_folds=[];parameter_counts={}
    for fold,(train_cases,test_cases) in enumerate(grouped_case_folds(cases),1):
        train=np.concatenate([np.arange(i*count,(i+1)*count) for i in train_cases])
        test=np.concatenate([np.arange(i*count,(i+1)*count) for i in test_cases])
        assert set(train).isdisjoint(test) and target[train].sum()>0
        protocol_folds.append({'fold':fold,'training_cases':[cases[i]['id'] for i in train_cases],
                               'evaluation_cases':[cases[i]['id'] for i in test_cases]})
        train_x=[x[train] for x in inputs];test_x=[x[test] for x in inputs]
        labels=torch.from_numpy(target[train]);positive=labels.sum()
        loss=nn.BCEWithLogitsLoss(pos_weight=(len(labels)-positive)/positive)
        for name,architecture in [('early',EarlyFusion),('intermediate',IntermediateFusion)]:
            t=time.perf_counter();torch.manual_seed(42+fold)
            model=architecture(query.shape[1]);parameter_counts[name]=sum(p.numel() for p in model.parameters())
            optimizer=torch.optim.Adam(model.parameters(),lr=.01,weight_decay=.001)
            model.train()
            for _ in range(120):
                optimizer.zero_grad();value=loss(model(*train_x),labels);value.backward();optimizer.step()
            model.eval()
            with torch.no_grad():probability=torch.sigmoid(model(*test_x)).numpy()
            scores[name][test_cases]=probability.reshape(-1,count)
            durations[name]+=time.perf_counter()-t
        t=time.perf_counter()
        semantic=LogisticRegression(C=1.,class_weight='balanced',random_state=42).fit(cosine[train],target[train])
        temporal=LogisticRegression(C=1.,class_weight='balanced',random_state=42).fit(cues[train],target[train])
        semantic_p=semantic.predict_proba(cosine[test])[:,1];temporal_p=temporal.predict_proba(cues[test])[:,1]
        probability=np.where(cues[test,1]>0,.5*semantic_p+.5*temporal_p,semantic_p)
        scores['late'][test_cases]=probability.reshape(-1,count)
        durations['late']+=time.perf_counter()-t
        print(f'Completed fold {fold}/4',flush=True)
    gold=[c['gold'] for c in cases];methods={};records=[]
    descriptions={
        'early':'Concatenate frozen passage/slide embeddings and timing cues, then train a 32-unit MLP.',
        'intermediate':'Train separate 16-unit passage/slide projections; fuse representations, differences/products and timing cues in a prediction head.',
        'late':'Fit separate semantic-cosine and timing logistic experts; average probabilities when timing exists, otherwise use semantic probability.'}
    for name in predictions:
        for i,row in enumerate(scores[name]):
            predictions[name][i]=ids[int(row.argmax())] if float(row.max())>=.5 else 'NO_CONFIDENT_SLIDE'
            records.append({'method':name,'case_id':cases[i]['id'],'case_group':cases[i]['group'],
                'gold':gold[i],'prediction':predictions[name][i],'best_pair_probability':float(row.max()),
                **{sid:float(p) for sid,p in zip(ids,row)}})
        measured=metrics(gold,predictions[name])
        methods[name]={'implementation':descriptions[name],'metrics':measured,
            'fit_and_predict_seconds_across_folds':durations[name],
            'predictions':predictions[name],
            'by_case_group':{g:metrics([gold[i] for i,c in enumerate(cases) if c['group']==g],
                [predictions[name][i] for i,c in enumerate(cases) if c['group']==g]) for g in sorted({c['group'] for c in cases})}}
    result={'status':'NEW CONSTRUCTED-CASE PROTOTYPE EXPERIMENT — NOT DEPLOYED-SYSTEM ACCURACY',
        'simulated_metrics':False,'cases':len(cases),'candidate_slides':count,
        'unique_passage_groups':len({' '.join(c['text'].lower().split()) for c in cases}),
        'scope':'Derived transcript/document text embeddings plus timing, not raw acoustic/image fusion. No real meeting labels.',
        'protocol':{'folds':protocol_folds,'grouping':'All identical normalized passage texts stay in the same fold.',
            'seed':42,'neural_epochs':120,'optimizer':'Adam lr=0.01 weight_decay=0.001',
            'pair_acceptance_threshold':.5,'hyperparameter_search':False,'encoder':'Frozen all-MiniLM-L6-v2',
            'class_weight':'Training-fold balanced loss / logistic weights','neural_parameter_counts':parameter_counts},
        'methods':methods,'elapsed_seconds':time.perf_counter()-started,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations':['Only 24 previously examined author-designed cases; 13 unique passage texts and one fixed six-slide catalog.',
            'No independent real-meeting or unseen-slide evaluation; no ASR or raw image/acoustic features.',
            'One seed, fixed hyperparameters/threshold, different architecture sizes; not an optimized or capacity-matched benchmark.',
            'Late experts receive engineered similarity/timing cues; neural prototypes receive embeddings/timing.',
            'Exploratory prototypes are not installed in the application and do not establish a general winner.']}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'predictions.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    with (out/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['method','correct','total','top1_accuracy','grounded_precision','grounded_recall','grounded_f1','coverage','fit_and_predict_seconds'])
        writer.writeheader()
        for name,v in methods.items():writer.writerow({'method':name,**{k:v['metrics'][k] for k in ['correct','total','top1_accuracy','grounded_precision','grounded_recall','grounded_f1','coverage']},'fit_and_predict_seconds':durations[name]})
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(12,6.2));names=list(methods);colors=['#087f8c','#5267aa','#bd6a2d']
    for ax,key,title in [(axes[0],'top1_accuracy','Slide selection / abstention correctness'),(axes[1],'grounded_f1','Grounded-link F1')]:
        values=[methods[n]['metrics'][key]*100 for n in names]
        bars=ax.bar([n.title() for n in names],values,color=colors);ax.bar_label(bars,fmt='%.2f%%',padding=4)
        ax.set(ylim=(0,110),ylabel='Percent',title=title);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('Early / intermediate / late: constructed-case prototype experiment',fontsize=15,fontweight='bold')
    fig.tight_layout(rect=(0,.24,1,.92))
    fig.text(.04,.04,'ACTUAL PROTOTYPE OUTPUTS — NOT REAL-MEETING OR DEPLOYED-SYSTEM ACCURACY\n24 constructed cases; four folds grouped by identical passage text; frozen text embeddings + timing.\nDifferent model capacities/representations; one seed; no tuning; no raw audio/image fusion.\nNumbers must not be presented as a validated architectural superiority claim.',fontsize=10,color='#8f3529')
    for extension in ['png','svg','pdf']:fig.savefig(out/('early_intermediate_late_comparison.'+extension),dpi=220)
    plt.close(fig)
    readme=['# Early, intermediate and late fusion: prototype outputs','',result['status'],'',result['scope'],'',
        'These are actual newly computed predictions, not invented showcase values. They use the existing constructed cases, not independently labelled real meetings.','',
        '| Prototype | Correct / total | Top-1 | Grounded F1 |','| --- | ---: | ---: | ---: |']
    for name,v in methods.items():
        m=v['metrics'];readme.append(f'| {name} | {m["correct"]}/{m["total"]} | {m["top1_accuracy"]:.2%} | {m["grounded_f1"]:.2%} |')
    readme+=['','## Implementations','']+[f'- **{n}:** {d}' for n,d in descriptions.items()]+['','## Limitations','']+['- '+x for x in result['limitations']]+['',
        'Regenerate: `.venv/bin/python scripts/compare_fusion_architectures.py`. Inspect `predictions.csv`, `comparison.csv` and `results.json`. Original saved application evaluations are unchanged.']
    (out/'README.md').write_text('\n'.join(readme)+'\n')
    (out/'index.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Fusion prototype experiment</title><body style="font:18px system-ui;max-width:1100px;margin:30px auto"><h1>Early / intermediate / late: prototype experiment</h1><p><strong>24 constructed cases, not real-meeting or deployed-system accuracy. Actual computed outputs; no invented values.</strong></p><img style="width:100%" src="early_intermediate_late_comparison.png"><p><a href="results.json">Protocol and results</a> · <a href="comparison.csv">Metric table</a> · <a href="predictions.csv">Every prediction</a> · <a href="README.md">Explanation and limitations</a></p></body></html>')
    assert all(len(m['predictions'])==24 for m in methods.values())
    print(json.dumps({n:v['metrics'] for n,v in methods.items()},indent=2))


if __name__=='__main__':main()
