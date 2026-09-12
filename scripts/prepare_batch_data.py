import os
import glob
import shutil
import subprocess
from pathlib import Path

def prepare_audio():
    print("Preparing Audio files...")
    os.makedirs("data/raw/audio", exist_ok=True)
    wavs = glob.glob("AMI_dataset/audio/Array1-01/*/audio/*.wav")
    count = 0
    for w in wavs:
        # e.g. AMI_dataset/audio/Array1-01/ES2002a/audio/ES2002a.Array1-01.wav
        meeting_id = Path(w).parent.parent.name
        dest = f"data/raw/audio/{meeting_id}.wav"
        if not os.path.exists(dest):
            # Use symlink to save space and time
            os.symlink(os.path.abspath(w), dest)
            count += 1
    print(f"Symlinked {count} audio files to data/raw/audio/.")

def prepare_ppts():
    print("Preparing Presentation files...")
    os.makedirs("data/raw/ppt", exist_ok=True)
    ppts = glob.glob("AMI_dataset/amicorpus/*/shared-doc/*.ppt")
    count = 0
    for p in ppts:
        meeting_id = Path(p).parent.parent.name
        filename = Path(p).name
        out_dir = f"data/raw/ppt/{meeting_id}"
        os.makedirs(out_dir, exist_ok=True)
        # Convert to pptx if not already done
        expected_pptx = os.path.join(out_dir, filename.replace(".ppt", ".pptx"))
        if not os.path.exists(expected_pptx):
            print(f"Converting {filename} for {meeting_id}...")
            # Convert using LibreOffice
            subprocess.run([
                "soffice", "--headless", "--convert-to", "pptx",
                "--outdir", out_dir, p
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            count += 1
    print(f"Converted {count} presentations to data/raw/ppt/.")

if __name__ == "__main__":
    prepare_audio()
    prepare_ppts()
    print("Batch data preparation complete.")
