# InfluenceIQ — 15-minute presenter guide

Use `InfluenceIQ_ESE_Final.pptx` for the presentation. The final deck contains exactly 18 slides, using the original headings and order. Slide 18 is the post-event photograph slot. The spoken plan is 14 minutes, with one minute reserved for transitions and small delays. Questions are outside the 15-minute plan. PowerPoint/Impress presenter notes contain the same prompts.

## Suggested handoffs

| Presenter | Slides | Planned speaking time | Focus |
| --- | --- | --- | --- |
| Anushka Chatterjee | 1–4 | 2:45 | MAI project: local meeting review with source evidence. |
| Amitkumar Racha | 5–8 | 3:40 | All six phases have artifacts; a fresh independent final evaluation is still future work. |
| Sahil Awatramani | 9–12 | 3:45 | Requirements cover the user journey and processing reliability. |
| Shriyans Sahoo | 13–18 | 3:50 | Functional checks establish execution; independent references establish accuracy. |

These are rehearsal assignments, not statements of who implemented each feature. Swap blocks if needed.

## Nontechnical audience rules

- Explain ASR as “what was said” and diarization as “who spoke when.”
- Use the illustrative discussion/decision example before the model formula.
- Do not read every architecture box; follow the three sweeps in slide 8’s notes.
- Define precision as “how many suggestions were right” and recall as “how much reference discussion was found.”
- Say “historical discussion F1 using human text,” never “overall project accuracy.”

## Rehearsal script

### 1. MAI Project AY 2026–27

**Anushka Chatterjee • 00:00–00:30 • 30 seconds**

Good evening. We are Group 12, presenting our MAI project, InfluenceIQ, under the guidance of Dr. Nivedita Mishra at Symbiosis Institute of Technology, Pune. Our aim is to help a reviewer find relevant decision discussion and return to the original words, speaker and recording time. We will explain the full architecture, compare the learned discussion detector with other classifiers, and show the scope of the results.

**Transition:** First, why is a meeting recording alone difficult to review?

**Evidence / limit:** Cover follows the supplied reference layout with the corrected MAI Project label. Team contacts: Anushka — anushkac2311@gmail.com; Amitkumar — rachaamitkumar@gmail.com; Sahil — sahilawatramani@gmail.com; Shriyans — shriyanssahoo2005@gmail.com. Faculty guide: nivedita.mishra@sitpune.edu.in.

### 2. Introduction

**Anushka Chatterjee • 00:30–01:15 • 45 seconds**

A recording contains the whole meeting, but a reviewer still has to locate the part that matters. There are three practical questions: where was the topic discussed, who spoke, and what exactly was said? Errors in any of these can change the interpretation. We therefore designed a review workflow around source passages. The system helps a person navigate and inspect evidence. It does not replace the person who decides whether a proposal was actually accepted.

**Transition:** A small example makes that distinction clearer.

### 3. Problem Statement

**Anushka Chatterjee • 01:15–02:05 • 50 seconds**

The statement on the left discusses a possible choice and asks for evidence. It is relevant to a decision, but the choice is not final. The statement on the right sounds like an agreement and can become a candidate for further review. Our supervised model is trained for the broader discussion-membership task. Its output is therefore a passage to inspect, not an automatic final decision. These sentences are illustrative examples; we are not presenting them as a model-accuracy test.

**Transition:** That gives us a precise set of project objectives.

### 4. Objectives of the Project

**Anushka Chatterjee • 02:05–02:45 • 40 seconds**

Our first objective is local processing after model provisioning. The second is traceability: a reviewer should see the original text and jump to its time in the recording. The third is evaluation with a clearly defined task. We compare models using the same discussion references, and evaluate speech errors separately. Functional requirements include audio upload or recording, optional presentations, editable participant labels, explicit stage status and source-preserving exports.

**Transition:** We positioned those objectives against related work rather than copying unrelated benchmark numbers.

### 5. Project Plan with Timeline

**Amitkumar Racha • 02:45–03:20 • 35 seconds**

The project progressed through six documented phases: defining scope, preparing project-separated data, comparing classifiers, selecting a score combination, integrating source-based review, and recording evaluation artifacts. We have removed the rough deck’s empty month fields. There is no evidence for precise phase dates, so this shows the completed sequence honestly. Independent final evaluation is not marked complete.

**Transition:** Here is what a user actually reviews.

### 6. Literature Review

**Amitkumar Racha • 03:20–04:10 • 50 seconds**

CALO established a broad meeting-assistant architecture. Whisper and alignment work provide the speech context, and diarization benchmarks show why speaker errors deserve a separate measure. Meeting datasets also study summarisation and evidence. Our implemented focus is narrower: local processing with extractive review suggestions, source links and a matched discussion-classifier comparison. We do not compare our F1 score with a summarisation score or claim that every external system is cloud-only or untraceable.

**Transition:** The next slide defines the project gap before we examine the complete solution.

**Evidence / limit:** References follow the paper. This is a scope comparison, not a head-to-head benchmark of complete assistants.

### 7. Gap in the Research / Technology / Methodology

**Amitkumar Racha • 04:10–04:55 • 45 seconds**

Related work already provides recognition, diarization and meeting-assistant ideas. We therefore do not claim that every other assistant lacks local processing or source links. Our engineering task is to connect these components and preserve traceability. Our evaluation task is to separate discussion retrieval from speech errors and final decisions. Independent labels for the complete recording workflow, slide links and influence remain missing. This is our bounded project contribution and the next research need.

**Transition:** The full architecture shows how these parts connect.

### 8. Description of the Proposed Solution

**Amitkumar Racha • 04:55–06:25 • 90 seconds**

Read this diagram from left to right. First the browser supplies audio and optional slides; the local API validates inputs and queues one analysis job. Second, speech recognition supplies words and times, while speaker clustering supplies speaker intervals. Cached words are combined with the final speaker intervals. Optional slides are extracted and matched to passages. Third, the learned English discussion branch produces review suggestions. The separate event, evidence, decision and interaction branch supports other candidate outputs and exploratory influence scores. Finally, reports and local persistence feed the review interface. Human edits return to the saved application report. These are data dependencies, not a claim that the modules run simultaneously.

**Point / demonstration:** Use three sweeps: capture/preparation; speech and slides; analysis and saved review. Do not read all boxes. A separate editable architecture deck and vector diagram are supplied for close inspection.

**Transition:** These processing and review stages define the requirements.

**Evidence / limit:** Verified against backend/api.py, src/pipeline/orchestrator.py, src/audio/asr.py, src/meeting/discussions.py and report/export modules. The learned discussion stage does not create final-decision anchors or feed the influence score.

### 9. Requirement Analysis

**Sahil Awatramani • 06:25–07:10 • 45 seconds**

The user must be able to supply audio, optionally attach slides, inspect source passages, correct speaker names and export a report. Operationally, the local models must already be provisioned, processing stages must be visible and the worker must queue analysis. Job state and report artifacts support recovery where available. An optional model failure receives an explicit status. Renaming a speaker changes the displayed identity; repairing a wrong acoustic cluster requires diarization and attribution to run again, reusing unchanged word observations.

**Transition:** The technology stack maps these requirements to concrete components.

### 10. Technology Stack

**Sahil Awatramani • 07:10–08:00 • 50 seconds**

The browser interface uses React, while FastAPI and Python coordinate the local workflow. FFmpeg normalizes the audio; faster-whisper recognizes words; Sherpa-ONNX supplies speaker segmentation and clustering. Presentation parsing extracts native text, tables and notes, and text similarity can propose slide links. The supervised English detector uses train-fitted lexical features and conventional classifiers. SQLite and local artifacts retain reports and job state. We do not fine-tune a speech or embedding foundation model. We do train small classifiers for the discussion task.

**Transition:** Here is the design of that trained NLP component.

### 11. Design: Discussion Detector

**Sahil Awatramani • 08:00–09:10 • 70 seconds**

The research unit is a dialogue act: a short manually delimited utterance. An act is positive when at least half its lexical word identifiers fall inside an annotated decision-discussion span. We convert words and character patterns into numerical features, and add context from up to forty acts on each side without crossing meeting boundaries. A random forest and logistic classifier each produce a score. The selected combination is seventy-five percent forest and twenty-five percent logistic, followed by smoothing and a fixed threshold. Labels and outcome categories are not input features. Future context makes this an offline detector. The speech models are pretrained, while these small classifiers are trained on our training partition.

**Transition:** The implementation also needs a careful separation of data.

### 12. Development / Implementation

**Sahil Awatramani • 09:10–10:10 • 60 seconds**

We have forty-seven AMI meetings with manual discussion spans. The custom split uses twenty-nine training meetings, six development meetings and twelve historical meetings. All meetings in a project series stay together. We compare four classifier families with local or wider-context features and select each configuration on development F1. However, the historical cohort has been examined across successive rounds and has only three independent project series. We therefore label the results exploratory. Human transcripts and act boundaries are used here, so this is not the accuracy of the complete audio application.

**Transition:** Here are the actual discussion results under that protocol.

### 13. Testing & Debugging

**Shriyans Sahoo • 10:10–10:55 • 45 seconds**

The recorded regression passed five hundred and ninety-seven software tests. Those checks cover things such as preserved source identifiers, batch scoring, meeting boundaries, exports and optional-stage failures. They do not mean five hundred and ninety-seven correctly understood meetings. We also retained changes that did not work: semantic and continuity variants failed the development gate, while calibration and refit results did not justify replacing the installed model. A two-excerpt speaker-calibration pilot reduced diarization error, but that is another small, separately scoped task.

**Transition:** Now let us examine the measured discussion results.

**Evidence / limit:** Regression log: professor_guidelines/evaluation/quality_scorecard/regression_tests.log. No new model training or application regression run is implied by building this deck.

### 14. Project Outcome: Discussion Detection

**Shriyans Sahoo • 10:55–12:15 • 80 seconds**

The chart compares the context versions on identical reference acts. The combined detector has a fifty-three point five-four percent F1 score, versus fifty-two point zero-eight for the matched forest. The gain is one point four-six percentage points. Precision is only thirty-nine point nine-four percent: roughly forty of every hundred flagged acts match the reference positives. Recall is eighty-one point one-eight percent, so we find many reference discussion acts but also flag many negatives. The descriptive uncertainty interval crosses zero, and some other classifiers have higher average precision. This is an exploratory task-level result, not a statistically established win or complete-project accuracy.

**Transition:** Recognition quality also depends on the language and cohort.

**Evidence / limit:** Exact P/R/F1/AP and confusion counts are retained in the research report. Do not call 53.54% overall accuracy.

### 15. Project Outcome: Speech and Speakers

**Shriyans Sahoo • 12:15–13:20 • 65 seconds**

Shriyans here. Word error rate counts substitutions, deletions and insertions against reference words; lower is better. On eight fixed Hindi samples, Turbo lowers word error from fifty point nine-six to twenty-eight point eight-five percent. Hinglish improves from sixty-six point one-three to fifty-seven point two-six percent. But historical English becomes worse, from sixty-one point six-one to sixty-three point nine-one percent. The shared default remains small, while Turbo is available explicitly. These are tiny speech pilots, not broad multilingual meeting validation. The same unchanged samples and strict normalization were used. In the custom two-excerpt speaker pilot, diarization error fell from 64.08 to 40.91 percent after development-selected calibration. All four development and historical audio meetings are from the referenced official training partition. Segment-reference and coverage limits apply; this is not an official full-corpus benchmark.

**Transition:** The conclusion brings the working system and remaining validation needs together.

### 16. Conclusion

**Shriyans Sahoo • 13:20–13:50 • 30 seconds**

To conclude, InfluenceIQ integrates local processing with source-linked discussion review. We have a working application, a matched classifier study and transparent component results. The current discussion score is fifty-three point five-four percent F1 on oracle inputs, and the next priority is independent recording-level evaluation. Final-decision accuracy, slide-link accuracy and human influence rankings remain unmeasured. The next priority is to freeze the pipeline and annotate fresh recordings independently. Thank you.

### 17. References

**Shriyans Sahoo • 13:50–14:00 • 10 seconds**

These are the main sources supporting our meeting-assistant context, speech and speaker components, and dataset discussion. The complete fifteen-entry bibliography is included in our IEEE paper and this slide’s notes. Thank you; we welcome your questions.

**Evidence / limit:** [1] G. Tur et al., “The CALO meeting assistant system,” IEEE Trans. Audio, Speech, Lang. Process., vol. 18, no. 6, pp. 1601–1611, Aug. 2010, doi: 10.1109/TASL.2009.2038810.
[2] A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, “Robust speech recognition via large-scale weak supervision,” in Proc. Int. Conf. Mach. Learn., vol. 202, 2023, pp. 28492–28518. [Online]. Available: https://proceedings.mlr.press/v202/radford23a.html
[3] M. Bain, J. Huh, T. Han, and A. Zisserman, “WhisperX: Time-accurate speech transcription of long-form audio,” in Proc. Interspeech, 2023, pp. 4489–4493, doi: 10.21437/Interspeech.2023-78.
[4] H. Bredin, “pyannote.audio 2.1 speaker diarization pipeline: Principle, benchmark, and recipe,” in Proc. Interspeech, 2023, pp. 1983–1987, doi: 10.21437/Interspeech.2023-105.
[5] A. Plaquet and H. Bredin, “Powerset multi-class cross entropy loss for neural speaker diarization,” in Proc. Interspeech, 2023, pp. 3222–3226, doi: 10.21437/Interspeech.2023-205.
[6] D. Macháček, R. Dabre, and O. Bojar, “Turning Whisper into real-time transcription system,” in Proc. IJCNLP–AACL: Syst. Demonstrations, 2023, pp. 17–24, doi: 10.18653/v1/2023.ijcnlp-demo.3.
[7] S. Baghel et al., “The DISPLACE challenge 2023,” in Proc. Interspeech, 2023, pp. 3562–3566, doi: 10.21437/Interspeech.2023-2367.
[8] S. B. Kalluri et al., “The second DISPLACE challenge: DIarization of SPeaker and LAnguage in Conversational Environments,” in Proc. Interspeech, 2024, pp. 1630–1634, doi: 10.21437/Interspeech.2024-1833.
[9] K. Bhogale et al., “Vistaar: Diverse benchmarks and training sets for Indian language ASR,” in Proc. Interspeech, 2023, pp. 4384–4388, doi: 10.21437/Interspeech.2023-2589.
[10] Y. Hu, T. Ganter, H. Deilamsalehy, F. Dernoncourt, H. Foroosh, and F. Liu, “MeetingBank: A benchmark dataset for meeting summarization,” in Proc. ACL, vol. 1, 2023, pp. 16409–16423, doi: 10.18653/v1/2023.acl-long.906.
[11] H. Kim, M. Cho, and S.-H. Na, “ExplainMeetSum: A dataset for explainable meeting summarization aligned with human intent,” in Proc. ACL, vol. 1, 2023, pp. 13079–13098, doi: 10.18653/v1/2023.acl-long.731.
[12] J. Carletta et al., “The AMI meeting corpus: A pre-announcement,” in Machine Learning for Multimodal Interaction, Lecture Notes in Computer Science, vol. 3869. Berlin, Germany: Springer, 2006, pp. 28–39, doi: 10.1007/11677482_3.
[13] A. Conneau et al., “FLEURS: Few-shot learning evaluation of universal representations of speech,” arXiv:2205.12446, 2022, doi: 10.48550/arXiv.2205.12446.
[14] A. Diwan et al., “MUCS 2021: Multilingual and code-switching ASR challenges for low resource Indian languages,” in Proc. Interspeech, 2021, pp. 2446–2450, doi: 10.21437/Interspeech.2021-1339.
[15] OpenAI, “Whisper large-v3-turbo,” model card. Accessed: Oct. 19, 2026. [Online]. Available: https://huggingface.co/openai/whisper-large-v3-turbo

### 18. Photograph of the Presentation

**Shriyans Sahoo • 14:00–14:00 • 0 seconds**

This slide retains the heading required by the original presentation. Add an actual photograph after the presentation if the department requires a photographic record. It is not part of the spoken fifteen-minute script.

**Point / demonstration:** For questions, return to slide 16 (Conclusion), slide 8 (architecture) or slide 14 (discussion results).

## Likely viva questions

**Is this training-free?** Speech and embedding models are pretrained/frozen. Small supervised discussion classifiers are trained on the training acts.

**Why not call the result superior?** Historical F1 improves by 1.46 points over the matched forest, but the three-series descriptive interval crosses zero and AP is worse than some baselines.

**Why is accuracy below an always-negative baseline?** The data is imbalanced. Predicting negative everywhere gives 77.72% accuracy but finds no discussion. Report positive F1, recall and balanced accuracy.

**Can it understand Hindi decisions?** Hindi/Hinglish speech recognition has small pilots. The learned discussion model is English-only; final-decision accuracy is unmeasured.

**Why use both forest and logistic regression?** This particular mixture was selected on development F1. We do not claim the model combination is inherently or universally better.

**What does ±40 mean?** Up to forty dialogue acts before and after, clipped to a meeting. Future context makes the detector offline.

**What happens when a speaker name is wrong?** Rename the displayed identity. If the acoustic grouping is wrong, rerun speaker separation; unchanged word observations can be reused.

**Does influence measure real decision power?** No independent human ranking exists. The audited case equals scaled decision counting; no causal or validated influence claim is supported.

**What is the novelty?** A bounded integration and comparative study: local review with source traceability, cached recognition/attribution separation, and explicit model/metric boundaries. There is no new foundation model or proven novelty over every prior system.

**Are the interface examples real model results?** The screenshots show the real application with isolated synthetic validation data. They demonstrate UI functionality only.


## Presentation-day checklist

- Open the final PPTX and PDF fallback locally; verify fonts and the projector’s 16:9 display.
- Practise at least once with all four members; stop the spoken part by 14:00 and keep the last minute as buffer.
- If demonstrating, prepare a completed English recording and test the sound output. Avoid new inference or model downloads on stage.
- Use Presenter View for notes; on a single screen keep this guide on a separate device.
- Keep the architecture SVG/PDF ready for detailed examiner questions.
- The rough deck’s “photograph of presentation” is a post-event record. Add a real photograph after the event if required; no photograph or implementation dates have been fabricated.
- Team contacts are retained in the cover notes and the contact list below; speaking assignments do not imply implementation ownership.

## Team contacts

Anushka Chatterjee — anushkac2311@gmail.com

Amitkumar Racha — rachaamitkumar@gmail.com

Sahil Awatramani — sahilawatramani@gmail.com

Shriyans Sahoo — shriyanssahoo2005@gmail.com

Faculty guide: Dr. Nivedita Mishra — nivedita.mishra@sitpune.edu.in
