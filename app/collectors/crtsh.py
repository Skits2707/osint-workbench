"""Certificate Transparency log search via crt.sh.

Every TLS certificate ever issued for a domain is published to public
CT logs — a goldmine for discovering subdomains and infrastructure
history. Completely public data, no authentication.
"""

from __future__ import annotations

import httpx

from ..models import Finding
from .base import Collector


class CrtShCollector(Collector):
    name = "crt.sh"
    description = "Subdomains and certificate history from public CT logs"
    supported_inputs = ("domain",)

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        domain = value.strip().lower().removeprefix("*.")
        try:
            resp = await client.get(
                "https://crt.sh/",
                params={"q": f"%.{domain}", "output": "json"},
                timeout=25,
            )
        except httpx.HTTPError as exc:
            return [Finding(
                source=self.name, category="infrastructure",
                fact_type="coverage_note",
                value=f"crt.sh unreachable: {exc}",
                snippet="CT logs could not be queried from this network. "
                        "Reported so coverage is explicit rather than silent.",
                confidence=100,
            )]
        if resp.status_code != 200:
            return []
        try:
            certs = resp.json()
        except ValueError:
            return []
        if not certs:
            return []

        subdomains: dict[str, str] = {}  # name -> earliest not_before
        for cert in certs:
            for name in cert.get("name_value", "").split("\n"):
                name = name.strip().lower()
                if name and "*" not in name:
                    earlier = subdomains.get(name)
                    nb = cert.get("not_before", "")
                    if earlier is None or (nb and nb < earlier):
                        subdomains[name] = nb

        findings = [Finding(
            source=self.name, category="infrastructure", fact_type="ct_summary",
            value=f"{len(certs)} certificates, {len(subdomains)} unique hostnames",
            url=f"https://crt.sh/?q=%25.{domain}",
            snippet="Certificate Transparency logs (public record of all TLS certs).",
            confidence=90,
            metadata={"cert_count": len(certs),
                      "hostname_count": len(subdomains)},
        )]
        # Cap individual subdomain findings so huge domains stay readable.
        for name, first_seen in sorted(subdomains.items())[:75]:
            findings.append(Finding(
                source=self.name, category="infrastructure", fact_type="subdomain",
                value=name,
                url=f"https://crt.sh/?q={name}",
                snippet=f"In CT logs since {first_seen[:10] or 'unknown'}.",
                confidence=85,
                metadata={"first_seen": first_seen},
            ))
        if len(subdomains) > 75:
            findings.append(Finding(
                source=self.name, category="infrastructure",
                fact_type="coverage_note",
                value=f"{len(subdomains) - 75} more hostnames on crt.sh (link above)",
                confidence=100,
            ))
        return findings
