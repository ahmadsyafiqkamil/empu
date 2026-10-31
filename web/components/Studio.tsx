"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AudioLines, Eye, Type } from "lucide-react";
import { apiGet, apiSend } from "@/lib/api";
import { COPY, studioReviewProgress } from "@/lib/copy";
import type { Entry, EntryStatus, Recording, Source } from "@/lib/types";
import { EntryCard } from "./EntryCard";
import { Stepper } from "./Stepper";
import { formatTime } from "@/lib/time";

type ReviewAction = "accept" | "edit" | "reject" | "merge" | "restore";
type StatusFilter = EntryStatus | "all" | "novel";

type MapStep = {
  pack_stage_id: string | null;
  name: string;
  t_start: number;
  t_end: number;
  entries: { id: number; term: string; keyframe_url: string | null }[];
};

type ProcessMap = {
  recording_id: number;
  title: string;
  duration_s: number | null;
  steps: MapStep[];
};

const FILTERS: { id: StatusFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "proposed", label: "Proposed" },
  { id: "accepted", label: "Accepted" },
  { id: "novel", label: "New" },
];

const LANES: { source: Source; label: string; icon: typeof AudioLines }[] = [
  { source: "speech", label: "Spoken", icon: AudioLines },
  { source: "on_screen_text", label: "On-screen", icon: Type },
  { source: "visual_only", label: "Visual", icon: Eye },
];

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
      return { action, actor: "documenter", merge_into_id: extra?.merge_into_id };
    default: {
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}

export function Studio({ recordingId }: { recordingId: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [rec, setRec] = useState<Recording | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [map, setMap] = useState<ProcessMap | null>(null);
  const [idx, setIdx] = useState(0);
  const [filter, setFilter] = useState<StatusFilter>("proposed");
  const [editing, setEditing] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [now, setNow] = useState(0);

  useEffect(() => {
    let stop = false;
    void (async () => {
      try {
        const r = await apiGet<Recording>(`/api/recordings/${recordingId}`);
        const e = await apiGet<Entry[]>(`/api/recordings/${recordingId}/entries`);
        if (!stop) {
          setRec(r);
          setEntries(e);
        }
        const m = await apiGet<ProcessMap>(`/api/recordings/${recordingId}/process-map`).catch(
          () => null,
        );
        if (!stop && m) setMap(m);
      } catch {
        /* keep loading state */
      }
    })();
    return () => {
      stop = true;
    };
  }, [recordingId]);

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
        if (filter === "novel") return e.is_novel;
        if (filter !== "all" && e.status !== filter) return false;
        return true;
      }),
    [entries, filter],
  );

  const activeIdx = Math.min(idx, Math.max(0, visible.length - 1));
  const current = visible[activeIdx] ?? null;
  const dur = rec?.duration_s || 1;

  const seekEntry = useCallback(
    (i: number) => {
      setEditing(false);
      setMergeOpen(false);
      setIdx(i);
      const t = visible[i]?.best_occurrence?.t_start ?? 0;
      if (videoRef.current) {
        videoRef.current.currentTime = t;
        setNow(t);
      }
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
        setEntries((all) => all.map((e) => (e.id === updated.id ? { ...e, ...updated } : e)));
      }
      setEditing(false);
    },
    [current],
  );

  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      const tag = (ev.target as HTMLElement | null)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (ev.key === "Escape") {
        setEditing(false);
        setMergeOpen(false);
        setWithdrawOpen(false);
        return;
      }
      if (editing || mergeOpen || withdrawOpen) return;
      const k = ev.key.toLowerCase();
      if (k === "j") seekEntry(Math.min(visible.length - 1, activeIdx + 1));
      if (k === "k") seekEntry(Math.max(0, activeIdx - 1));
      if (k === "a") void review("accept");
      if (k === "r") void review("reject");
      if (k === "e") {
        ev.preventDefault();
        setEditing(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing, mergeOpen, withdrawOpen, activeIdx, visible.length, seekEntry, review]);

  if (!rec) {
    return <p className="p-8 text-[13px] text-[var(--color-neutral-700)]">Loading recording…</p>;
  }

  const pct = counts.proposed + reviewed ? (reviewed / (counts.proposed + reviewed)) * 100 : 0;
  const steps = map?.steps ?? [];

  return (
    <>
      <Stepper steps={[{ label: "Upload" }, { label: "Process" }, { label: "Review in Studio" }]} active={2} done={[0, 1]} />

      {/* Recording strip */}
      <div className="grid grid-cols-[minmax(0,1fr)] border-b-2 border-[var(--color-divider)] lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="flex flex-col gap-0.5 px-6 py-5">
          <span className="text-[12px] text-[var(--color-neutral-700)]">
            Recording · {rec.duration_s ? formatTime(rec.duration_s) : "—"}
          </span>
          <h1 className="m-0 text-[26px] leading-tight tracking-[-0.02em] lg:text-[32px]">
            {rec.title}
          </h1>
          <span className="text-[13px] text-[var(--color-neutral-700)]">
            {rec.contributor?.name ? `Recorded by ${rec.contributor.name} · ` : ""}
            {rec.source_kind === "cc_by_video" ? "CC BY video" : "Own recording"} · Consent:{" "}
            {rec.consent_status === "withdrawn"
              ? "Withdrawn"
              : rec.consent_scope
                ? rec.consent_scope.charAt(0).toUpperCase() + rec.consent_scope.slice(1)
                : "—"}
          </span>
        </div>

        <div className="grid grid-cols-2 border-t-2 border-[var(--color-divider)] sm:grid-cols-4 lg:grid-cols-[repeat(4,110px)_240px] lg:border-t-0 lg:border-l-2">
          {[
            ["Proposed", counts.proposed],
            ["Accepted", counts.accepted],
            ["Edited", counts.edited],
            ["Rejected", counts.rejected],
          ].map(([label, value]) => (
            <div
              key={String(label)}
              className="border-r border-[var(--color-divider)] px-4 py-4"
            >
              <div className="text-[12px] text-[var(--color-neutral-700)]">{label}</div>
              <div className="font-heading text-[26px] leading-[1.1] lg:text-[32px]">{value}</div>
            </div>
          ))}
          <div className="col-span-2 flex flex-col justify-between gap-2 px-4 py-4 sm:col-span-4 lg:col-span-1">
            <div className="flex justify-between text-[12px]">
              <span className="text-[var(--color-neutral-700)]">Reviewed</span>
              <span className="font-heading">{studioReviewProgress(reviewed, entries.length)}</span>
            </div>
            <div className="h-1.5 bg-[var(--color-neutral-300)]">
              <div className="h-1.5 bg-[var(--color-accent)]" style={{ width: `${pct}%` }} />
            </div>
            <div className="flex flex-wrap gap-1">
              <a
                href={`/map`}
                className="btn btn-ghost text-[12px] text-[var(--color-text)]"
              >
                Process map
              </a>
              <a href="/studio/export" className="btn btn-ghost text-[12px] text-[var(--color-text)]">
                Export
              </a>
              {rec.consent_status !== "withdrawn" ? (
                <button
                  type="button"
                  className="btn btn-ghost text-[12px] text-[var(--color-accent-700)]"
                  onClick={() => setWithdrawOpen(true)}
                >
                  Withdraw consent
                </button>
              ) : (
                <span className="text-[12px] text-[var(--color-neutral-700)]">hidden from public</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Three panes */}
      <div className="grid grid-cols-[minmax(0,1fr)] min-h-0 flex-1 lg:grid-cols-[300px_minmax(0,1fr)_500px]">
        {/* Queue */}
        <div className="flex min-h-0 flex-col border-[var(--color-divider)] lg:border-r-2">
          <div className="flex flex-col gap-2.5 border-b border-[var(--color-divider)] p-4">
            <div className="grid grid-cols-4 border border-[var(--color-divider)]">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => {
                    setFilter(f.id);
                    setIdx(0);
                  }}
                  aria-pressed={filter === f.id}
                  className="border-r border-[var(--color-divider)] px-1 py-1.5 text-[12px] last:border-r-0"
                  style={
                    filter === f.id
                      ? { background: "var(--color-text)", color: "var(--color-bg)" }
                      : undefined
                  }
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="flex justify-between text-[12px] text-[var(--color-neutral-700)]">
              <span>{filter === "novel" ? "New terms" : "Sorted by time"}</span>
              <span>{visible.length} entries</span>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {visible.length === 0 ? (
              <div className="flex flex-col items-start gap-3 p-5">
                <p className="m-0 text-[15px]">{COPY.empty.studioFilter}</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setFilter("accepted");
                    setIdx(0);
                  }}
                >
                  {COPY.empty.showAccepted}
                </button>
              </div>
            ) : (
              visible.map((e, i) => {
                const on = i === activeIdx;
                const src = e.source ?? e.best_occurrence?.source;
                const Icon =
                  src === "speech" ? AudioLines : src === "on_screen_text" ? Type : Eye;
                return (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => seekEntry(i)}
                    className="grid w-full grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-2.5 border-b border-[var(--color-divider)] px-4 py-3 text-left"
                    style={{
                      background: on ? "var(--color-surface)" : undefined,
                      boxShadow: on ? "inset 3px 0 0 var(--color-accent)" : undefined,
                    }}
                  >
                    <span className="flex text-[var(--color-neutral-800)]">
                      {src ? <Icon className="size-4" aria-hidden /> : null}
                    </span>
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate text-[15px] font-semibold">{e.term}</span>
                      <span className="text-[11px] text-[var(--color-neutral-700)]">
                        {e.best_occurrence ? (
                          <span className="mono">{formatTime(e.best_occurrence.t_start)}</span>
                        ) : (
                          "—"
                        )}
                        {e.is_novel ? " · new" : ""}
                      </span>
                    </span>
                    <span
                      className="border px-1.5 py-0.5 text-[11px] font-semibold whitespace-nowrap"
                      style={{
                        background: e.status === "accepted" ? "var(--color-text)" : "transparent",
                        color: e.status === "accepted" ? "var(--color-bg)" : undefined,
                        borderColor:
                          e.status === "rejected"
                            ? "var(--color-accent-300)"
                            : e.status === "accepted"
                              ? "var(--color-text)"
                              : "var(--color-neutral-500)",
                      }}
                    >
                      {e.status === "proposed" ? "Proposed" : e.status === "accepted" ? "Accepted" : e.status === "edited" ? "Edited" : e.status === "rejected" ? "Rejected" : "Merged"}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Player + timeline */}
        <div className="flex min-h-0 flex-col gap-5 border-b-2 border-[var(--color-divider)] p-6 lg:border-b-0 lg:border-r-2">
          <div className="frame-media aspect-video">
            {rec.display_url ? (
              <video
                ref={videoRef}
                src={rec.display_url}
                controls
                playsInline
                preload="metadata"
                className="size-full object-contain"
                onTimeUpdate={(ev) => setNow(ev.currentTarget.currentTime)}
              />
            ) : null}
          </div>

          <div className="flex items-center justify-between text-[12px]">
            <span className="mono text-[var(--color-neutral-800)]">
              {formatTime(now)} / {formatTime(dur)}
            </span>
            <span className="text-[var(--color-neutral-700)]">Click a marker to jump to its time</span>
          </div>

          <div className="flex flex-col border-t-2 border-[var(--color-divider)]">
            {/* Stage bands */}
            <div className="grid grid-cols-[110px_minmax(0,1fr)] border-b border-[var(--color-divider)]">
              <div className="label py-2.5">Stage</div>
              <div className="flex border-l border-[var(--color-divider)] text-[12px]">
                {steps.length > 0 ? (
                  steps.map((s, i) => {
                    const w = Math.max(6, ((s.t_end - s.t_start) / dur) * 100);
                    return (
                      <div
                        key={i}
                        className="overflow-hidden border-r border-[var(--color-divider)] py-2.5 pr-2 pl-2 text-[11px] leading-tight last:border-r-0"
                        style={{ width: `${w}%`, minWidth: 64 }}
                        title={`${s.name} · ${formatTime(s.t_start)}–${formatTime(s.t_end)}`}
                      >
                        <b className="block truncate font-semibold">{s.name}</b>
                      </div>
                    );
                  })
                ) : (
                  <div className="py-2.5 pl-2 text-[var(--color-neutral-700)]">No process map</div>
                )}
              </div>
            </div>

            {/* Lanes */}
            {LANES.map((lane) => {
              const marks = visible.filter(
                (e) => (e.source ?? e.best_occurrence?.source) === lane.source,
              );
              return (
                <div
                  key={lane.source}
                  className="grid h-9 grid-cols-[110px_minmax(0,1fr)] border-b border-[var(--color-divider)]"
                >
                  <div className="flex items-center gap-1.5 text-[12px]">
                    <lane.icon className="size-3" aria-hidden />
                    {lane.label}
                  </div>
                  <div className="relative border-l border-[var(--color-divider)]">
                    {marks.map((e) => {
                      const t = e.best_occurrence?.t_start ?? 0;
                      const on = current?.id === e.id;
                      const i = visible.findIndex((v) => v.id === e.id);
                      return (
                        <button
                          key={e.id}
                          type="button"
                          title={`${e.term} · ${formatTime(t)}`}
                          aria-label={`${e.term} at ${formatTime(t)}`}
                          onClick={() => seekEntry(i)}
                          className="absolute top-3.5 size-2.5 -translate-x-1/2"
                          style={{
                            left: `${Math.min(99, (t / dur) * 100)}%`,
                            background:
                              e.status === "rejected"
                                ? "var(--color-neutral-400)"
                                : on
                                  ? "var(--color-accent)"
                                  : "var(--color-text)",
                            outline: on ? "2px solid var(--color-accent)" : undefined,
                            outlineOffset: on ? 2 : undefined,
                          }}
                        />
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {/* Ruler */}
            <div className="grid grid-cols-[110px_minmax(0,1fr)]">
              <div />
              <div className="mono flex justify-between border-l border-[var(--color-divider)] pt-1.5 text-[11px] text-[var(--color-neutral-700)]">
                {[0, 0.25, 0.5, 0.75, 1].map((f) => (
                  <span key={f}>{formatTime(dur * f)}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-auto flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-[var(--color-divider)] pt-4 text-[12px] text-[var(--color-neutral-800)]">
            {[
              ["A", "Accept"],
              ["E", "Edit"],
              ["R", "Reject"],
              ["K", "Previous"],
              ["J", "Next"],
              ["Esc", "Cancel"],
            ].map(([key, label]) => (
              <span key={key} className="flex items-center gap-1.5">
                <kbd>{key}</kbd>
                {label}
              </span>
            ))}
            <span className="ml-auto text-[var(--color-neutral-700)]">
              {rec.job?.mode === "B" ? "Mode B · retimed with speech recognition" : "Mode A"}
            </span>
          </div>
        </div>

        {/* Entry detail */}
        <div className="flex min-h-0 flex-col">
          {current ? (
            <EntryCard
              key={current.id}
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
            <div className="p-6">
              <p className="m-0 text-[15px]">{COPY.empty.studioFilter}</p>
            </div>
          )}
        </div>
      </div>

      {withdrawOpen ? (
        <div className="dialog-backdrop">
          <div role="dialog" aria-modal="true" aria-labelledby="withdraw-title" className="dialog">
            <div id="withdraw-title" className="dialog-title">
              Withdraw consent for this recording
            </div>
            <p className="m-0 text-[15px] leading-relaxed">{COPY.consent.confirm}</p>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={async () => {
                  const updated = await apiSend<Recording>(
                    `/api/recordings/${recordingId}/withdraw-consent`,
                    { method: "POST" },
                  );
                  setRec((r) => (r ? { ...r, ...updated } : r));
                  setWithdrawOpen(false);
                }}
              >
                Withdraw consent
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setWithdrawOpen(false)}
              >
                {COPY.studio.cancel}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
