import os
import requests
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# === CONFIGURATION ===
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.environ.get("OPENAI_PROJECT_ID")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
PYTHONANYWHERE_USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME")
PYTHONANYWHERE_API_TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN")

OUTPUT_FILENAME = "test-text.txt"

DOMAINS = [
    "ign.com", "kotaku.com", "polygon.com", "eurogamer.net",
    "gamerant.com", "gamesradar.com", "destructoid.com",
    "pcgamer.com", "vg247.com", "gamesindustry.biz"
]

KEYWORDS = [
    'layoffs', 'acquisition', 'merger', 'studio',
    'sold', 'units sold', 'sales', 'player count',
    'concurrent', 'review', 'metacritic', 'launch', 'released'
]

# === FUNCTIONS ===

def fetch_articles_by_domain():
    all_articles = []
    from_time = (datetime.utcnow() - timedelta(hours=24)).isoformat(timespec="seconds") + "Z"
    to_time = datetime.utcnow().isoformat(timespec="seconds") + "Z"
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
                all_articles.extend(articles)
            else:
                print(f"❌ Failed to fetch from {domain}: {response.status_code}")
        except Exception as e:
            print(f"❌ Exception fetching {domain}: {e}")
    return all_articles

def group_articles(articles, threshold=0.5):
    groups = []
    used = set()
    for i, a1 in enumerate(articles):
        if i in used:
            continue
        group = [a1]
        title1 = str(a1.get("title", "")).lower()
        for j, a2 in enumerate(articles[i+1:], start=i+1):
            if j in used:
                continue
            title2 = str(a2.get("title", "")).lower()
            if SequenceMatcher(None, title1, title2).ratio() > threshold:
                group.append(a2)
                used.add(j)
        used.add(i)
        groups.append(group)
    return groups

def score_group(group):
    text = " ".join(
        (str(a.get("title", "")) + " " + str(a.get("description", ""))).lower()
        for a in group
    )
    return sum(1 for kw in KEYWORDS if kw in text)

def generate_script(groups):
    articles_text = ""
    for group in groups:
        top = group[0]
        articles_text += f"Title: {top['title']}\nSummary: {top.get('description', '')}\nSource: {top['source']['name']}\nLink: {top['url']}\n\n"

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
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def push_to_pythonanywhere(content):
    headers = {
        "Authorization": f"Token {PYTHONANYWHERE_API_TOKEN}"
    }
    upload_url = f"https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/files/path/home/{PYTHONANYWHERE_USERNAME}/Podcast/{OUTPUT_FILENAME}"
    response = requests.post(upload_url, headers=headers, files={"content": content.encode("utf-8")})
    print(f"📡 Upload response [{response.status_code}]: {response.text}")
    if response.status_code == 200:
        print("✅ Upload successful.")
    else:
        print("⚠️ Upload may have issues.")

# === MAIN SCRIPT ===
def main():
    print("📥 Fetching gaming articles from the last 24 hours...")
    articles = fetch_articles_by_domain()
    print(f"✅ Retrieved {len(articles)} articles.")

    print("🔗 Grouping by similar titles...")
    grouped = group_articles(articles)
    print(f"✅ Formed {len(grouped)} topic clusters.")

    print("📊 Scoring topics by keyword relevance...")
    top_groups = sorted(grouped, key=score_group, reverse=True)[:6]

    print("🧠 Generating GPT script...")
    script = generate_script(top_groups)

    print("📤 Uploading script to PythonAnywhere as 'test-text.txt'...")
    push_to_pythonanywhere(script)

    print("✅ Done!")

if __name__ == "__main__":
    main()
