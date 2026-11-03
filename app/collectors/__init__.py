"""Collector registry. New collectors register themselves here."""

from .base import Collector
from .breaches import BreachCollector
from .crtsh import CrtShCollector
from .github import GitHubCollector
from .gravatar import GravatarCollector
from .rdap import RdapCollector
from .username import UsernameCollector
from .wayback import WaybackCollector

REGISTRY: list[Collector] = [
    UsernameCollector(),
    GitHubCollector(),
    GravatarCollector(),
    BreachCollector(),
    CrtShCollector(),
    WaybackCollector(),
    RdapCollector(),
]


def collectors_for(input_type: str) -> list[Collector]:
    return [c for c in REGISTRY if c.supports(input_type)]
