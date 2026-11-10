"""
Feeds Module
Fetches, filters (24-48 hours), deduplicates, and ranks cybersecurity news from global RSS feeds.
"""
import calendar
from datetime import datetime, timezone, timedelta
import html
import re
import ssl
import time
import urllib.request
from typing import Any, Dict, List, Optional
import feedparser
from dateutil import parser as date_parser

# Keyword weights for threat ranking
SEVERITY_KEYWORDS = {
    "zero-day": 10,
    "0-day": 10,
    "actively exploited": 9,
    "remote code execution": 8,
    "rce": 8,
    "ransomware": 7,
    "critical vulnerability": 7,
    "supply chain": 7,
    "data breach": 6,
    "backdoor": 6,
    "espionage": 6,
    "apt": 5,
    "malware": 5,
    "stealer": 5,
    "cve-": 5,
    "exploit": 4,
    "phishing": 3,
    "ddos": 2
}

def clean_html(raw_html: str) -> str:
    """Removes HTML tags and decodes HTML entities."""
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    clean_text = html.unescape(clean_text)
    return re.sub(r"\s+", " ", clean_text).strip()

def parse_entry_datetime(entry: Any) -> Optional[datetime]:
    """Extracts a timezone-aware UTC datetime from an RSS entry."""
    # Attempt 1: published_parsed struct_time
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            ts = calendar.timegm(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    # Attempt 2: updated_parsed struct_time
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            ts = calendar.timegm(entry.updated_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    # Attempt 3: string date parsing
    for date_key in ["published", "updated", "pubDate", "date"]:
        date_str = entry.get(date_key)
        if date_str:
            try:
                dt = date_parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                continue

    return None

def calculate_article_score(title: str, summary: str) -> int:
    """Calculates an importance score based on threat intelligence keywords."""
    combined = (title + " " + summary).lower()
    score = 0
    for keyword, weight in SEVERITY_KEYWORDS.items():
        if keyword in combined:
            score += weight
    # Boost if CVE identifier is found
    if re.search(r"cve-\d{4}-\d{4,}", combined):
        score += 8
    return score

def is_duplicate_title(title: str, existing_titles: List[str]) -> bool:
    """Checks if a similar title has already been selected."""
    def tokenize(s: str) -> set:
        words = re.findall(r"\b\w{4,}\b", s.lower())
        return set(words)

    words1 = tokenize(title)
    if not words1:
        return False

    for existing in existing_titles:
        words2 = tokenize(existing)
        if not words2:
            continue
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0.45:  # Over 45% significant word overlap
            return True
    return False

def fetch_feed_articles(source_name: str, feed_url: str, time_window_hours: int = 24) -> List[Dict[str, Any]]:
    """Fetches and parses articles from a single RSS feed within the given time window."""
    articles = []
    ssl_context = ssl._create_unverified_context()
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        req = urllib.request.Request(feed_url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=12, context=ssl_context) as response:
            raw_data = response.read()
            feed = feedparser.parse(raw_data)
    except Exception as e:
        print(f"[-] Warning: Failed to fetch {source_name} ({feed_url}): {e}")
        return articles

    now_utc = datetime.now(timezone.utc)
    cutoff_time = now_utc - timedelta(hours=time_window_hours)

    for entry in feed.entries:
        pub_dt = parse_entry_datetime(entry)
        # If date is available, apply time window filter
        if pub_dt and pub_dt < cutoff_time:
            continue

        title = clean_html(entry.get("title", ""))
        link = entry.get("link", "")
        summary = clean_html(entry.get("summary", "") or entry.get("description", ""))

        if not title or not link:
            continue

        score = calculate_article_score(title, summary)

        articles.append({
            "source": source_name,
            "title": title,
            "link": link,
            "summary": summary,
            "published": pub_dt.isoformat() if pub_dt else "Recent",
            "score": score
        })

    return articles

def get_top_cyber_news(feed_sources: List[Dict[str, Any]], time_window_hours: int = 24, top_n: int = 5) -> List[Dict[str, Any]]:
    """Aggregates all enabled feeds, deduplicates, and returns top N highest scored articles."""
    all_articles = []
    for source in feed_sources:
        if not source.get("enabled", True):
            continue
        name = source["name"]
        url = source["url"]
        fetched = fetch_feed_articles(name, url, time_window_hours=time_window_hours)
        all_articles.extend(fetched)

    # Sort primarily by score descending, then by publication date if available
    all_articles.sort(key=lambda x: (x["score"], x["published"]), reverse=True)

    selected: List[Dict[str, Any]] = []
    existing_titles: List[str] = []

    for article in all_articles:
        if is_duplicate_title(article["title"], existing_titles):
            continue
        selected.append(article)
        existing_titles.append(article["title"])
        if len(selected) >= top_n:
            break

    return selected
