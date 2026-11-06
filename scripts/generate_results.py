"""Build presentation graphs from saved results and the trusted installed model."""
import csv
import hashlib
import html
import json
from pathlib import Path
import textwrap

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'
EV = 'professor_guidelines/evaluation/'
RANKING = 'docs/paper_20261024/analysis/results.json'
CONTROLLED = 'outputs/evaluation/final_ca4/controlled_comparison.json'
REAL = 'outputs/evaluation/final_ca4/real_unlabelled_comparison.json'
COLORS = ['#087f8c', '#bd6a2d', '#5267aa', '#ba5265', '#6d8255', '#596777', '#8b5b9c']
NAMES = {'temporal_only': 'Temporal only', 'semantic_only': 'Semantic only',
         'temporal_semantic_hybrid': 'Temporal + semantic'}
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'figure.facecolor': 'white'})


def pooled_der(rows):
    """Pool by reference speaker-time, not by number of excerpts."""
    total = sum(row['der']['total_reference_duration'] for row in rows)
    if total <= 0:
        raise ValueError('Positive reference speaker-time is required')
    return sum(row['der']['der'] * row['der']['total_reference_duration'] for row in rows) / total


def confusion_metrics(counts):
    tn, fp, fn, tp = counts
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {'precision': precision, 'recall': recall,
            'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0,
            'accuracy': (tp + tn) / sum(counts)}


def generate():
    (OUT / 'graphs').mkdir(parents=True, exist_ok=True)
    (OUT / 'tables').mkdir(exist_ok=True)
    sources, graphs, tables = {}, [], []

    def source(name):
        path = ROOT / name
        sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def load(name):
        return json.loads(source(name).read_text())

    def table(name, rows):
        rows = list(rows)
        assert rows, name
        path = OUT / 'tables' / (name + '.csv')
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        tables.append(str(path.relative_to(OUT)))

    controlled, real = load(CONTROLLED), load(REAL)
    quality = load(EV + 'quality_scorecard/summary.json')
    audio = load(EV + 'audio_summary.json')
    ranking = load(RANKING)
    dataset = load(EV + 'decision_discussion/dataset_counts.json')
    model_manifest = load('models/discussion/manifest.json')
    config = yaml.safe_load(source('config/config.yaml').read_text())
    website = load('outputs/evaluation/website_regression_20261025.json')['real_pipeline']
    docker = load('outputs/evaluation/huggingface_backend_20261026.json')
    with source(EV + 'classifier_comparison/comparison.csv').open() as stream:
        classifiers = [{k: v if k == 'method' else float(v) for k, v in row.items()}
                       for row in csv.DictReader(stream)]
    model_path = source('models/discussion/model.joblib')
    assert sources['models/discussion/model.joblib'] == model_manifest['model_sha256']
    bundle = joblib.load(model_path)
    feature_names = np.concatenate([[key + ': ' + term for term in bundle['vectorizers'][key].get_feature_names_out()]
                                    for key in ('word', 'char', 'context_40')])
    linear, forest = bundle['classifiers']['linear'], bundle['classifiers']['forest']
    assert len(feature_names) == linear.n_features_in_ == forest.n_features_in_
    assert sum(quality['discussion']['installed']['confusion_matrix_tn_fp_fn_tp']) == dataset['test']['acts']
    for key, value in confusion_metrics(quality['discussion']['installed']['confusion_matrix_tn_fp_fn_tp']).items():
        assert np.isclose(value, quality['discussion']['installed'][key]), key
    for row in quality['asr']:
        for metric in ('wer', 'cer'):
            assert np.isclose(row[metric]['rate'], row[metric]['errors'] / row[metric]['reference_length'])
    for values in controlled['methods'].values():
        assert np.isclose(values['metrics']['top1_accuracy'], values['metrics']['correct'] / values['metrics']['total'])
    for values in real['methods'].values():
        assert np.isclose(values['coverage'], values['linked_passages'] / real['passages'])

    pdf = PdfPages(OUT / 'ALL_MODEL_AND_FUSION_ANALYSIS.pdf')

    def save(fig, name, title, caption, inputs):
        fig.suptitle(title, fontsize=16, fontweight='bold', color='#17324d', y=.985)
        fig.tight_layout(rect=(0, .17, 1, .93))
        fig.text(.025, .025, '\n'.join(textwrap.wrap(caption, 145)), fontsize=8.5, color='#455665', va='bottom')
        for extension in ('png', 'svg', 'pdf'):
            fig.savefig(OUT / 'graphs' / f'{name}.{extension}', dpi=210)
        pdf.savefig(fig)
        plt.close(fig)
        graphs.append({'name': name, 'title': title, 'caption': caption, 'sources': inputs,
                       'png': f'graphs/{name}.png', 'svg': f'graphs/{name}.svg', 'pdf': f'graphs/{name}.pdf'})

    def bars(ax, labels, values, ylabel, colors=None, limit=100):
        artists = ax.bar(range(len(labels)), values, color=colors or COLORS[0])
        ax.set_xticks(range(len(labels)), labels)
        ax.set_ylabel(ylabel)
        if limit is not None:
            ax.set_ylim(0, limit)
        ax.bar_label(artists, labels=[f'{value:.2f}' for value in values], padding=4, fontsize=9)
        ax.grid(axis='y', alpha=.18)
        ax.set_axisbelow(True)

    inventory = [
        ('ASR', 'Whisper Small / faster-whisper', 'Pretrained; default CPU int8', 'WER / CER pilots'),
        ('Optional ASR', 'Whisper Medium / large-v3-turbo', 'Pretrained; optional', 'WER / CER pilots'),
        ('Speakers', 'Sherpa-ONNX; pyannote-style segmentation + 3D-Speaker embedding', 'Pretrained; default backend', 'Small DER calibration pilot'),
        ('Speaker alternative', 'Python pyannote.audio backend', 'Installed alternative; not the configured default', 'Not a matched engine comparison in this collection'),
        ('Slide semantics', 'all-MiniLM-L6-v2 + cosine', 'Frozen pretrained encoder', 'Constructed alignment diagnostic; real coverage only'),
        ('Lexical alternative', 'TF-IDF cosine', 'Selectable alternative; not averaged with MiniLM', 'No matched TF-IDF vs MiniLM result shown here'),
        ('Discussion review', 'Random Forest + Logistic Regression', 'Trained English model; 75/25 ensemble', 'Historical AMI reference-act evaluation'),
        ('Events / decisions', 'Bilingual rules and source-linked reconstruction', 'Default; not a generative model', 'Historical role diagnostic; no general decision F1'),
        ('UI contribution score', 'Seven max-normalized weighted features', 'Prototype fixed weights', 'GAP outcome-proxy diagnostic; not causal validity'),
        ('Research ranking', 'Training-fold scaling + Ridge', 'Separate exploratory model', 'Grouped-CV outcome-alignment agreement'),
        ('Android path', 'whisper.cpp, native speakers and lexical TF-IDF', 'Separate native implementation', 'No matched physical-device benchmark in this collection'),
    ]
    table('model_inventory', [dict(zip(['stage', 'model_or_method', 'status', 'evaluation'], row)) for row in inventory])

    fig, ax = plt.subplots(figsize=(14, 7.5)); ax.axis('off'); ax.set(xlim=(0, 14), ylim=(0, 7))
    boxes = [(0.3,5.2,'Audio input\nFFmpeg: 16 kHz mono'), (4.9,5.2,'Whisper words + timestamps\nSherpa-ONNX speaker intervals'),
             (9.5,5.2,'Overlap attribution\nSpeaker-attributed transcript'), (0.3,2.95,'Optional PPTX\nText / tables / notes'),
             (4.9,2.95,'MiniLM + cosine\nPassage / slide similarity'), (9.5,2.95,'Temporal + semantic scores\nMissing timing → semantics'),
             (4.9,.7,'Events / decisions / interactions\nSeparate learned discussion review'),
             (9.5,.7,'Contribution features + report\nSource-linked human review')]
    for x,y,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),3.9,1.15,boxstyle='round,pad=.08',facecolor='#edf6f7',edgecolor=COLORS[0]))
        ax.text(x+1.95,y+.575,label,ha='center',va='center',fontsize=10)
    for a,b in [((4.25,5.8),(4.8,5.8)),((8.85,5.8),(9.4,5.8)),((11.45,5.1),(6.85,4.25)),
                ((11.45,5.1),(11.45,4.25)),((4.25,3.5),(4.8,3.5)),((8.85,3.5),(9.4,3.5)),
                ((11.45,2.85),(6.85,1.95)),((8.85,1.25),(9.4,1.25))]:
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#526675','connectionstyle':'arc3,rad=.03'})
    ax.plot([11.45,13.75,13.75,6.85],[5.1,4.7,2.3,2.3],ls='--',color='#8b5b9c',lw=1)
    ax.annotate('',xy=(6.85,1.95),xytext=(6.85,2.3),arrowprops={'arrowstyle':'->','color':'#8b5b9c'})
    ax.text(10,2.4,'No-PPT path',color='#8b5b9c',fontsize=9)
    save(fig,'01_model_pipeline','Implemented models and information flow',
         'Conceptual dependency diagram, not measured performance. Speech and document contents are related through derived representations; no jointly trained raw-audio/image fusion network.', ['config/config.yaml','src/pipeline/orchestrator.py'])

    fusion_rows = [
        ['Word + speaker intervals','Temporal overlap association','Implemented; audio-derived information'],
        ['Temporal + semantic evidence','Weighted score-level fusion','Implemented; optional timing; 0.5 / 0.5'],
        ['Word + character + context TF-IDF','Feature concatenation','Implemented inside text classifier'],
        ['Forest + logistic probabilities','Classifier-output ensemble','Implemented inside text; 0.75 / 0.25'],
        ['MiniLM versus TF-IDF','Alternative representations','Selectable; not fused together'],
        ['Participation + contribution features','Research feature combination','Implemented in GAP ranking; no slide input'],
        ['Early / intermediate audio–document network','Joint learned multimodal fusion','Not deployed; separate toy prototypes exist'],
        ['Cross-attention / tensor / learned graph fusion','Learned interaction mechanisms','Not implemented'],
        ['Learned reliability gating','Input-dependent weighting','Not implemented; fixed missing-cue rule only'],
    ]
    fig, ax = plt.subplots(figsize=(14,7)); ax.axis('off')
    graphic = ax.table(cellText=fusion_rows,colLabels=['Information / method','What operation is this?','Current implementation'],loc='center',cellLoc='left',colWidths=[.30,.29,.41])
    graphic.auto_set_font_size(False);graphic.set_fontsize(9);graphic.scale(1,2.55)
    for (r,c),cell in graphic.get_celld().items():
        if r==0:cell.set_facecolor('#dceef0');cell.set_text_props(weight='bold')
        elif r<=6:cell.set_facecolor('#f0f8f4')
    save(fig,'02_fusion_methods_used','Which fusion methods have actually been used?',
         'The temporal–semantic hybrid combines cues at the score level. It is not an architecture combining early and late neural fusion. Within-text concatenation/ensembling does not create extra input modalities.', ['src/fusion/multimodal_representation.py','src/meeting/discussions.py','config/config.yaml'])
    table('fusion_implementation',[dict(zip(['method','operation','status'],r)) for r in fusion_rows])

    methods=list(controlled['methods']);labels=[NAMES[k] for k in methods]
    fusion_data=[{'method':k,**v['metrics']} for k,v in controlled['methods'].items()]
    table('controlled_fusion_metrics',fusion_data)
    fig, ax=plt.subplots(figsize=(9,5.2))
    bars(ax,labels,[100*controlled['methods'][k]['metrics']['top1_accuracy'] for k in methods],'Top-1 correctness (%)',COLORS[:3])
    save(fig,'03_controlled_fusion_top1','Controlled fusion diagnostic: semantic-only performs best',
         '24 author-designed cases / six constructed slides. Expected NO_CONFIDENT_SLIDE is included in correctness. This is not independent real-meeting accuracy; no claim of universal hybrid superiority.',[CONTROLLED])
    fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    for ax,metrics,title in [(axes[0],['grounded_precision','grounded_recall','grounded_f1'],'Grounded-link metrics'),
                              (axes[1],['macro_f1_including_no_slide','coverage'],'Macro F1 and link coverage')]:
        x=np.arange(3);width=.23
        for i,metric in enumerate(metrics):
            v=[100*controlled['methods'][k]['metrics'][metric] for k in methods]
            p=ax.bar(x+(i-(len(metrics)-1)/2)*width,v,width,label=metric.replace('_',' '),color=COLORS[i])
            ax.bar_label(p,fmt='%.1f',fontsize=8,padding=2)
        ax.set(xticks=x,xticklabels=labels,ylim=(0,120),ylabel='Percent',title=title);ax.legend(fontsize=8,loc='upper center')
    save(fig,'04_controlled_fusion_metrics','Fusion quality and coverage measure different things',
         'Constructed diagnostic only. Macro F1 includes the no-slide class. Hybrid coverage is 100% because it also links unrelated cases; higher coverage is not automatically better.',[CONTROLLED])
    groups=list(controlled['methods'][methods[0]]['by_group'])
    matrix=np.array([[controlled['methods'][k]['by_group'][g]['correct'] for k in methods] for g in groups])
    fig,ax=plt.subplots(figsize=(9,6));image=ax.imshow(matrix,vmin=0,vmax=4,cmap='YlGnBu',aspect='auto')
    ax.set(xticks=range(3),xticklabels=labels,yticks=range(len(groups)),yticklabels=[g.replace('_',' ') for g in groups])
    for row in range(len(groups)):
        for col in range(3):ax.text(col,row,f'{matrix[row,col]}/4',ha='center',va='center',color='white' if matrix[row,col]>2 else '#17324d',fontsize=13)
    fig.colorbar(image,ax=ax,label='Correct cases out of four')
    save(fig,'05_fusion_case_heatmap','Where each alignment strategy succeeds and fails',
         'Four cases per constructed group. Timing helps vague references but hurts offscreen/unrelated cases under the fixed 0.5/0.5 score rule and threshold 0.3.',[CONTROLLED])
    table('controlled_fusion_case_groups',[{'group':g,'method':k,**controlled['methods'][k]['by_group'][g]} for g in groups for k in methods])

    fig,axes=plt.subplots(1,2,figsize=(11,5));linked=[real['methods'][k]['linked_passages'] for k in methods]
    bars(axes[0],labels,linked,'Linked passages (count)',COLORS[:3],limit=50)
    bars(axes[1],labels,[100*real['methods'][k]['coverage'] for k in methods],'Link coverage (%)',COLORS[:3],limit=5)
    save(fig,'06_real_unlabelled_coverage','Real example: 39 / 1,008 passages linked; accuracy unknown',
         f"{real['passages']} passages / {real['slides']} slides / {real['slides_with_valid_times']} valid timed slides. Semantic and hybrid agree because of the missing-timing fallback. Independent relevance labels are unavailable; coverage is not accuracy.",[REAL])
    table('real_fusion_coverage',[{'method':k,'passages':real['passages'],'linked_passages':real['methods'][k]['linked_passages'],
        'coverage':real['methods'][k]['coverage'],'accuracy_status':'unavailable: independent labels missing'} for k in methods])

    installed=quality['discussion']['installed'];negative=quality['discussion']['always_negative']
    metrics=['accuracy','balanced_accuracy','precision','recall','f1','average_precision']
    fig,ax=plt.subplots(figsize=(12,5.5));x=np.arange(len(metrics))
    for i,(name,values) in enumerate([('Installed forest/logistic',installed),('Always negative',negative)]):
        p=ax.bar(x+(i-.5)*.36,[100*values[k] for k in metrics],.36,label=name,color=COLORS[i]);ax.bar_label(p,fmt='%.1f',fontsize=9,padding=3)
    ax.set(xticks=x,xticklabels=[k.replace('_','\n') for k in metrics],ylim=(0,110),ylabel='Metric (%)');ax.legend()
    save(fig,'07_discussion_model_vs_baseline','Discussion review: high recall, limited precision',
         quality['discussion']['scope']+'. Always-negative accuracy is high because of imbalance, but it retrieves no positives. These results do not measure final decisions or raw-audio application accuracy.',[EV+'quality_scorecard/summary.json'])
    table('discussion_metrics',[{'model':name,**values} for name,values in [('installed',installed),('always_negative',negative)]])
    tn,fp,fn,tp=installed['confusion_matrix_tn_fp_fn_tp'];matrix=np.array([[tn,fp],[fn,tp]])
    fig,ax=plt.subplots(figsize=(7.5,6));ax.imshow(matrix,cmap='Blues')
    for r in range(2):
        for c in range(2):ax.text(c,r,f'{matrix[r,c]:,}',ha='center',va='center',fontsize=20,color='white' if matrix[r,c]>3500 else '#17324d')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Predicted negative','Predicted discussion'],yticklabels=['Reference negative','Reference discussion'],xlabel='Prediction',ylabel='Human reference')
    save(fig,'08_discussion_confusion_matrix','Installed discussion classifier: historical confusion counts',
         '11,136 human reference dialogue acts: TN 5,627; FP 3,028; FN 467; TP 2,014. Reference text/boundaries differ from deployed ASR passages. Historical cohort was repeatedly inspected.',[EV+'quality_scorecard/summary.json'])

    families=['logistic_regression','complement_nb','linear_svm','random_forest'];fig,ax=plt.subplots(figsize=(11,5.5));x=np.arange(4)
    for i,variant in enumerate(['local','context_40']):
        values=[100*next(r['f1'] for r in classifiers if r['method']==f'{family}__{variant}') for family in families]
        p=ax.bar(x+(i-.5)*.34,values,.34,label=variant.replace('_',' '),color=COLORS[i]);ax.bar_label(p,fmt='%.2f',fontsize=9,padding=3)
    ax.axhline(installed['f1']*100,color=COLORS[2],linestyle='--',label=f"Installed ensemble F1 {installed['f1']*100:.2f}%")
    ax.set(xticks=x,xticklabels=['Logistic regression','Complement NB','Linear SVM','Random forest'],ylim=(0,65),ylabel='Historical positive-class F1 (%)');ax.legend(fontsize=9)
    save(fig,'09_classifier_family_comparison','Saved discussion classifiers: local versus context features',
         'Previously examined AMI reference-act cohort. Model-specific development selections differ; this is an exploratory comparison, not independent evidence of ensemble superiority. Installed blend is a separately selected configuration.',[EV+'classifier_comparison/comparison.csv',EV+'quality_scorecard/summary.json'])
    table('classifier_comparison',classifiers)

    table('speech_error_metrics',[{'cohort':r['cohort'],'model':r['model'],'wer':r['wer']['rate'],'wer_errors':r['wer']['errors'],
          'reference_words':r['wer']['reference_length'],'cer':r['cer']['rate'],'cer_errors':r['cer']['errors'],'reference_characters':r['cer']['reference_length']} for r in quality['asr']])
    cohorts=list(dict.fromkeys(r['cohort'] for r in quality['asr']))
    for index,metric in enumerate(['wer','cer'],10):
        fig,ax=plt.subplots(figsize=(12,5.6));x=np.arange(len(cohorts))
        for i,model in enumerate(['small','medium','large-v3-turbo']):
            values=[next((100*r[metric]['rate'] for r in quality['asr'] if r['cohort']==cohort and r['model']==model),np.nan) for cohort in cohorts]
            p=ax.bar(x+(i-1)*.24,values,.24,label=model,color=COLORS[i]);ax.bar_label(p,labels=[f'{v:.2f}' if np.isfinite(v) else '' for v in values],fontsize=8,padding=3)
        ax.set(xticks=x,xticklabels=[textwrap.fill(c,23) for c in cohorts],ylabel=metric.upper()+' (%) — lower is better',ylim=(0,85));ax.legend()
        save(fig,f'{index:02d}_speech_{metric}',f'Speech models: {metric.upper()} across separate small cohorts',
             'English development/historical each contain two clips; Hindi and Hinglish each contain eight samples. Missing medium historical bar means unrecorded, not zero. Cohorts are separate; no full-meeting multilingual accuracy claim.',[EV+'quality_scorecard/summary.json'])

    fig,ax=plt.subplots(figsize=(9,5.2));thresholds=sorted(float(k) for k in audio['development_pooled_der']);values=[100*audio['development_pooled_der'][str(k)] for k in thresholds]
    ax.plot(thresholds,values,'o-',color=COLORS[0]);ax.axvline(audio['selected_threshold'],ls='--',color=COLORS[1],label='Selected on development')
    for x,y in zip(thresholds,values):ax.annotate(f'{y:.2f}%',(x,y),xytext=(0,8),textcoords='offset points',ha='center')
    ax.set(xlabel='Clustering threshold',ylabel='Development pooled DER (%) — lower is better',xticks=thresholds,ylim=(12,25));ax.legend()
    save(fig,'12_speaker_threshold_development','Speaker clustering threshold selection',
         'Small development pilot only; threshold 0.9 was selected before the separate held-out excerpt comparison. This is not a full-corpus calibration curve.',[EV+'audio_summary.json'])
    rows=audio['test'];meetings=list(dict.fromkeys(r['meeting'] for r in rows));thresholds=sorted(set(r['threshold'] for r in rows))
    fig,axes=plt.subplots(1,2,figsize=(12,5.5));x=np.arange(len(meetings))
    for i,threshold in enumerate(thresholds):
        p=axes[0].bar(x+(i-.5)*.34,[100*next(r['der']['der'] for r in rows if r['meeting']==m and r['threshold']==threshold) for m in meetings],.34,label=f'Threshold {threshold}',color=COLORS[i]);axes[0].bar_label(p,fmt='%.2f',padding=3)
    axes[0].set(xticks=x,xticklabels=meetings,ylabel='DER (%)',ylim=(0,100));axes[0].legend()
    pooled=[100*pooled_der([r for r in rows if r['threshold']==t]) for t in thresholds]
    bars(axes[1],[str(t) for t in thresholds],pooled,'Speaker-time-pooled DER (%)',COLORS[:2]);axes[1].set_xlabel('Threshold')
    assert np.isclose(pooled_der([r for r in rows if r['threshold']==.9]),quality['audio_diarization']['pooled_der'])
    save(fig,'13_speaker_heldout_der','Diarization: two held-out excerpts and pooled errors',
         'Two 120-second AMI excerpts; 0.25s collar, overlap included, optimal speaker mapping. Pool by reference speaker-time. Excerpt pilot only; no streaming or physical-device performance claim.',[EV+'audio_summary.json',EV+'quality_scorecard/summary.json'])
    table('speaker_heldout_der',[{'meeting':r['meeting'],'threshold':r['threshold'],'der':r['der']['der'],'reference_speaker_seconds':r['der']['total_reference_duration'],'clusters':r['clusters'],'reference_speakers':r['reference_speakers']} for r in rows])

    fig,ax=plt.subplots(figsize=(8,5));weight=bundle['linear_weight']
    bars(ax,['Random Forest','Logistic Regression'],[100*(1-weight),100*weight],'Configured ensemble weight (%)',COLORS[:2])
    save(fig,'14_discussion_ensemble_weights','Discussion classifier: 75% forest + 25% logistic',
         f"Installed model configuration, not accuracy or modality importance. Context radius {bundle['context_radius']} units; smoothing radius {bundle['smoothing_radius']}; threshold {bundle['threshold']:.5f}. These combine text-classifier outputs.",['models/discussion/manifest.json','models/discussion/model.joblib'])
    weights=config['influence']['weights'];total=sum(weights.values());fig,ax=plt.subplots(figsize=(11,5))
    bars(ax,[k.replace('_','\n') for k in weights],[100*v/total for v in weights.values()],'Prototype configured weight (%)',COLORS[0],limit=28)
    save(fig,'15_contribution_feature_weights','Default contribution-score weights',
         'Configuration values, not empirically learned feature importance. Features are max-normalized across participants, then weighted. Missing categories stay zero; the highest participant score need not be one.', ['config/config.yaml'])
    table('contribution_weights',[{'feature':k,'normalized_weight':v/total} for k,v in weights.items()])

    rank_labels={'participation':'Participation Ridge','contribution':'Contribution Ridge','combined':'Combined Ridge','word_count':'Word count','speaking_duration':'Speaking duration','constant_ties':'Constant ties','prototype_fixed_weights':'Fixed prototype score'}
    names=list(rank_labels);fig,ax=plt.subplots(figsize=(12,5.8))
    bars(ax,[rank_labels[k].replace(' ','\n',1) for k in names],[100*ranking['scores'][k]['pairwise_accuracy'] for k in names],'Mean meeting-level pairwise agreement (%)',COLORS,limit=85)
    save(fig,'16_gap_participant_rankings','GAP research ranking: outcome alignment, not causal influence',
         '28 previously examined meetings / 84 people / 87 comparable pairs. Reference transcripts/speakers, no slides. Ridge research models are separate from the default UI score. Cross-validated exploratory point estimates.',[RANKING])
    table('gap_rankings',[{'method':k,'pairwise_accuracy':ranking['scores'][k]['pairwise_accuracy'],'top_set_accuracy':ranking['scores'][k]['top_set_accuracy'],'comparable_pairs':ranking['scores'][k]['comparable_pairs']} for k in names])
    contrasts=ranking['contrasts'];keys=list(contrasts);points=np.array([100*contrasts[k]['difference'] for k in keys]);intervals=np.array([np.array(contrasts[k]['descriptive_paired_bootstrap_95_ci'])*100 for k in keys])
    fig,ax=plt.subplots(figsize=(11,5.2));y=np.arange(len(keys))
    ax.errorbar(points,y,xerr=np.array([points-intervals[:,0],intervals[:,1]-points]),fmt='o',capsize=6,color=COLORS[0]);ax.axvline(0,ls='--',color=COLORS[1])
    ax.set(yticks=y,yticklabels=[k.replace('_minus_',' minus ').replace('_',' ') for k in keys],xlabel='Difference in pairwise agreement (percentage points)');ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    save(fig,'17_gap_difference_intervals','Ranking differences: descriptive intervals include zero',
         'Intervals are copied from the saved paired bootstrap, not newly estimated. Previously examined corpus and overlapping CV training sets limit interpretation; no reliable-superiority or fresh-confirmation claim.',[RANKING])
    table('gap_contrasts',[{'contrast':k,'difference':v['difference'],'descriptive_interval_low':v['descriptive_paired_bootstrap_95_ci'][0],'descriptive_interval_high':v['descriptive_paired_bootstrap_95_ci'][1]} for k,v in contrasts.items()])
    coverage=ranking['feature_coverage'];fig,axes=plt.subplots(1,2,figsize=(13,5.5))
    for ax,key,denominator,title in [(axes[0],'active_participants',ranking['participants'],'Active participants'),(axes[1],'active_meetings',ranking['meetings'],'Active meetings')]:
        labels=[r['feature'].replace('influence_','').replace('_','\n') for r in coverage]
        bars(ax,labels,[r[key] for r in coverage],f'Count out of {denominator}',limit=denominator);ax.set_title(title)
    save(fig,'18_gap_feature_coverage','Historical extraction coverage is sparse',
         f"Historical snapshot: {ranking['participants_without_contribution_features']} / {ranking['participants']} participants and {ranking['meetings_without_contribution_features']} / {ranking['meetings']} meetings had no contribution features. No slides were supplied. Later rule fixes were not rerun as a new GAP benchmark.",[RANKING])
    table('gap_feature_coverage',coverage)
    deletions=ranking['fixed_weight_deletions'];baseline=ranking['scores']['prototype_fixed_weights']['pairwise_accuracy'];fig,ax=plt.subplots(figsize=(11,5.2))
    delta=[100*(r['pairwise_accuracy']-baseline) for r in deletions]
    p=ax.barh([r['deleted_feature'].replace('influence_','') for r in deletions],delta,color=[COLORS[1] if v<0 else COLORS[0] for v in delta]);ax.bar_label(p,fmt='%.2f',padding=3);ax.axvline(0,color='#526675');ax.set_xlabel('Change from full fixed score (percentage points)');ax.set_xlim(-8,4)
    save(fig,'19_gap_feature_deletions','Fixed-score deletion diagnostic',
         'Saved delete-one-feature results on the same historical GAP representation; not retraining or causal feature importance. Inactive features can be removed without changing predictions. No confidence intervals are available.',[RANKING])
    table('gap_feature_deletions',[{**r,'difference_from_full':r['pairwise_accuracy']-baseline} for r in deletions])

    timing=website['timings'];fig,ax=plt.subplots(figsize=(11,5.8));labels=list(timing);values=list(timing.values())
    p=ax.barh([k.replace('_',' ') for k in labels],values,color=COLORS[0]);ax.bar_label(p,labels=[f'{v:.3f}' for v in values],padding=3,fontsize=8);ax.invert_yaxis();ax.set(xlabel='Recorded stage wall time (seconds)',xlim=(0,max(values)*1.25))
    save(fig,'20_pipeline_stage_runtime','Stage timing: 90-second English functional recording',
         'Warm models with uncached meeting inputs; two audio parts, two decks, four-speaker constraint. Excludes upload, queue, decode and final persistence. One laptop run; not a general latency benchmark.', ['outputs/evaluation/website_regression_20261025.json'])
    table('pipeline_stage_runtime',[{'stage':k,'seconds':v,'condition':'90s English; warm models; uncached meeting inputs'} for k,v in timing.items()])
    fig,axes=plt.subplots(1,3,figsize=(12,5))
    for ax,label,value,subtitle in [(axes[0],'Fresh meeting inputs',website['elapsed_seconds'],'90s input; warm models'),(axes[1],'Cached repeat',website['cached_elapsed_seconds'],'Same 90s input; cached'),(axes[2],'Docker functional check',docker['processing_seconds'],'30s input; 2 CPUs / 4 GiB')]:
        bars(ax,[label],[value],'Recorded seconds',limit=max(1,value*1.35));ax.set_title(subtitle,fontsize=10)
    save(fig,'21_runtime_conditions','Different runtime conditions must remain separate',
         'Independent panels use different scales and input/cache/resource conditions. These are functional timing records, not a matched comparison of models or cloud hosts. Cached repeat is not fresh inference speed.', ['outputs/evaluation/website_regression_20261025.json','outputs/evaluation/huggingface_backend_20261026.json'])
    table('runtime_conditions',[{'condition':'90s warm-model fresh-input laptop','input_seconds':90,'processing_seconds':website['elapsed_seconds']},
          {'condition':'same 90s cached repeat','input_seconds':90,'processing_seconds':website['cached_elapsed_seconds']},
          {'condition':'30s isolated Docker 2 CPUs 4 GiB','input_seconds':30,'processing_seconds':docker['processing_seconds']}])

    splits=['train','dev','test'];split_labels=['Training','Development','Historical evaluation'];fig,axes=plt.subplots(1,2,figsize=(12,5.3))
    bars(axes[0],split_labels,[dataset[k]['meetings'] for k in splits],'Meetings (count)',COLORS[:3],limit=35)
    x=np.arange(3);pos=np.array([dataset[k]['positive_acts'] for k in splits]);neg=np.array([dataset[k]['acts'] for k in splits])-pos
    axes[1].bar(x,neg,label='Negative acts',color=COLORS[2]);axes[1].bar(x,pos,bottom=neg,label='Positive acts',color=COLORS[0]);axes[1].set(xticks=x,xticklabels=split_labels,ylabel='Human reference dialogue acts');axes[1].legend(fontsize=9)
    save(fig,'22_ami_discussion_split','AMI discussion subset: meeting split and reference acts',
         '47 selected meetings, not the entire AMI corpus. Related series stay together. Historical evaluation contains 12 meetings / three series and was repeatedly examined; act counts are not independent-meeting counts.',[EV+'decision_discussion/dataset_counts.json'])
    table('ami_discussion_split',[{'split':k,**dataset[k]} for k in splits])
    roles=ranking['role_diagnostic']['rows'];fig,ax=plt.subplots(figsize=(10,5));x=np.arange(len(roles))
    for i,(key,label) in enumerate([('reference_positive','Reference positives'),('predicted_positive','Emitted positives'),('true_positive','Matched positives')]):
        p=ax.bar(x+(i-1)*.23,[r[key] for r in roles],.23,label=label,color=COLORS[i]);ax.bar_label(p,fmt='%d',padding=3)
    ax.set(xticks=x,xticklabels=[r['reference_role'] for r in roles],ylabel='Utterance counts',ylim=(0,820));ax.legend()
    save(fig,'23_gap_role_diagnostic','Historical event-role coverage: a known failure finding',
         '8,009 reference utterances. The evaluated historical snapshot emitted no proposals among 537 reference-positive proposal acts. Later keyword fixes do not retroactively update this diagnostic. Roles are not contribution/outcome links.',[RANKING])
    table('gap_role_diagnostic',roles)

    coefficients=linear.coef_[0];chosen=np.r_[np.argsort(coefficients)[:10],np.argsort(coefficients)[-10:]]
    fig,ax=plt.subplots(figsize=(12,9));values=coefficients[chosen]
    p=ax.barh(feature_names[chosen],values,color=[COLORS[1] if v<0 else COLORS[0] for v in values]);ax.axvline(0,color='#526675');ax.set_xlabel('Logistic coefficient (negative ← → discussion-positive)');ax.tick_params(axis='y',labelsize=8)
    save(fig,'24_logistic_feature_coefficients','Installed logistic component: strongest signed coefficients',
         'Top ten negative and positive coefficients of the actual trusted installed model. Prefix identifies word/character/context feature space. Coefficients depend on correlated TF-IDF features; not causal explanations or full-ensemble probabilities.', ['models/discussion/model.joblib'])
    table('logistic_top_coefficients',[{'feature':feature_names[i],'coefficient':float(coefficients[i])} for i in chosen])
    importance=forest.feature_importances_;chosen=np.argsort(importance)[-18:];fig,ax=plt.subplots(figsize=(12,8.5));ax.barh(feature_names[chosen],importance[chosen],color=COLORS[0]);ax.set_xlabel('Random-forest impurity-based importance');ax.tick_params(axis='y',labelsize=8)
    save(fig,'25_forest_feature_importance','Installed random forest: top impurity-based feature importances',
         'Actual forest component, not permutation importance or causal contribution. Correlated features and impurity-based biases limit interpretation; these importances do not measure the importance of physical input modalities.', ['models/discussion/model.joblib'])
    table('forest_top_importance',[{'feature':feature_names[i],'impurity_importance':float(importance[i])} for i in chosen])
    dimensions={k:len(bundle['vectorizers'][k].get_feature_names_out()) for k in ('word','char','context_40')};fig,ax=plt.subplots(figsize=(9,5))
    bars(ax,list(dimensions),list(dimensions.values()),'Active TF-IDF dimensions (count)',COLORS[:3],limit=max(dimensions.values())*1.25)
    save(fig,'26_discussion_feature_dimensions','Discussion input: concatenated word, character and context features',
         'Actual feature dimensions supplied to the installed classifiers. Stored unused context variants are excluded. Feature count is not model accuracy or an extra physical modality.', ['models/discussion/model.joblib'])
    table('discussion_feature_dimensions',[{'feature_space':k,'dimensions':v} for k,v in dimensions.items()])

    speaker_metrics=quality['audio_diarization'];fig,axes=plt.subplots(1,2,figsize=(13,5.5))
    rate_keys=['pooled_der','pooled_jer','speech_precision','speech_recall','speech_f1']
    bars(axes[0],['DER\n↓','JER\n↓','Speech\nprecision ↑','Speech\nrecall ↑','Speech\nF1 ↑'],[100*speaker_metrics[k] for k in rate_keys],'Different metric rates (%)',COLORS[:5],limit=110)
    bars(axes[1],['Speaker-count MAE\n↓'],[speaker_metrics['speaker_count_mae']],'Absolute count error',COLORS[1],limit=3)
    save(fig,'27_speaker_additional_diagnostics','Speaker pilot: complementary diagnostic measures',
         'Selected threshold 0.9; only two held-out excerpts. DER/JER and count MAE are lower-is-better; precision/recall/F1 are higher-is-better. Speech detection metrics concern speech activity, not word transcription correctness.',[EV+'quality_scorecard/summary.json'])
    table('speaker_additional_diagnostics',[{'metric':k,'value':speaker_metrics[k]} for k in rate_keys+['speaker_count_mae']])
    tw=config['alignment']['temporal_weight'];sw=config['alignment']['semantic_weight'];threshold=config['alignment']['threshold']
    fig,ax=plt.subplots(figsize=(13,7));ax.axis('off');ax.set(xlim=(0,13),ylim=(0,7))
    boxes=[(.4,5.1,5,1.1,'Semantic S\nMiniLM passage / slide cosine similarity'),
           (.4,3,5,1.1,'Temporal T\nOverlap with supplied slide-display intervals'),
           (.4,.9,5,1.1,'Timing unavailable\nUse semantic score alone: C = S'),
           (7.4,3.2,5.1,2,f'With timing: weighted score fusion\nC = ({tw:g}T + {sw:g}S) / ({tw:g} + {sw:g})\nWithout timing: C = S'),
           (7.4,.6,5.1,1.25,f'Keep top {config["alignment"]["top_k"]} candidates\nBest score ≥ {threshold:g}: assign slide\nOtherwise: NO_CONFIDENT_SLIDE')]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.07',facecolor='#edf6f7',edgecolor=COLORS[0]));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=11)
    for a,b in [((5.5,5.6),(7.3,4.7)),((5.5,3.55),(7.3,4)),((5.5,1.45),(7.3,3.4)),((9.95,3.1),(9.95,1.95))]:
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#526675'})
    save(fig,'28_temporal_semantic_fusion_flow','The actual alignment fusion rule and missing-timing fallback',
         'Configuration/implementation diagram, not measured accuracy. Pure temporal-only and semantic-only settings serve as single-cue baselines. Fixed weighted cue fusion is not learned cross-attention or a neural early-plus-late hybrid architecture.', ['config/config.yaml','src/fusion/multimodal_representation.py'])
    pdf.close()

    # Include fingerprints for inspected implementation files as well as numeric inputs.
    for item in graphs:
        for name in item['sources']:
            if name not in sources: source(name)
    source('scripts/generate_results.py')
    model_details={'linear_class':type(linear).__name__,'forest_class':type(forest).__name__,
        'linear_C':linear.C,'forest_trees':forest.n_estimators,'forest_max_depth':forest.max_depth,
        'linear_weight':bundle['linear_weight'],'forest_weight':1-bundle['linear_weight'],
        'context_radius_units':bundle['context_radius'],'smoothing_radius_units':bundle['smoothing_radius'],
        'threshold':bundle['threshold'],'feature_dimensions':dimensions}
    analysis={'date':'2026-10-26','scope':'Saved-result visual analysis and installed model inspection; no retraining or new benchmark',
        'graphs':graphs,'tables':tables,'source_sha256':sources,'installed_discussion_model':model_details,
        'controlled_fusion':fusion_data,'real_fusion':{'passages':real['passages'],'slides':real['slides'],'timed_slides':real['slides_with_valid_times'],'accuracy_available':False},
        'discussion_metrics':quality['discussion'],'asr':quality['asr'],
        'speaker_pooled_der':{str(t):pooled_der([r for r in rows if r['threshold']==t]) for t in thresholds},
        'speaker_additional_diagnostics':speaker_metrics,
        'gap_pairwise_accuracy':{k:v['pairwise_accuracy'] for k,v in ranking['scores'].items()},
        'limitations':['Constructed fusion cases are not independent real-meeting accuracy.',
            'Real slide-link coverage is not accuracy; ground-truth relevance labels missing.',
            'Discussion results use historical human text/boundaries, not full ASR application outputs.',
            'GAP is previously inspected outcome-proxy research with reference speakers and no slides.',
            'Historical role/coverage snapshots were not rerun after later extraction fixes.',
            'No matched TF-IDF/MiniLM, learned cross-attention or full end-to-end multimodal accuracy result is claimed.',
            'No ROC/PR curves or uncertainty estimates were fabricated from summary metrics.']}
    (OUT/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    (OUT/'model_inventory.json').write_text(json.dumps({'models':[dict(zip(['stage','model','status','evaluation'],r)) for r in inventory],'installed_discussion_details':model_details},indent=2)+'\n')
    cards='\n'.join(f'<article id="{g["name"]}"><h2>{html.escape(g["title"])}</h2><img loading="lazy" src="{g["png"]}" alt="{html.escape(g["title"])}"><p>{html.escape(g["caption"])}</p><p><a href="{g["png"]}">PNG</a> · <a href="{g["svg"]}">SVG</a> · <a href="{g["pdf"]}">PDF</a></p><small>Sources: {html.escape(", ".join(g["sources"]))}</small></article>' for g in graphs)
    index='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>InfluenceIQ model and fusion results</title><style>
body{font:16px/1.5 system-ui,sans-serif;color:#17324d;background:#eef3f5;margin:0}main{max-width:1150px;margin:auto;padding:26px}h1{font-size:2rem}article{background:white;padding:24px;margin:24px 0;border-radius:10px}img{display:block;width:100%;height:auto}a{color:#087f8c}small{overflow-wrap:anywhere}.notice{padding:16px;background:#fff3dc;border-left:4px solid #bd6a2d}nav{display:flex;gap:18px;flex-wrap:wrap}</style><main><h1>InfluenceIQ: model and fusion analysis</h1><p>26 October 2026 · '''+str(len(graphs))+''' figures from saved evidence and the installed classifier.</p><p class="notice">This is a visual analysis of existing results, not a new benchmark. Accuracy, coverage, reference-text classification, outcome-proxy ranking and runtime are separate quantities. No single full-project accuracy is established.</p><nav><a href="ALL_MODEL_AND_FUSION_ANALYSIS.pdf">All figures as PDF</a><a href="analysis.json">Numerical analysis and provenance</a><a href="model_inventory.json">Model inventory</a><a href="tables/">CSV tables</a><a href="README.md">Interpretation guide</a></nav>'''+cards+'</main></html>'
    experiment=OUT/'fusion_architecture_experiment/index.html'
    if experiment.exists():
        index=index.replace('</nav>','<a href="fusion_architecture_experiment/index.html">New early/intermediate/late prototype experiment</a></nav>')
    (OUT/'index.html').write_text(index)
    lines=['# Model and fusion results','',f'{len(graphs)} graphs, each available as PNG, SVG and PDF. Open `index.html` for the gallery or `ALL_MODEL_AND_FUSION_ANALYSIS.pdf` for the complete figure collection.','',
        'Regenerate from the project root: `.venv/bin/python scripts/generate_results.py`. Existing source result files are read, not modified. No training, audio processing or new accuracy experiment is performed.','',
        '## Main conclusions','',
        '- Controlled alignment: semantic-only 83.33%, hybrid 66.67%, temporal-only 50% on 24 constructed cases. This does not establish universal superiority.',
        '- Real untimed example: 39/1,008 links, 3.87% coverage; relevance accuracy and F1 are unavailable.',
        '- Installed English discussion model: 53.54% F1, 39.94% precision, 81.18% recall on historical human reference acts.',
        '- Speech pilots show mixed changes across small language/cohort samples; lower WER/CER is better.',
        '- Speaker threshold 0.9: small held-out pooled DER 40.91%; limited excerpts and explicit protocol.',
        '- GAP combined Ridge: 68.93% mean meeting-level pairwise agreement with an outcome-alignment proxy. Difference intervals include zero.',
        '- The default UI contribution score is fixed-weight aggregation, distinct from research Ridge models.',
        '- The main cross-source fusion is temporal/semantic score combination. TF-IDF concatenation and forest/logistic ensembling operate within text. Neural cross-attention/tensor/graph fusion is not implemented.','',
        '## How to use the figures','',
        'Graphs 01–06 explain the system and fusion; 07–09 discuss classification; 10–13 cover speech/speakers; 14–19 explain model weights and ranking limitations; 20–23 cover runtime, data and historical failures; 24–26 inspect trained model features; 27 adds speaker diagnostics; 28 diagrams the exact fusion rule.','',
        '## Figure index','']
    for g in graphs:lines.extend([f'### {g["name"]}: {g["title"]}',g['caption'],f'Sources: `{ "`, `".join(g["sources"]) }`',''])
    lines.extend(['## Interpretation limits','']+['- '+v for v in analysis['limitations']]+['',
        'Top model coefficients and impurity importances are model-specific associations, not causal explanations. Configuration weights are not measured accuracy. Individual probabilities are not used to fabricate ROC or PR curves. Sources and SHA-256 fingerprints are recorded in `analysis.json`.','',
        'This report covers the current selected pipeline and its main saved comparisons, not every archived experimental variant. No recordings, account databases, credentials or full private transcripts are copied into this folder.'])
    if experiment.exists():
        lines.extend(['','## Separate new early/intermediate/late prototypes','',
            'Open `fusion_architecture_experiment/index.html` for the new small constructed-case experiment. It is separate from the deployed pipeline and original temporal/semantic diagnostic. All metrics are computed from saved out-of-fold prototype predictions; no fake showcase values are used. Read its limitations before presenting.'])
    (OUT/'README.md').write_text('\n'.join(lines)+'\n')
    assert len(graphs)==28
    assert all((OUT/g['png']).stat().st_size>10000 for g in graphs)
    assert (OUT/'ALL_MODEL_AND_FUSION_ANALYSIS.pdf').stat().st_size>100000
    print(json.dumps({'folder':str(OUT),'graphs':len(graphs),'csv_tables':len(tables),'status':'generated'},indent=2))


if __name__=='__main__':
    generate()
