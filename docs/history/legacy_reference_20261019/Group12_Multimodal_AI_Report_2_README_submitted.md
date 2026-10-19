# Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis
## Report 2 — Resources, Dataset, Modalities, Risk Analysis & EDA

> **Source document:** Group 12 Multimodal AI Project Report 2  
> **Project:** *Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis*  
> **Institution:** Symbiosis Institute of Technology, Pune  
> **Department:** Artificial Intelligence & Machine Learning  
> **Academic Year:** 2026–27  
>
> **Purpose of this README:** Convert Report 2 into a structured, LLM-friendly format so that a developer, researcher, coding agent, or other LLM can understand the selected dataset, resource requirements, risks, modalities, preprocessing decisions, and exploratory findings without needing to interpret the original PDF layout.

---

# 1. Project Identity

| Field | Value |
|---|---|
| Project Title | **Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis** |
| Course | Multimodal AI |
| Degree | Bachelor of Technology in Artificial Intelligence & Machine Learning |
| Institution | Symbiosis Institute of Technology, Pune |
| Department | Artificial Intelligence & Machine Learning |
| Academic Year | 2026–27 |
| Group | Group 12 |
| Project Guide | Dr. Nivedita Mishra |

### Team

- Anushka Chatterjee — 23070126015
- Amitkumar Racha — 24070126501
- Sahil Awatramani — 23070126112
- Shriyans Sahoo — 23070126125

---

# 2. What This Report Covers

This second report focuses on the practical and data-oriented foundation of the proposed meeting-intelligence system.

It covers:

1. Resource allocation
2. Risk analysis and mitigation
3. Dataset selection and description
4. Modalities selected for the system
5. Rationale for modality selection
6. Exploratory Data Analysis (EDA)
7. Audio exploration
8. Dialogue-act exploration
9. Decision-annotation exploration
10. Presentation/document exploration
11. Cross-modal exploration
12. EDA findings and preprocessing implications
13. References

The report uses the **AMI (Augmented Multi-party Interaction) Meeting Corpus** as the selected multimodal dataset.

---

# 3. Resource Allocation

The project requires:

- local storage,
- computational resources,
- software libraries,
- intermediate-output storage/caching.

The resource plan is motivated mainly by the computational cost of processing long meeting recordings and by the size and multimodal nature of the AMI corpus.

---

## 3.1 Storage Requirements

The AMI Meeting Corpus contains a large collection of meeting audio.

According to the report:

- raw audio recordings occupy **more than 80 GB**,
- the corpus includes headset and microphone-array recordings,
- additional storage is required beyond raw audio.

### Additional storage targets

The project may need storage for:

```text
Raw audio
   +
Processed audio
   +
Transcripts
   +
Speaker diarization outputs
   +
Extracted presentations
   +
Semantic embeddings
```

### Storage implication

Storage should therefore be planned for both:

1. original dataset files, and
2. generated intermediate/final artifacts.

---

# 4. Computational Resources

The main computational demand comes from speech processing.

The report identifies these major processing components:

| Component | Tool specified in Report 2 | Purpose |
|---|---|---|
| Automatic Speech Recognition | **faster-whisper** | Speech-to-text |
| Speaker Diarization | **pyannote.audio** | Identify/separate speakers |
| Voice Activity Detection | **Silero VAD** | Detect speech regions |

### Why computation is important

Both ASR and speaker diarization can be computationally expensive, particularly for long meetings.

Therefore, the project is designed as a **modular offline workflow** in which:

- each major processing stage can operate independently,
- intermediate outputs can be stored/cached,
- cached results can be reused,
- expensive processing does not need to be repeated.

### ASR optimization

The report states that ASR uses **int8 quantization** to reduce computational load.

---

# 5. Software Resources

The implementation environment is Python.

The main libraries/tools specified in Report 2 are:

| Software / Library | Role |
|---|---|
| **Python** | Main development environment |
| **faster-whisper** | Automatic Speech Recognition |
| **pyannote.audio** | Speaker diarization |
| **Silero VAD** | Voice Activity Detection |
| **python-pptx** | Presentation-content extraction |
| **sentence-transformers** | Semantic embeddings |
| **LibreOffice** | Legacy `.ppt` → `.pptx` conversion |

### Modular software architecture

The report explicitly separates these modules into stages so that:

- modules can be tested independently,
- outputs can be reused,
- expensive operations can be cached.

---

# 6. Risk Analysis and Mitigation

The report identifies four major risks:

1. Data format incompatibility
2. Computational bottlenecks
3. Acoustic challenges
4. Multimodal alignment problems

---

## 6.1 Risk: Data Format Incompatibility

### Problem

Presentation files in the AMI corpus may use the legacy:

```text
.ppt
```

format.

The chosen extraction workflow requires:

```text
.pptx
```

### Mitigation

Introduce a preliminary conversion stage:

```text
Legacy .ppt
      |
      v
Headless LibreOffice
      |
      v
.pptx
      |
      v
python-pptx extraction
```

This conversion is treated as a required preprocessing step.

---

## 6.2 Risk: Computational Bottlenecks

### Problem

The following processes are computationally demanding:

- transcription,
- speaker diarization.

This becomes more significant as meeting duration increases.

### Mitigation

Use an independent modular pipeline with intermediate JSON outputs.

Examples of reusable artifacts include:

```text
transcripts.json
alignments.json
speaker_segments.json
...
```

These outputs can be cached so development/testing does not rerun expensive processing on the raw recordings.

---

## 6.3 Risk: Acoustic Challenges

### Problem

Meeting-room recordings may contain:

- overlapping speech,
- background noise,
- room reverberation.

These conditions can affect:

- ASR,
- speaker diarization.

### Mitigation

The report proposes aligning:

- speech-activity detection,
- ASR segmentation,
- speaker-diarization boundaries

using temporal overlap.

Conceptually:

```text
VAD / ASR segment
       |
       | temporal overlap
       v
Speaker diarization boundary
       |
       v
Best matching speaker assignment
```

This allows a speech segment to be associated with the appropriate speaker even when the boundaries produced by the systems are not exactly identical.

---

## 6.4 Risk: Multimodal Alignment

### Problem

The project combines two information streams:

```text
Spoken dialogue
+
Presentation slides
```

Misalignment can occur in:

- time,
- semantics.

Such errors can affect downstream:

- decision analysis,
- participant influence analysis.

### Mitigation

Preserve audio timestamps throughout the speech-processing pipeline.

Transform presentation content into:

- textual representations,
- semantic embeddings.

Then perform alignment using both:

```text
Temporal information
+
Semantic information
```

---

# 7. Selected Dataset

## 7.1 Dataset Name

**AMI (Augmented Multi-party Interaction) Meeting Corpus**

The report describes it as a multimodal database designed for studying meetings and human interaction.

---

## 7.2 Dataset Size / General Description

According to the report:

- approximately **100 hours** of synchronized meeting recordings are included,
- meetings were recorded in several instrumented meeting rooms,
- many meetings involve a group of four people,
- participants take different roles in a fictional design-project scenario,
- the database also contains natural meetings.

This provides a range of meeting interactions.

---

# 8. Modalities and Annotations Available in AMI

The dataset contains multiple synchronized information sources.

### Audio

- close-talking headset microphone recordings from individual participants,
- microphone-array recordings capturing the whole room.

### Video

- video streams.

### Presentation / document content

- electronic copies of presentations,
- documents shown in meetings.

### Textual / annotation data

- word-level speech transcripts,
- dialogue-act annotations,
- named-entity annotations,
- meeting summaries,
- decision-related annotations.

Conceptually:

```text
AMI Meeting Corpus
│
├── Individual headset audio
├── Room microphone-array audio
├── Video
├── Presentations
├── Documents
├── Word-level transcripts
├── Dialogue acts
├── Named entities
├── Meeting summaries
└── Decision annotations
```

---

# 9. Why AMI Is Suitable for This Project

The report selects AMI because it provides a combination of:

- speech,
- speaker-related information,
- presentation material,
- manual annotations,
- synchronized multimodal sources.

This is especially important because the project requires relationships between modalities.

### Critical property: synchronization

The timing between sources is important because information in one modality can be correlated with information in another according to the meeting timeline.

For example:

```text
At time T:
Participant statement
        ↕
Relevant slide content
```

---

# 10. How Dataset Annotations Support Evaluation

The report identifies several useful reference signals.

### Word-level transcripts

Useful for evaluating and analyzing speech recognition/conversation processing.

### Dialogue-act annotations

Useful for understanding conversational behavior and for analyzing the structure and role of utterances.

### Decision annotations

Useful as reference data for the proposed decision-analysis component.

### Presentation/document data

Provide additional context related to subjects discussed by participants.

Thus the dataset supports both:

```text
System Input
+
Reference / Evaluation Data
```

---

# 11. Modalities Chosen for the Project

The proposed system focuses on **two major modalities**:

1. **Spoken Audio**
2. **Visual/Document Information**

The AMI dataset includes video, but the report states that **video is not used in the current implementation**.

---

# 12. Modality 1 — Spoken Audio

## 12.1 What audio provides

Spoken audio captures the actual verbal interaction among meeting participants.

It provides information about:

- what was said,
- who said it,
- when it was said,
- how the discussion progressed.

---

## 12.2 Audio sources in AMI

AMI contains:

- close-talking participant headset recordings,
- room microphone-array recordings.

### Headset audio

More closely associated with individual participants.

### Room-array audio

Captures the overall meeting atmosphere and may contain:

- background noise,
- reverberation,
- overlapping speech.

---

# 13. Spoken-Audio Processing Pipeline

The report defines the following sequence:

```text
Raw Audio
   |
   v
1. Voice Activity Detection
   |
   v
2. Speaker Diarization
   |
   v
3. Automatic Speech Recognition
   |
   v
4. Speaker-attributed Transcript
   |
   v
5. Temporal Alignment of ASR + Diarization
```

---

## 13.1 Step 1 — Voice Activity Detection

Use:

**Silero VAD**

Purpose:

- identify speech regions,
- reduce irrelevant non-speech intervals,
- provide speech-focused segments for later processing.

---

## 13.2 Step 2 — Speaker Diarization

Use:

**pyannote.audio**

Purpose:

- determine who is speaking at each point in time,
- produce speaker segments,
- maintain speaker attribution.

---

## 13.3 Step 3 — Automatic Speech Recognition

Use:

**faster-whisper**

Purpose:

```text
Speech → Text
```

The report specifically intends the ASR pipeline to work offline.

---

## 13.4 Step 4 — Speaker-Attributed Transcript

Combine ASR and speaker diarization.

The resulting information should make it possible to establish:

```text
WHO?
WHAT?
WHEN?
```

Conceptual representation:

```text
Timestamp → Speaker → Statement
```

---

## 13.5 Step 5 — Temporal Alignment

ASR segments and diarization segments may have different boundaries.

The project therefore aligns them using temporal overlap so that recognized text can be associated with the correct speaker.

---

# 14. Modality 2 — Visual / Document Information

The second modality is the presentation/document content used during the meeting.

AMI contains digital copies of:

- presentations,
- documents used in the meetings.

---

## 14.1 Information available from the presentation

Presentation/document content can contain:

- slide text,
- tables,
- notes,
- design alternatives,
- technical details,
- other material relevant to the discussion.

This modality provides contextual information that may not be present in the transcript alone.

---

# 15. PPT Processing Pipeline

The report defines the following workflow:

```text
Legacy Presentation
      |
      v
1. Convert .ppt → .pptx
      |
      v
2. Extract slide text/structure
      |
      v
3. Textual preprocessing
      |
      v
4. Semantic embedding generation
      |
      v
5. Alignment with spoken discussion
```

### Tools

| Task | Tool |
|---|---|
| `.ppt` → `.pptx` conversion | LibreOffice |
| Slide content extraction | python-pptx |
| Semantic embeddings | sentence-transformers |

---

# 16. Semantic Representation of Presentation Content

After extracting slide content, the report states that it may be represented with semantic embeddings generated using **sentence-transformers**.

Conceptually:

```text
Slide Content
   |
   v
Text / Structural Representation
   |
   v
Semantic Embedding
   |
   v
Comparable with speech representation
```

This supports cross-modal matching between what is being discussed and what appears on a slide.

---

# 17. Why These Two Modalities Were Selected

The report describes the two modalities as complementary.

| Modality | Primary Information |
|---|---|
| **Spoken Audio** | Who said what, when, and how discussion progressed |
| **Presentation / Document** | What topic, design, or material was being discussed |

Combining them enables the project to move beyond:

```text
Speech transcription only
```

toward:

```text
Decision analysis
+
Participant influence analysis
```

---

# 18. Why Video Is Not Used

Although AMI contains video recordings, the report explicitly says that **video is not being used for the current implementation**.

Therefore:

```text
AMI provides:
Audio + Video + Documents + Annotations

Current project uses:
Audio + Presentation/Document

Current project does NOT use:
Video
```

Do not assume video-based face recognition, visual speaker identification, lip reading, or visual attention analysis is part of the current implementation.

---

# 19. Exploratory Data Analysis (EDA)

The EDA is multimodal rather than conventional tabular EDA.

The report explores:

1. audio structure,
2. audio properties,
3. dialogue acts,
4. decision annotations,
5. presentations/documents,
6. cross-modal relationships.

The stated goal is to understand the dataset and identify preprocessing requirements **before applying the major machine-learning components**.

---

# 20. Audio Data Exploration

The audio data was explored at:

- file level,
- metadata level.

The purpose was to understand:

- available recording sources,
- suitability for speech processing,
- recording characteristics,
- meeting-length variation.

---

## 20.1 Two Main Audio Recording Settings

### Headset recordings

Characteristics:

- associated more closely with individual participants.

### Room microphone-array recordings

Characteristics:

- capture the broader meeting environment,
- may include noise,
- may contain reverberation,
- may include overlapping speech.

---

## 20.2 Meeting Duration Exploration

Available WAV recordings were examined to study:

- recording length,
- audio properties,
- meeting-duration variability.

This matters because the pipeline must not assume that all meetings have the same duration.

---

## 20.3 Audio Preprocessing Finding

The initial analysis showed that preprocessing is required before:

- ASR,
- speaker diarization.

The report states that the selected audio input is normalized by:

```text
Multi-channel audio
        ↓
Mono audio
        ↓
16 kHz sampling rate
```

Therefore, the standardized target format is:

```text
Mono
16 kHz
```

---

# 21. Dialogue-Act Exploration

AMI provides manually annotated dialogue acts representing different forms of communicative behavior.

The report analyzed these annotations to understand the linguistic/conversational structure of meetings.

### Number of dialogue-act occurrences

The report states:

**116,357** dialogue-act occurrences were found while analyzing the dialogue-act XML files.

---

## 21.1 Dialogue-Act Distribution

| Dialogue Act | Count | Percentage |
|---|---:|---:|
| Inform | 33,484 | 28.8% |
| Backchannel | 21,910 | 18.8% |
| Assess | 21,391 | 18.4% |
| Fragment | 16,796 | 14.4% |
| Suggest | 9,391 | 8.1% |
| Stall | 8,459 | 7.3% |
| Elicit-Inform | 4,240 | 3.6% |
| Other | 686 | 0.6% |
| **Total** | **116,357** | **100.0%** |

---

# 22. Interpretation of Dialogue-Act EDA

The distribution shows that meeting conversations contain multiple forms of interaction rather than only straightforward informative speech.

The report highlights:

### Highly prevalent categories

- Inform
- Backchannel
- Assess
- Fragment

### Particularly relevant decision-related categories

- **Suggest** — associated with proposals/suggestions.
- **Elicit-Inform** — associated with requests for information.

This supports the need to analyze the **role of an utterance in conversational context**, rather than relying on isolated keywords.

---

# 23. Important Implication for Event and Influence Analysis

The report explicitly states that decision formation and participant influence cannot be accurately inferred from isolated keywords.

Instead, the system must consider:

```text
Utterance content
+
Conversational context
+
Position within dialogue
+
Interaction with other participants
+
Relation to decisions
```

This is important because a keyword such as "suggest" does not by itself establish the complete meaning or impact of the utterance.

---

# 24. Decision Annotation Exploration

AMI contains decision annotations.

The report investigated the structure of the decision XML files to understand how decisions are represented.

### Purpose

Decision annotations are intended to serve as reference information for the system's decision-analysis component.

They can help evaluate whether the system correctly identifies:

- important decision points,
- surrounding discussion,
- progression toward a decision.

---

# 25. Decision Context

The report emphasizes that decisions should not be treated as isolated events.

They need to be understood in relation to preceding conversational actions.

Examples identified in the report:

```text
Suggest
   ↓
Assess / Discuss
   ↓
More evidence / interaction
   ↓
Decision
```

Therefore, dialogue-act information can provide context clues for reconstructing decision progression.

---

# 26. Presentation and Document Exploration

The presentation data was explored separately from audio because the two modalities have different data formats.

The AMI corpus contains digital copies of:

- presentations,
- documents used in meetings.

---

# 27. Presentation Format Problem

The EDA identified a compatibility issue:

```text
AMI presentation:
legacy .ppt

Selected extraction workflow:
.pptx
```

Therefore, conversion is required.

The report explicitly treats this as a **necessary preprocessing stage**, not an optional transformation.

---

# 28. Document Preprocessing Workflow

The report specifies five stages:

### Step 1 — Format conversion

```text
.ppt → .pptx
```

using LibreOffice.

### Step 2 — Content extraction

Use **python-pptx** to extract:

- textual content,
- slide structure.

### Step 3 — Text preprocessing

Clean/process extracted textual content.

### Step 4 — Semantic embeddings

Use **sentence-transformers** to generate semantic representations.

### Step 5 — Cross-modal alignment

Align slide representations with spoken discussion.

Full flow:

```text
Legacy PPT
   ↓
LibreOffice Conversion
   ↓
PPTX
   ↓
python-pptx
   ↓
Slide Text / Structure
   ↓
Text Preprocessing
   ↓
Sentence-Transformers
   ↓
Semantic Representation
   ↓
Audio–PPT Alignment
```

---

# 29. Cross-Modal Data Exploration

The preliminary exploration also examined how audio and presentation information can be linked.

The report gives these conceptual representations:

```text
Audio
  ↓
Speech Segments
  ↓
Speaker Information
  ↓
Transcript
```

and:

```text
Presentation
  ↓
Slide Content
  ↓
Semantic Representation
```

These two representations can then be linked using:

```text
Temporal Information
+
Semantic Information
```

---

# 30. Example of Cross-Modal Linking

Suppose a participant discusses a specific design option.

The system should be capable of associating:

```text
Spoken discussion about design option
             ↕
Relevant PPT slide containing that design option
```

This relationship is critical because decision-related context may be distributed between:

- spoken conversation, and
- presentation material.

---

# 31. Why Cross-Modal Alignment Matters

The report identifies multimodal alignment as especially important for **decision lineage**.

A decision may be supported by information spread across:

```text
Conversation
+
Presentation material
```

Therefore, a system analyzing only one modality can miss context needed to understand:

- what was proposed,
- what evidence was shown,
- what issue was discussed,
- what decision eventually resulted.

---

# 32. EDA Findings and Preprocessing Implications

The report summarizes the major observations and the resulting pipeline decisions.

| Observation | Implication for Pipeline |
|---|---|
| Multiple audio recording sources | Audio standardization is required |
| Noise, reverberation and overlapping speech may occur | VAD and speaker-aware processing are required |
| Different meeting durations | Meetings need to be processed independently |
| Multiple dialogue-act categories | Transcript analysis should consider conversational context |
| Decision annotations are available | They can provide reference information for decision analysis |
| Presentations may use legacy `.ppt` format | Format conversion is required before extraction |
| Audio and document data contain complementary information | Cross-modal alignment is required |

---

# 33. Overall EDA Interpretation

The report states that this EDA is better understood as:

```text
Pre-processing exploration
+
Modality-specific data exploration
```

rather than conventional tabular EDA.

The main objective is to understand how the raw multimodal dataset should be transformed before the main ML/AI components are executed.

---

# 34. Preprocessing Requirements Extracted from Report 2

The report establishes the following practical preprocessing requirements.

## Audio

```text
Raw multi-channel audio
        ↓
Mono conversion
        ↓
16 kHz standardization
        ↓
VAD
        ↓
ASR / diarization
```

## Presentation

```text
.ppt
 ↓
.pptx
 ↓
Content extraction
 ↓
Text preprocessing
 ↓
Semantic embedding
```

## Cross-modal

```text
Audio timestamp
+
Speaker-attributed transcript
+
Slide semantic representation
        ↓
Temporal + semantic alignment
```

## Computational

```text
Expensive processing
        ↓
Intermediate JSON artifacts
        ↓
Cache
        ↓
Reuse in development/evaluation
```

---

# 35. Data and Processing Dependencies

A future implementation should understand the dependencies in roughly this order:

```text
AMI Dataset
│
├── Audio
│   ├── Headset recordings
│   └── Room-array recordings
│        ↓
│      Standardization
│        ↓
│      VAD
│        ↓
│      Diarization
│        ↓
│      ASR
│        ↓
│      Speaker-attributed transcript
│
├── Presentations/Documents
│   ├── Legacy .ppt
│   └── Other document content
│        ↓
│      LibreOffice conversion
│        ↓
│      python-pptx
│        ↓
│      Text preprocessing
│        ↓
│      Sentence-transformers
│        ↓
│      Slide semantic representation
│
└── Annotations
    ├── Word-level transcripts
    ├── Dialogue acts
    ├── Named entities
    ├── Meeting summaries
    └── Decision annotations

Audio representation + PPT representation
                  ↓
       Temporal + Semantic Alignment
                  ↓
          Multimodal meeting analysis
```

---

# 36. LLM-Friendly Technical Stack Extracted from Report 2

This is the stack explicitly mentioned in the report:

```yaml
language:
  - Python

audio:
  asr:
    tool: faster-whisper
    optimization: int8 quantization
  diarization:
    tool: pyannote.audio
  vad:
    tool: Silero VAD
  preprocessing:
    - multi-channel-to-mono conversion
    - 16 kHz standardization

presentation:
  conversion:
    tool: LibreOffice
    purpose: ".ppt -> .pptx"
  extraction:
    tool: python-pptx
  semantic_representation:
    tool: sentence-transformers

dataset:
  name: "AMI Meeting Corpus"
  approximate_duration: "100 hours"
  modalities_available:
    - headset audio
    - microphone-array audio
    - video
    - presentations
    - documents
    - word-level transcripts
    - dialogue-act annotations
    - named-entity annotations
    - meeting summaries
    - decision annotations

current_project_modalities:
  - spoken_audio
  - presentation_document

excluded_current_modality:
  - video

processing_strategy:
  - offline
  - modular
  - intermediate-output caching
  - reusable JSON outputs
```

---

# 37. Resource Strategy for an AI Coding Agent

When an LLM/coding agent works on this project, it should understand the resource constraints as:

### Storage

Plan for:

```text
>80 GB raw audio
+
processed artifacts
+
transcripts
+
diarization outputs
+
presentation extraction
+
semantic embeddings
```

### Compute

Prioritize efficient handling of:

- ASR,
- speaker diarization,
- long recordings.

### Reusability

Do not make the pipeline regenerate all outputs every time.

Prefer:

```text
Raw Input
  ↓
Stage 1
  ↓
Cached Output
  ↓
Stage 2
  ↓
Cached Output
  ↓
Stage 3
```

rather than repeatedly:

```text
Raw Input → full pipeline
Raw Input → full pipeline
Raw Input → full pipeline
```

---

# 38. Risk-Aware Implementation Rules

A future implementation should preserve the following report-derived constraints.

### Rule 1 — Normalize audio

Convert selected multi-channel audio to:

```text
mono @ 16 kHz
```

### Rule 2 — Keep timestamps

Timestamp information must survive the speech-processing stages because it is needed for:

- speaker attribution,
- cross-modal alignment,
- decision-lineage reconstruction.

### Rule 3 — Expect imperfect diarization/ASR boundaries

Use temporal overlap when combining speaker and speech segments.

### Rule 4 — Convert presentations first

Do not assume all AMI presentations are immediately compatible with python-pptx.

Check/convert:

```text
.ppt → .pptx
```

### Rule 5 — Preserve semantic information

PPT content must be represented so it can be compared with meeting discussion.

### Rule 6 — Consider conversational context

Do not perform decision/influence analysis solely by keyword matching.

### Rule 7 — Process meetings independently

Meeting durations vary; the pipeline should not assume one fixed recording length.

### Rule 8 — Cache expensive outputs

Store intermediate results, preferably in structured machine-readable files such as JSON where appropriate.

### Rule 9 — Current modality scope is audio + documents

Do not silently add video-based processing to the current implementation.

---

# 39. Relationship to the Main Project Architecture

Report 2 provides the implementation/data foundation for the broader architecture described in the project.

The relationship is:

```text
REPORT 2
Resource + Dataset + EDA + Preprocessing
                  |
                  v
REPORT 1 / MAIN SYSTEM
Multimodal Meeting Intelligence Pipeline
                  |
                  v
Audio + PPT Fusion
                  |
                  v
Events / Evidence
                  |
                  v
Decision Reconstruction
                  |
                  v
Participant Contribution
                  |
                  v
Influence Analysis
```

Report 2 therefore answers:

> **What data do we have, what resources are required, what are the risks, how should the modalities be prepared, and what did initial exploration reveal?**

---

# 40. Important Facts That Must Not Be Invented

The report explicitly names some tools and resources, but it does **not** provide a complete production implementation specification.

Do not infer from this report that the project already has:

- final model weights,
- measured production accuracy,
- final hardware benchmark results,
- a fixed semantic-similarity threshold,
- a fixed alignment algorithm formula,
- a finalized database schema,
- a finalized API,
- a finalized frontend,
- a finalized deployment platform,
- a fixed influence-score equation,
- final influence-ranking results.

Those are not established in this report.

---

# 41. Key Dataset Facts

```text
Dataset:
AMI Meeting Corpus

Approximate synchronized meeting content:
~100 hours

Common meeting structure:
Groups of four participants in many meetings

Primary current project modalities:
1. Spoken audio
2. Presentation/document data

Dataset also provides:
- video
- transcripts
- dialogue acts
- named entities
- meeting summaries
- decision annotations

Current project:
Does not use video.
```

---

# 42. Key Numerical EDA Facts

### Storage

```text
Raw audio: > 80 GB
```

### Meeting corpus

```text
Approximately 100 hours of synchronized meeting recordings
```

### Dialogue acts

```text
Total: 116,357
```

### Dialogue-act distribution

```text
Inform        = 33,484 (28.8%)
Backchannel   = 21,910 (18.8%)
Assess        = 21,391 (18.4%)
Fragment      = 16,796 (14.4%)
Suggest       =  9,391 ( 8.1%)
Stall         =  8,459 ( 7.3%)
Elicit-Inform =  4,240 ( 3.6%)
Other         =    686 ( 0.6%)
```

### Audio normalization

```text
Channels: Mono
Sample rate: 16 kHz
```

---

# 43. One-View Project Understanding

An LLM should be able to understand Report 2 from this compact model:

```text
PROJECT
Offline multimodal meeting intelligence.

DATASET
AMI Meeting Corpus (~100h synchronized meeting data).

INPUTS USED
1. Spoken audio
2. PPT/document content

AUDIO TOOLS
Silero VAD
→ pyannote.audio
→ faster-whisper

PPT TOOLS
LibreOffice
→ python-pptx
→ sentence-transformers

AUDIO PREPROCESSING
Multi-channel → mono
16 kHz standardization
VAD
Speaker-aware processing

PPT PREPROCESSING
.ppt → .pptx
Extract content
Text preprocessing
Semantic embeddings

FUSION
Temporal alignment
+
Semantic alignment

ANNOTATIONS AVAILABLE
Transcripts
Dialogue acts
Named entities
Summaries
Decision annotations

IMPORTANT EDA FINDINGS
- Audio sources differ
- Noise/reverberation/overlap exist
- Meeting durations vary
- Dialogue contains multiple interaction types
- Decisions require contextual analysis
- PPT format conversion is necessary
- Audio and PPT provide complementary information

RESOURCE STRATEGY
- >80 GB raw audio
- Additional storage for processed outputs
- ASR/diarization are computationally expensive
- Cache intermediate JSON outputs
- ASR int8 quantization reduces computational load

CURRENT MODALITIES
Audio + document/presentation

NOT CURRENTLY USED
Video
```

---

# 44. References from Report 2

The report includes the following references:

1. G. Louradour, “faster-whisper: Faster Whisper transcription with CTranslate2,” GitHub repository, 2023.  
   https://github.com/SYSTRAN/faster-whisper

2. H. Bredin, “pyannote.audio: Neural building blocks for speaker diarization,” GitHub repository, 2023.  
   https://github.com/pyannote/pyannote-audio

3. Silero Team, “Silero VAD: Pre-trained enterprise-grade voice activity detector,” GitHub repository, 2021.  
   https://github.com/snakers4/silero-vad

4. S. Canny et al., “python-pptx: Create and update PowerPoint files with Python,” GitHub repository, 2013.  
   https://github.com/scanny/python-pptx

5. N. Reimers and I. Gurevych, “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks,” Proc. 2019 Conference on Empirical Methods in Natural Language Processing (EMNLP), Hong Kong, China, 2019, pp. 3982–3992.

6. J. Carletta et al., “The AMI Meeting Corpus: A Pre-Announcement,” in *Machine Learning for Multimodal Interaction (MLMI 2005)*, Lecture Notes in Computer Science, vol. 3869, Springer, Berlin, Heidelberg, 2006, pp. 28–39.

7. AMI Project Consortium, “AMI Meeting Corpus,” Idiap Research Institute.  
   https://www.idiap.ch/webarchives/sites/www.amiproject.org/ami-scientific-portal/meeting-corpus.html

---

# 45. Source-to-README Mapping

| Original Report Section | README Section |
|---|---|
| 1. Resource Allocation | §§3–5 |
| 1.1 Resource Allocation | §§3–5 |
| 1.2 Risk Analysis and Mitigation | §6 |
| 2. Description of Selected Dataset | §§7–10 |
| 3. Modalities Chosen | §§11–18 |
| 3.1 Spoken Audio Modality | §§12–13 |
| 3.2 Visual/Document Modality | §§14–16 |
| 3.3 Rationale for Modality Selection | §17 |
| 4. EDA | §§19–33 |
| 4.1 Audio Data Exploration | §20 |
| 4.2 Dialogue-Act Exploration | §§21–23 |
| 4.3 Decision Annotation Exploration | §§24–25 |
| 4.4 Presentation and Document Exploration | §§26–28 |
| 4.5 Cross-Modal Data Exploration | §§29–31 |
| 4.6 EDA Findings and Preprocessing Implications | §§32–34 |
| References | §44 |

---

# 46. Final Context Block for LLMs

```yaml
project:
  name: "Offline Multimodal Meeting Intelligence for Decision and Participant Influence Analysis"
  course: "Multimodal AI"
  institution: "Symbiosis Institute of Technology, Pune"
  department: "Artificial Intelligence & Machine Learning"
  academic_year: "2026-27"
  group: 12

dataset:
  name: "AMI Meeting Corpus"
  size: "~100 hours synchronized meeting recordings"
  common_meeting_structure: "many meetings involve four participants"
  available_modalities:
    - headset_audio
    - room_microphone_array_audio
    - video
    - presentations
    - documents
    - word_level_transcripts
    - dialogue_act_annotations
    - named_entity_annotations
    - meeting_summaries
    - decision_annotations
  reason_selected:
    - "multimodal meeting data"
    - "speaker-related information"
    - "presentation material"
    - "manual reference annotations"
    - "synchronized sources"

current_modalities:
  audio: true
  presentation_document: true
  video: false

audio_stack:
  language: "Python"
  vad: "Silero VAD"
  diarization: "pyannote.audio"
  asr: "faster-whisper"
  asr_optimization: "int8 quantization"

audio_preprocessing:
  - "multi-channel to mono"
  - "16 kHz sampling rate"
  - "voice activity detection"
  - "speaker diarization"
  - "ASR"
  - "temporal ASR/diarization alignment"

ppt_stack:
  conversion: "LibreOffice"
  extraction: "python-pptx"
  embeddings: "sentence-transformers"

ppt_preprocessing:
  - "legacy .ppt to .pptx"
  - "slide text/structure extraction"
  - "text preprocessing"
  - "semantic embedding generation"
  - "alignment with discussion"

fusion:
  methods:
    - "temporal alignment"
    - "semantic alignment"

resources:
  raw_audio_storage: ">80 GB"
  additional_storage:
    - "processed audio"
    - "transcripts"
    - "speaker diarization outputs"
    - "extracted presentations"
    - "semantic embeddings"

compute:
  expensive_components:
    - "ASR"
    - "speaker diarization"
  strategy:
    - "offline modular processing"
    - "cache intermediate outputs"
    - "reuse outputs"
    - "int8 ASR quantization"

risks:
  - issue: "legacy .ppt format"
    mitigation: ".ppt -> .pptx using headless LibreOffice"
  - issue: "computational bottlenecks"
    mitigation: "modular pipeline + cached intermediate JSON outputs"
  - issue: "noise/reverberation/overlapping speech"
    mitigation: "VAD + speaker-aware temporal overlap alignment"
  - issue: "audio/PPT temporal or semantic misalignment"
    mitigation: "preserve timestamps + textual/semantic slide representations"

eda:
  type: "modality-specific preprocessing/data exploration"
  audio:
    observations:
      - "headset and room-array sources differ"
      - "noise/reverberation/overlapping speech may occur"
      - "meeting durations vary"
    normalized_format:
      channels: "mono"
      sample_rate: "16 kHz"
  dialogue_acts:
    total: 116357
    distribution:
      Inform: "33484 (28.8%)"
      Backchannel: "21910 (18.8%)"
      Assess: "21391 (18.4%)"
      Fragment: "16796 (14.4%)"
      Suggest: "9391 (8.1%)"
      Stall: "8459 (7.3%)"
      Elicit-Inform: "4240 (3.6%)"
      Other: "686 (0.6%)"
  decisions:
    - "decision annotations available as reference data"
    - "decision progression should be interpreted in conversational context"
  presentations:
    - "legacy .ppt can require conversion"
    - "slide content should be extracted and embedded"
  cross_modal:
    - "audio -> speech segments -> speaker information -> transcript"
    - "presentation -> slide content -> semantic representation"
    - "link using temporal + semantic information"

critical_rules_for_future_llms:
  - "Do not assume video is part of current implementation"
  - "Do not rely on isolated keywords for decision/influence analysis"
  - "Do not discard timestamps"
  - "Do not repeatedly recompute expensive audio processing"
  - "Convert legacy presentations before python-pptx processing"
  - "Keep multimodal alignment as a core requirement"
  - "Treat unspecified implementation details as design decisions, not report facts"
```

---

# 47. End of Report 2 README

This README is a faithful implementation-oriented restructuring of the second report. It is intended to function as **persistent project context for LLMs and developers**, especially when building the dataset pipeline, preprocessing modules, audio/PPT fusion, and later decision/influence-analysis components.
