import os
import requests
import yagmail
from io import BytesIO

# === Setup ===
print("🔧 Loading environment variables...")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"  # Your cloned voice
MODEL_ID = "eleven_multilingual_v2"

if not ELEVENLABS_API_KEY:
    raise Exception("❌ Missing ELEVENLABS_API_KEY")
if not SENDER_EMAIL or not APP_PASSWORD or not RECIPIENT_EMAIL:
    raise Exception("❌ Missing one of: SENDER_EMAIL, APP_PASSWORD, RECIPIENT_EMAIL")

print("✅ Environment variables loaded.")

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
        "style": 0.5,
        "use_speaker_boost": True
    }
}

print("🎙️ Sending request to ElevenLabs...")
url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
response = requests.post(url, headers=HEADERS, json=payload)

if response.status_code != 200:
    print("❌ TTS failed!")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
else:
    print("✅ TTS audio received.")
    mp3_data = BytesIO(response.content)
    mp3_data.seek(0)

    print("📧 Preparing to send email with attachment...")
    try:
        yag = yagmail.SMTP(user=SENDER_EMAIL, password=APP_PASSWORD)
        yag.send(
            to=RECIPIENT_EMAIL,
            subject="🎧 French TTS Test – Your Cloned Voice",
            contents="Attached is the test of your cloned voice speaking in French with an excited tone.",
            attachments=[("test_voice_fr.mp3", mp3_data.read())]
        )
        print("📤 Email sent successfully to:", RECIPIENT_EMAIL)
    except Exception as e:
        print("❌ Failed to send email:", e)
