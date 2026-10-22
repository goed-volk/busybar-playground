import logging

import pytest

from busybar_kit.client import close_clients, get_busybar_client
from busybar_kit.config import load_config
from busybar_kit.draw import build_rectangle_element, build_text_element, draw_display_elements
from busybar_kit.resolve import clear_resolution_cache, resolve_device_connection
from busybar_kit.text import sanitize_text


def test_text_sanitizer():
    assert sanitize_text("Hello World") == "Hello World"
    assert sanitize_text("Regen & Buien (ë é €)") == "Regen & Buien (e e EUR)"
    assert sanitize_text("Test Emoji 🌧️") == "Test Emoji "

    with pytest.raises(ValueError):
        sanitize_text("🌧️")


def test_config_resolution(tmp_registry):
    clear_resolution_cache()
    config = load_config(config_dir=tmp_registry)
    assert config.name == "office"
    assert config.token == "test_secret_token_123"


def test_resolve_explicit_host(tmp_registry):
    clear_resolution_cache()
    config = load_config(config_dir=tmp_registry)
    resolved = resolve_device_connection(config=config, explicit_host="192.168.1.50")
    assert resolved.addr == "http://192.168.1.50"


def test_dry_run_zero_writes(caplog):
    elem = build_text_element("Dry run text")
    with caplog.at_level(logging.INFO):
        res = draw_display_elements(
            client=None,
            elements=[elem],
            application_name="dry_app",
            dry_run=True,
        )
    assert res is True
    assert "[DRY-RUN]" in caplog.text


def test_build_rectangle_element_defaults():
    rect = build_rectangle_element(width=20, height=10, id="rect_test")
    assert rect.id == "rect_test"
    assert rect.width == 20
    assert rect.height == 10
    assert rect.fill == "solid"
    assert rect.fill_colors == ["#FFFFFFFF"]
    assert rect.border_width == 0
    assert rect.border_color == "#FFFFFFFF"
    assert rect.radius == 0


def test_build_rectangle_element_custom_styling():
    rect = build_rectangle_element(
        width=30,
        height=15,
        id="styled_rect",
        color="#11223344",
        fill="gradient_h",
        fill_colors=["#000000FF", "#FFFFFFFF"],
        border_width=2,
        border_color="#FF0000FF",
        radius=3,
    )
    assert rect.id == "styled_rect"
    assert rect.width == 30
    assert rect.height == 15
    assert rect.fill == "gradient_h"
    assert rect.fill_colors == ["#000000FF", "#FFFFFFFF"]
    assert rect.border_width == 2
    assert rect.border_color == "#FF0000FF"
    assert rect.radius == 3


def test_draw_display_elements_with_mock_client(mock_bar_transport, monkeypatch):
    monkeypatch.setenv("BUSYBAR_TOKEN", "mock_token")
    transport, requests = mock_bar_transport
    client = get_busybar_client(
        explicit_host="http://192.168.1.100",
        transport=transport,
        reuse=False,
    )
    txt = build_text_element("Live test", id="t1")
    res = draw_display_elements(
        client=client,
        elements=[txt],
        application_name="test_live",
        priority=60,
    )
    assert res is True
    assert any("/api/display/draw" in req.url.path for req in requests)
    close_clients()


def test_draw_display_elements_409_retry_handling(monkeypatch):
    monkeypatch.setenv("BUSYBAR_TOKEN", "mock_token")
    from httpx2 import MockTransport, Request, Response

    requests: list[Request] = []

    def handler_409(request: Request) -> Response:
        requests.append(request)
        if "/api/display/draw" in request.url.path:
            return Response(409, json={"error": "Priority conflict", "code": 409})
        return Response(200, json={"version": "1.2.3", "api_semver": "27.5.0"})

    transport = MockTransport(handler_409)
    client = get_busybar_client(
        explicit_host="http://192.168.1.100",
        transport=transport,
        reuse=False,
    )
    txt = build_text_element("Conflict test", id="t2")

    res = draw_display_elements(
        client=client,
        elements=[txt],
        application_name="conflict_app",
        priority=50,
        max_409_retries=1,
        initial_backoff=0.01,
    )
    assert res is False
    assert len([r for r in requests if "/api/display/draw" in r.url.path]) == 2
    close_clients()
