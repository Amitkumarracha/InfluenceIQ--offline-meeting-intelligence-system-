import os
import shutil
import glob
import subprocess

audio_dir = "data/raw/audio"
ppt_dir = "data/raw/ppt"
output_dir = "data/test_samples"

os.makedirs(output_dir, exist_ok=True)

# Find all meetings with both audio and ppt
valid_meetings = []
if os.path.exists(ppt_dir):
    for meeting_id in sorted(os.listdir(ppt_dir)):
        ppt_files = glob.glob(os.path.join(ppt_dir, meeting_id, "*.pptx"))
        audio_file = os.path.join(audio_dir, f"{meeting_id}.wav")
        
        if ppt_files and os.path.exists(audio_file):
            valid_meetings.append((meeting_id, audio_file, ppt_files[0]))
            
        if len(valid_meetings) >= 5:
            break

for i, (meeting_id, audio_path, ppt_path) in enumerate(valid_meetings, 1):
    sample_folder = os.path.join(output_dir, f"sample_{i}_{meeting_id}")
    os.makedirs(sample_folder, exist_ok=True)
    
    # Generate a 2-minute clipped version for fast UI testing
    dest_audio = os.path.join(sample_folder, f"{meeting_id}_2min_test.wav")
    dest_ppt = os.path.join(sample_folder, f"{meeting_id}_slides.pptx")
    
    # Copy PPT
    shutil.copy2(ppt_path, dest_ppt)
    
    # Clip Audio (first 2 mins)
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path, 
        "-t", "120", "-acodec", "copy", dest_audio
    ], capture_output=True)
    
    print(f"Created: {sample_folder}")
    print(f"  - {os.path.basename(dest_audio)}")
    print(f"  - {os.path.basename(dest_ppt)}\n")

