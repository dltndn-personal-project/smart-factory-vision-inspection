"""진입점의 설정 오류 종료 (docs/spec/04-verification.md 3.1절 test_main, 02-service.md 6절, C-05 일부)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def test_invalid_config_exits_2(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MQTT_", "IMAGE_ROOT", "LOG_LEVEL", "HEALTH_FILE"))}
    env.update(
        PYTHONPATH=str(SRC),
        MQTT_URL="http://h",
        IMAGE_ROOT=str(tmp_path),
        HEALTH_FILE=str(tmp_path / "health"),
    )
    proc = subprocess.run(
        [sys.executable, "-m", "vision_inspection"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert proc.returncode == 2, proc.stderr.decode("utf-8", "replace")
    lines = proc.stdout.decode("utf-8").splitlines()
    assert lines, "no log output"
    last = json.loads(lines[-1])
    assert list(last)[:3] == ["ts", "level", "event"]
    assert last["level"] == "ERROR"
    assert last["event"] == "error"
    assert last["reason"] == "invalid_config"
    assert last["detail"].startswith("MQTT_URL")
    assert not (tmp_path / "health").exists()
