"""Correlation engine — turns a pile of findings into an assessment.

Three jobs:
1. LINK: assert relationships between findings (e.g. a GitHub profile
   whose twitter_username matches a Twitter profile found by the
   username search). Linked accounts get a confidence boost.
2. CONTRADICT: flag mutually inconsistent identity facts (e.g. two
   different locations) instead of silently merging them.
3. VERDICT: summarise the investigation as an overall verification
   assessment with evidence counts.

MVP heuristics, deliberately transparent: every boost or flag carries
a human-readable reason, so the report stays explainable.
"""

from __future__ import annotations

import re

from .models import Finding, Link

BOOST_FOR_LINKED = 10          # applied when a profile is corroborated
HIGH_CONFIDENCE = 80


def _norm(v: str) -> str:
    return re.sub(r"[^a-z0-9]", "", v.lower())


def correlate(inv_id: int, findings: list[Finding],
              input_value: str) -> tuple[list[Link], list[Finding], str]:
    """Returns (links, contradiction-flag pseudo-findings, verdict)."""
    links: list[Link] = []
    flags: list[Finding] = []

    profiles = [f for f in findings if f.fact_type == "profile"]
    input_key = _norm(input_value.split("@")[0])

    # -- 1. Cross-platform handle matching -------------------------------
    # If a profile finding mentions a handle that appears in another
    # finding (e.g. GitHub lists twitter "jane" and username search found
    # Twitter "jane"), link them and boost both.
    handles = {}  # normalised handle -> finding ids
    for f in profiles:
        meta_handle = f.metadata.get("login") or f.metadata.get("username")
        if meta_handle:
            handles.setdefault(_norm(meta_handle), []).append(f)

    for f in findings:
        if f.fact_type not in ("twitter", "linked_account") or f.id is None:
            continue
        key = _norm(str(f.metadata.get("shortname") or f.value.split(":")[-1].strip()))
        for pf in handles.get(key, []):
            if pf.id and pf.id != f.id:
                links.append(Link(
                    from_id=f.id, to_id=pf.id,
                    reason=f"Handle '{key}' cross-referenced between {f.source} and {pf.source}",
                    confidence=85,
                ))
                f.confidence = min(100, f.confidence + BOOST_FOR_LINKED)
                pf.confidence = min(100, pf.confidence + BOOST_FOR_LINKED)

    # -- 2. Gravatar-verified account links boost matching profiles ------
    gravatar_platforms = {
        str(f.metadata.get("platform", "")).lower()
        for f in findings
        if f.fact_type == "linked_account" and f.source == "gravatar"
    }
    if gravatar_platforms:
        for f in profiles:
            site = str(f.metadata.get("site", "")).lower()
            if any(p in site for p in gravatar_platforms):
                f.confidence = min(100, f.confidence + 15)
                if f.id:
                    gv = next(g for g in findings
                              if g.fact_type == "linked_account"
                              and str(g.metadata.get("platform", "")).lower() in site)
                    if gv.id:
                        links.append(Link(
                            from_id=gv.id, to_id=f.id,
                            reason="Profile matches a Gravatar-verified account link "
                                   "(owner-confirmed on Gravatar)",
                            confidence=90,
                        ))

    # -- 3. Contradiction detection --------------------------------------
    for fact_type in ("location", "name"):
        vals = {f.value for f in findings if f.fact_type == fact_type}
        if len(vals) > 1:
            flags.append(Finding(
                source="correlation", category="identity",
                fact_type="contradiction",
                value=f"Conflicting {fact_type}s: " + " vs ".join(sorted(vals)),
                snippet=(f"Multiple distinct {fact_type} values found across sources. "
                         "May indicate different people sharing a handle, or outdated "
                         "information. Review manually."),
                confidence=100,
            ))

    # -- 4. Verdict -------------------------------------------------------
    high = [f for f in findings
            if f.confidence >= HIGH_CONFIDENCE and f.fact_type != "coverage_note"]
    accounts = [f for f in profiles if f.confidence >= HIGH_CONFIDENCE]
    n_sites = len({f.metadata.get("site") or f.metadata.get("login") for f in accounts})

    if n_sites >= 3:
        strength = "STRONG"
        why = (f"{n_sites} high-confidence profiles share the identifier, "
               f"{len(links)} corroborated cross-links.")
    elif n_sites >= 1 or high:
        strength = "MODERATE"
        why = (f"{n_sites} high-confidence profile(s), "
               f"{len(high)} high-confidence findings total.")
    else:
        strength = "WEAK"
        why = "Little corroborated public footprint for this identifier."

    if flags:
        strength += " (with contradictions)"
    verdict = f"{strength}: {why}"
    return links, flags, verdict
