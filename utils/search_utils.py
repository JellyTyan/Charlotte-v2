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


# ---------------------------------------------------------------------------
# Транслитерация кириллица ⇄ латиница («санае» ⇄ «sanae»)
# ---------------------------------------------------------------------------
_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u",
}
# Сначала длинные сочетания, чтобы «sh» стало «ш», а не «сх»
_LAT_TO_CYR = sorted({
    "shch": "щ", "sch": "щ", "zh": "ж", "kh": "х", "ts": "ц", "ch": "ч", "sh": "ш",
    "yu": "ю", "ya": "я", "yo": "ё",
    "ai": "ай", "ei": "ей", "oi": "ой",  # японские имена: Reimu → Рейму, Kaito → Кайто
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х", "i": "и",
    "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "к", "r": "р",
    "s": "с", "t": "т", "u": "у", "v": "в", "w": "в", "x": "кс", "y": "й", "z": "з",
}.items(), key=lambda kv: -len(kv[0]))


def transliterate(text: str, short_i: str = "y") -> str:
    """Транслит запроса в «другой» алфавит: кириллица → латиница или латиница → кириллица.

    Направление выбирается по преобладающему алфавиту, как в fix_layout.
    Ожидает уже приведённый к нижнему регистру текст (см. normalize_query).
    `short_i` — как писать «й» латиницей: «y» по русским правилам или «i» как в японских именах.
    """
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    cyrillic = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    if cyrillic > latin:
        return "".join(short_i if c == "й" else _CYR_TO_LAT.get(c, c) for c in text)
    if latin > cyrillic:
        out, i = [], 0
        while i < len(text):
            for lat, cyr in _LAT_TO_CYR:
                if text.startswith(lat, i):
                    out.append(cyr)
                    i += len(lat)
                    break
            else:
                out.append(text[i])
                i += 1
        return "".join(out)
    return text


def query_variants(raw: str) -> list[str]:
    """Все формы запроса для поиска, без дублей: как ввели, с исправленной раскладкой, в транслите.

    Транслит строится и от исправленной раскладки: «cfyft» → «санае» → «sanae».
    """
    clean, layout_alt = normalize_query(raw)
    variants = [clean]
    for form in (clean, layout_alt):
        if form:
            variants += [form, transliterate(form), transliterate(form, short_i="i")]
    return list(dict.fromkeys(v for v in variants if v))


if __name__ == "__main__":
    assert normalize_query("  GHBDTN   vbh ") == ("ghbdtn vbh", "привет мир")
    assert normalize_query("руддщ") == ("руддщ", "hello")
    assert normalize_query("123") == ("123", None)
    assert escape_ilike("50%_\\") == "50\\%\\_\\\\"
    assert transliterate("санае лижет рейму") == "sanae lizhet reymu"
    assert transliterate("sanae") == "санае"
    assert transliterate("shchit yuki") == "щит юки"
    assert transliterate("reimu") == "рейму" and transliterate("рейму", short_i="i") == "reimu"
    assert transliterate("123") == "123"
    assert query_variants("Санае") == ["санае", "sanae", "cfyft", "кфйфт"]
    assert query_variants("snae") == ["snae", "снае", "ытфу", "ytfu"]
    assert "sanae" in query_variants("cfyft")  # «санае» в английской раскладке
    assert {"reimu", "reymu"} <= set(query_variants("рейму"))
    assert query_variants("42") == ["42"]
    print("search_utils OK")
