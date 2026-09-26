# 03 실행 환경 계획 (M2 VIS-1, M4 VIS-4)

> 목적: VIS-1(골격, 설정, 로그, `Makefile`)과 VIS-4(컨테이너, 단독 compose, smoke)의 PLAN 정의와 단계 개요.
> 읽어야 할 때: VIS-1 또는 VIS-4를 실행하거나 등록할 때. 같이 읽을 spec: `docs/spec/03-runtime.md`, VIS-1은 `02-service.md` 4절, VIS-4는 `04-verification.md` 3.3절과 `AGREEMENTS.md` V-04·V-05.

## 1. 요약

| task | 선행 | size | 내용 |
|---|---|---|---|
| VIS-1 | SHARED-5 | M | `pyproject.toml`, `requirements*.txt`, `Makefile`(`venv`, `test`), `.gitignore`, `src/vision_inspection/{__init__,config,logs}.py`, `tests/{conftest,test_config,test_logs}.py`, verify `unit` |
| VIS-4 | VIS-3 | M | `Dockerfile`, `.dockerignore`, `compose.yaml`, `.env.example`, `tests/test_smoke.py`, `Makefile` `smoke`, verify `smoke`, `docs/COMPONENT.md` 실행 절 |

- VIS-1이 첫 `make venv`를 하므로 인터넷(pip)이 필요하다(`HUMAN.md`).
- VIS-4는 이미지 빌드에 인터넷(Docker Hub `python:3.12-slim-bookworm`, pip)과 Docker Desktop이 필요하다. 이 task부터 모든 task의 verify에 `smoke`(첫 실행 1~2분, 이후 약 20초)가 붙는다.
- VIS-4 scope에는 `src/**`가 없다. smoke에서 서비스 코드 결함이 드러나면 고치지 않고 멈춘다(`README.md` 5절 멈춤 표 scope). 조율 agent가 FIX task를 만든다.

## 2. task

### VIS-1 골격, 설정, 로그

```yaml
  - id: VIS-1
    milestone: M2
    type: feature
    title: 골격, 설정(config)과 한 줄 JSON 로그(logs), Makefile과 verify unit
    why: 모든 뒤 task가 쓰는 venv·pytest 진입점, 환경 변수 설정 검증(빈 값·Topic 규칙·같은 Topic 거부), 로그 형식을 먼저 고정한다 (spec 03 1~4절, 02 4절, D-06, D-07, D-18, D-19, C-06)
    depends_on: [SHARED-5]
    contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]
    scope: [src/**, tests/**, pyproject.toml, requirements.txt, requirements-dev.txt, Makefile, .gitignore, agent/config.yaml, docs/spec/03-runtime.md, docs/spec/DECISIONS.md]
    acceptance:
      - id: A1
        text: load_config가 기본값·환경 변수 덮어쓰기를 읽고, 잘못된 MQTT_URL·빈 값·CONVENTIONS 밖 Topic·같은 두 Topic을 설정 오류로, LOG_LEVEL을 대소문자 무시로, 없는 IMAGE_ROOT를 오류 아님으로 처리한다 (spec 03 2절, 04 3.1절)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_config.py::test_defaults tests/test_config.py::test_env_overrides tests/test_config.py::test_invalid_mqtt_url tests/test_config.py::test_empty_value_is_error tests/test_config.py::test_invalid_topic tests/test_config.py::test_same_topics_rejected tests/test_config.py::test_log_level_case_insensitive tests/test_config.py::test_missing_image_root_is_not_error"}
      - id: A2
        text: iso_ms가 밀리초 3자리로 버리고 Z를 붙이며, Logger가 ts·level·event를 맨 앞에 둔 한 줄 JSON을 쓰고 LOG_LEVEL보다 낮은 수준을 거르며 비ASCII를 그대로 둔다 (spec 02 4절, C-06)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_logs.py::test_iso_ms_truncates tests/test_logs.py::test_record_is_one_json_line_with_leading_keys tests/test_logs.py::test_level_filter tests/test_logs.py::test_non_ascii_kept"}
      - id: A3
        text: 직접 의존만 == 로 고정되어 있다. requirements.txt는 paho-mqtt 한 줄, requirements-dev.txt는 -r requirements.txt와 pytest 한 줄이다 (spec 03 3절, D-06)
        check: {type: command, run: "python3 -c \"import re, sys; rd = lambda f: [l.strip() for l in open(f) if l.strip() and not l.lstrip().startswith('#')]; r = rd('requirements.txt'); d = rd('requirements-dev.txt'); sys.exit(not (len(r) == 1 and re.fullmatch(r'paho-mqtt==[0-9.]+', r[0]) and d[:1] == ['-r requirements.txt'] and len(d) == 2 and re.fullmatch(r'pytest==[0-9.]+', d[1])))\""}
      - id: A4
        text: venv·캐시·로컬 데이터가 git에 잡히지 않는다 (spec 03 7절)
        check: {type: command, run: "for p in .venv/.installed src/vision_inspection/__pycache__/x.pyc tests/__pycache__/x.pyc .pytest_cache/x .env data/ground_truth/products.jsonl; do git check-ignore -q \"$p\" || exit 1; done"}
      - id: A5
        text: agent/config.yaml verify에 spec 04 4절의 unit 명령이 그대로 있고 통과한다
        check: {type: command, run: "python3 -c \"import sys, yaml; v = yaml.safe_load(open('agent/config.yaml'))['verify']; sys.exit(0 if {'name': 'unit', 'run': 'make test'} in v else 1)\" && make test"}
    size: M
```

단계 개요:
1. `pyproject.toml`(spec 03 3절 그대로), `requirements.txt`, `requirements-dev.txt`, `.gitignore`. → A3, A4
2. `Makefile` `venv`(Python 3.12 확인 첫 줄, `.venv/.installed` stamp), `test`, `.PHONY`. `make venv` 실행. → A4
3. `config.py`: `Config`(frozen), `load_config(env)`, `ConfigError("<변수>: <이유>")`, 표 순서로 첫 오류만. `test_config.py`. → A1
4. `logs.py`: `iso_ms`, `Logger.emit`(공통 키 순서, 수준 거름, 매번 flush). `test_logs.py`. → A2
5. `tests/conftest.py`에 VIS-1이 쓰는 것만(나머지 fixture는 쓰는 task가 더한다). `__init__.py`.
6. `agent/config.yaml` verify에 `{name: unit, run: "make test"}` → `validate.py --remote`. → A5

읽을 spec: 03 1~4·7절, 02 4절(로그 표와 `logs.py` 공개 이름), 04 1·2·3.1절(`test_config`, `test_logs`), D-06, D-07, D-18, D-19.

### VIS-4 컨테이너, 단독 compose, smoke

```yaml
  - id: VIS-4
    milestone: M4
    type: feature
    title: Dockerfile, 단독 확인용 compose.yaml, compose smoke와 verify smoke
    why: integration이 저장소 루트 Dockerfile로 이미지를 만들고 읽기 전용 /data 마운트와 healthcheck로 조합할 수 있어야 한다. smoke가 그 실행 정의 전체를 자동으로 확인한다 (spec 03 5~7절, AGREEMENTS V-04·V-05, D-15, D-17, C-08, C-09)
    depends_on: [VIS-3]
    contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]
    scope: [Dockerfile, .dockerignore, compose.yaml, .env.example, tests/**, Makefile, agent/config.yaml, docs/COMPONENT.md, docs/spec/03-runtime.md, docs/spec/DECISIONS.md]
    acceptance:
      - id: A1
        text: compose smoke가 통과한다. up --build --wait로 healthy, /data RW=false, 볼륨에 넣은 Ground Truth로 P-00000001(dent)·P-00000002(양품) 결과만 오고, 로그가 모두 JSON이며, stop -t 10 뒤 종료 코드 0과 마지막 줄 stopped다 (spec 04 3.3절, C-04, C-05, C-06, C-08)
        check: {type: command, run: "make venv >/dev/null && .venv/bin/python -m pytest -q tests/test_smoke.py::test_compose_smoke"}
      - id: A2
        text: smoke 테스트에 skip 경로가 없다(Docker를 못 쓰면 실패, spec 04 1절)
        check: {type: command, run: "test -f tests/test_smoke.py && ! grep -Eq 'pytest\\.skip|mark\\.skip|skipif|importorskip' tests/test_smoke.py tests/conftest.py"}
      - id: A3
        text: Dockerfile이 spec 03 5절의 기반 이미지·HEALTHCHECK·진입점을 쓰고 포트·볼륨을 선언하지 않으며, 환경 변수와 .env 없이 해석한 compose 정의에서 프로젝트 이름이 vision-inspection, vision-inspection 서비스의 /data가 읽기 전용이고 포트가 없으며 Mosquitto는 127.0.0.1:1883에 묶인다 (C-08, V-04, V-05)
        check: {type: command, run: "grep -qx 'FROM python:3.12-slim-bookworm' Dockerfile && grep -q '^HEALTHCHECK' Dockerfile && grep -Eq '^ENTRYPOINT \\[\"python\", ?\"-m\", ?\"vision_inspection\"\\]' Dockerfile && ! grep -Eq '^(EXPOSE|VOLUME)' Dockerfile && env -u VIS_MQTT_PORT -u COMPOSE_PROJECT_NAME docker compose --env-file /dev/null config --format json | python3 -c \"import json, sys; c = json.load(sys.stdin); s = c['services']['vision-inspection']; v = s['volumes']; p = c['services']['mosquitto']['ports']; sys.exit(not (c['name'] == 'vision-inspection' and len(v) == 1 and v[0]['target'] == '/data' and v[0].get('read_only') is True and v[0]['type'] == 'volume' and not s.get('ports') and len(p) == 1 and p[0]['host_ip'] == '127.0.0.1' and str(p[0]['published']) == '1883'))\""}
      - id: A4
        text: .env.example에 spec 03 2절의 환경 변수 7개가 있고, .dockerignore가 tests·docs·agent·.venv·.git·data·.env를 뺀다 (spec 03 5·7절)
        check: {type: command, run: "for v in MQTT_URL MQTT_CLIENT_ID PRODUCT_CREATED_TOPIC VISION_RESULT_TOPIC IMAGE_ROOT LOG_LEVEL HEALTH_FILE; do grep -Eq \"^#? ?$v=\" .env.example || exit 1; done && for e in .git .venv tests docs agent data .env; do grep -qx \"$e\" .dockerignore || exit 1; done"}
      - id: A5
        text: 이미지 안에 /data가 없다(빈 named volume에 이미지 내용이 복사되지 않게, D-17)
        check: {type: command, run: "docker build -q -t vision-inspection:local . >/dev/null && docker run --rm --entrypoint sh vision-inspection:local -c 'test ! -e /data'"}
      - id: A6
        text: docs/COMPONENT.md 실행 절이 실제 명령(docker compose up -d --build --wait, make smoke, 로컬 실행)을 적고 미정 표시가 없다 (C-09)
        check: {type: command, run: "grep -q 'docker compose up -d --build --wait' docs/COMPONENT.md && grep -q 'make smoke' docs/COMPONENT.md && grep -q 'python -m vision_inspection' docs/COMPONENT.md && ! grep -q '<미정' docs/COMPONENT.md"}
      - id: A7
        text: agent/config.yaml verify에 spec 04 4절 네 항목(agent-files, unit, broker, smoke)이 그대로 있고 smoke가 통과한다 (C-09. 나머지 셋은 verify가 함께 돌린다)
        check: {type: command, run: "python3 -c \"import sys, yaml; v = yaml.safe_load(open('agent/config.yaml'))['verify']; need = [{'name': 'agent-files', 'run': 'python3 agent/core/tools/validate.py'}, {'name': 'unit', 'run': 'make test'}, {'name': 'broker', 'run': 'make docker-test'}, {'name': 'smoke', 'run': 'make smoke'}]; sys.exit(0 if all(n in v for n in need) else 1)\" && make smoke"}
    size: M
```

단계 개요:
1. `Dockerfile`(spec 03 5절 그대로), `.dockerignore`. `docker build`로 확인. → A3, A5
2. `compose.yaml`(spec 03 6절 그대로), `.env.example`. → A3, A4
3. `tests/test_smoke.py`(spec 04 3.3절 1~9단계, `@pytest.mark.smoke`, 빈 포트 선택, 실패 시 로그 100줄, 항상 `down -v`). 필요하면 `conftest.py`에 공용 도우미. → A1, A2
4. `Makefile` `smoke`. `make smoke` 두 번(첫 빌드, 캐시 뒤) 통과와 시간 기록.
5. `docs/COMPONENT.md` 실행·검증 환경 절을 실제 명령으로 갱신. → A6
6. `agent/config.yaml` verify에 `{name: smoke, run: "make smoke"}` → `validate.py --remote`. → A7

읽을 spec: 03 5~7절, 04 1·3.3·4절, 02 5·6절(기동 확인 파일, 종료), `AGREEMENTS.md` V-04·V-05, D-15, D-17.
