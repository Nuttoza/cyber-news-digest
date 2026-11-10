"""
LINE Notifier Module
Sends the Cyber Threat Intelligence Daily Digest directly to LINE chat via Messaging API
using Broadcast (all followers) or Push (specific user/group ID).
"""
from datetime import datetime
import json
from typing import Dict, List
import requests

GITHUB_ACTIONS_URL = "https://github.com/Nuttoza/cyber-news-digest/actions"

def format_line_message(articles: List[Dict[str, str]], repo_url: str = GITHUB_ACTIONS_URL) -> str:
    """Formats the top 5 articles into a clean message with Git download link."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"ข่าวทางไซเบอร์ประจำวันที่ {today_str}\n"
    ]

    for idx, item in enumerate(articles, 1):
        lines.append(f"{idx}. หัวข้อเรื่อง: {item.get('title', '')}")
        lines.append(f"สรุป: {item.get('summary', '')}")
        lines.append(f"IOC: {item.get('iocs', 'ไม่มี')}")
        lines.append(f"link: {item.get('link', '')}\n")

    lines.append("ดาวน์โหลดไฟล์เอกสารฉบับเต็ม (PDF / Word):")
    lines.append(repo_url)

    return "\n".join(lines).strip()

def send_to_line(access_token: str, articles: List[Dict[str, str]], user_id: str = "") -> bool:
    """
    Sends the digest to LINE.
    If user_id is provided, sends via Push (works for User ID 'U...' and Group ID 'C...').
    Otherwise, sends via Broadcast to all users who added the bot.
    """
    if not access_token or not access_token.strip():
        print("[-] LINE notification skipped: No access token provided.")
        return False

    message_text = format_line_message(articles)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token.strip()}"
    }

    payload = {
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }

    # Decide between Push (specific User/Group ID) or Broadcast (all friends)
    if user_id and len(user_id) == 33 and (user_id.startswith("U") or user_id.startswith("C")):
        url = "https://api.line.me/v2/bot/message/push"
        payload["to"] = user_id
        method_name = f"Push to {user_id}"
    else:
        url = "https://api.line.me/v2/bot/message/broadcast"
        method_name = "Broadcast (All Friends)"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            print(f"[+] ส่งสรุปข่าวเข้า LINE สำเร็จ ({method_name})")
            return True
        else:
            print(f"[-] แจ้งเตือน LINE ล้มเหลว (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[-] แจ้งเตือน LINE เกิดข้อผิดพลาด: {e}")
        return False
