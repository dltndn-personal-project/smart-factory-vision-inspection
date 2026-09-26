"""실제 Mosquitto 연동 테스트 (docs/spec/04-verification.md 3.2절, 02-service.md).

모두 docker 마커다. Docker를 쓸 수 없으면 fixture가 실패한다. 서비스는 실제 진입점(`python -m vision_inspection`)으로
띄우고, 기다림은 "사건이 올 때까지 최대 N초"로 쓴다. 미발행 확인은 sentinel 결과 뒤 0.5초 더 기다려 본다.
"""

from __future__ import annotations

import json
import statistics
import threading
import time

import pytest

pytestmark = pytest.mark.docker

CONNECT_TIMEOUT = 10.0  # 서비스 기동(파이썬 import 포함)부터 connected까지. 기준 수치가 아니라 테스트 안전 한도


def test_publishes_shared_example(broker, service, results, gt_file, shared_examples):
    gt_file.write([shared_examples["ground_truth_bytes"].rstrip(b"\n")])
    svc = service(broker.url)
    svc.wait_for("connected", timeout=CONNECT_TIMEOUT)
    res = results(broker)

    pc = shared_examples["product_created_bytes"]
    res.publish(pc)
    body, qos, retain, _ = res.get(timeout=5)
    assert body == shared_examples["vision_result"]
    assert qos == 1
    assert retain is False
    res.expect_none(0.5)

    _, received = svc.wait_for("received")
    assert received["topic"] == "factory/product/created"
    assert received["bytes"] == len(pc)
    _, published = svc.wait_for("published")
    assert published["product_id"] == shared_examples["vision_result"]["product_id"]
    assert published["timestamp"] == shared_examples["vision_result"]["timestamp"]
    assert published["defect"] == shared_examples["vision_result"]["defect"]
    assert published["defect_type"] == shared_examples["vision_result"]["defect_type"]
    assert type(published["latency_ms"]) is int and published["latency_ms"] >= 0

    # retain false 발행: 새 구독자는 SUBACK 뒤 1초 동안 retained 메시지를 받지 않는다
    late = results(broker)
    late.expect_none(1.0)


def test_invalid_inputs_not_published(broker, service, results, gt_file, make_pc, gt_line):
    contradictory = gt_line("P-00000008", None)
    contradictory["defect_type"] = "scratch"  # defect false + scratch
    gt_file.write(
        [
            gt_line("P-00000007", "dent"),
            gt_line("P-00000007", "dent"),
            contradictory,
            gt_line("P-00000009", None),
        ]
    )
    svc = service(broker.url)
    svc.wait_for("connected", timeout=CONNECT_TIMEOUT)
    res = results(broker)

    inputs = [
        (b"{not json", "invalid_json"),
        (make_pc("P-00000002", schema_version=2), "invalid_payload"),
        (make_pc("P-1"), "invalid_product_id"),
        (make_pc("P-00000004", timestamp="2026-09-25T05:20:13Z"), "invalid_timestamp"),
        (make_pc("P-00000005", image_path="products/P-00000099.jpg"), "invalid_image_path"),
        (make_pc("P-00000006"), "ground_truth_missing"),
        (make_pc("P-00000007"), "ground_truth_duplicate"),
        (make_pc("P-00000008"), "ground_truth_invalid"),
    ]
    for payload, _ in inputs:
        res.publish(payload)
    res.publish(make_pc("P-00000009"))  # sentinel

    body, _, _, _ = res.get(timeout=5)
    assert body["product_id"] == "P-00000009"
    assert body["defect"] is False and body["defect_type"] is None
    res.expect_none(0.5)

    svc.wait_for("published", lambda r: r["product_id"] == "P-00000009")
    assert [r["reason"] for r in svc.events("dropped")] == [reason for _, reason in inputs]


def test_ground_truth_created_later(broker, service, results, gt_file, make_pc, gt_line):
    assert not gt_file.path.exists()
    svc = service(broker.url)
    svc.wait_for("connected", timeout=CONNECT_TIMEOUT)
    res = results(broker)

    res.publish(make_pc("P-00000001"))
    _, dropped = svc.wait_for("dropped")
    assert dropped["reason"] == "ground_truth_unreadable"
    assert dropped["product_id"] == "P-00000001"

    gt_file.write([gt_line("P-00000002", "contamination")])
    res.publish(make_pc("P-00000002"))
    body, _, _, _ = res.get(timeout=5)
    assert body["product_id"] == "P-00000002"
    assert body["defect"] is True and body["defect_type"] == "contamination"
    res.expect_none(0.5)


def test_broker_restart_resubscribes(fixed_port_broker, service, results, gt_file, make_pc, gt_line):
    fixed_port_broker.start()
    gt_file.write([gt_line("P-00000001", "scratch")])
    svc = service(fixed_port_broker.url)
    svc.wait_for("connected", timeout=CONNECT_TIMEOUT)
    assert svc.health_file.exists()
    mark = svc.mark()

    # restart는 다른 스레드에서 한다: disconnected 로그 직후(재연결은 빨라도 1초 뒤) 기동 확인 파일을 보기 위해
    restart_done: list[float] = []
    errors: list[BaseException] = []

    def restart() -> None:
        try:
            fixed_port_broker.restart()
            restart_done.append(time.monotonic())
        except BaseException as e:  # 주 스레드에서 다시 올린다
            errors.append(e)

    worker = threading.Thread(target=restart, name="vis-test-docker-restart")
    worker.start()
    i_disc, _ = svc.wait_for("disconnected", after=mark, timeout=30)
    assert not svc.health_file.exists()
    worker.join(timeout=60)
    assert not errors, errors
    assert restart_done, "docker restart가 끝나지 않았다"

    remaining = restart_done[0] + 15 - time.monotonic()
    svc.wait_for("connected", after=i_disc + 1, timeout=max(0.0, remaining))
    assert svc.health_file.exists()

    res = results(fixed_port_broker)
    res.publish(make_pc("P-00000001"))
    body, _, _, _ = res.get(timeout=5)
    assert body["product_id"] == "P-00000001"
    assert body["defect_type"] == "scratch"


def test_starts_before_broker(fixed_port_broker, service, results, gt_file, make_pc, gt_line):
    gt_file.write([gt_line("P-00000001", "dent")])
    svc = service(fixed_port_broker.url)
    time.sleep(2)  # 미발생 확인(연결되지 않음)을 위한 관찰 시간. 통과를 기다리는 sleep이 아니다
    assert not svc.health_file.exists()
    assert len(svc.events("connect_failed")) >= 1
    assert not svc.events("connected")

    t_start = time.monotonic()
    fixed_port_broker.start()
    svc.wait_for("connected", timeout=max(0.0, t_start + 15 - time.monotonic()))
    assert svc.health_file.exists()

    res = results(fixed_port_broker)
    res.publish(make_pc("P-00000001"))
    body, _, _, _ = res.get(timeout=5)
    assert body["product_id"] == "P-00000001"
    assert body["defect"] is True and body["defect_type"] == "dent"


def test_sigterm_exits_0(broker, service):
    svc = service(broker.url)
    svc.wait_for("connected", timeout=CONNECT_TIMEOUT)
    assert svc.health_file.exists()

    code = svc.stop(timeout=5)
    assert code == 0
    last = json.loads(svc.lines[-1])
    assert last["event"] == "stopped"
    assert last["signal"] == "SIGTERM"
    assert not svc.health_file.exists()


def test_latency_1800_lines(broker, service, results, gt_file, make_pc, gt_line):
    kinds = (None, "scratch", "dent", "contamination")
    ids = [f"P-{n:08d}" for n in range(1, 1801)]
    gt_file.write([gt_line(pid, kinds[n % 4]) for n, pid in enumerate(ids)])
    expected = {pid: kinds[n % 4] for n, pid in enumerate(ids)}
    svc = service(broker.url)
    svc.wait_for("connected", timeout=CONNECT_TIMEOUT)
    res = results(broker)

    last30 = ids[-30:]
    sent: dict[str, float] = {}
    t_begin = time.monotonic()
    for k, pid in enumerate(last30):
        delay = t_begin + k * 0.1 - time.monotonic()
        if delay > 0:
            time.sleep(delay)  # 0.1초 간격 발행(속도 조절)
        sent[pid] = res.publish(make_pc(pid))

    got = res.take(30, timeout=10)
    latencies: dict[str, float] = {}
    for body, qos, retain, arrived in got:
        pid = body["product_id"]
        assert pid in sent and pid not in latencies, pid
        assert body["defect_type"] == expected[pid]
        latencies[pid] = arrived - sent[pid]
    assert sorted(latencies) == sorted(last30)

    values = list(latencies.values())
    median = statistics.median(values)
    worst = max(values)
    print(f"\nlatency_1800_lines: n={len(values)} median={median * 1000:.1f} ms max={worst * 1000:.1f} ms")
    assert worst <= 2.0
    assert median <= 0.5
