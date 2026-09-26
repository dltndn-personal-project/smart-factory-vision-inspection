# 04 검증

> 목적: 테스트 전략과 테스트 목록, `agent/config.yaml` `verify`에 넣을 명령과 시점, 과제 성능 기준의 처리, 사람 확인 목록을 정한다.
> 읽어야 할 때: 모든 구현 task의 acceptance를 정할 때, verify를 추가할 때.

## 1. 원칙

- task acceptance는 `command`·`artifact`·`metric`만 쓴다(`DECISIONS.md` D-03). 이 Component에는 사람 확인 항목이 없다(6절).
- 처리 규칙(`01-processing.md`)은 Broker 없이 단위 테스트로 모두 확인한다. MQTT 동작(`02-service.md`)은 실제 Mosquitto로, 컨테이너 정의(`03-runtime.md` 5·6절)는 compose smoke로 확인한다.
- 서비스는 테스트 안에서도 실제 진입점(`python -m vision_inspection` 하위 프로세스)으로 띄운다. 로그를 stdout에서 읽어 확인한다.
- 시간을 기다리는 곳은 "사건이 올 때까지 최대 N초"로 쓴다. 고정 sleep으로 통과를 기다리지 않는다. 미발행 확인은 뒤에 보낸 정상 메시지(sentinel)의 결과가 온 뒤 0.5초 더 기다려 본다(처리와 발행이 수신 순서대로이므로).
- Docker를 쓸 수 없으면 `docker`·`smoke` 테스트는 **실패**한다. 건너뛰어 통과로 만들지 않는다.

## 2. 도구와 공용 fixture

- 도구: `03-runtime.md` 3·4절(venv, pytest 9.1.1, `Makefile`).
- `tests/fixtures/shared_d0c997c/`: Shared `d0c997c` INTERFACES의 예시를 그대로 옮긴 `product_created.json`, `vision_result.json`, `ground_truth.jsonl`(예시 한 줄 + `\n`). 호환성 확인의 기준이다(`docs/ARCHITECTURE.md` 4.5절). 바꾸지 않는다.
- `tests/conftest.py`:

| fixture | 내용 |
|---|---|
| `shared_examples` | 위 세 파일을 읽은 dict와 bytes |
| `gt_file(tmp_path)` | `write(lines, tail=None)`: `tmp_path/ground_truth/products.jsonl`에 dict는 `encode`한 줄, str은 그대로 줄로 쓰고 각 줄 끝에 `\n`. `tail`은 `\n` 없이 덧붙인다. 경로(`image_root`, `path`)를 돌려준다 |
| `make_pc(product_id, **override)` | Product Created bytes. 기본 timestamp `2026-09-25T05:20:13.425Z`, `image_path`는 `products/{product_id}.jpg`. `override`에 `None`을 주면 그 키를 뺀다 |
| `gt_line(product_id, defect_type)` | Shared 예시 줄을 복사해 `product_id`·`timestamp`·`image_path`·`defect`·`defect_type`·`bbox`만 바꾼 dict(`defect_type`이 None이면 양품) |
| `broker` (docker) | `docker run -d --rm -p 127.0.0.1::1883 eclipse-mosquitto:2.1.2-alpine mosquitto -c /mosquitto-no-auth.conf`, `docker port`로 포트 확인, paho probe가 CONNACK을 받을 때까지 최대 15초, 끝나면 `docker rm -f`. factory-simulator `server/tests/conftest.py`의 `_broker`와 같은 방식 |
| `fixed_port_broker` (docker) | 같되 미리 고른 빈 포트에 묶는다(재시작해도 포트가 유지되게). 시작 전 포트만 돌려주는 `start()`를 따로 둔다 |
| `service(env)` (docker) | `subprocess.Popen([sys.executable, "-m", "vision_inspection"], env=…, stdout=PIPE)`. env는 `PYTHONPATH=src`, `MQTT_URL`, `IMAGE_ROOT=tmp`, `HEALTH_FILE=tmp/health`와 `MQTT_CLIENT_ID=vis-test-<uuid8>`. 읽기 스레드가 줄을 모은다. `wait_for(event, pred=None, timeout)`, `stop(sig=SIGTERM, timeout=5) -> int`. 입력을 보내는 테스트는 먼저 `wait_for("connected")`(SUBACK 뒤 로그, `02-service.md` 1절)를 기다린다. 종료 때 모든 stdout 줄에 4절 로그 검사를 한다(C-06) |
| `results(broker)` (docker) | `factory/vision/result`를 QoS 1로 구독한 paho client. fixture는 `on_subscribe`로 SUBACK을 받은 뒤에(최대 5초) 돌려준다. `(dict, qos, retain, 도착 monotonic)`을 queue에 모은다 |

## 3. 테스트 목록

### 3.1 단위 (`make test`. `test_config`·`test_logs`는 VIS-1, `test_payload`·`test_ground_truth`·`test_process`는 VIS-2, `test_main`은 VIS-3이 만든다)

| 파일 | 테스트 | 확인 |
|---|---|---|
| `test_config.py` | `test_defaults`, `test_env_overrides`, `test_invalid_mqtt_url`(매개변수: `http://h`, `mqtt://`, `mqtt://h:0`, `mqtt://h:65536`, `mqtt://h:1883/`, `mqtt://u@h`), `test_empty_value_is_error`, `test_invalid_topic`(`factory/+/x`, `#`, `Factory/x`, `a//b`, 공백), `test_same_topics_rejected`, `test_log_level_case_insensitive`, `test_missing_image_root_is_not_error` | `03-runtime.md` 2절 |
| `test_logs.py` | `test_iso_ms_truncates`(…`.999999` → `.999Z`), `test_record_is_one_json_line_with_leading_keys`, `test_level_filter`, `test_non_ascii_kept` | `02-service.md` 4절 |
| `test_payload.py` | `test_shared_example_parses`, `test_unknown_fields_ignored`, `test_invalid_json`(UTF-8 아님, JSON 아님, 배열, `NaN` 값), `test_invalid_payload`(`schema_version` 없음·2·`true`·`"1"`, 필수 필드 없음·int), `test_invalid_product_id`(`P-1`, `p-00000001`, 아랍 숫자, 끝 `\n`), `test_invalid_timestamp`(밀리초 없음·2자리, `+00:00`, 끝 `\n`), `test_invalid_image_path`(절대 경로, `products/.P-….jpg.tmp`, 다른 id, `../`), `test_build_matches_shared_example`, `test_encoded_key_order_matches_shared_example`, `test_no_other_ground_truth_fields` | C-02, `01-processing.md` 2·4절 |
| `test_ground_truth.py` | `test_shared_example_line_found`, `test_incomplete_last_line_ignored`(찾는 줄이 잘린 끝에만 있으면 missing), `test_empty_file_is_missing`, `test_duplicate`, `test_bad_lines_skipped_and_counted`(깨진 JSON, 배열 줄, 빈 줄, UTF-8 아닌 줄, `Infinity` 값), `test_unreadable`(파일 없음, 디렉터리), `test_invalid`(`defect: "true"`, `defect_type` 키 없음, false+`scratch`, true+null, true+`Scratch`), `test_other_fields_ignored`(`bbox`·`fault_level`이 이상해도 통과) | `01-processing.md` 3절 |
| `test_process.py` | `test_publish_outcome`, `test_each_reason`(`01-processing.md` 5절 9개 전부), `test_drop_carries_ids_only_when_valid`(`invalid_product_id`는 둘 다 None, `invalid_timestamp`는 `product_id`만, `invalid_image_path`와 Ground Truth 오류는 둘 다), `test_bad_lines_reported_on_publish`, `test_mean_time_1800_lines` | C-03, C-07 |
| `test_main.py` | `test_invalid_config_exits_2`(`MQTT_URL=http://h`로 하위 프로세스, 10초 안에 종료 코드 2, 마지막 줄 `error`·`invalid_config`) | C-05 일부 |

- `test_mean_time_1800_lines`: `gt_line`으로 1,800줄(`P-00000001`~`P-00001800`)을 쓰고, 마지막 제품의 Product Created로 `process()`를 한 번 데운 뒤 20번 불러 평균을 잰다(`time.perf_counter`). 기준은 C-07. 측정값을 출력한다.

### 3.2 Docker 연동 (`make docker-test`, VIS-3, `test_broker.py`, `@pytest.mark.docker`)

| 테스트 | 절차와 통과 기준 |
|---|---|
| `test_publishes_shared_example` | Shared 예시 Ground Truth 줄을 쓰고 서비스가 `connected`를 남긴 뒤 예시 Product Created를 QoS 1로 발행 → 5초 안에 결과 하나. dict가 Shared 예시 Vision Result와 같고 `qos == 1`, `retain is False`. 로그에 `received`, `published`(`latency_ms` int ≥ 0) (C-04) |
| `test_invalid_inputs_not_published` | 이 순서로 발행: `invalid_json`, `schema_version` 2, 잘못된 `product_id`, 잘못된 timestamp, 잘못된 `image_path`, 줄 없음, 중복 줄, 모순 줄, 정상 sentinel → 결과는 sentinel 하나뿐. `dropped` 로그의 `reason`이 앞 8개와 같은 순서 (C-03, C-04) |
| `test_ground_truth_created_later` | 파일 없이 발행 → `ground_truth_unreadable`. 파일을 만든 뒤 다른 제품 발행 → 결과 수신(상태를 기억하지 않음) |
| `test_broker_restart_resubscribes` | `fixed_port_broker`. `connected` 뒤 `docker restart` → `disconnected`, 다시 `connected`가 restart 명령이 끝난 뒤 15초 안. 기동 확인 파일이 다시 있음. 새 Product Created → 결과 수신 (C-05) |
| `test_starts_before_broker` | 비어 있는 포트로 서비스 시작 → 2초 뒤 기동 확인 파일 없음, `connect_failed` 1회 이상. 그 포트로 broker 시작 → 15초 안에 `connected`, 결과 수신 (C-05) |
| `test_sigterm_exits_0` | `connected` 뒤 SIGTERM → 5초 안에 종료 코드 0, 마지막 줄 `stopped`(`signal: "SIGTERM"`), 기동 확인 파일 없음 (C-05) |
| `test_latency_1800_lines` | 1,800줄 파일. 마지막 30개 제품의 Product Created를 0.1초 간격으로 발행 → 30개 모두 수신. 각 결과의 지연(자기 Product Created 발행 호출 → 도착)이 모두 2초 이하이고 중앙값이 0.5초 이하. 측정값(중앙값, 최대)을 출력한다 (C-07) |

- 모든 테스트의 `service` 정리 단계에서 로그 검사(C-06): 모든 줄이 JSON 객체, 첫 세 키가 `ts`·`level`·`event`, `ts`가 CONVENTIONS 정규식, `event`와 `reason`이 `02-service.md` 4절 값 안.

### 3.3 smoke (`make smoke`, VIS-4, `test_smoke.py::test_compose_smoke`, `@pytest.mark.smoke`)

저장소 루트에서, 프로젝트 이름 `vis-smoke`, `VIS_MQTT_PORT`는 테스트가 고른 빈 포트:

1. 남은 자원 정리: `docker compose -p vis-smoke down -v --remove-orphans`.
2. `docker compose -p vis-smoke up -d --build --wait --wait-timeout 60` → 종료 코드 0(서비스가 healthy, C-08). 빌드 시간은 출력만 한다.
3. `docker inspect`로 `vision-inspection` 컨테이너의 `/data` 마운트가 `RW=false`.
4. `docker run --rm -i -v vis-smoke_image-storage:/data eclipse-mosquitto:2.1.2-alpine sh -c 'mkdir -p /data/ground_truth && cat >> /data/ground_truth/products.jsonl'`에 세 줄을 넣는다: `P-00000001` 불량(`dent`), `P-00000002` 양품, 끝에 `\n` 없는 `P-00000003`.
5. 호스트 paho로 `127.0.0.1:<VIS_MQTT_PORT>`에 `factory/vision/result`를 구독해 SUBACK을 받은 뒤(최대 5초) Product Created `P-00000001`, `P-00000002`, `P-00000003`, 잘못된 JSON을 발행한다.
6. 10초 안에 `P-00000001`(`defect: true`, `defect_type: "dent"`)과 `P-00000002`(`defect: false`, `defect_type: null`) 결과가 오고, 둘 다 4절 형식(나머지 키 null, `PASS_THROUGH`)이다. 그 뒤 1초 동안 다른 결과가 없다.
7. `docker compose -p vis-smoke logs --no-log-prefix vision-inspection`의 모든 줄이 JSON이고 `started`, `connected`, `published` 2개, `dropped`(`ground_truth_missing`, `invalid_json`)가 있다.
8. `docker compose -p vis-smoke stop -t 10 vision-inspection` → 컨테이너 종료 코드 0(`docker inspect -f '{{.State.ExitCode}}'`), 로그 마지막 줄 `stopped`.
9. 성공·실패와 무관하게 `docker compose -p vis-smoke down -v --remove-orphans`. 실패하면 compose 로그 마지막 100줄을 출력한다.

## 4. verify 명령과 추가 시점

각 영역을 처음 만드는 task가 `agent/config.yaml`의 `verify`에 아래 명령을 그대로 추가한다(`DECISIONS.md` D-04). 먼저 실제로 실행해 통과를 확인한다.

| 순서 | 추가하는 task | 항목 |
|---|---|---|
| 1 | BOOT-1 (plan PR) | `{name: agent-files, run: "python3 agent/core/tools/validate.py"}` (2026-09-27 이 맥에서 통과 확인) |
| 2 | VIS-1 | `{name: unit, run: "make test"}` |
| 3 | VIS-3 | `{name: broker, run: "make docker-test"}` |
| 4 | VIS-4 | `{name: smoke, run: "make smoke"}` |

- 전제: Docker Desktop이 실행 중이고 `eclipse-mosquitto:2.1.2-alpine`, `python:3.12-slim-bookworm`을 받을 수 있다(`HUMAN.md` H-1). 2026-09-27 확인한 도구: Python 3.12.13, Docker 28.3.0, Docker Compose v2.38.1, GNU Make 3.81, `eclipse-mosquitto:2.1.2-alpine` 로컬에 있음.
- 예상 시간: unit 수 초, broker 약 1분(broker 재시작·재연결 대기 포함), smoke 첫 실행은 이미지 빌드로 1~2분, 이후 약 20초. 모두 `check_timeout` 1800초 안이다.
- GitHub CI(`Validate Component`)는 agent 파일 검사만 돌린다. 위 명령은 `agent.py verify`가 로컬에서 돌린다.

## 5. 과제 성능 기준

| Shared ARCHITECTURE 2절 기준 | 이 Component |
|---|---|
| Vision Model mAP@0.5 ≥ 0.80 | 현재 범위 제외(Shared 2절, 4.3절 현재 범위, 19.1절). 측정하지 않는다 |
| Vision Inference 20 FPS | 현재 범위 제외. 측정하지 않는다 |
| PdM F1, PdM Inference 100 ms | 해당 없음(predictive-maintenance) |
| Dashboard 5초 이내 갱신 | 측정은 integration(19.1절). 이 Component의 몫(Product Created 수신 → Vision Result PUBACK)은 `published.latency_ms`로 로그에 남고, 자체 상한을 C-07로 검사한다 |

C-07의 상한은 Shared 기준이 아니라 이 Component의 자체 확인이다(`DECISIONS.md` D-21). 수치의 원본은 `00-overview.md` C-07, 측정 방법은 3.1절 `test_mean_time_1800_lines`, 3.2절 `test_latency_1800_lines`다. 상한은 이 맥의 측정값보다 크게 여유를 두었다(1,800줄 파싱 약 6 ms, D-21). 실패하면 기준을 늦추지 말고 원인(파일 캐시, Docker 부하)을 먼저 확인해 PR에 적는다.

## 6. 사람 확인 목록

없다. 화면이 없고, 관찰할 수 있는 결과(발행 Payload, 로그, 종료 코드, 마운트, healthcheck)를 모두 위 자동 테스트가 본다. 시스템 시연에서의 모습은 integration과 factory-operations의 사람 확인에 포함된다(`DECISIONS.md` D-20).

## 7. PLAN 반영 규칙

- 완료 정의(C-02~C-08)의 acceptance는 pytest node id로 적는다. 예: `make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_payload.py::test_build_matches_shared_example`. node id가 없으면 pytest가 실패하므로 테스트가 있어야 통과한다. 테스트 이름을 바꾸는 것은 acceptance 변경이다.
- C-01은 SHARED-5, C-09는 BOOT-1과 VIS-4의 acceptance로 확인한다.
- PR merge는 조율 agent가 CI 통과와 `finish` 통과 뒤에 한다(`DECISIONS.md` D-01).
