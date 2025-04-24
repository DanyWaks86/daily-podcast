import os
import requests
import subprocess
from datetime import datetime, timedelta
from pydub import AudioSegment
import yagmail
from gtts import gTTS

# === STEP 2: Restore SSH private key from env variable ===
if "SSH_PRIVATE_KEY" in os.environ:
    os.makedirs("/opt/render/.ssh", exist_ok=True)
    with open("/opt/render/.ssh/id_pythonanywhere", "w") as f:
        f.write(os.environ["SSH_PRIVATE_KEY"])
    os.chmod("/opt/render/.ssh/id_pythonanywhere", 0o600)

# === CONFIGURATION ===
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.environ.get("OPENAI_PROJECT_ID")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")
SSH_USERNAME = os.environ.get("SSH_USERNAME")
SSH_HOSTNAME = os.environ.get("SSH_HOSTNAME")
SSH_KEY_PATH = "/opt/render/.ssh/id_pythonanywhere"
SSH_PRIVATE_KEY = os.environ.get("SSH_PRIVATE_KEY")

PODCAST_DIR = "/opt/render/project/src/podcast/"
BASE_URL = "https://daily-podcast-files.onrender.com/podcast/"
RSS_FILENAME = "rss.xml"
MAX_EPISODES = 14

# === STEP 1: Set up SSH Key ===
if SSH_PRIVATE_KEY:
    os.makedirs("/opt/render/.ssh", exist_ok=True)
    with open(SSH_KEY_PATH, "w") as f:
        f.write(SSH_PRIVATE_KEY)
    os.chmod(SSH_KEY_PATH, 0o600)

# === STEP 2: Disable strict SSH host checking ===
ssh_config_path = "/opt/render/.ssh/config"
os.makedirs("/opt/render/.ssh", exist_ok=True)
with open(ssh_config_path, "w") as f:
    f.write(f"""
Host pythonanywhere
    HostName {SSH_HOSTNAME}
    User {SSH_USERNAME}
    IdentityFile {SSH_KEY_PATH}
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
""")
os.chmod(ssh_config_path, 0o600)

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
    return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        temp_path = os.path.join(PODCAST_DIR, f"raw_audio_{datetime.now().strftime('%Y-%m-%d')}.mp3")
        tts.save(temp_path)
        with open(temp_path, "rb") as f:
            return f.read()
    except Exception as e:
        print(f"❌ gTTS TTS Error: {e}")
        return None

def save_audio_with_intro_outro(raw_audio_path, filename_base):
    intro = AudioSegment.from_file(os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3"), format="mp3") - 8
    voice = AudioSegment.from_file(raw_audio_path, format="mp3")
    combined = intro + voice + intro  # reuse intro as outro
    final_filename = os.path.join(PODCAST_DIR, f"final_podcast_{filename_base}.mp3")
    combined.export(final_filename, format="mp3")
    return final_filename

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
      <description>Gaming news highlights summarized by Dany Waksman. Listen now.</description>
      <enclosure url=\"{BASE_URL}{f}\" length=\"5000000\" type=\"audio/mpeg\" />
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
      <itunes:email>dany.waksman@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:image href=\"{BASE_URL}podcast-cover.jpg\" />
{rss_items}
  </channel>
</rss>"""
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

def scp_to_pythonanywhere(local_file):
    remote_path = f"/home/{SSH_USERNAME}/podcast/"
    scp_cmd = f"scp -F /opt/render/.ssh/config {local_file} pythonanywhere:{remote_path}"
    print(f"🔐 SCPing {local_file} to PythonAnywhere...")
    subprocess.run(scp_cmd, shell=True)

def push_to_pythonanywhere():
    print("🚀 Pushing podcast folder to PythonAnywhere...")
    files_to_push = [
        f"{PODCAST_DIR}final_podcast_{datetime.now().strftime('%Y-%m-%d')}.mp3",
        f"{PODCAST_DIR}raw_audio_{datetime.now().strftime('%Y-%m-%d')}.mp3",
        f"{PODCAST_DIR}{RSS_FILENAME}",
        os.path.join(PODCAST_DIR, "breaking-news-intro-logo-314320.mp3"),
        os.path.join(PODCAST_DIR, "test.txt")
    ]
    for file in files_to_push:
        scp_to_pythonanywhere(file)

# === MAIN PROCESS ===
print("📰 Fetching gaming articles...")
articles = fetch_gaming_news()
if not articles:
    print("❌ No articles found.")
    exit()
print(f"✅ Fetched {len(articles)} articles.")

print("🧠 Generating podcast script...")
script = generate_script(articles)
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
raw_audio_path = os.path.join(PODCAST_DIR, f"raw_audio_{datetime.now().strftime('%Y-%m-%d')}.mp3")
with open(raw_audio_path, "wb") as f:
    f.write(audio_data)

print("🎧 Saving final podcast with intro/outro...")
final_filename = save_audio_with_intro_outro(raw_audio_path, datetime.now().strftime('%Y-%m-%d'))

print("📬 Sending podcast email...")
send_email_with_podcast(final_filename)

print("🛠️ Updating RSS feed...")
update_rss()

print("🚀 Pushing podcast folder to PythonAnywhere...")
push_to_pythonanywhere()

print("✅ Done!")
