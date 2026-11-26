import logging
import threading
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
    """Draw ``elements``; retry HTTP 409 conflicts with capped, jittered backoff.

    ``timeout`` is the HTTP request timeout in seconds. ``display_until`` is a Unix
    timestamp (seconds) after which the device hides the elements; it is set on every
    element that has neither its own ``timeout`` nor ``display_until`` (the API treats
    the two as mutually exclusive). The caller's element objects are not modified.

    Returns True when drawn (or dry-run), False when the frame was skipped after
    ``max_409_retries`` conflicts or when ``cancel`` was set. Backoff waits on ``cancel``,
    so a caller shutting down interrupts it immediately. Other API errors are re-raised.
    """
    validate_app_name_and_id(application_name, field_name="application_name")

    if display_until is not None:
        elements = apply_display_until(elements, display_until)

    if dry_run:
        logger.info(
            "[DRY-RUN] Would draw %d element(s) for app '%s' at priority %d",
            len(elements),
            application_name,
            priority,
        )
        return True

    if client is None:
        raise ValueError("client cannot be None unless dry_run=True")

    waiter = cancel if cancel is not None else threading.Event()
    backoff = initial_backoff
    for attempt in range(max_409_retries + 1):
        if waiter.is_set():
            logger.debug("Draw for app '%s' cancelled", application_name)
            return False
        try:
            display_elements_model = DisplayElements(
                application_name=application_name,
                priority=priority,
                elements=elements,
                led_notification_color=led_notification_color,
            )

            request_kwargs: dict[str, Any] = {}
            if timeout is not None:
                request_kwargs["timeout"] = timeout

            client.display_draw(display_elements_model, **request_kwargs)

            logger.debug(
                "Successfully drew %d element(s) for app '%s' at priority %d",
                len(elements),
                application_name,
                priority,
            )
            return True
        except BusyBarAPIError as e:
            if e.status_code == 409:
                logger.warning(
                    "Priority conflict (409) drawing for app '%s' "
                    "at priority %d (attempt %d/%d): %s",
                    application_name,
                    priority,
                    attempt + 1,
                    max_409_retries + 1,
                    e,
                )
                if attempt < max_409_retries:
                    sleep_time = min(backoff, max_backoff) + uniform(0.05, 0.25)
                    if waiter.wait(sleep_time):
                        logger.debug("409 backoff for app '%s' cancelled", application_name)
                        return False
                    backoff *= 2
                    continue
                else:
                    logger.warning(
                        "Skipping draw cycle for app '%s' after max 409 conflict retries.",
                        application_name,
                    )
                    return False
            else:
                raise

    return False
