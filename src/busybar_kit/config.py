import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import tomllib
except ImportError:
    import tomli as tomllib


CONFIG_DIR_ENV = "BUSYBAR_CONFIG_DIR"
DEFAULT_APP_DIR = "busybar"
DEVICES_FILE = "devices.toml"
DEVICES_EXAMPLE_FILE = "devices.example.toml"
ENV_FILE = ".env"


@dataclass
class DeviceConfig:
    name: str
    label: str
    wifi_host: str | None = None
    usb_host: str | None = None
    prefer: str = "wifi"
    token_env: str | None = None
    token: str | None = None
    source: Path | None = None  # devices file this config came from, if any


def get_project_root() -> Path:
    """Three levels above this file: the repository root in a source checkout."""
    return Path(__file__).resolve().parent.parent.parent


def source_checkout_root() -> Path | None:
    """Repository root when the kit runs from a checkout (editable install), else None.

    An installed kit lives in site-packages, where the path three levels up is not a
    project directory, so repository-relative ``config/`` and ``.env`` must not be used.
    """
    root = get_project_root()
    if (root / "pyproject.toml").is_file() and (root / "src" / "busybar_kit").is_dir():
        return root
    return None


def xdg_config_dir(
    app_name: str = DEFAULT_APP_DIR, environ: Mapping[str, str] | None = None
) -> Path:
    environ = os.environ if environ is None else environ
    base = environ.get("XDG_CONFIG_HOME", "")
    root = Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    return root / app_name


def config_search_dirs(
    config_dir: Path | str | None = None,
    app_name: str = DEFAULT_APP_DIR,
    environ: Mapping[str, str] | None = None,
) -> list[Path]:
    """Directories searched for ``devices.toml``, in order.

    1. ``config_dir`` argument, alone.
    2. ``$BUSYBAR_CONFIG_DIR``, alone.
    3. ``<repo>/config`` when running from a source checkout, then
       ``$XDG_CONFIG_HOME/<app_name>`` (default ``~/.config/busybar``).
    """
    environ = os.environ if environ is None else environ
    if config_dir is not None:
        return [Path(config_dir).expanduser()]
    if environ.get(CONFIG_DIR_ENV):
        return [Path(environ[CONFIG_DIR_ENV]).expanduser()]
    dirs: list[Path] = []
    checkout = source_checkout_root()
    if checkout is not None:
        dirs.append(checkout / "config")
    dirs.append(xdg_config_dir(app_name, environ))
    return dirs


def find_devices_file(search_dirs: list[Path]) -> Path | None:
    """First ``devices.toml`` in ``search_dirs``, else the first ``devices.example.toml``."""
    for name in (DEVICES_FILE, DEVICES_EXAMPLE_FILE):
        for directory in search_dirs:
            if (directory / name).is_file():
                return directory / name
    return None


def load_config(
    config_dir: Path | str | None = None,
    device_name: str | None = None,
    env_file: Path | str | None = None,
    app_name: str = DEFAULT_APP_DIR,
) -> DeviceConfig:
    """Load one device's config. Safe both from a checkout and as an installed library.

    ``devices.toml`` is looked up as described in :func:`config_search_dirs`. Without
    any file, a single USB device at ``10.0.4.20`` is assumed. ``.env`` comes from
    ``env_file``, else from next to the devices file, the checkout root and the XDG
    directory; values never override variables already in the environment.
    """
    search_dirs = config_search_dirs(config_dir, app_name)
    devices_file = find_devices_file(search_dirs)

    if env_file is not None:
        load_dotenv(env_file)
    else:
        checkout = source_checkout_root()
        candidates = [
            devices_file.parent if devices_file else None,
            checkout,
            xdg_config_dir(app_name),
        ]
        seen: set[Path] = set()
        for directory in candidates:
            if directory is None or directory in seen:
                continue
            seen.add(directory)
            if (directory / ENV_FILE).is_file():
                load_dotenv(directory / ENV_FILE)

    devices_data: dict[str, Any] = {}
    if devices_file is not None:
        with open(devices_file, "rb") as f:
            devices_data = tomllib.load(f)

    target_device = (
        device_name or os.environ.get("BUSYBAR_DEVICE") or devices_data.get("default") or "office"
    )

    devices = devices_data.get("devices", {})
    device_raw = devices.get(target_device, {})

    token_env = device_raw.get("token_env") or "BUSYBAR_TOKEN"
    token = os.environ.get(token_env) or os.environ.get("BUSYBAR_TOKEN")

    if not token and token_env in os.environ:
        token = os.environ[token_env]

    if not token and "token_env" in device_raw and not os.environ.get(device_raw["token_env"]):
        raise ValueError(
            f"Missing required environment variable '{device_raw['token_env']}' "
            f"for device '{target_device}'"
        )

    return DeviceConfig(
        name=target_device,
        label=device_raw.get("label", target_device),
        wifi_host=device_raw.get("wifi_host"),
        usb_host=device_raw.get("usb_host", "10.0.4.20"),
        prefer=device_raw.get("prefer", "wifi"),
        token_env=token_env,
        token=token,
        source=devices_file,
    )
