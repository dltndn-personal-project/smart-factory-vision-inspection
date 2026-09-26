import pytest

from vision_inspection.ground_truth import GroundTruth, Lookup, lookup
from vision_inspection.payload import Rejected


def _reject(path, product_id) -> Rejected:
    with pytest.raises(Rejected) as e:
        lookup(path, product_id)
    return e.value


def test_shared_example_line_found(gt_file, shared_examples):
    p = gt_file.write([shared_examples["ground_truth_bytes"].rstrip(b"\n")])
    assert p.path.read_bytes() == shared_examples["ground_truth_bytes"]
    assert lookup(p.path, "P-00000113") == Lookup(GroundTruth(True, "scratch"), 0)


def test_good_and_other_lines(gt_file, gt_line):
    p = gt_file.write([gt_line("P-00000001", "dent"), gt_line("P-00000002", None), gt_line("P-00000003", "contamination")])
    assert lookup(p.path, "P-00000002") == Lookup(GroundTruth(False, None), 0)
    assert lookup(p.path, "P-00000003") == Lookup(GroundTruth(True, "contamination"), 0)


def test_incomplete_last_line_ignored(gt_file, gt_line):
    from vision_inspection.payload import encode

    p = gt_file.write([gt_line("P-00000001", "dent")], tail=encode(gt_line("P-00000002", None)))
    assert lookup(p.path, "P-00000001").gt == GroundTruth(True, "dent")
    r = _reject(p.path, "P-00000002")
    assert r.reason == "ground_truth_missing"
    assert r.bad_lines == 0  # 잘린 끝 줄은 깨진 줄로 세지 않는다


def test_empty_file_is_missing(gt_file):
    p = gt_file.write([])
    assert p.path.read_bytes() == b""
    assert _reject(p.path, "P-00000001").reason == "ground_truth_missing"


def test_duplicate(gt_file, gt_line):
    p = gt_file.write([gt_line("P-00000001", "dent"), gt_line("P-00000002", None), gt_line("P-00000001", "dent")])
    r = _reject(p.path, "P-00000001")
    assert r.reason == "ground_truth_duplicate"
    assert "2" in r.detail


def test_bad_lines_skipped_and_counted(gt_file, gt_line):
    p = gt_file.write(
        [
            '{"product_id": "P-00000001", broken',
            "[1, 2, 3]",
            "",
            b"\xff\xfe not utf-8",
            '{"product_id":"P-00000009","defect":true,"defect_type":"dent","severity":Infinity}',
            gt_line("P-00000001", "scratch"),
            '"just a string"',
        ]
    )
    assert lookup(p.path, "P-00000001") == Lookup(GroundTruth(True, "scratch"), 6)
    r = _reject(p.path, "P-00000009")  # Infinity가 든 줄은 깨진 줄이므로 찾지 못한다
    assert r.reason == "ground_truth_missing" and r.bad_lines == 6


def test_bad_lines_carried_on_rejection(gt_file, gt_line):
    p = gt_file.write(["not json", gt_line("P-00000001", "dent"), gt_line("P-00000001", "dent")])
    r = _reject(p.path, "P-00000001")
    assert r.reason == "ground_truth_duplicate" and r.bad_lines == 1


def test_unreadable(tmp_path):
    r = _reject(tmp_path / "ground_truth" / "products.jsonl", "P-00000001")
    assert r.reason == "ground_truth_unreadable"
    assert r.detail.startswith("FileNotFoundError")

    d = tmp_path / "dir.jsonl"
    d.mkdir()
    r = _reject(d, "P-00000001")
    assert r.reason == "ground_truth_unreadable"


@pytest.mark.parametrize(
    "change",
    [
        {"defect": "true"},
        {"defect": 1},
        {"defect": None},
        {"defect": ...},  # 키 없음
        {"defect_type": ...},  # 키 없음(null과 다르다)
        {"defect": False, "defect_type": "scratch"},
        {"defect": True, "defect_type": None},
        {"defect": True, "defect_type": "Scratch"},
        {"defect": True, "defect_type": "crack"},
        {"defect": True, "defect_type": ["scratch"]},
    ],
)
def test_invalid(gt_file, gt_line, change):
    line = gt_line("P-00000001", "scratch")
    for key, value in change.items():
        if value is ...:
            del line[key]
        else:
            line[key] = value
    p = gt_file.write([line])
    assert _reject(p.path, "P-00000001").reason == "ground_truth_invalid"


def test_other_fields_ignored(gt_file, gt_line):
    line = gt_line("P-00000001", "dent")
    line.update(
        bbox="not a bbox",
        fault_level=-99,
        severity="high",
        defect_probability=None,
        defect_params=[1],
        render_seed="x",
        timestamp="garbage",
        image_path="/abs/elsewhere.png",
        schema_version=7,
    )
    del line["image_size"]
    p = gt_file.write([line])
    assert lookup(p.path, "P-00000001") == Lookup(GroundTruth(True, "dent"), 0)


def test_does_not_write_under_image_root(gt_file, gt_line):
    p = gt_file.write([gt_line("P-00000001", "dent")])
    before = sorted(x.relative_to(p.image_root) for x in p.image_root.rglob("*"))
    lookup(p.path, "P-00000001")
    with pytest.raises(Rejected):
        lookup(p.path, "P-00000002")
    assert sorted(x.relative_to(p.image_root) for x in p.image_root.rglob("*")) == before
