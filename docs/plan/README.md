# Vision Inspection 구현 계획

> 상태: Codex 리뷰 반영(`docs/reviews/plan-codex-1.md`), 이 계획 PR에서 `agent/PLAN.yaml`에 등록했다(2026-09-27, 책임자 채팅 승인 spec D-02, 조율 결정 C-01).
> 읽어야 할 때: task를 시작·실행·merge할 때, 다음 task를 고를 때, 계획을 바꿀 때. 무엇을 만드는지는 `docs/spec/README.md`부터.

## 1. 읽는 규칙

1. 이 폴더는 `docs/spec/`과 파일 이름이 같다. 영역 NN을 작업하면 `docs/spec/NN-*.md`와 `docs/plan/NN-*.md`를 같이 읽는다. 어느 파일인지는 2절 표.
2. 계획 파일은 사람이 읽는 원본이고, `agent/PLAN.yaml`은 도구(`agent.py`)가 실행하는 사본이다. 두 곳의 task 블록(id, milestone, type, owner, title, why, depends_on, contract, scope, acceptance, size)과 milestone 블록은 같아야 한다.
3. 다르면 **PLAN.yaml이 이긴다**. 발견한 agent는 작업을 계속하고 PR 본문에 차이를 적는다. 조율 agent가 계획 파일을 PLAN.yaml에 맞게 고친다.
4. 계획 파일의 단계 개요와 "읽을 spec"은 PLAN.yaml에 없다. `20-plan.md`에서 `SESSION.yaml` steps를 쓸 때 출발점으로 쓴다(8개 이하).
5. 설계 결정은 `docs/spec/DECISIONS.md` 하나에 둔다. 이 계획은 새 설계 결정을 만들지 않았다. 절차 근거는 spec D-01~D-05와 조율 결정 C-01·C-05·C-09·C-15·C-17이다.

## 2. task → 계획 파일 → spec

| task | 계획 파일 | 읽을 spec(모두 `docs/spec/`, 절은 계획 파일의 "읽을 spec") |
|---|---|---|
| BOOT-1, SHARED-1·2·3 | `00-overview.md` 4절 | `00-overview.md` 6절, `DECISIONS.md` 1절 (모두 이 계획 PR에서 완료) |
| SHARED-5 | `00-overview.md` 4절 | `DECISIONS.md` D-05, `AGREEMENTS.md` 머리말, `agent/core/process/90-shared.md` 1절 |
| VIS-1 | `03-runtime.md` | `03-runtime.md` 1~4·7절, `02-service.md` 4절, `04-verification.md` 2·3.1절 |
| VIS-2 | `01-processing.md` | `01-processing.md`, `04-verification.md` 2·3.1절 |
| VIS-3 | `02-service.md` | `02-service.md`, `04-verification.md` 2·3.1·3.2절, `AGREEMENTS.md` V-03·V-06·V-07 |
| VIS-4 | `03-runtime.md` | `03-runtime.md` 5~7절, `04-verification.md` 3.3절, `AGREEMENTS.md` V-04·V-05 |
| verify 명령 추가, acceptance 규칙 | `04-verification.md` | `04-verification.md` 4·7절 |
| 단계, 의존, C-xx 대응 | `00-overview.md` | `00-overview.md` |
| 사람 할 일 시점 | `HUMAN.md` | `HUMAN.md` |

모든 task는 `DECISIONS.md`의 관련 항목과 `AGENTS.md`를 따른다. VIS-n은 `contract: [docs/INTERFACES.md, docs/CONVENTIONS.md]`로 SHARED-5가 채택한 `contract_ref`(`d0c997c`)의 Shared 문서를 `90-shared.md` 1절 명령으로 읽는다(spec D-05). `AGREEMENTS.md`는 그 확정본을 이 Component가 어떻게 지키는지의 요약이다.

## 3. 단계와 milestone

단계 = milestone M1~M4(M0은 BOOT-1). 결과, 종료 조건, task, 완료 정의 대응은 `00-overview.md` 1~3절. 조율 agent는 phase마다 새 subagent를 띄운다(조율 결정 C-07).

| phase | task | 새 verify | 필요한 환경 | verify 한 번(추정) |
|---|---|---|---|---|
| M1 | SHARED-5 | 없음 | `gh` 로그인(원격 Shared 읽기) | 1초 미만 |
| M2 | VIS-1 → VIS-2 | `unit` | 인터넷(첫 pip) | 수 초 |
| M3 | VIS-3 | `broker` | Docker Desktop | 약 1분 |
| M4 | VIS-4 | `smoke` | Docker Desktop, 인터넷(첫 이미지 빌드) | 약 1.5분 |

## 4. 실행 순서와 병렬

**한 번에 task 하나, PLAN 순서**다(`00-overview.md` 2절 표 순서). task 하나 = 브랜치 하나 = PR 하나이고, 다음 task는 앞 PR이 merge된 최신 main에서 시작한다. `agent.py start`는 `depends_on`이 모두 `done`일 때만 시작한다.

병렬은 쓰지 않는다. VIS-1~4는 차례로 앞 task의 결과(`src/**`, `tests/**`, `Makefile`, `agent/config.yaml`)를 이어서 쓰므로 scope가 모두 겹치고, SHARED-5는 VIS-1의 선행이다. phase 사이도 순차다.

## 5. task 하나 실행하기 (실행 agent)

실행 agent는 조율 agent가 띄운 subagent 하나이고 phase 안의 task를 하나씩 한다. 먼저 `AGENTS.md`, `agent/core/process/00-session.md`를 읽는다.

```sh
git switch main && git pull --ff-only
git switch -c agent/<ID>
python3 agent/core/tools/agent.py next            # <ID>가 나와야 한다
python3 agent/core/tools/agent.py start <ID>
# plan: 20-plan.md. 계획 파일의 단계 개요로 SESSION.yaml steps 작성(do, check, done: false)
git add agent/SESSION.yaml && git commit -m "<ID>: 계획"
python3 agent/core/tools/agent.py phase execute
# execute: 30-execute.md. step마다 check 실행 → done: true → commit "<ID>: <한 일>"
python3 agent/core/tools/agent.py verify           # 40-verify.md. 실패하면 고치고 commit 뒤 다시(같은 항목 3회까지)
python3 agent/core/tools/agent.py finish
git add agent/tasks/<ID>.yaml agent/SESSION.yaml && git commit -m "<ID>: 완료 기록"
python3 agent/core/tools/validate.py --remote
git push -u origin agent/<ID>
gh pr create --base main --head agent/<ID> --title "<ID>: <title>" --body-file <본문 파일>
gh pr checks <번호> --watch                        # 실패하면 고치고 push
```

- 회고(`agent.py retro`)는 책임자가 요청할 때만 쓴다. 요청이 없으면 verify 다음에 바로 finish.
- commit 메시지: `<ID>: <한 일>`(00-session.md). 서명 줄은 실행 환경이 정한 규칙을 따른다.
- `agent/config.yaml`을 바꾸는 task(VIS-1, VIS-3, VIS-4)는 추가할 명령을 먼저 직접 실행해 통과를 확인한다.
- 임시 파일은 `<scratchpad>/vision-inspection/<task>/` 아래에만 둔다. 컨테이너·프로세스는 이름이나 PID로만 정리하고 넓은 패턴의 `pkill`을 쓰지 않는다(조율 결정 C-11).
- spec을 고쳐야 하면 자기 scope의 spec 파일(영역 파일)과 `DECISIONS.md`만 고친다. 새 결정은 `DECISIONS.md`에 새 ID로 추가한다(spec README 1절 4). `00-overview.md`, `04-verification.md`, `AGREEMENTS.md`, `README.md`, `HUMAN.md`는 고치지 않는다. 영역 파일이라도 `02-service.md` 4절의 `event`·`reason` 값, `03-runtime.md` 2절의 환경 변수 이름, 5절의 `HEALTHCHECK` 뜻은 `AGREEMENTS.md`와 묶여 있어 고치지 않는다(spec README 6절).
- Agent는 PR을 merge하지 않는다. merge는 조율 agent가 한다(spec D-01).

PR 본문:

```markdown
## <ID>: <title>
계획: docs/plan/<파일> · spec: <읽은 spec 절> · contract_ref: <SHA>

### acceptance
| ID | 결과 | 증거 요약(명령 출력 마지막 줄, 측정값) |

### 공통 verify
| name | 결과 | 걸린 시간 |
evidence commit: <SHA> (agent/tasks/<ID>.yaml)

### 바꾼 spec과 새 결정
- docs/spec/…: <무엇을, 왜> / D-xx: <한 줄>

### 계획과 다르게 한 점
- step note 요약. PLAN.yaml과 계획 파일의 차이를 발견했으면 여기에
```

멈출 때(`80-escalate.md`). 이 계획에서 예상되는 경우:

| stops | 예 |
|---|---|
| scope | VIS-4에서 `src/**` 수정이 필요함(smoke가 서비스 결함을 드러냄), 어느 task든 `04-verification.md`·`AGREEMENTS.md`·`00-overview.md` 변경이 필요함 |
| ambiguity | spec 두 곳이 모순, 테스트 기대값이 spec 규칙과 맞지 않음(기대값을 바꾸지 않는다) |
| contract | `contract_ref` 문서가 spec·`AGREEMENTS.md`와 다름, `event`·`reason` 값이나 환경 변수 이름을 바꿔야 함 |
| repeated-failure | 같은 verify 항목 3회, 같은 step 3회 실패. 예: C-07 시간 상한, 재연결 15초 |
| tool | Docker·네트워크·`gh`를 쓸 수 없음(H-1), `paho-mqtt==2.1.0`·`pytest==9.1.1`을 설치할 수 없음 |

절차: 변경을 commit → `python3 agent/core/tools/agent.py block --reason "<stops>: <무엇이 막혔나>" --unblock-when "<해제 조건>" --owner "<조율 agent 또는 책임자>"` → commit(`<ID>: block`) → push → draft PR 본문에 질문과 선택지 → 조율 agent에 보고. 다른 task로 넘어가지 않는다(다음 task는 조율 agent가 고른다).

## 6. 조율 agent

- 시작 전: `HUMAN.md`의 H-1 조건 확인(다음 phase에 Docker·인터넷이 필요한지). 3절 표.
- merge 조건(spec D-01): PR에 `agent/tasks/<ID>.yaml`이 `status: done`으로 있고, `Validate Component / validate` CI가 통과했고, PR 본문의 acceptance·verify가 모두 pass다. 그 뒤 main에 merge하고 다음 task를 최신 main에서 띄운다.
- merge 방식은 merge commit(`gh pr merge <번호> --merge`)이다. squash·rebase는 쓰지 않는다: `agent/tasks/<ID>.yaml`의 `commit`(evidence commit)이 main 이력에 남아야 한다(조율 결정 C-01).
- block을 받으면: 해제 조건을 해결한다(계획 수정 PR, FIX task 추가, spec 수정 task). 해결되면 `agent/tasks/<ID>.yaml`을 지워 다시 연다.
- FIX task: 발견된 결함은 해당 영역의 `type: fix` task(ID `FIX-<번호>`, 결함이 드러난 milestone, scope는 그 영역, acceptance는 command)로 추가한다(spec 00 6절). `proposed` 없이 넣는다(spec D-02).
- 사람 task는 없다. VIS-4 merge가 이 Component의 완료다(spec 00 2절 C-01~C-09). 그 뒤 integration이 `AGREEMENTS.md` V-04~V-07을 맞추도록 조율 agent가 전달한다.

### 등록 (완료: 이 계획 PR에 포함)

책임자의 채팅 지시(spec D-02, 조율 결정 C-01)를 근거로 계획과 같은 PR에서 했다. 바꾼 파일은 `agent/PLAN.yaml`, `agent/tasks/BOOT-1.yaml`, `agent/tasks/SHARED-3.yaml`, `agent/tasks/SHARED-2.yaml`, `.github/CODEOWNERS`, `docs/ARCHITECTURE.md` 11.7절 표.

1. `agent/PLAN.yaml`: 머리 주석에 승인 근거. M1의 exit criteria를 `00-overview.md` 1절 블록으로 바꾸고 M2~M4를 추가한다. SHARED-2·SHARED-3·SHARED-5를 `00-overview.md` 4절 블록으로 바꾸고(manual → command, D-03), VIS-1~4 블록을 `00-overview.md` 2절 표 순서로 붙인다. 모두 `proposed` 없음.
2. `agent/tasks/BOOT-1.yaml`: `status: verifying`(A3 pending)을 `status: done`으로. `commit`은 그대로, `finished_at` 추가, `checks` 모두 `pass`. 근거 D-02, 조율 결정 C-09(simulator 선례).
3. `agent/tasks/SHARED-3.yaml`(`owner: human`, 도구로 시작할 수 없음): A1 명령을 main `d3a1611`의 `docs/ARCHITECTURE.md`에서 실행해 통과를 확인하고 `status: done`, `commit: <그 main commit>`, `finished_at`, `checks: {A1: pass}`로 쓴다(simulator HUM-1 기록과 같은 모양).
4. SHARED-2를 도구 절차로 실행한다: `agent.py start SHARED-2` → steps(11.7절 task 표 갱신) → `verify`(A1~A3, `agent-files`) → `finish`.
5. `.github/CODEOWNERS`: `* @<component-책임자>`를 `* @dltndn`으로(조율 결정 C-15).
6. `python3 agent/core/tools/validate.py --remote`와 `python3 agent/core/tools/agent.py next`(SHARED-5가 나와야 한다).

## 7. 계획 바꾸기

- 계획 변경은 계획 파일과 `agent/PLAN.yaml`을 같은 PR에서 고친다. 결정이면 `docs/spec/DECISIONS.md`에 새 ID를 추가한다.
- 실행 agent는 승인된 task의 acceptance·check·scope를 바꾸지 않는다(`20-plan.md`). 필요하면 멈추고, 조율 agent가 계획 변경 PR을 올린다.
- 새 task는 `proposed` 없이 넣는다(spec D-02).
