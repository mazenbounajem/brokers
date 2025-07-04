import os
import subprocess
import pyttsx3
from transformers import pipeline

def create_video(input_folder='extracted_images', output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)

    # Summarization pipeline (uses distilbart-cnn)
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

    # Text enhancement pipeline for emphasizing selling keywords
    enhancer = pipeline("text2text-generation", model="google/flan-t5-base")

    # Use a female voice (voice selection varies by OS)
    def generate_tts_female(text, output_path):
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        voices = engine.getProperty('voices')

        # Try to select a known female voice
        female_voice = None
        for voice in voices:
            if "zira" in voice.name.lower():  # Windows female voice
                female_voice = voice
                break
        if not female_voice:
            for voice in voices:
                if "female" in voice.name.lower() or "woman" in voice.name.lower():
                    female_voice = voice
                    break
        if female_voice:
            engine.setProperty('voice', female_voice.id)
        else:
            print("⚠️ Female voice not found. Using default voice.")
            print("Available voices:")
            for voice in voices:
                print(f"- {voice.name} | ID: {voice.id}")

        engine.save_to_file(text, output_path)
        engine.runAndWait()

    def create_padded_image(image_path, output_path):
        cmd = [
            "ffmpeg", "-y",
            "-i", image_path,
            "-vf", "scale=iw*min(1440/iw\\,2560/ih):ih*min(1440/iw\\,2560/ih),pad=1440:2560:(1440-iw*min(1440/iw\\,2560/ih))/2:(2560-ih*min(1440/iw\\,2560/ih))/2:color=black",
            output_path
        ]
        subprocess.run(cmd, check=True)

    segment_files = []

    # === Process Each Page ===
    for file in sorted(os.listdir(input_folder)):
        if file.endswith('.jpeg'):
            base_name = os.path.splitext(file)[0]
            image_path = os.path.join(input_folder, file)
            text_path = os.path.join(input_folder, f"{base_name}.txt")

            if not os.path.exists(text_path):
                print(f"❌ Missing text for {file}")
                continue

            # Read and enhance text for selling emphasis
            with open(text_path, 'r', encoding='utf-8') as f:
                original_text = f.read().strip()
            if not original_text:
                print(f"⚠️ Empty text: {text_path}")
                continue

            enhanced_text = enhancer(f"Enhance this property description to emphasize selling points: {original_text}", max_length=100)[0]['generated_text']

            # Summarize enhanced text
            summarized = summarizer(enhanced_text, max_length=60, min_length=25, do_sample=False)[0]['summary_text']

            # TTS to WAV with adjusted voice rate for better clarity
            tts_path = os.path.join(output_folder, f"{base_name}.wav")
            generate_tts_female(summarized, tts_path)

            # Padded image to vertical 1440x2560 with safe areas
            padded_img_path = os.path.join(output_folder, f"{base_name}_padded.jpeg")
            create_padded_image(image_path, padded_img_path)

            # Combine image + audio into video
            segment_path = os.path.join(output_folder, f"{base_name}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", padded_img_path,
                "-i", tts_path,
                "-shortest",
                "-vf", "scale=1440:2560",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "30",  # fixed frame rate
                "-preset", "slow",
                "-profile:v", "high",
                "-movflags", "+faststart",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
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

    # Trim video to max 30 seconds
    trimmed_video_path = os.path.join(output_folder, "final_video_trimmed.mp4")
    cmd_trim = [
        "ffmpeg", "-y",
        "-i", final_video_path,
        "-t", "30",
        "-c", "copy",
        trimmed_video_path
    ]
    subprocess.run(cmd_trim, check=True)

    print(f"\n✅ Final vertical video created: {trimmed_video_path}")

def create_video_from_user_text(input_folder='extracted_images', output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)

    # Use a female voice (voice selection varies by OS)
    def generate_tts_female(text, output_path):
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        voices = engine.getProperty('voices')

        # Try to select a known female voice
        female_voice = None
        for voice in voices:
            if "zira" in voice.name.lower():  # Windows female voice
                female_voice = voice
                break
        if not female_voice:
            for voice in voices:
                if "female" in voice.name.lower() or "woman" in voice.name.lower():
                    female_voice = voice
                    break
        if female_voice:
            engine.setProperty('voice', female_voice.id)
        else:
            print("⚠️ Female voice not found. Using default voice.")
            print("Available voices:")
            for voice in voices:
                print(f"- {voice.name} | ID: {voice.id}")

        engine.save_to_file(text, output_path)
        engine.runAndWait()

    def create_padded_image(image_path, output_path):
        cmd = [
            "ffmpeg", "-y",
            "-i", image_path,
            "-vf", "scale=iw*min(1440/iw\\,2560/ih):ih*min(1440/iw\\,2560/ih),pad=1440:2560:(1440-iw*min(1440/iw\\,2560/ih))/2:(2560-ih*min(1440/iw\\,2560/ih))/2:color=black",
            output_path
        ]
        subprocess.run(cmd, check=True)

    segment_files = []

    # Read user text from user_text.txt
    user_text_path = os.path.join(input_folder, 'user_text.txt')
    if not os.path.exists(user_text_path):
        print(f"❌ Missing user text file: {user_text_path}")
        return

    with open(user_text_path, 'r', encoding='utf-8') as f:
        user_text = f.read().strip()

    if not user_text:
        print(f"⚠️ Empty user text file: {user_text_path}")
        return

    # For each image in input_folder, create video segment with user text TTS
    for file in sorted(os.listdir(input_folder)):
        if file.endswith('.jpeg'):
            base_name = os.path.splitext(file)[0]
            image_path = os.path.join(input_folder, file)

            # TTS to WAV with user text
            tts_path = os.path.join(output_folder, f"{base_name}.wav")
            generate_tts_female(user_text, tts_path)

            # Padded image to vertical 1440x2560 with safe areas
            padded_img_path = os.path.join(output_folder, f"{base_name}_padded.jpeg")
            create_padded_image(image_path, padded_img_path)

            # Combine image + audio into video
            segment_path = os.path.join(output_folder, f"{base_name}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", padded_img_path,
                "-i", tts_path,
                "-shortest",
                "-vf", "scale=1440:2560",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "30",  # fixed frame rate
                "-preset", "slow",
                "-profile:v", "high",
                "-movflags", "+faststart",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
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

    # Trim video to max 30 seconds
    trimmed_video_path = os.path.join(output_folder, "final_video_trimmed.mp4")
    cmd_trim = [
        "ffmpeg", "-y",
        "-i", final_video_path,
        "-t", "30",
        "-c", "copy",
        trimmed_video_path
    ]
    subprocess.run(cmd_trim, check=True)

    print(f"\n✅ Final vertical video created from user text: {trimmed_video_path}")
