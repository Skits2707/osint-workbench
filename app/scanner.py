"""Scan orchestration: run collectors, store findings, correlate."""

from __future__ import annotations

import asyncio
import logging

import httpx

from .collectors import collectors_for
from .collectors.base import DEFAULT_HEADERS
from .correlation import correlate
from .db import Store
from .models import Finding

log = logging.getLogger("scanner")


async def run_investigation(store: Store, inv_id: int,
                            input_type: str, input_value: str):
    """Executed as a FastAPI background task."""
    collectors = collectors_for(input_type)
    all_findings: list[Finding] = []

    try:
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS,
                                     timeout=12) as client:
            results = await asyncio.gather(
                *(c.collect(input_type, input_value, client) for c in collectors),
                return_exceptions=True,
            )
        for collector, result in zip(collectors, results):
            if isinstance(result, Exception):
                log.warning("collector %s failed: %s", collector.name, result)
                all_findings.append(Finding(
                    source=collector.name, category="exposure",
                    fact_type="coverage_note",
                    value=f"{collector.name} collector failed: {result}",
                    confidence=100,
                ))
            else:
                all_findings.extend(result)

        store.add_findings(inv_id, all_findings)

        # Correlation works on findings with IDs assigned.
        links, flags, verdict = correlate(inv_id, all_findings, input_value)
        for f in all_findings:
            if f.id is not None:
                store.update_confidence(f.id, f.confidence)
        if flags:
            store.add_findings(inv_id, flags)
        if links:
            store.add_links(inv_id, links)

        store.set_status(inv_id, "done", verdict)
    except Exception as exc:  # never leave an investigation hanging
        log.exception("investigation %s failed", inv_id)
        store.set_status(inv_id, "error", str(exc))
