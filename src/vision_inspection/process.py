"""Product Created 한 건의 순수 처리 순서 (docs/spec/01-processing.md 1~4절).

paho를 import하지 않는다. Rejected 말고 다른 예외는 잡지 않는다(호출자가 internal_error로 처리한다).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ground_truth import lookup
from .payload import Rejected, build_vision_result, encode, parse_product_created

DETAIL_MAX = 200


@dataclass(frozen=True)
class Publish:
    payload: bytes
    product_id: str
    timestamp: str
    defect: bool
    defect_type: str | None
    bad_lines: int


@dataclass(frozen=True)
class Drop:
    reason: str
    detail: str
    product_id: str | None
    timestamp: str | None
    bad_lines: int


def process(raw: bytes, ground_truth_path: Path) -> Publish | Drop:
    pc = None
    try:
        pc = parse_product_created(raw)
        found = lookup(ground_truth_path, pc.product_id)
    except Rejected as r:
        if pc is not None:  # Ground Truth 단계: 검증을 통과한 값을 싣는다
            r.product_id, r.timestamp = pc.product_id, pc.timestamp
        return Drop(r.reason, r.detail[:DETAIL_MAX], r.product_id, r.timestamp, r.bad_lines)
    gt = found.gt
    return Publish(
        payload=encode(build_vision_result(pc, gt)),
        product_id=pc.product_id,
        timestamp=pc.timestamp,
        defect=gt.defect,
        defect_type=gt.defect_type,
        bad_lines=found.bad_lines,
    )
