import fitz  # pymupdf
import pytesseract
from PIL import Image

from ocr.utils import clean_text, is_likely_scanned


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Per-page hybrid extraction using pymupdf only.
    Replaces the pdfplumber + pymupdf split — single library, unified coordinate system.

    Strategy per page:
    - get text layer via get_text() (fast, clean)
    - if page has images → OCR just those image regions
    - if text layer is empty → OCR full page
    """
    all_text = []

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            page_text = page.get_text() or ""
            image_text = ""

            images = page.get_images()

            if images:
                image_text = _ocr_page_images(page, images)

            if is_likely_scanned(page_text) and not images:
                image_text = _ocr_full_page(page)

            combined = page_text + "\n" + image_text
            all_text.append(clean_text(combined))

    return "\n\n".join(all_text)


def _ocr_page_images(page: fitz.Page, images: list) -> str:
    """
    Run tesseract on embedded image regions within the page.
    Uses pymupdf to clip and rasterize — no pdfplumber needed.
    """
    ocr_results = []

    for img in images:
        try:
            bbox = page.get_image_bbox(img[7])

            # clip the page to the image region and render to pixmap
            clip = fitz.Rect(bbox)
            mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
            pix = page.get_pixmap(matrix=mat, clip=clip)

            # convert pixmap to PIL image for tesseract
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            text = pytesseract.image_to_string(pil_img, lang="eng")
            if text.strip():
                ocr_results.append(text.strip())

        except Exception:
            continue

    return "\n".join(ocr_results)


def _ocr_full_page(page: fitz.Page) -> str:
    """
    Rasterize the full page and OCR it.
    Only called when text layer is empty (fully scanned page).
    """
    try:
        mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
        pix = page.get_pixmap(matrix=mat)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return pytesseract.image_to_string(pil_img, lang="eng").strip()
    except Exception:
        return ""