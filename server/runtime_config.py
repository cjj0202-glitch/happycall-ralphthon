"""Explicit server configuration; never expose credential values in diagnostics."""
from __future__ import annotations

from collections.abc import Mapping
from ipaddress import IPv6Address
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from scripts.demo_openai_env import ENV_FILE, REQUIRED_POLICY, assert_key
from server.errors import DemoError


DEMO_ENV_KEYS = frozenset({"OPENAI_API_KEY", *REQUIRED_POLICY})
LOCAL_CORS_ORIGINS = ("http://localhost:3100", "http://127.0.0.1:3100")
CORS_ENV_KEY = "ONEFLOW_CORS_ORIGINS"


def read_demo_env(*, environ: Mapping[str, str] | None = None,
                  env_file: Path | None = None) -> dict[str, str]:
    """Read allowlisted keys only. Explicit runtime values, including blanks, win."""
    environment = os.environ if environ is None else environ
    result = {key: environment[key] for key in DEMO_ENV_KEYS if key in environment}
    missing = DEMO_ENV_KEYS - result.keys()
    if not missing:
        return result
    path = ENV_FILE if env_file is None else env_file
    try:
        if path.is_file():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key in missing:
                    result[key] = value.strip()
    except (OSError, UnicodeError):
        raise DemoError("DEMO_CONFIG_UNAVAILABLE", "데모 서버 환경설정을 읽을 수 없습니다.", 503) from None
    return result


def require_demo_api_key(values: Mapping[str, str] | None = None) -> str:
    """Share the live-request and health readiness guard without creating a client."""
    values = read_demo_env() if values is None else values
    if any(values.get(key) != expected for key, expected in REQUIRED_POLICY.items()):
        raise DemoError("DEMO_POLICY_REQUIRED", "데모 전용 키·예산 정책을 확인해 주세요.", 503)
    key = values.get("OPENAI_API_KEY", "")
    try:
        assert_key(key)
    except ValueError:
        raise DemoError("API_KEY_MISSING", "데모 서버 API 키가 준비되지 않았습니다.", 503) from None
    return key


def _origin(value: str) -> str:
    """Accept complete origins only and match the browser's canonical serialization."""
    if not value or "*" in value or any(ch.isspace() for ch in value):
        raise ValueError
    if not re.fullmatch(r"https?://(?:\[[0-9a-f:.]+\]|[a-z0-9.-]+)(?::[0-9]+)?", value, re.IGNORECASE):
        raise ValueError
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path or "?" in value or "#" in value or "\\" in value):
        raise ValueError
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{IPv6Address(host).compressed}]"
    elif (len(host) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                   for label in host.split("."))):
        raise ValueError
    port = parsed.port
    if parsed.netloc.endswith(":") or (port is not None and not 1 <= port <= 65535):
        raise ValueError
    default_port = 80 if parsed.scheme == "http" else 443
    suffix = f":{port}" if port is not None and port != default_port else ""
    return f"{parsed.scheme}://{host}{suffix}"


def cors_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    """An explicit deployment list replaces local defaults; invalid lists fail closed."""
    environment = os.environ if environ is None else environ
    if CORS_ENV_KEY not in environment:
        return list(LOCAL_CORS_ORIGINS)
    try:
        origins = [_origin(item.strip()) for item in environment[CORS_ENV_KEY].split(",")]
    except ValueError:
        raise ValueError("ONEFLOW_CORS_ORIGINS에는 쉼표로 구분한 올바른 HTTP(S) origin을 지정해야 합니다.") from None
    return list(dict.fromkeys(origins))
