import tempfile
import os
from typing import Tuple
import pandas as pd

from ocr.extractor import extract_text_from_pdf
from detection.presidio_engine import detect_phi
from detection.claude_engine import detect_phi_claude
from detection.merger import merge_results
from redaction.pdf_redactor import redact_pdf
from report.generator import build_report, report_to_dataframe, report_to_csv


def process_document(file_bytes: bytes) -> Tuple[str, pd.DataFrame, str]:
    """
    Main pipeline handler - called when user clicks De-identify.
    Returns:
        - path to redacted PDF (Gradio needs a file path for download)
        - dataframe for the report table
        - summary markdown string
    """
    if file_bytes is None:
        return None, pd.DataFrame(), None, "No file uploaded."

    try:
        # step 1 - extract text
        extracted_text = extract_text_from_pdf(file_bytes)

        if not extracted_text.strip():
            return None, pd.DataFrame(), None, "Could not extract text from this PDF."

        # step 2 - detect PHI with presidio
        presidio_results = detect_phi(extracted_text)

        # step 3 - secondary pass with claude
        # passing presidio results so claude doesn't duplicate
        presidio_as_dicts = [
            {"text": extracted_text[r.start:r.end], "start": r.start, "end": r.end}
            for r in presidio_results
        ]
        claude_results = detect_phi_claude(extracted_text, already_found=presidio_as_dicts)

        # step 4 - merge both result sets
        merged = merge_results(presidio_results, claude_results, extracted_text)

        if not merged:
            return None, pd.DataFrame(), None, "No PHI detected in this document."

        # step 5 - redact the PDF
        redacted_bytes, spans_with_replacements = redact_pdf(file_bytes, merged)

        # step 6 - build report
        report = build_report("uploaded_document.pdf", spans_with_replacements)
        df = report_to_dataframe(report)

        # step 7 - save redacted PDF to temp file for Gradio to serve
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_redacted.pdf")
        tmp.write(redacted_bytes)
        tmp.close()

        total = report["total_phi_detected"]
        summary = f"**{total} PHI instances detected and redacted.** " \
                  f"Highlighted values in the output PDF are synthetic replacements."

        csv_tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_report.csv", mode="w")
        csv_tmp.write(report_to_csv(report))
        csv_tmp.close()

        return tmp.name, df, csv_tmp.name, summary

    except Exception as e:
        # not great error handling but good enough for a prototype
        return None, pd.DataFrame(), None, f"Something went wrong: {str(e)}"