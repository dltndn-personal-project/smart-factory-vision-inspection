# 04 검증 계획

> 목적: verify 명령이 들어가는 시점과 그 뒤 task마다 드는 검증 시간, acceptance 작성 규칙, 테스트 파일과 task의 대응을 정한다. 사람 확인 task는 없다.
> 읽어야 할 때: task의 acceptance를 쓰거나 바꿀 때, `agent/config.yaml`을 바꾸는 task(VIS-1, VIS-3, VIS-4), 조율 agent가 phase 환경을 준비할 때. 같이 읽을 spec: `docs/spec/04-verification.md`.

## 1. verify 명령과 시점

명령은 spec 04 4절에 고정되어 있다. 해당 task가 먼저 직접 실행해 통과를 확인한 뒤 그대로 넣는다(spec D-04). acceptance가 `{name, run}` 쌍이 그대로 있는지 검사한다.

| 순서 | 넣는 task | 항목 | 그 뒤 task마다 드는 시간(spec 04 4절 추정) | 필요한 환경 |
|---|---|---|---|---|
| 1 | BOOT-1 (이 계획 PR, 완료) | `{name: agent-files, run: "python3 agent/core/tools/validate.py"}` | 1초 미만 | 없음 |
| 2 | VIS-1 | `{name: unit, run: "make test"}` | 수 초 | 첫 `make venv`에 인터넷(pip) |
| 3 | VIS-3 | `{name: broker, run: "make docker-test"}` | 약 1분 | Docker Desktop, `eclipse-mosquitto:2.1.2-alpine`(이 맥에 있음) |
| 4 | VIS-4 | `{name: smoke, run: "make smoke"}` | 첫 실행 1~2분(이미지 빌드), 이후 약 20초 | Docker Desktop, 첫 빌드에 인터넷(Docker Hub, pip) |

- phase별 verify 한 번의 시간: M1 1초 미만, M2 수 초, M3 약 1분, M4 약 1.5분. 모두 `check_timeout` 1800초 안이다.
- GitHub CI(`Validate Component`)는 agent 파일 검사와 `agent/core` 단위 테스트만 돌린다. 위 명령은 `agent.py verify`가 로컬에서 돌린다.

## 2. acceptance 작성 규칙

- 모두 `command`·`artifact`·`metric`이다(spec D-03). `manual`은 이미 끝난 BOOT-1 A3만 남는다(simulator 선례. 결과 기록은 D-02로 `pass`).
- 완료 정의 C-02~C-08은 pytest node id로 적는다: `make venv >/dev/null && .venv/bin/python -m pytest -q tests/<파일>::<테스트>`. node id가 없으면 pytest가 실패하므로 테스트가 있어야 통과한다. 테스트 이름을 바꾸는 것은 acceptance 변경이다(spec 04 7절). 매개변수화한 테스트도 함수 이름으로 적어 모든 경우를 돌린다.
- 측정 테스트(C-07)는 `-s`로 측정값이 증거 출력에 남게 한다.
- Docker 테스트는 skip 경로가 없는지 `grep`으로 함께 본다(VIS-3 A6, VIS-4 A2). Docker를 못 쓰면 실패해야 한다.
- 파일 없음으로 음성 검사(`! grep …`)가 통과하지 않게 `test -f`를 먼저 둔다.

## 3. 테스트 파일과 task

| 파일 | 만드는 task | 마커 | 실행 |
|---|---|---|---|
| `tests/test_config.py`, `tests/test_logs.py` | VIS-1 | 없음 | `make test` |
| `tests/test_payload.py`, `tests/test_ground_truth.py`, `tests/test_process.py`, `tests/fixtures/shared_d0c997c/` | VIS-2 | 없음 | `make test` |
| `tests/test_main.py` | VIS-3 | 없음 | `make test` |
| `tests/test_broker.py` | VIS-3 | `docker` | `make docker-test` |
| `tests/test_smoke.py` | VIS-4 | `smoke` | `make smoke` |
| `tests/conftest.py` | VIS-1이 만들고 VIS-2·3이 fixture를 더함 | - | - |

## 4. 사람 확인

없다(spec 04 6절, D-20, 조율 결정 C-17). 시스템 시연에서의 모습은 integration과 factory-operations의 사람 확인에 포함된다. 그래서 마지막 milestone(M4)에도 `owner: human` task가 없다.

## 5. 실패했을 때

- C-07 상한 실패: 기준을 늦추지 않는다. 원인(파일 캐시, Docker 부하)을 먼저 보고 PR에 적는다(spec 04 5절).
- 같은 verify 항목 3회 실패(`budget.verify_attempts`)는 멈춘다(`README.md` 5절).
- 앞 task가 넣은 verify가 뒤 task에서 실패하면 뒤 task의 변경을 먼저 의심한다. 앞 task 영역의 결함이면 멈추고 조율 agent가 FIX task를 만든다.
