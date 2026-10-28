"""Database tables: spec section 9 plus D5 (stage_id, canon_key), D9 (source_*), D10 (time_source).

No `from __future__ import annotations` here: SQLModel resolves field types at class creation.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from empu.enums import (
    AccessLevel,
    Category,
    ChunkStatus,
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

DEFAULT_DATASET_LICENSE = "Determined by the community; contact the archive owner"


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Archive(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    craft_pack_id: str
    description: str = ""
    owner_name: str = ""
    license: str = DEFAULT_DATASET_LICENSE
    default_access: AccessLevel = AccessLevel.public
    is_demo: bool = False
    is_sandbox: bool = False
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))


class Contributor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    role: ContributorRole = ContributorRole.maestro
    region: str = ""
    sanggar: str = ""
    bio: str = ""
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))


class Recording(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    archive_id: int = Field(foreign_key="archive.id", index=True)
    contributor_id: int | None = Field(default=None, foreign_key="contributor.id")
    title: str
    recorded_at: str | None = None
    location: str = ""
    language_hint: str = "id,jv"
    duration_s: float | None = None
    original_path: str
    display_path: str | None = None
    analysis_path: str | None = None
    consent_status: ConsentStatus = ConsentStatus.granted
    consent_scope: AccessLevel = AccessLevel.public
    consent_note: str = ""
    consent_evidence: str = ""
    consent_withdrawn_at: datetime | None = Field(default=None, sa_column=Column(DateTime))
    source_kind: SourceKind = SourceKind.own_recording
    source_url: str | None = None
    source_creator: str | None = None
    license: str | None = None
    attribution: str | None = None
    status: JobStatus = JobStatus.queued
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    status: JobStatus = Field(default=JobStatus.queued, index=True)
    progress: float = 0.0
    detail: str = ""
    error: str | None = None
    mode: PipelineMode = PipelineMode.A
    model: str = ""
    prompt_version: str = ""
    usage_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    timings_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))
    started_at: datetime | None = Field(default=None, sa_column=Column(DateTime))
    finished_at: datetime | None = Field(default=None, sa_column=Column(DateTime))


class Chunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    idx: int
    start_s: float
    end_s: float
    path: str
    sha256: str = ""
    file_id: str | None = None
    status: ChunkStatus = ChunkStatus.pending
    raw_path: str | None = None
    parsed_path: str | None = None
    error: str | None = None
    usage_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    latency_s: float | None = None
    cached: bool = False


class Entry(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("archive_id", "canon_key"),)

    id: int | None = Field(default=None, primary_key=True)
    archive_id: int = Field(foreign_key="archive.id", index=True)
    canon_key: str = Field(index=True)
    term: str
    category: Category = Category.other
    stage_id: str | None = None
    gloss_id: str = ""
    gloss_en: str = ""
    variants_json: list = Field(default_factory=list, sa_column=Column(JSON))
    pack_term_id: str | None = None
    is_novel: bool = False
    status: EntryStatus = Field(default=EntryStatus.proposed, index=True)
    merged_into_id: int | None = None
    access_level: AccessLevel = AccessLevel.public
    best_occurrence_id: int | None = None
    crop_path: str | None = None
    overlay_path: str | None = None
    sam_status: SamStatus = SamStatus.skipped
    sam_prompt: str | None = None
    maestro_note: str = ""
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))


class Occurrence(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(foreign_key="entry.id", index=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    chunk_id: int | None = None
    spoken: str = ""
    term_raw: str = ""
    source: Source
    t_start: float
    t_end: float
    time_source: TimeSource = TimeSource.muse
    asr_score: float | None = None
    stage_raw: str | None = None
    stage_id: str | None = None
    visible: str = ""
    visible_object_en: str | None = None
    visual_match: VisualMatch = VisualMatch.not_visible
    gloss_raw: str = ""
    gloss_en_raw: str = ""
    evidence_quote: str = ""
    confidence: Confidence = Confidence.low
    clip_path: str | None = None
    audio_path: str | None = None
    keyframe_path: str | None = None
    status: OccurrenceStatus = OccurrenceStatus.proposed


class ProcessStep(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    pack_stage_id: str | None = None
    name_raw: str
    t_start: float
    t_end: float
    tools_json: list = Field(default_factory=list, sa_column=Column(JSON))
    order: int = 0


class ReviewEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(foreign_key="entry.id", index=True)
    occurrence_id: int | None = None
    action: ReviewAction
    before_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    after_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    actor: str
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime))
