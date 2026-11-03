"""Wayback Machine (Internet Archive) history for a domain or URL.

Tells you how long a site has existed publicly and how heavily it has
been archived — useful for establishing whether a domain is established
or freshly created (a classic scam-signal check). Public API, no auth.
"""

from __future__ import annotations

import httpx

from ..models import Finding
from .base import Collector

CDX = "https://web.archive.org/cdx/search/cdx"


class WaybackCollector(Collector):
    name = "wayback"
    description = "Internet Archive snapshot history"
    supported_inputs = ("domain",)

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        domain = value.strip().lower()
        try:
            first = await client.get(CDX, params={
                "url": domain, "output": "json", "limit": 1,
                "filter": "statuscode:200",
            }, timeout=20)
            last = await client.get(CDX, params={
                "url": domain, "output": "json", "limit": -1,
                "filter": "statuscode:200",
            }, timeout=20)
            count = await client.get(CDX, params={
                "url": domain, "output": "json", "showNumPages": "true",
            }, timeout=20)
        except httpx.HTTPError as exc:
            return [Finding(
                source=self.name, category="infrastructure",
                fact_type="coverage_note",
                value=f"Wayback Machine unreachable: {exc}",
                snippet="The archive could not be queried from this network. "
                        "Reported so coverage is explicit rather than silent.",
                confidence=100,
            )]

        def row(resp):
            try:
                data = resp.json()
                return data[1] if len(data) > 1 else None
            except (ValueError, IndexError):
                return None

        first_row, last_row = row(first), row(last)
        if not first_row:
            return [Finding(
                source=self.name, category="infrastructure",
                fact_type="archive_status",
                value="No Wayback Machine captures — site has no public archive history",
                url=f"https://web.archive.org/web/*/{domain}",
                snippet="Fresh or never-indexed domain. For a supposedly established "
                        "entity, no history is itself a signal worth noting.",
                confidence=80,
            )]

        # CDX row format: [urlkey, timestamp, original, mimetype, statuscode, digest, length]
        first_ts, last_ts = first_row[1], last_row[1] if last_row else first_row[1]
        fmt = lambda ts: f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"  # noqa: E731

        findings = [Finding(
            source=self.name, category="infrastructure", fact_type="archive_history",
            value=f"Publicly archived since {fmt(first_ts)} (latest: {fmt(last_ts)})",
            url=f"https://web.archive.org/web/{last_ts}/{domain}",
            snippet="Internet Archive CDX index — public crawl history.",
            confidence=90,
            metadata={"first_capture": first_ts, "last_capture": last_ts},
        )]
        # Oldest snapshot link — what did this site used to be?
        findings.append(Finding(
            source=self.name, category="infrastructure", fact_type="archive_oldest",
            value=f"Oldest capture: view site as of {fmt(first_ts)}",
            url=f"https://web.archive.org/web/{first_ts}/{domain}",
            snippet="Historical content can reveal previous owners or purposes.",
            confidence=85,
        ))
        return findings
