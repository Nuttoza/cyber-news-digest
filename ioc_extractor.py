"""
IOC (Indicator of Compromise) Extractor Module
Extracts and defangs CVEs, Hashes (MD5, SHA1, SHA256), IPs, Domains, and URLs.
"""
import ipaddress
import re
from typing import Dict, List, Set

CVE_REGEX = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
SHA256_REGEX = re.compile(r"\b[a-fA-F0-9]{64}\b")
SHA1_REGEX = re.compile(r"\b[a-fA-F0-9]{40}\b")
MD5_REGEX = re.compile(r"\b[a-fA-F0-9]{32}\b")
IPV4_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Well-known benign public IPs to exclude
BENIGN_IPS = {
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9",
    "208.67.222.222", "208.67.220.220", "127.0.0.1", "0.0.0.0"
}

def defang_ip(ip: str) -> str:
    """Defangs an IP address by replacing the last dot with [.]"""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}[.]{parts[3]}"
    return ip.replace(".", "[.]")

def defang_url(url: str) -> str:
    """Defangs a URL: http -> hxxp, https -> hxxps, . -> [.]"""
    url = re.sub(r"^http://", "hxxp://", url, flags=re.IGNORECASE)
    url = re.sub(r"^https://", "hxxps://", url, flags=re.IGNORECASE)
    return url.replace(".", "[.]")

def defang_domain(domain: str) -> str:
    """Defangs a domain name: example.com -> example[.]com"""
    if "." in domain:
        last_dot = domain.rfind(".")
        return domain[:last_dot] + "[.]" + domain[last_dot+1:]
    return domain

def is_valid_public_ip(ip_str: str) -> bool:
    """Checks if a string is a valid public, non-reserved IPv4 address."""
    if ip_str in BENIGN_IPS:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local)
    except ValueError:
        return False

def extract_iocs_from_text(text: str) -> Dict[str, List[str]]:
    """
    Extracts CVEs, Hashes, and Public IPs from raw text.
    Returns a dictionary of deduplicated and sorted indicators.
    """
    if not text:
        return {"cves": [], "sha256": [], "sha1": [], "md5": [], "ips": []}

    cves: Set[str] = {cve.upper() for cve in CVE_REGEX.findall(text)}
    
    sha256_matches = set(SHA256_REGEX.findall(text))
    # Filter out sha256 false positives from sha1 and md5
    remaining_text = SHA256_REGEX.sub(" ", text)
    sha1_matches = set(SHA1_REGEX.findall(remaining_text))
    remaining_text = SHA1_REGEX.sub(" ", remaining_text)
    md5_matches = set(MD5_REGEX.findall(remaining_text))

    raw_ips = set(IPV4_REGEX.findall(text))
    valid_ips = [defang_ip(ip) for ip in raw_ips if is_valid_public_ip(ip)]

    return {
        "cves": sorted(list(cves)),
        "sha256": sorted(list(sha256_matches)),
        "sha1": sorted(list(sha1_matches)),
        "md5": sorted(list(md5_matches)),
        "ips": sorted(valid_ips)
    }

def format_iocs_summary(ioc_dict: Dict[str, List[str]]) -> str:
    """
    Formats the extracted IOCs dictionary into a human-readable string.
    Returns 'ไม่มี' if no significant IOCs were detected.
    """
    lines = []
    if ioc_dict.get("cves"):
        lines.append(f"CVE: {', '.join(ioc_dict['cves'])}")
    if ioc_dict.get("sha256"):
        lines.append(f"SHA-256: {', '.join(ioc_dict['sha256'][:3])}")
    if ioc_dict.get("sha1"):
        lines.append(f"SHA-1: {', '.join(ioc_dict['sha1'][:3])}")
    if ioc_dict.get("md5"):
        lines.append(f"MD5: {', '.join(ioc_dict['md5'][:3])}")
    if ioc_dict.get("ips"):
        lines.append(f"IP: {', '.join(ioc_dict['ips'][:3])}")

    if not lines:
        return "ไม่มี"
    return "\n".join(lines)
