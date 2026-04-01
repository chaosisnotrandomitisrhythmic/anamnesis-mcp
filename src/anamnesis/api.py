"""Shared Anthropic API client for anamnesis scripts."""

import json
import logging
import os
import re
import urllib.request
from pathlib import Path

from .paths import MODEL

log = logging.getLogger(__name__)


def get_api_key() -> str:
    """Get Anthropic API key from env or shell rc files.

    Checks ANTHROPIC_API_KEY env var first, then parses shell rc files
    as a fallback (for cron environments that don't source the shell).
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    for rc in (".zshrc", ".bashrc", ".bash_profile", ".profile"):
        rc_path = Path.home() / rc
        if rc_path.exists():
            for line in rc_path.read_text().splitlines():
                m = re.search(r'ANTHROPIC_API_KEY=["\']?([^"\'\s]+)', line)
                if m:
                    return m.group(1)
    return ""


def call_api(system: str, user_content: str) -> str:
    """Call Anthropic Messages API with adaptive thinking."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No ANTHROPIC_API_KEY found. Set it in env or ensure it's exported in ~/.zshrc"
        )

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 16000,
        "thinking": {"type": "adaptive"},
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())

    texts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            texts.append(block["text"])

    usage = data.get("usage", {})
    log.info(
        "API call: input=%s output=%s",
        usage.get("input_tokens", "?"),
        usage.get("output_tokens", "?"),
    )
    return "\n".join(texts)
