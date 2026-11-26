import os
from pathlib import Path

import pytest

from busybar_kit import config as config_mod
from busybar_kit.config import (
    AppConfig,
    ConfigError,
    DeviceConfig,
    load_app_config,
    load_config,
    redact,
)

TWO_DEVICES = """
default = "desk"

[devices.desk]
label = "Desk bar"
wifi_host = "192.168.1.10"
token_env = "DESK_TOKEN"

[devices.lab]
usb_host = "10.0.4.20"
prefer = "usb"
"""


@pytest.fixture(autouse=True)
def installed(monkeypatch, tmp_path):
    """Run as an installed library with an empty XDG directory."""
    monkeypatch.setattr(config_mod, "source_checkout_root", lambda: None)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for key in ("BUSYBAR_TOKEN", "BUSYBAR_DEVICE", "BUSYBAR_CONFIG_DIR", "DESK_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def write(tmp_path: Path, body: str, name: str = "devices.toml") -> Path:
    path = tmp_path / "cfg" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def test_enumerates_all_devices(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    app = load_app_config(path, environ={})
    assert list(app.devices) == ["desk", "lab"]
    assert app.default_device == "desk" and app.source == path
    lab = app.device("lab")
    assert (lab.label, lab.usb_host, lab.prefer, lab.wifi_host) == ("lab", "10.0.4.20", "usb", None)


def test_accepts_directory(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    assert load_app_config(path.parent, environ={}).source == path


def test_device_selection_order(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    app = load_app_config(path, environ={"BUSYBAR_DEVICE": "lab"})
    assert app.device().name == "lab"
    assert app.device("desk").name == "desk"
    assert load_app_config(path, environ={}).device().name == "desk"
    with pytest.raises(ConfigError, match="nope"):
        app.device("nope")


def test_default_is_first_device_when_unset(tmp_path):
    path = write(tmp_path, TWO_DEVICES.replace('default = "desk"', ""))
    assert load_app_config(path, environ={}).default_device == "desk"


def test_token_for_does_not_require_env(tmp_path):
    app = load_app_config(write(tmp_path, TWO_DEVICES), environ={})
    assert app.token_for(app.device("desk")) is None


def test_token_for_prefers_token_env_then_busybar_token(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    app = load_app_config(path, environ={"DESK_TOKEN": "d", "BUSYBAR_TOKEN": "g"})
    assert app.token_for(app.device("desk")) == "d"
    assert app.token_for(app.device("lab")) == "g"


def test_dotenv_is_not_written_to_os_environ(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    (path.parent / ".env").write_text("DESK_TOKEN=from-dotenv\n")
    app = load_app_config(path)
    assert app.token_for(app.device("desk")) == "from-dotenv"
    assert "DESK_TOKEN" not in os.environ


def test_real_environment_wins_over_dotenv(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    env_file = tmp_path / "custom.env"
    env_file.write_text("DESK_TOKEN=from-dotenv\nOTHER=x\n")
    app = load_app_config(path, env_file=env_file, environ={"DESK_TOKEN": "real"})
    assert app.token_for(app.device("desk")) == "real"
    assert app.env["OTHER"] == "x"


def test_missing_explicit_paths_raise(tmp_path):
    with pytest.raises(ConfigError, match="does not exist"):
        load_app_config(tmp_path / "missing.toml", environ={})
    path = write(tmp_path, TWO_DEVICES)
    with pytest.raises(ConfigError, match="env_file"):
        load_app_config(path, env_file=tmp_path / "missing.env", environ={})
    with pytest.raises(ConfigError):
        load_app_config(environ={"BUSYBAR_CONFIG_DIR": str(tmp_path / "gone")})


def test_literal_token_rejected(tmp_path):
    path = write(tmp_path, '[devices.a]\nusb_host = "10.0.4.20"\ntoken = "s3cret"\n')
    with pytest.raises(ConfigError, match="token_env") as info:
        load_app_config(path, environ={})
    assert "s3cret" not in str(info.value)


@pytest.mark.parametrize(
    ("body", "match"),
    [
        ('[devices.a]\nusb_host = "10.0.4.20"\nprefer = "bluetooth"\n', "prefer"),
        ('[devices.a]\nlabel = "No hosts"\n', "wifi_host or usb_host"),
        ('[devices.a]\nwifi_host = "  "\n', "wifi_host or usb_host"),
        ('default = "b"\n[devices.a]\nusb_host = "10.0.4.20"\n', "default device 'b'"),
        ('default = "a"\n', "no \\[devices"),
        ("[devices.a\n", "invalid TOML"),
        ("[devices.a]\nwifi_host = 42\n", "must be a string"),
    ],
)
def test_invalid_config_rejected(tmp_path, body, match):
    with pytest.raises(ConfigError, match=match):
        load_app_config(write(tmp_path, body), environ={})


def test_config_error_is_value_error():
    assert issubclass(ConfigError, ValueError)


def test_no_file_defaults_to_one_usb_device():
    app = load_app_config(environ={})
    assert app.source is None
    device = app.device()
    assert (device.usb_host, device.wifi_host, device.prefer) == ("10.0.4.20", None, "usb")


def test_example_file_ignored_outside_checkout(tmp_path):
    xdg = tmp_path / "xdg" / "busybar"
    xdg.mkdir(parents=True)
    (xdg / "devices.example.toml").write_text(TWO_DEVICES)
    assert load_app_config().source is None


def test_secrets_never_in_repr(tmp_path):
    path = write(tmp_path, TWO_DEVICES)
    app = load_app_config(path, environ={"DESK_TOKEN": "s3cret"})
    assert "s3cret" not in repr(app)
    assert "s3cret" not in repr(DeviceConfig("a", "a", token="s3cret"))
    assert "s3cret" not in repr(load_config(path.parent, device_name="desk"))


def test_redact():
    assert redact("abc") == "<set>"
    assert redact("") == "<unset>" and redact(None) == "<unset>"


def test_load_config_compat_fills_token(tmp_path, monkeypatch):
    path = write(tmp_path, TWO_DEVICES)
    monkeypatch.setenv("BUSYBAR_TOKEN", "g")
    cfg = load_config(path.parent, device_name="lab")
    assert (cfg.name, cfg.token, cfg.token_env) == ("lab", "g", "BUSYBAR_TOKEN")
    assert load_config(path.parent).token == "g"  # desk falls back to BUSYBAR_TOKEN


def test_app_config_is_frozen():
    app = AppConfig(devices={}, default_device="x")
    with pytest.raises(AttributeError):
        app.default_device = "y"  # type: ignore[misc]
