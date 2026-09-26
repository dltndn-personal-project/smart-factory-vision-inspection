# 00 계획 개요

> 목적: 단계(= milestone M0~M4)의 결과와 종료 조건, 모든 task의 의존 관계, 완료 정의 C-01~C-09를 어느 task가 만족시키는지 정한다. M0·M1 task(BOOT-1, SHARED-n)의 PLAN 정의도 여기에 둔다.
> 읽어야 할 때: 계획을 등록·수정할 때, 다음에 무엇을 할지 정할 때, milestone 완료를 판단할 때, SHARED-5를 실행할 때. 같이 읽을 spec: `docs/spec/00-overview.md`, `docs/spec/DECISIONS.md` 1절.

## 1. 단계

단계 하나가 milestone 하나다. spec 00 6절의 milestone 이름을 그대로 쓴다. 사람 task milestone은 없다(spec D-20, 조율 결정 C-17).

| 단계 | 결과 | task | 종료 조건 요약 | 새 verify 명령 |
|---|---|---|---|---|
| M0 bootstrap | 도메인 슬롯과 첫 verify | BOOT-1 | COMPONENT.md 미정 없음, `agent-files` | `agent-files` (이 계획 PR) |
| M1 Shared 계약 | `d0c997c`를 `contract_ref`로 채택 | SHARED-1·2·3(완료), SHARED-5 | C-01 | 없음 |
| M2 처리 코어 | 설정·로그·검증·조회·조립이 paho 없이 단위 테스트로 확인됨 | VIS-1, VIS-2 | C-02, C-03, C-07(단위) | `unit` |
| M3 MQTT 서비스 | 실제 Mosquitto에서 받고 발행하는 서비스 | VIS-3 | C-04, C-05, C-06, C-07(연동) | `broker` |
| M4 패키징 | 컨테이너와 단독 compose, smoke 자동 확인 | VIS-4 | C-08, C-09 | `smoke` |

PLAN.yaml에 넣을 milestone 블록(M0은 그대로 둔다. M1은 이미 이루어진 게시를 반영해 exit criteria를 바꾼다. D-02·D-03):

```yaml
  - id: M1
    outcome: Vision pass-through에 필요한 Shared 계약 변경(Shared PR #6, merge commit d0c997c)이 게시·merge되었고, 이 Component가 그 commit을 contract_ref로 채택한다
    exit_criteria:
      - I-1·I-4 MESSAGE와 DOC-1 DOCUMENT_CHANGE(ISSUE-c8fad59b)가 Shared main에 merge되어 있고 SHARED_ISSUE_STATUS.yaml에 기록되어 있다 (SHARED-1, SHARED-2)
      - SHARED_CONFIG.json의 contract_ref가 d0c997c97129141d9853a42ce6e0d1f8f7309ae9이고 validate.py --remote가 통과한다 (C-01, SHARED-5)
      - docs/ARCHITECTURE.md 상단에 채택 기록이 있고 4절 첫 문단이 채택한 contract_ref 기준이다 (SHARED-5)
  - id: M2
    outcome: 설정·로그, Product Created 검증, Ground Truth 조회, Vision Result 조립이 paho 없이 동작하고 단위 테스트로 확인된다
    exit_criteria:
      - make test가 통과하고 C-02(Shared 예시와 같은 dict·키 순서), C-03(미발행 reason 9개), C-07 단위(1,800줄 평균 50 ms 이하) 테스트가 그 안에 있다
      - payload·ground_truth·process 모듈이 paho를 import하지 않는다
      - agent/config.yaml verify에 unit이 있다
  - id: M3
    outcome: python -m vision_inspection이 실제 Mosquitto에서 Product Created를 받아 Vision Result를 발행하고, 재연결·종료·설정 오류를 spec대로 처리한다
    exit_criteria:
      - make docker-test가 통과하고 C-04(발행·미발행), C-05(재연결 15초, SIGTERM 종료 코드 0, 설정 오류 2), C-06(로그 형식), C-07 연동(30개 지연 최대 2초·중앙값 0.5초 이하) 테스트가 그 안에 있다
      - paho를 import하는 모듈은 app.py 하나다
      - agent/config.yaml verify에 broker가 있다
  - id: M4
    outcome: 저장소 루트의 Dockerfile과 compose.yaml로 컨테이너가 healthy가 되고, 읽기 전용 /data의 Ground Truth로 결과를 발행하는 것을 smoke가 자동으로 확인한다
    exit_criteria:
      - make smoke가 통과한다 (C-08)
      - agent/config.yaml verify에 spec 04 4절 네 항목(agent-files, unit, broker, smoke)이 있고 모두 통과한다 (C-09)
      - docs/COMPONENT.md 실행 절이 실제 실행 방법과 같다
```

## 2. task 목록과 의존

PLAN 순서(= `agent.py next`의 우선순위). 모두 순서대로 하나씩 한다(`README.md` 4절).

| # | task | 단계 | 선행 | size | 상태·내용 | 계획 파일 |
|---|---|---|---|---|---|---|
| 1 | BOOT-1 | M0 | - | M | 이 계획 PR에서 완료(A3는 D-02로 갈음) | 이 파일 4절 |
| 2 | SHARED-1 | M1 | - | S | 완료(PR #4) | 이 파일 4절(변경 없음) |
| 3 | SHARED-2 | M1 | SHARED-1, SHARED-3 | S | 이 계획 PR에서 완료 기록(A2 자동 검사로 교체) | 이 파일 4절 |
| 4 | SHARED-3 | M1 | - | S | `owner: human`. 이 계획 PR에서 완료 기록(A1 자동 검사로 교체) | 이 파일 4절 |
| 5 | SHARED-5 | M1 | SHARED-2 | S | `contract_ref` 채택. **첫 구현 task** | 이 파일 4절 |
| 6 | VIS-1 | M2 | SHARED-5 | M | 골격, `config`, `logs`, `Makefile`, verify `unit` | `03-runtime.md` |
| 7 | VIS-2 | M2 | VIS-1 | M | `payload`, `ground_truth`, `process`, Shared 예시 fixture | `01-processing.md` |
| 8 | VIS-3 | M3 | VIS-2 | M | `app`, `__main__`, Docker 연동 테스트, verify `broker` | `02-service.md` |
| 9 | VIS-4 | M4 | VIS-3 | M | `Dockerfile`, `compose.yaml`, smoke, verify `smoke` | `03-runtime.md` |

```text
BOOT-1 (done)
SHARED-1 (done) ─┐
SHARED-3 (done) ─┴─▶ SHARED-2 (done) ─▶ SHARED-5 ─▶ VIS-1 ─▶ VIS-2 ─▶ VIS-3 ─▶ VIS-4
```

- VIS-1은 SHARED-5 뒤에 시작한다(spec D-05: 구현 task는 채택한 `contract_ref`로 Shared 문서를 읽는다). SHARED-5에 필요한 Shared 확정(`d0c997c`)은 이미 main에 있어 기다릴 것이 없다.
- VIS-n은 앞 task의 모듈과 `Makefile`·`agent/config.yaml`을 이어서 쓰므로 scope가 겹친다. 병렬 없음.

## 3. 완료 정의 대응

모든 C-xx가 하나 이상의 task acceptance로 덮인다. "테스트"는 acceptance가 가리키는 이름 붙은 pytest node id다(spec 04 7절).

| ID | 확인 | task(acceptance) |
|---|---|---|
| C-01 | `contract_ref`가 `d0c997c…`이고 `validate.py --remote` 통과 | SHARED-5(A1, A2) |
| C-02 | Shared 예시로 만든 결과가 예시 Vision Result와 같은 dict·키 순서 | VIS-2(A1 fixture 모양, A2 `test_build_matches_shared_example`, `test_encoded_key_order_matches_shared_example`), VIS-3(A2 실제 Broker) |
| C-03 | 미발행 `reason` 9개가 해당 입력에서 나오고 결과 없음 | VIS-2(A3 검증, A4 Ground Truth, A5 `test_each_reason`), VIS-3(A3 `test_invalid_inputs_not_published`) |
| C-04 | 실제 Mosquitto에서 하나에 하나, QoS 1·retain false, 잘못된 입력은 없음 | VIS-3(A2, A3), VIS-4(A1 smoke) |
| C-05 | 재연결·재구독 15초, SIGTERM 5초 안 종료 코드 0, 설정 오류 2 | VIS-3(A1 `test_invalid_config_exits_2`, A4), VIS-4(A1 smoke 8단계 `stop` 종료 코드 0) |
| C-06 | stdout 모든 줄이 JSON, `event`·`reason`이 표 안 | VIS-1(A2 `test_logs.py`), VIS-3(A2~A5: 모든 docker 테스트의 `service` 정리 단계 검사), VIS-4(A1 smoke 7단계) |
| C-07 | 단위 평균 50 ms, 연동 최대 2초·중앙값 0.5초 | VIS-2(A6 `test_mean_time_1800_lines`), VIS-3(A5 `test_latency_1800_lines`) |
| C-08 | `up -d --build --wait` healthy, `/data` `RW=false`, 결과 발행 | VIS-4(A1 `test_compose_smoke`, A3 compose 정의) |
| C-09 | COMPONENT.md 미정 없음, verify 네 항목 모두 통과 | BOOT-1(A1, A2), VIS-4(A6, A7) |

한 번 들어간 verify 명령은 이후 모든 task에서 돈다. 그래서 C-02·C-03·C-07 단위(`unit`), C-04~C-07 연동(`broker`), C-08(`smoke`)은 해당 task 뒤의 모든 변경에서 다시 확인된다.

## 4. M0·M1 task

### BOOT-1 (이 계획 PR에서 완료)

PLAN 블록은 바꾸지 않는다(simulator 선례와 같이 A3 `manual`을 남긴다). 이 계획 PR에서 도구 절차로 실행했다: `agent.py start BOOT-1` → steps 2개(COMPONENT.md 작성, verify `agent-files` 추가) → `verify`(A1·A2·`agent-files` pass, A3 pending) → `finish`(`status: verifying`). 등록 단계에서 `agent/tasks/BOOT-1.yaml`을 `status: done`, A3 `pass`, `finished_at`으로 바꾼다. 근거는 D-02(책임자 채팅 승인이 PLAN 승인)와 조율 결정 C-09다.

### SHARED-1 (완료, 변경 없음)

`agent/tasks/SHARED-1.yaml` `status: done`(PR #4). PLAN 블록은 그대로다.

### SHARED-3 (이 계획 PR에서 완료 기록)

사용자가 2026-09-27 D-6을 (b) Ground Truth 파일 읽기로 다시 결정했고 `docs/ARCHITECTURE.md` 11.3절에 적혀 있다. A1의 `manual`을 같은 사실을 보는 `command`로 바꾼다(D-03). `owner: human` task라 도구로 시작할 수 없으므로, 등록 단계에서 A1 명령을 실행해 통과를 확인하고 `agent/tasks/SHARED-3.yaml`을 손으로 쓴다(simulator HUM-1 기록과 같은 모양: `status: done`, `commit`은 확인한 main commit, `finished_at`, `checks: {A1: pass}`).

```yaml
  - id: SHARED-3
    milestone: M1
    type: chore
    owner: human
    title: Vision이 불량 정보를 받는 경로 결정
    why: Shared ISSUE-9f81b8ac가 Product Created에서 결함 정보를 빼고 ground_truth/products.jsonl을 평가·검증 전용으로 정해, 2026-09-24 결정 D-6(별도 Topic)을 다시 판단해야 했다. 2026-09-27 사용자가 (b) Ground Truth 파일 읽기로 결정했다
    depends_on: []
    scope: [docs/ARCHITECTURE.md]
    acceptance:
      - id: A1
        text: 사용자의 전달 경로 결정((b) Ground Truth 파일 읽기)과 날짜가 docs/ARCHITECTURE.md 11.3절 D-6 재결정 항목에 적혀 있다 (manual에서 바꿈, spec D-03)
        check: {type: command, run: "grep -Eq '^\\| D-6 재결정 \\| .*\\[결정\\] \\(b\\)\\*\\* \\(사용자, 2026-09-27\\)' docs/ARCHITECTURE.md"}
    size: S
```

### SHARED-2 (이 계획 PR에서 완료 기록)

DOC-1(`ISSUE-c8fad59b`)은 Shared PR #6으로 merge되었고(merge commit `d0c997c`), 게시 기록(`docs/ARCHITECTURE.md` 11.7절)과 `SHARED_ISSUE_STATUS.yaml` 기록은 SHARED-1 PR에서 함께 남겼다. A2의 `manual`(DOC-1 본문을 D-11과 A§19 복구 방법에 대조)을 Shared `d0c997c`의 Issue 본문을 원격으로 읽어 같은 내용을 보는 `command`로 바꾼다(D-03). 등록 단계에서 도구 절차(`start` → steps → `verify` → `finish`)로 실행한다. 바꿀 파일은 11.7절의 task 상태 표(SHARED-2·SHARED-3 행을 완료로)뿐이다.

```yaml
  - id: SHARED-2
    milestone: M1
    type: chore
    title: DOC-1 범위 축소·Ground Truth 입력 경로·Vision Result 확정 DOCUMENT_CHANGE 게시, 게시 후 기록
    why: I-1의 범위 축소(D-1, D-2, D-11), 입력 경로(D-6 재결정), 출력 결정(D-7~D-10)을 계약 문서 수정과 함께 한 번에 올린다. 입력 경로 없이는 Vision Result를 발행할 수 없다 (2026-09-27 사용자 지시, Shared PR #6. 닫힌 PR #5 대체)
    depends_on: [SHARED-1, SHARED-3]
    scope: [docs/ARCHITECTURE.md, SHARED_ISSUE_STATUS.yaml]
    acceptance:
      - id: A1
        text: DOC-1 DOCUMENT_CHANGE가 Shared main의 issues/index.json에 등록되어 있고 ID가 ARCHITECTURE.md 게시 기록에 적혀 있다
        check: {type: command, run: "index=$(gh api \"repos/$(jq -r .repository SHARED_CONFIG.json)/contents/issues/index.json\" -H 'Accept: application/vnd.github.raw+json') && for key in DOC-1; do id=$(grep -Eo \"^- $key: ISSUE-[0-9A-Fa-f-]{36}\" docs/ARCHITECTURE.md | cut -d' ' -f3) && test -n \"$id\" && printf '%s' \"$index\" | jq -e --arg id \"$id\" 'any(.issues[]; .issue_id == $id and .type == \"DOCUMENT_CHANGE\")' >/dev/null || exit 1; done"}
      - id: A2
        text: Shared d0c997c의 DOC-1 본문에서 change.after 또는 compatibility에 현재 범위 제외와 "복귀는 새 DOCUMENT_CHANGE로 제안"(D-11)이 있고, transition.rollback에 A§19 복구 방법(19절, 계약 commit 8b1efb0으로 되돌림)이 있다 (manual에서 바꿈, spec D-03)
        check: {type: command, run: "id=$(grep -Eo '^- DOC-1: ISSUE-[0-9A-Fa-f-]{36}' docs/ARCHITECTURE.md | cut -d' ' -f3) && test -n \"$id\" && gh api --method GET \"repos/$(jq -r .repository SHARED_CONFIG.json)/contents/issues/$id.yaml\" -f ref=d0c997c97129141d9853a42ce6e0d1f8f7309ae9 -H 'Accept: application/vnd.github.raw+json' | python3 -c \"import sys, yaml; d = yaml.safe_load(sys.stdin); c = d['change']['after'] + d['compatibility']; r = d['transition']['rollback']; sys.exit(not ('현재 범위' in c and '새 DOCUMENT_CHANGE' in c and '19절' in r and '8b1efb06325f711814152f4867d86e4413b4a404' in r))\""}
      - id: A3
        text: 게시한 DOC-1이 90-shared.md 2·4절에 따라 SHARED_ISSUE_STATUS.yaml에 기록되어 있고 원격 검사를 통과한다
        check: {type: command, run: "python3 -c \"import re, sys, yaml; doc = open('docs/ARCHITECTURE.md', encoding='utf-8').read(); status = (yaml.safe_load(open('SHARED_ISSUE_STATUS.yaml')) or {}).get('issues') or {}; ids = [re.search(r'^- ' + k + r': (ISSUE-[0-9A-Fa-f-]{36})', doc, re.M) for k in ['DOC-1']]; sys.exit(not all(m and m.group(1) in status for m in ids))\" && python3 agent/core/tools/validate.py --remote"}
    size: S
```

### SHARED-5 `contract_ref` 채택 (첫 구현 task)

```yaml
  - id: SHARED-5
    milestone: M1
    type: chore
    title: Shared d0c997c를 contract_ref로 채택하고 ARCHITECTURE.md에 기록
    why: 구현은 Shared 승인 뒤에 한다(U-12). 이 Component가 쓰는 Interface가 모두 확정된 Shared d0c997c를 contract_ref로 고정해야 VIS-n이 contract 필드로 계약 문서를 읽을 수 있다 (spec D-05, C-01, 조율 결정 C-05)
    depends_on: [SHARED-2]
    contract: [docs/ARCHITECTURE.md, docs/INTERFACES.md, docs/CONVENTIONS.md]
    scope: [SHARED_CONFIG.json, docs/ARCHITECTURE.md]
    acceptance:
      - id: A1
        text: SHARED_CONFIG.json의 contract_ref가 d0c997c97129141d9853a42ce6e0d1f8f7309ae9이고 repository·component·process_ref는 바뀌지 않았다 (C-01)
        check: {type: command, run: "test \"$(jq -r .contract_ref SHARED_CONFIG.json)\" = d0c997c97129141d9853a42ce6e0d1f8f7309ae9 && test \"$(jq -r '.repository + \" \" + .component + \" \" + .process_ref' SHARED_CONFIG.json)\" = 'dltndn-personal-project/smart-factory-shared-repository vision-inspection 6bcd2aad8e374a7e96f816051585a49cb5e30f86'"}
      - id: A2
        text: 저장소 검사가 원격 비교까지 통과한다 (C-01)
        check: {type: command, run: "python3 agent/core/tools/validate.py --remote"}
      - id: A3
        text: docs/ARCHITECTURE.md 상단에 채택 기록 줄("> - **contract_ref 채택 (SHARED-5)**:" 뒤에 전체 SHA)이 있고, 4절 첫 문단이 contract_ref를 null로 적지 않고 채택한 SHA를 적는다 (manual에서 바꿈, spec D-03)
        check: {type: command, run: "grep -Eq '^> - \\*\\*contract_ref 채택 \\(SHARED-5\\)\\*\\*: .*d0c997c97129141d9853a42ce6e0d1f8f7309ae9' docs/ARCHITECTURE.md && sec=$(sed -n '/^## 4\\./,/^### 4\\.1/p' docs/ARCHITECTURE.md) && printf '%s' \"$sec\" | grep -q d0c997c97129141d9853a42ce6e0d1f8f7309ae9 && ! printf '%s' \"$sec\" | grep -q null"}
    size: S
```

단계 개요:
1. `90-shared.md` 1절 명령이 쓰는 형식으로 `SHARED_CONFIG.json` `contract_ref`만 바꾼다. → A1
2. 1절 명령으로 `d0c997c`의 `docs/INTERFACES.md`, `docs/CONVENTIONS.md`, `docs/ARCHITECTURE.md`를 원격으로 읽어, Vision 관련 절(Product Created, Vision Result, Image Reference, Ground Truth, CONVENTIONS)이 spec `AGREEMENTS.md`의 요약과 다르지 않은지 확인한다. 다르면 멈춘다(`README.md` 5절 멈춤 표 contract).
3. `docs/ARCHITECTURE.md`: 상단 인용 블록 끝에 `> - **contract_ref 채택 (SHARED-5)**: <날짜> Shared d0c997c97129141d9853a42ce6e0d1f8f7309ae9를 contract_ref로 채택했다 …` 한 줄, 4절 첫 문단의 "아직 null" 문장을 채택 사실로, 11.6절·11.7절 task 표의 SHARED-5 상태를 완료로. 이력 문단은 고치지 않는다. → A3
4. `validate.py --remote`. → A2

읽을 spec: `DECISIONS.md` D-05, `AGREEMENTS.md` 머리말, `agent/core/process/90-shared.md` 1절.

- `SHARED_ISSUE_STATUS.yaml`의 `contract_ref: null` 기록은 바꾸지 않는다. 검토 당시의 값이고, Shared Issue 재검토는 사용자가 요청할 때만 한다(AGENTS.md Shared 절).
