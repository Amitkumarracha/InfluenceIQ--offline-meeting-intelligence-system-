import json,platform,subprocess,html,base64,re,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from markdown_it import MarkdownIt
root=Path.cwd();out=root/'professor_guidelines';ev=out/'evaluation'
a=json.loads((ev/'audio_summary.json').read_text());small=json.loads((ev/'indic_summary.json').read_text());medium=json.loads((ev/'medium/indic_summary.json').read_text());long=json.loads((ev/'long_recording_diagnostic.json').read_text())
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)
rows=[[r['meeting'],r['threshold'],r['clusters'],r['reference_speakers'],f"{100*r['der']['der']:.2f}%"] for r in a['test']]
der=table(['Meeting','Threshold','Groups','Reference speakers','DER'],rows)
indic=table(['Model','Corpus','Samples','WER','CER'],[[model,lang,v['n'],f"{100*v['wer']:.2f}%",f"{100*v['cer']:.2f}%"] for model,result in [('small',small),('medium',medium)] for lang,v in result['summary'].items()])
results=f'''# Evaluation results — 19 October 2026

These are measured pilot results, not full-corpus benchmarks or deployment certification.

## Speaker calibration

Development: two 120-second AMI excerpts; held-out: two different meeting groups. Minimum pooled development DER selected threshold 0.9. Full protocol and individual results are in `evaluation/audio_protocol.json` and `evaluation/ami_*.json`.

{der}

The 42-minute private recording fell from 139 groups to {long['groups']} in a separate diagnostic. Its true count remains unknown. This reduces fragmentation but does not establish correct attribution. Original saved meeting data was not overwritten. Diagnostic processing took {long['elapsed_seconds']:.1f} seconds with other evaluation workloads active; peak process RSS was {long['peak_process_rss_mb']:.1f} MiB.

## Speech recognition

{indic}

English AMI held-out WER: IS1001b {100*a['asr'][0]['wer']['wer']:.2f}%; TS3007d {100*a['asr'][1]['wer']['wer']:.2f}%. Distant audio, overlap, spelling and reference conventions matter. Hindi/Hinglish measurements use eight samples each. Hinglish samples are consecutive technical-lecture segments; some hypotheses include neighbouring speech, so boundary/reference mismatch requires manual audit. Keep these strict scores; do not silently fix references after seeing predictions. Medium improves this small pilot but does not deliver reliable accuracy. The small default remains a latency trade-off.

## Functional evidence

The earlier audio-pilot software regression passed 563 tests with seven dependency warnings. Focused comparative metric checks are recorded in `evaluation/comparative_metric_tests.log`; that regression log is `evaluation/final_pytest.log`. Browser tests verify synthetic microphone previews, recovery, pause/resume, uploads, search, edits, evidence and responsive layouts. Real local preview inference is recorded separately in `evaluation/live_preview_real_model.json`. Android Java tests and APK build completed; no physical-phone accuracy or thermal certification is implied. Later pipeline validation is recorded separately with the new experiment.

## Downstream evaluation

Eight ablation variants ran against the existing long meeting. Human influence rankings and event/decision/slide references are missing, so those accuracy metrics remain unavailable. The outputs under `evaluation/downstream/` include private source-derived content: review before sharing. Score differences are sensitivity analysis, not proof of improved influence accuracy.

## Limits

No speech-model training/fine-tuning was performed in this audio pilot; a separately reported linear decision-discussion classifier has now been trained on manual AMI annotations. Public dataset provenance and SHA-256 values are in the two manifests. Neither benchmark contamination nor generalisation to Indian meetings has been ruled out. Timing with concurrent evaluation jobs is not a controlled latency comparison. Full recordings, additional languages, independent human labels, physical Android tests and confidence intervals remain future validation.
'''
(out/'EVALUATION_RESULTS.md').write_text(results)
refs=[
('Tur et al.','2010','The CALO Meeting Assistant System','https://doi.org/10.1109/TASL.2009.2038810','Integrated meeting capture and semantic analysis; foundational system.'),
('Radford et al.','2023','Robust Speech Recognition via Large-Scale Weak Supervision','https://proceedings.mlr.press/v202/radford23a.html','Multilingual speech recognition; pretrained ASR basis, not influence analysis.'),
('Bain et al.','2023','WhisperX: Time-Accurate Speech Transcription of Long-Form Audio','https://www.isca-archive.org/interspeech_2023/bain23_interspeech.html','VAD and forced alignment for transcription; not implemented here as WhisperX.'),
('Bredin','2023','pyannote.audio 2.1 speaker diarization pipeline: principle, benchmark, and recipe','https://www.isca-archive.org/interspeech_2023/bredin23_interspeech.html','Local segmentation, embeddings and global clustering; calibration motivates our pilot.'),
('Plaquet and Bredin','2023','Powerset multi-class cross entropy loss for neural speaker diarization','https://www.isca-archive.org/interspeech_2023/plaquet23_interspeech.html','Overlap-sensitive speaker segmentation; no decision extraction.'),
('Macháček, Dabre and Bojar','2023','Turning Whisper into Real-Time Transcription System','https://aclanthology.org/2023.ijcnlp-demo.3/','Streaming commitment policy; our fixed-window preview is simpler and not equivalent.'),
('Wang et al.','2024','Simul-Whisper: Attention-Guided Streaming Whisper with Truncation Detection','https://www.isca-archive.org/interspeech_2024/wang24ea_interspeech.html','Streaming word-boundary handling; not integrated in this prototype.'),
('Baghel et al.','2023','The DISPLACE Challenge 2023','https://www.isca-archive.org/interspeech_2023/baghel23_interspeech.html','Multilingual conversational speaker/language diarization benchmark.'),
('Kalluri et al.','2024','The Second DISPLACE Challenge: DIarization of SPeaker and LAnguage in Conversational Environments','https://www.isca-archive.org/interspeech_2024/kalluri24_interspeech.html','Code-switched multi-speaker evaluation; appropriate future meeting benchmark.'),
('Bhogale et al.','2023','Vistaar: Diverse Benchmarks and Training Sets for Indian Language ASR','https://www.isca-archive.org/interspeech_2023/bhogale23_interspeech.html','Indian-language diversity and domain evaluation; no integration claim.'),
('Hu et al.','2023','MeetingBank: A Benchmark Dataset for Meeting Summarization','https://aclanthology.org/2023.acl-long.906/','Meeting transcripts, minutes and metadata; generative summarisation is outside our scope.'),
('Kim, Cho and Na','2023','ExplainMeetSum: A Dataset for Explainable Meeting Summarization Aligned with Human Intent','https://aclanthology.org/2023.acl-long.731/','Evidence-backed summary evaluation; our outputs are extractive candidates.'),
('Medennikov et al.','2025','Streaming Sortformer: Speaker Cache-Based Online Speaker Diarization with Arrival-Time Ordering','https://www.isca-archive.org/interspeech_2025/medennikov25_interspeech.html','Streaming identity tracking; our live preview does not provide this.'),
('Conneau et al.','2022','FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech','https://arxiv.org/abs/2205.12446','Multilingual speech benchmark; Hindi pilot source.'),
('Diwan et al.','2021','MUCS 2021: Multilingual and Code-Switching ASR Challenges for Low Resource Indian Languages','https://www.isca-archive.org/interspeech_2021/diwan21_interspeech.html','Code-switch ASR benchmark; Hinglish pilot source.')]
comparison=table(['Work','Scope and distinction'],[[f'[{i}] {r[0]} ({r[1]})',r[4]] for i,r in enumerate(refs,1)]+[['InfluenceIQ','Local audio + PPTX evidence review, editable identities, heuristic decisions and influence; privacy by local inference, not audited encryption.']])
verified=json.loads((ev/'bibliography_verification.json').read_text()) if (ev/'bibliography_verification.json').exists() else []
reference_lines=[]
for i,r in enumerate(refs,1):
 meta=next((item.get('metadata',{}) for item in verified if item['url']==r[3]),{})
 authors='; '.join(meta.get('citation_author',[])) or r[0]
 venue=(meta.get('citation_conference_title') or [''])[0]
 pages='–'.join((meta.get('citation_firstpage') or [])+(meta.get('citation_lastpage') or []))
 doi=(meta.get('citation_doi') or [''])[0]
 if i==1:venue='IEEE Transactions on Audio, Speech, and Language Processing 18(6)';doi='10.1109/TASL.2009.2038810'
 reference_lines.append(f'[{i}] {authors} ({r[1]}). {r[2]}. {venue}. {pages}. '+('https://doi.org/'+doi if doi else r[3]))
bib='\n\n'.join(reference_lines)
fig,ax=plt.subplots(figsize=(8,3));names=['IS1001b','TS3007d'];x=range(2)
for offset,t in [(-.18,.5),(.18,.9)]: ax.bar([i+offset for i in x],[next(r['der']['der']*100 for r in a['test'] if r['meeting']==m and r['threshold']==t) for m in names],.35,label=f'Threshold {t}')
ax.set_xticks(list(x),names);ax.set_ylabel('DER (%)');ax.legend();fig.tight_layout();fig.savefig(out/'figures/diarization.png',dpi=300);fig.savefig(out/'figures/diarization.svg');fig.savefig(out/'figures/diarization.pdf');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,3));ax.axis('off')
labels=['Capture / upload\nAudio + optional PPTX','Local speech models\nASR → diarization','NLP + alignment\nEvidence and influence','Human review\nNames, roles, export']
for i,label in enumerate(labels):
 ax.text(.12+i*.25,.55,label,ha='center',va='center',fontsize=9,bbox=dict(boxstyle='round',facecolor='#dceef3'))
 if i<3:ax.annotate('',xy=(.245+i*.25,.55),xytext=(.225+i*.25,.55),arrowprops=dict(arrowstyle='->'))
ax.text(.5,.12,'Live path: bounded 15-second local ASR drafts; full recording retained for final analysis',ha='center',fontsize=9);fig.tight_layout();fig.savefig(out/'figures/architecture.png',dpi=200);plt.close(fig)
paper=f'''# InfluenceIQ: Local Meeting Analysis with Reviewable Evidence and Speaker Calibration

Author names, affiliations, corresponding email and ORCID: TO BE COMPLETED BY AUTHORS.

## Abstract

Meeting recordings contain decisions and contributions that are difficult to review manually, especially when speech recognition and speaker attribution errors propagate into participant analytics. This paper presents InfluenceIQ, a local meeting-analysis prototype combining pretrained speech recognition, speaker diarization, optional presentation alignment and rule-based event extraction. Users can inspect source evidence, correct participant names and roles, and review candidate decisions and actions without generative summarisation. A bounded browser recording path supplies local transcription drafts while preserving the complete recording for final analysis. The system separates cached speech observations from speaker attribution so that corrections can reuse recognition output. We evaluate clustering thresholds using two development and two held-out meeting excerpts and conduct a small Hindi and Hindi–English speech-recognition pilot using public references. Calibration reduces fragmentation and diarization error on the held-out excerpts, but substantial errors remain. Functional checks cover backend behaviour, browser workflows and Android build components. Influence rankings lack independent human annotations and are therefore not presented as validated measurements. The results support an inspectable engineering prototype and identify the additional annotation, acoustic evaluation and device testing required before reliable deployment.

Keywords: offline meeting analysis; speaker diarization; Hindi–English speech; evidence review; evaluation

## 1 Introduction

CALO established a broad meeting-assistant architecture including recognition and semantic interpretation [1]. InfluenceIQ addresses a narrower deployment objective: local processing with reviewable candidate events and participant contributions. Pretrained Whisper recognition [2] provides the speech layer. Recognition and attribution errors can invalidate downstream interpretation, so a usable interface is insufficient evidence of accuracy.

## 2 Related work and contribution

Table 1 compares fifteen relevant works, including eleven published in 2023–2025 and foundational system/dataset sources. Features outside a paper's stated scope are not treated as proven absent. WhisperX [3] addresses alignment; diarization pipelines [4,5] motivate explicit calibration. Streaming ASR [6,7] and streaming speaker tracking [13] are more specialised than the fixed-window preview implemented here. DISPLACE [8,9] motivates multilingual meeting evaluation; Vistaar [10] highlights domain diversity. MeetingBank [11] and ExplainMeetSum [12] inform evidence-oriented review, although this project excludes generative summaries. FLEURS [14] and MUCS [15] supply the public Indic pilot data.

Table 1. Related work and scope.

{comparison}

The engineering contributions are local audio/presentation integration, cached recognition independent of speaker corrections, editable identities propagated to evidence, bounded live drafts, and explicit missing-ground-truth reporting. These are integration contributions, not a new foundational speech model or a demonstrated patent novelty claim. Offline execution, diarization and decision extraction are not individually novel.

## 3 System and methods

Fig. 1 depicts the implemented pipeline. FFmpeg normalises audio. Local faster-whisper decodes chunks, while Sherpa-ONNX performs complete-recording speaker clustering. The word cache supports re-attribution. PPTX extraction feeds configured semantic/temporal alignment; a lexical TF-IDF option is also available. Unicode-aware rules identify English, Hindi and romanised-Hindi event candidates. Evidence and interaction links support decision chains. No language model generates meeting summaries or answers.

![Local pipeline](figures/architecture.png)

Fig. 1. Local processing and review.

Influence is a weighted sum of participant-normalised proposal, evidence, objection, revision, decision, interaction and slide-grounding features. Current weights are 0.15, 0.20, 0.15, 0.20, 0.15, 0.05 and 0.10. They are prototype assumptions, not fitted or independently validated parameters. Zero means no scored evidence was detected. Speaker identity errors can change every downstream feature.

The browser stores the original recording and sends independent 15-second PCM windows to an authenticated local preview endpoint. One worker and bounded admission avoid an unbounded preview queue. Busy periods are disclosed and final analysis uses the complete saved audio. Live speaker identities, stable streaming word commitments and constant-memory full-recording diarization are not implemented.

## 4 Evaluation protocol

AMI Array1-01 excerpts cover seconds 60–180. ES2002a and ES2003a form development; IS1001b and TS3007d form held-out testing. Thresholds 0.5, 0.7, 0.9 and 1.1 were fixed before inference; minimum pooled development DER selects 0.9. DER includes overlap, optimal speaker permutation, a 0.25-second collar and an explicit 120-second evaluation interval. Manual segment references may include internal silence; this is not an official full-corpus score.

The Hindi pilot uses eight FLEURS test recordings [14]; the Hinglish pilot uses eight consecutive MUCS mirror test rows [15]. Selection precedes inference and manifests record revisions and hashes. Word scoring applies NFKC, case folding and Unicode word tokenisation, without transliteration. Character scoring excludes spaces. Both models use local CPU int8 inference and automatic language settings. No reference text supplies hints. Timing during concurrent evaluation is not used for comparative speed claims. Human event, alignment and influence references are absent.

## 5 Results

Table 2 reports held-out speaker results. Fig. 2 visualises the same calibration comparison. Calibration improves both excerpts, but the second remains difficult; matching speaker count does not imply correct attribution.

Table 2. Held-out diarization pilot.

{der}

![Diarization comparison](figures/diarization.png)

Fig. 2. Held-out diarization error.

The private 42-minute diagnostic produced 37 groups versus the previous 139. Its true count is unknown, so this cannot establish speaker accuracy. It remains unsuitable for unreviewed participant rankings.

Table 3 reports strict Indic recognition error. Medium reduces WER in this pilot but retains substantial errors; Hinglish CER increases. Script variation, spelling and segment-boundary differences require transparent error analysis rather than post-hoc reference correction.

Table 3. Indic recognition pilot.

{indic}

The two English held-out WER values were {100*a['asr'][0]['wer']['wer']:.2f}% and {100*a['asr'][1]['wer']['wer']:.2f}%. Automated functional tests, synthetic microphone browser checks, real preview inference, Java tests and APK compilation provide separate implementation evidence. Eight downstream ablations execute, but missing human rankings prevent ranking-accuracy comparisons. No overall influence accuracy is reported.

## 6 Discussion and limitations

The principal unresolved issue is propagation of speech and speaker errors into decisions and participant scores. A smaller error rate in this pilot does not demonstrate broad reliability. Two test meetings and eight samples per Indic corpus are insufficient for strong statistical claims. Consecutive lecture examples are correlated and do not represent natural multi-party Hinglish meetings. Pretraining overlap is unknown. Physical-phone memory, heat and battery behaviour are unmeasured. Local execution avoids remote inference but does not itself provide audited storage encryption or consent management.

Future evaluation requires independent speaker/session splits, fluent annotators, adjudication, inter-rater agreement and meeting-level confidence intervals. Influence evaluation must compare independent human rankings and simple speaking-time baselines. Domain-specific model tuning should use separate training/development/test data; the present study performs no fine-tuning.

## 7 Conclusion

InfluenceIQ integrates local speech processing, presentation evidence and editable participant review with bounded recording previews. The calibration pilot reduces speaker fragmentation, while measured recognition and diarization errors reveal clear limits. Functional completion does not validate influence or establish deployment accuracy. The prototype is suitable for further controlled research and review; broader multilingual annotation and physical-device evaluation are required before stronger claims.

## Statements and declarations

Funding, competing interests, author contributions, affiliation and ethics/consent statements: authors must supply and verify these before submission. No ethics approval is asserted here. Public dataset references and manifests are provided; private meeting artifacts must not be redistributed without consent. Code availability depends on the authors' chosen repository release. AI assistance was used for coding, evaluation orchestration and drafting; human authors must review all claims and comply with institutional and journal disclosure rules.

## References

{bib}
'''
from research_figures import generate
from PIL import Image
generate()
paper=paper.replace('![Local pipeline](figures/architecture.png)', '![Local pipeline](figures/system_architecture.png)')
paper=paper.replace('## 4 Evaluation protocol', "### 3.1 Interfaces and error propagation\n\nLike the supplied CALO paper, this description separates architecture, component methods and evaluation. The implementation differs from CALO and its published results are not reused as our own. Browser previews contain unassigned-speaker text; final speaker labels are assigned only after complete-recording clustering. Authentication, source preservation and review controls surround the analysis stages. The native Android client is a separate execution path and is not assigned the laptop's benchmark results.\n\n### 3.2 Scoring definitions\n\nFor participant p and feature k, let x(p,k) be the observed feature count and m(k) the maximum across participants. The normalised value is z(p,k)=x(p,k)/m(k) when m(k)>0, otherwise zero. The influence estimate is I(p)=sum_k w(k)z(p,k), with nonnegative weights summing to one. This equation describes the implemented score; it is not a causal model. Errors in speaker labels, extracted events or slide links alter x(p,k). A name edit changes displayed identity, not the acoustic evidence.\n\nWER=(S+D+I)/N, where S, D and I are word substitutions, deletions and insertions and N is the reference word count. DER=(missed speaker-time + false-alarm speaker-time + confused speaker-time)/reference speaker-time under the declared collar and overlap policy. These error rates answer different questions and cannot be averaged into a single system accuracy.\n\n## 4 Evaluation protocol")
paper=paper.replace('## 5 Results', 'Fig. 3 summarises the evaluation separation. The public references are used for scoring rather than injected into recognition. Fig. 4 shows the development threshold sweep; the selected threshold is carried unchanged into held-out testing. Confidence intervals are not reported for the two-meeting experiment because that sample cannot support a useful population-level claim.\n\n![Evaluation protocol](figures/evaluation_protocol.png)\n\nFig. 3. Evaluation separation.\n\n![Development calibration](figures/calibration.png)\n\nFig. 4. Development threshold sweep.\n\n## 5 Results')
paper=paper.replace('## 6 Discussion and limitations', 'Fig. 5 breaks held-out DER into missed speech, false alarms and speaker confusion. The residual error is not solely a clustering problem: false alarms remain prominent on TS3007d. Fig. 6 compares strict word and character errors on identical Indic samples. Medium reduces WER but increases Hinglish CER, so the evidence does not support a blanket claim that the larger model is more accurate on every measure.\n\n![Diarization errors](figures/der_components.png)\n\nFig. 5. Diarization error components.\n\n![Indic model comparison](figures/indic_errors.png)\n\nFig. 6. Indic word and character errors.\n\n## 6 Discussion and limitations')
extension_path=ev/'public_extension/summary.json'
if extension_path.exists():
 extension=json.loads(extension_path.read_text())
 paragraph=f"An additional public MUCS diagnostic used four prespecified spaced test rows (100, 400, 800, 1200), downloaded from the dataset mirror and processed locally with the small model. Pooled strict WER was {extension['wer']*100:.2f}% ({extension['errors']} edits / {extension['reference_words']} reference words). This additional diagnostic was performed after the initial pilot and is not a confirmatory full-corpus benchmark. Table 4 lists each result; speaker/session independence and boundary quality still need auditing.\n\nTable 4. Additional public-audio diagnostic.\n\n"
 paragraph+=table(['Test row','Reference words','WER'],[[r['index'],r['wer']['reference_length'],f"{r['wer']['wer']*100:.2f}%"] for r in extension['rows']])
 paper=paper.replace('## 6 Discussion and limitations',paragraph+'\n## 6 Discussion and limitations')
paper=paper.replace('## Statements and declarations','## Statements and declarations\n\nDataset licensing: original MUCS source SLR104 specifies CC BY-SA 4.0; the Hugging Face mirror declares CC BY 4.0. The discrepancy is recorded in the protocol; original-source terms must be respected. Audio is not bundled with the manuscript.')
for old,new in [(2,4),(3,2),(4,3)]:
 paper=paper.replace(f'Fig. {old}',f'Fig. TEMP{new}')
paper=paper.replace('Fig. TEMP','Fig. ')
from build_comparative_evaluation import build as build_comparative
comparison, audio_metrics_table, ablation_metrics_table = build_comparative()
baseline_table = table(['Method', 'Clusters', 'Nonzero scores', 'Human accuracy'],
 [[row['method'], row['clusters'], row['nonzero_scores'], 'Unmeasured'] for row in comparison['baselines']])
methods_addition = """### 4.1 Comparative metrics and component removal

Additional diagnostics re-score the same saved AMI predictions: Jaccard error rate (JER), union-of-speech precision/recall/F1 and absolute speaker-count error. DER is pooled by reference speaker-time; JER is pooled by reference-speaker count; count MAE averages meetings. These supplementary diagnostics do not reselect the threshold. Definitions and implementation follow pyannote.metrics and its documented diarization evaluation approach [4]. Speech-region detection ignores speaker identity. Word/character comparisons use identical samples and report strict edit counts. We report descriptive differences; the small sample does not support claims of population significance.

A1 is the full-system control. A2 removes presentation links before rerunning downstream NLP. A3 removes temporal alignment, and A4 removes semantic alignment; each recomputes downstream analysis. A5 removes evidence weights, A6 interaction weights, and A7 decision-impact weights; remaining weights are renormalized. A8 is the speaking-time baseline, not a component-removal ablation. The downstream study uses the original saved 139-cluster recording, so it evaluates code sensitivity rather than validated participant influence. Mean absolute score change averages the same cluster set. Zero change and missing human labels remain visible.

"""
paper=paper.replace('## 5 Results',methods_addition+'## 5 Results')
results_addition = """### 5.1 Complementary audio metrics

Table 5 and Fig. 7 present the additional diagnostics on the same two held-out excerpts. DER, JER and count errors improve, while speech detection changes little. Grouping improves without solving all speech-region errors. Count accuracy alone is insufficient evidence of correct identities.

Table 5. Complementary audio diagnostics.

""" + audio_metrics_table + """
![Complementary audio metrics](figures/audio_metric_comparison.png)

Fig. 7. Complementary audio metrics.

### 5.2 Component ablation

Table 6 and Fig. 8 show the completed downstream sensitivity study. A2–A4 do not change influence scores on this recording, although slide-grounded event counts change in A2/A4. Consequently, this case supplies no evidence that presentation alignment improves influence ranking. A5/A6 alter scores, while A7 makes all scores zero. This describes the current decision-linked scoring rule; it does not establish that the removed components caused correct influence estimates. Renormalization can change scores even when the removed feature had no detected evidence.

Table 6. Component-removal sensitivity.

""" + ablation_metrics_table + """
![Component sensitivity](figures/ablation_sensitivity.png)

Fig. 8. Component-removal sensitivity.

A1–A7 are shown in Fig. 8. A8 has a different scoring definition and is retained as a separate baseline. These outputs derive from 139 unverified acoustic clusters; they must not be used as real-person rankings. Independent human ratings are needed to turn sensitivity changes into a component-utility study.

### 5.3 Influence baselines

Table 7 records the six baseline methods and proposed score. Output coverage is descriptive. All human-ranking comparisons remain unavailable. Score scales differ between methods, so nonzero counts and score magnitudes cannot rank their quality. Performance numbers from unrelated publications or commercial products are not inserted into this comparison.

Table 7. Baseline output coverage.

""" + baseline_table + '\n'
paper=paper.replace('## 6 Discussion and limitations', results_addition+'\n## 6 Discussion and limitations')
paper=paper.replace("Like the supplied CALO paper, this description separates architecture, component methods and evaluation.", "The system description separates architecture, component methods and evaluation.")
paper=paper.replace('For participant p and feature k, let x(p,k) be the observed feature count', 'For participant p and feature k, let x(p,k) be the decision-gated contribution feature value, including the bonuses defined by the implementation')
paper=paper.replace('AMI Array1-01 excerpts cover seconds 60–180.', 'AMI Array1-01 excerpts cover seconds 60–180. These four meetings are in the published BUT/pyannote training partition; “held-out” below refers only to the local calibration split, not the official benchmark test set.')
paper=paper.replace('Manual segment references may include internal silence; this is not an official full-corpus score.', 'Manual segment references may include internal silence and differ from the standard word-derived RTTM recipe. TS3007d has no supplied manual segment before 99.5 seconds although the clip begins at 60 seconds; the recogniser emits text in that prefix. This coverage sensitivity requires audio/reference auditing. The standard AMI UEM covers the full recording, so this study does not remove the prefix post hoc. These are custom pilot scores, not official benchmark results.')
paper=paper.replace('A5/A6 alter scores, while A7 makes all scores zero. This describes the current decision-linked scoring rule; it does not establish that the removed components caused correct influence estimates. Renormalization can change scores even when the removed feature had no detected evidence.', 'The saved feature audit shows that only decision contribution is nonzero; the other six feature families are inactive. Exactly, proposed scores equal 0.15 times the B3 decision-event-count baseline, so their rankings are identical. A5 is pure rescaling by 1/0.80 and A6 by 1/0.95 (within stored rounding), while A7 removes the only active feature. The score-change bars therefore do not demonstrate evidence or interaction utility. None of the 34 slides has timing metadata, making the temporal ablation uninformative. These are algebraic diagnostics of a degenerate case, not positive component-utility results.')
paper=paper.replace('The principal unresolved issue is propagation of speech and speaker errors', 'The current experiments do not establish benefit beyond decision-event counting: the only active feature in the downstream case is decision contribution, and its proposed ranking equals that baseline. Audio reference coverage and scoring conventions also need validation before interpreting the weakest scores. The principal unresolved issue is propagation of speech and speaker errors')
from report_decision_discussions import build as report_decision_discussions
nlp_table = report_decision_discussions()
# Keep the new NLP experiment distinct from the existing unvalidated influence model.
paper=paper.replace('## 5 Results', """### 4.2 Supervised decision-discussion pilot

A separate research-only classifier uses manual decision-discussion spans from 47 AMI meetings. A dialogue act is labelled positive when at least half of its lexical word IDs belong to a manual decision span. Reference text and act boundaries are oracle inputs; annotator act-type labels are not features. Outside-span acts are assumed negative, subject to annotation-completeness review. This task measures discussion membership, not final decisions or influence.

The custom project-series split uses 29 training, six development and 12 test meetings. Only three independent series are in the test cohort. The available manual decision files do not intersect the official BUT test partition, so this is explicitly a custom split. TF-IDF word/character/context variants use class-balanced logistic regression. C and thresholds are selected on development F1; all predefined variants are retained. Context includes the neighbouring previous/next act and therefore assumes offline access. Models remain research artifacts and are not installed in the app.

## 5 Results""")
paper=paper.replace('## 6 Discussion and limitations', """### 5.4 Initial decision-discussion comparison

Table 8 reports the independently annotated discussion-membership experiment. The context model, selected on development, achieves 42.35% F1 versus 37.83% for word-only and 38.36% for word+character. Its precision is 28.18%, so false positives remain a major limitation. Always-positive F1 is 36.44%; this baseline prevents a misleading interpretation of high recall. The explicit-decision rule addresses narrower cues than discussion membership, so its poor recall is not the principal evidence of improvement. The result is exploratory and requires a new independent final evaluation after further development.

Table 8. Decision-discussion tagging with oracle inputs.

""" + nlp_table + '\n## 6 Discussion and limitations')
paper=paper.replace('Human event, alignment and influence references are absent.', 'Reference labels matching the project event taxonomy, slide alignment and influence rankings are absent. Separate manual decision-discussion spans support the narrower classifier pilot described below.')
paper=paper.replace('the present study performs no fine-tuning.', 'the speech models are not fine-tuned, while the separate linear discussion classifier is trained on manual annotations.')
improved_path = ev / 'decision_discussion_v2/summary.json'
if improved_path.exists():
 from report_discussion_improvements import build as report_discussion_improvements
 paper=paper.replace('## 6 Discussion and limitations', report_discussion_improvements()+'## 6 Discussion and limitations')
 improved=json.loads(improved_path.read_text())
 chosen=next(r for r in improved['models'] if r['method']==improved['primary'])
 m=chosen['test']
 paper=paper.replace('Functional checks cover backend behaviour, browser workflows and Android build components.', f"An exploratory classifier study with reference transcripts and dialogue-act boundaries raises decision-discussion F1 from 42.35% to {100*m['f1']:.2f}% on a previously examined cohort; independent confirmation remains necessary. Functional checks cover backend behaviour, browser workflows and Android build components.")
 results+=f"\n## Decision-discussion continued development\n\nThe dev-selected `{improved['primary']}` configuration scores {100*m['precision']:.2f}% precision, {100*m['recall']:.2f}% recall and {100*m['f1']:.2f}% F1 on the same historical cohort as the initial 42.35% F1 pilot. This is exploratory continued development with oracle transcripts/act boundaries, not independent confirmation or app accuracy. See `DECISION_DISCUSSION_IMPROVEMENTS.md` and `evaluation/decision_discussion_v2/` for all variants, the smoothing ablation, frozen selection and provenance. Production rules are unchanged.\n"
 (out/'EVALUATION_RESULTS.md').write_text(results)
classifier_path = ev / 'classifier_comparison/summary.json'
if classifier_path.exists():
 from report_classifier_comparison import build as report_classifier_comparison
 classifier_methods, classifier_results = report_classifier_comparison()
 paper=paper.replace('## 5 Results', classifier_methods+'## 5 Results')
 paper=paper.replace('## 6 Discussion and limitations', classifier_results+'## 6 Discussion and limitations')
 classifier_data=json.loads(classifier_path.read_text())
 classifier_selected=next(r for r in classifier_data['models'] if r['method']==classifier_data['primary'])
 paper=paper.replace(f"An exploratory classifier study with reference transcripts and dialogue-act boundaries raises decision-discussion F1 from 42.35% to {100*m['f1']:.2f}% on a previously examined cohort; independent confirmation remains necessary.", f"An exploratory comparison of four classifier families using reference transcripts and dialogue-act boundaries selects {classifier_selected['family'].replace('_', ' ')} with {'wider context' if classifier_selected['features']=='context_40' else 'current-act features'}, reaching {100*classifier_selected['test']['f1']:.2f}% F1 on a previously examined cohort; independent confirmation remains necessary.")
 paper=paper.replace('Functional completion does not validate influence or establish deployment accuracy.', f"The matched discussion-classifier study selects {classifier_selected['family'].replace('_', ' ')} on development and measures {100*classifier_selected['test']['f1']:.2f}% historical F1 with oracle inputs; precision, recall and ranking metrics expose trade-offs. Functional completion does not validate influence or establish deployment accuracy.")
 results+=f"\n## Matched classifier comparison\n\nFour classifier families were trained with both current-act and context-40 features, using the same split and development selection rule. All eight results are reported in `CLASSIFIER_COMPARISON.md` and Table 10 of the manuscript. The new development-selected pipeline, `{classifier_data['primary']}`, scores {100*classifier_selected['test']['f1']:.2f}% historical F1. This task-level exploratory study does not benchmark complete meeting assistants or establish general superiority.\n"
 (out/'EVALUATION_RESULTS.md').write_text(results)
pipeline_path = ev / 'pipeline_improvement/summary.json'
if pipeline_path.exists():
 from report_pipeline_improvement import build as report_pipeline_improvement
 paper=paper.replace('## 6 Discussion and limitations', report_pipeline_improvement()+'## 6 Discussion and limitations')
 pipeline_data=json.loads(pipeline_path.read_text())
 pipeline_f1=100*pipeline_data['test']['f1']
 paper=paper.replace(f"An exploratory comparison of four classifier families using reference transcripts and dialogue-act boundaries selects {classifier_selected['family'].replace('_', ' ')} with {'wider context' if classifier_selected['features']=='context_40' else 'current-act features'}, reaching {100*classifier_selected['test']['f1']:.2f}% F1 on a previously examined cohort; independent confirmation remains necessary.", f"An exploratory four-family comparison followed by forest/linear score combination reaches {pipeline_f1:.2f}% discussion-membership F1 with reference transcripts and dialogue-act boundaries on a previously examined cohort. The selected model now supplies local review suggestions; independent recording-level accuracy validation remains necessary.")
 paper=paper.replace(f"The matched discussion-classifier study selects {classifier_selected['family'].replace('_', ' ')} on development and measures {100*classifier_selected['test']['f1']:.2f}% historical F1 with oracle inputs; precision, recall and ranking metrics expose trade-offs.", f"The learned discussion-review extension combines forest and linear scores, reaches {pipeline_f1:.2f}% historical F1 with oracle inputs, and is integrated into the local report and review workflow. Its recording-level accuracy remains unmeasured.")
 paper=paper.replace('No language model generates meeting summaries or answers.', 'A local forest/linear discussion detector additionally suggests English source passages for human review; these suggestions do not create final-decision anchors. No language model generates meeting summaries or answers.')
 results+=f"\n## Pipeline integration\n\nThe development-selected forest/linear combination scores {pipeline_f1:.2f}% historical discussion-membership F1, with {100*pipeline_data['test']['precision']:.2f}% precision and {100*pipeline_data['test']['recall']:.2f}% recall. It is installed locally for English discussion review and included in new report exports and the decision-review screen. See `PIPELINE_IMPROVEMENTS.md` for measured comparisons, runtime checks and limits. Actual recording/ASR-passage accuracy remains unmeasured.\n"
 (out/'EVALUATION_RESULTS.md').write_text(results)
quality_path = ev / 'turbo_quality/summary.json'
if quality_path.exists():
 from report_quality_improvements import build as report_quality_improvements
 paper=paper.replace('## 6 Discussion and limitations', report_quality_improvements()+'\n## 6 Discussion and limitations')
 quality=json.loads((ev/'quality_scorecard/summary.json').read_text())
 results+=f"\n## Further quality experiments and complete scorecard\n\nThe local speech default is `{quality['installed_asr']}` after fixed-sample evaluation. `QUALITY_IMPROVEMENTS.md` reports all recognition cohorts, the installed discussion model's accuracy/balanced accuracy/precision/recall/F1/AP and other metrics, negative NLP trials, and missing ground truth. No new NLP candidate met the release criteria; the installed forest/linear model is retained. Unrounded values and reference denominators are in `evaluation/quality_scorecard/`. These are exploratory task scores, not complete application accuracy.\n"
 (out/'EVALUATION_RESULTS.md').write_text(results)
assert all(f'Fig. {i}.' in paper for i in range(1,9))
assert 150 <= len(paper.split('## Abstract')[1].split('Keywords:')[0].split()) <= 250
(out/'RESEARCH_SUPPLEMENT.md').write_text(paper)
(out/'README.md').write_text('''# Research package

The main manuscript is now an IEEE conference-style draft: `RESEARCH_PAPER.pdf` is typeset with the unmodified IEEEtran class; `RESEARCH_PAPER.docx` is editable Word; `RESEARCH_PAPER.md` is the authored source; `RESEARCH_PAPER.tex` and `IEEEtran.cls` support LaTeX editing. `RESEARCH_PAPER.html` is a browser reading copy. The previous expanded report is preserved as `RESEARCH_SUPPLEMENT` in all five reader formats. The four student authors, institute affiliation and faculty guide are copied from the supplied project-cover screenshot; all five contact emails are included as supplied by the user. No venue-specific page limit or PDF eXpress approval is asserted. Formatting and build notes are in `IEEE_FORMAT_NOTES.md`.

Start with `QUALITY_IMPROVEMENTS.md` for the latest speech-model evaluation, complete metric scorecard and retained negative experiments. Read `PIPELINE_IMPROVEMENTS.md` for the installed learned discussion-review stage and its measured limits, `CLASSIFIER_COMPARISON.md` for the matched four-family/two-feature comparison and `DECISION_DISCUSSION_IMPROVEMENTS.md` for the context/smoothing experiments. Read `SUBMISSION_RECOVERY_PLAN.md` for the research plan, `DECISION_DISCUSSION_EXPERIMENT.md` for the original supervised pilot, `RESEARCH_VALIDITY_REVIEW.md` for the critical audit, `COMPARATIVE_AND_ABLATION.md` for earlier metric comparisons, `EVALUATION_RESULTS.md` for measurements, `PROJECT_GUIDE.md` for run commands, and `ANNOTATION_AND_SUBMISSION.md` for remaining validation. Every Markdown document has editable Word (`.docx`), legacy Word (`.doc`) and PDF companions. The source professor instructions and CALO PDF are preserved; the user's current IEEE-format instruction governs the main manuscript.

Raw measurements are in `evaluation/`; original diagrams are in `figures/`. Private downstream artifacts must be reviewed before sharing. The project is not scientifically validated merely because its functional tests pass. Human annotations, physical phone testing and author declarations remain necessary.
''')
md=MarkdownIt('commonmark').enable('table')
for path in out.glob('*.md'):
 if path.name=='RESEARCH_PAPER.md':continue
 content=md.render(path.read_text())
 content=re.sub(r'<p>(<img[^>]+>)</p>\s*<p>(Fig\. [^<]+)</p>',r'<p style="page-break-inside:avoid">\1<br/>\2</p>',content)
 page='<html><head><meta charset="utf-8"><style>@page {size:A4;margin:2cm} body {font-family:"Liberation Serif";font-size:11pt} table {border-collapse:collapse;width:100%;font-size:9pt} td,th {border:1px solid #888;padding:4px} img {max-width:100%;width:650px} pre {white-space:pre-wrap;font-size:9pt} h1,h2,h3 {page-break-after:avoid}</style></head><body>'+content+'</body></html>'
 
 for asset in (out/'figures').glob('*.png'):
  width,height=Image.open(asset).size
  page=page.replace('src="figures/'+asset.name+'"', 'width="600" height="'+str(round(600*height/width))+'" src="data:image/png;base64,'+base64.b64encode(asset.read_bytes()).decode()+'"')
 path.with_suffix('.html').write_text(page)
print(indic)

# Keep all reader formats in sync; embed figures so Word/PDF cannot lose relative assets.
for fmt in ['docx:Office Open XML Text','doc:MS Word 97','pdf:writer_pdf_Export']:
 subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/influenceiq-report-lo','--headless','--convert-to',fmt,'--outdir',str(out),*[str(p) for p in out.glob('*.html') if p.name!='RESEARCH_PAPER.html']],check=True,stdout=subprocess.DEVNULL,timeout=120)
subprocess.run([sys.executable,str(root/'scripts/build_ieee_paper.py'),'--pdf'],check=True)
subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/influenceiq-ieee-word','--headless','--convert-to','doc:MS Word 97','--outdir',str(out),str(out/'RESEARCH_PAPER.docx')],check=True,stdout=subprocess.DEVNULL,timeout=120)
