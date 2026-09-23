#!/bin/bash

# Exit on any error
set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: ./scripts/process_new_meeting.sh <MEETING_ID> <AUDIO_WAV_PATH> [PPTX_PATH]"
    echo "Example: ./scripts/process_new_meeting.sh my_test_01 /path/to/audio.wav /path/to/slides.pptx"
    exit 1
fi

MEETING_ID=$1
AUDIO_FILE=$2
PPT_FILE=$3

echo "=================================================="
echo " Starting Multimodal Pipeline for: $MEETING_ID"
echo "=================================================="

source .venv/bin/activate
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:$LD_LIBRARY_PATH"
export HF_HUB_OFFLINE=1

echo "[1/7] Running Audio Pipeline (VAD, Diarization, ASR)..."
python3 scripts/run_pipeline.py --audio "$AUDIO_FILE" --meeting-id "$MEETING_ID"

if [ -n "$PPT_FILE" ] && [ -f "$PPT_FILE" ]; then
    echo "[2/7] Running PPT Pipeline..."
    python3 scripts/run_pipeline.py --ppt "$PPT_FILE" --meeting-id "$MEETING_ID"
    
    echo "[3/7] Aligning Audio with Slides..."
    python3 scripts/run_pipeline.py \
        --transcript "data/processed/audio/${MEETING_ID}_transcript.json" \
        --slides "data/processed/slides/${MEETING_ID}_slides.json" \
        --meeting-id "$MEETING_ID"
        
    MULTIMODAL_FILE="data/processed/alignment/${MEETING_ID}_multimodal.json"
else
    echo "[2/7 & 3/7] No PPT provided. Skipping PPT and Alignment phases."
    MULTIMODAL_FILE="data/processed/audio/${MEETING_ID}_transcript.json" # Fallback to just transcript if no slides
fi

echo "[4/7] Extracting Events..."
# Note: If no PPT, we might need a slight adjustment, but assuming the pipeline handles it or we just use transcript
if [ -f "$MULTIMODAL_FILE" ]; then
    python3 scripts/run_pipeline.py --multimodal "$MULTIMODAL_FILE" --meeting-id "$MEETING_ID"
fi

echo "[5/7] Reconstructing Decisions..."
EVENTS_FILE="data/processed/events/${MEETING_ID}_events.json"
EVIDENCE_FILE="data/processed/events/${MEETING_ID}_evidence.json"
if [ -f "$EVENTS_FILE" ]; then
    python3 scripts/run_pipeline.py --events "$EVENTS_FILE" --evidence "$EVIDENCE_FILE" --meeting-id "$MEETING_ID"
fi

echo "[6/7] Analyzing Interactions & Influence..."
DECISIONS_FILE="data/processed/decisions/${MEETING_ID}_decisions.json"
if [ -f "$DECISIONS_FILE" ]; then
    python3 scripts/run_pipeline.py --decisions "$DECISIONS_FILE" --events "$EVENTS_FILE" --evidence "$EVIDENCE_FILE" --meeting-id "$MEETING_ID"
    
    INTERACTIONS_FILE="data/processed/interactions/${MEETING_ID}_interactions.json"
    if [ -f "$INTERACTIONS_FILE" ]; then
        python3 scripts/run_pipeline.py --interactions "$INTERACTIONS_FILE" --decisions "$DECISIONS_FILE" --events "$EVENTS_FILE" --evidence "$EVIDENCE_FILE" --meeting-id "$MEETING_ID"
    fi
fi

echo "[7/7] Generating Final Report..."
python3 scripts/generate_report.py --meeting-id "$MEETING_ID" --format json markdown html csv

echo "=================================================="
echo " Finished! Report is available at: outputs/reports/${MEETING_ID}_report.md"
echo "=================================================="

