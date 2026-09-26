# 01 메시지 처리 계획 (M2 VIS-2)

> 목적: VIS-2(Product Created 검증, Ground Truth 조회, Vision Result 조립, 순수 처리 순서)의 PLAN 정의와 단계 개요.
> 읽어야 할 때: VIS-2를 실행하거나 등록할 때. 같이 읽을 spec: `docs/spec/01-processing.md`, `04-verification.md` 2·3.1절.

## 1. 요약

| task | 선행 | size | 내용 |
|---|---|---|---|
| VIS-2 | VIS-1 | M | `payload.py`, `ground_truth.py`, `process.py`, `tests/fixtures/shared_d0c997c/`, `conftest.py`의 `shared_examples`·`gt_file`·`make_pc`·`gt_line`, `test_payload.py`, `test_ground_truth.py`, `test_process.py` |

- fixture 세 파일은 `contract_ref`(`d0c997c`) INTERFACES의 예시를 그대로 옮긴다(`90-shared.md` 1절 명령으로 읽는다). 이후 바꾸지 않는다. 호환성 확인의 기준이다.
- 이 task의 모듈은 paho를 import하지 않는다(spec 01 1절). 파일 읽기 말고는 부작용이 없다.
- 새 verify 명령은 없다. `unit`(`make test`)이 이 task의 테스트를 함께 돈다.

## 2. task

### VIS-2 처리 코어

```yaml
  - id: VIS-2
    milestone: M2
    type: feature
    title: Product Created 검증, Ground Truth 조회, Vision Result 조립(payload, ground_truth, process)
    why: pass-through 처리 규칙 전체를 Broker 없이 확정하고, Shared 예시와 같은 결과(키 순서 포함)와 미발행 reason 9개를 단위 테스트로 고정한다 (spec 01, D-10, D-11, D-12, D-21, C-02, C-03, C-07)
    depends_on: [VIS-1]
    contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]
    scope: [src/**, tests/**, docs/spec/01-processing.md, docs/spec/DECISIONS.md]
    acceptance:
      - id: A1
        text: tests/fixtures/shared_d0c997c/에 Shared 예시 세 파일이 있고, vision_result.json은 spec 01 4절의 10개 키를 그 순서로 가지며(judgement_source PASS_THROUGH, bbox null), ground_truth.jsonl은 \n으로 끝나는 한 줄이다 (C-02)
        check: {type: command, run: "d=tests/fixtures/shared_d0c997c && test -f $d/product_created.json && test \"$(wc -l < $d/ground_truth.jsonl)\" -eq 1 && test \"$(tail -c 1 $d/ground_truth.jsonl | od -An -c | tr -d ' ')\" = '\\n' && python3 -c \"import json, sys; d = json.load(open('tests/fixtures/shared_d0c997c/vision_result.json')); sys.exit(not (list(d) == ['schema_version', 'product_id', 'timestamp', 'defect', 'defect_type', 'confidence', 'bbox', 'image_path', 'gradcam_path', 'judgement_source'] and d['judgement_source'] == 'PASS_THROUGH' and d['bbox'] is None and d['schema_version'] == 1))\""}
      - id: A2
        text: Shared 예시 Product Created와 Ground Truth 줄로 만든 결과가 예시 Vision Result와 같은 dict이고 encode의 키 순서도 같으며, Ground Truth의 다른 필드가 결과에 없다 (C-02)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_payload.py::test_shared_example_parses tests/test_payload.py::test_build_matches_shared_example tests/test_payload.py::test_encoded_key_order_matches_shared_example tests/test_payload.py::test_no_other_ground_truth_fields"}
      - id: A3
        text: Product Created 검증이 spec 01 2절 순서대로 invalid_json(UTF-8 아님, 배열, NaN 포함)·invalid_payload(schema_version true 등)·invalid_product_id(유니코드 숫자, 끝 \n)·invalid_timestamp·invalid_image_path를 내고 모르는 필드를 무시한다 (C-03)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_payload.py::test_unknown_fields_ignored tests/test_payload.py::test_invalid_json tests/test_payload.py::test_invalid_payload tests/test_payload.py::test_invalid_product_id tests/test_payload.py::test_invalid_timestamp tests/test_payload.py::test_invalid_image_path"}
      - id: A4
        text: Ground Truth 조회가 잘린 마지막 줄·빈 파일을 missing으로, 중복을 duplicate로, 깨진 줄을 건너뛰고 세며, 읽기 실패를 unreadable로, defect·defect_type 위반을 invalid로 보고 다른 필드는 보지 않는다 (spec 01 3절, C-03)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_ground_truth.py::test_shared_example_line_found tests/test_ground_truth.py::test_incomplete_last_line_ignored tests/test_ground_truth.py::test_empty_file_is_missing tests/test_ground_truth.py::test_duplicate tests/test_ground_truth.py::test_bad_lines_skipped_and_counted tests/test_ground_truth.py::test_unreadable tests/test_ground_truth.py::test_invalid tests/test_ground_truth.py::test_other_fields_ignored"}
      - id: A5
        text: process()가 정상 입력에 Publish를, spec 01 5절의 reason 9개 각각에 Drop을 돌려주고, Drop의 product_id·timestamp는 검증을 통과한 값만 싣고, bad_lines를 Publish에도 싣는다 (C-03)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_process.py::test_publish_outcome tests/test_process.py::test_each_reason tests/test_process.py::test_drop_carries_ids_only_when_valid tests/test_process.py::test_bad_lines_reported_on_publish"}
      - id: A6
        text: 1,800줄 Ground Truth에서 process() 한 번이 평균 50 ms 이하이고 측정값을 출력한다 (C-07 단위, D-21)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q -s tests/test_process.py::test_mean_time_1800_lines"}
      - id: A7
        text: payload·ground_truth·process 모듈이 paho를 import하지 않는다 (spec 01 1절)
        check: {type: command, run: "for f in payload ground_truth process; do test -f src/vision_inspection/$f.py || exit 1; done && ! grep -Eq '^[[:space:]]*(import|from)[[:space:]]+paho' src/vision_inspection/payload.py src/vision_inspection/ground_truth.py src/vision_inspection/process.py"}
      - id: A8
        text: 단위 테스트 전체가 통과한다
        check: {type: command, run: "make test"}
    size: M
```

단계 개요:
1. `90-shared.md` 1절로 `d0c997c` INTERFACES를 읽고 Product Created, Vision Result, Ground Truth 예시를 fixture 세 파일로 옮긴다. → A1
2. `conftest.py`: `shared_examples`, `gt_file`, `make_pc`, `gt_line`(spec 04 2절 표).
3. `payload.py`: `Rejected`, `_reject_constant`, `ProductCreated`, `parse_product_created`(2절 6단계), `build_vision_result`, `encode`. `test_payload.py`. → A2, A3
4. `ground_truth.py`: `GroundTruth`, `Lookup`, `lookup`(3절 1~7단계). `test_ground_truth.py`. → A4
5. `process.py`: `Publish`, `Drop`, `process`(`Rejected` → `Drop`, 실을 id 규칙). `test_process.py`와 1,800줄 시간 측정. → A5, A6
6. paho import 검사와 `make test`. → A7, A8

읽을 spec: 01 전체, 04 2·3.1절(`test_payload`, `test_ground_truth`, `test_process`), D-10, D-11, D-12, D-21. 계약: `contract_ref`의 INTERFACES Product Created·Vision Result·Ground Truth, CONVENTIONS Timestamp·ID·Payload.

- C-07 상한을 넘으면 기준을 늦추지 않는다. 원인(파일 캐시, 측정 방법)을 먼저 보고 PR에 적는다(spec 04 5절). 계속 실패하면 멈춘다(repeated-failure).
