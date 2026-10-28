"""Content-derived URL for the shared, immutable analytics asset."""

import hashlib
import re
from pathlib import Path

ANALYTICS_FILE = Path(__file__).resolve().parent / "elh-preview/assets/analytics.js"


def analytics_url(content: bytes | None = None) -> str:
    if content is None:
        content = ANALYTICS_FILE.read_bytes()
    version = hashlib.sha256(content).hexdigest()[:12]
    return f"/assets/analytics.js?v={version}"


def refresh_html(document: str, content: bytes | None = None) -> str:
    """Refresh served asset URLs without rewriting approval-hashed articles."""
    current = analytics_url(content)
    return re.sub(
        r'(<script\b[^>]*\bsrc=["\'])(/assets/analytics\.js[^"\']*)(["\'])',
        lambda match: match[1] + current + match[3],
        document,
        flags=re.I,
    )
