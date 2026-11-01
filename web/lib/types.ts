export type Source = "speech" | "on_screen_text" | "visual_only";
export type SourceKind = "own_recording" | "cc_by_video";
export type EntryStatus = "proposed" | "accepted" | "edited" | "rejected" | "merged";
export type JobStatus =
  | "queued"
  | "normalizing"
  | "chunking"
  | "analyzing"
  | "merging"
  | "grounding"
  | "cutting"
  | "ready"
  | "failed";

/** Per-stage status from `GET /api/jobs` (see api job_out). */
export type JobStageStatus = "pending" | "running" | "done" | "error";

export type Occurrence = {
  id: number;
  entry_id: number;
  recording_id: number;
  recording_title: string;
  spoken: string;
  term_raw: string;
  source: Source;
  t_start: number;
  t_end: number;
  time_source: "asr" | "muse";
  stage_id: string | null;
  visible: string;
  visible_object_en: string | null;
  visual_match: "yes" | "no" | "not_visible";
  evidence_quote: string;
  confidence: "low" | "medium" | "high";
  status: string;
  clip_url: string | null;
  audio_url: string | null;
  keyframe_url: string | null;
};


export type EntryListItem = {
  id: number;
  term: string;
  category: string;
  stage_id: string | null;
  gloss_id: string;
  gloss_en: string;
  is_novel: boolean;
  status: EntryStatus;
  access_level: string;
  source: Source | null;
  confidence: string | null;
  n_occurrences: number;
  crop_url: string | null;
  keyframe_url: string | null;
  clip_url: string | null;
};

export type Entry = {
  id: number;
  term: string;
  category: string;
  stage_id: string | null;
  gloss_id: string;
  gloss_en: string;
  is_novel: boolean;
  status: EntryStatus;
  access_level: string;
  source: Source | null;
  confidence: string | null;
  n_occurrences: number;
  crop_url: string | null;
  keyframe_url: string | null;
  clip_url: string | null;
  variants: string[];
  pack_term_id: string | null;
  maestro_note: string;
  sam_status: string;
  overlay_url: string | null;
  best_occurrence: Occurrence | null;
  occurrences: Occurrence[];
  attribution: string | null;
  contributor_name: string | null;
  validation_label?: string;
};

export type Job = {
  id: number;
  recording_id: number;
  status: JobStatus;
  progress: number;
  detail: string;
  error: string | null;
  mode: "A" | "B";
  stages: {
    name: string;
    status: JobStageStatus;
    started_at: string | null;
    finished_at: string | null;
    seconds: number | null;
  }[];
};

export type Recording = {
  id: number;
  archive_id: number;
  title: string;
  duration_s: number | null;
  status: JobStatus;
  display_url: string | null;
  job: Job | null;
  attribution: string | null;
  source_kind: string;
  consent_status: string | null;
  consent_scope?: string | null;
  source_creator?: string | null;
  license?: string | null;
  contributor?: { name: string; region: string; sanggar: string } | null;
};

export type RecordingSummary = {
  id: number;
  archive_id: number;
  archive_title: string;
  title: string;
  duration_s: number | null;
  status: JobStatus;
  consent_status: string;
  consent_scope: string;
  source_kind: string;
  source_creator: string | null;
  n_entries: number;
  n_reviewed: number;
  n_proposed: number;
  display_url: string | null;
};

export type Archive = {
  id: number;
  slug: string;
  title: string;
  craft_pack_id: string;
  description: string;
  is_demo: boolean;
  recording_count: number;
  validated_count: number;
};

export type Pack = {
  id: string;
  version: string;
  name: { id: string; en: string };
};

export type PackDetail = {
  id: string;
  version: string;
  name: { id: string; en: string };
  languages: string[];
  n_stages: number;
  n_terms: number;
};

export type AskEvidence = {
  entry: EntryListItem;
  occurrence: Occurrence;
  archive_slug: string;
  archive_title: string;
};

export type AskAnswer = {
  answer: string;
  lang: string;
  refused: boolean;
  evidence: AskEvidence[];
  model: string;
  prompt_version: string;
  cached: boolean;
};
