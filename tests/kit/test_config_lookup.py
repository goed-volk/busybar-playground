import os
from pathlib import Path

import pytest

from busybar_kit import config as config_mod
from busybar_kit.config import (
    config_search_dirs,
    get_project_root,
    load_config,
    source_checkout_root,
    xdg_config_dir,
)

DEVICES = """
default = "{name}"

[devices.{name}]
label = "{label}"
wifi_host = "{wifi}"
token_env = "{token_env}"
"""


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """load_dotenv writes into os.environ; restore it fully after each test."""
    saved = dict(os.environ)
    for key in ("BUSYBAR_TOKEN", "BUSYBAR_DEVICE", "BUSYBAR_CONFIG_DIR", "LIB_TOKEN", "REPO_TOKEN"):
        os.environ.pop(key, None)
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    yield
    os.environ.clear()
    os.environ.update(saved)


def write_config(directory: Path, name: str, label: str, wifi: str, token_env: str, token=None):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "devices.toml").write_text(
        DEVICES.format(name=name, label=label, wifi=wifi, token_env=token_env)
    )
    if token is not None:
        (directory / ".env").write_text(f"{token_env}={token}\n")


@pytest.fixture
def installed(monkeypatch):
    """Simulate the kit installed in site-packages (no source checkout)."""
    monkeypatch.setattr(config_mod, "source_checkout_root", lambda: None)


def test_running_from_this_checkout_is_detected():
    assert source_checkout_root() == get_project_root()
    assert (get_project_root() / "config" / "devices.example.toml").is_file()


def test_installed_reads_xdg_config_and_env(installed, tmp_path):
    xdg = tmp_path / "xdg" / "busybar"
    write_config(xdg, "lib", "Library bar", "192.168.1.7", "LIB_TOKEN", token="from-xdg-env")
    cfg = load_config()
    assert (cfg.name, cfg.label, cfg.wifi_host) == ("lib", "Library bar", "192.168.1.7")
    assert cfg.token == "from-xdg-env"
    assert cfg.source == xdg / "devices.toml"


def test_installed_app_name_selects_xdg_subdir(installed, tmp_path):
    write_config(tmp_path / "xdg" / "busybar-tray", "tray", "Tray bar", "10.1.1.1", "LIB_TOKEN")
    os.environ["LIB_TOKEN"] = "t"
    assert load_config(app_name="busybar-tray").name == "tray"
    assert xdg_config_dir("busybar-tray") == tmp_path / "xdg" / "busybar-tray"


def test_installed_without_any_config_defaults_to_usb(installed):
    cfg = load_config()
    assert cfg.usb_host == "10.0.4.20" and cfg.wifi_host is None
    assert cfg.source is None


def test_installed_never_uses_site_packages_relative_paths(installed, tmp_path):
    dirs = config_search_dirs()
    assert dirs == [tmp_path / "xdg" / "busybar"]


def test_config_dir_env_override(installed, tmp_path):
    custom = tmp_path / "elsewhere"
    write_config(custom, "env", "Env bar", "10.2.2.2", "LIB_TOKEN", token="x")
    write_config(tmp_path / "xdg" / "busybar", "lib", "Library bar", "10.3.3.3", "LIB_TOKEN")
    os.environ["BUSYBAR_CONFIG_DIR"] = str(custom)
    cfg = load_config()
    assert cfg.name == "env" and cfg.source == custom / "devices.toml"


def test_explicit_config_dir_wins(installed, tmp_path):
    explicit = tmp_path / "explicit"
    write_config(explicit, "exp", "Explicit", "10.4.4.4", "LIB_TOKEN", token="x")
    os.environ["BUSYBAR_CONFIG_DIR"] = str(tmp_path / "ignored")
    assert load_config(config_dir=explicit).name == "exp"


def test_checkout_config_takes_precedence_over_xdg(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "src" / "busybar_kit").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='busybar-kit'\n")
    write_config(repo / "config", "repo", "Repo bar", "10.5.5.5", "REPO_TOKEN")
    (repo / ".env").write_text("REPO_TOKEN=from-repo-root\n")
    write_config(tmp_path / "xdg" / "busybar", "lib", "Library bar", "10.6.6.6", "LIB_TOKEN")
    monkeypatch.setattr(config_mod, "get_project_root", lambda: repo)
    cfg = load_config()
    assert cfg.name == "repo" and cfg.token == "from-repo-root"
    assert config_search_dirs() == [repo / "config", tmp_path / "xdg" / "busybar"]


def test_example_file_used_only_as_last_resort(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "src" / "busybar_kit").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("")
    (repo / "config").mkdir()
    (repo / "config" / "devices.example.toml").write_text(
        DEVICES.format(name="ex", label="Example", wifi="192.168.1.42", token_env="LIB_TOKEN")
    )
    monkeypatch.setattr(config_mod, "get_project_root", lambda: repo)
    os.environ["LIB_TOKEN"] = "t"
    assert load_config().name == "ex"
    write_config(tmp_path / "xdg" / "busybar", "lib", "Library bar", "10.7.7.7", "LIB_TOKEN")
    assert load_config().name == "lib"  # a real devices.toml beats the example


def test_dotenv_does_not_override_real_environment(installed, tmp_path):
    write_config(
        tmp_path / "xdg" / "busybar", "lib", "Lib", "10.8.8.8", "LIB_TOKEN", token="dotenv"
    )
    os.environ["LIB_TOKEN"] = "real"
    assert load_config().token == "real"
