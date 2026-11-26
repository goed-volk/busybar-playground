"""Device configuration loading.

:func:`load_app_config` returns every configured device plus the merged environment
(real environment over ``.env``) without touching ``os.environ``. :func:`load_config` is
the v0.2 single-device entry point, kept on top of it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib


CONFIG_DIR_ENV = "BUSYBAR_CONFIG_DIR"
DEVICE_ENV = "BUSYBAR_DEVICE"
TOKEN_ENV = "BUSYBAR_TOKEN"
DEFAULT_APP_DIR = "busybar"
DEVICES_FILE = "devices.toml"
DEVICES_EXAMPLE_FILE = "devices.example.toml"
ENV_FILE = ".env"
DEFAULT_DEVICE_NAME = "office"
DEFAULT_USB_HOST = "10.0.4.20"
PREFER_VALUES = ("wifi", "usb")


class ConfigError(ValueError):
    """Invalid, missing or inconsistent device configuration."""


@dataclass
class DeviceConfig:
    name: str
    label: str
    wifi_host: str | None = None
    usb_host: str | None = None
    prefer: str = "wifi"
    token_env: str | None = None
    token: str | None = field(default=None, repr=False)
    source: Path | None = None  # devices file this config came from, if any


def redact(secret: str | None) -> str:
    """``"<set>"`` or ``"<unset>"``; safe to log or print in place of a token."""
    return "<set>" if secret else "<unset>"


@dataclass(frozen=True)
class AppConfig:
    """All configured devices plus the environment tokens are read from."""

    devices: dict[str, DeviceConfig]
    default_device: str
    source: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict, repr=False)

    def device(self, name: str | None = None) -> DeviceConfig:
        """``name``, else ``$BUSYBAR_DEVICE``, else ``default_device``."""
        target = name or self.env.get(DEVICE_ENV) or self.default_device
        try:
            return self.devices[target]
        except KeyError:
            known = ", ".join(sorted(self.devices)) or "none"
            raise ConfigError(f"Unknown device {target!r} (configured: {known})") from None

    def token_for(self, device: DeviceConfig) -> str | None:
        """Token from ``device.token``, ``device.token_env`` or ``BUSYBAR_TOKEN``; else None.

        A missing token is not an error here: dry runs, listings and unauthenticated
        emulators need none. The device answers 401 when one is required.
        """
        if device.token:
            return device.token
        if device.token_env and self.env.get(device.token_env):
            return self.env[device.token_env]
        return self.env.get(TOKEN_ENV) or None


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
    """First ``devices.toml`` in ``search_dirs``, else the first ``devices.example.toml``.

    Kept for v0.2 callers. :func:`load_app_config` only falls back to the example file
    inside a source checkout's ``config/`` directory.
    """
    for name in (DEVICES_FILE, DEVICES_EXAMPLE_FILE):
        for directory in search_dirs:
            if (directory / name).is_file():
                return directory / name
    return None


def _find_devices_file(search_dirs: list[Path]) -> Path | None:
    for directory in search_dirs:
        if (directory / DEVICES_FILE).is_file():
            return directory / DEVICES_FILE
    checkout = source_checkout_root()
    if checkout is not None and checkout / "config" in search_dirs:
        example = checkout / "config" / DEVICES_EXAMPLE_FILE
        if example.is_file():
            return example
    return None


def _locate_devices_file(
    config: Path | str | None, app_name: str, environ: Mapping[str, str]
) -> Path | None:
    explicit: Path | None = None
    if config is not None:
        explicit = Path(config).expanduser()
    elif environ.get(CONFIG_DIR_ENV):
        explicit = Path(environ[CONFIG_DIR_ENV]).expanduser()

    if explicit is None:
        return _find_devices_file(config_search_dirs(None, app_name, environ))
    if explicit.is_file():
        return explicit
    if explicit.is_dir():
        return _find_devices_file([explicit])
    raise ConfigError(f"Config path does not exist: {explicit}")


def _read_dotenv(
    env_file: Path | str | None,
    devices_file: Path | None,
    app_name: str,
    environ: Mapping[str, str],
) -> dict[str, str]:
    if env_file is not None:
        path = Path(env_file).expanduser()
        if not path.is_file():
            raise ConfigError(f"env_file does not exist: {path}")
        files = [path]
    else:
        candidates = [
            devices_file.parent if devices_file else None,
            source_checkout_root(),
            xdg_config_dir(app_name, environ),
        ]
        files = []
        for directory in candidates:
            if directory is not None and (directory / ENV_FILE).is_file():
                if directory / ENV_FILE not in files:
                    files.append(directory / ENV_FILE)

    merged: dict[str, str] = {}
    for path in files:  # earlier files win, matching load_dotenv(override=False)
        for key, value in dotenv_values(path).items():
            if value is not None:
                merged.setdefault(key, value)
    return merged


def _optional_str(raw: Mapping[str, Any], key: str, where: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{where}: '{key}' must be a string")
    value = value.strip()
    return value or None


def _parse_device(name: str, raw: Any, source: Path) -> DeviceConfig:
    where = f"{source} [devices.{name}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: must be a table")
    if "token" in raw:
        raise ConfigError(
            f"{where}: literal 'token' keys are not allowed. Set token_env to the name of "
            "an environment variable (or .env entry) that holds the token."
        )
    wifi_host = _optional_str(raw, "wifi_host", where)
    usb_host = _optional_str(raw, "usb_host", where)
    if not wifi_host and not usb_host:
        raise ConfigError(f"{where}: set at least one of wifi_host or usb_host")
    prefer = raw.get("prefer", "wifi")
    if prefer not in PREFER_VALUES:
        raise ConfigError(f"{where}: prefer must be 'wifi' or 'usb', got {prefer!r}")

    return DeviceConfig(
        name=name,
        label=_optional_str(raw, "label", where) or name,
        wifi_host=wifi_host,
        usb_host=usb_host,
        prefer=prefer,
        token_env=_optional_str(raw, "token_env", where),
        source=source,
    )


def _parse_devices_file(path: Path) -> tuple[dict[str, DeviceConfig], str]:
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: invalid TOML: {e}") from e

    raw_devices = data.get("devices")
    if not isinstance(raw_devices, dict) or not raw_devices:
        raise ConfigError(f"{path}: no [devices.<name>] tables defined")
    devices = {name: _parse_device(name, raw, path) for name, raw in raw_devices.items()}

    default = data.get("default")
    if default is None:
        default = next(iter(devices))
    elif default not in devices:
        raise ConfigError(f"{path}: default device {default!r} is not defined under [devices]")
    return devices, default


def load_app_config(
    config: Path | str | None = None,
    *,
    env_file: Path | str | None = None,
    app_name: str = DEFAULT_APP_DIR,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load every configured device. Never mutates ``os.environ``.

    ``config`` is a ``devices.toml`` file or a directory holding one; when given (or set
    through ``$BUSYBAR_CONFIG_DIR``) it must exist. Otherwise ``devices.toml`` is looked
    up as described in :func:`config_search_dirs`; ``devices.example.toml`` is only used
    from a source checkout's ``config/`` directory. Without any devices file a single
    USB device at ``10.0.4.20`` is assumed.

    ``.env`` comes from ``env_file`` (must exist), else from next to the devices file,
    the checkout root and the XDG directory. ``environ`` (default ``os.environ``) always
    wins over ``.env`` values. The merged mapping is kept on :attr:`AppConfig.env`.
    """
    base_env = dict(os.environ if environ is None else environ)
    devices_file = _locate_devices_file(config, app_name, base_env)
    dotenv = _read_dotenv(env_file, devices_file, app_name, base_env)
    env = {**dotenv, **base_env}

    if devices_file is None:
        devices = {
            DEFAULT_DEVICE_NAME: DeviceConfig(
                name=DEFAULT_DEVICE_NAME,
                label=DEFAULT_DEVICE_NAME,
                usb_host=DEFAULT_USB_HOST,
                prefer="usb",
            )
        }
        default = DEFAULT_DEVICE_NAME
    else:
        devices, default = _parse_devices_file(devices_file)

    return AppConfig(devices=devices, default_device=default, source=devices_file, env=env)


def load_config(
    config_dir: Path | str | None = None,
    device_name: str | None = None,
    env_file: Path | str | None = None,
    app_name: str = DEFAULT_APP_DIR,
) -> DeviceConfig:
    """v0.2 entry point: one device, with its token filled in.

    Built on :func:`load_app_config`; ``.env`` values no longer leak into
    ``os.environ``. Raises :class:`ConfigError` for an unknown device name.
    """
    app = load_app_config(config_dir, env_file=env_file, app_name=app_name)
    device = app.device(device_name)
    return DeviceConfig(
        name=device.name,
        label=device.label,
        wifi_host=device.wifi_host,
        usb_host=device.usb_host,
        prefer=device.prefer,
        token_env=device.token_env or TOKEN_ENV,
        token=app.token_for(device),
        source=device.source,
    )
