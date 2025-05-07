import os
import requests
import subprocess
from datetime import datetime, timezone
from pydub import AudioSegment
import yagmail
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

# === CONFIGURATION ===
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.environ.get("OPENAI_PROJECT_ID")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

PYTHONANYWHERE_USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN")

PODCAST_DIR = "/opt/render/project/src/podcast/"
BASE_URL = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/"
RSS_FILENAME = "rss.xml"

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')

def fetch_rss_articles_txt():
    print("📥 Fetching scored articles from PythonAnywhere...")
    headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
    url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/rss_articles_scored_{TODAY}.txt"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch RSS-scored articles: {response.text}")
        return None
    return response.text

def generate_script(rss_text):
    print("🧠 Generating podcast script...")
    prompt = f"""You are generating a daily podcast script...
(omit full prompt for brevity)...
Here are the real articles:

{rss_text}
"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": OPENAI_PROJECT_ID
    }
    data = {
        "model": "gpt-4-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

def upload_english_script(script):
    print("📤 Uploading English script to PythonAnywhere...")
    try:
        headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
        url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/en/podcast_{TODAY}.txt"
        response = requests.post(url, headers=headers, files={"content": script.encode("utf-8")})
        if response.status_code == 200:
            print("✅ English script uploaded successfully.")
        else:
            print(f"⚠️ Failed to upload English script: {response.status_code} {response.text}")
    except Exception as e:
        print(f"⚠️ Exception during upload: {e}")

def text_to_speech(text):
    print("🎙️ Converting script to audio...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 1.0, "style": 0.0, "use_speaker_boost": True},
        "output_format": "wav"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("❌ ElevenLabs TTS Error:", response.text)
        return None
    print("✅ Audio data received!")
    return response.content

def normalize_and_export(audio_data):
    raw_path = os.path.join(PODCAST_DIR, "voice_raw.mp3")
    wav_path = os.path.join(PODCAST_DIR, "voice_normalized.wav")
    with open(raw_path, "wb") as f:
        f.write(audio_data)
    subprocess.run(["ffmpeg", "-y", "-i", raw_path, "-af", "loudnorm", wav_path], check=True)
    return wav_path

def save_final_mp3(wav_path):
    intro = AudioSegment.from_file(os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3"), format="mp3") - 8
    voice = AudioSegment.from_file(wav_path, format="wav")
    final_audio = intro + voice + intro
    mp3_path = os.path.join(PODCAST_DIR, f"final_podcast_{TODAY}.mp3")
    final_audio.export(mp3_path, format="mp3", tags={"title": f"Daily Digest – {TODAY}", "artist": "Dany Waksman", "album": "Daily Video Games Digest"})
    return mp3_path

def add_id3_tags(mp3_path):
    audio = MP3(mp3_path, ID3=EasyID3)
    audio["title"] = f"Gaming News Digest - {TODAY}"
    audio["artist"] = "Dany Waksman"
    audio["album"] = "Daily Video Games Digest"
    audio.save()
    print("✅ ID3 tags added.")

def send_email(mp3_path):
    yag = yagmail.SMTP(user=SENDER_EMAIL, password=APP_PASSWORD)
    yag.send(
        to=RECIPIENT_EMAIL,
        subject=f"🎧 Daily Digest – {TODAY}",
        contents="Here’s your latest AI-generated podcast episode!",
        attachments=mp3_path
    )
    print("📬 Email sent.")

def push_to_pythonanywhere(mp3_path):
    print("🚀 Uploading files to PythonAnywhere via API...")
    headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/"
    files_to_upload = [
        mp3_path,
        os.path.join(PODCAST_DIR, f"podcast_{TODAY}.html"),
        os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3"),
        os.path.join(PODCAST_DIR, "rss.xml"),
    ]
    for file_path in files_to_upload:
        with open(file_path, "rb") as f:
            response = requests.post(upload_url + os.path.basename(file_path), headers=headers, files={"content": f})
            if response.status_code == 200:
                print(f"✅ Uploaded {os.path.basename(file_path)}.")
            else:
                print(f"❌ Failed to upload {file_path}: {response.text}")

# === MAIN PROCESS ===
rss_text = fetch_rss_articles_txt()
if not rss_text:
    exit()
script = generate_script(rss_text)
upload_english_script(script)

audio_data = text_to_speech(script)
if not audio_data:
    exit()

wav_path = normalize_and_export(audio_data)
mp3_path = save_final_mp3(wav_path)
add_id3_tags(mp3_path)
send_email(mp3_path)
push_to_pythonanywhere(mp3_path)

print("✅ Done!")
