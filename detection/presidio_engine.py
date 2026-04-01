from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from typing import List

from config import (
    CLINICAL_ALLOWLIST, PHONE_CONTEXT_KEYWORDS, ADDRESS_CONTEXT_KEYWORDS, 
    ADDRESS_COMPONENT_KEYWORDS, AGE_CONTEXT_KEYWORDS
)


def _build_analyzer() -> AnalyzerEngine:
    # using spacy small model, en_core_web_lg is more accurate but too heavy for this
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
    })
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

    # add indian phone number recognizer on top of default ones
    phone_recognizer = PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=[
            Pattern(
                name="indian_mobile",
                # covers: 10-digit mobile, +91 prefix, landline with STD code
                # not covering bare 8-digit landlines - too many false positives with lab values
                regex=r"(\+91[\s\-]?)?0?[6-9]\d{9}|0\d{2,4}[\s\-]?\d{6,8}",
                score=0.6
            )
        ],
        context=PHONE_CONTEXT_KEYWORDS
    )

    # indian address block recognizer
    # matches patterns starting with a number followed by address components
    address_keywords = "|".join(ADDRESS_COMPONENT_KEYWORDS)
    address_recognizer = PatternRecognizer(
        supported_entity="LOCATION",
        patterns=[
            Pattern(
                name="indian_address_component",
                regex=rf"(?i)[A-Za-z][A-Za-z\s]{{2,}}(?:{address_keywords})",
                score=0.6
            )
        ],
        context=ADDRESS_CONTEXT_KEYWORDS
    )

    age_recognizer = PatternRecognizer(
        supported_entity="AGE",
        patterns=[
            Pattern(
                name="age_pattern",
                regex=r"(?i)\b\d{1,3}\s*(?:years?|yrs?|y\.?o\.?|y\b)",
                score=0.85
            )
        ],
        context=AGE_CONTEXT_KEYWORDS
    )
    url_recognizer = PatternRecognizer(
        supported_entity="URL",
        patterns=[
            Pattern(
                name="url_pattern",
                regex=r"(?i)(https?://|www\.)[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(/\S*)?",
                score=0.85
            )
        ]
    )
    analyzer.registry.add_recognizer(url_recognizer)
    analyzer.registry.add_recognizer(age_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(address_recognizer)
    # analyzer.registry.add_recognizer(pincode_recognizer)

    return analyzer


# init once at module load, reusing across requests
_analyzer = _build_analyzer()


def detect_phi(text: str) -> List[RecognizerResult]:
    """
    Run Presidio on the extracted text and return spans.
    Filters out anything in the clinical allowlist after detection.
    """
    results = _analyzer.analyze(
        text=text,
        language="en",
        entities=[
            "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS",
            "LOCATION", "DATE_TIME", "URL", "ID", "AGE"
        ],
        score_threshold=0.4  # keeping this low, merger will handle confidence filtering
    )

    filtered = _apply_allowlist(results, text)
    return filtered


def _apply_allowlist(results: List[RecognizerResult], text: str) -> List[RecognizerResult]:
    """
    Remove any spans that match clinical terms we never want redacted.
    Presidio occasionally flags test names and units as proper nouns.
    """
    clean = []
    for r in results:
        span_text = text[r.start:r.end].strip()

        # skip if exact match or substring of an allowlisted term
        # if any(span_text.lower() == term.lower() for term in CLINICAL_ALLOWLIST):
        #     continue
        if any(term.lower() in span_text.lower() for term in CLINICAL_ALLOWLIST):
            continue
        # skip pure numeric spans - reference range values kept getting flagged
        if span_text.replace(".", "").replace("-", "").replace(" ", "").isdigit():
            continue
        
        # drop suspiciously short date spans - likely partial matches or artifacts
        if r.entity_type == "DATE_TIME" and len(span_text) < 4:
            continue
        
        clean.append(r)

    final = []
    person_texts = [text[r.start:r.end] for r in clean if r.entity_type == "PERSON"]
    for r in clean:
        if r.entity_type == "PERSON":
            span_text = text[r.start:r.end]
            # skip if a longer span contains this span's text
            if any(span_text != p and span_text in p for p in person_texts):
                continue
        final.append(r)
    return final