"""
Generate a short synthetic test audio file for pipeline validation.
Produces a 30-second WAV with two alternating sine tones (simulating two speakers).
Uses only stdlib — no FFmpeg required.
Output: data/raw/audio/test_meeting.wav
"""

import math
import struct
import wave
from pathlib import Path

OUT_PATH = Path("data/raw/audio/test_meeting.wav")
SR = 16000
DURATION = 30  # seconds


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n = SR * DURATION
    segment_len = SR * 3  # 3-second alternating tones

    samples = []
    for i in range(n):
        seg_idx = i // segment_len
        freq = 440.0 if seg_idx % 2 == 0 else 880.0
        t = i / SR
        val = int(0.4 * 32767 * math.sin(2 * math.pi * freq * t))
        samples.append(val)

    with wave.open(str(OUT_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SR)
        wf.writeframes(struct.pack(f"<{n}h", *samples))

    print(f"Saved: {OUT_PATH}  ({DURATION}s, {SR} Hz, mono)")

if __name__ == "__main__":
    main()
