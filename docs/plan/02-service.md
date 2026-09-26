# 02 서비스 계획 (M3 VIS-3)

> 목적: VIS-3(paho client와 콜백, 기동·종료, Docker Mosquitto 연동 테스트)의 PLAN 정의와 단계 개요.
> 읽어야 할 때: VIS-3을 실행하거나 등록할 때. 같이 읽을 spec: `docs/spec/02-service.md`, `04-verification.md` 2·3.2절, `AGREEMENTS.md` V-03·V-06·V-07.

## 1. 요약

| task | 선행 | size | 내용 |
|---|---|---|---|
| VIS-3 | VIS-2 | M | `app.py`, `__main__.py`, `conftest.py`의 `broker`·`fixed_port_broker`·`service`·`results`, `test_main.py`, `test_broker.py`(`@pytest.mark.docker`), `Makefile` `docker-test`, verify `broker` |

- Docker Desktop이 꺼져 있으면 연동 테스트는 실패한다(건너뛰지 않는다, spec 04 1절). 시작 전에 `docker info`로 확인하고, 꺼져 있으면 H-1 문제로 멈춘다(`README.md` 5절 멈춤 표 tool). `eclipse-mosquitto:2.1.2-alpine`은 이 맥에 있다.
- 서비스는 테스트 안에서도 실제 진입점(`python -m vision_inspection` 하위 프로세스)으로 띄운다. 기다림은 "사건이 올 때까지 최대 N초"로 쓰고 고정 sleep으로 통과를 기다리지 않는다(spec 04 1절).
- 이 task부터 모든 task의 verify에 `broker`(약 1분)가 붙는다.
- `02-service.md` 4절의 `event`·`reason` 값은 `AGREEMENTS.md` V-06과 묶여 있다. 바꿔야 하면 멈춘다(`README.md` 5절 멈춤 표 contract).

## 2. task

### VIS-3 MQTT 서비스

```yaml
  - id: VIS-3
    milestone: M3
    type: feature
    title: paho MQTT 서비스(app, __main__)와 Docker Mosquitto 연동 테스트, verify broker
    why: 처리 코어를 실제 Broker에 붙여 Product Created 하나에 Vision Result 하나를 QoS 1·retain false로 발행하고, 재연결·재구독, 기동 확인 파일, SIGTERM·설정 오류 종료 코드를 spec대로 만든다 (spec 02, D-08, D-09, D-13~D-16, C-04, C-05, C-06, C-07)
    depends_on: [VIS-2]
    contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]
    scope: [src/**, tests/**, Makefile, agent/config.yaml, docs/spec/02-service.md, docs/spec/DECISIONS.md]
    acceptance:
      - id: A1
        text: 잘못된 설정(MQTT_URL=http://h)으로 python -m vision_inspection을 띄우면 10초 안에 종료 코드 2로 끝나고 마지막 줄이 error·invalid_config다 (C-05 일부)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_main.py::test_invalid_config_exits_2"}
      - id: A2
        text: 실제 Mosquitto에서 Shared 예시 Product Created에 대해 5초 안에 Shared 예시와 같은 Vision Result 하나가 qos 1·retain false로 오고, received와 published(latency_ms int 0 이상) 로그가 남는다 (C-02, C-04, C-06)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_broker.py::test_publishes_shared_example"}
      - id: A3
        text: 잘못된 입력 8종 뒤 정상 sentinel을 보내면 결과는 sentinel 하나뿐이고 dropped reason이 보낸 순서와 같으며, Ground Truth 파일이 나중에 생겨도 상태 없이 이어서 처리한다 (C-03, C-04)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_broker.py::test_invalid_inputs_not_published tests/test_broker.py::test_ground_truth_created_later"}
      - id: A4
        text: Broker 재시작 뒤 15초 안에 다시 connected(기동 확인 파일 다시 생성)되어 결과를 발행하고, Broker보다 먼저 떠도 connect_failed 뒤 15초 안에 연결되며, SIGTERM에 5초 안 종료 코드 0·마지막 줄 stopped·기동 확인 파일 삭제다 (C-05)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_broker.py::test_broker_restart_resubscribes tests/test_broker.py::test_starts_before_broker tests/test_broker.py::test_sigterm_exits_0"}
      - id: A5
        text: 1,800줄 Ground Truth에서 30개 Vision Result 지연이 모두 2초 이하이고 중앙값 0.5초 이하이며 측정값을 출력한다 (C-07 연동, D-21)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q -s tests/test_broker.py::test_latency_1800_lines"}
      - id: A6
        text: 연동 테스트에 skip 경로가 없고 docker 마커가 붙어 있다(Docker를 못 쓰면 실패, make test에서는 빠짐. spec 04 1절)
        check: {type: command, run: "test -f tests/test_broker.py && ! grep -Eq 'pytest\\.skip|mark\\.skip|skipif|importorskip' tests/test_broker.py tests/conftest.py && grep -q 'mark.docker' tests/test_broker.py"}
      - id: A7
        text: paho를 import하는 모듈은 src/vision_inspection/app.py 하나다 (spec 02 1절)
        check: {type: command, run: "test -f src/vision_inspection/app.py && test -f src/vision_inspection/__main__.py && test \"$(grep -rlE '^[[:space:]]*(import|from)[[:space:]]+paho' src)\" = src/vision_inspection/app.py"}
      - id: A8
        text: agent/config.yaml verify에 spec 04 4절의 broker 명령이 그대로 있고 통과한다
        check: {type: command, run: "python3 -c \"import sys, yaml; v = yaml.safe_load(open('agent/config.yaml'))['verify']; sys.exit(0 if {'name': 'broker', 'run': 'make docker-test'} in v else 1)\" && make docker-test"}
      - id: A9
        text: 단위 테스트 전체가 통과한다
        check: {type: command, run: "make test"}
    size: M
```

단계 개요:
1. `app.py`: client 생성·콜백 등록·`reconnect_delay_set(1, 10)`·`connect_async`·`loop_forever(retry_first_connection=True)`, `on_connect` 구독과 `sub_mid`, `on_subscribe`에서 기동 확인 파일·`connected`, 실패·끊김 콜백, 콜백 예외 처리(spec 02 1·5절).
2. `on_message`·`on_publish`: `process()` 호출, `warning`·`dropped`·`publish()` rc 처리(`MQTT_ERR_NO_CONN`은 받아들임), `pending[mid]`, `published.latency_ms`(spec 02 2·3절, D-13).
3. `__main__.py`: `main() -> int`, 설정 오류 2, 신호 처리기 → `disconnect()`, `stopped` 0, 예상 밖 예외 1(spec 02 6절, D-16). `test_main.py`. → A1
4. `conftest.py`: `broker`, `fixed_port_broker`, `service`(정리 단계 로그 검사), `results`(SUBACK 뒤 반환). spec 04 2절 표.
5. `test_broker.py` 7개(spec 04 3.2절). → A2~A6
6. paho import 검사. `Makefile` `docker-test`, `agent/config.yaml` verify `{name: broker, run: "make docker-test"}` → `validate.py --remote`. → A7~A9

읽을 spec: 02 전체, 04 1·2·3.1(`test_main`)·3.2절, D-08, D-09, D-13, D-14, D-15, D-16, `AGREEMENTS.md` V-03·V-06·V-07.

- 연동 테스트가 흔들리면 기다림 한도를 늘리기 전에 기다리는 사건(SUBACK, `connected`)이 맞는지 먼저 본다. 기준 수치(15초, 5초, C-07)는 바꾸지 않는다.
