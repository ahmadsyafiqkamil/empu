import Link from "next/link";
import { formatTimeRange } from "@/lib/time";

export type MapEntry = { id: number; term: string; keyframe_url: string | null };
export type MapStep = {
  pack_stage_id: string | null;
  name: string;
  t_start: number;
  t_end: number;
  entries: MapEntry[];
};

function widthPct(s: MapStep, duration: number): string {
  const d = Math.max(1, duration);
  const w = Math.max(4, ((s.t_end - s.t_start) / d) * 100);
  return `${w.toFixed(1)}%`;
}

export function ProcessMapBand({
  steps,
  duration,
  slug,
}: {
  steps: MapStep[];
  duration: number;
  slug: string;
}) {
  if (steps.length === 0) {
    return <p className="text-sm text-[var(--muted)]">No process map yet.</p>;
  }
  return (
    <div className="flex w-full items-stretch gap-px overflow-hidden border border-[var(--line)]">
      {steps.map((s, i) => {
        const first = s.entries[0];
        const inner = (
          <span className="flex h-full min-w-0 flex-col justify-between gap-1 p-2">
            <span className="truncate text-xs font-medium">{s.name}</span>
            <span className="truncate font-mono text-[10px] text-[var(--muted)]">
              {formatTimeRange(s.t_start, s.t_end)}
            </span>
          </span>
        );
        return (
          <span
            key={i}
            className="group block bg-[var(--surface)] hover:bg-[var(--accent)] hover:text-white"
            style={{ width: widthPct(s, duration) }}
            title={s.name}
          >
            {first ? (
              <Link href={`/d/${slug}/${first.id}`} className="flex h-full">
                {inner}
              </Link>
            ) : (
              inner
            )}
          </span>
        );
      })}
    </div>
  );
}