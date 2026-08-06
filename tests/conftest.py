from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml


@pytest.fixture(scope="session")
def spec() -> dict[str, Any]:
    spec_path = (
        Path(__file__).resolve().parent.parent / "vendor" / "busybar-openapi" / "openapi.yaml"
    )
    with open(spec_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def mock_bar_transport() -> tuple[httpx.MockTransport, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)

        if "/api/display/draw" in request.url.path or "/busybar/display/draw" in request.url.path:
            if request.headers.get("X-Trigger-409"):
                return httpx.Response(
                    409,
                    json={"error": "Requested priority level is below active app", "code": 409},
                )
            return httpx.Response(200, json={"result": "OK"})

        if "/api/version" in request.url.path or "/busybar/version" in request.url.path:
            return httpx.Response(200, json={"version": "25.0.0", "api_semver": "25.0.0"})

        return httpx.Response(200, json={"result": "OK"})

    transport = httpx.MockTransport(handler)
    return transport, requests


@pytest.fixture
def tmp_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    devices_toml = config_dir / "devices.toml"
    devices_toml.write_text(
        """
default = "office"

[devices.office]
label = "Office Test"
wifi_host = "192.168.1.100"
usb_host = "10.0.4.20"
prefer = "wifi"
token_env = "BUSYBAR_TOKEN"
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("BUSYBAR_TOKEN", "test_secret_token_123")
    return config_dir
