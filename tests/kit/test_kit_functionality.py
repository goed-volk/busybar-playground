import logging

import pytest

from busybar_kit.config import load_config
from busybar_kit.draw import build_text_element, draw_display_elements
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
