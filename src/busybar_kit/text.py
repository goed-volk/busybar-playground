"""Printable-ASCII sanitizer for BUSY Bar text elements.

Firmware rejects text that does not match ``^[\\x20-\\x7E]+$``. Every display string must
pass through :func:`sanitize_text` first. Pure function: no I/O.

Characters are transliterated, not dropped, wherever an ASCII form exists: whitespace
controls become spaces (so words never run together), typographic quotes and dashes map
to their ASCII counterparts, and letters NFKD cannot decompose (``L``-stroke, ``AE``,
``o``-slash, sharp s) have explicit entries. Unmappable characters such as emoji are
removed, and the result is stripped with internal whitespace runs collapsed.
"""

from __future__ import annotations

import re
import unicodedata

PRINTABLE_ASCII_RE = re.compile(r"^[\x20-\x7E]+$")

# Application names and element IDs accepted by the firmware.
IDENTIFIER_RE = re.compile(r"[a-zA-Z0-9._-]+")

TRANSLITERATION_MAP: dict[str, str] = {
    "ß": "ss",
    "ẞ": "SS",
    "æ": "ae",
    "Æ": "AE",
    "œ": "oe",
    "Œ": "OE",
    "ø": "o",
    "Ø": "O",
    "å": "a",
    "Å": "A",
    "ł": "l",
    "Ł": "L",
    "đ": "d",
    "Đ": "D",
    "ð": "d",
    "Ð": "D",
    "þ": "th",
    "Þ": "Th",
    "ı": "i",
    "‘": "'",
    "’": "'",
    "‚": ",",
    "‛": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "′": "'",
    "″": '"',
    "«": "<<",
    "»": ">>",
    "‹": "<",
    "›": ">",
    "‐": "-",
    "‑": "-",
    "‒": "-",
    "–": "-",
    "—": "-",
    "―": "-",
    "−": "-",
    "…": "...",
    "•": "*",
    "·": "-",
    " ": " ",
    " ": " ",
    " ": " ",
    " ": " ",
    " ": " ",
    "\t": " ",
    "\n": " ",
    "\r": " ",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "¢": "c",
    "©": "(c)",
    "®": "(R)",
    "™": "TM",
    "°": "deg",
    "±": "+/-",
    "×": "x",
    "÷": "/",
    "→": "->",
    "←": "<-",
    "↑": "^",
    "↓": "v",
    "⇒": "=>",
    "✓": "v",
    "✔": "v",
    "✗": "x",
    "✘": "x",
    "♥": "<3",
    "❤": "<3",
    # Accented Latin letters (NFKD handles these too; kept explicit for clarity).
    "ë": "e",
    "é": "e",
    "è": "e",
    "ê": "e",
    "ä": "a",
    "á": "a",
    "à": "a",
    "â": "a",
    "ö": "o",
    "ó": "o",
    "ò": "o",
    "ô": "o",
    "ü": "u",
    "ú": "u",
    "ù": "u",
    "û": "u",
    "ï": "i",
    "í": "i",
    "ì": "i",
    "î": "i",
    "ÿ": "y",
    "ñ": "n",
    "ç": "c",
    "Ë": "E",
    "É": "E",
    "È": "E",
    "Ê": "E",
    "Ä": "A",
    "Á": "A",
    "À": "A",
    "Â": "A",
    "Ö": "O",
    "Ó": "O",
    "Ò": "O",
    "Ô": "O",
    "Ü": "U",
    "Ú": "U",
    "Ù": "U",
    "Û": "U",
    "Ï": "I",
    "Í": "I",
    "Ì": "I",
    "Î": "I",
}

_WHITESPACE_RUN = re.compile(r" {2,}")


def transliterate_char(char: str) -> str:
    """Printable-ASCII form of one character, or ``""`` when there is none."""
    if 0x20 <= ord(char) <= 0x7E:
        return char
    mapped = TRANSLITERATION_MAP.get(char)
    if mapped is not None:
        return mapped
    decomposed = unicodedata.normalize("NFKD", char)
    return "".join(c for c in decomposed if 0x20 <= ord(c) <= 0x7E)


def sanitize_text(text: str, *, max_length: int | None = None) -> str:
    """Return ``text`` as stripped, single-spaced printable ASCII.

    Raises ``ValueError`` when the input is empty or nothing printable remains (for
    example an emoji-only string), since firmware rejects empty text. ``max_length``
    truncates the result.
    """
    if text is None:
        raise ValueError("text is None")
    result = "".join(transliterate_char(c) for c in str(text))
    result = _WHITESPACE_RUN.sub(" ", result).strip()
    if max_length is not None:
        if max_length < 1:
            raise ValueError("max_length must be >= 1")
        result = result[:max_length].rstrip()
    if not result:
        raise ValueError(f"Text {text!r} contained no valid printable ASCII characters")
    return result


def is_printable_ascii(text: str) -> bool:
    return bool(text) and PRINTABLE_ASCII_RE.match(text) is not None


def sanitize_optional(text: str | None, *, max_length: int | None = None) -> str | None:
    """Like :func:`sanitize_text`, but ``None`` instead of raising for absent content.

    Returns ``None`` for ``None``, empty input, or input with nothing printable left (for
    example an emoji-only feed title). An invalid ``max_length`` still raises
    ``ValueError``, since that is a caller bug rather than missing content.
    """
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    if text is None:
        return None
    try:
        return sanitize_text(text, max_length=max_length)
    except ValueError:
        return None


def validate_identifier(value: object, field_name: str = "identifier") -> str:
    """Return ``value`` when it is a valid application name or element ID.

    Raises ``ValueError`` (never ``TypeError``) for non-strings, empty strings, and
    anything outside ``^[a-zA-Z0-9._-]+$``. A trailing newline is rejected too.
    """
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {field_name} {value!r}. Must match pattern ^[a-zA-Z0-9._-]+$")
    return value
