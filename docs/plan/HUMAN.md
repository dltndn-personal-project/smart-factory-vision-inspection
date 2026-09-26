# 사람이 할 일의 시점

> 목적: spec `HUMAN.md`의 H-1이 계획의 어느 시점에 필요한지 적는다. 방법과 건너뛸 때의 영향은 spec `HUMAN.md`가 원본이다(여기서 반복하지 않는다).
> 읽어야 할 때: 조율 agent가 다음 phase를 시작하기 전, 책임자가 언제 무엇을 해야 하는지 볼 때.

사람 확인 task는 없다(spec D-20, 조율 결정 C-17). 계획 승인은 책임자 채팅 지시로 갈음했다(spec D-02).

| ID | 계획에서의 시점 | 필요한 task | 준비가 안 됐을 때 |
|---|---|---|---|
| 등록 | 이 계획 PR의 merge. SHARED-5 전 | 모든 task | 이 PR이 main에 merge되어야 `agent.py next`가 SHARED-5를 고른다 |
| H-1 | 계속. 특히 아래 task를 시작하기 전 | 아래 표 | 해당 task의 verify가 실패해 task가 멈춘다(`README.md` 5절 tool). 잘못 통과하지는 않는다 |

## H-1이 특히 필요한 시점

| 시작 전 task | 필요한 것 | 이유 |
|---|---|---|
| SHARED-5 | `gh auth status` 로그인, Shared 저장소 읽기 권한 | 계약 문서 원격 읽기, `validate.py --remote` |
| VIS-1 | 인터넷(pip: `paho-mqtt`, `pytest`) | 첫 `make venv` |
| VIS-3 | Docker Desktop 실행 | Docker Mosquitto 연동 테스트. 이후 모든 task의 verify에 `broker`가 들어간다 |
| VIS-4 | Docker Desktop, 인터넷(Docker Hub `python:3.12-slim-bookworm`, 이미지 안 pip) | 이미지 빌드와 smoke |
| 모든 task | `gh auth status` 로그인 | push, PR, `validate.py --remote` |
