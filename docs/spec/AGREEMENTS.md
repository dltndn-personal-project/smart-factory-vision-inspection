# 교차 Component 약속

> 목적: 이 Component가 다른 Component에 약속하는 것과 다른 Component의 무엇에 의존하는지를 정한다.
> 읽어야 할 때: MQTT 구독·발행, Ground Truth 파일, Image Storage 마운트, 실행 조건을 구현하거나 바꿀 때. 다른 Component(특히 factory-operations, integration)가 이 Component와 연동할 때.
> 지위: 형식의 원본은 Shared `dltndn-personal-project/smart-factory-shared-repository` `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`의 INTERFACES·CONVENTIONS다(이 Component가 SHARED-5에서 `contract_ref`로 채택한다, `DECISIONS.md` D-05). 이 파일은 그 확정본을 이 Component가 어떻게 지키는지와, Shared가 정하지 않은 실행 조건(V-04~V-07)을 적는다. Shared와 다르면 Shared를 따른다.

각 항목의 형식: **약속·의존**, **근거**(Shared 절 또는 factory-simulator `docs/spec/AGREEMENTS.md` ID), **맞출 Component**.

## 목록

| ID | 항목 | 방향 | 맞출 Component |
|---|---|---|---|
| V-01 | Product Created 구독 | 의존(factory-simulator) | 없음 |
| V-02 | Ground Truth 파일 읽기 | 의존(factory-simulator) | 없음 |
| V-03 | Vision Result 발행 | 약속(factory-operations) | factory-operations |
| V-04 | Image Storage 마운트 | 의존(integration) | integration |
| V-05 | 시스템 compose 실행 조건 | 의존(integration) | integration |
| V-06 | 관측 로그 | 약속(integration) | integration(선택) |
| V-07 | MQTT 연결 | 의존(integration, Broker) | integration |

Shared에 새로 올릴 Interface는 없다. factory-simulator에 바라는 변경도 없다.

## V-01 Product Created 구독

**약속·의존**
- `factory/product/created`를 QoS 1로 구독한다. Shared 확정 형식(`schema_version` 1, `product_id`, 밀리초 `timestamp`, `image_path`)만 받아들이고 모르는 필드는 무시한다. 검증 규칙은 `01-processing.md` 2절이다.
- 생산자가 이미지 rename과 Ground Truth 줄 기록을 끝낸 뒤에 발행한다는 전제에 의존한다. 이 전제가 깨지면(줄이 나중에 쓰임) 그 제품은 `ground_truth_missing`으로 결과가 없다. 기다리거나 다시 읽지 않는다.
- 끊긴 동안·기동 전에 발행된 Product Created는 받지 못하고 되찾지 않는다(clean session, retain false).

**근거**: Shared INTERFACES Product Created(발행 전제), Interface 목록(QoS 1, retain false). factory-simulator A-06, D-37(Ground Truth 기록 실패 시 발행 안 함).

**맞출 Component**: 없음. factory-simulator의 현재 동작 그대로다.

## V-02 Ground Truth 파일 읽기

**약속·의존**
- `IMAGE_ROOT/ground_truth/products.jsonl`을 메시지마다 읽기 전용으로 처음부터 읽는다. `\n`으로 끝나지 않은 마지막 줄은 무시한다. 같은 `product_id`의 완성된 줄이 정확히 하나일 때 그 줄의 `defect`, `defect_type`만 쓴다(`01-processing.md` 3절).
- 나머지 필드(`bbox`, `fault_level`, `severity`, `defect_probability`, `defect_params`, `render_seed` 등)는 결과에 옮기지 않는다. factory-simulator A-18은 `bbox`를 옮길 수 있다고 적지만, Shared 확정본을 따라 `bbox`는 항상 null이다(조율 결정 C-16).
- 의존: 기록자는 factory-simulator 하나이고, 한 번 쓴 줄을 바꾸지 않으며, 발행한 `product_id`를 같은 볼륨에서 다시 쓰지 않는다. 볼륨을 지우면 번호가 1부터 다시 시작하는데, 이 Component는 상태가 없으므로 따로 할 일이 없다.

**근거**: Shared INTERFACES Ground Truth(현재 범위 예외), Vision Result(입력과 처리), CONVENTIONS Ground Truth·ID. factory-simulator A-08, A-09, A-18, D-50.

**맞출 Component**: 없음.

## V-03 Vision Result 발행

**약속**
- Product Created 하나에 Vision Result를 최대 하나 발행한다(같은 Product Created를 두 번 받으면 두 번). `factory/vision/result`, QoS 1, retain false.
- Payload는 Shared 확정본과 같은 10개 키를 항상 넣는다: `schema_version` 1, `product_id`·`timestamp`·`image_path`는 Product Created 값 그대로, `defect`·`defect_type`은 Ground Truth 값 그대로, `confidence`·`bbox`·`gradcam_path`는 항상 null, `judgement_source`는 항상 `"PASS_THROUGH"`. 키 순서는 Shared 예시와 같다(소비자는 순서에 의존하지 않아도 된다). 인코딩은 UTF-8 JSON 한 줄.
- 발행 순서는 Product Created 수신 순서다. 처리 시간은 보통 수 ms이고, 1,800줄 파일에서의 지연 상한을 자동 테스트로 확인한다(`00-overview.md` C-07).
- 결과가 없을 수 있다: 입력이 잘못되었거나 Ground Truth 줄을 찾지 못하면 발행하지 않고 로그만 남긴다(오류 결과 메시지 없음). 소비자는 Product Created에 대응하는 결과가 오지 않는 경우를 처리해야 한다(예: "검사 결과 없음"으로 표시). 재전송 요청 수단은 없다.

**근거**: Shared INTERFACES Vision Result(형식, 오류, 순서·중복), ARCHITECTURE 4.3절 현재 범위, 4.4절 Data Integration, 12절.

**맞출 Component**: factory-operations(결과 없음·중복 결과 처리, `judgement_source` 해석. 결함 값이 AI 판정이 아니라 Simulator 불량 정보를 옮긴 값임을 상관분석 해석에 반영).

## V-04 Image Storage 마운트

**의존**
- Image Storage named volume을 컨테이너 `/data`에 **읽기 전용**(`:ro`)으로 마운트해 준다. `IMAGE_ROOT`는 `/data`(이미지 기본값).
- 이 Component는 볼륨에 아무것도 쓰지 않는다. `gradcam/`도 현재 범위에서 쓰지 않는다. Shared INTERFACES Image Reference가 "`gradcam/`을 쓰는 vision-inspection은 쓰기 권한"이라고 적은 것은 모델 판정 복귀 때의 조건이다.
- 볼륨이 비어 있어도(`ground_truth/`가 아직 없어도) 기동한다.

**근거**: Shared INTERFACES Image Reference, CONVENTIONS 실행 환경과 설정(named volume, bind mount 금지). 조율 결정 C-16. factory-simulator A-17(다른 Component는 `:ro`).

**맞출 Component**: integration(시스템 compose의 마운트).

## V-05 시스템 compose 실행 조건

**의존**: 시스템 compose는 integration이 소유한다. 이 Component가 요구하는 조건:

```yaml
services:
  vision-inspection:
    image: vision-inspection:<COMPOSITION.json에 고정한 commit>   # 저장소 루트 Dockerfile로 빌드
    environment:
      MQTT_URL: mqtt://mosquitto:1883
      IMAGE_ROOT: /data
    volumes: ["image-storage:/data:ro"]
    depends_on: [mosquitto]
```

- 빌드: 저장소 루트 `Dockerfile`, 인자 없음. 이미지 진입점은 `python -m vision_inspection`이고 추가 명령 인자는 없다.
- 환경 변수: 위 두 개면 된다. 나머지(`MQTT_CLIENT_ID`, 두 Topic, `LOG_LEVEL`, `HEALTH_FILE`)는 기본값을 쓴다(`03-runtime.md` 2절). Topic 접두사를 바꾸면 두 Topic 변수를 함께 준다.
- 포트: 없다. HTTP를 열지 않는다.
- 기동 확인: 컨테이너 `HEALTHCHECK`가 있다. 상태 `healthy`는 "Broker에 연결되어 Product Created 구독이 승인됨(SUBACK)"이다. 그 뒤 발행된 Product Created는 받는다. `docker compose up --wait` 또는 다른 서비스의 `depends_on: {vision-inspection: {condition: service_healthy}}`로 기다릴 수 있다. Broker가 떠 있으면 컨테이너 시작 뒤 보통 3~6초 안에 `healthy`가 된다(검사 간격 3초).
- 기동 순서: 요구하지 않는다. Broker가 늦게 떠도 1~10초 간격으로 다시 연결한다. 다만 연결 전에 발행된 Product Created는 받지 못하므로, E2E 시나리오는 `healthy`를 확인한 뒤 제품 생산을 시작한다.
- 종료: `docker stop`(SIGTERM)에 종료 코드 0으로 곧 끝난다. 설정 오류는 종료 코드 2. restart 정책은 두지 않는다.
- 사용자: root. 초기화 때 따로 지울 상태가 없다.

**근거**: Shared ARCHITECTURE 19.1절(integration이 실행 정의 소유), CONVENTIONS 실행 환경과 설정. factory-simulator A-17과 같은 형식.

**맞출 Component**: integration(compose 정의, 기동 대기, E2E 시작 시점).

## V-06 관측 로그

**약속**: stdout에 한 줄 JSON 로그를 쓴다. `event`와 `reason` 값은 `02-service.md` 4절 표로 고정하며, 바꾸면 이 항목과 함께 바꾼다. integration은 E2E 검증에서 다음을 쓸 수 있다.

- 결과 발행 확인: `event: "published"`(`product_id`, `defect`, `defect_type`, `latency_ms`).
- 미발행 원인: `event: "dropped"`와 `reason`(값 목록은 `02-service.md` 4절).
- 연결 상태: `connected`, `disconnected`, `connect_failed`.
- `detail`의 문구는 약속하지 않는다.

**근거**: Shared CONVENTIONS 오류 표현(오류는 로그로 남긴다), ARCHITECTURE 19.1절(Interface 준수 검사, 교차 문제 재현 근거 기록).

**맞출 Component**: integration(선택. Payload 검사만으로도 E2E 확인은 된다).

## V-07 MQTT 연결

**의존**
- Broker: Mosquitto 2.1.2, 익명 접속, 1883 포트, 인증·TLS 없음(factory-simulator A-17과 같다).
- 이 Component의 연결: MQTT 3.1.1, client id `vision-inspection`(고정 기본값), clean session, keepalive 30초, LWT 없음, retained 메시지 발행 없음.
- client id는 시스템에서 유일해야 한다. 같은 id로 다른 client가 붙으면 Broker가 먼저 연결을 끊어 서로 번갈아 끊긴다. 인스턴스는 하나만 띄운다.

**근거**: Shared INTERFACES Interface 목록(factory-simulator 연결 규칙, 접두사), ARCHITECTURE 13절. client id 공통 규칙은 Shared에 없어 이 Component가 정했다(`docs/ARCHITECTURE.md` 4.9절, Q-7).

**맞출 Component**: integration(Broker 설정, 인스턴스 하나, 다른 검증 client가 `vision-inspection` id를 쓰지 않음).

## ARCHITECTURE 미결 사항 대응

`docs/ARCHITECTURE.md` 11절에 남아 있던 항목의 해결 위치다.

| ID | 항목 | 해결 |
|---|---|---|
| L-1 | 언어와 MQTT 라이브러리 | `DECISIONS.md` D-06, D-08 (Python 3.12, paho-mqtt 2.1.0) |
| L-6 | 검증 명령과 `verify` | `04-verification.md` 4절, D-04 |
| R-9 | paho 2.x API, 재연결, 재구독, PUBACK | `02-service.md` 1~3절, D-08(이 맥에서 확인) |
| U-5 | 언어 제약 | D-06 (작업 환경 기준 Python 3.12) |
| U-6 | 실행 방식 | `03-runtime.md`, V-05 |
| U-8 | 테스트·lint 도구 | D-07 (pytest. lint는 두지 않는다) |
| U-9 | ARCHITECTURE와 COMPONENT.md 관계 | 따로 유지. 확정 요약만 BOOT-1이 COMPONENT.md로 옮긴다(`00-overview.md` 6절) |
| U-10 | 모델 판정 복귀 | 이번 범위 밖. 복귀는 Shared DOCUMENT_CHANGE와 새 설계로 한다(Shared ARCHITECTURE 4.3절) |
| U-11 | 결과의 로컬 파일 기록 | 하지 않는다. 로그만(D-14, `02-service.md` 4절) |
| Q-7 | client id | V-07 |
| Q-11, Q-17 | Inspection Image, ARCHITECTURE 6절 그림 문구 | 구현에 필요 없음(ARCHITECTURE 11.1절). 조치 없음 |
| Q-14 | Vision 결과 지연 목표 | Shared 목표 없음. 자체 상한(`00-overview.md` C-07, D-21) |
| Q-18, Q-24(상관분석 해석) | Operations의 기록·해석 | factory-operations 몫. V-03 "맞출 Component"에 적었다 |
