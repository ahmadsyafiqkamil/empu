"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Pencil, X } from "lucide-react";
import { apiGet } from "@/lib/api";
import { COPY, mergePreview } from "@/lib/copy";
import type { Entry, EntryListItem, Source } from "@/lib/types";
import { ConfidenceTag } from "./ConfidenceTag";
import { CropView } from "./CropView";
import { EvidenceClip } from "./EvidenceClip";
import { NovelBadge } from "./NovelBadge";
import { SourceBadge } from "./SourceBadge";
import { StatusPill } from "./StatusPill";
import { ValidationLabel } from "./ValidationLabel";
import { formatTime, formatTimeRange } from "@/lib/time";

type ReviewAction = "accept" | "edit" | "reject" | "merge" | "restore";

function confidenceLevel(value: string | null | undefined): "high" | "medium" | "low" | null {
  if (value === "high" || value === "medium" || value === "low") return value;
  return null;
}

export function EntryCard({
  entry,
  archiveId,
  editing,
  onEditStart,
  onEditCancel,
  onReview,
  mergeOpen,
  onMergeOpenChange,
}: {
  entry: Entry;
  archiveId: number;
  editing: boolean;
  onEditStart: () => void;
  onEditCancel: () => void;
  onReview: (action: ReviewAction, extra?: Record<string, unknown>) => Promise<void>;
  mergeOpen: boolean;
  onMergeOpenChange: (open: boolean) => void;
}) {
  const occ = entry.best_occurrence;
  const source: Source | null = entry.source ?? occ?.source ?? null;

  const [term, setTerm] = useState(entry.term);
  const [glossEn, setGlossEn] = useState(entry.gloss_en);
  const [glossId, setGlossId] = useState(entry.gloss_id);
  const [maestroNote, setMaestroNote] = useState(entry.maestro_note);
  const [mergeQuery, setMergeQuery] = useState("");
  const [mergeHits, setMergeHits] = useState<EntryListItem[]>([]);
  const [mergeTarget, setMergeTarget] = useState<EntryListItem | null>(null);
  const mergeRef = useRef<HTMLDivElement>(null);

  const closeMerge = useCallback(() => {
    setMergeQuery("");
    setMergeHits([]);
    setMergeTarget(null);
    onMergeOpenChange(false);
  }, [onMergeOpenChange]);

  function openEdit() {
    setTerm(entry.term);
    setGlossEn(entry.gloss_en);
    setGlossId(entry.gloss_id);
    setMaestroNote(entry.maestro_note);
    onEditStart();
  }

  useEffect(() => {
    if (!mergeOpen) return;
    let cancelled = false;
    const q = mergeQuery.trim();
    void (async () => {
      try {
        const path =
          q.length > 0
            ? `/api/archives/${archiveId}/entries?q=${encodeURIComponent(q)}`
            : `/api/archives/${archiveId}/entries`;
        const hits = await apiGet<EntryListItem[]>(path);
        if (!cancelled) setMergeHits(hits.filter((h) => h.id !== entry.id));
      } catch {
        if (!cancelled) setMergeHits([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [archiveId, entry.id, mergeOpen, mergeQuery]);

  useEffect(() => {
    if (!mergeOpen) return;
    function onDoc(ev: MouseEvent) {
      if (mergeRef.current && !mergeRef.current.contains(ev.target as Node)) closeMerge();
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [mergeOpen, closeMerge]);

  const conf = confidenceLevel(entry.confidence ?? occ?.confidence);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      {/* Evidence pair */}
      {occ ? (
        <div className="grid grid-cols-[minmax(0,1fr)_128px] gap-3 px-6 pt-6">
          <EvidenceClip
            clipUrl={entry.clip_url}
            tStart={occ.t_start}
            tEnd={occ.t_end}
            source={occ.source}
            timeSource={occ.time_source}
          />
          <CropView
            cropUrl={entry.crop_url}
            overlayUrl={entry.overlay_url}
            keyframeUrl={entry.keyframe_url}
            samStatus={entry.sam_status}
            mode="compact"
          />
        </div>
      ) : null}

      {/* Term */}
      <div className="flex flex-col gap-3 border-b border-[var(--color-divider)] px-6 py-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="m-0 text-[28px] leading-none tracking-[-0.02em] lg:text-[40px]">
              {entry.term}
            </h2>
            {occ?.t_start != null ? (
              <div className="mt-1.5 text-[13px] text-[var(--color-neutral-700)]">
                {formatTimeRange(occ.t_start, occ.t_end)}
              </div>
            ) : null}
          </div>
          <StatusPill status={entry.status} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SourceBadge source={source} />
          {entry.is_novel ? <NovelBadge /> : null}
          {conf ? <ConfidenceTag confidence={conf} ascii /> : null}
        </div>
      </div>

      {/* Quote */}
      {occ?.evidence_quote ? (
        <div className="flex flex-col gap-1.5 border-b border-[var(--color-divider)] px-6 py-5">
          <span className="label">
            {occ.source === "speech"
              ? `Said at ${formatTime(occ.t_start)}`
              : occ.source === "on_screen_text"
                ? `Shown at ${formatTime(occ.t_start)}`
                : `Seen at ${formatTime(occ.t_start)}`}
          </span>
          <div className="text-[17px] leading-[1.4] text-pretty lg:text-[19px]">
            {occ.source === "speech" ? <>“{occ.evidence_quote}”</> : <>{occ.evidence_quote}</>}
          </div>
        </div>
      ) : null}

      {/* Meaning */}
      {editing ? (
        <div className="m-6 flex flex-col gap-3 border-2 border-[var(--color-accent)] p-4">
          <div className="label font-extrabold text-[var(--color-accent-700)]">Editing</div>
          <label className="field">
            <span className="field-label">Term</span>
            <input className="input" value={term} onChange={(e) => setTerm(e.target.value)} />
          </label>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-3 md:grid-cols-2">
            <label className="field">
              <span className="field-label">English</span>
              <textarea
                className="input"
                rows={2}
                value={glossEn}
                onChange={(e) => setGlossEn(e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field-label">Bahasa Indonesia</span>
              <textarea
                className="input"
                rows={2}
                value={glossId}
                onChange={(e) => setGlossId(e.target.value)}
              />
            </label>
          </div>
          <label className="field">
            <span className="field-label">Maker&apos;s note</span>
            <input
              className="input"
              value={maestroNote}
              onChange={(e) => setMaestroNote(e.target.value)}
              placeholder="e.g. confirmed by the maker at 2:10"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() =>
                void onReview("edit", {
                  changes: {
                    term,
                    gloss_en: glossEn,
                    gloss_id: glossId,
                    maestro_note: maestroNote,
                  },
                }).then(() => onEditCancel())
              }
            >
              {COPY.studio.saveEdit}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onEditCancel}>
              {COPY.studio.cancel}
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-[minmax(0,1fr)] border-b border-[var(--color-divider)] md:grid-cols-2">
          <div className="px-6 py-4 md:border-r md:border-[var(--color-divider)]">
            <div className="label">English</div>
            <div className="mt-1 text-[15px] font-semibold">{entry.gloss_en}</div>
          </div>
          <div className="px-6 py-4">
            <div className="label">Bahasa Indonesia</div>
            <div className="mt-1 text-[15px] font-semibold">{entry.gloss_id}</div>
          </div>
        </div>
      )}

      {/* Validation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--color-divider)] px-6 py-3.5">
        <ValidationLabel variant={entry.status === "proposed" ? "proposed" : "documenter"} />
        {entry.stage_id ? (
          <span className="ml-auto text-[12px] text-[var(--color-neutral-700)]">
            Stage <em className="not-italic font-semibold text-[var(--color-text)]">{entry.stage_id}</em>
          </span>
        ) : null}
      </div>

      {/* Actions */}
      {!editing ? (
        <div className="relative grid grid-cols-2 gap-2 px-6 py-4 lg:grid-cols-[1.3fr_1fr_1fr_1fr]">
          <button
            type="button"
            className="btn h-11 justify-start gap-2.5 bg-[var(--color-text)] text-[var(--color-bg)] hover:bg-[var(--color-neutral-900)] hover:text-[var(--color-bg)]"
            onClick={() => void onReview("accept")}
          >
            <Check className="size-4" aria-hidden />
            Accept
            <kbd className="ml-auto opacity-70">A</kbd>
          </button>
          <button
            type="button"
            className="btn btn-secondary h-11 justify-start gap-2.5"
            onClick={openEdit}
          >
            <Pencil className="size-3.5" aria-hidden />
            Edit
            <kbd className="ml-auto text-[var(--color-neutral-700)]">E</kbd>
          </button>
          <button
            type="button"
            className="btn btn-secondary is-danger h-11 justify-start gap-2.5"
            onClick={() => void onReview("reject")}
          >
            <X className="size-3.5" aria-hidden />
            Reject
            <kbd className="ml-auto opacity-70">R</kbd>
          </button>
          <div className="relative col-span-2 lg:col-span-1" ref={mergeRef}>
            <button
              type="button"
              className="btn btn-secondary h-11 w-full"
              aria-expanded={mergeOpen}
              onClick={() => (mergeOpen ? closeMerge() : onMergeOpenChange(true))}
            >
              Merge…
            </button>
            {mergeOpen ? (
              <div className="absolute right-0 bottom-12 z-20 flex w-[340px] flex-col gap-2.5 border-2 border-[var(--color-text)] bg-[var(--color-bg)] p-3 shadow-[var(--shadow-lg)]">
                <input
                  className="input h-9"
                  placeholder="Find the entry to merge into"
                  aria-label="Merge target"
                  value={mergeQuery}
                  onChange={(e) => setMergeQuery(e.target.value)}
                  autoFocus
                />
                <ul className="flex max-h-44 flex-col overflow-y-auto">
                  {mergeHits.map((h) => (
                    <li key={h.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between px-2 py-2 text-left hover:bg-[var(--color-surface)]"
                        onClick={() => setMergeTarget(h)}
                      >
                        <span className="font-semibold">{h.term}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                {mergeTarget ? (
                  <div className="flex flex-col gap-2.5 border-t border-[var(--color-divider)] pt-2.5">
                    <p className="m-0 text-[14px]">{mergePreview(entry.term, mergeTarget.term)}</p>
                    <button
                      type="button"
                      className="btn btn-primary self-start"
                      onClick={() =>
                        void onReview("merge", { merge_into_id: mergeTarget.id }).then(closeMerge)
                      }
                    >
                      Merge
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="mt-auto bg-[var(--color-surface)] px-6 py-4 text-[12px] text-[var(--color-neutral-800)]">
        <div className="label">Source</div>
        {occ?.recording_title ?? "Recording"} ·{" "}
        {entry.contributor_name ? `recorded by ${entry.contributor_name}` : "own recording"}
      </div>
    </div>
  );
}
