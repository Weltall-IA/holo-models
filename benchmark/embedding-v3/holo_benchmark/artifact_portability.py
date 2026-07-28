"""Portable JSON helpers for versioned benchmark artifacts."""
from __future__ import annotations

import os
import re
from typing import Any

_POSIX_ABSOLUTE_PATH = re.compile(r"(?<![:/>\w])/(?:[^\s\"'<>]+)")
_WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?<![\w])(?:[a-z]:[\\/])(?:[^\s\"'<>]+)"
)


def sanitize_host_text(text: str) -> str:
    """Redact absolute filesystem paths and isolated local usernames."""
    cleaned = _WINDOWS_ABSOLUTE_PATH.sub("<path>", str(text))
    cleaned = _POSIX_ABSOLUTE_PATH.sub("<path>", cleaned)
    for name in (os.environ.get("USER", ""), os.environ.get("LOGNAME", "")):
        if not name:
            continue
        cleaned = re.sub(
            rf"(?<![\w.-]){re.escape(name)}(?![\w.-])",
            "<user>",
            cleaned,
        )
    return cleaned


def sanitize_host_payload(value: Any) -> Any:
    """Recursively sanitize strings while preserving JSON-compatible structure."""
    if isinstance(value, dict):
        return {str(key): sanitize_host_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_host_payload(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_host_payload(item) for item in value]
    if isinstance(value, str):
        return sanitize_host_text(value)
    return value


def host_specific_strings(value: Any, path: str = "$") -> list[dict[str, str]]:
    """Return string locations that would change under sanitization."""
    findings: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            findings.extend(host_specific_strings(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(host_specific_strings(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        sanitized = sanitize_host_text(value)
        if sanitized != value:
            findings.append({"path": path, "value": value})
    return findings


def assert_portable_payload(value: Any) -> None:
    findings = host_specific_strings(value)
    if findings:
        locations = ", ".join(item["path"] for item in findings[:5])
        raise ValueError(f"artifact contains host-specific strings at: {locations}")
