import requests
import subprocess
import os

# === CONFIGURATION ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")  # Your ElevenLabs API Key
VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"  # Your ElevenLabs Voice ID (Dany)

# Paths
PODCAST_DIR = "/opt/render/project/src/podcast/"
INTRO_MUSIC_PATH = os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3")
VOICE_OUTPUT_PATH = os.path.join(PODCAST_DIR, "voice_test.wav")  # Downloaded ElevenLabs voice file
FINAL_OUTPUT_PATH = os.path.join(PODCAST_DIR, "final_podcast_TEST.mp3")  # Final podcast output for testing

# Text to generate
TEXT_TO_SPEAK = "Welcome to the Daily Video Games Digest. I'm Dany Waksman, a video game enthusiast, bringing you this AI-generated podcast to stay informed with the latest in the gaming world. Let's jump right in."

# === Step 1: Generate Voice Audio ===
headers = {
    "Accept": "audio/wav",  # Request WAV format
    "Content-Type": "application/json",
    "xi-api-key": ELEVENLABS_API_KEY
}

payload = {
    "text": TEXT_TO_SPEAK,
    "voice_settings": {
        "stability": 0.4,
        "similarity_boost": 0.75
    },
    "output_format": "wav"  # Ask for WAV output to avoid compression
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

print("✅ Voice audio downloaded successfully.")

# === Step 2: Merge Intro and Voice ===
# Using ffmpeg to concat intro + generated voice, no re-encoding
try:
    subprocess.run([
        "ffmpeg",
        "-y",  # Overwrite output if exists
        "-i", INTRO_MUSIC_PATH,
        "-i", VOICE_OUTPUT_PATH,
        "-filter_complex", "[0:0][1:0]concat=n=2:v=0:a=1[out]",
        "-map", "[out]",
        "-b:a", "256k",  # Export at 256kbps MP3 for high quality
        FINAL_OUTPUT_PATH
    ], check=True)

    print(f"✅ Test podcast generated successfully: {FINAL_OUTPUT_PATH}")

except subprocess.CalledProcessError as e:
    print("❌ Error during ffmpeg merge:", e)
    exit(1)
