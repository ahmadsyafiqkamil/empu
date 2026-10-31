"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { Archive, RecordingSummary } from "@/lib/types";

type Row = RecordingSummary & { archiveTitle: string };

const STATUS_LABEL: Record<string, { label: string; filled: boolean }> = {
  ready: { label: "Ready", filled: false },
  failed: { label: "Failed", filled: false },
};

function statusFor(r: Row): { label: string; style: React.CSSProperties } {
  if (r.status !== "ready") {
    const known = STATUS_LABEL[r.status];
    return {
      label: known?.label ?? "Processing",
      style: {
        background: "transparent",
        color: "var(--color-neutral-800)",
        borderColor: "var(--color-neutral-500)",
      },
    };
  }
  if (r.n_proposed > 0) {
    return {
      label: "Needs review",
      style: {
        background: "var(--color-accent-100)",
        color: "var(--color-accent-800)",
        borderColor: "var(--color-accent-300)",
      },
    };
  }
  return {
    label: "Reviewed",
    style: {
      background: "var(--color-text)",
      color: "var(--color-bg)",
      borderColor: "var(--color-text)",
    },
  };
}

function metaFor(r: Row): string {
  const bits: string[] = [];
  if (r.source_kind === "cc_by_video" && r.source_creator) bits.push(`CC BY · ${r.source_creator}`);
  if (r.duration_s) {
    const m = Math.floor(r.duration_s / 60);
    const s = Math.floor(r.duration_s % 60);
    bits.push(`${m}:${String(s).padStart(2, "0")}`);
  }
  return bits.join(" · ");
}

export function StudioHome() {
  const [archives, setArchives] = useState<Archive[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await apiGet<Archive[]>("/api/archives");
        if (cancelled) return;
        setArchives(list);
        const nested = await Promise.all(
          list.map((a) =>
            apiGet<RecordingSummary[]>(`/api/archives/${a.id}/recordings`)
              .then((recs) => recs.map((r) => ({ ...r, archiveTitle: a.title })))
              .catch(() => [] as Row[]),
          ),
        );
        if (!cancelled) setRows(nested.flat());
      } catch {
        if (!cancelled) setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const waiting = rows.filter((r) => r.n_proposed > 0).length;
  const reviewed = rows.reduce((n, r) => n + r.n_reviewed, 0);

  return (
    <>
      <div className="grid grid-cols-[minmax(0,1fr)] border-b-2 border-[var(--color-divider)] lg:grid-cols-[minmax(0,1fr)_repeat(3,200px)]">
        <div className="px-5 py-8 lg:px-14 lg:pt-10 lg:pb-8">
          <h1 className="m-0 text-[32px] tracking-[-0.02em] lg:text-[42px]">Recordings</h1>
          <p className="mt-1 text-[15px] text-[var(--color-neutral-800)]">
            AI proposes; a person decides. Review what&apos;s waiting.
          </p>
        </div>
        {[
          { label: "Waiting for review", value: waiting, accent: true },
          { label: "Reviewed entries", value: reviewed },
          { label: "Archives", value: archives.length },
        ].map((s) => (
          <div
            key={s.label}
            className="border-t border-[var(--color-divider)] px-5 py-6 lg:border-t-0 lg:border-l"
          >
            <div className="text-[12px] text-[var(--color-neutral-700)]">{s.label}</div>
            <div
              className="font-heading text-[36px] leading-[1.1] lg:text-[42px]"
              style={s.accent ? { color: "var(--color-accent-700)" } : undefined}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] flex-1 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 overflow-x-auto px-5 py-6 lg:px-14 lg:py-8">
          {loading ? (
            <p className="text-[13px] text-[var(--color-neutral-700)]">Loading recordings…</p>
          ) : rows.length === 0 ? (
            <div className="empty">
              <span>No recordings yet.</span>
              <Link href="/studio/upload" className="btn btn-secondary">
                Upload a recording
              </Link>
            </div>
          ) : (
            <table className="table min-w-[720px]">
              <thead>
                <tr>
                  <th>Recording</th>
                  <th>Archive</th>
                  <th>Status</th>
                  <th className="w-[200px]">Reviewed</th>
                  <th>Consent</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const st = statusFor(r);
                  const pct = r.n_entries ? (r.n_reviewed / r.n_entries) * 100 : 0;
                  return (
                    <tr key={r.id}>
                      <td className="py-3.5">
                        <div className="font-semibold">{r.title}</div>
                        <div className="text-[12px] text-[var(--color-neutral-700)]">
                          {metaFor(r)}
                        </div>
                      </td>
                      <td className="text-[13px]">{r.archiveTitle}</td>
                      <td>
                        <span
                          className="inline-flex border px-1.5 py-0.5 text-[11px] font-semibold whitespace-nowrap"
                          style={st.style}
                        >
                          {st.label}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2 text-[12px]">
                          <div className="h-1 flex-1 bg-[var(--color-neutral-300)]">
                            <div
                              className="h-1 bg-[var(--color-text)]"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="mono whitespace-nowrap">
                            {r.n_reviewed} / {r.n_entries}
                          </span>
                        </div>
                      </td>
                      <td className="text-[13px]">
                        {r.consent_status === "withdrawn"
                          ? "Withdrawn"
                          : r.consent_scope.charAt(0).toUpperCase() + r.consent_scope.slice(1)}
                      </td>
                      <td className="text-right">
                        <Link
                          href={`/studio/recordings/${r.id}`}
                          className="btn btn-secondary text-[13px] whitespace-nowrap"
                        >
                          {r.n_proposed > 0 ? "Review" : "Open"} →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="border-t-2 border-[var(--color-divider)] lg:border-t-0 lg:border-l-2">
          <Link
            href="/studio/upload"
            className="flex flex-col gap-1 no-underline"
            style={{ background: "var(--color-accent)", color: "var(--color-bg)", padding: 24 }}
          >
            <b className="font-heading text-[20px]">Upload recording →</b>
            <span className="text-[13px]">A narrated work video, up to 20 minutes.</span>
          </Link>
          <Link
            href="/studio/export"
            className="flex flex-col gap-1 border-b border-[var(--color-divider)] px-6 py-5 text-[var(--color-text)] no-underline hover:bg-[var(--color-surface)]"
          >
            <b className="font-heading text-[18px]">Export</b>
            <span className="text-[13px] text-[var(--color-neutral-700)]">
              JSON, CSV, ELAN or a ZIP of the archive.
            </span>
          </Link>
          <Link
            href="/studio/packs"
            className="flex flex-col gap-1 border-b border-[var(--color-divider)] px-6 py-5 text-[var(--color-text)] no-underline hover:bg-[var(--color-surface)]"
          >
            <b className="font-heading text-[18px]">Craft packs</b>
            <span className="text-[13px] text-[var(--color-neutral-700)]">
              Stages and terms each craft is matched against.
            </span>
          </Link>
        </div>
      </div>
    </>
  );
}
