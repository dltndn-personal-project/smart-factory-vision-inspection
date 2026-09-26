"""공용 fixture (docs/spec/04-verification.md 2절).

VIS-2가 shared_examples, gt_file, make_pc, gt_line을 더했다. VIS-3이 Docker fixture broker, fixed_port_broker,
service, results를 더했다. Docker를 쓸 수 없으면 Docker fixture는 실패한다(건너뛰지 않는다, 04 1절).
Docker 컨테이너 이름은 vision-inspection-test-<uuid8>이다(다른 Component 테스트와 겹치지 않게).
"""

from __future__ import annotations

import copy
import json
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

import paho.mqtt.client as mqtt  # 테스트 쪽 MQTT client. src에서는 app.py만 paho를 쓴다
import pytest
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode

FIXTURES = Path(__file__).parent / "fixtures" / "shared_d0c997c"
DEFAULT_TIMESTAMP = "2026-09-25T05:20:13.425Z"


def _load_examples() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, name in (
        ("product_created", "product_created.json"),
        ("vision_result", "vision_result.json"),
        ("ground_truth", "ground_truth.jsonl"),
    ):
        raw = (FIXTURES / name).read_bytes()
        out[key] = json.loads(raw)
        out[key + "_bytes"] = raw
    return out


@pytest.fixture
def shared_examples() -> dict[str, Any]:
    """Shared d0c997c 예시. 키: product_created, vision_result, ground_truth(dict)와 각 *_bytes(파일 내용)."""
    return _load_examples()


@dataclass(frozen=True)
class GtPaths:
    image_root: Path
    path: Path


class GtFile:
    def __init__(self, root: Path) -> None:
        self.image_root = root
        self.path = root / "ground_truth" / "products.jsonl"

    def write(self, lines: list[Any], tail: str | bytes | None = None) -> GtPaths:
        """dict는 encode한 줄, str·bytes는 그대로 한 줄로 쓰고 각 줄 끝에 \\n. tail은 \\n 없이 덧붙인다."""
        from vision_inspection.payload import encode

        chunks: list[bytes] = []
        for line in lines:
            if isinstance(line, dict):
                chunks.append(encode(line))
            elif isinstance(line, str):
                chunks.append(line.encode("utf-8"))
            else:
                chunks.append(bytes(line))
            chunks.append(b"\n")
        if tail is not None:
            chunks.append(tail.encode("utf-8") if isinstance(tail, str) else bytes(tail))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"".join(chunks))
        return GtPaths(self.image_root, self.path)


@pytest.fixture
def gt_file(tmp_path: Path) -> GtFile:
    return GtFile(tmp_path)


@pytest.fixture
def make_pc() -> Callable[..., bytes]:
    """Product Created bytes. override 값이 None이면 그 키를 뺀다."""

    def make(product_id: str, /, **override: Any) -> bytes:
        obj: dict[str, Any] = {
            "schema_version": 1,
            "product_id": product_id,
            "timestamp": DEFAULT_TIMESTAMP,
            "image_path": f"products/{product_id}.jpg",
        }
        for key, value in override.items():
            if value is None:
                obj.pop(key, None)
            else:
                obj[key] = value
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    return make


@pytest.fixture
def gt_line() -> Callable[[str, str | None], dict[str, Any]]:
    """Shared 예시 Ground Truth 줄을 복사해 product_id·timestamp·image_path·defect·defect_type·bbox만 바꾼 dict."""
    example = _load_examples()["ground_truth"]

    def make(product_id: str, defect_type: str | None) -> dict[str, Any]:
        obj = copy.deepcopy(example)
        obj["product_id"] = product_id
        obj["timestamp"] = DEFAULT_TIMESTAMP
        obj["image_path"] = f"products/{product_id}.jpg"
        obj["defect"] = defect_type is not None
        obj["defect_type"] = defect_type
        obj["bbox"] = [250, 301, 330, 352] if defect_type is not None else None
        return obj

    return make


# --- Docker 연동 fixture (VIS-3, docs/spec/04-verification.md 2절) ------------------------------

MOSQUITTO_IMAGE = "eclipse-mosquitto:2.1.2-alpine"
CONTAINER_PREFIX = "vision-inspection-test-"
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
PRODUCT_CREATED_TOPIC = "factory/product/created"
VISION_RESULT_TOPIC = "factory/vision/result"
CONFIG_KEYS = (
    "MQTT_URL",
    "MQTT_CLIENT_ID",
    "PRODUCT_CREATED_TOPIC",
    "VISION_RESULT_TOPIC",
    "IMAGE_ROOT",
    "LOG_LEVEL",
    "HEALTH_FILE",
)

# 02-service.md 4절 표. event → 허용 reason(reason 키가 없어야 하면 빈 집합)
LOG_REASONS: dict[str, frozenset[str]] = {
    "started": frozenset(),
    "connected": frozenset(),
    "connect_failed": frozenset({"connect_failed"}),
    "disconnected": frozenset({"disconnected"}),
    "received": frozenset(),
    "warning": frozenset({"ground_truth_bad_lines"}),
    "dropped": frozenset(
        {
            "invalid_json",
            "invalid_payload",
            "invalid_product_id",
            "invalid_timestamp",
            "invalid_image_path",
            "ground_truth_unreadable",
            "ground_truth_missing",
            "ground_truth_duplicate",
            "ground_truth_invalid",
            "publish_failed",
            "internal_error",
        }
    ),
    "published": frozenset(),
    "error": frozenset({"invalid_config", "internal_error"}),
    "stopped": frozenset(),
}
LOG_LEVELS = frozenset({"INFO", "WARNING", "ERROR"})
# CONVENTIONS Timestamp 정규식 ^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$ (ASCII 숫자만)
TS_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z")


def log_problems(lines: list[str]) -> list[str]:
    """C-06: 모든 줄이 JSON 객체, 첫 세 키 ts·level·event, ts 형식, event·reason이 4절 값 안."""
    problems: list[str] = []
    for n, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except ValueError:
            problems.append(f"line {n}: not JSON: {line!r}")
            continue
        if not isinstance(rec, dict):
            problems.append(f"line {n}: not an object: {line!r}")
            continue
        if list(rec)[:3] != ["ts", "level", "event"]:
            problems.append(f"line {n}: leading keys {list(rec)[:3]}")
            continue
        if not isinstance(rec["ts"], str) or not TS_RE.fullmatch(rec["ts"]):
            problems.append(f"line {n}: ts {rec['ts']!r}")
        if rec["level"] not in LOG_LEVELS:
            problems.append(f"line {n}: level {rec['level']!r}")
        event = rec["event"]
        if event not in LOG_REASONS:
            problems.append(f"line {n}: event {event!r}")
        elif "reason" in rec and rec["reason"] not in LOG_REASONS[event]:
            problems.append(f"line {n}: reason {rec['reason']!r} for event {event!r}")
        elif "reason" not in rec and LOG_REASONS[event]:
            problems.append(f"line {n}: event {event!r} without reason")
    return problems


def _uuid8() -> str:
    return uuid.uuid4().hex[:8]


def _new_client(prefix: str) -> mqtt.Client:
    return mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=f"{prefix}-{_uuid8()}",
        protocol=mqtt.MQTTv311,
        clean_session=True,
    )


def _wait_broker_ready(host: str, port: int, timeout: float = 15.0) -> None:
    """paho probe가 CONNACK을 받을 때까지 최대 timeout초 (factory-simulator _broker와 같은 방식)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        acknowledged = threading.Event()
        probe = _new_client("vis-test-probe")

        def on_connect(client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
            if not reason_code.is_failure:
                acknowledged.set()

        probe.on_connect = on_connect
        try:
            if probe.connect(host, port, keepalive=5) == MQTTErrorCode.MQTT_ERR_SUCCESS:
                probe.loop_start()
                if acknowledged.wait(min(0.5, max(0.0, deadline - time.monotonic()))):
                    return
        except OSError:
            pass
        finally:
            probe.disconnect()
            probe.loop_stop()
        time.sleep(0.1)
    raise TimeoutError(f"MQTT broker 127.0.0.1:{port}가 {timeout}초 안에 CONNACK을 보내지 않았다")


def _docker_run_broker(name: str, binding: str) -> None:
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", name, "-p", binding,
         MOSQUITTO_IMAGE, "mosquitto", "-c", "/mosquitto-no-auth.conf"],
        check=True, timeout=30, stdout=subprocess.DEVNULL,
    )


def _docker_rm(name: str) -> None:
    subprocess.run(["docker", "rm", "-f", name], timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@dataclass(frozen=True)
class Broker:
    name: str
    host: str
    port: int
    url: str


@pytest.fixture
def broker() -> Iterator[Broker]:
    """임의 호스트 포트의 Mosquitto 컨테이너. CONNACK을 받을 때까지 기다린 뒤 돌려준다."""
    name = CONTAINER_PREFIX + _uuid8()
    try:
        _docker_run_broker(name, "127.0.0.1::1883")
        port_text = subprocess.check_output(["docker", "port", name, "1883/tcp"], text=True, timeout=10)
        port = int(port_text.strip().splitlines()[0].rsplit(":", 1)[1])
        b = Broker(name, "127.0.0.1", port, f"mqtt://127.0.0.1:{port}")
        _wait_broker_ready(b.host, b.port)
        yield b
    finally:
        _docker_rm(name)


class FixedPortBroker:
    """미리 고른 빈 포트에 묶는 Mosquitto. 포트·url은 start() 전에 알 수 있고, restart해도 포트가 유지된다."""

    def __init__(self) -> None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port: int = sock.getsockname()[1]
        self.host = "127.0.0.1"
        self.url = f"mqtt://127.0.0.1:{self.port}"
        self.name = CONTAINER_PREFIX + _uuid8()
        self.started = False

    def start(self) -> None:
        """컨테이너를 띄우고 CONNACK을 받을 때까지(최대 15초) 기다린다."""
        self.started = True
        _docker_run_broker(self.name, f"127.0.0.1:{self.port}:1883")
        _wait_broker_ready(self.host, self.port)

    def restart(self) -> None:
        """docker restart. 명령이 끝나면 돌아온다(Broker 준비는 기다리지 않는다)."""
        subprocess.run(["docker", "restart", self.name], check=True, timeout=60, stdout=subprocess.DEVNULL)

    def remove(self) -> None:
        if self.started:
            _docker_rm(self.name)


@pytest.fixture
def fixed_port_broker() -> Iterator[FixedPortBroker]:
    b = FixedPortBroker()
    try:
        yield b
    finally:
        b.remove()


class ServiceProcess:
    """`python -m vision_inspection` 하위 프로세스. 읽기 스레드가 stdout 줄을 모은다."""

    def __init__(self, env: dict[str, str], health_file: Path) -> None:
        self.health_file = health_file
        self.lines: list[str] = []
        self._cond = threading.Condition()
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "vision_inspection"], env=env, cwd=REPO_ROOT, stdout=subprocess.PIPE
        )
        self._reader = threading.Thread(target=self._read, name="vis-test-service-reader", daemon=True)
        self._reader.start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            with self._cond:
                self.lines.append(line)
                self._cond.notify_all()

    def records(self) -> list[dict[str, Any]]:
        """지금까지 읽은 줄 중 JSON 객체인 것(순서 유지). 형식 검사는 정리 단계의 log_problems가 한다."""
        with self._cond:
            lines = list(self.lines)
        out: list[dict[str, Any]] = []
        for line in lines:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
        return out

    def events(self, event: str) -> list[dict[str, Any]]:
        return [r for r in self.records() if r.get("event") == event]

    def mark(self) -> int:
        """지금까지 읽은 줄 수. wait_for(after=...)에 넘긴다."""
        with self._cond:
            return len(self.lines)

    def wait_for(
        self,
        event: str,
        pred: Callable[[dict[str, Any]], bool] | None = None,
        timeout: float = 5.0,
        after: int = 0,
    ) -> tuple[int, dict[str, Any]]:
        """줄 번호 after(0부터) 이후에서 event(와 pred)에 맞는 첫 줄을 최대 timeout초 기다린다. (줄 번호, 레코드)."""
        deadline = time.monotonic() + timeout
        start = after
        with self._cond:
            while True:
                for i in range(start, len(self.lines)):
                    try:
                        rec = json.loads(self.lines[i])
                    except ValueError:
                        continue
                    if isinstance(rec, dict) and rec.get("event") == event and (pred is None or pred(rec)):
                        return i, rec
                start = len(self.lines)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(
                        f"{timeout}초 안에 {event!r} 로그가 없다. 마지막 줄들:\n" + "\n".join(self.lines[-20:])
                    )
                self._cond.wait(remaining)

    def stop(self, sig: int = signal.SIGTERM, timeout: float = 5.0) -> int:
        """신호를 보내고 timeout초 안에 끝나기를 기다려 종료 코드를 돌려준다(넘으면 TimeoutExpired)."""
        self.proc.send_signal(sig)
        code = self.proc.wait(timeout=timeout)
        self._reader.join(timeout=5)
        return code

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=10)
        self._reader.join(timeout=5)


@pytest.fixture
def service(tmp_path: Path) -> Iterator[Callable[..., ServiceProcess]]:
    """service(mqtt_url, image_root=tmp_path, **env) → ServiceProcess. 정리 단계에서 모든 stdout 줄을 검사한다(C-06)."""
    started: list[ServiceProcess] = []

    def start(mqtt_url: str, image_root: Path | None = None, **extra: str) -> ServiceProcess:
        health_file = tmp_path / "health"
        env = {k: v for k, v in os.environ.items() if k not in CONFIG_KEYS}
        env.update(
            PYTHONPATH=str(SRC),
            MQTT_URL=mqtt_url,
            IMAGE_ROOT=str(image_root if image_root is not None else tmp_path),
            HEALTH_FILE=str(health_file),
            MQTT_CLIENT_ID=f"vis-test-{_uuid8()}",
        )
        env.update(extra)
        svc = ServiceProcess(env, health_file)
        started.append(svc)
        return svc

    yield start

    problems: list[str] = []
    for svc in started:
        svc.close()
        problems.extend(log_problems(svc.lines))
    assert not problems, "로그 형식 위반(C-06):\n" + "\n".join(problems)


class Results:
    """factory/vision/result를 QoS 1로 구독한 paho client. 받은 것을 (dict, qos, retain, 도착 monotonic)로 모은다.

    Product Created 발행도 이 client로 한다(publish). 재연결하면 다시 구독한다.
    """

    def __init__(self, host: str, port: int, topic: str = VISION_RESULT_TOPIC, timeout: float = 5.0) -> None:
        self.topic = topic
        self.queue: queue.Queue[tuple[Any, int, bool, float]] = queue.Queue()
        self._ready = threading.Event()
        self._sub_mid: int | None = None
        self._client = _new_client("vis-test-results")
        self._client.on_connect = self._on_connect
        self._client.on_subscribe = self._on_subscribe
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.connect(host, port, keepalive=30)
        self._client.loop_start()
        if not self._ready.wait(timeout):
            self.close()
            raise TimeoutError(f"{timeout}초 안에 {topic} 구독 SUBACK이 없다")

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if not reason_code.is_failure:
            _, self._sub_mid = client.subscribe(self.topic, qos=1)

    def _on_subscribe(self, client: Any, userdata: Any, mid: int, reason_codes: list[Any], properties: Any) -> None:
        if mid == self._sub_mid and reason_codes and not reason_codes[0].is_failure:
            self._ready.set()

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        self._ready.clear()

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        arrived = time.monotonic()
        try:
            body: Any = json.loads(msg.payload)
        except ValueError:
            body = bytes(msg.payload)
        self.queue.put((body, msg.qos, bool(msg.retain), arrived))

    def publish(self, payload: bytes, topic: str = PRODUCT_CREATED_TOPIC, qos: int = 1) -> float:
        """발행 호출 직전의 monotonic 시각을 돌려준다."""
        t = time.monotonic()
        info = self._client.publish(topic, payload, qos=qos, retain=False)
        assert info.rc == MQTTErrorCode.MQTT_ERR_SUCCESS, info.rc
        return t

    def get(self, timeout: float = 5.0) -> tuple[Any, int, bool, float]:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError(f"{timeout}초 안에 {self.topic} 메시지가 없다") from None

    def take(self, n: int, timeout: float) -> list[tuple[Any, int, bool, float]]:
        """n개를 전체 timeout초 안에 받는다."""
        deadline = time.monotonic() + timeout
        out = []
        while len(out) < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"{timeout}초 안에 {n}개 중 {len(out)}개만 받았다")
            try:
                out.append(self.queue.get(timeout=remaining))
            except queue.Empty:
                continue
        return out

    def expect_none(self, duration: float) -> None:
        """duration초 동안 아무것도 오지 않아야 한다."""
        try:
            got = self.queue.get(timeout=duration)
        except queue.Empty:
            return
        raise AssertionError(f"예상하지 않은 메시지: {got!r}")

    def close(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()


@pytest.fixture
def results() -> Iterator[Callable[..., Results]]:
    """results(broker) → Results. SUBACK을 받은 뒤(최대 5초) 돌려준다. broker는 host·port를 가진 객체."""
    made: list[Results] = []

    def make(b: Any, topic: str = VISION_RESULT_TOPIC) -> Results:
        r = Results(b.host, b.port, topic)
        made.append(r)
        return r

    yield make
    for r in made:
        r.close()
