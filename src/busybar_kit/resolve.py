"""Wi-Fi-first device connection resolution.

:func:`resolve_device` is pure apart from the probe: no module state, no caching. It
returns a :class:`Resolution` that says which address was chosen, why, and whether the
device answered. :func:`resolve_device_connection` is the cached v0.2 wrapper.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, NamedTuple
from urllib.parse import urlsplit

import httpx2

from busybar_kit.config import DEFAULT_USB_HOST, DeviceConfig, load_config

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_USB_HOST",
    "REACHABLE_STATUS",
    "Resolution",
    "ResolvedConnection",
    "candidate_hosts",
    "clear_resolution_cache",
    "is_device_reachable",
    "looks_like_busybar",
    "normalize_addr",
    "resolve_device",
    "resolve_device_connection",
]

ResolutionSource = Literal["explicit", "wifi", "usb", "fallback"]

# 401/403 still prove a BUSY Bar is answering (token missing, or Wi-Fi API disabled).
REACHABLE_STATUS = frozenset({200, 401, 403})


def normalize_addr(host: str) -> str:
    """``http://`` + host without trailing slash. Raises ``ValueError`` on empty input."""
    if not isinstance(host, str):
        raise ValueError(f"host must be a string, got {type(host).__name__}")
    value = host.strip()
    scheme = "http"
    if value.lower().startswith(("http://", "https://")):
        scheme, value = value.split("://", 1)
    value = value.rstrip("/")
    if not value:
        raise ValueError("host is empty")
    return f"{scheme.lower()}://{value}"


def _safe_host(addr: str) -> str:
    """Host and port only, so URL userinfo never reaches a log line."""
    try:
        parts = urlsplit(addr)
        host = parts.hostname or "?"
        return f"{host}:{parts.port}" if parts.port else host
    except ValueError:
        return "?"


@dataclass(frozen=True)
class Resolution:
    """Outcome of resolving one device.

    ``reachable`` is True when the probe succeeded, False for the unprobed-or-failed
    fallback, and None for an explicit host (never probed).
    """

    addr: str
    source: ResolutionSource
    reachable: bool | None
    token: str | None = field(default=None, repr=False)

    @property
    def host(self) -> str:
        return self.addr.split("://", 1)[-1].rstrip("/")


class ResolvedConnection(NamedTuple):
    addr: str
    token: str | None


def candidate_hosts(device: DeviceConfig) -> list[tuple[Literal["wifi", "usb"], str]]:
    """``(source, addr)`` pairs in ``device.prefer`` order, deduplicated by normalized address."""
    order: tuple[Literal["wifi", "usb"], ...] = (
        ("usb", "wifi") if device.prefer == "usb" else ("wifi", "usb")
    )
    seen: set[str] = set()
    result: list[tuple[Literal["wifi", "usb"], str]] = []
    for source in order:
        host = device.usb_host if source == "usb" else device.wifi_host
        if not host or not host.strip():
            continue
        addr = normalize_addr(host)
        if addr.lower() in seen:
            continue
        seen.add(addr.lower())
        result.append((source, addr))
    return result


def looks_like_busybar(response: httpx2.Response) -> bool:
    """Match the API response shapes, so captive portals and gateway 403 pages are rejected.

    200 must carry ``VersionInfo`` (``api_semver``); 401/403 must carry the JSON ``Error``
    object (``error``).
    """
    if response.status_code not in REACHABLE_STATUS:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    return ("api_semver" if response.status_code == 200 else "error") in body


def is_device_reachable(
    addr: str,
    timeout: float = 1.5,
    transport: httpx2.BaseTransport | None = None,
) -> bool:
    """True when ``addr`` answers ``GET /api/version`` like a BUSY Bar. Never raises.

    Environment proxies are ignored: a device is always on the LAN or USB link, and a
    proxy or gateway answering in its place must not count as reachable. Failures are
    logged at DEBUG with the exception type only.
    """
    try:
        url = f"{normalize_addr(addr)}/api/version"
        with httpx2.Client(timeout=timeout, transport=transport, trust_env=False) as http:
            response = http.get(url)
    except Exception as exc:
        logger.debug("Probe of %s failed: %s", _safe_host(str(addr)), type(exc).__name__)
        return False
    ok = looks_like_busybar(response)
    if not ok:
        logger.debug(
            "Probe of %s: HTTP %d is not a BUSY Bar response",
            _safe_host(url),
            response.status_code,
        )
    return ok


def resolve_device(
    device: DeviceConfig,
    token: str | None = None,
    *,
    explicit_host: str | None = None,
    probe_fn: Callable[[str], bool] | None = None,
    timeout: float = 1.0,
    transport: httpx2.BaseTransport | None = None,
) -> Resolution:
    """Pick the address for ``device``. No caching; every call probes again.

    ``explicit_host`` is used as-is without probing. Otherwise :func:`candidate_hosts`
    are probed in order and the first reachable one wins. When none answers, the
    device's ``usb_host`` (or ``10.0.4.20``) is returned with ``reachable=False``.
    ``token`` defaults to ``device.token``.
    """
    if token is None:
        token = device.token
    if explicit_host:
        return Resolution(normalize_addr(explicit_host), "explicit", None, token)

    if probe_fn is None:

        def probe_fn(addr: str) -> bool:
            if transport is None:
                return is_device_reachable(addr, timeout=timeout)
            return is_device_reachable(addr, timeout=timeout, transport=transport)

    for source, addr in candidate_hosts(device):
        if probe_fn(addr):
            logger.debug("Resolved device '%s' via %s to %s", device.name, source, addr)
            return Resolution(addr, source, True, token)

    fallback = normalize_addr(device.usb_host or DEFAULT_USB_HOST)
    logger.debug("No candidate answered for device '%s'; falling back to %s", device.name, fallback)
    return Resolution(fallback, "fallback", False, token)


_resolved_cache: dict[str, ResolvedConnection] = {}


def resolve_device_connection(
    config: DeviceConfig | None = None,
    explicit_host: str | None = None,
    use_cache: bool = True,
) -> ResolvedConnection:
    """v0.2 wrapper over :func:`resolve_device` with a process-wide cache."""
    if config is None:
        config = load_config()

    cache_key = f"{config.name}:{explicit_host}"
    if use_cache and cache_key in _resolved_cache:
        return _resolved_cache[cache_key]

    resolution = resolve_device(config, explicit_host=explicit_host)
    result = ResolvedConnection(addr=resolution.addr, token=resolution.token)
    if use_cache:
        _resolved_cache[cache_key] = result
    return result


def clear_resolution_cache() -> None:
    _resolved_cache.clear()
