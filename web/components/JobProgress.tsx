"use client";

import { Check, Circle, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import { STAGE_LABEL } from "@/lib/copy";
import { cn } from "@/lib/cn";
import type { Job, JobStatus } from "@/lib/types";

type StageStatus = "waiting" | "running" | "done" | "failed";

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

function StageStatusIcon({ status }: { status: string }) {
  const iconClass = "size-4 shrink-0";
  switch (status as StageStatus) {
    case "waiting":
      return <Circle className={cn(iconClass, "text-[var(--muted)]")} aria-hidden />;
    case "running":
      return (
        <Loader2
          className={cn(iconClass, "animate-spin text-[var(--accent)]")}
          aria-hidden
        />
      );
    case "done":
      return <Check className={cn(iconClass, "text-[var(--ok)]")} aria-hidden />;
    case "failed":
      return <XCircle className={cn(iconClass, "text-[var(--danger)]")} aria-hidden />;
    default:
      return <Circle className={cn(iconClass, "text-[var(--muted)]")} aria-hidden />;
  }
}

function stageLabel(name: string): string {
  if (name in STAGE_LABEL) {
    return STAGE_LABEL[name as keyof typeof STAGE_LABEL];
  }
  return name;
}

function JobStatusFooter({ job, router }: { job: Job; router: ReturnType<typeof useRouter> }) {
  switch (job.status) {
    case "ready":
      return (
        <Link
          className="mt-6 inline-block bg-[var(--accent)] px-4 py-2 text-[var(--bg)]"
          href={`/studio/recordings/${job.recording_id}`}
        >
          Open in Studio
        </Link>
      );
    case "failed":
      return (
        <div className="mt-6 space-y-2">
          {job.error ? <p className="text-[var(--danger)]">{job.error}</p> : null}
          <button
            className="border border-[var(--line)] px-4 py-2"
            type="button"
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
      );
    case "queued":
    case "normalizing":
    case "chunking":
    case "analyzing":
    case "merging":
    case "grounding":
    case "cutting":
      return null;
    default: {
      const _exhaustive: never = job.status;
      return _exhaustive;
    }
  }
}

export function JobProgress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function tick() {
      try {
        const j = await apiGet<Job>(`/api/jobs/${jobId}`);
        if (stop) return;
        setJob(j);
        if (shouldPollJob(j.status)) {
          timer = setTimeout(tick, 2000);
        }
      } catch {
        if (!stop) {
          timer = setTimeout(tick, 2000);
        }
      }
    }

    void tick();
    return () => {
      stop = true;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [jobId]);

  if (!job) {
    return <p className="p-8">Loading…</p>;
  }

  const modeLine =
    job.mode === "B" ? "Mode B · retimed with speech recognition" : "Mode A";

  return (
    <main className="mx-auto max-w-lg p-8">
      <h1 className="text-2xl">Processing</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        {modeLine}
        {job.detail ? ` · ${job.detail}` : ""}
      </p>
      <ol className="mt-6 space-y-2">
        {job.stages.map((s) => (
          <li
            key={s.name}
            className="flex items-center justify-between gap-3 border-b border-[var(--line)] py-2"
          >
            <span className="flex min-w-0 items-center gap-2">
              <StageStatusIcon status={s.status} />
              <span>{stageLabel(s.name)}</span>
            </span>
            <span className="shrink-0 text-right text-sm text-[var(--muted)]">
              {s.status}
              {s.seconds != null ? ` · ${s.seconds.toFixed(1)}s` : ""}
              {s.status === "running" && job.detail ? ` · ${job.detail}` : ""}
            </span>
          </li>
        ))}
      </ol>
      <div className="mt-4 h-1 bg-[var(--line)]">
        <div
          className="h-1 bg-[var(--accent)] transition-[width] duration-150"
          style={{ width: `${Math.round(job.progress * 100)}%` }}
        />
      </div>
      <JobStatusFooter job={job} router={router} />
    </main>
  );
}
