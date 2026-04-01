import fitz  # pymupdf
import io
from typing import List, Dict

from redaction.synthesizer import get_replacement

# yellow highlight color for synthetic replacements
HIGHLIGHT_COLOR = (1, 0.95, 0.2)  # RGB, roughly yellow

WARNING_BANNER = (
    "⚠ DE-IDENTIFIED DOCUMENT — Highlighted values are synthetic replacements. "
    "Do not use for clinical decisions."
)


def redact_pdf(file_bytes: bytes, phi_spans: List[Dict]) -> tuple[bytes, List[Dict]]:
    """
    Apply redactions to the PDF and return redacted PDF bytes.
    Also returns the phi_spans with replacement values filled in,
    used later for the redaction report.

    Process:
    - find each PHI span in the PDF text layer using pymupdf search
    - cover original text with white rectangle
    - write synthetic replacement on top
    - highlight the replacement in yellow
    - add warning banner on each page
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    updated_spans = []

    for span in phi_spans:
        original_text = span["text"]
        replacement = get_replacement(span["entity_type"], original_text)
        span["replacement"] = replacement

        for page in doc:
            redacted_rects = []
            
            search_terms = _get_searchable_text(original_text, span["entity_type"])
            instances = []
            for term in search_terms:
                found = page.search_for(term, quads=False)
                instances.extend(found)

            for rect in instances:
                # skip if this rect overlaps with an already redacted area
                if any(rect.intersects(r) for r in redacted_rects):
                    continue

                extended_rect = fitz.Rect(
                    rect.x0,
                    rect.y0,
                    max(rect.x1, rect.x0 + len(replacement) * 5),
                    rect.y1
                )

                if rect.y0 > 200 and span["entity_type"] == "LOCATION":
                    continue

                page.draw_rect(extended_rect, color=(1, 1, 1), fill=(1, 1, 1))

                insert_point = fitz.Point(rect.x0 + 1, rect.y1 - 1)
                fontsize = min(9, rect.height * 0.85)

                page.insert_text(
                    insert_point,
                    replacement,
                    fontsize=fontsize,
                    color=(0, 0, 0)
                )

                highlight = page.add_highlight_annot(extended_rect)
                highlight.set_colors(stroke=HIGHLIGHT_COLOR)
                highlight.update()

                redacted_rects.append(rect)

        updated_spans.append(span)
    # add warning banner to every page
    _add_warning_banner(doc)

    # redact QR codes
    _redact_qr_codes(doc)

    output = io.BytesIO()
    doc.save(output)
    doc.close()

    return output.getvalue(), updated_spans


def _add_warning_banner(doc: fitz.Document):
    """
    Add a red warning text banner at the top of every page.
    Small font, doesn't take much space.
    """
    for page in doc:
        page_width = page.rect.width
        banner_rect = fitz.Rect(10, 5, page_width - 10, 20)

        # light red background for the banner
        page.draw_rect(banner_rect, color=(1, 0.8, 0.8), fill=(1, 0.8, 0.8))

        page.insert_text(
            fitz.Point(12, 16),
            WARNING_BANNER,
            fontsize=6.5,
            color=(0.6, 0, 0)
        )

def _get_searchable_text(span_text: str, entity_type: str) -> list[str]:
    if entity_type == "PERSON":
        parts = span_text.strip().split()
        noise = {"sample", "collected", "at", "by", "ref", "age", "sex", "years", "male", "female"}
        clean_parts = [p for p in parts if p.lower() not in noise]
        if len(clean_parts) < len(parts):
            return [" ".join(clean_parts)] if clean_parts else [span_text]

    if entity_type == "LOCATION":
        return [span_text, span_text.upper()]
    
    if entity_type == "URL":
        return [span_text, span_text.upper(), span_text.lower()]
    return [span_text]

def _redact_qr_codes(doc: fitz.Document):
    """
    Cover QR codes and barcodes with white rectangles.
    Both encode record identifiers — indirect re-identification vectors.
    Detection is geometry-based, no need to decode the content.
    QR codes: roughly square, small
    Barcodes: wide and short aspect ratio
    """
    for page in doc:
        for img in page.get_images():
            try:
                bbox = page.get_image_bbox(img[7])
                width = bbox.x1 - bbox.x0
                height = bbox.y1 - bbox.y0
                if height == 0:
                    continue
                aspect_ratio = width / height
                # QR code: square, small
                is_qr = 0.8 <= aspect_ratio <= 1.2 and width < 150
                # barcode: wide and short
                is_barcode = aspect_ratio > 2.5 and height < 80
                if is_qr or is_barcode:
                    page.draw_rect(bbox, color=(1,1,1), fill=(1,1,1))
            except Exception:
                continue