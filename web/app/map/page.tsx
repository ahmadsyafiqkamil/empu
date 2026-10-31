import Link from "next/link";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { COPY } from "@/lib/copy";
import { formatTime } from "@/lib/time";
import type { Archive, RecordingSummary } from "@/lib/types";

const API = process.env.EMPU_API_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export default async function ProcessMapIndex() {
  const archives: Archive[] = await fetch(`${API}/api/public/archives`, { cache: "no-store" })
    .then((r) => r.json())
    .catch(() => []);

  const recordings: RecordingSummary[][] = await Promise.all(
    archives.map((a) =>
      fetch(`${API}/api/public/archives/${a.slug}/recordings`, { cache: "no-store" })
        .then((r) => (r.ok ? (r.json() as Promise<RecordingSummary[]>) : []))
        .catch(() => [] as RecordingSummary[]),
    ),
  );

  return (
    <>
      <PublicHeader />
      <main className="mx-auto w-full max-w-[1100px] px-5 pt-8 pb-16 lg:px-0">
        <p className="label">Process map</p>
        <h1 className="mt-2 text-[34px] leading-none tracking-[-0.03em] md:text-[44px] lg:text-[52px]">
          How a recording becomes a dictionary
        </h1>
        <p className="mt-3 max-w-[680px] text-[15px] text-[var(--color-neutral-800)]">
          Each recording is divided into the stages of the craft. Every accepted term sits inside
          the stage where the maker actually said it, so you can read the process in order.
        </p>

        {archives.length === 0 ? (
          <div className="empty mt-8">
            <span>{COPY.empty.dictionary}</span>
          </div>
        ) : (
          archives.map((a, i) => {
            const recs = recordings[i] ?? [];
            return (
              <section key={a.slug} className="pt-10">
                <div className="flex flex-wrap items-baseline justify-between gap-2 border-b-2 border-[var(--color-divider)] pb-2">
                  <h2 className="m-0 text-[22px] tracking-[-0.01em] lg:text-[26px]">{a.title}</h2>
                  <Link href={`/d/${a.slug}`} className="text-[13px]">
                    Open the dictionary →
                  </Link>
                </div>
                {recs.length === 0 ? (
                  <p className="mt-4 text-[13px] text-[var(--color-neutral-700)]">
                    No public recording in this archive yet.
                  </p>
                ) : (
                  <ul className="m-0 flex list-none flex-col p-0">
                    {recs.map((r) => (
                      <li key={r.id}>
                        <Link
                          href={`/d/${a.slug}/map/${r.id}`}
                          className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-[var(--color-divider)] py-4 text-[var(--color-text)] no-underline hover:bg-[var(--color-surface)]"
                        >
                          <span className="min-w-0">
                            <span className="block text-[16px] font-semibold">{r.title}</span>
                            <span className="block text-[12px] text-[var(--color-neutral-700)]">
                              {r.n_entries} public terms
                              {r.duration_s ? ` · ${formatTime(r.duration_s)}` : ""}
                            </span>
                          </span>
                          <span className="mono text-[12px] text-[var(--color-neutral-700)]">
                            {r.duration_s ? formatTime(r.duration_s) : ""}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            );
          })
        )}
      </main>
      <PublicFooter />
    </>
  );
}
