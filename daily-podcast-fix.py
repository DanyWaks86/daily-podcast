import requests
import subprocess
import os
from datetime import datetime
import yagmail

# === CONFIGURATION ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")  # Your ElevenLabs API Key
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

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

# === Step 3: Email both files to yourself ===
def send_email_with_attachments(wav_path, mp3_path):
    if not all([SENDER_EMAIL, APP_PASSWORD, RECIPIENT_EMAIL]):
        print("❌ Missing email credentials. Please set SENDER_EMAIL, APP_PASSWORD, and RECIPIENT_EMAIL.")
        exit(1)

    yag = yagmail.SMTP(user=SENDER_EMAIL, password=APP_PASSWORD)
    
    yag.send(
        to=RECIPIENT_EMAIL,
        subject=f"🎧 Daily Podcast Voice Test – {datetime.now().strftime('%B %d, %Y')}",
        contents="Here are your voicefix test podcast files attached. Enjoy!",
        attachments=[wav_path, mp3_path]
    )

    print(f"✅ Email sent successfully to {RECIPIENT_EMAIL} with attachments!")

send_email_with_attachments(VOICE_OUTPUT_PATH, FINAL_OUTPUT_PATH)
