from typing import List, Dict
from presidio_analyzer import RecognizerResult


def merge_results(
    presidio_results: List[RecognizerResult],
    claude_results: List[Dict],
    text: str
) -> List[Dict]:
    """
    Combines spans from both detectors into a single deduplicated list.
    Presidio results are generally more precise for standard patterns.
    Claude catches the contextual stuff Presidio misses.
    """
    combined = []

    # normalize presidio results to same dict format as claude results
    for r in presidio_results:
        combined.append({
            "text": text[r.start:r.end],
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": r.score,
            "detector": "presidio"
        })

    # add claude results, skip if they overlap with something presidio already found
    for r in claude_results:
        start = r.get("start", 0)
        end = r.get("end", 0)
        entity_type = r.get("entity_type", "UNKNOWN")
        span_text = r.get("text", text[start:end])

        if not _overlaps_with_existing(start, end, combined):
            combined.append({
                "text": span_text,
                "entity_type": entity_type,
                "start": start,
                "end": end,
                "score": 0.7,  # default confidence for claude detections
                "detector": "claude"
            })

    # sort by position in document
    combined.sort(key=lambda x: x["start"])

    return combined


def _overlaps_with_existing(start: int, end: int, existing: List[Dict]) -> bool:
    """
    Check if a span overlaps with any already in our list.
    Using simple range overlap - good enough for this.
    """
    for e in existing:
        # overlap condition: not (new_end <= existing_start or new_start >= existing_end)
        if not (end <= e["start"] or start >= e["end"]):
            return True
    return False