import os
import requests
import openai
from datetime import datetime, timezone
from pydub import AudioSegment
from io import BytesIO

# === ENVIRONMENT CONFIGURATION ===
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
PYTHONANYWHERE_USERNAME = os.getenv("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.getenv("PYTHONANYWHERE_API_TOKEN")

DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
SCRIPT_URL = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/en/podcast_{DATE}.txt"
COVER_IMAGE_URL = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/podcast-cover.png"

LANGUAGE_SETTINGS = {
    "fr": {"name": "French", "voice_id": "TxGEqnHWrfWFTfGW9XjX", "locale": "fr-fr"},
}

HEADERS_ELEVENLABS = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

HEADERS_PYTHONANYWHERE = {
    "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
}

def fetch_script():
    print("📥 Downloading English script from PythonAnywhere...")
    response = requests.get(SCRIPT_URL, headers=HEADERS_PYTHONANYWHERE)
    if response.status_code != 200:
        raise RuntimeError(f"❌ Failed to fetch English script: {response.text}")
    return response.text

def translate_text(text, lang_code):
    print(f"🧠 Translating to {LANGUAGE_SETTINGS[lang_code]['name']}...")
    prompt = f"Translate this podcast script into {LANGUAGE_SETTINGS[lang_code]['name']} with a natural, local tone:\n\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def text_to_speech(text, voice_id):
    print("🔊 Generating TTS audio...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.75}
    }
    response = requests.post(url, headers=HEADERS_ELEVENLABS, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"❌ TTS error: {response.text}")
    return BytesIO(response.content)

def generate_html(lang_code):
    print("📝 Generating HTML...")
    return f"""<html>
  <head><title>{DATE} - {LANGUAGE_SETTINGS[lang_code]['name']} Gaming Podcast</title></head>
  <body>
    <h1>{DATE} - {LANGUAGE_SETTINGS[lang_code]['name']} Gaming Podcast</h1>
    <audio controls>
      <source src=\"final_podcast_{lang_code}_{DATE}.mp3\" type=\"audio/mpeg\">
    </audio>
  </body>
</html>""".encode("utf-8")

def generate_rss(lang_code):
    print("📰 Generating RSS feed...")
    mp3_url = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/{lang_code}/final_podcast_{lang_code}_{DATE}.mp3"
    html_url = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/{lang_code}/podcast_{DATE}.html"
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\"
     xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\"
     xmlns:atom=\"http://www.w3.org/2005/Atom\"
     xmlns:podcast=\"https://podcastindex.org/namespace/1.0\">
  <channel>
    <title>Daily Video Games Digest ({LANGUAGE_SETTINGS[lang_code]['name']})</title>
    <link>{html_url}</link>
    <language>{LANGUAGE_SETTINGS[lang_code]['locale']}</language>
    <description>Daily gaming news in {LANGUAGE_SETTINGS[lang_code]['name']}</description>
    <itunes:image href=\"{COVER_IMAGE_URL}\"/>
    <item>
      <title>Episode - {DATE}</title>
      <link>{html_url}</link>
      <description>AI-generated daily news in {LANGUAGE_SETTINGS[lang_code]['name']}.</description>
      <enclosure url=\"{mp3_url}\" type=\"audio/mpeg\"/>
      <guid>{html_url}</guid>
      <pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
    </item>
  </channel>
</rss>""".encode("utf-8")

def upload_to_pythonanywhere(lang_code, filename, content_bytes):
    url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/{lang_code}/{filename}"
    response = requests.post(url, headers=HEADERS_PYTHONANYWHERE, files={"content": content_bytes})
    if response.status_code != 200:
        raise RuntimeError(f"❌ Upload failed for {filename}: {response.text}")
    print(f"✅ Uploaded {filename} to /Podcast/{lang_code}/")

def main():
    english_text = fetch_script()
    lang_code = "fr"

    translated = translate_text(english_text, lang_code)
    audio_bytes_io = text_to_speech(translated, LANGUAGE_SETTINGS[lang_code]["voice_id"])

    print("🎵 Combining audio with intro/outro...")
    intro = AudioSegment.from_mp3(f"{BASE_DIR}/breaking-news-intro-logo-314320.mp3")
    voice = AudioSegment.from_file(audio_bytes_io, format="mp3")
    combined = intro + voice + intro

    final_audio_io = BytesIO()
    combined.export(final_audio_io, format="mp3")
    final_audio_io.seek(0)

    html_bytes = generate_html(lang_code)
    rss_bytes = generate_rss(lang_code)

    upload_to_pythonanywhere(lang_code, f"final_podcast_{lang_code}_{DATE}.mp3", final_audio_io)
    upload_to_pythonanywhere(lang_code, f"podcast_{DATE}.html", html_bytes)
    upload_to_pythonanywhere(lang_code, f"rss_{lang_code}.xml", rss_bytes)

    print(f"✅ Done processing {LANGUAGE_SETTINGS[lang_code]['name']} podcast!")

if __name__ == "__main__":
    main()
