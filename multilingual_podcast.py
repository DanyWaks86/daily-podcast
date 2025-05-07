import os
import openai
import requests
from datetime import datetime
from pydub import AudioSegment

# ENV variables expected: OPENAI_API_KEY, ELEVENLABS_API_KEY
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

BASE_DIR = "/home/DanyWaks/Podcast"
DATE = datetime.now().strftime("%Y-%m-%d")
ENGLISH_SCRIPT_PATH = f"{BASE_DIR}/en/podcast_{DATE}.txt"
INTRO_MUSIC_PATH = f"{BASE_DIR}/intro_music.mp3"

LANGUAGE_SETTINGS = {
    "fr": {"name": "French", "voice_id": "TxGEqnHWrfWFTfGW9XjX"},
    "es": {"name": "Spanish", "voice_id": "MF3mGyEYCl7XYWbV9V6O"},
    "pt": {"name": "Portuguese", "voice_id": "M7KjBV5hZY0TzF0D8OIK"},
    "de": {"name": "German", "voice_id": "oWAxZDx7w5VEj9dCyTzz"},
    "ja": {"name": "Japanese", "voice_id": "N3IP6t3n4Sn8tXg5Ggqe"},
}

HEADERS = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}


def translate_text(text, target_language):
    prompt = f"Translate this podcast script into {LANGUAGE_SETTINGS[target_language]['name']} with a natural, local tone:\n\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def text_to_speech(text, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print("❌ TTS error:", response.text)
        return None
    return response.content


def generate_rss(lang, date_str, title="Daily Video Games Digest"):
    folder = f"{BASE_DIR}/{lang}"
    mp3_url = f"https://danywaks.pythonanywhere.com/Podcast/{lang}/final_podcast_{date_str}.mp3"
    html_url = f"https://danywaks.pythonanywhere.com/Podcast/{lang}/podcast_{date_str}.html"
    rss_path = os.path.join(folder, f"rss_{lang}.xml")

    item = f"""
    <item>
      <title>{title} - {date_str}</title>
      <link>{html_url}</link>
      <description><![CDATA[Gaming news podcast in {LANGUAGE_SETTINGS[lang]['name']}]]></description>
      <enclosure url="{mp3_url}" type="audio/mpeg" />
      <guid>{html_url}</guid>
      <pubDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>
    </item>
    """
    
    with open(rss_path, 'w', encoding='utf-8') as f:
        f.write(f"""
        <rss version="2.0">
          <channel>
            <title>{title} ({LANGUAGE_SETTINGS[lang]['name']})</title>
            <link>{html_url}</link>
            <description>Daily gaming news in {LANGUAGE_SETTINGS[lang]['name']}</description>
            {item}
          </channel>
        </rss>
        """)


def main():
    with open(ENGLISH_SCRIPT_PATH, 'r', encoding='utf-8') as f:
        english_script = f.read()

    for lang_code, settings in LANGUAGE_SETTINGS.items():
        translated_text = translate_text(english_script, lang_code)
        print(f"Translated script to {settings['name']}")

        audio_bytes = text_to_speech(translated_text, settings["voice_id"])
        if not audio_bytes:
            continue

        folder = f"{BASE_DIR}/{lang_code}"
        os.makedirs(folder, exist_ok=True)

        tts_path = os.path.join(folder, f"tts_{DATE}.mp3")
        final_path = os.path.join(folder, f"final_podcast_{DATE}.mp3")
        html_path = os.path.join(folder, f"podcast_{DATE}.html")

        with open(tts_path, 'wb') as f:
            f.write(audio_bytes)

        tts_audio = AudioSegment.from_mp3(tts_path)
        intro_music = AudioSegment.from_mp3(INTRO_MUSIC_PATH)
        final_audio = intro_music + tts_audio
        final_audio.export(final_path, format="mp3")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(f"""
            <html>
              <head><title>{DATE} - {settings['name']} Gaming Podcast</title></head>
              <body>
                <h1>{DATE} - {settings['name']} Gaming Podcast</h1>
                <audio controls>
                  <source src="final_podcast_{DATE}.mp3" type="audio/mpeg">
                </audio>
              </body>
            </html>
            """)

        generate_rss(lang_code, DATE)
        print(f"✅ Generated podcast in {settings['name']}")


if __name__ == "__main__":
    main()
