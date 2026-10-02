import json

import pytest

from app.core.config import ConnectorConfigSyncError, synchronize_connector_config_from_portal


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def portal_config(**overrides):
    values = {
        "mcegoldDataServicesUrl": "https://mds.example.test/connector/1.0",
        "mcegoldUsername": "demo-user",
        "mcegoldPassword": "demo-password",
        "mcegoldApiKey": "demo-api-key",
    }
    values.update(overrides)
    return values


def test_saving_endpoint_updates_connector_host(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert read_json(connector_path)["host"] == "https://mds.example.test/connector/1.0"


def test_saving_username_updates_connector_user_name(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert read_json(connector_path)["userName"] == "demo-user"


def test_saving_password_updates_connector_password(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert read_json(connector_path)["password"] == "demo-password"


def test_saving_api_key_updates_connector_api_key(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert read_json(connector_path)["apiKey"] == "demo-api-key"


def test_authentication_scheme_defaults_to_basic_api(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert read_json(connector_path)["authenticationScheme"] == "BasicApi"


def test_default_request_and_publication_channels_are_blank(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)
    config = read_json(connector_path)

    assert config["request"]["channel"] == ""
    assert config["request"]["readResponse"] is True
    assert config["request"]["removeResponseOnSuccess"] is False
    assert config["publication"]["channel"] == ""


def test_existing_explicit_channel_values_are_preserved(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"
    connector_path.write_text(
        json.dumps(
            {
                "request": {
                    "channel": "/custom/request",
                    "readResponse": False,
                    "removeResponseOnSuccess": True,
                },
                "publication": {"channel": "/custom/publication"},
            }
        ),
        encoding="utf-8",
    )

    synchronize_connector_config_from_portal(portal_config(), connector_path)
    config = read_json(connector_path)

    assert config["request"]["channel"] == "/custom/request"
    assert config["request"]["readResponse"] is False
    assert config["request"]["removeResponseOnSuccess"] is True
    assert config["publication"]["channel"] == "/custom/publication"


def test_existing_unrelated_connector_config_fields_are_preserved(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"
    connector_path.write_text(
        json.dumps({"customOption": {"enabled": True}, "authenticationScheme": "BasicApi"}),
        encoding="utf-8",
    )

    synchronize_connector_config_from_portal(portal_config(), connector_path)
    config = read_json(connector_path)

    assert config["customOption"] == {"enabled": True}
    assert config["host"] == "https://mds.example.test/connector/1.0"


def test_missing_connector_config_is_created_safely(tmp_path) -> None:
    connector_path = tmp_path / "nested" / "connector.config.json"

    synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert connector_path.exists()
    assert not connector_path.with_name("connector.config.json.tmp").exists()
    assert read_json(connector_path)["userName"] == "demo-user"


def test_failed_synchronization_does_not_leave_partial_temp_file(tmp_path) -> None:
    connector_path = tmp_path / "connector.config.json"
    connector_path.write_text("{", encoding="utf-8")

    with pytest.raises(ConnectorConfigSyncError):
        synchronize_connector_config_from_portal(portal_config(), connector_path)

    assert connector_path.read_text(encoding="utf-8") == "{"
    assert not connector_path.with_name("connector.config.json.tmp").exists()
