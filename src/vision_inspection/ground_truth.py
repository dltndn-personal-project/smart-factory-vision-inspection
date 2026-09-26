"""Ground Truth 조회 (docs/spec/01-processing.md 3절, DECISIONS D-10, D-11).

메시지마다 파일 전체를 read_bytes()로 읽는다. 위치 기억·색인·캐시·대기·재시도는 없다. paho를 import하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .payload import Rejected, loads_strict

DEFECT_TYPES = ("scratch", "dent", "contamination")


@dataclass(frozen=True)
class GroundTruth:
    defect: bool
    defect_type: str | None


@dataclass(frozen=True)
class Lookup:
    gt: GroundTruth
    bad_lines: int


def lookup(path: Path, product_id: str) -> Lookup:
    # 1. 읽기 전용으로 전체 읽기
    try:
        data = path.read_bytes()
    except OSError as e:
        raise Rejected("ground_truth_unreadable", f"{type(e).__name__}: {e.strerror or e}") from None

    # 2. 마지막 조각(\n으로 끝나지 않은 줄 또는 빈 조각)은 버린다
    complete = data.split(b"\n")[:-1]

    # 3~4. 깨진 줄은 세고 건너뛰며, 같은 product_id의 줄을 모은다
    bad_lines = 0
    matches: list[dict] = []
    for line in complete:
        try:
            obj = loads_strict(line)
        except (ValueError, RecursionError):
            bad_lines += 1
            continue
        if not isinstance(obj, dict):
            bad_lines += 1
            continue
        if obj.get("product_id") == product_id:
            matches.append(obj)

    # 5. 정확히 한 줄
    if not matches:
        raise Rejected("ground_truth_missing", f"no complete line for {product_id}", bad_lines=bad_lines)
    if len(matches) > 1:
        raise Rejected("ground_truth_duplicate", f"{len(matches)} lines", bad_lines=bad_lines)

    # 6. defect, defect_type만 검사한다
    line = matches[0]
    if "defect" not in line or type(line["defect"]) is not bool:
        raise Rejected("ground_truth_invalid", "defect missing or not a boolean", bad_lines=bad_lines)
    if "defect_type" not in line:
        raise Rejected("ground_truth_invalid", "defect_type missing", bad_lines=bad_lines)
    defect: bool = line["defect"]
    defect_type = line["defect_type"]
    if defect is False and defect_type is not None:
        raise Rejected("ground_truth_invalid", f"defect false with defect_type {defect_type!r}", bad_lines=bad_lines)
    if defect is True and defect_type not in DEFECT_TYPES:
        raise Rejected("ground_truth_invalid", f"defect true with defect_type {defect_type!r}", bad_lines=bad_lines)

    # 7.
    return Lookup(GroundTruth(defect, defect_type), bad_lines)
