import os
import requests
import yagmail
from datetime import datetime
from io import BytesIO

# === Configuration ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"  # Your cloned voice
MODEL_ID = "eleven_multilingual_v2"

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# === Text for TTS ===
french_text = (
    "Bonjour à tous et bienvenue dans notre podcast quotidien sur les jeux vidéo ! "
    "Voici les actualités les plus passionnantes d'aujourd'hui."
)

payload = {
    "text": french_text,
    "model_id": MODEL_ID,
    "voice_settings": {
        "stability": 0.4,
        "similarity_boost": 0.75
    }
}

headers = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

# === Request to ElevenLabs ===
print("🎙️ Sending request to ElevenLabs...")
url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    print("❌ TTS failed:", response.text)
    exit()

print("✅ TTS audio received.")
audio_io = BytesIO(response.content)
audio_io.seek(0)

# === Send email with audio attachment ===
print("📧 Sending email with attachment...")
yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)

try:
    yag.send(
        to=RECIPIENT_EMAIL,
        subject=f"🎧 French Voice Test – {datetime.now().strftime('%B %d, %Y')}",
        contents="Here is the test audio in French using your cloned ElevenLabs voice.",
        attachments=[("test_french_voice.mp3", audio_io)]
    )
    print("✅ Email sent successfully.")
except Exception as e:
    print(f"❌ Failed to send email: {e}")
