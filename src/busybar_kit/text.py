import unicodedata

# Transliteration mapping for non-ASCII characters commonly found in text/weather descriptions
TRANSLITERATION_MAP = {
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
    "ß": "ss",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
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


def sanitize_text(text: str) -> str:
    if not text:
        return ""

    result = []
    for char in text:
        if 0x20 <= ord(char) <= 0x7E:
            result.append(char)
        elif char in TRANSLITERATION_MAP:
            result.append(TRANSLITERATION_MAP[char])
        else:
            normalized = unicodedata.normalize("NFKD", char)
            ascii_chars = [c for c in normalized if 0x20 <= ord(c) <= 0x7E]
            if ascii_chars:
                result.extend(ascii_chars)
            # Emoji or unmappable unicode non-printable/non-ASCII characters are omitted/stripped

    res_str = "".join(result)
    if not res_str and text:
        raise ValueError(f"Text '{text}' contained no valid printable ASCII characters")

    return res_str
