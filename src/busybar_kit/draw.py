import logging
import re
import time
from random import uniform
from typing import Any, Literal

from busylib.client import BusyBar
from busylib.exceptions import BusyBarAPIError
from busylib.types import (
    AnimationElement,
    CountdownElement,
    DisplayElementBase,
    DisplayElements,
    ImageElement,
    TextElement,
)
from pydantic import Field, ValidationError, field_validator

from busybar_kit.text import sanitize_text

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

APP_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
_element_id_counter = 0


class RectangleElement(DisplayElementBase):
    type: Literal["rectangle"] = "rectangle"
    x: int = Field(default=0, ge=-4096, le=4095)
    y: int = Field(default=0, ge=-4096, le=4095)
    width: int
    height: int
    color: str = Field(default="#FFFFFFFF", pattern=r"^#[a-fA-F0-9]{8}$")
    fill: Literal["none", "solid", "gradient_h", "gradient_v"] = "solid"

    @field_validator("fill", mode="before")
    @classmethod
    def convert_bool_fill(cls, v: Any) -> Any:
        if isinstance(v, bool):
            return "solid" if v else "none"
        return v


def validate_app_name_and_id(name_or_id: str, field_name: str = "application_name") -> str:
    if not name_or_id or not APP_NAME_PATTERN.match(name_or_id):
        raise ValueError(
            f"Invalid {field_name} '{name_or_id}'. Must match pattern ^[a-zA-Z0-9._-]+$"
        )
    return name_or_id


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
) -> RectangleElement:
    element_id = id or _next_element_id("rect")
    validate_app_name_and_id(element_id, field_name="id")

    return RectangleElement(
        id=element_id,
        width=width,
        height=height,
        x=x,
        y=y,
        color=color,
        fill=fill,
    )


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
) -> bool:
    validate_app_name_and_id(application_name, field_name="application_name")

    raw_elements = [
        el.model_dump(mode="json", exclude_none=True) if hasattr(el, "model_dump") else el
        for el in elements
    ]

    payload_dict = {
        "application_name": application_name,
        "priority": priority,
        "elements": raw_elements,
    }
    if led_notification_color:
        payload_dict["led_notification_color"] = led_notification_color

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

    backoff = initial_backoff
    for attempt in range(max_409_retries + 1):
        try:
            try:
                display_elements_model = DisplayElements(
                    application_name=application_name,
                    priority=priority,
                    elements=elements,
                )
                client.display_draw(
                    display_elements_model,
                    timeout=timeout,
                    display_until=display_until,
                    led_notification_color=led_notification_color,
                )
            except ValidationError:
                client._request("POST", "/api/display/draw", json_payload=payload_dict)

            logger.debug(
                "Successfully drew %d element(s) for app '%s' at priority %d",
                len(elements),
                application_name,
                priority,
            )
            return True
        except BusyBarAPIError as e:
            if getattr(e, "status_code", None) == 409 or "409" in str(e):
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
                    sleep_time = backoff + uniform(0.05, 0.25)
                    time.sleep(sleep_time)
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
