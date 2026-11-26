import threading

import httpx2
import pytest
from busylib.exceptions import BusyBarAPIError

from busybar_kit import draw as draw_mod
from busybar_kit.client import get_busybar_client
from busybar_kit.config import DeviceConfig
from busybar_kit.draw import build_text_element, draw_display_elements


class Recorder(threading.Event):
    """Records backoff waits instead of sleeping."""

    def __init__(self, interrupt_after: int | None = None):
        super().__init__()
        self.waits: list[float] = []
        self.interrupt_after = interrupt_after

    def wait(self, timeout=None):
        self.waits.append(timeout)
        return self.interrupt_after is not None and len(self.waits) >= self.interrupt_after


def _client(statuses, bodies=None):
    draws: list[httpx2.Request] = []

    def handler(request):
        if request.url.path == "/api/display/draw":
            draws.append(request)
            status = statuses.pop(0) if statuses else 200
            if status != 200:
                body = (bodies or {}).get(status, {"error": "Priority conflict", "code": status})
                return httpx2.Response(status, json=body)
            return httpx2.Response(200, json={"result": "OK"})
        return httpx2.Response(200, json={"api_semver": "27.14.0"})

    client = get_busybar_client(
        config=DeviceConfig("o", "o", token="t"),
        explicit_host="bar.test",
        transport=httpx2.MockTransport(handler),
        reuse=False,
    )
    return client, draws


ELEMENTS = [build_text_element("hi", id="t1")]


@pytest.fixture(autouse=True)
def fixed_jitter(monkeypatch):
    monkeypatch.setattr(draw_mod, "uniform", lambda a, b: 0.1)


def test_409_retries_then_draws():
    client, draws = _client([409, 409, 200])
    rec = Recorder()
    assert draw_display_elements(
        client, ELEMENTS, application_name="app", initial_backoff=0.5, cancel=rec
    )
    assert len(draws) == 3
    assert rec.waits == [pytest.approx(0.6), pytest.approx(1.1)]


def test_409_backoff_is_capped():
    client, draws = _client([409] * 10)
    rec = Recorder()
    assert not draw_display_elements(
        client,
        ELEMENTS,
        application_name="app",
        max_409_retries=5,
        initial_backoff=1.0,
        max_backoff=2.0,
        cancel=rec,
    )
    assert len(draws) == 6
    assert rec.waits == [pytest.approx(w) for w in (1.1, 2.1, 2.1, 2.1, 2.1)]


def test_cancel_interrupts_backoff():
    client, draws = _client([409] * 10)
    rec = Recorder(interrupt_after=1)
    assert not draw_display_elements(client, ELEMENTS, application_name="app", cancel=rec)
    assert len(draws) == 1 and len(rec.waits) == 1


def test_cancel_set_before_draw_sends_nothing():
    client, draws = _client([])
    cancel = threading.Event()
    cancel.set()
    assert not draw_display_elements(client, ELEMENTS, application_name="app", cancel=cancel)
    assert draws == []


def test_non_409_error_mentioning_409_is_raised():
    client, draws = _client([500], {500: {"error": "upstream returned 409 earlier", "code": 500}})
    with pytest.raises(BusyBarAPIError) as info:
        draw_display_elements(client, ELEMENTS, application_name="app", cancel=Recorder())
    assert info.value.status_code == 500
    assert len(draws) == 1
