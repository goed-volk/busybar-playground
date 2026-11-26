"""busylib client construction and a session owner for long-running hosts.

:func:`make_client` builds one uncached client without network I/O.
:class:`DeviceSession` owns one lazily created client per device for workers and
daemons. ``get_busybar_client`` and friends are the cached v0.2 helpers.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from typing import Any

import httpx2
from busylib import AsyncBusyBar, BusyBar
from busylib.exceptions import BusyBarAPIError, BusyBarError
from busylib.versioning import API_VERSION

from busybar_kit.config import DeviceConfig, load_config
from busybar_kit.draw import (
    MAX_409_BACKOFF,
    PRIORITY_INFO_DEFAULT,
    DrawResult,
    draw_display_elements_result,
)
from busybar_kit.resolve import Resolution, normalize_addr, resolve_device_connection
from busybar_kit.text import validate_identifier

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
    # An explicit transport keeps httpx2 from routing LAN/USB device traffic through
    # HTTP(S)_PROXY from the environment.
    kwargs["transport"] = transport if transport is not None else httpx2.HTTPTransport()
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
    kwargs["transport"] = transport if transport is not None else httpx2.AsyncHTTPTransport()
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


class DeviceError(RuntimeError):
    """A device write failed. The message never contains tokens."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def describe_error(exc: BaseException) -> str:
    """``"HTTP <code>: <error>"`` for API errors, else the exception type name."""
    if isinstance(exc, BusyBarAPIError):
        return f"HTTP {exc.status_code}: {exc.error}"
    return type(exc).__name__


def _wrap(exc: BaseException) -> DeviceError:
    # BusyBarAPIError subclasses BusyBarError: check it first to keep status_code.
    status = exc.status_code if isinstance(exc, BusyBarAPIError) else None
    return DeviceError(describe_error(exc), status_code=status)


_DEVICE_ERRORS = (BusyBarError, httpx2.HTTPError, OSError)


def make_client(
    addr: str,
    *,
    token: str | None = None,
    transport: httpx2.BaseTransport | None = None,
    timeout: float = 3.0,
    max_retries: int = 1,
    compatibility_mode: str = "warn",
) -> BusyBar:
    """One new ``BusyBar`` client. No caching and no network I/O.

    Without ``transport`` an explicit ``httpx2.HTTPTransport()`` is passed, so
    ``HTTP(S)_PROXY`` never routes device traffic.
    """
    return BusyBar(
        normalize_addr(addr),
        token=token,
        timeout=timeout,
        max_retries=max_retries,
        transport=transport if transport is not None else httpx2.HTTPTransport(),
        compatibility_mode=compatibility_mode,  # type: ignore[arg-type]
    )


class DeviceSession:
    """Owns one reused client for one device and application.

    ``target`` is a :class:`~busybar_kit.resolve.Resolution` or an address. With
    ``dry_run=True`` no client or transport is ever constructed. ``draw``, ``clear`` and
    ``close`` are thread-safe; draws and clears are serialized so they reach the device
    in call order. ``close()`` sets the session's ``cancel`` event, which interrupts a
    draw waiting in 409 backoff unless that draw was given its own ``cancel``.
    """

    def __init__(
        self,
        target: Resolution | str,
        *,
        application_name: str,
        token: str | None = None,
        dry_run: bool = False,
        transport: httpx2.BaseTransport | None = None,
        timeout: float = 3.0,
        max_retries: int = 1,
        client_factory: Callable[..., BusyBar] | None = None,
        cancel: threading.Event | None = None,
    ) -> None:
        if isinstance(target, Resolution):
            self.addr = target.addr
            self._token = token if token is not None else target.token
        else:
            self.addr = normalize_addr(target)
            self._token = token
        self.application_name = validate_identifier(application_name, "application_name")
        self.dry_run = dry_run
        self.cancel = cancel if cancel is not None else threading.Event()
        self._transport = transport
        self._timeout = timeout
        self._max_retries = max_retries
        self._factory = client_factory or make_client
        self._client: BusyBar | None = None
        self._client_lock = threading.Lock()
        self._io_lock = threading.RLock()
        self._closed = False
        self.writes = 0

    def __repr__(self) -> str:
        return (
            f"DeviceSession(addr={self.addr!r}, application_name={self.application_name!r}, "
            f"dry_run={self.dry_run}, closed={self._closed})"
        )

    def __enter__(self) -> DeviceSession:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def client(self) -> BusyBar | None:
        """The session's client, created on first use. Always None in dry-run."""
        if self.dry_run:
            return None
        with self._client_lock:
            if self._closed:
                raise DeviceError("session is closed")
            if self._client is None:
                self._client = self._factory(
                    self.addr,
                    token=self._token,
                    transport=self._transport,
                    timeout=self._timeout,
                    max_retries=self._max_retries,
                )
            return self._client

    def draw(
        self,
        elements: list[Any],
        *,
        priority: int = PRIORITY_INFO_DEFAULT,
        display_until: int | float | None = None,
        led_notification_color: str | None = None,
        request_timeout: float | None = None,
        max_409_retries: int = 3,
        initial_backoff: float = 0.5,
        max_backoff: float = MAX_409_BACKOFF,
        cancel: threading.Event | None = None,
    ) -> DrawResult:
        """Draw through :func:`~busybar_kit.draw.draw_display_elements_result`.

        Invalid payloads raise ``ValueError``/``ValidationError`` (also in dry-run).
        Transport and non-409 API failures raise :class:`DeviceError`. A closed session
        returns ``CANCELLED``.
        """
        with self._io_lock:
            if self._closed:
                return DrawResult.CANCELLED
            try:
                result = draw_display_elements_result(
                    self.client,
                    elements,
                    application_name=self.application_name,
                    priority=priority,
                    timeout=request_timeout,
                    display_until=display_until,
                    led_notification_color=led_notification_color,
                    dry_run=self.dry_run,
                    max_409_retries=max_409_retries,
                    initial_backoff=initial_backoff,
                    max_backoff=max_backoff,
                    cancel=cancel if cancel is not None else self.cancel,
                )
            except DeviceError:
                raise
            except _DEVICE_ERRORS as e:
                raise _wrap(e) from e
            if result is DrawResult.DRAWN:
                self.writes += 1
            return result

    def clear(self, element_ids: Sequence[str] | None = None) -> bool:
        """Remove this application's elements (all, or ``element_ids``). Never raises
        for device or transport errors; returns False instead. True in dry-run."""
        with self._io_lock:
            if self._closed:
                return False
            if element_ids is not None and not element_ids:
                return True  # nothing to remove; an empty list would mean "all" on the wire
            if self.dry_run:
                logger.debug("[DRY-RUN] Would clear app '%s'", self.application_name)
                return True
            try:
                client = self.client
                if client is None:  # pragma: no cover - only None in dry-run
                    return False
                client.display_clear(
                    element_ids=list(element_ids) if element_ids is not None else None,
                    application_name=self.application_name,
                )
            except (DeviceError, *_DEVICE_ERRORS) as e:
                logger.warning(
                    "Clear for app '%s' failed: %s", self.application_name, describe_error(e)
                )
                return False
            self.writes += 1
            return True

    def close(self) -> None:
        """Interrupt pending backoff and close the client. Idempotent."""
        self.cancel.set()
        with self._io_lock, self._client_lock:
            if self._closed:
                return
            self._closed = True
            client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception as e:  # closing must never raise
                logger.debug("Closing client failed: %s", type(e).__name__)
