import re
from config import MIN_TEXT_LENGTH_PER_PAGE


def clean_text(text: str) -> str:
    """
    Basic cleanup after extraction.
    """
    if not text:
        return ""

    # collapse multiple spaces but keep newlines
    text = re.sub(r" {2,}", " ", text)

    # remove null bytes and other control chars that sometimes sneak in
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    # strip trailing spaces on each line
    lines = [line.rstrip() for line in text.splitlines()]

    # drop completely empty lines in a row (keep single empty lines for spacing)
    cleaned = []
    prev_empty = False
    for line in lines:
        is_empty = line.strip() == ""
        if is_empty and prev_empty:
            continue
        cleaned.append(line)
        prev_empty = is_empty

    return "\n".join(cleaned).strip()


def is_likely_scanned(text: str, threshold: int = MIN_TEXT_LENGTH_PER_PAGE) -> bool:
    """
    Quick check if extracted text is suspiciously short.
    Used to decide whether to fall back to full-page OCR.
    """
    return len(text.strip()) < threshold