"""Logger Configuration"""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

_STANDARD_LOG_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter compatible with Go slog, Promtail, and Loki."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        # Format ISO8601 UTC timestamp (e.g. 2026-09-28T21:25:01.421900Z)
        timestamp = (
            datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )

        log_data = {
            "time": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.message,
        }

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            log_data["exception"] = record.exc_text
        elif record.exc_text:
            log_data["exception"] = record.exc_text

        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, default=str, ensure_ascii=False)


def setup_logger(log_level: int = logging.INFO) -> logging.Logger:
    """Configures structured JSON logging for both console (stdout) and file."""
    os.makedirs("logs", exist_ok=True)

    json_formatter = JSONFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)

    file_handler = RotatingFileHandler(
        "logs/charlotte.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(json_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on multiple calls
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy aiogram event logs
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    return logging.getLogger(__name__)

