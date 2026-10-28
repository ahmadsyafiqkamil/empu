from enum import StrEnum


class Category(StrEnum):
    tool = "tool"
    tool_part = "tool_part"
    material = "material"
    dye = "dye"
    stage = "stage"
    technique = "technique"
    motif = "motif"
    other = "other"


class Source(StrEnum):
    speech = "speech"
    on_screen_text = "on_screen_text"
    visual_only = "visual_only"


class VisualMatch(StrEnum):
    yes = "yes"
    no = "no"
    not_visible = "not_visible"


class Confidence(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


CONFIDENCE_RANK = {Confidence.low: 0, Confidence.medium: 1, Confidence.high: 2}


class ContributorRole(StrEnum):
    maestro = "maestro"
    student = "student"
    documenter = "documenter"


class ConsentStatus(StrEnum):
    granted = "granted"
    withdrawn = "withdrawn"


class AccessLevel(StrEnum):
    public = "public"
    community = "community"
    private = "private"


class JobStatus(StrEnum):
    queued = "queued"
    normalizing = "normalizing"
    chunking = "chunking"
    analyzing = "analyzing"
    merging = "merging"
    grounding = "grounding"
    cutting = "cutting"
    ready = "ready"
    failed = "failed"


class PipelineMode(StrEnum):
    A = "A"
    B = "B"


class EntryStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    edited = "edited"
    rejected = "rejected"
    merged = "merged"


class OccurrenceStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"


class ReviewAction(StrEnum):
    accept = "accept"
    edit = "edit"
    reject = "reject"
    merge = "merge"
    restore = "restore"
    add_manual = "add_manual"


class SamStatus(StrEnum):
    ok = "ok"
    empty = "empty"
    error = "error"
    skipped = "skipped"


class ChunkStatus(StrEnum):
    pending = "pending"
    done = "done"
    failed = "failed"
