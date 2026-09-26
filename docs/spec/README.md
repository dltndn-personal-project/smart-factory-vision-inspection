# Vision Inspection 구현 spec

> 상태: **확정** (2026-09-27). 책임자가 조율 agent를 통해 남은 설계 결정을 위임했고(조율 결정 C-00, C-01) 이 spec이 그 결정이다.
> 읽어야 할 때: 구현·계획 task를 시작할 때 항상 이 파일부터. 여기서 가리키는 파일(절)만 읽는다.

## 1. 읽는 규칙

1. 이 README의 2절 표에서 작업 영역을 찾는다.
2. 표가 가리키는 파일·절만 읽는다. 다른 파일은 링크를 따라갈 때만 연다.
3. 한 주제는 한 파일에만 있다. 다른 파일은 그 파일을 가리킨다. 두 곳에 같은 내용이 보이면 원본(가리킴을 받는 쪽)을 따르고 중복을 고친다.
4. spec에 없는 설계 결정이 필요하면 추측으로 진행하지 않는다. `DECISIONS.md`에 새 항목을 추가하는 PR로 정한 뒤 구현한다(책임자가 결정을 위임했으므로 agent가 정할 수 있다). 교차 Component 약속(`AGREEMENTS.md`)을 바꾸는 결정은 조율 agent에게 먼저 알린다.

## 2. 작업 영역 → 읽을 문서

| 작업 영역·질문 | 읽을 문서(절) |
|---|---|
| 무엇을 만드나, 언제 끝나나, 시연에서의 역할 | `00-overview.md` |
| PLAN에 milestone·task 추가, BOOT-1, SHARED-n 정리 | `00-overview.md` 6절, `04-verification.md` 4·7절, `DECISIONS.md` 1절 |
| `contract_ref` 채택(SHARED-5) | `DECISIONS.md` D-05, `AGREEMENTS.md` 머리말 |
| Product Created 검증, Ground Truth 조회, Vision Result 조립, 미발행 `reason` | `01-processing.md` |
| MQTT 연결·구독·발행, 재연결, 발행 완료 | `02-service.md` 1~3절 |
| 로그 형식, `event`·`reason` 목록 | `02-service.md` 4절 |
| 기동 확인(healthcheck), 신호, 종료 코드 | `02-service.md` 5·6절 |
| 디렉터리 구조, 설정(환경 변수), 의존성, `Makefile`, 로컬 실행 | `03-runtime.md` 1~4절 |
| `Dockerfile`, 단독 확인용 `compose.yaml` | `03-runtime.md` 5~7절 |
| 테스트, verify 명령, 성능 기준 | `04-verification.md` |
| 다른 Component·Shared와의 약속(Payload, 마운트, 시스템 compose 조건) | `AGREEMENTS.md` |
| 왜 이렇게 정했나 | `DECISIONS.md` |
| 사람이 해야 하는 일 | `HUMAN.md` |

## 3. 문서 목록

| 파일 | 내용 |
|---|---|
| `00-overview.md` | 목표, 완료 정의(C-01~C-09), 시연에서의 역할, 범위, 구현 순서와 milestone 윤곽 |
| `01-processing.md` | 순수 처리 함수, Product Created 검증, Ground Truth 조회, Vision Result 조립, 미발행 `reason` |
| `02-service.md` | paho client와 콜백, 메시지 처리 순서, 발행 완료, 한 줄 JSON 로그, 기동 확인 파일, 기동·종료 |
| `03-runtime.md` | 디렉터리, 설정 키, 의존성, `Makefile`, 로컬 실행, `Dockerfile`, `compose.yaml` |
| `04-verification.md` | 테스트 전략·목록, verify 명령과 추가 시점, 과제 성능 기준, 사람 확인(없음) |
| `DECISIONS.md` | 결정 기록 D-01~D-21 (D-01~D-05 절차) |
| `AGREEMENTS.md` | 교차 Component 약속 V-01~V-07, ARCHITECTURE 미결 사항 대응 |
| `HUMAN.md` | 사람이 할 일 H-1 |

## 4. 기준 문서의 순서

충돌하면 앞의 것을 따른다.

1. 책임자의 현재 지시(채팅, 조율 agent가 전달)
2. `AGENTS.md`의 불변 규칙. 단, `DECISIONS.md` 1절의 절차 예외 D-01~D-03은 책임자가 2026-09-27 채팅으로 지시했다(조율 결정 C-01). D-04·D-05는 위임 범위에서 정했다
3. Shared `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`의 `docs/INTERFACES.md`, `docs/CONVENTIONS.md`, `docs/ARCHITECTURE.md`(SHARED-5 이후 `contract_ref`. 그 전에는 같은 commit을 기준으로 읽는다, D-05)
4. 이 spec(`docs/spec/`)
5. `docs/COMPONENT.md`(BOOT-1 뒤)
6. `docs/ARCHITECTURE.md`(초안, 배경과 근거)

## 5. `docs/ARCHITECTURE.md`와의 관계

ARCHITECTURE.md는 이 spec의 배경과 근거다. 범위와 리뷰에서 정한 규칙은 그대로 전제로 쓴다(`DECISIONS.md` 0절). 두 문서가 다르면 이 spec을 따른다. 다른 곳:

| ARCHITECTURE | 이 spec |
|---|---|
| 2.1·2.3절 모듈 5개(`config`, `payload`, `ground_truth`, `app`, `main`) | 파일 8개. `process`(순수 처리 순서), `logs`를 떼고 `main`은 `__main__`(D-18) |
| 4.8절 설정 키 6개 | `HEALTH_FILE` 추가, 빈 값은 설정 오류(D-19) |
| 4.9절 "라이브러리의 자동 재연결", R-9 미확인 | `loop_forever(retry_first_connection=True)`, `reconnect_delay_set(1, 10)`, 이 맥에서 확인(D-08). NO_CONN 발행은 paho가 재연결 뒤 보냄(D-13) |
| 9절 `reason`에 `disconnected` | `disconnected`는 event. `dropped`의 `reason`은 11개(D-14) |
| 10절 event 7개 | `connect_failed`, `warning`, `stopped` 추가. `connected`와 기동 확인 파일은 구독 SUBACK 뒤(D-14, D-15) |
| 4.8절 Topic 설정 | CONVENTIONS 이름 규칙만 받고 두 Topic이 같으면 오류(D-19) |
| 6.3절 "명령은 spec·plan에서" | verify 명령 네 개와 시점을 고정(`04-verification.md` 4절). 기동 확인은 파일 healthcheck(D-15) |
| 8절 "지연 목표를 따로 두지 않는다" | 자체 상한(`00-overview.md` C-07)을 테스트로 확인(D-21). Shared 기준은 아니다 |
| 4.4절 "쓰기 권한으로 마운트되어도 쓰지 않는다" | 읽기 전용 마운트를 요구한다(조율 결정 C-16, V-04) |
| 11절 미결 사항 | `AGREEMENTS.md` 끝 표 |

## 6. 바꾸는 방법

- spec 변경은 해당 파일과 그것을 가리키는 파일을 같은 PR에서 고친다. 결정이 바뀌면 `DECISIONS.md`에 새 항목을 추가한다.
- `AGREEMENTS.md`를 바꾸면 "맞출 Component"가 달라질 수 있다. PR 본문에 적고 조율 agent에게 알린다.
- `02-service.md` 4절의 `event`·`reason` 값, `03-runtime.md` 2절의 환경 변수 이름, 5절의 `HEALTHCHECK` 뜻은 `AGREEMENTS.md` V-05·V-06과 함께 바꾼다.
- spec 리뷰 기록은 `docs/reviews/`에 있다. 구현에는 필요 없다.

## 7. 참고한 Shared commit

`dltndn-personal-project/smart-factory-shared-repository` main `d0c997c97129141d9853a42ce6e0d1f8f7309ae9`(2026-09-26T16:08:11Z, Shared PR #6 merge). 2026-09-27 spec 작성 때 기본 브랜치를 다시 조회해 같은 commit임을 확인했고, `docs/ARCHITECTURE.md`, `docs/INTERFACES.md`, `docs/CONVENTIONS.md`를 원격 Contents API(`gh api … -f ref=<SHA>`)로 읽었다. 로컬 `shared-repository/` 폴더는 쓰지 않았다. `contract_ref`는 아직 null이므로 이 commit은 SHARED-5 전까지 참고 기준이다(`agent/core/process/90-shared.md` 2절).
