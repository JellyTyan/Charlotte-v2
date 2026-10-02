"""Search query utilities: metacharacter escaping and keyboard layout normalization.

Usage:
    from utils.search_utils import escape_ilike, fix_layout, normalize_query
"""

# ---------------------------------------------------------------------------
# QWERTY → ЙЦУКЕН mapping (and reverse)
# ---------------------------------------------------------------------------
_EN_CHARS = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>~"
_RU_CHARS = "йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ"

_EN_TO_RU = str.maketrans(_EN_CHARS, _RU_CHARS)
_RU_TO_EN = str.maketrans(_RU_CHARS, _EN_CHARS)


def fix_layout(text: str) -> str:
    """Convert QWERTY→ЙЦУКЕН layout mistake: 'ghbdtn' → 'привет'.

    Detects which direction to convert by checking whether the input contains
    more Cyrillic or Latin letters.
    """
    latin_count = sum(1 for c in text if c.isascii() and c.isalpha())
    cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04ff')

    if latin_count > cyrillic_count:
        # Assume user typed Russian on QWERTY — convert to ЙЦУКЕН
        return text.translate(_EN_TO_RU)
    if cyrillic_count > latin_count:
        # Assume user typed English on ЙЦУКЕН — convert to QWERTY
        return text.translate(_RU_TO_EN)
    return text


# ---------------------------------------------------------------------------
# ILIKE metacharacter escaping
# ---------------------------------------------------------------------------
def escape_ilike(value: str, escape_char: str = "\\") -> str:
    """Escape SQL ILIKE wildcards and the escape character itself.

    PostgreSQL ILIKE special chars: % _ \\
    After this, pass ``escape_char`` as the ESCAPE argument to ILIKE.

    Example:
        pattern = "%" + escape_ilike(user_input) + "%"
        stmt.where(col.ilike(pattern, escape="\\\\"))
    """
    value = value.replace(escape_char, escape_char * 2)
    value = value.replace("%", escape_char + "%")
    value = value.replace("_", escape_char + "_")
    return value


# ---------------------------------------------------------------------------
# High-level query normalizer
# ---------------------------------------------------------------------------
def normalize_query(raw: str) -> tuple[str, str | None]:
    """Clean and normalize a search query.

    Returns:
        (clean_query, layout_alternative)
        - clean_query: stripped, lowercased, collapsed whitespace
        - layout_alternative: same text with fixed keyboard layout, or None
          if it is identical to clean_query (no conversion happened)
    """
    clean = " ".join(raw.strip().lower().split())
    alternative = fix_layout(clean)
    return clean, (alternative if alternative != clean else None)
