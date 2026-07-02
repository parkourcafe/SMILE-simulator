"""B2C pack catalog (CLAUDE.md → Key Business Decisions: B2C pricing).

Free tier (1 watermarked generation) is tracked on the user row, not as a pack.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackDef:
    pack_type: str
    generations_total: int
    price_rub: float
    price_uzs: float
    title: str


PACKS: dict[str, PackDef] = {
    "mini": PackDef("mini", 5, 149.0, 15000.0, "Mini — 5 generations"),
    "main": PackDef("main", 20, 499.0, 50000.0, "Main — 20 generations + 3 styles"),
    "extended": PackDef("extended", 50, 899.0, 90000.0, "Extended — 50 generations + all styles"),
}


def price_for(pack_type: str, currency: str) -> tuple[float, str]:
    pack = PACKS[pack_type]
    if currency.upper() == "UZS":
        return pack.price_uzs, "UZS"
    return pack.price_rub, "RUB"
