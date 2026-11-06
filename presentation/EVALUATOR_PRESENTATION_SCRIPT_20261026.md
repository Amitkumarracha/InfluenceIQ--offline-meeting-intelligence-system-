# InfluenceIQ / Meet IQ — complete presentation and evaluator answers

Prepared 26 October 2026 from implementation, configuration, installed model metadata and saved evaluation records. Use the slide bullets on screen and the **Say** paragraphs as your script. This is a presentation of implemented behavior and scoped experiments, not a new accuracy benchmark. The latest backend packaging was tested locally; public cloud deployment has not been completed.

## Read this first: the five answers to memorize

1. **Purpose:** source-linked meeting review: what was said, who said it, and which passages may relate to decisions, actions and contributions.
2. **Summary:** we already build a structured executive summary. We have not deployed an LLM that writes abstractive meeting notes.
3. **Modalities:** audio plus optional presentation documents. The document fusion mainly relates recognized speech text to extracted slide text; it is not a jointly trained raw-audio/image network.
4. **Fusion:** temporal attribution connects words to speaker intervals; slide alignment combines semantic and available temporal scores. Text-feature concatenation and a classifier ensemble occur in the separate discussion detector.
5. **Results:** on 24 constructed alignment cases, semantic-only scored 83.33%, hybrid 66.67%, temporal-only 50%. The real untimed example has 3.87% link coverage, not 3.87% accuracy. There is no single overall project accuracy.

## Slide 01 — Project identity and purpose

**On the slide**

- InfluenceIQ: an offline-first meeting-intelligence and review system.
- Meet IQ is the application label used in parts of the interface.
- Timestamped speech, speakers, optional slide context and source-linked candidates.
- A reviewer checks the outputs against the original recording.

**Say**

> Good morning, ma'am. Our project is InfluenceIQ, also called Meet IQ in the application. It converts meeting recordings into timestamped, speaker-attributed transcripts and structured suggestions about discussions, decisions, actions and participant contributions. Optional presentations add document context. The main idea is to make the analysis inspectable: the reviewer can return to the source recording rather than relying only on a paragraph of generated notes. Influence refers to contribution to decision discussion; IQ indicates intelligent assistance, not a personal intelligence measurement.

## Slide 02 — Problem statement and intended users

**On the slide**

- Long recordings take time to review and decisions need surrounding context.
- Speaking the longest does not necessarily mean contributing most to an outcome.
- A summary alone does not expose every speaker, timestamp or reasoning step.
- Intended use: review assistance for teams, students and meeting participants.

**Say**

> A recording contains the information, but locating a particular proposal or checking who supported it still requires work. Counting speaking time gives participation, but not necessarily contribution. We therefore preserve speakers and timestamps, identify candidate event types, and connect relevant passages. This is assistance for a reviewer, not a replacement for their judgment and not an automatic employee-performance assessment. We have not measured reviewer time savings in a user study, so that remains an intended benefit rather than a proved percentage improvement.

## Slide 03 — What is our contribution and novelty?

**On the slide**

- An implemented local workflow combining audio, document context and source traceability.
- Structured candidate decisions, interactions and interpretable contribution features.
- Learned English discussion-review model alongside the rule-based workflow.
- Controlled fusion comparisons and exploratory outcome-alignment diagnostics.
- Established models are reused; no claim of a newly invented foundation model.

**Say**

> Our contribution is the concrete integration, the source-preserving intermediate representation, and the scoped evaluation of its components. We implemented the application, stage coordination, temporal attribution, document association, event and lineage logic, contribution computation, recovery and review interface. We also trained the smaller discussion detector and examined contribution features experimentally. Whisper, MiniLM, random forests and Ridge regression already exist. We should describe an engineering and experimental contribution, not claim that using these algorithms proves worldwide algorithmic novelty or that no existing meeting assistant offers similar features.

## Slide 04 — We do have a summary: why no generative notes?

**On the slide**

- Implemented: structured executive summary from detected events and decisions.
- It includes proposals, candidate confirmed decisions and action-item excerpts.
- Not deployed: LLM-written abstractive notes or a meeting chatbot.
- Core requirements are traceability, local execution and reviewable outputs.
- Generative notes could be an optional future view, with factuality evaluation.

**Say**

> We have not removed summarization completely. The report generator already constructs an executive summary from structured outputs, including proposals, detected decisions and action items. What we have not added is a separate large language model that rewrites the meeting into free-form prose. That component is not required to establish source-linked review, speaker attribution or contribution analysis. Keeping the current summary extractive avoids introducing a new rewriting stage and supports local operation without a paid inference API. However, extraction can still miss or misclassify statements. Generative summarization is useful, not inherently unsuitable; a grounded, evaluated version could be added later.

## Slide 05 — Modalities: what information enters the system?

**On the slide**

- Audio: waveform, speech content, word times and speaker-related acoustic information.
- Optional PPTX documents: native text, tables, notes and document metadata.
- Downstream fusion compares ASR text with extracted document text.
- Slide-display timing is optional metadata; a PPTX file does not supply it automatically.
- No face, gaze, emotion, gesture or general chart-understanding model.

**Say**

> Our two input sources are audio and presentation documents. From audio we derive text, timestamps and speaker intervals. From PPTX we extract document content. It is accurate to call the application multimodal at the input and information-processing level, but we must explain that its main semantic fusion happens after both sources have textual representations. The extracted transcript is derived from audio, not a third independent input modality. The present implementation does not jointly train acoustic and image features, and it does not interpret facial expressions or arbitrary slide diagrams. OCR is optional and disabled in the default configuration.

## Slide 06 — Complete system architecture

**On the slide**

- Browser record/upload → authenticated FastAPI validation and queue.
- FFmpeg normalization → Whisper transcript → speaker diarization and word attribution.
- Optional PPT extraction → passage-to-slide alignment.
- Events/evidence → decision candidates → interactions and contribution scores.
- Report, history, audio playback, human corrections and exports.

**Say**

> The browser sends ordered audio parts and optional presentations to the API. The API validates the request, stores it and returns a meeting identifier with HTTP 202. A single background worker processes the meeting. It normalizes the audio, produces draft words, estimates speaker intervals and attributes words to speakers. Optional document alignment enriches the transcript representation. Rule-based event analysis, evidence associations and decision reconstruction then feed interactions and contribution features. The learned discussion detector is a separate branch. Finally, the report is saved and the browser retrieves progress and results by polling.

## Slide 07 — Phase 1: input handling and audio preparation

**On the slide**

- Accept ordered parts of one recording and optional ordered PPTX files.
- Validate type, decodability, options and aggregate upload size.
- FFmpeg converts audio to 16 kHz, mono, PCM16 WAV.
- Save inputs, job state and checkpoints for recovery.
- Concatenating recording parts is not microphone-array fusion or source separation.

**Say**

> Audio models need a consistent input representation, so we use FFmpeg to decode and normalize recordings to 16-kilohertz mono PCM16. The web API accepts up to 32 audio parts and up to 32 presentations, in their intended order, with a configurable aggregate upload limit whose code default is one GiB. These are implementation limits, not claims about provider upload limits or quality. We preserve inputs and progress. We have not implemented denoising or acoustic separation of overlapping voices; normalization only standardizes the format.

## Slide 08 — Phase 2: speech recognition model

**On the slide**

- Pretrained multilingual Whisper through faster-whisper / CTranslate2.
- Shared default: small model, CPU, int8, beam size 5, four threads.
- 120-second central chunks, word timestamps and speech filtering.
- Draft recognition appears before final whole-meeting speaker attribution.
- Pretrained weights are reused; Whisper was not trained by our team.

**Say**

> Whisper performs automatic speech recognition: it predicts the words spoken in the audio. faster-whisper is the inference implementation, with CTranslate2 providing execution. We use small as the shared default and int8 computation for a practical CPU deployment. Central chunks are 120 seconds with short surrounding context, and midpoint selection avoids intentionally duplicating boundary words. Recognition observations and speaker attribution have separate caches, so attribution can be updated without necessarily repeating unchanged recognition. English and Hindi are the configured language scope; this does not establish reliable arbitrary Hinglish meeting recognition.

## Slide 09 — Phase 3: speaker diarization and word attribution

**On the slide**

- Sherpa-ONNX: pretrained segmentation, speaker embeddings and whole-meeting clustering.
- Configured clustering threshold 0.9; optional exact known speaker count.
- Assign each word using greatest qualifying speaker-time overlap.
- Ties or inadequate coverage produce UNKNOWN; names remain reviewable labels.
- Diarization groups voices; it does not verify identity or separate mixed voices.

**Say**

> Diarization asks who spoke when. The selected engine uses local pyannote-style segmentation and a 3D-Speaker ERes2Net embedding model through Sherpa-ONNX. It clusters the meeting into anonymous speaker groups. We then calculate word-to-speaker temporal coverage and assign the strongest qualifying speaker, with default minimum coverage 0.3. Ambiguous words can stay UNKNOWN. A user can review speaker names or provide the actual speaker count. This does not make acoustic attribution infallible, and whole-meeting clustering means that ASR chunking does not make the entire pipeline bounded-memory streaming.

## Slide 10 — Phase 4: document extraction and semantic representation

**On the slide**

- python-pptx extracts title/body text, tables and speaker notes.
- all-MiniLM-L6-v2 represents slide and transcript text as 384-dimensional vectors.
- Cosine similarity supplies the semantic matching score.
- TF-IDF is an implemented lexical alternative, not an extra averaged score.
- Native text extraction does not equal general visual understanding.

**Say**

> A slide's text representation combines its title, body, table cells and notes. MiniLM encodes this content and each transcript passage into a shared sentence-vector space, where cosine similarity measures semantic closeness. This can relate paraphrases more flexibly than exact word matching. The model is pretrained and frozen in this project. It is lightweight enough for our CPU workflow, but the current model is English-oriented and we have not validated Hindi-to-English slide matching. TF-IDF is available as a lower-cost lexical alternative; it replaces the embedding method for a run rather than being averaged with MiniLM.

## Slide 11 — Which fusion techniques did we actually use?

**On the slide**

- Temporal association: recognized words + speaker intervals.
- Alignment score fusion: semantic similarity + available slide-display overlap.
- Unified records: passage, speaker, times, slide candidates and scores.
- Discussion detector: concatenate word, character and context TF-IDF features.
- Discussion detector: weighted probability ensemble of forest and logistic classifiers.

**Say**

> The main multimodal alignment technique is score-level fusion: the sources are processed first, and their semantic and temporal evidence is combined afterward. It is reasonable to describe this as a late score-combination design, but it is not a learned multimodal network combining two classifier labels. Separately, our discussion detector uses feature-level concatenation and a classifier-output ensemble. Those last two operations combine representations and models within text, so they should not be presented as additional physical modalities. The word-to-speaker operation is temporal information association, rather than learned cross-attention.

## Slide 12 — Temporal–semantic alignment formula and fallback

**On the slide**

- Semantic score: cosine between passage and slide embeddings.
- Temporal score: overlap with the slide's active interval / passage duration.
- Combined score = (0.5 × temporal + 0.5 × semantic) / (0.5 + 0.5).
- No valid slide timing → semantic-only; top 3 candidates, threshold 0.3.
- Below threshold → NO_CONFIDENT_SLIDE; similarity is not a probability.

**Say**

> With valid timing, the current prototype gives semantic and temporal evidence equal weight. For example, a temporal score of 0.8 and semantic score of 0.6 produce 0.7. When slide timing is missing, the semantic score is used on its own; the missing cue is not invented or treated as half a score. This is important because an uploaded deck usually does not tell us when each slide appeared. Therefore, the actual untimed audio-plus-PPT web path generally behaves as semantic alignment, even though the implementation supports hybrid scoring. The candidate can remain unassigned when confidence is weak.

## Slide 13 — Why these methods, and why not other fusion methods?

**On the slide**

- Modular scores are inspectable and support missing document/timing inputs.
- Pure timing struggles with missing timestamps and references to earlier slides.
- Pure semantics struggles with vague phrases such as “this figure.”
- No jointly trained early-fusion or cross-attention model was implemented.
- Alternatives need aligned labels, computation and fair validation; no superiority claim.

**Say**

> This design fits our separate audio and document sources and CPU-oriented deployment. Semantic matching can work without a slide-transition log, while timing can help with context-dependent phrases. Early raw-feature fusion, learned gating, cross-attention and multimodal Transformers are possible alternatives. Our rationale for not implementing them is the project scope, limited aligned supervision and the need for an inspectable modular system. We did not run a fair benchmark proving those alternatives are worse. Our fixed equal weights are prototype defaults, and the results show that they need more careful validation before a production hybrid claim.

## Slide 14 — Phase 5: events, evidence and decision candidates

**On the slide**

- Default bilingual rules identify 11 event categories.
- Categories include proposals, evidence, objections, revisions, decisions and actions.
- Evidence relations use event type, speaker, timing and available slide links.
- Decision reconstruction groups related candidates and records source lineage.
- Detected “confirmed” is a system status, not human-verified correctness.

**Say**

> The default event extractor uses explicit rules for eleven categories: proposal, question, objection, evidence, correction, clarification, agreement, disagreement, revision, decision and action item. Evidence associations typically use a 60-second window, and decision grouping uses a configurable window whose default is 120 seconds. The system stores the source events behind candidate decisions and unresolved proposals. An explicit decision-like expression can produce the status confirmed, but that is a rule-based system label. It does not establish that the meeting genuinely adopted a decision, particularly when recognition or context is wrong.

## Slide 15 — Separate learned discussion detector: what we trained

**On the slide**

- English discussion membership: suggest passages for review, not final decisions.
- Word unigrams/bigrams + character 3–5 grams + up to ±40 context units.
- Concatenate sparse TF-IDF features; forest 75% + logistic regression 25%.
- Smooth over ±5 units; decision threshold approximately 0.35774.
- AMI split: 29 training, 6 development and 12 historical meetings.

**Say**

> Our smaller supervised model predicts whether an English passage belongs to decision-related discussion. The active features are word TF-IDF, character TF-IDF and context-40 TF-IDF. The installed forest has 100 trees with maximum depth 10; logistic regression uses C equal to 3 and balanced class weights. We combine their positive-class scores with weights 0.75 and 0.25, then apply neighborhood smoothing and the selected threshold. These settings were selected using development data. Evaluation used human reference dialogue acts, while the application receives ASR passages, so the reported discussion metric is not end-to-end application accuracy.

## Slide 16 — Phase 6: interactions and participant contribution scores

**On the slide**

- Build directed source-linked interactions from evidence and decision lineage.
- Seven contribution features; normalize each across meeting participants.
- Weights: proposal .15, evidence .20, objection .15, revision .20.
- Decision .15, interaction .05, slide grounding .10.
- A reviewable prototype score; not PageRank, causality or a personal rating.

**Say**

> For each participant, we count or aggregate decision-linked contributions such as proposals, linked evidence, objections and revisions. Each feature is divided by that feature's maximum in the meeting, then the seven weighted features are added. A zero can mean that no relevant evidence was extracted, not that the person contributed nothing. A highest score such as 0.7 is possible because some categories may be absent and their weights are not redistributed. Scores do not sum to one across people. Interaction graphs expose inferred relationships; graph arrows and temporal order do not prove causal influence.

## Slide 17 — Frontend, backend, storage and local operation

**On the slide**

- React/Vite: record, upload, progress, transcript, review, charts and exports.
- FastAPI/Uvicorn: validation, accounts, queue, processing and private API access.
- SQLite/SQLAlchemy plus private audio, checkpoints and report files.
- bcrypt password hashing and JWT login; one serialized ML worker.
- Offline inference after model provisioning; cloud clients still need connectivity.

**Say**

> The frontend captures recordings using browser APIs, preserves drafts locally and polls job progress. The backend validates and persists work before one background executor processes it. It stores account history in SQLite and larger artifacts on disk. A second analysis waits, which is a deliberate resource constraint. Model provisioning needs internet once; processing can then run without external inference APIs. In cloud mode, local inference means computation on the server, while the user's browser still needs a network connection. The separate native Android application also supports local processing, but does not have exact Python model or output parity.

## Slide 18 — Outputs and human review

**On the slide**

- Timestamped transcript, anonymous speaker groups and source audio playback.
- Optional slide candidates and alignment scores.
- Discussion passages, candidate decisions, actions and source references.
- Interaction and contribution breakdowns, warnings and structured executive summary.
- Saved history; review edits; JSON, text, subtitle, table and calendar exports.

**Say**

> The outputs let a person move from a candidate result back to the original passage and recording. Users can review names and roles, correct speaker count through reanalysis, inspect decision evidence, review follow-up tasks and export results. The structured executive summary is one view of those outputs. JSON preserves structured information, text and subtitle exports support reuse, and reviewed tasks can be exported as calendar data. A source pointer makes verification possible; it does not guarantee that the linked statement is relevant or correctly recognized.

## Slide 19 — Fusion comparison: the controlled diagnostic

**On the slide**

- 24 author-designed cases; six constructed slides; top-1 correctness includes abstention.
- Temporal-only: 12/24 correct → 50.00%.
- Semantic-only: 20/24 correct → 83.33%.
- Equal-weight hybrid: 16/24 correct → 66.67%.
- Semantic-only wins this constructed diagnostic; it is not a real-meeting benchmark.

**Say**

> We did compare fusion strategies. The constructed diagnostic includes exact content, paraphrases, vague context, offscreen references, missing timing and unrelated passages. Semantic-only produced the highest overall top-1 result. The hybrid helped the four context-dependent cases, but failed the offscreen and unrelated groups. A visible slide can receive a high temporal score even when it is irrelevant. For example, temporal one and semantic zero combine to 0.5, which exceeds our threshold of 0.3. That explains why a fixed temporal weight can force a false link. We therefore report the negative result instead of claiming hybrid superiority.

## Slide 20 — Real fusion example: coverage is not accuracy

**On the slide**

- Real record: 1,008 passages and 34 slides; no valid slide-display timestamps.
- Temporal-only: 0 links; semantic-only: 39 links.
- Hybrid: the same 39 links, because its missing-timing fallback is semantic-only.
- Link coverage: 39/1,008 = 3.87%; semantic/hybrid agreement = 100%.
- Independent relevance labels are missing, so accuracy and F1 are unavailable.

**Say**

> This is a real unlabelled application record, unlike the constructed diagnostic. It shows that most passages remained unlinked under the threshold, and that the semantic fallback behaved consistently. It does not tell us how many of the thirty-nine links are correct. Low coverage could reflect irrelevant slides, recognition or language mismatch, a conservative threshold, or weak semantic representation; we cannot choose one explanation without review labels. One hundred percent agreement between two methods also does not establish correctness when they implement the same fallback.

## Slide 21 — Discussion results and the misleading-accuracy trap

**On the slide**

- Historical reference-act cohort: precision 39.94%, recall 81.18%, F1 53.54%.
- Model accuracy: 68.62%; balanced accuracy: 73.10%.
- Always-negative baseline accuracy: 77.72%, but positive-class F1 = 0.
- High recall supports review suggestions; low precision means false positives.
- Reference-text results do not validate final decisions or raw-audio performance.

**Say**

> Accuracy alone is misleading because the classes are imbalanced. Always saying that a passage is not a discussion obtains higher raw accuracy than our installed detector, but retrieves no positive discussion passages. Our detector retrieves many positives, reflected in recall around eighty-one percent, while precision around forty percent means that many suggestions need rejection. Positive-class F1 is approximately fifty-four percent. These figures justify cautious review assistance, not autonomous decision extraction. The historical cohort has been examined repeatedly, so it should be described as exploratory rather than a fresh independent confirmation.

## Slide 22 — Speech and speaker evaluation: small scoped pilots

**On the slide**

- WER measures word errors; DER measures speaker-time errors; lower is better.
- Hindi, 8 samples: Small WER 50.96%; Turbo 28.85%.
- Hinglish, 8 samples: Small 66.13%; Turbo 57.26%.
- Historical English, 2 clips: Small 61.61%; Turbo 63.91%.
- Speaker pilot: pooled DER 64.08% → 40.91%; only two held-out excerpts.

**Say**

> Larger speech models did not improve every cohort. Turbo improved this small Hindi pilot but regressed on the two historical English clips. This supports retaining the smaller shared default while allowing model choice; it does not prove Small is the most accurate model. WER includes substitutions, deletions and insertions, and should not simply be renamed accuracy. Diarization threshold 0.9 was selected using development excerpts, then examined on two different held-out excerpts with a 0.25-second collar and overlap included. These are limited pilots, not full-corpus or multilingual-meeting guarantees.

## Slide 23 — Influence research: a separate exploratory task

**On the slide**

- GAP study: 28 meetings, 84 people and 87 comparable participant pairs.
- Compare participation features, contribution features and their combination.
- Combined Ridge: 68.93% pairwise; participation-only Ridge: 61.79%.
- Word count: 66.55%; duration: 67.86%; fixed prototype score: 55.77%.
- Outcome alignment is a proxy, not ground-truth causal influence.

**Say**

> The ranking research is separate from the default interface score. Its combined Ridge representation uses six participation and seven contribution features, with meeting-group cross-validation and training-fold scaling. The combined model obtains sixty-eight point nine three percent mean meeting-level pairwise accuracy. Its improvement over participation-only Ridge is seven point one four percentage points, but the descriptive paired interval crosses zero. The margin over word count is smaller and also uncertain. The corpus had already been examined and uses reference text and speakers without slides, so this cannot validate the complete multimodal pipeline or causal influence.

## Slide 24 — Engineering validation and deployment status

**On the slide**

- Saved earlier full-suite record: 656 Python tests; latest hosting subset: 59 passed.
- Real Docker check: 2 audio parts + 2 PPTs, 30 seconds of public English speech.
- 2 CPUs / 4 GiB limit: 33.821 seconds post-upload processing, 14 transcript segments.
- Playback, export, account isolation and volume-backed container replacement passed.
- Backend packaged for Hugging Face; public hosting and cloud latency not verified.

**Say**

> Software tests check behavior and protections; they are not a percentage of meeting-analysis correctness. The recent container test exercised real models and two audio and presentation inputs. It checked completed outputs, audio playback, export, isolation and retained state after replacing the container with the same volume. Docker Desktop needed recovery from local host memory pressure during image import, after which the runtime test passed. This is a local resource-limited test, not a hosted latency result. Persistent Docker-volume behavior also does not automatically certify a provider's object-storage mount for SQLite.

## Slide 25 — Missing features, necessary work and future scope

**On the slide**

- Necessary: larger independent labels, end-to-end accuracy and deployment-storage validation.
- Necessary: reduce speaker/event errors and evaluate real reviewer usefulness.
- Not required for this scope: facial analysis, emotion scoring or a chatbot.
- Optional extensions: grounded generative notes, slide-transition capture and learned fusion.
- Do not equate an omitted convenience feature with an unimportant correctness gap.

**Say**

> Some omissions are scope choices: a chatbot, face tracking or generative prose is not needed for the implemented source-review objective. Other omissions are real validation gaps: we need independent multimodal relevance labels, robust speaker-attributed evaluation and trustworthy contribution references before stronger claims. The existing score is sensitive to missing events and speaker errors, and real user usefulness has not been measured. Future work should first improve and validate those foundations, then evaluate optional grounded summaries or learned fusion. Cloud durability and concurrency also need verification before broader public use.

## Slide 26 — Demonstration and conclusion

**On the slide**

- Open a completed meeting; play an original transcript timestamp.
- Inspect a speaker, discussion passage, action and candidate decision's sources.
- Show slide links or explicit unassigned passages, then the contribution breakdown.
- Export a report and explain the metric's exact scope.
- Contribution: local, source-linked review with transparent evidence and limitations.

**Say**

> To conclude, we built a working meeting-review application that combines pretrained speech, speaker and text representations with structured analysis and smaller learned components. Its strength is an inspectable workflow: the reviewer can return to the evidence, see uncertainty, correct permitted metadata and reuse the report. Our comparisons do not show universal hybrid improvement, and our contribution score is not a validated causal judgment. We have demonstrated the pipeline and identified where stronger supervision and evaluation are needed. I will now show a completed meeting and trace one candidate result back to its original source.

## Appendix A — Every phase: model, reason and boundary

| Phase | Actual method | Why it is used | Important boundary |
| --- | --- | --- | --- |
| Input preparation | FFmpeg decode/resample; 16 kHz mono PCM16 | Compatible waveform and ordered input parts | No denoising or multi-microphone signal fusion |
| Speech filtering | faster-whisper VAD filter; standalone Silero module also exists | Limit non-speech processing | Separate Silero stage is not mandatory in every web run |
| Recognition | Pretrained Whisper Small, faster-whisper/CTranslate2, int8 | CPU-oriented multilingual recognition and timestamps | No Whisper training or broad Hinglish validation |
| Speakers | Sherpa-ONNX segmentation + 3D-Speaker ERes2Net + FastClustering | Local whole-meeting anonymous voice grouping | No verified identity, voice separation or streaming-memory guarantee |
| Word attribution | Unioned speaker-interval overlap, coverage threshold | Associate recognized words with voice intervals | ASR boundaries and overlap errors can yield wrong labels |
| PPT extraction | python-pptx; text/tables/notes; optional Tesseract OCR | Access document content without a general visual model | OCR defaults off; diagrams are not generally understood |
| Slide semantics | all-MiniLM-L6-v2, 384-dimensional vectors, cosine | Text-semantic matching with a small pretrained encoder | English-oriented; cross-language matching unvalidated |
| Alignment alternative | TF-IDF cosine | Lexical matching and native Android feasibility | Misses paraphrases and many language equivalents |
| Alignment fusion | Weighted temporal/semantic scores; missing-timing fallback | Inspectable cue combination with optional timing | Equal weights are prototype settings, not validated optimum |
| Event extraction | Default KeywordEventExtractor, bilingual rules | Explicit candidate categories and source traces | Indirect language, negation and ASR mistakes remain difficult |
| Evidence/decisions | Event-role, time and speaker rules; source-linked lineage | Reconstruct reviewable relationships and candidates | Not formal entailment or causal inference |
| Learned review | TF-IDF concatenation; logistic + random forest; smoothing | Suggest English decision-discussion passages | Distinct from final decisions and default influence scoring |
| Interactions | Inferred event/lineage relations; directed graph representation | Explain speaker associations | Default scorer is not PageRank or a graph neural network |
| Default contribution | Max-normalized seven-feature weighted sum | Transparent feature breakdown | Prototype weights; meeting-relative, extraction-dependent |
| Ranking research | StandardScaler + Ridge; grouped nested CV | Controlled exploratory comparison of feature families | Not the default deployed UI scorer or causal target |
| Report | Structured extraction and export templates | Preserve detected content and source references | No LLM paraphrase; extraction is still fallible |

## Appendix B — Equations with simple explanations

**Word/speaker attribution:** overlap = max(0, min(word_end, turn_end) − max(word_start, turn_start)). Union intervals for the same speaker before totaling. Coverage = overlap / word duration. Select the best qualifying speaker; ties or weak evidence can remain UNKNOWN.

**Semantic similarity:** cosine(u,v) = (u·v) / (||u|| × ||v||). This measures similarity of representations, not the probability that the slide proves a statement.

**Temporal slide score:** T = passage/slide-active-interval overlap / passage duration. It requires real timing metadata, not simply slide order.

**Alignment combination:** C = (wT×T + wS×S)/(wT+wS). Defaults wT = wS = 0.5. With missing timing and the normal nonzero semantic weight, C = S. Pure temporal-only configuration cannot invent missing timing.

**Discussion ensemble:** p = 0.75×p_random_forest + 0.25×p_logistic. Smooth within the meeting over up to five neighboring units in each direction. Flag p at or above 0.3577398635496262. It is not a calibrated guarantee of correctness.

**Contribution normalization:** z(p,k) = x(p,k) / max_q x(q,k), or zero for an inactive feature. I(p) = Σ_k w_k z(p,k). Missing categories remain zero. A top score need not equal 1. Scores are not shares of a fixed total across people.

**WER:** (substitutions + deletions + insertions) / reference words. Lower is better; insertions mean it is not a simple bounded classification error.

**DER:** (missed speech time + false-alarm speech time + speaker-confusion time) / reference speaker time, under a stated mapping, overlap and collar protocol.

**Precision:** correct positive suggestions / all positive suggestions. **Recall:** correct positive suggestions / all true positives. **F1:** 2PR/(P+R). **Coverage:** linked passages / all passages. These answer different questions.

## Appendix C — Fusion comparison: explain the outcome rather than hide it

| Constructed group | Temporal correct / 4 | Semantic correct / 4 | Hybrid correct / 4 |
| --- | ---: | ---: | ---: |
| Exact content | 4 | 4 | 4 |
| Paraphrases | 4 | 4 | 4 |
| Vague/context-dependent references | 4 | 0 | 4 |
| References to an offscreen slide | 0 | 4 | 0 |
| Missing slide timing | 0 | 4 | 4 |
| Unrelated or blank passages | 0 | 4 | 0 |
| Total | 12/24 | 20/24 | 16/24 |

The hybrid's coverage was 100%, including links on cases that should have been rejected. Semantic coverage was 66.67%, because abstention can be correct. More coverage is therefore not automatically better. This diagnostic checks constructed behaviors; its small author-designed sample cannot establish general statistical superiority.

The real comparison contains no independent relevance labels. Its temporal-only links = 0, semantic links = hybrid links = 39, total passages = 1,008, total slides = 34, valid timed slides = 0. No accuracy or F1 can be reported there. Labels and representative meetings are needed before choosing or learning improved weights. A possible future method would gate unreliable timing instead of adding it with a constant weight; that gating is not implemented in the current default.

## Appendix D — Novelty and “why not” answers

**Supported contribution statement:** “We implemented a local, source-preserving meeting-review workflow that connects speakers and optional document context to structured decision-related candidates and interpretable contribution features. We also trained a smaller discussion-review detector and evaluated selected representations and fusion choices with explicit scope limits.”

**Do not claim:** first-ever meeting assistant; newly invented Whisper/MiniLM/fusion; universally superior hybrid; verified causal influence; hallucination-free output; robust multilingual performance; a single whole-system accuracy; an independent test when a corpus was repeatedly examined.

**Why not only a summary?** The core question includes who said what, which evidence supports a candidate and how to inspect it. The existing structured summary is one compact view of that richer representation. A generated summary by itself would not provide those capabilities automatically.

**Why not an LLM everywhere?** It is a reasonable alternative, but it adds a separate inference and evaluation stage. Local CPU feasibility, direct source preservation and prototype scope motivated the implemented design. We did not prove that an LLM-based system is less accurate, slower or less private in every configuration; local LLMs also exist.

**Why Small rather than Turbo by default?** Small is a practical CPU-oriented default; larger models are optional. The saved pilots show mixed effects rather than universal model superiority. Small is not claimed to be the most accurate option.

**Why MiniLM rather than TF-IDF by default?** Pretrained sentence representations provide a mechanism for matching paraphrases with limited task-specific training. TF-IDF is implemented as an alternative. The three-way fusion diagnostic does not itself isolate MiniLM versus TF-IDF, so do not invent a benchmark proving one always wins.

**Why rules for events?** They supply explicit candidate patterns and source links in a small prototype. Their limits are visible and include context dependence and missed roles. An experimental learned contextual extractor exists, but the normal web path uses default rules; it should not be described as if that research model powers every UI result.

**Why not early/raw fusion?** The audio waveform and document are asynchronous, heterogeneous inputs. A meaningful learned combination needs a representation and alignment protocol plus suitable supervision. Using transparent derived representations was a project choice, not a claim that raw fusion is mathematically impossible.

**Why not cross-attention, a GNN or reinforcement learning?** None was necessary to implement the specified review workflow, and each would need an appropriate training target, data and fair evaluation. No controlled benchmark of those alternatives was run. The existence of a graph representation does not mean a GNN was trained.

**Why keep hybrid support if it loses?** Timing can resolve some vague references, as the constructed context-dependent cases show. The implementation also supports missing timing. Retaining a capability does not justify claiming it is the best default for every dataset; fixed weights need further validation.

## Appendix E — Missing versus unnecessary: classify honestly

| Item | Status | Why it matters |
| --- | --- | --- |
| Structured executive summary | Implemented | Compact view of detected proposals, decisions and actions |
| LLM-written notes / chatbot | Not deployed; optional future feature | Useful convenience, not required for the current review objective |
| Human source review | Required by design | Candidates and scores remain fallible |
| Large independent real multimodal labels | Missing validation | Necessary for stronger alignment/fusion accuracy claims |
| Independent causal contribution labels | Missing | Outcome alignment does not establish causal influence |
| Robust Hindi/English code-switching validation | Missing | Current tiny pilots do not represent real mixed-language meetings |
| Speaker identification / overlapping-voice separation | Not implemented as verified capabilities | Anonymous diarization is not either of these tasks |
| Facial expression, gaze and emotion analysis | Outside present scope | Not needed to demonstrate the implemented source-linked workflow |
| Automatic slide-transition capture | Not implemented in normal PPT upload | Required if temporal alignment is to use actual display timing automatically |
| General chart/image reasoning | Not implemented | Extracted text/metadata and optional OCR do not provide this |
| Multi-user parallel ML processing | Limited to one worker | Wider load needs queue, storage and concurrency design |
| Persistent public cloud deployment | Not yet verified | Prepared packaging and local volume tests are not a hosted deployment |
| User study and measured review-time savings | Not performed | Necessary to quantify practical reviewer benefit |
| Broader fairness, calibration and domain testing | Not established | Scores should not be used as personal performance judgments |

## Appendix F — Rapid viva: direct answers to likely questions

**1. What exactly is your research question?** Whether source-linked speech, document context and extracted contribution features can support review and an exploratory comparison with an outcome-alignment reference. Application functionality, discussion detection and ranking are distinct evaluation tasks.

**2. What did your team train?** The smaller discussion-review classifiers and separate experimental research models. The deployed speech, speaker and embedding networks are pretrained components, not foundation models trained by the team.

**3. Where is AI if some stages use rules?** Recognition, speaker segmentation/embeddings, sentence embeddings and discussion classifiers use learned models. The subsequent rules associate their outputs into reviewable structure.

**4. Is this really multimodal if matching is text-to-text?** It uses heterogeneous audio and document inputs, with semantic alignment performed on derived textual representations. We explicitly do not claim a raw acoustic-image fusion network or independently learned visual understanding.

**5. Are transcript text and audio two independent modalities in your experiment?** Transcript text is derived from the same audio, so we should not count it as an independently supplied additional source to inflate the modality count.

**6. Is speaker identity a modality?** Speaker intervals are acoustic metadata/features derived from audio, not a new independently supplied input modality.

**7. Is your fusion early, intermediate or late?** The alignment combines separately computed semantic and temporal evidence scores; score-level or late score fusion is the most precise description. The discussion classifier additionally has feature concatenation and probability ensembling within text.

**8. Are TF-IDF and MiniLM fused together?** No. They are selectable alignment methods. The normal Python path uses embeddings, and the native Android path uses lexical TF-IDF.

**9. Is the forest/logistic ensemble multimodal?** It is model-output combination, but its inputs are text-derived features. It is not an additional audio-image fusion experiment.

**10. Are the fusion weights learned?** The normal alignment weights are prototype configuration values, 0.5 and 0.5. Discussion ensemble weights are selected model settings. These are different sets of weights.

**11. Why use threshold 0.3?** It is a prototype alignment setting that allows abstention. It has not been established as a calibrated or universally optimal threshold on independent real multimodal labels.

**12. Why did hybrid do worse?** A temporal cue can be misleading for unrelated visible content or references to a different slide. Equal fixed weights can push that cue above the acceptance threshold. The constructed group counts make that failure visible.

**13. What does 3.87% mean?** Thirty-nine of 1,008 passages received slide links. It measures coverage, not accuracy; the real record has no independent slide-relevance labels.

**14. What does 100% agreement mean?** Semantic and hybrid produced the same selections because timing was absent. They could agree on correct or incorrect selections.

**15. What happens without a PPT?** The audio transcript proceeds to event analysis without document alignment. The core audio-only review path remains available.

**16. How do you know which slide was visible?** Only if valid slide-display timing is supplied. The normal PPTX document order is not a synchronized display log.

**17. Is the system hallucination-free?** No. It does not add an LLM rewriting stage, but recognition can produce incorrect words and downstream rules or links can be wrong. Source preservation helps inspection rather than guaranteeing truth.

**18. Does Whisper generate text?** Yes, its speech-recognition decoder predicts transcription tokens. “No generative notes” means no separate chat-style model writes free-form meeting summaries; it does not mean the application contains no neural text generation at all.

**19. Does MiniLM mean you use a language model?** Yes, a pretrained text encoder produces representations. The structured-summary stage itself does not invoke a language model to paraphrase content.

**20. Why not just use ChatGPT or a commercial assistant?** Our implemented focus is local processing and inspectable source-linked review. We did not run a matched commercial-system benchmark, so we cannot claim commercial tools are universally worse or lack these features.

**21. Are detected decisions guaranteed final?** No. They are candidate reconstructions based on detected event patterns and context. A label such as confirmed is a system category, not human adjudication.

**22. Is an action item the same as a decision?** No. An action is a proposed or stated task; a decision is an inferred commitment or resolution. They can be related but are separately represented.

**23. Is the discussion detector a decision detector?** It suggests membership in decision-related discussion. A discussion may contain alternatives or questions without a final adopted decision.

**24. Why are some people scored zero?** Their attributed transcript may not contain scored decision-linked events, or extraction and speaker errors may have removed those features. Zero does not establish zero real contribution.

**25. Why is the top score 0.7 rather than 1?** Normalization occurs per feature. Some feature categories can be inactive, and their weights are not redistributed, so no participant needs to achieve the full weighted total.

**26. Is influence a probability?** No. It is a meeting-relative prototype weighted score whose component evidence is inspectable.

**27. Is influence causal?** No. A temporal association, lineage arrow or outcome-alignment proxy does not demonstrate that a participant caused a decision.

**28. Is the final score PageRank?** No. The default is a weighted sum of seven normalized contribution features, even though interaction graph structures also exist.

**29. Why not count speaking time?** Speaking time is a useful baseline and is retained for comparison. The research question asks whether additional contribution information helps, and current experiments show that it does not consistently dominate participation baselines.

**30. Did the learned ranking clearly beat word count?** The combined Ridge point estimate was 68.93% versus 66.55%, but the descriptive difference interval includes zero. This is exploratory evidence, not reliable superiority.

**31. Does 68.93% describe the UI contribution score?** No. That result belongs to a separate grouped-CV Ridge study. The fixed prototype score obtained 55.77% under that study's protocol.

**32. Why is raw discussion accuracy lower than always-negative?** The positive class is less frequent. Predicting only negatives can score highly on accuracy while retrieving no relevant discussions, so we inspect precision, recall, F1 and balanced accuracy.

**33. Is F1 53.54% satisfactory?** It is a modest exploratory result with high recall and low precision. It can motivate review suggestions but does not justify autonomous high-stakes decisions or a strong accuracy claim.

**34. Did you fine-tune Whisper or MiniLM?** Not in the selected deployed pipeline. We provision and run pretrained weights. The smaller discussion models are trained on the project's labelled-text protocol.

**35. What prevents train/test leakage?** Discussion splitting groups related meeting series, and the ranking protocol groups by meeting and fits scaling within training folds. However, repeated historical inspection means those cohorts are exploratory; grouped splitting does not erase that history.

**36. Why not report only the best model for each language?** That would overstate generalization on tiny inspected pilots. We retain regressions and the shared default, and state the evaluated cohort and conditions.

**37. Is local inference the same as fully offline use?** A laptop or Android can process locally after provisioning. A remote browser still needs connectivity to its server; model downloads, account sync or cloud hosting need connectivity when used.

**38. Is a GPU required?** No for the tested CPU pipeline. GPU ASR is an optional execution mode requiring compatible runtime libraries; it does not automatically accelerate every stage.

**39. Why does another recording wait?** One background ML executor serializes jobs. This limits resource contention. More simultaneous users require an explicitly designed worker queue and shared durable state.

**40. Are speaker numbers real identities?** No. They are cluster labels; the frontend shows consecutive display numbers and allows review of names. Exact speaker count is a constraint, not verified identification.

**41. Can it handle simultaneous speakers?** The diarization/scoring protocol can represent overlapping activity, but the application does not acoustically separate mixed voices. Recognition and word attribution can remain uncertain.

**42. What are the main error-propagation paths?** Wrong ASR words can change event detection and slide matching; wrong speakers can misassign contributions; wrong event or evidence relations can distort candidate decisions and scores.

**43. What are the baseline methods?** Alignment compares temporal, semantic and hybrid cues; discussion compares against always-negative and other saved classifier protocols; ranking includes word count, duration and feature-family models. These are separate experiments.

**44. Is the 24-case fusion test a train/test experiment?** No. It is a frozen-encoder, author-designed diagnostic with known expected outcomes, not independent real-meeting generalization evidence.

**45. What would make the fusion claim stronger?** Independently labelled real meetings with slide transitions, separate development and held-out evaluation, matched preprocessing, uncertainty analysis and a tuned or learned fusion method evaluated without test leakage.

**46. What would make the contribution claim stronger?** Better event and speaker coverage, independent contribution annotations, a justified target, stronger baseline comparisons, calibration and human review studies.

**47. Which API key is used for analysis?** No paid external AI inference key is required for the selected local models. MAI_SECRET_KEY signs app login tokens; HF_TOKEN is for authenticated hosting operations or optional gated alternatives, not ordinary inference with the selected public weights.

**48. What is tested versus deployed?** The local application and a resource-limited Docker runtime were tested. Backend packaging is ready. No public Hugging Face/Render deployment or provider persistence guarantee has been verified in this session.

**49. Is this ready for employee evaluation or production decisions?** No. The current score and candidates are research/review outputs with known extraction, validation and fairness gaps.

**50. What is the final honest takeaway?** We built a working, inspectable meeting-review system using established models, implemented and tested its integration, and obtained scoped experimental results that expose both useful mechanisms and clear limitations.

## Appendix G — Presentation conduct and evidence locations

If interrupted, answer in this order: **what is implemented → how it works → the relevant measurement → its boundary**. Say “not evaluated” when that is the truth. Do not describe a future feature as implemented. Show one completed meeting before starting a long live recording. Explain a weak or zero result through its evidence rather than inventing a successful interpretation.

| Topic | Primary project evidence |
| --- | --- |
| Workflow and branches | `src/pipeline/orchestrator.py` |
| Current configuration | `config/config.yaml` |
| API, authentication and worker | `backend/api.py` |
| Frontend behavior | `frontend/src/App.jsx` |
| Word/speaker attribution | `src/audio/asr.py` and `src/audio/onnx_diarization.py` |
| Alignment formula and fallback | `src/fusion/multimodal_representation.py` |
| Slide embedding construction | `src/ppt/embeddings.py` |
| Event/decision/contribution logic | `src/meeting/events.py`, `decisions.py`, `influence.py` |
| Structured executive summary | `src/report/generator.py`, `_build_executive_summary()` |
| Installed discussion model | `models/discussion/model.joblib`, `src/meeting/discussions.py` |
| Controlled fusion results | `outputs/evaluation/final_ca4/controlled_comparison.json` |
| Real unlabelled fusion | `outputs/evaluation/final_ca4/real_unlabelled_comparison.json` |
| Discussion and speech scorecard | `professor_guidelines/evaluation/quality_scorecard/metrics.csv` |
| Speaker pilot | `professor_guidelines/evaluation/audio_summary.json` |
| Ranking protocol/results | `docs/paper_20261024/analysis/protocol.json`, `results.json` |
| Recent Docker validation | `outputs/evaluation/huggingface_backend_20261026.json` |

Primary external references for reused methods: [Whisper paper](https://arxiv.org/abs/2212.04356), [MiniLM sentence-model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [Sherpa-ONNX diarization documentation](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html), [multimodal taxonomy survey](https://arxiv.org/abs/1705.09406). These explain established methods, not evidence that our implementation outperforms other systems.

Preparation check: removed one stray `%` from the controlled-comparison JSON so it parses again; no saved numerical values were changed and no accuracy experiment was rerun. This presentation is an evidence-based explanation, not independent validation of the complete system.
