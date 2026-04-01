# HIPAA De-identification System

A prototype for automated redaction of Protected Health Information (PHI) from medical documents. Upload a PDF, detect PHI, replace it with synthetic data, and download a redacted PDF with a full audit trail.

---

## Running the app

### With Docker (recommended)

```bash
git clone <repo-url>
cd hipaa-deidentification

cp .env.example .env
# add your Anthropic API key to .env

docker compose up --build
```

App will be available at `http://localhost:7860`

### Without Docker

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# tesseract needs to be installed at the system level
# ubuntu/wsl: sudo apt install tesseract-ocr tesseract-ocr-eng poppler-utils
# mac: brew install tesseract poppler

cp .env.example .env
# add your Anthropic API key

python main.py
```

---

## How it works

### 1. OCR and text extraction

Per-page hybrid extraction — not a single global strategy.

For each page, `pdfplumber` reads the text layer directly (fast, error-free, preserves table structure). If the page also has embedded images (stamps, handwritten notes), `pytesseract` runs separately on just those image regions. If the entire page has no text layer (fully scanned document), the whole page is converted to an image and OCR'd.

This avoids running OCR on content that is already clean text — tesseract introduces character recognition errors on text-layer PDFs and breaks table alignment. The sample files provided are fully text-layer PDFs so tesseract is not invoked on them at all.

Known limitation: handwriting recognition accuracy with Tesseract is low and is out of scope for this prototype.

### 2. PHI detection

Two-pass hybrid detection:

**Presidio (primary)** — Microsoft's open source PHI detection library. Purpose-built for HIPAA identifiers with built-in recognizers for names, dates, phone numbers, addresses, emails, and IDs. No GPU required.

Three custom recognizers are added on top of Presidio's defaults:

- Indian phone numbers — 10-digit mobiles (starting 6-9), optional leading 0, +91 prefix variants, and STD code landlines. Presidio's default phone recognizer targets US formats and misses Indian formats entirely.
- Indian address components — named building, road, and area components ending with keywords like Road, Nagar, Complex, Bungalow, Colony etc. Detected as LOCATION entities.
- Age — numeric age with year suffix variants (Years, Yrs, y). HIPAA lists age as a protected identifier and Presidio has no built-in recognizer for it.

**Claude API (secondary)** — A second pass using `claude-sonnet-4-20250514` catches contextual PHI that pattern-based detection misses — doctor names embedded in sentences, non-standard ID formats. Results from both passes are merged and deduplicated by span overlap.

**Precision vs recall tradeoff** — HIPAA defines 18 identifier categories but Presidio's entity taxonomy does not map 1:1 to all 18. General NLP models are also trained on general English text, not medical documents — "Mill" in Mill/cumm gets flagged as a surname, reference range numbers get flagged as IDs. A clinical allowlist is applied after detection to ensure test names, units, and reference values are never redacted. This is domain adaptation, not a hack — the alternative is fine-tuning a NER model on labeled clinical text (e.g. Med7, AWS Comprehend Medical) which is out of scope for this prototype.

Bare 8-digit landline numbers without a context keyword are intentionally skipped — indistinguishable from 8-digit clinical values without surrounding context.

### 3. Redaction and synthetic replacement

PHI spans are replaced with synthetic values rather than black-box placeholders. This preserves the visual and semantic structure of the document so it remains clinically readable:

| PHI type | Replacement strategy |
|---|---|
| Patient / doctor name | faker-generated Indian name, Dr. prefix preserved |
| Age | Random age in same format (Years / Yrs) |
| Phone number | Random number matching original format |
| Date | Original date shifted by random 1-30 days |
| Address component | Random uppercase string, same length as original |
| Email | faker-generated email |
| Patient ID / Report ID | Random alphanumeric, same length |
| URL | [REDACTED_URL] |

Date shifting preserves relative temporal relationships — the gap between collection date and reporting date stays meaningful even after de-identification.

All synthetic replacements are highlighted in yellow in the output PDF. A warning banner is added to every page: "DE-IDENTIFIED DOCUMENT — Highlighted values are synthetic replacements. Do not use for clinical decisions." This prevents downstream misuse if the document is accidentally treated as a real record.

### 4. Redaction report

A full audit trail is returned alongside the redacted PDF. The report shows every PHI instance detected, its type, the synthetic replacement, which detector caught it, and the confidence score. Available as an in-UI table and a downloadable CSV.

---

## Design decisions

**Why Presidio + Claude instead of a single model**

Presidio is deterministic, fast, and free per call — reliable for standard patterns like phone numbers, emails, and dates. Claude understands context and catches what Presidio misses. Running Presidio first and Claude as a top-up pass keeps latency and cost reasonable.

**Why Gradio instead of React**

The core interaction is upload a file, get a file back. Gradio has native binary file input and output components that handle PDF download out of the box. It also runs as part of the Python app — no separate frontend service, no nginx, simpler Docker setup.

**Why synthetic data instead of [REDACTED] placeholders**

If the de-identified output is used for AI training (the primary use case mentioned in the brief), placeholder tokens corrupt the training data — a model trained on "Patient [PATIENT_NAME] presented with..." learns nothing useful about clinical language. Synthetic replacement preserves the linguistic structure.

**Why HIPAA framework with Indian phone formats**

HIPAA defines what to redact (the 18 identifier categories). Indian phone formats define how to detect phone numbers for this document set. These are two separate layers — the framework is US-based, the detection implementation is adapted for the sample documents provided from Indian labs.

**Regional language handling**

The sample documents include Kannada text in lab headers. The NER model processes English only. Regional language content is treated as institutional branding — patient identifiers in the provided samples appear exclusively in English. If patient PHI appeared in regional scripts, a multilingual model would be required.

---

## Project structure

```
hipaa-deidentification/
├── config.py              # env vars, allowlists, constants
├── main.py                # entry point
├── ocr/
│   ├── extractor.py       # per-page hybrid extraction
│   └── utils.py           # text cleaning helpers
├── detection/
│   ├── presidio_engine.py # presidio + custom recognizers (phone, address, age)
│   ├── claude_engine.py   # claude API secondary detection pass
│   └── merger.py          # merge and deduplicate spans from both detectors
├── redaction/
│   ├── synthesizer.py     # synthetic replacement generation
│   └── pdf_redactor.py    # apply redactions, highlights, warning banner
├── report/
│   └── generator.py       # redaction report JSON, dataframe, CSV
├── app/
│   ├── ui.py              # gradio layout and components
│   └── handlers.py        # pipeline orchestration
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Known limitations

- Lab names and address components rendered in decorative or multi-object fonts may not be redacted — pymupdf's text search cannot match strings split across separate PDF text objects. Production systems would use font-aware text extraction.
- Footer content rendered as graphic elements (lab address, timing in image-based footers) is not extracted by pdfplumber and therefore not detected or redacted. This applies to facility information, not patient PHI.
- Bare 8-digit landline numbers without a context keyword are not detected — false positive risk against 8-digit clinical values is too high without surrounding context.
- Handwriting recognition accuracy is low with Tesseract.
- Date shifting preserves relative temporal relationships but does not guarantee full de-identification for very specific date combinations — an edge case for research use.
- Claude API secondary pass adds latency of approximately 2-4 seconds per document.
- Documents with patient identifiers in regional scripts (Kannada, Hindi etc.) are not fully de-identified — the NER model processes English only.