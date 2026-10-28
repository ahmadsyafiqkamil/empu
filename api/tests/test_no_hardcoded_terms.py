"""Craft knowledge lives only in packs/. No craft term may appear in api/empu/**."""

import re

from conftest import REPO_ROOT
from empu.text import normalize

ALLOW = {"finishing", "other"}


def craft_words(pack) -> set[str]:
    words = set()
    for s in pack.stages:
        words |= {normalize(s.id), *(normalize(v) for v in s.variants)}
    for t in pack.terms:
        words |= {normalize(t.id), normalize(t.label), *(normalize(v) for v in t.variants)}
    return {w for w in words if len(w) >= 4 and w not in ALLOW}


def test_no_craft_terms_in_package(pack):
    words = craft_words(pack)
    offenders = []
    for path in (REPO_ROOT / "api" / "empu").rglob("*.py"):
        text = normalize(path.read_text())
        for w in words:
            if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text):
                offenders.append(f"{path.name}: {w}")
    assert offenders == [], offenders
