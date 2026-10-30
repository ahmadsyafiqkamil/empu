"""Craft pack loader. All craft knowledge lives in packs/*.yaml, never in code."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, NamedTuple

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from empu.enums import Category
from empu.text import normalize

PACK_ID_RE = re.compile(r"^[a-z0-9_]+$")


class PackError(ValueError):
    pass


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    en: str


class PackStage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: LocalizedText
    variants: list[str] = []

    @property
    def display_label(self) -> str:
        return self.id.replace("_", " ")


class PackTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    category: Category
    variants: list[str] = []
    stage: str | None = None
    gloss_id: str
    gloss_en: str
    visual: bool = False
    sam_prompt: str | None = None
    verified: bool = False


class AsrErrorExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heard: str
    correct: str


class PackRef(NamedTuple):
    kind: Literal["term", "stage"]
    id: str


class CraftPack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    version: str
    name: LocalizedText
    languages: list[str]
    prompt_context: str
    asr_error_examples: list[AsrErrorExample] = []
    stages: list[PackStage]
    terms: list[PackTerm]

    def _forms(self) -> Iterator[tuple[PackRef, set[str]]]:
        for s in self.stages:
            yield PackRef("stage", s.id), {s.id, s.label.id, *s.variants}
        for t in self.terms:
            yield PackRef("term", t.id), {t.id, t.label, *t.variants}

    @model_validator(mode="after")
    def _check(self) -> CraftPack:
        errors: list[str] = []
        for kind, ids in (
            ("stage", [s.id for s in self.stages]),
            ("term", [t.id for t in self.terms]),
        ):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                errors.append(f"duplicate {kind} ids: {dup}")
        known = {s.id for s in self.stages}
        for t in self.terms:
            if t.stage and t.stage not in known:
                errors.append(f"term {t.id}: unknown stage {t.stage}")
            if t.visual and not t.sam_prompt:
                errors.append(f"term {t.id}: visual=true requires sam_prompt")
        owner: dict[str, PackRef] = {}
        for ref, forms in self._forms():
            for form in forms:
                key = normalize(form)
                if not key:
                    continue
                prev = owner.setdefault(key, ref)
                if prev != ref:
                    errors.append(
                        f"variant '{form}' used by {prev.kind}:{prev.id} and {ref.kind}:{ref.id}"
                    )
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def variant_index(self) -> dict[str, PackRef]:
        index: dict[str, PackRef] = {}
        for ref, forms in self._forms():
            for form in forms:
                if key := normalize(form):
                    index[key] = ref
        return index

    def stage(self, stage_id: str | None) -> PackStage | None:
        return next((s for s in self.stages if s.id == stage_id), None)

    def term(self, term_id: str | None) -> PackTerm | None:
        return next((t for t in self.terms if t.id == term_id), None)


def load_pack(pack_id: str, packs_dir: Path) -> CraftPack:
    path = Path(packs_dir) / f"{pack_id}.yaml"
    if not path.exists():
        raise PackError(f"pack {pack_id!r} not found in {packs_dir}")
    try:
        pack = CraftPack.model_validate(yaml.safe_load(path.read_text()))
    except (ValidationError, ValueError) as e:
        raise PackError(f"pack {pack_id!r} is invalid: {e}") from e
    if pack.id != pack_id:
        raise PackError(f"pack file {path.name} declares id {pack.id!r}")
    return pack


def list_packs(packs_dir: Path) -> list[CraftPack]:
    return [load_pack(p.stem, packs_dir) for p in sorted(Path(packs_dir).glob("*.yaml"))]


def is_valid_pack_id(pack_id: str) -> bool:
    """Pack ids become filenames; allow only safe slug characters."""
    return bool(PACK_ID_RE.match(pack_id or ""))


def parse_yaml(text: str) -> CraftPack:
    """Parse a YAML document into a validated CraftPack, or raise PackError."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise PackError(f"pack is not valid YAML: {e}") from e
    if not isinstance(doc, dict):
        raise PackError("pack must be a YAML mapping (top-level keys like id, name, stages…)")
    try:
        return CraftPack.model_validate(doc)
    except (ValidationError, ValueError) as e:
        raise PackError(f"pack is invalid: {e}") from e


def write_pack(pack: CraftPack, packs_dir: Path) -> Path:
    """Write a validated pack to packs/<id>.yaml and return the path."""
    path = Path(packs_dir) / f"{pack.id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(pack.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path
