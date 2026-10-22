import jsonschema
import pytest
from busylib.types import DisplayElements
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from busybar_kit.draw import (
    build_animation_element,
    build_countdown_element,
    build_image_element,
    build_rectangle_element,
    build_text_element,
)

BASE_URI = "urn:openapi"


@pytest.fixture
def openapi_registry(spec: dict) -> Registry:
    resource = DRAFT202012.create_resource(spec)
    return Registry().with_resource(BASE_URI, resource)


def test_contract_text_element_schema(openapi_registry: Registry):
    elem = build_text_element("Hello World", id="txt1", x=10, y=5, font="bold", align="center")
    display_elements = DisplayElements(application_name="test_app", priority=50, elements=[elem])
    payload = display_elements.model_dump(mode="json", exclude_none=True)

    schema = {"$ref": f"{BASE_URI}#/components/schemas/DisplayElements"}
    jsonschema.validate(instance=payload, schema=schema, registry=openapi_registry)


def test_contract_all_elements_schema(openapi_registry: Registry):
    txt = build_text_element("Sample ASCII", id="t1")
    img = build_image_element("test.png", id="i1")
    anim = build_animation_element("anim.gif", id="a1")
    cd = build_countdown_element(1700000000, id="c1")
    rect = build_rectangle_element(
        width=10,
        height=10,
        id="r1",
        fill="solid",
        fill_colors=["#FFFFFFFF"],
        border_width=0,
        border_color="#FFFFFFFF",
        radius=0,
    )

    display_elements = DisplayElements(
        application_name="valid_app_123",
        priority=70,
        elements=[txt, img, anim, cd, rect],
    )
    payload = display_elements.model_dump(mode="json", exclude_none=True)

    schema = {"$ref": f"{BASE_URI}#/components/schemas/DisplayElements"}
    jsonschema.validate(instance=payload, schema=schema, registry=openapi_registry)

    # Test rectangle element schema standalone
    rect_payload = rect.model_dump(mode="json", exclude_none=True)
    rect_schema = {"$ref": f"{BASE_URI}#/components/schemas/RectangleElement"}
    jsonschema.validate(instance=rect_payload, schema=rect_schema, registry=openapi_registry)


def test_contract_invalid_app_name_rejected():
    with pytest.raises(ValueError):
        build_text_element("test", id="invalid space id")
