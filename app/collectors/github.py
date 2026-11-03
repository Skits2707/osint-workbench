"""GitHub public API lookup.

Uses only the official, unauthenticated REST endpoints (rate limit
60 req/hr, plenty for an investigation). Works for usernames and for
email addresses via the public commit-author search.
"""

from __future__ import annotations

import httpx

from ..models import Finding
from .base import Collector

API = "https://api.github.com"


class GitHubCollector(Collector):
    name = "github"
    description = "GitHub public profile and activity"
    supported_inputs = ("username", "email")

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        username = value.strip().lstrip("@")
        if input_type == "email":
            username = await self._username_from_email(value.strip(), client)
            if not username:
                return []
        return await self._profile_findings(username, client)

    async def _username_from_email(self, email: str,
                                   client: httpx.AsyncClient) -> str | None:
        # Public commit search by author email (no auth needed for low volume).
        try:
            resp = await client.get(
                f"{API}/search/commits",
                params={"q": f"author-email:{email}", "per_page": 1},
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items and items[0].get("author"):
                    return items[0]["author"]["login"]
        except (httpx.HTTPError, ValueError, KeyError):
            pass
        return None

    async def _profile_findings(self, username: str,
                                client: httpx.AsyncClient) -> list[Finding]:
        try:
            resp = await client.get(f"{API}/users/{username}", timeout=10)
        except httpx.HTTPError:
            return []
        if resp.status_code != 200:
            return []
        p = resp.json()
        url = p.get("html_url", f"https://github.com/{username}")

        findings = [Finding(
            source=self.name, category="account", fact_type="profile",
            value=f"GitHub: {p.get('login')}",
            url=url,
            snippet=(f"Public GitHub profile. {p.get('public_repos', 0)} public repos, "
                     f"created {str(p.get('created_at', ''))[:10]}."),
            confidence=90,
            metadata={
                "login": p.get("login"),
                "repos": p.get("public_repos"),
                "followers": p.get("followers"),
                "created_at": p.get("created_at"),
                "avatar": p.get("avatar_url"),
            },
        )]
        # Optional profile fields — each becomes its own sourced finding.
        field_map = [
            ("name", "name", "identity", 85),
            ("company", "employer", "identity", 75),
            ("location", "location", "identity", 75),
            ("blog", "website", "infrastructure", 75),
            ("twitter_username", "twitter", "account", 85),
            ("email", "email", "identity", 85),
        ]
        for key, fact, cat, conf in field_map:
            if val := p.get(key):
                findings.append(Finding(
                    source=self.name, category=cat, fact_type=fact,
                    value=str(val).lstrip("@") if key == "twitter_username" else str(val),
                    url=url,
                    snippet=f"'{key}' field on public GitHub profile.",
                    confidence=conf,
                ))
        return findings
