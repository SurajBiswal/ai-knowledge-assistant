"""Remove exact runtime credentials from untrusted MCP tool results.

MCP servers are outside the application's trust boundary. A malicious or
misconfigured server could repeat an Authorization header or API key in text
or structured output. The runtime calls this module before returning a result
to an adapter, registry, agent, or future API layer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import logging
from typing import Any


REDACTED_SECRET = "[REDACTED]"
SDK_LOGGER_NAMES = ("mcp", "httpx", "httpx2", "httpcore")


class KnownSecretLogFilter(logging.Filter):
    """Redact active MCP secrets before SDK records reach log handlers."""

    def __init__(self, secrets: Sequence[str]) -> None:
        """Copy secrets so later clearing runtime headers cannot expose logs."""
        super().__init__()
        self._secrets = tuple(item for item in secrets if item)

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize message arguments and omit secret-bearing tracebacks."""
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg, self._secrets)
        record.args = redact_json_value(record.args, self._secrets)
        if record.exc_info is not None:
            record.exc_info = None
            record.exc_text = None
        return True

    def clear(self) -> None:
        """Drop the filter's credential copies after the owner task ends."""
        self._secrets = ()


def install_sdk_secret_log_filter(
    secrets: Sequence[str],
) -> tuple[KnownSecretLogFilter, list[logging.Filterer]]:
    """Attach one filter to known SDK loggers and current root handlers."""
    secret_filter = KnownSecretLogFilter(secrets)
    targets: list[logging.Filterer] = [
        logging.getLogger(name) for name in SDK_LOGGER_NAMES
    ]
    targets.extend(logging.getLogger().handlers)
    for target in targets:
        target.addFilter(secret_filter)
    return secret_filter, targets


def remove_sdk_secret_log_filter(
    installed: tuple[KnownSecretLogFilter, list[logging.Filterer]],
) -> None:
    """Detach and clear one connection's filter after cleanup completes."""
    secret_filter, targets = installed
    for target in targets:
        target.removeFilter(secret_filter)
    secret_filter.clear()


def redact_text(value: str, secrets: Sequence[str]) -> str:
    """Replace every exact known secret while leaving ordinary text intact."""
    redacted = value
    for secret in sorted(
        {item for item in secrets if item},
        key=len,
        reverse=True,
    ):
        redacted = redacted.replace(secret, REDACTED_SECRET)
    return redacted


def redact_json_value(value: Any, secrets: Sequence[str]) -> Any:
    """Recursively redact strings in JSON-like structured tool content."""
    if isinstance(value, str):
        return redact_text(value, secrets)
    if isinstance(value, Mapping):
        return {
            (
                redact_text(key, secrets)
                if isinstance(key, str)
                else key
            ): redact_json_value(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_json_value(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_json_value(item, secrets) for item in value)
    return value


def redact_mcp_tool_result(result: Any, secrets: Sequence[str]) -> Any:
    """Return a copied MCP result with text and structured secrets removed."""
    if not secrets:
        return result

    structured = getattr(result, "structured_content", None)
    redacted_structured = redact_json_value(structured, secrets)

    redacted_blocks: list[Any] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if not isinstance(text, str):
            redacted_blocks.append(block)
            continue
        update = {"text": redact_text(text, secrets)}
        model_copy = getattr(block, "model_copy", None)
        if callable(model_copy):
            redacted_blocks.append(model_copy(update=update, deep=True))
            continue
        copied_block = deepcopy(block)
        setattr(copied_block, "text", update["text"])
        redacted_blocks.append(copied_block)

    updates = {
        "content": redacted_blocks,
        "structured_content": redacted_structured,
    }
    model_copy = getattr(result, "model_copy", None)
    if callable(model_copy):
        return model_copy(update=updates, deep=True)
    copied_result = deepcopy(result)
    for name, value in updates.items():
        if hasattr(copied_result, name):
            setattr(copied_result, name, value)
    return copied_result
