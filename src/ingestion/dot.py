"""Download official PDFs and reuse verified, content-addressed source files."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import requests

from src.common import Source, atomic_write, is_dot_url, sha256, utc_now, write_json


def acquire(
    source: Source, bronze: Path, session: requests.Session, refresh: bool, offline: bool
) -> tuple[dict, str]:
    cache = bronze / f"{source.period}.json"
    current = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    checksum = current.get("sha256")
    cached_path = bronze / f"{source.period}-{checksum}.pdf"
    verified = (
        current.get("pdf_url") == source.pdf_url
        and cached_path.is_file()
        and sha256(cached_path) == checksum
    )
    metadata = asdict(source)
    if verified and not refresh:
        return {**current, **metadata}, "cache_hit"
    if offline:
        raise ValueError("No checksum-verified PDF in the local Bronze cache")

    headers = {}
    if verified:
        if current.get("etag"):
            headers["If-None-Match"] = current["etag"]
        if current.get("http_last_modified"):
            headers["If-Modified-Since"] = current["http_last_modified"]
    with session.get(source.pdf_url, headers=headers, timeout=(10, 60)) as response:
        if not is_dot_url(response.url):
            raise ValueError("PDF request redirected outside the official DOT domain")
        if response.status_code == 304 and verified:
            return {**current, **metadata}, "not_modified"
        response.raise_for_status()
        content = response.content
        if not content.startswith(b"%PDF-"):
            raise ValueError("Response did not contain PDF bytes")
        checksum = hashlib.sha256(content).hexdigest()
        local_name = f"{source.period}-{checksum}.pdf"
        pdf_path = bronze / local_name
        if not pdf_path.is_file() or sha256(pdf_path) != checksum:
            atomic_write(pdf_path, content)
        same_bytes = verified and current["sha256"] == checksum
        record = {
            **metadata,
            "sha256": checksum,
            "byte_count": len(content),
            "local_name": local_name,
            "downloaded_at": current["downloaded_at"] if same_bytes else utc_now(),
            "etag": response.headers.get("ETag"),
            "http_last_modified": response.headers.get("Last-Modified"),
        }
        write_json(cache, record)
        return record, "unchanged" if same_bytes else "downloaded"
