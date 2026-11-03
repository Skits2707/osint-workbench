"""Collector plugin interface.

Every source is a plugin: drop a new file in this package, subclass
Collector, and register it. The scanner runs all collectors that
support the given input type concurrently.
"""

from __future__ import annotations

import httpx

from ..models import Finding

# Shared async client settings: polite, timeout-bounded, honest UA.
DEFAULT_HEADERS = {
    "User-Agent": "OSINT-Workbench/0.1 (portfolio project; public data only)"
}


class Collector:
    name: str = "base"
    description: str = ""
    supported_inputs: tuple[str, ...] = ()  # "email" | "username" | "name"

    async def collect(self, input_type: str, value: str,
                      client: httpx.AsyncClient) -> list[Finding]:
        raise NotImplementedError

    def supports(self, input_type: str) -> bool:
        return input_type in self.supported_inputs
