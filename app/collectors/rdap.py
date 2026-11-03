"""RDAP domain registration lookup.

RDAP is the modern, structured successor to WHOIS — official registry
data served over HTTPS. Gives registrar, creation/expiry dates, status
and nameservers without any scraping. rdap.org bootstraps to the
correct registry for any TLD.
"""

from __future__ import annotations

import httpx

from ..models import Finding
from .base import Collector


class RdapCollector(Collector):
    name = "rdap"
    description = "Official domain registration data (registry record)"
    supported_inputs = ("domain",)

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        domain = value.strip().lower()
        try:
            resp = await client.get(f"https://rdap.org/domain/{domain}",
                                    follow_redirects=True, timeout=15)
        except httpx.HTTPError as exc:
            return [Finding(
                source=self.name, category="infrastructure",
                fact_type="coverage_note",
                value=f"RDAP registry unreachable: {exc}",
                snippet="Registry lookup failed from this network. Reported so "
                        "coverage is explicit rather than silent.",
                confidence=100,
            )]
        if resp.status_code == 404:
            return [Finding(
                source=self.name, category="infrastructure",
                fact_type="registration",
                value=f"{domain} is not registered (available)",
                url=str(resp.url), confidence=95,
            )]
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except ValueError:
            return []

        findings: list[Finding] = []
        events = {e.get("eventAction"): e.get("eventDate", "")
                  for e in data.get("events", [])}

        if created := events.get("registration"):
            findings.append(Finding(
                source=self.name, category="infrastructure",
                fact_type="registered",
                value=f"Registered {created[:10]}",
                url=str(resp.url),
                snippet="Domain registration date from official registry (RDAP). "
                        "Very recent registration is a classic risk signal.",
                confidence=95,
                metadata={"created": created},
            ))
        if expires := events.get("expiration"):
            findings.append(Finding(
                source=self.name, category="infrastructure",
                fact_type="expires",
                value=f"Expires {expires[:10]}",
                url=str(resp.url), confidence=90,
            ))

        # Registrar name
        for ent in data.get("entities", []):
            if "registrar" in ent.get("roles", []):
                vcard = ent.get("vcardArray", [None, []])[1]
                name = next((v[3] for v in vcard if v[0] == "fn"), None)
                if name:
                    findings.append(Finding(
                        source=self.name, category="infrastructure",
                        fact_type="registrar", value=name,
                        url=str(resp.url), confidence=95,
                    ))
                break

        nameservers = [ns.get("ldhName") for ns in data.get("nameservers", [])
                       if ns.get("ldhName")]
        if nameservers:
            findings.append(Finding(
                source=self.name, category="infrastructure",
                fact_type="nameservers",
                value=", ".join(nameservers[:4]),
                url=str(resp.url),
                snippet="Nameservers often reveal the hosting provider.",
                confidence=90,
                metadata={"nameservers": nameservers},
            ))
        return findings
