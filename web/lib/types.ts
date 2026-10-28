export type Source = "speech" | "on_screen_text" | "visual_only";
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
    status: string;
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
