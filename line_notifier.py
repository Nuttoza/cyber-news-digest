"""
LINE Notifier Module
Sends the Cyber Threat Intelligence Daily Digest notification to LINE chat via Messaging API
using Push (specific user/group ID) or Broadcast.
Sends the 1-page preview image and the GitHub Releases download link.
"""
from datetime import datetime
from typing import Optional
import os
import requests

DEFAULT_IMAGE_URL = "https://raw.githubusercontent.com/Nuttoza/cyber-news-digest/main/docs/latest_preview.png"
GITHUB_RELEASES_URL = "https://github.com/Nuttoza/cyber-news-digest/releases"

def format_line_message(release_url: str = GITHUB_RELEASES_URL) -> str:
    """Formats notification containing the date and the release page download link."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    return (
        f"รายงานสถานการณ์ข่าวภัยคุกคามทางไซเบอร์ ประจำวันที่ {today_str}\n\n"
        f"ติดตามและดาวน์โหลดเอกสาร (Word / PDF) ได้ที่หน้า Release:\n"
        f"{release_url}"
    )

def send_to_line(
    access_token: str,
    user_id: str = "",
    image_url: str = DEFAULT_IMAGE_URL,
    release_url: str = GITHUB_RELEASES_URL
) -> bool:
    """
    Sends the preview image and release link notification to LINE.
    If user_id is provided, sends via Push (User ID 'U...' or Group ID 'C...').
    Otherwise, sends via Broadcast to all users/groups who added the bot.
    """
    if not access_token or not access_token.strip():
        print("[-] LINE notification skipped: No access token provided.")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token.strip()}"
    }

    messages = []
    # 1. Image preview of the 1-page report
    if image_url and image_url.startswith("https://"):
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })

    # 2. Text message with release page download link
    message_text = format_line_message(release_url)
    messages.append({
        "type": "text",
        "text": message_text
    })

    payload = {
        "messages": messages
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
            print(f"[+] ส่งข้อความและรูปภาพพรีวิวเข้า LINE สำเร็จ ({method_name})")
            return True
        else:
            print(f"[-] แจ้งเตือน LINE ล้มเหลว (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[-] แจ้งเตือน LINE เกิดข้อผิดพลาด: {e}")
        return False

if __name__ == "__main__":
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    target_user = os.environ.get("LINE_USER_ID", "")
    img = os.environ.get("LINE_PREVIEW_IMAGE_URL", DEFAULT_IMAGE_URL)
    if token:
        send_to_line(access_token=token, user_id=target_user, image_url=img)
    else:
        print("[-] LINE_CHANNEL_ACCESS_TOKEN not set. Exiting without sending.")
