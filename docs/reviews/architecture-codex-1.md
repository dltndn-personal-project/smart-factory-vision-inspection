# 아키텍처 리뷰 기록 1 (Codex)

- 날짜: 2026-09-27
- 리뷰어: Codex CLI `codex-cli 0.155.0-alpha.16.4`, `codex exec -m gpt-6-sol -c model_reasoning_effort="high" -s read-only --skip-git-repo-check -C <저장소> -o <scratch>/arch-review.md "<요청>"`. 파일 수정 금지를 지시했고, 실행 뒤 `git status`가 깨끗한 것을 확인했다.
- 대상: `docs/ARCHITECTURE.md`, `docs/COMPONENT.md`, `SHARED_ISSUE_STATUS.yaml` (branch `docs/architecture-review`, commit `620e921` = main)
- 비교 기준: Shared `dltndn-personal-project/smart-factory-shared-repository` main `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`의 `docs/INTERFACES.md`, `docs/CONVENTIONS.md`, `docs/ARCHITECTURE.md`(원격 Contents API로 읽어 scratch에 저장한 사본), factory-simulator `docs/spec/AGREEMENTS.md`(A-06~A-09, A-17, A-18), `docs/spec/04-products.md`
- 요청 요지: Shared 확정 Interface(Product Created, Vision Result, Ground Truth, Image Reference)와 simulator 실제 동작(발행 순서, 파일 쓰기 순서, 점 파일, JSONL 마지막 줄, QoS·retain, timestamp)과의 모순, 범위 축소 뒤에도 남은 낡은 서술, 구현자가 스스로 설계 결정을 내려야 하는 빈 곳(Ground Truth 줄이 안 보일 때의 대기·재시도, 조회 방식, 중복 줄, MQTT 재연결, 설정값, 로그, 테스트), 이 맥(Python 3.12, Docker, 로컬)에서 실행·검증할 수 없는 것, toy 범위에 비해 과한 설계, 더 나은 대안이 분명한 약한 결정. 지적마다 심각도와 근거 위치를 달라고 했다. 범위 축소(pass-through, Shared ISSUE-c8fad59b) 자체는 논쟁 대상에서 뺐다.
- 판정 방법: 지적마다 대상 문서의 해당 절과 Shared `d0c997c` 원문, simulator spec을 직접 읽어 확인했다. 조율 결정 C-03 기준(사실 오류·모순·구현자가 정해야 하는 빈 곳·검증 불가능한 명령은 반영, 운영 수준 요구는 미반영)과 이번 단계의 수정 범위(`docs/ARCHITECTURE.md`만)를 적용했다.
- 결과: 지적 12개. 반영 9, 부분 반영 2, 미반영 1.

| 번호 | 요지 | 판정 | 이유 / 반영 위치 |
|---|---|---|---|
| 1 | "승인된 Interface가 아직 없다", Vision Result가 후보·승인 대기라는 서술과 11.1절의 Q-19~Q-25가 Shared 확정본과 다름 (high) | 반영 | 4절 첫 문단, 4.1절 표, 11.1절이 Shared PR #6 이전 상태 그대로였다. 4절을 `d0c997c` 확정본 요약으로 다시 쓰고 `contract_ref` null(채택 전)과 Shared 확정을 구분해 적었다. 11.1절은 질문별 처리 결과 표로 바꿨다. 1.1·1.2·1.5절, 0.1절 범례, 11.6절, 부록 A도 맞췄다 |
| 2 | Vision Result 표에 필수 `schema_version`이 없고, 처리 시각·밀리초·ID 유일성·production sequence를 미정으로 둠. JSON Schema 파일 부재를 계약 미정과 혼동 (medium) | 반영 | 모두 확인했다. 4.3절 표에 `schema_version`과 필수 여부를 넣고, 4.6절(밀리초 3자리 고정, 처리 시각 필드 없음), 4.7절(볼륨 수명 유일성, sequence는 숫자 부분)을 CONVENTIONS대로 고쳤다. 4.5절은 "필드 계약은 확정, 검증은 표준 라이브러리"로 바꿨다(L-9 해소) |
| 3 | 같은 `product_id` 완성 줄이 여럿이거나 줄의 `timestamp`·`image_path`가 입력과 다를 때의 처리가 없음. 매번 처음부터 읽고, 정확히 하나이며 공통 필드도 일치할 때만 복사하자는 제안 (medium) | 부분 반영 | 조회 방식(메시지마다 처음부터 읽기, L-10 해소)과 "정확히 하나일 때만 사용, 둘 이상이면 로그·미발행"은 반영했다(4.2절, 9절 `ground_truth_duplicate`). 다른 줄이 JSON으로 깨졌을 때 전체를 막지 않도록 그 줄만 건너뛰는 규칙도 추가했다. 공통 필드 대조는 넣지 않았다. Shared I:Ground Truth 현재 범위 예외가 "`defect`, `defect_type`만 읽고 나머지 필드는 읽어도 쓰지 않는다"로 정했고, 생산자가 같은 값을 쓰므로(simulator 04 7·8절) 실익이 없다 |
| 4 | 줄 누락 시 재시도 없이 미발행하는 결정은 Shared와 맞지만 문서가 이를 임시 가정·미결로 표시함. 생산자 순서(rename → JSONL 쓰기·flush → 발행)를 한곳에 명시하자 (medium) | 반영 | 9절 첫 문단이 "모두 [가정], 오류 결과 발행 여부는 Q-15에서 정한다"였다. I:Vision Result 오류를 근거로 확정 정책으로 바꾸고, 3.1절에 simulator의 실제 쓰기 순서와 "대기·재시도 정책을 두지 않는다"를 적었다. 4.2절 시점 항목도 같다 |
| 5 | 이미지 존재 확인의 기본값이 없고, 경로 검사가 "`products/` 아래"뿐이라 다른 파일명·점 파일을 받아들일 여지 (medium) | 반영 | 존재 확인은 하지 않기로 정하고 설정 항목을 없앴다(L-7 해소). `image_path`는 정확히 `products/{product_id}.jpg`여야 한다. 절대 경로, `..`, 임시 점 파일이 함께 걸러진다. 1.2, 1.5, 3.1, 4.2, 4.4, 6.1, 9절 |
| 6 | Vision client id, 재연결 뒤 재구독, 발행 성공 판단 시점이 없음 (medium) | 반영 | 4.9절 신설: MQTT 3.1.1, clean session, keepalive 30초, 고정 client id `vision-inspection`, 연결될 때마다 재구독, 라이브러리 자동 재연결, 끊긴 동안의 메시지는 되찾지 않음, PUBACK 수신 시 `published` 로그, 재발행 큐 없음. 라이브러리 API 확인은 spec(R-9)으로 남겼다 |
| 7 | Docker Compose를 미정으로 두고 브로커·볼륨 설정 키와 기본값이 없음 (medium) | 반영 | CONVENTIONS가 Docker Compose·named volume을 정했는데 6.2·7절, U-6가 미정이었다. 6.2·7절과 U-6를 고쳤다. 4.8절에 설정 키와 기본값(`MQTT_URL`, `MQTT_CLIENT_ID`, 두 Topic, `IMAGE_ROOT`, `LOG_LEVEL`)을 적었다. 이름은 simulator(`09-runtime.md`)와 맞췄다. 4.4절에 읽기 전용 마운트로 동작함과 Image Reference의 쓰기 권한 문구와의 관계를 적었다 |
| 8 | 검증 명령이 비어 있고, simulator는 렌더러나 `fake_renderer.py` 없이는 제품을 만들지 않으므로 Compose만 올리는 검증은 핵심 흐름을 시험하지 못함 (medium) | 부분 반영 | 6.3절 신설: 호스트 Python 3.12 단위 테스트 범위, simulator 없이 Mosquitto + Vision + 테스트 볼륨으로 Product Created를 직접 발행하는 컨테이너 확인, simulator E2E는 integration 몫(참고로 `fake_renderer.py`). 실제 명령과 `agent/config.yaml` `verify`는 넣지 않았다. 실행해 본 명령만 적는 규칙(`config.yaml` 주석)과 C-02 단계 구분에 따라 spec·plan(BOOT-1)에서 정한다. `agent/config.yaml`은 사람 관리 파일이다 |
| 9 | "모든 로그에 `product_id`와 입력 timestamp"는 시작 로그·파싱 실패에서 불가능하고, JSON 로그가 "권장"뿐임 (medium) | 반영 | 10절을 한 줄 JSON으로 확정하고 공통 필드(`ts`, `level`, `event`), `reason`(9절 표에 값 목록), `product_id`·`timestamp`는 알 수 있을 때만, `event` 값(`received`, `dropped`, `published` 등)을 정했다. 주기 집계는 없앴다(건수는 로그로 센다) |
| 10 | 모델 복귀를 가정한 `PassThroughJudge` 교체 경계와 10개 모듈은 toy 범위에 과함 (low) | 반영 | 모델 복귀는 미정(U-10)이고 복귀하면 Shared DOCUMENT_CHANGE와 함께 다시 설계해야 한다. 모듈을 `config`, `payload`, `ground_truth`, `app`, `main` 다섯으로 줄이고 판정 경계를 없앴다(L-8 삭제). 2.1~2.3, 5.1절 |
| 11 | `COMPONENT.md`가 거의 전부 `<미정>`이라 확정된 책임·입력·출력·볼륨·검증 조건을 알 수 없음 (medium) | 미반영 | 사실은 맞다. 다만 `COMPONENT.md` 채우기는 BOOT-1 task이고, 조율 결정 C-09에 따라 plan 단계에서 spec을 근거로 한다. 이번 단계는 `docs/ARCHITECTURE.md`만 고친다. 0.2절에 옮길 항목(pass-through 책임, 입력 파일, 출력 Topic, 읽기 전용 볼륨, 실행·검증 조건)과 옮기지 않을 항목을 적어 두었다 |
| 12 | `SHARED_ISSUE_STATUS.yaml`은 확정 사항을 정확히 기록하는데 아키텍처는 미승인·미정으로 남김. 상태값을 `applied`로 바꾸지 말 것 (low) | 반영 | 상태 파일은 고치지 않았다(`affected`는 계약 채택과 구현이 남았다는 뜻으로 맞다). 아키텍처 쪽을 번호 1·2·4의 수정으로 기록에 맞췄다. 11.6절에 검토 결과와 남은 일을 적었다 |

## 리뷰가 확인한 적합 영역

이미지 rename과 Ground Truth 기록 뒤 Product Created 발행, `\n`으로 끝나지 않은 마지막 줄 무시, Ground Truth 읽기 전용 접근, Vision Result의 `confidence`·`bbox`·`gradcam_path` `null`과 `PASS_THROUGH`, 입력 timestamp 유지, QoS 1·retain false, 중복 Product Created에 대한 중복 결과 허용, 범위 축소 유지.

## 참고

- Codex는 자기 샌드박스에서 Shared 원격 조회가 실패해 scratch 사본으로만 비교했다고 밝혔다. 그 사본은 리뷰 직전 이 저장소 작업자가 `gh api`로 `d0c997c`를 지정해 받은 것이다.
- 첫 실행은 외부 요인으로 중단되어 출력이 없었고, 같은 요청을 격리한 scratch 디렉터리에서 다시 실행한 결과를 판정했다.
