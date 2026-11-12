import os
from datetime import datetime
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

FONT_NAME = "TH Sarabun New"

def apply_thai_font(run, font_name=FONT_NAME, size_pt=16, bold=False, color_rgb=None):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color_rgb:
        run.font.color.rgb = color_rgb

    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rPr.append(rFonts)

    sz_val = str(int(size_pt * 2))
    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), sz_val)
    rPr.append(szCs)

    if bold:
        bCs = OxmlElement('w:bCs')
        rPr.append(bCs)

def set_cell_background(cell, hex_color: str):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def set_table_borders(table, color="708090", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = OxmlElement('w:tblBorders')
        for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), val)
            border.set(qn('w:sz'), sz)
            border.set(qn('w:space'), '0')
            border.set(qn('w:color'), color)
            borders.append(border)
        tblPr[0].append(borders)

def set_cell_margins(cell, top=40, bottom=40, left=80, right=80):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def get_thai_buddhist_date(dt=None):
    if dt is None:
        dt = datetime.now()
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    year_be = dt.year + 543
    month_th = thai_months[dt.month - 1]
    return f"{dt.day} {month_th} {year_be}"

def create_table_document(items, output_docx, logo_path=None, issue_no="01/2569"):
    doc = Document()

    # Configure Landscape A4 orientation with optimal compact margins
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11.69)
    section.page_height = Inches(8.27)
    section.top_margin = Inches(0.35)
    section.bottom_margin = Inches(0.35)
    section.left_margin = Inches(0.45)
    section.right_margin = Inches(0.45)

    # 1. Logo
    if logo_path and os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(0)
        p_logo.paragraph_format.space_after = Pt(1)
        p_logo.paragraph_format.line_spacing = Pt(12)
        run_logo = p_logo.add_run()
        run_logo.add_picture(logo_path, width=Inches(0.95))

    # 2. Main Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(0)
    p_title.paragraph_format.line_spacing = Pt(16)
    r_title = p_title.add_run("สถานการณ์ข่าวภัยคุกคามทางไซเบอร์")
    apply_thai_font(r_title, size_pt=16, bold=True, color_rgb=RGBColor(16, 44, 87))

    # 3. Date Subtitle
    date_str = get_thai_buddhist_date()
    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_date.paragraph_format.space_before = Pt(0)
    p_date.paragraph_format.space_after = Pt(2)
    p_date.paragraph_format.line_spacing = Pt(15)
    r_date = p_date.add_run(f"ประจำวันที่ {date_str}")
    apply_thai_font(r_date, size_pt=14.5, bold=True, color_rgb=RGBColor(30, 30, 30))

    # 4. Issue number & Date table (borderless 2-column)
    sub_table = doc.add_table(rows=1, cols=2)
    sub_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sub_table.autofit = False
    sub_table.rows[0].cells[0].width = Inches(5.3)
    sub_table.rows[0].cells[1].width = Inches(5.4)

    c0 = sub_table.rows[0].cells[0]
    p_c0 = c0.paragraphs[0]
    p_c0.paragraph_format.space_before = Pt(0)
    p_c0.paragraph_format.space_after = Pt(2)
    p_c0.paragraph_format.line_spacing = Pt(14)
    r_c0 = p_c0.add_run(f"ที่ {issue_no}")
    apply_thai_font(r_c0, size_pt=14, bold=True)

    c1 = sub_table.rows[0].cells[1]
    p_c1 = c1.paragraphs[0]
    p_c1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_c1.paragraph_format.space_before = Pt(0)
    p_c1.paragraph_format.space_after = Pt(2)
    p_c1.paragraph_format.line_spacing = Pt(14)
    r_c1 = p_c1.add_run(date_str)
    apply_thai_font(r_c1, size_pt=14, bold=True)

    # 5. Main 6-column Table
    table = doc.add_table(rows=1, cols=6)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color="556B2F" if False else "607D8B", sz="5", val="single")

    col_widths = [Inches(0.55), Inches(2.25), Inches(1.35), Inches(2.85), Inches(2.75), Inches(1.04)]
    headers = [
        "ลำดับ",
        "หัวข้อข่าว",
        "IOC",
        "สาระสำคัญ / ผลกระทบ",
        "แนวทางป้องกัน / ข้อเสนอแนะ",
        "แหล่งข่าว"
    ]

    hdr_row = table.rows[0]
    hdr_tr = hdr_row._tr.get_or_add_trPr()
    hdr_tr.append(OxmlElement('w:tblHeader'))

    for i, title in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.width = col_widths[i]
        set_cell_background(cell, "1F3A60")  # Royal/Navy Blue
        set_cell_margins(cell, top=60, bottom=60, left=60, right=60)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = Pt(13)
        r = p.add_run(title)
        apply_thai_font(r, size_pt=13, bold=True, color_rgb=RGBColor(255, 255, 255))

    for idx, item in enumerate(items, 1):
        row = table.add_row()
        row_tr = row._tr.get_or_add_trPr()
        row_tr.append(OxmlElement('w:cantSplit'))

        bg = "F9FBFC" if idx % 2 == 0 else "FFFFFF"

        # Col 0: ลำดับ
        c0 = row.cells[0]
        c0.width = col_widths[0]
        c0.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c0, bg)
        set_cell_margins(c0, top=40, bottom=40, left=40, right=40)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.line_spacing = Pt(13)
        r0 = p0.add_run(str(idx))
        apply_thai_font(r0, size_pt=12.5, bold=True)

        # Col 1: หัวข้อข่าว
        c1 = row.cells[1]
        c1.width = col_widths[1]
        c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c1, bg)
        set_cell_margins(c1, top=40, bottom=40, left=60, right=60)
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = Pt(13)
        r1 = p1.add_run(item.get("title", ""))
        apply_thai_font(r1, size_pt=12, bold=True, color_rgb=RGBColor(20, 30, 45))

        # Col 2: IOC
        c2 = row.cells[2]
        c2.width = col_widths[2]
        c2.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c2, bg)
        set_cell_margins(c2, top=40, bottom=40, left=50, right=50)
        p2 = c2.paragraphs[0]
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = Pt(12)
        r2 = p2.add_run(item.get("iocs", "ไม่มี"))
        apply_thai_font(r2, size_pt=11.5, color_rgb=RGBColor(170, 30, 20) if item.get("iocs") != "ไม่มี" else RGBColor(80, 80, 80))

        # Col 3: สาระสำคัญ / ผลกระทบ
        c3 = row.cells[3]
        c3.width = col_widths[3]
        c3.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c3, bg)
        set_cell_margins(c3, top=40, bottom=40, left=60, right=60)
        p3 = c3.paragraphs[0]
        p3.paragraph_format.space_before = Pt(0)
        p3.paragraph_format.space_after = Pt(0)
        p3.paragraph_format.line_spacing = Pt(12)
        
        bullets_imp = item.get("key_points", [])
        if isinstance(bullets_imp, str):
            bullets_imp = [b.strip() for b in bullets_imp.split("\n") if b.strip()]
        
        for b_idx, bullet in enumerate(bullets_imp):
            if b_idx > 0:
                p3 = c3.add_paragraph()
                p3.paragraph_format.space_before = Pt(0)
                p3.paragraph_format.space_after = Pt(0)
                p3.paragraph_format.line_spacing = Pt(12)
            b_text = bullet if bullet.startswith("•") else f"• {bullet}"
            r3 = p3.add_run(b_text)
            apply_thai_font(r3, size_pt=11.5, color_rgb=RGBColor(25, 25, 25))

        # Col 4: แนวทางป้องกัน / ข้อเสนอแนะ
        c4 = row.cells[4]
        c4.width = col_widths[4]
        c4.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c4, bg)
        set_cell_margins(c4, top=40, bottom=40, left=60, right=60)
        p4 = c4.paragraphs[0]
        p4.paragraph_format.space_before = Pt(0)
        p4.paragraph_format.space_after = Pt(0)
        p4.paragraph_format.line_spacing = Pt(12)

        bullets_rec = item.get("recommendations", [])
        if isinstance(bullets_rec, str):
            bullets_rec = [b.strip() for b in bullets_rec.split("\n") if b.strip()]

        for b_idx, bullet in enumerate(bullets_rec):
            if b_idx > 0:
                p4 = c4.add_paragraph()
                p4.paragraph_format.space_before = Pt(0)
                p4.paragraph_format.space_after = Pt(0)
                p4.paragraph_format.line_spacing = Pt(12)
            b_text = bullet if bullet.startswith("•") else f"• {bullet}"
            r4 = p4.add_run(b_text)
            apply_thai_font(r4, size_pt=11.5, color_rgb=RGBColor(25, 25, 25))

        # Col 5: แหล่งข่าว
        c5 = row.cells[5]
        c5.width = col_widths[5]
        c5.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c5, bg)
        set_cell_margins(c5, top=40, bottom=40, left=40, right=40)
        p5 = c5.paragraphs[0]
        p5.paragraph_format.space_before = Pt(0)
        p5.paragraph_format.space_after = Pt(0)
        p5.paragraph_format.line_spacing = Pt(12)
        r5 = p5.add_run(item.get("source", ""))
        apply_thai_font(r5, size_pt=11, color_rgb=RGBColor(60, 60, 60))

    os.makedirs(os.path.dirname(os.path.abspath(output_docx)), exist_ok=True)
    doc.save(output_docx)
    return output_docx

# User's exact sample items
sample_items = [
    {
        "title": "Microsoft อุดช่องโหว่ 1,235 รายการ พบ Outlook Zero-Day ถูกโจมตีจริง",
        "iocs": "CVE-2026-124194\n(Outlook)",
        "key_points": [
            "Outlook Zero-Day ถูกใช้โจมตีจริง",
            "ออกแพตช์ประจำเดือน พ.ย. ครอบคลุม 1,235 ช่องโหว่",
            "เสี่ยงต่อระบบอีเมลและข้อมูลยืนยันตัวตน"
        ],
        "recommendations": [
            "เร่งติดตั้งแพตช์ Microsoft ล่าสุด",
            "ตรวจสอบ Outlook/Office ทุกเครื่อง",
            "เฝ้าระวังอีเมลและการเชื่อมต่อผิดปกติ"
        ],
        "source": "BleepingComputer\nCISA KEV"
    },
    {
        "title": "ช่องโหว่ RCE ใน SGLang ถูกใช้เจาะระบบ NEAR AI",
        "iocs": "SGLang RCE",
        "key_points": [
            "สั่งรันโค้ดบนเซิร์ฟเวอร์ AI ได้",
            "เข้าถึงคำขอ รวมถึงโหมด Confidential",
            "กระทบผู้ใช้ราว 100 ราย และ AI agents 18 ราย"
        ],
        "recommendations": [
            "อัปเดต SGLang ตามผู้พัฒนา",
            "แยกบริการ AI จากระบบข้อมูลสำคัญ",
            "ตรวจสอบ Log, Secrets และการเข้าถึงย้อนหลัง"
        ],
        "source": "The Hacker News\nNEAR AI Incident Report"
    },
    {
        "title": "ช่องโหว่ Xen Orchestra ถูกโจมตีเพื่อยึดสิทธิ์ผู้ดูแลระบบ VM",
        "iocs": "Xen Orchestra\nAuth Bypass",
        "key_points": [
            "หลบเลี่ยงการยืนยันตัวตนได้",
            "อาจเข้าถึงคำสั่งระดับผู้ดูแลระบบ",
            "เสี่ยงยึดระบบจัดการ XCP-ng และ VM"
        ],
        "recommendations": [
            "อัปเดต Xen Orchestra ตามผู้ผลิต",
            "จำกัดหน้า Admin เฉพาะเครือข่ายบริหาร",
            "ตรวจสอบบัญชีและ Log การสั่งงาน VM"
        ],
        "source": "BleepingComputer\nVates Security Advisory"
    },
    {
        "title": "กลุ่ม Turla ใช้มัลแวร์ Cereal จารกรรมอีเมลบน Microsoft Exchange",
        "iocs": "Cereal malware\nTurla",
        "key_points": [
            "มุ่งโจมตี Exchange ของหน่วยงานรัฐ",
            "ใช้ดักเก็บอีเมลและสั่งคำสั่งในหน่วยความจำ",
            "เสี่ยงข้อมูลราชการและการสื่อสารรั่วไหล"
        ],
        "recommendations": [
            "ตรวจสอบและอัปเดต Exchange Server",
            "เฝ้าระวังการอ่าน/ส่งออกอีเมลผิดปกติ",
            "ตรวจสอบ Persistence และการทำงานในหน่วยความจำ"
        ],
        "source": "ESET Research\nBleepingComputer"
    },
    {
        "title": "แฮกเกอร์ใช้บัญชี AWS ของ Qubole เข้าถึงข้อมูลลูกค้าหลายสภาพแวดล้อม",
        "iocs": "Qubole AWS IAM",
        "key_points": [
            "ใช้ข้อมูลรับรอง IAM ที่ถูกขโมย",
            "เข้าถึง AWS environments ของลูกค้าหลายราย",
            "ดึง Secrets และดาวน์โหลดข้อมูล (14–26 ต.ค. 2026)"
        ],
        "recommendations": [
            "หมุนเวียน Access Keys และ Secrets",
            "ตรวจสอบ CloudTrail, IAM Role และการดึงข้อมูล",
            "ใช้ Least Privilege, MFA และจำกัด Trust Policy"
        ],
        "source": "BleepingComputer\nWiz Research"
    }
]

out_docx = r"C:\Users\user\.gemini\antigravity\scratch\cyber_news_digest\output\Cyber_Center_Report_Sample.docx"
logo = r"C:\Users\user\.gemini\antigravity\scratch\cyber_news_digest\assets\logo.png"
create_table_document(sample_items, out_docx, logo_path=logo)
print("Updated Docx created successfully!")
