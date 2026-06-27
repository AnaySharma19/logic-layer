import os
import json
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from logiclayer.trusted_sources.scraper import scrape_url_text

# Paths relative to the project root
CONFIG_PATH = Path("logiclayer/config/whitelisted_domains.json")
DB_PATH = Path("local-knowledge-base/knowledge_base.db")
FACTS_DIR = Path("local-knowledge-base/facts")

def load_whitelist():
    """Loads approved domain structures out of configuration blocks."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("domains", [])
    return []

def search_trusted_sources(query: str):
    """
    Searches via DuckDuckGo, restricts results tightly to whitelisted domains or .gov sites,
    scrapes content, normalizes the data shape, and caches hits locally.
    """
    print(f"🌐 Activating Trusted Source Search Layer for: '{query}'...")
    whitelist = load_whitelist()
    
    # Construct an organic search request targeting our domains
    search_url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    data = {"q": query}
    
    try:
        res = requests.post(search_url, data=data, headers=headers, timeout=10)
        if res.status_code != 200:
            print("❌ Search engine temporary failure.")
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("a", class_="result__url")
        
        valid_url = None
        valid_domain = None
        
        # 1. Look through results and enforce the strict domain architecture guardrail
        for r in results:
            url = r.get("href", "").strip()
            if not url or "duckduckgo.com" in url:
                continue
                
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower().replace("www.", "")
            
            # Match strictly against whitelist or any fallback .gov domain
            if domain in whitelist or domain.endswith(".gov"):
                valid_url = url
                valid_domain = domain
                break
                
        if not valid_url:
            print("🛑 Search hit open web links, but zero items matched the secure domain whitelist.")
            return None
            
        print(f"🎯 Whitelist Match Found: {valid_url}")
        
        # 2. Scrape the text out of the matching url
        scraped_content = scrape_url_text(valid_url)
        if not scraped_content:
            print("❌ Failed to parse body text from matching url source.")
            return None
            
        # 3. Normalize into the exact same layout tuple matching check_local_db
        # (claim, value, source_name)
        fact_id = f"fact_{uuid.uuid4().hex[:6]}"
        source_id = f"src_{uuid.uuid4().hex[:6]}"
        source_name = f"{valid_domain.capitalize()} Reference"
        
        normalized_result = (query, scraped_content[:200], source_name)
        
        # 4. Cache it back locally to disk as new JSON artifacts so it auto-seeds
        FACTS_DIR.mkdir(parents=True, exist_ok=True)
        Path("local-knowledge-base/sources").mkdir(parents=True, exist_ok=True)
        
        source_data = {
            "source_id": source_id,
            "name": source_name,
            "url": valid_url
        }
        fact_data = {
            "fact_id": fact_id,
            "claim": query,
            "value": scraped_content[:200],
            "source_id": source_id
        }
        
        with open(Path(f"local-knowledge-base/sources/{source_id}.json"), "w") as f:
            json.dump(source_data, f, indent=4)
        with open(Path(f"local-knowledge-base/facts/{fact_id}.json"), "w") as f:
            json.dump(fact_data, f, indent=4)
            
        print(f"💾 Fresh lookup results successfully cached into local JSON fact stores!")
        return normalized_result
        
    except Exception as e:
        print(f"💥 Trusted Source runtime lookup error: {e}")
        return None