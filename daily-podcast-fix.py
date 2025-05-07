import os
import io
import requests
import subprocess
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
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
MAX_EPISODES = 14

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')


def add_id3_tags(mp3_path, date_str):
    try:
        audio = MP3(mp3_path, ID3=EasyID3)
        audio["title"] = f"Gaming News Digest - {date_str}"
        audio["artist"] = "Dany Waksman"
        audio["album"] = "Daily Video Games Digest"
        audio.save()
        print(f"✅ ID3 tags added to {mp3_path}")
    except Exception as e:
        print(f"❌ Failed to add ID3 tags: {e}")


def fetch_rss_articles_txt():
    print("📥 Fetching scored articles from PythonAnywhere...")
    headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
    txt_filename = f"rss_articles_scored_{TODAY}.txt"
    txt_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/{txt_filename}"
    response = requests.get(txt_url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch RSS-scored articles: {response.text}")
        return None
    return response.text


def generate_script_from_text(rss_text):
    prompt = f"""You are generating a daily podcast script based on real gaming news articles. Follow these rules carefully:

1. Carefully read the articles provided.
2. Select and summarize only the **6 most important or impactful stories**.
3. For each story, **mention the news source** naturally (e.g., \"according to IGN\").
4. Write in a **natural, casual podcast tone**, as if you are personally telling listeners the day's biggest stories.
5. **Do not** use any headers like \"Story 1\" or Markdown formatting.
6. Focus on **delivering a tight and engaging podcast script that lasts approximately 4–5 minutes** total.

Start the podcast script with this exact intro:
\"Welcome to the Daily Video Games Digest. I'm Dany Waksman, a video game enthusiast, bringing you this AI-generated podcast to stay informed with the latest in the gaming world. Let's jump right into yesterday’s biggest stories, {datetime.now().strftime('%B %d')}.”

End the podcast script with this exact outro:
\"Thanks for tuning into the Daily Video Games Digest. If you enjoyed today’s update, be sure to check back tomorrow for the latest in gaming news. Until then, happy gaming!\"

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
    return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')


def text_to_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 1.0,
            "style": 0.0,
            "use_speaker_boost": True
        },
        "output_format": "wav"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("❌ ElevenLabs TTS Error:", response.text)
        return None
    return response.content


def save_audio_with_intro_outro(audio_data, filename_base):
    raw_voice_path = os.path.join(PODCAST_DIR, "voice_raw.mp3")
    normalized_voice_path = os.path.join(PODCAST_DIR, "voice_normalized.wav")
    with open(raw_voice_path, "wb") as f:
        f.write(audio_data)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", raw_voice_path,
        "-af", "loudnorm",
        normalized_voice_path
    ], check=True)
    intro = AudioSegment.from_file(os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3"), format="mp3") - 8
    voice = AudioSegment.from_file(normalized_voice_path, format="wav")
    combined = intro + voice + intro
    final_filename = os.path.join(PODCAST_DIR, f"final_podcast_{filename_base}.mp3")
    combined.export(
        final_filename,
        format="mp3",
        tags={
            "title": f"Daily Video Games Digest – {filename_base}",
            "artist": "Dany Waksman",
            "album": "Daily Video Games Digest"
        }
    )
    return final_filename


def send_email_with_podcast(final_filename):
    yag = yagmail.SMTP(user=SENDER_EMAIL, password=APP_PASSWORD)
    yag.send(
        to=RECIPIENT_EMAIL,
        subject=f"🎧 Daily Video Games Digest – {datetime.now().strftime('%B %d, %Y')}",
        contents="Here’s your latest AI-generated podcast episode!",
        attachments=final_filename
    )


def push_to_pythonanywhere_api():
    print("🚀 Uploading files to PythonAnywhere via API...")
    headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/"
    for filename in [
        f"final_podcast_{TODAY}.mp3",
        f"podcast_{TODAY}.html",
        "breaking-news-intro-logo-314320.mp3",
        "rss.xml",
    ]:
        local_path = os.path.join(PODCAST_DIR, filename)
        with open(local_path, "rb") as f:
            response = requests.post(upload_url + filename, headers=headers, files={"content": f})
            if response.status_code != 200:
                print(f"❌ Failed to upload {filename}: {response.text}")
            else:
                print(f"✅ Uploaded {filename} to PythonAnywhere.")


# === MAIN PROCESS ===
rss_text = fetch_rss_articles_txt()
if not rss_text:
    print("❌ No RSS article text found.")
    exit()

print("🧠 Generating podcast script...")
script = generate_script_from_text(rss_text)
if not script:
    print("❌ Failed to generate script.")
    exit()

print("📤 Uploading English script to PythonAnywhere...")
try:
    headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/en/podcast_{TODAY}.txt"
    response = requests.post(upload_url, headers=headers, files={"content": script.encode("utf-8")})
    if response.status_code == 200:
        print("✅ English script uploaded successfully.")
    else:
        print(f"⚠️ Failed to upload English script: {response.text}")
except Exception as e:
    print(f"⚠️ Exception during English script upload: {e}")

print("🎙️ Converting script to audio...")
audio_data = text_to_speech(script)
if not audio_data:
    print("❌ No audio data returned from TTS engine.")
    exit()
print("✅ Audio data received!")

final_filename = save_audio_with_intro_outro(audio_data, TODAY)
add_id3_tags(final_filename, TODAY)
send_email_with_podcast(final_filename)
push_to_pythonanywhere_api()

print("✅ Done!")
