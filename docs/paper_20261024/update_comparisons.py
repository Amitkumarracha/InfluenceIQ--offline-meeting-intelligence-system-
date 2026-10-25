#!/usr/bin/env python3
"""Regenerate descriptive comparison/ablation tables from saved measurements."""
from pathlib import Path
import csv
import json

FOLDER=Path(__file__).resolve().parent


def load(name):return json.loads((FOLDER/name).read_text())


def table(header,rows):
    return '\n'.join(['| '+' | '.join(header)+' |','| '+' | '.join(['---']*len(header))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n\n'


def percent(value):return f'{100*value:.2f}'


def main():
    results=load('analysis/results.json');initial=load('historical_records/initial_results.json')
    initial_dev=load('historical_records/initial_development.json')
    semantic=load('historical_records/semantic_results.json');semantic_dev=load('historical_records/semantic_development.json')
    inventory=[]
    text='''## V. Comparative Analysis and Ablation Study

### A. Contribution Coverage and Role Diagnostics

Table III counts the participants and meetings with any nonzero value in each contribution category. A category is active only when its normalized value is positive. Proposal, evidence, revision, and slide grounding are inactive for all participants. Slide inactivity is expected because GAP has no slide input. The other inactive categories expose extraction or association limitations. Seventy of 84 people and 22 of 28 meetings have no contribution features at all; zeros are not independent judgments that these people contributed nothing.

Table III. Feature availability on 28 GAP meetings and 84 participants. A feature is available when its normalized value is nonzero; counts and percentages use the column denominators.

'''
    text+=table(['Contribution category','People with feature / 84','Meetings with feature / 28'],
                [[r['feature'].replace('influence_','').replace('_',' ').title(),f"{r['active_participants']}/84 ({100*r['active_participants']/84:.1f}%)",f"{r['active_meetings']}/28 ({100*r['active_meetings']/28:.1f}%)"] for r in results['feature_coverage']])
    text+='''The fixed role diagnostic has 537 reference-positive Proposal utterances and no emitted proposals, yielding zero proposal precision, recall and F1 under the declared convention. Agreement has 684 reference positives, 80 emissions, 24 true positives, 56 false positives and 660 false negatives: precision 30.00%, recall 3.51%, and F1 6.28%. These are corpus-wide descriptive role checks, not participant influence accuracy. Fig. 2 supplies source examples, and Fig. 5 visualizes feature availability.

### B. Main Comparative Analysis: Latest Model and Matched Baselines

Table IV is the principal result table. Every row uses the same 28 GAP meetings, 84 participants and 87 reference-comparable within-meeting pairs. The three ridge models use identical nested group folds, estimator family and parameter-search budget. **The latest combined model obtains 68.93% meeting-average pairwise accuracy**, the highest observed mean among these seven matched methods. Its point advantage is 1.07 percentage points over speaking duration, 2.38 points over word count and 7.14 points over participation-only ridge. These are observed differences, not established superiority.

Table IV. Main matched comparison on 28 GAP meetings, 84 participants and 87 comparable pairs. Higher pairwise accuracy is better; intervals are descriptive. Exact top set is complete winner-set agreement. Nonconstant output counts meetings with distinct participant scores and measures coverage, not correctness.

'''
    names={'combined':'**Latest combined ridge**','participation':'Participation-only ridge','contribution':'Contribution-only ridge',
           'word_count':'Word-count baseline','speaking_duration':'Speaking-duration baseline','prototype_fixed_weights':'Fixed contribution-score baseline','constant_ties':'Constant-tie reference'}
    inputs={'combined':'6 activity + 7 contribution','participation':'6 activity','contribution':'7 contribution',
            'word_count':'Word volume','speaking_duration':'Union of speech intervals','prototype_fixed_weights':'7 weighted contribution','constant_ties':'No distinguishing signal'}
    order=['combined','speaking_duration','word_count','participation','prototype_fixed_weights','contribution','constant_ties']
    rows=[]
    for key in order:
        r=results['scores'][key];lo,hi=r['descriptive_bootstrap_95_ci'];win=round(28*r['top_set_accuracy'])
        value=percent(r['pairwise_accuracy']);value='**'+value+'**' if key=='combined' else value
        rows.append([names[key],inputs[key],value,f'{100*lo:.2f} to {100*hi:.2f}',f'{win}/28 ({100*r["top_set_accuracy"]:.2f}%)',f'{28-r["constant_meetings"]}/28'])
        inventory.append({'experiment':'Nested group GAP (28 meetings)','task':'AII outcome-alignment ordering','model_id':key,
                          'method':names[key].replace('**',''),'development_score':'not a single dev cohort','evaluation_metric':'meeting-average pairwise accuracy (%)',
                          'evaluation_score':percent(r['pairwise_accuracy']),'status':'Exploratory corpus reuse; comparable within this experiment'})
    text+=table(['Model / baseline','Input features','Pairwise accuracy (%)','Descriptive 95% interval (%)','Exact top set /28 (%)','Nonconstant output /28'],rows)
    text+='''The interval column is a conditional meeting-bootstrap summary, not a guarantee of population performance. Exact top set means the complete predicted winner set equals the reference set. Nonconstant output means at least two participants receive different scores; it is coverage, not correctness. Each meeting is weighted equally, reference-tied pairs are excluded and predicted ties receive half credit. Neither pairwise accuracy nor exact top-set agreement is human-validated causal influence. Fig. 4 makes the 68.93% result visible alongside every matched baseline.

![Matched model comparison](figures/controlled_results.png)

Fig. 4. All seven matched methods on 28 GAP meetings. Points show meeting-average pairwise accuracy and bars show descriptive 95% meeting-bootstrap intervals. The latest combined Ridge result is 68.93%; the dashed line marks the constant-tie score. Prior corpus reuse and overlapping fitted folds limit inference.

![Contribution feature availability](figures/feature_coverage.png)

Fig. 5. Contribution-feature availability among 84 participants and 28 meetings. Labels give active counts and percentages. Slide grounding is unavailable by design; the remaining inactive categories diagnose extraction or association limitations. Zero activity is not evidence of zero human contribution.

### C. Paired Comparative Analysis

Table V compares methods within the same meetings. It reports the direction of change and the number of meetings improved, unchanged or worsened. Fig. 6 plots the paired intervals against zero. The combined model improves on participation-only ridge in six meetings, ties in 19 and worsens in three. Its descriptive interval includes zero. The word-count comparison is also inconclusive; higher means alone do not establish reliable generalization.

Table V. Paired differences; positive values favor the first method.

'''
    contrast_names={'combined_minus_participation':'Combined minus participation ridge','combined_minus_word_count':'Combined minus word count','contribution_minus_participation':'Contribution minus participation ridge'}
    rows=[]
    for key,label in contrast_names.items():
        r=results['contrasts'][key];lo,hi=r['descriptive_paired_bootstrap_95_ci']
        rows.append([label,f"{100*r['difference']:+.2f}",f'{100*lo:.2f} to {100*hi:.2f}',
                     f"{r['meetings_better']} / {r['meetings_same']} / {r['meetings_worse']}",'Includes zero'])
    text+=table(['Matched contrast','Difference (points)','Descriptive 95% interval (points)','Better / same / worse meetings','Interpretation'],rows)
    text+='''![Paired model differences](figures/paired_differences.png)

Fig. 6. Paired meeting-average differences and descriptive 95% paired-bootstrap intervals. Positive values favor the first method. All three intervals cross zero, so these observations do not establish a reliable performance gain.

### D. Comparative Analysis of Earlier Models and Pipelines

Table VI reports all fourteen final methods from the original GAP experiment, including the five fixed baselines and all three learned model families under structure, text and combined inputs. Parameters were selected on development data. The selected primary remains structural Extra Trees: 83.33% development and 61.11% historical pairwise accuracy, versus word count's 82.78% and 63.89%. The nonprimary combined Extra Trees candidate is not retrospectively promoted because it scored 66.67%. This six-meeting cohort contains 19 participants and 21 comparable pairs; its 33.33–83.33% primary interval is broad.

Table VI. All original GAP finalists: 16 fitting, six development and six historical evaluation meetings. PA is meeting-average pairwise accuracy; higher is better. The primary was selected on development PA, not on historical results. This earlier snapshot is distinct from Table IV.

'''
    original_labels={'speaking_time':'Speaking duration','word_count':'Word count','utterance_count':'Utterance count','decision_count':'Decision-event count','prototype_influence':'Original weighted score'}
    model_labels={'ridge':'Ridge','pairwise_logistic':'Pairwise logistic regression','extra_trees':'Extra Trees','rank_ensemble':'Rank ensemble'}
    representations={'structure':'Structural features','text':'Participant text','combined':'Structural + text',
                     'lower_threshold':'Lower event threshold','semantic':'Semantic uptake','semantic_embeddings':'Semantic uptake + text embeddings',
                     'learned_roles':'Learned roles','learned_roles_embeddings':'Learned roles + text embeddings'}
    def model_label(key):
        feature,model=key.split('__')
        return representations[feature]+' / '+model_labels[model]
    orig_rows=[]
    for key,r in initial['results'].items():
        dev=max((d for d in initial_dev if d['name']==key),key=lambda d:d['development']['meeting_macro_pairwise_accuracy'],default=None)
        if dev is None:raise AssertionError(key)
        label=original_labels[key] if key in original_labels else model_label(key)
        status='Selected primary' if key==initial['primary_selected_on_development'] else ('Fixed baseline' if key in original_labels else 'Nonprimary finalist')
        orig_rows.append([label,percent(dev['development']['meeting_macro_pairwise_accuracy']),percent(r['meeting_macro_pairwise_accuracy']),status])
        inventory.append({'experiment':'Original GAP (6 historical meetings)','task':'AII outcome-alignment ordering','model_id':key,'method':label,
                          'development_score':percent(dev['development']['meeting_macro_pairwise_accuracy']),
                          'evaluation_metric':'meeting-average pairwise accuracy (%)','evaluation_score':percent(r['meeting_macro_pairwise_accuracy']),'status':status+'; earlier source snapshot'})
    assert len(orig_rows)==14
    text+=table(['Model / representation','Development PA (%)','Historical PA (%)','Selection status'],orig_rows)
    text+='''Table VII includes every final semantic/role model combination, plus the corrected pipeline, topic, contextual-role and XGBoost variants. Version B denotes the earlier semantic/role snapshot; version C denotes corrected extraction and attribution. These comparisons reuse previously examined historical groups. Rank ensembles, semantic uptake, participant-text embeddings, contextual roles and boosted ranking are therefore visible rather than hidden in selected successful rows.

Table VII. All later GAP ranking finalists on the six historical meetings. PA is meeting-average pairwise accuracy; higher is better. B uses the earlier semantic/role snapshot and C corrected extraction/attribution. Repeated historical evaluation is exploratory, and these rows are not matched to Table IV's 28-meeting protocol.

'''
    sem_rows=[]
    for key,r in semantic['results'].items():
        if '__' not in key:continue
        dev=max((d for d in semantic_dev if d['name']==key),key=lambda d:d['development']['meeting_macro_pairwise_accuracy'])
        label=model_label(key)
        sem_rows.append([label,percent(dev['development']['meeting_macro_pairwise_accuracy']),percent(r['meeting_macro_pairwise_accuracy']),'B: earlier snapshot'])
    corrected=load('historical_records/corrected_fixed_results.json');balanced=load('historical_records/balanced_fixed_results.json')
    xgb=load('historical_records/corrected_ranker_selection.json');xgb_hist=load('historical_records/corrected_ranker_results.json')
    sem_rows.extend([
        ['Corrected fixed keyword pipeline',percent(corrected['cohorts']['development']['corrected_keyword']['meeting_macro_pairwise_accuracy']),percent(corrected['cohorts']['test']['corrected_keyword']['meeting_macro_pairwise_accuracy']),'C: corrected fixed score'],
        ['Corrected pipeline + semantic topics',percent(corrected['cohorts']['development']['corrected_keyword_topic']['meeting_macro_pairwise_accuracy']),percent(corrected['cohorts']['test']['corrected_keyword_topic']['meeting_macro_pairwise_accuracy']),'C: topic feature toggle'],
        ['Balanced contextual roles + fixed score',percent(balanced['cohorts']['dev']['contextual_roles_fixed_influence']['meeting_macro_pairwise_accuracy']),percent(balanced['cohorts']['test']['contextual_roles_fixed_influence']['meeting_macro_pairwise_accuracy']),'C: learned role replacement'],
        ['Selected XGBoost ranker',percent(xgb['development']['meeting_macro_pairwise_accuracy']),percent(xgb_hist['candidate']['meeting_macro_pairwise_accuracy']),'C: development-selected ranker']])
    for i,row in enumerate(sem_rows):inventory.append({'experiment':'Later GAP (6 historical meetings)','task':'AII outcome-alignment ordering','model_id':'pipeline_'+str(i),'method':row[0],
        'development_score':row[1],'evaluation_metric':'meeting-average pairwise accuracy (%)','evaluation_score':row[2],'status':row[3]+'; exploratory'})
    assert len(sem_rows)==24
    text+=table(['Pipeline / model family','Development PA (%)','Historical PA (%)','Feature version / scope'],sem_rows)
    text+='''The latest 68.93% result in Table IV uses nested predictions over 28 meetings, whereas Tables VI–VII use the original six historical meetings and different feature versions. Their numerical ordering is not a matched experiment. We can state that the latest model has the highest observed mean among its matched Table IV comparators; we cannot claim that it reliably beats every historical pipeline or a classifier evaluated on another task. The complete model inventory is also supplied as a machine-readable CSV.

### E. Explicit Ablation Study

Table VIII separates two kinds of ablation. The feature-family study removes participation or contribution inputs and refits Ridge under the same nested tuning procedure. The fixed-score study deletes one contribution weight without refitting or renormalizing. Each change is measured relative to its own full reference system; the 68.93% Ridge reference must not be confused with the 55.77% fixed-score reference. Fig. 7 visualizes these two groups separately.

Table VIII. Ablations on the same 28 meetings. PA is meeting-average pairwise accuracy. Ridge rows refit under identical nested tuning and use the 68.93% full reference; weight-deletion rows have no refit or renormalization and use the 55.77% fixed reference. Negative changes reduce PA; constant meetings have tied scores for every participant.

'''
    arows=[];full=results['scores']['combined']['pairwise_accuracy'];fixed=results['scores']['prototype_fixed_weights']['pairwise_accuracy']
    for label,key,interpretation in [('Ridge: all 13 features','combined','Full learned reference'),('Ridge: remove 7 contribution inputs','participation','Participation-only refit'),('Ridge: remove 6 participation inputs','contribution','Contribution-only refit')]:
        r=results['scores'][key];arows.append([label,percent(r['pairwise_accuracy']),f'{100*(r["pairwise_accuracy"]-full):+.2f}',r['constant_meetings'],interpretation])
    arows.append(['Fixed score: all 7 categories',percent(fixed),'+0.00',results['scores']['prototype_fixed_weights']['constant_meetings'],'Full fixed reference'])
    active={r['feature']:r['active_participants'] for r in results['feature_coverage']}
    for r in results['fixed_weight_deletions']:
        name=r['deleted_feature'];arows.append(['Fixed score: remove '+name.replace('influence_','').replace('_',' '),percent(r['pairwise_accuracy']),f'{100*(r["pairwise_accuracy"]-fixed):+.2f}',r['constant_meetings'],'Inactive input; unchanged' if active[name]==0 else 'Active category deletion'])
    text+=table(['System / removed input','PA (%)','Change vs own full system (points)','Constant meetings /28','Meaning'],arows)
    text+='''Removing contribution inputs lowers the learned model's point estimate by 7.14 points, while removing participation lowers it by 15.54 points. These differences remain exploratory; Table V provides the paired uncertainty for the first contrast in the opposite direction. For the fixed score, removing decision features lowers PA from 55.77% to 50.30%; removing interaction raises it to 56.96%. Deleting inactive categories leaves the score unchanged. Such sensitivity does not establish validated personal impact or show that interaction information is generally harmful.

![Two distinct ablation studies](figures/ablation_results.png)

Fig. 7. Ablation changes relative to each panel's full system. Left: the same nested procedure refits Ridge after removing one feature family, relative to the 68.93% combined model. Right: single contribution weights are deleted without refitting or renormalization, relative to the 55.77% fixed score. The two references and interventions differ.

### F. Supporting Classifier and Role Comparisons

Table IX makes the earlier Logistic Regression, Complement Naive Bayes, calibrated linear SVM, Random Forest, forest/logistic combination and neural candidates explicit. These are supporting tasks. AMI discussion uses 11,136 historical acts from 12 meetings; GAP role macro F1 uses the separate utterance-role target. Neither is participant-ordering PA, and the neural epoch choices and label supports remain in the supplement.

Table IX. All supporting classifier finalists. AMI rows report positive-class discussion F1 and GAP rows unweighted four-role macro F1; higher is better. Historical cohorts and label targets differ from participant-ranking PA, so these scores cannot establish cross-task superiority.

'''
    classifiers=load('historical_records/discussion_classifier_comparison.json');component_rows=[]
    labels={'logistic_regression':'Logistic Regression','complement_nb':'Complement NB','linear_svm':'Calibrated linear SVM','random_forest':'Random Forest'}
    for r in classifiers['models']:
        component_rows.append(['AMI discussion',labels[r['family']],r['features'].replace('_',' '),percent(r['dev']['f1']),percent(r['test']['f1'])])
    discussion=load('historical_records/discussion_results.json')['metrics']
    component_rows.extend([['AMI discussion','75% forest + 25% logistic','Installed combination','59.79',percent(discussion['frozen_blend']['f1'])],
                           ['AMI discussion','Fine-tuned MiniLM','Neural candidate','53.10',percent(discussion['macro_f1'])]])
    for label,file in [('Unweighted MiniLM','unweighted_roles_results.json'),('Balanced MiniLM','balanced_roles_results.json')]:
        r=load('historical_records/'+file)['metrics']
        component_rows.append(['GAP role macro F1',label,'Four-role classification','See frozen protocol',percent(r['macro_f1'])])
    for i,row in enumerate(component_rows):inventory.append({'experiment':row[0],'task':row[0],'model_id':'component_'+str(i),'method':row[1]+' / '+row[2],
        'development_score':row[3],'evaluation_metric':'positive F1 (%)' if row[0]=='AMI discussion' else 'four-role macro F1 (%)','evaluation_score':row[4],'status':'Supporting task; not ranking accuracy'})
    ai=load('historical_records/ai_pilot_results.json')
    for key,r in ai['methods'].items():
        inventory.append({'experiment':'AI-labelled relationship pilot','task':'Relationship agreement with AI labels','model_id':key,'method':key.replace('_',' '),
                          'development_score':'See frozen pilot protocol','evaluation_metric':'AI-label agreement (%)',
                          'evaluation_score':percent(r['ai_label_agreement']),'status':'11 historical pairs; no independent human validation'})
    text+=table(['Task','Model','Input / variant','Development F1 (%)','Historical F1 (%)'],component_rows)
    text+='''The installed combination retains 53.54% positive F1; the neural discussion candidate scores 46.32%. The separate AI-labelled relationship pilot and source-only/outcome-only controls remain in the supplement, where their 54.55% paired agreement is compared with 63.64% majority agreement. Those AI-label agreements are not human-validated influence accuracy. The machine-readable record includes all 61 evaluated methods or variants across these tasks, and a separate CSV preserves all 121 ranking development-search records. Search-grid trials that were scored only on development data are distinct from historically evaluated finalists; invalidated trials supply no valid result.

'''
    # Preserve the existing methods and discussion; replace only the results section.
    p=FOLDER/'manuscript.md';source=p.read_text();before=source.split('## V. ',1)[0];after='## VI. '+source.split('## VI. ',1)[1]
    after=after.replace('Table VII states','Table X states').replace('Table VII. Canonical','Table X. Canonical')
    source=before+text+after
    source=source.replace('The authors acknowledge Dr. Nivedita Mishra, Department of Artificial Intelligence & Machine Learning, Symbiosis Institute of Technology, Pune, for project guidance.',
        'The authors acknowledge their faculty guide, Dr. Nivedita Mishra, Department of Artificial Intelligence & Machine Learning, Symbiosis Institute of Technology, Pune, Symbiosis International (Deemed University), Pune 412115, Maharashtra, India (e-mail: nivedita.mishra@sitpune.edu.in), for project guidance.')
    p.write_text(source)
    with (FOLDER/'analysis/model_pipeline_inventory.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(inventory[0]));writer.writeheader();writer.writerows(inventory)
    trials=[]
    for name,filename in [('Original GAP','initial_development.json'),('Semantic/role GAP','semantic_development.json'),('Corrected XGBoost','corrected_ranker_development.json')]:
        for i,r in enumerate(load('historical_records/'+filename),1):
            trials.append({'experiment':name,'trial':i,'method':r.get('name','XGBoost / '+r.get('feature_set','')),
                           'development_PA_percent':percent(r['development']['meeting_macro_pairwise_accuracy']),
                           'parameters_json':json.dumps({k:v for k,v in r.items() if k!='development'},sort_keys=True),
                           'scope':'Development selection only; not an independent evaluation'})
    with (FOLDER/'analysis/development_search_inventory.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(trials[0]));writer.writeheader();writer.writerows(trials)
    record={'main_result_table':'IV','main_pairwise_accuracy':results['scores']['combined']['pairwise_accuracy'],
            'matched_methods':order,'original_methods':len(orig_rows),'later_pipelines':len(sem_rows),'supporting_models':len(component_rows),
            'ablation_rows':len(arows),'inventory_rows':len(inventory),'development_search_records':len(trials),
            'scope':'Cross-protocol or cross-task superiority is not established.'}
    (FOLDER/'analysis/comparison_table_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
