import logging

import httpx2
import pytest

from busybar_kit import resolve as resolve_mod
from busybar_kit.config import DeviceConfig
from busybar_kit.resolve import (
    Resolution,
    candidate_hosts,
    is_device_reachable,
    normalize_addr,
    resolve_device,
    resolve_device_connection,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.0.4.20", "http://10.0.4.20"),
        ("  10.0.4.20/ ", "http://10.0.4.20"),
        ("http://bar.local/", "http://bar.local"),
        ("https://bar.local:8443", "https://bar.local:8443"),
        ("127.0.0.1:8080", "http://127.0.0.1:8080"),
    ],
)
def test_normalize_addr(raw, expected):
    assert normalize_addr(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "http://", "https:///", None])
def test_normalize_addr_rejects_empty(bad):
    with pytest.raises(ValueError):
        normalize_addr(bad)


def test_candidates_follow_prefer_and_dedupe_normalized():
    wifi = DeviceConfig("d", "d", wifi_host="http://10.0.4.20/", usb_host="10.0.4.20")
    assert candidate_hosts(wifi) == [("wifi", "http://10.0.4.20")]
    both = DeviceConfig("d", "d", wifi_host="192.168.1.5", usb_host="10.0.4.20", prefer="usb")
    assert candidate_hosts(both) == [("usb", "http://10.0.4.20"), ("wifi", "http://192.168.1.5")]
    assert candidate_hosts(DeviceConfig("d", "d")) == []


def test_resolution_fields_and_repr():
    res = Resolution("http://10.0.4.20", "usb", True, "s3cret")
    assert res.host == "10.0.4.20"
    assert "s3cret" not in repr(res)
    assert Resolution("https://bar.local:8443/", "explicit", None).host == "bar.local:8443"


def test_explicit_host_skips_probe():
    calls = []
    res = resolve_device(
        DeviceConfig("d", "d", wifi_host="1.2.3.4"),
        "tok",
        explicit_host="bar.test/",
        probe_fn=lambda a: calls.append(a) or True,
    )
    assert (res.addr, res.source, res.reachable, res.token) == (
        "http://bar.test",
        "explicit",
        None,
        "tok",
    )
    assert calls == []


def test_first_reachable_candidate_wins():
    calls = []
    device = DeviceConfig("d", "d", wifi_host="192.168.1.5", usb_host="10.0.4.21")

    def probe(addr):
        calls.append(addr)
        return addr.endswith("10.0.4.21")

    res = resolve_device(device, probe_fn=probe)
    assert (res.addr, res.source, res.reachable) == ("http://10.0.4.21", "usb", True)
    assert calls == ["http://192.168.1.5", "http://10.0.4.21"]


def test_fallback_uses_device_usb_host():
    device = DeviceConfig("d", "d", wifi_host="192.168.1.5", usb_host="10.0.4.99", token="t")
    res = resolve_device(device, probe_fn=lambda a: False)
    assert (res.addr, res.source, res.reachable, res.token) == (
        "http://10.0.4.99",
        "fallback",
        False,
        "t",
    )
    wifi_only = DeviceConfig("d", "d", wifi_host="192.168.1.5")
    assert resolve_device(wifi_only, probe_fn=lambda a: False).addr == "http://10.0.4.20"


def test_resolve_device_is_cache_free():
    state = {"up": False}
    device = DeviceConfig("d", "d", wifi_host="192.168.1.5", usb_host="10.0.4.20")
    assert resolve_device(device, probe_fn=lambda a: state["up"]).source == "fallback"
    state["up"] = True
    assert resolve_device(device, probe_fn=lambda a: state["up"]).source == "wifi"


def test_transport_and_timeout_reach_probe():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx2.Response(200, json={"api_semver": "27.16.0"})

    device = DeviceConfig("d", "d", wifi_host="192.168.1.5")
    res = resolve_device(device, transport=httpx2.MockTransport(handler), timeout=0.2)
    assert res.source == "wifi" and res.reachable is True
    assert seen == ["http://192.168.1.5/api/version"]


def test_probe_failure_logged_at_debug_without_secrets(caplog):
    def boom(request):
        raise httpx2.ConnectError("refused", request=request)

    with caplog.at_level(logging.DEBUG, logger="busybar_kit.resolve"):
        assert not is_device_reachable(
            "http://user:s3cret@10.9.9.9", transport=httpx2.MockTransport(boom)
        )
    assert "ConnectError" in caplog.text
    assert "s3cret" not in caplog.text and "user" not in caplog.text
    assert all(r.levelno == logging.DEBUG for r in caplog.records)


def test_probe_never_raises_on_bad_addr():
    assert is_device_reachable("") is False


def test_v02_wrapper_uses_resolve_device(monkeypatch):
    monkeypatch.setattr(resolve_mod, "is_device_reachable", lambda a, **kw: False)
    device = DeviceConfig("w", "w", wifi_host="1.2.3.4", usb_host="10.0.4.77", token="t")
    res = resolve_device_connection(device, use_cache=False)
    assert res == ("http://10.0.4.77", "t")
