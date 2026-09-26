# 결정 기록

> 목적: 이 Component 안에서 내린 설계·절차 결정과 그 이유를 한 곳에 둔다. 다른 Component와의 약속은 `AGREEMENTS.md`에 있다.
> 읽어야 할 때: spec의 값이나 규칙이 왜 그런지 알아야 할 때, 결정을 바꾸려 할 때.
> 기준일: 2026-09-27. 책임자가 채팅으로 조율 agent에게 절차 예외를 지시하고 설계 결정을 위임했다(조율 결정 C-00, C-01). 아래는 그 위임으로 정한 것이다.

결정을 바꾸려면 새 ID로 항목을 추가하고 이전 항목의 "결정"에 `→ D-xx로 대체`를 붙인다. 지우지 않는다.

## 0. 이미 확정된 결정

다시 논의하지 않고 아래 결정의 전제로 쓴다.

- 범위: AI 모델 판정을 하지 않는 pass-through(Shared ISSUE-c8fad59b, Shared PR #6, `d0c997c`). `docs/ARCHITECTURE.md` 문서 상단과 11.3절 U-13, D-1~D-12, D-6 재결정.
- 입력 경로: Product Created 구독 + `ground_truth/products.jsonl`의 같은 `product_id` 줄에서 `defect`, `defect_type`만 읽음(Shared ARCHITECTURE 4.3절 현재 범위, INTERFACES Ground Truth·Vision Result).
- 출력: Shared INTERFACES Vision Result 확정본(`schema_version` 1, `factory/vision/result`, QoS 1, retain false, `confidence`·`bbox`·`gradcam_path` null, `judgement_source: "PASS_THROUGH"`).
- 아키텍처 리뷰에서 정한 것(`docs/reviews/architecture-codex-1.md`): 메시지마다 파일 전체 읽기, 완성된 같은 줄이 정확히 하나일 때만 사용, 줄 없음은 대기 없이 로그·미발행, `image_path` 정확 일치, MQTT 연결 규칙(ARCHITECTURE 4.9절), 설정 키(4.8절), 한 줄 JSON 로그와 `reason` 목록(9·10절).
- 조율 결정 C-16: `/data` 읽기 전용 마운트, `bbox`는 항상 null.

## 1. 절차 (책임자가 승인한 예외)

### D-01 PR merge 주체
- 문맥: `AGENTS.md`는 "Agent는 PR을 merge하지 않는다"고 정한다.
- 선택지: (a) 규칙대로 사람이 merge (b) 조율 agent가 merge
- 결정: (b). 조율 agent가 CI(`Validate Component / validate`) 통과와, 구현 PR이면 `agent/tasks/<ID>.yaml` `status: done`과 PR 본문 acceptance·verify 통과를 확인한 뒤 merge commit으로 main에 merge한다(squash·rebase 금지). task를 실행한 agent는 merge하지 않는다.
- 이유: 책임자 채팅 지시(2026-09-27)와 조율 결정 C-01. factory-simulator D-01과 같다.
- 영향: `04-verification.md` 7절

### D-02 계획 승인
- 문맥: PLAN의 새 milestone·task에는 `proposed: true`를 붙이고 사람이 지워야 착수할 수 있다.
- 선택지: (a) 매 계획 PR마다 사람이 `proposed`를 지움 (b) 책임자의 채팅 지시를 승인으로 보고 `proposed` 없이 등록
- 결정: (b). 이 spec을 따르는 계획 작업은 milestone과 task를 `proposed` 없이 등록한다. 이미 `proposed: true`가 붙은 M1과 SHARED-n은 계획 작업이 이 항목을 근거로 표시를 정리한다(PR 본문에 적는다).
- 이유: 책임자 채팅 지시(2026-09-27), 조율 결정 C-01.
- 영향: `00-overview.md` 6절

### D-03 acceptance는 자동 검사만
- 문맥: 기존 PLAN에는 `manual` acceptance(BOOT-1 A3, SHARED-2 A2, SHARED-3 A1, SHARED-5 A3)가 있다.
- 선택지: (a) task마다 manual 유지 (b) 모든 task는 `command`·`artifact`·`metric`만 쓰고 사람 확인은 마지막 milestone의 `owner: human` task로 모음
- 결정: (b). 기존 manual 항목은 계획 작업이 자동 검사로 바꾸거나, 이미 이루어진 사실(Shared PR #6 merge, 2026-09-27 D-6 재결정)을 근거로 완료 처리한다. 이 Component는 사람 확인 항목이 없어 사람 task도 없다(D-20).
- 이유: 책임자 채팅 지시(2026-09-27), 조율 결정 C-01, C-09.
- 영향: `00-overview.md` 6절, `04-verification.md` 1·6·7절

### D-04 verify 명령 추가 방식
- 문맥: `agent/config.yaml`은 사람 관리 파일이고 `verify`가 비어 있다.
- 선택지: (a) 사람이 따로 추가 (b) 영역을 처음 만드는 task가 `agent/config.yaml`을 scope에 넣고 같은 PR에서 추가
- 결정: (b). 명령과 시점은 `04-verification.md` 4절에 고정되어 있으므로 task는 그 명령을 그대로 넣는다. 약하게 바꾸지 않는다.
- 이유: factory-simulator D-05와 같다. 명령을 spec에 미리 고정해 임의 변경을 막는다.
- 영향: `04-verification.md` 4절

### D-05 계약 기준과 `contract_ref` 채택 시점
- 문맥: `SHARED_CONFIG.json` `contract_ref`가 null이다. 이 Component가 쓰는 Interface(Product Created, Vision Result, Image Reference, Ground Truth)와 CONVENTIONS는 Shared `d0c997c`에서 모두 확정이다. Shared main은 2026-09-27 조회 때도 `d0c997c`다.
- 선택지: (a) factory-simulator처럼 AGREEMENTS를 구현 기준으로 쓰고 null 유지 (b) 구현 전에 `d0c997c`를 `contract_ref`로 채택(SHARED-5)하고 구현 task는 `contract` 필드로 Shared 문서를 읽음 (c) 구현 시점의 최신 Shared main을 채택
- 결정: (b). SHARED-5가 구현 task(VIS-n)보다 먼저 `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`를 채택한다. VIS-n은 `contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]`를 적는다. 뒤에 Shared가 바뀌어도 Vision 관련 절이 바뀌지 않으면 다시 채택하지 않는다. 바뀌면 조율 agent에게 알리고 멈춘다.
- 이유: 조율 결정 C-04·C-05. (c)는 채택 대상이 task 시점마다 달라지고, 다른 Component의 미정 Interface 확정(PdM Result 등)이 이 Component와 무관하다. 채택 절차가 도구 문제로 불가능하면 (a)로 대신하고 이 파일에 새 항목으로 적는다(C-05).
- 영향: `00-overview.md` 6절, `AGREEMENTS.md` 머리말

## 2. 도구

### D-06 Python과 의존성 관리
- 문맥: 이 맥에는 Python 3.12.13과 `venv`·`pip`가 있고 uv는 없다.
- 선택지: (a) 저장소 루트 `.venv` + `pip install -r`(직접 의존 `==` 고정) (b) uv 설치 (c) 시스템 Python에 설치
- 결정: (a). 런타임 의존은 `paho-mqtt==2.1.0` 하나, 테스트 의존은 `pytest==9.1.1` 하나다(2026-09-27 PyPI 최신 안정판, 이 맥 venv에 설치 확인). 간접 의존은 고정하지 않는다.
- 이유: 새 도구 설치 없이 agent가 비대화식으로 만든다. factory-simulator와 같은 버전이라 두 Component의 MQTT 동작이 같다.
- 영향: `03-runtime.md` 3·4절

### D-07 테스트 도구와 실행 진입점
- 선택지: (a) pytest + 저장소 루트 `Makefile`(venv stamp) (b) 셸 스크립트 (c) verify에 명령 직접 나열
- 결정: (a). 마커 `docker`(Mosquitto 컨테이너 연동), `smoke`(compose)로 나누고 `--strict-markers`를 쓴다. smoke도 pytest로 써서 결과 판정과 node id를 단위 테스트와 같은 방식으로 한다.
- 이유: factory-simulator D-07과 같은 흐름. 요구사항이 바뀔 때만 재설치한다. verify 명령이 짧다.
- 영향: `03-runtime.md` 3·4절, `04-verification.md`

### D-08 MQTT client 실행 방식
- 선택지: (a) paho 2.1.0 `loop_forever(retry_first_connection=True)`를 주 스레드에서 돌리고 콜백 안에서 처리·발행 (b) `loop_start()` 네트워크 스레드 + 처리 스레드와 큐 (c) aiomqtt(asyncio)
- 결정: (a). MQTT 3.1.1, `CallbackAPIVersion.VERSION2`, clean session, keepalive 30초, `reconnect_delay_set(1, 10)`.
- 이유: 처리가 수 ms이고 제품은 2초에 1개라 스레드를 나눌 이유가 없다. 한 스레드라 `publish()`가 돌려준 `mid`를 기록하기 전에 `on_publish`가 불릴 경쟁이 없고, 받은 순서대로 발행된다. 재연결·첫 연결 재시도가 라이브러리에 있다. 2026-09-27 이 맥에서 Mosquitto 2.1.2로 발행·PUBACK, Broker 재시작 뒤 재연결·재구독, 신호 처리기의 `disconnect()`로 종료를 확인했다(ARCHITECTURE R-9 해소).
- 영향: `02-service.md` 1~3·6절

### D-09 테스트용 MQTT Broker
- 선택지: (a) Docker `eclipse-mosquitto:2.1.2-alpine` 컨테이너 (b) 프로세스 안 Python broker (c) 가짜 client만
- 결정: (a). 처리 규칙은 Broker 없는 단위 테스트로, MQTT 동작은 실제 Mosquitto로 본다. Docker를 쓸 수 없으면 실패한다.
- 이유: factory-simulator(D-09)·integration이 쓰는 것과 같은 Broker다. 이미지가 이 맥에 있고 `/mosquitto-no-auth.conf`로 익명 접속한다.
- 영향: `04-verification.md` 2·3절

## 3. 처리

### D-10 Ground Truth 조회 방식
- 결정: 메시지마다 파일 전체를 `read_bytes()`로 읽는다. 위치 기억·색인·캐시·대기·재시도는 없다(ARCHITECTURE L-10 해소를 그대로 확정).
- 이유: 파일은 시연 5분 약 60 KB, 1시간 1,800줄·1 MB 안쪽이다. 1,800줄에서도 평균 50 ms 이하를 테스트로 확인한다(D-21). 상태가 없으면 재기동·볼륨 초기화(`product_id`가 1부터 다시 시작, CONVENTIONS ID)에서도 틀린 캐시가 생기지 않는다.
- 영향: `01-processing.md` 3절

### D-11 Ground Truth 줄 판정
- 결정: `\n`으로 끝난 줄만 본다. 깨진 줄(UTF-8 아님, JSON 아님, 객체 아님, 빈 줄)은 건너뛰고 세며, 찾던 줄을 찾으면 발행하고 경고 로그를 남긴다. 같은 `product_id`의 줄이 정확히 하나일 때만 쓰고, `defect`·`defect_type`의 타입·일관성만 검사한다. `defect_type` 키가 없는 것은 null과 다르게 오류로 본다.
- 이유: 한 줄이 깨졌다고 이후 모든 제품을 막지 않는다. 중복은 생산자 규칙상 파일 손상이므로 추측하지 않는다. 다른 필드는 Shared 예외 범위 밖이라 대조에 쓰지 않는다(아키텍처 리뷰 3번 판정).
- 영향: `01-processing.md` 3절

### D-12 Product Created 검증 순서와 정규식
- 결정: `01-processing.md` 2절 순서(JSON → `schema_version` → 필수 필드 타입 → `product_id` → timestamp → `image_path`)로 검사하고 첫 실패의 `reason`만 남긴다. 정규식은 `[0-9]`와 `re.fullmatch`를 쓴다. timestamp는 형식만 본다. `schema_version`의 `true`는 거부한다.
- 이유: Python의 `\d`는 유니코드 숫자를, `$`는 끝 `\n`을 받아들여 CONVENTIONS의 의도보다 넓다. `bool`은 `int`의 하위 타입이라 `True == 1`이 참이다. 날짜 값 검증은 생산자가 시계로 만드는 값이라 실익이 없다.
- 영향: `01-processing.md` 2절, `04-verification.md` 3.1절

### D-13 MQTT 경계 사례
- 결정: (1) `publish()` rc가 `MQTT_ERR_NO_CONN`이면 발행 요청이 받아들여진 것으로 본다. paho가 메모리에 두었다가 재연결 뒤 보낸다. 그 밖의 오류 rc는 `publish_failed`로 버린다. 이 Component가 따로 재발행 큐를 두지 않는다. (2) retained Product Created도 보통 메시지처럼 처리한다. (3) 같은 Product Created를 두 번 받으면 두 번 발행한다.
- 이유: (1) paho 2.1.0은 연결이 없을 때 QoS 1 메시지를 `_out_messages`에 남기고 재연결 때 보낸다(소스 확인). 이것을 "실패"로 로그하면 뒤에 `published`가 나와 로그가 모순된다. (2)(3) 계약상 Product Created는 retain false이고, Vision Result는 중복을 허용하며 소비자가 `product_id`로 구분한다(Shared INTERFACES Vision Result). 걸러 내는 규칙을 더하면 상태가 생긴다.
- 영향: `02-service.md` 1~3절

### D-14 로그 형식
- 결정: stdout 한 줄 JSON, 공통 키 `ts`·`level`·`event`, `event` 10개와 `dropped`의 `reason` 11개를 `02-service.md` 4절 표로 고정한다. ARCHITECTURE 10절의 event 목록에 `connect_failed`, `warning`, `stopped`를 더했고, `disconnected`는 `dropped`의 사유가 아니라 event다. `detail` 형식은 약속하지 않는다.
- 이유: integration과 테스트가 `event`·`reason`만으로 판정할 수 있게 한다. 연결 실패·깨진 줄 경고·정상 종료를 구분할 event가 ARCHITECTURE 목록에 없었다.
- 영향: `02-service.md` 4절, `AGREEMENTS.md` V-06

### D-15 기동 확인 방법
- 문맥: HTTP endpoint가 없다. integration은 compose에서 기동을 확인할 방법이 필요하다.
- 선택지: (a) 연결 상태 파일 + `HEALTHCHECK test -f` (b) healthcheck 없이 로그의 `connected`로 확인 (c) 작은 HTTP `/healthz` 추가 (d) healthcheck가 MQTT로 직접 접속
- 결정: (a). `on_connect` 성공 때 `HEALTH_FILE`을 만들고 끊기면 지운다. 컨테이너 상태 `healthy`는 "Broker에 연결되어 구독 중"을 뜻한다.
- 이유: 의존 추가가 없고 `docker compose up --wait`와 `depends_on: condition: service_healthy`를 그대로 쓸 수 있다. 2026-09-27 이 맥에서 시험 이미지로 확인했다. (b)는 compose가 기다릴 수 없다. (c)는 포트와 서버가 생긴다. (d)는 client id 충돌과 Broker 부하를 만든다.
- 영향: `02-service.md` 5절, `03-runtime.md` 5절, `AGREEMENTS.md` V-05

### D-16 종료와 종료 코드
- 결정: SIGTERM·SIGINT는 `disconnect()`로 루프를 끝내고 종료 코드 0. 설정 오류는 2. 그 밖의 예상하지 못한 최상위 예외는 1. 자동 재시작과 restart 정책은 없다.
- 이유: 컨테이너 PID 1은 처리기가 없으면 SIGTERM을 무시해 `docker stop`이 10초 뒤 SIGKILL로 끝난다. 종료 코드로 설정 오류를 구분하면 integration이 원인을 바로 안다. 자동 재시작은 Shared ARCHITECTURE 12절 범위 밖이다.
- 영향: `02-service.md` 6절

### D-17 컨테이너
- 결정: `python:3.12-slim-bookworm` 한 단계, root 실행, `PYTHONPATH=/app/src`, 이미지 안에 `/data`를 만들지 않음, 포트 없음. Image Storage는 `/data`에 읽기 전용 마운트(`:ro`)를 요구한다.
- 이유: factory-simulator와 같은 기반 이미지·사용자다(볼륨 권한 문제 회피). 이미지에 `/data` 내용이 있으면 빈 named volume을 처음 마운트할 때 Docker가 그 내용을 볼륨에 복사한다. 이 Component는 볼륨에 쓰지 않으므로(조율 결정 C-16) 읽기 전용이 맞다.
- 영향: `03-runtime.md` 5·6절, `AGREEMENTS.md` V-04·V-05

### D-18 코드 배치
- 결정: `src/vision_inspection/`에 파일 8개(`__init__`, `__main__`, `config`, `logs`, `payload`, `ground_truth`, `process`, `app`)를 두고, 패키지 빌드 설정 없이 `PYTHONPATH=src`로 import한다. ARCHITECTURE 2.1절의 5개 모듈에서 `main`을 `__main__`으로 바꾸고, 순수 처리 순서를 `process`로, 로그를 `logs`로 뗐다.
- 이유: 처리 규칙 전체를 paho 없이 단위 테스트하려면 `app`에서 순수 부분(`process`)을 떼야 한다. 로그 형식은 `__main__`의 설정 오류와 `app`이 함께 쓴다. 패키지 설치(`pip install -e .`)는 build backend를 더 받아야 하고 얻는 것이 없다.
- 영향: `03-runtime.md` 1절

### D-19 설정
- 결정: 환경 변수만 쓴다. 변수가 없으면 기본값, 빈 문자열이면 설정 오류. `MQTT_URL`은 `mqtt://host[:port]`만 받는다. `HEALTH_FILE`을 ARCHITECTURE 4.8절 키에 더했다.
- 이유: 설정 값이 7개뿐이라 파일이 필요 없다. 빈 값을 기본값으로 바꾸면 `.env`나 compose의 실수가 조용히 숨는다. factory-simulator와 같은 이름·형식(`MQTT_URL`, `IMAGE_ROOT`, `LOG_LEVEL`)이다.
- 영향: `03-runtime.md` 2절

## 4. 검증

### D-20 사람 확인 없음
- 선택지: (a) 마지막 milestone에 사람 task(예: 로그 눈으로 확인) (b) 사람 task 없음
- 결정: (b).
- 이유: 화면이 없고, 관찰할 수 있는 결과(Payload, 로그, 종료 코드, 마운트, healthcheck)를 모두 자동 테스트가 판정한다. 시스템 시연은 integration·factory-operations의 확인 범위다. 사람에게 확인을 맡길 이유가 없다.
- 영향: `00-overview.md` 2·6절, `04-verification.md` 6절, `HUMAN.md`

### D-21 처리 시간 자체 상한
- 문맥: Shared ARCHITECTURE 2절의 Vision 성능 기준(mAP, FPS)은 현재 범위 제외다. Dashboard 5초 기준의 일부가 이 Component의 처리 시간이다.
- 결정: `process()` 평균 50 ms 이하(1,800줄 파일), 실제 Broker에서 Product Created 발행 → Vision Result 도착 1초 이하를 자동 테스트로 확인한다. 로그 `published.latency_ms`에 매 결과의 시간을 남긴다.
- 이유: 파일 전체 읽기(D-10)가 1시간 분량에서도 충분히 빠르다는 근거를 테스트로 남긴다. 상한은 여유 있게 잡아 이 맥에서 흔들리지 않게 했다(2026-09-27 이 맥에서 Shared 예시 형태 1,800줄·약 0.8 MB를 나누고 파싱하는 데 평균 약 6 ms).
- 영향: `00-overview.md` C-07, `04-verification.md` 3·5절
