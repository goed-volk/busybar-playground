import logging
import threading
from enum import Enum
from random import uniform
from typing import Any, Literal

from busylib.client import BusyBar
from busylib.exceptions import BusyBarAPIError
from busylib.types import (
    AnimationElement,
    CountdownElement,
    DisplayElements,
    ImageElement,
    RectangleElement,
    TextElement,
)

from busybar_kit.text import IDENTIFIER_RE, sanitize_text, validate_identifier

logger = logging.getLogger(__name__)

# Priority Ladder Bands (Project Convention)
PRIORITY_STUB = 0
PRIORITY_AMBIENT_MIN = 20
PRIORITY_AMBIENT_MAX = 39
PRIORITY_INFO_DEFAULT = 50
PRIORITY_NOTABLE_MIN = 60
PRIORITY_NOTABLE_MAX = 79
PRIORITY_SESSION = 90
PRIORITY_URGENT_MIN = 91
PRIORITY_URGENT_MAX = 100

# Upper bound for a single 409 backoff wait (before jitter), in seconds.
MAX_409_BACKOFF = 4.0

APP_NAME_PATTERN = IDENTIFIER_RE  # kept for v0.2 callers; use busybar_kit.text
_element_id_counter = 0


class DrawResult(str, Enum):
    """Outcome of one draw call.

    ``CONFLICT_SKIPPED`` means a higher-priority app held the display through every 409
    retry: the frame was not shown and the caller should resend a full frame later.
    ``CANCELLED`` means the caller's ``cancel`` event was set: stop, do not retry.
    """

    DRAWN = "drawn"
    DRY_RUN = "dry_run"
    CONFLICT_SKIPPED = "conflict_skipped"
    CANCELLED = "cancelled"

    @property
    def ok(self) -> bool:
        """True for ``DRAWN`` and ``DRY_RUN``, matching the v0.2 ``bool`` return."""
        return self in (DrawResult.DRAWN, DrawResult.DRY_RUN)


def validate_app_name_and_id(name_or_id: str, field_name: str = "application_name") -> str:
    """Alias of :func:`busybar_kit.text.validate_identifier`."""
    return validate_identifier(name_or_id, field_name)


def _next_element_id(prefix: str = "el") -> str:
    global _element_id_counter
    _element_id_counter += 1
    return f"{prefix}_{_element_id_counter}"


def build_text_element(
    text: str,
    *,
    id: str | None = None,
    x: int = 0,
    y: int = 0,
    font: str = "normal",
    align: str = "top_left",
    color: str = "#FFFFFFFF",
) -> TextElement:
    sanitized = sanitize_text(text)
    element_id = id or _next_element_id("txt")
    validate_app_name_and_id(element_id, field_name="id")

    return TextElement(
        id=element_id,
        text=sanitized,
        x=x,
        y=y,
        font=font,
        align=align,
        color=color,
    )


def build_image_element(
    path: str,
    *,
    id: str | None = None,
    x: int = 0,
    y: int = 0,
    align: str = "top_left",
) -> ImageElement:
    element_id = id or _next_element_id("img")
    validate_app_name_and_id(element_id, field_name="id")

    return ImageElement(
        id=element_id,
        path=path,
        x=x,
        y=y,
    )


def build_animation_element(
    path: str,
    *,
    id: str | None = None,
    x: int = 0,
    y: int = 0,
    loop: bool = True,
) -> AnimationElement:
    element_id = id or _next_element_id("anim")
    validate_app_name_and_id(element_id, field_name="id")

    return AnimationElement(
        id=element_id,
        path=path,
        x=x,
        y=y,
        loop=loop,
    )


def build_countdown_element(
    timestamp: str | int | float,
    *,
    id: str | None = None,
    x: int = 0,
    y: int = 0,
    color: str = "#FFFFFFFF",
    direction: Literal["time_left", "time_since"] = "time_left",
    show_hours: Literal["when_non_zero", "always"] = "when_non_zero",
) -> CountdownElement:
    element_id = id or _next_element_id("cd")
    validate_app_name_and_id(element_id, field_name="id")

    return CountdownElement(
        id=element_id,
        timestamp=str(timestamp),
        x=x,
        y=y,
        color=color,
        direction=direction,
        show_hours=show_hours,
    )


def build_rectangle_element(
    width: int,
    height: int,
    *,
    id: str | None = None,
    x: int = 0,
    y: int = 0,
    color: str = "#FFFFFFFF",
    fill: Literal["none", "solid", "gradient_h", "gradient_v"] | bool = "solid",
    fill_colors: list[str] | None = None,
    border_width: int = 0,
    border_color: str | None = None,
    radius: int = 0,
) -> RectangleElement:
    element_id = id or _next_element_id("rect")
    validate_app_name_and_id(element_id, field_name="id")

    if isinstance(fill, bool):
        fill_mode: Literal["none", "solid", "gradient_h", "gradient_v"] = (
            "solid" if fill else "none"
        )
    else:
        fill_mode = fill

    resolved_fill_colors = fill_colors if fill_colors is not None else [color]
    resolved_border_color = border_color if border_color is not None else color

    return RectangleElement(
        id=element_id,
        width=width,
        height=height,
        x=x,
        y=y,
        radius=radius,
        fill=fill_mode,
        fill_colors=resolved_fill_colors,
        border_width=border_width,
        border_color=resolved_border_color,
    )


def apply_display_until(elements: list[Any], display_until: int | float) -> list[Any]:
    """Copies of ``elements`` with ``display_until`` set where no timing is set yet."""
    if isinstance(display_until, bool) or display_until <= 0:
        raise ValueError(f"display_until must be a positive Unix timestamp, got {display_until!r}")
    stamp = str(int(display_until))
    result: list[Any] = []
    for element in elements:
        if isinstance(element, dict):
            has_timing = element.get("timeout") is not None or element.get("display_until")
            result.append(element if has_timing else {**element, "display_until": stamp})
        else:
            has_timing = element.timeout is not None or element.display_until is not None
            result.append(
                element if has_timing else element.model_copy(update={"display_until": stamp})
            )
    return result


def draw_display_elements_result(
    client: BusyBar | None,
    elements: list[Any],
    *,
    application_name: str,
    priority: int = PRIORITY_INFO_DEFAULT,
    timeout: int | float | None = None,
    display_until: int | float | None = None,
    led_notification_color: str | None = None,
    dry_run: bool = False,
    max_409_retries: int = 3,
    initial_backoff: float = 0.5,
    max_backoff: float = MAX_409_BACKOFF,
    cancel: threading.Event | None = None,
) -> DrawResult:
    """Draw ``elements``; retry HTTP 409 conflicts with capped, jittered backoff.

    ``timeout`` is the HTTP request timeout in seconds. ``display_until`` is a Unix
    timestamp (seconds) after which the device hides the elements; it is set on every
    element that has neither its own ``timeout`` nor ``display_until`` (the API treats
    the two as mutually exclusive). The caller's element objects are not modified.

    The payload is validated as ``DisplayElements`` before anything else, so a dry run
    raises for the same invalid input a live draw would (``ValueError`` or pydantic
    ``ValidationError``). Dry runs log at DEBUG only, so animation loops do not flood.

    Backoff waits on ``cancel``, so a caller shutting down interrupts it immediately.
    Each 409 is logged at DEBUG; a skipped cycle is logged once at INFO. Errors other
    than 409 are re-raised.
    """
    validate_app_name_and_id(application_name, field_name="application_name")

    if display_until is not None:
        elements = apply_display_until(elements, display_until)

    payload = DisplayElements(
        application_name=application_name,
        priority=priority,
        elements=elements,
        led_notification_color=led_notification_color,
    )

    if dry_run:
        logger.debug(
            "[DRY-RUN] Would draw %d element(s) for app '%s' at priority %d",
            len(payload.elements),
            application_name,
            priority,
        )
        return DrawResult.DRY_RUN

    if client is None:
        raise ValueError("client cannot be None unless dry_run=True")

    request_kwargs: dict[str, Any] = {}
    if timeout is not None:
        request_kwargs["timeout"] = timeout

    waiter = cancel if cancel is not None else threading.Event()
    backoff = initial_backoff
    attempts = max_409_retries + 1
    for attempt in range(1, attempts + 1):
        if waiter.is_set():
            logger.debug("Draw for app '%s' cancelled", application_name)
            return DrawResult.CANCELLED
        try:
            client.display_draw(payload, **request_kwargs)
        except BusyBarAPIError as e:
            if e.status_code != 409:
                raise
            logger.debug(
                "Priority conflict (409) for app '%s' at priority %d (attempt %d/%d)",
                application_name,
                priority,
                attempt,
                attempts,
            )
            if attempt == attempts:
                break
            if waiter.wait(min(backoff, max_backoff) + uniform(0.05, 0.25)):
                logger.debug("409 backoff for app '%s' cancelled", application_name)
                return DrawResult.CANCELLED
            backoff *= 2
            continue
        logger.debug(
            "Drew %d element(s) for app '%s' at priority %d",
            len(payload.elements),
            application_name,
            priority,
        )
        return DrawResult.DRAWN

    logger.info(
        "Skipped draw for app '%s' at priority %d: display held by a higher priority "
        "after %d attempt(s)",
        application_name,
        priority,
        attempts,
    )
    return DrawResult.CONFLICT_SKIPPED


def draw_display_elements(
    client: BusyBar | None,
    elements: list[Any],
    *,
    application_name: str,
    priority: int = PRIORITY_INFO_DEFAULT,
    timeout: int | float | None = None,
    display_until: int | float | None = None,
    led_notification_color: str | None = None,
    dry_run: bool = False,
    max_409_retries: int = 3,
    initial_backoff: float = 0.5,
    max_backoff: float = MAX_409_BACKOFF,
    cancel: threading.Event | None = None,
) -> bool:
    """v0.2 interface of :func:`draw_display_elements_result`.

    True when drawn or dry-run; False when skipped after 409 conflicts or cancelled.
    Use :func:`draw_display_elements_result` to tell those two apart.
    """
    return draw_display_elements_result(
        client,
        elements,
        application_name=application_name,
        priority=priority,
        timeout=timeout,
        display_until=display_until,
        led_notification_color=led_notification_color,
        dry_run=dry_run,
        max_409_retries=max_409_retries,
        initial_backoff=initial_backoff,
        max_backoff=max_backoff,
        cancel=cancel,
    ).ok
