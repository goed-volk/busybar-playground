import jsonschema
import pytest
from busylib.types import DisplayElements

from busybar_kit.draw import (
    build_animation_element,
    build_countdown_element,
    build_image_element,
    build_rectangle_element,
    build_text_element,
)


def test_contract_text_element_schema(spec: dict):
    elem = build_text_element("Hello World", id="txt1", x=10, y=5, font="bold", align="center")
    display_elements = DisplayElements(application_name="test_app", priority=50, elements=[elem])
    payload = display_elements.model_dump(mode="json", exclude_none=True)

    display_elements_schema = spec["components"]["schemas"]["DisplayElements"]
    resolver = jsonschema.RefResolver.from_schema(spec)

    jsonschema.validate(instance=payload, schema=display_elements_schema, resolver=resolver)


def test_contract_all_elements_schema(spec: dict):
    txt = build_text_element("Sample ASCII", id="t1")
    img = build_image_element("test.png", id="i1")
    anim = build_animation_element("anim.gif", id="a1")
    cd = build_countdown_element(1700000000, id="c1")

    display_elements = DisplayElements(
        application_name="valid_app_123",
        priority=70,
        elements=[txt, img, anim, cd],
    )
    payload = display_elements.model_dump(mode="json", exclude_none=True)

    display_elements_schema = spec["components"]["schemas"]["DisplayElements"]
    resolver = jsonschema.RefResolver.from_schema(spec)

    jsonschema.validate(instance=payload, schema=display_elements_schema, resolver=resolver)

    # Test rectangle element schema
    rect = build_rectangle_element(10, 10, id="r1")
    rect_payload = rect.model_dump(mode="json", exclude_none=True)
    rect_schema = spec["components"]["schemas"]["RectangleElement"]
    jsonschema.validate(instance=rect_payload, schema=rect_schema, resolver=resolver)


def test_contract_invalid_app_name_rejected():
    with pytest.raises(ValueError):
        build_text_element("test", id="invalid space id")
