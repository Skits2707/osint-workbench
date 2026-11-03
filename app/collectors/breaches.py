"""Breach exposure check.

Two modes:
1. HaveIBeenPwned official API (requires a paid API key set via the
   HIBP_API_KEY environment variable) — proper, ToS-compliant route.
2. Without a key, reports that the check was skipped so the report is
   honest about coverage rather than silently omitting it.

Deliberately does NOT use unofficial breach mirrors or paste dumps —
only the sanctioned API.
"""

from __future__ import annotations

import os

import httpx

from ..models import Finding
from .base import Collector


class BreachCollector(Collector):
    name = "breaches"
    description = "Known data-breach exposure for an email (HIBP official API)"
    supported_inputs = ("email",)

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        email = value.strip().lower()
        key = os.environ.get("HIBP_API_KEY", "").strip()
        if not key:
            return [Finding(
                source=self.name, category="exposure", fact_type="coverage_note",
                value="Breach check skipped — set HIBP_API_KEY to enable",
                snippet="HaveIBeenPwned requires a paid API key. This note keeps "
                        "the report honest about what was and wasn't checked.",
                confidence=100,
            )]
        try:
            resp = await client.get(
                "https://haveibeenpwned.com/api/v3/breachedaccount/"
                + email + "?truncateResponse=false",
                headers={"hibp-api-key": key, "User-Agent": "OSINT-Workbench"},
                timeout=15,
            )
        except httpx.HTTPError:
            return []
        if resp.status_code == 404:
            return [Finding(
                source=self.name, category="exposure", fact_type="breach_status",
                value="No known breaches for this email",
                url="https://haveibeenpwned.com/",
                snippet="HIBP API returned 404 (no breaches found).",
                confidence=90,
            )]
        if resp.status_code != 200:
            return []

        findings = []
        for breach in resp.json():
            findings.append(Finding(
                source=self.name, category="exposure", fact_type="breach",
                value=f"{breach.get('Title')} ({str(breach.get('BreachDate', ''))[:7]})",
                url="https://haveibeenpwned.com/",
                snippet=(f"Email appeared in the {breach.get('Title')} breach; "
                         f"data classes: {', '.join(breach.get('DataClasses', [])[:6])}."),
                confidence=95,
                metadata={"breach": breach.get("Name"),
                          "date": breach.get("BreachDate"),
                          "data_classes": breach.get("DataClasses", [])},
            ))
        return findings
