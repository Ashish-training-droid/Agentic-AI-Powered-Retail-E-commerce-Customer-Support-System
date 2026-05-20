"""
Logging utilities for the ShopEase support system.

Provides structured logging with agent context, timestamps, and
severity levels. Logs are written to both console and file.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone


LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create a named logger with console and file handlers.

    Args:
        name: Logger name (typically module or agent name)
        level: Logging level (default INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"shopease.{name}")

    if logger.handlers:
        return logger

    logger.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_DIR / "system.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


def log_agent_step(
    logger: logging.Logger,
    agent_name: str,
    action: str,
    details: str = "",
    level: int = logging.INFO,
):
    """
    Log a structured agent pipeline step.

    Args:
        logger: Logger instance
        agent_name: Name of the agent performing the action
        action: What the agent did
        details: Additional context
        level: Log level
    """
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    msg = f"[{agent_name}] {action}"
    if details:
        msg += f" | {details}"
    logger.log(level, msg)
