# Evaluation results — 19 October 2026

These are measured pilot results, not full-corpus benchmarks or deployment certification.

## Speaker calibration

Development: two 120-second AMI excerpts; held-out: two different meeting groups. Minimum pooled development DER selected threshold 0.9. Full protocol and individual results are in `evaluation/audio_protocol.json` and `evaluation/ami_*.json`.

| Meeting | Threshold | Groups | Reference speakers | DER |
|---|---|---|---|---|
| IS1001b | 0.5 | 12 | 4 | 46.01% |
| TS3007d | 0.5 | 13 | 4 | 83.54% |
| IS1001b | 0.9 | 4 | 4 | 26.90% |
| TS3007d | 0.9 | 7 | 4 | 56.01% |


The 42-minute private recording fell from 139 groups to 37 in a separate diagnostic. Its true count remains unknown. This reduces fragmentation but does not establish correct attribution. Original saved meeting data was not overwritten. Diagnostic processing took 1047.6 seconds with other evaluation workloads active; peak process RSS was 1108.2 MiB.

## Speech recognition

| Model | Corpus | Samples | WER | CER |
|---|---|---|---|---|
| small | hindi | 8 | 50.96% | 20.09% |
| small | hinglish | 8 | 66.13% | 50.00% |
| medium | hindi | 8 | 37.02% | 14.98% |
| medium | hinglish | 8 | 57.26% | 52.25% |


English AMI held-out WER: IS1001b 41.59%; TS3007d 81.00%. Distant audio, overlap, spelling and reference conventions matter. Hindi/Hinglish measurements use eight samples each. Hinglish samples are consecutive technical-lecture segments; some hypotheses include neighbouring speech, so boundary/reference mismatch requires manual audit. Keep these strict scores; do not silently fix references after seeing predictions. Medium improves this small pilot but does not deliver reliable accuracy. The small default remains a latency trade-off.

## Functional evidence

Final complete suite: 560 passed, seven dependency warnings. Earlier focused metric tests: 89 passed. Final regression log is `evaluation/final_pytest.log`. Browser test verifies synthetic microphone previews, recovery, pause/resume, uploads, search, edits, evidence and responsive layouts. Real local preview inference is recorded separately in `evaluation/live_preview_real_model.json`. Android Java tests and APK build completed; no physical-phone accuracy or thermal certification is implied.

## Downstream evaluation

Eight ablation variants ran against the existing long meeting. Human influence rankings and event/decision/slide references are missing, so those accuracy metrics remain unavailable. The outputs under `evaluation/downstream/` include private source-derived content: review before sharing. Score differences are sensitivity analysis, not proof of improved influence accuracy.

## Limits

No training/fine-tuning was performed. Public dataset provenance and SHA-256 values are in the two manifests. Neither benchmark contamination nor generalisation to Indian meetings has been ruled out. Timing with concurrent evaluation jobs is not a controlled latency comparison. Full recordings, additional languages, independent human labels, physical Android tests and confidence intervals remain future validation.
