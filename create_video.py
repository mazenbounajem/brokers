import os
import subprocess
import pyttsx3

# === Configuration ===
input_folder = 'extracted_images'       # <-- change this to your folder path
output_folder = 'horizentaloutput'
os.makedirs(output_folder, exist_ok=True)

segment_files = []

def generate_tts_offline(text, output_path_wav):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.save_to_file(text, output_path_wav)
    engine.runAndWait()

# === Process each image-text pair ===
for file in sorted(os.listdir(input_folder)):
    if file.endswith('.jpeg'):
        base_name = os.path.splitext(file)[0]
        image_path = os.path.join(input_folder, file)
        text_path = os.path.join(input_folder, f"{base_name}.txt")

        if not os.path.exists(text_path):
            print(f"❌ Missing text for {file}")
            continue

        # Read text
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()

        if not text:
            print(f"⚠️ Skipping empty text file: {text_path}")
            continue

        # Generate offline TTS
        tts_path = os.path.join(output_folder, f"{base_name}.wav")
        generate_tts_offline(text, tts_path)

        # Create a video segment (image + audio)
        segment_path = os.path.join(output_folder, f"{base_name}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", tts_path,
            "-shortest",
            "-vf", "scale=1280:720",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            segment_path
        ]
        subprocess.run(cmd, check=True)
        segment_files.append(segment_path)

# === Concatenate all segments ===
concat_list_path = os.path.join(output_folder, "concat_list.txt")
with open(concat_list_path, 'w') as f:
    for seg in segment_files:
        f.write(f"file '{os.path.abspath(seg)}'\n")

final_video_path = os.path.join(output_folder, "final_video.mp4")
cmd_concat = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_list_path,
    "-c", "copy",
    final_video_path
]
subprocess.run(cmd_concat, check=True)

print(f"\n🎬 Final video created at: {final_video_path}")