import json
import logging

from skills_gateway.logging import (
    StructuredEvent,
    JsonFormatter,
    TextFormatter,
    setup_logging,
    log_event,
    INSTANCE_ID,
)


class TestStructuredEvent:
    def test_to_dict_required_fields(self):
        evt = StructuredEvent("service_start", "Starting up")
        d = evt.to_dict(environment="production", level="INFO")
        assert d["service"] == "skills-gateway"
        assert d["event"] == "service_start"
        assert d["message"] == "Starting up"
        assert d["level"] == "INFO"
        assert d["environment"] == "production"
        assert d["instance_id"] == INSTANCE_ID
        assert "timestamp" in d

    def test_to_dict_extra_fields(self):
        evt = StructuredEvent("skill_search", "Searching", query="react", request_id="abc")
        d = evt.to_dict(environment="development", level="DEBUG")
        assert d["query"] == "react"
        assert d["request_id"] == "abc"
        assert d["environment"] == "development"
        assert d["level"] == "DEBUG"

    def test_to_dict_none_fields_omitted(self):
        evt = StructuredEvent("test", "msg", error=None, duration_ms=None)
        d = evt.to_dict()
        assert "error" not in d
        assert "duration_ms" not in d


class TestJsonFormatter:
    def test_formats_structured_event_as_json(self):
        fmt = JsonFormatter(environment="production")
        evt = StructuredEvent("service_start", "Starting")
        record = logging.LogRecord("test", logging.INFO, "", 0, evt, (), None)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["service"] == "skills-gateway"
        assert data["event"] == "service_start"

    def test_formats_plain_string_as_json(self):
        fmt = JsonFormatter(environment="production")
        record = logging.LogRecord("test", logging.INFO, "", 0, "hello world", (), None)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["message"] == "hello world"
        assert data["service"] == "skills-gateway"


class TestTextFormatter:
    def test_formats_structured_event_as_text(self):
        fmt = TextFormatter(environment="development")
        evt = StructuredEvent("skill_search", "Searching", query="react")
        record = logging.LogRecord("test", logging.INFO, "", 0, evt, (), None)
        output = fmt.format(record)
        assert "skill_search" in output
        assert "Searching" in output
        assert "query=react" in output

    def test_formats_plain_string_as_text(self):
        fmt = TextFormatter(environment="development")
        record = logging.LogRecord("test", logging.INFO, "", 0, "plain message", (), None)
        output = fmt.format(record)
        assert "plain message" in output


class TestSetupLogging:
    def test_json_format(self):
        logger = setup_logging(log_format="json", environment="production")
        assert logger.handlers[0].formatter.__class__.__name__ == "JsonFormatter"

    def test_text_format(self):
        logger = setup_logging(log_format="text", environment="development")
        assert logger.handlers[0].formatter.__class__.__name__ == "TextFormatter"


class TestLogEvent:
    def test_log_event_creates_structured_output(self, caplog):
        setup_logging(log_format="json", environment="production")
        with caplog.at_level(logging.INFO, logger="skills-gateway"):
            log_event("skill_list", "Listing skills", skills_count=5)
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert isinstance(record.msg, StructuredEvent)
        assert record.msg.event == "skill_list"
