"""Core data structures for OSINT Workbench.

Every piece of information the tool collects is a Finding with full
provenance: where it came from, when it was retrieved, and how much
confidence the source warrants. This is the backbone of the whole app.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Finding:
    source: str            # collector that produced it, e.g. "github"
    category: str          # "account" | "identity" | "infrastructure" | "exposure"
    fact_type: str         # "username" | "email" | "name" | "location" | "avatar" | ...
    value: str             # the fact itself
    url: str = ""          # provenance: where it was seen
    snippet: str = ""      # short raw evidence excerpt
    confidence: int = 50   # 0-100, set by collector / correlation engine
    retrieved_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None  # set after DB insert

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["retrieved_at_iso"] = time.strftime(
            "%Y-%m-%d %H:%M:%S UTC", time.gmtime(self.retrieved_at)
        )
        return d


@dataclass
class Link:
    """A asserted relationship between two findings, produced by the
    correlation engine. Confidence reflects strength of evidence."""
    from_id: int
    to_id: int
    reason: str
    confidence: int


CONFIDENCE_LABELS = [
    (80, "High"),
    (50, "Medium"),
    (0, "Low"),
]


def confidence_label(score: int) -> str:
    for threshold, label in CONFIDENCE_LABELS:
        if score >= threshold:
            return label
    return "Low"
