"""Product Created 검증, Vision Result 조립·직렬화 (docs/spec/01-processing.md 2·4절).

paho를 import하지 않는다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

JUDGEMENT_SOURCE = "PASS_THROUGH"

_PRODUCT_ID_RE = re.compile(r"P-[0-9]{8}")
_TIMESTAMP_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z")
_REQUIRED = ("product_id", "timestamp", "image_path")


class Rejected(Exception):
    """미발행 사유. reason은 01-processing.md 5절 값이다."""

    def __init__(
        self,
        reason: str,
        detail: str = "",
        product_id: str | None = None,
        timestamp: str | None = None,
        bad_lines: int = 0,
    ) -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail
        self.product_id = product_id
        self.timestamp = timestamp
        self.bad_lines = bad_lines


def _reject_constant(name: str) -> Any:
    """json.loads parse_constant: 표준 JSON이 아닌 NaN, Infinity, -Infinity를 거부한다."""
    raise ValueError(f"non-standard JSON constant {name}")


def loads_strict(raw: bytes) -> Any:
    """UTF-8(strict) 디코드 뒤 NaN·Infinity를 거부하는 json.loads. 실패하면 ValueError(UnicodeDecodeError 포함)."""
    return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)


@dataclass(frozen=True)
class ProductCreated:
    product_id: str
    timestamp: str
    image_path: str


def parse_product_created(raw: bytes) -> ProductCreated:
    """2절 순서로 검사하고 처음 실패한 단계의 Rejected를 낸다."""
    # 1. UTF-8 JSON 객체
    try:
        obj = loads_strict(raw)
    except ValueError as e:  # UnicodeDecodeError, JSONDecodeError는 ValueError의 하위 클래스
        raise Rejected("invalid_json", f"{type(e).__name__}: {e}") from None
    if not isinstance(obj, dict):
        raise Rejected("invalid_json", f"top-level value is {type(obj).__name__}, not an object")

    # 2. schema_version == 1 (bool 거부)
    if "schema_version" not in obj:
        raise Rejected("invalid_payload", "schema_version missing")
    version = obj["schema_version"]
    if not (type(version) is int and version == 1):
        raise Rejected("invalid_payload", f"schema_version must be 1, got {version!r}")

    # 3. 필수 필드가 있고 str
    for key in _REQUIRED:
        if key not in obj:
            raise Rejected("invalid_payload", f"{key} missing")
        if not isinstance(obj[key], str):
            raise Rejected("invalid_payload", f"{key} must be a string, got {type(obj[key]).__name__}")
    product_id: str = obj["product_id"]
    timestamp: str = obj["timestamp"]
    image_path: str = obj["image_path"]

    # 4. product_id
    if not _PRODUCT_ID_RE.fullmatch(product_id):
        raise Rejected("invalid_product_id", f"product_id {product_id!r} does not match P-[0-9]{{8}}")

    # 5. timestamp (형식만)
    if not _TIMESTAMP_RE.fullmatch(timestamp):
        raise Rejected(
            "invalid_timestamp",
            f"timestamp {timestamp!r} is not UTC ISO 8601 with 3-digit milliseconds and Z",
            product_id=product_id,
        )

    # 6. image_path
    expected = f"products/{product_id}.jpg"
    if image_path != expected:
        raise Rejected(
            "invalid_image_path",
            f"image_path {image_path!r} is not {expected!r}",
            product_id=product_id,
            timestamp=timestamp,
        )

    return ProductCreated(product_id=product_id, timestamp=timestamp, image_path=image_path)


def build_vision_result(pc: ProductCreated, gt: Any) -> dict[str, Any]:
    """4절 키 순서(Shared 예시와 같음)의 새 dict. gt는 defect, defect_type 속성을 가진다(ground_truth.GroundTruth)."""
    return {
        "schema_version": 1,
        "product_id": pc.product_id,
        "timestamp": pc.timestamp,
        "defect": gt.defect,
        "defect_type": gt.defect_type,
        "confidence": None,
        "bbox": None,
        "image_path": pc.image_path,
        "gradcam_path": None,
        "judgement_source": JUDGEMENT_SOURCE,
    }


def encode(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
