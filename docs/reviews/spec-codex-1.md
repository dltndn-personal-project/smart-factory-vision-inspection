# spec 리뷰 기록 1 (Codex)

- 날짜: 2026-09-27
- 리뷰어: Codex CLI `codex-cli 0.155.0-alpha.16.4`, `codex exec -m gpt-6-sol -c model_reasoning_effort="high" -s read-only --skip-git-repo-check -C <저장소> -o <scratch>/vision-inspection/spec/spec-review.md "<요청>"`. 파일 수정 금지를 지시했고, 실행 뒤 `git status`가 깨끗한 것을 확인했다.
- 대상: `docs/spec/**`, `docs/ARCHITECTURE.md`, `docs/COMPONENT.md` (branch `docs/spec`, commit `e29ded0`)
- 비교 기준: Shared `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`의 `docs/INTERFACES.md`, `docs/CONVENTIONS.md`, `docs/ARCHITECTURE.md`(원격 Contents API로 받은 scratch 사본), factory-simulator `docs/spec/AGREEMENTS.md`(A-06~A-09, A-17, A-18)·`09-runtime.md`·`server/tests/conftest.py`, 조율 결정 C-00~C-16
- 요청 요지: 파일 사이 모순, 구현자가 설계 결정을 스스로 내려야 하는 빈 곳, 틀린 식·수치·정규식·명령(paho-mqtt 2.1.0 API, Docker/compose, Makefile, pytest 설정), 이 맥(Python 3.12.13, Docker 28.3.0, Compose v2.38.1, Make 3.81)에서 실행·확인할 수 없거나 흔들리기 쉬운 검증, 더 나은 대안이 분명한 약한 결정, README 라우팅 누락과 중복, 다른 Component가 받아들이기 어려운 약속, `HUMAN.md`가 최소인지와 D-20(사람 확인 없음)의 타당성, toy 범위에 비해 과한 설계. D-01~D-03은 논쟁 대상에서 뺐다.
- 판정 방법: 지적마다 해당 파일·절을 다시 읽어 확인했다. 2번은 이 맥에서 paho 2.1.0과 `eclipse-mosquitto:2.1.2-alpine`으로 `subscribe()` 반환값 `(MQTT_ERR_SUCCESS, mid)`와 `on_subscribe(client, userdata, mid, reason_code_list, properties)`의 `Granted QoS 1`을 확인했고, 5번은 Python 3.12 `json.loads('{"a":NaN}')`가 받아들이는 것을 확인했다. 조율 결정 C-03 기준(사실 오류·모순·빈 곳·검증 불가능한 명령은 반영, 운영 수준 요구는 미반영)을 적용했다.
- 결과: 지적 8개. 반영 6, 부분 반영 2, 미반영 0.

| 번호 | 요지 | 판정 | 이유 / 반영 위치 |
|---|---|---|---|
| 1 | 두 Topic을 같게 설정하면 Vision Result가 Product Created 검증을 통과해 끝없이 재발행됨 (high) | 반영 | 확인했다. 결과에도 `schema_version`·`product_id`·`timestamp`·`image_path`가 있고 모르는 필드는 무시한다. 같은 값이면 설정 오류로 한다. `03-runtime.md` 2절, `DECISIONS.md` D-19, `04-verification.md` 3.1절 `test_same_topics_rejected` |
| 2 | `subscribe()` 호출 직후 기동 확인 파일을 만들어 SUBACK 전에 `healthy`가 됨 (high) | 반영 | 호출 성공은 Broker의 구독 등록이 아니다. rc를 검사하고 `on_subscribe`에서 `mid`와 Granted QoS를 확인한 뒤 파일 생성과 `connected` 로그를 한다. 실패 분기(rc 오류, SUBACK 실패 코드)는 `connect_failed`. `02-service.md` 1·4·5절, D-08, D-15, `AGREEMENTS.md` V-05, README 5절 |
| 3 | `Rejected`에 `product_id`·`timestamp`가 없어 `Drop`에 검증된 값을 실을 수 없음 (medium) | 반영 | 함수 경계의 빈 곳이다. `Rejected`에 두 필드를 더하고, 실패 단계별로 실을 값(5단계 `product_id`만, 6단계와 Ground Truth 오류는 둘 다)을 고정했다. `01-processing.md` 1절, `04-verification.md` 3.1절 `test_drop_carries_ids_only_when_valid` |
| 4 | 연동 테스트가 결과 구독 client와 서비스의 구독 승인을 기다리지 않음 (medium) | 반영 | 첫 메시지를 놓칠 수 있다. `results` fixture는 SUBACK 뒤에 돌려주고, 입력을 보내는 테스트는 SUBACK 뒤 로그인 `connected`를 먼저 기다린다. smoke도 구독 SUBACK 뒤 발행한다. `04-verification.md` 2절, 3.3절 5단계 |
| 5 | Python `json.loads`가 표준 JSON이 아닌 `NaN`·`Infinity`를 받음 (medium) | 반영 | 확인했다. `parse_constant`로 거부하고 Product Created(`invalid_json`)와 Ground Truth 줄(깨진 줄)에 같은 함수를 쓴다. `01-processing.md` 2·3절, D-12, `04-verification.md` 3.1절 |
| 6 | 평균 50 ms와 연동 개별 1초를 필수 게이트로 두면 흔들릴 수 있음 (medium) | 부분 반영 | 단위 평균 50 ms는 유지했다. 이 맥 측정값(1,800줄 약 6 ms)의 8배 여유가 있다. 연동 기준은 개별 1초에서 "모두 2초 이하, 중앙값 0.5초 이하"로 바꿔 한 건의 흔들림에 덜 민감하게 했고, 측정값을 출력하게 했다. 시간 측정을 선택 확인으로 빼지는 않았다. 파일 전체 읽기(D-10)가 충분히 빠르다는 근거를 자동으로 남기려는 목적이라서다. 실패 시 기준을 늦추지 않고 원인을 PR에 적는 규칙을 더했다. `00-overview.md` C-07, `04-verification.md` 3.1·3.2·5절, D-21 |
| 7 | Topic 검증이 CONVENTIONS 이름 규칙(`/`로 구분한 소문자)보다 넓음 (low) | 반영 | `re.fullmatch(r"[a-z0-9_]+(/[a-z0-9_]+)*")`로 좁히고 경계값 테스트를 넣었다. `03-runtime.md` 2절, `04-verification.md` 3.1절 `test_invalid_topic` |
| 8 | `dropped.reason` 목록과 지연 상한이 여러 파일에 반복됨 (low) | 부분 반영 | `AGREEMENTS.md` V-06의 `reason` 목록을 지우고 `02-service.md` 4절을 가리키게 했다. 지연 수치는 `00-overview.md` C-07 하나를 원본으로 두고 `04-verification.md` 5절, D-21, V-03, README는 C-07을 가리키게 했다. 테스트 표(3.2절)의 수치는 절차의 일부라 남겼다. `01-processing.md` 5절(처리 `reason`)과 `02-service.md` 4절(로그)의 관계는 원래 가리킴이라 그대로 둔다 |

## 리뷰가 확인한 적합 영역

Shared 확정본과의 pass-through Payload, `bbox: null`(조율 결정 C-16), Ground Truth 읽기 전용 접근, simulator의 기록 후 발행 약속과의 일치, paho 2.1.0에서 `MQTT_ERR_NO_CONN` 발행이 재연결 뒤 전송된다는 판단(D-13, 2.1.0 소스와 일치), 사람 확인 없음(D-20)과 최소한의 `HUMAN.md`.
