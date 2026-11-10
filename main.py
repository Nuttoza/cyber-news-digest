"""
Cyber Threat Intelligence Daily Digest CLI
Aggregates cybersecurity news globally in the past 24-48 hours,
summarizes into Thai (1-2 lines), extracts IOCs, prints result, and generates .docx and .pdf reports.
"""
import argparse
from datetime import datetime
import json
import os
import sys

from docx_generator import create_cyber_digest_docx
from feeds import get_top_cyber_news
from line_notifier import send_to_line
from summarizer import process_all_articles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config() -> dict:
    default_config = {
        "gemini_api_key": "",
        "gemini_model": "gemini-3.1-flash-lite",
        "time_window_hours": 48,
        "target_articles_count": 5,
        "output_dir": "output",
        "feed_sources": []
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception as e:
            print(f"[-] Warning: Failed to parse config.json: {e}")
    return default_config

def convert_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """Converts a .docx file to .pdf using win32com (Windows) or LibreOffice (Linux/GitHub Actions)."""
    abs_docx = os.path.abspath(docx_path)
    abs_pdf = os.path.abspath(pdf_path)

    # Strategy 1: Windows with Microsoft Word COM
    if sys.platform == "win32":
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            try:
                doc = word.Documents.Open(abs_docx)
                doc.SaveAs(abs_pdf, FileFormat=17)  # 17 = wdFormatPDF
                doc.Close(SaveChanges=False)
            finally:
                word.Quit()
                pythoncom.CoUninitialize()
            return os.path.exists(abs_pdf)
        except Exception as e:
            print(f"[-] Warning: Windows win32com conversion failed: {e}")

    # Strategy 2: Linux / Mac / GitHub Actions with LibreOffice
    import subprocess
    try:
        cmd = ["libreoffice", "--headless", "--convert-to", "pdf", abs_docx, "--outdir", os.path.dirname(abs_pdf)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        if result.returncode == 0 and os.path.exists(abs_pdf):
            return True
    except Exception as e:
        pass

    return False

def main():
    parser = argparse.ArgumentParser(description="Cyber Threat News Aggregator & Thai Summarizer")
    parser.add_argument("--hours", type=int, help="Time window in hours (default: 48)")
    parser.add_argument("--count", type=int, help="Number of top stories (default: 5)")
    parser.add_argument("--output-dir", type=str, help="Output directory for reports")
    parser.add_argument("--api-key", type=str, help="Gemini API Key override")
    args = parser.parse_args()

    config = load_config()

    hours = args.hours or config.get("time_window_hours", 48)
    count = args.count or config.get("target_articles_count", 5)
    output_dir = args.output_dir or os.path.join(BASE_DIR, config.get("output_dir", "output"))
    
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY") or config.get("gemini_api_key", "")
    model_name = config.get("gemini_model", "gemini-3.1-flash-lite")
    feed_sources = config.get("feed_sources", [])

    print("================================================================================")
    print("รายงานสรุปข่าวภัยคุกคามทางไซเบอร์ประจำวัน (รอบ 24-48 ชม.)")
    print(f"ช่วงเวลาย้อนหลัง: {hours} ชั่วโมง | จำนวนข่าวที่ต้องการ: {count} ข่าว")
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or config.get("line_channel_access_token", "")
    line_user_id = os.environ.get("LINE_USER_ID") or config.get("line_user_id", "")
    print(f"AI Model: {model_name} | API Key ตรวจพบ: {'ใช่ (เชื่อมต่อ AI)' if api_key.strip() else 'ยังไม่ได้ระบุ (ใช้ Heuristic Fallback)'} | LINE: {'เปิดใช้งาน' if line_token.strip() else 'ปิด'}")
    print("================================================================================")

    print("\n[1/4] กำลังดึงข่าวจากแหล่งข้อมูลระดับโลก (RSS Feeds)...")
    raw_articles = get_top_cyber_news(feed_sources, time_window_hours=hours, top_n=count)
    if not raw_articles:
        print("[-] ไม่พบข่าวใหม่ในช่วงเวลาดังกล่าว")
        sys.exit(0)

    print(f"[+] คัดเลือกข่าวที่มีนัยสำคัญระดับสูงได้ {len(raw_articles)} ข่าว")

    print("\n[2/4] กำลังวิเคราะห์ แปลสรุปภาษาไทย 1-2 บรรทัด และสกัด IOC...")
    processed = process_all_articles(raw_articles, api_key=api_key, model_name=model_name)

    print("\n================================================================================")
    print("ผลลัพธ์สรุปข่าวไซเบอร์ประจำวัน:")
    print("================================================================================")
    for idx, item in enumerate(processed, 1):
        print(f"\n{idx}. หัวข้อเรื่อง: {item['title']}")
        print(f"สรุป: {item['summary']}")
        print(f"IOC: {item['iocs']}")
        print(f"link: {item['link']}")

    print("\n================================================================================")
    print("\n[3/4] กำลังสร้างเอกสาร Word (.docx) และส่งออกเป็น PDF (.pdf)...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    docx_file = os.path.join(output_dir, f"Cyber_Threat_Digest_{today_str}.docx")
    pdf_file = os.path.join(output_dir, f"Cyber_Threat_Digest_{today_str}.pdf")

    # 1. Generate DOCX
    create_cyber_digest_docx(processed, docx_file, date_str=today_str)
    print(f"[+] บันทึกเอกสาร Word (.docx) เรียบร้อย: {docx_file}")

    # 2. Convert to PDF
    pdf_success = convert_to_pdf(docx_file, pdf_file)
    if pdf_success:
        print(f"[+] บันทึกเอกสาร PDF (.pdf) เรียบร้อย: {pdf_file}")
    else:
        print("[-] ไม่สามารถแปลงเป็นไฟล์ PDF ได้ กรุณาเปิดไฟล์ .docx ในโปรแกรม Word แล้ว Save as PDF")

    # 3. Send to LINE
    if line_token.strip():
        print("\n[4/4] กำลังส่งสรุปข่าวเข้า LINE...")
        send_to_line(line_token, processed, user_id=line_user_id)
    else:
        print("\n[4/4] ข้ามการส่ง LINE (ยังไม่ได้ใส่ Channel access token)")

    print("\nเสร็จสิ้นภารกิจประจำวันเรียบร้อยครับ!")

if __name__ == "__main__":
    main()
