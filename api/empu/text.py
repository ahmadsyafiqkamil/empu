import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


def normalize(s: str | None) -> str:
    """Casefold, drop punctuation and underscores, collapse whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).casefold()
    s = _PUNCT.sub(" ", s).replace("_", " ")
    return _SPACE.sub(" ", s).strip()
