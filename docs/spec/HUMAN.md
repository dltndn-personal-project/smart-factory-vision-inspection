# 사람이 할 일

> 목적: 프로젝트 완료까지 책임자(사람)만 할 수 있는 일을 최소로 모은다. 그 밖의 결정과 작업은 agent가 하고, merge는 조율 agent가 한다(`DECISIONS.md` 1절).
> 읽어야 할 때: 책임자가 무엇을 언제 해야 하는지 볼 때, 계획 작업이 사람 task를 만들 때.

| ID | 무엇 | 언제 |
|---|---|---|
| H-1 | agent 작업 환경 유지 | 구현 기간 내내 |

사람 확인 task는 없다(`DECISIONS.md` D-20). 교차 Component 약속(`AGREEMENTS.md`)은 Shared 확정본을 따르고 Shared에 새로 올릴 것이 없어, 반영 요청도 없다. integration이 V-04~V-07을 맞추는 것은 조율 agent가 integration spec 단계에서 전달한다(조율 결정 C-06).

## H-1 agent 작업 환경 유지

- 방법: 맥북에서 Docker Desktop을 켜 두고 `gh auth status`가 로그인 상태이게 한다. 첫 의존 설치와 이미지 빌드에 인터넷이 필요하다(pip의 `paho-mqtt`·`pytest`, Docker Hub의 `python:3.12-slim-bookworm`. `eclipse-mosquitto:2.1.2-alpine`은 이 맥에 이미 있다).
- 건너뛰면: `broker`·`smoke` 검증이 실패해 VIS-3·VIS-4가 멈춘다(건너뛰어 통과하지는 않는다, `04-verification.md` 1절). `gh`가 로그아웃되면 SHARED-5의 원격 검사(`validate.py --remote`)와 PR 생성이 실패한다.
