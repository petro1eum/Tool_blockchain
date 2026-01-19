"""Structured JSON logging for TrustChain.

Usage:
    from trustchain.v2.logging import setup_logging

    setup_logging(level="INFO", json_format=True)

    import logging
    logger = logging.getLogger("trustchain")
    logger.info("sign", extra={"tool_id": "api", "status": "success"})
"""

import json
import logging
import sys


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging (ELK/Splunk compatible)."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "ts": record.created,
            "level": record.levelname,
            "msg": record.getMessage(),
        }

        # Add extra fields (passed via extra={...})
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "taskName",
            ):
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def setup_logging(
    level: str = "INFO", json_format: bool = True, logger_name: str = "trustchain"
) -> logging.Logger:
    """Configure structured logging.

    Args:
        level: DEBUG, INFO, WARNING, ERROR
        json_format: True for JSON, False for standard format
        logger_name: Logger name
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger(name: str = "trustchain") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
