"""Synthetic environment and in-process ASGI tests; no real secret file or network."""
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from starlette.testclient import TestClient

from server import runtime_config as config
from server.errors import DemoError


LOCAL_KEY = "sk-" + "local-synthetic-only-" * 3
RUNTIME_KEY = "sk-" + "runtime-synthetic-only-" * 3
LOCAL_VALUES = {**config.REQUIRED_POLICY, "OPENAI_API_KEY": LOCAL_KEY}
RUNTIME_VALUES = {**config.REQUIRED_POLICY, "OPENAI_API_KEY": RUNTIME_KEY}


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    for key in (*config.DEMO_ENV_KEYS, config.CORS_ENV_KEY):
        monkeypatch.delenv(key, raising=False)
    # Every default reader call points here, including health/live integrations.
    path = tmp_path / "synthetic.env"
    monkeypatch.setattr(config, "ENV_FILE", path)
    return path


def write_env(path, values):
    lines = ["# Synthetic test data only", "", "ignored line"]
    lines += [f"{key} = {value}" for key, value in values.items()]
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def set_env(monkeypatch, values):
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_local_file_and_bom_keep_existing_demo_policy(isolated_environment):
    write_env(isolated_environment, LOCAL_VALUES)
    assert config.read_demo_env(environ={}) == LOCAL_VALUES
    assert config.require_demo_api_key() == LOCAL_KEY


def test_runtime_environment_overrides_every_local_value(isolated_environment):
    local = {key: "different-local-value" for key in config.DEMO_ENV_KEYS}
    write_env(isolated_environment, local)
    assert config.read_demo_env(environ=RUNTIME_VALUES) == RUNTIME_VALUES


def test_complete_runtime_configuration_never_reads_local_file(monkeypatch):
    def fail_read(*args, **kwargs):
        raise AssertionError("Complete runtime configuration must not open a file")
    monkeypatch.setattr(Path, "is_file", fail_read)
    monkeypatch.setattr(Path, "read_text", fail_read)
    assert config.read_demo_env(environ=RUNTIME_VALUES) == RUNTIME_VALUES


def test_partial_runtime_only_fills_missing_values(isolated_environment):
    write_env(isolated_environment, LOCAL_VALUES)
    actual = config.read_demo_env(environ={"OPENAI_API_KEY": RUNTIME_KEY})
    assert actual == RUNTIME_VALUES


@pytest.mark.parametrize("key", sorted(config.DEMO_ENV_KEYS))
def test_explicit_empty_runtime_value_never_falls_back(key, isolated_environment):
    write_env(isolated_environment, LOCAL_VALUES)
    values = config.read_demo_env(environ={key: ""})
    assert values[key] == ""
    with pytest.raises(DemoError) as caught:
        config.require_demo_api_key(values)
    assert caught.value.status == 503
    assert caught.value.code == ("API_KEY_MISSING" if key == "OPENAI_API_KEY" else "DEMO_POLICY_REQUIRED")


def test_unrelated_file_and_process_keys_are_not_returned(isolated_environment):
    extra = {"BLOB_READ_WRITE_TOKEN": "private-synthetic", "OPENAI_BASE_URL": "https://untrusted.invalid"}
    write_env(isolated_environment, {**LOCAL_VALUES, **extra})
    actual = config.read_demo_env(environ=extra)
    assert actual == LOCAL_VALUES
    assert set(actual) == config.DEMO_ENV_KEYS


def test_missing_file_leaves_live_configuration_unready(isolated_environment):
    assert not isolated_environment.exists()
    assert config.read_demo_env(environ={}) == {}
    with pytest.raises(DemoError, match="데모 전용") as caught:
        config.require_demo_api_key({})
    assert caught.value.code == "DEMO_POLICY_REQUIRED"


@pytest.mark.parametrize("key", sorted(config.DEMO_ENV_KEYS))
def test_each_required_configuration_key_is_required(key):
    values = {name: value for name, value in RUNTIME_VALUES.items() if name != key}
    with pytest.raises(DemoError) as caught:
        config.require_demo_api_key(values)
    assert caught.value.code == ("API_KEY_MISSING" if key == "OPENAI_API_KEY" else "DEMO_POLICY_REQUIRED")


@pytest.mark.parametrize("key", sorted(config.REQUIRED_POLICY))
def test_policy_cannot_be_relaxed_by_runtime_configuration(key):
    values = {**RUNTIME_VALUES, key: "unapproved-policy-synthetic"}
    with pytest.raises(DemoError) as caught:
        config.require_demo_api_key(values)
    assert caught.value.code == "DEMO_POLICY_REQUIRED"
    assert "unapproved-policy-synthetic" not in str(caught.value)


@pytest.mark.parametrize("key", ["", "not-an-api-key", "sk-" + "x" * 36, "sk-" + "x" * 38 + "\n"])
def test_invalid_api_key_is_rejected_without_echo(key):
    with pytest.raises(DemoError) as caught:
        config.require_demo_api_key({**RUNTIME_VALUES, "OPENAI_API_KEY": key})
    assert caught.value.code == "API_KEY_MISSING"
    assert caught.value.status == 503
    assert "sk-" not in str(caught.value)


def test_api_key_format_boundary_is_preserved():
    assert config.require_demo_api_key({**RUNTIME_VALUES, "OPENAI_API_KEY": "sk-" + "x" * 37}) == "sk-" + "x" * 37


def test_file_failure_has_static_error_message(isolated_environment, monkeypatch):
    write_env(isolated_environment, LOCAL_VALUES)
    def fail_read(*args, **kwargs):
        raise PermissionError("private-synthetic-path-and-value")
    monkeypatch.setattr(Path, "read_text", fail_read)
    with pytest.raises(DemoError) as caught:
        config.read_demo_env(environ={})
    assert caught.value.code == "DEMO_CONFIG_UNAVAILABLE"
    assert caught.value.status == 503
    assert "private-synthetic" not in str(caught.value)


def test_live_client_uses_runtime_key_and_pinned_endpoint(monkeypatch):
    from server import live
    set_env(monkeypatch, RUNTIME_VALUES)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://untrusted.invalid")
    constructor = Mock()
    monkeypatch.setattr(live, "OpenAI", constructor)
    assert live.demo_client() is constructor.return_value
    constructor.assert_called_once_with(api_key=RUNTIME_KEY, base_url="https://api.openai.com/v1",
                                        timeout=90, max_retries=0)


def test_invalid_live_config_does_not_construct_client(monkeypatch):
    from server import live
    set_env(monkeypatch, {**RUNTIME_VALUES, "OPENAI_DEMO_PURPOSE": ""})
    constructor = Mock(side_effect=AssertionError("No client for invalid config"))
    monkeypatch.setattr(live, "OpenAI", constructor)
    with pytest.raises(DemoError):
        live.demo_client()
    constructor.assert_not_called()


@pytest.mark.parametrize("change,ready", [({}, True), ({"OPENAI_API_KEY": "sk-short"}, False),
    ({"OPENAI_API_KEY": ""}, False), ({"ONEFLOW_RUNTIME_MODE": ""}, False)])
def test_health_shares_live_validation_without_exposing_key(change, ready, monkeypatch):
    from server import handlers
    set_env(monkeypatch, {**RUNTIME_VALUES, **change})
    runtime = Mock()
    runtime.check_ready.return_value = {"reservedUsd": 0, "accounting": "synthetic-test"}
    monkeypatch.setattr(handlers, "get_runtime_storage", Mock(return_value=runtime))
    result = asyncio.run(handlers.health())
    assert result["liveReady"] is ready
    assert result["runtime"] == "synthetic-demo"
    assert result["synthetic"] is True
    assert result["budget"]["accounting"] == "synthetic-test"
    assert "sk-" not in json.dumps(result)


def test_default_cors_keeps_both_local_origins():
    assert config.cors_origins({}) == ["http://localhost:3100", "http://127.0.0.1:3100"]


def test_deployment_cors_replaces_local_and_normalizes_duplicates():
    origins = config.cors_origins({config.CORS_ENV_KEY:
        " HTTPS://Demo.Example.COM:443 , https://demo.example.com, http://[::1]:3100 "})
    assert origins == ["https://demo.example.com", "http://[::1]:3100"]


@pytest.mark.parametrize("value", ["", " ", "*", "https://*.example.com", "null", ",",
    "https://demo.example.com,", "https://demo.example.com,,https://other.example.com",
    "https://demo.example.com/", "https://demo.example.com/api", "https://demo.example.com?",
    "https://demo.example.com?q=synthetic-secret", "https://demo.example.com#", "file://demo.example.com",
    "https://user:synthetic-secret@demo.example.com", "https://", "demo.example.com",
    "https://demo example.com", "https://demo.example.com:", "https://demo.example.com:0",
    "https://demo.example.com:65536", "https://demo.example.com:abc", "https://demo..example.com",
    "https://-demo.example.com", "https://[::1]garbage", "https://[not-ipv6]",
    "https://demo.example.com\\evil", "https://demo.example.co\nm"])
def test_invalid_cors_is_rejected_without_echo(value):
    with pytest.raises(ValueError) as caught:
        config.cors_origins({config.CORS_ENV_KEY: value})
    assert str(caught.value) == "ONEFLOW_CORS_ORIGINS에는 쉼표로 구분한 올바른 HTTP(S) origin을 지정해야 합니다."


def preflight(client, origin):
    return client.options("/api/cases/SYN-TEST", headers={"Origin": origin,
        "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "Content-Type,X-Demo-Role"})


def test_real_asgi_cors_defaults_allow_local_and_reject_foreign():
    from server.app import create_app
    with TestClient(create_app()) as client:
        for origin in config.LOCAL_CORS_ORIGINS:
            response = preflight(client, origin)
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert "access-control-allow-credentials" not in response.headers
        denied = preflight(client, "https://untrusted.invalid")
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers


def test_real_asgi_cors_only_allows_exact_deployment_origin(monkeypatch):
    from server.app import create_app
    monkeypatch.setenv(config.CORS_ENV_KEY, "https://demo.example.com")
    with TestClient(create_app()) as client:
        allowed = preflight(client, "https://demo.example.com")
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "https://demo.example.com"
        assert "access-control-allow-credentials" not in allowed.headers
        for origin in (*config.LOCAL_CORS_ORIGINS, "https://demo.example.com.untrusted.invalid", "null"):
            denied = preflight(client, origin)
            assert denied.status_code == 400
            assert "access-control-allow-origin" not in denied.headers


def test_invalid_cors_prevents_app_creation(monkeypatch):
    from server.app import create_app
    monkeypatch.setenv(config.CORS_ENV_KEY, "")
    with pytest.raises(ValueError, match="ONEFLOW_CORS_ORIGINS"):
        create_app()
