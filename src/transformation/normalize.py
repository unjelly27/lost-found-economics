"""Convert DOT display values without altering counts or inferring missing data."""

import re
from decimal import Decimal

CARRIERS = {
    name.upper(): name for name in (
        "Alaska Airlines", "Allegiant Air", "American Airlines", "Delta Air Lines",
        "Envoy Air", "Frontier Airlines", "Hawaiian Airlines", "JetBlue Airways",
        "PSA Airlines", "Republic Airways", "SkyWest Airlines", "Southwest Airlines",
        "Spirit Airlines", "United Airlines",
    )
}
CARRIERS.update({"ALASKA AIRLINES1": "Alaska Airlines", "ALASKA AIRLINES2": "Alaska Airlines"})
INTEGER = re.compile(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)", re.ASCII)
RATE = re.compile(r"-?\d+\.\d{2}", re.ASCII)


def normalize_carrier(raw_name: str) -> str:
    key = " ".join(raw_name.split()).upper()
    if key not in CARRIERS:
        raise ValueError(f"unrecognized operating carrier {raw_name!r}")
    return CARRIERS[key]


def parse_count(raw: str) -> int:
    if not INTEGER.fullmatch(raw.strip()):
        raise ValueError(f"invalid or missing baggage count {raw!r}")
    value = int(raw.strip().replace(",", ""))
    if not -(2**63) <= value < 2**63:
        raise ValueError(f"baggage count outside SQLite integer range: {raw!r}")
    return value


def parse_rate(raw: str) -> Decimal:
    if not RATE.fullmatch(raw.strip()):
        raise ValueError(f"expected a two-decimal published rate, found {raw!r}")
    return Decimal(raw.strip())
