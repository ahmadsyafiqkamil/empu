import Link from "next/link";
import { ProcessMapBand, type MapStep } from "@/components/ProcessMapBand";
import { formatTimeRange } from "@/lib/time";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

type ProcessMap = {
  recording_id: number;
  title: string;
  duration_s: number | null;
  steps: MapStep[];
};

type ArchiveMeta = { title: string };

export default async function ProcessMapPage({
  params,
}: {
  params: Promise<{ slug: string; recordingId: string }>;
}) {
  const { slug, recordingId } = await params;
  const archive: ArchiveMeta | null = await fetch(
    `${API}/api/public/archives/${slug}`,
    { cache: "no-store" },
  )
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
  const r = await fetch(`${API}/api/public/recordings/${recordingId}/process-map`, {
    cache: "no-store",
  });
  if (!r.ok) {
    return (
      <p className="p-8">
        This recording isn&apos;t public, or it has no process map yet.
      </p>
    );
  }
  const map: ProcessMap = await r.json();
  const duration = map.duration_s ?? 0;

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <p className="text-sm text-[var(--muted)]">
        <Link href={`/d/${slug}`} className="underline">
          {archive?.title ?? slug}
        </Link>{" "}
        · {map.title}
      </p>
      <h1 className="mt-2 font-display text-3xl">{map.title}</h1>

      {/* Desktop: horizontal band */}
      <div className="mt-8 hidden md:block">
        <ProcessMapBand steps={map.steps} duration={duration} slug={slug} />
        <p className="mt-3 text-xs text-[var(--muted)]">
          Each band is one process stage. Select a band to open its first term.
        </p>
      </div>

      {/* Mobile: vertical list */}
      <ol className="mt-8 divide-y divide-[var(--line)] md:hidden">
        {map.steps.map((s, i) => (
          <li key={i} className="py-3">
            <p className="font-display text-lg">{s.name}</p>
            <p className="font-mono text-xs text-[var(--muted)]">
              {formatTimeRange(s.t_start, s.t_end)}
            </p>
            <ul className="mt-2 space-y-1 text-sm">
              {s.entries.map((e) => (
                <li key={e.id}>
                  <Link href={`/d/${slug}/${e.id}`} className="underline">
                    {e.term}
                  </Link>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </main>
  );
}