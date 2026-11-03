"""Username enumeration across public profile pages.

Method: unauthenticated GET of the public profile URL. A profile is
reported only when the site clearly returns success for existing
profiles (curated in sites.py). Sites that soft-200 missing profiles
are given lower base confidence so the correlation engine can demand
corroboration before treating them as verified.
"""

from __future__ import annotations

import asyncio
import re

import httpx

from ..models import Finding
from .base import Collector
from .sites import SITES

# Marker strings that indicate a missing profile even on HTTP 200.
MISSING_MARKERS = re.compile(
    r"(page not found|user not found|profile not found|doesn.?t exist|"
    r"not available|no such user|account suspended|404)",
    re.IGNORECASE,
)


class UsernameCollector(Collector):
    name = "username-search"
    description = "Checks public profile pages across ~45 sites for a username"
    supported_inputs = ("username",)

    async def _check(self, site: dict, username: str,
                     client: httpx.AsyncClient) -> Finding | None:
        url = site["url"].replace("{u}", username)
        try:
            resp = await client.get(url, follow_redirects=True, timeout=10)
        except (httpx.HTTPError, asyncio.TimeoutError):
            return None

        exists = False
        if site.get("json"):
            # e.g. Reddit about.json: 200 JSON = exists, 404 = not
            exists = resp.status_code == 200 and "data" in resp.text[:2000]
        elif resp.status_code == 200:
            exists = not MISSING_MARKERS.search(resp.text[:20000])
        if not exists:
            return None

        return Finding(
            source=self.name,
            category="account",
            fact_type="profile",
            value=f"{site['name']}: {username}",
            url=str(resp.url),
            snippet=f"Public profile page for '{username}' returned HTTP 200 on {site['name']}.",
            confidence=site["confidence"],
            metadata={"site": site["name"], "username": username},
        )

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        username = value.strip().lstrip("@")
        # Bound concurrency so we are polite to remote hosts.
        sem = asyncio.Semaphore(8)

        async def guarded(site):
            async with sem:
                return await self._check(site, username, client)

        results = await asyncio.gather(*(guarded(s) for s in SITES))
        return [r for r in results if r is not None]
