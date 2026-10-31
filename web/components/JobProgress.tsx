"use client";

import { Check, Circle, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Stepper } from "@/components/Stepper";
import { apiGet, apiSend } from "@/lib/api";
import { STAGE_LABEL } from "@/lib/copy";
import { cn } from "@/lib/cn";
import type { Archive, Job, JobStageStatus, JobStatus, Recording } from "@/lib/types";

const STEPS = [{ label: "Upload" }, { label: "Process" }, { label: "Review in Studio" }];

const STAGE_HINT: Record<string, string> = {
  normalizing: "Converting to a standard format and reading the audio track.",
  chunking: "Splitting the video so each part can be watched in full.",
  analyzing: "Proposing terms from speech, on-screen text and what is shown.",
  merging: "Linking each term to a known stage and flagging new terms.",
  grounding: "Cropping the named tool from the original frame.",
  cutting: "Saving the exact moment each term was said or shown.",
  ready: "Everything is ready for a person to review.",
};

function shouldPollJob(status: JobStatus): boolean {
  switch (status) {
    case "ready":
    case "failed":
      return false;
    case "queued":
    case "normalizing":
    case "chunking":
    case "analyzing":
    case "merging":
    case "grounding":
    case "cutting":
      return true;
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

function StageIcon({ status }: { status: JobStageStatus }) {
  const cls = "size-4 shrink-0";
  switch (status) {
    case "pending":
      return <Circle className={cn(cls, "text-[var(--color-neutral-500)]")} aria-hidden />;
    case "running":
      return <Loader2 className={cn(cls, "animate-spin text-[var(--color-accent)]")} aria-hidden />;
    case "done":
      return <Check className={cls} aria-hidden />;
    case "error":
      return <XCircle className={cn(cls, "text-[var(--color-accent-700)]")} aria-hidden />;
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

function secondsLabel(job: Job): string {
  if (job.status === "ready") {
    const total = job.stages.reduce((n, s) => n + (s.seconds ?? 0), 0);
    return `${Math.round(total)}s total`;
  }
  const started = job.stages
    .map((s) => s.started_at)
    .filter((v): v is string => Boolean(v))
    .map((v) => new Date(v).getTime())
    .filter((v) => Number.isFinite(v));
  if (!started.length) return "";
  const elapsed = Math.max(0, Date.now() - Math.min(...started));
  const m = Math.floor(elapsed / 60000);
  const s = Math.floor((elapsed % 60000) / 1000);
  return `${m}:${String(s).padStart(2, "0")} elapsed`;
}

export function JobProgress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [rec, setRec] = useState<Recording | null>(null);
  const [archive, setArchive] = useState<Archive | null>(null);

  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function tickOnce() {
      try {
        const j = await apiGet<Job>(`/api/jobs/${jobId}`);
        if (stop) return;
        setJob(j);
        if (shouldPollJob(j.status)) {
          timer = setTimeout(tickOnce, 2000);
        }
      } catch {
        if (!stop) timer = setTimeout(tickOnce, 2000);
      }
    }

    void tickOnce();
    return () => {
      stop = true;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [jobId]);

  const recordingIdNum = job?.recording_id;

  useEffect(() => {
    if (!recordingIdNum) return;
    let cancelled = false;
    void (async () => {
      try {
        const r = await apiGet<Recording>(`/api/recordings/${recordingIdNum}`);
        if (cancelled) return;
        setRec(r);
        try {
          const a = await apiGet<Archive>(`/api/archives/${r.archive_id}`);
          if (!cancelled) setArchive(a);
        } catch {
          /* archive label is optional */
        }
      } catch {
        /* metadata is optional */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [recordingIdNum]);

  const pct = useMemo(() => Math.round((job?.progress ?? 0) * 100), [job?.progress]);
  const done = job?.stages.filter((s) => s.status === "done").length ?? 0;
  const elapsed = job ? secondsLabel(job) : "";

  if (!job) {
    return <p className="p-8 text-[13px] text-[var(--color-neutral-700)]">Loading job…</p>;
  }

  const stepIndex = 1;

  return (
    <>
      <Stepper steps={STEPS} active={stepIndex} done={[0]} />

      <div className="grid grid-cols-[minmax(0,1fr)] flex-1 lg:grid-cols-[minmax(0,1fr)_400px]">
        <div className="flex flex-col gap-6 border-[var(--color-divider)] px-5 py-10 lg:border-r-2 lg:px-14 lg:py-12">
          <div>
            <h1 className="m-0 text-[32px] tracking-[-0.02em] lg:text-[42px]">Processing</h1>
            <p className="mt-1 mb-0 text-[15px] text-[var(--color-neutral-800)]">
              {job.mode === "B" ? "Mode B · retimed with speech recognition" : "Mode A"}
              {elapsed ? ` · ${elapsed}` : ""}
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex justify-between text-[13px]">
              <span>
                Step {Math.min(done + 1, job.stages.length)} of {job.stages.length}
              </span>
              <span className="font-heading">{pct}%</span>
            </div>
            <div className="h-2 bg-[var(--color-neutral-300)]">
              <div
                className="h-2 bg-[var(--color-accent)] transition-[width] duration-150"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          <ol className="flex flex-col border-t-2 border-[var(--color-divider)]">
            {job.stages.map((s, i) => (
              <li
                key={s.name}
                className="grid grid-cols-[28px_24px_minmax(0,1fr)] items-start gap-3 border-b border-[var(--color-divider)] py-4 lg:grid-cols-[44px_28px_minmax(0,1fr)_120px] lg:gap-3"
                style={{
                  opacity: s.status === "pending" ? 0.55 : 1,
                  background: s.status === "running" ? "var(--color-surface)" : undefined,
                }}
              >
                <span className="mono hidden pt-0.5 pl-2 text-[13px] text-[var(--color-neutral-700)] lg:block">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="flex pt-0.5">
                  <StageIcon status={s.status} />
                </span>
                <span className="flex flex-col gap-0.5">
                  <span className="text-[16px] font-semibold lg:text-[17px]">
                    {STAGE_LABEL[s.name as keyof typeof STAGE_LABEL] ?? s.name}
                  </span>
                  <span className="text-[13px] text-[var(--color-neutral-700)]">
                    {s.status === "running" && job.detail ? job.detail : STAGE_HINT[s.name]}
                  </span>
                </span>
                <span className="mono col-start-3 text-[12px] text-[var(--color-neutral-700)] lg:col-start-4 lg:pt-0.5 lg:pr-2 lg:text-right lg:text-[13px]">
                  {s.seconds != null ? `${s.seconds.toFixed(1)}s` : s.status === "running" ? "…" : "—"}
                </span>
              </li>
            ))}
          </ol>

          {job.status === "ready" ? (
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={`/studio/recordings/${job.recording_id}`}
                className="btn btn-primary h-11 min-w-[200px] justify-start"
              >
                Open in Studio
                <span className="ml-auto" aria-hidden>
                  →
                </span>
              </Link>
              <span className="text-[13px] text-[var(--color-neutral-700)]">
                A person reviews every proposed term next.
              </span>
            </div>
          ) : job.status === "failed" ? (
            <div className="flex flex-col gap-3">
              <p className="m-0 text-[13px] text-[var(--color-accent-700)]">
                {job.error ?? "Processing failed."}
              </p>
              <button
                type="button"
                className="btn btn-secondary self-start h-11"
                onClick={async () => {
                  const res = await apiSend<{ job_id: number }>(
                    `/api/recordings/${job.recording_id}/reprocess`,
                    {
                      method: "POST",
                      body: JSON.stringify({}),
                      headers: { "Content-Type": "application/json" },
                    },
                  );
                  router.push(`/studio/jobs/${res.job_id}`);
                }}
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled
                className="btn btn-primary h-11 min-w-[200px] justify-start"
              >
                Open in Studio
                <span className="ml-auto" aria-hidden>
                  →
                </span>
              </button>
              <span className="text-[13px] text-[var(--color-neutral-700)]">
                Available when all steps are done. Processing continues if you leave.
              </span>
            </div>
          )}
        </div>

        <aside className="flex flex-col border-t-2 border-[var(--color-divider)] lg:border-t-0">
          <div className="frame-media aspect-video">
            {rec?.display_url ? (
              <video
                src={rec.display_url}
                muted
                playsInline
                preload="metadata"
                className="size-full object-cover"
              />
            ) : null}
          </div>
          <div className="flex flex-col gap-3 px-6 py-6">
            <h3 className="m-0 text-[22px]">{rec?.title ?? "Recording"}</h3>
            <dl className="grid grid-cols-[120px_minmax(0,1fr)] text-[13px]">
              {[
                ["Archive", archive?.title ?? "—"],
                [
                  "Duration",
                  rec?.duration_s
                    ? `${Math.floor(rec.duration_s / 60)}:${String(
                        Math.floor(rec.duration_s % 60),
                      ).padStart(2, "0")}`
                    : "—",
                ],
                ["Contributor", rec?.contributor?.name ?? "—"],
                ["Source", rec?.source_kind === "cc_by_video" ? "CC BY video" : "Own recording"],
                [
                  "Consent",
                  rec?.consent_status === "withdrawn"
                    ? "Withdrawn"
                    : rec?.consent_scope
                      ? `${rec.consent_scope.charAt(0).toUpperCase()}${rec.consent_scope.slice(1)}`
                      : "—",
                ],
              ].map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="border-b border-[var(--color-divider)] py-2.5 text-[var(--color-neutral-700)]">
                    {k}
                  </dt>
                  <dd className="m-0 border-b border-[var(--color-divider)] py-2.5">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </aside>
      </div>
    </>
  );
}
