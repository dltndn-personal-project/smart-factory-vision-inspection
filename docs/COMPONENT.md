# Vision Quality Inspection — Component 도메인 설명

시스템 내 책임은 Shared `docs/ARCHITECTURE.md` 4.3절과 17절(Responsibility Summary)이 기준이다. 이 파일은 그 범위 안에서 저장소 수준의 세부를 적는다. 구현 기준은 `docs/spec/`(먼저 `docs/spec/README.md`)이고, 설계의 배경과 근거는 `docs/ARCHITECTURE.md`(Component 아키텍처 초안)에 있다. 실행 순서는 `docs/plan/`에 있다.

Agent가 계획·구현·검증할 때 참조하는 이 Component의 도메인 슬롯이다. `agent/core`의 절차는 도메인을 모르므로 도메인 지식은 이 파일에만 둔다. 사람이 리뷰한다.

## 목적과 책임

factory-simulator가 발행하는 Product Created를 받아, Image Storage의 `ground_truth/products.jsonl`에서 같은 `product_id` 줄의 `defect`, `defect_type`을 읽고, Shared 확정본 그대로의 Vision Result를 `factory/vision/result`로 발행하는 작은 MQTT 서비스다(pass-through 판정, Shared `d0c997c` ARCHITECTURE 4.3절 현재 범위). 완료 정의는 `docs/spec/00-overview.md` 2절(C-01~C-09)이다.

## 경계

- 하지 않는 일: AI 모델 추론·학습·평가, Grad-CAM, 이미지 파일 열기·디코딩(경로 문자열만 옮긴다), Image Storage 쓰기(`gradcam/` 포함), Ground Truth의 `defect`·`defect_type` 밖 필드 전달(`bbox`는 항상 null), 오류 결과 메시지 발행, 재시도·대기·중복 제거, 결과 파일·DB 기록, 시스템 compose와 named volume 정의(integration 소유), Vision mAP·FPS 측정(현재 범위 제외). 자세한 표는 `docs/spec/00-overview.md` 4절.
- 소유하는 데이터·자원: 처리 규칙(Product Created 검증, Ground Truth 조회, Vision Result 조립), 한 줄 JSON 로그 형식(`event`·`reason` 값), 컨테이너 이미지 하나(`vision-inspection:local`)와 기동 확인 파일. 소유하는 영속 데이터는 없다.
- Integration Component가 아니다. 저장소의 `compose.yaml`은 단독 확인·smoke용이다.

## 용어

| 용어 | 뜻 |
|---|---|
| pass-through 판정 | AI 모델 없이 Ground Truth의 `defect`, `defect_type`을 그대로 결과로 옮기는 판정. 결과의 `judgement_source`는 `"PASS_THROUGH"` |
| Product Created | factory-simulator가 이미지 저장과 Ground Truth 기록 뒤 `factory/product/created`로 발행하는 입력 이벤트(QoS 1) |
| Ground Truth 줄 | `ground_truth/products.jsonl`의 `\n`으로 끝난 한 줄(JSON 객체). 같은 `product_id`의 완성된 줄이 정확히 하나일 때만 쓴다 |
| Vision Result | 이 Component가 발행하는 결과(`schema_version` 1, 10개 키, QoS 1, retain false). 형식 원본은 Shared INTERFACES |
| 미발행(`dropped`) | 입력 오류·Ground Truth 문제로 결과를 발행하지 않고 로그만 남기는 것. 사유는 `reason` 값(`docs/spec/02-service.md` 4절) |
| 기동 확인 파일 | 구독 SUBACK을 받으면 만들고 끊기면 지우는 파일(`HEALTH_FILE`). 컨테이너 `HEALTHCHECK`가 본다 |
| `contract_ref` | 이 Component가 구현 기준으로 채택한 Shared commit(`SHARED_CONFIG.json`). SHARED-5에서 `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`로 채택한다 |

## 구조

task `scope` glob의 기준이다. 원본은 `docs/spec/03-runtime.md` 1절이며, 각 경로는 표의 task가 만든다(`docs/plan/00-overview.md`).

| 경로 | 역할 | 만드는 task |
|---|---|---|
| `src/vision_inspection/**` | 서비스 코드. `config`, `logs`(VIS-1), `payload`, `ground_truth`, `process`(VIS-2, paho 없는 순수 처리), `app`(paho를 import하는 유일한 모듈), `__main__`(VIS-3) | VIS-1~3 |
| `tests/**` | pytest. 단위(`make test`), Docker Mosquitto 연동(`-m docker`), compose smoke(`-m smoke`). `tests/fixtures/shared_d0c997c/`는 Shared 예시 원본 | VIS-1~4 |
| `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `Makefile`, `.gitignore` | pytest 설정(패키지 빌드 없음, `PYTHONPATH=src`), 직접 의존 고정(`paho-mqtt==2.1.0`, `pytest==9.1.1`), venv·검증 명령 진입점 | VIS-1 |
| `Dockerfile`, `.dockerignore`, `compose.yaml`, `.env.example` | 컨테이너 이미지, 단독 확인용 compose(Mosquitto 포함), 환경 변수 예시 | VIS-4 |
| `docs/**` | 구현 spec(`docs/spec/`), 계획(`docs/plan/`), 리뷰 기록, 아키텍처 초안, 이 파일 | - |
| `agent/**`, `SHARED_CONFIG.json`, `SHARED_ISSUE_STATUS.yaml` | 작업 절차와 계획, Shared 연결 설정과 Issue 검토 기록 | - |

## 외부 의존과 계약

- Shared 계약: task의 `contract`에 적고 `agent/core/process/90-shared.md` 1절로 `contract_ref` 기준 문서를 읽는다. 이 Component가 쓰는 것은 Shared `d0c997c`의 INTERFACES(Product Created, Vision Result, Image Reference, Ground Truth)와 CONVENTIONS다. 구현 task(VIS-n)는 SHARED-5 채택 뒤에 시작한다(`docs/spec/DECISIONS.md` D-05).
- 교차 Component 약속과 실행 조건(마운트, 시스템 compose, 로그, MQTT 연결)은 `docs/spec/AGREEMENTS.md` V-01~V-07이다.
- 그 외 의존: MQTT Broker(Mosquitto 2.1.2, 익명 1883), Image Storage named volume의 `ground_truth/products.jsonl`(기록자 factory-simulator, `/data`에 읽기 전용 마운트), Python 3.12, paho-mqtt 2.1.0, pytest 9.1.1, Docker(연동 테스트·smoke, `eclipse-mosquitto:2.1.2-alpine`, `python:3.12-slim-bookworm`).

## 실행·검증 환경

원본은 `docs/spec/03-runtime.md`(설정 2절, 로컬 실행 4절, Dockerfile 5절, compose 6절)다. 명령은 모두 저장소 루트에서 실행한다.

- 설정: 환경 변수만(`MQTT_URL`, `MQTT_CLIENT_ID`, `PRODUCT_CREATED_TOPIC`, `VISION_RESULT_TOPIC`, `IMAGE_ROOT`, `LOG_LEVEL`, `HEALTH_FILE`). 기본값은 컨테이너 기준이며 `.env.example`에 있다. 빈 값은 설정 오류(종료 코드 2).
- 이미지: 저장소 루트 `Dockerfile`(`python:3.12-slim-bookworm`, 진입점 `python -m vision_inspection`, 포트 없음, `HEALTHCHECK`는 기동 확인 파일 `test -f "$HEALTH_FILE"`). 로컬 태그는 `vision-inspection:local`(`docker build -t vision-inspection:local .`).
- 단독 확인(Mosquitto 포함, factory-simulator 없이):

  ```sh
  docker compose up -d --build --wait            # vision-inspection이 healthy(구독 SUBACK 받음)가 될 때까지 기다린다
  docker run --rm -i -v vision-inspection_image-storage:/data eclipse-mosquitto:2.1.2-alpine \
    sh -c 'mkdir -p /data/ground_truth && cat >> /data/ground_truth/products.jsonl' < gt.jsonl   # gt.jsonl: 넣을 Ground Truth 줄(각 줄 끝 \n)
  docker compose exec -T mosquitto mosquitto_sub -v -t factory/vision/result   # 결과 보기
  docker compose logs -f vision-inspection                                      # 한 줄 JSON 로그
  docker compose down -v
  ```

  Mosquitto는 `127.0.0.1:${VIS_MQTT_PORT:-1883}`에만 묶인다. `/data`(named volume `image-storage`)는 읽기 전용 마운트이고 처음에는 비어 있다.
- 로컬 실행(개발용, Docker는 broker만):

  ```sh
  make venv
  docker compose up -d mosquitto
  mkdir -p data/ground_truth
  PYTHONPATH=src MQTT_URL=mqtt://127.0.0.1:1883 IMAGE_ROOT=./data HEALTH_FILE=/tmp/vis-dev.connected \
    .venv/bin/python -m vision_inspection
  ```

- 테스트: `make test`(단위), `make docker-test`(Docker Mosquitto 연동), `make smoke`(compose smoke: 프로젝트 이름 `vis-smoke`, 빈 호스트 포트, 빌드·healthy·읽기 전용 `/data`·결과 두 개·JSON 로그·`stop` 뒤 종료 코드 0 확인, 끝나면 `down -v`). Docker를 쓸 수 없으면 `docker-test`·`smoke`는 실패한다.
- 필요한 것: Python 3.12, Docker Desktop 실행, 첫 의존 설치·이미지 빌드에 인터넷(`docs/spec/HUMAN.md` H-1).
- 시스템 조합(시스템 compose, Image Storage 마운트, 기동 확인)은 integration이 `docs/spec/AGREEMENTS.md` V-04·V-05에 맞춰 정의한다.

공통 검증 명령은 `agent/config.yaml`의 `verify`에 둔다. 추가 시점과 명령은 `docs/spec/04-verification.md` 4절에 고정되어 있다: `agent-files`(BOOT-1), `unit`(VIS-1, `make test`), `broker`(VIS-3, `make docker-test`), `smoke`(VIS-4, `make smoke`).
