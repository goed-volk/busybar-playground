import logging
import threading

import httpx2
import pytest
from busylib import BusyBar
from pydantic import ValidationError

from busybar_kit import draw as draw_mod
from busybar_kit.draw import (
    DrawResult,
    build_text_element,
    draw_display_elements,
    draw_display_elements_result,
)

ELEMENTS = [build_text_element("hi", id="t1")]


@pytest.fixture(autouse=True)
def fixed_jitter(monkeypatch):
    monkeypatch.setattr(draw_mod, "uniform", lambda a, b: 0.0)


def _client(statuses):
    draws = []

    def handler(request):
        if request.url.path == "/api/display/draw":
            draws.append(request)
            status = statuses.pop(0) if statuses else 200
            if status != 200:
                return httpx2.Response(status, json={"error": "conflict", "code": status})
            return httpx2.Response(200, json={"result": "OK"})
        return httpx2.Response(200, json={"api_semver": "27.16.0"})

    return BusyBar("http://bar.test", transport=httpx2.MockTransport(handler)), draws


class Waits(threading.Event):
    """Records backoff waits; sets itself on the n-th wait to simulate a mid-wait cancel."""

    def __init__(self, cancel_on: int | None = None):
        super().__init__()
        self.count = 0
        self.cancel_on = cancel_on

    def wait(self, timeout=None):
        self.count += 1
        if self.cancel_on is not None and self.count >= self.cancel_on:
            self.set()
        return self.is_set()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"elements": []},
        {"elements": ELEMENTS, "priority": 0},
        {"elements": ELEMENTS, "priority": 101},
        {"elements": [{"id": "x", "type": "nonsense"}]},
        {"elements": ELEMENTS, "led_notification_color": "not-a-color"},
    ],
)
def test_dry_run_validates_payload(kwargs):
    with pytest.raises((ValueError, ValidationError)):
        draw_display_elements(None, application_name="app", dry_run=True, **kwargs)


def test_dry_run_rejects_bad_application_name():
    with pytest.raises(ValueError):
        draw_display_elements(None, ELEMENTS, application_name="bad name", dry_run=True)


def test_dry_run_does_not_log_at_info(caplog):
    with caplog.at_level(logging.DEBUG):
        for _ in range(20):
            result = draw_display_elements_result(
                None, ELEMENTS, application_name="app", dry_run=True
            )
    assert result is DrawResult.DRY_RUN
    assert not [r for r in caplog.records if r.levelno >= logging.INFO]


def test_drawn():
    client, draws = _client([])
    assert draw_display_elements_result(client, ELEMENTS, application_name="a") is DrawResult.DRAWN
    assert len(draws) == 1


def test_conflict_skipped_vs_cancelled(caplog):
    client, draws = _client([409] * 10)
    with caplog.at_level(logging.DEBUG, logger="busybar_kit"):
        result = draw_display_elements_result(
            client, ELEMENTS, application_name="a", max_409_retries=2, cancel=Waits()
        )
    assert result is DrawResult.CONFLICT_SKIPPED
    assert len(draws) == 3
    kit = [r for r in caplog.records if r.name.startswith("busybar_kit")]
    info = [r for r in kit if r.levelno >= logging.INFO]
    assert len(info) == 1 and info[0].levelno == logging.INFO
    assert len([r for r in kit if "409" in r.getMessage()]) == 3


def test_cancelled_before_draw():
    client, draws = _client([])
    cancel = threading.Event()
    cancel.set()
    result = draw_display_elements_result(client, ELEMENTS, application_name="a", cancel=cancel)
    assert result is DrawResult.CANCELLED
    assert draws == []


def test_cancelled_mid_wait():
    client, draws = _client([409] * 10)
    result = draw_display_elements_result(
        client, ELEMENTS, application_name="a", max_409_retries=5, cancel=Waits(cancel_on=2)
    )
    assert result is DrawResult.CANCELLED
    assert len(draws) == 2


def test_dry_run_wins_over_cancel():
    cancel = threading.Event()
    cancel.set()
    result = draw_display_elements_result(
        None, ELEMENTS, application_name="a", dry_run=True, cancel=cancel
    )
    assert result is DrawResult.DRY_RUN


def test_bool_wrapper_and_ok():
    assert DrawResult.DRAWN.ok and DrawResult.DRY_RUN.ok
    assert not DrawResult.CONFLICT_SKIPPED.ok and not DrawResult.CANCELLED.ok
    assert DrawResult("conflict_skipped") is DrawResult.CONFLICT_SKIPPED
    client, _ = _client([409] * 10)
    assert draw_display_elements(client, ELEMENTS, application_name="a", cancel=Waits()) is False
