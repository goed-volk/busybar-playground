import json

import httpx2
import pytest
from busylib.types import TextElement

from busybar_kit.client import get_busybar_client
from busybar_kit.config import DeviceConfig
from busybar_kit.draw import apply_display_until, build_text_element, draw_display_elements


def _client():
    bodies: list[dict] = []

    def handler(request):
        if request.url.path == "/api/display/draw":
            bodies.append(json.loads(request.content))
            return httpx2.Response(200, json={"result": "OK"})
        return httpx2.Response(200, json={"api_semver": "27.14.0"})

    client = get_busybar_client(
        config=DeviceConfig("o", "o", token="t"),
        explicit_host="bar.test",
        transport=httpx2.MockTransport(handler),
        reuse=False,
    )
    return client, bodies


def test_display_until_is_sent_per_element():
    client, bodies = _client()
    plain = build_text_element("hi", id="a")
    timed = TextElement(id="b", text="own", font="small", timeout=5)
    assert draw_display_elements(
        client, [plain, timed], application_name="app", display_until=1700000000.9, timeout=5
    )
    sent = {e["id"]: e for e in bodies[0]["elements"]}
    assert sent["a"]["display_until"] == "1700000000"
    assert "display_until" not in sent["b"] and sent["b"]["timeout"] == 5  # mutually exclusive
    assert plain.display_until is None  # caller's object untouched


def test_dict_elements_supported():
    out = apply_display_until(
        [{"id": "x", "type": "text"}, {"id": "y", "type": "text", "timeout": 3}], 1700000000
    )
    assert out[0]["display_until"] == "1700000000"
    assert "display_until" not in out[1]


@pytest.mark.parametrize("bad", [0, -5, True])
def test_invalid_display_until_rejected(bad):
    with pytest.raises(ValueError):
        apply_display_until([build_text_element("hi", id="a")], bad)


def test_display_until_in_dry_run():
    assert draw_display_elements(
        None,
        [build_text_element("hi", id="a")],
        application_name="app",
        display_until=1700000000,
        dry_run=True,
    )
