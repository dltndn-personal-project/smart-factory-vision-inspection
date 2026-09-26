import json
import statistics
import time

import pytest

from vision_inspection.process import Drop, Publish, process

TS = "2026-09-25T05:20:13.425Z"

REASONS = [
    "invalid_json",
    "invalid_payload",
    "invalid_product_id",
    "invalid_timestamp",
    "invalid_image_path",
    "ground_truth_unreadable",
    "ground_truth_missing",
    "ground_truth_duplicate",
    "ground_truth_invalid",
]


def test_publish_outcome(gt_file, shared_examples):
    p = gt_file.write([shared_examples["ground_truth_bytes"].rstrip(b"\n")])
    out = process(shared_examples["product_created_bytes"], p.path)
    assert isinstance(out, Publish)
    assert json.loads(out.payload) == shared_examples["vision_result"]
    assert list(json.loads(out.payload)) == list(shared_examples["vision_result"])
    assert (out.product_id, out.timestamp, out.defect, out.defect_type, out.bad_lines) == (
        "P-00000113", TS, True, "scratch", 0,
    )


def test_publish_good_product(gt_file, gt_line, make_pc):
    p = gt_file.write([gt_line("P-00000002", None)])
    out = process(make_pc("P-00000002"), p.path)
    assert isinstance(out, Publish)
    assert (out.defect, out.defect_type) == (False, None)
    assert json.loads(out.payload)["defect_type"] is None


def _case(reason, tmp_path, gt_file, gt_line, make_pc):
    """reason 하나를 내는 (raw, ground_truth_path)."""
    ok = gt_file.write([gt_line("P-00000001", "dent")]).path
    if reason == "invalid_json":
        return b"{oops", ok
    if reason == "invalid_payload":
        return make_pc("P-00000001", schema_version=2), ok
    if reason == "invalid_product_id":
        return make_pc("P-00000001", product_id="P-1"), ok
    if reason == "invalid_timestamp":
        return make_pc("P-00000001", timestamp="2026-09-25T05:20:13Z"), ok
    if reason == "invalid_image_path":
        return make_pc("P-00000001", image_path="products/P-00000002.jpg"), ok
    if reason == "ground_truth_unreadable":
        return make_pc("P-00000001"), tmp_path / "missing" / "products.jsonl"
    if reason == "ground_truth_missing":
        return make_pc("P-00000002"), ok
    if reason == "ground_truth_duplicate":
        return make_pc("P-00000001"), gt_file.write([gt_line("P-00000001", "dent")] * 2).path
    if reason == "ground_truth_invalid":
        bad = gt_line("P-00000001", "dent")
        bad["defect_type"] = "Dent"
        return make_pc("P-00000001"), gt_file.write([bad]).path
    raise AssertionError(reason)


@pytest.mark.parametrize("reason", REASONS)
def test_each_reason(reason, tmp_path, gt_file, gt_line, make_pc):
    raw, path = _case(reason, tmp_path, gt_file, gt_line, make_pc)
    out = process(raw, path)
    assert isinstance(out, Drop)
    assert out.reason == reason
    assert isinstance(out.detail, str) and out.detail and len(out.detail) <= 200


def test_drop_carries_ids_only_when_valid(tmp_path, gt_file, gt_line, make_pc):
    expected = {
        "invalid_json": (None, None),
        "invalid_payload": (None, None),
        "invalid_product_id": (None, None),
        "invalid_timestamp": ("P-00000001", None),
        "invalid_image_path": ("P-00000001", TS),
        "ground_truth_unreadable": ("P-00000001", TS),
        "ground_truth_missing": ("P-00000002", TS),
        "ground_truth_duplicate": ("P-00000001", TS),
        "ground_truth_invalid": ("P-00000001", TS),
    }
    for reason, ids in expected.items():
        raw, path = _case(reason, tmp_path, gt_file, gt_line, make_pc)
        out = process(raw, path)
        assert isinstance(out, Drop) and out.reason == reason
        assert (out.product_id, out.timestamp) == ids, reason


def test_detail_truncated_to_200(gt_file, gt_line, make_pc):
    p = gt_file.write([gt_line("P-00000001", "dent")])
    out = process(make_pc("P-00000001", image_path="x" * 1000), p.path)
    assert isinstance(out, Drop) and out.reason == "invalid_image_path"
    assert len(out.detail) == 200


def test_bad_lines_reported_on_publish(gt_file, gt_line, make_pc):
    p = gt_file.write(["not json", "", gt_line("P-00000001", "dent"), "[]"])
    out = process(make_pc("P-00000001"), p.path)
    assert isinstance(out, Publish) and out.bad_lines == 3

    missing = process(make_pc("P-00000005"), p.path)
    assert isinstance(missing, Drop) and missing.reason == "ground_truth_missing" and missing.bad_lines == 3


def test_mean_time_1800_lines(gt_file, gt_line, make_pc):
    types = ["scratch", "dent", "contamination", None, None]
    lines = [gt_line(f"P-{i:08d}", types[i % len(types)]) for i in range(1, 1801)]
    p = gt_file.write(lines)
    raw = make_pc("P-00001800")
    assert isinstance(process(raw, p.path), Publish)  # 데우기

    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        out = process(raw, p.path)
        times.append(time.perf_counter() - t0)
        assert isinstance(out, Publish)
    mean_ms = statistics.fmean(times) * 1000
    size_kb = p.path.stat().st_size / 1024
    print(f"\nprocess() 1,800 lines ({size_kb:.0f} KB): mean {mean_ms:.2f} ms, max {max(times) * 1000:.2f} ms (limit 50 ms)")
    assert mean_ms <= 50
