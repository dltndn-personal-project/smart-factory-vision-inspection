"""환경 변수 설정 (docs/spec/03-runtime.md 2절, DECISIONS D-19)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEFAULTS: dict[str, str] = {
    "MQTT_URL": "mqtt://mosquitto:1883",
    "MQTT_CLIENT_ID": "vision-inspection",
    "PRODUCT_CREATED_TOPIC": "factory/product/created",
    "VISION_RESULT_TOPIC": "factory/vision/result",
    "IMAGE_ROOT": "/data",
    "LOG_LEVEL": "INFO",
    "HEALTH_FILE": "/tmp/vision-inspection.connected",
}

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

_MQTT_URL_RE = re.compile(r"mqtt://([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?")
_CLIENT_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_TOPIC_RE = re.compile(r"[a-z0-9_]+(/[a-z0-9_]+)*")
_TOPIC_MAX = 256


class ConfigError(ValueError):
    """설정 오류. 메시지는 "<변수 이름>: <이유>"."""

    def __init__(self, name: str, reason: str) -> None:
        super().__init__(f"{name}: {reason}")
        self.name = name
        self.reason = reason


@dataclass(frozen=True)
class Config:
    mqtt_url: str
    mqtt_host: str
    mqtt_port: int
    client_id: str
    product_created_topic: str
    vision_result_topic: str
    image_root: Path
    ground_truth_path: Path
    log_level: str
    health_file: Path


def _get(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if value is None:
        return DEFAULTS[name]
    if value == "":
        raise ConfigError(name, "empty value")
    return value


def _topic(env: Mapping[str, str], name: str) -> str:
    value = _get(env, name)
    if len(value) > _TOPIC_MAX:
        raise ConfigError(name, f"longer than {_TOPIC_MAX} characters")
    if not _TOPIC_RE.fullmatch(value):
        raise ConfigError(name, "must be lowercase segments [a-z0-9_] separated by '/'")
    return value


def load_config(env: Mapping[str, str]) -> Config:
    """env를 읽고 검증한다. 틀린 값이 여럿이면 표 순서로 첫 번째만 ConfigError로 알린다."""
    mqtt_url = _get(env, "MQTT_URL")
    m = _MQTT_URL_RE.fullmatch(mqtt_url)
    if not m:
        raise ConfigError("MQTT_URL", "must be mqtt://host[:port]")
    mqtt_host = m.group(1)
    mqtt_port = int(m.group(2)) if m.group(2) is not None else 1883
    if not 1 <= mqtt_port <= 65535:
        raise ConfigError("MQTT_URL", "port must be 1-65535")

    client_id = _get(env, "MQTT_CLIENT_ID")
    if not _CLIENT_ID_RE.fullmatch(client_id):
        raise ConfigError("MQTT_CLIENT_ID", "must be 1-64 characters of [A-Za-z0-9_-]")

    product_created_topic = _topic(env, "PRODUCT_CREATED_TOPIC")
    vision_result_topic = _topic(env, "VISION_RESULT_TOPIC")
    if vision_result_topic == product_created_topic:
        raise ConfigError("VISION_RESULT_TOPIC", "must differ from PRODUCT_CREATED_TOPIC")

    image_root = Path(_get(env, "IMAGE_ROOT"))

    log_level = _get(env, "LOG_LEVEL").upper()
    if log_level not in LOG_LEVELS:
        raise ConfigError("LOG_LEVEL", "must be one of " + ", ".join(LOG_LEVELS))

    health_file = Path(_get(env, "HEALTH_FILE"))

    return Config(
        mqtt_url=mqtt_url,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        client_id=client_id,
        product_created_topic=product_created_topic,
        vision_result_topic=vision_result_topic,
        image_root=image_root,
        ground_truth_path=image_root / "ground_truth" / "products.jsonl",
        log_level=log_level,
        health_file=health_file,
    )
