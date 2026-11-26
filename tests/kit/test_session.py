import json
import threading

import httpx2
import pytest
from busylib.exceptions import BusyBarError

from busybar_kit import client as client_mod
from busybar_kit.client import DeviceError, DeviceSession, describe_error, make_client
from busybar_kit.draw import DrawResult, build_text_element
from busybar_kit.resolve import Resolution

ELEMENTS = [build_text_element("hi", id="t1")]
TOKEN = "s3cret-token-value"


class Device:
    """MockTransport recording requests; ``status`` sets the draw/clear response code."""

    def __init__(self, status: int = 200):
        self.status = status
        self.requests: list[httpx2.Request] = []
        self.transport = httpx2.MockTransport(self.handle)

    def handle(self, request):
        self.requests.append(request)
        if request.url.path == "/api/version":
            return httpx2.Response(200, json={"api_semver": "27.16.0"})
        if self.status != 200:
            return httpx2.Response(self.status, json={"error": "nope", "code": self.status})
        return httpx2.Response(200, json={"result": "OK"})

    def paths(self, method=None):
        return [r.url.path for r in self.requests if method in (None, r.method)]


def test_make_client_has_no_proxy_and_no_version_call(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("http_proxy", "http://proxy.invalid:3128")
    client = make_client("10.0.4.20")
    try:
        assert not client.client._mounts
    finally:
        client.close()

    device = Device()
    client = make_client("bar.test", token=TOKEN, transport=device.transport)
    assert device.requests == []  # construction is network-free
    client.display_draw(
        {"application_name": "a", "elements": [ELEMENTS[0].model_dump(exclude_none=True)]}
    )
    assert "/api/version" not in device.paths()
    client.close()


def test_make_client_is_not_cached():
    assert make_client("bar.test") is not make_client("bar.test")


def test_session_client_is_lazy_and_reused():
    built = []

    def factory(addr, **kwargs):
        built.append((addr, kwargs))
        return make_client(addr, **kwargs)

    session = DeviceSession(
        Resolution("http://bar.test", "wifi", True, TOKEN),
        application_name="app",
        transport=Device().transport,
        client_factory=factory,
    )
    assert built == []
    assert session.client is session.client
    assert len(built) == 1 and built[0][0] == "http://bar.test"
    assert built[0][1]["token"] == TOKEN
    session.close()


def test_dry_run_constructs_nothing(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("no client may be built in dry-run")

    monkeypatch.setattr(client_mod, "make_client", forbidden)
    monkeypatch.setattr(httpx2, "HTTPTransport", forbidden)
    session = DeviceSession("bar.test", application_name="app", dry_run=True)
    assert session.client is None
    assert session.draw(ELEMENTS) is DrawResult.DRY_RUN
    assert session.clear() is True
    assert session.writes == 0
    session.close()


def test_dry_run_still_validates():
    session = DeviceSession("bar.test", application_name="app", dry_run=True)
    with pytest.raises(ValueError):
        session.draw([])


def test_draw_and_clear_count_writes():
    device = Device()
    session = DeviceSession("bar.test", application_name="app", transport=device.transport)
    assert session.draw(ELEMENTS) is DrawResult.DRAWN
    assert session.clear(["t1"]) is True
    assert session.clear([]) is True  # no request: an empty list must not clear everything
    assert session.writes == 2
    deletes = [r for r in device.requests if r.method == "DELETE"]
    assert len(deletes) == 1
    assert json.loads(deletes[0].content) == {"element_ids": ["t1"]}
    assert deletes[0].url.params["application_name"] == "app"
    assert "/api/version" not in device.paths()
    session.close()


def test_api_error_wrapped_without_token():
    device = Device(status=500)
    session = DeviceSession(
        "bar.test", application_name="app", token=TOKEN, transport=device.transport
    )
    with pytest.raises(DeviceError) as info:
        session.draw(ELEMENTS)
    assert info.value.status_code == 500
    assert str(info.value) == "HTTP 500: nope"
    assert TOKEN not in str(info.value) and TOKEN not in repr(session)
    session.close()


def test_transport_error_wrapped():
    def boom(request):
        raise httpx2.ConnectError("refused", request=request)

    session = DeviceSession(
        "bar.test", application_name="app", token=TOKEN, transport=httpx2.MockTransport(boom)
    )
    with pytest.raises(DeviceError) as info:
        session.draw(ELEMENTS)
    assert info.value.status_code is None
    assert TOKEN not in str(info.value)
    assert session.clear() is False  # clear never raises
    session.close()


def test_409_is_a_result_not_an_error(monkeypatch):
    monkeypatch.setattr("busybar_kit.draw.uniform", lambda a, b: 0.0)
    session = DeviceSession("bar.test", application_name="app", transport=Device(409).transport)
    result = session.draw(ELEMENTS, max_409_retries=1, initial_backoff=0.0)
    assert result is DrawResult.CONFLICT_SKIPPED
    assert session.writes == 0
    session.close()


def test_close_interrupts_backoff_and_is_idempotent():
    device = Device(409)
    session = DeviceSession("bar.test", application_name="app", transport=device.transport)
    results = []
    worker = threading.Thread(
        target=lambda: results.append(session.draw(ELEMENTS, initial_backoff=30.0))
    )
    worker.start()
    while not device.requests:
        threading.Event().wait(0.01)
    session.close()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert results == [DrawResult.CANCELLED]
    session.close()
    assert session.closed
    assert session.draw(ELEMENTS) is DrawResult.CANCELLED
    assert session.clear() is False
    with pytest.raises(DeviceError):
        _ = session.client


def test_concurrent_draws_share_one_client():
    built = []

    def factory(addr, **kwargs):
        built.append(addr)
        return make_client(addr, **kwargs)

    session = DeviceSession(
        "bar.test", application_name="app", transport=Device().transport, client_factory=factory
    )
    threads = [threading.Thread(target=session.draw, args=(ELEMENTS,)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(built) == 1 and session.writes == 8
    session.close()


def test_describe_error():
    from busylib.exceptions import BusyBarAPIError

    assert describe_error(BusyBarAPIError("busy", status_code=409)) == "HTTP 409: busy"
    assert describe_error(BusyBarError(f"token={TOKEN}")) == "BusyBarError"
    assert describe_error(OSError("x")) == "OSError"


def test_invalid_application_name_rejected():
    with pytest.raises(ValueError):
        DeviceSession("bar.test", application_name="bad name")
