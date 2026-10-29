"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import {
  COPY,
  studioReviewProgress,
  studioStatusCounts,
} from "@/lib/copy";
import { sourceColorVar } from "@/lib/source";
import type { Entry, EntryStatus, Recording, Source } from "@/lib/types";
import { EntryCard } from "./EntryCard";
import { AttributionLine } from "./AttributionLine";
import { SourceBadge } from "./SourceBadge";

type ReviewAction = "accept" | "edit" | "reject" | "merge" | "restore";
type StatusFilter = EntryStatus | "all";

const DESKTOP_MIN = 1280;

function reviewBody(
  action: ReviewAction,
  extra?: Record<string, unknown>,
): Record<string, unknown> {
  switch (action) {
    case "accept":
    case "reject":
    case "restore":
      return { action, actor: "documenter" };
    case "edit":
      return { action, actor: "documenter", changes: extra?.changes ?? {} };
    case "merge":
      return {
        action,
        actor: "documenter",
        merge_into_id: extra?.merge_into_id,
      };
    default: {
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}

function TimelineMarker({
  source,
  active,
  leftPct,
  title,
  onClick,
}: {
  source: Source;
  active: boolean;
  leftPct: number;
  title: string;
  onClick: () => void;
}) {
  const color = active ? "var(--wax)" : sourceColorVar(source);
  const base =
    "absolute top-1/2 -translate-x-1/2 -translate-y-1/2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]";
  switch (source) {
    case "speech":
      return (
        <button
          type="button"
          title={title}
          className={`${base} size-3 rounded-full`}
          style={{ left: `${leftPct}%`, background: color }}
          onClick={onClick}
        />
      );
    case "on_screen_text":
      return (
        <button
          type="button"
          title={title}
          className={`${base} size-3`}
          style={{ left: `${leftPct}%`, background: color }}
          onClick={onClick}
        />
      );
    case "visual_only":
      return (
        <button
          type="button"
          title={title}
          className={`${base} h-0 w-0 border-x-[6px] border-b-[10px] border-x-transparent bg-transparent`}
          style={{
            left: `${leftPct}%`,
            borderBottomColor: color,
          }}
          onClick={onClick}
        />
      );
    default: {
      const _exhaustive: never = source;
      return _exhaustive;
    }
  }
}

export function Studio({ recordingId }: { recordingId: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [rec, setRec] = useState<Recording | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [idx, setIdx] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("proposed");
  const [sourceFilter, setSourceFilter] = useState<Source | "all">("all");
  const [novel, setNovel] = useState(false);
  const [editing, setEditing] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [desktopOk, setDesktopOk] = useState(true);

useEffect(() => {
    let stop = false;
    async function load() {
      try {
        const r = await apiGet<Recording>(`/api/recordings/${recordingId}`);
        const e = await apiGet<Entry[]>(`/api/recordings/${recordingId}/entries`);
        if (!stop) {
          setRec(r);
          setEntries(e);
        }
      } catch {
        /* keep loading state */
      }
    }
    void load();
    return () => {
      stop = true;
    };
  }, [recordingId]);

  useEffect(() => {
    function check() {
      setDesktopOk(window.innerWidth >= DESKTOP_MIN);
    }
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const counts = useMemo(() => {
    const c = { proposed: 0, accepted: 0, edited: 0, rejected: 0 };
    for (const e of entries) {
      if (e.status === "proposed") c.proposed += 1;
      else if (e.status === "accepted") c.accepted += 1;
      else if (e.status === "edited") c.edited += 1;
      else if (e.status === "rejected") c.rejected += 1;
    }
    return c;
  }, [entries]);

  const reviewed = counts.accepted + counts.edited + counts.rejected;

  const visible = useMemo(
    () =>
      entries.filter((e) => {
        if (statusFilter !== "all" && e.status !== statusFilter) return false;
        if (sourceFilter !== "all" && e.source !== sourceFilter) return false;
        if (novel && !e.is_novel) return false;
        return true;
      }),
    [entries, statusFilter, sourceFilter, novel],
  );

  const activeIdx = Math.min(idx, Math.max(0, visible.length - 1));
  const current = visible[activeIdx] ?? null;

  const seekEntry = useCallback(
    (i: number) => {
      setEditing(false);
      setMergeOpen(false);
      setIdx(i);
      const e = visible[i];
      const t = e?.best_occurrence?.t_start ?? 0;
      if (videoRef.current) videoRef.current.currentTime = t;
    },
    [visible],
  );

  const review = useCallback(
    async (action: ReviewAction, extra?: Record<string, unknown>) => {
      if (!current) return;
      const updated = await apiSend<Entry>(`/api/entries/${current.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reviewBody(action, extra)),
      });
      if (action === "merge") {
        setEntries((all) => all.filter((e) => e.id !== current.id));
      } else {
        setEntries((all) =>
          all.map((e) => (e.id === updated.id ? { ...e, ...updated } : e)),
        );
      }
    },
    [current],
  );

  const withdraw = useCallback(async () => {
    if (!window.confirm("Hide this recording from the public dictionary?")) return;
    const updated = await apiSend<Recording>(`/api/recordings/${recordingId}/withdraw-consent`, {
      method: "POST",
    });
    setRec((r) => (r ? { ...r, ...updated } : r));
  }, [recordingId]);

  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      if (ev.target instanceof HTMLInputElement || ev.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (editing || mergeOpen) return;
      if (ev.key === "j" || ev.key === "J") seekEntry(Math.min(visible.length - 1, activeIdx + 1));
      if (ev.key === "k" || ev.key === "K") seekEntry(Math.max(0, activeIdx - 1));
      if (ev.key === "a" || ev.key === "A") void review("accept");
      if (ev.key === "r" || ev.key === "R") void review("reject");
      if (ev.key === "e" || ev.key === "E") setEditing(true);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing, mergeOpen, activeIdx, visible.length, seekEntry, review]);

  if (!desktopOk) {
    return (
      <p className="p-8 text-center text-[var(--muted)]">{COPY.empty.studioDesktop}</p>
    );
  }

  if (!rec) return <p className="p-8">Loading…</p>;

  const dur = rec.duration_s || 1;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-[var(--line)] px-4 py-3 text-sm">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="font-display text-lg">{rec.title}</h1>
          <AttributionLine variant="inline" attribution={rec.attribution} />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--muted)]">
          <span>{studioStatusCounts(counts)}</span>
          <span>{studioReviewProgress(reviewed, entries.length)}</span>
          <span>
            {COPY.studio.accept} · {COPY.studio.edit} · {COPY.studio.reject} ·{" "}
            {COPY.studio.previous} · {COPY.studio.next}
          </span>
          {rec.consent_status !== "withdrawn" ? (
            <button
              type="button"
              className="underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
              onClick={() => void withdraw()}
            >
              Withdraw consent
            </button>
          ) : (
            <span>hidden from public</span>
          )}
        </div>
      </header>
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.2fr)_minmax(24rem,1fr)]">
        <section className="border-r border-[var(--line)] p-4">
          {rec.display_url ? (
            <video
              ref={videoRef}
              src={rec.display_url}
              controls
              className="aspect-video w-full bg-black"
            />
          ) : null}
          <div className="relative mt-3 h-10 rounded bg-[var(--line)]/40">
            {visible.map((e, i) => {
              const occ = e.best_occurrence;
              const src = e.source ?? occ?.source;
              if (!src) return null;
              const t = occ?.t_start ?? 0;
              return (
                <TimelineMarker
                  key={e.id}
                  source={src}
                  active={i === activeIdx}
                  leftPct={(t / dur) * 100}
                  title={e.term}
                  onClick={() => seekEntry(i)}
                />
              );
            })}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-[var(--muted)]">
            <span className="inline-flex items-center gap-1">
              <SourceBadge source="speech" size="sm" />
            </span>
            <span className="inline-flex items-center gap-1">
              <SourceBadge source="on_screen_text" size="sm" />
            </span>
            <span className="inline-flex items-center gap-1">
              <SourceBadge source="visual_only" size="sm" />
            </span>
          </div>
        </section>
        <section className="flex min-h-0 flex-col">
          <div className="flex flex-wrap items-center gap-2 border-b border-[var(--line)] p-3 text-sm">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as StatusFilter);
                setIdx(0);
              }}
              className="border border-[var(--line)] bg-transparent p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
            >
              <option value="all">All</option>
              <option value="proposed">Proposed</option>
              <option value="accepted">Accepted</option>
              <option value="edited">Edited</option>
              <option value="rejected">Rejected</option>
            </select>
            <select
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value as Source | "all");
                setIdx(0);
              }}
              className="border border-[var(--line)] bg-transparent p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
            >
              <option value="all">all sources</option>
              <option value="speech">spoken</option>
              <option value="on_screen_text">on-screen text</option>
              <option value="visual_only">visual only</option>
            </select>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={novel}
                onChange={(e) => {
                  setNovel(e.target.checked);
                  setIdx(0);
                }}
              />
              novel
            </label>
            <span className="ml-auto text-[var(--muted)]">{visible.length} entries</span>
          </div>
          {current ? (
            <EntryCard
              entry={current}
              archiveId={rec.archive_id}
              editing={editing}
              onEditStart={() => setEditing(true)}
              onEditCancel={() => setEditing(false)}
              onReview={review}
              mergeOpen={mergeOpen}
              onMergeOpenChange={setMergeOpen}
            />
          ) : (
            <div className="space-y-3 p-4">
              <p className="text-[var(--muted)]">{COPY.empty.studioFilter}</p>
              <button
                type="button"
                className="text-sm text-[var(--accent)] underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)]"
                onClick={() => {
                  setStatusFilter("accepted");
                  setIdx(0);
                }}
              >
                {COPY.empty.showAccepted}
              </button>
            </div>
          )}
          {visible.length > 0 ? (
            <ul className="mt-auto max-h-32 overflow-y-auto border-t border-[var(--line)] text-xs">
              {visible.map((e, i) => (
                <li key={e.id}>
                  <button
                    type="button"
                    className={`flex w-full items-center gap-2 px-3 py-1.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--wax)] ${
                      i === activeIdx ? "bg-[var(--line)]/50" : ""
                    }`}
                    onClick={() => seekEntry(i)}
                  >
                    {e.source ? <SourceBadge source={e.source} size="sm" /> : null}
                    <span className="truncate">{e.term}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  );
}
