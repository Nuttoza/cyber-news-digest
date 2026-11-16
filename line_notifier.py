"""
LINE Notifier Module
Sends the Cyber Threat Intelligence Daily Digest notification to LINE chat via Messaging API
using Push (specific user/group ID) or Broadcast.
Sends ONLY the 1-page preview image (no text message).
"""
import os
import requests

DEFAULT_IMAGE_URL = "https://raw.githubusercontent.com/Nuttoza/cyber-news-digest/main/docs/latest_preview.png"

def send_to_line(
    access_token: str,
    user_id: str = "",
    image_url: str = DEFAULT_IMAGE_URL
) -> bool:
    """
    Sends ONLY the preview image of the report to LINE.
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
    # Send image only
    if image_url and image_url.startswith("https://"):
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })

    if not messages:
        print("[-] LINE notification skipped: No valid image URL provided.")
        return False

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
            print(f"[+] ส่งรูปภาพพรีวิวเข้า LINE สำเร็จ ({method_name})")
            return True
        else:
            print(f"[-] แจ้งเตือน LINE ล้มเหลว (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[-] แจ้งเตือน LINE เกิดข้อผิดพลาด: {e}")
        return False

if __name__ == "__main__":
    img = os.environ.get("LINE_PREVIEW_IMAGE_URL", DEFAULT_IMAGE_URL)
    bots = [
        ("Bot 2", os.environ.get("LINE_CHANNEL_ACCESS_TOKEN_2", ""), os.environ.get("LINE_USER_ID_2", "")),
    ]

    sent_any = False
    for bot_name, token, target_user in bots:
        if token and token.strip():
            print(f"[*] กำลังส่งแจ้งเตือนผ่าน {bot_name}...")
            send_to_line(access_token=token, user_id=target_user, image_url=img)
            sent_any = True

    if not sent_any:
        print("[-] No LINE_CHANNEL_ACCESS_TOKEN_2 configured. Exiting without sending.")
