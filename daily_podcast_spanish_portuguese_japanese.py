import os
import requests
import openai
from datetime import datetime, timezone
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

DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
SCRIPT_FILENAME = f"podcast_{DATE}.txt"
INTRO_MUSIC_URL = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/breaking-news-intro-logo-314320.mp3"
VOICE_ID = "Av6SEi7Xo7fWEjACu6Pr"
MODEL_ID = "eleven_multilingual_v2"

HEADERS_11 = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

HEADERS_PY = {
    "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
}

LANGUAGES = {
    "es": "Spanish",
    "pt": "Portuguese",
    "ja": "Japanese"
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
def translate_text(text, language):
prompt = (
    f"Translate the following podcast script into **natural, fluent {language}** with an **engaging, energetic, and conversational tone**. "
    f"Imagine it's being read aloud by a charismatic podcast host who’s passionate about video games. "
    f"Use casual, expressive, and dynamic language — like something you'd hear on a popular local gaming podcast. "
    f"Preserve the spirit, rhythm, and excitement of the original English content. "
    f"Avoid stiff or overly formal phrasing — make it sound authentic and fun for native {language} listeners.\n\n"
    f"{text}"
)

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# === ElevenLabs TTS ===
def generate_audio(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 1.0,
            "style": 0.0,
            "use_speaker_boost": True  # <-- Critical for fidelity
        }
    }
    response = requests.post(url, headers=HEADERS_11, json=payload)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception(f"TTS failed: {response.text}")

# === Combine Audio with loudnorm ===
def combine_audio(voice_audio_io):
    intro_response = requests.get(INTRO_MUSIC_URL)
    if intro_response.status_code != 200:
        raise Exception(f"Failed to download intro music: {intro_response.status_code} – {intro_response.text}")
    intro_audio = BytesIO(intro_response.content)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_raw:
        temp_raw.write(voice_audio_io.read())
        temp_raw.flush()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_norm:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", temp_raw.name,
                "-ar", "44100",
                "-af", "loudnorm",
                temp_norm.name
            ], check=True)

            normalized_voice = AudioSegment.from_wav(temp_norm.name)

    intro = AudioSegment.from_file(intro_audio, format="mp3")
    final_audio = intro + normalized_voice + intro

    output_io = BytesIO()
    final_audio.export(output_io, format="mp3")
    output_io.seek(0)
    return output_io

# === Upload to PythonAnywhere ===
def upload_to_pythonanywhere(filename, fileobj, lang_code):
    url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/{lang_code}/{filename}"
    fileobj.seek(0, os.SEEK_END)
    print(f"📁 Preparing to upload: {filename} ({fileobj.tell() / 1024:.1f} KB)")
    fileobj.seek(0)

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"🔁 Attempt {attempt} to upload {filename}...")
        response = requests.post(url, headers=HEADERS_PY, files={"content": fileobj})
        if response.status_code == 200:
            print(f"✅ Uploaded {filename} to PythonAnywhere.")
            return
        print(f"⚠️ Upload failed ({response.status_code}): {response.text or '[empty]'}")
        if attempt < max_retries:
            time.sleep(2)
            fileobj.seek(0)
        else:
            raise Exception(f"❌ Failed after 3 attempts: {filename}")

# === Generate HTML page ===
def generate_html(lang_code):
    titles = {
        "es": "El Flash Del Gaming",
        "pt": "Minuto Gamer",
        "ja": "ゲーミング・ミニッツ"
    }
    title = titles.get(lang_code, f"{LANGUAGES.get(lang_code, lang_code)} Gaming Podcast")

    return f"""<html>
  <head><title>{DATE} - {title}</title></head>
  <body>
    <h1>{DATE} - {title}</h1>
    <audio controls>
      <source src="final_podcast_{lang_code}_{DATE}.mp3" type="audio/mpeg">
    </audio>
  </body>
</html>"""


# === Generate RSS ===
def generate_rss(lang_code):
    base_url = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com/Podcast/{lang_code}/"
    cover_url = f"{base_url}podcast-cover-{lang_code}.png"

    titles = {
        "es": "El Flash Del Gaming",
        "pt": "Minuto Gamer",
        "ja": "ゲーミング・ミニッツ"
    }

    descriptions = {
        "es": "Un podcast diario con las noticias más importantes del mundo de los videojuegos, en español.",
        "pt": "Um podcast diário com as principais notícias do mundo dos videogames, em português.",
        "ja": "毎日のゲーム業界ニュースを日本語でお届けするAI生成ポッドキャスト。"
    }

    summaries = {
        "es": "El Flash Del Gaming — noticias rápidas del mundo gamer en español, generadas por IA.",
        "pt": "Minuto Gamer — notícias rápidas do mundo gamer em português, geradas por IA.",
        "ja": "ゲーミング・ミニッツ — 毎日配信、AIが読み上げる日本語のゲームニュース。"
    }

    title = titles.get(lang_code, f"Daily Video Games Digest ({LANGUAGES.get(lang_code, lang_code)})")
    description = descriptions.get(lang_code, f"Daily video game news podcast in {LANGUAGES.get(lang_code, lang_code)}.")
    summary = summaries.get(lang_code, f"AI-generated daily gaming news in {LANGUAGES.get(lang_code, lang_code)}.")

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\"
     xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\"
     xmlns:atom=\"http://www.w3.org/2005/Atom\"
     xmlns:podcast=\"https://podcastindex.org/namespace/1.0\">
  <channel>
    <title>{title}</title>
    <link>{base_url}</link>
    <language>{lang_code}</language>
    <description>{description}</description>
    <itunes:author>Dany Waksman</itunes:author>
    <itunes:owner>
      <itunes:name>Dany Waksman</itunes:name>
      <itunes:email>dany.waksman@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:summary>{summary}</itunes:summary>
    <itunes:explicit>no</itunes:explicit>
    <podcast:locked>yes</podcast:locked>
    <itunes:image href=\"{cover_url}\"/>
    <itunes:category text=\"Technology\"/>
    <itunes:category text=\"Leisure\">
      <itunes:category text=\"Video Games\"/>
    </itunes:category>
    <item>
      <title>{title} - {DATE}</title>
      <link>{base_url}podcast_{DATE}.html</link>
      <description><![CDATA[{description}]]></description>
      <enclosure url=\"{base_url}final_podcast_{lang_code}_{DATE}.mp3\" type=\"audio/mpeg\" />
      <guid>{base_url}podcast_{DATE}.html</guid>
      <pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
      <itunes:author>Dany Waksman</itunes:author>
    </item>
  </channel>
</rss>"""


# === Main ===
def main():
    print("📥 Fetching English script...")
    script = fetch_english_script()

    for lang_code, language in LANGUAGES.items():
        print(f"\n🌍 Translating to {language}...")
        translated = translate_text(script, language)

        print("🔊 Generating voice audio...")
        voice_mp3 = generate_audio(translated)

        print("🎵 Combining with intro/outro...")
        final_audio_io = combine_audio(voice_mp3)

        print("☁️ Uploading MP3...")
        upload_to_pythonanywhere(f"final_podcast_{lang_code}_{DATE}.mp3", final_audio_io, lang_code)

        print("📜 Uploading HTML...")
        html = generate_html(lang_code)
        upload_to_pythonanywhere(f"podcast_{DATE}.html", BytesIO(html.encode("utf-8")), lang_code)

        print("📡 Uploading RSS...")
        rss = generate_rss(lang_code)
        upload_to_pythonanywhere(f"rss_{lang_code}.xml", BytesIO(rss.encode("utf-8")), lang_code)

        print(f"✅ {language} version published!")

if __name__ == "__main__":
    main()
