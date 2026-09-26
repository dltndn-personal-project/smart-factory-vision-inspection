import json
from dataclasses import dataclass

import pytest

from vision_inspection.payload import (
    ProductCreated,
    Rejected,
    build_vision_result,
    encode,
    parse_product_created,
)

GT_ONLY_FIELDS = ("image_size", "spawned_at", "fault_level", "severity", "defect_probability", "defect_params", "render_seed")


@dataclass(frozen=True)
class _GT:
    defect: bool
    defect_type: str | None


def _gt_from_line(line: dict) -> _GT:
    return _GT(line["defect"], line["defect_type"])


def _reject(raw: bytes) -> Rejected:
    with pytest.raises(Rejected) as e:
        parse_product_created(raw)
    return e.value


def test_shared_example_parses(shared_examples):
    pc = parse_product_created(shared_examples["product_created_bytes"])
    ex = shared_examples["product_created"]
    assert pc == ProductCreated(ex["product_id"], ex["timestamp"], ex["image_path"])


def test_unknown_fields_ignored(make_pc):
    raw = make_pc("P-00000007", extra={"a": [1, 2]}, note="무시", defect=True)
    assert parse_product_created(raw) == ProductCreated("P-00000007", "2026-09-25T05:20:13.425Z", "products/P-00000007.jpg")


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff\xfe{}",  # UTF-8 아님
        '{"schema_version":1,"product_id":"P-00000001"}'.encode("utf-16"),
        b"not json",
        b"",
        b'{"schema_version":1,',
        b"[]",
        b'[{"schema_version":1}]',
        b'"text"',
        b"null",
        b"1",
        b'{"schema_version":1,"product_id":"P-00000001","timestamp":"2026-09-25T05:20:13.425Z","image_path":"products/P-00000001.jpg","x":NaN}',
        b'{"schema_version":Infinity}',
        b'{"schema_version":-Infinity}',
    ],
)
def test_invalid_json(raw):
    r = _reject(raw)
    assert r.reason == "invalid_json"
    assert r.product_id is None and r.timestamp is None


@pytest.mark.parametrize(
    "override",
    [
        {"schema_version": None},  # 없음
        {"schema_version": 2},
        {"schema_version": True},
        {"schema_version": "1"},
        {"schema_version": 1.0},
        {"product_id": None},
        {"timestamp": None},
        {"image_path": None},
        {"product_id": 113},
        {"timestamp": 1758777613425},
        {"image_path": ["products/P-00000001.jpg"]},
    ],
)
def test_invalid_payload(make_pc, override):
    r = _reject(make_pc("P-00000001", **override))
    assert r.reason == "invalid_payload"
    assert r.product_id is None and r.timestamp is None


def test_invalid_payload_reports_first_missing_field_in_order(make_pc):
    r = _reject(make_pc("P-00000001", timestamp=None, image_path=None))
    assert r.reason == "invalid_payload" and "timestamp" in r.detail


@pytest.mark.parametrize(
    "product_id",
    ["P-1", "p-00000001", "P-0000000١", "P-00000001\n", "P-000000001", "Q-00000001", " P-00000001", ""],
)
def test_invalid_product_id(make_pc, product_id):
    raw = make_pc("P-00000001", product_id=product_id)
    r = _reject(raw)
    assert r.reason == "invalid_product_id"
    assert r.product_id is None and r.timestamp is None


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-09-25T05:20:13Z",
        "2026-09-25T05:20:13.42Z",
        "2026-09-25T05:20:13.4250Z",
        "2026-09-25T05:20:13.425+00:00",
        "2026-09-25T05:20:13.425Z\n",
        "2026-09-25 05:20:13.425Z",
        "2026-09-25T05:20:13.425z",
        "2026-09-2٥T05:20:13.425Z",
    ],
)
def test_invalid_timestamp(make_pc, timestamp):
    r = _reject(make_pc("P-00000001", timestamp=timestamp))
    assert r.reason == "invalid_timestamp"
    assert r.product_id == "P-00000001" and r.timestamp is None


def test_timestamp_format_only(make_pc):
    # 날짜 값의 유효성은 보지 않고, 받은 문자열을 그대로 싣는다
    pc = parse_product_created(make_pc("P-00000001", timestamp="2026-13-45T25:61:61.999Z"))
    assert pc.timestamp == "2026-13-45T25:61:61.999Z"


@pytest.mark.parametrize(
    "image_path",
    [
        "/data/products/P-00000001.jpg",
        "products/.P-00000001.jpg.tmp",
        "products/P-00000002.jpg",
        "products/../products/P-00000001.jpg",
        "../products/P-00000001.jpg",
        "products/P-00000001.jpeg",
        "products/P-00000001.jpg\n",
        "",
    ],
)
def test_invalid_image_path(make_pc, image_path):
    r = _reject(make_pc("P-00000001", image_path=image_path))
    assert r.reason == "invalid_image_path"
    assert r.product_id == "P-00000001" and r.timestamp == "2026-09-25T05:20:13.425Z"


def test_build_matches_shared_example(shared_examples):
    pc = parse_product_created(shared_examples["product_created_bytes"])
    result = build_vision_result(pc, _gt_from_line(shared_examples["ground_truth"]))
    assert result == shared_examples["vision_result"]
    assert list(result) == list(shared_examples["vision_result"])


def test_encoded_key_order_matches_shared_example(shared_examples):
    pc = parse_product_created(shared_examples["product_created_bytes"])
    raw = encode(build_vision_result(pc, _gt_from_line(shared_examples["ground_truth"])))
    assert b"\n" not in raw and b": " not in raw and b", " not in raw
    decoded = json.loads(raw)
    assert list(decoded) == list(shared_examples["vision_result"])
    assert decoded == shared_examples["vision_result"]
    assert raw == (
        b'{"schema_version":1,"product_id":"P-00000113","timestamp":"2026-09-25T05:20:13.425Z",'
        b'"defect":true,"defect_type":"scratch","confidence":null,"bbox":null,'
        b'"image_path":"products/P-00000113.jpg","gradcam_path":null,"judgement_source":"PASS_THROUGH"}'
    )


def test_good_product_result(make_pc):
    pc = parse_product_created(make_pc("P-00000002"))
    result = build_vision_result(pc, _GT(False, None))
    assert result["defect"] is False and result["defect_type"] is None
    assert result["confidence"] is None and result["bbox"] is None and result["gradcam_path"] is None


def test_no_other_ground_truth_fields(shared_examples):
    line = shared_examples["ground_truth"]
    assert line["bbox"] is not None  # 예시 줄의 bbox는 값이 있지만 옮기지 않는다
    pc = parse_product_created(shared_examples["product_created_bytes"])
    result = build_vision_result(pc, _gt_from_line(line))
    assert result["bbox"] is None
    for key in GT_ONLY_FIELDS:
        assert key not in result
    assert set(result) == {
        "schema_version", "product_id", "timestamp", "defect", "defect_type",
        "confidence", "bbox", "image_path", "gradcam_path", "judgement_source",
    }
