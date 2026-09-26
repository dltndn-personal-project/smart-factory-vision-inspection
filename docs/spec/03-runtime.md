# 03 실행 환경

> 목적: 디렉터리 구조, 의존성, 설정(환경 변수), `Makefile`, 로컬 실행, `Dockerfile`, 단독 확인용 `compose.yaml`을 정한다.
> 읽어야 할 때: 골격(VIS-1), 설정 키를 추가할 때, 패키징(VIS-4), integration이 실행 정의를 만들 때(`AGREEMENTS.md` V-05와 함께).

## 1. 디렉터리 구조

```text
src/vision_inspection/
  __init__.py
  __main__.py        # main(): 설정 → 로그 → app 실행 → 종료 코드 (02 6절)
  config.py          # Config, load_config, ConfigError (2절)
  logs.py            # iso_ms, Logger (02 4절)
  payload.py         # ProductCreated, Rejected, parse_product_created, build_vision_result, encode (01 2·4절)
  ground_truth.py    # GroundTruth, Lookup, lookup (01 3절)
  process.py         # Publish, Drop, process (01 1절)
  app.py             # paho client와 콜백. paho를 import하는 유일한 모듈 (02 1~3·5절)
tests/
  conftest.py        # 공용 fixture (04 2절)
  fixtures/          # Shared d0c997c 예시 payload
  test_*.py
pyproject.toml       # pytest 설정만 (패키지 빌드 설정 없음)
requirements.txt     # 런타임 직접 의존
requirements-dev.txt # -r requirements.txt + 테스트 의존
Makefile
Dockerfile
.dockerignore
compose.yaml         # 단독 확인·smoke용. 시스템 compose는 integration 소유
.env.example
.gitignore
```

- 패키지는 설치하지 않고 `PYTHONPATH=src`로 import한다(`DECISIONS.md` D-18). pytest는 `pyproject.toml`의 `pythonpath`, 컨테이너는 `ENV PYTHONPATH`, 로컬 실행은 명령 앞의 환경 변수로 준다.

## 2. 설정

환경 변수만 쓴다. 설정 파일은 없다. `load_config(env: Mapping[str, str]) -> Config`(frozen dataclass)가 읽고 검증한다.

| 환경 변수 | 기본값 | 검증 | `Config` 필드 |
|---|---|---|---|
| `MQTT_URL` | `mqtt://mosquitto:1883` | `re.fullmatch(r"mqtt://([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?", v)`, 포트 1~65535, 생략 시 1883 | `mqtt_url`, `mqtt_host`, `mqtt_port` |
| `MQTT_CLIENT_ID` | `vision-inspection` | `re.fullmatch(r"[A-Za-z0-9_-]{1,64}", v)` | `client_id` |
| `PRODUCT_CREATED_TOPIC` | `factory/product/created` | `re.fullmatch(r"[a-z0-9_]+(/[a-z0-9_]+)*", v)`, 256자 이하(CONVENTIONS: `/`로 구분한 소문자) | `product_created_topic` |
| `VISION_RESULT_TOPIC` | `factory/vision/result` | 같음. `PRODUCT_CREATED_TOPIC`과 같으면 오류(자기 결과를 다시 받아 끝없이 재발행하기 때문이다. Vision Result도 Product Created 검증을 통과한다) | `vision_result_topic` |
| `IMAGE_ROOT` | `/data` | 빈 문자열이 아님. 상대 경로면 현재 폴더 기준. 존재 여부는 보지 않는다 | `image_root: Path`, `ground_truth_path: Path`(`image_root / "ground_truth" / "products.jsonl"`) |
| `LOG_LEVEL` | `INFO` | 대소문자 무시 `DEBUG`, `INFO`, `WARNING`, `ERROR` | `log_level`(대문자) |
| `HEALTH_FILE` | `/tmp/vision-inspection.connected` | 빈 문자열이 아님 | `health_file: Path` |

- 변수가 없으면 기본값, 있는데 빈 문자열이면 설정 오류다(`DECISIONS.md` D-19).
- 설정 오류는 `ConfigError("<변수 이름>: <이유>")`이고 종료 코드 2로 끝난다(`02-service.md` 6절). 여러 개가 틀려도 첫 번째만 보고한다(위 표 순서).
- `IMAGE_ROOT`나 Ground Truth 파일이 아직 없는 것은 설정 오류가 아니다. 메시지를 처리할 때 `ground_truth_unreadable`이 된다.
- 기본값은 컨테이너 기준이다. 호스트에서 실행할 때는 `MQTT_URL`, `IMAGE_ROOT`를 준다.

## 3. 의존성

| 파일 | 내용 |
|---|---|
| `requirements.txt` | `paho-mqtt==2.1.0` |
| `requirements-dev.txt` | `-r requirements.txt`, `pytest==9.1.1` |

- 직접 의존만 `==`로 고정한다(`DECISIONS.md` D-06). 2026-09-27 이 맥에서 두 버전을 venv에 설치해 import를 확인했다. 조합이 동작하지 않으면 동작하는 가장 최신 조합으로 바꾸고 PR 본문에 적는다.
- 표준 라이브러리 밖의 의존을 더 추가하지 않는다(JSON Schema 라이브러리, pydantic, 로깅 라이브러리 없음).

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "--strict-markers"
markers = [
  "docker: Docker로 Mosquitto를 띄우는 연동 테스트",
  "smoke: compose로 컨테이너 이미지를 빌드해 확인하는 테스트",
]
```

## 4. `Makefile`과 로컬 실행

저장소 루트 `Makefile`(macOS 기본 GNU Make 3.81, 레시피 들여쓰기는 탭):

| 대상 | 하는 일 |
|---|---|
| `venv` | `.venv/.installed`가 `requirements.txt`·`requirements-dev.txt`보다 오래됐거나 없으면 `python3 -m venv .venv && .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements-dev.txt && touch .venv/.installed` |
| `test` | `venv` 후 `.venv/bin/python -m pytest -q -m "not docker and not smoke"` |
| `docker-test` | `venv` 후 `.venv/bin/python -m pytest -q -m docker` |
| `smoke` | `venv` 후 `.venv/bin/python -m pytest -q -m smoke` |

- `test`는 VIS-1, `docker-test`는 VIS-3, `smoke`는 VIS-4가 추가한다. `.PHONY`로 선언한다.
- `venv` 레시피의 첫 줄은 `python3 -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))'`다. `python3`이 3.12가 아니면 venv를 만들기 전에 실패한다. 이 맥의 `python3`은 3.12.13이다.

로컬 실행(Docker 없이, 개발용):

```sh
make venv
docker compose up -d mosquitto                       # broker만 (127.0.0.1:1883)
mkdir -p data/ground_truth                           # 필요하면 Ground Truth 줄을 직접 넣는다
PYTHONPATH=src MQTT_URL=mqtt://127.0.0.1:1883 IMAGE_ROOT=./data HEALTH_FILE=/tmp/vis-dev.connected \
  .venv/bin/python -m vision_inspection
```

## 5. `Dockerfile`

저장소 루트 `Dockerfile`:

```dockerfile
FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src \
    IMAGE_ROOT=/data HEALTH_FILE=/tmp/vision-inspection.connected
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
HEALTHCHECK --interval=3s --timeout=2s --start-period=10s --retries=3 \
  CMD test -f "$HEALTH_FILE"
ENTRYPOINT ["python", "-m", "vision_inspection"]
```

- 기반 이미지는 factory-simulator와 같다. root로 실행한다(볼륨 파일 권한 문제를 피한다. simulator D-34와 같음).
- 이미지 안에 `/data`를 만들지 않는다. 빈 named volume을 처음 마운트할 때 이미지 내용이 볼륨으로 복사되지 않게 하기 위해서다(`DECISIONS.md` D-17).
- `EXPOSE`, 포트 없음. HTTP를 열지 않는다.
- `.dockerignore`: `.git`, `.venv`, `**/__pycache__`, `.pytest_cache`, `tests`, `docs`, `agent`, `data`, `.env`.
- 이미지 이름: 로컬 빌드는 `vision-inspection:local`.

## 6. 단독 확인용 `compose.yaml`

```yaml
name: vision-inspection
services:
  mosquitto:
    image: eclipse-mosquitto:2.1.2-alpine
    command: ["mosquitto", "-c", "/mosquitto-no-auth.conf"]
    ports: ["127.0.0.1:${VIS_MQTT_PORT:-1883}:1883"]
  vision-inspection:
    build: .
    image: vision-inspection:local
    environment:
      MQTT_URL: mqtt://mosquitto:1883
      IMAGE_ROOT: /data
    volumes: ["image-storage:/data:ro"]
    depends_on: [mosquitto]
volumes:
  image-storage: {}
```

- factory-simulator 없이 돈다. 볼륨은 비어 있으므로 Ground Truth 줄은 확인하는 쪽이 넣는다(smoke, `04-verification.md` 3.3절):
  `docker run --rm -i -v <project>_image-storage:/data eclipse-mosquitto:2.1.2-alpine sh -c 'mkdir -p /data/ground_truth && cat >> /data/ground_truth/products.jsonl'`
- 결과 보기: `docker compose exec -T mosquitto mosquitto_sub -v -t factory/vision/result`. 로그: `docker compose logs -f vision-inspection`.
- 2026-09-27 이 맥(Docker 28.3.0, Compose v2.38.1)에서 같은 구조의 시험 이미지로 `up -d --build --wait`가 healthy로 끝나고, 읽기 전용 마운트(`RW=false`)에서 위 명령으로 넣은 Ground Truth를 읽는 것을 확인했다.

## 7. `.env.example`과 `.gitignore`

- `.env.example`: 2절 변수 7개를 기본값과 함께 주석으로 적는다(로컬 실행에서 `set -a; . ./.env; set +a`로 쓸 수 있게). 실제 `.env`는 commit하지 않는다. compose는 이 파일을 쓰지 않는다.
- `.gitignore`: `.venv/`, `**/__pycache__/`, `.pytest_cache/`, `.env`, `data/`.

시스템 조합에서 integration이 맞출 조건(이미지, 환경 변수, 마운트, 기동 확인)은 `AGREEMENTS.md` V-05다.
