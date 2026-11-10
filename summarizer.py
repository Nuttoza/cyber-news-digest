"""
Summarizer Module
Connects to Gemini API to translate and summarize cybersecurity news into Thai (1-2 lines)
and verify/extract Indicators of Compromise (IOCs).
"""
import json
import os
import re
from typing import Any, Dict, List
import requests

from ioc_extractor import extract_iocs_from_text, format_iocs_summary

SYSTEM_PROMPT = """คุณคือนักวิเคราะห์ภัยคุกคามทางไซเบอร์ (Cyber Threat Intelligence Analyst) มืออาชีพ
หน้าที่ของคุณคืออ่านข่าวความปลอดภัยทางไซเบอร์ สรุปและแปลเป็นภาษาไทย โดยต้องตอบกลับเป็น JSON เท่านั้น
รูปแบบ JSON Schema:
{
  "thai_title": "หัวข้อข่าวภาษาไทยที่กระชับและเข้าใจง่าย (พร้อมชื่อภาษาอังกฤษเดิมในวงเล็บ)",
  "thai_summary": "สรุปเนื้อหาสำคัญ 1-2 บรรทัด อธิบายว่าเกิดเหตุการณ์อะไร ผลกระทบระดับไหน และข้อแนะนำรับมือ",
  "iocs": "รายการ IOC เช่น CVE, SHA256/MD5 Hash, C2 IP, Malicious Domain (ให้ defang เช่น 1.1.1[.]1 หรือ hxxps) หากไม่มีให้ใส่คำว่า 'ไม่มี'"
}
ข้อกำหนดสำคัญ:
1. รักษาศัพท์เทคนิคให้ถูกต้อง เช่น Zero-day, Ransomware, RCE, Supply Chain, Phishing
2. 'thai_summary' ต้องมีความยาวไม่เกิน 1-2 บรรทัด กระชับ ตรงประเด็น
3. ตรวจสอบ IOC ให้แม่นยำ ห้ามกุขึ้นมาเองเด็ดขาด ถ้าไม่มีให้ตอบว่า 'ไม่มี'
"""

def call_gemini_api(api_key: str, model_name: str, article: Dict[str, Any]) -> Dict[str, str]:
    """Calls Gemini REST API to process an article with automatic model fallback and retry."""
    import time

    candidate_models = [model_name]
    for fallback_model in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
        if fallback_model not in candidate_models:
            candidate_models.append(fallback_model)

    headers = {"Content-Type": "application/json"}
    user_content = f"""วิเคราะห์ข่าวไซเบอร์ต่อไปนี้:
ชื่อข่าว: {article.get('title', '')}
แหล่งที่มา: {article.get('source', '')}
เนื้อหา/สรุป: {article.get('summary', '')}
ลิงก์: {article.get('link', '')}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT + "\n\n" + user_content}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    last_error = None
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=25)
                if response.status_code == 200:
                    data = response.json()
                    text_result = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_result)
                elif response.status_code in (429, 503):
                    time.sleep(1.5)
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    continue
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    break
            except Exception as err:
                last_error = str(err)
                time.sleep(1.0)
                continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

def summarize_article(article: Dict[str, Any], api_key: str = "", model_name: str = "gemini-2.5-flash") -> Dict[str, str]:
    """
    Summarizes an article. Uses Gemini API if API key is present.
    Otherwise, falls back to regex-based IOC extraction and heuristic title/summary.
    """
    raw_text = f"{article.get('title', '')} {article.get('summary', '')}"
    extracted_iocs = extract_iocs_from_text(raw_text)
    regex_ioc_str = format_iocs_summary(extracted_iocs)

    if api_key and api_key.strip():
        try:
            ai_data = call_gemini_api(api_key, model_name, article)
            thai_title = ai_data.get("thai_title", article.get("title", ""))
            thai_summary = ai_data.get("thai_summary", article.get("summary", "")[:150])
            iocs = ai_data.get("iocs", regex_ioc_str)
            if iocs.strip() == "" or iocs.lower() == "none":
                iocs = regex_ioc_str

            return {
                "title": thai_title,
                "summary": thai_summary,
                "iocs": iocs,
                "link": article.get("link", ""),
                "source": article.get("source", ""),
                "published": article.get("published", "")
            }
        except Exception as e:
            print(f"[-] AI Summarization warning ({article.get('source')}): {e}. Using fallback summarizer.")

    # Fallback when no API key or API call fails
    summary_text = article.get("summary", "")
    if len(summary_text) > 180:
        summary_text = summary_text[:180].rsplit(" ", 1)[0] + "..."

    return {
        "title": f"{article.get('title', '')}",
        "summary": summary_text or "ไม่มีรายละเอียดเนื้อหาเพิ่มเติม",
        "iocs": regex_ioc_str,
        "link": article.get("link", ""),
        "source": article.get("source", ""),
        "published": article.get("published", "")
    }

def process_all_articles(articles: List[Dict[str, Any]], api_key: str = "", model_name: str = "gemini-2.5-flash") -> List[Dict[str, str]]:
    """Processes a list of raw articles into formatted digests."""
    results = []
    for idx, art in enumerate(articles, 1):
        print(f"[*] Processing news #{idx}/{len(articles)}: {art.get('title', '')[:50]}...")
        processed = summarize_article(art, api_key=api_key, model_name=model_name)
        results.append(processed)
    return results
