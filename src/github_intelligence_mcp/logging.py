"""Application logging setup.

All application log output goes to **stderr**: stdout carries the MCP JSON-RPC
protocol when the server runs over the stdio transport, so writing logs to
stdout would corrupt the protocol stream.

Secrets (tokens, authorization headers) must never be passed to log calls.
"""

from __future__ import annotations

import logging
import sys

_APP_LOGGER_NAMESPACE = "github_intelligence_mcp"
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: str) -> None:
    """Configure application logging once, targeting stderr.

    Safe to call multiple times; subsequent calls only refresh the level.
    """
    logger = logging.getLogger(_APP_LOGGER_NAMESPACE)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
        # Third-party HTTP chatter is noise at INFO; keep it to warnings.
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    logger.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the application namespace."""
    return logging.getLogger(f"{_APP_LOGGER_NAMESPACE}.{name}")
