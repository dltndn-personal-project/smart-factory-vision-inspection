# 01 메시지 처리

> 목적: Product Created 한 건을 받아 Vision Result를 만들거나 미발행 사유(`reason`)를 정하는 순수 처리 규칙을 정한다. MQTT와 로그 출력은 `02-service.md`다.
> 읽어야 할 때: `payload.py`, `ground_truth.py`, `process.py`와 그 단위 테스트(VIS-2).
> Payload 형식의 원본은 Shared `d0c997c` INTERFACES(Product Created, Vision Result, Ground Truth)다. 아래는 그것을 구현 규칙으로 옮긴 것이며 다르면 Shared를 따른다.

## 1. 모듈과 함수

모두 paho를 import하지 않는다. 파일 읽기 말고는 부작용이 없다.

| 모듈 | 공개 이름 | 하는 일 |
|---|---|---|
| `payload.py` | `ProductCreated(product_id, timestamp, image_path)`(frozen dataclass), `parse_product_created(raw: bytes) -> ProductCreated`, `build_vision_result(pc, gt) -> dict`, `encode(obj: dict) -> bytes` | 2절 검증, 4절 조립·직렬화 |
| `ground_truth.py` | `GroundTruth(defect: bool, defect_type: str \| None)`, `Lookup(gt: GroundTruth, bad_lines: int)`, `lookup(path: Path, product_id: str) -> Lookup` | 3절 조회 |
| `process.py` | `Publish`, `Drop`(frozen dataclass), `process(raw: bytes, ground_truth_path: Path) -> Publish \| Drop` | 2~4절을 순서대로 실행 |
| (공통) | `Rejected(Exception)`: `reason: str`, `detail: str`, `product_id: str \| None = None`, `timestamp: str \| None = None`, `bad_lines: int = 0` | 미발행 사유 전달. `payload.py`에 둔다 |

```python
@dataclass(frozen=True)
class Publish:
    payload: bytes            # encode(build_vision_result(...))
    product_id: str
    timestamp: str
    defect: bool
    defect_type: str | None
    bad_lines: int            # 3절에서 건너뛴 줄 수

@dataclass(frozen=True)
class Drop:
    reason: str               # 5절 표의 값
    detail: str               # 사람용 설명. 200자로 자른다. 형식은 약속이 아니다
    product_id: str | None    # 2절 4단계를 통과했을 때만
    timestamp: str | None     # 2절 5단계를 통과했을 때만
    bad_lines: int
```

- `process()`는 `Rejected`를 잡아 같은 이름의 필드로 `Drop`을 만든다. `parse_product_created`는 그때까지 통과한 값만 `Rejected`에 싣는다: 5단계(`invalid_timestamp`) 실패는 `product_id`만, 6단계(`invalid_image_path`) 실패는 `product_id`와 `timestamp`, 그 앞 단계 실패는 둘 다 None. Ground Truth 단계(3절)의 `Rejected`에는 `process()`가 잡은 예외의 `product_id`·`timestamp` 속성에 검증된 값을 넣는다. `_reject_constant`도 `payload.py`에 두고 `ground_truth.py`가 import한다.
- 그 밖의 예외는 잡지 않는다(호출자 `app.py`가 `internal_error`로 처리한다, `02-service.md` 3절).
- 설정 `IMAGE_ROOT`에서 경로를 만드는 것은 호출자다: `ground_truth_path = Path(IMAGE_ROOT) / "ground_truth" / "products.jsonl"`.

## 2. Product Created 검증

위에서부터 검사하고 처음 실패한 단계의 `reason`으로 끝낸다.

| 단계 | 검사 | 실패 `reason` |
|---|---|---|
| 1 | `raw.decode("utf-8")`(strict) 뒤 `json.loads(text, parse_constant=_reject_constant)`. `_reject_constant`는 `NaN`·`Infinity`·`-Infinity`에서 `ValueError`를 낸다(Python 기본 파서는 표준 JSON이 아닌 이 값들을 받는다). 결과가 `dict`가 아니면 실패 | `invalid_json` |
| 2 | `schema_version`이 있고 `type(v) is int and v == 1`(`True`는 int지만 거부한다) | `invalid_payload` |
| 3 | `product_id`, `timestamp`, `image_path`가 모두 있고 `str`이다(이 순서로 보고 첫 실패를 `detail`에 적는다) | `invalid_payload` |
| 4 | `re.fullmatch(r"P-[0-9]{8}", product_id)` | `invalid_product_id` |
| 5 | `re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z", timestamp)` | `invalid_timestamp` |
| 6 | `image_path == f"products/{product_id}.jpg"` | `invalid_image_path` |

- 정규식은 `[0-9]`와 `fullmatch`를 쓴다. Python `\d`는 유니코드 숫자(예: `١`)를, `$`는 끝의 `\n`을 받아들이기 때문이다(`DECISIONS.md` D-12). Shared CONVENTIONS의 `\d`·`^…$` 정규식과 ASCII 입력에서 같은 결과다.
- timestamp는 형식만 본다. 날짜 값의 유효성(13월 등)은 보지 않는다. 받은 문자열을 파싱·재포맷하지 않고 그대로 결과에 싣는다.
- 모르는 필드는 무시한다(CONVENTIONS Payload). 이미지 파일의 존재는 확인하지 않는다.

## 3. Ground Truth 조회

`lookup(path, product_id)`:

1. `path.read_bytes()`. `OSError`(없음, 권한, 디렉터리 등)면 `Rejected("ground_truth_unreadable", "<예외 클래스 이름>: <strerror>")`.
2. `data.split(b"\n")`의 마지막 조각은 `\n`으로 끝나지 않은 줄(또는 빈 조각)이므로 버린다. 나머지가 완성된 줄이다.
3. 완성된 줄마다 `line.decode("utf-8")` → `json.loads(…, parse_constant=_reject_constant)`(2절 1단계와 같은 함수). 둘 중 하나라도 실패하거나 결과가 `dict`가 아니면 그 줄을 건너뛰고 `bad_lines += 1`. 빈 줄도 여기에 든다.
4. `obj.get("product_id") == product_id`인 줄을 모은다. 비교는 문자열 동등이다.
5. 모은 줄이 0개면 `Rejected("ground_truth_missing")`, 2개 이상이면 `Rejected("ground_truth_duplicate", "<개수> lines")`.
6. 한 줄이면 `defect`, `defect_type`만 읽고 검사한다. 아래 중 하나면 `Rejected("ground_truth_invalid")`:
   - `defect` 키가 없거나 `type(defect) is not bool`
   - `defect_type` 키가 없음(null과 다르다)
   - `defect is False`인데 `defect_type is not None`
   - `defect is True`인데 `defect_type`이 `"scratch"`, `"dent"`, `"contamination"` 중 하나가 아님
7. `Lookup(GroundTruth(defect, defect_type), bad_lines)`를 돌려준다. 4~6단계의 `Rejected`에도 그때까지 센 `bad_lines`를 넣는다.

- 메시지마다 파일 전체를 처음부터 읽는다. 위치 기억·색인·캐시·대기·재시도는 없다(`DECISIONS.md` D-10).
- 그 줄의 다른 필드(`bbox`, `fault_level`, `severity`, `defect_probability`, `defect_params`, `render_seed`, `timestamp`, `image_path` 등)는 읽어도 쓰지 않고 대조 검사에도 쓰지 않는다(Shared Ground Truth 현재 범위 예외).
- 파일은 `read_bytes()`로만 연다(읽기 전용). `IMAGE_ROOT` 아래에 아무것도 만들지 않는다.

## 4. Vision Result 조립과 직렬화

`build_vision_result(pc, gt)`는 아래 키를 이 순서로 가진 새 `dict`를 돌려준다(Shared 예시와 같은 순서).

| 키 | 값 |
|---|---|
| `schema_version` | `1` |
| `product_id` | `pc.product_id` |
| `timestamp` | `pc.timestamp` |
| `defect` | `gt.defect` |
| `defect_type` | `gt.defect_type` |
| `confidence` | `None` |
| `bbox` | `None` (Ground Truth의 `bbox`를 옮기지 않는다. 조율 결정 C-16) |
| `image_path` | `pc.image_path` |
| `gradcam_path` | `None` |
| `judgement_source` | `"PASS_THROUGH"` |

`encode(obj) = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. 결과 예(한 줄):

```json
{"schema_version":1,"product_id":"P-00000113","timestamp":"2026-09-25T05:20:13.425Z","defect":true,"defect_type":"scratch","confidence":null,"bbox":null,"image_path":"products/P-00000113.jpg","gradcam_path":null,"judgement_source":"PASS_THROUGH"}
```

## 5. 미발행 `reason` 목록

`process()`가 `Drop`으로 돌려주는 값이다. 로그 형식과 서비스 수준 `reason`(`publish_failed`, `internal_error` 등)은 `02-service.md` 4절이다.

| `reason` | 조건 | 결정된 곳 |
|---|---|---|
| `invalid_json` | UTF-8 JSON 객체가 아님 | 2절 1단계 |
| `invalid_payload` | `schema_version` ≠ 1, 필수 필드 없음·타입 오류 | 2절 2·3단계 |
| `invalid_product_id` | `product_id` 형식 불일치 | 2절 4단계 |
| `invalid_timestamp` | timestamp 형식 불일치 | 2절 5단계 |
| `invalid_image_path` | `image_path`가 `products/{product_id}.jpg`가 아님 | 2절 6단계 |
| `ground_truth_unreadable` | 파일 없음·권한·읽기 오류 | 3절 1단계 |
| `ground_truth_missing` | 같은 `product_id`의 완성된 줄 없음(잘린 마지막 줄만 있는 경우 포함). `defect: false`로 채우지 않는다 | 3절 5단계 |
| `ground_truth_duplicate` | 같은 `product_id`의 완성된 줄이 둘 이상. 어느 줄도 고르지 않는다 | 3절 5단계 |
| `ground_truth_invalid` | 찾은 줄의 `defect`·`defect_type`이 6단계 조건 위반 | 3절 6단계 |

`bad_lines > 0`은 미발행 사유가 아니다. 찾던 줄을 찾으면 발행하고, 서비스가 경고 로그(`ground_truth_bad_lines`)를 따로 남긴다.
