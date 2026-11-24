import functools

import httpx2
import pytest

from busybar_kit import resolve as resolve_mod
from busybar_kit.client import close_clients, get_async_busybar_client, get_busybar_client
from busybar_kit.config import DeviceConfig
from busybar_kit.resolve import clear_resolution_cache, is_device_reachable


@pytest.mark.parametrize(
    ("status", "kwargs", "expected"),
    [
        (200, {"json": {"api_semver": "27.14.0"}}, True),
        (401, {"json": {"error": "unauthorized"}}, True),
        (403, {"json": {"error": "forbidden", "error_code": "forbidden"}}, True),
        (403, {"text": "Destination IP is in a private/reserved range"}, False),
        (200, {"text": "<html>captive portal</html>"}, False),
        (200, {"json": {"hello": "world"}}, False),
        (200, {"json": ["api_semver"]}, False),
        (404, {"json": {"error": "not found"}}, False),
        (500, {"json": {"error": "boom"}}, False),
    ],
)
def test_probe_requires_busybar_response_shape(status, kwargs, expected):
    transport = httpx2.MockTransport(lambda r: httpx2.Response(status, **kwargs))
    assert is_device_reachable("10.0.4.20", transport=transport) is expected


def test_probe_network_error_is_false():
    def boom(request):
        raise httpx2.ConnectError("refused", request=request)

    assert is_device_reachable("10.9.9.9", transport=httpx2.MockTransport(boom)) is False


def test_probe_hits_version_endpoint_and_ignores_env_proxies(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:3128")
    seen: dict = {}
    paths: list[str] = []
    real_client = httpx2.Client

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_client(*args, **kwargs)

    def handler(request):
        paths.append(request.url.path)
        return httpx2.Response(200, json={"api_semver": "27.14.0"})

    monkeypatch.setattr(httpx2, "Client", spy)
    assert is_device_reachable("bar.test", transport=httpx2.MockTransport(handler))
    assert seen["trust_env"] is False
    assert paths == ["/api/version"]


def test_gateway_403_does_not_win_resolution(monkeypatch):
    """A plain-text 403 on the Wi-Fi host must fall through to the USB candidate."""

    def handler(request):
        if request.url.host == "192.168.1.100":
            return httpx2.Response(403, text="Forbidden by gateway")
        return httpx2.Response(200, json={"api_semver": "27.14.0"})

    probe = functools.partial(is_device_reachable, transport=httpx2.MockTransport(handler))
    monkeypatch.setattr(resolve_mod, "is_device_reachable", probe)
    clear_resolution_cache()
    config = DeviceConfig(
        name="office", label="Office", wifi_host="192.168.1.100", usb_host="10.0.4.20"
    )
    resolved = resolve_mod.resolve_device_connection(config=config, use_cache=False)
    assert resolved.addr == "http://10.0.4.20"


def _config():
    return DeviceConfig(name="office", label="Office", usb_host="10.0.4.20", token="t")


def test_sync_client_ignores_env_proxies(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:3128")
    monkeypatch.setattr("busylib.BusyBar.version", lambda self: None)
    client = get_busybar_client(config=_config(), explicit_host="10.0.4.20", reuse=False)
    try:
        assert not client.client._mounts  # no proxy mounted for device traffic
    finally:
        client.close()
        close_clients()


def test_async_client_ignores_env_proxies(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:3128")
    client = get_async_busybar_client(config=_config(), explicit_host="10.0.4.20", reuse=False)
    assert not client.client._mounts
    close_clients()


def test_caller_transport_still_used(mock_bar_transport):
    transport, requests = mock_bar_transport
    client = get_busybar_client(
        config=_config(), explicit_host="192.168.1.50", transport=transport, reuse=False
    )
    assert any(r.url.path == "/api/version" for r in requests)
    client.close()
