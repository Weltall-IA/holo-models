"""Portable JSON helpers for versioned benchmark artifacts."""
from __future__ import annotations

import os
import re
from typing import Any

_POSIX_ABSOLUTE_PATH = re.compile(r"(?<![:/>\w])/(?:[^\s\"'<>]+)")
_WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?<![\w])(?:[a-z]:[\\/])(?:[^\s\"'<>]+)"
)
_RELATIVE_API_ENDPOINT = re.compile(
    r"^/(?:[A-Za-z0-9._~!$&'()*+,;=:@%-]+/)*"
    r"[A-Za-z0-9._~!$&'()*+,;=:@%-]+/?$"
)
_API_ENDPOINT_FIELDS = frozenset({"endpoint", "endpoint_path", "api_endpoint"})


def _is_relative_api_endpoint(value: str, path: str) -> bool:
    """Return whether a string is an API route in an endpoint field.

    Relative API routes such as ``/rerank`` and ``/v1/rerank`` are portable
    protocol identifiers, not host filesystem paths. The exemption is
    deliberately contextual so the same string under ``path`` or another
    filesystem-oriented field remains subject to path redaction.
    """
    field = path.rsplit(".", 1)[-1]
    if field not in _API_ENDPOINT_FIELDS:
        return False
    if "\\" in value or value.startswith("//"):
        return False
    if any(segment == ".." for segment in value.split("/")):
        return False
    return _RELATIVE_API_ENDPOINT.fullmatch(value) is not None


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


def sanitize_host_payload(value: Any, path: str = "$") -> Any:
    """Recursively sanitize strings while preserving JSON-compatible structure."""
    if isinstance(value, dict):
        return {
            str(key): sanitize_host_payload(item, f"{path}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            sanitize_host_payload(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return [
            sanitize_host_payload(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        if _is_relative_api_endpoint(value, path):
            return value
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
        if _is_relative_api_endpoint(value, path):
            return findings
        sanitized = sanitize_host_text(value)
        if sanitized != value:
            findings.append({"path": path, "value": value})
    return findings


def assert_portable_payload(value: Any) -> None:
    findings = host_specific_strings(value)
    if findings:
        locations = ", ".join(item["path"] for item in findings[:5])
        raise ValueError(f"artifact contains host-specific strings at: {locations}")
