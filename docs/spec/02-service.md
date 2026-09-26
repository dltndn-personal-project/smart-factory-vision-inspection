# 02 서비스 (MQTT, 로그, 수명 주기)

> 목적: MQTT 연결·구독·발행, 메시지 처리 순서, 한 줄 JSON 로그, 기동 확인 파일, 종료와 종료 코드를 정한다.
> 읽어야 할 때: `app.py`, `logs.py`, `__main__.py`와 Docker 연동 테스트(VIS-1 로그, VIS-3). 설정 키는 `03-runtime.md` 2절, 처리 규칙은 `01-processing.md`.

## 1. MQTT client

- 라이브러리: paho-mqtt 2.1.0(`DECISIONS.md` D-06, D-08). paho를 import하는 모듈은 `app.py` 하나다.
- 생성: `mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID, protocol=MQTTv311, clean_session=True)`. 인증·TLS·LWT 없음.
- 기동 순서: 콜백 등록 → `reconnect_delay_set(min_delay=1, max_delay=10)` → `connect_async(host, port, keepalive=30)` → `loop_forever(retry_first_connection=True)`(주 스레드에서 막힌다).
- 모든 콜백과 메시지 처리는 주 스레드(paho 루프) 하나에서 순서대로 실행된다. 별도 스레드·asyncio·작업 큐는 없다. 제품은 2초에 1개이고 처리는 수 ms라 충분하다(`DECISIONS.md` D-08).
- 2026-09-27 이 맥에서 paho 2.1.0과 `eclipse-mosquitto:2.1.2-alpine`으로 확인한 동작: `subscribe()`가 `(MQTT_ERR_SUCCESS, mid)`를 돌려주고 `on_subscribe`가 `[Granted QoS 1]`로 불린다. `on_message` 안의 `publish()`가 즉시 rc 0을 돌려주고 PUBACK 뒤 `on_publish`가 불린다. Broker 재시작 뒤 자동 재연결되어 `on_connect`의 재구독으로 수신이 이어진다. Broker 없이 시작해도 `retry_first_connection=True`로 재시도한다. 신호 처리기에서 `disconnect()`를 부르면 `loop_forever`가 돌아온다.

| 콜백 | 하는 일 |
|---|---|
| `on_connect`(성공) | `rc, mid = subscribe(PRODUCT_CREATED_TOPIC, qos=1)`. rc가 `MQTT_ERR_SUCCESS`면 `sub_mid = mid`로 기억하고 SUBACK을 기다린다. 아니면 `connect_failed` 로그(`detail`: rc 이름). 이때는 연결이 끊긴 것이므로 `on_disconnect`와 paho 재연결이 뒤따른다 |
| `on_subscribe(client, userdata, mid, reason_code_list, properties)` | `mid == sub_mid`이고 `reason_code_list[0].is_failure`가 아니면(Granted QoS) 기동 확인 파일 생성(5절) → `connected` 로그. 실패 코드면 파일을 만들지 않고 `connect_failed` 로그(`detail: "subscribe refused"`). 다른 mid는 무시 |
| `on_connect`(실패 reason code) | 기동 확인 파일 삭제 → `connect_failed` 로그. paho가 재시도한다 |
| `on_connect_fail`(TCP 연결 실패) | 같음 |
| `on_disconnect` | 기동 확인 파일 삭제 → `disconnected` 로그(종료 중이면 INFO) |
| `on_message` | 2절 |
| `on_publish` | 3절 |

- 콜백 본문은 모두 `try/except Exception`으로 감싼다. 잡은 예외는 로그로 남기고 루프를 계속 돈다(paho는 콜백 예외를 루프 밖으로 올려 `loop_forever`를 끝내기 때문이다). `on_message`에서 잡으면 `dropped`·`internal_error`, 다른 콜백에서 잡으면 `error`·`internal_error`.
- `retain` 플래그가 붙은 Product Created도 똑같이 처리한다(계약상 retain false. 중복 결과는 계약이 허용한다, `DECISIONS.md` D-13).

## 2. 메시지 하나의 처리

`on_message(client, userdata, msg)`:

1. `t0 = time.monotonic()`. `received` 로그(`topic`, `bytes`).
2. `outcome = process(bytes(msg.payload), ground_truth_path)`(`01-processing.md`).
3. `outcome.bad_lines > 0`이면 `warning` 로그(`reason: ground_truth_bad_lines`, `count`, 알면 `product_id`).
4. `Drop`이면 `dropped` 로그(`reason`, `detail`, 알면 `product_id`·`timestamp`)로 끝난다.
5. `Publish`면 `info = client.publish(VISION_RESULT_TOPIC, outcome.payload, qos=1, retain=False)`.
   - `info.rc`가 `MQTT_ERR_SUCCESS` 또는 `MQTT_ERR_NO_CONN`이면 `pending[info.mid] = (product_id, timestamp, defect, defect_type, t0)`. NO_CONN이면 paho가 메모리에 두었다가 재연결 뒤 보낸다(`DECISIONS.md` D-13). 이 Component는 따로 재발행하지 않는다.
   - 그 밖의 rc면 `dropped`(`reason: publish_failed`, `detail`: rc 이름)로 끝난다.

## 3. 발행 완료

`on_publish(client, userdata, mid, reason_code, properties)`: `pending.pop(mid)`이 있으면 `published` 로그(`product_id`, `timestamp`, `defect`, `defect_type`, `latency_ms = int((time.monotonic() - t0) * 1000)`). 없으면 무시한다.

- 정상 연결에서 받은 메시지마다 `dropped` 또는 `published` 중 하나가 정확히 한 번 나온다. PUBACK 전에 연결이 끊기면 `published`가 늦게 나오거나(재연결 뒤 재전송) 나오지 않을 수 있다(프로세스 종료). 이것은 받아들인다(Shared ARCHITECTURE 12절).
- 같은 Product Created를 두 번 받으면 결과도 두 번 발행한다. 중복을 막지 않는다.

## 4. 로그

stdout에 한 줄에 JSON 객체 하나를 쓰고 매번 flush한다(`sys.stdout.write(line + "\n")`, `flush()`). 직렬화는 `json.dumps(record, separators=(",", ":"), ensure_ascii=False)`. paho 내부 로그는 켜지 않는다. 이 로그가 이 Component의 유일한 기록이다(결과 파일·DB 없음, U-11).

- 공통 키(이 순서로 맨 앞): `ts`(기록 시각, UTC, 밀리초 3자리 버림, `Z`. CONVENTIONS Timestamp 형식), `level`(`INFO`|`WARNING`|`ERROR`), `event`. 나머지 키는 아래 표의 순서.
- `LOG_LEVEL`보다 낮은 수준은 쓰지 않는다(`DEBUG` < `INFO` < `WARNING` < `ERROR`. `DEBUG` 수준 event는 없다).
- `product_id`, `timestamp`는 `01-processing.md` 2절에서 그 값이 검증을 통과했을 때만 넣는다. 값이 없는 선택 키는 빼고, null로 넣지 않는다.

| `event` | `level` | 언제 | 추가 키 |
|---|---|---|---|
| `started` | INFO | 설정을 읽고 연결 전 | `mqtt_url`, `client_id`, `subscribe_topic`, `publish_topic`, `image_root`, `judgement_source`(`"PASS_THROUGH"`) |
| `connected` | INFO | 구독 SUBACK 수신(구독 완료) | 없음 |
| `connect_failed` | WARNING | 연결 실패 | `reason: "connect_failed"`, `detail` |
| `disconnected` | WARNING(종료 중 INFO) | 연결 끊김 | `reason: "disconnected"`, `detail` |
| `received` | INFO | 메시지 수신 | `topic`, `bytes` |
| `warning` | WARNING | Ground Truth 깨진 줄을 건너뜀 | `reason: "ground_truth_bad_lines"`, `count`, `product_id`? |
| `dropped` | ERROR | 결과를 발행하지 않음 | `reason`, `detail`, `product_id`?, `timestamp`? |
| `published` | INFO | PUBACK 수신 | `product_id`, `timestamp`, `defect`, `defect_type`, `latency_ms` |
| `error` | ERROR | 설정 오류(시작 시), 메시지 밖의 예상하지 못한 예외 | `reason`(`invalid_config`\|`internal_error`), `detail` |
| `stopped` | INFO | 종료 신호로 루프가 끝남 | `signal`(`SIGTERM`\|`SIGINT`) |

`dropped`의 `reason`은 `01-processing.md` 5절의 9개와 `publish_failed`, `internal_error`, 모두 11개다. `detail`은 사람이 읽는 설명이며(200자로 자름) 값 형식은 약속하지 않는다. `event`와 `reason` 값은 integration이 검사에 쓸 수 있는 약속이다(`AGREEMENTS.md` V-06).

예:

```text
{"ts":"2026-09-27T05:20:13.431Z","level":"INFO","event":"received","topic":"factory/product/created","bytes":118}
{"ts":"2026-09-27T05:20:13.436Z","level":"INFO","event":"published","product_id":"P-00000113","timestamp":"2026-09-25T05:20:13.425Z","defect":true,"defect_type":"scratch","latency_ms":5}
{"ts":"2026-09-27T05:20:15.402Z","level":"ERROR","event":"dropped","reason":"ground_truth_missing","detail":"no complete line for P-00000114","product_id":"P-00000114","timestamp":"2026-09-25T05:20:15.398Z"}
```

`logs.py` 공개 이름: `iso_ms(dt: datetime) -> str`, `Logger(level: str, stream=sys.stdout)`, `Logger.emit(level: str, event: str, **fields) -> None`. 시각은 호출 때 `datetime.now(timezone.utc)`로 얻는다(테스트는 `iso_ms`만 고정 시각으로 검사한다).

## 5. 기동 확인 파일

HTTP endpoint가 없으므로 컨테이너 healthcheck는 파일로 한다(`DECISIONS.md` D-15).

- 경로: 설정 `HEALTH_FILE`(기본 `/tmp/vision-inspection.connected`).
- 시작할 때 있으면 지운다. 구독 SUBACK을 받았을 때 만든다(`touch`, 1절). 연결 실패·끊김·종료 때 지운다(없으면 무시).
- 뜻: "지금 Broker에 연결되어 Product Created 구독이 승인됨(SUBACK)". 이 파일이 생긴 뒤 발행된 Product Created는 받는다. Ground Truth 파일 유무와는 무관하다.
- 컨테이너 `HEALTHCHECK`는 `03-runtime.md` 5절.

## 6. 기동과 종료

`python -m vision_inspection`(`__main__.py`의 `main() -> int`, `sys.exit(main())`):

1. `load_config(os.environ)`(`03-runtime.md` 2절). `ConfigError`면 `error` 로그(`reason: invalid_config`, `detail`) 후 종료 코드 2. 이때 Logger 수준은 `INFO`로 쓴다.
2. `started` 로그, 기동 확인 파일 정리.
3. `SIGTERM`, `SIGINT` 처리기 설치: 종료 표시를 하고 `client.disconnect()`. 컨테이너에서 PID 1로 돌기 때문에 처리기가 있어야 신호를 받는다.
4. `loop_forever(retry_first_connection=True)`. 돌아오면 기동 확인 파일 삭제, `stopped` 로그, 종료 코드 0.
5. 위 과정 밖(콜백 밖)의 예상하지 못한 예외: `error` 로그(`reason: internal_error`) 후 종료 코드 1.

- 자동 재시작은 하지 않는다(Shared ARCHITECTURE 12절). 컨테이너 restart 정책도 두지 않는다.
- 종료 때 처리 중이던 메시지나 PUBACK을 기다리지 않는다.
