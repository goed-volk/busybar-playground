import pytest

from busybar_kit.draw import validate_app_name_and_id
from busybar_kit.text import (
    PRINTABLE_ASCII_RE,
    is_printable_ascii,
    sanitize_optional,
    sanitize_text,
    validate_identifier,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hello", "Hello"),
        ("Café crème", "Cafe creme"),
        ("Straße", "Strasse"),
        ("Ærø Ødegaard", "AEro Odegaard"),
        ("Łódź", "Lodz"),
        ("“quoted” – dash — and…", '"quoted" - dash - and...'),
        ("€5 for ☕", "EUR5 for"),
        ("tab\tand\nnewline", "tab and newline"),
        ("  lots    of   space  ", "lots of space"),
        ("Regen & Buien (ë é €)", "Regen & Buien (e e EUR)"),
        ("20°C ± 2", "20degC +/- 2"),
    ],
)
def test_transliteration_keeps_words(raw, expected):
    out = sanitize_text(raw)
    assert out == expected
    assert PRINTABLE_ASCII_RE.match(out)


@pytest.mark.parametrize("raw", ["", "   ", "☕🚀", "​", "日本語", None])
def test_rejects_empty_or_unmappable(raw):
    with pytest.raises(ValueError):
        sanitize_text(raw)


def test_max_length():
    assert sanitize_text("abcdef ghij", max_length=7) == "abcdef"
    with pytest.raises(ValueError):
        sanitize_text("abc", max_length=0)


def test_is_printable_ascii():
    assert is_printable_ascii("ABC xyz ~")
    assert not is_printable_ascii("")
    assert not is_printable_ascii("é")


@pytest.mark.parametrize("raw", [None, "", "   ", "☕🚀"])
def test_sanitize_optional_returns_none_for_absent_content(raw):
    assert sanitize_optional(raw) is None


def test_sanitize_optional_sanitizes_and_truncates():
    assert sanitize_optional("Café crème", max_length=4) == "Cafe"


@pytest.mark.parametrize("raw", [None, "x"])
def test_sanitize_optional_rejects_bad_max_length(raw):
    with pytest.raises(ValueError):
        sanitize_optional(raw, max_length=0)


@pytest.mark.parametrize("good", ["app", "my-app_1.2", "A.b-C_d"])
def test_validate_identifier_accepts(good):
    assert validate_identifier(good) == good


@pytest.mark.parametrize("bad", ["", "has space", "ü", "abc\n", "a/b", None, 42, b"app", ["a"]])
def test_validate_identifier_rejects_with_value_error(bad):
    with pytest.raises(ValueError):
        validate_identifier(bad, "id")


@pytest.mark.parametrize("bad", [None, 42])
def test_validate_app_name_and_id_non_string_is_value_error(bad):
    with pytest.raises(ValueError):
        validate_app_name_and_id(bad)
