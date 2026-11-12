"""
Feeds Module
Fetches, filters (24-48 hours), deduplicates by IOC and threat topic,
and selects the top 3-5 most detailed, non-overlapping cybersecurity news stories.
"""
import calendar
from datetime import datetime, timezone, timedelta
import html
import re
import ssl
import time
import urllib.request
from typing import Any, Dict, List, Optional, Set
import feedparser
from dateutil import parser as date_parser

from ioc_extractor import extract_iocs_from_text

# Keyword weights for threat ranking
SEVERITY_KEYWORDS = {
    "zero-day": 12,
    "0-day": 12,
    "actively exploited": 10,
    "remote code execution": 9,
    "rce": 9,
    "ransomware": 8,
    "critical vulnerability": 8,
    "supply chain": 7,
    "data breach": 6,
    "backdoor": 6,
    "espionage": 6,
    "apt": 5,
    "malware": 5,
    "stealer": 5,
    "cve-": 6,
    "exploit": 4,
    "phishing": 3,
    "ddos": 2
}

# Major entity keywords to detect duplicate topic coverage across different news outlets
COMMON_ENTITIES = [
    "cisco broadworks", "cisco", "openwave", "n-able", "n-central",
    "apache http/2", "apache", "zoom workplace", "zoom", "maersk",
    "screenconnect", "xen orchestra", "citrix", "ivanti", "outlook",
    "microsoft exchange", "exchange server", "sharepoint", "near ai",
    "sglang", "qubole", "ebpf", "baker tilly", "qlik sense", "asus",
    "whitearmor", "qilin", "turla", "antifox", "fortinet", "palo alto",
    "crowdstrike", "checkpoint", "sonicwall", "confluence", "jira", "gitlab"
]

def clean_html(raw_html: str) -> str:
    """Removes HTML tags and decodes HTML entities."""
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    clean_text = html.unescape(clean_text)
    return re.sub(r"\s+", " ", clean_text).strip()

def parse_entry_datetime(entry: Any) -> Optional[datetime]:
    """Extracts a timezone-aware UTC datetime from an RSS entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            ts = calendar.timegm(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            ts = calendar.timegm(entry.updated_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

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
    if re.search(r"cve-\d{4}-\d{4,}", combined):
        score += 8
    return score

def extract_article_entities(title: str, summary: str) -> Set[str]:
    """Extracts known product, vendor, or threat actor entities."""
    combined = (title + " " + summary).lower()
    found = set()
    for ent in COMMON_ENTITIES:
        if ent in combined:
            found.add(ent)
    return found

def get_article_detail_score(article: Dict[str, Any]) -> float:
    """
    Evaluates how detailed an article is.
    Heavily rewards presence of CVEs and unique IOCs, content depth, and threat severity.
    Used to pick the superior article when duplicates on the same story exist.
    """
    iocs = article.get("extracted_iocs", {})
    cves = iocs.get("cves", [])
    total_iocs = sum(len(v) for v in iocs.values())
    summary_len = len(article.get("summary", ""))

    score = (
        len(cves) * 35.0 +                     # More CVEs = significantly higher detail
        total_iocs * 12.0 +                    # Other IOCs (IP, Hash)
        article.get("score", 0) * 1.5 +        # Base threat score
        min(summary_len / 40.0, 15.0)          # Richer text content
    )
    return score

def are_articles_duplicate(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """
    Determines if two articles report on the same security incident/vulnerability.
    Checks:
    1. Direct IOC/CVE overlap (e.g. sharing CVE-2026-20320)
    2. Shared specific target entities (e.g. Cisco BroadWorks, N-central, ScreenConnect)
    3. High title similarity on non-generic words
    """
    # 1. Direct CVE overlap
    cves_a = set(a.get("extracted_iocs", {}).get("cves", []))
    cves_b = set(b.get("extracted_iocs", {}).get("cves", []))
    if cves_a and cves_b and (cves_a & cves_b):
        return True

    # 2. IP / Hash overlap
    ips_a = set(a.get("extracted_iocs", {}).get("ips", []))
    ips_b = set(b.get("extracted_iocs", {}).get("ips", []))
    if ips_a and ips_b and (ips_a & ips_b):
        return True

    # 3. Entity overlap
    ent_a = a.get("entities", set())
    ent_b = b.get("entities", set())
    for e1 in ent_a:
        for e2 in ent_b:
            if " " in e1 and (e1 == e2 or e1 in e2 or e2 in e1):
                return True
            if e1 in ["n-central", "n-able", "screenconnect", "openwave", "maersk", "ebpf", "sglang", "xen orchestra"] and e1 == e2:
                return True

    # 4. Title keyword overlap (excluding generic security stopwords)
    def get_keywords(text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_-]{4,}\b", text.lower())
        stopwords = {
            "flaw", "flaws", "vulnerability", "vulnerabilities", "attack", "attacks",
            "critical", "security", "patch", "patches", "actively", "exploited", "exploit",
            "threat", "actors", "hacker", "hackers", "remote", "could", "after", "before",
            "discovery", "update", "updates", "releases", "fixes", "fixed", "allows", "target"
        }
        return {w for w in words if w not in stopwords}

    kw_a = get_keywords(a["title"])
    kw_b = get_keywords(b["title"])
    if kw_a and kw_b:
        shared = kw_a & kw_b
        if len(shared) >= 2:
            return True
        if len(shared) >= 1 and (len(shared) / min(len(kw_a), len(kw_b)) >= 0.5):
            return True

    return False

def deduplicate_and_rank_articles(articles: List[Dict[str, Any]], min_n: int = 3, max_n: int = 5) -> List[Dict[str, Any]]:
    """
    Groups articles by story topic/IOC, picks the single most detailed article per cluster,
    and returns 3 to 5 unique, non-overlapping articles.
    """
    for art in articles:
        text = art["title"] + " " + art["summary"]
        art["extracted_iocs"] = extract_iocs_from_text(text)
        art["entities"] = extract_article_entities(art["title"], art["summary"])
        art["detail_score"] = get_article_detail_score(art)

    # Sort candidates by detail score descending
    candidates = sorted(articles, key=lambda x: x["detail_score"], reverse=True)

    clusters: List[List[Dict[str, Any]]] = []

    for art in candidates:
        matched_cluster = None
        for cluster in clusters:
            if any(are_articles_duplicate(art, existing) for existing in cluster):
                matched_cluster = cluster
                break
        if matched_cluster is not None:
            matched_cluster.append(art)
        else:
            clusters.append([art])

    selected: List[Dict[str, Any]] = []

    # From each unique cluster, pick the article with the highest detail score (richest IOCs/info)
    for cluster in clusters:
        best_art = max(cluster, key=lambda x: x["detail_score"])
        selected.append(best_art)
        if len(selected) >= max_n:
            break

    return selected

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

def get_top_cyber_news(feed_sources: List[Dict[str, Any]], time_window_hours: int = 24, top_n: int = 5, min_stories: int = 3) -> List[Dict[str, Any]]:
    """
    Aggregates all enabled feeds, deduplicates stories sharing the same IOC or incident,
    and returns 3 to 5 unique, non-overlapping articles with the highest detail.
    """
    all_articles = []
    for source in feed_sources:
        if not source.get("enabled", True):
            continue
        name = source["name"]
        url = source["url"]
        fetched = fetch_feed_articles(name, url, time_window_hours=time_window_hours)
        all_articles.extend(fetched)

    if not all_articles:
        return []

    # Deduplicate by IOC/topic, selecting the most detailed version for each story (3 to 5 unique stories)
    selected = deduplicate_and_rank_articles(all_articles, min_n=min_stories, max_n=top_n)
    return selected
