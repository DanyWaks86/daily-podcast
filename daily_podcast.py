import os
import io
import requests
import subprocess
from datetime import datetime, timedelta
from pydub import AudioSegment
import yagmail

# === CONFIGURATION ===
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.environ.get("OPENAI_PROJECT_ID")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
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

TODAY = datetime.now().strftime('%Y-%m-%d')

def fetch_gaming_news():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    url = (
        f"https://newsapi.org/v2/everything?"
        f"from={yesterday}&"
        f"sortBy=popularity&"
        f"language=en&"
        f"pageSize=15&"
        f"domains=ign.com,kotaku.com,polygon.com,eurogamer.net,gamesradar.com,gamesindustry.biz&"
        f"apiKey={NEWSAPI_KEY}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch news: {response.text}")
        return []
    return response.json().get('articles', [])

def generate_script(articles):
    articles_text = ""
    for article in articles:
        title = article.get('title', '')
        description = article.get('description', '')
        source = article.get('source', {}).get('name', '')
        link = article.get('url', '')
        articles_text += f"Title: {title}\nSummary: {description}\nSource: {source}\nLink: {link}\n\n"

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

{articles_text}
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
    return response.json().get('choices', [{}])[0].get('message', {}).get('content', ''), articles

def text_to_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("❌ ElevenLabs TTS Error:", response.text)
        return None
    return response.content

def save_audio_with_intro_outro(audio_data, filename_base):
    intro = AudioSegment.from_file(os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3"), format="mp3") - 8
    voice = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
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

def generate_show_notes(articles, date_str):
    html_content = f"""<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>Daily Video Games Digest – {date_str}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 20px; }}
        h1 {{ color: #333; }}
        ul {{ line-height: 1.6; }}
        footer {{ margin-top: 40px; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <h1>Daily Video Games Digest – {date_str}</h1>
    <p>Welcome to today's episode! Here are the articles we talked about:</p>
    <ul>
"""
    for article in articles:
        title = article.get('title', 'No title')
        link = article.get('url', '#')
        source = article.get('source', {}).get('name', 'Unknown')
        html_content += f"        <li><a href=\"{link}\">{title}</a> – Source: {source}</li>\n"

    html_content += f"""
    </ul>
    <h2>🎧 Listen to the episode:</h2>
    <audio controls>
        <source src=\"{BASE_URL}final_podcast_{date_str}.mp3\" type=\"audio/mpeg\">
        Your browser does not support the audio element.
    </audio>
    <footer>
        <p>Subscribe on your favorite platform: Apple Podcasts, Spotify, Amazon Music.</p>
    </footer>
</body>
</html>"""
    with open(os.path.join(PODCAST_DIR, f"podcast_{date_str}.html"), "w") as f:
        f.write(html_content)

def update_rss():
    files = sorted(
        [f for f in os.listdir(PODCAST_DIR) if f.startswith("final_podcast_") and f.endswith(".mp3")],
        reverse=True
    )[:MAX_EPISODES]

    rss_items = ""
    for f in files:
        date_part = f.replace("final_podcast_", "").replace(".mp3", "")
        try:
            pub_date = datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue
        rss_items += f"""
    <item>
      <title>{pub_date.strftime('%B %d')} - Gaming News Digest</title>
      <link>{BASE_URL}podcast_{date_part}.html</link>
      <description><![CDATA[Gaming news highlights summarized by Dany Waksman. Full articles at: {BASE_URL}final_podcast_{date_part}.mp3]]></description>
      <enclosure url=\"{BASE_URL}final_podcast_{date_part}.mp3\" length=\"5000000\" type=\"audio/mpeg\" />
      <guid>{date_part}</guid>
      <pubDate>{pub_date.strftime('%a, %d %b %Y 06:00:00 GMT')}</pubDate>
    </item>
    """

    rss_feed = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\">
  <channel>
    <title>Daily Video Games Digest</title>
    <link>{BASE_URL}</link>
    <description>Quick daily updates on the biggest video game announcements, sales data, player milestones, and reviews. Hosted by Dany Waksman and powered by AI.</description>
    <language>en-us</language>
    <copyright>Dany Waksman 2025</copyright>
    <itunes:author>Dany Waksman</itunes:author>
    <itunes:owner>
      <itunes:name>Dany Waksman</itunes:name>
      <itunes:email>hatunadv@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:image href=\"https://danywaks.pythonanywhere.com/Podcast/podcast-cover.png\"/>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text=\"Leisure\">
      <itunes:category text=\"Video Games\" />
    </itunes:category>
    <itunes:category text=\"News\">
      <itunes:category text=\"Daily News\" />
      <itunes:category text=\"Tech News\" />
    </itunes:category>
{rss_items}
  </channel>
</rss>"
    with open(os.path.join(PODCAST_DIR, RSS_FILENAME), "w") as f:
        f.write(rss_feed)

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
    headers = {
        "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
    }
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/"

    for filename in [
        f"final_podcast_{TODAY}.mp3",
        f"podcast_{TODAY}.html",
        "breaking-news-intro-logo-314320.mp3",
        "rss.xml",
        "test.txt",
    ]:
        local_path = os.path.join(PODCAST_DIR, filename)
        with open(local_path, "rb") as f:
            response = requests.post(upload_url + filename, headers=headers, files={"content": f})
            if response.status_code != 200:
                print(f"❌ Failed to upload {filename}: {response.text}")
            else:
                print(f"✅ Uploaded {filename} to PythonAnywhere.")

# === MAIN PROCESS ===
print("📰 Fetching gaming articles...")
articles = fetch_gaming_news()
if not articles:
    print("❌ No articles found.")
    exit()
print(f"✅ Fetched {len(articles)} articles.")

print("🧠 Generating podcast script...")
script, articles_used = generate_script(articles)
if not script:
    print("❌ Failed to generate script.")
    exit()

print("🎙️ Converting script to audio...")
audio_data = text_to_speech(script)
if not audio_data:
    print("❌ No audio data returned from TTS engine.")
    exit()
print("✅ Audio data received!")

os.makedirs(PODCAST_DIR, exist_ok=True)
final_filename = save_audio_with_intro_outro(audio_data, TODAY)

print("📝 Generating show notes page...")
generate_show_notes(articles_used, TODAY)

print("📬 Sending podcast email...")
send_email_with_podcast(final_filename)

print("🛠️ Updating RSS feed...")
update_rss()

print("🚀 Pushing podcast folder to PythonAnywhere...")
push_to_pythonanywhere_api()

print("✅ Done!")
