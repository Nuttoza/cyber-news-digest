# 🛡️ ระบบรวบรวมและสรุปข่าวไซเบอร์ซีเคียวริตี้ประจำวัน (Cyber Threat Intelligence Daily Digest)

ระบบรวบรวมข่าวภัยคุกคามทางไซเบอร์จากสำนักข่าวชั้นนำระดับโลกในรอบ 24–48 ชั่วโมง คัดเลือก 5 ข่าวที่มีนัยสำคัญระดับสูง แปลและสรุปเป็นภาษาไทย 1-2 บรรทัด สกัดตัวชี้วัดภัยคุกคาม (IOC) และส่งออกเป็นเอกสาร Microsoft Word (.docx) สวยงามโดยอัตโนมัติ

---

## 📌 จุดเด่นของระบบ

1. **ครอบคลุมข่าวกรองระดับโลก:** ดึงข่าวจาก The Hacker News, BleepingComputer, SecurityWeek, The Record, Dark Reading, ESET WeLiveSecurity ฯลฯ
2. **กรองช่วงเวลาแม่นยำ:** ดึงเฉพาะข่าวสดใหม่ในรอบ 24–48 ชม. และตัดข่าวที่ซ้ำประเด็นเดียวกันออก
3. **จัดอันดับความรุนแรง (Threat Scoring):** ให้น้ำหนักกับ Zero-day, Ransomware, Critical CVE, RCE, และ Supply Chain โจมตี
4. **สรุปภาษาไทยกระชับ 1-2 บรรทัด:** คงศัพท์เทคนิคที่จำเป็น ชี้ชัดว่าใครทำอะไร และต้องรับมืออย่างไร
5. **สกัด IOC อัตโนมัติ:** คัดแยก CVE, SHA256/MD5 Hashes, C2 IPs (พร้อม Defang เช่น `192.168.1[.]1`)
6. **สร้างไฟล์ Word (.docx) และ PDF (.pdf) มืออาชีพ:** ใช้ฟอนต์ TH Sarabun New มีตารางสรุป ภาพรวม และการ์ดข่าวรายหัวข้อพร้อมลิงก์ที่คลิกได้
7. **ใช้ Gemini API ฟรี 100%:** ขับเคลื่อนด้วยโมเดล `gemini-3.1-flash-lite` รวดเร็ว แม่นยำ และประหยัดโควตา

---

## 📁 โครงสร้างโปรเจกต์

```text
cyber_news_digest/
├── config.json          # ตั้งค่าแหล่งข่าว, API Key, จำนวนข่าว, โมเดล AI
├── feeds.py             # ตัวดึงและคัดกรอง RSS Feeds (24-48 ชม.)
├── ioc_extractor.py     # ตัวสกัดและ Defang IOCs (CVE, Hash, IP, URL)
├── summarizer.py        # ตัวเชื่อมต่อ AI สรุป แปลไทย และสกัด IOC
├── docx_generator.py    # ตัวสร้างเอกสาร Word (.docx) จัดสไตล์ด้วย TH Sarabun New
├── main.py              # สคริปต์หลักสั่งประมวลผลและแปลงเป็น PDF
├── run_daily.bat        # ดับเบิ้ลคลิกเพื่อรันได้ทันที
├── schedule_task.ps1    # สคริปต์ตั้งเวลาทำงานอัตโนมัติทุกเช้าใน Windows
└── output/              # โฟลเดอร์เก็บเอกสาร Word (.docx) และ PDF (.pdf)
```

---

## 🚀 วิธีตั้งค่าและใช้งาน

### 1. การใส่ Gemini API Key (ฟรี)
1. ขอรับ API Key ฟรีได้ทันทีที่ [Google AI Studio](https://aistudio.google.com/app/apikey)
2. เปิดไฟล์ `config.json` แล้วใส่คีย์ลงในช่อง `"gemini_api_key"`:
```json
{
  "gemini_api_key": "AIzaSy...",
  "gemini_model": "gemini-2.5-flash",
  "time_window_hours": 48,
  "target_articles_count": 5
}
```
*(หรือตั้งค่า Environment Variable `GEMINI_API_KEY` ก็ได้เช่นกัน)*

---

### 2. วิธีสั่งรันด้วยตนเอง (Manual Run)
* **วิธีที่ 1 (ง่ายสุด):** ดับเบิ้ลคลิกที่ไฟล์ `run_daily.bat`
* **วิธีที่ 2 (ผ่าน Terminal/Command Line):**
```bash
python main.py
```
*(สามารถระบุออปชันเสริม เช่น `python main.py --hours 24 --count 5`)*

เมื่อประมวลผลเสร็จแล้ว เอกสารจะถูกบันทึกไว้ที่:
`output/Cyber_Threat_Digest_YYYY-MM-DD.docx`

---

### 3. วิธีตั้งเวลาให้ทำงานอัตโนมัติทุกเช้า (Windows Task Scheduler)
รันคำสั่งใน PowerShell เพื่อตั้งให้ระบบทำงานอัตโนมัติ เช่น เวลา 07:30 น. ของทุกวัน:
```powershell
powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1 -Time "07:30"
```
*(หากต้องการยกเลิกการตั้งเวลา ให้รัน `.\schedule_task.ps1 -Remove`)*
