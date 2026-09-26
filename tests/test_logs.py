import io
import json
import re
from datetime import datetime, timedelta, timezone

from vision_inspection.logs import Logger, iso_ms

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def test_iso_ms_truncates():
    assert iso_ms(datetime(2026, 9, 25, 5, 20, 13, 999999, tzinfo=timezone.utc)) == "2026-09-25T05:20:13.999Z"
    assert iso_ms(datetime(2026, 9, 25, 5, 20, 13, 0, tzinfo=timezone.utc)) == "2026-09-25T05:20:13.000Z"
    assert iso_ms(datetime(2026, 9, 25, 5, 20, 13, 425700, tzinfo=timezone.utc)) == "2026-09-25T05:20:13.425Z"
    kst = timezone(timedelta(hours=9))
    assert iso_ms(datetime(2026, 9, 25, 14, 20, 13, 1999, tzinfo=kst)) == "2026-09-25T05:20:13.001Z"


def test_record_is_one_json_line_with_leading_keys():
    out = io.StringIO()
    log = Logger("INFO", stream=out)
    log.emit("INFO", "received", topic="factory/product/created", bytes=118)
    log.emit("ERROR", "dropped", reason="ground_truth_missing", detail="no complete line\nfor P-1", product_id="P-00000114")
    text = out.getvalue()
    lines = text.split("\n")
    assert lines[-1] == "" and len(lines) == 3
    first, second = (json.loads(l) for l in lines[:2])
    assert list(first) == ["ts", "level", "event", "topic", "bytes"]
    assert first["level"] == "INFO" and first["event"] == "received" and first["bytes"] == 118
    assert TS_RE.match(first["ts"])
    assert list(second) == ["ts", "level", "event", "reason", "detail", "product_id"]
    assert second["detail"] == "no complete line\nfor P-1"
    assert " " not in lines[0].replace("factory/product/created", "")  # compact separators


def test_level_filter():
    out = io.StringIO()
    log = Logger("warning", stream=out)
    log.emit("INFO", "received", topic="t", bytes=1)
    log.emit("WARNING", "connect_failed", reason="connect_failed", detail="x")
    log.emit("ERROR", "error", reason="internal_error", detail="y")
    events = [json.loads(l)["event"] for l in out.getvalue().splitlines()]
    assert events == ["connect_failed", "error"]

    out = io.StringIO()
    Logger("DEBUG", stream=out).emit("INFO", "connected")
    assert json.loads(out.getvalue())["event"] == "connected"


def test_non_ascii_kept():
    out = io.StringIO()
    Logger("INFO", stream=out).emit("ERROR", "dropped", reason="invalid_json", detail="잘못된 JSON — ü")
    line = out.getvalue()
    assert "잘못된 JSON — ü" in line
    assert "\\u" not in line
    assert json.loads(line)["detail"] == "잘못된 JSON — ü"


def test_flush_each_record():
    class Counting(io.StringIO):
        flushes = 0

        def flush(self):
            self.flushes += 1
            super().flush()

    out = Counting()
    log = Logger("INFO", stream=out)
    log.emit("INFO", "connected")
    log.emit("INFO", "stopped", signal="SIGTERM")
    assert out.flushes == 2
