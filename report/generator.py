import uuid
from datetime import datetime, timezone
from typing import List, Dict
import pandas as pd


def build_report(filename: str, phi_spans: List[Dict]) -> Dict:
    """
    Build the redaction report from the final list of phi spans.
    Called after redaction so replacement values are already filled in.
    """
    summary_by_type = {}
    for span in phi_spans:
        entity_type = span.get("entity_type", "UNKNOWN")
        summary_by_type[entity_type] = summary_by_type.get(entity_type, 0) + 1

    report = {
        "job_id": str(uuid.uuid4())[:8],
        "original_filename": filename,
        "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_phi_detected": len(phi_spans),
        "summary_by_type": summary_by_type,
        "entities": [
            {
                "entity_type": s.get("entity_type"),
                "original_value": s.get("text"),
                "replacement": s.get("replacement", "[REDACTED]"),
                "detector": s.get("detector", "unknown"),
                "confidence": round(s.get("score", 0.0), 2),
            }
            for s in phi_spans
        ]
    }

    return report


def report_to_dataframe(report: Dict) -> pd.DataFrame:
    """
    Flatten report entities into a dataframe for Gradio table display.
    Keeping it simple - just the columns that matter for a reviewer.
    """
    if not report.get("entities"):
        return pd.DataFrame(columns=["Entity Type", "Original", "Replacement", "Detector", "Confidence"])

    rows = []
    for e in report["entities"]:
        rows.append({
            "Entity Type": e.get("entity_type", ""),
            "Original": e.get("original_value", ""),
            "Replacement": e.get("replacement", ""),
            "Detector": e.get("detector", ""),
            "Confidence": e.get("confidence", ""),
        })

    return pd.DataFrame(rows)


def report_to_csv(report: Dict) -> str:
    df = report_to_dataframe(report)
    return df.to_csv(index=False)