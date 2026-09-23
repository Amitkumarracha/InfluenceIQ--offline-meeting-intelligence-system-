# Complete Project Execution Guide: Multimodal Meeting-Intelligence System

This document contains all step-by-step instructions and commands needed to process the dataset and complete the project from start to finish on your Linux machine with GPU acceleration.

---

## Table of Contents
1. [Prerequisites & Environment Setup](#phase-0--environment-setup)
2. [Data Ingestion & Preparation](#phase-1--data-preparation)
3. [Audio Pipeline (Preprocess, VAD, Diarization, ASR)](#phase-2--audio-pipeline)
4. [Presentation & Slide Pipeline](#phase-3--presentation--slide-pipeline)
5. [Cross-Modal Audio–PPT Alignment](#phase-4--cross-modal-alignment)
6. [Meeting Analysis (Events, Decisions, Interactions, Influence)](#phase-5--meeting-intelligence-analysis)
7. [Report Generation](#phase-6--final-report-generation)
8. [Evaluation & Ablation (Optional)](#phase-7--evaluation--benchmarks-optional)

---

## Phase 0 — Environment Setup

Run these commands in your project root directory (`/home/CL502-12/MAI Project/`):

```bash
# 1. Recreate fresh Linux virtual environment
rm -rf .venv
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** Always ensure the virtual environment is active by running:
> ```bash
> source .venv/bin/activate
> ```

---

## Phase 1 — Data Preparation

### 1. Audio Data (Symlink Array1-01 room microphone audio)
```bash
mkdir -p data/raw/audio

for wav in AMI_dataset/audio/Array1-01/*/audio/*.wav; do
    meeting_id=$(basename $(dirname $(dirname "$wav")))
    ln -sf "$(realpath "$wav")" "data/raw/audio/${meeting_id}.wav"
done

# Verify
ls -l data/raw/audio | head -10
```

### 2. Presentation Data (.ppt to .pptx Conversion)
```bash
mkdir -p data/raw/ppt

for ppt in AMI_dataset/amicorpus/*/shared-doc/*.ppt; do
    meeting_id=$(basename $(dirname $(dirname "$ppt")))
    mkdir -p "data/raw/ppt/${meeting_id}"
    soffice --headless --convert-to pptx --outdir "data/raw/ppt/${meeting_id}" "$ppt"
done

# Verify
ls -l data/raw/ppt/ES2002a/
```

---

## Phase 2 — Audio Pipeline (GPU Accelerated)
*Runs: Audio standardization (16kHz mono) $\rightarrow$ Silero VAD $\rightarrow$ Pyannote Speaker Diarization (CUDA) $\rightarrow$ faster-whisper ASR (CUDA float16)*

```bash
source .venv/bin/activate

for wav in data/raw/audio/*.wav; do
    meeting_id=$(basename "$wav" .wav)
    echo "=================================================="
    echo "Processing Audio Pipeline: $meeting_id"
    echo "=================================================="
    python3 scripts/run_pipeline.py \
        --audio "$wav" \
        --meeting-id "$meeting_id"
done
```
* **Output directory:** `data/processed/audio/` (`*_processed.wav`, `*_vad.json`, `*_diarization.json`, `*_transcript.json`, `*_transcript.txt`)
* **Expected runtime on RTX A4000:** ~1.0 to 1.5 minutes per meeting (~3 to 3.5 hours for all 169 meetings).

---

## Phase 3 — Presentation & Slide Pipeline
*Runs: Slide text/tables/notes extraction $\rightarrow$ Sentence-Transformers (`all-MiniLM-L6-v2`) semantic embeddings*

```bash
source .venv/bin/activate

for meeting_dir in data/raw/ppt/*/; do
    meeting_id=$(basename "$meeting_dir")
    pptx=$(ls "$meeting_dir"*.pptx 2>/dev/null | head -1)
    if [ -n "$pptx" ]; then
        echo "=================================================="
        echo "Processing Slides: $meeting_id"
        echo "=================================================="
        python3 scripts/run_pipeline.py \
            --ppt "$pptx" \
            --meeting-id "$meeting_id"
    fi
done
```
* **Output directory:** `data/processed/slides/` (`*_slides.json`, `*_embeddings.npy`)

---

## Phase 4 — Cross-Modal Alignment
*Runs: Temporal and semantic alignment linking transcript segments to presented slides*

```bash
source .venv/bin/activate

for transcript in data/processed/audio/*_transcript.json; do
    meeting_id=$(basename "$transcript" _transcript.json)
    slides="data/processed/slides/${meeting_id}_slides.json"
    if [ -f "$slides" ]; then
        echo "=================================================="
        echo "Running Audio-PPT Alignment: $meeting_id"
        echo "=================================================="
        python3 scripts/run_pipeline.py \
            --transcript "$transcript" \
            --slides "$slides" \
            --meeting-id "$meeting_id"
    fi
done
```
* **Output directory:** `data/processed/alignment/` (`*_alignment.json`, `*_multimodal.json`)

---

## Phase 5 — Meeting Intelligence Analysis

### 1. Event & Evidence Extraction (Phase 8)
*Extracts proposals, questions, objections, agreements, and links evidence.*
```bash
source .venv/bin/activate

for mm in data/processed/alignment/*_multimodal.json; do
    meeting_id=$(basename "$mm" _multimodal.json)
    echo "Event Extraction: $meeting_id"
    python3 scripts/run_pipeline.py \
        --multimodal "$mm" \
        --meeting-id "$meeting_id"
done
```
* **Output directory:** `data/processed/events/` (`*_events.json`, `*_evidence.json`)

### 2. Decision Reconstruction (Phase 9)
*Reconstructs decision clusters and lineage trees.*
```bash
source .venv/bin/activate

for events in data/processed/events/*_events.json; do
    meeting_id=$(basename "$events" _events.json)
    evidence="data/processed/events/${meeting_id}_evidence.json"
    if [ -f "$evidence" ]; then
        echo "Decision Reconstruction: $meeting_id"
        python3 scripts/run_pipeline.py \
            --events "$events" \
            --evidence "$evidence" \
            --meeting-id "$meeting_id"
    fi
done
```
* **Output directory:** `data/processed/decisions/` (`*_decisions.json`, `*_decision_graph.json`)

### 3. Interaction Analysis (Phase 10)
*Constructs interaction network graphs across participants.*
```bash
source .venv/bin/activate

for decisions in data/processed/decisions/*_decisions.json; do
    meeting_id=$(basename "$decisions" _decisions.json)
    events="data/processed/events/${meeting_id}_events.json"
    evidence="data/processed/events/${meeting_id}_evidence.json"
    if [ -f "$events" ] && [ -f "$evidence" ]; then
        echo "Interaction Analysis: $meeting_id"
        python3 scripts/run_pipeline.py \
            --decisions "$decisions" \
            --events "$events" \
            --evidence "$evidence" \
            --meeting-id "$meeting_id"
    fi
done
```
* **Output directory:** `data/processed/interactions/` (`*_interactions.json`, `*_interaction_graph.json`)

### 4. Participant Influence Ranking (Phase 11)
*Calculates weighted influence scores and ranks participants.*
```bash
source .venv/bin/activate

for interactions in data/processed/interactions/*_interactions.json; do
    meeting_id=$(basename "$interactions" _interactions.json)
    decisions="data/processed/decisions/${meeting_id}_decisions.json"
    events="data/processed/events/${meeting_id}_events.json"
    evidence="data/processed/events/${meeting_id}_evidence.json"
    if [ -f "$decisions" ] && [ -f "$events" ] && [ -f "$evidence" ]; then
        echo "Influence Analysis: $meeting_id"
        python3 scripts/run_pipeline.py \
            --interactions "$interactions" \
            --decisions "$decisions" \
            --events "$events" \
            --evidence "$evidence" \
            --meeting-id "$meeting_id"
    fi
done
```
* **Output directory:** `data/processed/influence/` (`*_influence.json`, `*_baselines.json`)

---

## Phase 6 — Final Report Generation
*Generates formatted dossiers in HTML, Markdown, CSV, and JSON.*

```bash
source .venv/bin/activate

for influence in data/processed/influence/*_influence.json; do
    meeting_id=$(basename "$influence" _influence.json)
    echo "Generating Report: $meeting_id"
    python3 scripts/generate_report.py \
        --meeting-id "$meeting_id" \
        --format json markdown html csv
done
```
* **Output directory:** `outputs/reports/` (`<meeting_id>_report.html`, `<meeting_id>_report.md`, `<meeting_id>_report.json`, `<meeting_id>_report.csv`)

---

## Phase 7 — Evaluation & Benchmarks (Optional)
*Evaluates against ground truth and runs ablation studies.*

```bash
source .venv/bin/activate

for influence in data/processed/influence/*_influence.json; do
    meeting_id=$(basename "$influence" _influence.json)
    echo "Running Evaluation: $meeting_id"
    python3 scripts/run_evaluation.py \
        --meeting-id "$meeting_id" \
        --ablation
done
```
* **Output directory:** `outputs/evaluation/` (`*_metrics.json`, `*_ablation.json`, `comparison.csv`)

---

## Quick Reference: Running in Background (`nohup`)
If you want to run the full audio pipeline overnight without keeping the terminal open:

```bash
source .venv/bin/activate

nohup bash -c '
for wav in data/raw/audio/*.wav; do
    meeting_id=$(basename "$wav" .wav)
    python3 scripts/run_pipeline.py --audio "$wav" --meeting-id "$meeting_id"
done
' > audio_pipeline.log 2>&1 &
```

* Check live progress:
  ```bash
  tail -f audio_pipeline.log
  ```
* Check process:
  ```bash
  ps aux | grep run_pipeline
  ```

