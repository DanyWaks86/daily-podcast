import os
import requests
from datetime import datetime, timedelta

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
PYTHONANYWHERE_USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN")
OUTPUT_FILENAME = "articles-yesterday-test.txt"

DOMAINS = [
    "ign.com", "kotaku.com", "polygon.com", "eurogamer.net",
    "gamerant.com", "gamesradar.com", "destructoid.com",
    "pcgamer.com", "vg247.com", "gamesindustry.biz"
]

def fetch_articles():
    all_articles = []
    from_time = (datetime.utcnow() - timedelta(hours=48)).isoformat(timespec="seconds") + "Z"
    to_time = (datetime.utcnow() - timedelta(hours=24)).isoformat(timespec="seconds") + "Z"
    for domain in DOMAINS:
        url = (
            f"https://newsapi.org/v2/everything?"
            f"from={from_time}&to={to_time}&"
            f"sortBy=publishedAt&"
            f"language=en&"
            f"pageSize=10&"
            f"domains={domain}&"
            f"apiKey={NEWSAPI_KEY}"
        )
        try:
            response = requests.get(url)
            if response.status_code == 200:
                articles = response.json().get("articles", [])
                for art in articles:
                    art["source_domain"] = domain
                all_articles.extend(articles)
        except Exception as e:
            print(f"❌ Failed fetching from {domain}: {e}")
    return all_articles

def format_article_list(articles):
    lines = [f"Total articles: {len(articles)}\n"]
    for art in articles:
        title = art.get("title", "No title")
        url = art.get("url", "")
        source = art.get("source", {}).get("name", "Unknown")
        published = art.get("publishedAt", "No date")
        lines.append(f"- [{source}] {title}")
        lines.append(f"  Published: {published}")
        lines.append(f"  URL: {url}")
        lines.append("")
    return "\n".join(lines)

def push_to_pythonanywhere(content):
    headers = {"Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"}
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/{OUTPUT_FILENAME}"
    response = requests.post(upload_url, headers=headers, files={"content": content.encode("utf-8")})
    print(f"📡 Upload response [{response.status_code}]: {response.text}")

def main():
    print("📅 Fetching articles from 'yesterday' (UTC)...")
    articles = fetch_articles()
    print(f"✅ Retrieved {len(articles)} articles.")
    content = format_article_list(articles)
    print("📤 Uploading to PythonAnywhere as 'articles-yesterday.txt'...")
    push_to_pythonanywhere(content)
    print("✅ Done!")

if __name__ == "__main__":
    main()
