# Research contribution, novelty boundaries, and related work

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Three different comparisons

1. **Current versus supplied older code:** a verifiable implementation difference documented in [01](01_PROJECT_HISTORY_AND_COMPARISON.md) and [14](../validation/14_FILE_BY_FILE_COMPARISON.md).
2. **Whole MAI system versus published research:** requires a literature comparison and matched empirical evaluation. A method inherited from our older folder can still belong to the overall MAI design, but cannot be presented as newly added during laptop migration.
3. **Current versus alternative systems on a dataset:** requires rerunning both methods with matching inputs, labels, splits, settings, and resource accounting. A feature comparison is not an empirical superiority result.

This audit supplies a source-backed contribution inventory and a preliminary primary-source literature check. It does not establish “first”, state of the art, or exhaustive global novelty.

## Established components to credit

Whisper supplies pretrained multilingual speech recognition; this repository performs local inference and has no inspected training/fine-tuning implementation. Credit [Radford et al., Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356).

CTranslate2/int8 inference is functionality of the faster-whisper runtime, not an original quantization algorithm in MAI. Credit the [faster-whisper project](https://github.com/SYSTRAN/faster-whisper). Whisper.cpp provides the phone inference engine; credit its [upstream project](https://github.com/ggml-org/whisper.cpp).

Sentence embeddings and cosine similarity are established methods. Credit [Reimers and Gurevych, Sentence-BERT (2019)](https://aclanthology.org/D19-1410/), and distinguish the locally used [all-MiniLM-L6-v2 checkpoint](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from the general SBERT paper.

AMI is a pre-existing corpus, not a new dataset collected by this project. Credit its [official corpus page](https://groups.inf.ed.ac.uk/ami/corpus/) and [Carletta's corpus overview](https://groups.inf.ed.ac.uk/ami/corpus/overview.shtml). The local benchmark has a much narrower sample than the full corpus.

## Primary research comparisons

| Work | Verified subject | Relevance to MAI | What this does not prove |
| --- | --- | --- | --- |
| [Fernández et al., Modelling and Detecting Decisions in Multi-party Dialogue, SIGDIAL 2008](https://aclanthology.org/W08-0125/) | Meeting decision modeling/detection | Decision extraction is already a research topic; compare representation, context, annotation, and evaluation | That our heuristic lineage is uniquely novel or more accurate |
| [Zhong et al., QMSum, NAACL 2021](https://aclanthology.org/2021.naacl-main.472/) | Query-based meeting summarization with relevant-span selection | Our retrieved-passage Q&A belongs to an established locate/select-and-summarize family | That local lexical retrieval plus quote checking solves the benchmark |
| [Popescu-Belis et al., Accessing a Large Multimodal Corpus Using an Automatic Content Linking Device, 2009](https://www.research.ed.ac.uk/en/publications/accessing-a-large-multimodal-corpus-using-an-automatic-content-li/) | Content linking/retrieval using a multimodal meeting corpus | Meeting/document linking has prior art; compare slide inputs, timestamps, abstention, and source propagation | That transcript–slide relevance by itself is original |
| [Reimers and Gurevych, Sentence-BERT, 2019](https://aclanthology.org/D19-1410/) | Semantically meaningful embeddings compared using cosine similarity | Establishes the content-similarity primitive | That MAI trained a new encoder |

These are starting references rather than a complete review through 2026. Read full methods and evaluation sections before claiming direct equivalence or entering their reported numbers into a comparison table. Expand the review around slide grounding, argument/decision graphs, speaker contribution, multilingual meetings, and resource-constrained offline deployment.

Do not compare published scores directly with our one-excerpt WER if datasets, microphone channels, normalization, overlap handling, or inference conditions differ.

## Contribution candidates and their current evidence

| Candidate contribution | Present implementation | Inherited or current extension? | Needed evidence |
| --- | --- | --- | --- |
| Source-linked decision lineage grounded in transcript/slide IDs | Event/evidence/decision/interaction chain | Primarily inherited | Independently annotated relations, matched transcript-only/grounded comparisons, error analysis |
| Decision-linked participant contribution beyond speaking volume | Seven-feature explainable weighted score | Primarily inherited; UNKNOWN/baseline fixes later | Human ranking rubric, rater agreement, validated speakers, Spearman/Kendall with meaningful baselines |
| Abstaining optional-time slide alignment | Semantic/temporal score plus NO_CONFIDENT_SLIDE | Inherited; TF-IDF option added | Real slide timing/relevance labels; timing/content/no-PPT ablations |
| Recoverable local meeting pipeline | Bounded decode/ASR, atomic keys/checkpoints/previews, complete runner | Current extension over supplied copy | Failure-injection/recovery study, recomputed work, time to first preview, isolated memory/time runs |
| Hindi/English/Hinglish candidate-rule coverage | Unicode-safe terms, phrases and blockers | Current extension | Human bilingual transcripts and event labels, balanced noise/code-switching strata |
| Evidence-linked local notes with checkpointed coverage | Local GGUF model, exact quotes/IDs, per-part retention | Current extension | Entailment, contradiction/unsupported rate, evidence validity, coverage, length/resource comparisons |
| Offline phone implementation with resumable review | Native Whisper/JNI/service and local exports | Current extension | Physical ARM64 phones, latency/energy/thermal/interruption tests, real bilingual WER |

Integration can be a legitimate systems contribution if the requirements, design, and evaluation are clear. Ordinary dependency installation, authentication fixes, responsive layouts, and model downloads are engineering work; they are not standalone algorithmic novelty claims.

## Research questions worth testing

- Does actual slide grounding improve decision-relation or contribution evaluation beyond transcript-only evidence, when the same verified speakers and transcripts are used?
- Does decision-linked feature scoring agree with independent human contribution judgments better than full-transcript speaking time and event-count baselines?
- Does the 120-second context/checkpoint profile improve recognition and time to first usable preview across meetings, and what total runtime/memory cost does it impose?
- Does quote-checked local note generation reduce unsupported statements without unacceptable loss of useful content?
- What offline bilingual quality and resource envelope can a laptop and physical phone achieve under realistic recording conditions?

These are proposed questions, not findings. Change the paper's central claim to fit the strongest completed experiment, rather than trying to claim novelty for every feature.

## Claim wording

Supported implementation wording:

> We implement a modular local meeting-intelligence prototype that propagates transcript and optional slide identifiers into heuristic decision lineage and interpretable contribution estimates. The laptop version supports content-addressed transcription recovery and optional source-quoted local notes; a separate Android prototype performs on-device transcription and rule-candidate review.

Supported limited result wording:

> In a preliminary experiment on a 600-second English AMI excerpt, the small/int8 120-second chunk profile produced 41.49% WER versus 45.84% for the 300-second profile, with longer total processing time. Broader multilingual and decision-level validation remains outstanding.

Unsupported wording at present includes “novel transformer fusion”, “PageRank influence”, “causal influence”, “validated Hindi/Hinglish accuracy”, “complete Android feature parity”, “all-meeting accuracy”, “70% RAM reduction”, “zero hallucinations”, and “state of the art”.
