from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from empu.enums import (
    AccessLevel,
    Category,
    Confidence,
    ConsentStatus,
    ContributorRole,
    EntryStatus,
    JobStatus,
    OccurrenceStatus,
    PipelineMode,
    ReviewAction,
    SamStatus,
    Source,
    SourceKind,
    TimeSource,
    VisualMatch,
)


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _default_craft_pack_id() -> str:
    packs_dir = Path(__file__).resolve().parents[2] / "packs"
    for path in sorted(packs_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("id"):
            return str(doc["id"])
    return ""


class ContributorOut(APIModel):
    id: int
    name: str
    role: ContributorRole
    region: str
    sanggar: str


class ArchiveOut(APIModel):
    id: int
    slug: str
    title: str
    craft_pack_id: str
    description: str
    is_demo: bool
    recording_count: int = 0
    validated_count: int = 0


class ArchiveIn(APIModel):
    slug: str
    title: str
    craft_pack_id: str = Field(default_factory=_default_craft_pack_id)
    description: str = ""
    owner_name: str = ""


class OccurrenceOut(APIModel):
    id: int
    entry_id: int
    recording_id: int
    recording_title: str = ""
    spoken: str
    term_raw: str
    source: Source
    t_start: float
    t_end: float
    time_source: TimeSource
    stage_id: str | None
    visible: str
    visible_object_en: str | None
    visual_match: VisualMatch
    evidence_quote: str
    confidence: Confidence
    status: OccurrenceStatus
    clip_url: str | None
    audio_url: str | None
    keyframe_url: str | None


class EntryListItem(APIModel):
    id: int
    term: str
    category: Category
    stage_id: str | None
    gloss_id: str
    gloss_en: str
    is_novel: bool
    status: EntryStatus
    access_level: AccessLevel
    source: Source | None = None
    confidence: Confidence | None = None
    n_occurrences: int = 0
    crop_url: str | None = None
    keyframe_url: str | None = None
    clip_url: str | None = None


class EntryOut(EntryListItem):
    variants: list[str] = []
    pack_term_id: str | None = None
    maestro_note: str = ""
    sam_status: SamStatus = SamStatus.skipped
    overlay_url: str | None = None
    best_occurrence: OccurrenceOut | None = None
    occurrences: list[OccurrenceOut] = []
    attribution: str | None = None
    contributor_name: str | None = None


class JobStageOut(APIModel):
    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    seconds: float | None = None


class JobOut(APIModel):
    id: int
    recording_id: int
    status: JobStatus
    progress: float
    detail: str
    error: str | None
    mode: PipelineMode
    stages: list[JobStageOut] = []


class RecordingOut(APIModel):
    id: int
    archive_id: int
    title: str
    duration_s: float | None
    status: JobStatus
    consent_status: ConsentStatus
    consent_scope: AccessLevel
    source_kind: SourceKind
    source_url: str | None
    source_creator: str | None
    license: str | None
    attribution: str | None
    contributor: ContributorOut | None = None
    job: JobOut | None = None
    display_url: str | None = None


class ReviewIn(APIModel):
    action: ReviewAction
    actor: str = "documenter"
    occurrence_id: int | None = None
    merge_into_id: int | None = None
    changes: dict[str, Any] = Field(default_factory=dict)


class ReprocessIn(APIModel):
    mode: PipelineMode | None = None


class UploadAck(APIModel):
    recording_id: int
    job_id: int
