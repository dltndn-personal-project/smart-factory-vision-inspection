# 계획 리뷰 기록 1 (Codex)

- 날짜: 2026-09-27
- 리뷰어: Codex CLI `codex-cli 0.155.0-alpha.16.4`, `codex exec -m gpt-6-sol -c model_reasoning_effort="high" -s read-only --skip-git-repo-check -C <저장소> -o <scratch>/vision-inspection/plan/plan-review.md "<요청>"`. 파일 수정 금지를 지시했고, 실행 뒤 `git status`가 깨끗한 것을 확인했다.
- 대상: `docs/plan/**`와 계획 파일의 YAML 블록에서 모은 후보 PLAN(등록 전, scratch 사본) (branch `docs/plan`, commit `f58ae45`). 기준: `docs/spec/**`, `agent/config.yaml`, `agent/core/process/*.md`, `agent/core/tools/agent.py`·`validate.py`의 실제 동작, `docs/ARCHITECTURE.md` 11.3·11.7절, `SHARED_ISSUE_STATUS.yaml`, `agent/tasks/*.yaml`
- 요청 요지: spec 요구 중 task가 없는 것, C-01~C-09와 acceptance 대응 누락, 의존 순서 오류, 실행 불가능하거나 약한 acceptance(항상 통과, 이 맥에서 못 돌림, 셸·YAML 이스케이프), scope 누락·과다, 너무 큰 task, 병렬 scope 충돌, 계획 파일과 후보 PLAN 불일치, toy 범위에 비해 과한 계획, SHARED-2·SHARED-3·BOOT-1 완료 처리가 도구 동작과 맞는지. D-01~D-03과 사람 task 없음(D-20, 조율 결정 C-17)은 논쟁 대상에서 뺐다.
- Codex 확인 사항: 후보 PLAN 블록이 계획 파일과 같고 M0·BOOT-1·SHARED-1은 현행 PLAN과 같다. 의존 순환·역전 없음. C-01~C-09가 모두 task acceptance에 연결되어 있다. YAML 파싱과 BSD 도구·셸 이스케이프의 확정적 오류는 없다. Codex 샌드박스에서 `api.github.com`에 접속하지 못해 원격 명령은 Codex가 확인하지 못했다(아래 판정에서 직접 실행).
- 판정 방법: 지적마다 spec·도구 코드를 다시 읽어 확인했다. 후보 PLAN을 임시로 `agent/PLAN.yaml`에 넣어 `validate.py`를 통과시킨 뒤 되돌렸고, 모든 command를 `/bin/sh -n`으로 검사했다. SHARED-2 A1~A3, SHARED-3 A1은 현재 저장소에서 통과, SHARED-5 A1·A3은 현재 실패·가상 채택 사본에서 통과를 확인했다. VIS-1 A3·A4, VIS-2 A1·A7, VIS-3 A7, VIS-4 A3·A4는 scratch의 가짜 파일로 양성·음성을 실행했다(VIS-2 A1은 Shared `d0c997c` INTERFACES의 실제 예시로). 조율 결정 C-03 기준(사실 오류·모순·빈 곳·검증 불가능한 명령은 반영, 운영 수준 요구는 미반영)을 적용했다.
- 결과: 지적 9개. 반영 3, 부분 반영 3, 미반영 3.

| 번호 | 요지 | 판정 | 이유 / 반영 위치 |
|---|---|---|---|
| 1 | README 머리말·6절이 등록·완료·리뷰 기록을 이미 끝난 것으로 적는데 리뷰 시점 저장소는 등록 전 (high) | 미반영 | 계획 문서는 이 PR이 merge될 때의 상태를 적는다(simulator 계획 PR과 같다). 리뷰는 등록 전 commit을 대상으로 했고, 같은 PR에서 등록·완료 기록·이 리뷰 기록이 모두 들어간다. PR 본문에 순서를 적었다 |
| 2 | SHARED-3(`owner: human`) 완료를 agent가 손으로 기록하는 것은 도구의 완료 경로를 우회. BOOT-1 A3도 같음 (high) | 부분 반영 | 사람 task는 도구로 시작할 수 없게 되어 있어(`actionable`) 손 기록 외의 경로가 없다(simulator HUM-1 선례). 대신 사람의 결정이 이미 문서로 남은 경우의 기록 방법(결정 파일에서 acceptance 명령 실행, 결정한 사람·날짜·위치를 PR에 적음, 계획 PR merge가 승인)을 절차 예외로 명시했다. `docs/plan/README.md` 6절 |
| 3 | 같은 PR에서 SHARED-2를 실행하면서 등록 변경을 먼저 commit하는 단계가 없어 `verify`가 거부됨. "task 하나 = PR 하나"와도 다름 (high) | 반영 | 확인했다(`cmd_verify`의 미commit 검사). 등록 변경을 먼저 commit하는 단계와 SHARED-2의 commit 순서를 넣고, 이 PR의 절차 예외(이미 이루어진 일의 완료 기록, SHARED-5 시작 조건)를 명시했다. `docs/plan/README.md` 6절 |
| 4 | 이미 구독 중인 MQTT 3.1.1 client의 `retain == false`로는 retain false 발행을 판별할 수 없음 (medium) | 반영 | 맞다. Broker는 기존 구독자에게 retain 0으로 전달한다. `test_publishes_shared_example`에 "그 뒤 새 구독자가 1초 동안 retained 결과를 받지 않음"을 더했다. `docs/spec/04-verification.md` 3.2절, `docs/plan/02-service.md` VIS-3 A2 |
| 5 | 구독 QoS 1, retained·중복 입력, `MQTT_ERR_NO_CONN`, 구독 거부, 콜백 예외, 끊김 때 기동 확인 파일 삭제가 acceptance에 없음 (medium) | 부분 반영 | 끊김 때 파일 삭제는 기존 재시작 테스트에 한 줄로 확인할 수 있어 더했다(`test_broker_restart_resubscribes`, VIS-3 A4). 나머지는 미반영: retained·중복 입력은 "거르지 않음"(D-13)이라 따로 할 동작이 없고, NO_CONN·구독 거부·콜백 예외는 실제 Broker로 재현하기 어려워 toy 범위(조율 결정 C-00)에 비해 시험 장치가 커진다. 구독 QoS는 결과 도착과 재연결 테스트가 간접으로 본다 |
| 6 | SHARED-2 A2는 rollback의 부분 문자열만 보고, VIS-2 fixture가 Shared 예시와 같다는 자동 증거가 없음 (medium) | 반영 | SHARED-2 A2에 "마지막으로 검증된" 조합 문구 검사를 더했다. VIS-2 A1은 `contract_ref`의 INTERFACES를 원격으로 읽어 JSON 예시 블록과 fixture 세 파일의 값이 같은지 본다(키 순서는 기존 검사). `docs/plan/00-overview.md` SHARED-2 A2, `docs/plan/01-processing.md` VIS-2 A1 |
| 7 | verify 추가 acceptance가 `make` 종료 코드만 봐서 빈 레시피도 통과. C-09는 네 항목 포함만 봄 (medium) | 부분 반영 | `make test`·`make docker-test`·`make smoke` 출력의 pytest 요약이 `N passed`로 시작해야 통과하게 했다(수집 0개·실패 포함이면 실패). C-09는 verify 목록 전체가 spec 04 4절 네 항목과 순서까지 같은지 비교한다. 마커별 수집 대상을 따로 대조하는 검사는 node id acceptance가 이미 테스트 존재를 보장해 더하지 않았다. `docs/plan/03-runtime.md` VIS-1 A5·VIS-4 A7, `docs/plan/02-service.md` VIS-3 A8 |
| 8 | VIS-3이 한 세션 M task로 큼. 기본 발행과 수명 주기·연동 검증으로 나누자 (medium) | 미반영 | spec 00 6절 윤곽이 한 task로 정했고, 비슷한 크기의 simulator SRV-6(MQTT adapter와 Docker 연동 테스트)이 한 세션에 끝났다. 단계 개요가 6개로 8개 한도 안이다. 실행 중 8개를 넘으면 `20-plan.md` 규칙대로 멈추고 분해한다 |
| 9 | `src/**`, `tests/**`, `DECISIONS.md`가 반복되어 scope가 넓음 (low) | 미반영 | spec 00 6절이 정한 glob이다. 모든 task가 순차라 scope 충돌이 없고, 뒤 task가 앞 task 모듈을 이어 쓰므로 파일 단위로 좁히면 정상적인 수정도 멈춤이 된다. spec 수정 범위는 README 5절이 영역 파일과 `DECISIONS.md`로 제한한다 |

## 바뀌지 않은 것

- task 목록, `depends_on`, size, PLAN 순서는 후보와 같다. acceptance가 바뀐 task: SHARED-2(A2), VIS-1(A5), VIS-2(A1), VIS-3(A2, A4, A8), VIS-4(A7). spec 변경: `04-verification.md` 3.2절 두 테스트의 통과 기준.
