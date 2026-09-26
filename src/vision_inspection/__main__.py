"""진입점 `python -m vision_inspection` (docs/spec/02-service.md 6절, DECISIONS D-16).

종료 코드: 신호(SIGTERM·SIGINT)로 정상 종료 0, 예상하지 못한 예외 1, 설정 오류 2.
"""

from __future__ import annotations

import os
import signal
import sys

from .config import ConfigError, load_config
from .logs import Logger
from .payload import JUDGEMENT_SOURCE
from .process import DETAIL_MAX

EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_CONFIG = 2


def main() -> int:
    # 1. 설정. 오류면 INFO 수준 Logger로 error 로그 후 2.
    try:
        config = load_config(os.environ)
    except ConfigError as e:
        Logger("INFO").emit("ERROR", "error", reason="invalid_config", detail=str(e)[:DETAIL_MAX])
        return EXIT_CONFIG

    logger = Logger(config.log_level)
    try:
        from .app import Service, remove_health_file

        # 2. started, 기동 확인 파일 정리
        logger.emit(
            "INFO",
            "started",
            mqtt_url=config.mqtt_url,
            client_id=config.client_id,
            subscribe_topic=config.product_created_topic,
            publish_topic=config.vision_result_topic,
            image_root=str(config.image_root),
            judgement_source=JUDGEMENT_SOURCE,
        )
        remove_health_file(config.health_file)

        service = Service(config, logger)
        received: list[str] = []

        # 3. 신호 처리기: 종료 표시 후 disconnect() → loop_forever가 돌아온다
        def handle(signum: int, frame: object) -> None:
            if not received:
                received.append(signal.Signals(signum).name)
            service.stop()

        signal.signal(signal.SIGTERM, handle)
        signal.signal(signal.SIGINT, handle)

        # 4. 루프. 돌아오면 파일 삭제, stopped, 0
        service.run()
        remove_health_file(config.health_file)
        if not received:
            raise RuntimeError("network loop ended without a stop signal")
        logger.emit("INFO", "stopped", signal=received[0])
        return EXIT_OK
    except Exception as e:
        # 5. 콜백 밖의 예상하지 못한 예외
        try:
            remove_health_file(config.health_file)
        except Exception:
            pass
        logger.emit("ERROR", "error", reason="internal_error", detail=f"{type(e).__name__}: {e}"[:DETAIL_MAX])
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
