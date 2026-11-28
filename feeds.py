"""
Feeds Module
Fetches, filters (24-48 hours), deduplicates by IOC and threat topic,
and selects 3-5 cybersecurity news stories with priority on:
1. Thailand-related cybersecurity incidents/advisories (ThaiCERT, NCSA, Thai orgs).
2. Vendors/Products: Palo Alto Networks, Fortinet, Cisco.
3. Critical/High-danger threats: 0-day, active exploitation, KEV, remote code execution.
4. If no priority stories exist, selects other critical/dangerous threats.
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

# Priority vendors & products requested by user (Palo Alto, Fortinet, Cisco)
PRIORITY_VENDORS = {
    # Palo Alto Networks
    "palo alto": 50,
    "palo": 40,
    "pan-os": 50,
    "panos": 50,
    "globalprotect": 50,
    "cortex xdr": 40,
    "prisma access": 40,
    "prisma cloud": 40,
    "wildfire": 35,
    "expedition": 40,

    # Fortinet
    "fortinet": 50,
    "fortios": 50,
    "fortigate": 50,
    "fortimanager": 50,
    "fortianalyzer": 40,
    "forticlient": 45,
    "fortisiem": 40,
    "fortiweb": 40,
    "fortimail": 35,

    # Cisco
    "cisco": 50,
    "ios xe": 50,
    "ios-xe": 50,
    "ios xr": 45,
    "anyconnect": 50,
    "cisco secure client": 45,
    "firepower": 45,
    "cisco asa": 50,
    "broadworks": 45,
    "webex": 35,
    "duo security": 35,
    "cisco talos": 30
}

# High-severity / extreme danger keywords ("อันตรายมากๆ")
SEVERITY_KEYWORDS = {
    # Active exploitation / 0-day (อันตรายสูงสุด)
    "zero-day": 30,
    "0-day": 30,
    "actively exploited": 30,
    "active exploitation": 30,
    "under active exploit": 30,
    "in the wild": 25,
    "cisa kev": 25,
    "known exploited": 25,
    "mass exploitation": 22,

    # Critical impact (RCE, Unauthenticated, Max Severity)
    "remote code execution": 22,
    "rce": 22,
    "unauthenticated": 20,
    "pre-auth": 20,
    "pre-authentication": 20,
    "arbitrary code": 20,
    "critical vulnerability": 18,
    "maximum severity": 18,
    "cvss 9": 18,
    "cvss 10": 18,

    # Severe attacks & actor threats
    "ransomware": 15,
    "supply chain attack": 15,
    "backdoor": 14,
    "nation-state": 12,
    "apt": 10,
    "privilege escalation": 10,
    "authentication bypass": 12,
    "auth bypass": 12,
    "data breach": 8,
    "cve-": 6,
    "exploit": 5
}

# Major entity keywords to detect duplicate topic coverage across different news outlets
COMMON_ENTITIES = [
    "cisco broadworks", "cisco", "openwave", "n-able", "n-central",
    "apache http/2", "apache", "zoom workplace", "zoom", "maersk",
    "screenconnect", "xen orchestra", "citrix", "ivanti", "outlook",
    "microsoft exchange", "exchange server", "sharepoint", "near ai",
    "sglang", "qubole", "ebpf", "baker tilly", "qlik sense", "asus",
    "whitearmor", "qilin", "turla", "antifox", "fortinet", "fortios",
    "fortigate", "palo alto", "pan-os", "globalprotect", "crowdstrike",
    "checkpoint", "sonicwall", "confluence", "jira", "gitlab"
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

# Thailand-related keywords (English & Thai) to prioritize local incidents & advisories
THAILAND_WORD_KEYWORDS = [
    "thailand", "thai", "bangkok", "thaicert", "ncsa", "etda", "pdpa",
    "thai sec", "bank of thailand", "kasikorn", "scb", "krungthai", "bangkok bank",
    "ptt", "ais", "dtac", "truecorp", "chulalongkorn", "mahidol"
]
THAILAND_SUBSTRING_KEYWORDS = [
    "ประเทศไทย", "ไทย", "กรุงเทพ", "สกมช",
    ".go.th", ".co.th", ".ac.th", ".or.th", ".mi.th", ".in.th"
]

# General cybersecurity terms used to filter out non-cyber noise from Google News feeds
CYBER_RELEVANCE_KEYWORDS = [
    "cyber", "hack", "hacker", "hackers", "hacking", "malware", "ransomware",
    "phishing", "breach", "data leak", "leaked", "vulnerability", "vulnerabilities",
    "zero-day", "0-day", "cve-", "exploit", "apt", "trojan", "botnet", "ddos",
    "infostealer", "stealer", "espionage", "backdoor", "thaicert", "ncsa",
    "check point", "fortinet", "cisco", "palo alto", "threat actor", "scam",
    "ไซเบอร์", "แฮก", "มัลแวร์", "ช่องโหว่", "ข้อมูลรั่ว"
]

def check_priority_vendor(text: str) -> bool:
    """Checks if text mentions Palo Alto Networks, Fortinet, or Cisco products."""
    text_lower = text.lower()
    for vendor_kw in PRIORITY_VENDORS:
        pattern = r"\b" + re.escape(vendor_kw) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False

def check_thailand_related(text: str) -> bool:
    """Checks if text mentions Thailand, Thai organizations, or .th domains."""
    text_lower = text.lower()
    for kw in THAILAND_SUBSTRING_KEYWORDS:
        if kw in text_lower:
            return True
    for kw in THAILAND_WORD_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False

def is_cybersecurity_relevant(text: str) -> bool:
    """Checks if an article from a general news feed is genuinely about cybersecurity."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in CYBER_RELEVANCE_KEYWORDS)

def calculate_article_score(title: str, summary: str) -> int:
    """
    Calculates an importance score based on:
    1. Thailand-related cyber incidents/advisories
    2. Priority vendors (Palo Alto, Fortinet, Cisco)
    3. High severity / dangerous threat keywords
    """
    combined = (title + " " + summary).lower()
    title_lower = title.lower()
    score = 0

    # 0. Thailand Relevance Boost
    if check_thailand_related(title_lower):
        score += 60
    elif check_thailand_related(combined):
        score += 40

    # 1. Priority Vendors Boost
    for kw, weight in PRIORITY_VENDORS.items():
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, title_lower):
            score += weight + 30  # Stronger boost if mentioned in title
        elif re.search(pattern, combined):
            score += weight

    # 2. High Severity / Extreme Danger Keywords
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
    Evaluates how detailed and critical an article is.
    Heavily rewards:
    1. Thailand-related cyber incidents/advisories -> +250 bonus
    2. Priority vendors (Palo Alto, Fortinet, Cisco) -> +150 bonus
    3. CVEs and IOCs presence
    4. Threat severity and content depth
    """
    iocs = article.get("extracted_iocs", {})
    cves = iocs.get("cves", [])
    total_iocs = sum(len(v) for v in iocs.values())
    summary_len = len(article.get("summary", ""))

    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    is_priority = check_priority_vendor(text)
    is_thailand = check_thailand_related(text)
    thailand_boost = 250.0 if is_thailand else 0.0
    vendor_boost = 150.0 if is_priority else 0.0

    score = (
        thailand_boost +                       # Highest priority for Thailand-related cyber news
        vendor_boost +                         # Top priority for Palo, Fortinet, Cisco
        len(cves) * 30.0 +                     # CVE presence
        total_iocs * 10.0 +                    # Other IOCs (IP, Hash)
        article.get("score", 0) * 1.5 +        # Base threat & severity score
        min(summary_len / 40.0, 15.0)          # Richer text content
    )
    return score

def are_articles_duplicate(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """
    Determines if two articles report on the same security incident/vulnerability.
    Checks:
    1. Direct IOC/CVE overlap (e.g. sharing CVE-2026-20320)
    2. Shared specific target entities (e.g. Cisco BroadWorks, FortiOS, N-central)
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
            if e1 in ["n-central", "n-able", "screenconnect", "openwave", "maersk", "ebpf", "sglang", "xen orchestra", "fortios", "fortigate", "pan-os"] and e1 == e2:
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
    prioritizes Palo Alto / Fortinet / Cisco and high-danger threats,
    and returns 3 to 5 unique, non-overlapping articles.
    """
    for art in articles:
        text = art["title"] + " " + art["summary"]
        art["extracted_iocs"] = extract_iocs_from_text(text)
        art["entities"] = extract_article_entities(art["title"], art["summary"])
        art["is_priority_vendor"] = check_priority_vendor(text)
        art["is_thailand"] = check_thailand_related(text)
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

    # For each cluster, pick the article with the highest detail score
    cluster_best: List[Dict[str, Any]] = []
    for cluster in clusters:
        best_art = max(cluster, key=lambda x: x["detail_score"])
        cluster_best.append(best_art)

    # Sort the unique stories by detail_score descending
    cluster_best = sorted(cluster_best, key=lambda x: x["detail_score"], reverse=True)

    # Reserve up to 2 top slots for Thailand-related news (if any exist) so they are
    # always included alongside global critical threats without crowding out all 5 slots.
    thailand_stories = [art for art in cluster_best if art.get("is_thailand")][:2]
    other_stories = [art for art in cluster_best if art not in thailand_stories]
    selected = (thailand_stories + other_stories)[:max_n]
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

        # For general search feeds like Google News, require both Thailand & cybersecurity relevance
        if "google news" in source_name.lower():
            combined_text = f"{title} {summary}"
            if not (check_thailand_related(combined_text) and is_cybersecurity_relevant(combined_text)):
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
    prioritizes Palo Alto / Fortinet / Cisco and dangerous threats,
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

    # Deduplicate and rank: Prioritize Palo/Fortinet/Cisco -> Critical/Dangerous threats -> General
    selected = deduplicate_and_rank_articles(all_articles, min_n=min_stories, max_n=top_n)
    return selected
