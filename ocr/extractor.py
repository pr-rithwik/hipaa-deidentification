import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
import io

from ocr.utils import clean_text, is_likely_scanned


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Per-page hybrid extraction.
    - text layer via pdfplumber (clean, fast, preserves structure)
    - embedded images via tesseract (stamps, handwritten bits)
    Tried doing full OCR on everything first but it was mangling the table values
    so switched to this approach.
    """
    all_text = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            image_text = ""

            if page.images:
                image_text = _ocr_page_images(page)

            is_scanned = is_likely_scanned(page_text)
            if is_scanned and not page.images:
                image_text = _ocr_full_page(file_bytes, page_num)

            combined = page_text + "\n" + image_text
            all_text.append(clean_text(combined))

    return "\n\n".join(all_text)


def _ocr_page_images(page) -> str:
    """
    Run tesseract on embedded images within a page.
    Logos and QR codes usually return garbage but that's fine,
    they don't contain PHI anyway.
    """
    ocr_results = []

    for img_obj in page.images:
        try:
            # crop the image region from the page
            bbox = (img_obj["x0"], img_obj["top"], img_obj["x1"], img_obj["bottom"])
            cropped = page.within_bbox(bbox).to_image(resolution=150)
            pil_img = cropped.original

            text = pytesseract.image_to_string(pil_img, lang="eng")
            if text.strip():
                ocr_results.append(text.strip())
        except Exception:
            # if a specific image fails just skip it
            continue

    return "\n".join(ocr_results)


def _ocr_full_page(file_bytes: bytes, page_num: int) -> str:
    """
    Convert entire page to image and OCR it.
    Only called when the text layer is basically empty (scanned page).
    """
    try:
        images = convert_from_bytes(file_bytes, first_page=page_num + 1, last_page=page_num + 1)
        if not images:
            return ""
        text = pytesseract.image_to_string(images[0], lang="eng")
        return text.strip()
    except Exception:
        return ""