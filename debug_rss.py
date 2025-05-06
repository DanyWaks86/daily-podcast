import feedparser
import datetime
import os
import subprocess

# === SSH Key Restoration Block ===
SSH_PRIVATE_KEY = os.environ.get("SSH_PRIVATE_KEY", "")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH", "/tmp/ssh_key")

with open(SSH_KEY_PATH, "w") as key_file:
    key_file.write(SSH_PRIVATE_KEY)
os.chmod(SSH_KEY_PATH, 0o600)

# === RSS Feed Sources ===
FEEDS = {
    "IGN": "https://feeds.ign.com/ign/all",
    "GameSpot": "https://www.gamespot.com/feeds/news/",
    "Polygon": "https://www.polygon.com/rss/index.xml",
    "Kotaku": "https://kotaku.com/rss"
}

# === Output Filename ===
OUTPUT_FILE = "rss_articles.txt"

# Optional: spoof user-agent to avoid 403s
HEADERS = {"User-Agent": "Mozilla/5.0 (RSS Fetcher)"}

def fetch_articles():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"RSS Fetch Run: {now}\n"]

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            if not feed.entries:
                lines.append(f"[{source}] - FAILED (No articles)\n")
                continue

            lines.append(f"\n[{source}] - {len(feed.entries)} articles:\n")
            for entry in feed.entries[:5]:  # limit to 5 for test
                title = entry.get("title", "No Title")
                link = entry.get("link", "No Link")
                lines.append(f" - {title}\n   {link}\n")

        except Exception as e:
            lines.append(f"[{source}] - FAILED ({str(e)})\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines([line + "\n" for line in lines])

def push_to_pythonanywhere():
    username = os.environ["SSH_USERNAME"]
    hostname = os.environ["SSH_HOSTNAME"]
    remote_path = f"/home/{username}/Podcast/rss_articles.txt"

    subprocess.run([
        "scp",
        "-i", SSH_KEY_PATH,
        OUTPUT_FILE,
        f"{username}@{hostname}:{remote_path}"
    ])

if __name__ == "__main__":
    fetch_articles()
    push_to_pythonanywhere()
