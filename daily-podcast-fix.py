import requests
import subprocess
import os
from datetime import datetime

# === CONFIGURATION ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")  # Your ElevenLabs API Key
PYTHONANYWHERE_USERNAME = os.getenv("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.getenv("PYTHONANYWHERE_API_TOKEN")

VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"  # Your ElevenLabs Voice ID (Dany)

# Paths
PODCAST_DIR = "/opt/render/project/src/podcast/"
INTRO_MUSIC_PATH = os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3")

TODAY = datetime.now().strftime('%Y-%m-%d')
VOICE_OUTPUT_PATH = os.path.join(PODCAST_DIR, f"voice_{TODAY}.wav")
FINAL_OUTPUT_PATH = os.path.join(PODCAST_DIR, f"final_podcast_{TODAY}_TEST.mp3")

# Text to generate
TEXT_TO_SPEAK = (
    "Welcome to the Daily Video Games Digest. "
    "I'm Dany Waksman, a video game enthusiast, "
    "bringing you this AI-generated podcast to stay informed "
    "with the latest in the gaming world. Let's jump right in."
)

# === Step 1: Generate Voice Audio ===
headers = {
    "Accept": "audio/wav",
    "Content-Type": "application/json",
    "xi-api-key": ELEVENLABS_API_KEY
}

payload = {
    "text": TEXT_TO_SPEAK,
    "voice_settings": {
        "stability": 0.4,
        "similarity_boost": 0.75
    },
    "output_format": "wav"
}

response = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
    headers=headers,
    json=payload
)

if response.status_code != 200:
    print("❌ Error from ElevenLabs:", response.text)
    exit(1)

with open(VOICE_OUTPUT_PATH, "wb") as f:
    f.write(response.content)

print(f"✅ Voice audio downloaded successfully: {VOICE_OUTPUT_PATH}")

# === Step 2: Merge Intro and Voice ===
try:
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", INTRO_MUSIC_PATH,
        "-i", VOICE_OUTPUT_PATH,
        "-filter_complex", "[0:0][1:0]concat=n=2:v=0:a=1[out]",
        "-map", "[out]",
        "-b:a", "256k",
        FINAL_OUTPUT_PATH
    ], check=True)

    print(f"✅ Test podcast generated successfully: {FINAL_OUTPUT_PATH}")

except subprocess.CalledProcessError as e:
    print("❌ Error during ffmpeg merge:", e)
    exit(1)

# === Step 3: Upload both files to PythonAnywhere ===

def upload_to_pythonanywhere(local_path, remote_filename):
    headers = {
        "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
    }
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast2/{remote_filename}"

    with open(local_path, "rb") as f:
        response = requests.post(upload_url, headers=headers, files={"content": f})
        if response.status_code != 200:
            print(f"❌ Failed to upload {remote_filename}: {response.text}")
        else:
            print(f"✅ Uploaded {remote_filename} to PythonAnywhere.")

# Upload both files
upload_to_pythonanywhere(VOICE_OUTPUT_PATH, os.path.basename(VOICE_OUTPUT_PATH))
upload_to_pythonanywhere(FINAL_OUTPUT_PATH, os.path.basename(FINAL_OUTPUT_PATH))
