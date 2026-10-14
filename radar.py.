import os, json, time, difflib, requests, feedparser

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen.json"
MAX_SEND = 8
MAX_AGE_HOURS = 6

FEEDS = {
    "Techmeme": "https://www.techmeme.com/feed.xml",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News": "https://hnrss.org/frontpage?points=150",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "OpenAI": "https://openai.com/news/rss.xml",
    "DeepMind": "https://deepmind.google/blog/rss.xml",
    "NASA": "https://www.nasa.gov/feed/",
    "Inc42": "https://inc42.com/feed/",
}

PILLARS = {
    "AI & Models": ["ai", "gpt", "claude", "gemini", "llm", "model", "openai", "anthropic", "agent", "chatbot"],
    "Hardware & Gadgets": ["chip", "gpu", "nvidia", "iphone", "samsung", "phone", "laptop", "device", "wearable", "robot"],
    "Space & Science": ["nasa", "space", "isro", "rocket", "moon", "mars", "telescope", "research", "scientists"],
    "Tech, Work & Money": ["jobs", "layoff", "funding", "startup", "salary", "hiring", "stock", "revenue", "ipo"],
}


def pillar_of(title):
    t = " " + title.lower() + " "
    for name, words in PILLARS.items():
        if any(f" {w} " in t or f" {w}" in t for w in words):
            return name
    return "Other"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f), True
    return [], False


def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT, "text": text},
        timeout=20,
    )


def main():
    seen, existed = load_seen()
    seen_set = set(seen)
    now = time.time()
    new_items = []

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                print("No entries (check feed):", source)
                continue
        except Exception as e:
            print("Feed failed:", source, e)
            continue
        for e in feed.entries[:30]:
            uid = e.get("id") or e.get("link")
            if not uid or uid in seen_set:
                continue
            seen_set.add(uid)
            seen.append(uid)
            ts = e.get("published_parsed") or e.get("updated_parsed")
            age_ok = (not ts) or (now - time.mktime(ts) < MAX_AGE_HOURS * 3600)
            if age_ok:
                new_items.append({"title": e.get("title", "").strip(), "link": e.get("link", ""), "sources": [source]})

    if not existed:
        send("NEXT IN radar is live. I will message you when real stories appear.")
    else:
        # group similar headlines, count how many sources cover each story
        groups = []
        for item in new_items:
            for g in groups:
                if difflib.SequenceMatcher(None, g["title"].lower(), item["title"].lower()).ratio() > 0.6:
                    if item["sources"][0] not in g["sources"]:
                        g["sources"].append(item["sources"][0])
                    break
            else:
                groups.append(item)
        groups.sort(key=lambda g: len(g["sources"]), reverse=True)
        for g in groups[:MAX_SEND]:
            hot = "HOT " if len(g["sources"]) > 1 else ""
            send(f"{hot}[{pillar_of(g['title'])}] {g['title']}\nSources: {', '.join(g['sources'])}\n{g['link']}")

    with open(SEEN_FILE, "w") as f:
        json.dump(seen[-3000:], f)


main()
