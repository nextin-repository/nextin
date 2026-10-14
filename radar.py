import os, re, json, time, html, difflib, requests, feedparser

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]
SHEET_URL = os.environ.get("SHEET_WEBHOOK_URL", "")
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

# Feeds that are always one pillar, even without a keyword match
DEFAULT_PILLAR = {
    "OpenAI": "AI & Models",
    "DeepMind": "AI & Models",
    "Hugging Face": "AI & Models",
    "NASA": "Space & Science",
}

PILLARS = {
    "AI & Models": [
        "ai", "artificial intelligence", "gpt", "chatgpt", "claude", "gemini", "llm", "llms",
        "openai", "anthropic", "deepmind", "copilot", "chatbot", "chatbots", "agent", "agents",
        "model", "models", "neural", "machine learning", "mistral", "llama", "grok",
        "deepseek", "hugging face", "generative", "meta ai",
    ],
    "Hardware & Gadgets": [
        "chip", "chips", "gpu", "gpus", "nvidia", "amd", "intel", "qualcomm", "iphone",
        "android", "samsung", "pixel", "smartphone", "laptop", "headset", "wearable",
        "smartwatch", "robot", "robots", "robotics", "semiconductor", "tsmc", "processor",
        "battery", "apple", "vision pro", "quantum", "smart glasses",
    ],
    "Space & Science": [
        "nasa", "isro", "esa", "spacex", "rocket", "moon", "lunar", "mars", "telescope",
        "satellite", "asteroid", "astronomers", "astronaut", "orbit", "black hole",
        "scientists", "researchers", "physics", "fusion", "dna", "climate",
    ],
    "Tech, Work & Money": [
        "layoff", "layoffs", "jobs", "hiring", "salary", "startup", "startups", "funding",
        "raises", "ipo", "valuation", "revenue", "stock", "shares", "earnings", "acquires",
        "acquisition", "billion", "unicorn", "workers", "remote work",
    ],
}

PATTERNS = {
    name: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    for name, words in PILLARS.items()
}


def pillar_of(title, summary, source):
    text = title + " " + summary
    best, best_score = None, 0
    for name, pat in PATTERNS.items():
        # headline words count double
        score = 2 * len(pat.findall(title)) + len(pat.findall(summary))
        if score > best_score:
            best, best_score = name, score
    return best or DEFAULT_PILLAR.get(source)


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()[:220]


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f), True
    return [], False


def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT,
            "text": text,
            "link_preview_options": json.dumps({"is_disabled": True}),
        },
        timeout=20,
    )
    if not r.ok:
        print("Telegram error", r.status_code, r.text[:200])


def log_to_sheet(rows):
    if not SHEET_URL or not rows:
        return
    try:
        r = requests.post(SHEET_URL, json={"rows": rows}, timeout=30)
        print("Sheet response:", r.status_code)
    except Exception as e:
        print("Sheet failed:", e)


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
            if ts and now - time.mktime(ts) > MAX_AGE_HOURS * 3600:
                continue
            title = clean(e.get("title", ""))
            summary = clean(e.get("summary", ""))
            pillar = pillar_of(title, summary, source)
            if not pillar:
                continue  # off-pillar: muted
            new_items.append({
                "title": title, "link": e.get("link", ""), "summary": summary,
                "pillar": pillar, "sources": [source],
            })

    if not existed:
        send("NEXT IN radar is live. I will message you when real stories appear.")
    else:
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
            hot = "🔥 " if len(g["sources"]) > 1 else ""
            send(f"{hot}{g['pillar']}\n{g['title']}\n{', '.join(g['sources'])}\n{g['link']}")

        stamp = time.strftime("%Y-%m-%d %H:%M", time.gmtime(now + 19800)) + " IST"
        log_to_sheet([
            [stamp, g["pillar"], g["title"], ", ".join(g["sources"]), len(g["sources"]), g["link"], g["summary"]]
            for g in groups
        ])

    with open(SEEN_FILE, "w") as f:
        json.dump(seen[-3000:], f)


main()
