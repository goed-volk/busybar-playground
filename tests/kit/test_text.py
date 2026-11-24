import pytest

from busybar_kit.text import PRINTABLE_ASCII_RE, is_printable_ascii, sanitize_text


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
