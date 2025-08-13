import fitz  # PyMuPDF
import os
import re

# --- 1. File paths
pdf_path = "TH Delhi 21-07.pdf"
output_txt_path = "output_text_fixed.txt"


# --- 2. Extract metadata from file name (robust, supports many separators and date formats)
import itertools
file_name = os.path.basename(pdf_path)
file_base = os.path.splitext(file_name)[0]

# Define possible separators and date regexes
separators = r"[_\-•●.,:;\s]+"
date_patterns = [
    r"\d{2}[-_/~]?(?:\d{2}|[A-Za-z]+)[-_/~]?\d{2,4}",  # 12-07-2025, 12_07_2025, 12July2025, 12~07~2025
    r"\d{4}[-_/~]?\d{2}[-_/~]?\d{2}",                  # 2025-07-12
    r"\d{2}[A-Za-z]+\d{4}",                            # 16July2025
    r"\d{2}--\d{2}",                                   # 16--7
    r"\d{2}[-_/~]?[A-Za-z]+[-_/~]?\d{2,4}",            # 03_July_2025, 16-July-2025
    r"\d{2}[-_/~]?\d{2,4}",                            # 21-07-25
]

# Try to extract date
date = "Unknown"
for pat in date_patterns:
    m = re.search(pat, file_base)
    if m:
        date = m.group(0)
        break

# Remove date from base for further splitting
file_base_wo_date = file_base.replace(date, "") if date != "Unknown" else file_base

# Split by all possible separators
parts = re.split(separators, file_base_wo_date)
parts = [p for p in parts if p and not p.isdigit()]

# Heuristics: first part = newspaper, next = edition/city (if present)
newspaper_name = parts[0].strip() if parts else "Unknown"
edition = parts[1].strip() if len(parts) > 1 else "Unknown"

# Fallback: try to extract from first page text if any field is Unknown
if newspaper_name == "Unknown" or edition == "Unknown" or date == "Unknown":
    doc = fitz.open(pdf_path)
    first_page_text = doc[0].get_text()
    # Try to find a date in the first page text
    date_match = re.search(r"(\d{1,2}[-/ ]\d{1,2}[-/ ]\d{2,4})", first_page_text)
    if date == "Unknown":
        date = date_match.group(1) if date_match else "Unknown"
    # Try to find a newspaper name (first ALL CAPS line, not noise)
    lines = [l.strip() for l in first_page_text.splitlines() if l.strip()]
    if newspaper_name == "Unknown":
        for line in lines:
            if line.isupper() and 4 < len(line) < 50 and not re.search(r"EDITION|PAGE|NEWS|BUREAU|www|FOLLOW US|\d", line):
                newspaper_name = line
                break
    # Try to find edition (look for 'Edition' in text)
    if edition == "Unknown":
        for line in lines:
            if 'edition' in line.lower():
                edition = line.strip()
                break
    doc.close()

# --- 3. Load PDF
doc = fitz.open(pdf_path)


# --- 4. Function to split articles based on heading patterns and filter noise
import re
NOISE_PATTERNS = [
    r"^MONDAY$", r"^EDITION$", r"^PAGE( \d+)?$", r"^NEWS$", r"^INTERNATIONAL$", r"^EDITION$",
    r"^The Hindu Bureau$", r"^Press Trust of India$", r"^[A-Z ]+ BUREAU$", r"^www\.", r"^FOLLOW US$",
    r"^Vol\. ", r"^No\. ", r"^Chennai$", r"^Bengaluru$", r"^Hyderabad$", r"^Kolkata$", r"^Mumbai$",
    r"^NEW DELHI$", r"^PATNA$", r"^VIJAYAWADA$", r"^KATHMANDU$", r"^SWEIDA$", r"^DEIR AL-BALAH$",
    r"^\d{1,2}$", r"^\W*$", r"^»$", r"^\s*$"
]
NOISE_REGEX = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)

def split_articles(text):
    lines = text.splitlines()
    articles = []
    current_article = []

    for line in lines:
        stripped = line.strip()
        # Check if it's a heading: ALL CAPS and short
        if stripped.isupper() and 5 < len(stripped) < 100:
            if current_article:
                articles.append("\n".join(current_article))
                current_article = []
        current_article.append(stripped)

    if current_article:
        articles.append("\n".join(current_article))

    # Filter out noisy articles
    def is_noisy(article):
        # If the first line (headline) or the whole article matches noise, skip
        lines = [l.strip() for l in article.splitlines() if l.strip()]
        if not lines:
            return True
        if NOISE_REGEX.match(lines[0]):
            return True
        # Optionally, filter articles that are too short
        if len(" ".join(lines)) < 40:
            return True
        return False

    return [a for a in articles if not is_noisy(a)]

# --- 5. Process PDF
with open(output_txt_path, "w", encoding="utf-8") as out_file:
    # Top metadata
    out_file.write(
        f"# Metadata: newspaper_name={newspaper_name}, edition={edition}, "
        f"date={date}, source_file={file_name}, total_pages={len(doc)}\n\n"
    )

    article_count = 0

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text()
        clean_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

        # Split by header-like patterns
        articles = split_articles(clean_text)

        for article in articles:
            article_count += 1
            out_file.write(
                f"---\n# Article {article_count} | Page {page_number} | Newspaper: {newspaper_name} | "
                f"Edition: {edition} | Date: {date} | Source: {file_name}\n"
            )
            out_file.write(article.strip() + "\n\n")

print(f"✅ Finished. Total articles: {article_count}")
