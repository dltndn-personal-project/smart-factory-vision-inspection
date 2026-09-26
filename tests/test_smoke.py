"""compose smoke (docs/spec/04-verification.md 3.3절, 03-runtime.md 5·6절).

저장소 루트의 compose.yaml로 이미지를 빌드해 프로젝트 이름 vis-smoke로 띄우고, 실행 정의 전체(healthcheck, 읽기 전용
/data, 결과 발행, JSON 로그, 정상 종료)를 확인한다. Docker를 쓸 수 없으면 실패한다(건너뛰지 않는다, 04 1절).
성공·실패와 무관하게 끝에 `down -v --remove-orphans`로 자기 자원만 정리한다.
"""

from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import log_problems
from vision_inspection.payload import encode

pytestmark = pytest.mark.smoke

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT = "vis-smoke"
SERVICE = "vision-inspection"
VOLUME = f"{PROJECT}_image-storage"
MOSQUITTO_IMAGE = "eclipse-mosquitto:2.1.2-alpine"
LOG_TIMEOUT = 5.0  # 결과를 받은 뒤 docker logs에 줄이 나타날 때까지의 안전 한도(기준 수치 아님)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _compose_env(port: int) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}
    env["VIS_MQTT_PORT"] = str(port)
    return env


def _compose(env: dict[str, str], *args: str, check: bool = True, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-p", PROJECT, *args],
        cwd=REPO_ROOT, env=env, check=check, timeout=timeout, capture_output=True, text=True,
    )


def _service_logs(env: dict[str, str]) -> list[str]:
    out = _compose(env, "logs", "--no-log-prefix", SERVICE).stdout
    return [line for line in out.splitlines() if line.strip()]


def _container_id(env: dict[str, str]) -> str:
    cid = _compose(env, "ps", "-a", "-q", SERVICE).stdout.strip()
    assert cid, f"{SERVICE} 컨테이너가 없다"
    return cid


def _expected(example: dict[str, Any], product_id: str, defect_type: str | None) -> dict[str, Any]:
    obj = copy.deepcopy(example)
    obj.update(
        product_id=product_id,
        timestamp="2026-09-25T05:20:13.425Z",
        defect=defect_type is not None,
        defect_type=defect_type,
        confidence=None,
        bbox=None,
        image_path=f"products/{product_id}.jpg",
        gradcam_path=None,
        judgement_source="PASS_THROUGH",
    )
    return obj


def _events(lines: list[str]) -> list[dict[str, Any]]:
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def test_compose_smoke(results, make_pc, gt_line, shared_examples):
    port = _free_port()
    env = _compose_env(port)

    # 1. 남은 자원 정리
    _compose(env, "down", "-v", "--remove-orphans")
    try:
        # 2. 빌드와 기동. --wait는 healthcheck(구독 SUBACK 뒤 기동 확인 파일)가 healthy가 될 때까지 기다린다(C-08)
        t0 = time.monotonic()
        up = _compose(env, "up", "-d", "--build", "--wait", "--wait-timeout", "60", check=False, timeout=600)
        print(f"compose up --build --wait: {time.monotonic() - t0:.1f}s")
        assert up.returncode == 0, f"compose up 실패(종료 코드 {up.returncode}):\n{up.stdout}\n{up.stderr}"

        # 3. /data가 읽기 전용 마운트(V-04, D-17)
        cid = _container_id(env)
        mounts = json.loads(
            subprocess.check_output(["docker", "inspect", "-f", "{{json .Mounts}}", cid], text=True, timeout=15)
        )
        data = [m for m in mounts if m.get("Destination") == "/data"]
        assert len(data) == 1, mounts
        assert data[0]["RW"] is False, data[0]

        # 4. 볼륨에 Ground Truth 세 줄: 불량(dent), 양품, 끝에 \n 없는 줄(완성되지 않은 줄은 무시되어야 한다)
        gt = (
            encode(gt_line("P-00000001", "dent")) + b"\n"
            + encode(gt_line("P-00000002", None)) + b"\n"
            + encode(gt_line("P-00000003", "scratch"))
        )
        subprocess.run(
            ["docker", "run", "--rm", "-i", "-v", f"{VOLUME}:/data", MOSQUITTO_IMAGE,
             "sh", "-c", "mkdir -p /data/ground_truth && cat >> /data/ground_truth/products.jsonl"],
            input=gt, check=True, timeout=60, capture_output=True,
        )

        # 5. 호스트에서 결과 구독(SUBACK까지 최대 5초) 뒤 Product Created 셋과 잘못된 JSON 발행
        res = results(SimpleNamespace(host="127.0.0.1", port=port))
        for pid in ("P-00000001", "P-00000002", "P-00000003"):
            res.publish(make_pc(pid))
        res.publish(b"{not json")

        # 6. 10초 안에 P-00000001(dent)과 P-00000002(양품) 결과, 그 뒤 1초 동안 다른 결과 없음
        got = res.take(2, timeout=10)
        bodies = {body["product_id"]: (body, qos, retain) for body, qos, retain, _ in got}
        example = shared_examples["vision_result"]
        for pid, defect_type in (("P-00000001", "dent"), ("P-00000002", None)):
            assert pid in bodies, got
            body, qos, retain = bodies[pid]
            expected = _expected(example, pid, defect_type)
            assert body == expected
            assert list(body) == list(example)  # Shared 예시와 같은 키 순서(01 4절)
            assert qos == 1 and retain is False
        res.expect_none(1.0)

        # 7. 서비스 로그: 모든 줄이 JSON(C-06)이고 started, connected, published 2개, dropped 2종
        deadline = time.monotonic() + LOG_TIMEOUT
        while True:
            lines = _service_logs(env)
            recs = _events(lines)
            names = [r.get("event") for r in recs]
            reasons = {r.get("reason") for r in recs if r.get("event") == "dropped"}
            ok = (
                "started" in names
                and "connected" in names
                and names.count("published") == 2
                and {"ground_truth_missing", "invalid_json"} <= reasons
            )
            if ok or time.monotonic() >= deadline:
                break
            time.sleep(0.2)
        assert not log_problems(lines), "\n".join(log_problems(lines))
        assert "started" in names and "connected" in names, names
        assert names.count("published") == 2, names
        assert {"ground_truth_missing", "invalid_json"} <= reasons, reasons
        missing = [r for r in recs if r.get("reason") == "ground_truth_missing"]
        assert [r.get("product_id") for r in missing] == ["P-00000003"], missing

        # 8. stop -t 10 → 종료 코드 0, 로그 마지막 줄 stopped(C-05)
        _compose(env, "stop", "-t", "10", SERVICE, timeout=60)
        code = subprocess.check_output(
            ["docker", "inspect", "-f", "{{.State.ExitCode}}", cid], text=True, timeout=15
        ).strip()
        assert code == "0", code
        lines = _service_logs(env)
        assert not log_problems(lines), "\n".join(log_problems(lines))
        last = json.loads(lines[-1])
        assert last["event"] == "stopped", lines[-5:]
    except BaseException:
        # 실패하면 compose 로그 마지막 100줄
        tail = _compose(env, "logs", "--tail", "100", check=False, timeout=60)
        print("--- compose logs (tail 100) ---")
        print(tail.stdout)
        print(tail.stderr)
        raise
    finally:
        # 9. 성공·실패와 무관하게 정리
        _compose(env, "down", "-v", "--remove-orphans", check=False, timeout=120)
