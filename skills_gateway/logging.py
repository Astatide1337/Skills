import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone


INSTANCE_ID = os.getenv("HOSTNAME", os.getenv("SKG_INSTANCE_ID", str(uuid.uuid4())[:8]))


class StructuredEvent:
    def __init__(self, event: str, message: str, **kwargs):
        self.event = event
        self.message = message
        self.fields = kwargs

    def to_dict(self, environment: str = "production", level: str = "INFO") -> dict:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "service": "skills-gateway",
            "event": self.event,
            "environment": environment,
            "instance_id": INSTANCE_ID,
            "message": self.message,
        }
        record.update(self.fields)
        return {k: v for k, v in record.items() if v is not None}


class JsonFormatter(logging.Formatter):
    def __init__(self, environment: str = "production"):
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, StructuredEvent):
            data = record.msg.to_dict(
                environment=self.environment,
                level=record.levelname,
            )
        else:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "service": "skills-gateway",
                "environment": self.environment,
                "instance_id": INSTANCE_ID,
                "message": record.getMessage(),
            }
        if record.exc_info and record.exc_info[1]:
            data["error"] = str(record.exc_info[1])
        return json.dumps(data, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self, environment: str = "production"):
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).isoformat()
        if isinstance(record.msg, StructuredEvent):
            data = record.msg.to_dict(
                environment=self.environment,
                level=record.levelname,
            )
            extra_parts = " ".join(f"{k}={v}" for k, v in data.items() if k not in ("timestamp", "level", "service", "message", "environment"))
            return f"{ts} {record.levelname} skills-gateway {record.msg.event} {record.msg.message} {extra_parts}"
        return f"{ts} {record.levelname} skills-gateway {record.getMessage()}"


def setup_logging(log_level: str = "INFO", log_format: str = "json", environment: str = "production") -> logging.Logger:
    logger = logging.getLogger("skills-gateway")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        handler.setFormatter(JsonFormatter(environment=environment))
    else:
        handler.setFormatter(TextFormatter(environment=environment))

    logger.addHandler(handler)
    return logger


def log_event(event: str, message: str, level: str = "INFO", **kwargs):
    logger = logging.getLogger("skills-gateway")
    evt = StructuredEvent(event, message, **kwargs)
    logger.log(getattr(logging, level.upper(), logging.INFO), evt)


def new_request_id() -> str:
    return str(uuid.uuid4())
