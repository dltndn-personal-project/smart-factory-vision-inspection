from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from vision_inspection.config import DEFAULTS, Config, ConfigError, load_config


def test_defaults():
    c = load_config({})
    assert c == Config(
        mqtt_url="mqtt://mosquitto:1883",
        mqtt_host="mosquitto",
        mqtt_port=1883,
        client_id="vision-inspection",
        product_created_topic="factory/product/created",
        vision_result_topic="factory/vision/result",
        image_root=Path("/data"),
        ground_truth_path=Path("/data/ground_truth/products.jsonl"),
        log_level="INFO",
        health_file=Path("/tmp/vision-inspection.connected"),
    )
    with pytest.raises(FrozenInstanceError):
        c.mqtt_port = 1  # type: ignore[misc]


def test_env_overrides():
    c = load_config(
        {
            "MQTT_URL": "mqtt://127.0.0.1:18830",
            "MQTT_CLIENT_ID": "vis-test_1",
            "PRODUCT_CREATED_TOPIC": "plant2/product/created",
            "VISION_RESULT_TOPIC": "plant2/vision/result",
            "IMAGE_ROOT": "./data",
            "LOG_LEVEL": "WARNING",
            "HEALTH_FILE": "/tmp/vis-dev.connected",
            "UNRELATED": "ignored",
        }
    )
    assert (c.mqtt_url, c.mqtt_host, c.mqtt_port) == ("mqtt://127.0.0.1:18830", "127.0.0.1", 18830)
    assert c.client_id == "vis-test_1"
    assert c.product_created_topic == "plant2/product/created"
    assert c.vision_result_topic == "plant2/vision/result"
    assert c.image_root == Path("data")
    assert c.ground_truth_path == Path("data/ground_truth/products.jsonl")
    assert c.log_level == "WARNING"
    assert c.health_file == Path("/tmp/vis-dev.connected")


def test_port_defaults_to_1883():
    c = load_config({"MQTT_URL": "mqtt://broker.local"})
    assert (c.mqtt_host, c.mqtt_port) == ("broker.local", 1883)


@pytest.mark.parametrize(
    "url", ["http://h", "mqtt://", "mqtt://h:0", "mqtt://h:65536", "mqtt://h:1883/", "mqtt://u@h"]
)
def test_invalid_mqtt_url(url):
    with pytest.raises(ConfigError) as e:
        load_config({"MQTT_URL": url})
    assert str(e.value).startswith("MQTT_URL: ")


@pytest.mark.parametrize("name", list(DEFAULTS))
def test_empty_value_is_error(name):
    with pytest.raises(ConfigError) as e:
        load_config({name: ""})
    assert str(e.value).startswith(f"{name}: ")


@pytest.mark.parametrize("name", ["PRODUCT_CREATED_TOPIC", "VISION_RESULT_TOPIC"])
@pytest.mark.parametrize("topic", ["factory/+/x", "#", "Factory/x", "a//b", "factory/ x", "a" * 257])
def test_invalid_topic(name, topic):
    with pytest.raises(ConfigError) as e:
        load_config({name: topic})
    assert str(e.value).startswith(f"{name}: ")


def test_same_topics_rejected():
    with pytest.raises(ConfigError) as e:
        load_config({"VISION_RESULT_TOPIC": "factory/product/created"})
    assert str(e.value).startswith("VISION_RESULT_TOPIC: ")


def test_first_error_in_table_order():
    with pytest.raises(ConfigError) as e:
        load_config({"LOG_LEVEL": "loud", "MQTT_CLIENT_ID": "a b", "HEALTH_FILE": ""})
    assert str(e.value).startswith("MQTT_CLIENT_ID: ")


@pytest.mark.parametrize("value", ["debug", "Info", "WARNING", "error"])
def test_log_level_case_insensitive(value):
    assert load_config({"LOG_LEVEL": value}).log_level == value.upper()
    with pytest.raises(ConfigError) as e:
        load_config({"LOG_LEVEL": "trace"})
    assert str(e.value).startswith("LOG_LEVEL: ")


def test_missing_image_root_is_not_error(tmp_path):
    missing = tmp_path / "nope"
    c = load_config({"IMAGE_ROOT": str(missing)})
    assert c.image_root == missing
    assert c.ground_truth_path == missing / "ground_truth" / "products.jsonl"
    assert not missing.exists()
