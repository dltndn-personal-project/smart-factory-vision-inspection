# 00 개요

> 목적: 무엇을 만들고 언제 끝났다고 하는지, 구현 순서를 정한다.
> 읽어야 할 때: 계획(PLAN) 작업, milestone 완료 판단, 범위가 애매할 때.

## 1. 목표

factory-simulator가 발행하는 Product Created를 받아, Image Storage의 `ground_truth/products.jsonl`에서 같은 제품의 불량 여부·결함 유형을 읽고, Shared 확정본 그대로의 Vision Result를 발행하는 작은 MQTT 서비스를 만든다(pass-through 판정, Shared `d0c997c` ARCHITECTURE 4.3절 현재 범위). AI 모델, 이미지 디코딩, Grad-CAM은 없다. 이미지 파일은 열지 않고 경로 문자열만 옮긴다.

## 2. 완료 정의

아래가 모두 참이면 이 Component는 완료다. 다른 Component의 구현, integration E2E는 조건이 아니다.

| ID | 관찰할 수 있는 결과 | 확인 |
|---|---|---|
| C-01 | `SHARED_CONFIG.json` `contract_ref`가 `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`이고 `validate.py --remote`가 통과한다 | SHARED-5 acceptance |
| C-02 | Shared 예시 Product Created와 Ground Truth 줄로 만든 결과가 Shared 예시 Vision Result와 같은 dict이고, 직렬화한 키 순서도 같다 | 단위 |
| C-03 | `01-processing.md` 5절의 모든 미발행 `reason`이 해당 입력에서 나오고 결과를 만들지 않는다 | 단위 |
| C-04 | 실제 Mosquitto에서 Product Created 하나에 Vision Result 하나가 QoS 1·retain false로 `factory/vision/result`에 온다. 잘못된 입력에는 오지 않는다 | Docker 연동 |
| C-05 | Broker가 기동 때 없거나 도중에 재시작해도 15초 안에 다시 연결·재구독해 처리를 이어 간다. SIGTERM을 받으면 5초 안에 종료 코드 0으로 끝난다. 설정이 잘못되면 종료 코드 2로 끝난다 | Docker 연동 + 단위 |
| C-06 | stdout의 모든 줄이 JSON 객체 하나이고 `event`·`reason` 값이 `02-service.md` 4절 표 안에 있다 | 단위 + Docker 연동 |
| C-07 | 1,800줄 Ground Truth 파일에서 `process()` 한 번이 평균 50 ms 이하이고, 실제 Broker에서 30개 Vision Result의 지연(Product Created 발행 → 결과 도착)이 모두 2초 이하, 중앙값 0.5초 이하다 | 단위 + Docker 연동 |
| C-08 | 저장소 루트에서 `docker compose up -d --build --wait`로 컨테이너가 `healthy`가 되고, `/data`가 읽기 전용(`RW=false`)으로 마운트된 채 Ground Truth를 읽어 결과를 발행한다 | smoke |
| C-09 | `docs/COMPONENT.md`에 `<미정` 표시가 없고, `agent/config.yaml` `verify`에 `04-verification.md` 4절 네 항목이 있으며 모두 통과한다 | BOOT-1, VIS-4 |

사람이 확인할 항목은 없다(`04-verification.md` 6절, `DECISIONS.md` D-20).

## 3. 시연 흐름에서의 역할

시스템 시연(factory-simulator `docs/spec/00-overview.md` 3절 5분 시나리오)에서 이 Component는 화면이 없다. 칩이 검사 지점을 지나 Product Created가 나오면 수십 ms 안에 같은 `product_id`의 Vision Result를 발행하고, factory-operations Dashboard의 검사 결과·불량률이 이 값으로 갱신된다.

| 시연 시각(simulator 기준) | 이 Component에서 보이는 것 |
|---|---|
| 0:40 제품 이미지 | 제품마다 `published` 로그와 `factory/vision/result`의 `defect: false` |
| 1:50 Fault Level 8 이후 | `defect: true`, `defect_type`이 `scratch`·`dent`·`contamination`인 결과가 늘어난다 |
| 3:00 STOP ~ 3:40 START | Product Created가 없으니 결과도 없다. START 뒤 이어서 나온다 |

보는 방법: `docker compose logs -f vision-inspection` 또는 Broker에서 `mosquitto_sub -v -t factory/vision/result`. 시스템 조합과 시연 스크립트는 integration 소유다.

## 4. 범위

| 한다 | 하지 않는다 |
|---|---|
| Product Created 구독·검증(`01-processing.md` 2절) | 이미지 파일 열기·디코딩·전처리, 모델 추론, Grad-CAM, 학습·평가 |
| `ground_truth/products.jsonl` 읽기 전용 조회(`defect`, `defect_type`만) | `products/`·`gradcam/`·`training/`·`evaluation/` 접근, Image Storage 쓰기 |
| Vision Result 발행(Shared 확정본, `bbox` 항상 null) | Ground Truth의 다른 필드(`bbox`, `fault_level` 등) 전달 |
| 미발행 시 한 줄 JSON 로그(`reason`) | 오류 결과 메시지, 재시도·대기, 중복 제거, 결과 파일·DB 기록 |
| 단독 확인용 `compose.yaml`(Mosquitto 포함)과 루트 `Dockerfile` | 시스템 compose, named volume 정의(integration 소유) |
| 자동 테스트(단위, Docker 연동, smoke) | Vision mAP@0.5·20 FPS 측정(Shared ARCHITECTURE 2절 현재 범위 제외) |

## 5. 경계와 외부 의존

- 외부와 주고받는 것은 `AGREEMENTS.md`가 전부다. 형식의 원본은 Shared `d0c997c` INTERFACES(Product Created, Vision Result, Image Reference, Ground Truth)와 CONVENTIONS다.
- 소유: 처리 규칙, 로그 형식, 컨테이너 정의(이미지 하나). 소유하는 영속 데이터는 없다.
- 의존: MQTT Broker(Mosquitto 2.1.2, 익명 1883), Image Storage named volume의 `ground_truth/products.jsonl`(기록자 factory-simulator).

## 6. 구현 순서 (계획 입력)

계획 작업이 `agent/PLAN.yaml`에 옮길 milestone과 task 후보다. 각 task는 한 PR이고 앞 task가 merge된 뒤 시작한다. acceptance는 자동 검사만 쓴다(`DECISIONS.md` D-03). scope 열은 glob이다. 구현 task(VIS-n)는 `contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]`를 적고 SHARED-5 뒤에 시작한다(`DECISIONS.md` D-05).

| milestone | task | 내용 | scope | 읽을 spec |
|---|---|---|---|---|
| M0 bootstrap | BOOT-1 (기존) | plan PR에서 처리(조율 결정 C-09). `docs/COMPONENT.md`를 이 spec으로 채우고, verify에 `agent-files` 추가. A3(manual)은 C-01 채팅 승인으로 갈음 | 기존 | 00, 03, 04 4절 |
| M1 Shared 계약 | SHARED-2, SHARED-3 (기존) | 이미 이루어졌다(Shared PR #6 merge, D-6 재결정). plan PR이 근거와 함께 완료로 정리하고 manual 항목을 D-03에 맞게 처리한다 | 기존 | DECISIONS D-03 |
| | SHARED-5 (기존) | `contract_ref`를 `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`로 채택. `docs/ARCHITECTURE.md` 상단에 채택 사실 기록. A3(manual)은 자동 검사로 바꾼다(예: `contract_ref` 값 비교와 ARCHITECTURE의 SHA 문자열 검사) | `SHARED_CONFIG.json`, `docs/ARCHITECTURE.md` | DECISIONS D-05 |
| M2 처리 코어 | VIS-1 골격 | `pyproject.toml`, `requirements*.txt`, `Makefile`(venv, test), `.gitignore`, `src/vision_inspection/{__init__,config,logs}.py`와 테스트, verify에 `unit` 추가 | `src/**`, `tests/**`, `pyproject.toml`, `requirements*.txt`, `Makefile`, `.gitignore`, `agent/config.yaml` | 02 4절, 03 1~4절, 04 |
| | VIS-2 처리 | `payload.py`, `ground_truth.py`, `process.py`와 단위 테스트, Shared 예시 fixture | `src/**`, `tests/**` | 01, 04 3.1절 |
| M3 MQTT 서비스 | VIS-3 서비스 | `app.py`, `__main__.py`, Docker 연동 테스트, `Makefile` `docker-test`, verify에 `broker` 추가 | `src/**`, `tests/**`, `Makefile`, `agent/config.yaml` | 02, 04 3.2절 |
| M4 패키징 | VIS-4 컨테이너 | `Dockerfile`, `.dockerignore`, `compose.yaml`, `.env.example`, smoke 테스트, `Makefile` `smoke`, verify에 `smoke` 추가, `docs/COMPONENT.md` 실행 절 갱신 | `Dockerfile`, `.dockerignore`, `compose.yaml`, `.env.example`, `tests/**`, `Makefile`, `agent/config.yaml`, `docs/COMPONENT.md` | 03 5~7절, 04 3.3절, AGREEMENTS V-05 |

- 사람 task milestone은 없다(D-20).
- plan PR은 CODEOWNERS placeholder를 `@dltndn`으로 바꾼다(조율 결정 C-15).
- 발견된 결함은 해당 영역의 수정 task로 추가한다.
