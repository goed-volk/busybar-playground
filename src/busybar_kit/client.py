import logging
from typing import Any

import httpx2
from busylib import AsyncBusyBar, BusyBar
from busylib.versioning import API_VERSION

from busybar_kit.config import DeviceConfig, load_config
from busybar_kit.resolve import resolve_device_connection

logger = logging.getLogger(__name__)

_sync_clients: dict[str, BusyBar] = {}
_async_clients: dict[str, AsyncBusyBar] = {}


def get_busybar_client(
    config: DeviceConfig | None = None,
    explicit_host: str | None = None,
    transport: httpx2.BaseTransport | None = None,
    timeout: float | httpx2.Timeout | None = None,
    max_retries: int = 2,
    backoff: float = 0.25,
    compatibility_mode: str = "warn",
    reuse: bool = True,
) -> BusyBar:
    if config is None:
        config = load_config()

    cache_key = f"{config.name}:{explicit_host}"
    if reuse and cache_key in _sync_clients and transport is None:
        return _sync_clients[cache_key]

    resolved = resolve_device_connection(config=config, explicit_host=explicit_host)

    kwargs: dict[str, Any] = {
        "addr": resolved.addr,
        "token": resolved.token,
        "max_retries": max_retries,
        "backoff": backoff,
        "compatibility_mode": compatibility_mode,
    }
    if transport is not None:
        kwargs["transport"] = transport
    if timeout is not None:
        kwargs["timeout"] = timeout

    client = BusyBar(**kwargs)

    try:
        ver_info = client.version()
        measured_semver = getattr(ver_info, "api_semver", getattr(ver_info, "version", "unknown"))
        logger.info(
            "Connected to device '%s' at %s (API semver: %s, library target: %s)",
            config.name,
            resolved.addr,
            measured_semver,
            API_VERSION,
        )
    except Exception as e:
        logger.warning(
            "Connected to device '%s' at %s but version check failed: %s",
            config.name,
            resolved.addr,
            e,
        )

    if reuse and transport is None:
        _sync_clients[cache_key] = client

    return client


def get_async_busybar_client(
    config: DeviceConfig | None = None,
    explicit_host: str | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
    timeout: float | httpx2.Timeout | None = None,
    max_retries: int = 2,
    backoff: float = 0.25,
    compatibility_mode: str = "warn",
    reuse: bool = True,
) -> AsyncBusyBar:
    if config is None:
        config = load_config()

    cache_key = f"{config.name}:{explicit_host}"
    if reuse and cache_key in _async_clients and transport is None:
        return _async_clients[cache_key]

    resolved = resolve_device_connection(config=config, explicit_host=explicit_host)

    kwargs: dict[str, Any] = {
        "addr": resolved.addr,
        "token": resolved.token,
        "max_retries": max_retries,
        "backoff": backoff,
        "compatibility_mode": compatibility_mode,
    }
    if transport is not None:
        kwargs["transport"] = transport
    if timeout is not None:
        kwargs["timeout"] = timeout

    client = AsyncBusyBar(**kwargs)

    if reuse and transport is None:
        _async_clients[cache_key] = client

    return client


def close_clients() -> None:
    for client in _sync_clients.values():
        try:
            client.close()
        except Exception:
            pass
    _sync_clients.clear()
    _async_clients.clear()
