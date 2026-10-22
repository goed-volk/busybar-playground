import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import tomllib
except ImportError:
    import tomli as tomllib


@dataclass
class DeviceConfig:
    name: str
    label: str
    wifi_host: str | None = None
    usb_host: str | None = None
    prefer: str = "wifi"
    token_env: str | None = None
    token: str | None = None


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_config(
    config_dir: Path | str | None = None,
    device_name: str | None = None,
    env_file: Path | str | None = None,
) -> DeviceConfig:
    root = get_project_root()

    if env_file is None:
        dotenv_path = root / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path)
    else:
        load_dotenv(env_file)

    if config_dir is None:
        config_path = root / "config"
    else:
        config_path = Path(config_dir)

    devices_file = config_path / "devices.toml"
    if not devices_file.exists():
        devices_file = config_path / "devices.example.toml"

    devices_data: dict[str, Any] = {}
    if devices_file.exists():
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
    )
