"""
Summarizer Module
Connects to Gemini API to translate and summarize cybersecurity news into Thai,
verify/extract Indicators of Compromise (IOCs), analyze core impacts,
and provide actionable recommendations for SOC teams.
"""
import json
import os
import re
from typing import Any, Dict, List
import requests

from ioc_extractor import extract_iocs_from_text, format_iocs_summary

SYSTEM_PROMPT = """คุณคือนักวิเคราะห์ภัยคุกคามทางไซเบอร์ระดับยุทธศาสตร์ (Strategic Cyber Threat Intelligence Analyst) และผู้เชี่ยวชาญด้าน Security Operations Center (SOC)
หน้าที่ของคุณคืออ่านข่าวความปลอดภัยทางไซเบอร์ แปลสรุปเป็นภาษาไทย วิเคราะห์ผลกระทบ และเสนอแนวทางปฏิบัติสำหรับรายงานสถานการณ์ข่าวภัยคุกคามทางไซเบอร์
เพื่อให้เนื้อหาลงในตารางรายงาน 5 คอลัมน์ (ขนาดไม่เกิน 1 หน้ากระดาษ A4) ได้อย่างพอดี สวยงาม และกระชับ ตรงประเด็น

ให้ตอบกลับเป็น JSON Schema ตามรูปแบบนี้เท่านั้น:
{
  "thai_title": "หัวข้อข่าวภาษาไทยที่กระชับ ตรงประเด็น สละสลวย (ความยาวประมาณ 1-2 บรรทัด)",
  "iocs": "รหัส CVE ที่เกี่ยวข้อง หรือชื่อมัลแวร์/กลุ่มแฮกเกอร์/เทคนิค หรือ IOC สั้นๆ (ถ้าไม่มีให้ระบุ 'ไม่มี')",
  "key_points": [
    "สรุปสาระสำคัญและผลกระทบ ข้อ 1 (ประโยคสมบูรณ์ สั้นกระชับ 1 บรรทัด ไม่เกิน 15 คำ)",
    "สรุปสาระสำคัญและผลกระทบ ข้อ 2 (ประโยคสมบูรณ์ สั้นกระชับ 1 บรรทัด ไม่เกิน 15 คำ)",
    "สรุปสาระสำคัญและผลกระทบ ข้อ 3 (ประโยคสมบูรณ์ สั้นกระชับ 1 บรรทัด ไม่เกิน 15 คำ)"
  ],
  "recommendations": [
    "แนวทางป้องกัน/ข้อเสนอแนะ ข้อ 1 (Actionable นำไปทำได้จริง ประโยคสมบูรณ์ สั้นกระชับ 1 บรรทัด ไม่เกิน 15 คำ)",
    "แนวทางป้องกัน/ข้อเสนอแนะ ข้อ 2 (ประโยคสมบูรณ์ สั้นกระชับ 1 บรรทัด ไม่เกิน 15 คำ)",
    "แนวทางป้องกัน/ข้อเสนอแนะ ข้อ 3 (ประโยคสมบูรณ์ สั้นกระชับ 1 บรรทัด ไม่เกิน 15 คำ)"
  ],
  "source": "ชื่อแหล่งข่าวสั้นๆ เช่น BleepingComputer / The Hacker News / SecurityWeek"
}

ข้อกำหนดสำคัญมาก:
1. ตอบกลับเป็น JSON ภาษาไทยที่ถูกต้อง ห้ามใส่ markdown backticks ครอบ
2. ใช้ภาษาไทยที่เป็นทางการ สละสลวย ถูกต้องตามหลักไวยากรณ์และการตัดคำภาษาไทย ไม่ตัดคำขาดตอนจนเสียความหมาย
3. ใน 'key_points' และ 'recommendations' แต่ละข้อต้องเป็นประโยคที่สมบูรณ์ในตัวเอง ห้ามใส่สัญลักษณ์ bullet (•, -, *) และห้ามใส่เครื่องหมายขึ้นบรรทัดใหม่ (\\n) ในข้อความ
4. ใน 'recommendations' ให้ระบุแนวทางป้องกัน การเฝ้าระวัง หรือข้อเสนอแนะสำหรับ SOC/System Admin เป็นข้อย่อยสั้นๆ 2-3 ข้อ (เช่น การอัปเดตแพตช์, การตรวจสอบ Log, การบล็อก IOC)
5. ใน 'iocs' ให้ระบุรหัส CVE หรือชื่อภัยคุกคามสั้นๆ หากไม่มีให้ระบุ 'ไม่มี'
6. ใน 'source' ให้ระบุชื่อสำนักข่าวสั้นๆ
"""

def clean_bullet_item(text: str) -> str:
    """Removes leading bullets/dashes/numbers and internal linebreaks from a bullet text."""
    if not text:
        return ""
    cleaned = re.sub(r"^[•\-\*\d\.\s]+", "", text.strip())
    return " ".join(cleaned.split())

def call_gemini_api(api_key: str, model_name: str, article: Dict[str, Any]) -> Dict[str, Any]:
    """Calls Gemini REST API to process an article with automatic model fallback and retry."""
    import time

    candidate_models = [model_name]
    for fallback_model in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
        if fallback_model not in candidate_models:
            candidate_models.append(fallback_model)

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key.strip()
    }
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=25)
                if response.status_code == 200:
                    data = response.json()
                    text_result = data["candidates"][0]["content"]["parts"][0]["text"]
                    text_result = text_result.strip()
                    if text_result.startswith("```json"):
                        text_result = text_result[7:]
                    if text_result.startswith("```"):
                        text_result = text_result[3:]
                    if text_result.endswith("```"):
                        text_result = text_result[:-3]
                    return json.loads(text_result.strip())
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

def summarize_article(article: Dict[str, Any], api_key: str = "", model_name: str = "gemini-3.1-flash-lite") -> Dict[str, Any]:
    """
    Summarizes an article. Uses Gemini API if API key is present.
    Otherwise, falls back to regex-based IOC extraction and heuristic bullet points.
    """
    raw_text = f"{article.get('title', '')} {article.get('summary', '')}"
    extracted_iocs = extract_iocs_from_text(raw_text)
    regex_ioc_str = format_iocs_summary(extracted_iocs)

    if api_key and api_key.strip():
        try:
            ai_data = call_gemini_api(api_key, model_name, article)
            thai_title = ai_data.get("thai_title", article.get("title", ""))
            iocs = ai_data.get("iocs", regex_ioc_str)
            if not iocs or iocs.strip() == "" or iocs.lower() in ("none", "null"):
                iocs = regex_ioc_str if regex_ioc_str != "ไม่มี" else "ไม่มี"

            raw_kp = ai_data.get("key_points", [])
            if isinstance(raw_kp, str):
                raw_kp = raw_kp.split("\n")
            key_points = [clean_bullet_item(k) for k in raw_kp if clean_bullet_item(k)]

            raw_rec = ai_data.get("recommendations", [])
            if isinstance(raw_rec, str):
                raw_rec = raw_rec.split("\n")
            recommendations = [clean_bullet_item(r) for r in raw_rec if clean_bullet_item(r)]

            source_name = ai_data.get("source", article.get("source", "แหล่งข่าว")).strip()

            return {
                "title": thai_title,
                "summary": " ".join(key_points[:2]),
                "iocs": iocs,
                "key_points": key_points,
                "recommendations": recommendations,
                "source": source_name,
                "link": article.get("link", ""),
                "published": article.get("published", "")
            }
        except Exception as e:
            print(f"[-] AI Summarization warning ({article.get('source')}): {e}. Using fallback summarizer.")

    # Fallback when no API key or API call fails
    summary_text = article.get("summary", "")
    if len(summary_text) > 180:
        summary_text = summary_text[:180].rsplit(" ", 1)[0] + "..."

    fb_key_points = [
        f"เกิดเหตุการณ์ด้านความปลอดภัยที่เกี่ยวข้องกับ {article.get('title', '')[:60]}",
        "อาจส่งผลกระทบต่อความมั่นคงปลอดภัยของระบบและข้อมูลสำคัญในองค์กร",
        "เสี่ยงต่อการถูกแทรกซึมหากยังไม่ได้รับการติดตั้งแพตช์อัปเดต"
    ]
    fb_recs = [
        "ตรวจสอบระบบและเวอร์ชันของซอฟต์แวร์ที่เกี่ยวข้องภายในเครือข่าย",
        "ติดตามและเร่งอัปเดตแพตช์ความปลอดภัยล่าสุดจากผู้ผลิต",
        "เฝ้าระวังพฤติกรรมผิดปกติและการเชื่อมต่อเครือข่ายที่ไม่พึงประสงค์"
    ]
    if extracted_iocs.get("cves"):
        fb_recs[0] = f"เร่งอัปเดตแพตช์เพื่อปิดช่องโหว่ {', '.join(extracted_iocs['cves'][:2])}"
    elif extracted_iocs.get("ips") or extracted_iocs.get("sha256"):
        fb_recs[1] = "นำค่า IOC ที่พบไปตรวจสอบใน SIEM/EDR Logs และบล็อกการเชื่อมต่อ"

    return {
        "title": article.get("title", ""),
        "summary": summary_text or "ไม่มีรายละเอียดเนื้อหาเพิ่มเติม",
        "iocs": regex_ioc_str,
        "key_points": fb_key_points,
        "recommendations": fb_recs,
        "source": article.get("source", "แหล่งข่าว"),
        "link": article.get("link", ""),
        "published": article.get("published", "")
    }

def process_all_articles(articles: List[Dict[str, Any]], api_key: str = "", model_name: str = "gemini-3.1-flash-lite") -> List[Dict[str, Any]]:
    """Processes a list of raw articles into formatted digests."""
    results = []
    for idx, art in enumerate(articles, 1):
        print(f"[*] Processing news #{idx}/{len(articles)}: {art.get('title', '')[:50]}...")
        processed = summarize_article(art, api_key=api_key, model_name=model_name)
        results.append(processed)
    return results
