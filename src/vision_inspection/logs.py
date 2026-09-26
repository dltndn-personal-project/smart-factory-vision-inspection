"""stdout 한 줄 JSON 로그 (docs/spec/02-service.md 4절)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, TextIO

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


def iso_ms(dt: datetime) -> str:
    """UTC ISO 8601, 밀리초 3자리(버림), Z 접미사 (CONVENTIONS Timestamp)."""
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class Logger:
    """한 줄에 JSON 객체 하나. 공통 키 ts·level·event가 맨 앞이고 나머지는 넘긴 순서다."""

    def __init__(self, level: str, stream: TextIO | None = None) -> None:
        level = level.upper()
        if level not in _LEVELS:
            raise ValueError(f"unknown log level: {level}")
        self._threshold = _LEVELS[level]
        self._stream = stream if stream is not None else sys.stdout

    def emit(self, level: str, event: str, **fields: Any) -> None:
        if _LEVELS[level] < self._threshold:
            return
        record: dict[str, Any] = {"ts": iso_ms(datetime.now(timezone.utc)), "level": level, "event": event}
        for key, value in fields.items():
            if key not in record:
                record[key] = value
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        self._stream.write(line + "\n")
        self._stream.flush()
