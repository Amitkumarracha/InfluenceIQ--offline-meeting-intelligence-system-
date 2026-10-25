# InfluenceIQ — keep this beside your presentation

**Opening:** “InfluenceIQ converts meeting recordings into timestamped, speaker-attributed transcripts and source-linked suggestions about discussions, actions, decisions, and participant contributions. Optional presentation documents add context. A person reviews the candidates against the recording.”

**Name:** Influence = contribution to decision discussion; IQ = intelligent assistance. This is a branding explanation, not a personal intelligence test. Meet IQ is another application label in the same project.

**Flow:** Browser capture/upload → FastAPI validation/account/queue → FFmpeg 16 kHz mono PCM16 → Whisper draft words/times → Sherpa-ONNX speaker intervals → word attribution → optional PPT extraction/alignment → events/evidence → decision candidates/interactions → weighted contribution estimates → saved report and review.

**Separate branch:** The trained English discussion detector suggests passages. It does not directly create final decisions or the default influence score.

**Tech:** React/Vite + Axios + browser MediaRecorder/Web Audio/IndexedDB; Python/FastAPI/Uvicorn; SQLAlchemy/SQLite; bcrypt/JWT; faster-whisper/CTranslate2; Sherpa-ONNX; python-pptx; MiniLM/scikit-learn. Android independently uses Java/C++/JNI, whisper.cpp, and native speaker/TF-IDF processing.

**Modalities:** Audio and presentation documents. Fusion mainly compares audio-derived transcript text with extracted slide text. No trained raw acoustic-image network. Without PPT, the application follows its audio-only path.

**Fusion:** `C = (wt × temporal_overlap + ws × semantic_cosine) / (wt + ws)`. Defaults: 0.5/0.5, top three candidates, threshold 0.3. Missing timing → semantic-only. TF-IDF replaces MiniLM for a run; it is not averaged with MiniLM. Weak match → `NO_CONFIDENT_SLIDE`.

**Influence:** Normalize each feature by its meeting maximum, then take the weighted sum. Weights: proposal .15, evidence .20, objection .15, revision .20, decision .15, interaction .05, slide grounding .10. Zero may reflect missed evidence. A top score need not equal one. Scores are not causal impact or personal performance ratings.

**Learned discussion model:** Word + character TF-IDF, ±40 units of context; 75% forest + 25% logistic; ±5 smoothing; threshold 0.35774. Training/development/historical AMI split: 29/6/12 meetings. Pretrained speech/embedding models remain frozen.

**Numbers:** 656 software tests passed. Discussion: 53.54% F1, 39.94% precision, 81.18% recall on human reference acts. Latest GAP ranking: 68.93% pairwise accuracy, exploratory outcome-alignment task. Real functional run: 90 seconds of speech, two audio parts/two decks/four speakers → 41.84 seconds recorded processing; unchanged cached rerun → 0.60 seconds. These are different metrics/conditions.

**Fusion result:** Constructed 24-case top-1: temporal 50%, semantic 83.33%, hybrid 66.67%. Real untimed deck: 39/1,008 passages linked, 3.87% coverage, no accuracy reference. Do not claim universal hybrid superiority.

**Demo:** Open completed meeting → play a transcript timestamp → inspect speaker label → open a decision's sources → review an action → inspect influence breakdown → show slide links → export. Website: http://127.0.0.1:8001.

**Three answers to remember:** “A source pointer enables inspection; it does not prove correctness.” “Discussion, final decision, and causal influence are different tasks.” “Local deployment works; a public frontend alone still needs our Python models, API, and persistent storage.”
