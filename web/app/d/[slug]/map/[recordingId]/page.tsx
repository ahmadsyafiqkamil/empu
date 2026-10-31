import Link from "next/link";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { formatTime, formatTimeRange } from "@/lib/time";
import type { Archive } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

type MapEntry = { id: number; term: string; keyframe_url: string | null };
type MapStep = {
  pack_stage_id: string | null;
  name: string;
  t_start: number;
  t_end: number;
  entries: MapEntry[];
};
type ProcessMap = {
  recording_id: number;
  title: string;
  duration_s: number | null;
  steps: MapStep[];
};

export default async function ProcessMapPage({
  params,
}: {
  params: Promise<{ slug: string; recordingId: string }>;
}) {
  const { slug, recordingId } = await params;

  const archive: Archive | null = await fetch(`${API}/api/public/archives/${slug}`, {
    cache: "no-store",
  })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);

  const r = await fetch(`${API}/api/public/recordings/${recordingId}/process-map`, {
    cache: "no-store",
  });

  if (!r.ok) {
    return (
      <>
        <PublicHeader />
        <main className="mx-auto w-full max-w-[1100px] px-5 py-16 lg:px-0">
          <div className="empty">
            <span>This recording isn&apos;t public, or it has no process map yet.</span>
            <Link href={`/d/${slug}`} className="btn btn-secondary">
              Back to the dictionary
            </Link>
          </div>
        </main>
        <PublicFooter />
      </>
    );
  }

  const map: ProcessMap = await r.json();
  const duration = map.duration_s ?? 0;

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[1100px] px-5 pt-8 pb-16 lg:px-0">
        <p className="flex flex-wrap gap-2 text-[13px] text-[var(--color-neutral-700)]">
          <Link href={`/d/${slug}`} className="text-inherit">
            {archive?.title ?? slug}
          </Link>
          <span aria-hidden>/</span>
          <Link href="/map" className="text-inherit">
            Process map
          </Link>
        </p>

        <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-[var(--color-divider)] pt-4 pb-5">
          <h1 className="m-0 text-[30px] leading-none tracking-[-0.03em] md:text-[40px] lg:text-[48px]">
            {map.title}
          </h1>
          {duration ? (
            <span className="mono text-[13px] text-[var(--color-neutral-700)]">
              {formatTime(duration)}
            </span>
          ) : null}
        </div>

        {map.steps.length === 0 ? (
          <div className="empty mt-8">
            <span>No process map yet for this recording.</span>
          </div>
        ) : (
          <>
            {/* Desktop: one column per stage, proportional to duration. */}
            <div className="mt-6 hidden overflow-x-auto border-t-2 border-l-2 border-[var(--color-divider)] lg:flex">
              {map.steps.map((s, i) => {
                const share = ((s.t_end - s.t_start) / Math.max(1, duration)) * 100;
                const width = Math.max(200, share * 10);
                return (
                  <div
                    key={`${s.pack_stage_id ?? s.name}-${i}`}
                    className="flex flex-none flex-col border-r-2 border-b-2 border-[var(--color-divider)]"
                    style={{ width }}
                  >
                    <div className="border-b border-[var(--color-divider)] px-3 py-2.5">
                      <div className="text-[15px] font-semibold">{s.name}</div>
                      <div className="mono text-[11px] text-[var(--color-neutral-700)]">
                        {formatTimeRange(s.t_start, s.t_end)}
                      </div>
                    </div>
                    <div className="flex flex-col gap-2 p-3">
                      {s.entries.length === 0 ? (
                        <span className="text-[12px] text-[var(--color-neutral-600)]">
                          No public term here
                        </span>
                      ) : (
                        s.entries.map((e) => (
                          <Link
                            key={e.id}
                            href={`/d/${slug}/${e.id}`}
                            className="flex items-center gap-2 text-[var(--color-text)] no-underline hover:text-[var(--color-accent-700)]"
                          >
                            <span className="frame-media grid size-9 shrink-0 place-items-center bg-[var(--color-surface)]">
                              {e.keyframe_url ? (
                                // Frame URL only — original recording still.
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={e.keyframe_url}
                                  alt=""
                                  className="size-full object-cover"
                                />
                              ) : null}
                            </span>
                            <span className="min-w-0 truncate text-[13px] font-semibold">
                              {e.term}
                            </span>
                          </Link>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Mobile: vertical list */}
            <ol className="m-0 mt-6 flex list-none flex-col p-0 lg:hidden">
              {map.steps.map((s, i) => (
                <li
                  key={`${s.pack_stage_id ?? s.name}-${i}`}
                  className="border-b border-[var(--color-divider)] py-4"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[17px] font-semibold">{s.name}</span>
                    <span className="mono text-[12px] text-[var(--color-neutral-700)]">
                      {formatTime(s.t_start)}
                    </span>
                  </div>
                  <ul className="m-0 mt-2 flex list-none flex-col gap-1.5 p-0">
                    {s.entries.map((e) => (
                      <li key={e.id}>
                        <Link href={`/d/${slug}/${e.id}`} className="text-[14px]">
                          {e.term}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </>
        )}
      </main>
      <PublicFooter />
    </>
  );
}
