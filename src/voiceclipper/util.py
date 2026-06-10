from __future__ import annotations

import hashlib
import re
from pathlib import Path

_SESSION_ID_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_session_id(value: str) -> str:
    cleaned = _SESSION_ID_RE.sub("_", value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "session"
