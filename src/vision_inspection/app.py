"""paho MQTT client와 콜백 (docs/spec/02-service.md 1~3·5절, DECISIONS D-08, D-13, D-15).

paho를 import하는 유일한 모듈이다. 모든 콜백과 메시지 처리는 loop_forever를 도는 주 스레드 하나에서
순서대로 실행된다. 콜백 본문은 모두 try/except Exception으로 감싼다(paho는 콜백 예외를 루프 밖으로
올려 loop_forever를 끝내기 때문이다).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode

from .config import Config
from .logs import Logger
from .process import DETAIL_MAX, Drop, process

KEEPALIVE = 30
RECONNECT_MIN_DELAY = 1
RECONNECT_MAX_DELAY = 10


def _detail(value: Any) -> str:
    return str(value)[:DETAIL_MAX]


def _rc_name(rc: Any) -> str:
    return rc.name if isinstance(rc, MQTTErrorCode) else str(rc)


def remove_health_file(path: Path) -> None:
    path.unlink(missing_ok=True)


class Service:
    """Product Created를 구독하고 Vision Result를 발행한다. run()은 stop()이 불릴 때까지 막힌다."""

    def __init__(self, config: Config, logger: Logger) -> None:
        self._config = config
        self._log = logger
        self._stopping = False
        self._sub_mid: int | None = None
        # mid → (product_id, timestamp, defect, defect_type, t0)
        self._pending: dict[int, tuple[str, str, bool, str | None, float]] = {}
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=config.client_id,
            protocol=mqtt.MQTTv311,
            clean_session=True,
        )

    @property
    def stopping(self) -> bool:
        return self._stopping

    def run(self) -> None:
        client = self._client
        client.on_connect = self._on_connect
        client.on_connect_fail = self._on_connect_fail
        client.on_subscribe = self._on_subscribe
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_publish = self._on_publish
        client.reconnect_delay_set(min_delay=RECONNECT_MIN_DELAY, max_delay=RECONNECT_MAX_DELAY)
        client.connect_async(self._config.mqtt_host, self._config.mqtt_port, keepalive=KEEPALIVE)
        client.loop_forever(retry_first_connection=True)

    def stop(self) -> None:
        """종료 표시 후 disconnect(). 신호 처리기에서 부른다. loop_forever가 돌아온다."""
        self._stopping = True
        self._client.disconnect()

    # --- 연결 -----------------------------------------------------------------

    def _connect_failed(self, detail: str) -> None:
        remove_health_file(self._config.health_file)
        self._log.emit("WARNING", "connect_failed", reason="connect_failed", detail=_detail(detail))

    def _internal_error(self, where: str, exc: BaseException) -> None:
        self._log.emit("ERROR", "error", reason="internal_error", detail=_detail(f"{where}: {type(exc).__name__}: {exc}"))

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        try:
            if reason_code.is_failure:
                self._connect_failed(f"CONNACK {reason_code}")
                return
            rc, mid = client.subscribe(self._config.product_created_topic, qos=1)
            if rc == MQTTErrorCode.MQTT_ERR_SUCCESS:
                self._sub_mid = mid
            else:
                # 연결이 끊긴 경우다. on_disconnect와 paho 재연결이 뒤따른다.
                self._sub_mid = None
                self._log.emit("WARNING", "connect_failed", reason="connect_failed", detail=_detail(_rc_name(rc)))
        except Exception as e:
            self._internal_error("on_connect", e)

    def _on_connect_fail(self, client: mqtt.Client, userdata: Any) -> None:
        try:
            self._connect_failed(f"cannot connect to {self._config.mqtt_host}:{self._config.mqtt_port}")
        except Exception as e:
            self._internal_error("on_connect_fail", e)

    def _on_subscribe(
        self, client: mqtt.Client, userdata: Any, mid: int, reason_code_list: list[Any], properties: Any
    ) -> None:
        try:
            if mid != self._sub_mid:
                return
            if not reason_code_list or reason_code_list[0].is_failure:
                self._log.emit("WARNING", "connect_failed", reason="connect_failed", detail="subscribe refused")
                return
            self._config.health_file.touch()
            self._log.emit("INFO", "connected")
        except Exception as e:
            self._internal_error("on_subscribe", e)

    def _on_disconnect(
        self, client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any
    ) -> None:
        try:
            self._sub_mid = None
            remove_health_file(self._config.health_file)
            level = "INFO" if self._stopping else "WARNING"
            self._log.emit(level, "disconnected", reason="disconnected", detail=_detail(reason_code))
        except Exception as e:
            self._internal_error("on_disconnect", e)

    # --- 메시지 ---------------------------------------------------------------

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        product_id: str | None = None
        timestamp: str | None = None
        try:
            t0 = time.monotonic()
            raw = bytes(msg.payload)
            self._log.emit("INFO", "received", topic=msg.topic, bytes=len(raw))
            outcome = process(raw, self._config.ground_truth_path)
            product_id, timestamp = outcome.product_id, outcome.timestamp

            if outcome.bad_lines > 0:
                ids = {"product_id": product_id} if product_id is not None else {}
                self._log.emit("WARNING", "warning", reason="ground_truth_bad_lines", count=outcome.bad_lines, **ids)

            if isinstance(outcome, Drop):
                self._dropped(outcome.reason, outcome.detail, product_id, timestamp)
                return

            info = client.publish(self._config.vision_result_topic, outcome.payload, qos=1, retain=False)
            if info.rc in (MQTTErrorCode.MQTT_ERR_SUCCESS, MQTTErrorCode.MQTT_ERR_NO_CONN):
                # NO_CONN: paho가 메모리에 두었다가 재연결 뒤 보낸다(D-13).
                self._pending[info.mid] = (outcome.product_id, outcome.timestamp, outcome.defect, outcome.defect_type, t0)
            else:
                self._dropped("publish_failed", _rc_name(info.rc), product_id, timestamp)
        except Exception as e:
            try:
                self._dropped("internal_error", f"{type(e).__name__}: {e}", product_id, timestamp)
            except Exception:
                pass

    def _dropped(self, reason: str, detail: str, product_id: str | None, timestamp: str | None) -> None:
        ids: dict[str, str] = {}
        if product_id is not None:
            ids["product_id"] = product_id
        if timestamp is not None:
            ids["timestamp"] = timestamp
        self._log.emit("ERROR", "dropped", reason=reason, detail=_detail(detail), **ids)

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int, reason_code: Any, properties: Any) -> None:
        try:
            entry = self._pending.pop(mid, None)
            if entry is None:
                return
            product_id, timestamp, defect, defect_type, t0 = entry
            self._log.emit(
                "INFO",
                "published",
                product_id=product_id,
                timestamp=timestamp,
                defect=defect,
                defect_type=defect_type,
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as e:
            self._internal_error("on_publish", e)
