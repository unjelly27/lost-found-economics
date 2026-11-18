"""Shared paths, source metadata and file handling."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TARGET_PERIODS = tuple(f"{year}-{month:02}" for year in (2025, 2026) for month in range(1, 9))


@dataclass(frozen=True)
class Source:
    period: str
    title: str
    report_url: str
    pdf_url: str
    edition_month: str
    publication_date: str | None
    landing_last_updated: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_dot_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.netloc in {
        "www.transportation.gov", "transportation.gov"
    }


def read_sources(path: Path) -> list[Source]:
    sources = [Source(**entry) for entry in json.loads(path.read_text(encoding="utf-8"))]
    periods = [source.period for source in sources]
    if sorted(periods) != list(TARGET_PERIODS):
        raise ValueError("Source catalog must contain one entry per target reporting month")
    if any(not is_dot_url(url) for source in sources for url in (source.report_url, source.pdf_url)):
        raise ValueError("All catalog URLs must use the official DOT HTTPS domain")
    return sorted(sources, key=lambda source: source.period)


def atomic_write(path: Path, content: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary_path = Path(stream.name)
    try:
        temporary_path.write_bytes(content)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_json(path: Path, payload: object) -> None:
    atomic_write(path, (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
