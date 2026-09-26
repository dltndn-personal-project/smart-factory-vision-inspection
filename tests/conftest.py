"""공용 fixture (docs/spec/04-verification.md 2절).

VIS-2가 shared_examples, gt_file, make_pc, gt_line을 더했다. broker, service, results 등 Docker fixture는
VIS-3이 더한다.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

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

    def make(product_id: str, **override: Any) -> bytes:
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
