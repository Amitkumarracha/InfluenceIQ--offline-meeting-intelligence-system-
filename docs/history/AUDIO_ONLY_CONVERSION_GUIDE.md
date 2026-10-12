# Audio-Only Meeting Intelligence Conversion Guide

This guide outlines the step-by-step process for stripping out the PPT/Visual modality to pivot this system into an **Audio-Only Meeting Intelligence System** (ideal for phone calls, Zoom audio, or audio-only patent claims).

## 1. Architectural Changes Overview
In the current system, the pipeline looks like this:
`Audio -> Transcript` + `PPT -> Slides` ===> `Alignment` ===> `Events` ===> `Decisions/Influence`

In the Audio-Only version, the pipeline simplifies to:
`Audio -> Transcript` ===> `Events` ===> `Decisions/Influence`

---

## Step 1: Remove the PPT & Alignment Modules
You no longer need the presentation extraction, semantic embeddings, or alignment phases.

1. **Delete/Archive the PPT source code:**
   * Move the entire `src/ppt/` directory to an archive folder (or delete it).
   * Move `src/fusion/semantic_alignment.py` to an archive folder.
2. **Remove Dependencies:**
   * You can remove `sentence-transformers`, `python-pptx`, and any related visual processing libraries from your `requirements.txt`. This will make your Docker image much smaller!

---

## Step 2: Rewire the Event Extraction (The "Bridge")
Currently, the Event Extractor expects a `multimodal.json` file (which contains both transcript segments and mapped slides). We need to rewire it to accept the raw `transcript.json` directly.

1. **Edit `scripts/run_pipeline.py`:**
   * Remove the `--ppt`, `--slides`, `--embeddings`, and `--multimodal` arguments.
   * Modify the `--events` step so that instead of taking a multimodal file, it takes the `transcript.json`.
2. **Refactor Event Extraction (`src/fusion/multimodal_representation.py`):**
   * Rename this file to something like `src/intelligence/event_extractor.py`.
   * Update the parsing logic. Instead of looping over `multimodal['aligned_segments']`, it should simply loop over `transcript['segments']`.
   * Remove any logic that tries to read `slide_id` or `slide_content`.

---

## Step 3: Update the Intelligence Schemas
The downstream decision and influence graphs currently expect slide data.

1. **Remove slide references:**
   * In `src/meeting/decisions.py` and `src/meeting/interactions.py`, locate the data classes/schemas (where it assigns `slide_id` to an event or decision).
   * Delete those fields. The data structure should solely rely on `speaker`, `text`, `start_time`, and `end_time`.
2. **Update Prompts / Algorithmic Rules:**
   * If any algorithmic rule relied on "slide changes" to mark a new topic, you will need to replace this with a temporal rule (e.g., "if there is a 5-second silence, mark as a new topic") or a simple NLP topic-shift detection.

---

## Step 4: Update the Report Generator
1. **Edit `scripts/generate_report.py`:**
   * Remove the "Slides" count from the Executive Summary table.
   * Delete the "Slide-linked Discussion" section completely.
   * Ensure the CSV and JSON exporters no longer look for slide keys.

---

## Step 5: Clean Up the Execution Script
Your `scripts/process_new_meeting.sh` becomes wonderfully simple:

```bash
#!/bin/bash
MEETING_ID=$1
AUDIO_FILE=$2

# 1. Audio Pipeline
python3 scripts/run_pipeline.py --audio "$AUDIO_FILE" --meeting-id "$MEETING_ID"

# 2. Events (Directly from transcript)
python3 scripts/run_pipeline.py --extract-events "data/processed/audio/${MEETING_ID}_transcript.json" --meeting-id "$MEETING_ID"

# 3. Decisions & Influence
python3 scripts/run_pipeline.py --decisions "data/processed/events/${MEETING_ID}_events.json" --meeting-id "$MEETING_ID"
python3 scripts/run_pipeline.py --interactions "data/processed/decisions/${MEETING_ID}_decisions.json" --meeting-id "$MEETING_ID"

# 4. Report
python3 scripts/generate_report.py --meeting-id "$MEETING_ID"
```

## Conclusion
By dropping the PPT requirement, your system becomes infinitely more scalable. It can process standard phone calls, podcasts, and video-off Zoom meetings, making the patent highly applicable to enterprise VoIP/Telephony markets!

