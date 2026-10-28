"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "@/lib/api";
import { COPY, mergePreview } from "@/lib/copy";
import type { Entry, EntryListItem, Source } from "@/lib/types";
import { AttributionLine } from "./AttributionLine";
import { ConfidenceTag } from "./ConfidenceTag";
import { CropView } from "./CropView";
import { EvidenceClip } from "./EvidenceClip";
import { NovelBadge } from "./NovelBadge";
import { SourceBadge } from "./SourceBadge";
import { StatusChip } from "./StatusChip";
import { TimeSourceTag } from "./TimeSourceTag";
import { ValidationLabel } from "./ValidationLabel";

type ReviewAction = "accept" | "edit" | "reject" | "merge" | "restore";

function validationVariant(status: Entry["status"]): "documenter" | "proposed" {
  return status === "proposed" ? "proposed" : "documenter";
}

function confidenceLevel(
  value: string | null | undefined,
): "high" | "medium" | "low" | null {
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
    if (!mergeOpen) {
      return;
    }
    let cancelled = false;
    const q = mergeQuery.trim();
    void (async () => {
      try {
        const path =
          q.length > 0
            ? `/api/archives/${archiveId}/entries?q=${encodeURIComponent(q)}`
            : `/api/archives/${archiveId}/entries`;
        const hits = await apiGet<EntryListItem[]>(path);
        if (!cancelled) {
          setMergeHits(hits.filter((h) => h.id !== entry.id));
        }
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
      if (mergeRef.current && !mergeRef.current.contains(ev.target as Node)) {
        closeMerge();
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [mergeOpen, closeMerge]);

  const conf = confidenceLevel(entry.confidence ?? occ?.confidence);

  return (
    <article className="space-y-4 overflow-y-auto p-4">
      {occ ? (
        <EvidenceClip
          clipUrl={entry.clip_url}
          tStart={occ.t_start}
          tEnd={occ.t_end}
          source={occ.source}
          timeSource={occ.time_source}
        />
      ) : null}
      <div className="grid gap-4 md:grid-cols-[minmax(0,8rem)_1fr]">
        <CropView
          cropUrl={entry.crop_url}
          overlayUrl={entry.overlay_url}
          keyframeUrl={entry.keyframe_url}
          samStatus={entry.sam_status}
        />
        <div className="space-y-2">
          {editing ? (
            <label className="block text-xs text-[var(--muted)]">
              Term
              <input
                className="mt-1 w-full border border-[var(--line)] bg-transparent px-2 py-1 font-display text-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
              />
            </label>
          ) : (
            <h2 className="font-display text-2xl">{entry.term}</h2>
          )}
          {occ?.spoken ? (
            <p className="text-[var(--muted)] italic">{occ.spoken}</p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2">
            {source ? <SourceBadge source={source} /> : null}
            {entry.is_novel ? <NovelBadge /> : null}
            {conf ? <ConfidenceTag confidence={conf} /> : null}
            <StatusChip status={entry.status} />
            {occ ? <TimeSourceTag timeSource={occ.time_source} /> : null}
          </div>
          <ValidationLabel variant={validationVariant(entry.status)} />
        </div>
      </div>
      {occ?.evidence_quote ? (
        <blockquote className="border-l-2 border-[var(--accent)] pl-3 text-sm">
          {occ.evidence_quote}
        </blockquote>
      ) : null}
      {editing ? (
        <div className="space-y-2 text-sm">
          <label className="block text-xs text-[var(--muted)]">
            Gloss (English)
            <textarea
              className="mt-1 w-full border border-[var(--line)] bg-transparent px-2 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              rows={2}
              value={glossEn}
              onChange={(e) => setGlossEn(e.target.value)}
            />
          </label>
          <label className="block text-xs text-[var(--muted)]">
            Gloss (Bahasa Indonesia)
            <textarea
              className="mt-1 w-full border border-[var(--line)] bg-transparent px-2 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              rows={2}
              value={glossId}
              onChange={(e) => setGlossId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-[var(--muted)]">
            Maestro note
            <textarea
              className="mt-1 w-full border border-[var(--line)] bg-transparent px-2 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              rows={2}
              value={maestroNote}
              onChange={(e) => setMaestroNote(e.target.value)}
            />
          </label>
          {source ? (
            <div className="pt-1">
              <SourceBadge source={source} size="sm" />
            </div>
          ) : null}
        </div>
      ) : (
        <>
          <p>{entry.gloss_id}</p>
          <p className="text-[var(--muted)]">{entry.gloss_en}</p>
          {entry.stage_id ? (
            <p className="text-xs text-[var(--muted)]">Stage: {entry.stage_id}</p>
          ) : null}
          {entry.maestro_note ? (
            <p className="text-sm text-[var(--muted)]">{entry.maestro_note}</p>
          ) : null}
        </>
      )}
      {entry.attribution ? (
        <AttributionLine variant="inline" attribution={entry.attribution} />
      ) : null}
      <div className="relative flex flex-wrap gap-2 pt-2">
        {editing ? (
          <>
            <button
              type="button"
              className="bg-[var(--accent)] px-3 py-2 text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
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
            <button
              type="button"
              className="border border-[var(--line)] px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              onClick={onEditCancel}
            >
              {COPY.studio.cancel}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="bg-[var(--ok)] px-3 py-2 text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              onClick={() => void onReview("accept")}
            >
              {COPY.studio.accept}
            </button>
            <button
              type="button"
              className="border border-[var(--line)] px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              onClick={openEdit}
            >
              {COPY.studio.edit}
            </button>
            <button
              type="button"
              className="bg-[var(--danger)] px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              onClick={() => void onReview("reject")}
            >
              {COPY.studio.reject}
            </button>
            <div className="relative" ref={mergeRef}>
              <button
                type="button"
                className="border border-[var(--line)] px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
                onClick={() => (mergeOpen ? closeMerge() : onMergeOpenChange(true))}
              >
                {COPY.studio.merge}
              </button>
              {mergeOpen ? (
                <div className="absolute right-0 z-10 mt-1 w-72 border border-[var(--line)] bg-[var(--surface)] p-3 shadow-lg">
                  <input
                    className="w-full border border-[var(--line)] bg-transparent px-2 py-1 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
                    placeholder="Search headword…"
                    value={mergeQuery}
                    onChange={(e) => setMergeQuery(e.target.value)}
                    autoFocus
                  />
                  <ul className="mt-2 max-h-40 overflow-y-auto text-sm">
                    {mergeHits.map((h) => (
                      <li key={h.id}>
                        <button
                          type="button"
                          className="w-full px-1 py-1 text-left hover:bg-[var(--line)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
                          onClick={() => setMergeTarget(h)}
                        >
                          {h.term}
                        </button>
                      </li>
                    ))}
                  </ul>
                  {mergeTarget ? (
                    <div className="mt-3 space-y-2 border-t border-[var(--line)] pt-2">
                      <p className="text-sm">
                        {mergePreview(entry.term, mergeTarget.term)}
                      </p>
                      <button
                        type="button"
                        className="bg-[var(--accent)] px-2 py-1 text-sm text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
                        onClick={() =>
                          void onReview("merge", { merge_into_id: mergeTarget.id }).then(
                            () => closeMerge(),
                          )
                        }
                      >
                        Confirm merge
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </>
        )}
      </div>
    </article>
  );
}
