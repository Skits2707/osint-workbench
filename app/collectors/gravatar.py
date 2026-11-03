"""Gravatar lookup by email hash.

Gravatar exposes a public JSON profile endpoint keyed by the MD5 of a
lowercased, stripped email address. Profiles often contain display
name, location, and a list of *verified* linked accounts — which makes
Gravatar hits unusually strong correlation material.
"""

from __future__ import annotations

import hashlib

import httpx

from ..models import Finding
from .base import Collector


class GravatarCollector(Collector):
    name = "gravatar"
    description = "Public Gravatar profile for an email address"
    supported_inputs = ("email",)

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        email = value.strip().lower()
        digest = hashlib.md5(email.encode()).hexdigest()  # noqa: S324 - required by Gravatar API
        url = f"https://www.gravatar.com/{digest}.json"
        try:
            resp = await client.get(url, timeout=10)
        except httpx.HTTPError:
            return []
        if resp.status_code != 200:
            return []

        try:
            profile = resp.json()["entry"][0]
        except (ValueError, KeyError, IndexError):
            return []

        findings: list[Finding] = []
        profile_url = profile.get("profileUrl", url)

        findings.append(Finding(
            source=self.name, category="identity", fact_type="gravatar_profile",
            value=f"Gravatar profile exists for {email}",
            url=profile_url,
            snippet="Gravatar profile found via public hash lookup.",
            confidence=85,
            metadata={"hash": digest},
        ))
        if name := profile.get("displayName"):
            findings.append(Finding(
                source=self.name, category="identity", fact_type="name",
                value=name, url=profile_url,
                snippet="displayName on public Gravatar profile.",
                confidence=80,
            ))
        if loc := profile.get("currentLocation"):
            findings.append(Finding(
                source=self.name, category="identity", fact_type="location",
                value=loc, url=profile_url,
                snippet="currentLocation on public Gravatar profile.",
                confidence=70,
            ))
        # Verified linked accounts — gold for correlation.
        for acct in profile.get("accounts", []):
            findings.append(Finding(
                source=self.name, category="account", fact_type="linked_account",
                value=f"{acct.get('name', 'account')}: {acct.get('display', '')}",
                url=acct.get("url", profile_url),
                snippet="Verified account link on Gravatar profile (owner-confirmed).",
                confidence=90,
                metadata={"platform": acct.get("name"), "shortname": acct.get("shortname")},
            ))
        return findings
