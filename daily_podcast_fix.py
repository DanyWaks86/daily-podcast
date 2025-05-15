import os
import requests
import openai
from datetime import datetime, timezone, timedelta
from pydub import AudioSegment
from io import BytesIO
import subprocess
import tempfile
import time

# === Configuration ===
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
PYTHONANYWHERE_USERNAME = os.getenv("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.getenv("PYTHONANYWHERE_API_TOKEN")

BASE_URL = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/fr/"
DATE = "2025-05-14"
SCRIPT_FILENAME = f"podcast_{DATE}.txt"
INTRO_MUSIC_URL = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/breaking-news-intro-logo-314320.mp3"
VOICE_ID = "1a3lMdKLUcfcMtvN772u"
MODEL_ID = "eleven_multilingual_v2"

HEADERS_11 = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

HEADERS_PY = {
    "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
}

# === Download English script ===
def fetch_english_script():
    url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/en/{SCRIPT_FILENAME}"
    response = requests.get(url, headers=HEADERS_PY)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch English script: {response.text}")


# === Translate ===
from datetime import datetime, timedelta

def translate_text(text):
    # Remove the fixed English intro (always line 1)
    lines = text.strip().split('\n')
    body_only = '\n'.join(lines[1:]).strip()

    # Your fixed French intro
    french_intro = (
        f"Bienvenue dans la Minute Gaming ! Je suis Dany Waksman, passionné de jeux vidéo, et chaque jour, je vous emmène "
        f" faire le tour des actus les plus marquantes de l’univers du jeux video. Un condensé d’infos, généré par intelligence artificielle "
        f"pour rester à jour sans perdre une minute ! C'est parti pour le recap d'hier {(datetime.now() - timedelta(days=1)).strftime('%-d %B')}.\n\n"
    )

    # Translation prompt for the rest of the script
    prompt = (
        "Translate the following podcast script into natural, fluent Parisian French with an engaging and enthusiastic tone. "
        "Write as if you're a popular French-speaking podcast host from Paris. Use casual, expressive language that sounds natural to French listeners. "
        "Keep the energy high and the phrasing conversational. Do not over-formalize.\n\n"
        f"{body_only}"
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    translated_body = response.choices[0].message.content.strip()

    return french_intro + translated_body


# === ElevenLabs TTS ===
def generate_audio(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.9,
            "style": 0.2,
            "use_speaker_boost": True
        }
    } 
    
    response = requests.post(url, headers=HEADERS_11, json=payload)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception(f"TTS failed: {response.text}")

# === Combine Audio with loudnorm ===
def combine_audio(voice_audio_io):

    # Download intro music
    intro_response = requests.get(INTRO_MUSIC_URL)
    if intro_response.status_code != 200:
        raise Exception(f"Failed to download intro music: {intro_response.status_code} – {intro_response.text}")
    intro_audio = BytesIO(intro_response.content)

    # Save voice audio to temp file for loudnorm normalization
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_raw:
        temp_raw.write(voice_audio_io.read())
        temp_raw.flush()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_norm:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", temp_raw.name,
                "-ar", "44100",  # explicitly downsample to safe rate
                "-af", "loudnorm",
                temp_norm.name
            ], check=True)

            # Load normalized audio into memory
            normalized_voice = AudioSegment.from_wav(temp_norm.name)
        

    intro = AudioSegment.from_file(intro_audio, format="mp3")
    final_audio = intro + normalized_voice + intro

    output_io = BytesIO()
    final_audio.export(output_io, format="mp3")
    output_io.seek(0)
    return output_io


# === Upload to PythonAnywhere ===
def upload_to_pythonanywhere(filename, fileobj):
    url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/fr/{filename}"

    fileobj.seek(0, os.SEEK_END)
    size_kb = fileobj.tell() / 1024
    fileobj.seek(0)
    print(f"📁 Preparing to upload: {filename} ({size_kb:.1f} KB)")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"🔁 Attempt {attempt} of {max_retries} to upload {filename}...")
        response = requests.post(url, headers=HEADERS_PY, files={"content": fileobj})

        if response.status_code == 200:
            print(f"✅ Successfully uploaded {filename} to PythonAnywhere.")
            return

        print(f"⚠️ Upload failed (HTTP {response.status_code}).")
        print(f"📄 Response body: {response.text or '[empty]'}")

        if response.status_code == 413:
            print("❌ File too large to upload via API.")
            break
        elif response.status_code in [401, 403]:
            print("❌ Authentication or permission error. Check API token and username.")
            break
        elif attempt < max_retries:
            print("⏳ Retrying after 2 seconds...")
            time.sleep(2)
            fileobj.seek(0)
        else:
            raise Exception(f"❌ Final attempt failed to upload {filename}.")

# === Generate HTML page ===
def generate_html():
    return f"""<html>
  <head><title>{DATE} - La Minute Gaming</title></head>
  <body>
    <h1>{DATE} - Podcast Jeux Videos</h1>
    <audio controls>
      <source src=\"final_podcast_fr_{DATE}.mp3\" type=\"audio/mpeg\">
    </audio>
  </body>
</html>"""

# === Generate RSS ===
def update_rss():
    rss_filename = "rss_fr.xml"
    pub_date_formatted = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

    new_item = f"""
    <item>
      <title>La Minute Gaming - {DATE}</title>
      <link>{BASE_URL}podcast_{DATE}.html</link>
      <description><![CDATA[Podcast d'actualité jeux vidéos du jour, en français, présenté par Dany Waksman. Lire les notes: {BASE_URL}podcast_{DATE}.html]]></description>
      <enclosure url="{BASE_URL}final_podcast_fr_{DATE}.mp3" length="5000000" type="audio/mpeg" />
      <guid>{BASE_URL}podcast_{DATE}.html</guid>
      <pubDate>{pub_date_formatted}</pubDate>
      <itunes:author>Dany Waksman</itunes:author>
    </item>"""

    # Try fetching existing RSS file from PythonAnywhere
    url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/fr/{rss_filename}"
    response = requests.get(url, headers=HEADERS_PY)

    if response.status_code == 200:
        rss_content = response.text
        if f"<guid>{BASE_URL}podcast_{DATE}.html</guid>" in rss_content:
            print("✅ Today's episode already in RSS.")
            return
        updated_rss = rss_content.replace("</channel>", f"{new_item}\n  </channel>")
    else:
        print("🆕 Creating new rss_fr.xml from scratch.")
        updated_rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>La Minute Gaming</title>
    <link>{BASE_URL}</link>
    <language>fr-fr</language>
    <description>Un podcast quotidien d'actualités gaming en français.</description>
    <itunes:author>Dany Waksman</itunes:author>
    <itunes:owner>
      <itunes:name>Dany Waksman</itunes:name>
      <itunes:email>dany.waksman@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:summary>La Minute Gaming — l'actu de jeux vidéos en français, générée par IA.</itunes:summary>
    <itunes:explicit>no</itunes:explicit>
    <podcast:locked>yes</podcast:locked>
    <itunes:image href="{BASE_URL}podcast-cover-fr.png"/>
    <itunes:category text="Technology"/>
    <itunes:category text="Leisure">
      <itunes:category text="Video Games"/>
    </itunes:category>
    <atom:link href="{BASE_URL}rss_fr.xml" rel="self" type="application/rss+xml"/>
    {new_item}
  </channel>
</rss>"""

    # Upload updated RSS back to PythonAnywhere
    upload_to_pythonanywhere(rss_filename, BytesIO(updated_rss.encode("utf-8")))


# === Main ===
def main():
    print("📥 Fetching English script...")
    script = fetch_english_script()

    print("🧠 Translating to French...")
    translated = translate_text(script)

    print("🔊 Generating voice audio (first 30 seconds only)...")
    # Estimate first ~600 characters as 30 seconds of speech
    preview_text = translated[:600]
    voice_mp3 = generate_audio(preview_text)


    print("🎵 Combining with intro/outro...")
    final_audio_io = combine_audio(voice_mp3)

    print("☁️ Uploading MP3...")
    upload_to_pythonanywhere(f"final_podcast_fr_{DATE}.mp3", final_audio_io)

    print("📜 Uploading HTML...")
    html = generate_html()
    upload_to_pythonanywhere(f"podcast_{DATE}.html", BytesIO(html.encode("utf-8")))

    print("📡 Uploading RSS...")
    update_rss()


    print("✅ French version published!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
