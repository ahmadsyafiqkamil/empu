"""Craft knowledge lives only in packs/. No craft term may appear in api/empu/**."""

import re

from conftest import REPO_ROOT

from empu.text import normalize

ALLOW = {"finishing", "other"}

PACKAGE = REPO_ROOT / "api" / "empu"

# Frozen Gate 0 examples in muse-output.schema.json. Allowed only in that file.
# Do not edit the schema or bump PROMPT_VERSION to "fix" a new hit.
SCHEMA_EXAMPLES_PATH = "resources/muse-output.schema.json"
SCHEMA_EXAMPLES_ALLOWED = frozenset({
    "dilorot",
    "ngelowong",
    "nglorod",
    "nglowong",
    "copper wax pen",
})

SKIP_DIR_NAMES = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


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
    for path in PACKAGE.rglob("*"):
        if not path.is_file() or path.suffix in SKIP_SUFFIXES:
            continue
        if SKIP_DIR_NAMES.intersection(path.parts):
            continue
        rel = path.relative_to(PACKAGE).as_posix()
        allowed = SCHEMA_EXAMPLES_ALLOWED if rel == SCHEMA_EXAMPLES_PATH else frozenset()
        text = normalize(path.read_text())
        for w in words:
            if w in allowed:
                continue
            if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text):
                offenders.append(f"{rel}: {w}")
    assert offenders == [], offenders

