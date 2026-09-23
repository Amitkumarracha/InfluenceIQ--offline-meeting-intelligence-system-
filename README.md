# Multimodal Meeting Intelligence System

## 1. Project Overview
The Multimodal Meeting Intelligence System is an offline, GPU-accelerated pipeline designed to extract structured business and social intelligence from raw meeting recordings and presentation slides. It processes temporal audio streams and static visual assets (PPTs) to construct a directed interaction graph, enabling the deterministic extraction of decisions, participant interactions, and influence rankings without relying on hallucinatory LLMs.

### Core Capabilities
* **Offline Execution:** Uses local, open-source models (faster-whisper, pyannote.audio, sentence-transformers) to ensure complete data privacy and zero API costs.
* **Multimodal Fusion:** Maps spoken dialogue to specific presentation slides using semantic embeddings.
* **Deterministic Intelligence:** Algorithmically derives participant roles (decision-maker, objector) and influence scores based on meeting interaction graphs.
* **Resilience:** Includes aggressive caching for intermediate steps (VAD, Diarization, Embeddings) to prevent data loss and save compute time during interruptions.

---

## 2. System Architecture & Pipeline Phases

The system processes data in 11 sequential phases:

1. **Audio Preprocessing:** Normalizes raw `.wav` audio.
2. **Voice Activity Detection (VAD):** Identifies speech segments using Silero VAD.
3. **Speaker Diarization:** Clusters speech by speaker identity using `pyannote/speaker-diarization-3.1`.
4. **Automatic Speech Recognition (ASR):** Transcribes audio using `faster-whisper` (GPU-accelerated, FP16).
5. **PPT Extraction & Embeddings:** Extracts text/images from `.pptx` and computes semantic vectors using `all-MiniLM-L6-v2`.
6. **Semantic Alignment:** Maps audio transcript segments to relevant slides based on temporal and semantic proximity.
7. **Event Extraction:** Classifies multimodal segments into interaction events (e.g., questions, proposals).
8. **Evidence Linking:** Links events to specific evidence (transcripts/slides).
9. **Decision Reconstruction:** Algorithmically pieces together events to identify confirmed/rejected decisions.
10. **Interaction Analysis:** Constructs a directed graph of who responded to whom (agreements, objections).
11. **Influence Scoring:** Runs PageRank-style algorithms on the interaction graph to rank participant influence.

---

## 3. Environment Setup & Prerequisites

### Hardware & OS
* **OS:** Ubuntu Linux
* **Python:** 3.10
* **Compute:** NVIDIA GPU (e.g., RTX A4000) recommended.
* **CUDA:** System CUDA 13 (with CUDA 12 compatibility libraries available).

### Installation
1. **Create and Activate Virtual Environment:**
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment Variables:**
   Copy `.env.example` to `.env` and add your Hugging Face Token (required for Pyannote 3.1):
   ```bash
   cp .env.example .env
   # Edit .env to add: HF_TOKEN=your_token_here
   ```

### Important System Quirks (CUDA 12 vs 13)
`faster-whisper` (via `CTranslate2`) natively requests CUDA 12 libraries (`libcublas.so.12`). If the host system runs CUDA 13, you must point the environment to the CUDA 12 compatibility libraries before running the pipeline:
```bash
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH"
```

---

## 4. Execution Commands

*Run all commands from the project root with the `.venv` activated.*

### Phase A: Audio Pipeline (Batch Processing)
This command processes all audio files, utilizing smart caching to skip previously processed meetings.
```bash
source .venv/bin/activate
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH"

python3 run_small_chunk.py $(python3 - <<'PY'
import glob, os
ids = [os.path.splitext(os.path.basename(f))[0] for f in sorted(glob.glob("data/raw/audio/*.wav"))]
print(" ".join(ids))
PY
)
```

### Phase B: Presentation (PPT) Pipeline
Extracts slides and builds semantic embeddings. We use `HF_HUB_OFFLINE=1` to force the `sentence-transformers` library to use the locally cached model, avoiding SSL timeout issues on restricted networks.
```bash
source .venv/bin/activate
export HF_HUB_OFFLINE=1

for meeting_dir in data/raw/ppt/*/; do
    meeting_id=$(basename "$meeting_dir")
    pptx=$(ls "$meeting_dir"*.pptx 2>/dev/null | head -1)
    if [ -n "$pptx" ]; then
        echo "===== Processing Slides: $meeting_id ====="
        python3 scripts/run_pipeline.py --ppt "$pptx" --meeting-id "$meeting_id"
    fi
done
```

### Phase C: Intelligence Pipeline
Fuses audio and slides to construct the interaction graph and influence metrics.
```bash
source .venv/bin/activate
export HF_HUB_OFFLINE=1

# 1. Align transcripts with slides
for transcript in data/processed/audio/*_transcript.json; do
    mid=$(basename "$transcript" _transcript.json)
    slides="data/processed/slides/${mid}_slides.json"
    [ -f "$slides" ] && python3 scripts/run_pipeline.py --transcript "$transcript" --slides "$slides" --meeting-id "$mid"
done

# 2. Extract events
for mm in data/processed/alignment/*_multimodal.json; do
    mid=$(basename "$mm" _multimodal.json)
    python3 scripts/run_pipeline.py --multimodal "$mm" --meeting-id "$mid"
done

# 3. Reconstruct decisions
for ev in data/processed/events/*_events.json; do
    mid=$(basename "$ev" _events.json)
    evi="data/processed/events/${mid}_evidence.json"
    [ -f "$evi" ] && python3 scripts/run_pipeline.py --events "$ev" --evidence "$evi" --meeting-id "$mid"
done

# 4. Analyze interactions
for dec in data/processed/decisions/*_decisions.json; do
    mid=$(basename "$dec" _decisions.json)
    ev="data/processed/events/${mid}_events.json"
    evi="data/processed/events/${mid}_evidence.json"
    [ -f "$ev" ] && [ -f "$evi" ] && python3 scripts/run_pipeline.py --decisions "$dec" --events "$ev" --evidence "$evi" --meeting-id "$mid"
done

# 5. Calculate influence
for inter in data/processed/interactions/*_interactions.json; do
    mid=$(basename "$inter" _interactions.json)
    dec="data/processed/decisions/${mid}_decisions.json"
    ev="data/processed/events/${mid}_events.json"
    evi="data/processed/events/${mid}_evidence.json"
    [ -f "$dec" ] && [ -f "$ev" ] && [ -f "$evi" ] && python3 scripts/run_pipeline.py --interactions "$inter" --decisions "$dec" --events "$ev" --evidence "$evi" --meeting-id "$mid"
done
```

### Phase D: Report Generation
Compiles all JSON data into human-readable Markdown, HTML, and CSV formats.
```bash
source .venv/bin/activate
export HF_HUB_OFFLINE=1

for inf in data/processed/influence/*_influence.json; do
    mid=$(basename "$inf" _influence.json)
    echo "===== Generating Report: $mid ====="
    python3 scripts/generate_report.py --meeting-id "$mid" --format json markdown html csv
done
```

---

## 5. Output Directory Structure
After execution, the intelligence outputs are cleanly organized:

* `data/processed/audio/` - `.json` and `.txt` transcripts with speaker timestamps.
* `data/processed/slides/` - Extracted PPT text, image mappings, and `.npy` vector embeddings.
* `data/processed/alignment/` - Fused timelines of which slide was discussed when.
* `data/processed/interactions/` & `decisions/` - Graph data of social dynamics.
* `outputs/reports/` - Final compiled outputs (Markdown, HTML, CSV). **Use these for frontend displays and analysis.**

---

## 6. Next Steps: Frontend & Deployment

To convert this backend engine into a fully deployed web application:

1. **Frontend Dashboard:** Use the generated data in `outputs/reports/` as a "mock database" to build a React, Streamlit, or Gradio dashboard immediately without waiting for GPU processing.
2. **API Layer:** Wrap `scripts/run_pipeline.py` in a FastAPI server (`app.py`) that exposes endpoints like `/upload-audio` and `/get-influence-score`.
3. **Containerization:** Create a `Dockerfile` that installs `requirements.txt`, sets the `HF_HUB_OFFLINE=1` and `LD_LIBRARY_PATH` variables, and runs the FastAPI server.
4. **Packaging for Deployment:** Zip the codebase for transfer to a production server (omitting heavy raw datasets):
   ```bash
   zip -r full_project_deployment.zip src/ scripts/ config.yaml requirements.txt .env.example run_small_chunk.py README.md data/processed/ outputs/reports/
   ```
