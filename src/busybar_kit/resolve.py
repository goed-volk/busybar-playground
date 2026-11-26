import logging
from typing import NamedTuple

import httpx2

from busybar_kit.config import DeviceConfig, load_config

logger = logging.getLogger(__name__)

DEFAULT_USB_HOST = "10.0.4.20"


class ResolvedConnection(NamedTuple):
    addr: str
    token: str | None


_resolved_cache: dict[str, ResolvedConnection] = {}


# 401/403 still prove a BUSY Bar is answering (token missing, or Wi-Fi API disabled).
REACHABLE_STATUS = frozenset({200, 401, 403})


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
    proxy or gateway answering in its place must not count as reachable.
    """
    formatted_addr = addr if addr.startswith(("http://", "https://")) else f"http://{addr}"
    url = f"{formatted_addr.rstrip('/')}/api/version"
    try:
        with httpx2.Client(timeout=timeout, transport=transport, trust_env=False) as http:
            response = http.get(url)
    except Exception:
        return False
    return looks_like_busybar(response)


def resolve_device_connection(
    config: DeviceConfig | None = None,
    explicit_host: str | None = None,
    use_cache: bool = True,
) -> ResolvedConnection:
    if config is None:
        config = load_config()

    cache_key = f"{config.name}:{explicit_host}"
    if use_cache and cache_key in _resolved_cache:
        return _resolved_cache[cache_key]

    if explicit_host:
        target_addr = (
            explicit_host
            if explicit_host.startswith(("http://", "https://"))
            else f"http://{explicit_host}"
        )
        res = ResolvedConnection(addr=target_addr, token=config.token)
        if use_cache:
            _resolved_cache[cache_key] = res
        return res

    candidates = []
    if config.prefer == "wifi" and config.wifi_host:
        candidates.append(config.wifi_host)
    if config.usb_host:
        candidates.append(config.usb_host)
    if config.prefer == "usb" and config.wifi_host and config.wifi_host not in candidates:
        candidates.append(config.wifi_host)

    for cand in candidates:
        formatted_cand = cand if cand.startswith(("http://", "https://")) else f"http://{cand}"
        if is_device_reachable(formatted_cand):
            logger.info(
                "Resolved device '%s' to reachable candidate '%s'", config.name, formatted_cand
            )
            res = ResolvedConnection(addr=formatted_cand, token=config.token)
            if use_cache:
                _resolved_cache[cache_key] = res
            return res

    fallback_addr = f"http://{DEFAULT_USB_HOST}"
    logger.info("Fallback to default USB host '%s' for device '%s'", fallback_addr, config.name)
    res = ResolvedConnection(addr=fallback_addr, token=config.token)
    if use_cache:
        _resolved_cache[cache_key] = res
    return res


def clear_resolution_cache() -> None:
    _resolved_cache.clear()
