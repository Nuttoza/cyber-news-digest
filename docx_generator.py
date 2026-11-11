"""
DOCX Generator Module
Generates a cleanly formatted Microsoft Word document (.docx)
using TH Sarabun New font for official and standard Thai document layout.
"""
from datetime import datetime
import os
from typing import Dict, List, Optional
import docx
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FONT_NAME = "TH Sarabun New"

def apply_thai_font(run, font_name: str = FONT_NAME, size_pt: float = 16, bold: bool = False, color_rgb: Optional[RGBColor] = None):
    """
    Applies font name, size, bold, color, and Word XML complex script (CS)
    attributes to ensure TH Sarabun New renders properly on all Word versions.
    """
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color_rgb:
        run.font.color.rgb = color_rgb

    # Explicitly set XML elements for ASCII, High-ANSI, and Complex Scripts (Thai)
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rPr.append(rFonts)

    # Complex script font size (half-points: 16pt = 32)
    sz_val = str(int(size_pt * 2))
    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), sz_val)
    rPr.append(szCs)

    if bold:
        bCs = OxmlElement('w:bCs')
        rPr.append(bCs)

def set_cell_background(cell, hex_color: str):
    """Sets background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def add_hyperlink(paragraph, url: str, text: str, font_name: str = FONT_NAME, size_pt: float = 14, color_rgb="0055BB"):
    """Adds a clickable hyperlink styled with TH Sarabun New."""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)

    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')

    # Color
    c = OxmlElement('w:color')
    c.set(qn('w:val'), color_rgb)
    rPr.append(c)

    # Underline
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)

    # Fonts
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rPr.append(rFonts)

    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(size_pt * 2)))
    rPr.append(sz)

    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), str(int(size_pt * 2)))
    rPr.append(szCs)

    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def create_cyber_digest_docx(articles: List[Dict[str, str]], output_path: str, date_str: str = "") -> str:
    """Creates a formatted Word (.docx) document with TH Sarabun New without emojis/divider bars."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    doc = Document()

    # Set default document style to TH Sarabun New
    normal_style = doc.styles['Normal']
    normal_style.font.name = FONT_NAME
    normal_style.font.size = Pt(16)
    if hasattr(normal_style.element, "rPr") and normal_style.element.rPr is not None:
        rFonts = normal_style.element.rPr.get_or_add_rFonts()
        rFonts.set(qn('w:ascii'), FONT_NAME)
        rFonts.set(qn('w:hAnsi'), FONT_NAME)
        rFonts.set(qn('w:cs'), FONT_NAME)

    # Set page margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # 1. Document Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    title_run = title_p.add_run("รายงานสรุปข่าวภัยคุกคามทางไซเบอร์ประจำวัน")
    apply_thai_font(title_run, size_pt=22, bold=True, color_rgb=RGBColor(16, 44, 87))

    # 2. Subtitle / Metadata (วันที่จัดทำ: DD/MM/YYYY)
    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(12)
    now_date_display = datetime.now().strftime("%d/%m/%Y")
    sub_run = sub_p.add_run(f"วันที่จัดทำ: {now_date_display}")
    apply_thai_font(sub_run, size_pt=14, color_rgb=RGBColor(100, 110, 120))

    # 3. Summary Table Heading
    summary_head = doc.add_paragraph()
    summary_head.paragraph_format.space_before = Pt(4)
    summary_head.paragraph_format.space_after = Pt(4)
    sh_run = summary_head.add_run("ตารางสรุป 5 ข่าวสำคัญประจำวัน")
    apply_thai_font(sh_run, size_pt=16, bold=True, color_rgb=RGBColor(16, 44, 87))

    # 4. Create Summary Table
    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    headers = ["ลำดับ", "หัวข้อข่าวเด่น", "แหล่งที่มา", "IOC"]
    col_widths = [Inches(0.6), Inches(4.1), Inches(1.5), Inches(0.9)]

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = col_widths[i]
        set_cell_background(hdr_cells[i], "1F3A60")
        hdr_p = hdr_cells[i].paragraphs[0]
        hdr_p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
        for run in hdr_p.runs:
            apply_thai_font(run, size_pt=14, bold=True, color_rgb=RGBColor(255, 255, 255))

    for idx, item in enumerate(articles, 1):
        row_cells = table.add_row().cells
        for i in range(4):
            row_cells[i].width = col_widths[i]
            row_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        bg_color = "F7F9FC" if idx % 2 == 0 else "FFFFFF"
        for i in range(4):
            set_cell_background(row_cells[i], bg_color)

        # Col 0: No.
        p0 = row_cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(idx))
        apply_thai_font(r0, size_pt=14, bold=True)

        # Col 1: Title
        p1 = row_cells[1].paragraphs[0]
        title_text = item.get("title", "")
        if len(title_text) > 85:
            title_text = title_text[:85] + "..."
        r1 = p1.add_run(title_text)
        apply_thai_font(r1, size_pt=14)

        # Col 2: Source
        p2 = row_cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(item.get("source", ""))
        apply_thai_font(r2, size_pt=13, color_rgb=RGBColor(90, 90, 90))

        # Col 3: IOC Status
        p3 = row_cells[3].paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        has_ioc = item.get("iocs", "").strip() != "ไม่มี" and len(item.get("iocs", "").strip()) > 0
        r3 = p3.add_run("มี" if has_ioc else "ไม่มี")
        apply_thai_font(r3, size_pt=13, bold=True, color_rgb=RGBColor(180, 40, 20) if has_ioc else RGBColor(50, 130, 50))

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 5. Detailed Article Sections
    detail_head = doc.add_paragraph()
    detail_head.paragraph_format.space_before = Pt(8)
    detail_head.paragraph_format.space_after = Pt(6)
    dh_run = detail_head.add_run("รายละเอียดข่าวและการวิเคราะห์")
    apply_thai_font(dh_run, size_pt=17, bold=True, color_rgb=RGBColor(16, 44, 87))

    for idx, item in enumerate(articles, 1):
        # Card Header
        card_p = doc.add_paragraph()
        card_p.paragraph_format.space_before = Pt(10)
        card_p.paragraph_format.space_after = Pt(3)
        
        num_run = card_p.add_run(f"{idx}. หัวข้อเรื่อง: ")
        apply_thai_font(num_run, size_pt=16, bold=True, color_rgb=RGBColor(0, 85, 187))

        title_run = card_p.add_run(item.get("title", ""))
        apply_thai_font(title_run, size_pt=16, bold=True, color_rgb=RGBColor(20, 25, 35))

        # Summary Paragraph
        sum_p = doc.add_paragraph()
        sum_p.paragraph_format.left_indent = Inches(0.25)
        sum_p.paragraph_format.space_before = Pt(2)
        sum_p.paragraph_format.space_after = Pt(2)

        sum_label = sum_p.add_run("สรุป: ")
        apply_thai_font(sum_label, size_pt=15, bold=True, color_rgb=RGBColor(40, 40, 40))

        sum_val = sum_p.add_run(item.get("summary", ""))
        apply_thai_font(sum_val, size_pt=15, color_rgb=RGBColor(30, 30, 30))

        # IOC Paragraph
        ioc_p = doc.add_paragraph()
        ioc_p.paragraph_format.left_indent = Inches(0.25)
        ioc_p.paragraph_format.space_before = Pt(2)
        ioc_p.paragraph_format.space_after = Pt(2)

        ioc_label = ioc_p.add_run("IOC: ")
        apply_thai_font(ioc_label, size_pt=15, bold=True, color_rgb=RGBColor(180, 40, 20))

        ioc_val = ioc_p.add_run(item.get("iocs", "ไม่มี"))
        apply_thai_font(ioc_val, size_pt=14, color_rgb=RGBColor(60, 60, 60))

        # Thai National Security Impact Paragraph
        sec_impact = item.get("thai_security_impact", "").strip()
        if sec_impact:
            sec_p = doc.add_paragraph()
            sec_p.paragraph_format.left_indent = Inches(0.25)
            sec_p.paragraph_format.space_before = Pt(2)
            sec_p.paragraph_format.space_after = Pt(2)

            sec_label = sec_p.add_run("ผลกระทบต่อหน่วยงานความมั่นคงของไทย: ")
            apply_thai_font(sec_label, size_pt=15, bold=True, color_rgb=RGBColor(160, 30, 30))

            sec_val = sec_p.add_run(sec_impact)
            apply_thai_font(sec_val, size_pt=15, color_rgb=RGBColor(30, 30, 30))

        # SOC Recommendation Paragraph
        soc_rec = item.get("soc_recommendation", "").strip()
        if soc_rec:
            soc_p = doc.add_paragraph()
            soc_p.paragraph_format.left_indent = Inches(0.25)
            soc_p.paragraph_format.space_before = Pt(2)
            soc_p.paragraph_format.space_after = Pt(2)

            soc_label = soc_p.add_run("แนวทางปฏิบัติสำหรับทีม SOC: ")
            apply_thai_font(soc_label, size_pt=15, bold=True, color_rgb=RGBColor(20, 100, 160))

            soc_val = soc_p.add_run(soc_rec)
            apply_thai_font(soc_val, size_pt=15, color_rgb=RGBColor(30, 30, 30))

        # Link Paragraph
        link_p = doc.add_paragraph()
        link_p.paragraph_format.left_indent = Inches(0.25)
        link_p.paragraph_format.space_before = Pt(2)
        link_p.paragraph_format.space_after = Pt(8)

        link_label = link_p.add_run("link: ")
        apply_thai_font(link_label, size_pt=15, bold=True, color_rgb=RGBColor(60, 60, 60))

        raw_link = item.get("link", "")
        if raw_link:
            add_hyperlink(link_p, raw_link, raw_link, font_name=FONT_NAME, size_pt=14)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    return output_path
