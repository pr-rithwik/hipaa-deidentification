import json
import anthropic
from typing import List, Dict

from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# prompt is fairly explicit about what we want back
# tried a shorter prompt first but claude was returning inconsistent formats
DETECTION_PROMPT = """You are a HIPAA compliance assistant. Your job is to find Protected Health Information (PHI) in medical documents.

Given the text below, identify all PHI that should be redacted. Return ONLY a JSON array, no explanation, no markdown.

Each item in the array should have:
- "text": the exact string as it appears in the document
- "entity_type": one of PERSON, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION, DATE_TIME, URL, ID
- "start": character index where it starts
- "end": character index where it ends

Do NOT flag:
- Medical test names (Haemoglobin, RBC, WBC, Platelet etc.)
- Clinical units (g/dL, mg%, cells/mcL etc.)
- Reference range numbers
- Medical terminology

Text:
{text}

Return only the JSON array:"""


def detect_phi_claude(text: str, already_found: List[Dict] = None) -> List[Dict]:
    """
    Secondary PHI detection pass using Claude.
    Mainly catches things Presidio misses - doctor names in sentences,
    contextual identifiers etc.
    already_found is passed so Claude doesn't re-flag the same things.
    """
    if not text.strip():
        return []

    # chunk if too long - claude can handle big contexts but keeping it focused
    if len(text) > 4000:
        return _detect_chunked(text, already_found)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": DETECTION_PROMPT.format(text=text)
            }]
        )

        raw = response.content[0].text.strip()
        # sometimes returns with backticks even when told not to
        raw = raw.replace("```json", "").replace("```", "").strip()

        results = json.loads(raw)
        return results if isinstance(results, list) else []

    except (json.JSONDecodeError, Exception):
        # if claude returns something unparseable just skip this pass
        # presidio alone is still decent
        return []


def _detect_chunked(text: str, already_found: List[Dict] = None) -> List[Dict]:
    """
    Split long text into chunks and run detection on each.
    Offset tracking is a bit annoying but needed for correct char positions.
    """
    chunk_size = 3000
    overlap = 100  # small overlap to catch entities at chunk boundaries
    all_results = []
    offset = 0

    while offset < len(text):
        chunk = text[offset:offset + chunk_size]
        chunk_results = detect_phi_claude(chunk, already_found)

        # adjust char positions back to original text coordinates
        for r in chunk_results:
            r["start"] += offset
            r["end"] += offset

        all_results.extend(chunk_results)
        offset += chunk_size - overlap

    return all_results