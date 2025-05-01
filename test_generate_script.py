import os
import requests
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import json

# Config (make sure these env vars are set on Render)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.environ.get("OPENAI_PROJECT_ID")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
PYTHONANYWHERE_USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN")

PODCAST_DIR = "/opt/render/project/src/podcast/"
TODAY = "2025-05-01"
OUTPUT_FILENAME = f"test_{TODAY}.txt"

# 1. Fetch news
def fetch_articles():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    domains = ",".join([
        "ign.com", "kotaku.com", "polygon.com", "eurogamer.net",
        "gamerant.com", "gamesradar.com", "destructoid.com",
        "pcgamer.com", "vg247.com", "gamesindustry.biz"
    ])
    url = (
        f"https://newsapi.org/v2/everything?"
        f"from={yesterday}&"
        f"sortBy=publishedAt&"
        f"language=en&"
        f"pageSize=30&"
        f"domains={domains}&"
        f"apiKey={NEWSAPI_KEY}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch articles: {response.text}")
        return []
    return response.json().get("articles", [])

# 2. Group similar stories
def group_articles(articles, threshold=0.5):
    groups = []
    used = set()
    for i, a1 in enumerate(articles):
        if i in used:
            continue
        group = [a1]
        title1 = a1.get("title", "").lower()
        for j, a2 in enumerate(articles[i+1:], start=i+1):
            if j in used:
                continue
            title2 = a2.get("title", "").lower()
            if SequenceMatcher(None, title1, title2).ratio() > threshold:
                group.append(a2)
                used.add(j)
        used.add(i)
        groups.append(group)
    return sorted(groups, key=lambda g: len(g), reverse=True)[:6]

# 3. Generate GPT script
def generate_script(groups):
    articles_text = ""
    for group in groups:
        top = group[0]
        articles_text += f"Title: {top['title']}\nSummary: {top['description']}\nSource: {top['source']['name']}\nLink: {top['url']}\n\n"

    prompt = f"""You are generating a daily podcast script based on real gaming news articles. Follow these rules carefully:

1. Carefully read the articles provided.
2. Select and summarize only the **6 most important or impactful stories**.
3. For each story, **mention the news source** naturally (e.g., \"according to IGN\").
4. Write in a **natural, casual podcast tone**, as if you are personally telling listeners the day's biggest stories.
5. **Do not** use any headers like \"Story 1\" or Markdown formatting.
6. Focus on **delivering a tight and engaging podcast script that lasts approximately 4–5 minutes** total.

Start the podcast script with this exact intro:
\"Welcome to the Daily Video Games Digest. I'm Dany Waksman, a video game enthusiast, bringing you this AI-generated podcast to stay informed with the latest in the gaming world. Let's jump right into yesterday’s biggest stories, May 1st.”

End the podcast script with this exact outro:
\"Thanks for tuning into the Daily Video Games Digest. If you enjoyed today’s update, be sure to check back tomorrow for the latest in gaming news. Until then, happy gaming!\"

Here are the real articles:

{articles_text}
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": OPENAI_PROJECT_ID
    }
    payload = {
        "model": "gpt-4-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]

# 4. Push output to PythonAnywhere
def push_to_pythonanywhere(content):
    print("📤 Uploading to PythonAnywhere...")
    headers = {
        "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
    }
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/{OUTPUT_FILENAME}"

    response = requests.post(upload_url, headers=headers, files={"content": content.encode("utf-8")})
    if response.status_code == 200:
        print("✅ Upload successful.")
    else:
        print(f"❌ Upload failed: {response.text}")

# === RUN ===
print("🔎 Fetching articles...")
articles = fetch_articles()
if not articles:
    print("No articles retrieved.")
    exit()

print("🔗 Grouping articles...")
groups = group_articles(articles)

print("🧠 Generating script with GPT...")
script = generate_script(groups)

print("📝 Uploading test file...")
push_to_pythonanywhere(script)

print("✅ Test complete.")
