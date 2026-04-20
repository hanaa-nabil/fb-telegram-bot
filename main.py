import time
import json
import os
import requests
from datetime import datetime, timedelta
from facebook_scraper import get_posts
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
INTERVAL_HOURS = 3
SEEN_IDS_FILE = "seen_ids.json"
MAX_WORKERS = 10  # scrape 10 groups at the same time

GROUPS = [
    "1LWfnmYHWa", "18dUy6VAFu", "1DdqGBqiWq", "17Tw2E97bJ",
    "1BTRjXf7Mv", "1DdJMjkquF", "18HJJ9iEE5", "188ySxCsxb",
    "1CKRtWmnXD", "1Aw2KsAERu", "1LP2wA4z5k", "1ArtK9P116",
    "18rpm4axBk", "1BX2VmdxD8", "1G1gg7zKTK", "1AsVSUxVz4",
    "1CyeTbxsw9", "18apqJGR1T", "1DmY5j1XXZ", "1J9Z5NwxLS",
    "1CmZfp2ELn", "1KoyMStxx4", "18ZUYUsP3L", "1Bj3f8gtNo",
    "1Gs4sPxAzW", "1DuC4uBUYd", "18MKydcP8P", "1Hqk1CpsRp",
    "18dTXsvUnA", "1CUREBoS8s", "1B2rZ6sQ3G", "17A5MeD2Vw",
    "1DUaXPjd22", "1NNuCywmcC", "1NXeLKxKFX", "1R7VsXgr61",
    "1C5c5FrX5c", "1QWhhwopNs", "1Cn5iNifat", "1beZQCT9yB",
    "18Mxn49kD6", "1AM4qymGMJ", "1af3gEk39w", "1B3iZ4uDfq",
    "1861NW6MWK", "18i451EGBr", "1DLLwzaZd9", "1E3BxcfhKy",
    "19uKdRkWXK", "18PBpVB6zW", "1GJtN3AWrx", "1Bi2wiyeTC",
    "18cCTTUgHv", "18i3hjMm24", "1E6vAanG7D", "1ceM8majox",
    "1NPX5nss2w", "1BHJiPoyQ3", "17WVK1fQbw", "1FpsPVFidS",
    "1AM4Mq3ecE", "1Cm5vQ2GBC", "1cH938c3yg",
    "pos.system.in.srilanka", "1674879619436812",
    "UIUXWebDesignerjobsinEgypt"
]

def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE, "r") as f:
            return json.load(f)
    return []

def save_seen_ids(seen_ids):
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(seen_ids[-500:], f)

def send_telegram(text, url, group):
    message = (
        f"📢 New post\n"
        f"👥 {group}\n\n"
        f"{text[:3000]}\n\n"
        f"🔗 {url}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message},
            timeout=10
        )
        print(f"✅ Sent post from {group}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def scrape_group(group, seen_ids, cutoff_time):
    new_posts = []
    try:
        for post in get_posts(group, 
    pages=3, 
    timeout=30,
    extra_info=False,
    youtube_dl=False):
            post_id = post.get("post_id") or post.get("post_url")
            text = post.get("text") or ""
            post_time = post.get("time")

            if not text or len(text.strip()) < 10:
                continue
            if post_id in seen_ids:
                continue
            if post_time and post_time < cutoff_time:
                continue

            new_posts.append({
                "id": post_id,
                "text": text,
                "url": post.get("post_url", ""),
                "group": group
            })

    except Exception as e:
        print(f"⚠️ Error scraping {group}: {e}")

    return new_posts

def main():
    print(f"🚀 Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    seen_ids = load_seen_ids()
    cutoff_time = datetime.now() - timedelta(hours=INTERVAL_HOURS)
    all_new_posts = []

    # Scrape all groups in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(scrape_group, group, seen_ids, cutoff_time): group
            for group in GROUPS
        }
        for future in as_completed(futures):
            posts = future.result()
            all_new_posts.extend(posts)

    # Remove duplicates by post ID
    seen_in_run = set()
    unique_posts = []
    for post in all_new_posts:
        if post["id"] not in seen_in_run:
            seen_in_run.add(post["id"])
            unique_posts.append(post)

    # Send to Telegram
    sent_count = 0
    for post in unique_posts:
        send_telegram(post["text"], post["url"], post["group"])
        seen_ids.append(post["id"])
        sent_count += 1
        time.sleep(1)

    save_seen_ids(seen_ids)
    print(f"\n✅ Done! Sent {sent_count} new posts.")

if __name__ == "__main__":
    main()
