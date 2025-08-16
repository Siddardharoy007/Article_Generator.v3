from pymupdf4llm import PyMuPdfReader
import re
import os

# --- 1. File paths
pdf_path = "THE HINDU AD-FREE HD 12~07~2025.pdf"
output_txt_path = "output_text_final_llm.txt"

# --- 2. Noise patterns
NOISE_PATTERNS = [
    r"^MONDAY$", r"^EDITION$", r"^PAGE( \d+)?$", r"^NEWS$", r"^INTERNATIONAL$", r"^EDITION$",
    r"^The Hindu Bureau$", r"^Press Trust of India$", r"^[A-Z ]+ BUREAU$", r"^www\.", r"^FOLLOW US$",
    r"^Vol\. ", r"^No\. ", r"^Chennai$", r"^Bengaluru$", r"^Hyderabad$", r"^Kolkata$", r"^Mumbai$",
    r"^NEW DELHI$", r"^PATNA$", r"^VIJAYAWADA$", r"^KATHMANDU$", r"^SWEIDA$", r"^DEIR AL-BALAH$",
    r"^\d{1,2}$", r"^\W*$", r"^»$", r"^\s*$"
]
NOISE_REGEX = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)

# --- 3. Improved article splitter (with pymupdf4llm text)
def split_articles(text):
    lines = text.splitlines()
    articles = []
    current_article = []

    in_brief_mode = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip IN BRIEF sections
        if stripped.upper().startswith("IN BRIEF"):
            in_brief_mode = True
            continue
        if in_brief_mode and stripped.isupper() and len(stripped) > 10:
            in_brief_mode = False
        if in_brief_mode:
            continue

        # Detect heading
        if stripped.isupper() and 5 < len(stripped) < 100:
            if current_article:
                articles.append("\n".join(current_article))
                current_article = []
        current_article.append(stripped)

    if current_article:
        articles.append("\n".join(current_article))

    # --- Filter noise
    def is_noisy(article):
        lines = [l.strip() for l in article.splitlines() if l.strip()]
        if not lines:
            return True
        if NOISE_REGEX.match(lines[0]):
            return True

        text = " ".join(lines)
        if re.search(r"(Answers on page|Which city|Match the following|quiz)", text, re.IGNORECASE):
            return True
        if re.search(r"(CITY EDITION|Printed at|Vol\.|No\.)", text, re.IGNORECASE):
            return True

        return False

    return [a for a in articles if not is_noisy(a)]

# --- 4. Load PDF with pymupdf4llm
reader = PyMuPdfReader()
doc_chunks = reader.get_text(pdf_path, page_numbers=None)  
# This gives structured text chunks per page

# --- 5. Process and write
article_count = 0
with open(output_txt_path, "w", encoding="utf-8") as out_file:
    out_file.write(f"# Extracted (Final Clean with pymupdf4llm) from {os.path.basename(pdf_path)}\n\n")

    for chunk in doc_chunks:
        page_number = chunk["page"] + 1
        text = chunk["text"]
        articles = split_articles(text)

        for article in articles:
            article_count += 1
            out_file.write(f"---\n# Article {article_count} | Page {page_number}\n")
            out_file.write(article.strip() + "\n\n")

print(f"✅ Finished. Total clean articles extracted with pymupdf4llm: {article_count}")
