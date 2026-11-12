import re
from pythainlp.tokenize import word_tokenize

def insert_thai_word_breaks(text: str) -> str:
    """
    Inserts zero-width spaces (\u200b) at Thai word boundaries
    so that Word/LibreOffice line-breaking breaks cleanly on whole words
    without cutting Thai words awkwardly.
    """
    if not text:
        return ""
    # Tokenize by Thai words using newmm
    tokens = word_tokenize(text, engine="newmm")
    # Join with zero-width space
    return "\u200b".join(tokens)

def format_bullet_text(text: str) -> str:
    """
    Formats a bullet point:
    1. Cleans existing bullets/numbers/excess whitespace
    2. Uses non-breaking space (\u00a0) immediately after • so bullet and first word are NEVER split
    3. Inserts zero-width spaces (\u200b) between Thai words for proper line wrapping
    """
    if not text:
        return ""
    cleaned = re.sub(r"^[•\-\*\d\.\s]+", "", text.strip())
    cleaned = " ".join(cleaned.split())
    segmented = insert_thai_word_breaks(cleaned)
    return f"•\u00a0{segmented}"

if __name__ == "__main__":
    sample = "ผู้โจมตีสามารถเข้าถึงและรั่วไหลข้อมูลสำคัญรวมถึงข้อมูลการตั้งค่าระบบได้"
    print("Segmented:")
    tokens = word_tokenize(sample, engine="newmm")
    print(tokens)
    print("Formatted bullet:", repr(format_bullet_text(sample)[:50]))
