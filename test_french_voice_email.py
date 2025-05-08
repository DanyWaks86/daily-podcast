import os
import requests
import yagmail
from io import BytesIO

# === Setup ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"  # Your cloned voice
MODEL_ID = "eleven_multilingual_v2"

HEADERS = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

# === Prompt & TTS ===
french_text = (
    "Bonjour à tous et bienvenue dans notre podcast quotidien sur les jeux vidéo. "
    "Préparez-vous à découvrir les nouvelles les plus passionnantes du jour avec enthousiasme !"
)

payload = {
    "text": french_text,
    "model_id": MODEL_ID,
    "voice_settings": {
        "stability": 0.3,
        "similarity_boost": 0.8,
        "style": 0.5,              # Add some expressiveness
        "use_speaker_boost": True
    }
}

print("🎙️ Requesting TTS from ElevenLabs...")
response = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", headers=HEADERS, json=payload)

if response.status_code != 200:
    print("❌ TTS failed:", response.text)
else:
    print("✅ Audio received! Preparing email...")

    mp3_data = BytesIO(response.content)
    mp3_data.seek(0)

    yag = yagmail.SMTP(user=SENDER_EMAIL, password=APP_PASSWORD)
    yag.send(
        to=RECIPIENT_EMAIL,
        subject="🎧 French TTS Test – Your Cloned Voice",
        contents="Attached is the test of your cloned voice speaking in French with an excited tone.",
        attachments={"test_voice_fr.mp3": mp3_data.read()}
    )

    print("📤 Email sent!")
