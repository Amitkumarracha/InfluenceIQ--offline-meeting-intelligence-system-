# Training, annotation and multimodal research

Status: 7 October 2026. Read this with [19 — Android delivery](../validation/19_ANDROID_SPEAKERS_FUSION_AND_VALIDATION.md) and [21 — Deployment](../operations/21_OFFLINE_AND_WORKSTATION_DEPLOYMENT.md). No new research model has been trained on real labelled meeting data in this update.

## Is training required?

Training from scratch is not required to run the current application. ASR, speaker segmentation, speaker embeddings and the website's semantic text embeddings use pretrained models. Event rules, candidate decision lineage, TF-IDF matching and the prototype influence weights are deterministic analysis components. Their implementation does not establish accuracy.

| Component | Current implementation | What additional training would require |
| --- | --- | --- |
| ASR | Website: faster-whisper small; Android: imported multilingual whisper.cpp GGML model | Consented Hindi/English/Hinglish audio paired with independently checked transcripts; held-out speakers and recording conditions; export a compatible inference model after fine-tuning |
| Speaker separation | Pretrained ONNX segmentation + ERes2Net embeddings, clustering | Labelled speaker turns and overlap; first calibrate the clustering threshold/count using validation DER, then consider domain adaptation |
| Language | Restricted Hindi/English dominant-language detection; website also reports observed script/mix clues | Natural code-switching recordings and token/span language labels for a dedicated detector; dominant-language detection alone does not prove within-sentence switching accuracy |
| Event types / roles | English/Hindi/Hinglish phrase rules; roles describe observed contributions | Human-labelled event spans, speaker attribution and contribution roles; compare a small discriminative classifier against the rules |
| Audio–PPT fusion | Website: semantic embedding matching with optional timing, or TF-IDF; Android: native slide text TF-IDF | Human passage-to-slide labels, negatives, actual slide display timing if using temporal fusion, and separate test presentations |
| Visual fusion | Slide images/metadata are available, but visual embeddings/OCR are not implemented in this delivery | Slide image/text pairs and an actual image encoder/OCR implementation; evaluate diagram/image-only cases separately |
| Influence | Seven weighted decision-linked feature categories, weights are unvalidated | Independent participant/decision influence ratings, source-event annotations and agreement between raters; train and test on disjoint complete meetings |

The speaker framework supports pretrained Android diarization rather than requiring a new phone-specific model. Model provenance is linked in [the official Sherpa Android diarization documentation](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/apk.html). The application-specific questions are domain quality, model calibration and evaluation.

## What makes this multimodal?

Audio supplies speech timing, speaker turns and recognized text. A presentation supplies a separate source of slide text. Alignment connects the two sources; slide-grounded contributions then enter influence analysis. This is audio–presentation fusion implemented through text representations and observed timing. It qualifies as a multimodal processing pipeline; it is not a jointly trained audio/image neural model.

For a paper, describe the implemented representation precisely: **audio transcript–native PPT text alignment**. Android uses lexical TF-IDF similarity, no visual encoder, no OCR and no slide-display temporal input. The website's optional temporal fusion only uses supplied timing windows; it does not recover slide transitions from an audio file.

The older project already contained alignment, event/evidence reasoning and weighted influence. Do not claim those inherited algorithms as newly invented. New contributions could be investigated in bilingual adaptation, validated fusion/influence learning, evidence traceability, offline deployment and measured device/server tradeoffs. Establish novelty against related work and report ablations before claiming an improvement.

## Implemented training entry point

[`scripts/train_influence_weights.py`](../../scripts/train_influence_weights.py) learns the seven nonnegative weights constrained to sum to one. It minimizes squared error against human influence ratings. It uses the project's existing NumPy/SciPy dependencies, runs offline on CPU, and writes a portable JSON research artifact rather than a pickle or an automatically installed app model.

The trainer requires at least two training meetings, one validation meeting and one test meeting. These are **execution minimums**, not a defensible publication sample size. Entire meetings must stay in one split, each participant occurs once per meeting, and every feature must be finite/nonnegative. All participants must be included so per-meeting max-normalization matches inference. Label sources must be human; a model output must not serve as its own reference.

One input row has this structure. Values are illustrative schema values, not measured research data:

```json
{
  "meeting_id": "consented_meeting_001",
  "participant": "SPEAKER_00",
  "split": "train",
  "label_source": "human",
  "human_score": 0.75,
  "features": {
    "proposal": 2,
    "evidence": 1,
    "objection": 0,
    "revision": 1,
    "decision": 1,
    "interaction": 1,
    "slide_grounding": 2
  }
}
```

Put independent ratings in a private JSONL manifest, then run:

```bash
.venv/bin/python scripts/train_influence_weights.py \
  --manifest /absolute/path/to/human_influence_annotations.jsonl \
  --output outputs/training/influence_weights.json
```

If raters use a 1–5 scale, agree the rubric first and document the conversion to [0,1], for example `(rating - 1) / 4`. Retain annotator identities/pseudonyms, original ratings, adjudication and disagreement statistics separately. The trainer checks the manifest's declared label source; it cannot verify that someone actually annotated the meeting.

Android raw feature keys already match the short keys above. Website report keys require mapping:

| Training key | Website `raw_features` key |
| --- | --- |
| proposal | proposal_contribution |
| evidence | evidence_contribution |
| objection | objection_contribution |
| revision | revision_contribution |
| decision | decision_contribution |
| interaction | interaction_contribution |
| slide_grounding | slide_grounded_contribution |

The Android candidate lineage differs from the Python evidence/decision graph. Use separate manifests and record the extractor version. Do not combine their feature counts as if they came from one method.

Output includes the manifest SHA-256, training meeting IDs, learned weights, separate train/validation/test MSE, per-meeting Spearman and Kendall rankings, prototype-weight comparisons and seven feature-removal ablations. Tied/insufficient rankings are marked unavailable. Feature-removal ablations zero one contribution without renormalizing the remaining weights. No output is installed automatically; inspect held-out evidence before updating the application configuration.

## Annotation and experiment order

1. Measure current ASR WER and speaker DER on real recordings. Separate English, Hindi, Hinglish, noise, overlap and microphone conditions. Use human references, not the current transcript as ground truth.
2. Label events, action candidates, decisions, speaker contributions, source links and passage-to-slide matches. Mark uncertainty and absent decisions explicitly. An event's speaker must be verified before using it for influence labels.
3. Freeze meeting/team/speaker/site splits and the test set. Tune speaker clustering, match thresholds and rules on validation data only.
4. Compare audio-only influence, PPT lexical fusion, semantic fusion and any timing/visual extensions using identical inputs. Add speaking-time and event-count baselines. The new trainer compares learned and prototype weights; the existing evaluation framework provides other baselines.
5. Train small event/role classifiers or fusion weights where validation shows a measurable need. Fine-tune ASR/speaker encoders only after identifying systematic domain errors and obtaining enough labelled examples.
6. Report held-out WER, DER, event/decision/alignment F1, influence rank correlation, annotation agreement and phone/server latency/memory. Include uncertainty and adverse cases. Test data must not be used to select weights.

A GPU is useful for neural fine-tuning and faster ASR inference. It is unnecessary for this seven-feature weight trainer. Hosting and training are separate jobs: a deployed server can run existing pretrained models without training anything new.

## Still missing

There is no independently labelled natural Hinglish evaluation/training set supplied for this project, no new event/role neural classifier, no visual-slide encoder, no jointly trained multimodal network and no real learned weights artifact. Synthetic contract tests verify the training code and leakage rejection; they are not journal results. The submitted report and older snapshot remain intact.
