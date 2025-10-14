import os
import re
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Recipe site domains
RECIPE_DOMAINS = [
    "allrecipes.com", "foodnetwork.com", "epicurious.com", "seriouseats.com",
    "thekitchn.com", "cookinglight.com", "simplyrecipes.com", "onceuponachef.com",
    "smittenkitchen.com", "budgetbytes.com", "cookingclassy.com", "eatyourselfskinny.com",
    "saltandlavender.com", "americastestkitchen.com", "skinnytaste.com", "joyofbaking.com",
    "tasteofhome.com", "halfbakedharvest.com", "minimalistbaker.com", "leitesculinaria.com",
    "thepioneerwoman.com", "gimmesomeoven.com", "dinneratthezoo.com", "cafejohnny.com",
    "pinchofyum.com"
]

RECIPE_SEEDS = [
    "https://www.allrecipes.com/", "https://www.foodnetwork.com/recipes",
    "https://www.epicurious.com/", "https://www.seriouseats.com/recipes",
    "https://www.thekitchn.com/", "https://www.cookinglight.com/recipes",
    "https://www.simplyrecipes.com/", "https://www.onceuponachef.com/",
    "https://www.smittenkitchen.com/", "https://www.budgetbytes.com/",
    "https://www.cookingclassy.com/", "https://www.eatyourselfskinny.com/",
    "https://www.saltandlavender.com/", "https://www.americastestkitchen.com/browse",
    "https://www.skinnytaste.com/", "https://www.joyofbaking.com/",
    "https://www.tasteofhome.com/", "https://www.halfbakedharvest.com/",
    "https://minimalistbaker.com/recipes/", "https://leitesculinaria.com/",
    "https://www.thepioneerwoman.com/food-cooking/", "https://www.gimmesomeoven.com/",
    "https://www.dinneratthezoo.com/", "https://www.cafejohnny.com/", "https://pinchofyum.com/"
]

# Non-recipe sites
NONRECIPE_DOMAINS = [
    "nytimes.com", "bbc.com", "cnn.com", "reuters.com", "apnews.com",
    "theguardian.com", "washingtonpost.com", "npr.org", "forbes.com", "bloomberg.com",
    "cnet.com", "wired.com", "techcrunch.com", "arstechnica.com", "theverge.com",
    "vox.com", "nationalgeographic.com", "history.com", "sciencenews.org",
    "smithsonianmag.com", "time.com", "usatoday.com", "huffpost.com", "medium.com",
    "theatlantic.com"
]

NONRECIPE_SEEDS = [
    "https://www.nytimes.com/", "https://www.bbc.com/", "https://www.cnn.com/",
    "https://www.reuters.com/", "https://apnews.com/", "https://www.theguardian.com/",
    "https://www.washingtonpost.com/", "https://www.npr.org/", "https://www.forbes.com/",
    "https://www.bloomberg.com/", "https://www.cnet.com/", "https://www.wired.com/",
    "https://techcrunch.com/", "https://arstechnica.com/", "https://www.theverge.com/",
    "https://www.vox.com/", "https://www.nationalgeographic.com/", "https://www.history.com/",
    "https://www.sciencenews.org/", "https://www.smithsonianmag.com/", "https://time.com/",
    "https://www.usatoday.com/", "https://www.huffpost.com/", "https://medium.com/",
    "https://www.theatlantic.com/"
]

HEADERS = {
    "User-Agent": "recipe-reader/1.2 (+https://github.com/j01t3d/recipe-reader/)"
}

TOTAL_RECIPE_PAGES = TOTAL_NONRECIPE_PAGES = 5000
MIN_SIZE = 2000   # ~2 KB
MAX_SIZE = 300000 # ~300 KB, should prevent gigantic GIGABYTE FILES from downloading
THREADS = 5
RETRIES = 2
RETRY_DELAY = 1   # seconds

totalCount = 0

RECIPE_PER_SITE = TOTAL_RECIPE_PAGES // len(RECIPE_DOMAINS)
NONRECIPE_PER_SITE = TOTAL_NONRECIPE_PAGES // len(NONRECIPE_SEEDS)

lock = Lock()  # thread-safe printing

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def normalize_url(url):
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return normalized

def make_filename(url):
    parsed = urlparse(url)
    path = parsed.path.replace("/", "_").strip("_") or "index"
    hash_part = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{parsed.netloc}_{path[:80]}_{hash_part}.txt"

def fetch_page(url):
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=(3, 5))
            if resp.status_code == 200:
                return resp.text
            time.sleep(RETRY_DELAY)
        except:
            time.sleep(RETRY_DELAY)
    return None

def scrape_worker(seed_url, domain, out_folder, max_pages, visited_global):
    global totalCount
    queue = deque([seed_url])
    count = 0
    local_visited = set()

    while queue and count < max_pages:
        url = normalize_url(queue.popleft())
        if url in local_visited or url in visited_global:
            continue
        page_html = fetch_page(url)
        if not page_html:
            continue

        text = clean_text(page_html)

        sizeFlag = len(text) < MIN_SIZE or len(text) > MAX_SIZE

        if sizeFlag:
            continue

        fname = make_filename(url)
        with lock:
            os.makedirs(out_folder, exist_ok=True)
            with open(os.path.join(out_folder, fname), "w", encoding="utf-8") as f:
                f.write(text)
            visited_global.add(url)
            count += 1
            totalCount += 1
            print(f"[{out_folder}] Scraped {round(round(totalCount)/(TOTAL_RECIPE_PAGES + TOTAL_NONRECIPE_PAGES)*10000)/100}%, {count}/{max_pages}: {url}")

        soup = BeautifulSoup(page_html, "html.parser")
        for a in soup.find_all("a", href=True):
            full = normalize_url(urljoin(url, a['href']))
            parsed_full = urlparse(full)
            if domain:
                if domain in parsed_full.netloc and full not in visited_global:
                    queue.append(full)
            else:
                if full not in visited_global:
                    queue.append(full)
        time.sleep(0.3)  # polite delay

def scrape_sites(seeds, domains, out_folder, per_site):
    visited_global = set()
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for domain, seed in zip(domains, seeds):
            futures.append(executor.submit(scrape_worker, seed, domain, out_folder, per_site, visited_global))
        for _ in as_completed(futures):
            pass

def main():
    print("Scraping recipe sites...")
    scrape_sites(RECIPE_SEEDS, RECIPE_DOMAINS, "recipes", RECIPE_PER_SITE)

    print("Scraping non-recipe sites...")
    scrape_sites(NONRECIPE_SEEDS, NONRECIPE_DOMAINS, "nonrecipes", NONRECIPE_PER_SITE)

    print("Scraping completed.")

if __name__ == "__main__":
    main()
