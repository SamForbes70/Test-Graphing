"""Source validation utilities."""
from __future__ import annotations

import pandas as pd

VALID_CONFIDENCE = {"High", "Medium", "Low"}


def validate_event_sources(events: pd.DataFrame) -> pd.DataFrame:
    """Return validation findings for event annotations."""
    findings = []
    if events.empty:
        return pd.DataFrame([{"severity": "warning", "finding": "No event annotations were generated."}])
    for _, row in events.iterrows():
        title = row.get("event_title", "Unknown event")
        source_url = str(row.get("source_url", "")).strip()
        confidence = row.get("confidence_level", "")
        if title != "No reliable single-event explanation found" and not source_url:
            findings.append({"severity": "error", "finding": f"Missing source URL for event: {title}"})
        if confidence and confidence not in VALID_CONFIDENCE:
            findings.append({"severity": "warning", "finding": f"Invalid confidence level for event {title}: {confidence}"})
    if not findings:
        findings.append({"severity": "ok", "finding": "Event source checks passed."})
    return pd.DataFrame(findings)
