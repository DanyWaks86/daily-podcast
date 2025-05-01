import os
import requests
from datetime import datetime

PODCAST_DIR = "/opt/render/project/src/podcast/"
USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME")
TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN")
BASE_URL = f"https://{USERNAME}.pythonanywhere.com/Podcast/"
RSS_FILENAME = "rss.xml"
MAX_EPISODES = 14

def regenerate_rss():
    print("🔄 Regenerating RSS from existing MP3 files...")
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
      <enclosure url="{BASE_URL}final_podcast_{date_part}.mp3" length="5000000" type="audio/mpeg" />
      <guid>{date_part}</guid>
      <pubDate>{pub_date.strftime('%a, %d %b %Y 06:00:00 GMT')}</pubDate>
    </item>"""

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Daily Video Games Digest</title>
    <link>{BASE_URL}</link>
    <description>Daily video game news podcast, summarized and delivered by Dany Waksman.</description>
    <language>en-us</language>
    <ttl>1440</ttl>
{rss_items}
  </channel>
</rss>"""

    rss_path = os.path.join(PODCAST_DIR, RSS_FILENAME)
    with open(rss_path, "w", encoding="utf-8") as f:
        f.write(rss_feed)
    print("✅ RSS file regenerated.")

def upload_rss_to_pythonanywhere():
    print("🚀 Uploading RSS to PythonAnywhere...")
    headers = {
        "Authorization": f"Token {TOKEN}"
    }
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/files/path/home/{USERNAME}/Podcast/{RSS_FILENAME}"

    with open(os.path.join(PODCAST_DIR, RSS_FILENAME), "rb") as f:
        response = requests.post(upload_url, headers=headers, files={"content": f})
        if response.status_code == 200:
            print("✅ Successfully uploaded RSS to PythonAnywhere.")
        else:
            print(f"❌ Upload failed: {response.text}")

if __name__ == "__main__":
    regenerate_rss()
    upload_rss_to_pythonanywhere()
