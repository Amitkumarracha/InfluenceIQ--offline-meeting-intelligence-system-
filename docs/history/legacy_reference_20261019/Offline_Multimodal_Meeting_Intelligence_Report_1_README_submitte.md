# Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis

> **Source:** Multimodal AI Project Report, Group 12, Symbiosis Institute of Technology, Department of Artificial Intelligence & Machine Learning, AY 2026–27.  
> **Important:** This README is a structured, LLM-friendly representation of the submitted report. The report describes a **proposed/intended system and evaluation plan**; it does not present final experimental results or a completed implementation.

---

## 1. Project Identity

| Field | Details |
|---|---|
| Project title | **Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis** |
| Course / domain | Multimodal AI |
| Degree | Bachelor of Technology in Artificial Intelligence & Machine Learning |
| Institution | Symbiosis Institute of Technology, Pune |
| Academic year | 2026–27 |
| Group | Group 12 |
| Project guide | Dr. Nivedita Mishra |
| HOD listed in report | Dr. Sumit Kumar |
| Report date | 30/08/2026 |
| Primary modalities | Meeting audio + PPT presentation |
| Core focus | Speaker attribution, audio–PPT alignment, meeting-event/evidence extraction, decision reconstruction, participant contribution/influence analysis |
| Deployment philosophy | Offline / privacy-protecting / intended to work on local computing resources, including laptops |

### Team

- Anushka Chatterjee — 23070126015
- Amitkumar Racha — 24070126501
- Sahil Awatramani — 23070126112
- Shriyans Sahoo — 23070126125

---

## 2. One-Paragraph Project Explanation

The project proposes an **offline multimodal meeting-intelligence framework** that jointly analyzes a long-duration meeting recording and its corresponding PPT presentation. Instead of producing only a transcript or generic summary, the system is intended to determine **who said what, when it was said, which slide/evidence was being discussed, what proposals/objections/evidence/corrections/decisions/actions occurred, how decisions evolved, and how participants contributed to those decisions**. Participant influence is intended to be estimated from decision-relevant contributions—such as proposals, evidence, objections, interactions, and impact on decisions—rather than from speaking time alone.

---

## 3. Core Problem

### Existing problem

Meeting information exists in multiple modalities:

1. **Spoken discourse / audio**
2. **Presentation slides / PPT**

The report argues that conventional meeting-analysis tools mainly focus on:

- transcription,
- generic summarization,
- content extraction.

They generally do not provide an explicit connection between:

- spoken statements,
- speakers,
- timestamps,
- presentation content,
- evidence,
- proposals,
- objections,
- decisions,
- action items,
- decision lineage,
- participant influence.

### Why manual analysis is difficult

A one- or two-hour meeting plus its PPT can be labor-intensive to review. Critical information may be distributed across the meeting, including:

- proposals,
- oppositions/objections,
- evidence,
- corrections,
- decisions,
- action items.

A major problem identified by the report is that **speaking time is not equivalent to decision influence**. A participant who speaks briefly may provide crucial evidence or a suggestion that changes the final decision.

### Proposed solution

Build an **offline multimodal meeting intelligence system** that:

- processes long meeting audio,
- identifies speakers,
- transcribes speech,
- processes PPT content,
- aligns speech with relevant slides,
- extracts important meeting events,
- links claims with evidence,
- reconstructs decision lineage,
- analyzes participant interactions,
- estimates participant influence with supporting evidence.

---

# 4. Project Goals / Objectives

The report defines six main objectives:

### Objective 1 — Speaker-attributed transcription
Construct a pipeline for long-duration meeting audio that determines speakers and produces a speaker-attributed transcript.

### Objective 2 — PPT understanding
Capture and represent textual and visual information from PPT slides.

### Objective 3 — Cross-modal alignment
Link discussion fragments to the presentation information relevant to that discussion.

### Objective 4 — Meeting-event identification
Identify events including:

- suggestions,
- objections,
- evidence,
- corrections,
- decisions,
- tasks.

### Objective 5 — Inconsistency detection
Detect possible inconsistencies between:

- claims made during discussion, and
- information shown in the PPT,

and provide evidence supporting the observation.

### Objective 6 — Participant influence analysis
Estimate participant contribution/influence using:

- contributions,
- interactions,
- evidence,
- decision-making impact,

and provide an explanation for the analysis.

---

# 5. Why This Is a Multimodal AI Problem

The project does not treat the meeting as text alone.

## Audio modality

Used to obtain:

- speech,
- speaker identity/attribution,
- timestamps,
- conversational content.

## PPT modality

Used to obtain:

- text,
- headings,
- tables,
- numerical values,
- visual information,
- figures and other slide-level information.

## Fusion

The two modalities are combined using:

- **temporal alignment**
- **semantic similarity**

The desired integrated representation contains:

`Speaker + Statement + Timestamp + Corresponding Slide`

This lets the system reason about what was said and what presentation evidence was relevant at the same time.

---

# 6. High-Level End-to-End Pipeline

```text
MEETING AUDIO (1–2+ hours)
        |
        v
1. Pre-processing
   - resampling
   - normalization
   - VAD
        |
        v
2. Speaker Diarization
   - identify participants
   - create speaker segments
        |
        v
3. Offline ASR
   - speech -> text
        |
        v
4. Speaker-attributed Transcript
   Timestamp -> Speaker -> Statement


PPT PRESENTATION
        |
        v
5. PPT Processing
   - extract headings
   - extract tables
   - extract numbers
   - extract visual information
        |
        v
   Structured Slide Representation


Speaker-attributed Transcript + Structured Slides
                    |
                    v
6. Audio–PPT Alignment
   - temporal matching
   - semantic matching
                    |
                    v
     Speaker–Speaker / Statement–Slide Associations
                    |
                    v
7. Meeting Event + Evidence Extraction
   - proposals
   - objections
   - evidence
   - corrections
   - agreements
   - decisions
   - action items
                    |
                    v
8. Decision Reconstruction
   Proposal -> Evidence/Objection -> Revision -> Final Decision
                    |
                    +----------------------+
                    |                      |
                    v                      v
9. Participant Interaction         10. Participant Influence
   Analysis                           Estimation
   - responses                       - participation
   - support                         - proposal contribution
   - objections                      - evidence contribution
   - interaction graph               - objection contribution
                                      - decision contribution
                                      - interaction contribution
                    |                      |
                    +----------+-----------+
                               v
              Explainable Meeting Report
```

The report's Figure 3.1 on page 18 presents essentially this modular flow. It begins with meeting audio and PPT presentation as parallel inputs and progresses through preprocessing, diarization, ASR, PPT processing, audio–PPT alignment, event/evidence extraction, decision reconstruction, interaction analysis, influence estimation, and final report generation.

---

# 7. Detailed System Architecture

## Architecture Layers

The report's Table 3.1 defines nine main architecture steps.

| Layer | Proposed approach | Expected output |
|---|---|---|
| 1. Audio Input & Pre-processing | Accept long-duration meeting recordings; resampling, normalization and Voice Activity Detection (VAD). Lightweight noise reduction may be applied when required. | Clean, speech-focused audio segments |
| 2. Speaker Identification | Apply speaker diarization and speaker embeddings to separate participants and maintain consistent speaker identities. | Timestamped speaker segments |
| 3. Speech Recognition | Transcribe the complete meeting using an offline-capable ASR model while retaining timestamps and speaker IDs. | Speaker-attributed transcript |
| 4. PPT Understanding | Extract headings, tables, numerical values and relevant visual information; generate slide-level representations. | Structured PPT representation |
| 5. Audio–PPT Fusion | Match speech segments with relevant slides using temporal and semantic similarity. | Speaker–speaker/slide associations as described in the report |
| 6. Meeting Event Analysis | Identify proposals, questions, objections, evidence, corrections, agreements, decisions and action items. | Structured meeting events |
| 7. Evidence & Decision Analysis | Associate claims and evidence with slides; reconstruct proposals and their discussion toward final decisions. | Evidence-linked decision chains |
| 8. Interaction Analysis | Model responses, support, objections and influence between participants to determine how individual contributions affect discussion and decisions. | Participant interaction graph |
| 9. Influence Estimation & Report Generation | Calculate an explainable influence score using decision-relevant contribution signals rather than speaking duration alone. | Influence ranking + explainable meeting report |

> **Source fidelity note:** The report does not prescribe a final software stack or a specific model name for each architecture layer. Those implementation choices therefore remain unspecified in this README.

---

# 8. Processing and Integration

## 8.1 Long Audio Processing

Long meeting recordings are processed in smaller parts.

Purpose:

- improve processing efficiency,
- support recordings lasting around one or two hours,
- avoid keeping the entire audio recording in memory.

The report explicitly frames long-duration processing as an offline/local-computation requirement.

---

## 8.2 Speaker-Aware Transcription

ASR output and speaker-diarization results are combined into a transcript in the form:

```text
Timestamp -> Speaker -> Statement
```

Example schema:

```json
{
  "timestamp": "00:12:45",
  "speaker": "Speaker_03",
  "statement": "We should revise the budget allocation."
}
```

> The JSON example above is only a representation of the report's stated transcript structure; it is not an implementation example from the report.

This speaker-aware transcript is used as the main input for subsequent multimodal analysis.

---

## 8.3 PPT Representation

Each slide is converted into a structured representation containing the information available from the slide, including:

- text,
- headings,
- tables,
- numbers,
- visual information.

Purpose:

- represent the slide in machine-processable form,
- support matching between slide content and meeting discussion.

Conceptually:

```text
Slide ID
  ├── title / heading
  ├── textual content
  ├── tables
  ├── numbers
  └── visual information
```

---

## 8.4 Multimodal Fusion

The transcript and PPT representations are merged using:

1. **Temporal alignment**
2. **Semantic alignment**

The intended unified representation is approximately:

```text
{
  speaker,
  statement,
  timestamp,
  corresponding_slide
}
```

This allows later reasoning to connect:

- a speaker,
- a statement,
- a time,
- a relevant slide/evidence source.

---

# 9. Meeting Event Extraction

The report identifies the following meeting events as important:

| Event type | Meaning in the proposed system |
|---|---|
| Proposal | An idea/proposal introduced for discussion |
| Question | A question raised during discussion |
| Objection | A challenge, disagreement or issue identified |
| Evidence | Facts/information introduced to support discussion |
| Correction | A correction or revision to prior information/claims |
| Agreement | Support or acceptance of a point |
| Decision | A decision reached in the meeting |
| Action item | A task resulting from the meeting |

The report also describes evidence-linked decision analysis and decision reconstruction.

---

# 10. Evidence and Claim Analysis

A key goal is to connect statements with supporting information.

The proposed system should:

1. detect claims in discussion,
2. identify evidence in the relevant PPT content,
3. associate the claim with the evidence,
4. detect possible inconsistency between spoken claims and slide content,
5. retain evidence for explanation.

Conceptual representation:

```text
Speaker Statement
      |
      v
Claim / Event
      |
      +----> Relevant Slide
      |
      +----> Evidence
      |
      v
Decision-related reasoning
```

---

# 11. Decision Reconstruction / Decision Lineage

The report emphasizes not merely identifying the final decision, but understanding **how the decision was formed**.

The intended chain is:

```text
Proposal
   ↓
Evidence / Supporting Information
   ↓
Objection / Challenge / Discussion
   ↓
Revision
   ↓
Final Decision
```

The research-gap section summarizes the overall target pipeline as:

```text
Speaker Attribution
        →
Audio-PPT Alignment
        →
Event/Evidence Extraction
        →
Decision Reconstruction
        →
Participant Contribution
        →
Decision Influence
```

Decision lineage is expected to connect proposals, evidence, discussion and final decisions.

---

# 12. Participant Interaction Analysis

The interaction analysis component models how participants affect one another through:

- responses,
- support,
- objections,
- discussion interactions.

Its expected output is a **participant interaction graph**.

Conceptually:

```text
Participant A
   | support / objection / response
   v
Participant B
   |
   +--> Proposal
   +--> Evidence
   +--> Challenge
   +--> Decision impact
```

The report positions interaction as one signal for understanding contribution and influence.

---

# 13. Participant Influence Estimation

## Core principle

The project explicitly avoids treating **speaking duration as the sole measure of influence**.

Instead, influence is intended to combine multiple contribution signals.

### Influence signals defined in the report

1. **Participation**
   - speaking turns
   - relevant participation

2. **Contribution to proposal**
   - ideas or proposals introduced

3. **Contribution to evidence**
   - facts or information introduced

4. **Contribution to objection/challenge**
   - issues identified
   - challenges raised

5. **Contribution to decision**
   - contributions that lead to change
   - impact on the decision

6. **Contribution to interaction**
   - reactions, support or opposition generated by the contribution

### Explainability requirement

Influence scores should include the evidence used for scoring.

Conceptually:

```text
Participant
    |
    +--> Participation
    +--> Proposals
    +--> Evidence
    +--> Objections
    +--> Decision impact
    +--> Interaction effect
              |
              v
       Influence Score
              |
              v
      Evidence / Explanation
```

> The report does **not** provide a final mathematical formula or numerical weighting for these signals. Do not invent a formula and claim that it comes from the report.

---

# 14. Final System Output

The report specifies that the final structured meeting report should contain:

1. **Meeting summary**
2. **Speaker-wise participation**
3. **Key discussion points**
4. **PPT-linked statements**
5. **Proposals, objections and evidence**
6. **Identified decisions and decision lineage**
7. **Action items**
8. **Participant influence ranking with supporting evidence**

This is intended to be an **explainable** output rather than a black-box score.

---

# 15. Evaluation Plan

The framework is intended to be evaluated at both:

- individual pipeline stages, and
- overall meeting-analysis level.

The goal is to identify whether errors arise from:

- speech recognition,
- speaker identification,
- multimodal alignment,
- event extraction,
- decision extraction,
- influence analysis,
- processing efficiency.

## Evaluation metrics

| Component | Metric | Purpose |
|---|---|---|
| Speech Recognition | Word Error Rate (WER) | Transcription accuracy |
| Speaker Diarization | Diarization Error Rate (DER) | Speaker segmentation/attribution accuracy |
| PPT Alignment | Precision, Recall, F1-score, Alignment Accuracy | Whether speech segments are matched with correct slides |
| Event Extraction | Precision, Recall, F1-score | Detection of proposals, objections, evidence and decisions |
| Decision Extraction | Precision, Recall, F1-score | Identification of final decisions |
| Decision Lineage | Chain/relationship accuracy | Correctly connecting proposals, evidence, discussion and decisions |
| Influence Analysis | Correlation with human ratings; Rank correlation | Agreement between system influence estimates and human judgments |
| Processing Efficiency | Processing time, Real-Time Factor (RTF), memory usage | Feasibility for long-duration offline processing |

---

# 16. Baseline Strategy

The report proposes progressively stronger baselines.

| Baseline | Description | Purpose |
|---|---|---|
| **B1: Transcript-only** | Uses ASR transcript without PPT information | Establish transcript-only performance |
| **B2: Speaker + Transcript** | Adds speaker attribution to the transcript | Measure value of speaker information |
| **B3: Audio + PPT without Decision Analysis** | Uses meeting audio and PPT but does not model decision lineage | Measure contribution of multimodal inputs |
| **B4: Audio + PPT + Decision Analysis** | Includes multimodal alignment and decision reconstruction | Measure effectiveness of the proposed decision pipeline |
| **Proposed System** | Adds evidence-grounded participant influence analysis | Evaluate the complete framework |

---

# 17. Ablation Study

The report proposes removing major components one at a time and comparing them with the complete system.

Components mentioned for ablation include:

- PPT data,
- cross-modal alignment,
- evidence reasoning,
- interaction modeling,
- influence-on-decision modeling.

Purpose:

```text
Full System
   |
   +-- remove PPT
   +-- remove cross-modal alignment
   +-- remove evidence reasoning
   +-- remove interaction modeling
   +-- remove influence-on-decision component
   |
   v
Compare performance against complete system
```

This is intended to determine how much each multimodal/decision-analysis component contributes to overall performance.

---

# 18. Human Evaluation

The report states that influence cannot be directly verified as a simple objective ground truth, making human evaluation particularly important.

Proposed process:

1. Select meeting video clips.
2. Have human raters independently evaluate participants' influence on decision making.
3. Compare human ratings with system-generated influence estimates.

The report uses this to evaluate whether the influence measure is meaningful beyond simply claiming that the output appears reasonable.

---

# 19. Project Timeline

The report proposes a 12-week phased development plan.

| Week(s) | Phase | Key activities | Deliverable |
|---|---|---|---|
| 1–2 | Literature review & problem | Finalize literature review, research gap, problem statement, objectives and evaluation criteria | Finalized problem definition and literature review |
| 3 | Requirement analysis & architecture design | Finalize revised multimodal architecture and select tools/models | System architecture and tool-selection plan |
| 4–5 | Audio Processing & Speaker Attribution | Implement audio preprocessing, speaker diarization and speaker-attributed ASR on sample meeting recordings | Working diarization and transcription pipeline |
| 6 | PPT Processing | Extract slide text, headings, tables, numerical information and relevant visual features | Structured PPT representation |
| 7 | Audio–PPT Alignment | Develop temporal and semantic alignment between transcript segments and relevant PPT slides | Aligned audio–PPT representation |
| 8 | Event & Evidence Extraction | Identify proposals, objections, evidence, corrections, agreements and decisions and associate relevant evidence | Structured meeting-event representation |
| 9 | Decision Lineage & Interaction Analysis | Construct decision chains and participant interaction graph | Decision lineage and interaction graph |
| 10 | Participant Influence Model | Develop explainable influence scoring using participation, evidence, interaction and decision impact | Influence-analysis module and baseline implementation |
| 11 | Evaluation & Integration | Conduct component-level and end-to-end evaluation, ablation, human evaluation and integrate complete pipeline | Evaluation results and integrated prototype |
| 12 | Documentation & Final Presentation | Analyze results, finalize report, prepare project presentation | Final report, prototype and presentation |

---

# 20. Research Background

The literature review covers several related research directions:

- speech enhancement,
- multi-speaker speech recognition,
- speaker diarization,
- multimodal meeting processing,
- participant dominance/influence analysis,
- speech-to-slide alignment,
- automatic meeting summarization,
- meeting/event and argument extraction.

The report notes that these capabilities have largely been studied separately, motivating an integrated audio + PPT approach.

---

# 21. Literature Review Summary

The report reviews 28 sources. The major themes and representative contributions are summarized below.

| Ref. | Research direction | Main relevance identified by report |
|---|---|---|
| [1] | Speech enhancement | High-efficiency low-latency speech enhancement; groundwork for audio quality processing |
| [2] | Speech enhancement | Deep multi-frame filtering for robust speech preprocessing |
| [5] | Robust ASR | Robust recognition under noise and long-duration constraints |
| [6], [7], [8], [11] | Multi-talker / streaming ASR | Recognition in multi-speaker / overlapping environments and speaker-attributed ASR |
| [9], [10] | Speech separation | Continuous speech separation and efficient separation models |
| [12], [13], [14] | Speaker identification/diarization | Speaker spotting, neural diarization and overlap-aware diarization |
| [15] | Overlap detection | Detection of overlapping speech and speaker count |
| [16], [17], [18], [19], [20], [21] | Multimodal/audio-visual diarization | Combining audio/visual cues for speaker attribution |
| [22] | AMI meeting corpus | Multimodal meeting dataset with synchronized audio and presentation content |
| [23] | Participant dominance | Estimation of dominance using speaker-level meeting information |
| [24] | Influence modeling | Functional roles and participant influence |
| [25] | Roles & social network analysis | Role recognition using lexical and interaction information |
| [26] | Speech-to-slide alignment | Video-to-slide alignment using speech, OCR and visual features |
| [27] | Meeting summarization / argument structure | Automatic minuting and argument-structure construction |
| [28] | Meeting summarization / translation | Multi-person speech processing, minutes, summarization and translation |

### Literature conclusion

The report's central observation is:

> Existing capabilities provide many of the building blocks, but an integrated pipeline connecting speaker attribution, audio–PPT alignment, evidence extraction, decision reconstruction and participant influence is the targeted research contribution.

---

# 22. Research Gap

The report identifies the following gap:

### What exists separately

- speech enhancement,
- speaker diarization,
- meeting summarization,
- participant dominance/influence analysis,
- speech-to-slide alignment.

### What the report says is missing

A unified system that combines:

```text
Long-duration meeting audio
           +
Corresponding PPT slides
           +
Speaker involvement
           +
Discussion evidence
           +
Decision reconstruction
           +
Participant contribution/influence
```

### Key conceptual gap

**Conversation dominance is not necessarily decision influence.**

A person may talk frequently without making a decision-changing contribution, while another participant may speak briefly but introduce decisive evidence or a critical objection.

The proposed work therefore centers influence around **decision-relevant contributions**.

---

# 23. Privacy and Offline Design

The report describes the system as:

- **offline**
- **privacy-protecting**
- based on **local computation resources**
- intended to be feasible on **laptop computers**

The motivation is to analyze meeting recordings and presentations without requiring the meeting data to be sent to an external cloud-based service.

> The report does not specify a final deployment platform, exact model list, or production security architecture. Those should be treated as future implementation decisions rather than facts from the report.

---

# 24. Intended Inputs

## Input A — Meeting Audio

Expected characteristics:

- long-duration recording,
- potentially one to two hours or more,
- multi-speaker conversation,
- possible overlapping speech/noise.

Processing begins with audio preprocessing and is followed by speaker diarization and ASR.

## Input B — PPT Presentation

The corresponding presentation is processed to extract:

- headings,
- text,
- tables,
- numerical information,
- visual information.

The PPT becomes a structured slide-level representation for cross-modal alignment.

---

# 25. Intended Intermediate Representations

### 25.1 Audio segment

```text
AudioSegment
- start_time
- end_time
- audio_content
```

### 25.2 Speaker segment

```text
SpeakerSegment
- start_time
- end_time
- speaker_id
```

### 25.3 Speaker-attributed transcript unit

```text
TranscriptUnit
- timestamp
- speaker_id
- statement
```

### 25.4 Slide representation

```text
Slide
- slide_id
- heading/text
- tables
- numerical values
- visual information
```

### 25.5 Multimodal unit

```text
MultimodalUnit
- timestamp
- speaker_id
- statement
- slide_id
- semantic/temporal association
```

These schemas are conceptual abstractions derived from the report's stated processing flow; the report does not define a formal database schema.

---

# 26. Desired Explainability

The intended system should not output only:

```text
Participant A -> Influence = 0.82
```

Instead, the report expects supporting evidence, such as conceptually:

```text
Participant A
- introduced proposal
- provided supporting evidence
- raised/answered an objection
- contribution was connected to a later decision
- generated interaction/support from other participants
```

The exact scoring formula and weights are **not provided in the report**.

---

# 27. End-to-End Data Flow for an LLM

An LLM or developer implementing the project should interpret the pipeline as:

```text
INPUT
├── Meeting audio
└── Corresponding PPT

AUDIO PIPELINE
├── Resampling
├── Normalization
├── VAD
├── Speaker diarization
├── Speaker embeddings / identity consistency
└── Offline ASR
       ↓
Speaker-attributed timestamped transcript

PPT PIPELINE
├── Text extraction
├── Heading extraction
├── Table extraction
├── Numerical information extraction
└── Visual information representation
       ↓
Structured slide representation

FUSION
├── Temporal alignment
└── Semantic alignment
       ↓
Speaker + statement + timestamp + slide

MEETING ANALYSIS
├── Proposal extraction
├── Question extraction
├── Objection/challenge extraction
├── Evidence extraction
├── Correction extraction
├── Agreement extraction
├── Decision extraction
└── Action-item extraction

DECISION REASONING
├── Claim ↔ evidence links
├── Proposal ↔ objection links
├── Revision tracking
└── Final decision lineage

INTERACTION
├── Responses
├── Support
├── Objections
└── Participant interaction graph

INFLUENCE
├── Participation
├── Proposal contribution
├── Evidence contribution
├── Objection contribution
├── Decision contribution
└── Interaction contribution

OUTPUT
├── Meeting summary
├── Speaker-wise participation
├── Key discussion points
├── PPT-linked statements
├── Proposals / objections / evidence
├── Decision lineage
├── Action items
└── Evidence-backed participant influence ranking
```

---

# 28. What Makes the Proposed System Different

According to the report, the intended novelty is not simply transcription or summarization.

The system aims to jointly connect:

```text
WHO?
  ↓
Speaker Attribution

WHAT?
  ↓
ASR / Statement Extraction

WHEN?
  ↓
Timestamps

WHAT SLIDE / EVIDENCE?
  ↓
Audio–PPT Alignment

WHAT HAPPENED?
  ↓
Event & Evidence Extraction

HOW DID THE DECISION FORM?
  ↓
Decision Reconstruction / Lineage

WHO CONTRIBUTED TO THAT CHANGE?
  ↓
Interaction + Contribution Analysis

WHO INFLUENCED THE DECISION AND WHY?
  ↓
Explainable Influence Estimation
```

---

# 29. What the Report Does NOT Specify

To avoid hallucination during implementation, an LLM should **not assume** that the submitted report already finalized:

- a specific ASR model,
- a specific speaker-diarization model,
- a specific embedding model,
- a specific OCR library,
- a specific PPT-processing library,
- a specific semantic-embedding model,
- a specific vector database,
- a specific programming language,
- a specific UI,
- a specific API framework,
- a fixed influence-score equation,
- fixed weights for contribution signals,
- a finalized dataset split,
- final benchmark scores,
- final deployment hardware,
- production security/authentication design.

These are not specified as final implementation details in the report.

---

# 30. Status of the Work According to the Report

The report is written primarily as a **proposed/intended framework and research plan**.

Evidence from the report includes terms such as:

- “suggested system”
- “planned research”
- “proposed approach”
- “expected output”
- “intended system”
- “will be assessed”
- “will be performed”

Therefore:

### Treat as confirmed from report
- problem definition,
- motivation,
- objectives,
- research gap,
- proposed architecture,
- proposed processing stages,
- proposed influence signals,
- proposed evaluation plan,
- proposed baselines,
- proposed ablation study,
- proposed human evaluation,
- 12-week project timeline.

### Do not treat as already experimentally proven
- final accuracy,
- final influence correlation,
- final runtime,
- final memory consumption,
- final model performance,
- final deployment performance.

The report's conclusion specifically frames the architecture as intended to be feasible for offline laptop processing and says evaluation would measure the relevant components against baselines.

---

# 31. Suggested LLM System Understanding

When an LLM is given this README, it should understand the project as follows:

```text
PROJECT TYPE:
Offline multimodal meeting intelligence / meeting analytics research prototype.

PRIMARY INPUTS:
1. Long-duration meeting audio
2. Corresponding PPT presentation

PRIMARY OUTPUT:
Evidence-grounded, structured and explainable meeting analysis.

CORE RESEARCH CHAIN:
Speaker attribution
→ Audio–PPT alignment
→ Event/evidence extraction
→ Decision reconstruction
→ Participant contribution
→ Decision influence

KEY DIFFERENTIATOR:
Decision influence is not defined as speaking time.
It is based on decision-relevant participation, proposals, evidence,
objections/challenges, decision impact, and interactions.

CORE CONSTRAINT:
Offline/privacy-protecting processing.

IMPORTANT:
This report is a proposed architecture/evaluation plan, not a report
of final experimental results.
```

---

# 32. Implementation Interpretation Rules for Future AI Agents

When an AI coding assistant or another LLM works on this project:

### Rule 1 — Preserve the multimodal nature
Do not reduce the system to transcript-only summarization.

### Rule 2 — Preserve speaker attribution
Statements must retain speaker identity and timestamps wherever possible.

### Rule 3 — Preserve PPT linkage
Meeting statements should be connectable to relevant slide content.

### Rule 4 — Preserve evidence grounding
Claims, events and decisions should have traceable supporting evidence.

### Rule 5 — Preserve decision lineage
The system should show how discussion progressed from proposal/issue to final decision.

### Rule 6 — Do not equate talk time with influence
Speaking duration can be a participation signal, but the report explicitly argues that influence should depend on decision-relevant contribution.

### Rule 7 — Explain scores
Influence output should contain supporting evidence.

### Rule 8 — Respect offline processing
The intended design is local/offline and privacy-protecting.

### Rule 9 — Do not invent unspecified models or formulas
Choose implementation details only when designing the actual system, and label those choices as implementation decisions rather than report facts.

### Rule 10 — Evaluate component by component
Use the report's evaluation categories and baselines to isolate failure points and measure the value of multimodal components.

---

# 33. Key Terms / Glossary

| Term | Meaning in this project |
|---|---|
| **Multimodal Meeting Intelligence** | Joint analysis of meeting audio and PPT information |
| **Speaker Diarization** | Identifying and segmenting who spoke when |
| **ASR** | Automatic Speech Recognition; converts speech into text |
| **Speaker-attributed transcript** | Transcript where each statement is linked to a speaker and timestamp |
| **PPT Processing** | Conversion of presentation slides into structured text/visual representations |
| **Audio–PPT Alignment** | Connecting spoken discussion to the relevant presentation slide |
| **Temporal Alignment** | Matching content using time information |
| **Semantic Alignment** | Matching content based on meaning/similarity |
| **Meeting Event Extraction** | Identifying proposals, objections, evidence, corrections, agreements, decisions and action items |
| **Evidence Extraction** | Identifying information supporting claims or decisions |
| **Decision Lineage** | The chain describing how a proposal/discussion evolved into a final decision |
| **Interaction Analysis** | Modeling participant responses, support, objections and interactions |
| **Influence Analysis** | Estimating how participant contributions affect decisions |
| **RTF** | Real-Time Factor, used to evaluate processing efficiency |
| **DER** | Diarization Error Rate |
| **WER** | Word Error Rate |
| **Ablation Study** | Removing components one at a time to measure their contribution |

---

# 34. References

The source report contains 28 references.

1. A. Dementyev, C. K. A. Reddy, S. Wisdom, N. Chatlani, J. R. Hershey, and R. F. Lyon, “Towards sub-millisecond latency real-time speech enhancement models on hearables,” Proc. IEEE ICASSP, 2025.
2. H. Schröter, T. Rosenkranz, A. N. Escalante-B., and A. Maier, “Deep multi-frame filtering for hearing aids,” INTERSPEECH, 2023, pp. 3869–3873.
3. B. Lay, R. Makarov, and T. Gerkmann, “Real-time diffusion buffer for speech enhancement on a laptop,” INTERSPEECH, 2025, pp. 3531–3532.
4. X. Liang, L. Zhang, Z. Wu, and R. Xu, “Lite-RTSE: Exploring a cost-effective lite DNN model for real-time speech enhancement in RTC scenarios,” IEEE Signal Processing Letters, 2023, doi: 10.1109/LSP.2023.3330124.
5. R. Dahiya and S. Kumar, “Noise-robust speech recognition with latency-aware performance trade-offs,” IC3ECSBHI, 2026.
6. N. Kanda, J. Wu, Y. Wu, X. Xiao, Z. Meng, X. Wang, Y. Gaur, Z. Chen, J. Li, and T. Yoshioka, “Streaming multi-talker ASR with token-level serialized output training,” INTERSPEECH, 2022, pp. 3774–3778.
7. N. Kanda, J. Wu, X. Wang, Z. Chen, J. Li, and T. Yoshioka, “VarArray meets t-SOT: Advancing the state of the art of streaming distant conversational speech recognition,” IEEE ICASSP, 2023, pp. 1–5.
8. N. Kanda, J. Wu, Y. Wu, X. Xiao, Z. Meng, X. Wang, Y. Gaur, Z. Chen, J. Li, and T. Yoshioka, “Streaming speaker-attributed ASR with token-level speaker embeddings,” INTERSPEECH, 2022, doi: 10.48550/arXiv.2203.16685.
9. C. Li, L. Yang, W. Wang, and Y. Qian, “SkiM: Skipping memory LSTM for low-latency real-time continuous speech separation,” IEEE ICASSP, 2022, doi: 10.1109/ICASSP43922.2022.9746372.
10. S. Chen, Y. Wu, Z. Chen, J. Wu, T. Yoshioka, S. Liu, J. Li, and X. Yu, “Ultra fast speech separation model with teacher student learning,” INTERSPEECH, 2021, pp. 3026–3030.
11. A. Tripathi, H. Lu, and H. Sak, “End-to-end multi-talker overlapping speech recognition,” IEEE ICASSP, 2020, doi: 10.1109/ICASSP40776.2020.9054328.
12. J. Patino, H. Delgado, and N. Evans, “Enhanced low-latency speaker spotting using selective cluster enrichment,” BIOSIG, 2018, doi: 10.23919/BIOSIG.2018.8553619.
13. H. Bredin, R. Yin, J. M. Coria, G. Gelly, P. Korshunov, M. Lavechin, D. Fustes, H. Titeux, W. Bouaziz, and M.-P. Gill, “pyannote.audio: Neural building blocks for speaker diarization,” IEEE ICASSP, 2020, pp. 7124–7128.
14. R. Zhen, X. Zhang, C. Min, and B. Li, “Winner takes it all: An efficient overlap-aware hybrid online diarization with partial backtracking mechanism,” IEEE ICME, 2024, doi: 10.1109/ICME57554.2024.10687627.
15. S. Cornell, M. Omologo, S. Squartini, and E. Vincent, “Overlapped speech detection and speaker counting using distant microphone arrays,” Computer Speech & Language, vol. 72, art. 101306, 2022.
16. Z. Wang, S. Wu, H. Chen, M. He, J. Du, C.-H. Lee, J. Chen, S. Watanabe, S. M. Siniscalchi, O. Scharenborg, et al., “The multimodal information based speech processing (MISP) 2022 challenge: Audio-visual diarization and recognition,” IEEE ICASSP, 2023, doi: 10.1109/ICASSP49357.2023.10094836.
17. A. Eliav and S. Gannot, “Audio-visual approach for multimodal concurrent speaker detection,” IEEE Transactions on Audio, Speech, and Language Processing, 2026, doi: 10.1109/TASLPRO.2026.3668135.
18. K. Ishizuka, S. Araki, K. Otsuka, and M. Fujimoto, “A speaker diarization method based on the probabilistic fusion of audio-visual location information,” ICMI-MLMI, 2009, doi: 10.1145/1647314.1647327.
19. A. Noulas, G. Englebienne, and B. J. A. Kröse, “Multimodal speaker diarization,” IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 34, no. 1, pp. 79–93, 2012.
20. J. S. Chung, B.-J. Lee, and I. Han, “Who said that? Audio-visual speaker diarisation of real-world meetings,” INTERSPEECH, 2019, pp. 371–375.
21. R. Ahmad, S. Zubair, H. Alquhayz, and A. Ditta, “Multimodal speaker diarization using a pre-trained audio-visual synchronization model,” Sensors, vol. 19, no. 23, art. 5163, 2019.
22. J. Carletta, S. Ashby, S. Bourban, M. Flynn, M. Guillemot, T. Hain, J. Kadlec, J. Karaiskos, W. Kraaij, M. Kronenthal, et al., “The AMI meeting corpus: A pre-announcement,” in Machine Learning for Multimodal Interaction, LNCS, 2006, doi: 10.1007/11677482_3.
23. H. Hung, Y. Huang, G. Friedland, and D. Gatica-Perez, “Estimating dominance in multi-party meetings using speaker diarization,” IEEE Transactions on Audio, Speech, and Language Processing, vol. 19, no. 4, pp. 847–860, 2011.
24. W. Dong, B. Lepri, B. Cappelletti, A. S. Pentland, F. Pianesi, and M. Zancanaro, “Using the influence model to recognize functional roles in meetings,” ICMI, 2007, pp. 271–278.
25. N. P. Garg, S. Favre, H. Salamin, D. Hakkani-Tür, and A. Vinciarelli, “Role recognition for meeting participants: An approach based on lexical information and social network analysis,” ACM Multimedia, 2008, pp. 693–696.
26. K. Anderer, A. Reich, and M. Wölfel, “MaViLS, a benchmark dataset for video-to-slide alignment, assessing baseline accuracy with a multimodal alignment algorithm leveraging speech, OCR, and visual features,” INTERSPEECH, 2024, pp. 1375–1379.
27. A. Krishna et al., “Team Hitachi @ AutoMin 2021: Reference-free automatic minuting pipeline with argument structure construction over topic-based summarization,” INTERSPEECH/AutoMin, 2021.
28. Anonymous authors, “Multi-person speech curator for minutes of meetings along with meeting summarization and language translation,” ICAA 2023.

---

# 35. Source-to-README Mapping

For traceability, the README maps the report's chapters to implementation-oriented sections:

| Report chapter | README section(s) |
|---|---|
| Abstract | §§2–3 |
| Chapter 1: Introduction | §§3–4 |
| Motivation | §4 and §23 |
| Objectives | §5 |
| Chapter 2: Literature Review | §§20–22 and §34 |
| Research Gap | §22 |
| Chapter 3: Methodology | §§6–14 |
| System Architecture | §§7–8 |
| Influence Scoring | §13 |
| Final System Output | §14 |
| Chapter 4: Evaluation Plan | §§15–17 |
| Baselines | §16 |
| Ablation Study | §17 |
| Human Evaluation | §18 |
| Chapter 5: Timeline | §19 |
| Chapter 6: Conclusion | §30 |
| References | §34 |

---

# 36. Final LLM Context Block

```yaml
project:
  name: "Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis"
  type: "Multimodal AI research/project prototype"
  status: "Proposed/intended framework in the submitted report"
  institution: "Symbiosis Institute of Technology, Pune"
  academic_year: "2026-27"

inputs:
  - "Long-duration meeting audio"
  - "Corresponding PPT presentation"

audio_processing:
  - "Resampling"
  - "Normalization"
  - "Voice Activity Detection"
  - "Speaker diarization"
  - "Speaker embeddings"
  - "Offline ASR"

ppt_processing:
  - "Text/headings"
  - "Tables"
  - "Numerical values"
  - "Visual information"

fusion:
  methods:
    - "Temporal alignment"
    - "Semantic alignment"
  representation:
    - "Speaker"
    - "Statement"
    - "Timestamp"
    - "Corresponding slide"

event_analysis:
  events:
    - "Proposal"
    - "Question"
    - "Objection"
    - "Evidence"
    - "Correction"
    - "Agreement"
    - "Decision"
    - "Action item"

decision_analysis:
  - "Claim/evidence association"
  - "Decision reconstruction"
  - "Decision lineage"

interaction_analysis:
  - "Responses"
  - "Support"
  - "Objections"
  - "Participant interaction graph"

influence:
  signals:
    - "Participation"
    - "Proposal contribution"
    - "Evidence contribution"
    - "Objection/challenge contribution"
    - "Decision contribution"
    - "Interaction contribution"
  principle: "Do not use speaking time as the only measure"
  requirement: "Explain scores using evidence"
  exact_formula: "Not specified in report"

outputs:
  - "Meeting summary"
  - "Speaker-wise participation"
  - "Key discussion points"
  - "PPT-linked statements"
  - "Proposals, objections and evidence"
  - "Decision lineage"
  - "Action items"
  - "Evidence-backed participant influence ranking"

evaluation:
  speech_recognition: "WER"
  diarization: "DER"
  alignment: ["Precision", "Recall", "F1", "Alignment Accuracy"]
  event_extraction: ["Precision", "Recall", "F1"]
  decision_extraction: ["Precision", "Recall", "F1"]
  decision_lineage: "Chain/relationship accuracy"
  influence: ["Correlation with human ratings", "Rank correlation"]
  efficiency: ["Processing time", "RTF", "Memory usage"]

baselines:
  - "B1 Transcript-only"
  - "B2 Speaker + Transcript"
  - "B3 Audio + PPT without Decision Analysis"
  - "B4 Audio + PPT + Decision Analysis"
  - "Proposed System"

ablation:
  - "Remove PPT"
  - "Remove cross-modal alignment"
  - "Remove evidence reasoning"
  - "Remove interaction modeling"
  - "Remove influence-on-decision component"

constraints:
  - "Offline"
  - "Privacy-protecting"
  - "Long-duration processing"
  - "Intended to be feasible on laptop/local resources"

do_not_assume_from_report:
  - "Specific model names"
  - "Specific libraries/frameworks"
  - "Final influence formula/weights"
  - "Final benchmark numbers"
  - "Final deployment architecture"
  - "Final security architecture"
```

---

## End of README

This document is intentionally structured so that a human developer, coding agent, research assistant, or LLM can quickly understand the project's **purpose → inputs → pipeline → intermediate representations → decision reasoning → influence analysis → outputs → evaluation → constraints**, while clearly separating what is stated in the submitted report from implementation details that still need to be chosen.
