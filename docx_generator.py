"""
DOCX Generator Module
Generates a cleanly formatted Microsoft Word document (.docx)
using TH Sarabun New font adhering to the official Cyber Center (ศซภ.ทอ./สสท.กห.) template.
"""
from datetime import datetime
import os
from typing import Any, Dict, List, Optional
import docx
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FONT_NAME = "TH Sarabun New"

def apply_thai_font(run, font_name: str = FONT_NAME, size_pt: float = 14, bold: bool = False, color_rgb: Optional[RGBColor] = None, underline: bool = False):
    """
    Applies font name, size, bold, color, and Word XML complex script (CS)
    attributes to ensure TH Sarabun New renders properly on all Word versions.
    """
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.underline = underline
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
    """Sets background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def set_table_borders(table, color: str = "7F7F7F", sz: str = "4", val: str = "single"):
    """Sets borders for table cells."""
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

def set_cell_margins(cell, top: int = 25, bottom: int = 25, left: int = 35, right: int = 35):
    """Sets inner padding/margins of a table cell in dxa (twips)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_grid(table, col_widths_dxa: List[int]):
    """Configures master w:tblGrid and table width in dxa."""
    tblGrid = table._tbl.xpath('w:tblGrid')
    if tblGrid:
        table._tbl.remove(tblGrid[0])
    new_grid = OxmlElement('w:tblGrid')
    for w in col_widths_dxa:
        gridCol = OxmlElement('w:gridCol')
        gridCol.set(qn('w:w'), str(w))
        new_grid.append(gridCol)
    tblPr = table._tbl.xpath('w:tblPr')[0]
    tblPr.addnext(new_grid)

    tblW = table._tbl.xpath('w:tblPr/w:tblW')
    total_dxa = sum(col_widths_dxa)
    if tblW:
        tblW[0].set(qn('w:w'), str(total_dxa))
        tblW[0].set(qn('w:type'), 'dxa')

def set_row_cell_widths(row, col_widths_dxa: List[int]):
    """Sets individual cell widths in a row in dxa."""
    for i, w in enumerate(col_widths_dxa):
        tcPr = row.cells[i]._tc.get_or_add_tcPr()
        tcW = tcPr.xpath('w:tcW')
        if tcW:
            tcPr.remove(tcW[0])
        new_tcW = OxmlElement('w:tcW')
        new_tcW.set(qn('w:w'), str(w))
        new_tcW.set(qn('w:type'), 'dxa')
        tcPr.append(new_tcW)

def add_hyperlink(paragraph, url: str, text: str, font_name: str = FONT_NAME, size_pt: float = 12.5, color_rgb: str = "2E75B6"):
    """Adds a clickable hyperlink styled with TH Sarabun New."""
    if not url:
        run = paragraph.add_run(text)
        apply_thai_font(run, font_name=font_name, size_pt=size_pt, color_rgb=RGBColor(46, 117, 182), underline=True)
        return

    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)

    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')

    c = OxmlElement('w:color')
    c.set(qn('w:val'), color_rgb)
    rPr.append(c)

    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)

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

def get_thai_buddhist_date(dt: Optional[datetime] = None) -> str:
    """Returns date in Thai Buddhist Era format (e.g. 11 พฤศจิกายน 2569)."""
    if dt is None:
        dt = datetime.now()
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    year_be = dt.year + 543
    month_th = thai_months[dt.month - 1]
    return f"{dt.day} {month_th} {year_be}"

def create_cyber_digest_docx(articles: List[Dict[str, Any]], output_path: str, date_str: str = "", logo_path: Optional[str] = None, issue_no: str = "01/2569") -> str:
    """
    Creates the official Cyber Threat Digest Word document (.docx)
    matching the exact template (Portrait A4, 6-column landscape table, Cyber Center emblem).
    """
    doc = Document()

    # Portrait A4 with compact margins to ensure 5 stories fit on 1 page
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.32)
    section.bottom_margin = Inches(0.32)
    section.left_margin = Inches(0.35)
    section.right_margin = Inches(0.35)

    thai_date_str = get_thai_buddhist_date()

    if not logo_path:
        default_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
        if os.path.exists(default_logo):
            logo_path = default_logo

    # 1. Header Table: 1 row, 2 columns (borderless)
    # Left column: Logo (1500 dxa); Right column: Centered titles (9498 dxa)
    hdr_table = doc.add_table(rows=1, cols=2)
    hdr_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_table.autofit = False
    set_table_grid(hdr_table, [1500, 9498])
    set_row_cell_widths(hdr_table.rows[0], [1500, 9498])

    col_logo = hdr_table.rows[0].cells[0]
    col_title = hdr_table.rows[0].cells[1]
    col_logo.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    col_title.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    p_logo = col_logo.paragraphs[0]
    p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_logo.paragraph_format.space_before = Pt(0)
    p_logo.paragraph_format.space_after = Pt(0)
    p_logo.paragraph_format.line_spacing = None
    if logo_path and os.path.exists(logo_path):
        r_logo = p_logo.add_run()
        r_logo.add_picture(logo_path, width=Inches(0.95))

    p_title1 = col_title.paragraphs[0]
    p_title1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title1.paragraph_format.space_before = Pt(0)
    p_title1.paragraph_format.space_after = Pt(1)
    p_title1.paragraph_format.line_spacing = Pt(17)
    r_t1 = p_title1.add_run("สถานการณ์ข่าวภัยคุกคามทางไซเบอร์")
    apply_thai_font(r_t1, size_pt=19, bold=True, color_rgb=RGBColor(31, 78, 121))

    p_title2 = col_title.add_paragraph()
    p_title2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title2.paragraph_format.space_before = Pt(0)
    p_title2.paragraph_format.space_after = Pt(0)
    p_title2.paragraph_format.line_spacing = Pt(15)
    r_t2 = p_title2.add_run(f"ประจำวันที่ {thai_date_str}")
    apply_thai_font(r_t2, size_pt=16.5, bold=True, color_rgb=RGBColor(20, 20, 20))

    # 2. Subheader Table (borderless): Left: "ที่ 01/2569", Right: date
    sub_table = doc.add_table(rows=1, cols=2)
    sub_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sub_table.autofit = False
    set_table_grid(sub_table, [5499, 5499])
    set_row_cell_widths(sub_table.rows[0], [5499, 5499])

    c0 = sub_table.rows[0].cells[0]
    p_c0 = c0.paragraphs[0]
    p_c0.paragraph_format.space_before = Pt(2)
    p_c0.paragraph_format.space_after = Pt(2)
    p_c0.paragraph_format.line_spacing = Pt(13)
    r_c0 = p_c0.add_run(f"ที่ {issue_no}")
    apply_thai_font(r_c0, size_pt=14, bold=True)

    c1 = sub_table.rows[0].cells[1]
    p_c1 = c1.paragraphs[0]
    p_c1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_c1.paragraph_format.space_before = Pt(2)
    p_c1.paragraph_format.space_after = Pt(2)
    p_c1.paragraph_format.line_spacing = Pt(13)
    r_c1 = p_c1.add_run(thai_date_str)
    apply_thai_font(r_c1, size_pt=14, bold=True)

    # 3. Main 6-column table with exact dxa widths from template:
    # [738, 2307, 1080, 2520, 2553, 1800] -> Total = 10998 dxa (7.6375 inches)
    col_widths_dxa = [738, 2307, 1080, 2520, 2553, 1800]

    table = doc.add_table(rows=1, cols=6)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_grid(table, col_widths_dxa)
    set_table_borders(table, color="7F7F7F", sz="4", val="single")

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
    set_row_cell_widths(hdr_row, col_widths_dxa)

    for i, title in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=30, bottom=30, left=25, right=25)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = Pt(12)
        r = p.add_run(title)
        apply_thai_font(r, size_pt=12.5, bold=True, color_rgb=RGBColor(255, 255, 255))

    for idx, item in enumerate(articles, 1):
        row = table.add_row()
        row_tr = row._tr.get_or_add_trPr()
        row_tr.append(OxmlElement('w:cantSplit'))
        set_row_cell_widths(row, col_widths_dxa)

        # Col 0: ลำดับ
        c0 = row.cells[0]
        c0.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(c0, top=15, bottom=15, left=15, right=15)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.line_spacing = Pt(11)
        r0 = p0.add_run(str(idx))
        apply_thai_font(r0, size_pt=12, bold=True)

        # Col 1: หัวข้อข่าว
        c1 = row.cells[1]
        c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(c1, top=15, bottom=15, left=25, right=25)
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = Pt(11)
        r1 = p1.add_run(item.get("title", ""))
        apply_thai_font(r1, size_pt=11.5, bold=True, color_rgb=RGBColor(10, 10, 10))

        # Col 2: IOC (Light Amber Background #FBF2D3)
        c2 = row.cells[2]
        c2.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(c2, "FBF2D3")
        set_cell_margins(c2, top=15, bottom=15, left=20, right=20)
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = Pt(11)
        r2 = p2.add_run(item.get("iocs", "ไม่มี"))
        apply_thai_font(r2, size_pt=11, color_rgb=RGBColor(15, 15, 15))

        # Col 3: สาระสำคัญ / ผลกระทบ
        c3 = row.cells[3]
        c3.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(c3, top=15, bottom=15, left=25, right=25)
        p3 = c3.paragraphs[0]
        p3.paragraph_format.space_before = Pt(0)
        p3.paragraph_format.space_after = Pt(0)
        p3.paragraph_format.line_spacing = Pt(11)

        bullets_imp = item.get("key_points", [])
        if not bullets_imp and item.get("summary"):
            bullets_imp = [item.get("summary")]
        elif isinstance(bullets_imp, str):
            bullets_imp = [b.strip() for b in bullets_imp.split("\n") if b.strip()]

        for b_idx, bullet in enumerate(bullets_imp[:3]):
            if b_idx > 0:
                p3 = c3.add_paragraph()
                p3.paragraph_format.space_before = Pt(0)
                p3.paragraph_format.space_after = Pt(0)
                p3.paragraph_format.line_spacing = Pt(11)
            b_text = bullet if bullet.startswith("•") else f"• {bullet}"
            r3 = p3.add_run(b_text)
            apply_thai_font(r3, size_pt=11, color_rgb=RGBColor(15, 15, 15))

        # Col 4: แนวทางป้องกัน / ข้อเสนอแนะ
        c4 = row.cells[4]
        c4.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(c4, top=15, bottom=15, left=25, right=25)
        p4 = c4.paragraphs[0]
        p4.paragraph_format.space_before = Pt(0)
        p4.paragraph_format.space_after = Pt(0)
        p4.paragraph_format.line_spacing = Pt(11)

        bullets_rec = item.get("recommendations", [])
        if not bullets_rec and item.get("soc_recommendation"):
            bullets_rec = [item.get("soc_recommendation")]
        elif isinstance(bullets_rec, str):
            bullets_rec = [b.strip() for b in bullets_rec.split("\n") if b.strip()]

        for b_idx, bullet in enumerate(bullets_rec[:3]):
            if b_idx > 0:
                p4 = c4.add_paragraph()
                p4.paragraph_format.space_before = Pt(0)
                p4.paragraph_format.space_after = Pt(0)
                p4.paragraph_format.line_spacing = Pt(11)
            b_text = bullet if bullet.startswith("•") else f"• {bullet}"
            r4 = p4.add_run(b_text)
            apply_thai_font(r4, size_pt=11, color_rgb=RGBColor(15, 15, 15))

        # Col 5: แหล่งข่าว (Hyperlinks)
        c5 = row.cells[5]
        c5.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(c5, top=15, bottom=15, left=20, right=20)
        p5 = c5.paragraphs[0]
        p5.paragraph_format.space_before = Pt(0)
        p5.paragraph_format.space_after = Pt(0)
        p5.paragraph_format.line_spacing = Pt(11)

        source_val = item.get("source", "")
        link_val = item.get("link", "")
        sources = [s.strip() for s in source_val.split("\n") if s.strip()]
        if not sources:
            sources = [source_val] if source_val else ["แหล่งข่าว"]

        for s_idx, src in enumerate(sources):
            if s_idx > 0:
                p5 = c5.add_paragraph()
                p5.paragraph_format.space_before = Pt(0)
                p5.paragraph_format.space_after = Pt(0)
                p5.paragraph_format.line_spacing = Pt(11)
            if link_val:
                add_hyperlink(p5, link_val, src, font_name=FONT_NAME, size_pt=11, color_rgb="2E75B6")
            else:
                r5 = p5.add_run(src)
                apply_thai_font(r5, size_pt=11, color_rgb=RGBColor(46, 117, 182), underline=True)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    return output_path
